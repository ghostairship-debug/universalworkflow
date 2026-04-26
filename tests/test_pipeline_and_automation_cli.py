from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app


runner = CliRunner()


def _invoke(tmp_path: Path, *args: str):
    return runner.invoke(
        app,
        ["--db-path", str(tmp_path / "workflow.db"), "--workspace-root", str(tmp_path), *args],
    )


def test_pipeline_preview_exposes_h5_game_commercialization_pipeline(tmp_path: Path) -> None:
    result = _invoke(tmp_path, "pipeline", "preview", "--goal", "基于 PDF 做 Cocos H5 俄罗斯方块小游戏")

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["name"] == "h5_game_commercialization_pipeline"
    assert payload["execution_mode"] == "serial"
    assert [stage["stage_kind"] for stage in payload["stages"]] == [
        "agent_role",
        "cluster",
        "capability",
        "validation_gate",
    ]


def test_pipeline_run_does_not_fake_unexecuted_capability_stage(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "pipeline_evidence"
    result = _invoke(
        tmp_path,
        "pipeline",
        "run",
        "--goal",
        "M75 workflow self development",
        "--evidence-dir",
        evidence_dir.as_posix(),
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "blocked"
    assert payload["stop_reason"] == "capability_stage_not_executed"
    assert [stage["status"] for stage in payload["stage_results"]] == ["completed", "blocked", "skipped"]
    evidence_path = Path(payload["evidence_path"])
    assert evidence_path.exists()
    assert json.loads(evidence_path.read_text(encoding="utf-8"))["pipeline"]["name"] == "workflow_self_development_pipeline"


def test_pipeline_run_executes_validation_gate_and_short_circuits_on_failure(tmp_path: Path) -> None:
    from packages.core_domain.pipeline import run_workflow_pipeline

    def _fake_runner(command: str, cwd: Path, timeout_seconds: int) -> dict:
        return {"command": command, "cwd": cwd.as_posix(), "exit_code": 23, "stdout": "", "stderr": "failed"}

    payload = run_workflow_pipeline(
        "M75 workflow self development",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "pipeline_evidence",
        execute_capabilities=True,
        command_runner=_fake_runner,
    )

    assert payload["status"] == "blocked"
    assert payload["stop_reason"] == "unsupported_capability_stage"
    assert payload["stage_results"][1]["status"] == "blocked"
    assert payload["stage_results"][2]["status"] == "skipped"


def test_pipeline_run_uses_automation_lease_for_write_set(tmp_path: Path) -> None:
    create = _invoke(
        tmp_path,
        "automation",
        "lease",
        "create",
        "--allowed-action",
        "pipeline_run",
        "--write-set",
        "state/m73_m76_autopilot/cocos_e2e",
    )
    assert create.exit_code == 0
    lease = json.loads(create.stdout)

    result = _invoke(
        tmp_path,
        "pipeline",
        "run",
        "--goal",
        "基于 PDF 做 Cocos H5 俄罗斯方块小游戏",
        "--automation-lease-id",
        lease["lease_id"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "blocked"
    status = _invoke(tmp_path, "automation", "lease", "status", lease["lease_id"])
    assert status.exit_code == 0


def test_automation_lease_create_status_and_revoke(tmp_path: Path) -> None:
    create = _invoke(
        tmp_path,
        "automation",
        "lease",
        "create",
        "--allowed-action",
        "resume_run",
        "--write-set",
        "packages/example.py",
    )
    assert create.exit_code == 0
    lease = json.loads(create.stdout)
    assert lease["status"] == "active"
    assert lease["allowed_actions"] == ["resume_run"]
    assert "git_push" in lease["denied_actions"]

    status = _invoke(tmp_path, "automation", "lease", "status", lease["lease_id"])
    assert status.exit_code == 0
    assert json.loads(status.stdout)["lease_id"] == lease["lease_id"]

    revoke = _invoke(tmp_path, "automation", "lease", "revoke", lease["lease_id"])
    assert revoke.exit_code == 0
    assert json.loads(revoke.stdout)["status"] == "revoked"
