from __future__ import annotations

import json
import subprocess
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
    assert payload["name"] == "commercial_game_production_pipeline"
    assert payload["execution_mode"] == "serial"
    assert [stage["stage_kind"] for stage in payload["stages"]] == ["agent_role"] * 6 + [
        "capability",
        "capability",
        "agent_role",
        "agent_role",
        "validation_gate",
    ]
    assert payload["stages"][6]["metadata"]["capability"] == "commercial_game_asset_generation"
    assert payload["stages"][7]["metadata"]["capability"] == "commercial_game_task_card_worker"
    assert all(stage["metadata"].get("forbids_fixed_template") is True for stage in payload["stages"])


def test_pipeline_preview_blocks_removed_commercial_cocos_game_template(tmp_path: Path) -> None:
    result = _invoke(tmp_path, "pipeline", "preview", "--template", "commercial_cocos_game")

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["name"] == "deprecated_commercial_cocos_game_pipeline"
    assert payload["metadata"]["template_id"] == "commercial_cocos_game"
    assert payload["metadata"]["fixed_template_delivery_allowed"] is False
    assert [stage["metadata"].get("capability") for stage in payload["stages"]] == [
        "deprecated_cocos_template_removed",
    ]
    assert payload["stages"][0]["metadata"]["replacement_pipeline"] == "commercial_game_production"


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
    evidence_payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence_payload["pipeline"]["name"] == "workflow_self_development_pipeline"
    assert evidence_payload["evidence_path"] == payload["evidence_path"]


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
        "state/pipeline_runs",
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


def test_removed_commercial_cocos_template_blocks_before_old_generators(tmp_path: Path, monkeypatch) -> None:
    import packages.contributions.pipelines.registry as pipeline_registry
    import packages.contributions.pipelines.workflow_runtime as pipeline_module

    def _should_not_run(*_args, **_kwargs):
        raise AssertionError("removed commercial_cocos_game template must not call old generators")

    monkeypatch.setattr(pipeline_registry, "generate_cocos_commercial_asset_manifest", _should_not_run)
    monkeypatch.setattr(pipeline_registry, "run_cocos_game_e2e", _should_not_run)

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

    assert payload["status"] == "blocked"
    assert payload["stop_reason"] == "legacy_cocos_template_removed"
    assert payload["pipeline"]["name"] == "deprecated_commercial_cocos_game_pipeline"
    assert payload["stage_results"][0]["status"] == "blocked"
    assert payload["stage_results"][0]["failure_class"] == "legacy_cocos_template_removed"
    assert payload["stage_results"][0]["output"]["replacement_pipeline"] == "commercial_game_production"


def test_pipeline_cocos_creator_cli_is_diagnostic_only_by_default(tmp_path: Path) -> None:
    from packages.contracts import PipelineStage, PipelineStageKind
    from packages.contributions.pipelines.registry import execute_contribution_capability

    stage = PipelineStage(
        name="Old Cocos scaffold",
        stage_kind=PipelineStageKind.capability,
        order_index=0,
        goal="Should not run as production implementation",
        metadata={"capability": "cocos_creator_cli"},
    )

    payload = execute_contribution_capability(
        "cocos_creator_cli",
        stage=stage,
        root=tmp_path,
        target_dir=tmp_path / "evidence",
        shared_outputs={},
        source_path=tmp_path / "brief.md",
        creator_exe=tmp_path / "CocosCreator.exe",
    )

    assert payload["pipeline_status"] == "blocked"
    assert payload["result"]["failure_class"] == "cocos_scaffold_not_allowed_for_production_pipeline"


