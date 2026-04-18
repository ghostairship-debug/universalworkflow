from __future__ import annotations

from packages.contracts import TaskKind, TaskPacket
from packages.worker_adapters.base import ExecutionResult, WorkerAdapter, resolve_artifact_paths, utc_now


class NoopAdapter(WorkerAdapter):
    adapter_name = "noop"
    route_priority = 10

    def get_capabilities(self) -> list[str]:
        return [str(TaskKind.noop)]

    def estimate_cost(self, packet: TaskPacket) -> dict[str, int]:
        return {"timeout_seconds": 1}

    def launch(self, packet: TaskPacket) -> ExecutionResult:
        started_at = utc_now()
        artifact_paths = self.collect_artifacts(packet)
        finished_at = utc_now()
        return ExecutionResult(
            runtime_task_id=packet.runtime_task_id,
            return_code=0,
            stdout="noop adapter executed",
            stderr="",
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=max(int((finished_at - started_at).total_seconds() * 1000), 0),
            artifact_paths=artifact_paths,
            adapter_name=self.normalized_name(),
        )

    def collect_artifacts(self, packet: TaskPacket) -> list[str]:
        return resolve_artifact_paths(
            packet,
            create_missing=True,
            placeholder=f"adapter: {self.normalized_name()}\nruntime_task_id: {packet.runtime_task_id}\n",
        )
