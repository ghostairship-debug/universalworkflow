from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from packages.contracts import MutationMode, TaskKind, TaskPacket
from packages.core_domain.config import build_effective_config
from packages.core_domain.errors import WorkerAdapterUnavailableError
from packages.worker_adapters.base import ExecutionResult, resolve_artifact_paths, utc_now
from packages.worker_adapters.cli_base import CliAdapterBase, CompletedProcessRunner
from packages.worker_adapters.subprocess_support import (
    build_subprocess_env,
    completed_process_from_timeout,
    decode_subprocess_stream,
)


class ArtifactCliAdapter(CliAdapterBase):
    adapter_name = ""
    route_priority = 120
    executable_name = ""
    executable_env_key = ""
    command_template_env_key = ""
    output_label = "external artifact"

    def __init__(
        self,
        *,
        runner: CompletedProcessRunner | None = None,
        executable: str | None = None,
    ):
        self._uses_custom_runner = runner is not None
        super().__init__(runner=runner)
        self.executable = executable or self._configured_executable()

    def get_capabilities(self) -> list[str]:
        return [str(TaskKind.shell_exec)]

    def supports_mutation_mode(self, mode: MutationMode | str) -> bool:
        return MutationMode(mode) == MutationMode.artifact_only

    def _configured_executable(self) -> str:
        if self.executable_env_key:
            configured = os.getenv(self.executable_env_key)
            if configured:
                return configured
        return self.executable_name

    def _resolved_executable(self) -> str:
        resolved = shutil.which(self.executable)
        if resolved:
            return resolved
        candidate = Path(self.executable)
        if candidate.exists():
            return candidate.resolve().as_posix()
        raise WorkerAdapterUnavailableError(
            self.normalized_name(),
            f"{self.executable} executable was not found on PATH",
            {"executable": self.executable},
        )

    def _artifact_path_for(self, packet: TaskPacket) -> Path:
        artifact = packet.expected_artifacts[0] if packet.expected_artifacts else f"state/artifacts/{self.adapter_name}_output.md"
        path = Path(artifact)
        if not path.is_absolute():
            path = Path(packet.working_directory) / path
        return path.resolve()

    def _prompt_for(self, packet: TaskPacket) -> str:
        input_paths = packet.env.get("WORKFLOW_MULTIMODAL_INPUT_PATHS") or packet.env.get("WORKFLOW_REFERENCED_ARTIFACT_PATHS")
        return (
            "You are running inside the local Universal Agentic Workflow control plane.\n"
            f"Role: {self.output_label}.\n"
            "Return a concise, structured artifact in Chinese unless source material requires otherwise.\n"
            f"Working directory: {Path(packet.working_directory).resolve().as_posix()}\n"
            f"Goal: {packet.env.get('WORKFLOW_RUN_GOAL', '')}\n"
            f"Runtime brief: {packet.env.get('WORKFLOW_RUNTIME_BRIEF', '')}\n"
            f"Referenced paths: {input_paths or 'none'}\n"
            "Do not mutate repository files. Produce evidence, boundaries, risks, and handoff notes only.\n"
        )

    def _template_command(self, packet: TaskPacket, artifact_path: Path, prompt: str) -> list[str] | None:
        if not self.command_template_env_key:
            return None
        template = packet.env.get(self.command_template_env_key) or os.getenv(self.command_template_env_key)
        if not template:
            return None
        prompt_path = artifact_path.with_suffix(".prompt.txt")
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")
        formatted = template.format(
            executable=self._resolved_executable(),
            prompt=prompt,
            prompt_path=prompt_path.as_posix(),
            artifact_path=artifact_path.as_posix(),
            working_directory=Path(packet.working_directory).resolve().as_posix(),
        )
        return shlex.split(formatted, posix=os.name != "nt")

    def _default_command(self, packet: TaskPacket, artifact_path: Path, prompt: str) -> list[str]:
        raise NotImplementedError

    def build_command(self, packet: TaskPacket) -> list[str]:
        artifact_path = self._artifact_path_for(packet)
        prompt = self._prompt_for(packet)
        return self._template_command(packet, artifact_path, prompt) or self._default_command(packet, artifact_path, prompt)

    def _write_artifact(
        self,
        packet: TaskPacket,
        content: str | bytes | None,
        completed: subprocess.CompletedProcess[str],
    ) -> None:
        artifact_path = self._artifact_path_for(packet)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        content_text = decode_subprocess_stream(content)
        stderr_text = decode_subprocess_stream(completed.stderr)
        if not content_text.strip():
            content_text = json.dumps(
                {
                    "adapter": self.normalized_name(),
                    "status": "empty_output",
                    "return_code": completed.returncode,
                    "stderr_preview": stderr_text[:2000],
                },
                ensure_ascii=False,
                indent=2,
            )
        artifact_path.write_text(content_text.rstrip("\n") + "\n", encoding="utf-8")

    def launch(self, packet: TaskPacket) -> ExecutionResult:
        started_at = utc_now()
        command = self.build_command(packet)
        env = build_subprocess_env(packet.env)
        try:
            run_kwargs = {
                "cwd": packet.working_directory,
                "env": env,
                "capture_output": True,
                "text": True,
                "check": False,
                "timeout": self.timeout_seconds,
            }
            if not self._uses_custom_runner:
                run_kwargs.update({"encoding": "utf-8", "errors": "replace"})
            completed = self._runner(command, **run_kwargs)
        except subprocess.TimeoutExpired as exc:
            completed = completed_process_from_timeout(exc, command=command, timeout_seconds=self.timeout_seconds)
        stdout = decode_subprocess_stream(completed.stdout)
        stderr = decode_subprocess_stream(completed.stderr)
        if completed.returncode == 0:
            self._write_artifact(packet, stdout, completed)
        finished_at = utc_now()
        return ExecutionResult(
            runtime_task_id=packet.runtime_task_id,
            return_code=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=max(int((finished_at - started_at).total_seconds() * 1000), 0),
            artifact_paths=self.collect_artifacts(packet),
            adapter_name=self.normalized_name(),
            metadata={
                "mutation_mode": str(MutationMode.artifact_only),
                "output_label": self.output_label,
                "command_template_env_key": self.command_template_env_key or None,
            },
        )

    def collect_artifacts(self, packet: TaskPacket) -> list[str]:
        return resolve_artifact_paths(packet)