def test_pipeline_run_autodiscovers_cocos_creator_for_build(tmp_path: Path, monkeypatch) -> None:
    import apps.operator_cli.pipeline_commands as pipeline_commands

    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    captured: dict[str, object] = {}

    def _fake_run_workflow_pipeline(*_args, **kwargs):
        captured["creator_exe"] = kwargs.get("creator_exe")
        return {"status": "completed", "stage_results": [], "evidence_path": (tmp_path / "evidence.json").as_posix()}

    monkeypatch.setattr(pipeline_commands, "discover_cocos_creator_exe", lambda explicit=None: creator.resolve())
    monkeypatch.setattr(pipeline_commands, "run_workflow_pipeline", _fake_run_workflow_pipeline)

    result = _invoke(
        tmp_path,
        "pipeline",
        "run",
        "--template",
        "commercial_game_production",
        "--require-build",
    )

    assert result.exit_code == 0
    assert captured["creator_exe"] == creator.resolve()


def test_pipeline_run_passes_zero_degradation_options_and_source_path(tmp_path: Path, monkeypatch) -> None:
    import apps.operator_cli.pipeline_commands as pipeline_commands

    source = tmp_path / "brief.md"
    source.write_text("# brief", encoding="utf-8")
    bridge_report = tmp_path / "cocos_editor_bridge_report.json"
    bridge_report.write_text("{}", encoding="utf-8")
    captured: dict[str, object] = {}

    def _fake_run_workflow_pipeline(*_args, **kwargs):
        captured.update(kwargs)
        return {"status": "completed", "stage_results": [], "evidence_path": (tmp_path / "evidence.json").as_posix()}

    monkeypatch.setattr(pipeline_commands, "run_workflow_pipeline", _fake_run_workflow_pipeline)

    result = _invoke(
        tmp_path,
        "pipeline",
        "run",
        "--template",
        "commercial_game_production",
        "--source-path",
        source.as_posix(),
        "--require-cocos-ecosystem",
        "--cocos-bridge-mode",
        "report_only",
        "--cocos-bridge-timeout-seconds",
        "7",
        "--cocos-bridge-report-path",
        bridge_report.as_posix(),
        "--allow-existing-cocos-process",
        "--live-agent-roles",
        "--require-human-player-review",
    )

    assert result.exit_code == 0
    assert captured["source_path"] == source
    assert captured["require_cocos_ecosystem"] is True
    assert captured["cocos_bridge_mode"] == "report_only"
    assert captured["cocos_bridge_timeout_seconds"] == 7
    assert captured["cocos_bridge_report_path"] == bridge_report
    assert captured["allow_existing_cocos_process"] is True
    assert captured["live_agent_roles"] is True
    assert captured["require_human_player_review"] is True


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

    assert payload["status"] == "blocked"
    assert payload["stop_reason"] == "dependency_not_completed"
    assert [stage["status"] for stage in payload["stage_results"]] == ["skipped", "skipped"]


def test_pipeline_run_writes_heartbeat_during_slow_stage(tmp_path: Path, monkeypatch) -> None:
    import time

    from packages.contracts import PipelineStage, PipelineStageKind, WorkflowPipeline
    from packages.core_domain.pipeline import run_workflow_pipeline

    monkeypatch.setenv("WORKFLOW_PIPELINE_HEARTBEAT_INTERVAL_SECONDS", "0.05")
    stage = PipelineStage(
        name="Slow validation",
        stage_kind=PipelineStageKind.validation_gate,
        order_index=0,
        goal="Exercise pipeline heartbeat",
        validation_commands=["slow-check"],
    )
    pipeline = WorkflowPipeline(
        pipeline_id="pipeline_heartbeat_test",
        name="heartbeat_pipeline",
        goal="heartbeat",
        stages=[stage],
    )

    def _slow_runner(command: str, cwd: Path, timeout_seconds: int) -> dict:
        time.sleep(0.13)
        return {"command": command, "cwd": cwd.as_posix(), "exit_code": 0, "stdout": "", "stderr": ""}

    payload = run_workflow_pipeline(
        "heartbeat",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "pipeline_evidence",
        command_runner=_slow_runner,
        pipeline_previewer=lambda *args, **kwargs: pipeline,
    )

    heartbeat_path = Path(payload["heartbeat_path"])
    assert heartbeat_path.exists()
    heartbeats = [json.loads(line) for line in heartbeat_path.read_text(encoding="utf-8").splitlines()]
    assert len(heartbeats) >= 3
    assert heartbeats[0]["status"] == "running"
    assert heartbeats[-1]["status"] == "completed"
    assert any(item["current_stage"]["stage_id"] == stage.stage_id for item in heartbeats)


