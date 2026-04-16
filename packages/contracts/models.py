from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="allow", use_enum_values=True)


class PersistedContractModel(ContractModel):
    schema_version: str = "v1"
    created_at: datetime = Field(default_factory=utc_now)


class RunStatus(StrEnum):
    pending = "pending"
    prepared = "prepared"
    running = "running"
    awaiting_review = "awaiting_review"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


RUN_STATUS_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.pending: frozenset({RunStatus.prepared, RunStatus.cancelled}),
    RunStatus.prepared: frozenset({RunStatus.prepared, RunStatus.running, RunStatus.cancelled}),
    RunStatus.running: frozenset({RunStatus.awaiting_review, RunStatus.completed, RunStatus.failed}),
    RunStatus.awaiting_review: frozenset({RunStatus.completed, RunStatus.failed, RunStatus.cancelled}),
    RunStatus.completed: frozenset({RunStatus.completed}),
    RunStatus.failed: frozenset({RunStatus.failed}),
    RunStatus.cancelled: frozenset({RunStatus.cancelled}),
}


def allowed_run_status_transitions(current_status: RunStatus | str) -> tuple[RunStatus, ...]:
    normalized = RunStatus(current_status)
    return tuple(sorted(RUN_STATUS_TRANSITIONS[normalized], key=str))


def can_transition_run_status(current_status: RunStatus | str, next_status: RunStatus | str) -> bool:
    normalized_current = RunStatus(current_status)
    normalized_next = RunStatus(next_status)
    return normalized_next in RUN_STATUS_TRANSITIONS[normalized_current]


class PhaseStatus(StrEnum):
    pending = "pending"
    active = "active"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TaskStatus(StrEnum):
    pending = "pending"
    ready = "ready"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TaskKind(StrEnum):
    shell_exec = "shell_exec"
    noop = "noop"


class ReviewPolicy(StrEnum):
    auto_only = "auto_only"
    human_required = "human_required"


class ReviewDecision(StrEnum):
    pass_ = "pass"
    fail = "fail"


class ReviewerType(StrEnum):
    auto = "auto"
    human = "human"


class Run(PersistedContractModel):
    run_id: str = Field(default_factory=lambda: new_id("run"))
    goal: str
    preset_id: str
    status: RunStatus = RunStatus.pending
    updated_at: datetime = Field(default_factory=utc_now)


class Phase(PersistedContractModel):
    phase_id: str = Field(default_factory=lambda: new_id("phase"))
    run_id: str
    name: str
    order_index: int
    status: PhaseStatus = PhaseStatus.pending


class TaskCard(PersistedContractModel):
    task_card_id: str = Field(default_factory=lambda: new_id("card"))
    run_id: str
    title: str
    description: str
    acceptance_criteria: list[str] = Field(default_factory=list)


class RuntimeTask(PersistedContractModel):
    runtime_task_id: str = Field(default_factory=lambda: new_id("task"))
    run_id: str
    phase_id: str
    task_card_id: str
    task_kind: TaskKind
    status: TaskStatus = TaskStatus.pending
    summary: str


class TaskPacket(PersistedContractModel):
    task_packet_id: str = Field(default_factory=lambda: new_id("packet"))
    runtime_task_id: str
    run_id: str
    task_kind: TaskKind
    command: list[str] = Field(default_factory=list)
    working_directory: str
    env: dict[str, str] = Field(default_factory=dict)
    expected_artifacts: list[str] = Field(default_factory=list)


class ArtifactRef(ContractModel):
    path: str
    sha256: str
    mtime: float
    size_bytes: int


class CheckResult(ContractModel):
    name: str
    status: str
    detail: str | None = None


class Evidence(PersistedContractModel):
    evidence_id: str = Field(default_factory=lambda: new_id("evidence"))
    run_id: str
    runtime_task_id: str
    summary: str
    changed_files: list[str] = Field(default_factory=list)
    checks: list[CheckResult] = Field(default_factory=list)
    known_gaps: list[str] = Field(default_factory=list)
    artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    return_code: int
    raw_execution: dict[str, Any] = Field(default_factory=dict)


class ReviewVerdict(PersistedContractModel):
    verdict_id: str = Field(default_factory=lambda: new_id("verdict"))
    run_id: str
    evidence_id: str
    decision: ReviewDecision
    rationale: str
    reviewer_type: ReviewerType = ReviewerType.auto
    reviewed_at: datetime = Field(default_factory=utc_now)


class BudgetPolicy(ContractModel):
    max_retries: int = Field(ge=0)
    timeout_seconds: int = Field(gt=0)


class PresetDefinition(PersistedContractModel):
    preset_id: str
    name: str
    description: str
    allowed_task_kinds: list[TaskKind]
    default_review_policy: ReviewPolicy
    default_budget_policy: BudgetPolicy
    requires_manual_approval: bool = False


class HandoffLite(PersistedContractModel):
    handoff_id: str = Field(default_factory=lambda: new_id("handoff"))
    run_id: str
    from_phase_id: str
    to_phase_id: str
    summary: str
    blocking_risks: list[str] = Field(default_factory=list)
