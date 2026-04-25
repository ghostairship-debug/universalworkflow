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


class ExecutionProfileDefinition(ContractModel):
    adapter_name: str | None = None
    agent_model: str | None = None
    codex_model: str | None = None
    codex_reasoning_effort: str | None = None
    opencode_model: str | None = None
    opencode_variant: str | None = None
    runtime_gateway_provider: str | None = None
    runtime_gateway_model: str | None = None
    runtime_reasoning_effort: str | None = None
    worker_pool_id: str | None = None


class ExecutionScopeContext(ContractModel):
    preset_id: str | None = None
    agent_profile_id: str | None = None
    cluster_template_id: str | None = None
    cluster_member_id: str | None = None
    public_role: AgentRoleType | None = None
    role_label: str | None = None


class ResolvedExecutionProfile(ContractModel):
    adapter_name: str | None = None
    execution_lane: ExecutionLaneType | None = None
    selected_model: str | None = None
    selected_model_kind: str | None = None
    model_variant: str | None = None
    model_selection_source: str | None = None
    model_selection_reason: str | None = None
    dogfood_strong_model_enabled: bool = False
    dogfood_execution_backend: str | None = None
    adaptive_llm_routing_enabled: bool = False
    adaptive_route_tier: str | None = None
    adaptive_route_reason: str | None = None
    langchain_agent_provider: str | None = None
    langchain_agent_model: str | None = None
    langchain_agent_degraded_reason: str | None = None
    role_responsibilities: list[str] = Field(default_factory=list)
    claude_architect_call_count: int = 0
    multimodal_evidence_refs: list[str] = Field(default_factory=list)
    agent_model: str | None = None
    codex_model: str | None = None
    codex_reasoning_effort: str | None = None
    opencode_model: str | None = None
    opencode_variant: str | None = None
    runtime_gateway_provider: str | None = None
    runtime_gateway_model: str | None = None
    runtime_reasoning_effort: str | None = None
    worker_pool_id: str | None = None
    scope_context: ExecutionScopeContext | None = None
    source_map: dict[str, dict[str, Any]] = Field(default_factory=dict)
    applied_scopes: list[dict[str, Any]] = Field(default_factory=list)
    compatibility_fallback: str | None = None


class IntentSessionStatus(StrEnum):
    open = "open"
    clarifying = "clarifying"
    planning = "planning"
    ready_to_launch = "ready_to_launch"
    launched = "launched"
    closed = "closed"


class PlanDraftStatus(StrEnum):
    draft = "draft"
    needs_clarification = "needs_clarification"
    ready = "ready"
    approved = "approved"
    launched = "launched"


class ProfileVisibility(StrEnum):
    public = "public"
    internal = "internal"
    ephemeral = "ephemeral"


class GeneratedProfileSource(StrEnum):
    template_clone = "template_clone"
    interaction_generated = "interaction_generated"
    cluster_generated = "cluster_generated"


class ClusterExecutionMode(StrEnum):
    sequential = "sequential"
    parallel = "parallel"
    mixed = "mixed"


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
    startup_env: dict[str, str] = Field(default_factory=dict)
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
    canonical_tool_id: str | None = None
    raw_tool_name: str | None = None
    display_name: str | None = None
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

    @model_validator(mode="after")
    def fill_canonical_identity(self) -> "ToolProjectionEntry":
        raw_tool_name = self.raw_tool_name or self.tool_name
        self.raw_tool_name = raw_tool_name
        self.display_name = self.display_name or raw_tool_name.replace("_", " ")
        if self.canonical_tool_id:
            return self
        source_type = str(self.source_type)
        if source_type in {CapabilitySourceType.mcp_stdio, CapabilitySourceType.mcp_http} and self.server_profile_id:
            self.canonical_tool_id = f"mcp:{self.server_profile_id}:{raw_tool_name}"
        elif source_type == CapabilitySourceType.built_in:
            self.canonical_tool_id = f"builtin:{self.capability_id}:{raw_tool_name}"
        else:
            self.canonical_tool_id = f"{source_type}:{self.capability_id}:{raw_tool_name}"
        return self


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
    readiness_state: str = "configured"
    tool_count: int = Field(default=0, ge=0)
    failure_classes: list[str] = Field(default_factory=list)
    recent_call_summary: dict[str, Any] = Field(default_factory=dict)
    runtime_ledger_summary: dict[str, Any] = Field(default_factory=dict)
    probe_evidence: dict[str, Any] = Field(default_factory=dict)
    provider_route: str | None = None
    fallback_route: str | None = None
    runtime_probe_status: str = "not_probed"
    runtime_probe_reason: str | None = None
    runtime_probe_detail: dict[str, Any] = Field(default_factory=dict)
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


