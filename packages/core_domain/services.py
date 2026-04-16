from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packages.contracts import (
    Evidence,
    HandoffLite,
    PresetDefinition,
    PresetSuggestion,
    ReviewDecision,
    ReviewerType,
    ReviewVerdict,
    Run,
    RunEvent,
    RunEventType,
    RuntimeGateway,
    RuntimeStateRef,
    RunStatus,
    TaskStatus,
    TaskPacket,
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
        run = self.get_run(run_id)
        runtime_tasks = self.task_repo.list_runtime_tasks_for_run(run_id)
        handoffs = self.handoff_repo.list_for_run(run_id)
        runtime_state_refs = self.runtime_state_repo.list_for_run(run_id)
        return {
            "run": run.model_dump(mode="json"),
            "runtime_tasks": [task.model_dump(mode="json") for task in runtime_tasks],
            "runtime_task_ids": [task.runtime_task_id for task in runtime_tasks],
            "handoffs": [handoff.model_dump(mode="json") for handoff in handoffs],
            "runtime_state_refs": [state_ref.model_dump(mode="json") for state_ref in runtime_state_refs],
            "next_action": self._next_action_for(str(run.status)),
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
            updated_run = self.run_repo.update_status(run.run_id, RunStatus.prepared, connection=connection)
            assert updated_run is not None
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
            updated_run = self.run_repo.update_status(run.run_id, RunStatus.prepared, connection=connection)
            assert updated_run is not None
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
                    graph_step="cancelled",
                    state_payload={**state_ref.state_payload, "reason": "cancelled_by_operator"},
                    is_terminal=True,
                    created_at=state_ref.created_at,
                )
                self.runtime_state_repo.upsert(cancelled_state, connection=connection)
            updated_run = self.run_repo.update_status(run.run_id, RunStatus.cancelled, connection=connection)
            assert updated_run is not None
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
                    graph_step=terminal_step,
                    state_payload={**state_ref.state_payload, "human_review_decision": decision},
                    is_terminal=True,
                    created_at=state_ref.created_at,
                )
                self.runtime_state_repo.upsert(terminal_state, connection=connection)

            terminal_status = RunStatus.completed if decision == ReviewDecision.pass_ else RunStatus.failed
            updated_run = self.run_repo.update_status(run.run_id, terminal_status, connection=connection)
            assert updated_run is not None
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
            self.run_repo.update_status(run.run_id, RunStatus.running, connection=connection)
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
                    graph_step="awaiting_review",
                    state_payload={
                        **resumed_state.state_payload,
                        "review_policy": preset.default_review_policy,
                        "return_code": execution_result.return_code,
                    },
                    is_terminal=False,
                    created_at=resumed_state.created_at,
                )
                self.runtime_state_repo.upsert(awaiting_state, connection=connection)
                updated_run = self.run_repo.update_status(run.run_id, RunStatus.awaiting_review, connection=connection)
                assert updated_run is not None
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
                terminal_graph_step = "completed"
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
                terminal_graph_step = "failed"

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
            updated_run = self.run_repo.update_status(run.run_id, final_status, connection=connection)
            assert updated_run is not None
            self.event_repo.append(terminal_event, connection=connection)
        return ExecutedRunBundle(
            run=updated_run,
            execution_result=execution_result,
            evidence=evidence,
            review_verdict=review_verdict,
        )

    def execute_run(self, run_id: str) -> ExecutedRunBundle:
        return self.resume_run(run_id)
