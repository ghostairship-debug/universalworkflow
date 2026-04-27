from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app
from packages.contributions.games.cocos.capabilities import REQUIRED_PLAYER_VISIBLE_CHECKS


runner = CliRunner()


def _invoke(tmp_path: Path, *args: str):
    return runner.invoke(
        app,
        ["--db-path", str(tmp_path / "workflow.db"), "--workspace-root", str(tmp_path), *args],
    )


def _valid_player_visible_checks(tmp_path: Path) -> dict[str, dict[str, str]]:
    evidence_path = tmp_path / "player_visible_checks.json"
    evidence_path.write_text("{}", encoding="utf-8")
    return {
        check_name: {
            "status": "pass",
            "method": "playwright",
            "evidence_path": evidence_path.as_posix(),
            "evidence_hash": f"sha256:{check_name}",
            "validator_version": "test-v1",
        }
        for check_name in REQUIRED_PLAYER_VISIBLE_CHECKS
    }


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
        "cocos_graph_pressure_test",
        "cocos_asset_factory",
        "cocos_creator_cli",
        None,
    ]
    assert payload["stages"][1]["metadata"]["graph_backed"] is True
    stage_ids = [stage["stage_id"] for stage in payload["stages"]]
    assert [stage["depends_on"] for stage in payload["stages"]] == [
        [],
        [],
        [stage_ids[1]],
        [stage_ids[2]],
        [stage_ids[3]],
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
    assert [stage["status"] for stage in payload["stage_results"]] == ["stubbed", "blocked", "skipped"]
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
    import packages.contributions.pipelines.registry as pipeline_registry
    import packages.contributions.pipelines.workflow_runtime as pipeline_module

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
            "commercial_playable_go": True,
            "player_visible_checks": _valid_player_visible_checks(tmp_path),
        }

    monkeypatch.setattr(pipeline_registry, "generate_cocos_commercial_asset_manifest", _fake_assets)
    monkeypatch.setattr(pipeline_registry, "run_cocos_game_e2e", _fake_cocos)

    payload = pipeline_module.run_workflow_pipeline(
        "commercial game",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "pipeline_evidence",
        template="commercial_cocos_game",
        execute_capabilities=True,
        source_path=tmp_path / "design.pdf",
        creator_exe=tmp_path / "CocosCreator.exe",
        require_build=True,
        require_commercial=True,
    )

    assert payload["status"] == "completed"
    assert payload["pipeline"]["name"] == "commercial_cocos_game_pipeline"
    assert [stage["status"] for stage in payload["stage_results"]] == [
        "stubbed",
        "completed",
        "completed",
        "completed",
        "completed",
    ]
    assert calls == ["asset_factory", "cocos"]
    graph_stage = payload["stage_results"][1]
    assert graph_stage["metadata"]["graph_backed"] is True
    assert graph_stage["execution_backend"] == "langgraph_artifact_only_kernel"
    assert graph_stage["output"]["repair_decision"]["action"] == "no_repair_needed"


def test_pipeline_safe_runner_blocks_shell_metacharacters(tmp_path: Path, monkeypatch) -> None:
    from packages.core_domain.pipeline import _default_command_runner

    def _should_not_run(*args, **kwargs):
        raise AssertionError("blocked pipeline validation command must not reach subprocess.run")

    monkeypatch.setattr("subprocess.run", _should_not_run)

    result = _default_command_runner("python -m pytest | powershell", tmp_path, 10)

    assert result["exit_code"] == 126
    assert result["status"] == "blocked"
    assert "shell metacharacters" in result["stderr"]


def test_pipeline_skipped_dependency_does_not_satisfy_required_dependency(tmp_path: Path, monkeypatch) -> None:
    import packages.core_domain.pipeline as pipeline_module
    from packages.contracts import PipelineStage, PipelineStageKind, WorkflowPipeline

    first = PipelineStage(
        name="Blocked by missing dependency",
        stage_kind=PipelineStageKind.validation_gate,
        order_index=0,
        goal="Cannot run",
        depends_on=["missing-stage"],
        validation_commands=["python -m infra.scripts.check_doc_links"],
    )
    second = PipelineStage(
        name="Requires skipped stage",
        stage_kind=PipelineStageKind.validation_gate,
        order_index=1,
        goal="Must not run",
        depends_on=[first.stage_id],
        validation_commands=["python -m infra.scripts.check_doc_links"],
    )
    pipeline = WorkflowPipeline(
        name="dependency_truth_pipeline",
        goal="dependency truth",
        stages=[first, second],
    )
    monkeypatch.setattr(pipeline_module, "preview_workflow_pipeline", lambda *args, **kwargs: pipeline)

    payload = pipeline_module.run_workflow_pipeline(
        "dependency truth",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "pipeline_evidence",
    )

    assert [stage["status"] for stage in payload["stage_results"]] == ["skipped", "skipped"]