class CapabilityInvocationEnvelope(ContractModel):
    envelope_id: str = Field(default_factory=lambda: new_id("capenv"))
    run_id: str | None = None
    runtime_task_id: str | None = None
    preset_id: str | None = None
    task_kind: TaskKind | str
    lane_type: ExecutionLaneType | None = None
    review_policy: ReviewPolicy | str | None = None
    authority_mode: str | None = None
    descriptor: CapabilityDescriptor
    worker_pool_id: str | None = None
    tool_projection_id: str | None = None
    mutation_mode: MutationMode | None = None


class CapabilityExecutionReceipt(ContractModel):
    receipt_id: str = Field(default_factory=lambda: new_id("capreceipt"))
    envelope: CapabilityInvocationEnvelope
    status: str = "completed"
    adapter_name: str | None = None
    return_code: int
    started_at: datetime
    finished_at: datetime
    duration_ms: int = Field(default=0, ge=0)
    artifact_paths: list[str] = Field(default_factory=list)
    failure_class: str | None = None
    execution_target: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    callback_base_url: str | None = None
    auth_mode: str | None = None
    last_callback_at: str | None = None
    control_plane_id: str | None = None
    committed_lease_id: str | None = None
    fencing_token: str | None = None
    term_no: int | None = None
    authority_term_no: int | None = None
    commit_index: int | None = None
    decision_index: int | None = None


class CapabilityInvocationRecord(PersistedContractModel):
    invocation_id: str = Field(default_factory=lambda: new_id("capinv"))
    receipt_id: str | None = None
    capability_id: str
    provider_kind: str
    run_id: str | None = None
    runtime_task_id: str | None = None
    status: str
    return_code: int | None = None
    adapter_name: str | None = None
    duration_ms: int = Field(default=0, ge=0)
    failure_class: str | None = None
    payload_json: dict[str, Any] = Field(default_factory=dict)


class CapabilityProbeResult(PersistedContractModel):
    probe_id: str = Field(default_factory=lambda: new_id("capprobe"))
    provider: str
    adapter_name: str | None = None
    status: str
    live_probe: bool = False
    auth_source: str | None = None
    latency_ms: int = Field(default=0, ge=0)
    failure_class: str | None = None
    evidence_path: str | None = None
    fallback_route: str | None = None
    return_code: int | None = None
    stdout_preview: str | None = None
    stderr_preview: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClusterRouteDecision(PersistedContractModel):
    decision_id: str = Field(default_factory=lambda: new_id("clroute"))
    goal: str
    preset_id: str | None = None
    selected_template_ids: list[str] = Field(default_factory=list)
    preferred_template_ids: list[str] = Field(default_factory=list)
    source: str = "cluster_router"
    dynamic_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class OperatorActionReceipt(PersistedContractModel):
    receipt_id: str = Field(default_factory=lambda: new_id("opreceipt"))
    action_type: str
    workspace_root: str
    risk_level: str = "high"
    operator_id: str = "local_operator"
    requested_write_set: list[str] = Field(default_factory=list)
    scope_hash: str | None = None
    scope_payload: dict[str, Any] = Field(default_factory=dict)
    nonce: str = Field(default_factory=lambda: new_id("nonce"))
    status: str = "issued"
    expires_at: datetime
    consumed_at: datetime | None = None
    audit_timestamp: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


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
    authority_term_no: int | None = None
    commit_index: int | None = None
    decision_index: int | None = None


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
    execution_profile: ExecutionProfileDefinition | None = None


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


class ClarificationPrompt(ContractModel):
    prompt_id: str = Field(default_factory=lambda: new_id("clarify"))
    question: str
    answer: str | None = None
    required: bool = True
    source: str = "system"
    status: str = "pending"

    @model_validator(mode="after")
    def sync_status_from_answer(self) -> "ClarificationPrompt":
        if self.answer:
            self.status = "answered"
        elif self.required and self.status == "not_needed":
            self.status = "pending"
        return self