def test_pipeline_stage_executor_exception_records_failure_evidence_and_final_heartbeat(tmp_path: Path, monkeypatch) -> None:
    from packages.contracts import PipelineStage, PipelineStageKind, WorkflowPipeline
    from packages.core_domain.pipeline import run_workflow_pipeline

    monkeypatch.setenv("WORKFLOW_PIPELINE_HEARTBEAT_INTERVAL_SECONDS", "0.05")
    stage = PipelineStage(
        name="Exploding role",
        stage_kind=PipelineStageKind.agent_role,
        order_index=0,
        goal="Surface executor failures as evidence",
    )
    pipeline = WorkflowPipeline(
        pipeline_id="pipeline_exception_test",
        name="exception_pipeline",
        goal="exception evidence",
        stages=[stage],
    )

    def _exploding_role(**_kwargs) -> dict:
        raise RuntimeError("boom")

    payload = run_workflow_pipeline(
        "exception evidence",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "pipeline_evidence",
        execute_agent_roles=True,
        agent_role_executor=_exploding_role,
        pipeline_previewer=lambda *args, **kwargs: pipeline,
    )

    assert payload["status"] == "failed"
    assert payload["stop_reason"] == "agent_role_executor_exception"
    assert Path(payload["evidence_path"]).exists()
    stage_result = payload["stage_results"][0]
    assert stage_result["status"] == "failed"
    assert stage_result["failure_class"] == "agent_role_executor_exception"
    assert stage_result["output"]["error_type"] == "RuntimeError"
    heartbeats = [json.loads(line) for line in Path(payload["heartbeat_path"]).read_text(encoding="utf-8").splitlines()]
    assert heartbeats[-1]["status"] == "failed"


def test_cocos_manifest_validation_uses_commercial_playable_go(tmp_path: Path) -> None:
    import packages.contributions.pipelines.registry as pipeline_registry

    manifest_path = tmp_path / "cocos_manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")

    payload = pipeline_registry.execute_contribution_validation(
        "cocos_manifest_go_no_go",
        shared_outputs={
            "cocos_e2e": {
                "manifest": {"go_no_go": "GO", "blockers": []},
                "manifest_path": manifest_path.as_posix(),
                "commercial_go_no_go": "GO",
                "commercial_blockers": [],
            }
        },
        require_commercial=True,
    )

    assert payload["pipeline_status"] == "failed"
    gate = payload["result"]
    assert gate["status"] == "failed"
    readiness = gate["output"]["commercial_readiness"]
    assert readiness["technical_smoke_go"] is True
    assert readiness["production_scaffold_go"] is True
    assert readiness["commercial_playable_go"] is False
    assert "missing_player_visible_commercial_playable_evidence" in readiness["commercial_playable_blockers"]