class ClaudeArchitectAdapter(ArtifactCliAdapter):
    adapter_name = "claude_architect"
    route_priority = 94
    executable_name = "claude"
    executable_env_key = "WORKFLOW_CLAUDE_CLI"
    command_template_env_key = "WORKFLOW_CLAUDE_COMMAND_TEMPLATE"
    output_label = "one-shot architecture gate"

    def _call_limit_error(self, packet: TaskPacket) -> ExecutionResult | None:
        effective = build_effective_config()
        enabled = bool(effective["claude_architect"]["enabled"])
        if not enabled and packet.env.get("WORKFLOW_CLAUDE_ARCHITECT_ENABLED") not in {"1", "true", "True"}:
            raise WorkerAdapterUnavailableError(
                self.normalized_name(),
                "Claude architect gate is disabled",
                {"env": "WORKFLOW_CLAUDE_ARCHITECT_ENABLED"},
            )
        max_calls = int(effective["claude_architect"]["max_calls_per_session"])
        call_count = int(packet.env.get("WORKFLOW_CLAUDE_ARCHITECT_CALL_COUNT") or 0)
        if call_count < max_calls:
            return None
        now = utc_now()
        return ExecutionResult(
            runtime_task_id=packet.runtime_task_id,
            return_code=1,
            stdout="",
            stderr=f"claude architect quota guard blocked call {call_count + 1}; max_calls_per_session={max_calls}",
            started_at=now,
            finished_at=now,
            duration_ms=0,
            artifact_paths=[],
            adapter_name=self.normalized_name(),
            metadata={
                "quota_guarded": True,
                "claude_architect_call_count": call_count,
                "max_calls_per_session": max_calls,
            },
        )

    def _default_command(self, packet: TaskPacket, artifact_path: Path, prompt: str) -> list[str]:
        return [self._resolved_executable(), "-p", prompt, "--output-format", "text"]

    def launch(self, packet: TaskPacket) -> ExecutionResult:
        guarded = self._call_limit_error(packet)
        if guarded is not None:
            return guarded
        result = super().launch(packet)
        result.metadata.update({"quota_guarded": True})
        return result


