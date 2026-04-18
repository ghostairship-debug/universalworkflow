from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from packages.contracts import (
    BudgetLedger,
    CapabilityRoute,
    DomainPackDefinition,
    DomainPackResolution,
    Evidence,
    HandoffLite,
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
    RuntimeTask,
    TaskCard,
    TaskKind,
    TaskStatus,
    TaskPacket,
    WorkerLease,
    WorkerLeaseStatus,
    allowed_run_status_transitions,
    can_transition_run_status,
)
from packages.core_domain.auto_review import AutoReviewV0
from packages.core_domain.compile import CompileSnapshot, compile_run as build_compile_snapshot
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
from packages.runtime_langgraph.gateway import build_runtime_gateway_from_env
from packages.worker_adapters.base import ExecutionResult
from packages.worker_adapters.noop_adapter import NoopAdapter
from packages.worker_adapters.opencode_adapter import OpenCodeAdapter
from packages.worker_adapters.router import WorkerRouter
from packages.worker_adapters.shell_adapter import ShellAdapter


@dataclass(slots=True)
class PreparedRunBundle:
    run: Run
    preset: PresetDefinition
    task_packet: TaskPacket
    state_ref: RuntimeStateRef
    handoff: HandoffLite
    domain_pack: DomainPackResolution | None
    capability_route: CapabilityRoute | None
    memory_preview: MemoryRetrievalPreview | None


@dataclass(slots=True)
class ExecutedRunBundle:
    run: Run
    execution_result: ExecutionResult
    evidence: Evidence
    review_verdict: ReviewVerdict | None


@dataclass(slots=True)
class ReviewedRunBundle:
    run: Run
    evidence: Evidence
    review_verdict: ReviewVerdict


@dataclass(slots=True)
class RunDiagnosticContext:
    run: Run
    preset: PresetDefinition | None
    phases: list[Phase]
    task_cards: list[TaskCard]
    runtime_tasks: list[RuntimeTask]
    handoffs: list[HandoffLite]
    runtime_state_refs: list[RuntimeStateRef]
    snapshots: list[RunSnapshot]
    runtime_attempts: list[RuntimeAttempt]
    claims: list[RuntimeClaim]
    worker_leases: list[WorkerLease]
    evidence_by_task: dict[str, Evidence | None]
    latest_review_verdict: ReviewVerdict | None


