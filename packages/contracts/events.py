from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import ConfigDict, Field

from packages.contracts.models import ContractModel, PersistedContractModel, TraceContext, new_id


class RunEventType(StrEnum):
    run_created = "run_created"
    preset_selected = "preset_selected"
    domain_pack_selected = "domain_pack_selected"
    phase_created = "phase_created"
    handoff_created = "handoff_created"
    runtime_task_created = "runtime_task_created"
    run_compiled = "run_compiled"
    runtime_resumed = "runtime_resumed"
    runtime_task_started = "runtime_task_started"
    runtime_task_completed = "runtime_task_completed"
    evidence_submitted = "evidence_submitted"
    review_requested = "review_requested"
    review_submitted = "review_submitted"
    run_completed = "run_completed"
    run_failed = "run_failed"
    run_cancelled = "run_cancelled"
    claim_acquired = "claim_acquired"
    claim_released = "claim_released"
    worker_lease_acquired = "worker_lease_acquired"
    worker_lease_released = "worker_lease_released"
    runtime_attempt_created = "runtime_attempt_created"
    runtime_attempt_superseded = "runtime_attempt_superseded"
    runtime_attempt_closed = "runtime_attempt_closed"
    run_snapshot_created = "run_snapshot_created"
    memory_item_materialized = "memory_item_materialized"
    simulation_recorded = "simulation_recorded"
    repair_applied = "repair_applied"


class EventPayloadModel(ContractModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)
    trace_context: TraceContext | None = None


class RunCreatedPayload(EventPayloadModel):
    goal: str
    preset_id: str


class PresetSelectedPayload(EventPayloadModel):
    preset_id: str
    preset_name: str


class DomainPackSelectedPayload(EventPayloadModel):
    domain_pack_id: str
    domain_pack_name: str
    matched_preset_id: str
    task_kind: str
    adapter_name: str
    operator_label: str | None = None
    capability_tags: list[str] = Field(default_factory=list)
    evidence_expectations: list[str] = Field(default_factory=list)


class PhaseCreatedPayload(EventPayloadModel):
    phase_id: str
    phase_name: str


class HandoffCreatedPayload(EventPayloadModel):
    handoff_id: str
    from_phase_id: str
    to_phase_id: str


class RuntimeTaskCreatedPayload(EventPayloadModel):
    runtime_task_id: str
    task_kind: str
    summary: str


class RunCompiledPayload(EventPayloadModel):
    run_id: str
    status: str
    runtime_task_id: str


class RuntimeResumedPayload(EventPayloadModel):
    run_id: str
    runtime_task_id: str
    graph_step: str


class RuntimeTaskStartedPayload(EventPayloadModel):
    runtime_task_id: str
    task_kind: str


class RuntimeTaskCompletedPayload(EventPayloadModel):
    runtime_task_id: str
    return_code: int
    duration_ms: int


class EvidenceSubmittedPayload(EventPayloadModel):
    evidence_id: str
    summary: str


class ReviewRequestedPayload(EventPayloadModel):
    run_id: str
    policy: str
    status: str


class ReviewSubmittedPayload(EventPayloadModel):
    verdict_id: str
    decision: str


class RunCompletedPayload(EventPayloadModel):
    run_id: str
    status: str


class RunFailedPayload(EventPayloadModel):
    run_id: str
    status: str
    reason: str


class RunCancelledPayload(EventPayloadModel):
    run_id: str
    status: str
    reason: str


class ClaimAcquiredPayload(EventPayloadModel):
    run_id: str
    runtime_task_id: str
    claim_id: str
    owner: str
    lease_expires_at: str


class ClaimReleasedPayload(EventPayloadModel):
    run_id: str
    runtime_task_id: str
    claim_id: str
    status: str
    reason: str


class WorkerLeaseAcquiredPayload(EventPayloadModel):
    run_id: str
    runtime_task_id: str
    lease_id: str
    worker_name: str
    adapter_name: str
    heartbeat_at: str
    lease_expires_at: str


