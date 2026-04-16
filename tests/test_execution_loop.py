from __future__ import annotations

import os
from pathlib import Path

from packages.contracts import TaskKind, TaskPacket
from packages.core_domain.auto_review import AutoReviewV0
from packages.core_domain.db import migrate
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

    assert bundle.run.status == "awaiting_review"
    assert bundle.review_verdict is None

    approved = service.approve_run_review(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert approved.run.status == "completed"
    assert detail["runtime_state_refs"][0]["is_terminal"] is True
    assert detail["runtime_state_refs"][0]["graph_step"] == "completed"


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
