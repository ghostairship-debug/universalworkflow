from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packages.contracts import (
    Evidence,
    HandoffLite,
    Phase,
    PresetDefinition,
    PresetSuggestion,
    ReviewDecision,
    ReviewerType,
    ReviewVerdict,
    Run,
    RunEvent,
    RunEventType,
    RuntimeGateway,
    RuntimeGraphStep,
    RuntimeStateRef,
    RunStatus,
    TaskCard,
    TaskStatus,
    TaskPacket,
    allowed_run_status_transitions,
    can_transition_run_status,
)
from packages.core_domain.auto_review import AutoReviewV0
from packages.core_domain.compile import CompileSnapshot, compile_run as build_compile_snapshot
from packages.core_domain.db import unit_of_work
from packages.core_domain.errors import (
    EntityNotFoundError,
    InvalidStateTransitionError,
    PresetNotFoundError,
    PresetRequiredError,
)
from packages.core_domain.evidence_builder import EvidenceBuilder
from packages.core_domain.repositories import (
    EventRepository,
    EvidenceRepository,
    HandoffRepository,
    PresetRepository,
    ReviewRepository,
    RunRepository,
    RuntimeStateRepository,
    TaskRepository,
)
from packages.core_domain.resolver import PresetResolver
from packages.runtime_langgraph.gateway import NullRuntimeGateway
from packages.worker_adapters.shell_adapter import ExecutionResult, ShellAdapter


@dataclass(slots=True)
class PreparedRunBundle:
    run: Run
    preset: PresetDefinition
    task_packet: TaskPacket
    state_ref: RuntimeStateRef
    handoff: HandoffLite


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
    phases: list[Phase]
    task_cards: list[TaskCard]
    runtime_tasks: list[RuntimeTask]
    handoffs: list[HandoffLite]
    runtime_state_refs: list[RuntimeStateRef]
    evidence_by_task: dict[str, Evidence | None]
    latest_review_verdict: ReviewVerdict | None