def test_commercial_gate_v2_rejects_event_only_scaffold_go() -> None:
    import packages.contributions.pipelines.registry as pipeline_registry

    payload = pipeline_registry.execute_contribution_validation(
        "commercial_game_production_go_no_go",
        shared_outputs={
            "commercial_game_production": {
                "commercial_playable_go": True,
                "production_scaffold_go": True,
                "technical_smoke_go": True,
                "build": {"creator_exit_code": 36, "artifact_success": True, "fatal_marker_detected": False},
                "playtest": {
                    "console_errors": ["NotSupportedError: media element cannot play this source"],
                    "page_errors": [],
                    "feature_coverage": {
                        "campaignFirstSevenLevels": True,
                        "skinBackgroundCollection": True,
                        "generatedAudioAssets": True,
                    },
                },
                "commercial_feature_coverage": {
                    "commercial_browser_playtest": True,
                    "generated_audio_assets": True,
                },
            },
            "role_output:qa_player_perspective_agent": {
                "llm_call_status": "not_called_by_default",
            },
        },
        require_commercial=True,
        require_cocos_ecosystem=True,
        require_live_agent_roles=True,
        require_human_player_review=True,
    )

    gate = payload["result"]
    assert gate["status"] == "failed"
    assert gate["failure_class"] == "commercial_game_no_degradation_failed"
    blockers = gate["output"]["blockers"]
    assert "same_project_worker_patch_missing" in blockers
    assert "live_role_provider_proof_missing" in blockers
    assert "cocos_ecosystem_bridge_missing" in blockers
    assert "awaiting_human_player_review" in blockers
    assert "cocos_build_nonzero_exit" in blockers
    assert "browser_or_audio_runtime_error" in blockers
    assert "levels_not_distinct_or_less_than_eight" in blockers
    assert "skin_system_not_player_visible" in blockers
    assert gate["output"]["no_degradation_contract"]["go_no_go"] == "NO-GO"


def test_commercial_gate_v2_can_stop_at_human_review_only() -> None:
    import packages.contributions.pipelines.registry as pipeline_registry

    product_features = {
        "eightDistinctLevelGoals": True,
        "skinEquippedVisualChange": True,
        "shopOwnershipStates": True,
        "audioPlaybackVerified": True,
        "bgmStarted": True,
        "volumeToggleUsable": True,
    }
    payload = pipeline_registry.execute_contribution_validation(
        "commercial_game_production_go_no_go",
        shared_outputs={
            "commercial_game_production": {
                "commercial_playable_go": True,
                "same_project_worker_patch_go": True,
                "ecosystem_integration_go": True,
                "build": {"creator_exit_code": 0, "fatal_marker_detected": False},
                "playtest": {"console_errors": [], "page_errors": [], "feature_coverage": product_features},
                "commercial_feature_coverage": product_features,
            },
            "role_output:qa_player_perspective_agent": {
                "llm_call_status": "called",
                "llm_provider_evidence": {"configured": True, "provider": "test"},
            },
        },
        require_commercial=True,
        require_cocos_ecosystem=True,
        require_live_agent_roles=True,
        require_human_player_review=True,
    )

    assert payload["pipeline_status"] == "blocked"
    assert payload["stop_reason"] == "awaiting_human_player_review"
    gate = payload["result"]
    assert gate["status"] == "blocked"
    assert gate["failure_class"] == "awaiting_human_player_review"
    assert gate["output"]["blockers"] == ["awaiting_human_player_review"]
    assert gate["output"]["no_degradation_contract"]["go_no_go"] == "AWAITING_HUMAN_REVIEW"


def test_real_commercial_game_pipeline_runs_registered_stages_and_blocks_on_missing_task_cards(tmp_path: Path) -> None:
    import packages.contributions.pipelines.workflow_runtime as pipeline_module

    payload = pipeline_module.run_workflow_pipeline(
        "commercial game",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "pipeline_evidence",
        template="commercial_game_production",
        execute_agent_roles=True,
        execute_capabilities=True,
        source_path=tmp_path / "design.md",
        require_build=False,
        require_commercial=True,
    )

    assert payload["status"] == "blocked"
    assert [stage["status"] for stage in payload["stage_results"][:6]] == ["completed"] * 6
    asset_stage = payload["stage_results"][6]
    assert asset_stage["status"] == "completed"
    assert asset_stage["execution_backend"] == "commercial_game_asset_generation_v1"
    assert asset_stage["metadata"]["forbids_fixed_template"] is True
    worker_stage = payload["stage_results"][7]
    assert worker_stage["status"] == "blocked"
    assert worker_stage["failure_class"] == "task_card_quality_no_go"
    assert worker_stage["output"]["persistent_project_per_run"] is True


