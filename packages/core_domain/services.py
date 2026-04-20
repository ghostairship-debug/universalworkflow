from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from packages.contracts import (
    AgentRoleType,
    BudgetLedger,
    CapabilityRoute,
    ExecutionLaneType,
    DomainPackDefinition,
    DomainPackResolution,
    Evidence,
    ExecutionTargetRef,
    HandoffLite,
    LeaseRenewalRecord,
    MCPServerProfile,
    MemoryCandidate,
    MemoryItem,
    MemoryNamespace,
    MemoryRetrievalPreview,
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
    OwnershipActorKind,
    OwnershipDomainKind,
    RunStatus,
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
    PresetNotFoundError,
    PresetRequiredError,
    RepairActionNotAvailableError,
    RuntimeClaimConflictError,
    TaskKindNotAllowedError,
    UnsupportedRepairActionError,
    UnsupportedTaskKindError,
    WorkflowError,
)
from packages.core_domain.memory import (
    MEMORY_RETRIEVAL_PREVIEW_ENV_KEY,
    load_memory_retrieval_preview,
    load_seed_memory_namespaces,
)
from packages.core_domain.simulation import LocalDeterministicSimulationRunner, SimulationPolicyRegistry
from packages.core_domain.evidence_builder import EvidenceBuilder
from packages.core_domain.repositories import (
    BudgetLedgerRepository,
    EventRepository,
    EvidenceRepository,
    HandoffRepository,
    MemoryItemRepository,
    PresetRepository,
    ReviewRepository,
    RunSnapshotRepository,
    RunRepository,
    SimulationRecordRepository,
    RuntimeAttemptRepository,
    RuntimeClaimRepository,
    RuntimeStateRepository,
    TaskRepository,
    WorkerLeaseRepository,
)
from packages.core_domain.resolver import PresetResolver
from packages.core_domain.service_lifecycle import LifecycleServiceMixin
from packages.core_domain.service_memory_simulation import MemorySimulationServiceMixin
from packages.core_domain.service_projection import ProjectionServiceMixin
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
from packages.core_domain.skills import export_domain_pack_skill_bundle
from packages.core_domain.m8_flags import (
    active_feature_flags,
    is_agent_lane_enabled,
    is_durable_pilot_enabled,
    is_external_worker_pools_enabled,
    is_mcp_source_enabled,
    is_skill_export_enabled,
)
from packages.core_domain.observability import NullTraceExporter, TraceExporter, TraceRecord, build_trace_exporter_from_env
from packages.runtime_langgraph.durable_pilot import (
    DurableRuntimePilot,
    NullDurableRuntimePilot,
    build_durable_runtime_pilot_from_env,
)
from packages.runtime_langgraph.gateway import build_runtime_gateway_from_env
from packages.worker_adapters.langchain_agent_adapter import LangChainAgentAdapter
from packages.worker_adapters.base import ExecutionResult
from packages.worker_adapters.noop_adapter import NoopAdapter
from packages.worker_adapters.opencode_adapter import OpenCodeAdapter
from packages.worker_adapters.router import WorkerRouter
from packages.worker_adapters.shell_adapter import ShellAdapter


