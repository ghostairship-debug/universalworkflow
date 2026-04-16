from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app


runner = CliRunner()


def _invoke(tmp_path: Path, *args: str):
    return runner.invoke(app, ["--db-path", str(tmp_path / "workflow.db"), *args])


def test_cli_db_reset_and_preset_list(tmp_path: Path) -> None:
    reset_result = _invoke(tmp_path, "db", "reset")
    assert reset_result.exit_code == 0
    payload = json.loads(reset_result.stdout)
    assert payload["seeded_presets"] == ["feature_delivery", "research_spike"]

    preset_result = _invoke(tmp_path, "preset", "list", "--json")
    assert preset_result.exit_code == 0
    presets = json.loads(preset_result.stdout)
    assert {preset["preset_id"] for preset in presets} == {"feature_delivery", "research_spike"}

    suggest_result = _invoke(tmp_path, "run", "suggest-presets", "--goal", "Research the current architecture")
    assert suggest_result.exit_code == 0
    suggestions = json.loads(suggest_result.stdout)
    assert suggestions[0]["preset_id"] == "research_spike"


def test_cli_run_create_status_timeline_and_evidence(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")

    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Build one CLI artifact",
        "--preset",
        "feature_delivery",
        "--prepare",
        "--execute",
    )
    assert create_result.exit_code == 0
    create_payload = json.loads(create_result.stdout)
    run_id = create_payload["run"]["run_id"]
    runtime_task_id = create_payload["prepared_task_id"]
    assert create_payload["run"]["status"] == "completed"
    assert create_payload["review_decision"] == "pass"

    status_result = _invoke(tmp_path, "run", "status", run_id)
    assert status_result.exit_code == 0
    status_payload = json.loads(status_result.stdout)
    assert status_payload["status"] == "completed"
    assert runtime_task_id in status_payload["runtime_task_ids"]
    assert status_payload["effective_review_state"] == "auto_passed"
    assert status_payload["latest_review_verdict"]["decision"] == "pass"
    assert status_payload["failure_reason"] is None
    assert status_payload["recoverability_hint"] == "none"

    timeline_result = _invoke(tmp_path, "run", "timeline", run_id, "--json")
    assert timeline_result.exit_code == 0
    timeline = json.loads(timeline_result.stdout)
    assert timeline[-1]["event_type"] == "run_completed"

    evidence_result = _invoke(tmp_path, "task", "evidence", runtime_task_id)
    assert evidence_result.exit_code == 0
    evidence = json.loads(evidence_result.stdout)
    assert evidence["artifact_refs"]


def test_cli_run_create_with_human_required_returns_awaiting_review(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")

    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Research from create path",
        "--preset",
        "research_spike",
        "--prepare",
        "--execute",
    )
    assert create_result.exit_code == 0
    create_payload = json.loads(create_result.stdout)
    run_id = create_payload["run"]["run_id"]

    assert create_payload["run"]["status"] == "awaiting_review"
    assert create_payload["review_decision"] is None
    assert create_payload["evidence_id"]

    approve_result = _invoke(tmp_path, "run", "approve", run_id)
    assert approve_result.exit_code == 0
    assert json.loads(approve_result.stdout)["run"]["status"] == "completed"