class MMXMultimodalAdapter(ArtifactCliAdapter):
    adapter_name = "mmx_multimodal"
    route_priority = 96
    executable_name = "mmx"
    executable_env_key = "WORKFLOW_MMX_CLI"
    command_template_env_key = "WORKFLOW_MMX_COMMAND_TEMPLATE"
    output_label = "primary multimodal evidence extractor"

    def _default_command(self, packet: TaskPacket, artifact_path: Path, prompt: str) -> list[str]:
        model = packet.env.get("WORKFLOW_MMX_MODEL") or os.getenv("WORKFLOW_MMX_MODEL") or os.getenv("MINIMAX_MODEL") or "MiniMax-M2.7"
        base_url = packet.env.get("MINIMAX_BASE_URL") or os.getenv("MINIMAX_BASE_URL") or "https://api.minimaxi.com/v1"
        prompt_path = artifact_path.with_suffix(".prompt.txt")
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")
        return [
            sys.executable,
            "-m",
            "packages.worker_adapters.minimax_openai_cli",
            "--model",
            str(model),
            "--base-url",
            str(base_url).rstrip("/"),
            "--prompt-path",
            prompt_path.as_posix(),
        ]


class VertexMultimodalAdapter(ArtifactCliAdapter):
    adapter_name = "vertex_multimodal"
    route_priority = 97
    executable_name = "gcloud"
    executable_env_key = "WORKFLOW_VERTEX_CLI"
    command_template_env_key = "WORKFLOW_VERTEX_COMMAND_TEMPLATE"
    output_label = "fallback complex multimodal evidence extractor"

    def _default_command(self, packet: TaskPacket, artifact_path: Path, prompt: str) -> list[str]:
        project = (
            packet.env.get("WORKFLOW_VERTEX_PROJECT")
            or os.getenv("WORKFLOW_VERTEX_PROJECT")
            or os.getenv("GOOGLE_CLOUD_PROJECT")
            or os.getenv("GCLOUD_PROJECT")
        )
        if not project:
            raise WorkerAdapterUnavailableError(
                self.normalized_name(),
                "Vertex adapter requires GOOGLE_CLOUD_PROJECT, GCLOUD_PROJECT, or WORKFLOW_VERTEX_PROJECT",
                {"env": "GOOGLE_CLOUD_PROJECT"},
            )
        location = (
            packet.env.get("WORKFLOW_VERTEX_LOCATION")
            or os.getenv("WORKFLOW_VERTEX_LOCATION")
            or os.getenv("GOOGLE_VERTEX_LOCATION")
            or os.getenv("GOOGLE_CLOUD_LOCATION")
            or os.getenv("VERTEX_LOCATION")
            or "global"
        )
        model = packet.env.get("WORKFLOW_VERTEX_MODEL") or os.getenv("WORKFLOW_VERTEX_MODEL") or "gemini-2.5-flash"
        prompt_path = artifact_path.with_suffix(".prompt.txt")
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")
        return [
            sys.executable,
            "-m",
            "packages.worker_adapters.vertex_genai_cli",
            "--project",
            str(project),
            "--location",
            str(location),
            "--model",
            str(model),
            "--prompt-path",
            prompt_path.as_posix(),
        ]