class OrchestratorService(
    LifecycleServiceMixin,
    MemorySimulationServiceMixin,
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
        self.snapshot_repo = RunSnapshotRepository(self.db_path)
        self.memory_item_repo = MemoryItemRepository(self.db_path)
        self.simulation_record_repo = SimulationRecordRepository(self.db_path)
        self.runtime_gateway = runtime_gateway or build_runtime_gateway_from_env()
        self.capability_plane = capability_plane or CapabilityPlane(workspace_root=self._workspace_root())
        adapters = [shell_adapter or ShellAdapter(), OpenCodeAdapter(), NoopAdapter()]
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
        self.worker_pool_profiles = load_worker_pool_profiles(self.effective_config["worker_pools"]["seed_path"])

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

    def _selected_worker_pool_profile(self) -> Any | None:
        if not is_external_worker_pools_enabled():
            return None
        return resolve_worker_pool_profile(
            self.worker_pool_profiles,
            self.effective_config["worker_pools"]["default_pool_id"],
        )

    def _default_project_delivery_plan(self, run_id: str) -> OrchestrationPlan:
        barrier = OrchestrationBarrier(
            label="coder_researcher_parallel",
            role_ids=[AgentRoleType.coder, AgentRoleType.researcher],
            status="pending",
            member_count=2,
        )
        return OrchestrationPlan(
            run_id=run_id,
            preset_id="project_delivery",
            review_policy=ReviewPolicy.recommended,
            roles=[
                {"role": AgentRoleType.planner, "preset_id": "optional_delivery", "preferred_adapter": "agent", "fallback_adapter": "shell"},
                {"role": AgentRoleType.coder, "preset_id": "feature_delivery", "preferred_adapter": "opencode", "fallback_adapter": "shell"},
                {"role": AgentRoleType.researcher, "preset_id": "optional_delivery", "preferred_adapter": "agent", "fallback_adapter": "shell"},
                {"role": AgentRoleType.reviewer, "preset_id": "advisory_delivery", "preferred_adapter": "agent", "fallback_adapter": "shell"},
                {"role": AgentRoleType.operator, "preset_id": "guarded_delivery", "preferred_adapter": None, "fallback_adapter": None},
            ],
            steps=[
                OrchestrationStep(
                    role=AgentRoleType.planner,
                    title="Generate work breakdown",
                    preset_id="optional_delivery",
                    preferred_adapter="agent",
                    fallback_adapter="shell",
                    sequence_no=1,
                    status="pending",
                ),
                OrchestrationStep(
                    role=AgentRoleType.coder,
                    title="Implement primary delivery slice",
                    preset_id="feature_delivery",
                    preferred_adapter="opencode",
                    fallback_adapter="shell",
                    barrier_id=barrier.barrier_id,
                    sequence_no=2,
                    status="pending",
                ),
                OrchestrationStep(
                    role=AgentRoleType.researcher,
                    title="Research risks and supporting evidence",
                    preset_id="optional_delivery",
                    preferred_adapter="agent",
                    fallback_adapter="shell",
                    barrier_id=barrier.barrier_id,
                    sequence_no=2,
                    status="pending",
                ),
                OrchestrationStep(
                    role=AgentRoleType.reviewer,
                    title="Review implementation and research evidence",
                    preset_id="advisory_delivery",
                    preferred_adapter="agent",
                    fallback_adapter="shell",
                    sequence_no=3,
                    status="pending",
                ),
            ],
            barriers=[barrier],
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

    def get_run_orchestration(self, run_id: str) -> dict[str, Any]:
        context = self._load_run_context(run_id)
        orchestration = self._orchestration_from_context(context)
        if orchestration is None:
            return {"run_id": run_id, "enabled": False, "orchestration": None}
        return {"run_id": run_id, "enabled": True, "orchestration": orchestration}

    def _compile_child_run_with_fallback(
        self,
        run_id: str,
        *,
        preferred_adapter: str | None,
        fallback_adapter: str | None,
    ) -> PreparedRunBundle:
        adapter_candidates = [preferred_adapter, fallback_adapter, None]
        seen: set[str | None] = set()
        for adapter_name in adapter_candidates:
            if adapter_name in seen:
                continue
            seen.add(adapter_name)
            try:
                return self.compile_run(run_id, adapter_name=adapter_name)
            except (
                CapabilityAdapterNotFoundError,
                ExecutionLaneNotAllowedError,
                TaskKindNotAllowedError,
                UnsupportedTaskKindError,
            ):
                continue
        return self.compile_run(run_id)

    def _finalize_child_run_if_waiting(self, run_id: str) -> Run:
        run = self.get_run(run_id)
        if str(run.status) != RunStatus.awaiting_review:
            return run
        return self.approve_run_review(run_id).run

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
        artifact = packet.expected_artifacts[0] if packet.expected_artifacts else "state/artifacts/project_delivery.md"
        path = Path(artifact)
        if not path.is_absolute():
            path = Path(packet.working_directory) / path
        resolved = path.resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return [resolved.as_posix()]

    def _execute_project_delivery_orchestration(self, packet: TaskPacket) -> ExecutionResult:
        from packages.worker_adapters.base import utc_now

        started_at = utc_now()
        orchestration_payload = packet.env.get("WORKFLOW_ORCHESTRATION_PLAN")
        orchestration = (
            OrchestrationPlan.model_validate(json.loads(orchestration_payload))
            if orchestration_payload
            else self._default_project_delivery_plan(packet.run_id)
        )
        parent_goal = packet.env.get("WORKFLOW_RUN_GOAL", "")
        child_runs: list[dict[str, Any]] = []
        role_progress: dict[str, dict[str, Any]] = {}

        planner_step = next(step for step in orchestration.steps if step.role == AgentRoleType.planner)
        planner_run = self.create_run(self._role_goal_for(parent_goal, AgentRoleType.planner), planner_step.preset_id)
        planner_bundle = self._compile_child_run_with_fallback(
            planner_run.run_id,
            preferred_adapter=planner_step.preferred_adapter,
            fallback_adapter=planner_step.fallback_adapter,
        )
        self.resume_run(planner_run.run_id)
        planner_final = self._finalize_child_run_if_waiting(planner_run.run_id)
        if str(planner_final.status) != "completed" and planner_step.fallback_adapter and planner_step.fallback_adapter != planner_step.preferred_adapter:
            planner_run = self.create_run(self._role_goal_for(parent_goal, AgentRoleType.planner), planner_step.preset_id)
            planner_bundle = self._compile_child_run_with_fallback(
                planner_run.run_id,
                preferred_adapter=planner_step.fallback_adapter,
                fallback_adapter=None,
            )
            self.resume_run(planner_run.run_id)
            planner_final = self._finalize_child_run_if_waiting(planner_run.run_id)
        planner_step.run_id = planner_run.run_id
        planner_step.status = str(planner_final.status)
        child_runs.append(
            {
                "role": str(AgentRoleType.planner),
                "run_id": planner_run.run_id,
                "status": str(planner_final.status),
                "runtime_task_id": planner_bundle.task_packet.runtime_task_id,
            }
        )
        role_progress[str(AgentRoleType.planner)] = {"status": str(planner_final.status), "run_id": planner_run.run_id}

        parallel_steps = [step for step in orchestration.steps if step.role in {AgentRoleType.coder, AgentRoleType.researcher}]
        parallel_run_ids: list[str] = []
        for step in parallel_steps:
            child_run = self.create_run(self._role_goal_for(parent_goal, step.role), step.preset_id)
            prepared = self._compile_child_run_with_fallback(
                child_run.run_id,
                preferred_adapter=step.preferred_adapter,
                fallback_adapter=step.fallback_adapter,
            )
            step.run_id = child_run.run_id
            step.status = "prepared"
            parallel_run_ids.append(child_run.run_id)
            child_runs.append(
                {
                    "role": str(step.role),
                    "run_id": child_run.run_id,
                    "status": "prepared",
                    "runtime_task_id": prepared.task_packet.runtime_task_id,
                    "barrier_id": step.barrier_id,
                }
            )
        parallel_result = self.resume_runs_parallel(parallel_run_ids, max_workers=2) if parallel_run_ids else {"results": []}
        for step in parallel_steps:
            finalized = self._finalize_child_run_if_waiting(step.run_id or "")
            if str(finalized.status) != "completed" and step.fallback_adapter and step.fallback_adapter != step.preferred_adapter:
                recovered_run = self.create_run(self._role_goal_for(parent_goal, step.role), step.preset_id)
                recovered_bundle = self._compile_child_run_with_fallback(
                    recovered_run.run_id,
                    preferred_adapter=step.fallback_adapter,
                    fallback_adapter=None,
                )
                self.resume_run(recovered_run.run_id)
                finalized = self._finalize_child_run_if_waiting(recovered_run.run_id)
                step.run_id = recovered_run.run_id
                for child in child_runs:
                    if child["role"] == str(step.role):
                        child["run_id"] = recovered_run.run_id
                        child["runtime_task_id"] = recovered_bundle.task_packet.runtime_task_id
            step.status = str(finalized.status)
            role_progress[str(step.role)] = {
                "status": str(finalized.status),
                "run_id": step.run_id,
                "barrier_id": step.barrier_id,
            }
            for child in child_runs:
                if child["run_id"] == step.run_id:
                    child["status"] = str(finalized.status)
        for barrier in orchestration.barriers:
            barrier.status = "released" if parallel_run_ids else "skipped"

        reviewer_step = next(step for step in orchestration.steps if step.role == AgentRoleType.reviewer)
        reviewer_run = self.create_run(
            self._role_goal_for(parent_goal, AgentRoleType.reviewer, parallel_run_ids=parallel_run_ids),
            reviewer_step.preset_id,
        )
        reviewer_bundle = self._compile_child_run_with_fallback(
            reviewer_run.run_id,
            preferred_adapter=reviewer_step.preferred_adapter,
            fallback_adapter=reviewer_step.fallback_adapter,
        )
        self.resume_run(reviewer_run.run_id)
        reviewer_final = self._finalize_child_run_if_waiting(reviewer_run.run_id)
        if str(reviewer_final.status) != "completed" and reviewer_step.fallback_adapter and reviewer_step.fallback_adapter != reviewer_step.preferred_adapter:
            reviewer_run = self.create_run(
                self._role_goal_for(parent_goal, AgentRoleType.reviewer, parallel_run_ids=parallel_run_ids),
                reviewer_step.preset_id,
            )
            reviewer_bundle = self._compile_child_run_with_fallback(
                reviewer_run.run_id,
                preferred_adapter=reviewer_step.fallback_adapter,
                fallback_adapter=None,
            )
            self.resume_run(reviewer_run.run_id)
            reviewer_final = self._finalize_child_run_if_waiting(reviewer_run.run_id)
        reviewer_step.run_id = reviewer_run.run_id
        reviewer_step.status = str(reviewer_final.status)
        child_runs.append(
            {
                "role": str(AgentRoleType.reviewer),
                "run_id": reviewer_run.run_id,
                "status": str(reviewer_final.status),
                "runtime_task_id": reviewer_bundle.task_packet.runtime_task_id,
            }
        )
        role_progress[str(AgentRoleType.reviewer)] = {"status": str(reviewer_final.status), "run_id": reviewer_run.run_id}

        orchestration_summary = {
            "orchestration_id": orchestration.orchestration_id,
            "execution_mode": orchestration.execution_mode,
            "plan": orchestration.model_dump(mode="json"),
            "child_runs": child_runs,
            "parallel_batch": {
                "barrier_id": orchestration.barriers[0].barrier_id if orchestration.barriers else None,
                "member_count": len(parallel_run_ids),
                "status": orchestration.barriers[0].status if orchestration.barriers else "skipped",
                "results": parallel_result.get("results", []),
            },
            "role_progress": role_progress,
        }
        content_lines = [
            "# Project Delivery Orchestration",
            "",
            f"goal: {parent_goal}",
            f"orchestration_id: {orchestration.orchestration_id}",
            "roles:",
        ]
        for item in child_runs:
            content_lines.append(f"- {item['role']}: {item['run_id']} status={item['status']}")
        artifact_paths = self._write_orchestration_artifact(packet, "\n".join(content_lines) + "\n")
        finished_at = utc_now()
        return_code = 0 if all(item["status"] == "completed" for item in child_runs) else 1
        return ExecutionResult(
            runtime_task_id=packet.runtime_task_id,
            return_code=return_code,
            stdout=json.dumps(orchestration_summary, ensure_ascii=False),
            stderr="" if return_code == 0 else "one or more orchestration child runs did not complete successfully",
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=max(int((finished_at - started_at).total_seconds() * 1000), 0),
            artifact_paths=artifact_paths,
            adapter_name="shell",
            metadata={"orchestration": orchestration_summary},
        )

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
    ) -> ExecutionLaneType:
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

    def list_runs(self, limit: int = 10) -> list[Run]:
        return self.run_repo.list(limit=limit)

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
            "domain_pack_id": snapshot.domain_pack.domain_pack_id if snapshot.domain_pack is not None else None,
            "domain_pack_resolution": (
                snapshot.domain_pack.model_dump(mode="json") if snapshot.domain_pack is not None else None
            ),
            "capability_adapter": snapshot.capability_route.adapter_name if snapshot.capability_route is not None else None,
            "memory_retrieval_preview": (
                snapshot.memory_preview.model_dump(mode="json") if snapshot.memory_preview is not None else None
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

