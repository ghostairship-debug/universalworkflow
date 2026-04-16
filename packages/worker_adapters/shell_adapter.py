from __future__ import annotations

import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from packages.contracts import TaskKind, TaskPacket


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


class WorkerAdapter(ABC):
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


class ShellAdapter(WorkerAdapter):
    def get_capabilities(self) -> list[str]:
        return ["shell_exec", "noop"]

    def estimate_cost(self, packet: TaskPacket) -> dict[str, int]:
        return {"timeout_seconds": 120 if packet.task_kind == TaskKind.shell_exec else 1}

    def launch(self, packet: TaskPacket) -> ExecutionResult:
        started_at = utc_now()
        if packet.task_kind == TaskKind.noop:
            finished_at = utc_now()
            return ExecutionResult(
                runtime_task_id=packet.runtime_task_id,
                return_code=0,
                stdout="noop",
                stderr="",
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=max(int((finished_at - started_at).total_seconds() * 1000), 0),
                artifact_paths=self.collect_artifacts(packet),
            )

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
        )

    def collect_artifacts(self, packet: TaskPacket) -> list[str]:
        working_directory = Path(packet.working_directory)
        results: list[str] = []
        for artifact in packet.expected_artifacts:
            path = Path(artifact)
            if not path.is_absolute():
                path = working_directory / path
            if path.exists():
                results.append(path.resolve().as_posix())
        return results
