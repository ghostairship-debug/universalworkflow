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

    status_result = _invoke(tmp_path, "run", "status", run_id)
    assert status_result.exit_code == 0
    status_payload = json.loads(status_result.stdout)
    assert status_payload["status"] == "completed"
    assert runtime_task_id in status_payload["runtime_task_ids"]

    timeline_result = _invoke(tmp_path, "run", "timeline", run_id, "--json")
    assert timeline_result.exit_code == 0
    timeline = json.loads(timeline_result.stdout)
    assert timeline[-1]["event_type"] == "run_completed"

    evidence_result = _invoke(tmp_path, "task", "evidence", runtime_task_id)
    assert evidence_result.exit_code == 0
    evidence = json.loads(evidence_result.stdout)
    assert evidence["artifact_refs"]


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