def test_commercial_game_repair_packet_classifies_missing_source_as_operator_input(tmp_path: Path) -> None:
    import packages.contributions.pipelines.workflow_runtime as pipeline_module

    payload = pipeline_module.run_workflow_pipeline(
        "commercial game",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "pipeline_evidence",
        template="commercial_game_production",
        execute_agent_roles=True,
        execute_capabilities=True,
        repair_loop=True,
        db_path=tmp_path / "workflow.db",
        require_build=False,
        require_commercial=True,
    )

    assert payload["status"] == "failed"
    worker_stage = payload["stage_results"][7]
    assert worker_stage["status"] == "completed"
    assert worker_stage["output"]["commercial_playable_blockers"] == [
        "source_path_missing",
        "placeholder_assets_only",
    ]
    assert worker_stage["output"]["commercial_playable_blocker_details"][:1] == [
        {
            "blocker": "source_path_missing",
            "failure_class": "input_precondition_missing",
            "owner_role": "operator_input",
            "repair_mode": "supply_required_input",
            "recoverable_suggestion": "Rerun the pipeline with --pdf-path pointing to an existing source brief or PDF.",
        }
    ]
    supervisor = payload["stage_results"][9]["output"]["structured_output"]
    assert supervisor["repair_packets"][0] == (
        {
            "repair_packet_id": "repair_001_operator_input",
            "finding": "source_path_missing",
            "severity": "high",
            "owner_role": "operator_input",
            "affected_stage": "pipeline_invocation",
            "repair_mode": "supply_required_input",
            "max_attempts": 0,
            "rerun_policy": "rerun_full_pipeline_after_operator_input",
            "forbidden_changes": ["do_not_patch_business_code_for_missing_operator_input"],
            "acceptance": ["required_input_present", "pipeline_rechecked"],
            "recoverable_suggestion": "Rerun the pipeline with --pdf-path pointing to an existing source brief or PDF.",
            "failure_class": "input_precondition_missing",
        }
    )
    assert supervisor["repair_packets"][1]["finding"] == "placeholder_assets_only"
    assert supervisor["repair_packets"][1]["owner_role"] == "commercial_game_asset_generation"
    assert supervisor["repair_packets"][1]["repair_mode"] == "same_project_incremental_patch"


def test_real_asset_stage_skips_provider_when_required_source_is_missing(tmp_path: Path, monkeypatch) -> None:
    import packages.contributions.pipelines.commercial_game_production as commercial_pipeline
    import packages.contributions.pipelines.workflow_runtime as pipeline_module

    def _should_not_call_provider(*_args, **_kwargs):
        raise AssertionError("real asset provider should not run when required source input is missing")

    monkeypatch.setattr(commercial_pipeline, "generate_cocos_commercial_asset_manifest", _should_not_call_provider)

    payload = pipeline_module.run_workflow_pipeline(
        "commercial game",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "pipeline_evidence",
        template="commercial_game_production",
        execute_agent_roles=True,
        execute_capabilities=True,
        repair_loop=True,
        db_path=tmp_path / "workflow.db",
        require_real_assets=True,
        require_build=False,
        require_commercial=True,
    )

    asset_stage = payload["stage_results"][6]
    assert asset_stage["status"] == "completed"
    assert asset_stage["failure_class"] is None
    assert asset_stage["output"]["asset_generation_skipped"] is True
    worker_stage = payload["stage_results"][7]
    assert worker_stage["output"]["commercial_playable_blockers"] == ["source_path_missing"]
    supervisor = payload["stage_results"][9]["output"]["structured_output"]
    assert supervisor["repair_packets"][0]["owner_role"] == "operator_input"


