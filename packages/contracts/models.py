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


class MutationMode(StrEnum):
    artifact_only = "artifact_only"
    patch_apply = "patch_apply"


class ExecutionLaneType(StrEnum):
    native_deterministic = "native_deterministic"
    repo_change_controlled = "repo_change_controlled"
    standard_agent = "standard_agent"
    durable_incremental = "durable_incremental"
    graph_native_complex = "graph_native_complex"
    sessionful_external_agent = "sessionful_external_agent"


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


class WorkerPoolTransport(StrEnum):
    local = "local"
    http = "http"


class ExecutionTargetKind(StrEnum):
    local = "local"
    external_worker_pool = "external_worker_pool"


class AgentRoleType(StrEnum):
    planner = "planner"
    coder = "coder"
    researcher = "researcher"
    reviewer = "reviewer"
    operator = "operator"


class ControlPlaneIdentity(PersistedContractModel):
    control_plane_id: str
    name: str
    endpoint: str
    status: str = "active"


class AuthorityNodeIdentity(PersistedContractModel):
    node_id: str
    bind_url: str
    status: str = "active"
    role: str = "follower"
    last_heartbeat_at: datetime = Field(default_factory=utc_now)


class SchedulerConsensusTerm(PersistedContractModel):
    term_id: str = Field(default_factory=lambda: new_id("term"))
    term_no: int = Field(default=1, ge=1)
    leader_node_id: str
    quorum_size: int = Field(default=1, ge=1)
    commit_index: int = Field(default=0, ge=0)
    status: str = "active"
    started_at: datetime = Field(default_factory=utc_now)
    last_heartbeat_at: datetime = Field(default_factory=utc_now)
    closed_at: datetime | None = None
    close_reason: str | None = None


class SchedulerVoteRecord(PersistedContractModel):
    vote_id: str = Field(default_factory=lambda: new_id("vote"))
    proposal_id: str
    term_no: int = Field(ge=1)
    voter_node_id: str
    vote: str = "granted"
    reason: str = "peer_accept"


class LeaseFencingToken(ContractModel):
    token: str = Field(default_factory=lambda: new_id("fence"))
    control_plane_id: str
    term_no: int = Field(ge=1)
    commit_index: int = Field(ge=1)
    lease_epoch: int = Field(ge=1)


class MutationContract(ContractModel):
    task_card_ref: str | None = None
    task_card_path: str | None = None
    write_set: list[str] = Field(default_factory=list)
    read_set: list[str] = Field(default_factory=list)
    test_commands: list[str] = Field(default_factory=list)
    max_fix_iterations: int = Field(default=0, ge=0)
    mutation_mode: MutationMode = MutationMode.artifact_only

    @model_validator(mode="after")
    def validate_patch_apply_contract(self) -> "MutationContract":
        if self.mutation_mode == MutationMode.patch_apply and not self.write_set:
            raise ValueError("patch_apply mutation contract requires a non-empty write_set")
        return self


class RepoMutationResult(ContractModel):
    changed_files: list[str] = Field(default_factory=list)
    applied_patch_hash: str | None = None
    out_of_scope_rejections: list[str] = Field(default_factory=list)
    test_attempts: list[dict[str, Any]] = Field(default_factory=list)
    fix_iteration_count: int = Field(default=0, ge=0)
    final_test_status: str = "not_requested"


class SchedulerLeaseProposal(PersistedContractModel):
    proposal_id: str = Field(default_factory=lambda: new_id("proposal"))
    control_plane_id: str
    run_id: str
    runtime_task_id: str
    domain_kind: str = "runtime_task"
    domain_key: str
    requested_lease_seconds: int = Field(default=300, ge=1)
    requested_epoch: int = Field(default=1, ge=1)
    status: str = "pending"


class SchedulerLeaseDecision(PersistedContractModel):
    decision_id: str = Field(default_factory=lambda: new_id("decision"))
    lease_id: str = Field(default_factory=lambda: new_id("schedlease"))
    proposal_id: str
    control_plane_id: str
    run_id: str
    runtime_task_id: str
    domain_kind: str = "runtime_task"
    domain_key: str
    lease_epoch: int = Field(default=1, ge=1)
    decision: str = "granted"
    reason: str = "authority_granted"
    lease_expires_at: datetime = Field(default_factory=utc_now)
    released_at: datetime | None = None
    release_reason: str | None = None


