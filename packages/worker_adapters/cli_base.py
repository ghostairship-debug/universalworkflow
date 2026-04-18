from __future__ import annotations

import os
import subprocess
from typing import Callable

from packages.contracts import TaskPacket
from packages.worker_adapters.base import ExecutionResult, WorkerAdapter, resolve_artifact_paths, utc_now

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
        env = os.environ.copy()
        env.update(packet.env)
        completed = self._runner(
            self.build_command(packet),
            cwd=packet.working_directory,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        finished_at = utc_now()
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
        )

    def collect_artifacts(self, packet: TaskPacket) -> list[str]:
        return resolve_artifact_paths(packet)
