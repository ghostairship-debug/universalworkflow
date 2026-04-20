from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from packages.contracts import MutationMode, TaskKind, TaskPacket
from packages.core_domain.compile import build_artifact_content
from packages.core_domain.config import build_effective_config
from packages.core_domain.errors import WorkerAdapterUnavailableError
from packages.worker_adapters.cli_base import CliAdapterBase, CompletedProcessRunner
from packages.worker_adapters.base import ExecutionResult, utc_now
from packages.worker_adapters.subprocess_support import build_subprocess_env, completed_process_from_timeout


DEFAULT_OPENCODE_MODEL = "openai/gpt-5.4-mini"


class OpenCodeAdapter(CliAdapterBase):
    adapter_name = "opencode"
    route_priority = 100
    executable_name = "opencode"

    def __init__(
        self,
        *,
        model: str | None = None,
        variant: str | None = None,
        pure: bool = True,
        auto_approve: bool = False,
        runner: CompletedProcessRunner | None = None,
        executable: str | None = None,
    ):
        super().__init__(runner=runner)
        effective = build_effective_config()
        self.model = model or str(effective["opencode"]["model"] or os.getenv("WORKFLOW_OPENCODE_MODEL", DEFAULT_OPENCODE_MODEL))
        self.variant = variant or effective["opencode"]["variant"] or os.getenv("WORKFLOW_OPENCODE_VARIANT")
        self.pure = pure
        self.auto_approve = auto_approve
        self.executable = executable or self.executable_name

    def get_capabilities(self) -> list[str]:
        return [str(TaskKind.shell_exec)]

    def _resolved_executable(self) -> str:
        resolved = shutil.which(self.executable)
        if resolved:
            return resolved
        raise WorkerAdapterUnavailableError(
            self.normalized_name(),
            "opencode executable was not found on PATH",
            {"executable": self.executable},
        )

    def _artifact_path_for(self, packet: TaskPacket) -> str:
        artifact = packet.expected_artifacts[0] if packet.expected_artifacts else "state/artifacts/opencode_output.md"
        path = Path(artifact)
        if not path.is_absolute():
            path = Path(packet.working_directory) / path
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

    def _extract_output_text(self, stdout: str) -> str:
        parts: list[str] = []
        for raw_line in stdout.splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if payload.get("type") != "text":
                continue
            text = payload.get("part", {}).get("text")
            if text:
                parts.append(str(text))
        if parts:
            return "\n".join(parts).rstrip("\n") + "\n"
        fallback = stdout.strip()
        return fallback.rstrip("\n") + ("\n" if fallback else "")

    def _write_artifact(self, packet: TaskPacket, content: str) -> None:
        artifact_path = Path(self._artifact_path_for(packet))
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(content, encoding="utf-8")

    def build_command(self, packet: TaskPacket) -> list[str]:
        resolved_executable = self._resolved_executable()
        command = [
            resolved_executable,
            "run",
            self._prompt_for(packet),
            "--format",
            "json",
            "--dir",
            str(Path(packet.working_directory).resolve()),
        ]
        if self.pure:
            command.append("--pure")
        if self.model:
            command.extend(["--model", self.model])
        if self.variant:
            command.extend(["--variant", self.variant])
        if self.auto_approve:
            command.append("--dangerously-skip-permissions")
        return command

    def launch(self, packet: TaskPacket) -> ExecutionResult:
        started_at = utc_now()
        command = self.build_command(packet)
        env = build_subprocess_env(packet.env)
        try:
            completed = self._runner(
                command,
                cwd=packet.working_directory,
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            completed = completed_process_from_timeout(exc, command=command, timeout_seconds=self.timeout_seconds)
        output_text = self._extract_output_text(completed.stdout)
        if completed.returncode == 0 and output_text:
            self._write_artifact(packet, output_text)
        finished_at = utc_now()
        metadata = {"mutation_mode": str(self._mutation_mode_for(packet))}
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
