from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

from packages.contracts import CapabilityProbeResult, MutationMode, TaskKind, TaskPacket
from packages.core_domain.db import migrate
from packages.core_domain.errors import WorkerAdapterUnavailableError
from packages.core_domain.repositories import CapabilityProbeResultRepository
from packages.worker_adapters.base import ExecutionResult
from packages.worker_adapters.codex_adapter import CodexAdapter
from packages.worker_adapters.external_artifact_adapters import (
    ClaudeArchitectAdapter,
    MMXMultimodalAdapter,
    VertexMultimodalAdapter,
)
from packages.worker_adapters.langchain_agent_adapter import LangChainAgentAdapter
from packages.worker_adapters.opencode_adapter import OpenCodeAdapter
from packages.worker_adapters.shell_adapter import ShellAdapter


PROVIDERS = ["shell", "codex", "opencode", "mmx", "vertex", "claude", "langchain"]
DEFAULT_PROBE_TIMEOUT_SECONDS = 120
GENERIC_ASSISTANT_PATTERNS = (
    "how can i help",
    "how may i help",
    "hello! how can",
    "what can i help",
    "i'm here to help",
)
SIMULATED_OR_DRY_RUN_PATTERNS = (
    "simulated probe",
    "simulated action",
    "dry-run",
    "dry run",
    "cannot access external systems",
    "can't access external systems",
    "unable to access external systems",
    "no actual api call",
    "actual api call was not",
    "not actually executed",
    "fallback-only",
    "fallback only",
    "hypothetical",
)


def _preview(value: str | None, limit: int = 1000) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text[:limit]


def _packet_for_provider(provider: str, workspace_root: Path, evidence_dir: Path) -> TaskPacket:
    artifact = evidence_dir / f"{provider}_probe.md"
    proof_contract = {
        "status": "ok",
        "probe": "executed",
        "provider": provider,
        "live_backend": True,
        "no_fallback": True,
    }
    env = {
        "WORKFLOW_RUN_GOAL": f"Live capability probe for {provider}. Return a tiny proof of execution.",
        "WORKFLOW_PRESET_ID": "capability_probe",
        "WORKFLOW_TASK_KIND": str(TaskKind.shell_exec),
        "WORKFLOW_MUTATION_MODE": str(MutationMode.artifact_only),
        "WORKFLOW_RUNTIME_BRIEF": (
            "M67 live provider smoke. Do not mutate repository files. "
            "Return concrete evidence from the invoked backend. "
            f"Return only this proof JSON when possible: {json.dumps(proof_contract, sort_keys=True)}"
        ),
        "WORKFLOW_CAPABILITY_PROBE_PROVIDER": provider,
        "WORKFLOW_CAPABILITY_PROBE_CONTRACT_JSON": json.dumps(proof_contract, sort_keys=True),
        "WORKFLOW_CODEX_TIMEOUT_SECONDS": os.getenv("WORKFLOW_CODEX_TIMEOUT_SECONDS", "120"),
        "WORKFLOW_CLAUDE_ARCHITECT_ENABLED": os.getenv("WORKFLOW_CLAUDE_ARCHITECT_ENABLED", "1"),
    }
    command = [sys.executable, "-c", "print('workflow-shell-probe')"] if provider == "shell" else []
    return TaskPacket(
        runtime_task_id=f"probe_{provider}",
        run_id="capability_probe",
        task_kind=TaskKind.shell_exec,
        command=command,
        working_directory=workspace_root.as_posix(),
        env=env,
        expected_artifacts=[artifact.as_posix()],
    )


def _adapter_for_provider(provider: str):
    if provider == "shell":
        return ShellAdapter()
    if provider == "codex":
        return CodexAdapter(sandbox_mode="read-only", ephemeral=True)
    if provider == "opencode":
        return OpenCodeAdapter(pure=True, auto_approve=False)
    if provider == "mmx":
        return MMXMultimodalAdapter()
    if provider == "vertex":
        return VertexMultimodalAdapter()
    if provider == "claude":
        return ClaudeArchitectAdapter()
    if provider == "langchain":
        return LangChainAgentAdapter()
    raise ValueError(f"unsupported provider: {provider}")


