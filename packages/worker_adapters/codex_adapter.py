from __future__ import annotations

import os
import json
import shutil
import subprocess
from pathlib import Path

from packages.contracts import MutationMode, TaskKind, TaskPacket
from packages.core_domain.compile import build_artifact_content
from packages.core_domain.config import build_effective_config
from packages.core_domain.errors import WorkerAdapterUnavailableError
from packages.worker_adapters.base import ExecutionResult, utc_now
from packages.worker_adapters.cli_base import CliAdapterBase, CompletedProcessRunner
from packages.worker_adapters.subprocess_support import (
    build_subprocess_env,
    completed_process_from_timeout,
    run_subprocess_with_tree_timeout,
)


DEFAULT_CODEX_MODEL = "gpt-5.4"
DEFAULT_CODEX_REASONING_EFFORT = "xhigh"


def _coerce_codex_timeout_seconds(raw_value: str | None, default: int) -> int:
    if raw_value is None or not raw_value.strip():
        return default
    try:
        return max(1, int(raw_value))
    except ValueError:
        return default


def _resolve_codex_timeout_seconds(default: int) -> int:
    return _coerce_codex_timeout_seconds(os.getenv("WORKFLOW_CODEX_TIMEOUT_SECONDS"), default)


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

    def _artifact_path_for(self, packet: TaskPacket) -> str:
        artifact = packet.expected_artifacts[0] if packet.expected_artifacts else "state/artifacts/codex_output.md"
        path = Path(artifact)
        if not path.is_absolute():
            path = Path(packet.working_directory) / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path.resolve().as_posix()

    def _mutation_mode_for(self, packet: TaskPacket) -> MutationMode:
        if packet.mutation_contract is not None:
            return MutationMode(packet.mutation_contract.mutation_mode)
        return MutationMode(packet.env.get("WORKFLOW_MUTATION_MODE", MutationMode.artifact_only))

    def _artifact_content_for(self, packet: TaskPacket) -> str:
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
                responsibilities = [str(item) for item in parsed]
        except json.JSONDecodeError:
            responsibilities = []
        role_label = packet.env.get("WORKFLOW_ROLE_LABEL") or "workflow_role"
        public_role = packet.env.get("WORKFLOW_PUBLIC_ROLE") or "unknown"
        cluster_template_id = packet.env.get("WORKFLOW_CLUSTER_TEMPLATE_ID") or "unknown_cluster"
        cluster_member_id = packet.env.get("WORKFLOW_CLUSTER_MEMBER_ID") or "unknown_member"
        handoff_context = packet.env.get("WORKFLOW_ORCHESTRATION_PLAN_GRAPH") or "{}"
        runtime_brief = packet.env.get("WORKFLOW_RUNTIME_BRIEF") or ""
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
            f"Runtime brief: {runtime_brief}\n"
            f"Handoff context JSON: {handoff_context[:4000]}\n"
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

    def _prompt_for(self, packet: TaskPacket) -> str:
        mutation_mode = self._mutation_mode_for(packet)
        if mutation_mode == MutationMode.patch_apply:
            write_set = packet.env.get("WORKFLOW_MUTATION_WRITE_SET", "[]")
            read_set = packet.env.get("WORKFLOW_MUTATION_READ_SET", "[]")
            test_commands = packet.env.get("WORKFLOW_MUTATION_TEST_COMMANDS", "[]")
            attempt_index = packet.env.get("WORKFLOW_MUTATION_ATTEMPT_INDEX", "0")
            failure_feedback = packet.env.get("WORKFLOW_MUTATION_FAILURE_FEEDBACK", "").strip()
            task_card_ref = packet.env.get("WORKFLOW_MUTATION_TASK_CARD_REF", "").strip()
            task_card_content = packet.env.get("WORKFLOW_MUTATION_TASK_CARD_CONTENT", "").strip()
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
                "You are executing a local workflow repo mutation task inside a controlled repository.\n"
                f"Working directory: {Path(packet.working_directory).resolve().as_posix()}\n"
                f"Attempt index: {attempt_index}\n"
                f"Allowed write_set JSON: {write_set}\n"
                f"Read-only context paths JSON: {read_set}\n"
                f"Explicit test commands JSON: {test_commands}\n"
                f"{task_card_block}"
                f"{failure_block}"
                "Return only one valid unified diff patch that modifies files inside write_set.\n"
                "Do not wrap the patch in code fences. Do not add commentary before or after the diff.\n"
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
        command = [
            self._resolved_executable(),
            "exec",
            "--json",
            "--output-last-message",
            artifact_path,
            "--cd",
            str(Path(packet.working_directory).resolve()),
            "--skip-git-repo-check",
            "--sandbox",
            self.sandbox_mode,
            "--color",
            "never",
        ]
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
        env = build_subprocess_env(packet.env)
        timeout_seconds = self._timeout_seconds_for_packet(packet)
        run_kwargs = {
            "cwd": packet.working_directory,
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
                completed = run_subprocess_with_tree_timeout(command, **run_kwargs)
            else:
                completed = self._runner(command, **run_kwargs)
        except subprocess.TimeoutExpired as exc:
            completed = completed_process_from_timeout(exc, command=command, timeout_seconds=timeout_seconds)
        finished_at = utc_now()
        metadata = {
            "mutation_mode": str(self._mutation_mode_for(packet)),
            "codex_model": self._model_for_packet(packet),
            "codex_reasoning_effort": self._reasoning_effort_for_packet(packet),
            "sandbox_mode": self.sandbox_mode,
            "ephemeral": self.ephemeral,
            "timeout_seconds": timeout_seconds,
        }
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