def test_commercial_worker_executes_same_project_task_cards_with_patch_ledger(tmp_path: Path, monkeypatch) -> None:
    from packages.contracts import Run, TaskCard
    import packages.contributions.pipelines.commercial_game_production as commercial_pipeline
    from packages.core_domain.db import migrate
    from packages.core_domain.repositories import RunRepository, TaskRepository

    execute_commercial_game_task_card_worker = commercial_pipeline.execute_commercial_game_task_card_worker
    db_path = tmp_path / "workflow.db"
    pipeline_id = "pipeline_same_project_worker_test"
    migrate(db_path)
    RunRepository(db_path).create(Run(run_id=pipeline_id, goal="commercial worker", preset_id="commercial_game_production"))
    task_repo = TaskRepository(db_path)
    task_repo.create_task_card(
        TaskCard(
            run_id=pipeline_id,
            task_card_id="tc_levels",
            title="Implement levels",
            description="Implement eight distinct level goals on the same Cocos project.",
            goal="Implement eight distinct level goals on the same Cocos project.",
            write_set=["state/pipeline_runs/<run>/cocos_project/assets/scripts"],
            read_set=["role_output:product_gameplay_agent"],
            test_commands=["python -m pytest tests/test_cocos_e2e.py -q"],
            acceptance_criteria=["eight goals visible", "same project patched"],
            evidence_requirements=["same_project_patch", "feature_coverage"],
            blocking_conditions=["new_project_created"],
            model_guidance=["Patch the same project only."],
            execution_mode="same_project_patch",
            risk_level="high",
        )
    )
    task_repo.create_task_card(
        TaskCard(
            run_id=pipeline_id,
            task_card_id="tc_bridge_contract",
            title="Bridge contract",
            description="Workflow infrastructure bridge contract card that should not be run by the business worker.",
            goal="Keep infrastructure cards out of the business implementation worker.",
            write_set=["packages/contributions/games/cocos/ecosystem_bridge.py"],
            read_set=["docs/development/commercial_game_workflow_next_development_2026_04_28.md"],
            test_commands=["python -m pytest tests/test_cocos_e2e.py -q"],
            acceptance_criteria=["bridge checked", "business worker skips it"],
            evidence_requirements=["bridge_evidence"],
            blocking_conditions=["filesystem_only_bridge_claim"],
            model_guidance=["Do not patch game content for this card."],
            execution_mode="capability_contract",
            risk_level="high",
        )
    )
    source = tmp_path / "brief.md"
    source.write_text("# 商业小游戏", encoding="utf-8")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    runner_calls: list[dict[str, object]] = []
    evidence_order: list[str] = []

    def _fake_runner(**kwargs):
        runner_calls.append(kwargs)
        return {
            "status": "completed",
            "receipt_id": "receipt_tc_levels",
            "child_run_id": "run_tc_levels",
            "evidence_id": "evidence_tc_levels",
            "mutation_result": {
                "changed_files": [Path(kwargs["write_set"][0]).as_posix()],
                "applied_patch_hash": "abc123",
                "final_test_status": "passed",
            },
            "watchdog": {"timeout_type": None, "stream_event_count": 3},
            "timeout_seconds": 900,
            "idle_timeout_seconds": 240,
        }

    def _fake_ecosystem_evidence(**kwargs):
        evidence_order.append(f"ecosystem:{kwargs.get('bridge_mode')}")
        return {
            "strict_required": bool(kwargs.get("require_bridge")),
            "ecosystem_integration_go": True,
            "blockers": [],
            "failure_class": None,
            "checks": {"build_api_evidence": True},
        }

    def _fake_runtime_evidence(**_kwargs):
        evidence_order.append("runtime")
        return {
            "technical_smoke_go": True,
            "production_scaffold_go": False,
            "commercial_playable_go": True,
            "commercial_playable_blockers": [],
            "commercial_feature_coverage": {},
            "player_visible_checks": {},
            "manual_player_evidence": {},
            "build": {"creator_exit_code": 0, "fatal_marker_detected": False},
            "playtest": {"console_errors": [], "page_errors": []},
            "manifest_path": (tmp_path / "cocos_project" / "workflow_project_manifest.json").as_posix(),
        }

    monkeypatch.setattr(commercial_pipeline, "collect_cocos_ecosystem_bridge_evidence", _fake_ecosystem_evidence)
    monkeypatch.setattr(commercial_pipeline, "collect_project_runtime_evidence", _fake_runtime_evidence)

    payload = execute_commercial_game_task_card_worker(
        root=tmp_path,
        target_dir=tmp_path / "pipeline_evidence",
        shared_outputs={},
        pipeline_id=pipeline_id,
        db_path=db_path,
        source_path=source,
        creator_exe=creator,
        output_dir=tmp_path / "cocos_project",
        require_build=False,
        require_playtest=False,
        require_commercial=True,
        require_cocos_ecosystem=True,
        cocos_bridge_mode="auto",
        task_card_runner=_fake_runner,
    )

    output = payload["output"]
    assert payload["status"] == "completed"
    assert output["same_project_worker_patch_go"] is True
    assert output["same_project_patch_ledger"]["completed_count"] == 1
    assert output["same_project_patch_ledger"]["entries"][0]["receipt_id"] == "receipt_tc_levels"
    assert output["same_project_patch_ledger"]["entries"][0]["changed_files"]
    assert output["same_project_patch_ledger"]["entries"][0]["watchdog"]["stream_event_count"] == 3
    assert output["same_project_patch_ledger"]["entries"][0]["idle_timeout_seconds"] == 240
    assert output["skipped_non_worker_task_cards"] == ["tc_bridge_contract"]
    assert len(runner_calls) == 1
    assert runner_calls[0]["task_card"].task_card_id == "tc_levels"
    assert evidence_order == ["ecosystem:auto", "runtime", "ecosystem:report_only"]
    assert (tmp_path / "cocos_project" / "workflow_project_source.json").exists()


