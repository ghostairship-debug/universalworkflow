from __future__ import annotations

import os
import subprocess
from typing import Callable

from packages.contracts import TaskPacket
from packages.worker_adapters.base import ExecutionResult, WorkerAdapter, resolve_artifact_paths, utc_now
from packages.worker_adapters.subprocess_support import (
    build_subprocess_env,
    completed_process_from_timeout,
    decode_subprocess_stream,
)

CompletedProcessRunner = Callable[..., subprocess.CompletedProcess[str]]


class CliAdapterBase(WorkerAdapter):
    timeout_seconds = 180

    def __init__(self, *, runner: CompletedProcessRunner | None = None):
        self._runner = runner or subprocess.run

    def estimate_cost(self, packet: TaskPacket) -> dict[str, int]:
        return {"timeout_seconds": self.timeout_seconds}

    def build_command(self, packet: TaskPacket) -> list[str]:
        raise NotImplementedError

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
        finished_at = utc_now()
        stdout = decode_subprocess_stream(completed.stdout)
        stderr = decode_subprocess_stream(completed.stderr)
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
        )

    def collect_artifacts(self, packet: TaskPacket) -> list[str]:
        return resolve_artifact_paths(packet)