class OrchestratorService:
    def __init__(
        self,
        db_path: str | Path | None = None,
        runtime_gateway: RuntimeGateway | None = None,
        shell_adapter: ShellAdapter | None = None,
        evidence_builder: EvidenceBuilder | None = None,
        auto_review: AutoReviewV0 | None = None,
    ):
        self.db_path = Path(db_path) if db_path is not None else None
        self.run_repo = RunRepository(self.db_path)
        self.preset_repo = PresetRepository(self.db_path)
        self.task_repo = TaskRepository(self.db_path)
        self.event_repo = EventRepository(self.db_path)
        self.evidence_repo = EvidenceRepository(self.db_path)
        self.review_repo = ReviewRepository(self.db_path)
        self.handoff_repo = HandoffRepository(self.db_path)
        self.runtime_state_repo = RuntimeStateRepository(self.db_path)
        self.runtime_gateway = runtime_gateway or NullRuntimeGateway()
        self.shell_adapter = shell_adapter or ShellAdapter()
        self.evidence_builder = evidence_builder or EvidenceBuilder()
        self.auto_review = auto_review or AutoReviewV0()

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
        if latest_review_verdict is None:
            if str(run.status) == RunStatus.awaiting_review:
                return "human_pending"
            return "not_requested"
        if str(latest_review_verdict.reviewer_type) == ReviewerType.human:
            return "human_approved" if str(latest_review_verdict.decision) == ReviewDecision.pass_ else "human_rejected"
        return "auto_passed" if str(latest_review_verdict.decision) == ReviewDecision.pass_ else "auto_failed"

    def _serialize_contract(self, value: Evidence | ReviewVerdict | RuntimeStateRef | None) -> dict[str, Any] | None:
        return value.model_dump(mode="json") if value is not None else None

    def _load_run_context(self, run_id: str) -> RunDiagnosticContext:
        run = self.get_run(run_id)
        phases = self.task_repo.list_phases_for_run(run_id)
        task_cards = self.task_repo.list_task_cards_for_run(run_id)
        runtime_tasks = self.task_repo.list_runtime_tasks_for_run(run_id)
        handoffs = self.handoff_repo.list_for_run(run_id)
        runtime_state_refs = self.runtime_state_repo.list_for_run(run_id)
        latest_review_verdict = self.review_repo.latest_for_run(run_id)
        evidence_by_task = {
            task.runtime_task_id: self.evidence_repo.get_by_task(task.runtime_task_id) for task in runtime_tasks
        }
        return RunDiagnosticContext(
            run=run,
            phases=phases,
            task_cards=task_cards,
            runtime_tasks=runtime_tasks,
            handoffs=handoffs,
            runtime_state_refs=runtime_state_refs,
            evidence_by_task=evidence_by_task,
            latest_review_verdict=latest_review_verdict,
        )

    def _last_runtime_state(self, context: RunDiagnosticContext) -> RuntimeStateRef | None:
        if not context.runtime_state_refs:
            return None
        return max(
            context.runtime_state_refs,
            key=lambda state_ref: (state_ref.updated_at, state_ref.created_at, state_ref.state_ref_id),
        )

    def _last_evidence(self, context: RunDiagnosticContext) -> Evidence | None:
        evidences = [evidence for evidence in context.evidence_by_task.values() if evidence is not None]
        if not evidences:
            return None
        return max(evidences, key=lambda evidence: (evidence.created_at, evidence.evidence_id))

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

    def _inspection_problem(
        self,
        problem: str,
        reason: str,
        next_action: str,
        *,
        severity: str = "error",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "problem": problem,
            "severity": severity,
            "reason": reason,
            "next_action": next_action,
            "details": details or {},
        }

    def _inspect_context(self, context: RunDiagnosticContext) -> list[dict[str, Any]]:
        problems: list[dict[str, Any]] = []
        non_terminal_states = [state_ref for state_ref in context.runtime_state_refs if not state_ref.is_terminal]

        if str(context.run.status) == RunStatus.completed and non_terminal_states:
            state_ref = non_terminal_states[0]
            problems.append(
                self._inspection_problem(
                    "completed_runtime_non_terminal",
                    "run is marked completed but runtime state is still non-terminal",
                    "reconcile_runtime_state_ref",
                    details={
                        "runtime_task_id": state_ref.runtime_task_id,
                        "graph_step": state_ref.graph_step,
                        "state_ref_id": state_ref.state_ref_id,
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
                        details={"runtime_task_ids": [task.runtime_task_id for task in context.runtime_tasks]},
                    )
                )

        if str(context.run.status) == RunStatus.cancelled and non_terminal_states:
            state_ref = non_terminal_states[0]
            problems.append(
                self._inspection_problem(
                    "cancelled_with_live_runtime",
                    "run is cancelled but at least one runtime state is still live",
                    "terminate_or_reconcile_runtime",
                    details={
                        "runtime_task_id": state_ref.runtime_task_id,
                        "graph_step": state_ref.graph_step,
                        "state_ref_id": state_ref.state_ref_id,
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

    def list_presets(self) -> list[PresetDefinition]:
        return self.preset_repo.list()

    def suggest_presets(self, goal: str) -> list[PresetSuggestion]:
        return self._resolver().suggest(goal)

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

    def get_status_detail(self, run_id: str) -> dict[str, Any]:
        context = self._load_run_context(run_id)
        last_runtime_state = self._last_runtime_state(context)
        last_evidence = self._last_evidence(context)
        inspection_problems = self._inspect_context(context)
        return {
            "run": context.run.model_dump(mode="json"),
            "runtime_tasks": [task.model_dump(mode="json") for task in context.runtime_tasks],
            "runtime_task_ids": [task.runtime_task_id for task in context.runtime_tasks],
            "handoffs": [handoff.model_dump(mode="json") for handoff in context.handoffs],
            "runtime_state_refs": [state_ref.model_dump(mode="json") for state_ref in context.runtime_state_refs],
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
        problems = self._inspect_context(context)
        last_runtime_state = self._last_runtime_state(context)
        return {
            "run": context.run.model_dump(mode="json"),
            "effective_review_state": self._effective_review_state(context.run, context.latest_review_verdict),
            "last_runtime_state": self._serialize_contract(last_runtime_state),
            "passed": not problems,
            "problem_count": len(problems),
            "problems": problems,
            "recommended_action": problems[0]["next_action"] if problems else "none",
        }

    def _snapshot_for_run(self, run: Run, preset: PresetDefinition) -> CompileSnapshot:
        return build_compile_snapshot(run.goal, preset, run.run_id)

    def compile_run(self, run_id: str) -> PreparedRunBundle:
        run = self.get_run(run_id)
        self._require_status(run, "compile", [RunStatus.pending])
        preset = self.preset_repo.get(run.preset_id)
        if preset is None:
            raise PresetNotFoundError(f"preset not found: {run.preset_id}")
        snapshot = self._snapshot_for_run(run, preset)

        with unit_of_work(self.db_path) as connection:
            self.task_repo.create_phase(snapshot.compile_phase, connection=connection)
            self.task_repo.create_phase(snapshot.execution_phase, connection=connection)
            self.task_repo.create_task_card(snapshot.task_card, connection=connection)
            self.task_repo.create_runtime_task(snapshot.runtime_task, connection=connection)
            self.task_repo.create_task_packet(snapshot.task_packet, connection=connection)
            self.handoff_repo.create(snapshot.handoff, connection=connection)
            state_ref = self.runtime_gateway.start(run.run_id, snapshot.runtime_task.runtime_task_id)
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
        return PreparedRunBundle(
            run=updated_run,
            preset=preset,
            task_packet=snapshot.task_packet,
            state_ref=stored_state_ref,
            handoff=snapshot.handoff,
        )

    def recompile_run(self, run_id: str) -> PreparedRunBundle:
        run = self.get_run(run_id)
        self._require_status(run, "recompile", [RunStatus.prepared])
        preset = self.preset_repo.get(run.preset_id)
        if preset is None:
            raise PresetNotFoundError(f"preset not found: {run.preset_id}")
        snapshot = self._snapshot_for_run(run, preset)

        with unit_of_work(self.db_path) as connection:
            self.runtime_state_repo.clear_for_run(run.run_id, connection=connection)
            self.handoff_repo.clear_for_run(run.run_id, connection=connection)
            self.task_repo.clear_for_run(run.run_id, connection=connection)

            self.task_repo.create_phase(snapshot.compile_phase, connection=connection)
            self.task_repo.create_phase(snapshot.execution_phase, connection=connection)
            self.task_repo.create_task_card(snapshot.task_card, connection=connection)
            self.task_repo.create_runtime_task(snapshot.runtime_task, connection=connection)
            self.task_repo.create_task_packet(snapshot.task_packet, connection=connection)
            self.handoff_repo.create(snapshot.handoff, connection=connection)
            state_ref = self.runtime_gateway.start(run.run_id, snapshot.runtime_task.runtime_task_id)
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
        return PreparedRunBundle(
            run=updated_run,
            preset=preset,
            task_packet=snapshot.task_packet,
            state_ref=stored_state_ref,
            handoff=snapshot.handoff,
        )

    def prepare_run(self, run_id: str) -> PreparedRunBundle:
        return self.compile_run(run_id)

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
        state_ref = self.runtime_state_repo.get_by_task(runtime_task.runtime_task_id)
        if state_ref is None:
            raise EntityNotFoundError("runtime_state_ref", runtime_task.runtime_task_id)
        resumed_state = self.runtime_gateway.resume(state_ref)

        with unit_of_work(self.db_path) as connection:
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

            execution_result = self.shell_adapter.launch(task_packet)
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

            if str(preset.default_review_policy) == "human_required":
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
                return ExecutedRunBundle(
                    run=updated_run,
                    execution_result=execution_result,
                    evidence=evidence,
                    review_verdict=None,
                )

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
            updated_run = self._transition_run_status(
                Run.model_validate({**run.model_dump(mode="json"), "status": RunStatus.running}),
                "auto_review_finalize",
                final_status,
                connection=connection,
            )
            self.event_repo.append(terminal_event, connection=connection)
        return ExecutedRunBundle(
            run=updated_run,
            execution_result=execution_result,
            evidence=evidence,
            review_verdict=review_verdict,
        )

    def execute_run(self, run_id: str) -> ExecutedRunBundle:
        return self.resume_run(run_id)
