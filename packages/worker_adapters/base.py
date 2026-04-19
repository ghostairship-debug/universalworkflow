from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contracts import TaskPacket


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class ExecutionResult:
    runtime_task_id: str
    return_code: int
    stdout: str
    stderr: str
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    artifact_paths: list[str]
    adapter_name: str
    metadata: dict[str, Any] = field(default_factory=dict)


def resolve_artifact_paths(packet: TaskPacket, *, create_missing: bool = False, placeholder: str | None = None) -> list[str]:
    working_directory = Path(packet.working_directory)
    results: list[str] = []
    for artifact in packet.expected_artifacts:
        path = Path(artifact)
        if not path.is_absolute():
            path = working_directory / path
        if create_missing:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text(placeholder or "", encoding="utf-8")
        if path.exists():
            results.append(path.resolve().as_posix())
    return results


class WorkerAdapter(ABC):
    adapter_name = ""
    route_priority = 100

    def normalized_name(self) -> str:
        return self.adapter_name or self.__class__.__name__.replace("Adapter", "").lower()

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def estimate_cost(self, packet: TaskPacket) -> dict[str, int]:
        raise NotImplementedError

    @abstractmethod
    def launch(self, packet: TaskPacket) -> ExecutionResult:
        raise NotImplementedError

    @abstractmethod
    def collect_artifacts(self, packet: TaskPacket) -> list[str]:
        raise NotImplementedError
