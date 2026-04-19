from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class ExecutionLaneType(StrEnum):
    native_deterministic = "native_deterministic"
    standard_agent = "standard_agent"
    durable_incremental = "durable_incremental"
    graph_native_complex = "graph_native_complex"


class CapabilitySourceType(StrEnum):
    built_in = "built_in"
    mcp_stdio = "mcp_stdio"
    mcp_http = "mcp_http"


class TrustTier(StrEnum):
    t0_builtin_local = "t0_builtin_local"
    t1_local_stdio_mcp = "t1_local_stdio_mcp"
    t2_internal_managed_http_mcp = "t2_internal_managed_http_mcp"
    t3_third_party_remote_http_mcp = "t3_third_party_remote_http_mcp"


class MCPTransport(StrEnum):
    stdio = "stdio"
    http = "http"


class CapabilityRoute(ContractModel):
    capability: str
    adapter_name: str
    adapter_class: str


class MCPServerProfile(PersistedContractModel):
    profile_id: str
    name: str
    description: str
    transport: MCPTransport
    startup_command: list[str] = Field(default_factory=list)
    auth_mode: str = "env"
    allowed_tools: list[str] = Field(default_factory=list)
    max_tools: int = Field(default=5, ge=1)
    max_schema_bytes: int = Field(default=16384, ge=0)
    startup_timeout_ms: int = Field(default=4000, ge=0)
    call_timeout_ms: int = Field(default=10000, ge=0)
    retry_policy: str = "none"
    manifest_ttl_seconds: int = Field(default=300, ge=0)
    enabled: bool = True


class ToolProjectionEntry(ContractModel):
    capability_id: str
    tool_name: str
    description: str
    source_type: CapabilitySourceType
    trust_tier: TrustTier
    read_only: bool = True
    review_requirement: str = "none"
    timeout_budget_ms: int | None = None
    schema_hash: str
    enabled_for_preset: str | None = None
    redaction_rules: list[str] = Field(default_factory=list)
    server_profile_id: str | None = None
    adapter_name: str | None = None


class ToolProjectionManifest(PersistedContractModel):
    projection_id: str = Field(default_factory=lambda: new_id("projection"))
    run_id: str | None = None
    preset_id: str
    task_kind: TaskKind
    review_policy: ReviewPolicy
    lane_type: ExecutionLaneType
    domain_pack_id: str | None = None
    tools: list[ToolProjectionEntry] = Field(default_factory=list)
    max_schema_bytes: int = Field(default=0, ge=0)
    trust_tiers: list[TrustTier] = Field(default_factory=list)


class TraceContext(ContractModel):
    run_id: str
    event_id: str | None = None
    runtime_task_id: str | None = None
    state_ref_id: str | None = None
    attempt_id: str | None = None
    evidence_id: str | None = None
    verdict_id: str | None = None
    claim_id: str | None = None
    lease_id: str | None = None
    snapshot_id: str | None = None
    projection_id: str | None = None
    tool_call_id: str | None = None
    external_trace_id: str | None = None
    thread_id: str | None = None
    checkpoint_id: str | None = None
    assistant_id: str | None = None
    external_session_id: str | None = None
    memory_item_id: str | None = None
    simulation_record_id: str | None = None


class ReviewPolicy(StrEnum):
    auto_only = "auto_only"
    recommended = "recommended"
    human_required = "human_required"
    mandatory = "mandatory"


class SimulationTriggerPolicy(StrEnum):
    disabled = "disabled"
    failure_only = "failure_only"
    always = "always"


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


class BudgetLedger(PersistedContractModel):
    ledger_id: str = Field(default_factory=lambda: new_id("ledger"))
    run_id: str
    preset_id: str
    max_retries: int = Field(ge=0)
    timeout_seconds: int = Field(gt=0)
    compile_count: int = Field(default=0, ge=0)
    recompile_count: int = Field(default=0, ge=0)
    execution_count: int = Field(default=0, ge=0)
    total_runtime_ms: int = Field(default=0, ge=0)
    last_return_code: int | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class PresetDefinition(PersistedContractModel):
    preset_id: str
    name: str
    description: str
    allowed_task_kinds: list[TaskKind]
    default_review_policy: ReviewPolicy
    default_budget_policy: BudgetPolicy
    requires_manual_approval: bool = False


class DomainPackMatchRule(ContractModel):
    preset_ids: list[str] = Field(default_factory=list)
    task_kinds: list[TaskKind] = Field(default_factory=list)


class DomainPackCapabilityExposure(ContractModel):
    preferred_adapter_name: str | None = None
    capability_tags: list[str] = Field(default_factory=list)


class DomainPackCompileProjection(ContractModel):
    artifact_label: str
    goal_prefix: str | None = None
    artifact_context_lines: list[str] = Field(default_factory=list)


class DomainPackRuntimeProjection(ContractModel):
    operator_label: str | None = None
    evidence_expectations: list[str] = Field(default_factory=list)