class ClarificationState(ContractModel):
    status: str = "not_needed"
    prompts: list[ClarificationPrompt] = Field(default_factory=list)
    required_count: int = Field(default=0, ge=0)
    answered_count: int = Field(default=0, ge=0)
    blocking: bool = False

    @model_validator(mode="after")
    def sync_counts(self) -> "ClarificationState":
        self.required_count = sum(1 for prompt in self.prompts if prompt.required)
        self.answered_count = sum(1 for prompt in self.prompts if prompt.answer)
        self.blocking = self.required_count > self.answered_count
        if self.prompts and self.answered_count < self.required_count:
            self.status = "awaiting_answers"
        elif self.prompts:
            self.status = "resolved"
        return self


class IntentPacket(ContractModel):
    goal: str
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    preferred_preset_id: str | None = None
    preferred_cluster_template_ids: list[str] = Field(default_factory=list)
    referenced_artifact_paths: list[str] = Field(default_factory=list)
    followup_context: list[str] = Field(default_factory=list)


class IntentSession(PersistedContractModel):
    session_id: str = Field(default_factory=lambda: new_id("intent_session"))
    status: IntentSessionStatus = IntentSessionStatus.open
    intent_packet: IntentPacket
    clarification_state: ClarificationState = Field(default_factory=ClarificationState)
    latest_plan_draft_id: str | None = None
    active_run_id: str | None = None


class PlanDraft(PersistedContractModel):
    draft_id: str = Field(default_factory=lambda: new_id("plan_draft"))
    session_id: str
    status: PlanDraftStatus = PlanDraftStatus.draft
    summary: str
    selected_preset_id: str | None = None
    selected_cluster_template_ids: list[str] = Field(default_factory=list)
    plan_graph: dict[str, Any] | None = None
    policy_preview: dict[str, Any] | None = None
    capability_preview: dict[str, Any] | None = None
    notes: list[str] = Field(default_factory=list)


class LaunchDecision(PersistedContractModel):
    decision_id: str = Field(default_factory=lambda: new_id("launch_decision"))
    session_id: str
    approved: bool = False
    execute: bool = False
    selected_preset_id: str | None = None
    selected_cluster_template_ids: list[str] = Field(default_factory=list)
    rationale: str | None = None
    target_run_id: str | None = None


class FollowupRequest(PersistedContractModel):
    request_id: str = Field(default_factory=lambda: new_id("followup"))
    session_id: str
    run_id: str | None = None
    instruction: str
    intent: str = "continue"
    blocking: bool = False
    status: str = "pending"


class ChatMessageRole(StrEnum):
    user = "user"
    assistant = "assistant"
    system = "system"
    tool = "tool"


class ChatMessageType(StrEnum):
    text = "text"
    workflow_event = "workflow_event"
    confirmation_required = "confirmation_required"
    confirmation_result = "confirmation_result"
    error = "error"


class ChatMessageStatus(StrEnum):
    posted = "posted"
    pending_confirmation = "pending_confirmation"
    confirmed = "confirmed"
    blocked = "blocked"
    failed = "failed"


class ChatMessage(PersistedContractModel):
    message_id: str = Field(default_factory=lambda: new_id("chatmsg"))
    session_id: str
    run_id: str | None = None
    role: ChatMessageRole = ChatMessageRole.assistant
    content: str
    message_type: ChatMessageType = ChatMessageType.text
    action_type: str | None = None
    status: ChatMessageStatus = ChatMessageStatus.posted
    payload_json: dict[str, Any] = Field(default_factory=dict)
    provider_message_id: str | None = None
    parent_message_id: str | None = None
    stream_status: str | None = None
    graph_node: str | None = None
    token_usage: dict[str, Any] | None = None
    client_message_id: str | None = None


class ChatStreamEventType(StrEnum):
    user_message = "user_message"
    assistant_delta = "assistant_delta"
    assistant_final = "assistant_final"
    tool_action_proposed = "tool_action_proposed"
    confirmation_required = "confirmation_required"
    confirmation_result = "confirmation_result"
    graph_update = "graph_update"
    run_update = "run_update"
    status_patch = "status_patch"
    timeline_event = "timeline_event"
    test_evidence = "test_evidence"
    pr_ready_summary = "pr_ready_summary"
    heartbeat = "heartbeat"
    error = "error"


class ChatStreamEvent(PersistedContractModel):
    event_id: str = Field(default_factory=lambda: new_id("chatevt"))
    session_id: str
    run_id: str | None = None
    message_id: str | None = None
    event_type: ChatStreamEventType
    sequence_no: int = Field(default=0, ge=0)
    payload_json: dict[str, Any] = Field(default_factory=dict)