def test_cocos_require_commercial_uses_commercial_playable_go(tmp_path: Path, monkeypatch) -> None:
    import packages.contributions.pipelines.registry as pipeline_registry
    import packages.contributions.pipelines.workflow_runtime as pipeline_module

    def _fake_assets(*, output_dir: Path | str, **_kwargs):
        manifest_path = Path(output_dir) / "commercial_asset_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"go_no_go": "GO", "manifest_path": manifest_path.as_posix(), "blockers": [], "results": []}
        manifest_path.write_text(json.dumps(payload), encoding="utf-8")
        return payload

    def _fake_cocos(**_kwargs):
        manifest_path = tmp_path / "cocos_manifest.json"
        manifest_path.write_text("{}", encoding="utf-8")
        return {
            "manifest": {"go_no_go": "GO", "blockers": []},
            "manifest_path": manifest_path.as_posix(),
            "commercial_go_no_go": "GO",
            "commercial_blockers": [],
        }

    monkeypatch.setattr(pipeline_registry, "generate_cocos_commercial_asset_manifest", _fake_assets)
    monkeypatch.setattr(pipeline_registry, "run_cocos_game_e2e", _fake_cocos)

    payload = pipeline_module.run_workflow_pipeline(
        "commercial game",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "pipeline_evidence",
        template="commercial_cocos_game",
        execute_capabilities=True,
        source_path=tmp_path / "design.pdf",
        creator_exe=tmp_path / "CocosCreator.exe",
        require_build=True,
        require_commercial=True,
    )

    assert payload["status"] == "failed"
    gate = payload["stage_results"][-1]
    assert gate["status"] == "failed"
    readiness = gate["output"]["commercial_readiness"]
    assert readiness["technical_smoke_go"] is True
    assert readiness["production_scaffold_go"] is True
    assert readiness["commercial_playable_go"] is False
    assert "missing_player_visible_commercial_playable_evidence" in readiness["commercial_playable_blockers"]


def test_commercial_cocos_pipeline_records_graph_pressure_stage_without_commercial_claim(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import packages.contributions.pipelines.registry as pipeline_registry
    import packages.contributions.pipelines.workflow_runtime as pipeline_module

    def _fake_assets(*, output_dir: Path | str, **_kwargs):
        manifest_path = Path(output_dir) / "commercial_asset_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"go_no_go": "GO", "manifest_path": manifest_path.as_posix(), "blockers": [], "results": []}
        manifest_path.write_text(json.dumps(payload), encoding="utf-8")
        return payload

    def _fake_cocos(**_kwargs):
        manifest_path = tmp_path / "cocos_manifest.json"
        manifest_path.write_text("{}", encoding="utf-8")
        return {
            "manifest": {"go_no_go": "GO", "blockers": []},
            "manifest_path": manifest_path.as_posix(),
            "commercial_go_no_go": "GO",
            "commercial_playable_go": False,
            "commercial_blockers": [],
        }

    monkeypatch.setattr(pipeline_registry, "generate_cocos_commercial_asset_manifest", _fake_assets)
    monkeypatch.setattr(pipeline_registry, "run_cocos_game_e2e", _fake_cocos)

    payload = pipeline_module.run_workflow_pipeline(
        "commercial game",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "pipeline_evidence",
        template="commercial_cocos_game",
        execute_capabilities=True,
        source_path=tmp_path / "design.pdf",
        creator_exe=tmp_path / "CocosCreator.exe",
        require_build=False,
        require_commercial=True,
    )

    graph_stage = payload["stage_results"][1]
    gate = payload["stage_results"][-1]
    assert graph_stage["status"] == "completed"
    assert Path(graph_stage["output"]["graph_evidence_path"]).exists()
    assert graph_stage["output"]["commercial_claim"] == "pressure_test_only_not_commercial_ready"
    assert graph_stage["output"]["persistent_checkpoint"]["status"] == "completed"
    assert gate["status"] == "failed"
    assert gate["output"]["required_gate"] == "commercial_playable_go"


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