class SchedulerPeerHeartbeat(PersistedContractModel):
    heartbeat_id: str = Field(default_factory=lambda: new_id("peerhb"))
    control_plane_id: str
    status: str = "active"
    lease_count: int = Field(default=0, ge=0)
    observed_at: datetime = Field(default_factory=utc_now)


class SchedulerCommittedLease(PersistedContractModel):
    committed_lease_id: str = Field(default_factory=lambda: new_id("committed"))
    lease_id: str
    proposal_id: str
    decision_id: str | None = None
    control_plane_id: str
    run_id: str
    runtime_task_id: str
    domain_kind: str = "runtime_task"
    domain_key: str
    term_no: int = Field(default=1, ge=1)
    commit_index: int = Field(default=1, ge=1)
    lease_epoch: int = Field(default=1, ge=1)
    fencing_token: str = Field(default_factory=lambda: new_id("fence"))
    status: str = "active"
    lease_expires_at: datetime = Field(default_factory=utc_now)
    released_at: datetime | None = None
    release_reason: str | None = None


class ControlPlaneHandoffEnvelope(PersistedContractModel):
    envelope_id: str = Field(default_factory=lambda: new_id("handoffenv"))
    run_id: str
    runtime_task_id: str
    from_control_plane_id: str
    to_control_plane_id: str
    committed_lease_id: str
    term_no: int = Field(ge=1)
    commit_index: int = Field(ge=1)
    snapshot_payload: dict[str, Any] = Field(default_factory=dict)
    review_state: dict[str, Any] = Field(default_factory=dict)
    durable_refs: dict[str, Any] = Field(default_factory=dict)
    replay_excerpt: dict[str, Any] = Field(default_factory=dict)


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


class CapabilityDescriptor(ContractModel):
    capability_id: str
    provider_kind: str
    transport: str
    auth_mode: str = "none"
    scopes: list[str] = Field(default_factory=list)
    allowed_task_kinds: list[TaskKind] = Field(default_factory=list)
    cost_class: str = "local_low"
    latency_class: str = "local_low"
    side_effect_level: str = "read_only"
    evidence_schema: dict[str, Any] = Field(default_factory=dict)
    display_name: str | None = None
    source_type: CapabilitySourceType | None = None
    profile_id: str | None = None
    adapter_name: str | None = None
    enabled: bool = True
    default_selected: bool = False


class CapabilityHealth(ContractModel):
    descriptor: CapabilityDescriptor
    status: str = "ready"
    reason: str | None = None
    tool_count: int = Field(default=0, ge=0)
    failure_classes: list[str] = Field(default_factory=list)
    recent_call_summary: dict[str, Any] = Field(default_factory=dict)
    checked_at: datetime = Field(default_factory=utc_now)


class WorkerPoolProfile(PersistedContractModel):
    worker_pool_id: str
    name: str
    description: str
    enabled: bool = True
    transport: WorkerPoolTransport = WorkerPoolTransport.local
    adapter_name: str = "shell"
    dispatch_mode: str = "loopback"
    base_url: str | None = None
    auth_mode: str = "none"
    shared_secret_env: str | None = None
    callback_base_url: str | None = None
    heartbeat_interval_seconds: int = Field(default=30, ge=1)
    lease_ttl_seconds: int = Field(default=300, ge=1)


class ExecutionTargetRef(ContractModel):
    target_kind: ExecutionTargetKind = ExecutionTargetKind.local
    worker_pool_id: str | None = None
    adapter_name: str | None = None
    dispatch_mode: str | None = None
    worker_name: str | None = None
    worker_id: str | None = None
    dispatched_at: str | None = None
    dispatch_id: str | None = None
    base_url: str | None = None
    callback_base_url: str | None = None
    auth_mode: str | None = None
    last_callback_at: str | None = None
    control_plane_id: str | None = None
    committed_lease_id: str | None = None
    fencing_token: str | None = None
    term_no: int | None = None
    commit_index: int | None = None


class LeaseRenewalRecord(ContractModel):
    renewal_id: str = Field(default_factory=lambda: new_id("renewal"))
    run_id: str
    runtime_task_id: str
    worker_pool_id: str
    lease_id: str
    status: str
    renewed_at: datetime = Field(default_factory=utc_now)
    lease_expires_at: datetime
    callback_id: str | None = None
    heartbeat_at: datetime | None = None
    source: str = "control_plane"
    control_plane_id: str | None = None
    committed_lease_id: str | None = None
    fencing_token: str | None = None
    term_no: int | None = None
    commit_index: int | None = None


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
    external_session_url: str | None = None
    session_export_ref: str | None = None
    memory_item_id: str | None = None
    simulation_record_id: str | None = None


