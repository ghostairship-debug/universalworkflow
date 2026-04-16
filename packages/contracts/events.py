from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import ConfigDict, Field

from packages.contracts.models import ContractModel, PersistedContractModel, new_id


class RunEventType(StrEnum):
    run_created = "run_created"
    preset_selected = "preset_selected"
    phase_created = "phase_created"
    runtime_task_created = "runtime_task_created"
    runtime_task_started = "runtime_task_started"
    runtime_task_completed = "runtime_task_completed"
    evidence_submitted = "evidence_submitted"
    review_submitted = "review_submitted"
    run_completed = "run_completed"
    run_failed = "run_failed"


class EventPayloadModel(ContractModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class RunCreatedPayload(EventPayloadModel):
    goal: str
    preset_id: str


class PresetSelectedPayload(EventPayloadModel):
    preset_id: str
    preset_name: str


class PhaseCreatedPayload(EventPayloadModel):
    phase_id: str
    phase_name: str


class RuntimeTaskCreatedPayload(EventPayloadModel):
    runtime_task_id: str
    task_kind: str
    summary: str


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


EVENT_PAYLOAD_MODELS = {
    RunEventType.run_created: RunCreatedPayload,
    RunEventType.preset_selected: PresetSelectedPayload,
    RunEventType.phase_created: PhaseCreatedPayload,
    RunEventType.runtime_task_created: RuntimeTaskCreatedPayload,
    RunEventType.runtime_task_started: RuntimeTaskStartedPayload,
    RunEventType.runtime_task_completed: RuntimeTaskCompletedPayload,
    RunEventType.evidence_submitted: EvidenceSubmittedPayload,
    RunEventType.review_submitted: ReviewSubmittedPayload,
    RunEventType.run_completed: RunCompletedPayload,
    RunEventType.run_failed: RunFailedPayload,
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
