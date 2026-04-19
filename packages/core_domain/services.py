from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from packages.contracts import (
    BudgetLedger,
    CapabilityRoute,
    ExecutionLaneType,
    DomainPackDefinition,
    DomainPackResolution,
    Evidence,
    HandoffLite,
    MCPServerProfile,
    MemoryCandidate,
    MemoryItem,
    MemoryNamespace,
    MemoryRetrievalPreview,
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
from packages.core_domain.skills import export_domain_pack_skill_bundle
from packages.core_domain.m8_flags import (
    active_feature_flags,
    is_agent_lane_enabled,
    is_durable_pilot_enabled,
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
    ):
        self.db_path = Path(db_path) if db_path is not None else None
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

    def _effective_review_state(self, run: Run, latest_review_verdict: ReviewVerdict | None) -> str:
        if str(run.status) == RunStatus.awaiting_review:
            if latest_review_verdict is None:
                return "human_pending"
            if str(latest_review_verdict.reviewer_type) != ReviewerType.human:
                return "human_pending"
        if latest_review_verdict is None:
            return "not_requested"
        if str(latest_review_verdict.reviewer_type) == ReviewerType.human:
            return "human_approved" if str(latest_review_verdict.decision) == ReviewDecision.pass_ else "human_rejected"
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

    def _utc_now(self) -> datetime:
        return datetime.now(UTC)

    def _workspace_root(self) -> Path:
        return Path.cwd().resolve()

    def _feature_flags(self) -> dict[str, bool]:
        return active_feature_flags()

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
        refs = {
            "thread_id": state_ref.state_payload.get("thread_id"),
            "checkpoint_id": state_ref.state_payload.get("checkpoint_id"),
            "assistant_id": state_ref.state_payload.get("assistant_id"),
        }
        return {key: value for key, value in refs.items() if value}

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
        if snapshot.execution_lane == ExecutionLaneType.durable_incremental:
            payload_updates.update(
                self.durable_runtime_pilot.start(state_ref.run_id, state_ref.runtime_task_id)
            )
        return self._state_ref_with_payload_updates(state_ref, payload_updates)

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
    ) -> RuntimeClaim:
        active_claim = self.runtime_claim_repo.get_active_for_task(runtime_task_id, connection=connection)
        if active_claim is not None:
            raise RuntimeClaimConflictError(
                runtime_task_id,
                active_claim.claim_id,
                active_claim.lease_expires_at.isoformat(),
            )
        claim = RuntimeClaim(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            owner=owner,
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
    ) -> WorkerLease:
        lease = WorkerLease(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            worker_name=worker_name,
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
                    "adapter_name": lease.adapter_name,
                    "heartbeat_at": lease.heartbeat_at.isoformat(),
                    "lease_expires_at": lease.lease_expires_at.isoformat(),
                },
            ),
            connection=connection,
        )
        return lease

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
        snapshot = RunSnapshot(
            run_id=run_id,
            stage=RunSnapshotStage(stage),
            run_status=context.run.status,
            runtime_task_id=runtime_task_id or (context.runtime_tasks[0].runtime_task_id if context.runtime_tasks else None),
            summary=summary,
            snapshot_payload={
                "effective_review_state": self._effective_review_state(context.run, context.latest_review_verdict),
                "runtime_task_ids": [task.runtime_task_id for task in context.runtime_tasks],
                "latest_runtime_graph_step": str(last_runtime_state.graph_step) if last_runtime_state is not None else None,
                "latest_runtime_state_ref_id": last_runtime_state.state_ref_id if last_runtime_state is not None else None,
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

