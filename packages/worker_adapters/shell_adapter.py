from __future__ import annotations

import os
import subprocess

from packages.contracts import TaskKind, TaskPacket
from packages.worker_adapters.base import ExecutionResult, WorkerAdapter, resolve_artifact_paths, utc_now


class ShellAdapter(WorkerAdapter):
    adapter_name = "shell"
    route_priority = 50

    def get_capabilities(self) -> list[str]:
        return [str(TaskKind.shell_exec)]

    def estimate_cost(self, packet: TaskPacket) -> dict[str, int]:
        return {"timeout_seconds": 120}

    def launch(self, packet: TaskPacket) -> ExecutionResult:
        started_at = utc_now()
        env = os.environ.copy()
        env.update(packet.env)
        completed = subprocess.run(
            packet.command,
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