class AutomationWatchdog(PersistedContractModel):
    watchdog_id: str = Field(default_factory=lambda: new_id("watchdog"))
    session_id: str | None = None
    run_id: str | None = None
    objective: str
    trigger: str = "followup_pending"
    status: str = "active"
    auto_action_enabled: bool = False
    notes: list[str] = Field(default_factory=list)
    last_evaluated_at: datetime | None = None


class TerminationRule(ContractModel):
    max_turns: int | None = Field(default=None, ge=1)
    max_runtime_minutes: int | None = Field(default=None, ge=1)
    completion_signals: list[str] = Field(default_factory=list)
    escalate_on: list[str] = Field(default_factory=list)


class RoleEvaluationRubric(ContractModel):
    rubric_id: str = Field(default_factory=lambda: new_id("role_rubric"))
    criteria: list[str] = Field(default_factory=list)
    required_artifacts: list[str] = Field(default_factory=list)
    minimum_confidence: float | None = Field(default=None, ge=0, le=1)


class AgentProfileDefinition(PersistedContractModel):
    profile_id: str
    name: str
    description: str
    public_role: AgentRoleType
    role_label: str
    capability_tags: list[str] = Field(default_factory=list)
    repo_scope_paths: list[str] = Field(default_factory=list)
    capability_scope_tags: list[str] = Field(default_factory=list)
    visibility: ProfileVisibility = ProfileVisibility.internal
    temporary: bool = False
    cluster_only: bool = False
    system_brief: str | None = None
    termination_rule: TerminationRule = Field(default_factory=TerminationRule)
    evaluation_rubric: RoleEvaluationRubric | None = None
    execution_profile: ExecutionProfileDefinition | None = None


class GeneratedAgentProfile(PersistedContractModel):
    generated_profile_id: str = Field(default_factory=lambda: new_id("gen_profile"))
    base_profile_id: str | None = None
    source_type: GeneratedProfileSource = GeneratedProfileSource.interaction_generated
    public_role: AgentRoleType
    role_label: str
    session_id: str | None = None
    run_id: str | None = None
    cluster_template_id: str | None = None
    repo_scope_paths: list[str] = Field(default_factory=list)
    capability_scope_tags: list[str] = Field(default_factory=list)
    system_brief: str | None = None
    termination_rule: TerminationRule = Field(default_factory=TerminationRule)
    evaluation_rubric: RoleEvaluationRubric | None = None
    execution_profile: ExecutionProfileDefinition | None = None


class AgentProfileRegistry(PersistedContractModel):
    registry_id: str = Field(default_factory=lambda: new_id("profile_registry"))
    profiles: list[AgentProfileDefinition] = Field(default_factory=list)
    generated_profiles: list[GeneratedAgentProfile] = Field(default_factory=list)


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
    agent_profile_id: str | None = None
    cluster_template_id: str | None = None
    cluster_member_id: str | None = None
    role_label: str | None = None
    preferred_adapter: str | None = None
    fallback_adapter: str | None = None
    review_policy: ReviewPolicy | None = None
    execution_profile: ExecutionProfileDefinition | None = None


class OrchestrationStep(ContractModel):
    step_id: str = Field(default_factory=lambda: new_id("orchestration_step"))
    role: AgentRoleType
    title: str
    run_id: str | None = None
    preset_id: str
    agent_profile_id: str | None = None
    cluster_template_id: str | None = None
    cluster_member_id: str | None = None
    role_label: str | None = None
    preferred_adapter: str | None = None
    fallback_adapter: str | None = None
    barrier_id: str | None = None
    sequence_no: int = Field(default=1, ge=1)
    status: str = "pending"
    execution_profile: ExecutionProfileDefinition | None = None


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
    cluster_template_ids: list[str] = Field(default_factory=list)
    roles: list[RoleAssignment] = Field(default_factory=list)
    steps: list[OrchestrationStep] = Field(default_factory=list)
    barriers: list[OrchestrationBarrier] = Field(default_factory=list)
    execution_mode: str = "planner_parallel_reviewer"


class ClusterMemberSpec(ContractModel):
    member_id: str = Field(default_factory=lambda: new_id("cluster_member"))
    public_role: AgentRoleType
    agent_profile_id: str | None = None
    role_label: str
    responsibilities: list[str] = Field(default_factory=list)
    parallel_group: str | None = None
    required: bool = True
    execution_profile: ExecutionProfileDefinition | None = None