class WorkerLeaseReleasedPayload(EventPayloadModel):
    run_id: str
    runtime_task_id: str
    lease_id: str
    status: str
    reason: str


class RuntimeAttemptCreatedPayload(EventPayloadModel):
    run_id: str
    runtime_task_id: str
    attempt_id: str
    sequence_no: int
    trigger: str
    status: str


class RuntimeAttemptSupersededPayload(EventPayloadModel):
    run_id: str
    runtime_task_id: str
    attempt_id: str
    superseded_by_attempt_id: str
    reason: str


class RuntimeAttemptClosedPayload(EventPayloadModel):
    run_id: str
    runtime_task_id: str
    attempt_id: str
    status: str
    reason: str


class RunSnapshotCreatedPayload(EventPayloadModel):
    run_id: str
    snapshot_id: str
    stage: str
    run_status: str
    runtime_task_id: str | None = None


class MemoryItemMaterializedPayload(EventPayloadModel):
    run_id: str
    memory_item_id: str
    namespace_id: str
    source_candidate_id: str


class SimulationRecordedPayload(EventPayloadModel):
    run_id: str
    record_id: str
    policy_id: str
    status: str
    triggered: bool
    recorded_from: str


class RepairAppliedPayload(EventPayloadModel):
    run_id: str
    action: str
    problem: str
    repaired_runtime_task_ids: list[str]


EVENT_PAYLOAD_MODELS = {
    RunEventType.run_created: RunCreatedPayload,
    RunEventType.preset_selected: PresetSelectedPayload,
    RunEventType.domain_pack_selected: DomainPackSelectedPayload,
    RunEventType.phase_created: PhaseCreatedPayload,
    RunEventType.handoff_created: HandoffCreatedPayload,
    RunEventType.runtime_task_created: RuntimeTaskCreatedPayload,
    RunEventType.run_compiled: RunCompiledPayload,
    RunEventType.runtime_resumed: RuntimeResumedPayload,
    RunEventType.runtime_task_started: RuntimeTaskStartedPayload,
    RunEventType.runtime_task_completed: RuntimeTaskCompletedPayload,
    RunEventType.evidence_submitted: EvidenceSubmittedPayload,
    RunEventType.review_requested: ReviewRequestedPayload,
    RunEventType.review_submitted: ReviewSubmittedPayload,
    RunEventType.run_completed: RunCompletedPayload,
    RunEventType.run_failed: RunFailedPayload,
    RunEventType.run_cancelled: RunCancelledPayload,
    RunEventType.claim_acquired: ClaimAcquiredPayload,
    RunEventType.claim_released: ClaimReleasedPayload,
    RunEventType.worker_lease_acquired: WorkerLeaseAcquiredPayload,
    RunEventType.worker_lease_released: WorkerLeaseReleasedPayload,
    RunEventType.runtime_attempt_created: RuntimeAttemptCreatedPayload,
    RunEventType.runtime_attempt_superseded: RuntimeAttemptSupersededPayload,
    RunEventType.runtime_attempt_closed: RuntimeAttemptClosedPayload,
    RunEventType.run_snapshot_created: RunSnapshotCreatedPayload,
    RunEventType.memory_item_materialized: MemoryItemMaterializedPayload,
    RunEventType.simulation_recorded: SimulationRecordedPayload,
    RunEventType.repair_applied: RepairAppliedPayload,
}


class RunEvent(PersistedContractModel):
    event_id: str = Field(default_factory=lambda: new_id("event"))
    run_id: str
    event_type: RunEventType
    object_type: str
    object_id: str
    summary: str
    payload_json: dict[str, Any]


def validate_event_payload(event_type: RunEventType | str, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = RunEventType(event_type)
    model = EVENT_PAYLOAD_MODELS[normalized]
    return model.model_validate(payload).model_dump(mode="json")
