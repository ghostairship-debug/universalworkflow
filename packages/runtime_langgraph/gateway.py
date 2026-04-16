from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class RuntimeStateRef:
    run_id: str
    runtime_task_id: str
    graph_step: str


class RuntimeGateway(ABC):
    @abstractmethod
    def start(self, run_id: str, runtime_task_id: str) -> RuntimeStateRef:
        raise NotImplementedError

    @abstractmethod
    def resume(self, state_ref: RuntimeStateRef) -> RuntimeStateRef:
        raise NotImplementedError


class NullRuntimeGateway(RuntimeGateway):
    def start(self, run_id: str, runtime_task_id: str) -> RuntimeStateRef:
        return RuntimeStateRef(run_id=run_id, runtime_task_id=runtime_task_id, graph_step="started")

    def resume(self, state_ref: RuntimeStateRef) -> RuntimeStateRef:
        return RuntimeStateRef(
            run_id=state_ref.run_id,
            runtime_task_id=state_ref.runtime_task_id,
            graph_step="resumed",
        )
