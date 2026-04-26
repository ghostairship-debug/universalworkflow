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


def test_pipeline_preview_exposes_commercial_cocos_game_template(tmp_path: Path) -> None:
    result = _invoke(tmp_path, "pipeline", "preview", "--template", "commercial_cocos_game")

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["name"] == "commercial_cocos_game_pipeline"
    assert payload["metadata"]["template_id"] == "commercial_cocos_game"
    assert [stage["metadata"].get("capability") for stage in payload["stages"]] == [
        None,
        "cocos_asset_factory",
        "cocos_creator_cli",
        None,
    ]
    stage_ids = [stage["stage_id"] for stage in payload["stages"]]
    assert [stage["depends_on"] for stage in payload["stages"]] == [
        [],
        [stage_ids[0]],
        [stage_ids[1]],
        [stage_ids[2]],
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


def test_commercial_cocos_template_executes_asset_factory_before_cocos(tmp_path: Path, monkeypatch) -> None:
    import packages.core_domain.pipeline as pipeline_module

    calls: list[str] = []

    def _fake_assets(*, output_dir: Path | str, **_kwargs):
        calls.append("asset_factory")
        manifest_path = Path(output_dir) / "commercial_asset_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "go_no_go": "GO",
            "manifest_path": manifest_path.as_posix(),
            "blockers": [],
            "feature_coverage": {"commercial_polish_pass": True},
            "results": [{"asset_name": "background", "status": "completed", "artifact_paths": ["background.png"]}],
        }
        manifest_path.write_text(json.dumps(payload), encoding="utf-8")
        return payload

    def _fake_cocos(**kwargs):
        calls.append("cocos")
        assert kwargs["commercial_assets_payload"]["go_no_go"] == "GO"
        assert kwargs["generate_commercial_assets"] is False
        manifest_path = tmp_path / "cocos_manifest.json"
        manifest_path.write_text("{}", encoding="utf-8")
        return {
            "manifest": {"go_no_go": "GO", "blockers": []},
            "manifest_path": manifest_path.as_posix(),
            "commercial_go_no_go": "GO",
            "commercial_blockers": [],
        }

    monkeypatch.setattr(pipeline_module, "generate_cocos_commercial_asset_manifest", _fake_assets)
    monkeypatch.setattr(pipeline_module, "run_cocos_game_e2e", _fake_cocos)

    payload = pipeline_module.run_workflow_pipeline(
        "commercial game",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "pipeline_evidence",
        template="commercial_cocos_game",
        execute_capabilities=True,
        pdf_path=tmp_path / "design.pdf",
        cocos_creator_exe=tmp_path / "CocosCreator.exe",
        require_build=True,
        require_commercial=True,
    )

    assert payload["status"] == "completed"
    assert payload["pipeline"]["name"] == "commercial_cocos_game_pipeline"
    assert [stage["status"] for stage in payload["stage_results"]] == [
        "completed",
        "completed",
        "completed",
        "completed",
    ]
    assert calls == ["asset_factory", "cocos"]


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