def test_commercial_worker_blocks_when_no_same_project_business_cards(tmp_path: Path) -> None:
    from packages.contracts import Run, TaskCard
    from packages.contributions.pipelines.commercial_game_production import execute_commercial_game_task_card_worker
    from packages.core_domain.db import migrate
    from packages.core_domain.repositories import RunRepository, TaskRepository

    db_path = tmp_path / "workflow.db"
    pipeline_id = "pipeline_no_business_cards"
    migrate(db_path)
    RunRepository(db_path).create(Run(run_id=pipeline_id, goal="commercial worker", preset_id="commercial_game_production"))
    TaskRepository(db_path).create_task_card(
        TaskCard(
            run_id=pipeline_id,
            task_card_id="tc_gate",
            title="Gate only",
            description="Infrastructure-only card should not satisfy same-project commercial implementation.",
            goal="Infrastructure-only card should not satisfy same-project commercial implementation.",
            write_set=["packages/contributions/games/cocos/no_degradation.py"],
            read_set=["docs/evaluations/commercial_game_pipeline_evaluation_2026_04_28.md"],
            test_commands=["python -m pytest tests/test_pipeline_and_automation_cli.py -q"],
            acceptance_criteria=["gate checked", "no business implementation claim"],
            evidence_requirements=["negative_gate_test"],
            blocking_conditions=["business_worker_claims_gate_card"],
            model_guidance=["Do not generate game content for this infra card."],
            execution_mode="workflow_infra_bugfix",
            risk_level="high",
        )
    )
    source = tmp_path / "brief.md"
    source.write_text("# 商业小游戏", encoding="utf-8")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")

    payload = execute_commercial_game_task_card_worker(
        root=tmp_path,
        target_dir=tmp_path / "pipeline_evidence",
        shared_outputs={},
        pipeline_id=pipeline_id,
        db_path=db_path,
        source_path=source,
        creator_exe=creator,
        output_dir=tmp_path / "cocos_project",
        require_build=False,
        require_playtest=False,
        require_commercial=True,
    )

    output = payload["output"]
    assert output["same_project_worker_patch_go"] is False
    assert "same_project_business_task_cards_missing" in output["commercial_playable_blockers"]
    assert output["same_project_patch_ledger"]["entries"] == []