class OrchestratorService:
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
        domain_pack_registry: DomainPackRegistry | None = None,
        simulation_policy_registry: SimulationPolicyRegistry | None = None,
        evidence_builder: EvidenceBuilder | None = None,
        auto_review: AutoReviewV0 | None = None,
        simulation_runner: LocalDeterministicSimulationRunner | None = None,
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
        self.worker_router = worker_router or WorkerRouter(
            [shell_adapter or ShellAdapter(), OpenCodeAdapter(), NoopAdapter()]
        )
        self.domain_pack_registry = domain_pack_registry or DomainPackRegistry()
        self.simulation_policy_registry = simulation_policy_registry or SimulationPolicyRegistry()
        self.evidence_builder = evidence_builder or EvidenceBuilder()
        self.auto_review = auto_review or AutoReviewV0()
        self.simulation_runner = simulation_runner or LocalDeterministicSimulationRunner()

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

    def _worker_lease_projection(
        self,
        context: RunDiagnosticContext,
        latest_worker_lease: WorkerLease | None,
        active_worker_leases: list[WorkerLease],
        expired_active_worker_leases: list[WorkerLease],
    ) -> dict[str, Any]:
        return {
            "lease_count": len(context.worker_leases),
            "active_lease_count": len(active_worker_leases),
            "expired_active_lease_count": len(expired_active_worker_leases),
            "latest_lease_id": latest_worker_lease.lease_id if latest_worker_lease is not None else None,
            "latest_status": str(latest_worker_lease.status) if latest_worker_lease is not None else None,
            "latest_worker_name": latest_worker_lease.worker_name if latest_worker_lease is not None else None,
            "latest_adapter_name": latest_worker_lease.adapter_name if latest_worker_lease is not None else None,
            "latest_heartbeat_at": (
                latest_worker_lease.heartbeat_at.isoformat() if latest_worker_lease is not None else None
            ),
            "latest_lease_expires_at": (
                latest_worker_lease.lease_expires_at.isoformat() if latest_worker_lease is not None else None
            ),
            "active_lease_ids": [lease.lease_id for lease in active_worker_leases],
            "expired_active_lease_ids": [lease.lease_id for lease in expired_active_worker_leases],
        }

    def _attempt_projection(
        self,
        context: RunDiagnosticContext,
        latest_attempt: RuntimeAttempt | None,
        current_attempt: RuntimeAttempt | None,
    ) -> dict[str, Any]:
        superseded_attempts = self._superseded_attempts(context)
        interrupted_attempts = [
            attempt for attempt in context.runtime_attempts if str(attempt.status) == RuntimeAttemptStatus.interrupted
        ]
        terminal_attempts = [
            attempt
            for attempt in context.runtime_attempts
            if str(attempt.status)
            in {
                RuntimeAttemptStatus.completed,
                RuntimeAttemptStatus.failed,
                RuntimeAttemptStatus.cancelled,
                RuntimeAttemptStatus.interrupted,
            }
        ]
        return {
            "attempt_count": len(context.runtime_attempts),
            "current_attempt_id": current_attempt.attempt_id if current_attempt is not None else None,
            "current_runtime_task_id": current_attempt.runtime_task_id if current_attempt is not None else None,
            "current_trigger": str(current_attempt.trigger) if current_attempt is not None else None,
            "latest_attempt_id": latest_attempt.attempt_id if latest_attempt is not None else None,
            "latest_sequence_no": latest_attempt.sequence_no if latest_attempt is not None else None,
            "latest_status": str(latest_attempt.status) if latest_attempt is not None else None,
            "latest_runtime_task_id": latest_attempt.runtime_task_id if latest_attempt is not None else None,
            "superseded_attempt_ids": [attempt.attempt_id for attempt in superseded_attempts],
            "interrupted_attempt_ids": [attempt.attempt_id for attempt in interrupted_attempts],
            "terminal_attempt_count": len(terminal_attempts),
        }

    def _failure_reason_for(
        self,
        context: RunDiagnosticContext,
        last_runtime_state: RuntimeStateRef | None,
    ) -> str | None:
        if str(context.run.status) != RunStatus.failed:
            return None
        if context.latest_review_verdict is not None and str(context.latest_review_verdict.decision) == ReviewDecision.fail:
            if str(context.latest_review_verdict.reviewer_type) == ReviewerType.human:
                return "human_review_rejected"
            return "auto_review_failed"
        if last_runtime_state is not None and last_runtime_state.state_payload.get("return_code") not in (None, 0):
            return "runtime_return_code_non_zero"
        return "run_failed"

    def _waiting_reason_for(self, context: RunDiagnosticContext, last_evidence: Evidence | None) -> str | None:
        status = str(context.run.status)
        if status == RunStatus.pending:
            return "awaiting_compile"
        if status == RunStatus.prepared:
            return "awaiting_runtime_resume"
        if status == RunStatus.running:
            return "runtime_execution_in_progress"
        if status == RunStatus.awaiting_review:
            return "awaiting_human_review" if last_evidence is not None else "awaiting_human_review_missing_evidence"
        return None

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

    def _default_simulation_policy(self, preset_id: str | None) -> SimulationPolicyDefinition:
        matched_preset_ids = [preset_id] if preset_id is not None else []
        return SimulationPolicyDefinition(
            policy_id="simulation_disabled_unmatched",
            name="Disabled Simulation",
            description="Fallback simulation policy used when no explicit preset match exists.",
            preset_ids=matched_preset_ids,
            trigger_policy=SimulationTriggerPolicy.disabled,
            check_ids=[],
        )

    def _simulation_policy_for_context(self, context: RunDiagnosticContext) -> SimulationPolicyDefinition:
        preset_id = context.preset.preset_id if context.preset is not None else None
        if preset_id is None:
            return self._default_simulation_policy(None)
        return self.simulation_policy_registry.match(preset_id) or self._default_simulation_policy(preset_id)

    def _simulation_report_for(
        self,
        detail: dict[str, Any],
        inspection: dict[str, Any],
    ) -> SimulationReport:
        policy_payload = detail.get("simulation_policy")
        policy = (
            SimulationPolicyDefinition.model_validate(policy_payload)
            if policy_payload is not None
            else self._default_simulation_policy(detail["run"].get("preset_id"))
        )
        return self.simulation_runner.run(policy, detail, inspection)

    def _event_digest_for(self, timeline: list[RunEvent]) -> dict[str, Any]:
        event_type_counts = Counter(str(event.event_type) for event in timeline)
        latest_event = timeline[-1] if timeline else None
        terminal_event = next(
            (
                event
                for event in reversed(timeline)
                if str(event.event_type) in {RunEventType.run_completed, RunEventType.run_failed, RunEventType.run_cancelled}
            ),
            None,
        )
        recent_events = timeline[-5:]
        return {
            "event_count": len(timeline),
            "distinct_event_type_count": len(event_type_counts),
            "event_type_counts": dict(event_type_counts),
            "latest_event_type": str(latest_event.event_type) if latest_event is not None else None,
            "latest_event_at": latest_event.created_at.isoformat() if latest_event is not None else None,
            "terminal_event_type": str(terminal_event.event_type) if terminal_event is not None else None,
            "terminal_event_at": terminal_event.created_at.isoformat() if terminal_event is not None else None,
            "review_requested_count": event_type_counts.get(str(RunEventType.review_requested), 0),
            "review_submitted_count": event_type_counts.get(str(RunEventType.review_submitted), 0),
            "snapshot_event_count": event_type_counts.get(str(RunEventType.run_snapshot_created), 0),
            "repair_event_count": event_type_counts.get(str(RunEventType.repair_applied), 0),
            "recent_event_types": [str(event.event_type) for event in recent_events],
        }

    def _timeline_summary_for(self, timeline: list[RunEvent]) -> dict[str, Any]:
        digest = self._event_digest_for(timeline)
        return {
            "event_count": digest["event_count"],
            "event_type_counts": digest["event_type_counts"],
            "latest_event_type": digest["latest_event_type"],
            "latest_event_at": digest["latest_event_at"],
            "terminal_event_type": digest["terminal_event_type"],
            "repair_event_count": digest["repair_event_count"],
            "recent_event_types": digest["recent_event_types"],
        }

    def _summary_headline_for(
        self,
        detail: dict[str, Any],
        inspection: dict[str, Any],
        failure_taxonomy: dict[str, Any],
    ) -> str:
        run_status = str(detail["run"]["status"])
        if failure_taxonomy["category"] == "inconsistent_state":
            return f"Run {run_status} with {inspection['problem_count']} inspection issue(s)"
        if failure_taxonomy["category"] == "success":
            return "Run completed cleanly"
        if failure_taxonomy["category"] == "review_pending":
            return "Run is waiting for human review"
        if failure_taxonomy["category"] == "operator_cancelled":
            return "Run was cancelled by operator"
        if failure_taxonomy["category"] == "review_failure":
            return f"Run failed during review: {failure_taxonomy['primary_reason']}"
        if failure_taxonomy["category"] == "runtime_failure":
            return f"Run failed during execution: {failure_taxonomy['primary_reason']}"
        return f"Run is {run_status}"

    def _summary_lines_for(
        self,
        detail: dict[str, Any],
        inspection: dict[str, Any],
        failure_taxonomy: dict[str, Any],
        timeline_summary: dict[str, Any],
        simulation_report: SimulationReport,
    ) -> list[str]:
        return [
            (
                f"status={detail['run']['status']} review={detail['effective_review_state']} "
                f"taxonomy={failure_taxonomy['category']}"
            ),
            (
                f"attempts={detail['runtime_attempt_projection']['attempt_count']} "
                f"active_claims={len(detail['active_claims'])} "
                f"active_worker_leases={detail['worker_lease_projection']['active_lease_count']}"
            ),
            (
                f"inspection_problems={inspection['problem_count']} "
                f"latest_event={timeline_summary['latest_event_type']} "
                f"recommended_action={inspection['recommended_action']}"
            ),
            (
                f"simulation={simulation_report.status} "
                f"triggered={simulation_report.triggered} "
                f"policy={simulation_report.trigger_policy}"
            ),
        ]

    def _timeline_highlights_for(self, timeline: list[RunEvent]) -> list[dict[str, Any]]:
        return [
            {
                "event_id": event.event_id,
                "event_type": str(event.event_type),
                "summary": event.summary,
                "object_type": event.object_type,
                "object_id": event.object_id,
                "created_at": event.created_at.isoformat(),
            }
            for event in timeline[-5:]
        ]

    def _review_digest_for(self, detail: dict[str, Any], timeline: list[RunEvent]) -> dict[str, Any]:
        review_requested_events = [
            event for event in timeline if str(event.event_type) == str(RunEventType.review_requested)
        ]
        review_submitted_events = [
            event for event in timeline if str(event.event_type) == str(RunEventType.review_submitted)
        ]
        latest_requested = review_requested_events[-1] if review_requested_events else None
        latest_submitted = review_submitted_events[-1] if review_submitted_events else None
        latest_review_verdict = detail["latest_review_verdict"]
        return {
            "effective_review_state": detail["effective_review_state"],
            "latest_review_verdict": latest_review_verdict,
            "review_requested_count": len(review_requested_events),
            "review_submitted_count": len(review_submitted_events),
            "latest_review_requested_at": latest_requested.created_at.isoformat() if latest_requested is not None else None,
            "latest_review_submitted_at": latest_submitted.created_at.isoformat() if latest_submitted is not None else None,
            "latest_review_decision": (
                latest_review_verdict["decision"] if latest_review_verdict is not None else None
            ),
            "latest_reviewer_type": (
                latest_review_verdict["reviewer_type"] if latest_review_verdict is not None else None
            ),
            "pending_human_review": detail["effective_review_state"] == "human_pending",
        }

    def _closure_expectation_for(self, run_status: str) -> dict[str, Any]:
        if run_status == RunStatus.prepared:
            return {
                "required_event_type": str(RunEventType.run_compiled),
                "required_snapshot_stage": str(RunSnapshotStage.compiled),
                "terminal": False,
            }
        if run_status == RunStatus.awaiting_review:
            return {
                "required_event_type": str(RunEventType.review_requested),
                "required_snapshot_stage": str(RunSnapshotStage.awaiting_review),
                "terminal": False,
            }
        if run_status == RunStatus.completed:
            return {
                "required_event_type": str(RunEventType.run_completed),
                "required_snapshot_stage": str(RunSnapshotStage.completed),
                "terminal": True,
            }
        if run_status == RunStatus.failed:
            return {
                "required_event_type": str(RunEventType.run_failed),
                "required_snapshot_stage": str(RunSnapshotStage.failed),
                "terminal": True,
            }
        if run_status == RunStatus.cancelled:
            return {
                "required_event_type": str(RunEventType.run_cancelled),
                "required_snapshot_stage": str(RunSnapshotStage.cancelled),
                "terminal": True,
            }
        return {
            "required_event_type": None,
            "required_snapshot_stage": None,
            "terminal": False,
        }

    def _closure_audit_for(
        self,
        detail: dict[str, Any],
        inspection: dict[str, Any],
        event_digest: dict[str, Any],
        review_digest: dict[str, Any],
    ) -> dict[str, Any]:
        run_status = str(detail["run"]["status"])
        latest_snapshot = detail["latest_snapshot"]
        expectation = self._closure_expectation_for(run_status)
        required_event_type = expectation["required_event_type"]
        required_snapshot_stage = expectation["required_snapshot_stage"]
        missing_requirements: list[str] = []
        notes: list[str] = []

        if required_event_type is not None and event_digest["event_type_counts"].get(required_event_type, 0) == 0:
            missing_requirements.append(f"missing_event:{required_event_type}")

        if expectation["terminal"]:
            if event_digest["terminal_event_type"] != required_event_type:
                missing_requirements.append(f"missing_terminal_event:{required_event_type}")
            if latest_snapshot is None or latest_snapshot["stage"] != required_snapshot_stage:
                missing_requirements.append(f"missing_terminal_snapshot:{required_snapshot_stage}")
            if detail["current_runtime_attempt"] is not None:
                missing_requirements.append("terminal_run_has_live_attempt")
            if detail["active_claims"]:
                missing_requirements.append("terminal_run_has_active_claims")
            if detail["active_worker_leases"]:
                missing_requirements.append("terminal_run_has_active_worker_leases")
            if review_digest["effective_review_state"] == "human_pending":
                missing_requirements.append("terminal_run_still_review_pending")
        else:
            if required_snapshot_stage is not None and (
                latest_snapshot is None or latest_snapshot["stage"] != required_snapshot_stage
            ):
                missing_requirements.append(f"missing_snapshot:{required_snapshot_stage}")
            if run_status == RunStatus.awaiting_review and event_digest["terminal_event_type"] is not None:
                missing_requirements.append("awaiting_review_has_terminal_event")

        if review_digest["effective_review_state"] in {
            "auto_passed",
            "auto_failed",
            "human_approved",
            "human_rejected",
        } and review_digest["review_submitted_count"] == 0:
            missing_requirements.append("missing_review_submission_event")

        if run_status == RunStatus.awaiting_review and review_digest["review_requested_count"] == 0:
            missing_requirements.append("missing_review_request_event")

        if inspection["problem_count"] > 0:
            notes.append(f"state inspection reports {inspection['problem_count']} issue(s)")

        passed = not missing_requirements and inspection["problem_count"] == 0
        if missing_requirements:
            state = "closure_gap_detected"
        elif inspection["problem_count"] > 0:
            state = "closed_with_state_issues" if expectation["terminal"] else "open_with_state_issues"
        elif expectation["terminal"]:
            state = "closed"
        elif run_status == RunStatus.awaiting_review:
            state = "awaiting_review"
        elif run_status == RunStatus.prepared:
            state = "prepared"
        else:
            state = "open"

        if missing_requirements:
            if any(item.startswith("missing_terminal_") for item in missing_requirements):
                recommended_action = "inspect_timeline_and_reconcile"
            elif any("review" in item for item in missing_requirements):
                recommended_action = "inspect_review_closure"
            else:
                recommended_action = detail["recoverability_hint"]
        elif inspection["problem_count"] > 0:
            recommended_action = inspection["recommended_action"]
        else:
            recommended_action = detail["next_action"] if not expectation["terminal"] else "none"

        return {
            "passed": passed,
            "state": state,
            "required_event_type": required_event_type,
            "required_snapshot_stage": required_snapshot_stage,
            "has_terminal_event": event_digest["terminal_event_type"] == required_event_type if expectation["terminal"] else False,
            "has_required_snapshot": (
                latest_snapshot is not None and latest_snapshot["stage"] == required_snapshot_stage
                if required_snapshot_stage is not None
                else False
            ),
            "missing_requirements": missing_requirements,
            "notes": notes,
            "recommended_action": recommended_action,
        }

    def _build_event_inspection(
        self,
        detail: dict[str, Any],
        inspection: dict[str, Any],
        timeline: list[RunEvent],
    ) -> dict[str, Any]:
        event_digest = self._event_digest_for(timeline)
        review_digest = self._review_digest_for(detail, timeline)
        closure_audit = self._closure_audit_for(detail, inspection, event_digest, review_digest)
        return {
            "run": detail["run"],
            "event_digest": event_digest,
            "review_digest": review_digest,
            "closure_audit": closure_audit,
            "timeline_highlights": self._timeline_highlights_for(timeline),
            "operator_projection": {
                "status": detail["run"]["status"],
                "next_action": detail["next_action"],
                "recoverability_hint": detail["recoverability_hint"],
                "inspection_problem_count": inspection["problem_count"],
            },
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

    def list_domain_packs(self) -> list[DomainPackDefinition]:
        return self.domain_pack_registry.list()

    def list_memory_namespaces(self) -> list[MemoryNamespace]:
        return load_seed_memory_namespaces()

    def list_memory_items(
        self,
        *,
        run_id: str | None = None,
        namespace_id: str | None = None,
    ) -> list[MemoryItem]:
        return self.memory_item_repo.list(run_id=run_id, namespace_id=namespace_id)

    def _memory_candidate_id(self, run_id: str, namespace_id: str) -> str:
        return f"memcand_{run_id}_{namespace_id}"

    def preview_domain_pack_resolution(
        self,
        preset_id: str,
        task_kind: TaskKind | str | None = None,
        adapter_name: str | None = None,
    ) -> dict[str, Any]:
        preset = self.preset_repo.get(preset_id)
        if preset is None:
            raise PresetNotFoundError(f"preset not found: {preset_id}")
        resolved_task_kind = self._resolve_task_kind(preset, task_kind)
        domain_pack = self._resolve_domain_pack(preset, resolved_task_kind)
        selected_adapter = adapter_name or (
            domain_pack.capability_exposure.preferred_adapter_name if domain_pack is not None else None
        )
        capability_route = self._resolve_capability_route(resolved_task_kind, requested_adapter=selected_adapter)
        return {
            "preset": preset.model_dump(mode="json"),
            "task_kind": str(resolved_task_kind),
            "domain_pack": domain_pack.model_dump(mode="json") if domain_pack is not None else None,
            "capability_resolution": capability_route.model_dump(mode="json") if capability_route is not None else None,
            "resolved": domain_pack is not None,
        }

    def validate_domain_pack_catalog(self) -> dict[str, Any]:
        return self.domain_pack_registry.validate_catalog(self.list_presets(), self.list_capability_routes())

    def list_capability_routes(self) -> list[dict[str, str]]:
        return self.worker_router.routes()

    def runtime_gateway_status(self) -> dict[str, Any]:
        return self.runtime_gateway.describe()

    def list_runs(self, limit: int = 10) -> list[Run]:
        return self.run_repo.list(limit=limit)

    def list_simulation_policies(self) -> list[SimulationPolicyDefinition]:
        return self.simulation_policy_registry.list()

    def get_run_memory_candidates(self, run_id: str) -> list[MemoryCandidate]:
        detail = self.get_status_detail(run_id)
        summary = self.get_run_summary(run_id)
        inspection = self.inspect_run_state(run_id)
        audit_report = self.get_run_audit_report(run_id)
        timeline = self.get_timeline(run_id)
        runtime_task_ids = detail.get("runtime_task_ids", [])
        latest_review = detail.get("latest_review_verdict")
        domain_pack = detail.get("domain_pack")
        namespaces = {item.namespace_id: item for item in self.list_memory_namespaces()}

        candidates: list[MemoryCandidate] = []
        if "repo" in namespaces:
            candidates.append(
                MemoryCandidate(
                    candidate_id=self._memory_candidate_id(run_id, "repo"),
                    run_id=run_id,
                    namespace_id="repo",
                    title=f"Run summary for {detail['run']['preset_id']}",
                    summary=summary["headline"],
                    tags=[
                        detail["run"]["status"],
                        detail["review_policy"],
                        domain_pack["domain_pack_id"] if domain_pack is not None else "no_domain_pack",
                    ],
                    source_refs=[
                        f"run:{run_id}",
                        *[f"task:{task_id}" for task_id in runtime_task_ids],
                    ],
                )
            )
        if "policy" in namespaces:
            candidates.append(
                MemoryCandidate(
                    candidate_id=self._memory_candidate_id(run_id, "policy"),
                    run_id=run_id,
                    namespace_id="policy",
                    title=f"Review policy outcome for {run_id}",
                    summary=(
                        f"Policy `{detail['review_policy']}` ended in "
                        f"`{detail['effective_review_state']}` with next action `{detail['next_action']}`."
                    ),
                    tags=[detail["review_policy"], detail["effective_review_state"]],
                    source_refs=[
                        f"run:{run_id}",
                        *( [f"verdict:{latest_review['verdict_id']}"] if latest_review is not None else [] ),
                    ],
                )
            )
        failure_category = summary["failure_taxonomy"]["category"]
        if failure_category != "success" and "failure" in namespaces:
            candidates.append(
                MemoryCandidate(
                    candidate_id=self._memory_candidate_id(run_id, "failure"),
                    run_id=run_id,
                    namespace_id="failure",
                    title=f"Failure memory candidate for {run_id}",
                    summary=(
                        f"Failure category `{failure_category}` with closure state "
                        f"`{audit_report['review_packet']['closure_summary']['state']}`."
                    ),
                    tags=[
                        failure_category,
                        detail["run"]["status"],
                        detail["failure_reason"] or "no_failure_reason",
                    ],
                    source_refs=[f"run:{run_id}", "audit:run_audit_report"],
                )
            )
        if detail["run"]["status"] == RunStatus.completed and "release" in namespaces:
            candidates.append(
                MemoryCandidate(
                    candidate_id=self._memory_candidate_id(run_id, "release"),
                    run_id=run_id,
                    namespace_id="release",
                    title=f"Release-ready candidate for {run_id}",
                    summary=(
                        f"Completed run with review state `{detail['effective_review_state']}` and "
                        f"{inspection['problem_count']} inspection problems."
                    ),
                    tags=[
                        "completed",
                        detail["effective_review_state"],
                        domain_pack["domain_pack_id"] if domain_pack is not None else "generic",
                    ],
                    source_refs=[
                        f"run:{run_id}",
                        *( [f"event:{event.event_id}" for event in timeline[-3:]] ),
                    ],
                )
            )
        return candidates

    def materialize_run_memory_candidate(self, run_id: str, candidate_id: str) -> MemoryItem:
        candidates = self.get_run_memory_candidates(run_id)
        selected_candidate = next((item for item in candidates if item.candidate_id == candidate_id), None)
        if selected_candidate is None:
            raise EntityNotFoundError("memory_candidate", candidate_id)

        existing_item = self.memory_item_repo.get_by_source_candidate(candidate_id)
        if existing_item is not None:
            return existing_item

        with unit_of_work(self.db_path) as connection:
            memory_item = MemoryItem(
                run_id=run_id,
                namespace_id=selected_candidate.namespace_id,
                source_candidate_id=selected_candidate.candidate_id,
                title=selected_candidate.title,
                summary=selected_candidate.summary,
                tags=selected_candidate.tags,
                source_refs=selected_candidate.source_refs,
            )
            self.memory_item_repo.create(memory_item, connection=connection)
            self.event_repo.append(
                RunEvent(
                    run_id=run_id,
                    event_type=RunEventType.memory_item_materialized,
                    object_type="memory_item",
                    object_id=memory_item.memory_item_id,
                    summary=f"Memory item materialized in namespace `{memory_item.namespace_id}`",
                    payload_json={
                        "run_id": run_id,
                        "memory_item_id": memory_item.memory_item_id,
                        "namespace_id": memory_item.namespace_id,
                        "source_candidate_id": memory_item.source_candidate_id,
                    },
                ),
                connection=connection,
            )
        return memory_item

    def preview_memory_retrieval(
        self,
        *,
        preset_id: str | None = None,
        run_id: str | None = None,
        namespace_id: str | None = None,
        memory_item_ids: list[str] | None = None,
        limit: int = 5,
    ) -> MemoryRetrievalPreview:
        if run_id is not None:
            self.get_run(run_id)
        if preset_id is not None and self.preset_repo.get(preset_id) is None:
            raise PresetNotFoundError(f"preset not found: {preset_id}")

        items = self.list_memory_items(run_id=run_id, namespace_id=namespace_id)

        if preset_id is not None:
            items = [
                item
                for item in items
                if (origin_run := self.run_repo.get(item.run_id)) is not None and origin_run.preset_id == preset_id
            ]

        items = sorted(items, key=lambda item: (item.created_at, item.memory_item_id), reverse=True)

        if memory_item_ids:
            item_by_id = {item.memory_item_id: item for item in items}
            missing_item_ids = [item_id for item_id in memory_item_ids if item_id not in item_by_id]
            if missing_item_ids:
                raise EntityNotFoundError("memory_item", ",".join(missing_item_ids))
            selected_items = [item_by_id[item_id] for item_id in memory_item_ids]
        else:
            selected_items = items[:limit]

        namespace_ids = list(dict.fromkeys(item.namespace_id for item in selected_items))
        source_run_ids = list(dict.fromkeys(item.run_id for item in selected_items))
        brief_lines = [f"[{item.namespace_id}] {item.title}: {item.summary}" for item in selected_items]

        return MemoryRetrievalPreview(
            run_id=run_id,
            preset_id=preset_id,
            namespace_ids=namespace_ids,
            selected_memory_item_ids=[item.memory_item_id for item in selected_items],
            source_run_ids=source_run_ids,
            item_count=len(selected_items),
            brief_lines=brief_lines,
            items=selected_items,
        )

    def get_run_simulation(self, run_id: str) -> SimulationReport:
        detail = self.get_status_detail(run_id)
        inspection = self.inspect_run_state(run_id)
        return self._simulation_report_for(detail, inspection)

    def _persist_simulation_record(
        self,
        run_id: str,
        report: SimulationReport,
        *,
        recorded_from: SimulationRecordSource,
        connection,
    ) -> SimulationRecord:
        record = SimulationRecord(
            run_id=run_id,
            policy_id=report.policy_id,
            status=report.status,
            triggered=report.triggered,
            summary=report.summary,
            recorded_from=recorded_from,
            report=report,
        )
        self.simulation_record_repo.create(record, connection=connection)
        self.event_repo.append(
            RunEvent(
                run_id=run_id,
                event_type=RunEventType.simulation_recorded,
                object_type="simulation_record",
                object_id=record.record_id,
                summary=f"Simulation record persisted ({record.recorded_from})",
                payload_json={
                    "run_id": run_id,
                    "record_id": record.record_id,
                    "policy_id": record.policy_id,
                    "status": record.status,
                    "triggered": record.triggered,
                    "recorded_from": record.recorded_from,
                },
            ),
            connection=connection,
        )
        return record

    def _record_lifecycle_simulation_if_triggered(
        self,
        run_id: str,
        recorded_from: SimulationRecordSource,
    ) -> SimulationRecord | None:
        self.get_run(run_id)
        report = self.get_run_simulation(run_id)
        if not report.triggered:
            return None
        with unit_of_work(self.db_path) as connection:
            return self._persist_simulation_record(
                run_id,
                report,
                recorded_from=recorded_from,
                connection=connection,
            )

    def record_run_simulation(
        self,
        run_id: str,
        recorded_from: SimulationRecordSource = SimulationRecordSource.manual_request,
    ) -> SimulationRecord:
        self.get_run(run_id)
        report = self.get_run_simulation(run_id)
        with unit_of_work(self.db_path) as connection:
            return self._persist_simulation_record(
                run_id,
                report,
                recorded_from=recorded_from,
                connection=connection,
            )

    def list_simulation_records(self, run_id: str) -> list[SimulationRecord]:
        self.get_run(run_id)
        return self.simulation_record_repo.list_for_run(run_id)

    def get_dashboard_snapshot(self, *, focus_run_id: str | None = None, limit: int = 8) -> dict[str, Any]:
        runs = self.list_runs(limit=limit)
        run_rows: list[dict[str, Any]] = []
        for run in runs:
            detail = self.get_status_detail(run.run_id)
            run_rows.append(
                {
                    "run_id": run.run_id,
                    "goal": run.goal,
                    "preset_id": run.preset_id,
                    "status": run.status,
                    "updated_at": run.updated_at.isoformat(),
                    "effective_review_state": detail["effective_review_state"],
                    "next_action": detail["next_action"],
                    "failure_reason": detail["failure_reason"],
                    "waiting_reason": detail["waiting_reason"],
                    "domain_pack_id": (
                        detail["domain_pack"]["domain_pack_id"] if detail["domain_pack"] is not None else None
                    ),
                    "capability_adapter": (
                        detail["capability_resolution"]["adapter_name"]
                        if detail["capability_resolution"] is not None
                        else None
                    ),
                }
            )

        selected_run_id = focus_run_id or (run_rows[0]["run_id"] if run_rows else None)
        focus_detail = self.get_status_detail(selected_run_id) if selected_run_id is not None else None
        focus_summary = self.get_run_summary(selected_run_id) if selected_run_id is not None else None
        timeline_tail = (
            [event.model_dump(mode="json") for event in self.get_timeline(selected_run_id)[-8:]]
            if selected_run_id is not None
            else []
        )
        return {
            "runtime_gateway": self.runtime_gateway.describe(),
            "run_count": len(run_rows),
            "selected_run_id": selected_run_id,
            "runs": run_rows,
            "focus_detail": focus_detail,
            "focus_summary": focus_summary,
            "timeline_tail": timeline_tail,
        }

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
        return RuntimeStateRef.model_validate(
            {
                **state_ref.model_dump(mode="json"),
                "state_payload": payload,
            }
        )

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

    def get_run_summary(self, run_id: str) -> dict[str, Any]:
        detail = self.get_status_detail(run_id)
        inspection = self.inspect_run_state(run_id)
        timeline = self.get_timeline(run_id)
        failure_taxonomy = self._failure_taxonomy_for(detail, inspection)
        timeline_summary = self._timeline_summary_for(timeline)
        event_inspection = self._build_event_inspection(detail, inspection, timeline)
        simulation_report = self._simulation_report_for(detail, inspection)
        headline = self._summary_headline_for(detail, inspection, failure_taxonomy)
        return {
            "run": detail["run"],
            "headline": headline,
            "summary_lines": self._summary_lines_for(
                detail,
                inspection,
                failure_taxonomy,
                timeline_summary,
                simulation_report,
            ),
            "execution_profile": {
                "review_policy": detail["review_policy"],
                "domain_pack": detail["domain_pack"],
                "capability_resolution": detail["capability_resolution"],
                "simulation_policy": detail["simulation_policy"],
            },
            "failure_taxonomy": failure_taxonomy,
            "simulation_summary": {
                "policy_id": simulation_report.policy_id,
                "trigger_policy": simulation_report.trigger_policy,
                "triggered": simulation_report.triggered,
                "status": simulation_report.status,
                "finding_codes": simulation_report.finding_codes,
                "recommended_action": simulation_report.recommended_action,
                "latest_record_id": (
                    detail["latest_simulation_record"]["record_id"]
                    if detail.get("latest_simulation_record") is not None
                    else None
                ),
            },
            "review_summary": event_inspection["review_digest"],
            "inspection_summary": {
                "passed": inspection["passed"],
                "problem_count": inspection["problem_count"],
                "repairable_problem_count": inspection["repairable_problem_count"],
                "recommended_action": inspection["recommended_action"],
                "problem_codes": [str(problem["problem"]) for problem in inspection["problems"]],
            },
            "timeline_summary": timeline_summary,
            "closure_summary": event_inspection["closure_audit"],
            "ownership_summary": {
                "runtime_attempt_projection": detail["runtime_attempt_projection"],
                "latest_claim": detail["latest_claim"],
                "worker_lease_projection": detail["worker_lease_projection"],
            },
            "next_action": detail["next_action"],
            "recoverability_hint": detail["recoverability_hint"],
        }

    def get_event_inspection(self, run_id: str) -> dict[str, Any]:
        detail = self.get_status_detail(run_id)
        inspection = self.inspect_run_state(run_id)
        timeline = self.get_timeline(run_id)
        return self._build_event_inspection(detail, inspection, timeline)

    def get_run_audit_report(self, run_id: str) -> dict[str, Any]:
        detail = self.get_status_detail(run_id)
        summary = self.get_run_summary(run_id)
        inspection = self.inspect_run_state(run_id)
        simulation_report = self._simulation_report_for(detail, inspection)
        event_inspection = self.get_event_inspection(run_id)
        timeline = self.get_timeline(run_id)
        timeline_tail = [event.model_dump(mode="json") for event in timeline[-10:]]
        return {
            "audit_version": "m3_phase_3_v1",
            "report_generated_at": self._utc_now().isoformat(),
            "run": detail["run"],
            "summary": summary,
            "event_inspection": event_inspection,
            "state_inspection": inspection,
            "simulation_report": simulation_report.model_dump(mode="json"),
            "latest_simulation_record": detail["latest_simulation_record"],
            "review_packet": {
                "effective_review_state": summary["review_summary"]["effective_review_state"],
                "latest_review_verdict": summary["review_summary"]["latest_review_verdict"],
                "closure_summary": summary["closure_summary"],
                "next_action": summary["next_action"],
                "recoverability_hint": summary["recoverability_hint"],
            },
            "timeline_tail": timeline_tail,
            "timeline_overview": {
                "event_count": summary["timeline_summary"]["event_count"],
                "latest_event_type": summary["timeline_summary"]["latest_event_type"],
                "recent_event_types": summary["timeline_summary"]["recent_event_types"],
            },
        }

    def get_status_detail(self, run_id: str) -> dict[str, Any]:
        context = self._load_run_context(run_id)
        runtime_task = self._runtime_task_for_context(context)
        domain_pack = self._domain_pack_for_context(context)
        memory_preview = self._memory_preview_for_context(context)
        simulation_policy = self._simulation_policy_for_context(context)
        capability_route = self._capability_route_for_runtime_task(runtime_task)
        last_runtime_state = self._last_runtime_state(context)
        last_evidence = self._last_evidence(context)
        latest_attempt = self._last_attempt(context)
        current_attempt = self._current_attempt(context)
        latest_claim = self._last_claim(context)
        latest_worker_lease = self._last_worker_lease(context)
        latest_snapshot = self._last_snapshot(context)
        latest_simulation_record = self.simulation_record_repo.latest_for_run(run_id)
        budget_ledger = self.budget_repo.get_by_run(run_id)
        active_claims = self._active_claims_for(context)
        active_worker_leases = self._active_worker_leases_for(context)
        expired_active_worker_leases = self._expired_active_worker_leases(context)
        inspection_problems = self._inspect_context(context)
        return {
            "run": context.run.model_dump(mode="json"),
            "runtime_gateway": self.runtime_gateway.describe(),
            "review_policy": str(context.preset.default_review_policy) if context.preset is not None else None,
            "domain_pack": domain_pack.model_dump(mode="json") if domain_pack is not None else None,
            "memory_retrieval_preview": memory_preview.model_dump(mode="json") if memory_preview is not None else None,
            "simulation_policy": simulation_policy.model_dump(mode="json"),
            "capability_resolution": capability_route.model_dump(mode="json") if capability_route is not None else None,
            "runtime_tasks": [task.model_dump(mode="json") for task in context.runtime_tasks],
            "runtime_task_ids": [task.runtime_task_id for task in context.runtime_tasks],
            "handoffs": [handoff.model_dump(mode="json") for handoff in context.handoffs],
            "runtime_state_refs": [state_ref.model_dump(mode="json") for state_ref in context.runtime_state_refs],
            "snapshot_count": len(context.snapshots),
            "latest_snapshot": self._serialize_snapshot(latest_snapshot),
            "latest_simulation_record": self._serialize_contract(latest_simulation_record),
            "budget_ledger": budget_ledger.model_dump(mode="json") if budget_ledger is not None else None,
            "budget_projection": self._budget_projection(budget_ledger),
            "runtime_attempts": [attempt.model_dump(mode="json") for attempt in context.runtime_attempts],
            "latest_runtime_attempt": self._serialize_attempt(latest_attempt),
            "current_runtime_attempt": self._serialize_attempt(current_attempt),
            "runtime_attempt_projection": self._attempt_projection(context, latest_attempt, current_attempt),
            "claims": [claim.model_dump(mode="json") for claim in context.claims],
            "active_claims": [claim.model_dump(mode="json") for claim in active_claims],
            "latest_claim": self._serialize_claim(latest_claim),
            "worker_leases": [lease.model_dump(mode="json") for lease in context.worker_leases],
            "active_worker_leases": [lease.model_dump(mode="json") for lease in active_worker_leases],
            "latest_worker_lease": self._serialize_worker_lease(latest_worker_lease),
            "worker_lease_projection": self._worker_lease_projection(
                context,
                latest_worker_lease,
                active_worker_leases,
                expired_active_worker_leases,
            ),
            "latest_review_verdict": self._serialize_contract(context.latest_review_verdict),
            "last_review_verdict": self._serialize_contract(context.latest_review_verdict),
            "effective_review_state": self._effective_review_state(context.run, context.latest_review_verdict),
            "next_action": self._next_action_for(str(context.run.status)),
            "failure_reason": self._failure_reason_for(context, last_runtime_state),
            "waiting_reason": self._waiting_reason_for(context, last_evidence),
            "last_runtime_state": self._serialize_contract(last_runtime_state),
            "recoverability_hint": self._recoverability_hint_for(context, inspection_problems),
        }

    def inspect_run_state(self, run_id: str) -> dict[str, Any]:
        context = self._load_run_context(run_id)
        runtime_task = self._runtime_task_for_context(context)
        domain_pack = self._domain_pack_for_context(context)
        memory_preview = self._memory_preview_for_context(context)
        simulation_policy = self._simulation_policy_for_context(context)
        capability_route = self._capability_route_for_runtime_task(runtime_task)
        problems = self._inspect_context(context)
        last_runtime_state = self._last_runtime_state(context)
        latest_attempt = self._last_attempt(context)
        current_attempt = self._current_attempt(context)
        latest_snapshot = self._last_snapshot(context)
        latest_simulation_record = self.simulation_record_repo.latest_for_run(run_id)
        latest_worker_lease = self._last_worker_lease(context)
        budget_ledger = self.budget_repo.get_by_run(run_id)
        active_claims = self._active_claims_for(context)
        active_worker_leases = self._active_worker_leases_for(context)
        expired_active_worker_leases = self._expired_active_worker_leases(context)
        repairable_problem_count = sum(1 for problem in problems if problem["repairable"])
        return {
            "run": context.run.model_dump(mode="json"),
            "runtime_gateway": self.runtime_gateway.describe(),
            "review_policy": str(context.preset.default_review_policy) if context.preset is not None else None,
            "domain_pack": domain_pack.model_dump(mode="json") if domain_pack is not None else None,
            "memory_retrieval_preview": memory_preview.model_dump(mode="json") if memory_preview is not None else None,
            "simulation_policy": simulation_policy.model_dump(mode="json"),
            "capability_resolution": capability_route.model_dump(mode="json") if capability_route is not None else None,
            "effective_review_state": self._effective_review_state(context.run, context.latest_review_verdict),
            "last_runtime_state": self._serialize_contract(last_runtime_state),
            "latest_snapshot": self._serialize_snapshot(latest_snapshot),
            "latest_simulation_record": self._serialize_contract(latest_simulation_record),
            "runtime_attempts": [attempt.model_dump(mode="json") for attempt in context.runtime_attempts],
            "latest_runtime_attempt": self._serialize_attempt(latest_attempt),
            "current_runtime_attempt": self._serialize_attempt(current_attempt),
            "runtime_attempt_projection": self._attempt_projection(context, latest_attempt, current_attempt),
            "budget_projection": self._budget_projection(budget_ledger),
            "active_claims": [claim.model_dump(mode="json") for claim in active_claims],
            "active_worker_leases": [lease.model_dump(mode="json") for lease in active_worker_leases],
            "latest_worker_lease": self._serialize_worker_lease(latest_worker_lease),
            "worker_lease_projection": self._worker_lease_projection(
                context,
                latest_worker_lease,
                active_worker_leases,
                expired_active_worker_leases,
            ),
            "passed": not problems,
            "problem_count": len(problems),
            "repairable_problem_count": repairable_problem_count,
            "apply_supported": repairable_problem_count > 0,
            "problems": problems,
            "recommended_action": problems[0]["next_action"] if problems else "none",
        }

    def reconcile_run(self, run_id: str) -> dict[str, Any]:
        return self.inspect_run_state(run_id)

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

    def _snapshot_for_run(
        self,
        run: Run,
        preset: PresetDefinition,
        requested_task_kind: TaskKind | str | None = None,
        requested_adapter: str | None = None,
        memory_item_ids: list[str] | None = None,
    ) -> CompileSnapshot:
        resolved_task_kind = self._resolve_task_kind(preset, requested_task_kind)
        domain_pack = self._resolve_domain_pack(preset, resolved_task_kind)
        selected_adapter = requested_adapter or (
            domain_pack.capability_exposure.preferred_adapter_name if domain_pack is not None else None
        )
        capability_route = self._resolve_capability_route(resolved_task_kind, requested_adapter=selected_adapter)
        memory_preview = (
            self.preview_memory_retrieval(preset_id=preset.preset_id, memory_item_ids=memory_item_ids)
            if memory_item_ids
            else None
        )
        return build_compile_snapshot(
            run.goal,
            preset,
            run.run_id,
            task_kind=resolved_task_kind,
            domain_pack=domain_pack,
            capability_route=capability_route,
            memory_preview=memory_preview,
        )

    def compile_run(
        self,
        run_id: str,
        task_kind: TaskKind | str | None = None,
        adapter_name: str | None = None,
        memory_item_ids: list[str] | None = None,
    ) -> PreparedRunBundle:
        run = self.get_run(run_id)
        self._require_status(run, "compile", [RunStatus.pending])
        preset = self.preset_repo.get(run.preset_id)
        if preset is None:
            raise PresetNotFoundError(f"preset not found: {run.preset_id}")
        snapshot = self._snapshot_for_run(
            run,
            preset,
            task_kind,
            requested_adapter=adapter_name,
            memory_item_ids=memory_item_ids,
        )

        with unit_of_work(self.db_path) as connection:
            self._ensure_budget_ledger(run, preset, connection=connection, compile_count=1)
            self.task_repo.create_phase(snapshot.compile_phase, connection=connection)
            self.task_repo.create_phase(snapshot.execution_phase, connection=connection)
            self.task_repo.create_task_card(snapshot.task_card, connection=connection)
            self.task_repo.create_runtime_task(snapshot.runtime_task, connection=connection)
            self.task_repo.create_task_packet(snapshot.task_packet, connection=connection)
            self.handoff_repo.create(snapshot.handoff, connection=connection)
            self._create_runtime_attempt(
                run.run_id,
                snapshot.runtime_task.runtime_task_id,
                trigger=RuntimeAttemptTrigger.compile,
                connection=connection,
            )
            state_ref = self._state_ref_with_compile_context(
                self.runtime_gateway.start(run.run_id, snapshot.runtime_task.runtime_task_id),
                run,
                preset,
                snapshot,
            )
            stored_state_ref = self.runtime_state_repo.upsert(state_ref, connection=connection)
            updated_run = self._transition_run_status(run, "compile", RunStatus.prepared, connection=connection)
            for phase in (snapshot.compile_phase, snapshot.execution_phase):
                self.event_repo.append(
                    RunEvent(
                        run_id=run.run_id,
                        event_type=RunEventType.phase_created,
                        object_type="phase",
                        object_id=phase.phase_id,
                        summary="Phase created",
                        payload_json={"phase_id": phase.phase_id, "phase_name": phase.name},
                    ),
                    connection=connection,
                )
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.handoff_created,
                    object_type="handoff",
                    object_id=snapshot.handoff.handoff_id,
                    summary="Handoff created",
                    payload_json={
                        "handoff_id": snapshot.handoff.handoff_id,
                        "from_phase_id": snapshot.handoff.from_phase_id,
                        "to_phase_id": snapshot.handoff.to_phase_id,
                    },
                ),
                connection=connection,
            )
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.runtime_task_created,
                    object_type="runtime_task",
                    object_id=snapshot.runtime_task.runtime_task_id,
                    summary="Runtime task created",
                    payload_json={
                        "runtime_task_id": snapshot.runtime_task.runtime_task_id,
                        "task_kind": snapshot.runtime_task.task_kind,
                        "summary": snapshot.runtime_task.summary,
                    },
                ),
                connection=connection,
            )
            if snapshot.domain_pack is not None and snapshot.capability_route is not None:
                self.event_repo.append(
                    RunEvent(
                        run_id=run.run_id,
                        event_type=RunEventType.domain_pack_selected,
                        object_type="domain_pack",
                        object_id=snapshot.domain_pack.domain_pack_id,
                        summary="Domain pack selected",
                        payload_json={
                            "domain_pack_id": snapshot.domain_pack.domain_pack_id,
                            "domain_pack_name": snapshot.domain_pack.name,
                            "matched_preset_id": snapshot.domain_pack.matched_preset_id,
                            "task_kind": snapshot.runtime_task.task_kind,
                            "adapter_name": snapshot.capability_route.adapter_name,
                            "operator_label": snapshot.domain_pack.runtime_projection.operator_label,
                            "capability_tags": snapshot.domain_pack.capability_exposure.capability_tags,
                            "evidence_expectations": snapshot.domain_pack.runtime_projection.evidence_expectations,
                        },
                    ),
                    connection=connection,
                )
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.run_compiled,
                    object_type="run",
                    object_id=run.run_id,
                    summary="Run compiled",
                    payload_json={
                        "run_id": run.run_id,
                        "status": RunStatus.prepared,
                        "runtime_task_id": snapshot.runtime_task.runtime_task_id,
                    },
                ),
                connection=connection,
            )
            self._capture_run_snapshot(
                run.run_id,
                RunSnapshotStage.compiled,
                "Compile snapshot captured",
                runtime_task_id=snapshot.runtime_task.runtime_task_id,
                connection=connection,
                payload_extra={
                    "domain_pack_id": snapshot.domain_pack.domain_pack_id if snapshot.domain_pack is not None else None,
                    "domain_pack_resolution": (
                        snapshot.domain_pack.model_dump(mode="json") if snapshot.domain_pack is not None else None
                    ),
                    "adapter_name": snapshot.capability_route.adapter_name if snapshot.capability_route is not None else None,
                    "memory_retrieval_preview": (
                        snapshot.memory_preview.model_dump(mode="json") if snapshot.memory_preview is not None else None
                    ),
                },
            )
        return PreparedRunBundle(
            run=updated_run,
            preset=preset,
            task_packet=snapshot.task_packet,
            state_ref=stored_state_ref,
            handoff=snapshot.handoff,
            domain_pack=snapshot.domain_pack,
            capability_route=snapshot.capability_route,
            memory_preview=snapshot.memory_preview,
        )

    def recompile_run(
        self,
        run_id: str,
        task_kind: TaskKind | str | None = None,
        adapter_name: str | None = None,
        memory_item_ids: list[str] | None = None,
        *,
        ignore_budget: bool = False,
    ) -> PreparedRunBundle:
        run = self.get_run(run_id)
        self._require_status(run, "recompile", [RunStatus.prepared])
        preset = self.preset_repo.get(run.preset_id)
        if preset is None:
            raise PresetNotFoundError(f"preset not found: {run.preset_id}")
        snapshot = self._snapshot_for_run(
            run,
            preset,
            task_kind,
            requested_adapter=adapter_name,
            memory_item_ids=memory_item_ids,
        )

        with unit_of_work(self.db_path) as connection:
            ledger = self._ensure_budget_ledger(run, preset, connection=connection, compile_count=1)
            remaining_retries = self._remaining_retries(ledger)
            if not ignore_budget and remaining_retries is not None and remaining_retries <= 0:
                raise BudgetExhaustedError(run.run_id, remaining_retries, ledger.max_retries)
            next_compile_count = ledger.compile_count + 1
            next_recompile_count = ledger.recompile_count if ignore_budget else ledger.recompile_count + 1
            ledger = self.budget_repo.update(
                BudgetLedger.model_validate(
                    {
                        **ledger.model_dump(mode="json"),
                        "compile_count": next_compile_count,
                        "recompile_count": next_recompile_count,
                        "updated_at": self._utc_now().isoformat(),
                    }
                ),
                connection=connection,
            )
            self.runtime_state_repo.clear_for_run(run.run_id, connection=connection)
            self.handoff_repo.clear_for_run(run.run_id, connection=connection)
            self.task_repo.clear_for_run(run.run_id, connection=connection)

            self.task_repo.create_phase(snapshot.compile_phase, connection=connection)
            self.task_repo.create_phase(snapshot.execution_phase, connection=connection)
            self.task_repo.create_task_card(snapshot.task_card, connection=connection)
            self.task_repo.create_runtime_task(snapshot.runtime_task, connection=connection)
            self.task_repo.create_task_packet(snapshot.task_packet, connection=connection)
            self.handoff_repo.create(snapshot.handoff, connection=connection)
            self._ensure_current_runtime_attempt(
                run.run_id,
                snapshot.runtime_task.runtime_task_id,
                trigger=RuntimeAttemptTrigger.recompile,
                connection=connection,
                reason_if_superseded="recompile",
            )
            state_ref = self._state_ref_with_compile_context(
                self.runtime_gateway.start(run.run_id, snapshot.runtime_task.runtime_task_id),
                run,
                preset,
                snapshot,
            )
            stored_state_ref = self.runtime_state_repo.upsert(state_ref, connection=connection)
            updated_run = self._transition_run_status(run, "recompile", RunStatus.prepared, connection=connection)
            for phase in (snapshot.compile_phase, snapshot.execution_phase):
                self.event_repo.append(
                    RunEvent(
                        run_id=run.run_id,
                        event_type=RunEventType.phase_created,
                        object_type="phase",
                        object_id=phase.phase_id,
                        summary="Phase created",
                        payload_json={"phase_id": phase.phase_id, "phase_name": phase.name},
                    ),
                    connection=connection,
                )
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.handoff_created,
                    object_type="handoff",
                    object_id=snapshot.handoff.handoff_id,
                    summary="Handoff created",
                    payload_json={
                        "handoff_id": snapshot.handoff.handoff_id,
                        "from_phase_id": snapshot.handoff.from_phase_id,
                        "to_phase_id": snapshot.handoff.to_phase_id,
                    },
                ),
                connection=connection,
            )
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.runtime_task_created,
                    object_type="runtime_task",
                    object_id=snapshot.runtime_task.runtime_task_id,
                    summary="Runtime task created",
                    payload_json={
                        "runtime_task_id": snapshot.runtime_task.runtime_task_id,
                        "task_kind": snapshot.runtime_task.task_kind,
                        "summary": snapshot.runtime_task.summary,
                    },
                ),
                connection=connection,
            )
            if snapshot.domain_pack is not None and snapshot.capability_route is not None:
                self.event_repo.append(
                    RunEvent(
                        run_id=run.run_id,
                        event_type=RunEventType.domain_pack_selected,
                        object_type="domain_pack",
                        object_id=snapshot.domain_pack.domain_pack_id,
                        summary="Domain pack selected",
                        payload_json={
                            "domain_pack_id": snapshot.domain_pack.domain_pack_id,
                            "domain_pack_name": snapshot.domain_pack.name,
                            "matched_preset_id": snapshot.domain_pack.matched_preset_id,
                            "task_kind": snapshot.runtime_task.task_kind,
                            "adapter_name": snapshot.capability_route.adapter_name,
                            "operator_label": snapshot.domain_pack.runtime_projection.operator_label,
                            "capability_tags": snapshot.domain_pack.capability_exposure.capability_tags,
                            "evidence_expectations": snapshot.domain_pack.runtime_projection.evidence_expectations,
                        },
                    ),
                    connection=connection,
                )
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.run_compiled,
                    object_type="run",
                    object_id=run.run_id,
                    summary="Run recompiled",
                    payload_json={
                        "run_id": run.run_id,
                        "status": RunStatus.prepared,
                        "runtime_task_id": snapshot.runtime_task.runtime_task_id,
                    },
                ),
                connection=connection,
            )
            self._capture_run_snapshot(
                run.run_id,
                RunSnapshotStage.compiled,
                "Recompile snapshot captured",
                runtime_task_id=snapshot.runtime_task.runtime_task_id,
                connection=connection,
                payload_extra={
                    "domain_pack_id": snapshot.domain_pack.domain_pack_id if snapshot.domain_pack is not None else None,
                    "domain_pack_resolution": (
                        snapshot.domain_pack.model_dump(mode="json") if snapshot.domain_pack is not None else None
                    ),
                    "adapter_name": snapshot.capability_route.adapter_name if snapshot.capability_route is not None else None,
                    "memory_retrieval_preview": (
                        snapshot.memory_preview.model_dump(mode="json") if snapshot.memory_preview is not None else None
                    ),
                },
            )
        return PreparedRunBundle(
            run=updated_run,
            preset=preset,
            task_packet=snapshot.task_packet,
            state_ref=stored_state_ref,
            handoff=snapshot.handoff,
            domain_pack=snapshot.domain_pack,
            capability_route=snapshot.capability_route,
            memory_preview=snapshot.memory_preview,
        )

    def prepare_run(
        self,
        run_id: str,
        task_kind: TaskKind | str | None = None,
        adapter_name: str | None = None,
        memory_item_ids: list[str] | None = None,
    ) -> PreparedRunBundle:
        return self.compile_run(
            run_id,
            task_kind=task_kind,
            adapter_name=adapter_name,
            memory_item_ids=memory_item_ids,
        )

    def cancel_run(self, run_id: str) -> Run:
        run = self.get_run(run_id)
        if run.status == RunStatus.cancelled:
            return run
        self._require_status(run, "cancel", [RunStatus.pending, RunStatus.prepared, RunStatus.awaiting_review])
        with unit_of_work(self.db_path) as connection:
            state_refs = self.runtime_state_repo.list_for_run(run.run_id, connection=connection)
            for state_ref in state_refs:
                cancelled_state = RuntimeStateRef(
                    state_ref_id=state_ref.state_ref_id,
                    run_id=state_ref.run_id,
                    runtime_task_id=state_ref.runtime_task_id,
                    graph_step=RuntimeGraphStep.cancelled,
                    state_payload={**state_ref.state_payload, "reason": "cancelled_by_operator"},
                    is_terminal=True,
                    created_at=state_ref.created_at,
                )
                self.runtime_state_repo.upsert(cancelled_state, connection=connection)
            current_attempt = self.runtime_attempt_repo.current_for_run(run.run_id, connection=connection)
            if current_attempt is not None:
                self._close_runtime_attempt(
                    current_attempt,
                    status=RuntimeAttemptStatus.cancelled,
                    reason="run_cancelled",
                    connection=connection,
                )
            self._release_active_claims_for_run(
                run.run_id,
                status=RuntimeClaimStatus.released,
                reason="run_cancelled",
                connection=connection,
            )
            self._release_active_worker_leases_for_run(
                run.run_id,
                status=WorkerLeaseStatus.released,
                reason="run_cancelled",
                connection=connection,
            )
            updated_run = self._transition_run_status(run, "cancel", RunStatus.cancelled, connection=connection)
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.run_cancelled,
                    object_type="run",
                    object_id=run.run_id,
                    summary="Run cancelled",
                    payload_json={
                        "run_id": run.run_id,
                        "status": RunStatus.cancelled,
                        "reason": "cancelled_by_operator",
                    },
                ),
                connection=connection,
            )
            self._capture_run_snapshot(
                run.run_id,
                RunSnapshotStage.cancelled,
                "Cancelled snapshot captured",
                connection=connection,
            )
        self._record_lifecycle_simulation_if_triggered(
            run.run_id,
            SimulationRecordSource.lifecycle_cancelled,
        )
        return updated_run

    def approve_run_review(self, run_id: str, rationale: str = "approved by operator") -> ReviewedRunBundle:
        return self._finalize_human_review(run_id, ReviewDecision.pass_, rationale)

    def reject_run_review(self, run_id: str, rationale: str = "rejected by operator") -> ReviewedRunBundle:
        return self._finalize_human_review(run_id, ReviewDecision.fail, rationale)

    def _finalize_human_review(self, run_id: str, decision: ReviewDecision, rationale: str) -> ReviewedRunBundle:
        run = self.get_run(run_id)
        self._require_status(run, "human_review", [RunStatus.awaiting_review])
        runtime_tasks = self.task_repo.list_runtime_tasks_for_run(run.run_id)
        if not runtime_tasks:
            raise EntityNotFoundError("runtime_task", run.run_id)
        runtime_task = runtime_tasks[0]
        evidence = self.evidence_repo.get_by_task(runtime_task.runtime_task_id)
        if evidence is None:
            raise EntityNotFoundError("evidence", runtime_task.runtime_task_id)

        with unit_of_work(self.db_path) as connection:
            verdict = ReviewVerdict(
                run_id=run.run_id,
                evidence_id=evidence.evidence_id,
                decision=decision,
                rationale=rationale,
                reviewer_type=ReviewerType.human,
            )
            self.review_repo.create(verdict, connection=connection)
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.review_submitted,
                    object_type="review_verdict",
                    object_id=verdict.verdict_id,
                    summary=f"Review verdict: {verdict.decision}",
                    payload_json={
                        "verdict_id": verdict.verdict_id,
                        "decision": verdict.decision,
                    },
                ),
                connection=connection,
            )

            state_ref = self.runtime_state_repo.get_by_task(runtime_task.runtime_task_id, connection=connection)
            if state_ref is not None:
                terminal_step = "completed" if decision == ReviewDecision.pass_ else "failed"
                terminal_state = RuntimeStateRef(
                    state_ref_id=state_ref.state_ref_id,
                    run_id=state_ref.run_id,
                    runtime_task_id=state_ref.runtime_task_id,
                    graph_step=RuntimeGraphStep(terminal_step),
                    state_payload={**state_ref.state_payload, "human_review_decision": decision},
                    is_terminal=True,
                    created_at=state_ref.created_at,
                )
                self.runtime_state_repo.upsert(terminal_state, connection=connection)
            current_attempt = self.runtime_attempt_repo.current_for_run(run.run_id, connection=connection)
            if current_attempt is not None:
                self._close_runtime_attempt(
                    current_attempt,
                    status=RuntimeAttemptStatus.completed if decision == ReviewDecision.pass_ else RuntimeAttemptStatus.failed,
                    reason="human_review_approved" if decision == ReviewDecision.pass_ else "human_review_rejected",
                    connection=connection,
                )

            self._release_active_worker_leases_for_run(
                run.run_id,
                status=WorkerLeaseStatus.released,
                reason="run_terminal",
                connection=connection,
            )

            terminal_status = RunStatus.completed if decision == ReviewDecision.pass_ else RunStatus.failed
            updated_run = self._transition_run_status(run, "human_review", terminal_status, connection=connection)
            terminal_event = RunEvent(
                run_id=run.run_id,
                event_type=RunEventType.run_completed if terminal_status == RunStatus.completed else RunEventType.run_failed,
                object_type="run",
                object_id=run.run_id,
                summary="Run completed" if terminal_status == RunStatus.completed else "Run failed review",
                payload_json={
                    "run_id": run.run_id,
                    "status": terminal_status,
                }
                if terminal_status == RunStatus.completed
                else {
                    "run_id": run.run_id,
                    "status": terminal_status,
                    "reason": "human_review_reject",
                },
            )
            self.event_repo.append(terminal_event, connection=connection)
            self._capture_run_snapshot(
                run.run_id,
                RunSnapshotStage.completed if terminal_status == RunStatus.completed else RunSnapshotStage.failed,
                "Human review terminal snapshot captured",
                runtime_task_id=runtime_task.runtime_task_id,
                connection=connection,
                payload_extra={"decision": str(decision)},
            )
        self._record_lifecycle_simulation_if_triggered(
            run.run_id,
            SimulationRecordSource.lifecycle_terminal,
        )
        return ReviewedRunBundle(run=updated_run, evidence=evidence, review_verdict=verdict)

    def resume_run(self, run_id: str) -> ExecutedRunBundle:
        run = self.get_run(run_id)
        self._require_status(run, "resume", [RunStatus.prepared])
        preset = self.preset_repo.get(run.preset_id)
        if preset is None:
            raise PresetNotFoundError(f"preset not found: {run.preset_id}")
        runtime_tasks = self.task_repo.list_runtime_tasks_for_run(run.run_id)
        if not runtime_tasks:
            raise EntityNotFoundError("runtime_task", run.run_id)
        runtime_task = runtime_tasks[0]
        task_packet = self.task_repo.get_task_packet(runtime_task.runtime_task_id)
        if task_packet is None:
            raise EntityNotFoundError("task_packet", runtime_task.runtime_task_id)

        hook_source: SimulationRecordSource | None = None
        bundle: ExecutedRunBundle | None = None
        with unit_of_work(self.db_path) as connection:
            state_ref = self.runtime_state_repo.get_by_task(runtime_task.runtime_task_id, connection=connection)
            if state_ref is None:
                raise EntityNotFoundError("runtime_state_ref", runtime_task.runtime_task_id)
            budget_ledger = self._ensure_budget_ledger(run, preset, connection=connection, compile_count=1)
            self._ensure_current_runtime_attempt(
                run.run_id,
                runtime_task.runtime_task_id,
                trigger=RuntimeAttemptTrigger.resume,
                connection=connection,
                reason_if_superseded="resume",
                force_new=True,
            )
            self._acquire_runtime_claim(
                run.run_id,
                runtime_task.runtime_task_id,
                connection=connection,
            )
            resumed_state = self.runtime_gateway.resume(state_ref)
            self.runtime_state_repo.upsert(resumed_state, connection=connection)
            self._transition_run_status(run, "resume", RunStatus.running, connection=connection)
            self.task_repo.update_runtime_task_status(runtime_task.runtime_task_id, TaskStatus.running, connection=connection)
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.runtime_resumed,
                    object_type="runtime_state_ref",
                    object_id=resumed_state.state_ref_id,
                    summary="Runtime resumed",
                    payload_json={
                        "run_id": run.run_id,
                        "runtime_task_id": runtime_task.runtime_task_id,
                        "graph_step": resumed_state.graph_step,
                    },
                ),
                connection=connection,
            )
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.runtime_task_started,
                    object_type="runtime_task",
                    object_id=runtime_task.runtime_task_id,
                    summary="Runtime task started",
                    payload_json={
                        "runtime_task_id": runtime_task.runtime_task_id,
                        "task_kind": runtime_task.task_kind,
                    },
                ),
                connection=connection,
            )

            brief_env = {
                key: value
                for key, value in {
                    "WORKFLOW_RUNTIME_GATEWAY_PROVIDER": resumed_state.state_payload.get("runtime_gateway_provider"),
                    "WORKFLOW_LLM_MODEL": resumed_state.state_payload.get("llm_model"),
                    "WORKFLOW_RUNTIME_BRIEF": resumed_state.state_payload.get("runtime_brief"),
                }.items()
                if value
            }
            execution_packet = TaskPacket.model_validate(
                {
                    **task_packet.model_dump(mode="json"),
                    "env": {
                        **task_packet.env,
                        **{key: str(value) for key, value in brief_env.items()},
                    },
                }
            )

            adapter = self.worker_router.route(execution_packet)
            worker_lease = self._acquire_worker_lease(
                run.run_id,
                runtime_task.runtime_task_id,
                adapter_name=adapter.__class__.__name__.replace("Adapter", "").lower(),
                connection=connection,
            )
            execution_result = adapter.launch(execution_packet)
            completed_status = TaskStatus.completed if execution_result.return_code == 0 else TaskStatus.failed
            self.task_repo.update_runtime_task_status(runtime_task.runtime_task_id, completed_status, connection=connection)
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.runtime_task_completed,
                    object_type="runtime_task",
                    object_id=runtime_task.runtime_task_id,
                    summary="Runtime task completed",
                    payload_json={
                        "runtime_task_id": runtime_task.runtime_task_id,
                        "return_code": execution_result.return_code,
                        "duration_ms": execution_result.duration_ms,
                    },
                ),
                connection=connection,
            )

            evidence = self.evidence_builder.build(run.run_id, runtime_task.runtime_task_id, execution_result)
            self.evidence_repo.create(evidence, connection=connection)
            self.budget_repo.update(
                BudgetLedger.model_validate(
                    {
                        **budget_ledger.model_dump(mode="json"),
                        "execution_count": budget_ledger.execution_count + 1,
                        "total_runtime_ms": budget_ledger.total_runtime_ms + execution_result.duration_ms,
                        "last_return_code": execution_result.return_code,
                        "updated_at": self._utc_now().isoformat(),
                    }
                ),
                connection=connection,
            )
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.evidence_submitted,
                    object_type="evidence",
                    object_id=evidence.evidence_id,
                    summary=evidence.summary,
                    payload_json={"evidence_id": evidence.evidence_id, "summary": evidence.summary},
                ),
                connection=connection,
            )

            review_policy = ReviewPolicy(preset.default_review_policy)

            if review_policy == ReviewPolicy.human_required:
                self._release_worker_lease(
                    worker_lease,
                    status=WorkerLeaseStatus.released,
                    reason="awaiting_human_review",
                    connection=connection,
                )
                awaiting_state = RuntimeStateRef(
                    state_ref_id=resumed_state.state_ref_id,
                    run_id=run.run_id,
                    runtime_task_id=runtime_task.runtime_task_id,
                    graph_step=RuntimeGraphStep.awaiting_review,
                    state_payload={
                        **resumed_state.state_payload,
                        "review_policy": preset.default_review_policy,
                        "return_code": execution_result.return_code,
                    },
                    is_terminal=False,
                    created_at=resumed_state.created_at,
                )
                self.runtime_state_repo.upsert(awaiting_state, connection=connection)
                self._release_active_claims_for_run(
                    run.run_id,
                    status=RuntimeClaimStatus.released,
                    reason="awaiting_human_review",
                    connection=connection,
                )
                updated_run = self._transition_run_status(
                    Run.model_validate({**run.model_dump(mode="json"), "status": RunStatus.running}),
                    "request_human_review",
                    RunStatus.awaiting_review,
                    connection=connection,
                )
                self.event_repo.append(
                    RunEvent(
                        run_id=run.run_id,
                        event_type=RunEventType.review_requested,
                        object_type="run",
                        object_id=run.run_id,
                        summary="Human review requested",
                        payload_json={
                            "run_id": run.run_id,
                            "policy": preset.default_review_policy,
                            "status": RunStatus.awaiting_review,
                        },
                    ),
                    connection=connection,
                )
                self._capture_run_snapshot(
                    run.run_id,
                    RunSnapshotStage.awaiting_review,
                    "Awaiting-review snapshot captured",
                    runtime_task_id=runtime_task.runtime_task_id,
                    connection=connection,
                    payload_extra={"review_policy": str(preset.default_review_policy)},
                )
                hook_source = SimulationRecordSource.lifecycle_awaiting_review
                bundle = ExecutedRunBundle(
                    run=updated_run,
                    execution_result=execution_result,
                    evidence=evidence,
                    review_verdict=None,
                )
            else:
                review_verdict = self.auto_review.review(evidence)
                self.review_repo.create(review_verdict, connection=connection)
                self.event_repo.append(
                    RunEvent(
                        run_id=run.run_id,
                        event_type=RunEventType.review_submitted,
                        object_type="review_verdict",
                        object_id=review_verdict.verdict_id,
                        summary=f"Review verdict: {review_verdict.decision}",
                        payload_json={
                            "verdict_id": review_verdict.verdict_id,
                            "decision": review_verdict.decision,
                        },
                    ),
                    connection=connection,
                )

                if review_policy == ReviewPolicy.mandatory or (
                    review_policy == ReviewPolicy.recommended and review_verdict.decision == ReviewDecision.fail
                ):
                    awaiting_reason = (
                        "mandatory_human_signoff"
                        if review_policy == ReviewPolicy.mandatory
                        else "recommended_auto_review_failed"
                    )
                    self._release_worker_lease(
                        worker_lease,
                        status=WorkerLeaseStatus.released,
                        reason="awaiting_human_review",
                        connection=connection,
                    )
                    awaiting_state = RuntimeStateRef(
                        state_ref_id=resumed_state.state_ref_id,
                        run_id=run.run_id,
                        runtime_task_id=runtime_task.runtime_task_id,
                        graph_step=RuntimeGraphStep.awaiting_review,
                        state_payload={
                            **resumed_state.state_payload,
                            "review_policy": preset.default_review_policy,
                            "return_code": execution_result.return_code,
                            "awaiting_review_reason": awaiting_reason,
                            "latest_auto_review_decision": review_verdict.decision,
                        },
                        is_terminal=False,
                        created_at=resumed_state.created_at,
                    )
                    self.runtime_state_repo.upsert(awaiting_state, connection=connection)
                    self._release_active_claims_for_run(
                        run.run_id,
                        status=RuntimeClaimStatus.released,
                        reason="awaiting_human_review",
                        connection=connection,
                    )
                    updated_run = self._transition_run_status(
                        Run.model_validate({**run.model_dump(mode="json"), "status": RunStatus.running}),
                        "request_human_review",
                        RunStatus.awaiting_review,
                        connection=connection,
                    )
                    self.event_repo.append(
                        RunEvent(
                            run_id=run.run_id,
                            event_type=RunEventType.review_requested,
                            object_type="run",
                            object_id=run.run_id,
                            summary="Human review requested",
                            payload_json={
                                "run_id": run.run_id,
                                "policy": preset.default_review_policy,
                                "status": RunStatus.awaiting_review,
                            },
                        ),
                        connection=connection,
                    )
                    self._capture_run_snapshot(
                        run.run_id,
                        RunSnapshotStage.awaiting_review,
                        "Awaiting-review snapshot captured",
                        runtime_task_id=runtime_task.runtime_task_id,
                        connection=connection,
                        payload_extra={
                            "review_policy": str(preset.default_review_policy),
                            "awaiting_review_reason": awaiting_reason,
                            "latest_auto_review_decision": str(review_verdict.decision),
                        },
                    )
                    hook_source = SimulationRecordSource.lifecycle_awaiting_review
                    bundle = ExecutedRunBundle(
                        run=updated_run,
                        execution_result=execution_result,
                        evidence=evidence,
                        review_verdict=review_verdict,
                    )
                else:
                    if review_verdict.decision == ReviewDecision.pass_:
                        final_status = RunStatus.completed
                        terminal_event = RunEvent(
                            run_id=run.run_id,
                            event_type=RunEventType.run_completed,
                            object_type="run",
                            object_id=run.run_id,
                            summary="Run completed",
                            payload_json={"run_id": run.run_id, "status": RunStatus.completed},
                        )
                        terminal_graph_step = RuntimeGraphStep.completed
                    else:
                        final_status = RunStatus.failed
                        terminal_event = RunEvent(
                            run_id=run.run_id,
                            event_type=RunEventType.run_failed,
                            object_type="run",
                            object_id=run.run_id,
                            summary="Run failed review",
                            payload_json={
                                "run_id": run.run_id,
                                "status": RunStatus.failed,
                                "reason": "auto_review_fail",
                            },
                        )
                        terminal_graph_step = RuntimeGraphStep.failed

                    terminal_state = RuntimeStateRef(
                        state_ref_id=resumed_state.state_ref_id,
                        run_id=run.run_id,
                        runtime_task_id=runtime_task.runtime_task_id,
                        graph_step=terminal_graph_step,
                        state_payload={
                            **resumed_state.state_payload,
                            "review_policy": preset.default_review_policy,
                            "return_code": execution_result.return_code,
                        },
                        is_terminal=True,
                        created_at=resumed_state.created_at,
                    )
                    self.runtime_state_repo.upsert(terminal_state, connection=connection)
                    current_attempt = self.runtime_attempt_repo.current_for_run(run.run_id, connection=connection)
                    if current_attempt is not None:
                        self._close_runtime_attempt(
                            current_attempt,
                            status=RuntimeAttemptStatus.completed
                            if final_status == RunStatus.completed
                            else RuntimeAttemptStatus.failed,
                            reason="auto_review_passed" if final_status == RunStatus.completed else "auto_review_failed",
                            connection=connection,
                        )
                    self._release_worker_lease(
                        worker_lease,
                        status=WorkerLeaseStatus.released,
                        reason="run_terminal",
                        connection=connection,
                    )
                    self._release_active_claims_for_run(
                        run.run_id,
                        status=RuntimeClaimStatus.released,
                        reason="run_terminal",
                        connection=connection,
                    )
                    updated_run = self._transition_run_status(
                        Run.model_validate({**run.model_dump(mode="json"), "status": RunStatus.running}),
                        "auto_review_finalize",
                        final_status,
                        connection=connection,
                    )
                    self.event_repo.append(terminal_event, connection=connection)
                    self._capture_run_snapshot(
                        run.run_id,
                        RunSnapshotStage.completed if final_status == RunStatus.completed else RunSnapshotStage.failed,
                        "Auto terminal snapshot captured",
                        runtime_task_id=runtime_task.runtime_task_id,
                        connection=connection,
                        payload_extra={"decision": str(review_verdict.decision)},
                    )
                    hook_source = SimulationRecordSource.lifecycle_terminal
                    bundle = ExecutedRunBundle(
                        run=updated_run,
                        execution_result=execution_result,
                        evidence=evidence,
                        review_verdict=review_verdict,
                    )
        if hook_source is not None:
            self._record_lifecycle_simulation_if_triggered(run.run_id, hook_source)
        if bundle is None:
            raise RuntimeError(f"resume_run did not produce a terminal or awaiting-review bundle for {run.run_id}")
        return bundle

    def execute_run(self, run_id: str) -> ExecutedRunBundle:
        return self.resume_run(run_id)
