from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from packages.contracts import MutationMode, TaskPacket
from packages.worker_adapters.base import ExecutionResult, utc_now
from packages.worker_adapters.opencode_adapter import OpenCodeAdapter
from packages.worker_adapters.subprocess_support import build_subprocess_env, completed_process_from_timeout


class OpenCodeSessionAdapter(OpenCodeAdapter):
    adapter_name = "opencode_session"
    route_priority = 95

    def __init__(
        self,
        *,
        share: bool = True,
        export_session: bool = True,
        **kwargs: Any,
    ):
        kwargs.setdefault("pure", False)
        super().__init__(**kwargs)
        self.share = share
        self.export_session = export_session

    def build_command(self, packet: TaskPacket) -> list[str]:
        command = super().build_command(packet)
        if self.share and "--share" not in command:
            command.append("--share")
        attach_url = packet.env.get("WORKFLOW_EXTERNAL_SESSION_ATTACH_URL")
        if attach_url:
            command.extend(["--attach", attach_url])
        session_id = packet.env.get("WORKFLOW_EXTERNAL_SESSION_ID")
        continue_last = packet.env.get("WORKFLOW_EXTERNAL_SESSION_CONTINUE") in {"1", "true", "True"}
        if session_id:
            command.extend(["--session", session_id])
        elif continue_last:
            command.append("--continue")
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
        session_metadata = self._extract_session_metadata(completed.stdout, packet)
        artifact_paths = self.collect_artifacts(packet)
        export_ref = self._export_session_artifact(packet, session_metadata, env)
        if export_ref is not None:
            session_metadata["session_export_ref"] = export_ref
            artifact_paths.append(export_ref)
        finished_at = utc_now()
        metadata = {
            "mutation_mode": str(self._mutation_mode_for(packet)),
            "session_mode": "opencode_share",
            **session_metadata,
        }
        return ExecutionResult(
            runtime_task_id=packet.runtime_task_id,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=max(int((finished_at - started_at).total_seconds() * 1000), 0),
            artifact_paths=artifact_paths,
            adapter_name=self.normalized_name(),
            metadata=metadata,
        )

    def _extract_session_metadata(self, stdout: str, packet: TaskPacket) -> dict[str, str]:
        session_id = packet.env.get("WORKFLOW_EXTERNAL_SESSION_ID")
        session_url = packet.env.get("WORKFLOW_EXTERNAL_SESSION_URL")
        external_trace_id = None
        for raw_line in stdout.splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            found = self._scan_json_payload(payload)
            session_id = found.get("external_session_id") or session_id
            session_url = found.get("external_session_url") or session_url
            external_trace_id = found.get("external_trace_id") or external_trace_id
        result: dict[str, str] = {}
        if session_id:
            result["external_session_id"] = session_id
        if session_url:
            result["external_session_url"] = session_url
        if external_trace_id:
            result["external_trace_id"] = external_trace_id
        return result

    def _scan_json_payload(self, payload: Any) -> dict[str, str]:
        found: dict[str, str] = {}

        def _visit(value: Any) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    normalized = str(key).strip()
                    lowered = normalized.lower()
                    if lowered in {"session_id", "sessionid"} and isinstance(item, str):
                        found.setdefault("external_session_id", item)
                    elif lowered in {"share_url", "shareurl", "session_url", "sessionurl"} and isinstance(item, str):
                        found.setdefault("external_session_url", item)
                    elif lowered in {"trace_id", "traceid"} and isinstance(item, str):
                        found.setdefault("external_trace_id", item)
                    elif lowered == "url" and isinstance(item, str) and item.startswith("http"):
                        found.setdefault("external_session_url", item)
                    else:
                        _visit(item)
            elif isinstance(value, list):
                for item in value:
                    _visit(item)

        _visit(payload)
        return found

    def _export_session_artifact(
        self,
        packet: TaskPacket,
        session_metadata: dict[str, str],
        env: dict[str, str],
    ) -> str | None:
        if not self.export_session:
            return None
        session_id = session_metadata.get("external_session_id")
        if not session_id:
            return None
        export_path = Path(packet.working_directory) / "state" / "sessions" / f"{packet.runtime_task_id}_{session_id}.json"
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_command = [self._resolved_executable(), "export", session_id]
        try:
            completed = self._runner(
                export_command,
                cwd=packet.working_directory,
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            completed = completed_process_from_timeout(exc, command=export_command, timeout_seconds=self.timeout_seconds)
        if completed.returncode != 0 or not completed.stdout.strip():
            return None
        export_path.write_text(completed.stdout, encoding="utf-8")
        return export_path.resolve().as_posix()
