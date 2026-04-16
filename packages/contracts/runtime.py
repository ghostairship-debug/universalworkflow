from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from packages.contracts.models import ContractModel, PersistedContractModel, new_id


def runtime_utc_now() -> datetime:
    return datetime.now(UTC)


class RuntimeGraphStep(StrEnum):
    compiled = "compiled"
    resuming = "resuming"
    awaiting_review = "awaiting_review"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


TERMINAL_RUNTIME_GRAPH_STEPS = frozenset(
    {
        RuntimeGraphStep.completed,
        RuntimeGraphStep.failed,
        RuntimeGraphStep.cancelled,
    }
)


NON_TERMINAL_RUNTIME_GRAPH_STEPS = frozenset(
    {
        RuntimeGraphStep.compiled,
        RuntimeGraphStep.resuming,
        RuntimeGraphStep.awaiting_review,
    }
)


def is_terminal_runtime_graph_step(graph_step: RuntimeGraphStep | str) -> bool:
    return RuntimeGraphStep(graph_step) in TERMINAL_RUNTIME_GRAPH_STEPS


class RuntimeStateRef(PersistedContractModel):
    state_ref_id: str = Field(default_factory=lambda: new_id("state"))
    run_id: str
    runtime_task_id: str
    graph_step: RuntimeGraphStep
    state_payload: dict[str, Any] = Field(default_factory=dict)
    is_terminal: bool = False
    updated_at: datetime = Field(default_factory=runtime_utc_now)

    @model_validator(mode="after")
    def validate_graph_step_terminality(self) -> "RuntimeStateRef":
        expected_terminal = is_terminal_runtime_graph_step(self.graph_step)
        if self.is_terminal != expected_terminal:
            raise ValueError(
                f"runtime graph step `{self.graph_step}` requires is_terminal={expected_terminal}, "
                f"got {self.is_terminal}"
            )
        return self


class PresetSuggestion(ContractModel):
    preset_id: str
    score: int
    reason: str


class RuntimeGateway(ABC):
    @abstractmethod
    def start(self, run_id: str, runtime_task_id: str) -> RuntimeStateRef:
        raise NotImplementedError

    @abstractmethod
    def resume(self, state_ref: RuntimeStateRef) -> RuntimeStateRef:
        raise NotImplementedError
