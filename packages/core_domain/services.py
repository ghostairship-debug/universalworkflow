from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from packages.contracts import (
    Evidence,
    PresetDefinition,
    ReviewDecision,
    ReviewVerdict,
    Run,
    RunEvent,
    RunEventType,
    RunStatus,
    TaskStatus,
    TaskPacket,
)
from packages.core_domain.auto_review import AutoReviewV0
from packages.core_domain.compile import compile_run
from packages.core_domain.errors import EntityNotFoundError, PresetNotFoundError, PresetRequiredError
from packages.core_domain.evidence_builder import EvidenceBuilder
from packages.core_domain.repositories import (
    EventRepository,
    EvidenceRepository,
    PresetRepository,
    ReviewRepository,
    RunRepository,
    TaskRepository,
)
from packages.core_domain.resolver import PresetResolver
from packages.runtime_langgraph.gateway import NullRuntimeGateway, RuntimeGateway
from packages.worker_adapters.shell_adapter import ExecutionResult, ShellAdapter


@dataclass(slots=True)
class PreparedRunBundle:
    run: Run
    preset: PresetDefinition
    task_packet: TaskPacket


@dataclass(slots=True)
class ExecutedRunBundle:
    run: Run
    execution_result: ExecutionResult
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
        self.runtime_gateway = runtime_gateway or NullRuntimeGateway()
        self.shell_adapter = shell_adapter or ShellAdapter()
        self.evidence_builder = evidence_builder or EvidenceBuilder()
        self.auto_review = auto_review or AutoReviewV0()

    def _resolver(self) -> PresetResolver:
        return PresetResolver(self.preset_repo.list())

    def list_presets(self) -> list[PresetDefinition]:
        return self.preset_repo.list()

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

    def prepare_run(self, run_id: str) -> PreparedRunBundle:
        run = self.get_run(run_id)
        preset = self.preset_repo.get(run.preset_id)
        if preset is None:
            raise PresetNotFoundError(f"preset not found: {run.preset_id}")

        phase, task_card, runtime_task, task_packet = compile_run(run.goal, preset, run.run_id)
        self.task_repo.create_phase(phase)
        self.task_repo.create_task_card(task_card)
        self.task_repo.create_runtime_task(runtime_task)
        self.task_repo.create_task_packet(task_packet)
        self.run_repo.update_status(run.run_id, RunStatus.prepared)

        self.event_repo.append(
            RunEvent(
                run_id=run.run_id,
                event_type=RunEventType.phase_created,
                object_type="phase",
                object_id=phase.phase_id,
                summary="Phase created",
                payload_json={"phase_id": phase.phase_id, "phase_name": phase.name},
            )
        )
        self.event_repo.append(
            RunEvent(
                run_id=run.run_id,
                event_type=RunEventType.runtime_task_created,
                object_type="runtime_task",
                object_id=runtime_task.runtime_task_id,
                summary="Runtime task created",
                payload_json={
                    "runtime_task_id": runtime_task.runtime_task_id,
                    "task_kind": runtime_task.task_kind,
                    "summary": runtime_task.summary,
                },
            )
        )
        self.runtime_gateway.start(run.run_id, runtime_task.runtime_task_id)
        return PreparedRunBundle(run=self.get_run(run.run_id), preset=preset, task_packet=task_packet)

    def cancel_run(self, run_id: str) -> Run:
        run = self.get_run(run_id)
        updated_run = self.run_repo.update_status(run.run_id, RunStatus.cancelled)
        assert updated_run is not None
        self.event_repo.append(
            RunEvent(
                run_id=run.run_id,
                event_type=RunEventType.run_failed,
                object_type="run",
                object_id=run.run_id,
                summary="Run cancelled",
                payload_json={
                    "run_id": run.run_id,
                    "status": RunStatus.cancelled,
                    "reason": "cancelled_by_operator",
                },
            )
        )
        return updated_run

    def execute_run(self, run_id: str) -> ExecutedRunBundle:
        run = self.get_run(run_id)
        runtime_tasks = self.task_repo.list_runtime_tasks_for_run(run.run_id)
        if not runtime_tasks:
            raise EntityNotFoundError("runtime_task", run.run_id)
        runtime_task = runtime_tasks[0]
        task_packet = self.task_repo.get_task_packet(runtime_task.runtime_task_id)
        if task_packet is None:
            raise EntityNotFoundError("task_packet", runtime_task.runtime_task_id)

        self.run_repo.update_status(run.run_id, RunStatus.running)
        self.task_repo.update_runtime_task_status(runtime_task.runtime_task_id, TaskStatus.running)
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
            )
        )

        execution_result = self.shell_adapter.launch(task_packet)
        completed_status = TaskStatus.completed if execution_result.return_code == 0 else TaskStatus.failed
        self.task_repo.update_runtime_task_status(runtime_task.runtime_task_id, completed_status)
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
            )
        )

        evidence = self.evidence_builder.build(run.run_id, runtime_task.runtime_task_id, execution_result)
        self.evidence_repo.create(evidence)
        self.event_repo.append(
            RunEvent(
                run_id=run.run_id,
                event_type=RunEventType.evidence_submitted,
                object_type="evidence",
                object_id=evidence.evidence_id,
                summary=evidence.summary,
                payload_json={"evidence_id": evidence.evidence_id, "summary": evidence.summary},
            )
        )

        review_verdict = self.auto_review.review(evidence)
        self.review_repo.create(review_verdict)
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
            )
        )

        if review_verdict.decision == ReviewDecision.pass_:
            updated_run = self.run_repo.update_status(run.run_id, RunStatus.completed)
            terminal_event = RunEvent(
                run_id=run.run_id,
                event_type=RunEventType.run_completed,
                object_type="run",
                object_id=run.run_id,
                summary="Run completed",
                payload_json={"run_id": run.run_id, "status": RunStatus.completed},
            )
        else:
            updated_run = self.run_repo.update_status(run.run_id, RunStatus.failed)
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
        assert updated_run is not None
        self.event_repo.append(terminal_event)
        return ExecutedRunBundle(
            run=updated_run,
            execution_result=execution_result,
            evidence=evidence,
            review_verdict=review_verdict,
        )
