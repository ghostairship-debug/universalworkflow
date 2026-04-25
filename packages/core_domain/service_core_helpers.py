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
    PresetNotFoundError,
    PresetRequiredError,
    RepairActionNotAvailableError,
    RuntimeClaimConflictError,
    SchedulerArbitrationError,
    TaskKindNotAllowedError,
    UnsupportedRepairActionError,
    UnsupportedTaskKindError,
    WorkflowError,
)
from packages.core_domain.execution_profiles import build_effective_execution_defaults
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
    CapabilityInvocationRepository,
    CapabilityProbeResultRepository,
    ChatMessageRepository,
    ChatStreamEventRepository,
    ClusterRouteDecisionRepository,
    EventRepository,
    EvidenceRepository,
    FollowupRequestRepository,
    GeneratedAgentProfileRepository,
    HandoffRepository,
    IntentSessionRepository,
    MemoryItemRepository,
    OperatorActionReceiptRepository,
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
from packages.core_domain.service_operator_action import OperatorActionServiceMixin
from packages.core_domain.service_operator_action_guard import OperatorActionGuard
from packages.core_domain.service_projection import ProjectionServiceMixin
from packages.core_domain.service_execution_resolution import resolve_execution_profile_for_service
from packages.core_domain.service_repo_mutation import RepoMutationCoordinator
from packages.core_domain.service_scheduler import SchedulerServiceMixin
from packages.core_domain.service_worker_callbacks import WorkerCallbackServiceMixin
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
from packages.core_domain.local_scheduler_lease_arbiter import LocalSchedulerLeaseArbiter
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
from packages.runtime_langgraph.chat_control_graph import ChatControlGraph
from packages.runtime_langgraph.chat_runtime import ChatLLMRuntime, build_chat_llm_runtime_from_env
from packages.core_domain.service_ownership_lease import OwnershipLeaseService
from packages.core_domain.service_review_policy import ReviewPolicyService
from packages.core_domain.service_run_lifecycle import RunLifecycleService
from packages.worker_adapters.langchain_agent_adapter import LangChainAgentAdapter
from packages.worker_adapters.base import ExecutionResult
from packages.worker_adapters.codex_adapter import CodexAdapter
from packages.worker_adapters.external_artifact_adapters import (
    ClaudeArchitectAdapter,
    MMXMultimodalAdapter,
    VertexMultimodalAdapter,
)
from packages.worker_adapters.noop_adapter import NoopAdapter
from packages.worker_adapters.opencode_adapter import OpenCodeAdapter
from packages.worker_adapters.opencode_session_adapter import OpenCodeSessionAdapter
from packages.worker_adapters.router import WorkerRouter
from packages.worker_adapters.shell_adapter import ShellAdapter




class CoreHelperServiceMixin:
    def get_cluster_route_stats(self, *, days: int = 30) -> dict[str, Any]:
        return self.cluster_route_decision_repo.summarize_recent(days=days)

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
        return Path(str(self.effective_config.get("workspace", {}).get("root") or Path.cwd())).resolve()

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

