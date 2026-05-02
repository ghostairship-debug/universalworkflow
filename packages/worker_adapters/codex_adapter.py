from __future__ import annotations

import os
import json
import hashlib
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from packages.contracts import MutationMode, TaskKind, TaskPacket
from packages.core_domain.compile import build_artifact_content
from packages.core_domain.config import build_effective_config
from packages.core_domain.errors import WorkerAdapterUnavailableError
from packages.worker_adapters.base import ExecutionResult, utc_now
from packages.worker_adapters.cli_base import CliAdapterBase, CompletedProcessRunner
from packages.worker_adapters.subprocess_support import (
    TIMEOUT_EXIT_CODE,
    build_subprocess_env,
    completed_process_watchdog_metadata,
    completed_process_from_timeout,
    run_subprocess_with_tree_timeout,
)


DEFAULT_CODEX_MODEL = "gpt-5.4"
DEFAULT_CODEX_REASONING_EFFORT = "xhigh"
DOGFOOD_ARTIFACT_RUNTIME_BRIEF_LIMIT = 1200
DOGFOOD_ARTIFACT_HANDOFF_LIMIT = 1400
DOGFOOD_ARTIFACT_RESPONSIBILITY_LIMIT = 6
STREAM_PREVIEW_LIMIT = 4000
PROVIDER_STREAM_EVENT_TYPE = "provider_stream_observed"
PATCH_APPLY_DISABLED_CODEX_FEATURES = (
    "apps",
    "plugins",
    "memories",
    "tool_search",
    "browser_use",
    "computer_use",
    "image_generation",
    "workspace_dependencies",
)
PATCH_APPLY_PROMPT_WORKSPACE_ROOT = "workflow_codex_patch_apply"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _coerce_codex_timeout_seconds(raw_value: str | None, default: int) -> int:
    if raw_value is None or not raw_value.strip():
        return default
    try:
        return max(1, int(raw_value))
    except ValueError:
        return default


def _resolve_codex_timeout_seconds(default: int) -> int:
    return _coerce_codex_timeout_seconds(os.getenv("WORKFLOW_CODEX_TIMEOUT_SECONDS"), default)


def _resolve_codex_idle_timeout_seconds(timeout_seconds: int) -> int:
    raw_value = os.getenv("WORKFLOW_CODEX_IDLE_TIMEOUT_SECONDS") or os.getenv("WORKFLOW_PROVIDER_IDLE_TIMEOUT_SECONDS")
    return _coerce_codex_timeout_seconds(raw_value, min(timeout_seconds, 120))


def _stream_preview(value: str, *, limit: int = STREAM_PREVIEW_LIMIT) -> str:
    if len(value) <= limit:
        return value
    return value[-limit:]


def _safe_codex_event_metadata(text: str) -> tuple[str | None, list[str]]:
    stripped = text.strip()
    if not stripped:
        return None, []
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None, []
    if not isinstance(payload, dict):
        return None, []
    msg = payload.get("msg")
    event_type = payload.get("type") or payload.get("event") or (msg.get("type") if isinstance(msg, dict) else None)
    return (str(event_type) if event_type is not None else None), sorted(str(key) for key in payload.keys())[:20]