class DomainPackDefinition(PersistedContractModel):
    domain_pack_id: str
    name: str
    description: str
    enabled: bool = True
    match: DomainPackMatchRule = Field(default_factory=DomainPackMatchRule)
    capability_exposure: DomainPackCapabilityExposure = Field(default_factory=DomainPackCapabilityExposure)
    compile_projection: DomainPackCompileProjection
    runtime_projection: DomainPackRuntimeProjection = Field(default_factory=DomainPackRuntimeProjection)

    @model_validator(mode="before")
    @classmethod
    def _upgrade_flat_shape(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        if "match" not in payload:
            payload["match"] = {
                "preset_ids": payload.pop("preset_ids", []),
                "task_kinds": payload.pop("task_kinds", []),
            }
        if "capability_exposure" not in payload:
            payload["capability_exposure"] = {
                "preferred_adapter_name": payload.pop("preferred_adapter_name", None),
                "capability_tags": payload.pop("capability_tags", []),
            }
        if "compile_projection" not in payload:
            payload["compile_projection"] = {
                "artifact_label": payload.pop("artifact_label"),
                "goal_prefix": payload.pop("goal_prefix", None),
                "artifact_context_lines": payload.pop("artifact_context_lines", []),
            }
        if "runtime_projection" not in payload:
            payload["runtime_projection"] = {
                "operator_label": payload.pop("operator_label", None),
                "evidence_expectations": payload.pop("evidence_expectations", []),
            }
        return payload

    @property
    def preset_ids(self) -> list[str]:
        return self.match.preset_ids

    @property
    def task_kinds(self) -> list[TaskKind]:
        return self.match.task_kinds

    @property
    def artifact_label(self) -> str:
        return self.compile_projection.artifact_label

    @property
    def goal_prefix(self) -> str | None:
        return self.compile_projection.goal_prefix

    @property
    def preferred_adapter_name(self) -> str | None:
        return self.capability_exposure.preferred_adapter_name

    @property
    def capability_tags(self) -> list[str]:
        return self.capability_exposure.capability_tags

    @property
    def operator_label(self) -> str | None:
        return self.runtime_projection.operator_label

    @property
    def evidence_expectations(self) -> list[str]:
        return self.runtime_projection.evidence_expectations


class DomainPackResolution(ContractModel):
    domain_pack_id: str
    name: str
    description: str
    matched_preset_id: str
    matched_task_kind: TaskKind
    capability_exposure: DomainPackCapabilityExposure = Field(default_factory=DomainPackCapabilityExposure)
    compile_projection: DomainPackCompileProjection
    runtime_projection: DomainPackRuntimeProjection = Field(default_factory=DomainPackRuntimeProjection)


class MemoryNamespace(PersistedContractModel):
    namespace_id: str
    name: str
    kind: str
    scope: str
    retention_policy: str
    retrieval_policy: str


class MemoryCandidate(ContractModel):
    candidate_id: str = Field(default_factory=lambda: new_id("memcand"))
    run_id: str
    namespace_id: str
    title: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)


class MemoryItem(PersistedContractModel):
    memory_item_id: str = Field(default_factory=lambda: new_id("memory"))
    run_id: str
    namespace_id: str
    source_candidate_id: str
    title: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    materialized_from: str = "run_memory_candidate"


class MemoryRetrievalPreview(ContractModel):
    run_id: str | None = None
    preset_id: str | None = None
    namespace_ids: list[str] = Field(default_factory=list)
    selected_memory_item_ids: list[str] = Field(default_factory=list)
    source_run_ids: list[str] = Field(default_factory=list)
    item_count: int = Field(ge=0)
    brief_lines: list[str] = Field(default_factory=list)
    items: list[MemoryItem] = Field(default_factory=list)


class SimulationPolicyDefinition(PersistedContractModel):
    policy_id: str
    name: str
    description: str
    preset_ids: list[str] = Field(default_factory=list)
    trigger_policy: SimulationTriggerPolicy = SimulationTriggerPolicy.disabled
    simulator_name: str = "local_consistency_check"
    check_ids: list[str] = Field(default_factory=list)


class SimulationReportStatus(StrEnum):
    skipped = "skipped"
    passed = "passed"
    failed = "failed"


class SimulationRecordSource(StrEnum):
    manual_request = "manual_request"
    lifecycle_awaiting_review = "lifecycle_awaiting_review"
    lifecycle_terminal = "lifecycle_terminal"
    lifecycle_cancelled = "lifecycle_cancelled"


class SimulationReport(ContractModel):
    run_id: str
    preset_id: str
    policy_id: str
    trigger_policy: SimulationTriggerPolicy
    simulator_name: str
    triggered: bool
    status: SimulationReportStatus
    reason: str
    summary: str
    finding_codes: list[str] = Field(default_factory=list)
    recommended_action: str | None = None
    check_results: list[CheckResult] = Field(default_factory=list)


class SimulationRecord(PersistedContractModel):
    record_id: str = Field(default_factory=lambda: new_id("simrec"))
    run_id: str
    policy_id: str
    status: SimulationReportStatus
    triggered: bool
    summary: str
    recorded_from: SimulationRecordSource = SimulationRecordSource.manual_request
    report: SimulationReport


class HandoffLite(PersistedContractModel):
    handoff_id: str = Field(default_factory=lambda: new_id("handoff"))
    run_id: str
    from_phase_id: str
    to_phase_id: str
    summary: str
    blocking_risks: list[str] = Field(default_factory=list)