def test_commercial_task_worker_cli_uses_progress_watchdog(monkeypatch, tmp_path: Path) -> None:
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    calls: list[dict[str, object]] = []

    def _fake_tree_runner(command, cwd, capture_output, text, timeout, idle_timeout, check):
        calls.append(
            {
                "command": command,
                "cwd": cwd,
                "capture_output": capture_output,
                "text": text,
                "timeout": timeout,
                "idle_timeout": idle_timeout,
                "check": check,
            }
        )
        completed = subprocess.CompletedProcess(command, 124, stdout="", stderr="command timed out after 240s (idle_timeout)")
        setattr(completed, "timeout_type", "idle_timeout")
        setattr(completed, "stdout_event_count", 0)
        setattr(completed, "stderr_event_count", 0)
        setattr(completed, "stream_event_count", 0)
        setattr(completed, "last_output_age_seconds", 240.0)
        return completed

    monkeypatch.setattr(worker_cli, "run_subprocess_with_tree_timeout", _fake_tree_runner)

    result = worker_cli._run_json_command(
        ["python", "-m", "apps.operator_cli.main", "run", "from-task-card"],
        cwd=tmp_path,
        timeout_seconds=900,
        idle_timeout_seconds=240,
    )

    assert calls
    assert calls[0]["idle_timeout"] == 240
    assert result["failure_class"] == "provider_idle_timeout"
    assert result["watchdog"]["timeout_type"] == "idle_timeout"
    assert result["watchdog"]["stream_event_count"] == 0
    assert "retry_with_higher_idle_timeout_or_split_task" in result["recoverable_suggestion"]


def test_commercial_game_repair_packet_classifies_missing_creator_as_operator_input() -> None:
    from packages.contributions.pipelines.commercial_game_production import build_supervisor_repair_packets

    packets = build_supervisor_repair_packets(
        structured_output={},
        shared_outputs={"commercial_game_production": {"commercial_playable_blockers": ["cocos_creator_exe_missing"]}},
    )

    assert packets == [
        {
            "repair_packet_id": "repair_001_operator_input",
            "finding": "cocos_creator_exe_missing",
            "severity": "high",
            "owner_role": "operator_input",
            "affected_stage": "pipeline_invocation",
            "repair_mode": "supply_required_input",
            "max_attempts": 0,
            "rerun_policy": "rerun_full_pipeline_after_operator_input",
            "forbidden_changes": ["do_not_patch_business_code_for_missing_operator_input"],
            "acceptance": ["required_input_present", "pipeline_rechecked"],
            "recoverable_suggestion": "Rerun the pipeline with --creator-exe pointing to an installed Cocos Creator executable.",
            "failure_class": "input_precondition_missing",
        }
    ]


def test_commercial_game_repair_packet_classifies_provider_failures_without_project_patch() -> None:
    from packages.contributions.pipelines.commercial_game_production import build_supervisor_repair_packets

    packets = build_supervisor_repair_packets(
        structured_output={},
        shared_outputs={
            "commercial_game_assets": {
                "commercial_asset_blockers": [
                    "required_asset_background_provider_response_error",
                    "required_asset_sfx_clear_provider_usage_limit_exceeded",
                ]
            }
        },
    )

    assert packets[0]["owner_role"] == "commercial_game_asset_generation"
    assert packets[0]["repair_mode"] == "asset_provider_request_repair"
    assert packets[0]["failure_class"] == "provider_response_error"
    assert packets[1]["owner_role"] == "asset_provider_operator"
    assert packets[1]["repair_mode"] == "provider_quota_or_key_recovery"
    assert packets[1]["max_attempts"] == 0
    assert packets[1]["failure_class"] == "provider_usage_limit_exceeded"


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