def _safe_path_segment(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return cleaned[:96] or "unknown"


class CodexAdapter(CliAdapterBase):
    adapter_name = "codex"
    route_priority = 90
    executable_name = "codex"

    def __init__(
        self,
        *,
        model: str | None = None,
        runner: CompletedProcessRunner | None = None,
        executable: str | None = None,
        sandbox_mode: str = "read-only",
        ephemeral: bool = True,
        reasoning_effort: str | None = None,
    ):
        super().__init__(runner=runner)
        effective = build_effective_config()
        self.model = model or str(effective["codex"]["model"] or os.getenv("WORKFLOW_CODEX_MODEL", DEFAULT_CODEX_MODEL))
        self.reasoning_effort = reasoning_effort or str(
            effective["codex"]["reasoning_effort"]
            or os.getenv("WORKFLOW_CODEX_REASONING_EFFORT", DEFAULT_CODEX_REASONING_EFFORT)
        )
        self.executable = executable or self.executable_name
        self.sandbox_mode = sandbox_mode
        self.ephemeral = ephemeral
        self.timeout_seconds = _resolve_codex_timeout_seconds(self.timeout_seconds)

    def get_capabilities(self) -> list[str]:
        return [str(TaskKind.shell_exec)]

    def supports_mutation_mode(self, mode: MutationMode | str) -> bool:
        normalized = MutationMode(mode)
        return normalized in {MutationMode.artifact_only, MutationMode.patch_apply}

    def _resolved_executable(self) -> str:
        resolved = shutil.which(self.executable)
        if resolved:
            return resolved
        raise WorkerAdapterUnavailableError(
            self.normalized_name(),
            "codex executable was not found on PATH",
            {"executable": self.executable},
        )

    def _provider_stream_callback_for(self, packet: TaskPacket):
        db_path = packet.env.get("WORKFLOW_DB_PATH")
        if not db_path:
            return None
        runtime_task_id = packet.runtime_task_id
        run_id = packet.run_id
        adapter_name = self.normalized_name()
        task_card_ref = packet.mutation_contract.task_card_ref if packet.mutation_contract is not None else None
        counter = {"line_index": 0}

        def _record(event: dict[str, object]) -> None:
            text = str(event.get("text") or "")
            if not text:
                return
            counter["line_index"] += 1
            provider_event_type, parsed_keys = _safe_codex_event_metadata(text)
            is_control = bool(event.get("is_control"))
            is_material_progress = bool(event.get("is_material_progress"))
            classification = "control" if is_control else "provider_output"
            observed_at = str(event.get("observed_at") or _utc_now_iso())
            payload = {
                "trace_context": {
                    "run_id": run_id,
                    "runtime_task_id": runtime_task_id,
                },
                "run_id": run_id,
                "runtime_task_id": runtime_task_id,
                "adapter_name": adapter_name,
                "stream": str(event.get("stream") or "stdout"),
                "classification": classification,
                "observed_at": observed_at,
                "byte_count": int(event.get("byte_count") or len(text.encode("utf-8", errors="replace"))),
                "line_index": counter["line_index"],
                "line_sha256": hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest(),
                "provider_event_type": provider_event_type,
                "parsed_keys": parsed_keys,
                "is_material_progress": is_material_progress,
                "task_card_ref": task_card_ref,
            }
            try:
                with sqlite3.connect(db_path) as connection:
                    connection.execute(
                        """
                        INSERT INTO run_events (
                          event_id, run_id, event_type, object_type, object_id, summary,
                          payload_json, schema_version, created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            f"event_{uuid4().hex[:12]}",
                            run_id,
                            PROVIDER_STREAM_EVENT_TYPE,
                            "runtime_task",
                            runtime_task_id,
                            "Provider stream observed from Codex adapter",
                            json.dumps(payload, ensure_ascii=False, sort_keys=True),
                            "v1",
                            observed_at,
                        ),
                    )
                    connection.commit()
            except sqlite3.Error:
                return

        return _record

    def _artifact_path_for(self, packet: TaskPacket) -> str:
        artifact = packet.expected_artifacts[0] if packet.expected_artifacts else "state/artifacts/codex_output.md"
        path = Path(artifact)
        if not path.is_absolute():
            path = Path(packet.working_directory) / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path.resolve().as_posix()

    def _prompt_workspace_for(self, packet: TaskPacket) -> Path:
        if self._mutation_mode_for(packet) != MutationMode.patch_apply:
            return Path(packet.working_directory).resolve()
        override = packet.env.get("WORKFLOW_CODEX_PATCH_APPLY_PROMPT_WORKSPACE")
        if override:
            root = Path(override)
        else:
            root = Path(tempfile.gettempdir()) / PATCH_APPLY_PROMPT_WORKSPACE_ROOT
        task_ref = ""
        if packet.mutation_contract is not None and packet.mutation_contract.task_card_ref:
            task_ref = packet.mutation_contract.task_card_ref
        prompt_workspace = (
            root
            / _safe_path_segment(packet.run_id or "run")
            / _safe_path_segment(packet.runtime_task_id or task_ref or "task")
        )
        prompt_workspace.mkdir(parents=True, exist_ok=True)
        return prompt_workspace.resolve()

    def _mutation_mode_for(self, packet: TaskPacket) -> MutationMode:
        if packet.mutation_contract is not None:
            return MutationMode(packet.mutation_contract.mutation_mode)
        return MutationMode(packet.env.get("WORKFLOW_MUTATION_MODE", MutationMode.artifact_only))

    def _artifact_content_for(self, packet: TaskPacket) -> str:
        if packet.env.get("WORKFLOW_PRESET_ID") == "capability_probe" and packet.env.get("WORKFLOW_CAPABILITY_PROBE_CONTRACT_JSON"):
            return str(packet.env["WORKFLOW_CAPABILITY_PROBE_CONTRACT_JSON"]).strip() + "\n"
        return build_artifact_content(
            preset_id=packet.env.get("WORKFLOW_PRESET_ID", ""),
            goal=packet.env.get("WORKFLOW_RUN_GOAL", ""),
            adapter_name=self.normalized_name(),
            domain_pack_id=packet.env.get("WORKFLOW_DOMAIN_PACK_ID") or None,
            runtime_gateway=packet.env.get("WORKFLOW_RUNTIME_GATEWAY_PROVIDER") or None,
            runtime_model=packet.env.get("WORKFLOW_LLM_MODEL") or None,
            runtime_brief=packet.env.get("WORKFLOW_RUNTIME_BRIEF") or None,
        )

    def _is_dogfood_artifact_agent(self, packet: TaskPacket) -> bool:
        return (
            self._mutation_mode_for(packet) == MutationMode.artifact_only
            and packet.env.get("WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED") == "true"
            and packet.env.get("WORKFLOW_DOGFOOD_EXECUTION_BACKEND") == "codex_cli"
            and packet.env.get("WORKFLOW_MODEL_SELECTION_SOURCE") == "dogfood_strong_codex_cli"
        )

    def _dogfood_artifact_prompt_for(self, packet: TaskPacket) -> str:
        responsibilities = []
        try:
            parsed = json.loads(packet.env.get("WORKFLOW_ROLE_RESPONSIBILITIES", "[]"))
            if isinstance(parsed, list):
                responsibilities = [str(item) for item in parsed[:DOGFOOD_ARTIFACT_RESPONSIBILITY_LIMIT]]
        except json.JSONDecodeError:
            responsibilities = []
        role_label = packet.env.get("WORKFLOW_ROLE_LABEL") or "workflow_role"
        public_role = packet.env.get("WORKFLOW_PUBLIC_ROLE") or "unknown"
        cluster_template_id = packet.env.get("WORKFLOW_CLUSTER_TEMPLATE_ID") or "unknown_cluster"
        cluster_member_id = packet.env.get("WORKFLOW_CLUSTER_MEMBER_ID") or "unknown_member"
        handoff_context = packet.env.get("WORKFLOW_ORCHESTRATION_PLAN_GRAPH") or "{}"
        runtime_brief = packet.env.get("WORKFLOW_RUNTIME_BRIEF") or ""
        compact_runtime_brief = runtime_brief[:DOGFOOD_ARTIFACT_RUNTIME_BRIEF_LIMIT]
        compact_handoff_context = handoff_context[:DOGFOOD_ARTIFACT_HANDOFF_LIMIT]
        return (
            "You are a Codex CLI artifact-only workflow agent in a local personal operator runtime.\n"
            "Do not mutate repository files. Produce a concise, useful markdown artifact only.\n"
            f"Working directory: {Path(packet.working_directory).resolve().as_posix()}\n"
            f"Goal: {packet.env.get('WORKFLOW_RUN_GOAL', '')}\n"
            f"Preset: {packet.env.get('WORKFLOW_PRESET_ID', '')}\n"
            f"Cluster template: {cluster_template_id}\n"
            f"Cluster member: {cluster_member_id}\n"
            f"Public role: {public_role}\n"
            f"Role label: {role_label}\n"
            f"Responsibilities JSON: {json.dumps(responsibilities, ensure_ascii=False)}\n"
            f"Runtime brief: {compact_runtime_brief}\n"
            f"Handoff context JSON: {compact_handoff_context}\n"
            "Return markdown with these headings exactly:\n"
            "# Artifact\n"
            "## Role Output\n"
            "## Key Decisions\n"
            "## Risks And Checks\n"
            "## Handoff\n"
            "Do not wrap the artifact in code fences. Do not include a patch or shell commands.\n"
        )

    def _model_for_packet(self, packet: TaskPacket) -> str:
        return str(packet.env.get("WORKFLOW_CODEX_MODEL") or self.model)

    def _reasoning_effort_for_packet(self, packet: TaskPacket) -> str | None:
        return packet.env.get("WORKFLOW_CODEX_REASONING_EFFORT") or self.reasoning_effort

    def _timeout_seconds_for_packet(self, packet: TaskPacket) -> int:
        return _coerce_codex_timeout_seconds(
            packet.env.get("WORKFLOW_CODEX_TIMEOUT_SECONDS") or os.getenv("WORKFLOW_CODEX_TIMEOUT_SECONDS"),
            self.timeout_seconds,
        )

    def _idle_timeout_seconds_for_packet(self, packet: TaskPacket, timeout_seconds: int) -> int:
        raw_value = (
            packet.env.get("WORKFLOW_CODEX_IDLE_TIMEOUT_SECONDS")
            or packet.env.get("WORKFLOW_PROVIDER_IDLE_TIMEOUT_SECONDS")
            or os.getenv("WORKFLOW_CODEX_IDLE_TIMEOUT_SECONDS")
            or os.getenv("WORKFLOW_PROVIDER_IDLE_TIMEOUT_SECONDS")
        )
        if raw_value is None or not raw_value.strip():
            return _resolve_codex_idle_timeout_seconds(timeout_seconds)
        return _coerce_codex_timeout_seconds(raw_value, min(timeout_seconds, 120))

    def _env_value_or_file(self, packet: TaskPacket, key: str, default: str = "") -> str:
        value = packet.env.get(key)
        if value:
            return str(value)
        file_path = packet.env.get(f"{key}_FILE")
        if not file_path:
            return default
        try:
            return Path(file_path).read_text(encoding="utf-8")
        except OSError:
            return default

    def _prompt_for(self, packet: TaskPacket) -> str:
        mutation_mode = self._mutation_mode_for(packet)
        if mutation_mode == MutationMode.patch_apply:
            write_set = packet.env.get("WORKFLOW_MUTATION_WRITE_SET", "[]")
            read_set = packet.env.get("WORKFLOW_MUTATION_READ_SET", "[]")
            test_commands = packet.env.get("WORKFLOW_MUTATION_TEST_COMMANDS", "[]")
            attempt_index = packet.env.get("WORKFLOW_MUTATION_ATTEMPT_INDEX", "0")
            failure_feedback = packet.env.get("WORKFLOW_MUTATION_FAILURE_FEEDBACK", "").strip()
            provider_command_policy = packet.env.get("WORKFLOW_MUTATION_PROVIDER_COMMAND_POLICY", "patch_only_no_shell")
            read_set_context = self._env_value_or_file(packet, "WORKFLOW_MUTATION_READ_SET_CONTEXT", "[]")
            task_card_ref = packet.env.get("WORKFLOW_MUTATION_TASK_CARD_REF", "").strip()
            task_card_content = self._env_value_or_file(packet, "WORKFLOW_MUTATION_TASK_CARD_CONTENT", "").strip()
            failure_block = (
                "Previous attempt failed. Use the feedback below to produce a corrected patch.\n"
                f"{failure_feedback}\n"
                if failure_feedback
                else ""
            )
            task_card_block = (
                f"Task card ref: {task_card_ref}\nTask card content:\n{task_card_content}\n"
                if task_card_ref or task_card_content
                else ""
            )
            return (
                "You are executing a single-turn prompt-only patch proposal for a controlled repository.\n"
                f"Patch target working directory: {Path(packet.working_directory).resolve().as_posix()}\n"
                f"Attempt index: {attempt_index}\n"
                f"Allowed write_set JSON: {write_set}\n"
                f"Read-only context paths JSON: {read_set}\n"
                f"Embedded read-set context JSON: {read_set_context}\n"
                f"Explicit test commands JSON: {test_commands}\n"
                f"Provider command policy: {provider_command_policy}.\n"
                "Patch-only mode: do not run shell, PowerShell, cmd, Python, Node, npm, package-manager, "
                "file-inspection, or other tool commands. Do not ask for command output. Use only the "
                "embedded task-card content, read-set context, failure feedback, and paths already provided here.\n"
                "The CLI working directory is an isolated prompt-only broker directory; do not inspect it.\n"
                f"{task_card_block}"
                f"{failure_block}"
                "Return exactly one valid unified diff patch that modifies files inside write_set.\n"
                "Do not wrap the patch in code fences. Do not add commentary before or after the diff.\n"
                "Do not include shell transcripts, markdown, explanations, or non-diff text.\n"
            )
        if self._is_dogfood_artifact_agent(packet):
            return self._dogfood_artifact_prompt_for(packet)
        content = self._artifact_content_for(packet)
        return (
            "You are executing a local workflow task inside a controlled repository.\n"
            f"Working directory: {Path(packet.working_directory).resolve().as_posix()}\n"
            "Return only the exact UTF-8 file content shown between the markers below.\n"
            "Do not wrap it in code fences. Do not add commentary. Do not add any extra lines.\n"
            "<<<WORKFLOW_FILE>>>\n"
            f"{content}"
            "<<<END_WORKFLOW_FILE>>>\n"
        )

    def build_command(self, packet: TaskPacket, *, prompt_via_stdin: bool = False) -> list[str]:
        artifact_path = self._artifact_path_for(packet)
        command_cwd = self._prompt_workspace_for(packet)
        command = [
            self._resolved_executable(),
            "exec",
            "--json",
            "--output-last-message",
            artifact_path,
            "--cd",
            command_cwd.as_posix(),
            "--skip-git-repo-check",
            "--sandbox",
            self.sandbox_mode,
            "--color",
            "never",
        ]
        if self._mutation_mode_for(packet) == MutationMode.patch_apply:
            command.append("--ignore-user-config")
            command.append("--ignore-rules")
            for feature in PATCH_APPLY_DISABLED_CODEX_FEATURES:
                command.extend(["--disable", feature])
        if self.ephemeral:
            command.append("--ephemeral")
        model = self._model_for_packet(packet)
        reasoning_effort = self._reasoning_effort_for_packet(packet)
        if model:
            command.extend(["--model", model])
        if reasoning_effort:
            command.extend(["-c", f'model_reasoning_effort="{reasoning_effort}"'])
        command.append("-" if prompt_via_stdin else self._prompt_for(packet))
        return command

    def launch(self, packet: TaskPacket) -> ExecutionResult:
        started_at = utc_now()
        use_stdin_prompt = self._runner is subprocess.run
        command = self.build_command(packet, prompt_via_stdin=use_stdin_prompt)
        command_cwd = self._prompt_workspace_for(packet)
        env = build_subprocess_env(packet.env)
        timeout_seconds = self._timeout_seconds_for_packet(packet)
        idle_timeout_seconds = self._idle_timeout_seconds_for_packet(packet, timeout_seconds)
        run_kwargs = {
            "cwd": command_cwd.as_posix(),
            "env": env,
            "capture_output": True,
            "text": True,
            "check": False,
            "timeout": timeout_seconds,
        }
        if use_stdin_prompt:
            run_kwargs["input"] = self._prompt_for(packet)
            run_kwargs["encoding"] = "utf-8"
            run_kwargs["errors"] = "replace"
        try:
            if use_stdin_prompt:
                stream_callback = self._provider_stream_callback_for(packet)
                if stream_callback is not None:
                    run_kwargs["on_output"] = stream_callback
                completed = run_subprocess_with_tree_timeout(command, **run_kwargs, idle_timeout=idle_timeout_seconds)
            else:
                completed = self._runner(command, **run_kwargs)
        except subprocess.TimeoutExpired as exc:
            completed = completed_process_from_timeout(exc, command=command, timeout_seconds=timeout_seconds)
        finished_at = utc_now()
        failure_class = None
        if completed.returncode == TIMEOUT_EXIT_CODE:
            failure_class = "provider_timeout"
        elif completed.returncode != 0:
            failure_class = "execution_failed"
        metadata = {
            "mutation_mode": str(self._mutation_mode_for(packet)),
            "codex_model": self._model_for_packet(packet),
            "codex_reasoning_effort": self._reasoning_effort_for_packet(packet),
            "sandbox_mode": self.sandbox_mode,
            "ephemeral": self.ephemeral,
            "timeout_seconds": timeout_seconds,
            "idle_timeout_seconds": idle_timeout_seconds,
            "provider_command_policy": packet.env.get("WORKFLOW_MUTATION_PROVIDER_COMMAND_POLICY"),
            "transport_isolation_enabled": self._mutation_mode_for(packet) == MutationMode.patch_apply,
            "transport_disabled_features": list(PATCH_APPLY_DISABLED_CODEX_FEATURES)
            if self._mutation_mode_for(packet) == MutationMode.patch_apply
            else [],
            "prompt_transport": "stdin" if use_stdin_prompt else "argv",
            "prompt_workspace": command_cwd.as_posix(),
            "project_working_directory": Path(packet.working_directory).resolve().as_posix(),
            "project_rules_ignored": self._mutation_mode_for(packet) == MutationMode.patch_apply,
            **completed_process_watchdog_metadata(completed),
        }
        if failure_class is not None:
            metadata.update(
                {
                    "failure_class": failure_class,
                    "stdout_preview": _stream_preview(str(completed.stdout or "")),
                    "stderr_preview": _stream_preview(str(completed.stderr or "")),
                }
            )
        if self._is_dogfood_artifact_agent(packet):
            metadata.update(
                {
                    "prompt_family": "dogfood_artifact_agent",
                    "prompt_chars": len(self._prompt_for(packet)),
                    "role_label": packet.env.get("WORKFLOW_ROLE_LABEL") or "workflow_role",
                    "public_role": packet.env.get("WORKFLOW_PUBLIC_ROLE") or "unknown",
                    "cluster_template_id": packet.env.get("WORKFLOW_CLUSTER_TEMPLATE_ID") or "unknown_cluster",
                    "cluster_member_id": packet.env.get("WORKFLOW_CLUSTER_MEMBER_ID") or "unknown_member",
                }
            )
        return ExecutionResult(
            runtime_task_id=packet.runtime_task_id,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=max(int((finished_at - started_at).total_seconds() * 1000), 0),
            artifact_paths=self.collect_artifacts(packet),
            adapter_name=self.normalized_name(),
            metadata=metadata,
        )