class ReviewPolicy(StrEnum):
    auto_only = "auto_only"
    optional = "optional"
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
    mutation_contract: MutationContract | None = None


class ArtifactRef(ContractModel):
    path: str
    sha256: str
    mtime: float
    size_bytes: int


class CheckResult(ContractModel):
    name: str
    status: str
    detail: str | None = None


class ExternalSessionRef(ContractModel):
    external_session_id: str | None = None
    external_session_url: str | None = None
    session_export_ref: str | None = None


class ResultRawRef(ContractModel):
    storage_kind: str = "evidence.raw_execution"
    runtime_task_id: str
    payload_path: str = "raw_execution"
    artifact_paths: list[str] = Field(default_factory=list)


class ResultVerification(ContractModel):
    return_code: int
    checks: list[CheckResult] = Field(default_factory=list)
    known_gaps: list[str] = Field(default_factory=list)


class ResultProvenance(ContractModel):
    adapter_name: str
    started_at: datetime
    finished_at: datetime
    duration_ms: int = Field(default=0, ge=0)


class ResultEnvelope(ContractModel):
    summary: str
    raw_ref: ResultRawRef
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    verification: ResultVerification
    provenance: ResultProvenance
    mutations: dict[str, Any] | None = None
    usage: dict[str, Any] | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    external_trace_id: str | None = None
    session_ref: ExternalSessionRef | None = None


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
    result_envelope: ResultEnvelope | None = None

    @model_validator(mode="after")
    def sync_result_envelope(self) -> "Evidence":
        payload = self.raw_execution.get("result_envelope")
        if self.result_envelope is None and isinstance(payload, dict):
            self.result_envelope = ResultEnvelope.model_validate(payload)
        elif self.result_envelope is not None:
            self.raw_execution["result_envelope"] = self.result_envelope.model_dump(mode="json")
        return self


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


class RoleAssignment(ContractModel):
    role: AgentRoleType
    preset_id: str
    preferred_adapter: str | None = None
    fallback_adapter: str | None = None
    review_policy: ReviewPolicy | None = None


class OrchestrationStep(ContractModel):
    step_id: str = Field(default_factory=lambda: new_id("orchestration_step"))
    role: AgentRoleType
    title: str
    run_id: str | None = None
    preset_id: str
    preferred_adapter: str | None = None
    fallback_adapter: str | None = None
    barrier_id: str | None = None
    sequence_no: int = Field(default=1, ge=1)
    status: str = "pending"


class OrchestrationBarrier(ContractModel):
    barrier_id: str = Field(default_factory=lambda: new_id("orchestration_barrier"))
    label: str
    role_ids: list[AgentRoleType] = Field(default_factory=list)
    status: str = "pending"
    member_count: int = Field(default=0, ge=0)


class OrchestrationPlan(PersistedContractModel):
    orchestration_id: str = Field(default_factory=lambda: new_id("orchestration"))
    run_id: str | None = None
    preset_id: str
    review_policy: ReviewPolicy
    roles: list[RoleAssignment] = Field(default_factory=list)
    steps: list[OrchestrationStep] = Field(default_factory=list)
    barriers: list[OrchestrationBarrier] = Field(default_factory=list)
    execution_mode: str = "planner_parallel_reviewer"


class OrchestrationGraphNode(ContractModel):
    node_id: str = Field(default_factory=lambda: new_id("graphnode"))
    role: AgentRoleType
    goal: str
    required_capabilities: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    review_gate: str = "none"
    side_effect_level: str = "read_only"
    fallback_path: list[str] = Field(default_factory=list)
    preset_id: str | None = None
    preferred_adapter: str | None = None


class OrchestrationPlanGraph(PersistedContractModel):
    plan_graph_id: str = Field(default_factory=lambda: new_id("plangraph"))
    run_id: str | None = None
    preset_id: str
    goal: str
    execution_mode: str = "single_path"
    summary: str | None = None
    risk_summary: list[str] = Field(default_factory=list)
    nodes: list[OrchestrationGraphNode] = Field(default_factory=list)
    recommended_preset_id: str | None = None


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
