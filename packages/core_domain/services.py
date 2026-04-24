from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from packages.contracts import (
    AgentRoleType,
    AutomationWatchdog,
    AuthorityNodeIdentity,
    BudgetLedger,
    CapabilityDescriptor,
    CapabilityExecutionReceipt,
    CapabilityInvocationEnvelope,
    CapabilityRoute,
    ControlPlaneIdentity,
    ControlPlaneHandoffEnvelope,
    ExecutionLaneType,
    DomainPackDefinition,
    DomainPackResolution,
    Evidence,
    ExecutionTargetRef,
    ExecutionProfileDefinition,
    ExecutionScopeContext,
    HandoffLite,
    LeaseRenewalRecord,
    LeaseFencingToken,
    MCPServerProfile,
    MemoryCandidate,
    MemoryItem,
    MemoryNamespace,
    MemoryRetrievalPreview,
    MutationContract,
    MutationMode,
    OrchestrationBarrier,
    OrchestrationPlan,
    OrchestrationStep,
    Phase,
    PresetDefinition,
    PresetSuggestion,
    ReviewDecision,
    ReviewPolicy,
    ReviewerType,
    ReviewVerdict,
    Run,
    RunEvent,
    RunEventType,
    RunSnapshot,
    RunSnapshotStage,
    RuntimeAttempt,
    RuntimeAttemptStatus,
    RuntimeAttemptTrigger,
    RuntimeClaim,
    RuntimeClaimStatus,
    RuntimeGateway,
    RuntimeGraphStep,
    RuntimeStateRef,
    RepoMutationResult,
    ResolvedExecutionProfile,
    SchedulerCommittedLease,
    SchedulerConsensusTerm,
    OwnershipActorKind,
    OwnershipDomainKind,
    RunStatus,
    SchedulerLeaseDecision,
    SchedulerLeaseProposal,
    SchedulerPeerHeartbeat,
    SchedulerVoteRecord,
    SimulationPolicyDefinition,
    SimulationRecord,
    SimulationRecordSource,
    SimulationReport,
    SimulationTriggerPolicy,
    ToolProjectionManifest,
    RuntimeTask,
    TaskCard,
    TaskKind,
    TaskStatus,
    TaskPacket,
    TraceContext,
    WorkerLease,
    WorkerLeaseStatus,
    allowed_run_status_transitions,
    can_transition_run_status,
)
from packages.core_domain.auto_review import AutoReviewV0
from packages.core_domain.capability_plane import CapabilityPlane, TOOL_PROJECTION_MANIFEST_ENV_KEY, load_tool_projection_manifest
from packages.core_domain.compile import CompileSnapshot, compile_run as build_compile_snapshot
from packages.core_domain.config import build_effective_config
from packages.core_domain.context_budget import build_context_budget_report
from packages.core_domain.db import unit_of_work
from packages.core_domain.domain_packs import (
    DOMAIN_PACK_RESOLUTION_ENV_KEY,
    DomainPackRegistry,
    load_domain_pack_resolution,
)
from packages.core_domain.errors import (
    BudgetExhaustedError,
    CapabilityAdapterNotFoundError,
    DatabaseBusyError,
    EntityNotFoundError,
    ExecutionLaneNotAllowedError,
    InvalidStateTransitionError,
    MutationContractError,
    PatchApplyError,
    PresetNotFoundError,
    PresetRequiredError,
    RepairActionNotAvailableError,
    RepoMutationScopeError,
    RuntimeClaimConflictError,
    SchedulerArbitrationError,
    TaskKindNotAllowedError,
    UnsupportedRepairActionError,
    UnsupportedTaskKindError,
    WorkflowError,
)
from packages.core_domain.execution_profiles import build_effective_execution_defaults, resolve_execution_profile
from packages.core_domain.memory import (
    MEMORY_RETRIEVAL_PREVIEW_ENV_KEY,
    load_memory_retrieval_preview,
    load_seed_memory_namespaces,
)
from packages.core_domain.simulation import LocalDeterministicSimulationRunner, SimulationPolicyRegistry
from packages.core_domain.evidence_builder import EvidenceBuilder
from packages.core_domain.repositories import (
    BudgetLedgerRepository,
    AutomationWatchdogRepository,
    EventRepository,
    EvidenceRepository,
    FollowupRequestRepository,
    GeneratedAgentProfileRepository,
    HandoffRepository,
    IntentSessionRepository,
    MemoryItemRepository,
    PresetRepository,
    ReviewRepository,
    RunSnapshotRepository,
    RunRepository,
    SchedulerLeaseDecisionRepository,
    SchedulerLeaseProposalRepository,
    SchedulerPeerHeartbeatRepository,
    SimulationRecordRepository,
    RuntimeAttemptRepository,
    RuntimeClaimRepository,
    RuntimeStateRepository,
    TaskRepository,
    WorkerLeaseRepository,
)
from packages.core_domain.resolver import PresetResolver
from packages.core_domain.service_lifecycle import LifecycleServiceMixin
from packages.core_domain.service_interaction import InteractionServiceMixin
from packages.core_domain.service_memory_simulation import MemorySimulationServiceMixin
from packages.core_domain.service_orchestration import OrchestrationExecutionService
from packages.core_domain.service_projection import ProjectionServiceMixin
from packages.core_domain.service_scheduler_authority_support import SchedulerAuthoritySupportService
from packages.core_domain.service_types import (
    ExecutedRunBundle,
    PreparedRunBundle,
    ReviewedRunBundle,
    RunDiagnosticContext,
)
from packages.core_domain.external_workers import (
    ExternalWorkerGateway,
    load_worker_pool_profiles,
    resolve_worker_pool_profile,
)
from packages.core_domain.repo_mutation import (
    apply_unified_diff,
    capture_workspace_snapshot,
    extract_touched_paths,
    hash_patch_text,
    is_path_allowed,
    normalize_allowed_paths,
    restore_workspace_snapshot,
    run_test_commands,
)
from packages.core_domain.scheduler_authority import NullSchedulerAuthorityCluster, SchedulerAuthorityClusterService
from packages.core_domain.skills import export_domain_pack_skill_bundle
from packages.core_domain.m8_flags import (
    active_feature_flags,
    is_agent_lane_enabled,
    is_durable_pilot_enabled,
    is_external_worker_pools_enabled,
    is_mcp_source_enabled,
    is_sessionful_external_agents_enabled,
    is_skill_export_enabled,
)
from packages.core_domain.observability import NullTraceExporter, TraceExporter, TraceRecord, build_trace_exporter_from_env
from packages.core_domain.orchestration_engine import OrchestrationEngine
from packages.runtime_langgraph.durable_pilot import (
    DurableRuntimePilot,
    NullDurableRuntimePilot,
    build_durable_runtime_pilot_from_env,
)
from packages.core_domain.service_audit_replay import AuditReplayService
from packages.runtime_langgraph.gateway import build_runtime_gateway_from_env, resolve_runtime_gateway
from packages.core_domain.service_ownership_lease import OwnershipLeaseService
from packages.core_domain.service_review_policy import ReviewPolicyService
from packages.core_domain.service_run_lifecycle import RunLifecycleService
from packages.worker_adapters.langchain_agent_adapter import LangChainAgentAdapter
from packages.worker_adapters.base import ExecutionResult
from packages.worker_adapters.codex_adapter import CodexAdapter
from packages.worker_adapters.noop_adapter import NoopAdapter
from packages.worker_adapters.opencode_adapter import OpenCodeAdapter
from packages.worker_adapters.opencode_session_adapter import OpenCodeSessionAdapter
from packages.worker_adapters.router import WorkerRouter
from packages.worker_adapters.shell_adapter import ShellAdapter


