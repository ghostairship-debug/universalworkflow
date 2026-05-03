from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from packages.contracts import MutationMode, TaskKind, TaskPacket
from packages.core_domain.compile import build_artifact_content
from packages.core_domain.config import build_effective_config
from packages.core_domain.errors import WorkerAdapterUnavailableError
from packages.worker_adapters.cli_base import CliAdapterBase, CompletedProcessRunner
from packages.worker_adapters.base import ExecutionResult, utc_now
from packages.worker_adapters.subprocess_support import (
    TIMEOUT_EXIT_CODE,
    build_subprocess_env,
    completed_process_watchdog_metadata,
    completed_process_from_timeout,
    decode_subprocess_stream,
    run_subprocess_with_direct_visible_cli,
    run_subprocess_with_tree_timeout,
)


DEFAULT_OPENCODE_MODEL = "minimax/MiniMax-M2.7"
OPENCODE_INLINE_PROMPT_LIMIT = 12000
PROVIDER_STREAM_EVENT_TYPE = "provider_stream_observed"


def _coerce_opencode_timeout_seconds(raw_value: str | None, default: int) -> int:
    if raw_value:
        try:
            return max(1, int(raw_value))
        except ValueError:
            pass
    return default


def _resolve_opencode_timeout_seconds(default: int) -> int:
    return _coerce_opencode_timeout_seconds(
        os.getenv("WORKFLOW_OPENCODE_TIMEOUT_SECONDS") or os.getenv("WORKFLOW_PROVIDER_TIMEOUT_SECONDS"),
        default,
    )


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _safe_path_segment(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return cleaned[:96] or "unknown"


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
        self._uses_custom_runner = runner is not None
        super().__init__(runner=runner)
        effective = build_effective_config()
        self.model = model or str(effective["opencode"]["model"] or os.getenv("WORKFLOW_OPENCODE_MODEL", DEFAULT_OPENCODE_MODEL))
        self.variant = variant or effective["opencode"]["variant"] or os.getenv("WORKFLOW_OPENCODE_VARIANT")
        self.pure = pure
        self.auto_approve = auto_approve
        self.executable = executable or self.executable_name
        self.timeout_seconds = _resolve_opencode_timeout_seconds(self.timeout_seconds)

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
            "opencode executable was not found on PATH",
            {"executable": self.executable},
        )

    def _resolved_command_prefix(self) -> list[str]:
        resolved = self._resolved_executable()
        resolved_path = Path(resolved)
        if os.name == "nt" and resolved_path.suffix.lower() == ".cmd":
            script_path = resolved_path.parent / "node_modules" / "opencode-ai" / "bin" / "opencode"
            node_executable = shutil.which("node")
            if node_executable and script_path.exists():
                return [node_executable, str(script_path)]
        return [resolved]

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
            is_control = bool(event.get("is_control"))
            is_material_progress = bool(event.get("is_material_progress"))
            classification = "control" if is_control else "provider_output"
            observed_at = str(event.get("observed_at") or datetime.now(UTC).isoformat())
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
                "provider_event_type": None,
                "parsed_keys": [],
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
                            "Provider stream observed from OpenCode adapter",
                            json.dumps(payload, ensure_ascii=False, sort_keys=True),
                            "v1",
                            observed_at,
                        ),
                    )
                    connection.commit()
            except sqlite3.Error:
                return

        return _record

    def _direct_visible_cli_enabled(self, packet: TaskPacket) -> bool:
        return _truthy(packet.env.get("WORKFLOW_PROVIDER_DIRECT_VISIBLE_CLI")) or _truthy(
            packet.env.get("WORKFLOW_OPENCODE_DIRECT_VISIBLE_CLI")
        )

    def _direct_visible_session_dir_for(self, packet: TaskPacket) -> Path:
        root = packet.env.get("WORKFLOW_PROVIDER_VISIBLE_SESSION_ROOT")
        if root:
            base = Path(root)
        else:
            base = Path(packet.working_directory) / "state" / "provider_visible_cli_sessions"
        return (
            base
            / _safe_path_segment(packet.run_id or "run")
            / _safe_path_segment(packet.runtime_task_id or "task")
            / self.normalized_name()
        ).resolve()

    def _direct_visible_session_metadata_for(self, packet: TaskPacket) -> dict[str, str | None]:
        task_card_ref = packet.mutation_contract.task_card_ref if packet.mutation_contract is not None else None
        return {
            "run_id": packet.run_id,
            "runtime_task_id": packet.runtime_task_id,
            "task_card_ref": task_card_ref,
            "adapter_name": self.normalized_name(),
            "window_title": f"opencode direct provider {task_card_ref or packet.runtime_task_id}",
        }

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

    def _model_for_packet(self, packet: TaskPacket) -> str:
        return str(packet.env.get("WORKFLOW_OPENCODE_MODEL") or self.model)

    def _variant_for_packet(self, packet: TaskPacket) -> str | None:
        return packet.env.get("WORKFLOW_OPENCODE_VARIANT") or self.variant

    def _timeout_seconds_for_packet(self, packet: TaskPacket) -> int:
        return _coerce_opencode_timeout_seconds(
            packet.env.get("WORKFLOW_OPENCODE_TIMEOUT_SECONDS")
            or packet.env.get("WORKFLOW_PROVIDER_TIMEOUT_SECONDS")
            or os.getenv("WORKFLOW_OPENCODE_TIMEOUT_SECONDS")
            or os.getenv("WORKFLOW_PROVIDER_TIMEOUT_SECONDS"),
            self.timeout_seconds,
        )

    def _idle_timeout_seconds_for_packet(self, packet: TaskPacket, timeout_seconds: int) -> int:
        raw_value = packet.env.get("WORKFLOW_OPENCODE_IDLE_TIMEOUT_SECONDS") or packet.env.get(
            "WORKFLOW_PROVIDER_IDLE_TIMEOUT_SECONDS"
        )
        if raw_value:
            try:
                return max(1, int(raw_value))
            except ValueError:
                pass
        return min(timeout_seconds, 120)

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
            write_set_context = self._env_value_or_file(packet, "WORKFLOW_MUTATION_WRITE_SET_CONTEXT", "[]")
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
                "You are executing a local workflow repo mutation task inside a controlled repository.\n"
                f"Working directory: {Path(packet.working_directory).resolve().as_posix()}\n"
                f"Attempt index: {attempt_index}\n"
                f"Allowed write_set JSON: {write_set}\n"
                f"Embedded write-set context JSON: {write_set_context}\n"
                f"Read-only context paths JSON: {read_set}\n"
                f"Embedded read-set context JSON: {read_set_context}\n"
                f"Explicit test commands JSON: {test_commands}\n"
                f"Provider command policy: {provider_command_policy}.\n"
                "Patch-only mode: do not run shell, PowerShell, cmd, Python, Node, npm, package-manager, "
                "file-inspection, or other tool commands. Do not ask for command output. Use only the "
                "embedded task-card content, write-set context, read-set context, failure feedback, and paths already provided here.\n"
                f"{task_card_block}"
                f"{failure_block}"
                "Return exactly one valid unified diff patch that modifies files inside write_set.\n"
                "Do not wrap the patch in code fences. Do not add commentary before or after the diff.\n"
                "Do not include shell transcripts, markdown, explanations, or non-diff text.\n"
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

    def _extract_output_text(self, stdout: str | bytes | None) -> str:
        stdout = decode_subprocess_stream(stdout)
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

    def _coerce_artifact_output(self, packet: TaskPacket, content: str) -> str | None:
        expected = self._artifact_content_for(packet)
        if content.rstrip("\n") == expected.rstrip("\n"):
            return content
        if content.strip() == expected.strip():
            return expected
        marker_match = re.search(r"<<<WORKFLOW_FILE>>>\n(.*?)<<<END_WORKFLOW_FILE>>>", content, re.DOTALL)
        if marker_match is not None:
            candidate = marker_match.group(1)
            if candidate.rstrip("\n") == expected.rstrip("\n"):
                return candidate
            if candidate.strip() == expected.strip():
                return expected
        return None

    def _prompt_file_for(self, packet: TaskPacket, prompt: str) -> str:
        artifact_path = Path(self._artifact_path_for(packet))
        prompt_path = artifact_path.with_name(f"{artifact_path.stem}_prompt.txt")
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8", newline="\n")
        return prompt_path.resolve().as_posix()

    def _prompt_transport_for(self, packet: TaskPacket) -> str:
        prompt = self._prompt_for(packet)
        return "file_attachment" if len(prompt.encode("utf-8")) > OPENCODE_INLINE_PROMPT_LIMIT else "argv"

    def build_command(self, packet: TaskPacket, *, human_readable_output: bool = False) -> list[str]:
        prompt = self._prompt_for(packet)
        command = [
            *self._resolved_command_prefix(),
            "run",
            "--format",
            "default" if human_readable_output else "json",
            "--dir",
            str(Path(packet.working_directory).resolve()),
        ]
        if self.pure:
            command.append("--pure")
        model = self._model_for_packet(packet)
        variant = self._variant_for_packet(packet)
        if model:
            command.extend(["--model", model])
        if variant:
            command.extend(["--variant", variant])
        if self.auto_approve:
            command.append("--dangerously-skip-permissions")
        if len(prompt.encode("utf-8")) > OPENCODE_INLINE_PROMPT_LIMIT:
            command.append("Execute the workflow mutation instructions in the attached prompt file. Return only the requested unified diff.")
            command.extend(["--file", self._prompt_file_for(packet, prompt)])
        else:
            command.append(prompt)
        return command

    def launch(self, packet: TaskPacket) -> ExecutionResult:
        started_at = utc_now()
        env = build_subprocess_env(packet.env)
        timeout_seconds = self._timeout_seconds_for_packet(packet)
        idle_timeout_seconds = self._idle_timeout_seconds_for_packet(packet, timeout_seconds)
        try:
            direct_visible_cli = self._direct_visible_cli_enabled(packet) and not self._uses_custom_runner
            command = self.build_command(packet, human_readable_output=direct_visible_cli)
            runner = self._runner if self._uses_custom_runner else run_subprocess_with_tree_timeout
            run_kwargs = {
                "cwd": packet.working_directory,
                "env": env,
                "capture_output": True,
                "text": True,
                "check": False,
                "timeout": timeout_seconds,
            }
            if direct_visible_cli:
                run_kwargs["idle_timeout"] = idle_timeout_seconds
                stream_callback = self._provider_stream_callback_for(packet)
                if stream_callback is not None:
                    run_kwargs["on_output"] = stream_callback
                completed = run_subprocess_with_direct_visible_cli(
                    command,
                    provider_name=self.normalized_name(),
                    visible_session_dir=self._direct_visible_session_dir_for(packet),
                    visible_session_metadata=self._direct_visible_session_metadata_for(packet),
                    **run_kwargs,
                )
            else:
                if not self._uses_custom_runner:
                    run_kwargs["idle_timeout"] = idle_timeout_seconds
                completed = runner(
                    command,
                    **run_kwargs,
                )
        except subprocess.TimeoutExpired as exc:
            completed = completed_process_from_timeout(exc, command=command, timeout_seconds=timeout_seconds)
        stdout = decode_subprocess_stream(completed.stdout)
        stderr = decode_subprocess_stream(completed.stderr)
        output_text = self._extract_output_text(stdout)
        return_code = completed.returncode
        failure_class = None
        mutation_mode = self._mutation_mode_for(packet)
        artifact_content = output_text
        if return_code == 0 and output_text and mutation_mode == MutationMode.artifact_only:
            coerced_output = self._coerce_artifact_output(packet, output_text)
            if coerced_output is None:
                failure_class = "artifact_output_mismatch"
                return_code = 1
                message = "opencode artifact-only output did not match expected content"
                stderr = f"{stderr.rstrip()}\n{message}\n" if stderr else f"{message}\n"
            else:
                artifact_content = coerced_output
        if return_code == 0 and output_text:
            self._write_artifact(packet, artifact_content)
        finished_at = utc_now()
        metadata = {
            "mutation_mode": str(mutation_mode),
            "opencode_model": self._model_for_packet(packet),
            "opencode_variant": self._variant_for_packet(packet),
            "timeout_seconds": timeout_seconds,
            "idle_timeout_seconds": idle_timeout_seconds,
            "provider_command_policy": packet.env.get("WORKFLOW_MUTATION_PROVIDER_COMMAND_POLICY"),
            "prompt_transport": self._prompt_transport_for(packet),
            "provider_output_mode": "human_readable" if getattr(completed, "direct_visible_cli_session", None) is not None else "json",
            **completed_process_watchdog_metadata(completed),
        }
        if getattr(completed, "direct_visible_cli_session", None) is not None:
            metadata["direct_visible_cli_session"] = getattr(completed, "direct_visible_cli_session")
            metadata["direct_visible_cli_log_paths"] = getattr(completed, "direct_visible_cli_log_paths", None)
            metadata["direct_visible_provider_cli"] = True
        if return_code == TIMEOUT_EXIT_CODE:
            failure_class = "provider_timeout"
        if failure_class is not None:
            metadata["failure_class"] = failure_class
        return ExecutionResult(
            runtime_task_id=packet.runtime_task_id,
            return_code=return_code,
            stdout=stdout,
            stderr=stderr,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=max(int((finished_at - started_at).total_seconds() * 1000), 0),
            artifact_paths=self.collect_artifacts(packet) if return_code == 0 else [],
            adapter_name=self.normalized_name(),
            metadata=metadata,
        )
