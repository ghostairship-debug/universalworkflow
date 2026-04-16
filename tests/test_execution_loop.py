from __future__ import annotations

import os
from pathlib import Path

import pytest

from packages.contracts import RuntimeGraphStep, RuntimeStateRef, TaskKind, TaskPacket
from packages.core_domain.auto_review import AutoReviewV0
from packages.core_domain.db import migrate, unit_of_work
from packages.core_domain.errors import InvalidStateTransitionError
from packages.core_domain.evidence_builder import EvidenceBuilder
from packages.core_domain.repositories import PresetRepository
from packages.core_domain.services import OrchestratorService
from packages.worker_adapters.shell_adapter import ExecutionResult, ShellAdapter, utc_now


def test_execute_run_success_path(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Build one artifact", "feature_delivery")
    service.prepare_run(run.run_id)
    bundle = service.execute_run(run.run_id)

    assert bundle.run.status == "completed"
    assert bundle.execution_result.return_code == 0
    assert bundle.evidence.artifact_refs
    artifact_ref = bundle.evidence.artifact_refs[0]
    assert artifact_ref.sha256
    assert artifact_ref.mtime > 0
    assert artifact_ref.size_bytes > 0
    assert bundle.review_verdict.decision == "pass"


def test_compile_run_creates_handoff_and_runtime_state(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Prepare compile snapshot", "feature_delivery")
    prepared = service.compile_run(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert prepared.run.status == "prepared"
    assert detail["handoffs"]
    assert detail["runtime_state_refs"]
    assert detail["next_action"] == "resume"


def test_resume_run_updates_terminal_runtime_state(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Resume through prepared state", "feature_delivery")
    service.compile_run(run.run_id)
    bundle = service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert bundle.run.status == "completed"
    assert detail["runtime_state_refs"][0]["is_terminal"] is True
    assert detail["runtime_state_refs"][0]["graph_step"] == "completed"


def test_human_required_path_waits_for_manual_review(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Research runtime choices", "research_spike")
    service.compile_run(run.run_id)
    bundle = service.resume_run(run.run_id)
    waiting_detail = service.get_status_detail(run.run_id)

    assert bundle.run.status == "awaiting_review"
    assert bundle.review_verdict is None
    assert waiting_detail["effective_review_state"] == "human_pending"
    assert waiting_detail["latest_review_verdict"] is None

    approved = service.approve_run_review(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert approved.run.status == "completed"
    assert detail["runtime_state_refs"][0]["is_terminal"] is True
    assert detail["runtime_state_refs"][0]["graph_step"] == "completed"
    assert detail["effective_review_state"] == "human_approved"
    assert detail["latest_review_verdict"]["reviewer_type"] == "human"


def test_execute_run_rejects_invalid_transition_after_completion(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Complete then retry", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)

    with pytest.raises(InvalidStateTransitionError):
        service.resume_run(run.run_id)


def test_human_review_rejects_invalid_transition_before_review_state(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Approve too early", "feature_delivery")
    service.compile_run(run.run_id)

    with pytest.raises(InvalidStateTransitionError):
        service.approve_run_review(run.run_id)


def test_auto_review_fails_for_non_zero_return_code(tmp_path: Path) -> None:
    task_packet = TaskPacket(
        runtime_task_id="task_fail",
        run_id="run_fail",
        task_kind=TaskKind.shell_exec,
        command=["python", "-c", "import sys; sys.exit(2)"],
        working_directory=str(tmp_path),
    )
    result = ShellAdapter().launch(task_packet)
    evidence = EvidenceBuilder().build("run_fail", "task_fail", result)
    verdict = AutoReviewV0().review(evidence)

    assert result.return_code == 2
    assert verdict.decision == "fail"


def test_status_detail_projects_auto_review_state(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Auto review projection", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert detail["effective_review_state"] == "auto_passed"
    assert detail["latest_review_verdict"]["reviewer_type"] == "auto"
    assert detail["latest_review_verdict"]["decision"] == "pass"


def test_status_detail_projects_human_reject_state(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Human reject projection", "research_spike")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    service.reject_run_review(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert detail["effective_review_state"] == "human_rejected"
    assert detail["latest_review_verdict"]["reviewer_type"] == "human"
    assert detail["latest_review_verdict"]["decision"] == "fail"


def test_status_detail_exposes_operator_diagnostics(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    prepared_run = service.create_run("Prepared diagnostics", "feature_delivery")
    service.compile_run(prepared_run.run_id)
    prepared_detail = service.get_status_detail(prepared_run.run_id)

    assert prepared_detail["failure_reason"] is None
    assert prepared_detail["waiting_reason"] == "awaiting_runtime_resume"
    assert prepared_detail["last_runtime_state"]["graph_step"] == "compiled"
    assert prepared_detail["last_review_verdict"] is None
    assert prepared_detail["recoverability_hint"] == "resume_run"

    failed_run = service.create_run("Rejected diagnostics", "research_spike")
    service.compile_run(failed_run.run_id)
    service.resume_run(failed_run.run_id)
    service.reject_run_review(failed_run.run_id)
    failed_detail = service.get_status_detail(failed_run.run_id)

    assert failed_detail["failure_reason"] == "human_review_rejected"
    assert failed_detail["waiting_reason"] is None
    assert failed_detail["last_runtime_state"]["graph_step"] == "failed"
    assert failed_detail["recoverability_hint"] == "inspect_evidence_then_recompile"


def test_inspection_reports_completed_runtime_non_terminal(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Completed but runtime live", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    state_ref = service.runtime_state_repo.list_for_run(run.run_id)[0]
    service.runtime_state_repo.upsert(
        RuntimeStateRef(
            state_ref_id=state_ref.state_ref_id,
            run_id=state_ref.run_id,
            runtime_task_id=state_ref.runtime_task_id,
            graph_step=RuntimeGraphStep.awaiting_review,
            state_payload={**state_ref.state_payload, "corrupted": True},
            is_terminal=False,
            created_at=state_ref.created_at,
        )
    )

    inspection = service.inspect_run_state(run.run_id)

    assert inspection["passed"] is False
    assert inspection["problem_count"] == 1
    assert inspection["problems"][0]["problem"] == "completed_runtime_non_terminal"
    assert inspection["recommended_action"] == "reconcile_runtime_state_ref"


def test_inspection_reports_awaiting_review_missing_evidence(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Awaiting review missing evidence", "research_spike")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    with unit_of_work(db_path) as connection:
        connection.execute("DELETE FROM evidence WHERE run_id = ?", (run.run_id,))

    inspection = service.inspect_run_state(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert inspection["passed"] is False
    assert inspection["problems"][0]["problem"] == "awaiting_review_missing_evidence"
    assert inspection["recommended_action"] == "rebuild_or_replay_evidence"
    assert detail["waiting_reason"] == "awaiting_human_review_missing_evidence"


def test_inspection_reports_cancelled_with_live_runtime(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Cancelled but runtime live", "feature_delivery")
    service.compile_run(run.run_id)
    cancelled = service.cancel_run(run.run_id)
    assert cancelled.status == "cancelled"

    state_ref = service.runtime_state_repo.list_for_run(run.run_id)[0]
    service.runtime_state_repo.upsert(
        RuntimeStateRef(
            state_ref_id=state_ref.state_ref_id,
            run_id=state_ref.run_id,
            runtime_task_id=state_ref.runtime_task_id,
            graph_step=RuntimeGraphStep.compiled,
            state_payload={**state_ref.state_payload, "corrupted": True},
            is_terminal=False,
            created_at=state_ref.created_at,
        )
    )

    inspection = service.inspect_run_state(run.run_id)

    assert inspection["passed"] is False
    assert inspection["problems"][0]["problem"] == "cancelled_with_live_runtime"
    assert inspection["recommended_action"] == "terminate_or_reconcile_runtime"


def test_inspection_reports_prepared_compile_snapshot_incomplete_without_side_effects(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Prepared but incomplete snapshot", "feature_delivery")
    prepared = service.compile_run(run.run_id)
    timeline_before = service.get_timeline(run.run_id)
    with unit_of_work(db_path) as connection:
        connection.execute("DELETE FROM task_packets WHERE run_id = ?", (run.run_id,))

    inspection = service.inspect_run_state(run.run_id)
    timeline_after = service.get_timeline(run.run_id)

    assert inspection["passed"] is False
    assert inspection["problems"][0]["problem"] == "prepared_compile_snapshot_incomplete"
    assert inspection["problems"][0]["details"]["missing_components"] == [f"task_packet:{prepared.task_packet.runtime_task_id}"]
    assert inspection["recommended_action"] == "recompile_run"
    assert service.get_run(run.run_id).status == "prepared"
    assert service.task_repo.get_task_packet(prepared.task_packet.runtime_task_id) is None
    assert [event.event_id for event in timeline_after] == [event.event_id for event in timeline_before]


def test_out_of_band_change_is_recorded_as_known_gap(tmp_path: Path) -> None:
    artifact_path = tmp_path / "artifact.md"
    artifact_path.write_text("initial", encoding="utf-8")
    finished_at = utc_now()
    os.utime(artifact_path, (finished_at.timestamp() + 5, finished_at.timestamp() + 5))

    result = ExecutionResult(
        runtime_task_id="task_oob",
        return_code=0,
        stdout="ok",
        stderr="",
        started_at=finished_at,
        finished_at=finished_at,
        duration_ms=1,
        artifact_paths=[artifact_path.as_posix()],
    )
    evidence = EvidenceBuilder().build("run_oob", "task_oob", result)

    assert evidence.known_gaps
    assert "out-of-band change" in evidence.known_gaps[0]