def test_cli_compile_recompile_status_detail_and_handoffs(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Compile me from CLI",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]

    compile_result = _invoke(tmp_path, "run", "compile", run_id)
    assert compile_result.exit_code == 0
    compile_payload = json.loads(compile_result.stdout)
    assert compile_payload["run"]["status"] == "prepared"

    detail_result = _invoke(tmp_path, "run", "status-detail", run_id)
    assert detail_result.exit_code == 0
    detail_payload = json.loads(detail_result.stdout)
    assert detail_payload["next_action"] == "resume"
    assert detail_payload["waiting_reason"] == "awaiting_runtime_resume"
    assert detail_payload["failure_reason"] is None
    assert detail_payload["last_runtime_state"]["graph_step"] == "compiled"
    assert detail_payload["last_review_verdict"] is None
    assert detail_payload["recoverability_hint"] == "resume_run"
    assert detail_payload["handoffs"]
    assert detail_payload["effective_review_state"] == "not_requested"

    inspection_result = _invoke(tmp_path, "run", "inspect", run_id)
    assert inspection_result.exit_code == 0
    inspection_payload = json.loads(inspection_result.stdout)
    assert inspection_payload["passed"] is True
    assert inspection_payload["problem_count"] == 0
    assert inspection_payload["recommended_action"] == "none"

    handoffs_result = _invoke(tmp_path, "run", "handoffs", run_id)
    assert handoffs_result.exit_code == 0
    handoffs_payload = json.loads(handoffs_result.stdout)
    assert len(handoffs_payload) == 1

    recompile_result = _invoke(tmp_path, "run", "recompile", run_id)
    assert recompile_result.exit_code == 0
    recompile_payload = json.loads(recompile_result.stdout)
    assert recompile_payload["run"]["status"] == "prepared"


def test_cli_run_cancel(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Cancel me",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]

    cancel_result = _invoke(tmp_path, "run", "cancel", run_id)
    assert cancel_result.exit_code == 0
    payload = json.loads(cancel_result.stdout)
    assert payload["status"] == "cancelled"

    second_cancel_result = _invoke(tmp_path, "run", "cancel", run_id)
    assert second_cancel_result.exit_code == 0
    second_payload = json.loads(second_cancel_result.stdout)
    assert second_payload["status"] == "cancelled"


def test_cli_resume_runs_compiled_task(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Resume me from CLI",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]

    _invoke(tmp_path, "run", "compile", run_id)
    resume_result = _invoke(tmp_path, "run", "resume", run_id)
    assert resume_result.exit_code == 0
    resume_payload = json.loads(resume_result.stdout)
    assert resume_payload["run"]["status"] == "completed"

    timeline_result = _invoke(tmp_path, "run", "timeline", run_id, "--json")
    timeline = json.loads(timeline_result.stdout)
    assert "runtime_resumed" in [item["event_type"] for item in timeline]


def test_cli_human_review_approve_and_reject_paths(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")

    approve_create = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Research and approve",
        "--preset",
        "research_spike",
    )
    approve_run_id = json.loads(approve_create.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", approve_run_id)
    resume_result = _invoke(tmp_path, "run", "resume", approve_run_id)
    resume_payload = json.loads(resume_result.stdout)
    assert resume_payload["run"]["status"] == "awaiting_review"
    assert resume_payload["review_decision"] is None

    waiting_status = _invoke(tmp_path, "run", "status", approve_run_id)
    waiting_payload = json.loads(waiting_status.stdout)
    assert waiting_payload["effective_review_state"] == "human_pending"
    assert waiting_payload["latest_review_verdict"] is None

    approve_result = _invoke(tmp_path, "run", "approve", approve_run_id)
    assert approve_result.exit_code == 0
    assert json.loads(approve_result.stdout)["run"]["status"] == "completed"

    approved_status = _invoke(tmp_path, "run", "status", approve_run_id)
    approved_payload = json.loads(approved_status.stdout)
    assert approved_payload["effective_review_state"] == "human_approved"
    assert approved_payload["latest_review_verdict"]["reviewer_type"] == "human"

    reject_create = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Research and reject",
        "--preset",
        "research_spike",
    )
    reject_run_id = json.loads(reject_create.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", reject_run_id)
    _invoke(tmp_path, "run", "resume", reject_run_id)

    reject_result = _invoke(tmp_path, "run", "reject", reject_run_id)
    assert reject_result.exit_code == 0
    assert json.loads(reject_result.stdout)["run"]["status"] == "failed"

    rejected_status = _invoke(tmp_path, "run", "status", reject_run_id)
    rejected_payload = json.loads(rejected_status.stdout)
    assert rejected_payload["effective_review_state"] == "human_rejected"
    assert rejected_payload["latest_review_verdict"]["decision"] == "fail"
    assert rejected_payload["failure_reason"] == "human_review_rejected"
    assert rejected_payload["recoverability_hint"] == "inspect_evidence_then_recompile"