class ClusterReviewRubric(PersistedContractModel):
    rubric_id: str = Field(default_factory=lambda: new_id("cluster_rubric"))
    name: str
    criteria: list[str] = Field(default_factory=list)
    required_artifacts: list[str] = Field(default_factory=list)
    escalation_conditions: list[str] = Field(default_factory=list)
    quality_bar: str = "default"


class ExecutionClusterTemplate(PersistedContractModel):
    template_id: str
    name: str
    description: str
    domain_tags: list[str] = Field(default_factory=list)
    primary_public_role: AgentRoleType = AgentRoleType.operator
    member_specs: list[ClusterMemberSpec] = Field(default_factory=list)
    default_review_policy: ReviewPolicy = ReviewPolicy.auto_only
    execution_mode: ClusterExecutionMode = ClusterExecutionMode.mixed
    output_contract_name: str = "cluster_output_packet"
    review_rubric: ClusterReviewRubric | None = None
    default_execution_profile: ExecutionProfileDefinition | None = None


class ClusterExecutionPlan(PersistedContractModel):
    cluster_plan_id: str = Field(default_factory=lambda: new_id("cluster_plan"))
    cluster_template_id: str
    run_id: str | None = None
    session_id: str | None = None
    objective: str
    selected_member_ids: list[str] = Field(default_factory=list)
    handoff_points: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    status: str = "planned"


class ClusterHandoffPacket(PersistedContractModel):
    cluster_handoff_id: str = Field(default_factory=lambda: new_id("cluster_handoff"))
    cluster_template_id: str
    from_member_id: str | None = None
    to_member_id: str | None = None
    handoff_summary: str
    artifact_refs: list[str] = Field(default_factory=list)
    blocking_risks: list[str] = Field(default_factory=list)
    escalation_flags: list[str] = Field(default_factory=list)


class ClusterOutputPacket(PersistedContractModel):
    cluster_output_id: str = Field(default_factory=lambda: new_id("cluster_output"))
    cluster_template_id: str
    run_id: str | None = None
    objective: str
    summary: str
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    quality_verdict: str = "pending"
    escalation_flags: list[str] = Field(default_factory=list)
    followup_requests: list[str] = Field(default_factory=list)
    handoff_packets: list[ClusterHandoffPacket] = Field(default_factory=list)


class OrchestrationGraphNode(ContractModel):
    node_id: str = Field(default_factory=lambda: new_id("graphnode"))
    role: AgentRoleType
    goal: str
    agent_profile_id: str | None = None
    cluster_template_id: str | None = None
    cluster_member_id: str | None = None
    role_label: str | None = None
    required_capabilities: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    barrier_id: str | None = None
    review_gate: str = "none"
    side_effect_level: str = "read_only"
    fallback_path: list[str] = Field(default_factory=list)
    preset_id: str | None = None
    preferred_adapter: str | None = None
    retry_policy_id: str | None = None
    execution_profile: ResolvedExecutionProfile | None = None


class EdgeSpec(ContractModel):
    edge_id: str = Field(default_factory=lambda: new_id("graphedge"))
    from_node_id: str
    to_node_id: str
    edge_type: str = "depends_on"
    required: bool = True
    description: str | None = None


class BarrierSpec(ContractModel):
    barrier_id: str = Field(default_factory=lambda: new_id("graphbarrier"))
    label: str
    member_node_ids: list[str] = Field(default_factory=list)
    release_condition: str = "all_success"
    status: str = "pending"


class RetryPolicy(ContractModel):
    policy_id: str = Field(default_factory=lambda: new_id("retry"))
    target_node_ids: list[str] = Field(default_factory=list)
    max_attempts: int = Field(default=1, ge=1)
    strategy: str = "reuse_budget"
    backoff_seconds: int = Field(default=0, ge=0)


class OrchestrationPlanGraph(PersistedContractModel):
    plan_graph_id: str = Field(default_factory=lambda: new_id("plangraph"))
    run_id: str | None = None
    preset_id: str
    goal: str
    cluster_template_ids: list[str] = Field(default_factory=list)
    execution_mode: str = "single_path"
    summary: str | None = None
    risk_summary: list[str] = Field(default_factory=list)
    nodes: list[OrchestrationGraphNode] = Field(default_factory=list)
    edges: list[EdgeSpec] = Field(default_factory=list)
    barriers: list[BarrierSpec] = Field(default_factory=list)
    retry_policies: list[RetryPolicy] = Field(default_factory=list)
    engine_version: str = "m31_v1"
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