def _apply_probe_timeout_to_adapter(adapter: object) -> None:
    if not hasattr(adapter, "timeout_seconds"):
        return
    outer_timeout = _probe_timeout_seconds()
    adapter_timeout = max(1, outer_timeout - 5) if outer_timeout > 5 else outer_timeout
    try:
        current_timeout = int(getattr(adapter, "timeout_seconds"))
    except (TypeError, ValueError):
        current_timeout = adapter_timeout
    setattr(adapter, "timeout_seconds", min(current_timeout, adapter_timeout))


def _auth_source_for_provider(provider: str) -> str | None:
    candidates = {
        "codex": ["codex_cli_login", "OPENAI_API_KEY"],
        "opencode": ["MINIMAX_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"],
        "mmx": ["MINIMAX_API_KEY", "MINIMAX_TOKEN"],
        "vertex": ["GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT"],
        "claude": ["ANTHROPIC_API_KEY", "claude_cli_login"],
        "langchain": ["MINIMAX_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"],
        "shell": ["local_python"],
    }.get(provider, [])
    for candidate in candidates:
        if candidate.endswith("_login") or candidate == "local_python":
            return candidate
        if os.getenv(candidate):
            return candidate
    return None


def _result_from_execution(
    *,
    provider: str,
    adapter_name: str | None,
    live_probe: bool,
    execution: ExecutionResult,
    evidence_path: str | None,
) -> CapabilityProbeResult:
    stdout = execution.stdout or ""
    stderr = execution.stderr or ""
    artifact_text = ""
    if evidence_path:
        try:
            artifact_text = Path(evidence_path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            artifact_text = ""
    proof_ok, failure_class, proof_metadata = _classify_live_probe_evidence(
        provider=provider,
        adapter_name=adapter_name,
        stdout=stdout,
        artifact_text=artifact_text,
    )
    success = execution.return_code == 0 and proof_ok
    return CapabilityProbeResult(
        provider=provider,
        adapter_name=adapter_name,
        status="verified_ready" if success else "blocked",
        live_probe=live_probe,
        auth_source=_auth_source_for_provider(provider),
        latency_ms=execution.duration_ms,
        failure_class=None if success else (failure_class or "probe_failed"),
        evidence_path=evidence_path,
        fallback_route=None if success else "manual_investigation_required",
        return_code=execution.return_code,
        stdout_preview=_preview(stdout),
        stderr_preview=_preview(stderr),
        metadata={"artifact_paths": execution.artifact_paths, "proof": proof_metadata},
    )


def _contains_any_pattern(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in patterns)


def _iter_json_objects(text: str):
    stripped = text.strip()
    if not stripped:
        return
    decoder = json.JSONDecoder()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        yield payload
    index = 0
    while index < len(text):
        brace_index = text.find("{", index)
        if brace_index == -1:
            break
        try:
            payload, end_index = decoder.raw_decode(text[brace_index:])
        except json.JSONDecodeError:
            index = brace_index + 1
            continue
        if isinstance(payload, dict):
            yield payload
        index = brace_index + max(end_index, 1)


def _provider_adapter_values(provider: str, adapter_name: str | None) -> set[str]:
    values = {provider}
    if adapter_name:
        values.add(adapter_name)
    aliases = {
        "mmx": {"mmx_multimodal"},
        "vertex": {"vertex_multimodal"},
        "claude": {"claude_architect"},
        "langchain": {"agent", "langchain_agent"},
    }
    values.update(aliases.get(provider, set()))
    return {value.lower() for value in values}


def _classify_live_probe_evidence(
    *,
    provider: str,
    adapter_name: str | None,
    stdout: str,
    artifact_text: str,
) -> tuple[bool, str | None, dict[str, object]]:
    combined_text = "\n".join(item for item in [stdout or "", artifact_text or ""] if item)
    metadata: dict[str, object] = {"contract": "m67_live_proof_v1"}
    if not combined_text.strip():
        return False, "empty_output", metadata
    if '"status": "empty_output"' in artifact_text:
        return False, "empty_output", metadata
    if _contains_any_pattern(combined_text, SIMULATED_OR_DRY_RUN_PATTERNS):
        metadata["rejected_reason"] = "simulated_or_dry_run"
        return False, "simulated_or_dry_run_evidence", metadata
    if _contains_any_pattern(combined_text, GENERIC_ASSISTANT_PATTERNS):
        metadata["rejected_reason"] = "generic_assistant_reply"
        return False, "generic_assistant_evidence", metadata
    if provider == "shell":
        shell_ok = (
            "workflow-shell-probe" in combined_text
            or _artifact_has_live_proof(artifact_text, provider=provider, adapter_name=adapter_name)
            or _artifact_has_live_proof(stdout, provider=provider, adapter_name=adapter_name)
        )
        metadata["proof_type"] = "shell_stdout" if shell_ok else "missing_shell_marker"
        return (True, None, metadata) if shell_ok else (False, "missing_live_proof", metadata)
    if _artifact_has_live_proof(artifact_text, provider=provider, adapter_name=adapter_name) or _artifact_has_live_proof(
        stdout,
        provider=provider,
        adapter_name=adapter_name,
    ):
        metadata["proof_type"] = "json_live_proof"
        return True, None, metadata
    metadata["proof_type"] = "none"
    return False, "missing_live_proof", metadata


def _artifact_has_live_proof(artifact_text: str, *, provider: str, adapter_name: str | None) -> bool:
    text = artifact_text.strip()
    if not text:
        return False
    adapter_values = _provider_adapter_values(provider, adapter_name)
    for payload in _iter_json_objects(text):
        adapter_value = str(payload.get("adapter") or payload.get("provider") or "").lower()
        live_backend = payload.get("live_backend")
        no_fallback = payload.get("no_fallback")
        if (
            str(payload.get("status", "")).lower() == "ok"
            and str(payload.get("probe", "")).lower() == "executed"
            and adapter_value in adapter_values
            and live_backend is True
            and no_fallback is True
        ):
            return True
    return False

def probe_provider(
    *,
    provider: str,
    workspace_root: Path,
    evidence_dir: Path,
    require_live: bool,
) -> CapabilityProbeResult:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    if provider not in PROVIDERS:
        raise ValueError(f"unsupported provider: {provider}")
    if not require_live:
        return CapabilityProbeResult(
            provider=provider,
            adapter_name=provider,
            status="configured",
            live_probe=False,
            auth_source=_auth_source_for_provider(provider),
            evidence_path=None,
            metadata={"require_live": False},
        )
    try:
        adapter = _adapter_for_provider(provider)
        _apply_probe_timeout_to_adapter(adapter)
        packet = _packet_for_provider(provider, workspace_root, evidence_dir)
        execution = adapter.launch(packet)
        evidence_path = execution.artifact_paths[0] if execution.artifact_paths else None
        return _result_from_execution(
            provider=provider,
            adapter_name=adapter.normalized_name(),
            live_probe=True,
            execution=execution,
            evidence_path=evidence_path,
        )
    except WorkerAdapterUnavailableError as exc:
        return CapabilityProbeResult(
            provider=provider,
            adapter_name=provider,
            status="blocked",
            live_probe=True,
            auth_source=_auth_source_for_provider(provider),
            failure_class="adapter_unavailable",
            fallback_route="manual_investigation_required",
            stderr_preview=exc.message,
            metadata={"details": exc.details},
        )
    except Exception as exc:
        return CapabilityProbeResult(
            provider=provider,
            adapter_name=provider,
            status="blocked",
            live_probe=True,
            auth_source=_auth_source_for_provider(provider),
            failure_class=exc.__class__.__name__,
            fallback_route="manual_investigation_required",
            stderr_preview=str(exc),
        )


def _probe_timeout_seconds() -> int:
    raw_value = os.getenv("WORKFLOW_CAPABILITY_PROBE_TIMEOUT_SECONDS")
    if not raw_value:
        return DEFAULT_PROBE_TIMEOUT_SECONDS
    try:
        return max(1, int(raw_value))
    except ValueError:
        return DEFAULT_PROBE_TIMEOUT_SECONDS


def probe_provider_with_timeout(
    *,
    provider: str,
    workspace_root: Path,
    evidence_dir: Path,
    require_live: bool,
) -> CapabilityProbeResult:
    timeout_seconds = _probe_timeout_seconds()
    command = [
        sys.executable,
        "-m",
        "packages.core_domain.capability_probe",
        "--single-provider",
        provider,
        "--workspace-root",
        workspace_root.as_posix(),
        "--evidence-dir",
        evidence_dir.as_posix(),
    ]
    if require_live:
        command.append("--require-live")
    try:
        completed = subprocess.run(
            command,
            cwd=workspace_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return CapabilityProbeResult(
            provider=provider,
            adapter_name=provider,
            status="blocked",
            live_probe=require_live,
            auth_source=_auth_source_for_provider(provider),
            latency_ms=timeout_seconds * 1000,
            failure_class="probe_timeout",
            fallback_route="manual_investigation_required",
            stdout_preview=_preview(exc.output if isinstance(exc.output, str) else None),
            stderr_preview=f"capability probe timed out after {timeout_seconds}s",
            metadata={"command": command, "timeout_seconds": timeout_seconds},
        )
    try:
        payload = json.loads(completed.stdout)
        return CapabilityProbeResult.model_validate(payload)
    except Exception:
        return CapabilityProbeResult(
            provider=provider,
            adapter_name=provider,
            status="blocked",
            live_probe=require_live,
            auth_source=_auth_source_for_provider(provider),
            failure_class="probe_subprocess_failed",
            fallback_route="manual_investigation_required",
            return_code=completed.returncode,
            stdout_preview=_preview(completed.stdout),
            stderr_preview=_preview(completed.stderr),
            metadata={"command": command},
        )


def run_capability_probes(
    *,
    provider: str,
    workspace_root: Path,
    evidence_dir: Path,
    require_live: bool,
    db_path: str | Path | None = None,
    recorder: Callable[[CapabilityProbeResult], None] | None = None,
) -> dict[str, object]:
    providers = PROVIDERS if provider == "all" else [provider]
    if db_path is not None:
        migrate(db_path)
        repo = CapabilityProbeResultRepository(db_path)
        recorder = recorder or (lambda result: repo.create(result))
    results = []
    for item in providers:
        result = probe_provider_with_timeout(
            provider=item,
            workspace_root=workspace_root,
            evidence_dir=evidence_dir,
            require_live=require_live,
        )
        if recorder is not None:
            recorder(result)
        results.append(result.model_dump(mode="json"))
    blocked = [item for item in results if item["status"] == "blocked"]
    return {
        "provider": provider,
        "require_live": require_live,
        "overall_status": "blocked" if blocked else "passed",
        "blocked_count": len(blocked),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run a single capability probe.")
    parser.add_argument("--single-provider", choices=PROVIDERS, required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--require-live", action="store_true")
    args = parser.parse_args(argv)
    result = probe_provider(
        provider=args.single_provider,
        workspace_root=Path(args.workspace_root).resolve(),
        evidence_dir=Path(args.evidence_dir).resolve(),
        require_live=args.require_live,
    )
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0 if result.status != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