class OrchestratorService(
    LifecycleServiceMixin,
    MemorySimulationServiceMixin,
    InteractionServiceMixin,
    ProjectionServiceMixin,
):
    CLAIM_LEASE_SECONDS = 300
    WORKER_LEASE_SECONDS = 300
    SUPPORTED_REPAIR_ACTIONS = (
        "align_cancelled_runtime_state",
        "align_completed_runtime_state",
        "close_current_runtime_attempt_terminal",
        "create_repair_runtime_attempt",
        "expire_runtime_claim",
        "interrupt_current_runtime_attempt",
        "expire_worker_lease",
        "recompile_prepared_run",
        "release_runtime_claim",
        "release_worker_lease",
    )

    def __init__(
        self,
        db_path: str | Path | None = None,
        runtime_gateway: RuntimeGateway | None = None,
        shell_adapter: ShellAdapter | None = None,
        worker_router: WorkerRouter | None = None,
        capability_plane: CapabilityPlane | None = None,
        domain_pack_registry: DomainPackRegistry | None = None,
        simulation_policy_registry: SimulationPolicyRegistry | None = None,
        evidence_builder: EvidenceBuilder | None = None,
        auto_review: AutoReviewV0 | None = None,
        simulation_runner: LocalDeterministicSimulationRunner | None = None,
        trace_exporter: TraceExporter | None = None,
        durable_runtime_pilot: DurableRuntimePilot | None = None,
        external_worker_gateway: ExternalWorkerGateway | None = None,
    ):
        self.db_path = Path(db_path) if db_path is not None else None
        self.effective_config = build_effective_config(
            explicit_db_path=self.db_path.as_posix() if self.db_path is not None else None
        )
        self.run_repo = RunRepository(self.db_path)
        self.preset_repo = PresetRepository(self.db_path)
        self.budget_repo = BudgetLedgerRepository(self.db_path)
        self.task_repo = TaskRepository(self.db_path)
        self.event_repo = EventRepository(self.db_path)
        self.evidence_repo = EvidenceRepository(self.db_path)
        self.review_repo = ReviewRepository(self.db_path)
        self.handoff_repo = HandoffRepository(self.db_path)
        self.runtime_state_repo = RuntimeStateRepository(self.db_path)
        self.runtime_attempt_repo = RuntimeAttemptRepository(self.db_path)
        self.runtime_claim_repo = RuntimeClaimRepository(self.db_path)
        self.worker_lease_repo = WorkerLeaseRepository(self.db_path)
        self.scheduler_proposal_repo = SchedulerLeaseProposalRepository(self.db_path)
        self.scheduler_decision_repo = SchedulerLeaseDecisionRepository(self.db_path)
        self.scheduler_peer_heartbeat_repo = SchedulerPeerHeartbeatRepository(self.db_path)
        self.snapshot_repo = RunSnapshotRepository(self.db_path)
        self.memory_item_repo = MemoryItemRepository(self.db_path)
        self.intent_session_repo = IntentSessionRepository(self.db_path)
        self.followup_request_repo = FollowupRequestRepository(self.db_path)
        self.generated_agent_profile_repo = GeneratedAgentProfileRepository(self.db_path)
        self.automation_watchdog_repo = AutomationWatchdogRepository(self.db_path)
        self.simulation_record_repo = SimulationRecordRepository(self.db_path)
        self.runtime_gateway = runtime_gateway or build_runtime_gateway_from_env()
        runtime_gateway_description = self.runtime_gateway.describe()
        self.effective_config["runtime_gateway"]["provider"] = runtime_gateway_description.get("provider")
        self.effective_config["runtime_gateway"]["provider_source"] = (
            "runtime_gateway_argument" if runtime_gateway is not None else self.effective_config["runtime_gateway"]["provider_source"]
        )
        if runtime_gateway_description.get("model") is not None:
            self.effective_config["runtime_gateway"]["openai_model"] = runtime_gateway_description.get("model")
            self.effective_config["runtime_gateway"]["openai_model_source"] = (
                "runtime_gateway_argument"
                if runtime_gateway is not None
                else self.effective_config["runtime_gateway"]["openai_model_source"]
            )
        if runtime_gateway_description.get("reasoning_effort") is not None:
            self.effective_config["runtime_gateway"]["openai_reasoning_effort"] = runtime_gateway_description.get(
                "reasoning_effort"
            )
            self.effective_config["runtime_gateway"]["openai_reasoning_effort_source"] = (
                "runtime_gateway_argument"
                if runtime_gateway is not None
                else self.effective_config["runtime_gateway"]["openai_reasoning_effort_source"]
            )
        self.effective_config["execution_defaults"] = build_effective_execution_defaults(self.effective_config)
        self.capability_plane = capability_plane or CapabilityPlane(workspace_root=self._workspace_root())
        adapters = [shell_adapter or ShellAdapter(), CodexAdapter(), OpenCodeAdapter(), NoopAdapter()]
        if is_sessionful_external_agents_enabled():
            adapters.append(OpenCodeSessionAdapter())
        if is_agent_lane_enabled():
            adapters.append(
                LangChainAgentAdapter(
                    mcp_tool_caller=self.capability_plane.mcp_source.call_tool,
                )
            )
        self.worker_router = worker_router or WorkerRouter(adapters)
        self.domain_pack_registry = domain_pack_registry or DomainPackRegistry()
        self.simulation_policy_registry = simulation_policy_registry or SimulationPolicyRegistry()
        self.evidence_builder = evidence_builder or EvidenceBuilder()
        self.auto_review = auto_review or AutoReviewV0()
        self.simulation_runner = simulation_runner or LocalDeterministicSimulationRunner()
        self.trace_exporter = trace_exporter or build_trace_exporter_from_env()
        self.durable_runtime_pilot = durable_runtime_pilot or build_durable_runtime_pilot_from_env()
        self.external_worker_gateway = external_worker_gateway or ExternalWorkerGateway()
        self.orchestration_engine = OrchestrationEngine()
        self.worker_pool_profiles = load_worker_pool_profiles(self.effective_config["worker_pools"]["seed_path"])
        control_plane_id = self.effective_config["control_plane"]["id"]
        self.control_plane_identity = ControlPlaneIdentity(
            control_plane_id=control_plane_id,
            name=control_plane_id,
            endpoint=self.effective_config["db"]["path"],
            status="active",
        )
        self.scheduler_authority_cluster_enabled = bool(self.effective_config["scheduler_authority"]["enabled"])
        scheduler_authority_cluster_cls = (
            SchedulerAuthorityClusterService
            if self.scheduler_authority_cluster_enabled
            else NullSchedulerAuthorityCluster
        )
        self.scheduler_authority_cluster = scheduler_authority_cluster_cls(
            self.db_path,
            node_id=self.effective_config["scheduler_authority"]["node_id"],
            bind_url=self.effective_config["scheduler_authority"]["bind_url"],
            peer_urls=self.effective_config["scheduler_authority"]["peer_urls"],
            quorum_size=self.effective_config["scheduler_authority"]["quorum_size"],
            election_timeout_ms=self.effective_config["scheduler_authority"]["election_timeout_ms"],
            heartbeat_interval_ms=self.effective_config["scheduler_authority"]["heartbeat_interval_ms"],
        )
        if not self.preset_repo.list():
            self.preset_repo.seed_defaults()
        self.scheduler_authority_support = SchedulerAuthoritySupportService(self)
        self.orchestration_service = OrchestrationExecutionService(self)
        self.run_lifecycle_service = RunLifecycleService(self)
        self.review_policy_service = ReviewPolicyService(self)
        self.audit_replay_service = AuditReplayService(self)
        self.ownership_lease_service = OwnershipLeaseService(self)

    def _resolver(self) -> PresetResolver:
        return PresetResolver(self.preset_repo.list())

    def _require_status(self, run: Run, action: str, allowed_statuses: list[RunStatus | str]) -> None:
        allowed = [str(status) for status in allowed_statuses]
        if str(run.status) not in allowed:
            raise InvalidStateTransitionError(action, str(run.status), allowed)

    def _transition_run_status(
        self,
        run: Run,
        action: str,
        target_status: RunStatus | str,
        *,
        connection=None,
    ) -> Run:
        normalized_target = RunStatus(target_status)
        if not can_transition_run_status(run.status, normalized_target):
            raise InvalidStateTransitionError(
                action,
                str(run.status),
                [str(status) for status in allowed_run_status_transitions(run.status)],
                str(normalized_target),
            )
        updated_run = self.run_repo.update_status(run.run_id, normalized_target, connection=connection)
        assert updated_run is not None
        return updated_run

    def _next_action_for(self, status: str) -> str:
        if status == RunStatus.pending:
            return "compile"
        if status == RunStatus.prepared:
            return "resume"
        if status == RunStatus.awaiting_review:
            return "human_review"
        if status == RunStatus.running:
            return "observe"
        return "none"

    def _review_policy_for_context(
        self,
        context: RunDiagnosticContext,
        *,
        last_runtime_state: RuntimeStateRef | None = None,
    ) -> str:
        if context.preset is not None:
            return str(context.preset.default_review_policy)
        state_ref = last_runtime_state or self._last_runtime_state(context)
        if state_ref is not None and state_ref.state_payload.get("review_policy"):
            return str(state_ref.state_payload["review_policy"])
        return str(ReviewPolicy.auto_only)

    def _effective_review_state(
        self,
        run: Run,
        latest_review_verdict: ReviewVerdict | None,
        review_policy: ReviewPolicy | str | None = None,
    ) -> str:
        normalized_policy = str(review_policy or ReviewPolicy.auto_only)
        if str(run.status) == RunStatus.awaiting_review:
            if latest_review_verdict is None:
                return "human_pending"
            if str(latest_review_verdict.reviewer_type) != ReviewerType.human:
                return "human_pending"
        if latest_review_verdict is None:
            return "not_requested"
        if str(latest_review_verdict.reviewer_type) == ReviewerType.human:
            return "human_approved" if str(latest_review_verdict.decision) == ReviewDecision.pass_ else "human_rejected"
        if normalized_policy == str(ReviewPolicy.optional):
            return "advisory_passed" if str(latest_review_verdict.decision) == ReviewDecision.pass_ else "advisory_failed"
        return "auto_passed" if str(latest_review_verdict.decision) == ReviewDecision.pass_ else "auto_failed"

    def _serialize_contract(self, value: Evidence | ReviewVerdict | RuntimeStateRef | None) -> dict[str, Any] | None:
        return value.model_dump(mode="json") if value is not None else None

    def _serialize_claim(self, value: RuntimeClaim | None) -> dict[str, Any] | None:
        return value.model_dump(mode="json") if value is not None else None

    def _serialize_snapshot(self, value: RunSnapshot | None) -> dict[str, Any] | None:
        return value.model_dump(mode="json") if value is not None else None

    def _serialize_worker_lease(self, value: WorkerLease | None) -> dict[str, Any] | None:
        return value.model_dump(mode="json") if value is not None else None

    def _serialize_attempt(self, value: RuntimeAttempt | None) -> dict[str, Any] | None:
        return value.model_dump(mode="json") if value is not None else None

    def _control_plane_identity(self) -> tuple[str, str, str]:
        return (
            str(OwnershipActorKind.control_plane),
            "control_plane_local",
            "local_orchestrator",
        )

    def _worker_identity(self, adapter_name: str, *, worker_name: str | None = None) -> tuple[str, str, str]:
        normalized_adapter = (adapter_name or "worker").strip().lower().replace(" ", "_")
        return (
            str(OwnershipActorKind.worker),
            f"worker_{normalized_adapter}_local",
            worker_name or "local_worker",
        )

    def _ownership_domain_for(
        self,
        runtime_task_id: str,
        *,
        domain_kind: OwnershipDomainKind | str = OwnershipDomainKind.runtime_task,
        domain_key: str | None = None,
    ) -> tuple[str, str]:
        normalized_kind = str(OwnershipDomainKind(domain_kind))
        return normalized_kind, domain_key or runtime_task_id

    def _utc_now(self) -> datetime:
        return datetime.now(UTC)

    def _parse_iso_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

    def _workspace_root(self) -> Path:
        return Path.cwd().resolve()

    def _feature_flags(self) -> dict[str, bool]:
        return active_feature_flags()

    def get_effective_config(self) -> dict[str, Any]:
        return self.effective_config

    def list_worker_pool_profiles(self) -> list[dict[str, Any]]:
        return [
            {
                **profile.model_dump(mode="json"),
                "feature_flag_enabled": is_external_worker_pools_enabled(),
                "default_selected": profile.worker_pool_id == self.effective_config["worker_pools"]["default_pool_id"],
            }
            for profile in self.worker_pool_profiles
        ]

    def _selected_worker_pool_profile(self, worker_pool_id: str | None = None) -> Any | None:
        if not is_external_worker_pools_enabled():
            return None
        return resolve_worker_pool_profile(
            self.worker_pool_profiles,
            worker_pool_id or self.effective_config["worker_pools"]["default_pool_id"],
        )

    def _runtime_gateway_for_task_packet(self, task_packet: TaskPacket):
        return resolve_runtime_gateway(
            self.runtime_gateway,
            provider=task_packet.env.get("WORKFLOW_RUNTIME_GATEWAY_PROVIDER") or None,
            model=(
                task_packet.env.get("WORKFLOW_RUNTIME_GATEWAY_MODEL")
                or task_packet.env.get("WORKFLOW_LLM_MODEL")
                or None
            ),
            reasoning_effort=task_packet.env.get("WORKFLOW_RUNTIME_REASONING_EFFORT") or None,
        )

    def _scheduler_authority_payload(self, state_ref: RuntimeStateRef | None) -> dict[str, Any]:
        return self.scheduler_authority_support.authority_payload(state_ref)

    def _scheduler_decision_history(
        self,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self.scheduler_authority_support.decision_history(payload)

    def _scheduler_conflicts(
        self,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self.scheduler_authority_support.conflicts(payload)

    def _scheduler_handoff_history(
        self,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self.scheduler_authority_support.handoff_history(payload)

    def _cluster_summary_payload(
        self,
        *,
        cluster: dict[str, Any] | None = None,
        term: SchedulerConsensusTerm | dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return self.scheduler_authority_support.cluster_summary_payload(cluster=cluster, term=term)

    def _scheduler_context_for_dispatch(
        self,
        committed_lease: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return self.scheduler_authority_support.scheduler_context_for_dispatch(committed_lease)

    def _scheduler_committed_lease_payload(
        self,
        committed_lease: SchedulerCommittedLease | dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return self.scheduler_authority_support.committed_lease_payload(committed_lease)

    def _scheduler_handoff_envelope_payload(
        self,
        handoff_envelope: ControlPlaneHandoffEnvelope | dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return self.scheduler_authority_support.handoff_envelope_payload(handoff_envelope)

    def _scheduler_arbitration_updates(
        self,
        state_ref: RuntimeStateRef | None,
        *,
        control_plane_id: str,
        proposal: SchedulerLeaseProposal | None = None,
        decision: SchedulerLeaseDecision | None = None,
        committed_lease: SchedulerCommittedLease | dict[str, Any] | None = None,
        term: SchedulerConsensusTerm | dict[str, Any] | None = None,
        votes: list[SchedulerVoteRecord | dict[str, Any]] | None = None,
        handoff_envelope: ControlPlaneHandoffEnvelope | dict[str, Any] | None = None,
        heartbeat: SchedulerPeerHeartbeat | None = None,
        cluster: dict[str, Any] | None = None,
        conflict: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.scheduler_authority_support.arbitration_updates(
            state_ref,
            control_plane_id=control_plane_id,
            proposal=proposal,
            decision=decision,
            committed_lease=committed_lease,
            term=term,
            votes=votes,
            handoff_envelope=handoff_envelope,
            heartbeat=heartbeat,
            cluster=cluster,
            conflict=conflict,
        )

    def _create_control_plane_handoff_envelope(
        self,
        *,
        run_id: str,
        runtime_task_id: str,
        from_control_plane_id: str,
        to_control_plane_id: str,
        committed_lease: SchedulerCommittedLease,
        connection=None,
    ) -> ControlPlaneHandoffEnvelope:
        snapshots = self.snapshot_repo.list_for_run(run_id)
        latest_snapshot = snapshots[-1] if snapshots else None
        latest_review_verdict = self.review_repo.latest_for_run(run_id)
        state_ref = self.runtime_state_repo.get_by_task(runtime_task_id, connection=connection)
        replay_excerpt = {}
        try:
            replay = self.get_run_replay_packet(run_id)
            replay_excerpt = {
                "headline": replay["summary"]["headline"],
                "next_action": replay["summary"]["next_action"],
                "failure_taxonomy": replay["summary"]["failure_taxonomy"],
            }
        except WorkflowError:
            replay_excerpt = {}
        envelope = self.scheduler_authority_cluster.create_handoff_envelope(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            from_control_plane_id=from_control_plane_id,
            to_control_plane_id=to_control_plane_id,
            committed_lease_id=committed_lease.committed_lease_id,
            term_no=committed_lease.term_no,
            commit_index=committed_lease.commit_index,
            snapshot_payload=latest_snapshot.snapshot_payload if latest_snapshot is not None else {},
            review_state=(
                latest_review_verdict.model_dump(mode="json")
                if latest_review_verdict is not None
                else {"effective_review_state": "not_requested"}
            ),
            durable_refs=self._durable_refs_for_state(state_ref),
            replay_excerpt=replay_excerpt,
            connection=connection,
        )
        return envelope

    def _ensure_committed_scheduler_lease(
        self,
        *,
        run: Run,
        runtime_task: RuntimeTask,
        connection=None,
    ) -> tuple[dict[str, Any], ControlPlaneHandoffEnvelope | None]:
        result = self.scheduler_authority_cluster.submit_proposal(
            control_plane_id=self.control_plane_identity.control_plane_id,
            run_id=run.run_id,
            runtime_task_id=runtime_task.runtime_task_id,
            domain_kind="runtime_task",
            domain_key=runtime_task.runtime_task_id,
            connection=connection,
        )
        if not result.get("granted"):
            raise SchedulerArbitrationError(
                "control plane does not own a committed scheduler lease for the runtime task",
                {
                    "run_id": run.run_id,
                    "runtime_task_id": runtime_task.runtime_task_id,
                    "result": result,
                },
            )
        previous = result.get("previous_committed_lease")
        current = result.get("committed_lease")
        handoff_envelope = None
        if (
            isinstance(previous, dict)
            and isinstance(current, dict)
            and previous.get("control_plane_id") is not None
            and previous.get("control_plane_id") != current.get("control_plane_id")
        ):
            handoff_envelope = self._create_control_plane_handoff_envelope(
                run_id=run.run_id,
                runtime_task_id=runtime_task.runtime_task_id,
                from_control_plane_id=str(previous["control_plane_id"]),
                to_control_plane_id=str(current["control_plane_id"]),
                committed_lease=SchedulerCommittedLease.model_validate(current),
                connection=connection,
            )
            result["handoff_envelope"] = self._scheduler_handoff_envelope_payload(handoff_envelope)
        return result, handoff_envelope

    def _validate_callback_scheduler_context(
        self,
        *,
        runtime_task_id: str,
        execution_target: dict[str, Any] | None,
        connection=None,
    ) -> SchedulerCommittedLease:
        current_committed = self.scheduler_authority_cluster.get_active_committed_lease_for_domain(
            domain_kind="runtime_task",
            domain_key=runtime_task_id,
            connection=connection,
        )
        if current_committed is None:
            raise SchedulerArbitrationError(
                "worker callback arrived without an active committed scheduler lease",
                {"runtime_task_id": runtime_task_id},
            )
        if current_committed.control_plane_id != self.control_plane_identity.control_plane_id:
            raise SchedulerArbitrationError(
                "worker callback was received by a stale control plane",
                {
                    "runtime_task_id": runtime_task_id,
                    "active_control_plane_id": current_committed.control_plane_id,
                    "local_control_plane_id": self.control_plane_identity.control_plane_id,
                },
            )
        target = execution_target or {}
        if (
            target.get("committed_lease_id")
            and str(target.get("committed_lease_id")) != current_committed.committed_lease_id
        ):
            raise SchedulerArbitrationError(
                "worker callback committed lease does not match the active committed lease",
                {
                    "runtime_task_id": runtime_task_id,
                    "callback_committed_lease_id": target.get("committed_lease_id"),
                    "active_committed_lease_id": current_committed.committed_lease_id,
                },
            )
        if target.get("fencing_token") and str(target.get("fencing_token")) != current_committed.fencing_token:
            raise SchedulerArbitrationError(
                "worker callback fencing token does not match the active committed lease",
                {
                    "runtime_task_id": runtime_task_id,
                    "callback_fencing_token": target.get("fencing_token"),
                    "active_fencing_token": current_committed.fencing_token,
                },
            )
        return current_committed

    def _default_project_delivery_plan(self, run_id: str) -> OrchestrationPlan:
        plan = self.orchestration_service.default_orchestration_plan_for_preset("project_delivery", run_id)
        if plan is None:
            raise WorkflowError("default orchestration plan was not available", {"preset_id": "project_delivery"})
        return plan

    def _default_guarded_project_delivery_plan(self, run_id: str) -> OrchestrationPlan:
        plan = self.orchestration_service.default_orchestration_plan_for_preset("guarded_project_delivery", run_id)
        if plan is None:
            raise WorkflowError(
                "default orchestration plan was not available",
                {"preset_id": "guarded_project_delivery"},
            )
        return plan

    def _default_orchestration_plan_for_preset(self, preset_id: str, run_id: str) -> OrchestrationPlan | None:
        return self.orchestration_service.default_orchestration_plan_for_preset(preset_id, run_id)

    def _capability_descriptor_index(self) -> dict[str, CapabilityDescriptor]:
        descriptors = self.capability_plane.list_capability_descriptors(
            worker_pool_profiles=self.worker_pool_profiles,
            runtime_gateway_description=self.runtime_gateway.describe(),
            capability_routes=self.list_capability_routes(),
            default_worker_pool_id=self.effective_config["worker_pools"]["default_pool_id"],
        )
        return {descriptor.capability_id: descriptor for descriptor in descriptors}

    def _capability_descriptor_for_snapshot(
        self,
        snapshot: CompileSnapshot,
    ) -> CapabilityDescriptor:
        descriptors = self._capability_descriptor_index()
        worker_pool_id = snapshot.task_packet.env.get("WORKFLOW_WORKER_POOL_ID")
        if isinstance(worker_pool_id, str) and worker_pool_id:
            descriptor = descriptors.get(f"worker_pool:{worker_pool_id}")
            if descriptor is not None:
                return descriptor
        if snapshot.capability_route is not None:
            descriptor = descriptors.get(
                f"adapter_route:{snapshot.runtime_task.task_kind}:{snapshot.capability_route.adapter_name}"
            )
            if descriptor is not None:
                return descriptor
        return descriptors.get("built_in:local") or CapabilityDescriptor(
            capability_id="built_in:local",
            provider_kind="built_in",
            transport="local",
            scopes=["fallback_local"],
            allowed_task_kinds=[TaskKind(snapshot.runtime_task.task_kind)],
        )

    def _capability_invocation_envelope_for_snapshot(
        self,
        *,
        run: Run,
        preset: PresetDefinition,
        snapshot: CompileSnapshot,
    ) -> CapabilityInvocationEnvelope:
        worker_pool_id = snapshot.task_packet.env.get("WORKFLOW_WORKER_POOL_ID")
        return CapabilityInvocationEnvelope(
            run_id=run.run_id,
            runtime_task_id=snapshot.runtime_task.runtime_task_id,
            preset_id=preset.preset_id,
            task_kind=snapshot.runtime_task.task_kind,
            lane_type=snapshot.execution_lane,
            review_policy=preset.default_review_policy,
            authority_mode=self.effective_config["scheduler_authority"]["authority_mode"],
            descriptor=self._capability_descriptor_for_snapshot(snapshot),
            worker_pool_id=worker_pool_id if isinstance(worker_pool_id, str) else None,
            tool_projection_id=(
                snapshot.tool_projection_manifest.projection_id if snapshot.tool_projection_manifest is not None else None
            ),
            mutation_mode=(
                snapshot.task_packet.mutation_contract.mutation_mode
                if snapshot.task_packet.mutation_contract is not None
                else None
            ),
        )

    def _capability_invocation_envelope_from_state(
        self,
        state_ref: RuntimeStateRef | None,
    ) -> CapabilityInvocationEnvelope | None:
        if state_ref is None:
            return None
        payload = state_ref.state_payload.get("capability_invocation_envelope")
        if not isinstance(payload, dict):
            return None
        return CapabilityInvocationEnvelope.model_validate(payload)

    def _capability_execution_receipt_from_state(
        self,
        state_ref: RuntimeStateRef | None,
        evidence: Evidence | None,
    ) -> CapabilityExecutionReceipt | None:
        if state_ref is not None:
            payload = state_ref.state_payload.get("capability_execution_receipt")
            if isinstance(payload, dict):
                return CapabilityExecutionReceipt.model_validate(payload)
        if evidence is not None:
            payload = evidence.raw_execution.get("metadata", {}).get("capability_execution_receipt")
            if isinstance(payload, dict):
                return CapabilityExecutionReceipt.model_validate(payload)
        return None

    def _capability_failure_class_for_result(
        self,
        descriptor: CapabilityDescriptor,
        execution_result: ExecutionResult,
    ) -> str | None:
        if execution_result.return_code == 0:
            return None
        mapping = {
            "mcp_profile": "call_timeout",
            "worker_pool": "dispatch_failed",
            "runtime_gateway": "provider_call_failed",
            "adapter_route": "execution_failed",
        }
        return mapping.get(descriptor.provider_kind, "execution_failed")

    def _capability_execution_receipt_for_result(
        self,
        *,
        state_ref: RuntimeStateRef | None,
        execution_result: ExecutionResult,
    ) -> CapabilityExecutionReceipt | None:
        envelope = self._capability_invocation_envelope_from_state(state_ref)
        if envelope is None:
            return None
        execution_target = execution_result.metadata.get("execution_target")
        return CapabilityExecutionReceipt(
            envelope=envelope,
            status="completed" if execution_result.return_code == 0 else "failed",
            adapter_name=execution_result.adapter_name,
            return_code=execution_result.return_code,
            started_at=execution_result.started_at,
            finished_at=execution_result.finished_at,
            duration_ms=execution_result.duration_ms,
            artifact_paths=list(execution_result.artifact_paths),
            failure_class=self._capability_failure_class_for_result(envelope.descriptor, execution_result),
            execution_target=dict(execution_target) if isinstance(execution_target, dict) else None,
            metadata={
                "tool_projection_id": envelope.tool_projection_id,
                "worker_pool_id": envelope.worker_pool_id,
            },
        )

    def _orchestration_from_context(self, context: RunDiagnosticContext) -> dict[str, Any] | None:
        last_evidence = self._last_evidence(context)
        if last_evidence is not None:
            orchestration = last_evidence.raw_execution.get("metadata", {}).get("orchestration")
            if isinstance(orchestration, dict):
                return orchestration
        last_runtime_state = self._last_runtime_state(context)
        if last_runtime_state is not None:
            orchestration = last_runtime_state.state_payload.get("orchestration")
            if isinstance(orchestration, dict):
                return orchestration
        return None

    def _orchestration_plan_graph_from_context(self, context: RunDiagnosticContext) -> dict[str, Any] | None:
        last_runtime_state = self._last_runtime_state(context)
        if last_runtime_state is not None:
            graph = last_runtime_state.state_payload.get("orchestration_plan_graph")
            if isinstance(graph, dict):
                return graph
        runtime_task = self._runtime_task_for_context(context)
        if runtime_task is None:
            return None
        task_packet = self.task_repo.get_task_packet(runtime_task.runtime_task_id)
        if task_packet is None:
            return None
        payload = task_packet.env.get("WORKFLOW_ORCHESTRATION_PLAN_GRAPH")
        if not payload:
            return None
        return json.loads(payload)

    def get_run_orchestration(self, run_id: str) -> dict[str, Any]:
        context = self._load_run_context(run_id)
        orchestration = self._orchestration_from_context(context)
        if orchestration is None:
            return {"run_id": run_id, "enabled": False, "orchestration": None}
        return {"run_id": run_id, "enabled": True, "orchestration": orchestration}

    def get_run_orchestration_plan_graph(self, run_id: str) -> dict[str, Any]:
        context = self._load_run_context(run_id)
        plan_graph = self._orchestration_plan_graph_from_context(context)
        if plan_graph is None:
            return {"run_id": run_id, "enabled": False, "plan_graph": None}
        return {"run_id": run_id, "enabled": True, "plan_graph": plan_graph}

    def _compile_child_run_with_fallback(
        self,
        run_id: str,
        *,
        preferred_adapter: str | None,
        fallback_adapter: str | None,
        mutation_contract: MutationContract | None = None,
    ) -> PreparedRunBundle:
        return self.orchestration_service.compile_child_run_with_fallback(
            run_id,
            preferred_adapter=preferred_adapter,
            fallback_adapter=fallback_adapter,
            mutation_contract=mutation_contract,
        )

    def _finalize_child_run_if_waiting(self, run_id: str) -> Run:
        return self.orchestration_service.finalize_child_run_if_waiting(run_id)

    def _role_goal_for(self, parent_goal: str, role: AgentRoleType, *, parallel_run_ids: list[str] | None = None) -> str:
        if role == AgentRoleType.planner:
            return f"Plan a structured work breakdown for this project goal: {parent_goal}"
        if role == AgentRoleType.coder:
            return f"Implement the primary delivery slice for this project goal: {parent_goal}"
        if role == AgentRoleType.researcher:
            return f"Research risks, references, and open questions for this project goal: {parent_goal}"
        if role == AgentRoleType.reviewer:
            child_line = ", ".join(parallel_run_ids or [])
            return f"Review orchestration evidence for this project goal: {parent_goal}. Parallel child runs: {child_line}"
        return parent_goal

    def _write_orchestration_artifact(self, packet: TaskPacket, content: str) -> list[str]:
        return self.orchestration_service.write_orchestration_artifact(packet, content)

    def _task_card_content_for_mutation(self, contract: MutationContract | None, *, working_directory: str) -> str | None:
        if contract is None or not contract.task_card_path:
            return None
        task_card_path = Path(contract.task_card_path)
        if not task_card_path.is_absolute():
            task_card_path = Path(working_directory) / task_card_path
        resolved = task_card_path.resolve()
        if not resolved.exists():
            raise MutationContractError(
                "task_card_path does not exist for mutation contract",
                {"task_card_path": contract.task_card_path},
            )
        return resolved.read_text(encoding="utf-8")

    def _packet_for_mutation_attempt(
        self,
        packet: TaskPacket,
        contract: MutationContract,
        *,
        attempt_index: int,
        failure_feedback: str | None,
    ) -> TaskPacket:
        task_card_content = self._task_card_content_for_mutation(contract, working_directory=packet.working_directory)
        return TaskPacket.model_validate(
            {
                **packet.model_dump(mode="json"),
                "env": {
                    **packet.env,
                    "WORKFLOW_MUTATION_TASK_CARD_REF": contract.task_card_ref or "",
                    "WORKFLOW_MUTATION_TASK_CARD_PATH": contract.task_card_path or "",
                    "WORKFLOW_MUTATION_TASK_CARD_CONTENT": task_card_content or "",
                    "WORKFLOW_MUTATION_WRITE_SET": json.dumps(contract.write_set, ensure_ascii=False),
                    "WORKFLOW_MUTATION_READ_SET": json.dumps(contract.read_set, ensure_ascii=False),
                    "WORKFLOW_MUTATION_TEST_COMMANDS": json.dumps(contract.test_commands, ensure_ascii=False),
                    "WORKFLOW_MUTATION_ATTEMPT_INDEX": str(attempt_index),
                    "WORKFLOW_MUTATION_FAILURE_FEEDBACK": failure_feedback or "",
                },
            }
        )

    def _merge_test_feedback(self, attempts: list[dict[str, Any]]) -> str:
        if not attempts:
            return ""
        chunks: list[str] = []
        for attempt in attempts[-3:]:
            chunks.append(
                "\n".join(
                    [
                        f"command: {attempt['command']}",
                        f"return_code: {attempt['return_code']}",
                        f"stdout:\n{attempt['stdout']}",
                        f"stderr:\n{attempt['stderr']}",
                    ]
                ).strip()
            )
        return "\n\n".join(chunks)

    def _execute_repo_mutation(
        self,
        adapter,
        packet: TaskPacket,
    ) -> ExecutionResult:
        contract = packet.mutation_contract
        if contract is None or contract.mutation_mode != MutationMode.patch_apply:
            return adapter.launch(packet)
        if not adapter.supports_mutation_mode(MutationMode.patch_apply):
            raise MutationContractError(
                "repo mutation execution requires a patch-capable adapter",
                {"adapter_name": adapter.normalized_name()},
            )
        allowed_paths = normalize_allowed_paths(packet.working_directory, contract.write_set)
        baseline_snapshot = capture_workspace_snapshot(packet.working_directory, contract.write_set)
        attempt_limit = max(contract.max_fix_iterations, 0)
        failure_feedback: str | None = None
        aggregated_test_attempts: list[dict[str, Any]] = []
        out_of_scope_rejections: list[str] = []
        last_result: ExecutionResult | None = None
        last_patch_hash: str | None = None
        last_touched_paths: list[str] = []
        final_test_status = "patch_generation_failed"

        for attempt_index in range(attempt_limit + 1):
            if attempt_index > 0:
                restore_workspace_snapshot(
                    packet.working_directory,
                    baseline_snapshot,
                    extra_paths=last_touched_paths,
                )
                last_touched_paths = []
            attempt_packet = self._packet_for_mutation_attempt(
                packet,
                contract,
                attempt_index=attempt_index,
                failure_feedback=failure_feedback,
            )
            execution_result = adapter.launch(attempt_packet)
            last_result = execution_result
            patch_text = ""
            if execution_result.artifact_paths:
                patch_path = Path(execution_result.artifact_paths[0])
                if patch_path.exists():
                    patch_text = patch_path.read_text(encoding="utf-8")
            if execution_result.return_code != 0 and not patch_text.strip():
                failure_feedback = execution_result.stderr or execution_result.stdout or "patch generation failed"
                final_test_status = "patch_generation_failed"
                if attempt_index < attempt_limit:
                    continue
                break
            try:
                touched_paths = extract_touched_paths(patch_text, workspace_root=packet.working_directory)
            except ValueError as exc:
                failure_feedback = str(exc)
                final_test_status = "patch_parse_failed"
                if attempt_index < attempt_limit:
                    continue
                raise PatchApplyError(
                    "adapter did not return a valid unified diff patch",
                    {"reason": str(exc), "attempt_index": attempt_index},
                ) from exc
            rejected_paths = [path for path in touched_paths if not is_path_allowed(path, allowed_paths)]
            if rejected_paths:
                out_of_scope_rejections.extend(rejected_paths)
                failure_feedback = f"patch touched out-of-scope paths: {', '.join(rejected_paths)}"
                final_test_status = "patch_rejected"
                if attempt_index < attempt_limit:
                    continue
                raise RepoMutationScopeError(
                    "patch attempted to modify files outside the allowed write_set",
                    {
                        "rejected_paths": rejected_paths,
                        "allowed_paths": allowed_paths,
                    },
                )
            try:
                last_patch_hash = hash_patch_text(patch_text)
                last_touched_paths = apply_unified_diff(
                    packet.working_directory,
                    patch_text,
                    allowed_paths=allowed_paths,
                )
            except ValueError as exc:
                failure_feedback = str(exc)
                final_test_status = "patch_apply_failed"
                if attempt_index < attempt_limit:
                    continue
                raise PatchApplyError(
                    "failed to apply the generated unified diff patch",
                    {"reason": str(exc), "attempt_index": attempt_index},
                ) from exc
            command_attempts = []
            if contract.test_commands:
                command_attempts = run_test_commands(contract.test_commands, working_directory=packet.working_directory)
                for command_attempt in command_attempts:
                    aggregated_test_attempts.append({"iteration": attempt_index, **command_attempt})
            if command_attempts and any(not bool(item["passed"]) for item in command_attempts):
                failure_feedback = self._merge_test_feedback(command_attempts)
                final_test_status = "failed"
                if attempt_index < attempt_limit:
                    continue
                restore_workspace_snapshot(
                    packet.working_directory,
                    baseline_snapshot,
                    extra_paths=last_touched_paths,
                )
                break
            final_test_status = "passed" if contract.test_commands else "not_requested"
            mutation_result = RepoMutationResult(
                changed_files=sorted(set(last_touched_paths)),
                applied_patch_hash=last_patch_hash,
                out_of_scope_rejections=sorted(set(out_of_scope_rejections)),
                test_attempts=aggregated_test_attempts,
                fix_iteration_count=attempt_index,
                final_test_status=final_test_status,
            )
            return ExecutionResult(
                runtime_task_id=execution_result.runtime_task_id,
                return_code=0,
                stdout=execution_result.stdout,
                stderr=execution_result.stderr,
                started_at=execution_result.started_at,
                finished_at=execution_result.finished_at,
                duration_ms=execution_result.duration_ms,
                artifact_paths=execution_result.artifact_paths,
                adapter_name=execution_result.adapter_name,
                metadata={
                    **execution_result.metadata,
                    "mutation_contract": contract.model_dump(mode="json"),
                    "mutation_result": mutation_result.model_dump(mode="json"),
                },
            )

        failed_result = last_result or adapter.launch(packet)
        mutation_result = RepoMutationResult(
            changed_files=[],
            applied_patch_hash=last_patch_hash,
            out_of_scope_rejections=sorted(set(out_of_scope_rejections)),
            test_attempts=aggregated_test_attempts,
            fix_iteration_count=attempt_limit,
            final_test_status=final_test_status,
        )
        return ExecutionResult(
            runtime_task_id=failed_result.runtime_task_id,
            return_code=failed_result.return_code or 1,
            stdout=failed_result.stdout,
            stderr=failed_result.stderr or failure_feedback or "repo mutation failed",
            started_at=failed_result.started_at,
            finished_at=failed_result.finished_at,
            duration_ms=failed_result.duration_ms,
            artifact_paths=failed_result.artifact_paths,
            adapter_name=failed_result.adapter_name,
            metadata={
                **failed_result.metadata,
                "mutation_contract": contract.model_dump(mode="json"),
                "mutation_result": mutation_result.model_dump(mode="json"),
            },
        )

    def _execute_project_delivery_orchestration(self, packet: TaskPacket) -> ExecutionResult:
        return self.orchestration_service.execute_orchestration_packet(packet)

    def _agent_profile_definition(self, agent_profile_id: str | None):
        if not agent_profile_id:
            return None
        return next((profile for profile in self.list_agent_profiles() if profile.profile_id == agent_profile_id), None)

    def _cluster_template_definition(self, cluster_template_id: str | None):
        if not cluster_template_id:
            return None
        return next((template for template in self.list_cluster_templates() if template.template_id == cluster_template_id), None)

    def _cluster_member_definition(
        self,
        cluster_template_id: str | None,
        cluster_member_id: str | None,
    ):
        template = self._cluster_template_definition(cluster_template_id)
        if template is None or not cluster_member_id:
            return None
        return next((member for member in template.member_specs if member.member_id == cluster_member_id), None)

    def _execution_override_profile(
        self,
        *,
        adapter_name: str | None = None,
        agent_model: str | None = None,
        codex_model: str | None = None,
        opencode_model: str | None = None,
        opencode_variant: str | None = None,
        runtime_gateway_provider: str | None = None,
        runtime_gateway_model: str | None = None,
        runtime_reasoning_effort: str | None = None,
        worker_pool_id: str | None = None,
    ) -> ExecutionProfileDefinition | None:
        payload = {
            "adapter_name": adapter_name,
            "agent_model": agent_model,
            "codex_model": codex_model,
            "opencode_model": opencode_model,
            "opencode_variant": opencode_variant,
            "runtime_gateway_provider": runtime_gateway_provider,
            "runtime_gateway_model": runtime_gateway_model,
            "runtime_reasoning_effort": runtime_reasoning_effort,
            "worker_pool_id": worker_pool_id,
        }
        if not any(value is not None for value in payload.values()):
            return None
        return ExecutionProfileDefinition(**payload)

    def _router_default_adapter_for_task_kind(self, task_kind: TaskKind | str) -> str | None:
        route = self.worker_router.describe(str(task_kind), adapter_name=None)
        if route is None:
            return None
        return str(route.get("adapter_name") or "") or None

    def _resolve_execution_profile_for_run(
        self,
        *,
        preset: PresetDefinition,
        task_kind: TaskKind,
        domain_pack: DomainPackResolution | None,
        mutation_contract: MutationContract | None = None,
        requested_adapter: str | None = None,
        requested_agent_model: str | None = None,
        requested_codex_model: str | None = None,
        requested_opencode_model: str | None = None,
        requested_opencode_variant: str | None = None,
        requested_runtime_gateway_provider: str | None = None,
        requested_runtime_gateway_model: str | None = None,
        requested_runtime_reasoning_effort: str | None = None,
        requested_worker_pool_id: str | None = None,
        agent_profile_id: str | None = None,
        cluster_template_id: str | None = None,
        cluster_member_id: str | None = None,
        public_role: AgentRoleType | str | None = None,
        role_label: str | None = None,
    ) -> ResolvedExecutionProfile:
        cluster_member = self._cluster_member_definition(cluster_template_id, cluster_member_id)
        template = self._cluster_template_definition(cluster_template_id)
        resolved_agent_profile_id = (
            agent_profile_id
            or (cluster_member.agent_profile_id if cluster_member is not None and cluster_member.agent_profile_id else None)
        )
        agent_profile = self._agent_profile_definition(resolved_agent_profile_id)
        scope_context = ExecutionScopeContext(
            preset_id=preset.preset_id,
            agent_profile_id=resolved_agent_profile_id,
            cluster_template_id=cluster_template_id,
            cluster_member_id=cluster_member_id,
            public_role=public_role,
            role_label=role_label,
        )
        resolved = resolve_execution_profile(
            effective_config=self.effective_config,
            explicit_profile=self._execution_override_profile(
                adapter_name=requested_adapter,
                agent_model=requested_agent_model,
                codex_model=requested_codex_model,
                opencode_model=requested_opencode_model,
                opencode_variant=requested_opencode_variant,
                runtime_gateway_provider=requested_runtime_gateway_provider,
                runtime_gateway_model=requested_runtime_gateway_model,
                runtime_reasoning_effort=requested_runtime_reasoning_effort,
                worker_pool_id=requested_worker_pool_id,
            ),
            cluster_member_profile=cluster_member.execution_profile if cluster_member is not None else None,
            agent_profile=agent_profile.execution_profile if agent_profile is not None else None,
            preset_profile=preset.execution_profile,
            cluster_template_profile=template.default_execution_profile if template is not None else None,
            compatibility_adapter=self._default_adapter_for_preset(preset, task_kind, domain_pack),
            routing_default_adapter=self._router_default_adapter_for_task_kind(task_kind),
            scope_context=scope_context,
        )
        selected_adapter = resolved.adapter_name
        if (
            selected_adapter is not None
            and self._capability_route_for(task_kind, adapter_name=selected_adapter) is None
            and resolved.source_map.get("adapter_name", {}).get("scope") != "explicit_invocation"
        ):
            fallback_adapter = self._router_default_adapter_for_task_kind(task_kind)
            selected_model = None
            selected_model_kind = None
            model_variant = None
            if fallback_adapter == "agent":
                selected_model = resolved.agent_model
                selected_model_kind = "agent_model"
            elif fallback_adapter == "codex":
                selected_model = resolved.codex_model
                selected_model_kind = "codex_model"
            elif fallback_adapter in {"opencode", "opencode_session"}:
                selected_model = resolved.opencode_model
                selected_model_kind = "opencode_model"
                model_variant = resolved.opencode_variant
            source_map = dict(resolved.source_map)
            source_map["adapter_name"] = {
                "scope": "compatibility_fallback",
                "source": "worker_router_default",
                "value": fallback_adapter,
            }
            resolved = ResolvedExecutionProfile.model_validate(
                {
                    **resolved.model_dump(mode="json"),
                    "adapter_name": fallback_adapter,
                    "selected_model": selected_model,
                    "selected_model_kind": selected_model_kind,
                    "model_variant": model_variant,
                    "compatibility_fallback": "worker_router_default",
                    "source_map": source_map,
                }
            )
        lane = self._resolve_execution_lane(
            preset=preset,
            task_kind=task_kind,
            selected_adapter=resolved.adapter_name,
            mutation_contract=mutation_contract,
        )
        source_map = dict(resolved.source_map)
        source_map["execution_lane"] = {
            "scope": "derived_lane_rules",
            "source": "execution_lane_resolution",
            "value": str(lane),
        }
        return ResolvedExecutionProfile.model_validate(
            {
                **resolved.model_dump(mode="json"),
                "execution_lane": str(lane),
                "source_map": source_map,
            }
        )

    def _adapter_supports_mutation_mode(self, adapter_name: str | None, mode: MutationMode | str) -> bool:
        if not adapter_name:
            return False
        adapter = self._capability_route_for(TaskKind.shell_exec, adapter_name=adapter_name)
        if adapter is None:
            return False
        route = self.worker_router.route(
            TaskPacket(
                runtime_task_id="mutation_probe",
                run_id="mutation_probe",
                task_kind=TaskKind.shell_exec,
                command=[],
                working_directory=".",
                env={"WORKFLOW_CAPABILITY_ADAPTER": adapter_name},
            )
        )
        return route.supports_mutation_mode(mode)

    def _default_adapter_for_preset(
        self,
        preset: PresetDefinition,
        resolved_task_kind: TaskKind,
        domain_pack: DomainPackResolution | None,
    ) -> str | None:
        if domain_pack is not None and domain_pack.capability_exposure.preferred_adapter_name is not None:
            return domain_pack.capability_exposure.preferred_adapter_name
        if (
            preset.preset_id == "research_spike_reviewable"
            and is_agent_lane_enabled()
            and self.worker_router.describe(str(resolved_task_kind), adapter_name="agent") is not None
        ):
            return "agent"
        return None

    def _resolve_execution_lane(
        self,
        *,
        preset: PresetDefinition,
        task_kind: TaskKind,
        selected_adapter: str | None,
        mutation_contract: MutationContract | None = None,
    ) -> ExecutionLaneType:
        if mutation_contract is not None and mutation_contract.mutation_mode == MutationMode.patch_apply:
            return ExecutionLaneType.repo_change_controlled
        if selected_adapter == "opencode_session":
            if preset.preset_id == "feature_delivery":
                raise ExecutionLaneNotAllowedError(
                    preset.preset_id,
                    ExecutionLaneType.sessionful_external_agent,
                    [ExecutionLaneType.native_deterministic, ExecutionLaneType.repo_change_controlled],
                )
            return ExecutionLaneType.sessionful_external_agent
        if preset.preset_id == "feature_delivery":
            if selected_adapter == "agent":
                raise ExecutionLaneNotAllowedError(
                    preset.preset_id,
                    ExecutionLaneType.standard_agent,
                    [ExecutionLaneType.native_deterministic],
                )
            return ExecutionLaneType.native_deterministic
        if selected_adapter == "agent":
            if preset.preset_id == "research_spike_reviewable" and is_durable_pilot_enabled():
                return ExecutionLaneType.durable_incremental
            return ExecutionLaneType.standard_agent
        return ExecutionLaneType.native_deterministic

    def _build_tool_projection_manifest(
        self,
        *,
        run: Run,
        preset: PresetDefinition,
        task_kind: TaskKind,
        lane_type: ExecutionLaneType,
        domain_pack: DomainPackResolution | None,
    ) -> tuple[ToolProjectionManifest | None, list[MCPServerProfile]]:
        manifest, profiles = self.capability_plane.build_projection_manifest(
            run_id=run.run_id,
            preset_id=preset.preset_id,
            task_kind=task_kind,
            review_policy=ReviewPolicy(preset.default_review_policy),
            lane_type=lane_type,
            domain_pack_id=domain_pack.domain_pack_id if domain_pack is not None else None,
            include_mcp=is_mcp_source_enabled(),
        )
        return (manifest, profiles) if manifest.tools or lane_type != ExecutionLaneType.native_deterministic else (manifest, profiles)

    def _durable_refs_for_state(self, state_ref: RuntimeStateRef | None) -> dict[str, str]:
        if state_ref is None:
            return {}
        durable_runtime = state_ref.state_payload.get("durable_runtime")
        if isinstance(durable_runtime, dict):
            current_refs = durable_runtime.get("current_refs")
            if isinstance(current_refs, dict):
                refs = {
                    "thread_id": current_refs.get("thread_id"),
                    "checkpoint_id": current_refs.get("checkpoint_id"),
                    "assistant_id": current_refs.get("assistant_id"),
                }
                filtered = {key: value for key, value in refs.items() if value}
                if filtered:
                    return filtered
        refs = {
            "thread_id": state_ref.state_payload.get("thread_id"),
            "checkpoint_id": state_ref.state_payload.get("checkpoint_id"),
            "assistant_id": state_ref.state_payload.get("assistant_id"),
        }
        return {key: value for key, value in refs.items() if value}

    def _durable_lineage_for_state(self, state_ref: RuntimeStateRef | None) -> dict[str, Any] | None:
        refs = self._durable_refs_for_state(state_ref)
        if state_ref is None:
            return None
        durable_runtime = state_ref.state_payload.get("durable_runtime")
        if isinstance(durable_runtime, dict):
            history = durable_runtime.get("history")
            normalized_history = [dict(item) for item in history] if isinstance(history, list) else []
            return {
                "current_refs": refs,
                "history": normalized_history,
                "transition_count": len(normalized_history),
                "checkpoint_count": int(durable_runtime.get("checkpoint_count") or 0),
                "review_decision_count": int(durable_runtime.get("review_decision_count") or 0),
                "latest_reason": durable_runtime.get("latest_reason"),
                "latest_transition_at": durable_runtime.get("latest_transition_at"),
            }
        if not refs:
            return None
        return {
            "current_refs": refs,
            "history": [],
            "transition_count": 0,
            "checkpoint_count": 0,
            "review_decision_count": 0,
            "latest_reason": None,
            "latest_transition_at": None,
        }

    def _state_ref_with_durable_transition(
        self,
        state_ref: RuntimeStateRef,
        *,
        reason: str,
        refs: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeStateRef:
        previous_lineage = self._durable_lineage_for_state(state_ref)
        previous_refs = previous_lineage["current_refs"] if previous_lineage is not None else {}
        resolved_refs = {
            key: value
            for key, value in (refs or previous_refs).items()
            if key in {"thread_id", "checkpoint_id", "assistant_id"} and value
        }
        if not resolved_refs and previous_lineage is None:
            return state_ref
        history = list(previous_lineage["history"]) if previous_lineage is not None else []
        transition = {
            "index": len(history) + 1,
            "reason": reason,
            "graph_step": str(state_ref.graph_step),
            "is_terminal": state_ref.is_terminal,
            "at": state_ref.updated_at.isoformat(),
            "refs": resolved_refs,
        }
        if metadata:
            transition["metadata"] = dict(metadata)
        history.append(transition)
        checkpoint_count = (previous_lineage["checkpoint_count"] if previous_lineage is not None else 0) + (
            1 if resolved_refs.get("checkpoint_id") and resolved_refs.get("checkpoint_id") != previous_refs.get("checkpoint_id") else 0
        )
        review_decision_count = (previous_lineage["review_decision_count"] if previous_lineage is not None else 0) + (
            1 if metadata is not None and metadata.get("review_decision") is not None else 0
        )
        return self._state_ref_with_payload_updates(
            state_ref,
            {
                **resolved_refs,
                "durable_runtime": {
                    "current_refs": resolved_refs,
                    "history": history,
                    "transition_count": len(history),
                    "checkpoint_count": checkpoint_count,
                    "review_decision_count": review_decision_count,
                    "latest_reason": reason,
                    "latest_transition_at": state_ref.updated_at.isoformat(),
                },
            },
        )

    def _state_ref_with_payload_updates(
        self,
        state_ref: RuntimeStateRef,
        payload_updates: dict[str, Any],
    ) -> RuntimeStateRef:
        return RuntimeStateRef.model_validate(
            {
                **state_ref.model_dump(mode="json"),
                "state_payload": {
                    **state_ref.state_payload,
                    **payload_updates,
                },
            }
        )

    def _state_ref_with_m8_context(
        self,
        state_ref: RuntimeStateRef,
        snapshot: CompileSnapshot,
    ) -> RuntimeStateRef:
        payload_updates: dict[str, Any] = {
            "execution_lane": str(snapshot.execution_lane),
            "tool_projection_manifest": (
                snapshot.tool_projection_manifest.model_dump(mode="json")
                if snapshot.tool_projection_manifest is not None
                else None
            ),
            "mcp_server_profiles": [profile.model_dump(mode="json") for profile in snapshot.mcp_server_profiles],
            "feature_flags": self._feature_flags(),
        }
        worker_pool_id = snapshot.task_packet.env.get("WORKFLOW_WORKER_POOL_ID")
        if worker_pool_id:
            payload_updates["execution_target"] = {
                "target_kind": "external_worker_pool",
                "worker_pool_id": worker_pool_id,
                "dispatch_mode": "loopback",
                "adapter_name": snapshot.task_packet.env.get("WORKFLOW_CAPABILITY_ADAPTER") or None,
            }
        orchestration_payload = snapshot.task_packet.env.get("WORKFLOW_ORCHESTRATION_PLAN")
        if orchestration_payload:
            payload_updates["orchestration"] = json.loads(orchestration_payload)
        durable_refs: dict[str, str] = {}
        if snapshot.execution_lane == ExecutionLaneType.durable_incremental:
            durable_refs = self.durable_runtime_pilot.start(state_ref.run_id, state_ref.runtime_task_id)
            payload_updates.update(durable_refs)
        updated_state = self._state_ref_with_payload_updates(state_ref, payload_updates)
        if snapshot.execution_lane == ExecutionLaneType.durable_incremental:
            updated_state = self._state_ref_with_durable_transition(
                updated_state,
                reason="start",
                refs=durable_refs,
                metadata={
                    "execution_lane": str(snapshot.execution_lane),
                    "phase": "compile",
                },
            )
        return updated_state

    def _export_trace(
        self,
        *,
        run_id: str,
        name: str,
        lane_type: ExecutionLaneType | str,
        status: str,
        attributes: dict[str, Any],
    ) -> str | None:
        try:
            return self.trace_exporter.export(
                TraceRecord(
                    run_id=run_id,
                    name=name,
                    lane_type=str(lane_type),
                    status=status,
                    attributes=attributes,
                )
            )
        except Exception:
            return None

    def _remaining_retries(self, ledger: BudgetLedger | None) -> int | None:
        if ledger is None:
            return None
        return max(ledger.max_retries - ledger.recompile_count, 0)

    def _budget_projection(self, ledger: BudgetLedger | None) -> dict[str, Any] | None:
        if ledger is None:
            return None
        return {
            "max_retries": ledger.max_retries,
            "remaining_retries": self._remaining_retries(ledger),
            "timeout_seconds": ledger.timeout_seconds,
            "compile_count": ledger.compile_count,
            "recompile_count": ledger.recompile_count,
            "execution_count": ledger.execution_count,
            "total_runtime_ms": ledger.total_runtime_ms,
            "last_return_code": ledger.last_return_code,
            "updated_at": ledger.updated_at.isoformat(),
        }

    def _ensure_budget_ledger(
        self,
        run: Run,
        preset: PresetDefinition,
        *,
        connection=None,
        compile_count: int = 0,
    ) -> BudgetLedger:
        ledger = self.budget_repo.get_by_run(run.run_id, connection=connection)
        if ledger is not None:
            return ledger
        ledger = BudgetLedger(
            run_id=run.run_id,
            preset_id=preset.preset_id,
            max_retries=preset.default_budget_policy.max_retries,
            timeout_seconds=preset.default_budget_policy.timeout_seconds,
            compile_count=compile_count,
        )
        self.budget_repo.create(ledger, connection=connection)
        return ledger

    def _lease_expires_at(self) -> datetime:
        return self._utc_now() + timedelta(seconds=self.CLAIM_LEASE_SECONDS)

    def _worker_lease_expires_at(self) -> datetime:
        return self._utc_now() + timedelta(seconds=self.WORKER_LEASE_SECONDS)

    def _load_run_context(self, run_id: str, *, connection=None) -> RunDiagnosticContext:
        run = self.run_repo.get(run_id, connection=connection)
        if run is None:
            raise EntityNotFoundError("run", run_id)
        preset = self.preset_repo.get(run.preset_id, connection=connection)
        phases = self.task_repo.list_phases_for_run(run_id, connection=connection)
        task_cards = self.task_repo.list_task_cards_for_run(run_id, connection=connection)
        runtime_tasks = self.task_repo.list_runtime_tasks_for_run(run_id, connection=connection)
        handoffs = self.handoff_repo.list_for_run(run_id, connection=connection)
        runtime_state_refs = self.runtime_state_repo.list_for_run(run_id, connection=connection)
        snapshots = self.snapshot_repo.list_for_run(run_id, connection=connection)
        runtime_attempts = self.runtime_attempt_repo.list_for_run(run_id, connection=connection)
        claims = self.runtime_claim_repo.list_for_run(run_id, connection=connection)
        worker_leases = self.worker_lease_repo.list_for_run(run_id, connection=connection)
        latest_review_verdict = self.review_repo.latest_for_run(run_id, connection=connection)
        evidence_by_task = {
            task.runtime_task_id: self.evidence_repo.get_by_task(task.runtime_task_id, connection=connection)
            for task in runtime_tasks
        }
        return RunDiagnosticContext(
            run=run,
            preset=preset,
            phases=phases,
            task_cards=task_cards,
            runtime_tasks=runtime_tasks,
            handoffs=handoffs,
            runtime_state_refs=runtime_state_refs,
            snapshots=snapshots,
            runtime_attempts=runtime_attempts,
            claims=claims,
            worker_leases=worker_leases,
            evidence_by_task=evidence_by_task,
            latest_review_verdict=latest_review_verdict,
        )

    def _last_runtime_state(self, context: RunDiagnosticContext) -> RuntimeStateRef | None:
        if not context.runtime_state_refs:
            return None
        return max(context.runtime_state_refs, key=lambda state_ref: (state_ref.updated_at, state_ref.state_ref_id))

    def _last_evidence(self, context: RunDiagnosticContext) -> Evidence | None:
        evidences = [evidence for evidence in context.evidence_by_task.values() if evidence is not None]
        if not evidences:
            return None
        return max(evidences, key=lambda evidence: (evidence.created_at, evidence.evidence_id))

    def _last_claim(self, context: RunDiagnosticContext) -> RuntimeClaim | None:
        if not context.claims:
            return None
        return max(context.claims, key=lambda claim: (claim.created_at, claim.claim_id))

    def _last_snapshot(self, context: RunDiagnosticContext) -> RunSnapshot | None:
        if not context.snapshots:
            return None
        return max(context.snapshots, key=lambda snapshot: (snapshot.created_at, snapshot.snapshot_id))

    def _last_attempt(self, context: RunDiagnosticContext) -> RuntimeAttempt | None:
        if not context.runtime_attempts:
            return None
        return max(context.runtime_attempts, key=lambda attempt: (attempt.sequence_no, attempt.created_at, attempt.attempt_id))

    def _current_attempt(self, context: RunDiagnosticContext) -> RuntimeAttempt | None:
        current_attempts = [
            attempt for attempt in context.runtime_attempts if str(attempt.status) == RuntimeAttemptStatus.current
        ]
        if not current_attempts:
            return None
        return max(current_attempts, key=lambda attempt: (attempt.sequence_no, attempt.created_at, attempt.attempt_id))

    def _superseded_attempts(self, context: RunDiagnosticContext) -> list[RuntimeAttempt]:
        return [attempt for attempt in context.runtime_attempts if str(attempt.status) == RuntimeAttemptStatus.superseded]

    def _last_worker_lease(self, context: RunDiagnosticContext) -> WorkerLease | None:
        if not context.worker_leases:
            return None
        return max(context.worker_leases, key=lambda lease: (lease.created_at, lease.lease_id))

    def _active_claims_for(self, context: RunDiagnosticContext) -> list[RuntimeClaim]:
        return [claim for claim in context.claims if str(claim.status) == RuntimeClaimStatus.active]

    def _expired_active_claims(self, context: RunDiagnosticContext) -> list[RuntimeClaim]:
        now = self._utc_now()
        return [claim for claim in self._active_claims_for(context) if claim.lease_expires_at <= now]

    def _active_worker_leases_for(self, context: RunDiagnosticContext) -> list[WorkerLease]:
        return [lease for lease in context.worker_leases if str(lease.status) == WorkerLeaseStatus.active]

    def _expired_active_worker_leases(self, context: RunDiagnosticContext) -> list[WorkerLease]:
        now = self._utc_now()
        return [lease for lease in self._active_worker_leases_for(context) if lease.lease_expires_at <= now]

    def _acquire_runtime_claim(
        self,
        run_id: str,
        runtime_task_id: str,
        *,
        connection=None,
        owner: str = "local_orchestrator",
        owner_kind: OwnershipActorKind | str = OwnershipActorKind.control_plane,
        owner_id: str = "control_plane_local",
        domain_kind: OwnershipDomainKind | str = OwnershipDomainKind.runtime_task,
        domain_key: str | None = None,
        attempt_id: str | None = None,
    ) -> RuntimeClaim:
        active_claim = self.runtime_claim_repo.get_active_for_task(runtime_task_id, connection=connection)
        if active_claim is not None:
            raise RuntimeClaimConflictError(
                runtime_task_id,
                active_claim.claim_id,
                active_claim.lease_expires_at.isoformat(),
            )
        resolved_domain_kind, resolved_domain_key = self._ownership_domain_for(
            runtime_task_id,
            domain_kind=domain_kind,
            domain_key=domain_key,
        )
        claim = RuntimeClaim(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            owner=owner,
            owner_kind=OwnershipActorKind(owner_kind),
            owner_id=owner_id,
            domain_kind=OwnershipDomainKind(resolved_domain_kind),
            domain_key=resolved_domain_key,
            attempt_id=attempt_id,
            lease_expires_at=self._lease_expires_at(),
        )
        self.runtime_claim_repo.create(claim, connection=connection)
        self.event_repo.append(
            RunEvent(
                run_id=run_id,
                event_type=RunEventType.claim_acquired,
                object_type="runtime_claim",
                object_id=claim.claim_id,
                summary="Runtime claim acquired",
                payload_json={
                    "run_id": run_id,
                    "runtime_task_id": runtime_task_id,
                    "claim_id": claim.claim_id,
                    "owner": claim.owner,
                    "owner_kind": claim.owner_kind,
                    "owner_id": claim.owner_id,
                    "domain_kind": claim.domain_kind,
                    "domain_key": claim.domain_key,
                    "attempt_id": claim.attempt_id,
                    "lease_expires_at": claim.lease_expires_at.isoformat(),
                },
            ),
            connection=connection,
        )
        return claim

    def _release_runtime_claim(
        self,
        claim: RuntimeClaim,
        *,
        status: RuntimeClaimStatus | str,
        reason: str,
        connection=None,
    ) -> RuntimeClaim:
        released = self.runtime_claim_repo.release(
            claim.claim_id,
            released_at=self._utc_now().isoformat(),
            release_reason=reason,
            status=str(status),
            connection=connection,
        )
        assert released is not None
        self.event_repo.append(
            RunEvent(
                run_id=claim.run_id,
                event_type=RunEventType.claim_released,
                object_type="runtime_claim",
                object_id=claim.claim_id,
                summary=f"Runtime claim {status}",
                payload_json={
                    "run_id": claim.run_id,
                    "runtime_task_id": claim.runtime_task_id,
                    "claim_id": claim.claim_id,
                    "status": str(status),
                    "reason": reason,
                },
            ),
            connection=connection,
        )
        return released

    def _release_active_claims_for_run(
        self,
        run_id: str,
        *,
        status: RuntimeClaimStatus | str,
        reason: str,
        connection=None,
    ) -> list[RuntimeClaim]:
        active_claims = self.runtime_claim_repo.list_active_for_run(run_id, connection=connection)
        released_claims: list[RuntimeClaim] = []
        for claim in active_claims:
            released_claims.append(
                self._release_runtime_claim(
                    claim,
                    status=status,
                    reason=reason,
                    connection=connection,
                )
            )
        return released_claims

    def _acquire_worker_lease(
        self,
        run_id: str,
        runtime_task_id: str,
        *,
        adapter_name: str,
        connection=None,
        worker_name: str = "local_worker",
        worker_kind: OwnershipActorKind | str = OwnershipActorKind.worker,
        worker_id: str = "worker_local",
        domain_kind: OwnershipDomainKind | str = OwnershipDomainKind.runtime_task,
        domain_key: str | None = None,
        claim_id: str | None = None,
        attempt_id: str | None = None,
    ) -> WorkerLease:
        resolved_domain_kind, resolved_domain_key = self._ownership_domain_for(
            runtime_task_id,
            domain_kind=domain_kind,
            domain_key=domain_key,
        )
        lease = WorkerLease(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            worker_name=worker_name,
            worker_kind=OwnershipActorKind(worker_kind),
            worker_id=worker_id,
            domain_kind=OwnershipDomainKind(resolved_domain_kind),
            domain_key=resolved_domain_key,
            claim_id=claim_id,
            attempt_id=attempt_id,
            adapter_name=adapter_name,
            heartbeat_at=self._utc_now(),
            lease_expires_at=self._worker_lease_expires_at(),
        )
        self.worker_lease_repo.create(lease, connection=connection)
        self.event_repo.append(
            RunEvent(
                run_id=run_id,
                event_type=RunEventType.worker_lease_acquired,
                object_type="worker_lease",
                object_id=lease.lease_id,
                summary="Worker lease acquired",
                payload_json={
                    "run_id": run_id,
                    "runtime_task_id": runtime_task_id,
                    "lease_id": lease.lease_id,
                    "worker_name": lease.worker_name,
                    "worker_kind": lease.worker_kind,
                    "worker_id": lease.worker_id,
                    "domain_kind": lease.domain_kind,
                    "domain_key": lease.domain_key,
                    "claim_id": lease.claim_id,
                    "attempt_id": lease.attempt_id,
                    "adapter_name": lease.adapter_name,
                    "heartbeat_at": lease.heartbeat_at.isoformat(),
                    "lease_expires_at": lease.lease_expires_at.isoformat(),
                },
            ),
            connection=connection,
        )
        return lease

    def _ownership_topology_projection(
        self,
        latest_claim: RuntimeClaim | None,
        latest_worker_lease: WorkerLease | None,
        current_attempt: RuntimeAttempt | None,
    ) -> dict[str, Any]:
        claim_projection = (
            {
                "claim_id": latest_claim.claim_id,
                "owner": latest_claim.owner,
                "owner_kind": str(latest_claim.owner_kind),
                "owner_id": latest_claim.owner_id,
                "domain_kind": str(latest_claim.domain_kind),
                "domain_key": latest_claim.domain_key,
                "attempt_id": latest_claim.attempt_id,
                "status": str(latest_claim.status),
            }
            if latest_claim is not None
            else None
        )
        worker_projection = (
            {
                "lease_id": latest_worker_lease.lease_id,
                "worker_name": latest_worker_lease.worker_name,
                "worker_kind": str(latest_worker_lease.worker_kind),
                "worker_id": latest_worker_lease.worker_id,
                "adapter_name": latest_worker_lease.adapter_name,
                "domain_kind": str(latest_worker_lease.domain_kind),
                "domain_key": latest_worker_lease.domain_key,
                "claim_id": latest_worker_lease.claim_id,
                "attempt_id": latest_worker_lease.attempt_id,
                "status": str(latest_worker_lease.status),
            }
            if latest_worker_lease is not None
            else None
        )
        topology_aligned = (
            latest_claim is not None
            and latest_worker_lease is not None
            and str(latest_claim.domain_kind) == str(latest_worker_lease.domain_kind)
            and latest_claim.domain_key == latest_worker_lease.domain_key
            and latest_worker_lease.claim_id == latest_claim.claim_id
        )
        attempt_aligned = (
            current_attempt is not None
            and latest_claim is not None
            and latest_worker_lease is not None
            and latest_claim.attempt_id == current_attempt.attempt_id
            and latest_worker_lease.attempt_id == current_attempt.attempt_id
        )
        return {
            "claim": claim_projection,
            "worker_lease": worker_projection,
            "current_attempt_id": current_attempt.attempt_id if current_attempt is not None else None,
            "topology_aligned": topology_aligned,
            "attempt_aligned": attempt_aligned,
        }

    def _release_worker_lease(
        self,
        lease: WorkerLease,
        *,
        status: WorkerLeaseStatus | str,
        reason: str,
        connection=None,
    ) -> WorkerLease:
        released = self.worker_lease_repo.release(
            lease.lease_id,
            released_at=self._utc_now().isoformat(),
            release_reason=reason,
            status=str(status),
            connection=connection,
        )
        assert released is not None
        self.event_repo.append(
            RunEvent(
                run_id=lease.run_id,
                event_type=RunEventType.worker_lease_released,
                object_type="worker_lease",
                object_id=lease.lease_id,
                summary=f"Worker lease {status}",
                payload_json={
                    "run_id": lease.run_id,
                    "runtime_task_id": lease.runtime_task_id,
                    "lease_id": lease.lease_id,
                    "status": str(status),
                    "reason": reason,
                },
            ),
            connection=connection,
        )
        return released

    def _release_active_worker_leases_for_run(
        self,
        run_id: str,
        *,
        status: WorkerLeaseStatus | str,
        reason: str,
        connection=None,
    ) -> list[WorkerLease]:
        active_leases = self.worker_lease_repo.list_active_for_run(run_id, connection=connection)
        released_leases: list[WorkerLease] = []
        for lease in active_leases:
            released_leases.append(
                self._release_worker_lease(
                    lease,
                    status=status,
                    reason=reason,
                    connection=connection,
                )
            )
        return released_leases

    def _create_runtime_attempt(
        self,
        run_id: str,
        runtime_task_id: str,
        *,
        trigger: RuntimeAttemptTrigger | str,
        connection=None,
    ) -> RuntimeAttempt:
        attempt = RuntimeAttempt(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            sequence_no=self.runtime_attempt_repo.next_sequence_for_run(run_id, connection=connection),
            trigger=RuntimeAttemptTrigger(trigger),
        )
        self.runtime_attempt_repo.create(attempt, connection=connection)
        self.event_repo.append(
            RunEvent(
                run_id=run_id,
                event_type=RunEventType.runtime_attempt_created,
                object_type="runtime_attempt",
                object_id=attempt.attempt_id,
                summary="Runtime attempt created",
                payload_json={
                    "run_id": run_id,
                    "runtime_task_id": runtime_task_id,
                    "attempt_id": attempt.attempt_id,
                    "sequence_no": attempt.sequence_no,
                    "trigger": attempt.trigger,
                    "status": attempt.status,
                },
            ),
            connection=connection,
        )
        return attempt

    def _supersede_runtime_attempt(
        self,
        attempt: RuntimeAttempt,
        *,
        superseded_by_attempt_id: str,
        reason: str,
        connection=None,
    ) -> RuntimeAttempt:
        superseded = self.runtime_attempt_repo.supersede(
            attempt.attempt_id,
            superseded_by_attempt_id=superseded_by_attempt_id,
            superseded_at=self._utc_now().isoformat(),
            supersede_reason=reason,
            connection=connection,
        )
        assert superseded is not None
        self.event_repo.append(
            RunEvent(
                run_id=attempt.run_id,
                event_type=RunEventType.runtime_attempt_superseded,
                object_type="runtime_attempt",
                object_id=attempt.attempt_id,
                summary="Runtime attempt superseded",
                payload_json={
                    "run_id": attempt.run_id,
                    "runtime_task_id": attempt.runtime_task_id,
                    "attempt_id": attempt.attempt_id,
                    "superseded_by_attempt_id": superseded_by_attempt_id,
                    "reason": reason,
                },
            ),
            connection=connection,
        )
        return superseded

    def _close_runtime_attempt(
        self,
        attempt: RuntimeAttempt,
        *,
        status: RuntimeAttemptStatus | str,
        reason: str,
        connection=None,
    ) -> RuntimeAttempt:
        closed = self.runtime_attempt_repo.close(
            attempt.attempt_id,
            status=str(status),
            closed_at=self._utc_now().isoformat(),
            close_reason=reason,
            connection=connection,
        )
        assert closed is not None
        self.event_repo.append(
            RunEvent(
                run_id=attempt.run_id,
                event_type=RunEventType.runtime_attempt_closed,
                object_type="runtime_attempt",
                object_id=attempt.attempt_id,
                summary=f"Runtime attempt {status}",
                payload_json={
                    "run_id": attempt.run_id,
                    "runtime_task_id": attempt.runtime_task_id,
                    "attempt_id": attempt.attempt_id,
                    "status": str(status),
                    "reason": reason,
                },
            ),
            connection=connection,
        )
        return closed

    def _ensure_current_runtime_attempt(
        self,
        run_id: str,
        runtime_task_id: str,
        *,
        trigger: RuntimeAttemptTrigger | str,
        connection=None,
        reason_if_superseded: str = "runtime_task_changed",
        force_new: bool = False,
    ) -> RuntimeAttempt:
        current_attempt = self.runtime_attempt_repo.current_for_run(run_id, connection=connection)
        if not force_new and current_attempt is not None and current_attempt.runtime_task_id == runtime_task_id:
            return current_attempt
        next_attempt = RuntimeAttempt(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            sequence_no=self.runtime_attempt_repo.next_sequence_for_run(run_id, connection=connection),
            trigger=RuntimeAttemptTrigger(trigger),
        )
        if current_attempt is not None:
            self._supersede_runtime_attempt(
                current_attempt,
                superseded_by_attempt_id=next_attempt.attempt_id,
                reason=reason_if_superseded,
                connection=connection,
            )
        self.runtime_attempt_repo.create(next_attempt, connection=connection)
        self.event_repo.append(
            RunEvent(
                run_id=run_id,
                event_type=RunEventType.runtime_attempt_created,
                object_type="runtime_attempt",
                object_id=next_attempt.attempt_id,
                summary="Runtime attempt created",
                payload_json={
                    "run_id": run_id,
                    "runtime_task_id": runtime_task_id,
                    "attempt_id": next_attempt.attempt_id,
                    "sequence_no": next_attempt.sequence_no,
                    "trigger": next_attempt.trigger,
                    "status": next_attempt.status,
                },
            ),
            connection=connection,
        )
        return next_attempt

    def _inspection_problem(
        self,
        problem: str,
        reason: str,
        next_action: str,
        *,
        severity: str = "error",
        details: dict[str, Any] | None = None,
        repairable: bool = False,
        repair_action: str | None = None,
    ) -> dict[str, Any]:
        return {
            "problem": problem,
            "severity": severity,
            "reason": reason,
            "next_action": next_action,
            "repairable": repairable,
            "repair_action": repair_action,
            "details": details or {},
        }

    def _inspect_context(self, context: RunDiagnosticContext) -> list[dict[str, Any]]:
        problems: list[dict[str, Any]] = []
        non_terminal_states = self.runtime_state_repo.list_live_for_run(context.run.run_id)
        latest_attempt = self._last_attempt(context)
        current_attempt = self._current_attempt(context)
        last_runtime_state = self._last_runtime_state(context)
        current_runtime_task_ids = {task.runtime_task_id for task in context.runtime_tasks}
        active_claims = self._active_claims_for(context)
        expired_active_claims = self._expired_active_claims(context)
        active_worker_leases = self._active_worker_leases_for(context)
        expired_active_worker_leases = self._expired_active_worker_leases(context)
        scheduler_authority = self._scheduler_authority_payload(last_runtime_state)

        if (
            str(context.run.status) in {RunStatus.prepared, RunStatus.running, RunStatus.awaiting_review}
            and current_runtime_task_ids
            and current_attempt is None
        ):
            problems.append(
                self._inspection_problem(
                    "missing_current_runtime_attempt",
                    "run has active runtime task metadata but no current runtime attempt is recorded",
                    "create_repair_runtime_attempt",
                    repairable=True,
                    repair_action="create_repair_runtime_attempt",
                    details={
                        "run_status": str(context.run.status),
                        "runtime_task_ids": sorted(current_runtime_task_ids),
                        "latest_attempt_id": latest_attempt.attempt_id if latest_attempt is not None else None,
                    },
                )
            )

        if current_attempt is not None and current_attempt.runtime_task_id not in current_runtime_task_ids:
            problems.append(
                self._inspection_problem(
                    "current_runtime_attempt_task_missing",
                    "current runtime attempt points to a runtime task that is no longer present in the live run context",
                    "interrupt_current_runtime_attempt",
                    repairable=True,
                    repair_action="interrupt_current_runtime_attempt",
                    details={
                        "attempt_id": current_attempt.attempt_id,
                        "runtime_task_id": current_attempt.runtime_task_id,
                        "run_runtime_task_ids": sorted(current_runtime_task_ids),
                    },
                )
            )

        if str(context.run.status) == RunStatus.completed and non_terminal_states:
            state_ref = non_terminal_states[0]
            problems.append(
                self._inspection_problem(
                    "completed_runtime_non_terminal",
                    "run is marked completed but runtime state is still non-terminal",
                    "reconcile_runtime_state_ref",
                    repairable=True,
                    repair_action="align_completed_runtime_state",
                    details={
                        "runtime_task_id": state_ref.runtime_task_id,
                        "graph_step": state_ref.graph_step,
                        "state_ref_id": state_ref.state_ref_id,
                    },
                )
            )

        if (
            str(context.run.status) in {RunStatus.completed, RunStatus.failed, RunStatus.cancelled}
            and current_attempt is not None
        ):
            problems.append(
                self._inspection_problem(
                    "terminal_run_has_current_runtime_attempt",
                    "run is terminal but runtime attempt lineage still records a current attempt",
                    "close_current_runtime_attempt_terminal",
                    repairable=True,
                    repair_action="close_current_runtime_attempt_terminal",
                    details={
                        "attempt_id": current_attempt.attempt_id,
                        "run_status": str(context.run.status),
                        "runtime_task_id": current_attempt.runtime_task_id,
                    },
                )
            )

        if str(context.run.status) == RunStatus.awaiting_review:
            has_evidence = any(evidence is not None for evidence in context.evidence_by_task.values())
            if not has_evidence:
                problems.append(
                self._inspection_problem(
                    "awaiting_review_missing_evidence",
                    "run is awaiting human review but no evidence exists for its runtime task",
                    "rebuild_or_replay_evidence",
                    repairable=False,
                    repair_action=None,
                    details={"runtime_task_ids": [task.runtime_task_id for task in context.runtime_tasks]},
                )
            )

        if current_attempt is not None and (expired_active_claims or expired_active_worker_leases):
            problems.append(
                self._inspection_problem(
                    "current_runtime_attempt_interrupted",
                    "current runtime attempt still exists while its claim or worker lease has already expired",
                    "interrupt_current_runtime_attempt",
                    repairable=True,
                    repair_action="interrupt_current_runtime_attempt",
                    details={
                        "attempt_id": current_attempt.attempt_id,
                        "expired_claim_ids": [claim.claim_id for claim in expired_active_claims],
                        "expired_worker_lease_ids": [lease.lease_id for lease in expired_active_worker_leases],
                    },
                )
            )

        if str(context.run.status) == RunStatus.cancelled and non_terminal_states:
            state_ref = non_terminal_states[0]
            problems.append(
                self._inspection_problem(
                    "cancelled_with_live_runtime",
                    "run is cancelled but at least one runtime state is still live",
                    "terminate_or_reconcile_runtime",
                    repairable=True,
                    repair_action="align_cancelled_runtime_state",
                    details={
                        "runtime_task_id": state_ref.runtime_task_id,
                        "graph_step": state_ref.graph_step,
                        "state_ref_id": state_ref.state_ref_id,
                    },
                )
            )

        if expired_active_claims:
            problems.append(
                self._inspection_problem(
                    "runtime_claim_expired",
                    "run still has active claims whose lease has already expired",
                    "expire_runtime_claim",
                    repairable=True,
                    repair_action="expire_runtime_claim",
                    details={
                        "claim_ids": [claim.claim_id for claim in expired_active_claims],
                        "runtime_task_ids": [claim.runtime_task_id for claim in expired_active_claims],
                    },
                )
            )

        if str(context.run.status) != RunStatus.running and active_claims:
            problems.append(
                self._inspection_problem(
                    "non_running_run_has_active_claim",
                    "run is not running but still has one or more active runtime claims",
                    "release_runtime_claim",
                    repairable=True,
                    repair_action="release_runtime_claim",
                    details={
                        "run_status": str(context.run.status),
                        "claim_ids": [claim.claim_id for claim in active_claims],
                        "runtime_task_ids": [claim.runtime_task_id for claim in active_claims],
                    },
                )
            )

        if expired_active_worker_leases:
            problems.append(
                self._inspection_problem(
                    "worker_lease_expired",
                    "run still has active worker leases whose heartbeat lease has already expired",
                    "expire_worker_lease",
                    repairable=True,
                    repair_action="expire_worker_lease",
                    details={
                        "lease_ids": [lease.lease_id for lease in expired_active_worker_leases],
                        "runtime_task_ids": [lease.runtime_task_id for lease in expired_active_worker_leases],
                        "adapter_names": [lease.adapter_name for lease in expired_active_worker_leases],
                    },
                )
            )

        if str(context.run.status) != RunStatus.running and active_worker_leases:
            problems.append(
                self._inspection_problem(
                    "non_running_run_has_active_worker_lease",
                    "run is not running but still has one or more active worker leases",
                    "release_worker_lease",
                    repairable=True,
                    repair_action="release_worker_lease",
                    details={
                        "run_status": str(context.run.status),
                        "lease_ids": [lease.lease_id for lease in active_worker_leases],
                        "runtime_task_ids": [lease.runtime_task_id for lease in active_worker_leases],
                        "adapter_names": [lease.adapter_name for lease in active_worker_leases],
                    },
                )
            )

        active_decision = (
            scheduler_authority.get("active_decision") if isinstance(scheduler_authority.get("active_decision"), dict) else None
        )
        if active_decision is not None:
            lease_expires_at = self._parse_iso_datetime(active_decision.get("lease_expires_at"))
            released_at = self._parse_iso_datetime(active_decision.get("released_at"))
            if released_at is None and lease_expires_at is not None and lease_expires_at <= self._utc_now():
                problems.append(
                    self._inspection_problem(
                        "scheduler_authority_lease_expired",
                        "scheduler authority still projects an active lease decision whose lease has already expired",
                        "submit_scheduler_proposal_or_release_scheduler_lease",
                        repairable=False,
                        details={
                            "decision_id": active_decision.get("decision_id"),
                            "lease_id": active_decision.get("lease_id"),
                            "control_plane_id": active_decision.get("control_plane_id"),
                            "lease_epoch": active_decision.get("lease_epoch"),
                            "lease_expires_at": active_decision.get("lease_expires_at"),
                        },
                    )
                )

        conflicts = scheduler_authority.get("conflicts")
        if isinstance(conflicts, list) and conflicts:
            latest_conflict = next((item for item in reversed(conflicts) if isinstance(item, dict)), None)
            problems.append(
                self._inspection_problem(
                    "scheduler_authority_conflict",
                    "scheduler authority recorded at least one cross-control-plane lease conflict for this runtime task",
                    "inspect_scheduler_authority_conflicts",
                    severity="warning",
                    repairable=False,
                    details=latest_conflict or {"conflict_count": len(conflicts)},
                )
            )

        active_committed = (
            scheduler_authority.get("active_committed_lease")
            if isinstance(scheduler_authority.get("active_committed_lease"), dict)
            else None
        )
        if scheduler_authority.get("stale_plane_detected") and active_committed is not None:
            problems.append(
                self._inspection_problem(
                    "scheduler_authority_stale_control_plane",
                    "the local control plane is stale and no longer owns the active committed scheduler lease",
                    "inspect_scheduler_authority_takeover",
                    severity="warning",
                    repairable=False,
                    details={
                        "local_control_plane_id": scheduler_authority.get("local_control_plane_id"),
                        "active_control_plane_id": active_committed.get("control_plane_id"),
                        "committed_lease_id": active_committed.get("committed_lease_id"),
                        "fencing_token": active_committed.get("fencing_token"),
                        "term_no": active_committed.get("term_no"),
                        "authority_term_no": active_committed.get("authority_term_no")
                        or active_committed.get("term_no"),
                        "commit_index": active_committed.get("commit_index"),
                        "decision_index": active_committed.get("decision_index")
                        or active_committed.get("commit_index"),
                    },
                )
            )

        if str(context.run.status) == RunStatus.prepared:
            missing_components: list[str] = []
            if len(context.phases) < 2:
                missing_components.append("phases")
            if not context.task_cards:
                missing_components.append("task_cards")
            if not context.runtime_tasks:
                missing_components.append("runtime_tasks")
            if not context.handoffs:
                missing_components.append("handoffs")
            if not context.runtime_state_refs:
                missing_components.append("runtime_state_refs")
            for task in context.runtime_tasks:
                if self.task_repo.get_task_packet(task.runtime_task_id) is None:
                    missing_components.append(f"task_packet:{task.runtime_task_id}")
            if missing_components:
                problems.append(
                    self._inspection_problem(
                        "prepared_compile_snapshot_incomplete",
                        "run is prepared but compile snapshot persistence is incomplete",
                        "recompile_run",
                        repairable=True,
                        repair_action="recompile_prepared_run",
                        details={"missing_components": missing_components},
                    )
                )
        if self._execution_lane_for_context(context) == str(ExecutionLaneType.durable_incremental):
            durable_refs = self._durable_refs_for_state(last_runtime_state)
            durable_lineage = self._durable_lineage_for_state(last_runtime_state)
            if last_runtime_state is None:
                problems.append(
                    self._inspection_problem(
                        "durable_runtime_state_missing",
                        "durable lane is selected but no runtime state ref exists to anchor durable lineage",
                        "recompile_run",
                        repairable=True,
                        repair_action="recompile_prepared_run",
                    )
                )
            elif not durable_refs:
                problems.append(
                    self._inspection_problem(
                        "durable_refs_missing",
                        "durable lane runtime state does not expose thread/checkpoint/assistant refs",
                        "inspect_durable_lineage",
                        repairable=False,
                        details={"state_ref_id": last_runtime_state.state_ref_id},
                    )
                )
            elif durable_lineage is None:
                problems.append(
                    self._inspection_problem(
                        "durable_lineage_missing",
                        "durable lane runtime state exposes refs but does not persist structured durable lineage",
                        "inspect_durable_lineage",
                        repairable=False,
                        details={
                            "state_ref_id": last_runtime_state.state_ref_id,
                            "durable_refs": durable_refs,
                        },
                    )
                )
            else:
                top_level_refs = {
                    key: value
                    for key, value in {
                        "thread_id": last_runtime_state.state_payload.get("thread_id"),
                        "checkpoint_id": last_runtime_state.state_payload.get("checkpoint_id"),
                        "assistant_id": last_runtime_state.state_payload.get("assistant_id"),
                    }.items()
                    if value
                }
                if durable_lineage["current_refs"] != top_level_refs:
                    problems.append(
                        self._inspection_problem(
                            "durable_lineage_refs_mismatch",
                            "durable lineage current refs diverge from the top-level runtime state durable refs",
                            "inspect_durable_lineage",
                            repairable=False,
                            details={
                                "state_ref_id": last_runtime_state.state_ref_id,
                                "current_refs": durable_lineage["current_refs"],
                                "top_level_refs": top_level_refs,
                            },
                        )
                    )
                if not durable_lineage["history"]:
                    problems.append(
                        self._inspection_problem(
                            "durable_lineage_history_empty",
                            "durable lane runtime state is missing transition history",
                            "inspect_durable_lineage",
                            repairable=False,
                            details={"state_ref_id": last_runtime_state.state_ref_id},
                        )
                    )
        return problems

    def _recoverability_hint_for(
        self,
        context: RunDiagnosticContext,
        problems: list[dict[str, Any]] | None = None,
    ) -> str:
        if problems:
            return str(problems[0]["next_action"])
        status = str(context.run.status)
        if status == RunStatus.pending:
            return "compile_run"
        if status == RunStatus.prepared:
            return "resume_run"
        if status == RunStatus.awaiting_review:
            return "approve_or_reject_review"
        if status == RunStatus.failed:
            return "inspect_evidence_then_recompile"
        if status == RunStatus.cancelled:
            return "create_new_run"
        return "none"

    def _available_repair_actions(self, problems: list[dict[str, Any]]) -> list[str]:
        return [
            str(problem["repair_action"])
            for problem in problems
            if problem.get("repairable") and problem.get("repair_action") is not None
        ]

    def _failure_taxonomy_for(self, detail: dict[str, Any], inspection: dict[str, Any]) -> dict[str, Any]:
        run_status = str(detail["run"]["status"])
        failure_reason = detail.get("failure_reason")
        waiting_reason = detail.get("waiting_reason")
        problem_codes = [str(problem["problem"]) for problem in inspection["problems"]]

        if inspection["problem_count"] > 0:
            category = "inconsistent_state"
            primary_reason = problem_codes[0]
            is_failure = True
        elif run_status == RunStatus.completed:
            category = "success"
            primary_reason = "completed"
            is_failure = False
        elif run_status == RunStatus.failed:
            category = "review_failure" if failure_reason in {"human_review_rejected", "auto_review_failed"} else "runtime_failure"
            primary_reason = failure_reason or "run_failed"
            is_failure = True
        elif run_status == RunStatus.cancelled:
            category = "operator_cancelled"
            primary_reason = "cancelled_by_operator"
            is_failure = True
        elif run_status == RunStatus.awaiting_review:
            category = "review_pending"
            primary_reason = waiting_reason or "awaiting_human_review"
            is_failure = False
        else:
            category = "pending_work"
            primary_reason = waiting_reason or detail.get("next_action") or "awaiting_progress"
            is_failure = False

        return {
            "category": category,
            "primary_reason": primary_reason,
            "is_failure": is_failure,
            "is_terminal": run_status in {RunStatus.completed, RunStatus.failed, RunStatus.cancelled},
            "problem_codes": problem_codes,
        }

    def _select_repair_problem(self, run_id: str, problems: list[dict[str, Any]], action: str | None) -> dict[str, Any]:
        available_actions = self._available_repair_actions(problems)
        if action is not None and action not in self.SUPPORTED_REPAIR_ACTIONS:
            raise UnsupportedRepairActionError(action, list(self.SUPPORTED_REPAIR_ACTIONS))
        if not available_actions:
            raise RepairActionNotAvailableError(run_id, action, available_actions)
        selected_action = action or available_actions[0]
        for problem in problems:
            if problem.get("repairable") and problem.get("repair_action") == selected_action:
                return problem
        raise RepairActionNotAvailableError(run_id, selected_action, available_actions)

    def _runtime_terminal_graph_step_for_run_status(self, run_status: RunStatus | str) -> RuntimeGraphStep:
        normalized = RunStatus(run_status)
        mapping = {
            RunStatus.completed: RuntimeGraphStep.completed,
            RunStatus.failed: RuntimeGraphStep.failed,
            RunStatus.cancelled: RuntimeGraphStep.cancelled,
        }
        return mapping[normalized]

    def _task_terminal_status_for_run_status(self, run_status: RunStatus | str) -> TaskStatus:
        normalized = RunStatus(run_status)
        mapping = {
            RunStatus.completed: TaskStatus.completed,
            RunStatus.failed: TaskStatus.failed,
            RunStatus.cancelled: TaskStatus.cancelled,
        }
        return mapping[normalized]

    def _append_repair_event(
        self,
        run_id: str,
        action: str,
        problem: str,
        repaired_runtime_task_ids: list[str],
        *,
        connection=None,
    ) -> None:
        self.event_repo.append(
            RunEvent(
                run_id=run_id,
                event_type=RunEventType.repair_applied,
                object_type="run",
                object_id=run_id,
                summary=f"Repair applied: {action}",
                payload_json={
                    "run_id": run_id,
                    "action": action,
                    "problem": problem,
                    "repaired_runtime_task_ids": repaired_runtime_task_ids,
                },
            ),
            connection=connection,
        )

    def _capture_run_snapshot(
        self,
        run_id: str,
        stage: RunSnapshotStage | str,
        summary: str,
        *,
        runtime_task_id: str | None = None,
        connection=None,
        payload_extra: dict[str, Any] | None = None,
    ) -> RunSnapshot:
        context = self._load_run_context(run_id, connection=connection)
        last_runtime_state = self._last_runtime_state(context)
        last_attempt = self._last_attempt(context)
        current_attempt = self._current_attempt(context)
        last_claim = self._last_claim(context)
        last_worker_lease = self._last_worker_lease(context)
        review_policy = self._review_policy_for_context(context, last_runtime_state=last_runtime_state)
        snapshot = RunSnapshot(
            run_id=run_id,
            stage=RunSnapshotStage(stage),
            run_status=context.run.status,
            runtime_task_id=runtime_task_id or (context.runtime_tasks[0].runtime_task_id if context.runtime_tasks else None),
            summary=summary,
            snapshot_payload={
                "effective_review_state": self._effective_review_state(
                    context.run,
                    context.latest_review_verdict,
                    review_policy,
                ),
                "review_policy": review_policy,
                "runtime_task_ids": [task.runtime_task_id for task in context.runtime_tasks],
                "latest_runtime_graph_step": str(last_runtime_state.graph_step) if last_runtime_state is not None else None,
                "latest_runtime_state_ref_id": last_runtime_state.state_ref_id if last_runtime_state is not None else None,
                "durable_lineage": self._durable_lineage_for_state(last_runtime_state),
                "latest_attempt_id": last_attempt.attempt_id if last_attempt is not None else None,
                "current_attempt_id": current_attempt.attempt_id if current_attempt is not None else None,
                "latest_review_verdict_id": (
                    context.latest_review_verdict.verdict_id if context.latest_review_verdict is not None else None
                ),
                "latest_claim_id": last_claim.claim_id if last_claim is not None else None,
                "active_claim_ids": [claim.claim_id for claim in self._active_claims_for(context)],
                "latest_worker_lease_id": last_worker_lease.lease_id if last_worker_lease is not None else None,
                "active_worker_lease_ids": [lease.lease_id for lease in self._active_worker_leases_for(context)],
                **(payload_extra or {}),
            },
        )
        self.snapshot_repo.create(snapshot, connection=connection)
        self.event_repo.append(
            RunEvent(
                run_id=run_id,
                event_type=RunEventType.run_snapshot_created,
                object_type="run_snapshot",
                object_id=snapshot.snapshot_id,
                summary=summary,
                payload_json={
                    "run_id": run_id,
                    "snapshot_id": snapshot.snapshot_id,
                    "stage": snapshot.stage,
                    "run_status": snapshot.run_status,
                    "runtime_task_id": snapshot.runtime_task_id,
                },
            ),
            connection=connection,
        )
        return snapshot

    def _task_kind_for_recompile(self, run_id: str) -> TaskKind | str | None:
        runtime_tasks = self.task_repo.list_runtime_tasks_for_run(run_id)
        if runtime_tasks:
            return runtime_tasks[0].task_kind
        timeline = self.get_timeline(run_id)
        for event in reversed(timeline):
            if event.event_type == RunEventType.runtime_task_created:
                task_kind = event.payload_json.get("task_kind")
                if task_kind is not None:
                    return task_kind
        return None

    def _apply_align_terminal_runtime_state(self, run: Run, action: str, problem: str) -> list[str]:
        with unit_of_work(self.db_path) as connection:
            live_states = self.runtime_state_repo.list_live_for_run(run.run_id, connection=connection)
            if not live_states:
                raise RepairActionNotAvailableError(run.run_id, action, [action])
            target_graph_step = self._runtime_terminal_graph_step_for_run_status(run.status)
            target_task_status = self._task_terminal_status_for_run_status(run.status)
            repaired_runtime_task_ids: list[str] = []
            for state_ref in live_states:
                repaired_state = RuntimeStateRef(
                    state_ref_id=state_ref.state_ref_id,
                    run_id=state_ref.run_id,
                    runtime_task_id=state_ref.runtime_task_id,
                    graph_step=target_graph_step,
                    state_payload={
                        **state_ref.state_payload,
                        "repaired_action": action,
                        "repaired_problem": problem,
                    },
                    is_terminal=True,
                    created_at=state_ref.created_at,
                )
                self.runtime_state_repo.upsert(repaired_state, connection=connection)
                self.task_repo.update_runtime_task_status(
                    state_ref.runtime_task_id,
                    target_task_status,
                    connection=connection,
                )
                repaired_runtime_task_ids.append(state_ref.runtime_task_id)
            self._append_repair_event(
                run.run_id,
                action,
                problem,
                repaired_runtime_task_ids,
                connection=connection,
            )
        return repaired_runtime_task_ids

    def _apply_recompile_prepared_run(self, run_id: str, action: str, problem: str) -> list[str]:
        task_kind = self._task_kind_for_recompile(run_id)
        prepared = self.recompile_run(run_id, task_kind=task_kind, ignore_budget=True)
        self._append_repair_event(
            run_id,
            action,
            problem,
            [prepared.task_packet.runtime_task_id],
        )
        return [prepared.task_packet.runtime_task_id]

    def _apply_claim_release_repair(
        self,
        run_id: str,
        action: str,
        problem: str,
        *,
        status: RuntimeClaimStatus | str,
        reason: str,
    ) -> list[str]:
        with unit_of_work(self.db_path) as connection:
            active_claims = self.runtime_claim_repo.list_active_for_run(run_id, connection=connection)
            if not active_claims:
                raise RepairActionNotAvailableError(run_id, action, [action])
            repaired_runtime_task_ids: list[str] = []
            for claim in active_claims:
                self._release_runtime_claim(
                    claim,
                    status=status,
                    reason=reason,
                    connection=connection,
                )
                repaired_runtime_task_ids.append(claim.runtime_task_id)
            self._append_repair_event(
                run_id,
                action,
                problem,
                repaired_runtime_task_ids,
                connection=connection,
            )
        return repaired_runtime_task_ids

    def _apply_worker_lease_release_repair(
        self,
        run_id: str,
        action: str,
        problem: str,
        *,
        status: WorkerLeaseStatus | str,
        reason: str,
    ) -> list[str]:
        with unit_of_work(self.db_path) as connection:
            active_leases = self.worker_lease_repo.list_active_for_run(run_id, connection=connection)
            if not active_leases:
                raise RepairActionNotAvailableError(run_id, action, [action])
            repaired_runtime_task_ids: list[str] = []
            for lease in active_leases:
                self._release_worker_lease(
                    lease,
                    status=status,
                    reason=reason,
                    connection=connection,
                )
                repaired_runtime_task_ids.append(lease.runtime_task_id)
            self._append_repair_event(
                run_id,
                action,
                problem,
                repaired_runtime_task_ids,
                connection=connection,
            )
        return repaired_runtime_task_ids

    def _apply_close_current_attempt_terminal(
        self,
        run: Run,
        action: str,
        problem: str,
    ) -> list[str]:
        with unit_of_work(self.db_path) as connection:
            current_attempt = self.runtime_attempt_repo.current_for_run(run.run_id, connection=connection)
            if current_attempt is None:
                raise RepairActionNotAvailableError(run.run_id, action, [action])
            status_mapping = {
                RunStatus.completed: RuntimeAttemptStatus.completed,
                RunStatus.failed: RuntimeAttemptStatus.failed,
                RunStatus.cancelled: RuntimeAttemptStatus.cancelled,
            }
            close_reason_mapping = {
                RunStatus.completed: "reconciled_terminal_run_completed",
                RunStatus.failed: "reconciled_terminal_run_failed",
                RunStatus.cancelled: "reconciled_terminal_run_cancelled",
            }
            attempt_status = status_mapping[RunStatus(run.status)]
            self._close_runtime_attempt(
                current_attempt,
                status=attempt_status,
                reason=close_reason_mapping[RunStatus(run.status)],
                connection=connection,
            )
            repaired_runtime_task_ids = [current_attempt.runtime_task_id]
            self._append_repair_event(
                run.run_id,
                action,
                problem,
                repaired_runtime_task_ids,
                connection=connection,
            )
        return repaired_runtime_task_ids

    def _apply_interrupt_current_attempt(
        self,
        run_id: str,
        action: str,
        problem: str,
    ) -> list[str]:
        with unit_of_work(self.db_path) as connection:
            current_attempt = self.runtime_attempt_repo.current_for_run(run_id, connection=connection)
            if current_attempt is None:
                raise RepairActionNotAvailableError(run_id, action, [action])
            self._close_runtime_attempt(
                current_attempt,
                status=RuntimeAttemptStatus.interrupted,
                reason=f"reconciled_{problem}",
                connection=connection,
            )
            repaired_runtime_task_ids = [current_attempt.runtime_task_id]
            self._append_repair_event(
                run_id,
                action,
                problem,
                repaired_runtime_task_ids,
                connection=connection,
            )
        return repaired_runtime_task_ids

    def _apply_create_repair_attempt(
        self,
        run_id: str,
        action: str,
        problem: str,
    ) -> list[str]:
        with unit_of_work(self.db_path) as connection:
            run_context = self._load_run_context(run_id, connection=connection)
            if self._current_attempt(run_context) is not None or not run_context.runtime_tasks:
                raise RepairActionNotAvailableError(run_id, action, [action])
            runtime_task = run_context.runtime_tasks[0]
            self._ensure_current_runtime_attempt(
                run_id,
                runtime_task.runtime_task_id,
                trigger=RuntimeAttemptTrigger.repair,
                connection=connection,
                reason_if_superseded="repair_recreated_current_attempt",
            )
            repaired_runtime_task_ids = [runtime_task.runtime_task_id]
            self._append_repair_event(
                run_id,
                action,
                problem,
                repaired_runtime_task_ids,
                connection=connection,
            )
        return repaired_runtime_task_ids

    def list_presets(self) -> list[PresetDefinition]:
        return self.preset_repo.list()

    def list_runs(
        self,
        limit: int = 10,
        *,
        status: str | None = None,
        preset_id: str | None = None,
    ) -> list[Run]:
        return self.run_repo.list(limit=limit, status=status, preset_id=preset_id)

    def suggest_presets(self, goal: str) -> list[PresetSuggestion]:
        return self._resolver().suggest(goal)

    def _resolve_domain_pack(
        self,
        preset: PresetDefinition,
        task_kind: TaskKind | str | None,
    ) -> DomainPackResolution | None:
        return self.domain_pack_registry.resolve(preset.preset_id, task_kind=task_kind)

    def _capability_route_for(
        self,
        task_kind: TaskKind | str | None,
        adapter_name: str | None = None,
    ) -> CapabilityRoute | None:
        if task_kind is None:
            return None
        route = self.worker_router.describe(str(task_kind), adapter_name=adapter_name)
        return CapabilityRoute.model_validate(route) if route is not None else None

    def _selected_adapter_name_for_runtime_task(self, runtime_task: RuntimeTask | None) -> str | None:
        if runtime_task is None:
            return None
        task_packet = self.task_repo.get_task_packet(runtime_task.runtime_task_id)
        if task_packet is None:
            return None
        adapter_name = task_packet.env.get("WORKFLOW_CAPABILITY_ADAPTER") or None
        return adapter_name

    def _capability_route_for_runtime_task(self, runtime_task: RuntimeTask | None) -> CapabilityRoute | None:
        if runtime_task is None:
            return None
        return self._capability_route_for(
            runtime_task.task_kind,
            adapter_name=self._selected_adapter_name_for_runtime_task(runtime_task),
        )

    def _resolve_capability_route(
        self,
        task_kind: TaskKind | str,
        requested_adapter: str | None = None,
    ) -> CapabilityRoute | None:
        route = self._capability_route_for(task_kind, adapter_name=requested_adapter)
        if route is not None:
            return route
        if requested_adapter:
            capability = str(task_kind)
            available = [
                item["adapter_name"]
                for item in self.list_capability_routes()
                if item["capability"] == capability
            ]
            raise CapabilityAdapterNotFoundError(capability, requested_adapter, available)
        return None

    def _runtime_task_for_context(self, context: RunDiagnosticContext) -> RuntimeTask | None:
        if not context.runtime_tasks:
            return None
        return min(context.runtime_tasks, key=lambda task: (task.created_at, task.runtime_task_id))

    def _runtime_gateway_description_for_context(self, context: RunDiagnosticContext) -> dict[str, Any]:
        runtime_task = self._runtime_task_for_context(context)
        if runtime_task is None:
            return self.runtime_gateway.describe()
        task_packet = self.task_repo.get_task_packet(runtime_task.runtime_task_id)
        if task_packet is None:
            return self.runtime_gateway.describe()
        description = dict(self.runtime_gateway.describe())
        provider = task_packet.env.get("WORKFLOW_RUNTIME_GATEWAY_PROVIDER") or None
        if provider is None:
            return description
        normalized_provider = str(provider).strip().lower()
        description["provider"] = normalized_provider
        if normalized_provider in {"", "null", "none", "disabled"}:
            description["configured"] = False
            description["live"] = False
            description["model"] = None
            description["reasoning_effort"] = None
            return description
        runtime_model = task_packet.env.get("WORKFLOW_RUNTIME_GATEWAY_MODEL") or None
        reasoning_effort = task_packet.env.get("WORKFLOW_RUNTIME_REASONING_EFFORT") or None
        if runtime_model is not None:
            description["model"] = runtime_model
        if reasoning_effort is not None:
            description["reasoning_effort"] = reasoning_effort
        return description

    def _state_ref_with_compile_context(
        self,
        state_ref: RuntimeStateRef,
        run: Run,
        preset: PresetDefinition,
        snapshot: CompileSnapshot,
    ) -> RuntimeStateRef:
        payload = {
            **state_ref.state_payload,
            "goal": run.goal,
            "preset_id": preset.preset_id,
            "task_kind": str(snapshot.runtime_task.task_kind),
            "expected_artifacts": snapshot.task_packet.expected_artifacts,
            "working_directory": snapshot.task_packet.working_directory,
            "control_plane_id": self.control_plane_identity.control_plane_id,
            "domain_pack_id": snapshot.domain_pack.domain_pack_id if snapshot.domain_pack is not None else None,
            "domain_pack_resolution": (
                snapshot.domain_pack.model_dump(mode="json") if snapshot.domain_pack is not None else None
            ),
            "capability_adapter": snapshot.capability_route.adapter_name if snapshot.capability_route is not None else None,
            "memory_retrieval_preview": (
                snapshot.memory_preview.model_dump(mode="json") if snapshot.memory_preview is not None else None
            ),
            "resolved_execution": snapshot.resolved_execution.model_dump(mode="json"),
            "execution_resolution_trace": {
                "scope_context": (
                    snapshot.resolved_execution.scope_context.model_dump(mode="json")
                    if snapshot.resolved_execution.scope_context is not None
                    else None
                ),
                "source_map": snapshot.resolved_execution.source_map,
                "applied_scopes": snapshot.resolved_execution.applied_scopes,
                "compatibility_fallback": snapshot.resolved_execution.compatibility_fallback,
            },
            "mutation_contract": (
                snapshot.task_packet.mutation_contract.model_dump(mode="json")
                if snapshot.task_packet.mutation_contract is not None
                else None
            ),
            "capability_invocation_envelope": (
                json.loads(snapshot.task_packet.env["WORKFLOW_CAPABILITY_INVOCATION_ENVELOPE"])
                if snapshot.task_packet.env.get("WORKFLOW_CAPABILITY_INVOCATION_ENVELOPE")
                else None
            ),
            "orchestration_plan_graph": (
                json.loads(snapshot.task_packet.env["WORKFLOW_ORCHESTRATION_PLAN_GRAPH"])
                if snapshot.task_packet.env.get("WORKFLOW_ORCHESTRATION_PLAN_GRAPH")
                else None
            ),
        }
        payload["context_budget"] = build_context_budget_report(payload)
        return RuntimeStateRef.model_validate(
            {
                **state_ref.model_dump(mode="json"),
                "state_payload": payload,
            }
        )

    def _context_budget_from_state_ref(self, state_ref: RuntimeStateRef | None) -> dict[str, Any] | None:
        if state_ref is None:
            return None
        payload = state_ref.state_payload.get("context_budget")
        return payload if isinstance(payload, dict) else None

    def _parallel_batch_from_state_ref(self, state_ref: RuntimeStateRef | None) -> dict[str, Any] | None:
        if state_ref is None:
            return None
        payload = state_ref.state_payload.get("parallel_batch")
        return payload if isinstance(payload, dict) else None

    def _trace_context_for_context(
        self,
        context: RunDiagnosticContext,
        *,
        latest_event: RunEvent | None = None,
        last_runtime_state: RuntimeStateRef | None = None,
        latest_attempt: RuntimeAttempt | None = None,
        latest_evidence: Evidence | None = None,
        latest_review_verdict: ReviewVerdict | None = None,
    ) -> dict[str, Any]:
        if latest_event is None:
            timeline = self.event_repo.list_for_run(context.run.run_id)
            latest_event = max(timeline, key=lambda item: (item.created_at, item.event_id)) if timeline else None
        last_runtime_state = last_runtime_state or self._last_runtime_state(context)
        latest_attempt = latest_attempt or self._last_attempt(context)
        latest_evidence = latest_evidence or self._last_evidence(context)
        latest_review_verdict = latest_review_verdict or context.latest_review_verdict
        latest_claim = self._last_claim(context)
        latest_worker_lease = self._last_worker_lease(context)
        latest_snapshot = self._last_snapshot(context)
        latest_simulation_record = self.simulation_record_repo.latest_for_run(context.run.run_id)
        durable_refs = self._durable_refs_for_state(last_runtime_state)
        return TraceContext(
            run_id=context.run.run_id,
            event_id=latest_event.event_id if latest_event is not None else None,
            runtime_task_id=last_runtime_state.runtime_task_id if last_runtime_state is not None else None,
            state_ref_id=last_runtime_state.state_ref_id if last_runtime_state is not None else None,
            attempt_id=latest_attempt.attempt_id if latest_attempt is not None else None,
            evidence_id=latest_evidence.evidence_id if latest_evidence is not None else None,
            verdict_id=latest_review_verdict.verdict_id if latest_review_verdict is not None else None,
            claim_id=latest_claim.claim_id if latest_claim is not None else None,
            lease_id=latest_worker_lease.lease_id if latest_worker_lease is not None else None,
            snapshot_id=latest_snapshot.snapshot_id if latest_snapshot is not None else None,
            projection_id=(
                (last_runtime_state.state_payload.get("tool_projection_manifest") or {}).get("projection_id")
                if last_runtime_state is not None
                else None
            ),
            external_trace_id=last_runtime_state.state_payload.get("external_trace_id") if last_runtime_state is not None else None,
            external_session_id=last_runtime_state.state_payload.get("external_session_id") if last_runtime_state is not None else None,
            external_session_url=last_runtime_state.state_payload.get("external_session_url") if last_runtime_state is not None else None,
            session_export_ref=last_runtime_state.state_payload.get("session_export_ref") if last_runtime_state is not None else None,
            thread_id=durable_refs.get("thread_id"),
            checkpoint_id=durable_refs.get("checkpoint_id"),
            assistant_id=durable_refs.get("assistant_id"),
            simulation_record_id=latest_simulation_record.record_id if latest_simulation_record is not None else None,
        ).model_dump(mode="json")

    def _stored_domain_pack_for_runtime_task(self, runtime_task: RuntimeTask | None) -> DomainPackResolution | None:
        if runtime_task is None:
            return None
        task_packet = self.task_repo.get_task_packet(runtime_task.runtime_task_id)
        if task_packet is None:
            return None
        return load_domain_pack_resolution(task_packet.env.get(DOMAIN_PACK_RESOLUTION_ENV_KEY))

    def _stored_domain_pack_from_state_ref(self, state_ref: RuntimeStateRef | None) -> DomainPackResolution | None:
        if state_ref is None:
            return None
        payload = state_ref.state_payload.get("domain_pack_resolution")
        if payload is None:
            return None
        return DomainPackResolution.model_validate(payload)

    def _stored_memory_preview_for_runtime_task(
        self,
        runtime_task: RuntimeTask | None,
    ) -> MemoryRetrievalPreview | None:
        if runtime_task is None:
            return None
        task_packet = self.task_repo.get_task_packet(runtime_task.runtime_task_id)
        if task_packet is None:
            return None
        return load_memory_retrieval_preview(task_packet.env.get(MEMORY_RETRIEVAL_PREVIEW_ENV_KEY))

    def _stored_memory_preview_from_state_ref(
        self,
        state_ref: RuntimeStateRef | None,
    ) -> MemoryRetrievalPreview | None:
        if state_ref is None:
            return None
        payload = state_ref.state_payload.get("memory_retrieval_preview")
        if payload is None:
            return None
        return MemoryRetrievalPreview.model_validate(payload)

    def _tool_projection_manifest_for_context(
        self,
        context: RunDiagnosticContext,
    ) -> ToolProjectionManifest | None:
        runtime_task = self._runtime_task_for_context(context)
        if runtime_task is not None:
            task_packet = self.task_repo.get_task_packet(runtime_task.runtime_task_id)
            if task_packet is not None:
                manifest = load_tool_projection_manifest(task_packet.env.get(TOOL_PROJECTION_MANIFEST_ENV_KEY))
                if manifest is not None:
                    return manifest
        state_ref = self._last_runtime_state(context)
        if state_ref is None:
            return None
        payload = state_ref.state_payload.get("tool_projection_manifest")
        if payload is None:
            return None
        return ToolProjectionManifest.model_validate(payload)

    def _execution_lane_for_context(self, context: RunDiagnosticContext) -> str:
        state_ref = self._last_runtime_state(context)
        if state_ref is not None and state_ref.state_payload.get("execution_lane"):
            return str(state_ref.state_payload["execution_lane"])
        runtime_task = self._runtime_task_for_context(context)
        if runtime_task is None:
            return str(ExecutionLaneType.native_deterministic)
        task_packet = self.task_repo.get_task_packet(runtime_task.runtime_task_id)
        if task_packet is None:
            return str(ExecutionLaneType.native_deterministic)
        return task_packet.env.get("WORKFLOW_EXECUTION_LANE", str(ExecutionLaneType.native_deterministic))

    def _mcp_profiles_for_context(self, context: RunDiagnosticContext) -> list[dict[str, Any]]:
        state_ref = self._last_runtime_state(context)
        if state_ref is None:
            return []
        profiles = state_ref.state_payload.get("mcp_server_profiles")
        return profiles if isinstance(profiles, list) else []

    def _domain_pack_for_context(self, context: RunDiagnosticContext) -> DomainPackResolution | None:
        runtime_task = self._runtime_task_for_context(context)
        stored_resolution = self._stored_domain_pack_for_runtime_task(runtime_task)
        if stored_resolution is not None:
            return stored_resolution
        stored_state_resolution = self._stored_domain_pack_from_state_ref(self._last_runtime_state(context))
        if stored_state_resolution is not None:
            return stored_state_resolution
        if context.preset is None:
            return None
        task_kind = runtime_task.task_kind if runtime_task is not None else None
        return self._resolve_domain_pack(context.preset, task_kind)

    def _memory_preview_for_context(self, context: RunDiagnosticContext) -> MemoryRetrievalPreview | None:
        runtime_task = self._runtime_task_for_context(context)
        stored_preview = self._stored_memory_preview_for_runtime_task(runtime_task)
        if stored_preview is not None:
            return stored_preview
        return self._stored_memory_preview_from_state_ref(self._last_runtime_state(context))

    def _resolve_task_kind(self, preset: PresetDefinition, requested_task_kind: TaskKind | str | None) -> TaskKind:
        if requested_task_kind is None:
            return TaskKind(preset.allowed_task_kinds[0])
        try:
            normalized = TaskKind(requested_task_kind)
        except ValueError as exc:
            raise UnsupportedTaskKindError(str(requested_task_kind), [member.value for member in TaskKind]) from exc
        allowed = [TaskKind(task_kind) for task_kind in preset.allowed_task_kinds]
        if normalized not in allowed:
            raise TaskKindNotAllowedError(preset.preset_id, str(normalized), [str(task_kind) for task_kind in allowed])
        return normalized

    def create_run(self, goal: str, preset_id: str | None) -> Run:
        resolver = self._resolver()
        preset = resolver.manual_select(preset_id)
        run = self.run_repo.create(Run(goal=goal, preset_id=preset.preset_id))
        self.event_repo.append(
            RunEvent(
                run_id=run.run_id,
                event_type=RunEventType.run_created,
                object_type="run",
                object_id=run.run_id,
                summary="Run created",
                payload_json={"goal": run.goal, "preset_id": run.preset_id},
            )
        )
        self.event_repo.append(
            RunEvent(
                run_id=run.run_id,
                event_type=RunEventType.preset_selected,
                object_type="preset",
                object_id=preset.preset_id,
                summary="Preset selected",
                payload_json={"preset_id": preset.preset_id, "preset_name": preset.name},
            )
        )
        return run

    def get_run(self, run_id: str) -> Run:
        run = self.run_repo.get(run_id)
        if run is None:
            raise EntityNotFoundError("run", run_id)
        return run

    def get_timeline(self, run_id: str) -> list[RunEvent]:
        self.get_run(run_id)
        return self.event_repo.list_for_run(run_id)

    def get_task_evidence(self, runtime_task_id: str) -> Evidence:
        evidence = self.evidence_repo.get_by_task(runtime_task_id)
        if evidence is None:
            raise EntityNotFoundError("evidence", runtime_task_id)
        return evidence

    def list_handoffs(self, run_id: str) -> list[HandoffLite]:
        self.get_run(run_id)
        return self.handoff_repo.list_for_run(run_id)

    def list_claims(self, run_id: str) -> list[RuntimeClaim]:
        self.get_run(run_id)
        return self.runtime_claim_repo.list_for_run(run_id)

    def list_worker_leases(self, run_id: str) -> list[WorkerLease]:
        self.get_run(run_id)
        return self.worker_lease_repo.list_for_run(run_id)

    def submit_scheduler_proposal(
        self,
        *,
        control_plane_id: str,
        run_id: str,
        runtime_task_id: str,
        domain_kind: str = "runtime_task",
        domain_key: str,
        requested_lease_seconds: int = 300,
        requested_epoch: int = 1,
    ) -> dict[str, Any]:
        self.get_run(run_id)
        with unit_of_work(self.db_path) as connection:
            state_ref = self.runtime_state_repo.get_by_task(runtime_task_id, connection=connection)
            result = self.scheduler_authority_cluster.submit_proposal(
                control_plane_id=control_plane_id,
                run_id=run_id,
                runtime_task_id=runtime_task_id,
                domain_kind=domain_kind,
                domain_key=domain_key,
                requested_lease_seconds=requested_lease_seconds,
                requested_epoch=requested_epoch,
                connection=connection,
            )
            proposal = (
                SchedulerLeaseProposal.model_validate(result["proposal"])
                if isinstance(result.get("proposal"), dict)
                else None
            )
            decision = (
                SchedulerLeaseDecision.model_validate(result["decision"])
                if isinstance(result.get("decision"), dict)
                else None
            )
            committed_lease = (
                SchedulerCommittedLease.model_validate(result["committed_lease"])
                if isinstance(result.get("committed_lease"), dict)
                else None
            )
            term = (
                SchedulerConsensusTerm.model_validate(result["term"])
                if isinstance(result.get("term"), dict)
                else None
            )
            votes = [
                SchedulerVoteRecord.model_validate(item)
                for item in result.get("votes", [])
                if isinstance(item, dict)
            ]
            handoff_envelope_payload = result.get("handoff_envelope") if isinstance(result.get("handoff_envelope"), dict) else None
            handoff_envelope = (
                ControlPlaneHandoffEnvelope.model_validate(result["handoff_envelope"])
                if isinstance(result.get("handoff_envelope"), dict)
                else None
            )
            if state_ref is not None:
                updates = self._scheduler_arbitration_updates(
                    state_ref,
                    control_plane_id=control_plane_id,
                    proposal=proposal,
                    decision=decision,
                    committed_lease=committed_lease,
                    term=term,
                    votes=votes,
                    handoff_envelope=handoff_envelope_payload or handoff_envelope,
                    cluster=result.get("cluster"),
                    conflict=result.get("conflict"),
                )
                self.runtime_state_repo.upsert(
                    self._state_ref_with_payload_updates(state_ref, updates),
                    connection=connection,
                )
            return result

    def record_scheduler_peer_heartbeat(
        self,
        *,
        control_plane_id: str,
        status: str = "active",
        lease_count: int = 0,
        observed_at: str | None = None,
    ) -> dict[str, Any]:
        heartbeat = self.scheduler_peer_heartbeat_repo.create(
            SchedulerPeerHeartbeat(
                control_plane_id=control_plane_id,
                status=status,
                lease_count=lease_count,
                observed_at=datetime.fromisoformat(observed_at) if observed_at is not None else self._utc_now(),
            )
        )
        cluster = self.scheduler_authority_cluster.heartbeat_node(
            node_id=control_plane_id,
            bind_url=f"internal://{control_plane_id}",
            status=status,
            role="control_plane",
            observed_at=heartbeat.observed_at.isoformat(),
        )
        return {
            "heartbeat": heartbeat.model_dump(mode="json"),
            "cluster": cluster["cluster"],
        }

    def release_scheduler_lease(
        self,
        lease_id: str,
        *,
        release_reason: str = "control_plane_release",
    ) -> dict[str, Any]:
        with unit_of_work(self.db_path) as connection:
            released = self.scheduler_authority_cluster.release_lease(
                lease_id,
                release_reason=release_reason,
                connection=connection,
            )
            decision = (
                SchedulerLeaseDecision.model_validate(released["decision"])
                if isinstance(released.get("decision"), dict)
                else None
            )
            if decision is None:
                raise EntityNotFoundError("scheduler_lease", lease_id)
            state_ref = self.runtime_state_repo.get_by_task(decision.runtime_task_id, connection=connection)
            if state_ref is not None:
                updates = self._scheduler_arbitration_updates(
                    state_ref,
                    control_plane_id=decision.control_plane_id,
                    decision=decision,
                    committed_lease=released.get("committed_lease"),
                    cluster=released.get("cluster"),
                )
                self.runtime_state_repo.upsert(
                    self._state_ref_with_payload_updates(state_ref, updates),
                    connection=connection,
                )
            latest_heartbeat = self.scheduler_peer_heartbeat_repo.latest_for_control_plane(
                decision.control_plane_id,
                connection=connection,
            )
            return {
                "decision": decision.model_dump(mode="json"),
                "committed_lease": released.get("committed_lease"),
                "cluster": released.get("cluster"),
                "latest_peer_heartbeat": (
                    latest_heartbeat.model_dump(mode="json") if latest_heartbeat is not None else None
                ),
            }

    def get_scheduler_lease(self, lease_id: str) -> dict[str, Any]:
        payload = self.scheduler_authority_cluster.get_lease(lease_id)
        decision = (
            SchedulerLeaseDecision.model_validate(payload["decision"])
            if isinstance(payload.get("decision"), dict)
            else None
        )
        latest_heartbeat = (
            self.scheduler_peer_heartbeat_repo.latest_for_control_plane(decision.control_plane_id)
            if decision is not None
            else None
        )
        return {
            **payload,
            "latest_peer_heartbeat": (
                latest_heartbeat.model_dump(mode="json") if latest_heartbeat is not None else None
            ),
        }

    def list_runtime_attempts(self, run_id: str) -> list[RuntimeAttempt]:
        self.get_run(run_id)
        return self.runtime_attempt_repo.list_for_run(run_id)

    def list_snapshots(self, run_id: str) -> list[RunSnapshot]:
        self.get_run(run_id)
        return self.snapshot_repo.list_for_run(run_id)

    def get_budget_ledger(self, run_id: str) -> BudgetLedger:
        self.get_run(run_id)
        ledger = self.budget_repo.get_by_run(run_id)
        if ledger is None:
            raise EntityNotFoundError("budget_ledger", run_id)
        return ledger

    def _worker_callback_registry(self, state_ref: RuntimeStateRef | None) -> dict[str, list[str]]:
        if state_ref is None:
            return {"heartbeat": [], "completion": []}
        callbacks = state_ref.state_payload.get("worker_callbacks")
        if not isinstance(callbacks, dict):
            return {"heartbeat": [], "completion": []}
        heartbeat = callbacks.get("heartbeat")
        completion = callbacks.get("completion")
        return {
            "heartbeat": [str(item) for item in heartbeat] if isinstance(heartbeat, list) else [],
            "completion": [str(item) for item in completion] if isinstance(completion, list) else [],
        }

    def _append_worker_callback(
        self,
        state_ref: RuntimeStateRef,
        *,
        callback_type: str,
        callback_id: str,
        payload: dict[str, Any],
    ) -> RuntimeStateRef:
        registry = self._worker_callback_registry(state_ref)
        callback_ids = registry.setdefault(callback_type, [])
        if callback_id not in callback_ids:
            callback_ids.append(callback_id)
        callback_history = list(state_ref.state_payload.get("worker_callback_history") or [])
        callback_history.append({"type": callback_type, "callback_id": callback_id, **payload})
        return self._state_ref_with_payload_updates(
            state_ref,
            {
                "worker_callbacks": registry,
                "worker_callback_history": callback_history[-20:],
            },
        )

    def record_worker_heartbeat(
        self,
        *,
        callback_id: str,
        dispatch_id: str,
        run_id: str,
        runtime_task_id: str,
        lease_id: str,
        worker_pool_id: str,
        heartbeat_at: str,
        lease_expires_at: str,
        execution_target: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with unit_of_work(self.db_path) as connection:
            state_ref = self.runtime_state_repo.get_by_task(runtime_task_id, connection=connection)
            if state_ref is None:
                raise EntityNotFoundError("runtime_state_ref", runtime_task_id)
            committed_lease = self._validate_callback_scheduler_context(
                runtime_task_id=runtime_task_id,
                execution_target=execution_target,
                connection=connection,
            )
            registry = self._worker_callback_registry(state_ref)
            if callback_id in registry["heartbeat"]:
                return {"accepted": True, "duplicate": True, "callback_id": callback_id}
            lease = self.worker_lease_repo.touch(
                lease_id,
                heartbeat_at=heartbeat_at,
                lease_expires_at=lease_expires_at,
                connection=connection,
            )
            if lease is None:
                raise EntityNotFoundError("worker_lease", lease_id)
            renewed_at = datetime.fromisoformat(heartbeat_at)
            renewal = LeaseRenewalRecord(
                run_id=run_id,
                runtime_task_id=runtime_task_id,
                worker_pool_id=worker_pool_id,
                lease_id=lease_id,
                status="renewed",
                renewed_at=renewed_at,
                heartbeat_at=renewed_at,
                lease_expires_at=datetime.fromisoformat(lease_expires_at),
                callback_id=callback_id,
                source="worker_callback",
            )
            current_renewals = self._lease_renewals_for(state_ref, None)
            if callback_id not in {item.get("callback_id") for item in current_renewals if isinstance(item, dict)}:
                current_renewals.append(renewal.model_dump(mode="json"))
            payload_updates: dict[str, Any] = {
                "lease_renewals": current_renewals[-20:],
            }
            if execution_target is not None:
                payload_updates["execution_target"] = {
                    **execution_target,
                    "last_callback_at": heartbeat_at,
                }
                payload_updates["committed_scheduler_lease"] = self._scheduler_committed_lease_payload(committed_lease)
            updated_state = self._append_worker_callback(
                self._state_ref_with_payload_updates(state_ref, payload_updates),
                callback_type="heartbeat",
                callback_id=callback_id,
                payload={
                    "dispatch_id": dispatch_id,
                    "lease_id": lease_id,
                    "heartbeat_at": heartbeat_at,
                    "lease_expires_at": lease_expires_at,
                },
            )
            self.runtime_state_repo.upsert(updated_state, connection=connection)
            self.event_repo.append(
                RunEvent(
                    run_id=run_id,
                    event_type=RunEventType.worker_heartbeat_received,
                    object_type="worker_lease",
                    object_id=lease_id,
                    summary="Worker heartbeat received",
                    payload_json={
                        "run_id": run_id,
                        "runtime_task_id": runtime_task_id,
                        "lease_id": lease_id,
                        "worker_pool_id": worker_pool_id,
                        "callback_id": callback_id,
                        "heartbeat_at": heartbeat_at,
                        "lease_expires_at": lease_expires_at,
                    },
                ),
                connection=connection,
            )
        return {"accepted": True, "duplicate": False, "callback_id": callback_id}

    def record_worker_completion(
        self,
        *,
        callback_id: str,
        dispatch_id: str,
        run_id: str,
        runtime_task_id: str,
        lease_id: str,
        worker_pool_id: str,
        execution_target: dict[str, Any],
        lease_renewals: list[dict[str, Any]] | None = None,
        execution_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with unit_of_work(self.db_path) as connection:
            state_ref = self.runtime_state_repo.get_by_task(runtime_task_id, connection=connection)
            if state_ref is None:
                raise EntityNotFoundError("runtime_state_ref", runtime_task_id)
            committed_lease = self._validate_callback_scheduler_context(
                runtime_task_id=runtime_task_id,
                execution_target=execution_target,
                connection=connection,
            )
            registry = self._worker_callback_registry(state_ref)
            if callback_id in registry["completion"]:
                return {"accepted": True, "duplicate": True, "callback_id": callback_id}
            payload_updates: dict[str, Any] = {
                "execution_target": {
                    **execution_target,
                    "last_callback_at": self._utc_now().isoformat(),
                },
                "committed_scheduler_lease": self._scheduler_committed_lease_payload(committed_lease),
            }
            if lease_renewals is not None:
                merged_renewals = self._lease_renewals_for(state_ref, None)
                seen_callback_ids = {
                    item.get("callback_id")
                    for item in merged_renewals
                    if isinstance(item, dict)
                }
                for renewal in lease_renewals:
                    callback_ref = renewal.get("callback_id") if isinstance(renewal, dict) else None
                    if callback_ref and callback_ref in seen_callback_ids:
                        continue
                    if isinstance(renewal, dict):
                        merged_renewals.append(renewal)
                        if callback_ref:
                            seen_callback_ids.add(callback_ref)
                payload_updates["lease_renewals"] = merged_renewals[-20:]
            if execution_result is not None:
                payload_updates["remote_execution_result"] = execution_result
            updated_state = self._append_worker_callback(
                self._state_ref_with_payload_updates(state_ref, payload_updates),
                callback_type="completion",
                callback_id=callback_id,
                payload={
                    "dispatch_id": dispatch_id,
                    "lease_id": lease_id,
                    "return_code": execution_result.get("return_code") if execution_result is not None else None,
                },
            )
            self.runtime_state_repo.upsert(updated_state, connection=connection)
            self.event_repo.append(
                RunEvent(
                    run_id=run_id,
                    event_type=RunEventType.worker_completion_recorded,
                    object_type="runtime_task",
                    object_id=runtime_task_id,
                    summary="Worker completion callback recorded",
                    payload_json={
                        "run_id": run_id,
                        "runtime_task_id": runtime_task_id,
                        "lease_id": lease_id,
                        "worker_pool_id": worker_pool_id,
                        "callback_id": callback_id,
                        "dispatch_id": dispatch_id,
                        "return_code": execution_result.get("return_code") if execution_result is not None else None,
                    },
                ),
                connection=connection,
            )
        return {"accepted": True, "duplicate": False, "callback_id": callback_id}

    def apply_run_repair(self, run_id: str, action: str | None = None) -> dict[str, Any]:
        run = self.get_run(run_id)
        inspection_before = self.inspect_run_state(run_id)
        selected_problem = self._select_repair_problem(run_id, inspection_before["problems"], action)
        selected_action = str(selected_problem["repair_action"])

        if selected_action == "align_completed_runtime_state":
            repaired_runtime_task_ids = self._apply_align_terminal_runtime_state(
                run,
                selected_action,
                str(selected_problem["problem"]),
            )
        elif selected_action == "align_cancelled_runtime_state":
            repaired_runtime_task_ids = self._apply_align_terminal_runtime_state(
                run,
                selected_action,
                str(selected_problem["problem"]),
            )
        elif selected_action == "close_current_runtime_attempt_terminal":
            repaired_runtime_task_ids = self._apply_close_current_attempt_terminal(
                run,
                selected_action,
                str(selected_problem["problem"]),
            )
        elif selected_action == "create_repair_runtime_attempt":
            repaired_runtime_task_ids = self._apply_create_repair_attempt(
                run_id,
                selected_action,
                str(selected_problem["problem"]),
            )
        elif selected_action == "recompile_prepared_run":
            repaired_runtime_task_ids = self._apply_recompile_prepared_run(
                run_id,
                selected_action,
                str(selected_problem["problem"]),
            )
        elif selected_action == "interrupt_current_runtime_attempt":
            repaired_runtime_task_ids = self._apply_interrupt_current_attempt(
                run_id,
                selected_action,
                str(selected_problem["problem"]),
            )
        elif selected_action == "release_runtime_claim":
            repaired_runtime_task_ids = self._apply_claim_release_repair(
                run_id,
                selected_action,
                str(selected_problem["problem"]),
                status=RuntimeClaimStatus.released,
                reason="reconciled_non_running_active_claim",
            )
        elif selected_action == "expire_runtime_claim":
            repaired_runtime_task_ids = self._apply_claim_release_repair(
                run_id,
                selected_action,
                str(selected_problem["problem"]),
                status=RuntimeClaimStatus.expired,
                reason="reconciled_expired_claim",
            )
        elif selected_action == "release_worker_lease":
            repaired_runtime_task_ids = self._apply_worker_lease_release_repair(
                run_id,
                selected_action,
                str(selected_problem["problem"]),
                status=WorkerLeaseStatus.released,
                reason="reconciled_non_running_active_worker_lease",
            )
        elif selected_action == "expire_worker_lease":
            repaired_runtime_task_ids = self._apply_worker_lease_release_repair(
                run_id,
                selected_action,
                str(selected_problem["problem"]),
                status=WorkerLeaseStatus.expired,
                reason="reconciled_expired_worker_lease",
            )
        else:
            raise UnsupportedRepairActionError(selected_action, list(self.SUPPORTED_REPAIR_ACTIONS))

        self._capture_run_snapshot(
            run_id,
            RunSnapshotStage.repaired,
            f"Repair snapshot captured: {selected_action}",
            payload_extra={"repair_action": selected_action, "problem": str(selected_problem["problem"])},
        )
        inspection_after = self.inspect_run_state(run_id)
        updated_run = self.get_run(run_id)
        return {
            "run": updated_run.model_dump(mode="json"),
            "applied": True,
            "action": selected_action,
            "problem": selected_problem["problem"],
            "repaired_runtime_task_ids": repaired_runtime_task_ids,
            "inspection_before": inspection_before,
            "inspection_after": inspection_after,
        }

