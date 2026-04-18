from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from packages.contracts.models import ContractModel, PersistedContractModel, RunStatus, new_id


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


class RuntimeClaimStatus(StrEnum):
    active = "active"
    released = "released"
    expired = "expired"


class WorkerLeaseStatus(StrEnum):
    active = "active"
    released = "released"
    expired = "expired"


class RuntimeAttemptTrigger(StrEnum):
    compile = "compile"
    recompile = "recompile"
    resume = "resume"
    repair = "repair"


class RuntimeAttemptStatus(StrEnum):
    current = "current"
    superseded = "superseded"
    interrupted = "interrupted"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class RunSnapshotStage(StrEnum):
    compiled = "compiled"
    awaiting_review = "awaiting_review"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    repaired = "repaired"


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


class RuntimeClaim(PersistedContractModel):
    claim_id: str = Field(default_factory=lambda: new_id("claim"))
    run_id: str
    runtime_task_id: str
    owner: str = "local_orchestrator"
    status: RuntimeClaimStatus = RuntimeClaimStatus.active
    lease_expires_at: datetime = Field(default_factory=runtime_utc_now)
    released_at: datetime | None = None
    release_reason: str | None = None

    @model_validator(mode="after")
    def validate_claim_lifecycle(self) -> "RuntimeClaim":
        if self.status == RuntimeClaimStatus.active:
            if self.released_at is not None or self.release_reason is not None:
                raise ValueError("active runtime claim cannot have released_at or release_reason")
            return self
        if self.released_at is None:
            raise ValueError("non-active runtime claim must have released_at")
        if not self.release_reason:
            raise ValueError("non-active runtime claim must have release_reason")
        return self


class WorkerLease(PersistedContractModel):
    lease_id: str = Field(default_factory=lambda: new_id("lease"))
    run_id: str
    runtime_task_id: str
    worker_name: str = "local_worker"
    adapter_name: str
    status: WorkerLeaseStatus = WorkerLeaseStatus.active
    heartbeat_at: datetime = Field(default_factory=runtime_utc_now)
    lease_expires_at: datetime = Field(default_factory=runtime_utc_now)
    released_at: datetime | None = None
    release_reason: str | None = None

    @model_validator(mode="after")
    def validate_worker_lease_lifecycle(self) -> "WorkerLease":
        if self.status == WorkerLeaseStatus.active:
            if self.released_at is not None or self.release_reason is not None:
                raise ValueError("active worker lease cannot have released_at or release_reason")
            return self
        if self.released_at is None:
            raise ValueError("non-active worker lease must have released_at")
        if not self.release_reason:
            raise ValueError("non-active worker lease must have release_reason")
        return self


class RuntimeAttempt(PersistedContractModel):
    attempt_id: str = Field(default_factory=lambda: new_id("attempt"))
    run_id: str
    runtime_task_id: str
    sequence_no: int = Field(gt=0)
    trigger: RuntimeAttemptTrigger
    status: RuntimeAttemptStatus = RuntimeAttemptStatus.current
    superseded_by_attempt_id: str | None = None
    superseded_at: datetime | None = None
    supersede_reason: str | None = None
    closed_at: datetime | None = None
    close_reason: str | None = None

    @model_validator(mode="after")
    def validate_attempt_lifecycle(self) -> "RuntimeAttempt":
        if self.status == RuntimeAttemptStatus.current:
            if any(
                value is not None
                for value in (
                    self.superseded_by_attempt_id,
                    self.superseded_at,
                    self.supersede_reason,
                    self.closed_at,
                    self.close_reason,
                )
            ):
                raise ValueError("current runtime attempt cannot have supersede or close metadata")
            return self

        if self.status == RuntimeAttemptStatus.superseded:
            if not self.superseded_by_attempt_id or self.superseded_at is None or not self.supersede_reason:
                raise ValueError("superseded runtime attempt must record successor attempt and supersede metadata")
            if self.closed_at is not None or self.close_reason is not None:
                raise ValueError("superseded runtime attempt cannot have close metadata")
            return self

        if self.superseded_by_attempt_id is not None or self.superseded_at is not None or self.supersede_reason is not None:
            raise ValueError("closed runtime attempt cannot have supersede metadata")
        if self.closed_at is None or not self.close_reason:
            raise ValueError("closed runtime attempt must have closed_at and close_reason")
        return self


class RunSnapshot(PersistedContractModel):
    snapshot_id: str = Field(default_factory=lambda: new_id("snapshot"))
    run_id: str
    stage: RunSnapshotStage
    run_status: RunStatus
    runtime_task_id: str | None = None
    summary: str
    snapshot_payload: dict[str, Any] = Field(default_factory=dict)


class PresetSuggestion(ContractModel):
    preset_id: str
    score: int
    reason: str


class RuntimeGateway(ABC):
    @abstractmethod
    def describe(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def start(self, run_id: str, runtime_task_id: str) -> RuntimeStateRef:
        raise NotImplementedError

    @abstractmethod
    def resume(self, state_ref: RuntimeStateRef) -> RuntimeStateRef:
        raise NotImplementedError
