from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from pydantic import Field

from packages.contracts.models import ContractModel, PersistedContractModel, new_id


def runtime_utc_now() -> datetime:
    return datetime.now(UTC)


class RuntimeStateRef(PersistedContractModel):
    state_ref_id: str = Field(default_factory=lambda: new_id("state"))
    run_id: str
    runtime_task_id: str
    graph_step: str
    state_payload: dict[str, Any] = Field(default_factory=dict)
    is_terminal: bool = False
    updated_at: datetime = Field(default_factory=runtime_utc_now)


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
