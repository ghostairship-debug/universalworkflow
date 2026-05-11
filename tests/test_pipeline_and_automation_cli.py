from __future__ import annotations

import json
import sqlite3
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app


runner = CliRunner()


def _invoke(tmp_path: Path, *args: str):
    return runner.invoke(
        app,
        ["--db-path", str(tmp_path / "workflow.db"), "--workspace-root", str(tmp_path), *args],
    )


def _pipeline_stage_by_capability(payload: dict, capability: str) -> dict:
    for stage in payload["stage_results"]:
        if stage.get("metadata", {}).get("capability") == capability:
            return stage
    raise AssertionError(f"missing capability stage result: {capability}")


def _pipeline_stage_by_role(payload: dict, role_id: str) -> dict:
    for stage in payload["stage_results"]:
        if stage.get("metadata", {}).get("role_id") == role_id:
            return stage
    raise AssertionError(f"missing role stage result: {role_id}")


def _completed_pre_capability_agent_roles(payload: dict, capability: str) -> list[dict]:
    target = _pipeline_stage_by_capability(payload, capability)
    target_order = int(target.get("order_index") or 0)
    return [
        stage
        for stage in payload["stage_results"]
        if stage.get("metadata", {}).get("role_id")
        and int(stage.get("order_index") or 0) < target_order
    ]


def _visible_cli_session(tmp_path: Path, task_card_id: str = "tc_visible") -> dict[str, object]:
    session_dir = tmp_path / "visible_cli_sessions" / task_card_id
    return {
        "status": "completed",
        "pid": 1234,
        "window_title": f"workflowctl {task_card_id}",
        "argv": ["workflowctl", "run", "from-task-card"],
        "cwd": tmp_path.as_posix(),
        "stdout_log_path": (session_dir / "stdout.log").as_posix(),
        "stderr_log_path": (session_dir / "stderr.log").as_posix(),
        "stream_log_path": (session_dir / "stream.jsonl").as_posix(),
        "session_path": (session_dir / "visible_cli_session.json").as_posix(),
        "started_at": "2026-05-03T00:00:00+00:00",
        "ended_at": "2026-05-03T00:00:01+00:00",
    }


def _commercial_blueprint_task_card(pipeline_id: str, task_card_id: str = "tc_core"):
    from packages.contracts import TaskCard

    return TaskCard(
        run_id=pipeline_id,
        task_card_id=task_card_id,
        title=f"Task {task_card_id}",
        description=f"{task_card_id} patches the same Cocos project from the active phase blueprint.",
        goal=f"Patch {task_card_id} in the same project without creating or switching project roots.",
        write_set=["state/pipeline_runs/<run>/cocos_project/assets/scripts"],
        read_set=["brief.md"],
        test_commands=["python -m pytest tests/test_cocos_e2e.py -q"],
        acceptance_criteria=["same project patched", "fresh worker evidence remains valid"],
        evidence_requirements=["same_project_patch"],
        blocking_conditions=["new_project_created"],
        model_guidance=["Patch the same Cocos project only."],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
        metadata={
            "task_card_generation_source": "active_phase_execution_blueprint",
            "phase_execution_blueprint_schema": "universal_game_phase_execution_blueprint_v1",
            "task_card_compile_report_schema": "universal_game_task_card_compile_report_v1",
            "task_card_compile_go": True,
            "task_card_compile_blockers": [],
            "requirement_coverage_required": True,
            "required_requirement_ids": ["REQ-S001-C001-001"],
            "covered_requirement_ids": ["REQ-S001-C001-001"],
            "missing_requirement_ids": [],
            "human_visible_cli_required": True,
            "execution_visibility_mode": "human_visible_cli_enforced",
        },
    )


def _seed_commercial_worker_db(tmp_path: Path, pipeline_id: str) -> Path:
    from packages.contracts import Run
    from packages.core_domain.db import migrate
    from packages.core_domain.repositories import RunRepository, TaskRepository

    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    RunRepository(db_path).create(Run(run_id=pipeline_id, goal="commercial worker", preset_id="commercial_game_production"))
    TaskRepository(db_path).create_task_card(_commercial_blueprint_task_card(pipeline_id))
    return db_path


def _passing_ai_surrogate_evidence() -> dict[str, object]:
    return {
        "schema_version": "universal_ai_surrogate_playtest_quality_v1",
        "ai_surrogate_playtest_go": True,
        "blockers": [],
        "quality_score": 0.92,
        "coverage": {
            "core_loop": True,
            "input_responsiveness": True,
            "ui_readability": True,
            "audio_feedback": True,
            "progression": True,
        },
        "execution": {
            "packet_id": "ai-playtest-packet-001",
            "fresh_execution": True,
            "device_profiles": ["desktop_1080p", "mobile_portrait"],
        },
    }


def _passing_commercial_quality_scorecard() -> dict[str, object]:
    return {
        "schema_version": "commercial_game_quality_scorecard_v1",
        "go": True,
        "status": "completed",
        "total_score": 100,
        "area_scores": {
            "core_playability": 20,
            "portrait_mobile_ux": 15,
            "ui_polish": 15,
            "art_completeness": 15,
            "animation_feedback": 10,
            "audio_fit": 10,
            "content_depth": 10,
            "r5_no_regression": 5,
        },
        "hard_blockers": [],
        "blockers": [],
        "screenshots": ["mobile.png"],
        "replay_artifacts": ["real_pointer_drag.json"],
        "source": {"score_source": "test"},
    }


def _passing_commercial_assets(tmp_path: Path) -> dict[str, object]:
    manifest_path = tmp_path / "commercial_asset_manifest.json"
    manifest_path.write_text(json.dumps({"go_no_go": "GO", "assets": ["block_skin_01"]}), encoding="utf-8")
    return {
        "schema_version": "commercial_game_asset_stage_v1",
        "commercial_assets_go": True,
        "commercial_asset_blockers": [],
        "asset_manifest_path": manifest_path.as_posix(),
        "asset_manifest": {"go_no_go": "GO", "manifest_path": manifest_path.as_posix()},
        "provider_evidence": [{"provider": "local_stable_asset_manifest", "configured": True}],
        "placeholder_only": False,
    }


def _provider_visible_cli_session(tmp_path: Path, task_card_id: str) -> dict[str, object]:
    session_dir = tmp_path / "provider_visible_cli_sessions" / task_card_id
    return {
        "status": "completed",
        "provider": "codex",
        "provider_pid": 5678,
        "argv": ["codex", "exec"],
        "cwd": tmp_path.as_posix(),
        "stdout_log_path": (session_dir / "stdout.log").as_posix(),
        "stderr_log_path": (session_dir / "stderr.log").as_posix(),
        "stream_log_path": (session_dir / "stream.jsonl").as_posix(),
        "started_at": "2026-05-03T00:00:00+00:00",
        "ended_at": "2026-05-03T00:00:02+00:00",
    }


def _commercial_feature_coverage() -> dict[str, bool]:
    return {
        "mobilePortraitUi": True,
        "audioPlaybackVerified": True,
        "bgmStarted": True,
        "sfxPlaybackVerified": True,
        "volumeToggleUsable": True,
        "shopOwnershipStates": True,
        "skinEquippedVisualChange": True,
        "chineseUiPanelsVisible": True,
        "levelFlowPlayable": True,
        "failureReviveFeedback": True,
        "animationFeedbackVerified": True,
        "dragPlacement": True,
        "chineseUi": True,
        "generatedArtAssets": True,
        "cocosAssetBindings": True,
    }


def _passing_runtime_evidence(tmp_path: Path, project_dir: Path) -> dict[str, object]:
    feature_coverage = _commercial_feature_coverage()
    level_goals = [f"关卡{i}目标" for i in range(1, 9)]
    build_output = project_dir / "build" / "web-mobile"
    return {
        "technical_smoke_go": True,
        "production_scaffold_go": True,
        "commercial_playable_go": True,
        "commercial_playable_blockers": [],
        "commercial_feature_coverage": feature_coverage,
        "player_visible_checks": feature_coverage,
        "manual_player_evidence": {},
        "gameplay_semantic_evidence": {
            "board_state": {"rows": 10, "cols": 10},
            "piece_shapes": [{"cells": [[0, 0]]}, {"cells": [[0, 0], [1, 0]]}],
            "candidate_tray": [{}, {}, {}],
            "semantic_traces": {
                "placement": "trace/placement.json",
                "line_clear": "trace/line_clear.json",
                "candidate_refresh": "trace/candidate_refresh.json",
                "game_over": "trace/game_over.json",
                "anti_stall": "trace/anti_stall.json",
            },
        },
        "product_body_evidence": {
            "scene_nodes": ["Canvas", "Board", "CandidateTray", "LevelPanel", "ShopPanel"],
            "cocos_component_bindings": ["BoardRuntime", "RuleEngine", "CandidateTray", "LevelFlow", "ShopSkinPanel"],
            "product_body_path": (project_dir / "workflow_runtime_evidence" / "product_body_evidence.raw.json").as_posix(),
        },
        "product_depth_evidence": {
            "level_goals": level_goals,
            "distinct_level_goal_count": 8,
            "feature_coverage": feature_coverage,
            "player_visible_checks": feature_coverage,
            "screenshots": [(tmp_path / "mobile.png").as_posix()],
        },
        "build": {
            "creator_exit_code": 0,
            "fatal_marker_detected": False,
            "artifact_success": True,
            "build_output_path": build_output.as_posix(),
        },
        "playtest": {
            "passed": True,
            "url": "http://127.0.0.1:3000/index.html",
            "screenshots": [(tmp_path / "mobile.png").as_posix()],
            "console_errors": [],
            "page_errors": [],
            "real_pointer_drag_go": True,
            "real_pointer_drag": {"go": True, "board_state_changed": True, "score_changed": True},
            "portrait_orientation_go": True,
            "portrait_orientation": {
                "go": True,
                "viewport": {"width": 390, "height": 844},
                "screen_orientation": "portrait",
                "design_resolution": {"width": 1080, "height": 1920},
            },
            "feature_coverage": feature_coverage,
        },
        "commercial_quality_scorecard": _passing_commercial_quality_scorecard(),
        "manifest_path": (project_dir / "workflow_project_manifest.json").as_posix(),
    }


def _failing_cocos_build_runtime_evidence(tmp_path: Path, project_dir: Path) -> dict[str, object]:
    payload = _passing_runtime_evidence(tmp_path, project_dir)
    payload["production_scaffold_go"] = False
    payload["commercial_playable_go"] = False
    payload["commercial_playable_blockers"] = [
        "cocos_build_fatal_marker_detected",
        "cocos_build_no_artifact_success",
        "cocos_component_binding_missing",
    ]
    payload["product_body_evidence"] = {"scene_nodes": [], "cocos_component_bindings": []}
    payload["build"] = {
        "creator_exit_code": 36,
        "fatal_marker_detected": True,
        "artifact_success": False,
        "build_output_path": "",
        "stderr_tail": "Missing class WorkflowBlockPuzzleBoardBinding",
    }
    payload["playtest"] = {
        "status": "blocked",
        "passed": False,
        "failure_class": "missing_build_output",
        "screenshots": [],
        "console_errors": [],
        "page_errors": [],
        "feature_coverage": {},
    }
    return payload


def _write_machine_gate_repair_artifacts(project_dir: Path) -> None:
    artifacts = {
        project_dir / "workflow_runtime_evidence" / "machine_gate_repair_evidence.json": {"go": True, "blockers": []},
        project_dir / "workflow_runtime_evidence" / "cocos_ecosystem_bridge_evidence.json": {
            "ecosystem_integration_go": True,
            "blockers": [],
        },
        project_dir / "workflow_runtime_evidence" / "product_body_evidence.raw.json": {"go": True, "blockers": []},
        project_dir / "workflow_runtime_evidence" / "scene_prefab_binding_evidence.json": {"go": True, "blockers": []},
        project_dir / "settings" / "v2" / "packages" / "scene.json": {"currentSceneUuid": "block-puzzle-player-visible"},
    }
    for path, payload in artifacts.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for component in [
        "WorkflowBlockPuzzleBoardBinding",
        "WorkflowBlockPuzzleSceneRuntime",
        "WorkflowCandidateTrayBinding",
        "WorkflowCandidatePrefabBinding",
        "WorkflowBuildProductBodyWitness",
    ]:
        path = project_dir / "assets" / "scripts" / "runtime" / "workflow" / f"{component}.ts"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"@ccclass('{component}') export class {component} {{}}\n", encoding="utf-8")
    prefab = project_dir / "assets" / "prefabs" / "workflow_block_puzzle_board_binding.prefab"
    prefab.parent.mkdir(parents=True, exist_ok=True)
    prefab.write_text('{"__type__":"cc.Prefab"}\n', encoding="utf-8")


def _seed_child_workflow_state(
    db_path: Path,
    *,
    goal: str,
    receipt_id: str,
    heartbeat_age_seconds: int,
) -> None:
    now = datetime.now(UTC)
    receipt_created = (now - timedelta(seconds=60)).isoformat()
    run_created = (now - timedelta(seconds=30)).isoformat()
    heartbeat_at = (now - timedelta(seconds=heartbeat_age_seconds)).isoformat()
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE operator_action_receipts (receipt_id TEXT PRIMARY KEY, created_at TEXT, consumed_at TEXT);
            CREATE TABLE runs (run_id TEXT PRIMARY KEY, goal TEXT, status TEXT, created_at TEXT, updated_at TEXT);
            CREATE TABLE runtime_attempts (
              attempt_id TEXT PRIMARY KEY,
              run_id TEXT,
              runtime_task_id TEXT,
              status TEXT,
              created_at TEXT,
              closed_at TEXT,
              close_reason TEXT,
              sequence_no INTEGER
            );
            CREATE TABLE worker_leases (
              lease_id TEXT PRIMARY KEY,
              run_id TEXT,
              adapter_name TEXT,
              status TEXT,
              heartbeat_at TEXT,
              lease_expires_at TEXT,
              released_at TEXT,
              release_reason TEXT,
              created_at TEXT
            );
            CREATE TABLE run_events (
              event_id TEXT PRIMARY KEY,
              run_id TEXT,
              event_type TEXT,
              object_type TEXT,
              object_id TEXT,
              summary TEXT,
              payload_json TEXT,
              schema_version TEXT,
              created_at TEXT
            );
            """
        )
        connection.execute(
            "INSERT INTO operator_action_receipts (receipt_id, created_at, consumed_at) VALUES (?, ?, ?)",
            (receipt_id, receipt_created, (now - timedelta(seconds=50)).isoformat()),
        )
        connection.execute(
            "INSERT INTO runs (run_id, goal, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("child_run_001", goal, "running", run_created, run_created),
        )
        connection.execute(
            """
            INSERT INTO runtime_attempts (
              attempt_id, run_id, runtime_task_id, status, created_at, closed_at, close_reason, sequence_no
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("attempt_001", "child_run_001", "task_001", "current", run_created, None, None, 1),
        )
        connection.execute(
            """
            INSERT INTO worker_leases (
              lease_id, run_id, adapter_name, status, heartbeat_at, lease_expires_at, released_at, release_reason, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "lease_001",
                "child_run_001",
                "codex",
                "active",
                heartbeat_at,
                (now + timedelta(minutes=10)).isoformat(),
                None,
                None,
                run_created,
            ),
        )
        connection.execute(
            """
            INSERT INTO run_events (
              event_id, run_id, event_type, object_type, object_id, summary, payload_json, schema_version, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "event_heartbeat_001",
                "child_run_001",
                "worker_heartbeat_received",
                "runtime_task",
                "task_001",
                "heartbeat",
                "{}",
                "v1",
                heartbeat_at,
            ),
        )
        connection.commit()


def test_pipeline_preview_exposes_h5_game_commercialization_pipeline(tmp_path: Path) -> None:
    result = _invoke(tmp_path, "pipeline", "preview", "--goal", "基于 PDF 做 Cocos H5 俄罗斯方块小游戏")

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["name"] == "commercial_game_production_pipeline"
    assert payload["execution_mode"] == "serial"
    role_ids = [stage["metadata"].get("role_id") for stage in payload["stages"] if stage["stage_kind"] == "agent_role"]
    assert role_ids == [
        "intake_packaging_agent",
        "product_gameplay_agent",
        "mechanics_system_designer_agent",
        "level_economy_designer_agent",
        "ui_experience_agent",
        "ui_ux_polish_agent",
        "art_direction_agent",
        "animation_vfx_feedback_agent",
        "audio_feedback_designer_agent",
        "technical_plan_agent",
        "multimodal_generation_agent",
        "ai_playtest_oracle_agent",
        "task_card_generation_agent",
        "qa_player_perspective_agent",
        "commercial_quality_score_agent",
        "supervisor",
    ]
    capabilities = [stage["metadata"].get("capability") for stage in payload["stages"] if stage["stage_kind"] == "capability"]
    assert capabilities == ["commercial_game_asset_generation", "commercial_game_task_card_worker"]
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
    assert "blocked_by_same_project_worker" in blockers
    assert "cocos_build_nonzero_exit" not in blockers
    assert "browser_or_audio_runtime_error" not in blockers
    assert "levels_not_distinct_or_less_than_eight" not in blockers
    assert "skin_system_not_player_visible" not in blockers
    assert gate["output"]["no_degradation_contract"]["commercial_final_gate_evidence"]["blocked_downstream_stages"] == [
        "cocos_build",
        "browser_playtest",
        "product_depth",
    ]
    assert gate["output"]["no_degradation_contract"]["go_no_go"] == "NO-GO"


def test_commercial_gate_v2_can_stop_at_human_review_only() -> None:
    import packages.contributions.pipelines.registry as pipeline_registry

    product_features = {
        "eightDistinctLevelGoals": True,
        "skinEquippedVisualChange": True,
        "shopOwnershipStates": True,
        "chineseUiPanelsVisible": True,
        "levelFlowPlayable": True,
        "failureReviveFeedback": True,
        "audioPlaybackVerified": True,
        "bgmStarted": True,
        "sfxPlaybackVerified": True,
        "volumeToggleUsable": True,
        "animationFeedbackVerified": True,
        "mobilePortraitUi": True,
        "dragPlacement": True,
        "chineseUi": True,
        "generatedArtAssets": True,
        "cocosAssetBindings": True,
        "dragPlacement": True,
        "chineseUi": True,
        "generatedArtAssets": True,
        "cocosAssetBindings": True,
    }
    semantic_evidence = {
        "board_state": {"rows": 10, "cols": 10},
        "piece_shapes": [{"cells": [[0, 0]]}],
        "candidate_tray": [{}, {}, {}],
        "semantic_traces": {
            "placement": "trace/placement.json",
            "line_clear": "trace/line_clear.json",
            "candidate_refresh": "trace/candidate_refresh.json",
            "game_over": "trace/game_over.json",
            "anti_stall": "trace/anti_stall.json",
        },
    }
    semantic_evidence = {
        "board_state": {"rows": 10, "cols": 10},
        "piece_shapes": [{"cells": [[0, 0]]}],
        "candidate_tray": [{}, {}, {}],
        "semantic_traces": {
            "placement": "trace/placement.json",
            "line_clear": "trace/line_clear.json",
            "candidate_refresh": "trace/candidate_refresh.json",
            "game_over": "trace/game_over.json",
            "anti_stall": "trace/anti_stall.json",
        },
    }
    product_body_evidence = {
        "scene_nodes": ["Canvas", "Board", "CandidateTray"],
        "cocos_component_bindings": ["BoardModel", "RuleEngine", "CandidateTray"],
    }
    payload = pipeline_registry.execute_contribution_validation(
        "commercial_game_production_go_no_go",
        shared_outputs={
            "commercial_game_production": {
                "commercial_playable_go": True,
                "same_project_worker_patch_go": True,
                "ecosystem_integration_go": True,
                "same_project_patch_ledger": {
                    "same_project_worker_patch_go": True,
                    "task_card_count": 1,
                    "completed_count": 1,
                    "entries": [
                        {
                            "task_card_id": "tc_product_depth",
                            "status": "completed",
                            "receipt_id": "receipt_depth",
                            "child_run_id": "run_depth",
                            "child_attempt_id": "attempt_depth",
                            "worker_adapter": "codex",
                            "changed_files": ["state/project/assets/scripts/Game.ts"],
                            "mutation_result": {
                                "changed_files": ["state/project/assets/scripts/Game.ts"],
                                "final_test_status": "passed",
                            },
                            "attempts": [{"attempt_index": 1, "receipt_id": "receipt_depth"}],
                        }
                    ],
                    "blockers": [],
                },
                "cocos_ecosystem_evidence": {"ecosystem_integration_go": True, "blockers": [], "checks": {"assetdb": True}},
                "build": {
                    "creator_exit_code": 0,
                    "fatal_marker_detected": False,
                    "artifact_success": True,
                    "build_output_path": "build/web-mobile",
                },
                "playtest": {
                    "passed": True,
                    "url": "http://127.0.0.1:3000/index.html",
                    "screenshots": ["mobile.png"],
                    "console_errors": [],
                    "page_errors": [],
                    "real_pointer_drag_go": True,
                    "real_pointer_drag": {"go": True, "board_state_changed": True, "score_changed": True},
                    "portrait_orientation_go": True,
                    "portrait_orientation": {
                        "go": True,
                        "viewport": {"width": 390, "height": 844},
                        "screen_orientation": "portrait",
                        "design_resolution": {"width": 1080, "height": 1920},
                    },
                    "feature_coverage": {**product_features, "mobilePortraitUi": True},
                },
                "commercial_feature_coverage": product_features,
                "product_depth_evidence": {
                    "level_goals": [f"goal-{index}" for index in range(8)],
                    "feature_coverage": product_features,
                },
                "gameplay_semantic_evidence": semantic_evidence,
                "product_body_evidence": product_body_evidence,
                "ai_surrogate_playtest_evidence": _passing_ai_surrogate_evidence(),
                "commercial_quality_scorecard": _passing_commercial_quality_scorecard(),
            },
            "commercial_game_assets": {
                "commercial_assets_go": True,
                "asset_manifest_path": "assets/commercial_asset_manifest.json",
                "provider_evidence": [{"provider": "test", "status": "verified_ready"}],
                "asset_manifest": {"go_no_go": "GO", "manifest_path": "assets/commercial_asset_manifest.json"},
                "commercial_asset_blockers": [],
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
    assert gate["output"]["machine_evidence_go"] is True
    assert gate["output"]["commercial_final_gate_evidence"]["commercial_playable_go"] is False


def test_commercial_gate_allows_unattended_machine_ready_when_human_review_is_not_required() -> None:
    import packages.contributions.pipelines.registry as pipeline_registry

    product_features = {
        "eightDistinctLevelGoals": True,
        "skinEquippedVisualChange": True,
        "shopOwnershipStates": True,
        "chineseUiPanelsVisible": True,
        "levelFlowPlayable": True,
        "failureReviveFeedback": True,
        "audioPlaybackVerified": True,
        "bgmStarted": True,
        "sfxPlaybackVerified": True,
        "volumeToggleUsable": True,
        "animationFeedbackVerified": True,
        "mobilePortraitUi": True,
    }
    production = {
        "commercial_playable_go": False,
        "technical_smoke_go": True,
        "production_scaffold_go": True,
        "same_project_patch_ledger": {
            "same_project_worker_patch_go": True,
            "task_card_count": 1,
            "completed_count": 1,
            "entries": [
                {
                    "status": "completed",
                    "worker_adapter": "codex",
                    "receipt_id": "receipt",
                    "child_run_id": "run",
                    "child_attempt_id": "attempt",
                    "changed_files": ["state/project/assets/scripts/Game.ts"],
                    "mutation_result": {
                        "changed_files": ["state/project/assets/scripts/Game.ts"],
                        "final_test_status": "passed",
                    },
                    "attempts": [{"attempt_index": 1, "receipt_id": "receipt"}],
                }
            ],
            "blockers": [],
        },
        "build": {
            "creator_exit_code": 0,
            "fatal_marker_detected": False,
            "artifact_success": True,
            "build_output_path": "build/web-mobile",
        },
        "playtest": {
            "passed": True,
            "url": "http://127.0.0.1:3000/index.html",
            "screenshots": ["mobile.png"],
            "console_errors": [],
            "page_errors": [],
            "real_pointer_drag_go": True,
            "real_pointer_drag": {"go": True, "board_state_changed": True, "score_changed": True},
            "portrait_orientation_go": True,
            "portrait_orientation": {
                "go": True,
                "viewport": {"width": 390, "height": 844},
                "screen_orientation": "portrait",
                "design_resolution": {"width": 1080, "height": 1920},
            },
            "feature_coverage": product_features,
        },
        "commercial_feature_coverage": product_features,
        "product_depth_evidence": {
            "level_goals": [f"goal-{index}" for index in range(8)],
            "feature_coverage": product_features,
        },
        "gameplay_semantic_evidence": {
            "board_state": {"rows": 10, "cols": 10},
            "piece_shapes": [{"cells": [[0, 0]]}],
            "candidate_tray": [{}, {}, {}],
            "semantic_traces": {
                "placement": "trace/placement.json",
                "line_clear": "trace/line_clear.json",
                "candidate_refresh": "trace/candidate_refresh.json",
                "game_over": "trace/game_over.json",
                "anti_stall": "trace/anti_stall.json",
            },
        },
        "product_body_evidence": {
            "scene_nodes": ["Canvas", "Board", "CandidateTray"],
            "cocos_component_bindings": ["BoardModel", "RuleEngine", "CandidateTray"],
        },
        "ai_surrogate_playtest_evidence": _passing_ai_surrogate_evidence(),
        "commercial_quality_scorecard": _passing_commercial_quality_scorecard(),
    }
    payload = pipeline_registry.execute_contribution_validation(
        "commercial_game_production_go_no_go",
        shared_outputs={
            "commercial_game_production": production,
            "commercial_game_assets": {
                "commercial_assets_go": True,
                "asset_manifest": {"go_no_go": "GO", "manifest_path": "assets/manifest.json"},
                "commercial_asset_blockers": [],
            },
        },
        require_commercial=True,
        require_cocos_ecosystem=False,
        require_live_agent_roles=False,
        require_human_player_review=False,
    )

    assert payload["pipeline_status"] == "completed"
    assert payload["stop_reason"] is None
    assert payload["result"]["output"]["go_no_go"] == "GO"
    assert payload["result"]["output"]["required_gate"] == "machine_commercial_readiness_before_human_review"
    assert payload["result"]["output"]["blockers"] == []
    assert payload["result"]["output"]["human_review_skipped_for_unattended_run"] is True
    assert payload["result"]["output"]["commercial_playable_claim_allowed"] is False
    assert payload["result"]["output"]["machine_evidence_go"] is True


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
    assert all(
        stage["status"] == "completed"
        for stage in _completed_pre_capability_agent_roles(payload, "commercial_game_asset_generation")
    )
    asset_stage = _pipeline_stage_by_capability(payload, "commercial_game_asset_generation")
    assert asset_stage["status"] == "completed"
    assert asset_stage["execution_backend"] == "commercial_game_asset_generation_v1"
    assert asset_stage["metadata"]["forbids_fixed_template"] is True
    worker_stage = _pipeline_stage_by_capability(payload, "commercial_game_task_card_worker")
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
    worker_stage = _pipeline_stage_by_capability(payload, "commercial_game_task_card_worker")
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
    supervisor = _pipeline_stage_by_role(payload, "supervisor")["output"]["structured_output"]
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

    asset_stage = _pipeline_stage_by_capability(payload, "commercial_game_asset_generation")
    assert asset_stage["status"] == "completed"
    assert asset_stage["failure_class"] is None
    assert asset_stage["output"]["asset_generation_skipped"] is True
    worker_stage = _pipeline_stage_by_capability(payload, "commercial_game_task_card_worker")
    assert worker_stage["output"]["commercial_playable_blockers"] == ["source_path_missing"]
    supervisor = _pipeline_stage_by_role(payload, "supervisor")["output"]["structured_output"]
    assert supervisor["repair_packets"][0]["owner_role"] == "operator_input"


def test_real_asset_stage_enables_vertex_review_and_provider_fallbacks_for_real_assets(
    tmp_path: Path, monkeypatch
) -> None:
    import packages.contributions.pipelines.commercial_game_production as commercial_pipeline

    captured: dict[str, object] = {}

    def _fake_manifest(**kwargs):
        captured.update(kwargs)
        manifest_path = Path(kwargs["output_dir"]) / "commercial_asset_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema_version": "m77_cocos_commercial_assets_v1",
            "go_no_go": "GO",
            "manifest_path": manifest_path.as_posix(),
            "results": [
                {
                    "asset_name": "background",
                    "provider": "vertex_generation_api",
                    "status": "completed",
                    "artifact_paths": [(manifest_path.parent / "background.png").as_posix()],
                    "metadata": {"provider_fallback_used": True},
                }
            ],
            "feature_coverage": {
                "generated_art_assets": True,
                "generated_audio_assets": True,
                "skin_switching_visual_assets": True,
                "particle_effects": True,
                "commercial_polish_pass": True,
            },
            "blockers": [],
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        return manifest

    monkeypatch.setattr(commercial_pipeline, "generate_cocos_commercial_asset_manifest", _fake_manifest)
    source = tmp_path / "design.md"
    source.write_text("# commercial puzzle design\nvalid source for real assets\n", encoding="utf-8")

    payload = commercial_pipeline.execute_commercial_game_asset_generation(
        root=tmp_path,
        target_dir=tmp_path / "pipeline_evidence",
        shared_outputs={},
        pipeline_id="pipeline_real_asset_vertex_fallback",
        source_path=source,
        require_real_assets=True,
        require_commercial=False,
    )

    assert payload["status"] == "completed"
    assert payload["output"]["commercial_assets_go"] is True
    assert captured["include_vertex_review"] is True
    assert captured["enable_provider_fallbacks"] is True


def test_real_asset_stage_reuses_existing_valid_commercial_assets_before_provider(
    tmp_path: Path, monkeypatch
) -> None:
    import packages.contributions.pipelines.commercial_game_production as commercial_pipeline

    def _should_not_call_provider(*_args, **_kwargs):
        raise AssertionError("valid existing commercial assets should be reused before provider calls")

    monkeypatch.setattr(commercial_pipeline, "generate_cocos_commercial_asset_manifest", _should_not_call_provider)
    source = tmp_path / "design.md"
    source.write_text("# 商业小游戏\n必须使用已有真实资产继续修复。", encoding="utf-8")
    pipeline_id = "commercial_game_reuse_assets"
    asset_root = tmp_path / "pipeline_evidence" / pipeline_id / "assets"
    artifact_path = asset_root / "commercial_asset_factory" / "assets" / "images" / "background.png"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(b"real-image")
    manifest_path = asset_root / "commercial_asset_manifest.json"
    manifest = {
        "go_no_go": "GO",
        "manifest_path": manifest_path.as_posix(),
        "results": [
            {
                "asset_name": "background",
                "provider": "mmx_generation_api",
                "status": "completed",
                "artifact_paths": [artifact_path.as_posix()],
            }
        ],
        "blockers": [],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    stage_path = asset_root / "commercial_game_asset_stage.json"
    stage_path.write_text(
        json.dumps(
            {
                "schema_version": "commercial_game_asset_stage_v1",
                "pipeline_id": pipeline_id,
                "asset_manifest_path": manifest_path.as_posix(),
                "asset_manifest": manifest,
                "provider_evidence": [{"provider": "mmx_generation_api", "status": "completed"}],
                "placeholder_only": False,
                "require_real_assets": True,
                "commercial_assets_go": True,
                "commercial_asset_blockers": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    payload = commercial_pipeline.execute_commercial_game_asset_generation(
        root=tmp_path,
        target_dir=tmp_path / "pipeline_evidence",
        shared_outputs={},
        pipeline_id=pipeline_id,
        source_path=source,
        require_real_assets=True,
        require_commercial=False,
    )

    assert payload["status"] == "completed"
    assert payload["execution_backend"] == "commercial_game_asset_generation_reuse_v1"
    assert payload["output"]["commercial_assets_go"] is True
    assert payload["output"]["reused_existing_asset_stage"] is True
    assert payload["output"]["source_identity"]["source_sha256"]


def test_commercial_asset_stage_blocks_invalid_game_design_spec_before_provider(tmp_path: Path, monkeypatch) -> None:
    import packages.contributions.pipelines.commercial_game_production as commercial_pipeline

    def _should_not_call_provider(*_args, **_kwargs):
        raise AssertionError("asset provider must not run when GameDesignSpec validation fails")

    monkeypatch.setattr(commercial_pipeline, "generate_cocos_local_stable_asset_manifest", _should_not_call_provider)
    source = tmp_path / "empty.md"
    source.write_text("", encoding="utf-8")

    payload = commercial_pipeline.execute_commercial_game_asset_generation(
        root=tmp_path,
        target_dir=tmp_path / "pipeline_evidence",
        shared_outputs={},
        pipeline_id="commercial_game_production",
        source_path=source,
        require_commercial=True,
    )

    assert payload["status"] == "blocked"
    assert payload["failure_class"] == "game_design_spec_no_go"
    assert "source_requirements_missing" in payload["output"]["commercial_asset_blockers"]
    assert payload["output"]["game_design_spec_contract"]["go"] is False


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
            status="active",
            metadata={
                "task_card_generation_source": "active_phase_execution_blueprint",
                "phase_execution_blueprint_schema": "universal_game_phase_execution_blueprint_v1",
                "task_card_compile_report_schema": "universal_game_task_card_compile_report_v1",
                "task_card_compile_go": True,
                "task_card_compile_blockers": [],
                "requirement_coverage_required": True,
                "required_requirement_ids": ["REQ-S001-C001-001"],
                "covered_requirement_ids": ["REQ-S001-C001-001"],
                "missing_requirement_ids": [],
                "human_visible_cli_required": True,
                "execution_visibility_mode": "human_visible_cli_enforced",
            },
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
            status="active",
        )
    )
    source = tmp_path / "brief.md"
    source.write_text("# 商业小游戏\n必须实现八个不同关卡目标。\n必须有中文 UI 和 BGM。", encoding="utf-8")
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
            "child_attempt_id": "attempt_tc_levels",
            "worker_adapter": "codex",
            "evidence_id": "evidence_tc_levels",
            "mutation_result": {
                "changed_files": [Path(kwargs["write_set"][0]).as_posix()],
                "applied_patch_hash": "abc123",
                "final_test_status": "passed",
            },
            "watchdog": {"timeout_type": None, "stream_event_count": 3},
            "timeout_seconds": 900,
            "idle_timeout_seconds": 240,
            "visible_cli_session": _visible_cli_session(tmp_path, "tc_levels"),
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
        return _passing_runtime_evidence(tmp_path, tmp_path / "cocos_project")

    monkeypatch.setattr(commercial_pipeline, "collect_cocos_ecosystem_bridge_evidence", _fake_ecosystem_evidence)
    monkeypatch.setattr(commercial_pipeline, "collect_project_runtime_evidence", _fake_runtime_evidence)

    payload = execute_commercial_game_task_card_worker(
        root=tmp_path,
        target_dir=tmp_path / "pipeline_evidence",
        shared_outputs={
            "commercial_game_assets": _passing_commercial_assets(tmp_path),
            "ai_surrogate_playtest_evidence": _passing_ai_surrogate_evidence(),
        },
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
    assert output["same_project_patch_ledger"]["entries"][0]["task_card_path"].endswith("tc_levels.md")
    assert output["same_project_patch_ledger"]["entries"][0]["continuation_required"] is False
    assert output["same_project_patch_ledger"]["next_incomplete_task_card_id"] is None
    assert output["same_project_patch_ledger"]["next_continuation_command"] is None
    assert output["skipped_non_worker_task_cards"] == ["tc_bridge_contract"]
    assert len(runner_calls) == 1
    assert runner_calls[0]["task_card"].task_card_id == "tc_levels"
    assert evidence_order == ["ecosystem:auto", "runtime", "ecosystem:report_only"]
    assert set(output["evidence_contracts"]) == {
        "asset_graph",
        "cocos_bridge_evidence",
        "same_project_patch_ledger",
        "build_ledger",
        "browser_playtest_ledger",
        "gameplay_semantic_evidence",
        "product_body_evidence",
        "product_depth_evidence",
        "commercial_quality_scorecard",
    }
    assert output["build_ledger_go"] is True
    assert output["browser_playtest_ledger_go"] is True
    assert (tmp_path / "cocos_project" / "workflow_project_source.json").exists()


def test_commercial_worker_auto_repairs_post_worker_cocos_build_blocker(
    tmp_path: Path, monkeypatch
) -> None:
    import packages.contributions.pipelines.commercial_game_production as commercial_pipeline
    from packages.core_domain.repositories import TaskRepository

    execute_commercial_game_task_card_worker = commercial_pipeline.execute_commercial_game_task_card_worker
    pipeline_id = "pipeline_auto_repair_build_gate"
    db_path = _seed_commercial_worker_db(tmp_path, pipeline_id)
    source = tmp_path / "brief.md"
    source.write_text("# 商业小游戏\n必须实现俄罗斯方块消除式商业化体验。", encoding="utf-8")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    project_dir = tmp_path / "cocos_project"
    runner_calls: list[dict[str, object]] = []
    runtime_calls: list[str] = []
    ecosystem_calls: list[str] = []

    def _fake_runner(**kwargs):
        task_card_id = kwargs["task_card"].task_card_id
        runner_calls.append(kwargs)
        if "machine_gate_repair" in task_card_id:
            _write_machine_gate_repair_artifacts(project_dir)
        return {
            "status": "completed",
            "receipt_id": f"receipt_{task_card_id}",
            "child_run_id": f"run_{task_card_id}",
            "child_attempt_id": f"attempt_{task_card_id}",
            "worker_adapter": "codex",
            "evidence_id": f"evidence_{task_card_id}",
            "mutation_result": {
                "changed_files": [Path(kwargs["write_set"][0]).as_posix()],
                "applied_patch_hash": f"hash_{task_card_id}",
                "final_test_status": "passed",
            },
            "watchdog": {"timeout_type": None, "stream_event_count": 3},
            "timeout_seconds": 900,
            "idle_timeout_seconds": 240,
            "visible_cli_session": _visible_cli_session(tmp_path, task_card_id),
            "provider_visible_cli_required": True,
            "provider_visible_cli_session": _provider_visible_cli_session(tmp_path, task_card_id),
            "control_plane_visibility": "resident",
            "provider_visibility": "direct_visible",
        }

    def _fake_ecosystem_evidence(**kwargs):
        ecosystem_calls.append(str(kwargs.get("bridge_mode") or ""))
        return {
            "strict_required": bool(kwargs.get("require_bridge")),
            "ecosystem_integration_go": True,
            "blockers": [],
            "failure_class": None,
            "checks": {"build_api_evidence": True, "assetdb_import_query_evidence": True},
            "bridge_runner_evidence": {"status": "completed", "fresh": True},
        }

    def _fake_runtime_evidence(**_kwargs):
        runtime_calls.append("runtime")
        if len(runtime_calls) == 1:
            return _failing_cocos_build_runtime_evidence(tmp_path, project_dir)
        return _passing_runtime_evidence(tmp_path, project_dir)

    monkeypatch.setattr(commercial_pipeline, "collect_cocos_ecosystem_bridge_evidence", _fake_ecosystem_evidence)
    monkeypatch.setattr(commercial_pipeline, "collect_project_runtime_evidence", _fake_runtime_evidence)

    payload = execute_commercial_game_task_card_worker(
        root=tmp_path,
        target_dir=tmp_path / "pipeline_evidence",
        shared_outputs={
            "commercial_game_assets": _passing_commercial_assets(tmp_path),
            "ai_surrogate_playtest_evidence": _passing_ai_surrogate_evidence(),
        },
        pipeline_id=pipeline_id,
        db_path=db_path,
        source_path=source,
        creator_exe=creator,
        output_dir=project_dir,
        require_build=True,
        require_playtest=True,
        require_commercial=True,
        require_cocos_ecosystem=True,
        cocos_bridge_mode="auto",
        task_card_runner=_fake_runner,
        max_repair_attempts=2,
    )

    output = payload["output"]
    repair_card_id = f"{pipeline_id}_machine_gate_repair_01_cocos_build_product_body"
    assert payload["status"] == "completed"
    assert [call["task_card"].task_card_id for call in runner_calls] == ["tc_core", repair_card_id]
    assert runtime_calls == ["runtime", "runtime"]
    assert ecosystem_calls == ["auto", "report_only", "auto", "report_only"]
    assert output["same_project_patch_ledger"]["task_card_count"] == 2
    assert output["same_project_patch_ledger"]["completed_count"] == 2
    assert output["same_project_patch_ledger"]["entries"][1]["task_card_id"] == repair_card_id
    assert output["machine_gate_repair_loop"]["repair_attempt_count"] == 1
    assert output["machine_gate_repair_loop"]["history"][0]["task_card_ids"] == [repair_card_id]
    assert output["machine_gate_repair_loop"]["history"][0]["remaining_repairable_blockers"] == []
    assert output["post_worker_machine_gate"]["machine_evidence_go"] is True
    assert output["post_worker_machine_gate"]["repairable_machine_blockers"] == []
    assert output["build_ledger_go"] is True
    assert output["browser_playtest_ledger_go"] is True
    assert output["product_body_evidence"]["go"] is True
    assert TaskRepository(db_path).get_task_card(repair_card_id) is not None


def test_post_repair_ecosystem_success_is_not_overridden_by_stale_prebuild_failure() -> None:
    import packages.contributions.pipelines.commercial_game_production as commercial_pipeline

    fresh_report_only_evidence = {
        "strict_required": True,
        "ecosystem_integration_go": True,
        "blockers": [],
        "failure_class": None,
        "operator_action_required": False,
        "operator_actions": [],
        "evidence_path": "project/workflow_runtime_evidence/cocos_ecosystem_bridge_evidence.json",
    }
    stale_prebuild_failure = {
        "strict_required": True,
        "ecosystem_integration_go": False,
        "failure_class": "cocos_ecosystem_bridge_missing",
        "blockers": [
            "assetdb_import_query_evidence",
            "scene_create_save_evidence",
            "node_component_binding_evidence",
            "prefab_create_instantiate_evidence",
        ],
        "operator_action_required": True,
        "operator_actions": [{"kind": "open_cocos_editor"}],
        "evidence_path": "state/pipeline_runs/run/cocos_ecosystem/cocos_ecosystem_bridge_evidence.json",
    }

    commercial_pipeline._merge_prebuild_ecosystem_evidence(fresh_report_only_evidence, stale_prebuild_failure)

    assert fresh_report_only_evidence["ecosystem_integration_go"] is True
    assert fresh_report_only_evidence["blockers"] == []
    assert fresh_report_only_evidence["operator_action_required"] is False
    assert "failure_class" not in fresh_report_only_evidence
    assert fresh_report_only_evidence["prebuild_bridge_evidence"]["failure_class"] == "cocos_ecosystem_bridge_missing"


def test_machine_gate_repair_card_scopes_build_blockers_and_precise_cocos_context(tmp_path: Path) -> None:
    import packages.contributions.pipelines.commercial_game_production as commercial_pipeline

    project_dir = tmp_path / "cocos_project"
    scene = project_dir / "assets" / "scene" / "block_puzzle_player_visible.scene"
    runtime = project_dir / "assets" / "scripts" / "runtime" / "gameplay" / "BlockPuzzleRuntimeController.ts"
    workflow_binding = project_dir / "assets" / "scripts" / "runtime" / "workflow" / "WorkflowBlockPuzzleBoardBinding.ts"
    repair_evidence = project_dir / "workflow_runtime_evidence" / "machine_gate_repair_evidence.json"
    scene.parent.mkdir(parents=True)
    runtime.parent.mkdir(parents=True)
    workflow_binding.parent.mkdir(parents=True)
    repair_evidence.parent.mkdir(parents=True)
    scene.write_text('{"__type__":"WorkflowBlockPuzzleSceneRuntime"}', encoding="utf-8")
    runtime.write_text("export class BlockPuzzleRuntimeController {}", encoding="utf-8")
    workflow_binding.write_text("@ccclass('WorkflowBlockPuzzleBoardBinding') export class WorkflowBlockPuzzleBoardBinding {}", encoding="utf-8")
    repair_evidence.write_text("{}", encoding="utf-8")
    requirement_matrix = tmp_path / "requirement_matrix.json"
    requirement_matrix.write_text("{}", encoding="utf-8")

    cards = commercial_pipeline._build_machine_gate_repair_cards(
        pipeline_id="pipeline_scoped_machine_gate",
        project_dir=project_dir,
        run_root=tmp_path / "pipeline_evidence",
        repair_round=1,
        post_worker_gate={
            "repairable_machine_blockers": [
                "cocos_build_fatal_marker_detected",
                "browser_playtest_missing",
                "product_feature_depth_missing",
                "ai_surrogate_playtest_missing",
            ]
        },
        runtime_evidence={},
        ecosystem_evidence={},
        game_design_contract={"requirement_matrix_path": requirement_matrix.as_posix()},
    )

    assert len(cards) == 1
    card = cards[0]
    assert card.task_card_id == "pipeline_scoped_machine_gate_machine_gate_repair_01_cocos_build_product_body"
    assert card.metadata["machine_gate_blockers"] == ["cocos_build_fatal_marker_detected"]
    assert card.metadata["deferred_machine_gate_blockers"] == [
        "browser_playtest_missing",
        "product_feature_depth_missing",
        "ai_surrogate_playtest_missing",
    ]
    assert scene.as_posix() in card.read_set
    assert runtime.as_posix() in card.read_set
    assert workflow_binding.as_posix() in card.read_set
    assert (project_dir / "assets" / "scripts" / "runtime" / "workflow" / "WorkflowCandidatePrefabBinding.ts").as_posix() in card.read_set
    assert "assets/workflow_bridge_probe/**" in card.write_set
    assert "assets/scripts/runtime/workflow/WorkflowBlockPuzzleSceneRuntime.ts" in card.expected_artifacts
    assert "assets/scripts/runtime/workflow/WorkflowCandidateTrayBinding.ts" in card.expected_artifacts
    assert "assets/scripts/runtime/workflow/WorkflowCandidatePrefabBinding.ts" in card.expected_artifacts
    assert "assets/prefabs/workflow_block_puzzle_board_binding.prefab" in card.expected_artifacts
    assert repair_evidence.as_posix() in card.read_set
    assert requirement_matrix.as_posix() not in card.read_set
    assert any("existing-file patch" in item for item in card.model_guidance)
    assert any("Every Workflow* class" in item for item in card.model_guidance)
    assert any("exactly one valid JSON document" in item for item in card.model_guidance)
    assert any("intentionally narrowed" in item for item in card.model_guidance)


def test_machine_gate_repair_card_persistence_replaces_stale_db_card(tmp_path: Path) -> None:
    import packages.contributions.pipelines.commercial_game_production as commercial_pipeline
    from packages.contracts import TaskCard
    from packages.core_domain.repositories import TaskRepository

    db_path = _seed_commercial_worker_db(tmp_path, "pipeline_stale_card")
    repo = TaskRepository(db_path)
    stale = TaskCard(
        run_id="pipeline_stale_card",
        task_card_id="pipeline_stale_card_machine_gate_repair_01_cocos_build_product_body",
        title="Old repair",
        description="Old broad repair card.",
        goal="Old broad repair card.",
        write_set=["assets/**"],
        read_set=["GameDesignSpec", "old_requirement_matrix.json"],
        test_commands=["old-test"],
        acceptance_criteria=["old"],
        evidence_requirements=["old"],
        blocking_conditions=["old"],
        model_guidance=["old"],
        risk_level="high",
        execution_mode="same_project_patch",
        status="active",
        metadata={"machine_gate_repair_card": True},
    )
    fresh = stale.model_copy(
        update={
            "title": "Fresh repair",
            "read_set": ["cocos_build_stderr.log", "assets/scene/block_puzzle_player_visible.scene"],
            "model_guidance": ["fresh narrowed card"],
        }
    )
    repo.create_task_card(stale)

    report = commercial_pipeline._persist_machine_gate_repair_cards(db_path=db_path, cards=[fresh])
    stored = repo.get_task_card(fresh.task_card_id)

    assert report["write_mode"] == "upsert_current_repair_card"
    assert report["updated_task_card_ids"] == [fresh.task_card_id]
    assert stored is not None
    assert stored.title == "Fresh repair"
    assert stored.read_set == ["cocos_build_stderr.log", "assets/scene/block_puzzle_player_visible.scene"]


def test_task_card_retry_context_includes_patch_apply_failure_feedback(tmp_path: Path) -> None:
    from packages.contributions.pipelines.commercial_game_task_worker import _task_card_path_with_retry_context

    card_path = tmp_path / "repair_card.md"
    card_path.write_text("# Repair Card\n", encoding="utf-8")

    retry_path = _task_card_path_with_retry_context(
        card_path,
        attempt_index=2,
        prior_entry={
            "status": "failed",
            "failure_class": "same_project_patch_apply_failed",
            "final_failure_class": "same_project_patch_apply_failed",
            "mutation_result": {
                "final_test_status": "patch_apply_failed",
                "failure_reason": "new-file patch target already exists `assets/scripts/runtime/workflow/WorkflowBlockPuzzleBoardBinding.ts`",
            },
            "recoverable_suggestion": "rerun_with_existing_file_diff",
        },
    )

    assert retry_path != card_path
    retry_text = retry_path.read_text(encoding="utf-8")
    assert "Previous Runtime Repair Failure" in retry_text
    assert "same_project_patch_apply_failed" in retry_text
    assert "new-file patch target already exists" in retry_text


def test_commercial_worker_blocks_reusing_project_with_different_source(tmp_path: Path) -> None:
    import packages.contributions.pipelines.commercial_game_production as commercial_pipeline

    pipeline_id = "pipeline_source_mismatch_guard"
    db_path = _seed_commercial_worker_db(tmp_path, pipeline_id)
    source = tmp_path / "brief_current.md"
    source.write_text("# current commercial game\nImplement a game from this source only.", encoding="utf-8")
    old_source = tmp_path / "brief_old.md"
    old_source.write_text("# old game\nDo not reuse this game project for the current source.", encoding="utf-8")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    project_dir = tmp_path / "cocos_project"
    project_dir.mkdir()
    (project_dir / "workflow_project_source.json").write_text(
        json.dumps(
            {
                "schema_version": "commercial_game_same_project_bootstrap_v1",
                "source_path": old_source.resolve().as_posix(),
                "source_sha256": "old-source-hash",
            }
        ),
        encoding="utf-8",
    )

    def _unexpected_runner(**_kwargs):
        raise AssertionError("source mismatch must block before task-card execution")

    payload = commercial_pipeline.execute_commercial_game_task_card_worker(
        root=tmp_path,
        target_dir=tmp_path / "pipeline_evidence",
        shared_outputs={},
        pipeline_id=pipeline_id,
        db_path=db_path,
        source_path=source,
        creator_exe=creator,
        output_dir=project_dir,
        require_build=False,
        require_playtest=False,
        require_commercial=False,
        task_card_runner=_unexpected_runner,
    )

    output = payload["output"]
    assert output["same_project_worker_patch_go"] is False
    assert "same_project_source_mismatch" in output["commercial_playable_blockers"]
    assert output["same_project_reuse_guard"]["reuse_mode"] == "blocked_source_mismatch"
    assert output["same_project_patch_ledger"]["entries"] == []


def test_commercial_worker_blocks_unmanaged_nonempty_project_dir(tmp_path: Path) -> None:
    import packages.contributions.pipelines.commercial_game_production as commercial_pipeline

    pipeline_id = "pipeline_unmanaged_project_guard"
    db_path = _seed_commercial_worker_db(tmp_path, pipeline_id)
    source = tmp_path / "brief.md"
    source.write_text("# current commercial game\nImplement a game from this source only.", encoding="utf-8")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    project_dir = tmp_path / "cocos_project"
    (project_dir / "assets/scripts").mkdir(parents=True)
    (project_dir / "assets/scripts/LegacyGame.ts").write_text("// unmanaged stale project", encoding="utf-8")

    def _unexpected_runner(**_kwargs):
        raise AssertionError("unmanaged project reuse must block before task-card execution")

    payload = commercial_pipeline.execute_commercial_game_task_card_worker(
        root=tmp_path,
        target_dir=tmp_path / "pipeline_evidence",
        shared_outputs={},
        pipeline_id=pipeline_id,
        db_path=db_path,
        source_path=source,
        creator_exe=creator,
        output_dir=project_dir,
        require_build=False,
        require_playtest=False,
        require_commercial=False,
        task_card_runner=_unexpected_runner,
    )

    output = payload["output"]
    assert output["same_project_worker_patch_go"] is False
    assert "same_project_unmanaged_project_dir" in output["commercial_playable_blockers"]
    assert output["same_project_reuse_guard"]["reuse_mode"] == "blocked_unmanaged_existing_project"
    assert output["same_project_patch_ledger"]["entries"] == []


def test_commercial_worker_blocks_business_cards_not_from_active_phase_blueprint(tmp_path: Path) -> None:
    from packages.contracts import Run, TaskCard
    from packages.contributions.pipelines.commercial_game_production import execute_commercial_game_task_card_worker
    from packages.core_domain.db import migrate
    from packages.core_domain.repositories import RunRepository, TaskRepository

    db_path = tmp_path / "workflow.db"
    pipeline_id = "pipeline_non_blueprint_card"
    migrate(db_path)
    RunRepository(db_path).create(Run(run_id=pipeline_id, goal="commercial worker", preset_id="commercial_game_production"))
    TaskRepository(db_path).create_task_card(
        TaskCard(
            run_id=pipeline_id,
            task_card_id="tc_manual_gameplay",
            title="Manual gameplay implementation",
            description="Manual same-project implementation card must not satisfy the commercial blueprint compiler contract.",
            goal="Manual same-project implementation card must be blocked unless it came from the active phase blueprint compiler.",
            write_set=["state/pipeline_runs/<run>/cocos_project/assets/scripts"],
            read_set=["brief.md"],
            test_commands=["python -m pytest tests/test_task_card_store.py -q"],
            acceptance_criteria=["blueprint gate blocks", "runner not called"],
            evidence_requirements=["blueprint_compile_contract"],
            blocking_conditions=["manual_card_executed"],
            model_guidance=["Do not execute cards that bypass the active phase blueprint compiler."],
            execution_mode="same_project_patch",
            risk_level="high",
            status="active",
        )
    )
    source = tmp_path / "brief.md"
    source.write_text("# 商业小游戏\n必须有中文 UI。\n必须有 BGM。", encoding="utf-8")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")

    def _unexpected_runner(**_kwargs):
        raise AssertionError("non-blueprint business card must block before runner execution")

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
        task_card_runner=_unexpected_runner,
    )

    output = payload["output"]
    assert output["same_project_worker_patch_go"] is False
    assert output["game_design_spec_contract"]["go"] is True
    assert any("task_card_not_from_active_phase_blueprint" in item for item in output["commercial_playable_blockers"])
    assert output["task_card_compile_contract"]["go"] is False
    assert output["same_project_patch_ledger"]["entries"] == []


def test_commercial_worker_short_circuits_downstream_after_same_project_patch_failure(
    tmp_path: Path, monkeypatch
) -> None:
    from packages.contracts import Run, TaskCard
    import packages.contributions.pipelines.commercial_game_production as commercial_pipeline
    from packages.core_domain.db import migrate
    from packages.core_domain.repositories import RunRepository, TaskRepository

    db_path = tmp_path / "workflow.db"
    pipeline_id = "pipeline_same_project_worker_failed"
    migrate(db_path)
    RunRepository(db_path).create(Run(run_id=pipeline_id, goal="commercial worker", preset_id="commercial_game_production"))
    TaskRepository(db_path).create_task_card(
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
            blocking_conditions=["workflow_child_stalled"],
                model_guidance=["Patch the same project only."],
                execution_mode="same_project_patch",
                risk_level="high",
                status="active",
                metadata={
                    "task_card_generation_source": "active_phase_execution_blueprint",
                    "phase_execution_blueprint_schema": "universal_game_phase_execution_blueprint_v1",
                    "task_card_compile_report_schema": "universal_game_task_card_compile_report_v1",
                    "task_card_compile_go": True,
                    "task_card_compile_blockers": [],
                    "requirement_coverage_required": True,
                    "required_requirement_ids": ["REQ-S001-C001-001"],
                    "covered_requirement_ids": ["REQ-S001-C001-001"],
                    "missing_requirement_ids": [],
                    "human_visible_cli_required": True,
                    "execution_visibility_mode": "human_visible_cli_enforced",
                },
            )
    )
    source = tmp_path / "brief.md"
    source.write_text(
        "# commercial game\nThe game must implement eight distinct level goals.\nThe game must have Chinese UI and audio.",
        encoding="utf-8",
    )
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")

    def _failed_runner(**kwargs):
        return {
            "status": "failed",
            "failure_class": "workflow_child_stalled",
            "receipt_id": "receipt_tc_levels",
            "child_run_id": "run_tc_levels",
            "child_attempt_id": "attempt_tc_levels",
            "worker_adapter": "codex",
            "watchdog_source": "db_runtime_state",
            "watchdog": {"timeout_type": "idle_timeout", "stream_event_count": 0},
            "timeout_seconds": 900,
            "idle_timeout_seconds": 240,
            "recoverable_suggestion": "resume_from_next_incomplete_task_card_after_closed_child_run",
            "command": [
                "python",
                "-m",
                "apps.operator_cli.main",
                "run",
                "from-task-card",
                Path(kwargs["task_card_path"]).as_posix(),
                "--execute",
            ],
        }

    def _fake_ecosystem_evidence(**_kwargs):
        return {
            "strict_required": False,
            "ecosystem_integration_go": True,
            "blockers": [],
            "failure_class": None,
            "checks": {"build_api_evidence": True},
        }

    def _runtime_should_not_run(**_kwargs):
        raise AssertionError("downstream runtime evidence must short-circuit after upstream patch failure")

    monkeypatch.setattr(commercial_pipeline, "collect_cocos_ecosystem_bridge_evidence", _fake_ecosystem_evidence)
    monkeypatch.setattr(commercial_pipeline, "collect_project_runtime_evidence", _runtime_should_not_run)

    payload = commercial_pipeline.execute_commercial_game_task_card_worker(
        root=tmp_path,
        target_dir=tmp_path / "pipeline_evidence",
        shared_outputs={},
        pipeline_id=pipeline_id,
        db_path=db_path,
        source_path=source,
        creator_exe=creator,
        output_dir=tmp_path / "cocos_project",
        require_build=True,
        require_playtest=True,
        require_commercial=True,
        require_cocos_ecosystem=False,
        task_card_runner=_failed_runner,
    )

    output = payload["output"]
    blockers = output["commercial_playable_blockers"]
    assert output["same_project_worker_patch_go"] is False
    assert output["build_ledger"]["status"] == "blocked"
    assert output["browser_playtest_ledger"]["status"] == "blocked"
    assert output["product_depth_evidence"]["status"] == "blocked"
    assert output["build_ledger"]["blockers"] == ["blocked_by_same_project_worker"]
    assert output["product_depth_evidence"]["blockers"] == ["blocked_by_same_project_worker"]
    assert output["blocked_downstream_stages"] == [
        "cocos_build",
        "browser_playtest",
        "audio_runtime",
        "gameplay_semantic",
        "product_body",
        "product_depth",
        "human_player_review",
    ]
    assert output["normalized_repair_packet"]["root_cause"] == "same_project_worker_patch_failed"
    assert output["normalized_repair_packet"]["blocked_downstream_stages"] == output["blocked_downstream_stages"]
    assert "workflow_child_stalled" in output["same_project_patch_ledger"]["blockers"]
    assert "blocked_by_same_project_worker" in blockers
    assert "levels_not_distinct_or_less_than_eight" not in blockers
    assert "audio_runtime_not_verified" not in blockers


def test_collect_project_runtime_evidence_writes_build_and_browser_ledgers(tmp_path: Path, monkeypatch) -> None:
    import packages.contributions.pipelines.commercial_game_task_worker as worker_module

    project_dir = tmp_path / "cocos_project"
    build_output = project_dir / "build" / "web-mobile"
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    feature_coverage = {
        "mobilePortraitUi": True,
        "dragPlacement": True,
        "chineseUi": True,
        "generatedArtAssets": True,
        "cocosAssetBindings": True,
        "animationFeedbackVerified": True,
        "audioPlaybackVerified": True,
        "bgmStarted": True,
        "sfxPlaybackVerified": True,
        "volumeToggleUsable": True,
        "shopOwnershipStates": True,
        "skinEquippedVisualChange": True,
        "chineseUiPanelsVisible": True,
        "levelFlowPlayable": True,
        "failureReviveFeedback": True,
    }
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "workflow_commercial_feature_evidence.json").write_text(
        json.dumps(
            {
                "commercial_feature_coverage": feature_coverage,
                "player_visible_checks": feature_coverage,
                "product_depth_evidence": {
                    "level_goals": [f"goal-{index}" for index in range(8)],
                    "feature_coverage": feature_coverage,
                    "player_visible_checks": feature_coverage,
                },
            }
        ),
        encoding="utf-8",
    )

    def _fake_build(**_kwargs):
        return {
            "creator_exit_code": 0,
            "fatal_marker_detected": False,
            "artifact_success": True,
            "build_output_path": build_output.as_posix(),
        }

    def _fake_playtest(**_kwargs):
        return {
            "passed": True,
            "url": "http://127.0.0.1:3000/index.html",
            "screenshots": ["mobile.png", "desktop.png"],
            "console_errors": [],
            "page_errors": [],
            "real_pointer_drag_go": True,
            "real_pointer_drag": {"go": True, "board_state_changed": True, "score_changed": True},
            "portrait_orientation_go": True,
            "portrait_orientation": {
                "go": True,
                "viewport": {"width": 390, "height": 844},
                "screen_orientation": "portrait",
                "design_resolution": {"width": 1080, "height": 1920},
            },
            "feature_coverage": feature_coverage,
            "result_path": (project_dir / "playtest_evidence" / "cocos_playtest_result.json").as_posix(),
        }

    monkeypatch.setattr(worker_module, "build_cocos_project", _fake_build)
    monkeypatch.setattr(worker_module, "playtest_cocos_build", _fake_playtest)

    payload = worker_module.collect_project_runtime_evidence(
        project_dir=project_dir,
        creator_exe=creator,
        require_build=True,
        require_playtest=True,
    )

    assert payload["commercial_playable_blockers"] == []
    assert payload["build_ledger"]["go"] is True
    assert payload["browser_playtest_ledger"]["go"] is True
    assert payload["build_ledger"]["source"]["build_command"]
    assert payload["browser_playtest_ledger"]["source"]["audio_runtime_proof"]["sfxPlaybackVerified"] is True
    assert Path(payload["build_ledger_path"]).exists()
    assert Path(payload["browser_playtest_ledger_path"]).exists()


def test_collect_project_runtime_evidence_records_browser_playtest_exception(tmp_path: Path, monkeypatch) -> None:
    import packages.contributions.pipelines.commercial_game_task_worker as worker_module

    project_dir = tmp_path / "cocos_project"
    build_output = project_dir / "build" / "web-mobile"
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")

    def _fake_build(**_kwargs):
        return {
            "creator_exit_code": 36,
            "fatal_marker_detected": False,
            "artifact_success": True,
            "build_output_path": build_output.as_posix(),
        }

    def _failing_playtest(**_kwargs):
        raise TimeoutError("canvas selector timed out")

    monkeypatch.setattr(worker_module, "build_cocos_project", _fake_build)
    monkeypatch.setattr(worker_module, "playtest_cocos_build", _failing_playtest)

    payload = worker_module.collect_project_runtime_evidence(
        project_dir=project_dir,
        creator_exe=creator,
        require_build=True,
        require_playtest=True,
    )

    assert payload["build_ledger"]["go"] is True
    assert payload["browser_playtest_ledger"]["go"] is False
    assert "browser_playtest_TimeoutError" in payload["browser_playtest_ledger"]["blockers"]
    assert "browser_playtest_execution_failed" in payload["browser_playtest_ledger"]["blockers"]
    assert Path(payload["browser_playtest_ledger_path"]).exists()
    assert Path(project_dir / "playtest_evidence" / "cocos_playtest_exception.json").exists()


def test_production_worker_generates_human_review_packet_without_human_go(tmp_path: Path) -> None:
    from packages.contributions.pipelines.commercial_game_task_worker import production_payload_from_worker

    def _dedupe(values):
        result = []
        seen = set()
        for value in values:
            text = str(value)
            if text not in seen:
                seen.add(text)
                result.append(text)
        return result

    product_features = {
        "shopOwnershipStates": True,
        "skinEquippedVisualChange": True,
        "chineseUiPanelsVisible": True,
        "levelFlowPlayable": True,
        "failureReviveFeedback": True,
        "audioPlaybackVerified": True,
        "bgmStarted": True,
        "sfxPlaybackVerified": True,
        "volumeToggleUsable": True,
        "animationFeedbackVerified": True,
        "mobilePortraitUi": True,
        "dragPlacement": True,
        "chineseUi": True,
        "generatedArtAssets": True,
        "cocosAssetBindings": True,
    }
    semantic_evidence = {
        "board_state": {"rows": 10, "cols": 10},
        "piece_shapes": [{"cells": [[0, 0]]}],
        "candidate_tray": [{}, {}, {}],
        "semantic_traces": {
            "placement": "trace/placement.json",
            "line_clear": "trace/line_clear.json",
            "candidate_refresh": "trace/candidate_refresh.json",
            "game_over": "trace/game_over.json",
            "anti_stall": "trace/anti_stall.json",
        },
    }
    payload = production_payload_from_worker(
        schema_version="test_worker_schema",
        created_at="2026-04-29T00:00:00Z",
        pipeline_id="pipeline_human_review_packet_test",
        project_dir=tmp_path / "cocos_project",
        task_card_quality={
            "schema_version": "m108_task_card_quality_v2",
            "task_card_count": 1,
            "execution_eligible_count": 1,
            "lifecycle_blocked_count": 0,
            "requirement_coverage_blocked_count": 0,
            "go_no_go": "GO",
        },
        runtime_evidence={
            "technical_smoke_go": True,
            "production_scaffold_go": False,
            "commercial_playable_go": True,
            "commercial_playable_blockers": [],
            "commercial_feature_coverage": product_features,
            "player_visible_checks": {},
            "manual_player_evidence": {},
            "product_depth_evidence": {
                "level_goals": [f"goal-{index}" for index in range(8)],
                "feature_coverage": product_features,
            },
            "gameplay_semantic_evidence": semantic_evidence,
            "product_body_evidence": {
                "scene_nodes": ["Canvas", "Board", "CandidateTray"],
                "cocos_component_bindings": ["BoardModel", "RuleEngine", "CandidateTray"],
            },
            "build": {
                "creator_exit_code": 0,
                "fatal_marker_detected": False,
                "artifact_success": True,
                "build_output_path": "build/web-mobile",
            },
            "playtest": {
                "passed": True,
                "url": "http://127.0.0.1:3000/index.html",
                "screenshots": ["mobile.png"],
                "console_errors": [],
                "page_errors": [],
                "real_pointer_drag_go": True,
                "real_pointer_drag": {"go": True, "board_state_changed": True, "score_changed": True},
                "portrait_orientation_go": True,
                "portrait_orientation": {
                    "go": True,
                    "viewport": {"width": 390, "height": 844},
                    "screen_orientation": "portrait",
                    "design_resolution": {"width": 1080, "height": 1920},
                },
                "feature_coverage": {"mobilePortraitUi": True, **product_features},
            },
            "commercial_quality_scorecard": _passing_commercial_quality_scorecard(),
        },
        assets_stage={
            "commercial_assets_go": True,
            "asset_manifest_path": "assets/commercial_asset_manifest.json",
            "asset_manifest": {"go_no_go": "GO", "manifest_path": "assets/commercial_asset_manifest.json"},
            "commercial_asset_blockers": [],
        },
        ecosystem_evidence={"ecosystem_integration_go": True, "blockers": [], "checks": {"assetdb": True}},
        patch_ledger={
            "same_project_worker_patch_go": True,
            "task_card_count": 1,
            "completed_count": 1,
            "entries": [
                {
                    "task_card_id": "tc_product_depth",
                    "status": "completed",
                    "receipt_id": "receipt_depth",
                    "child_run_id": "run_depth",
                    "child_attempt_id": "attempt_depth",
                    "worker_adapter": "codex",
                    "changed_files": ["state/project/assets/scripts/Game.ts"],
                    "mutation_result": {
                        "changed_files": ["state/project/assets/scripts/Game.ts"],
                        "final_test_status": "passed",
                    },
                    "attempts": [{"attempt_index": 1, "receipt_id": "receipt_depth"}],
                }
            ],
            "blockers": [],
        },
        skipped_task_cards=[],
        max_repair_attempts=3,
        dedupe_strings=_dedupe,
        blocker_details=lambda blockers: [{"blocker": item} for item in blockers],
        recoverable_suggestions=lambda blockers: [],
    )

    assert payload["machine_evidence_go"] is True
    assert payload["product_depth_evidence"]["go"] is True
    assert payload["human_review_packet"]["status"] == "AWAITING_HUMAN_REVIEW"
    assert payload["human_review_packet"]["human_player_review_go"] is False
    assert payload["human_player_review_go"] is False
    assert payload["commercial_playable_go"] is False
    assert payload["commercial_game_development_readiness"]["commercial_game_development_readiness_go"] is True


def test_same_project_asset_repair_overrides_placeholder_asset_stage(tmp_path: Path) -> None:
    from packages.contributions.pipelines.commercial_game_evidence_contracts import build_asset_graph_contract
    from packages.contributions.pipelines.commercial_game_task_worker import (
        _effective_assets_stage_from_same_project_repair,
    )

    project_dir = tmp_path / "cocos_project"
    manifest_path = (
        project_dir
        / "assets"
        / "resources"
        / "commercial_assets"
        / "art"
        / "player_visible_asset_manifest.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "commercial_player_visible_asset_manifest_v1",
                "placeholder_assets_only": False,
                "non_placeholder_player_visible_asset_count": 18,
                "real_player_visible_files": [{"path": "assets/resources/commercial_assets/art/generated_jelly_atlas.json"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    effective = _effective_assets_stage_from_same_project_repair(
        project_dir=project_dir,
        assets_stage={
            "commercial_assets_go": False,
            "placeholder_only": True,
            "commercial_asset_blockers": ["placeholder_assets_only"],
            "provider_evidence": [],
        },
    )

    assert effective["commercial_assets_go"] is True
    assert effective["placeholder_only"] is False
    assert effective["commercial_asset_blockers"] == []
    assert effective["same_project_asset_repair_applied"] is True
    contract = build_asset_graph_contract(effective)
    assert contract["go"] is True
    assert contract["blockers"] == []


def test_same_project_patch_ledger_records_continuation_for_idle_timeout(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import execute_same_project_task_cards

    card = TaskCard(
        run_id="pipeline_idle_timeout",
        task_card_id="tc_audio",
        title="Repair audio runtime",
        description="Repair browser-supported audio runtime in the same Cocos project.",
        goal="Repair browser-supported audio runtime in the same Cocos project.",
        write_set=["state/pipeline_runs/<run>/cocos_project/assets/scripts"],
        read_set=["commercial_asset_bindings.json"],
        test_commands=["python -m pytest tests/test_cocos_e2e.py -q"],
        acceptance_criteria=["audio works", "same project patched"],
        evidence_requirements=["audio_runtime_evidence", "same_project_patch"],
        blocking_conditions=["provider_idle_timeout"],
        model_guidance=["Resume this exact card; do not create a new project."],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    receipts: list[str] = []

    def _timeout_runner(**kwargs):
        task_card_path = Path(kwargs["task_card_path"])
        receipt_id = f"receipt_audio_{len(receipts) + 1}"
        receipts.append(receipt_id)
        return {
            "status": "failed",
            "failure_class": "provider_idle_timeout",
            "receipt_id": receipt_id,
            "watchdog": {"timeout_type": "idle_timeout", "stream_event_count": 0},
            "timeout_seconds": 900,
            "idle_timeout_seconds": 240,
            "recoverable_suggestion": "retry_with_higher_idle_timeout_or_split_task",
            "command": ["python", "-m", "apps.operator_cli.main", "run", "from-task-card", task_card_path.as_posix(), "--execute"],
        }

    ledger = execute_same_project_task_cards(
        root=tmp_path,
        run_root=tmp_path / "pipeline_evidence",
        project_dir=tmp_path / "cocos_project",
        pipeline_id="pipeline_idle_timeout",
        db_path=tmp_path / "workflow.db",
        task_cards=[card],
        max_repair_attempts=2,
        task_card_runner=_timeout_runner,
    )

    entry = ledger["entries"][0]
    assert ledger["same_project_worker_patch_go"] is False
    assert "same_project_task_card_patch_failed" in ledger["blockers"]
    assert "blocked_after_three_attempts" in ledger["blockers"]
    assert "provider_timeout_recoverable" in ledger["blockers"]
    assert ledger["next_incomplete_task_card_id"] == "tc_audio"
    assert ledger["next_continuation_command"] == entry["continuation_command"]
    assert len(receipts) == 3
    assert receipts == ["receipt_audio_1", "receipt_audio_2", "receipt_audio_3"]
    assert entry["status"] == "blocked"
    assert entry["failure_class"] == "blocked_after_three_attempts"
    assert entry["final_failure_class"] == "provider_timeout"
    assert entry["retry_exhausted"] is True
    assert len(entry["attempts"]) == 3
    assert entry["continuation_required"] is True
    assert entry["continuation_reason"] == "blocked_after_three_attempts"
    assert "commercial_game_task_card_resume" in entry["continuation_command"]
    assert "--execution-visibility-mode" in entry["continuation_command"]
    assert "human_visible_cli_enforced" in entry["continuation_command"]
    assert entry["execution_visibility_mode"] == "human_visible_cli_enforced"
    assert "--operator-receipt-id" not in entry["continuation_command"]
    assert entry["task_card_path"].endswith("tc_audio.md")


def test_same_project_patch_ledger_recovers_exhausted_provider_when_artifacts_and_tests_pass(
    monkeypatch, tmp_path: Path
) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines import commercial_game_task_worker as worker
    from packages.contributions.pipelines.commercial_game_task_worker import execute_same_project_task_cards

    monkeypatch.setattr(
        worker,
        "run_safe_commands",
        lambda commands, working_directory: [
            {
                "command": str(command.command),
                "argv": ["python", "-c", "print('ok')"],
                "return_code": 0,
                "passed": True,
                "status": "passed",
            }
            for command in commands
        ],
    )
    project_dir = tmp_path / "cocos_project"
    evidence_dir = project_dir / "workflow_runtime_evidence"
    audio_dir = project_dir / "assets" / "scripts" / "runtime" / "audio"
    evidence_dir.mkdir(parents=True)
    audio_dir.mkdir(parents=True)
    audio_evidence = evidence_dir / "audio_feedback_polish_evidence.json"
    feature_evidence = project_dir / "workflow_commercial_feature_evidence.json"
    audio_runtime = audio_dir / "CommercialAudioRuntime.ts"
    audio_evidence.write_text(
        json.dumps(
            {
                "schema_version": "commercial_audio_feedback_polish_v1",
                "go": True,
                "audioPlaybackVerified": True,
                "bgmStarted": True,
                "sfxPlaybackVerified": True,
                "volumeToggleUsable": True,
            }
        ),
        encoding="utf-8",
    )
    feature_evidence.write_text(
        json.dumps({"go": True, "feature_coverage": {"audioPlaybackVerified": True, "sfxPlaybackVerified": True}}),
        encoding="utf-8",
    )
    audio_runtime.write_text("export class CommercialAudioRuntime {}\n", encoding="utf-8")
    card = TaskCard(
        run_id="pipeline_recover_exhausted",
        task_card_id="tc_audio_recovery",
        title="Repair audio runtime",
        description="Repair audio runtime evidence in the same project.",
        goal="Repair audio runtime evidence in the same project.",
        write_set=[
            "workflow_runtime_evidence/audio_feedback_polish_evidence.json",
            "workflow_commercial_feature_evidence.json",
            "assets/scripts/runtime/audio/CommercialAudioRuntime.ts",
        ],
        read_set=["workflow_runtime_evidence/audio_feedback_polish_evidence.json"],
        test_commands=["python -c \"print('ok')\""],
        acceptance_criteria=["audio evidence exists", "tests pass"],
        evidence_requirements=["same_project_patch", "human_visible_cli_session"],
        expected_artifacts=[
            "workflow_runtime_evidence/audio_feedback_polish_evidence.json",
            "workflow_commercial_feature_evidence.json",
            "assets/scripts/runtime/audio/CommercialAudioRuntime.ts",
        ],
        blocking_conditions=["provider_timeout", "same_project_patch_parse_failed"],
        model_guidance=["Finalize existing valid evidence when provider output parsing fails after retries."],
        provider_lane="codex_cli",
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
        metadata={"execution_visibility_mode": "human_visible_cli_enforced"},
    )
    attempts: list[int] = []

    def _parse_failed_runner(**kwargs):
        attempts.append(len(attempts) + 1)
        index = len(attempts)
        return {
            "status": "failed",
            "failure_class": "same_project_patch_parse_failed",
            "receipt_id": f"receipt_audio_recovery_{index}",
            "child_run_id": f"child_audio_recovery_{index}",
            "child_attempt_id": f"attempt_audio_recovery_{index}",
            "worker_adapter": kwargs.get("adapter_name") or "codex",
            "execution_visibility_mode": "human_visible_cli_enforced",
            "visible_cli_session": _visible_cli_session(tmp_path, "tc_audio_recovery"),
            "mutation_result": {"changed_files": [], "final_test_status": "failed"},
            "stderr_preview": "provider returned prose instead of a parseable patch",
        }

    ledger = execute_same_project_task_cards(
        root=tmp_path,
        run_root=tmp_path / "pipeline_evidence",
        project_dir=project_dir,
        pipeline_id="pipeline_recover_exhausted",
        db_path=tmp_path / "workflow.db",
        task_cards=[card],
        max_repair_attempts=2,
        task_card_runner=_parse_failed_runner,
    )

    entry = ledger["entries"][0]
    assert ledger["same_project_worker_patch_go"] is True
    assert "blocked_after_three_attempts" not in ledger["blockers"]
    assert attempts == [1, 2, 3]
    assert entry["status"] == "completed"
    assert entry["failure_class"] is None
    assert entry["final_failure_class"] is None
    assert entry["retry_exhausted"] is False
    assert entry["deterministic_exhausted_provider_recovery"]["go"] is True
    assert entry["mutation_result"]["satisfaction_mode"] == (
        "deterministic_existing_project_artifact_validation_after_provider_exhaustion"
    )
    assert Path(entry["deterministic_exhausted_provider_recovery"]["artifact_validation"]["checked_artifacts"][0]).exists()
    assert entry["mutation_result"]["final_test_status"] == "passed"


def test_same_project_patch_ledger_recovers_prior_exhausted_entry_without_reinvoking_provider(
    monkeypatch, tmp_path: Path
) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines import commercial_game_task_worker as worker
    from packages.contributions.pipelines.commercial_game_task_worker import execute_same_project_task_cards

    monkeypatch.setattr(
        worker,
        "run_safe_commands",
        lambda commands, working_directory: [
            {
                "command": str(command.command),
                "argv": ["python", "-c", "print('ok')"],
                "return_code": 0,
                "passed": True,
                "status": "passed",
            }
            for command in commands
        ],
    )
    project_dir = tmp_path / "cocos_project"
    evidence_dir = project_dir / "workflow_runtime_evidence"
    evidence_dir.mkdir(parents=True)
    audio_evidence = evidence_dir / "audio_feedback_polish_evidence.json"
    audio_evidence.write_text(json.dumps({"go": True, "audioPlaybackVerified": True}), encoding="utf-8")
    run_root = tmp_path / "pipeline_evidence"
    ledger_root = run_root / "task_card_worker"
    ledger_root.mkdir(parents=True)
    (ledger_root / "same_project_patch_ledger.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "task_card_id": "tc_prior_audio_recovery",
                        "status": "blocked",
                        "failure_class": "blocked_after_three_attempts",
                        "final_failure_class": "same_project_patch_parse_failed",
                        "retry_exhausted": True,
                        "receipt_id": "receipt_prior_audio_3",
                        "child_run_id": "child_prior_audio_3",
                        "child_attempt_id": "attempt_prior_audio_3",
                        "worker_adapter": "opencode",
                        "execution_visibility_mode": "human_visible_cli_enforced",
                        "visible_cli_session": _visible_cli_session(tmp_path, "tc_prior_audio_recovery"),
                        "attempts": [
                            {
                                "attempt_index": 3,
                                "status": "failed",
                                "failure_class": "same_project_patch_parse_failed",
                                "receipt_id": "receipt_prior_audio_3",
                                "child_run_id": "child_prior_audio_3",
                                "child_attempt_id": "attempt_prior_audio_3",
                                "worker_adapter": "opencode",
                                "execution_visibility_mode": "human_visible_cli_enforced",
                                "visible_cli_session": _visible_cli_session(tmp_path, "tc_prior_audio_recovery"),
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    card = TaskCard(
        run_id="pipeline_prior_recover_exhausted",
        task_card_id="tc_prior_audio_recovery",
        title="Recover prior audio runtime",
        description="Recover prior exhausted provider entry when artifacts and tests pass.",
        goal="Recover prior exhausted provider entry when artifacts and tests pass.",
        write_set=["workflow_runtime_evidence/audio_feedback_polish_evidence.json"],
        read_set=["workflow_runtime_evidence/audio_feedback_polish_evidence.json"],
        test_commands=["python -c \"print('ok')\""],
        acceptance_criteria=["audio evidence exists", "tests pass"],
        evidence_requirements=["same_project_patch", "human_visible_cli_session"],
        expected_artifacts=["workflow_runtime_evidence/audio_feedback_polish_evidence.json"],
        blocking_conditions=["same_project_patch_parse_failed"],
        model_guidance=["Do not reinvoke providers when the exhausted entry has valid artifacts."],
        provider_lane="codex_cli",
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
        metadata={"execution_visibility_mode": "human_visible_cli_enforced"},
    )

    def _unexpected_runner(**_kwargs):
        raise AssertionError("provider should not be reinvoked when prior exhausted artifacts already pass")

    ledger = execute_same_project_task_cards(
        root=tmp_path,
        run_root=run_root,
        project_dir=project_dir,
        pipeline_id="pipeline_prior_recover_exhausted",
        db_path=tmp_path / "workflow.db",
        task_cards=[card],
        max_repair_attempts=2,
        task_card_runner=_unexpected_runner,
    )

    entry = ledger["entries"][0]
    assert ledger["same_project_worker_patch_go"] is True
    assert entry["status"] == "completed"
    assert entry["prior_exhausted_entry_recovered"] is True
    assert entry["deterministic_exhausted_provider_recovery"]["go"] is True
    assert entry["mutation_result"]["final_test_status"] == "passed"


def test_same_project_business_task_cards_excludes_persisted_machine_gate_repair_cards() -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import same_project_business_task_cards

    def _card(task_card_id: str, metadata: dict[str, object]) -> TaskCard:
        return TaskCard(
            run_id="pipeline_business_filter",
            task_card_id=task_card_id,
            title=f"Task {task_card_id}",
            description=f"Task {task_card_id}",
            goal=f"Patch {task_card_id} in the same project with a real implementation.",
            write_set=["state/pipeline_runs/<run>/cocos_project/assets/scripts"],
            read_set=["brief.md"],
            test_commands=["python -m pytest tests/test_commercial_game_evidence_contracts.py -q"],
            acceptance_criteria=["same project patched", "tests passed"],
            evidence_requirements=["same_project_patch"],
            blocking_conditions=["provider_timeout"],
            model_guidance=["Use the same project only."],
            execution_mode="same_project_patch",
            risk_level="high",
            status="active",
            metadata=metadata,
        )

    cards = [
        _card("tc_core", {}),
        _card(
            "tc_machine_gate_repair",
            {"machine_gate_repair_card": True, "task_card_generation_source": "active_phase_machine_gate_repair"},
        ),
    ]

    assert [card.task_card_id for card in same_project_business_task_cards(cards)] == ["tc_core"]


def test_same_project_patch_ledger_retries_runtime_failures_until_success(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import execute_same_project_task_cards

    def _card(task_card_id: str) -> TaskCard:
        return TaskCard(
            run_id="pipeline_retry_success",
            task_card_id=task_card_id,
            title=f"Task {task_card_id}",
            description=f"Task {task_card_id}",
            goal=f"Patch {task_card_id} in the same project with fresh receipt retry accounting.",
            write_set=["state/pipeline_runs/<run>/cocos_project/assets/scripts"],
            read_set=["brief.md"],
            test_commands=["python -m pytest tests/test_commercial_game_evidence_contracts.py -q"],
            acceptance_criteria=["same project patched", "tests passed"],
            evidence_requirements=["same_project_patch"],
            blocking_conditions=["provider_output_idle_timeout"],
            model_guidance=["Retry the same card only with fresh receipts."],
            execution_mode="same_project_patch",
            risk_level="high",
            status="active",
        )

    calls: list[str] = []

    def _runner(**kwargs):
        task_id = kwargs["task_card"].task_card_id
        calls.append(task_id)
        attempt_index = calls.count(task_id)
        if task_id == "tc_levels" and attempt_index < 3:
            return {
                "status": "failed",
                "failure_class": "provider_output_idle_timeout",
                "receipt_id": f"receipt_levels_{attempt_index}",
                "watchdog": {
                    "timeout_type": "provider_output_idle_timeout",
                    "stream_event_count": attempt_index,
                    "control_output_event_count": attempt_index,
                    "provider_output_event_count": 0,
                    "last_provider_output_at": f"2026-04-30T00:00:0{attempt_index}+00:00",
                },
            }
        return {
            "status": "completed",
            "failure_class": None,
            "receipt_id": f"receipt_{task_id}_{attempt_index}",
            "child_run_id": f"run_{task_id}_{attempt_index}",
            "child_attempt_id": f"attempt_{task_id}_{attempt_index}",
            "worker_adapter": "codex",
            "mutation_result": {
                "changed_files": [f"state/project/assets/scripts/{task_id}.ts"],
                "final_test_status": "passed",
            },
            "watchdog": {"stream_event_count": 3, "provider_output_event_count": 2, "material_progress_event_count": 1},
            "visible_cli_session": _visible_cli_session(tmp_path, task_id),
        }

    ledger = execute_same_project_task_cards(
        root=tmp_path,
        run_root=tmp_path / "pipeline_evidence",
        project_dir=tmp_path / "cocos_project",
        pipeline_id="pipeline_retry_success",
        db_path=tmp_path / "workflow.db",
        task_cards=[_card("tc_levels"), _card("tc_shop")],
        max_repair_attempts=1,
        task_card_runner=_runner,
    )

    first_entry = ledger["entries"][0]
    assert ledger["same_project_worker_patch_go"] is True
    assert ledger["blockers"] == []
    assert calls == ["tc_levels", "tc_levels", "tc_levels", "tc_shop"]
    assert first_entry["status"] == "completed"
    assert first_entry["final_test_status"] == "passed"
    assert first_entry["consecutive_failure_count"] == 0
    assert first_entry["retry_exhausted"] is False
    assert [attempt["receipt_id"] for attempt in first_entry["attempts"]] == [
        "receipt_levels_1",
        "receipt_levels_2",
        "receipt_tc_levels_3",
    ]


def test_same_project_patch_ledger_retries_adaptive_scope_timeout_with_fallback_adapter(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import execute_same_project_task_cards

    card = TaskCard(
        run_id="pipeline_scope_timeout",
        task_card_id="tc_machine_gate_repair",
        title="Repair Cocos machine gate",
        description="Narrow and retry Cocos machine gate repair after adaptive wall timeout.",
        goal="Patch the same project after adaptive wall timeout without losing receipt accounting.",
        write_set=["state/pipeline_runs/<run>/cocos_project/assets/scripts"],
        read_set=["cocos_build_stderr.log"],
        test_commands=["python -m pytest tests/test_commercial_game_evidence_contracts.py -q"],
        acceptance_criteria=["same project patched", "tests passed"],
        evidence_requirements=["same_project_patch", "human_visible_cli_session"],
        blocking_conditions=["task_scope_too_large_after_adaptive_wall_timeout"],
        model_guidance=["Retry with a narrower scope or fallback adapter."],
        provider_lane="codex_cli",
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
        metadata={"execution_visibility_mode": "human_visible_cli_enforced", "human_visible_cli_required": True},
    )
    adapter_calls: list[str | None] = []

    def _runner(**kwargs):
        adapter_calls.append(kwargs.get("adapter_name"))
        attempt_index = len(adapter_calls)
        if attempt_index == 1:
            return {
                "status": "failed",
                "failure_class": "task_scope_too_large_after_adaptive_wall_timeout",
                "receipt_id": "receipt_scope_1",
                "worker_adapter": kwargs.get("adapter_name"),
                "watchdog": {
                    "timeout_type": "adaptive_wall_timeout_exhausted",
                    "adaptive_wall_timeout_extension_count": 1,
                    "adaptive_wall_timeout_exhausted": True,
                },
            }
        return {
            "status": "completed",
            "receipt_id": "receipt_scope_2",
            "child_run_id": "run_scope_2",
            "child_attempt_id": "attempt_scope_2",
            "worker_adapter": kwargs.get("adapter_name"),
            "mutation_result": {
                "changed_files": ["state/project/assets/scripts/MachineGateRepair.ts"],
                "final_test_status": "passed",
            },
            "visible_cli_session": _visible_cli_session(tmp_path, "tc_machine_gate_repair"),
            "watchdog": {"stream_event_count": 3, "provider_output_event_count": 2, "material_progress_event_count": 1},
        }

    ledger = execute_same_project_task_cards(
        root=tmp_path,
        run_root=tmp_path / "pipeline_evidence",
        project_dir=tmp_path / "cocos_project",
        pipeline_id="pipeline_scope_timeout",
        db_path=tmp_path / "workflow.db",
        task_cards=[card],
        max_repair_attempts=1,
        task_card_runner=_runner,
    )

    entry = ledger["entries"][0]
    assert ledger["same_project_worker_patch_go"] is True
    assert adapter_calls == ["codex", "opencode"]
    assert entry["status"] == "completed"
    assert [attempt["failure_class"] for attempt in entry["attempts"]] == [
        "task_scope_too_large_after_adaptive_wall_timeout",
        None,
    ]


def test_same_project_patch_ledger_switches_adapter_after_patch_parse_failure(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import execute_same_project_task_cards

    card = TaskCard(
        run_id="pipeline_patch_parse_fallback",
        task_card_id="tc_audio_parse",
        title="Repair audio runtime",
        description="Fallback to another patch-capable provider after unparseable patch output.",
        goal="Patch the same project after provider output parse failure.",
        write_set=["state/pipeline_runs/<run>/cocos_project/assets/scripts"],
        read_set=["brief.md"],
        test_commands=["python -m pytest tests/test_commercial_game_evidence_contracts.py -q"],
        acceptance_criteria=["same project patched", "tests passed"],
        evidence_requirements=["same_project_patch", "human_visible_cli_session"],
        blocking_conditions=["same_project_patch_parse_failed"],
        model_guidance=["Switch provider after parse failure before declaring exhaustion."],
        provider_lane="codex_cli",
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
        metadata={"execution_visibility_mode": "human_visible_cli_enforced", "human_visible_cli_required": True},
    )
    adapter_calls: list[str | None] = []

    def _runner(**kwargs):
        adapter_calls.append(kwargs.get("adapter_name"))
        if len(adapter_calls) == 1:
            return {
                "status": "failed",
                "failure_class": "same_project_patch_parse_failed",
                "receipt_id": "receipt_parse_1",
                "child_run_id": "run_parse_1",
                "child_attempt_id": "attempt_parse_1",
                "worker_adapter": kwargs.get("adapter_name"),
                "visible_cli_session": _visible_cli_session(tmp_path, "tc_audio_parse"),
                "mutation_result": {"changed_files": [], "final_test_status": "patch_parse_failed"},
            }
        return {
            "status": "completed",
            "receipt_id": "receipt_parse_2",
            "child_run_id": "run_parse_2",
            "child_attempt_id": "attempt_parse_2",
            "worker_adapter": kwargs.get("adapter_name"),
            "mutation_result": {
                "changed_files": ["state/project/assets/scripts/AudioFeedbackController.ts"],
                "final_test_status": "passed",
            },
            "visible_cli_session": _visible_cli_session(tmp_path, "tc_audio_parse"),
        }

    ledger = execute_same_project_task_cards(
        root=tmp_path,
        run_root=tmp_path / "pipeline_evidence",
        project_dir=tmp_path / "cocos_project",
        pipeline_id="pipeline_patch_parse_fallback",
        db_path=tmp_path / "workflow.db",
        task_cards=[card],
        max_repair_attempts=1,
        task_card_runner=_runner,
    )

    entry = ledger["entries"][0]
    assert ledger["same_project_worker_patch_go"] is True
    assert adapter_calls == ["codex", "opencode"]
    assert entry["worker_adapter"] == "opencode"
    assert [attempt["failure_class"] for attempt in entry["attempts"]] == ["same_project_patch_parse_failed", None]


def test_same_project_patch_ledger_uses_fallback_adapter_after_prior_no_material_progress(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import execute_same_project_task_cards

    run_root = tmp_path / "pipeline_evidence"
    ledger_root = run_root / "task_card_worker"
    ledger_root.mkdir(parents=True)
    (ledger_root / "same_project_patch_ledger.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "task_card_id": "tc_audio",
                        "status": "blocked",
                        "failure_class": "blocked_after_three_attempts",
                        "final_failure_class": "provider_no_material_progress_timeout",
                        "worker_adapter": "codex",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    card = TaskCard(
        run_id="pipeline_adapter_fallback",
        task_card_id="tc_audio",
        title="Task tc_audio",
        description="Task tc_audio",
        goal="Patch audio feedback in the same project with fresh receipt retry accounting.",
        write_set=["state/pipeline_runs/<run>/cocos_project/assets/scripts"],
        read_set=["brief.md"],
        test_commands=["python -m pytest tests/test_commercial_game_evidence_contracts.py -q"],
        acceptance_criteria=["same project patched", "tests passed"],
        evidence_requirements=["same_project_patch", "human_visible_cli_session"],
        blocking_conditions=["provider_no_material_progress_timeout"],
        model_guidance=["Retry the same card only with fresh receipts."],
        provider_lane="codex_cli",
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
        metadata={"execution_visibility_mode": "human_visible_cli_enforced", "human_visible_cli_required": True},
    )
    adapter_calls: list[str | None] = []

    def _runner(**kwargs):
        adapter_calls.append(kwargs.get("adapter_name"))
        return {
            "status": "completed",
            "receipt_id": "receipt_audio_fallback",
            "child_run_id": "run_audio_fallback",
            "child_attempt_id": "attempt_audio_fallback",
            "worker_adapter": kwargs.get("adapter_name"),
            "mutation_result": {
                "changed_files": ["state/project/assets/scripts/AudioFeedbackController.ts"],
                "final_test_status": "passed",
            },
            "visible_cli_session": {
                "status": "completed",
                "pid": 1234,
                "argv": ["workflowctl", "run", "from-task-card"],
                "cwd": tmp_path.as_posix(),
                "stdout_log_path": (tmp_path / "stdout.log").as_posix(),
                "stderr_log_path": (tmp_path / "stderr.log").as_posix(),
                "stream_log_path": (tmp_path / "stream.jsonl").as_posix(),
                "started_at": "2026-05-03T00:00:00+00:00",
            },
        }

    ledger = execute_same_project_task_cards(
        root=tmp_path,
        run_root=run_root,
        project_dir=tmp_path / "cocos_project",
        pipeline_id="pipeline_adapter_fallback",
        db_path=tmp_path / "workflow.db",
        task_cards=[card],
        max_repair_attempts=1,
        task_card_runner=_runner,
    )

    assert adapter_calls == ["opencode"]
    assert ledger["same_project_worker_patch_go"] is True
    assert ledger["entries"][0]["worker_adapter"] == "opencode"
    assert ledger["entries"][0]["execution_visibility_mode"] == "human_visible_cli_enforced"


def test_collect_project_runtime_evidence_refreshes_contracts_from_task_card_artifacts(tmp_path: Path) -> None:
    from packages.contributions.pipelines.commercial_game_task_worker import collect_project_runtime_evidence

    project_dir = tmp_path / "cocos_project"
    evidence_dir = project_dir / "workflow_runtime_evidence"
    evidence_dir.mkdir(parents=True)
    (project_dir / "workflow_commercial_feature_evidence.json").write_text(
        json.dumps({"commercial_feature_coverage": {}}),
        encoding="utf-8",
    )
    (evidence_dir / "gameplay_semantic_evidence.raw.json").write_text(
        json.dumps(
            {
                "board_state": {"rows": 10, "cols": 10},
                "piece_shapes": [{"id": "single"}],
                "candidate_tray": [{"slot": 0}, {"slot": 1}, {"slot": 2}],
                "semantic_traces": {
                    "placement": "placement.json",
                    "line_clear": "line_clear.json",
                    "candidate_refresh": "candidate_refresh.json",
                    "game_over": "game_over.json",
                    "anti_stall": "anti_stall.json",
                },
                "model_transition_traces": {"placement": {"before": {}, "after": {}}},
                "baseline_only": True,
            }
        ),
        encoding="utf-8",
    )
    (evidence_dir / "product_body_evidence.raw.json").write_text(
        json.dumps(
            {
                "scene_nodes": ["Canvas", "Board", "Hud"],
                "cocos_component_bindings": ["BoardView", "InputController", "AudioFeedbackController"],
                "scene_path": "assets/scene/product_body.scene",
                "baseline_only": True,
            }
        ),
        encoding="utf-8",
    )
    (evidence_dir / "core_loop_runtime_evidence.json").write_text(
        json.dumps({"state_transitions": [{"to": "failed"}, {"to": "levelComplete"}]}),
        encoding="utf-8",
    )
    (evidence_dir / "level_goal_evidence.json").write_text(
        json.dumps(
            {
                "levels": [
                    {
                        "level_id": "level_1",
                        "goals": [
                            {"id": f"goal_{index}", "visible_label": f"Goal {index} 0/1"}
                            for index in range(1, 9)
                        ],
                    }
                ],
                "revive_and_failure_rules": {"failure_condition": "moves == 0"},
            }
        ),
        encoding="utf-8",
    )
    (evidence_dir / "commercial_shop_skin_gallery_evidence.json").write_text(
        json.dumps(
            {
                "shop_ownership_state": {"stored_fields": ["ownedSkinIds"]},
                "skin_equipped_visual_change": {"player_visible_targets": ["boardPreview.color"]},
            }
        ),
        encoding="utf-8",
    )
    (evidence_dir / "chinese_ui_panels_evidence.json").write_text(
        json.dumps(
            {
                "chinese_ui_panels": [
                    {"panel_id": "hud_panel", "chinese_name": "HUD", "chinese_labels": {"score": "分数"}},
                    {"panel_id": "shop_panel", "chinese_name": "商店", "chinese_labels": {"buy": "购买"}},
                    {"panel_id": "gallery_panel", "chinese_name": "画廊", "chinese_labels": {"skin": "皮肤"}},
                    {"panel_id": "settings_panel", "chinese_name": "设置", "chinese_labels": {"music": "音乐"}},
                    {"panel_id": "failure_revive_panel", "chinese_name": "复活", "chinese_labels": {"revive": "复活"}},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (evidence_dir / "audio_feedback_polish_evidence.json").write_text(
        json.dumps(
            {
                "audio_runtime_evidence": {"runtime_bound": True, "event_bindings_count": 4},
                "feedback_animation_evidence": {
                    "runtime_bound": True,
                    "binding_count": 4,
                    "feedback_types": ["placement", "line_clear", "failure", "success"],
                },
                "polish_runtime_evidence": {"runtime_bound": True, "effects_count": 3},
            }
        ),
        encoding="utf-8",
    )
    (evidence_dir / "product_depth_evidence.json").write_text(
        json.dumps({"schema_version": "commercial_game_product_depth_evidence_v1", "blockers": ["blocked_by_same_project_worker"]}),
        encoding="utf-8",
    )

    result = collect_project_runtime_evidence(
        project_dir=project_dir,
        creator_exe=tmp_path / "CocosCreator.exe",
        require_build=False,
        require_playtest=False,
    )

    product_depth = json.loads((evidence_dir / "product_depth_evidence.json").read_text(encoding="utf-8"))
    product_body = json.loads((evidence_dir / "product_body_evidence.json").read_text(encoding="utf-8"))
    build_ledger = json.loads((evidence_dir / "build_ledger.json").read_text(encoding="utf-8"))
    browser_ledger = json.loads((evidence_dir / "browser_playtest_ledger.json").read_text(encoding="utf-8"))
    assert result["commercial_feature_coverage"]["audioPlaybackVerified"] is True
    assert result["commercial_feature_coverage"]["shopOwnershipStates"] is True
    assert result["commercial_feature_coverage"]["chineseUiPanelsVisible"] is True
    assert product_depth["go"] is True
    assert product_body["go"] is True
    assert product_body["source"]["baseline_only"] is False
    assert "blocked_by_same_project_worker" not in product_depth["blockers"]
    assert "blocked_by_same_project_worker" not in product_body["blockers"]
    assert "blocked_by_same_project_worker" not in build_ledger["blockers"]
    assert "blocked_by_same_project_worker" not in browser_ledger["blockers"]


def test_collect_project_runtime_evidence_merges_current_worker_schema(tmp_path: Path) -> None:
    from packages.contributions.pipelines.commercial_game_task_worker import collect_project_runtime_evidence

    project_dir = tmp_path / "cocos_project"
    evidence_dir = project_dir / "workflow_runtime_evidence"
    content_dir = project_dir / "assets" / "resources" / "content"
    evidence_dir.mkdir(parents=True)
    content_dir.mkdir(parents=True)
    (project_dir / "workflow_commercial_feature_evidence.json").write_text(
        json.dumps({"generatedArtAssets": [{"asset_id": "board"}], "particleEffects": ["clear_sweep"]}),
        encoding="utf-8",
    )
    (evidence_dir / "gameplay_semantic_evidence.raw.json").write_text(
        json.dumps(
            {
                "board_state": {"rows": 10, "cols": 10},
                "piece_shapes": [{"cells": [[0, 0]]}],
                "candidate_tray": [{}, {}, {}],
                "runtime_phase": True,
                "semantic_traces": {"placement": True, "line_clear": True},
                "model_transition_traces": [{"transition": "placement", "before": {}, "after": {}}],
            }
        ),
        encoding="utf-8",
    )
    (evidence_dir / "product_body_evidence.raw.json").write_text(
        json.dumps(
            {
                "engine_native_product_body": {
                    "runtime_components": [{"path": "assets/scripts/runtime/model/GameModel.ts"}],
                    "scene_prefab_component_bindings": [
                        {
                            "scene_path": "assets/scene/game.scene",
                            "scene_meta_path": "assets/scene/game.scene.meta",
                            "settings_path": "settings/v2/packages/scene.json",
                        },
                        {
                            "prefab_path": "assets/prefabs/hud.prefab",
                            "bound_components": ["GameModel"],
                        },
                    ],
                },
                "baseline_only": False,
            }
        ),
        encoding="utf-8",
    )
    (evidence_dir / "scene_prefab_binding_evidence.json").write_text(
        json.dumps(
            {
                "scene": {
                    "scene_path": "assets/scene/game.scene",
                    "root_node": "GameRoot",
                    "runtime_controller_node": "RuntimeController",
                    "component_bindings": [{"component_path": "assets/scripts/runtime/model/GameModel.ts"}],
                },
                "prefabs": [{"prefab_path": "assets/prefabs/hud.prefab"}],
            }
        ),
        encoding="utf-8",
    )
    (content_dir / "level_goal_matrix.json").write_text(
        json.dumps(
            {
                "levels": [
                    {"levelId": index, "goals": [{"goalId": f"goal_{index}", "kind": "score", "amount": index * 10}]}
                    for index in range(1, 9)
                ]
            }
        ),
        encoding="utf-8",
    )
    (evidence_dir / "level_goal_evidence.json").write_text(
        json.dumps({"rules_runtime_state_proof": {"revive": {"max_per_run": 3}}}),
        encoding="utf-8",
    )
    (evidence_dir / "commercial_shop_skin_gallery_evidence.json").write_text(
        json.dumps(
            {
                "shop_skin_gallery_runtime_state": {
                    "skin_reward_ids": ["mint", "neon"],
                    "gallery_entry_ids": ["spring_full"],
                    "state_fields_persisted": ["unlockedRewardIds", "selectedSkinId"],
                },
                "unlock_replay": [
                    {"step": 1, "puzzle_piece_state": {"spring": 1}},
                    {"step": 2, "awarded_reward_ids": ["spring_full"], "skin_unlocked": True},
                ],
            }
        ),
        encoding="utf-8",
    )
    (evidence_dir / "chinese_ui_panels_evidence.json").write_text(
        json.dumps(
            {
                "chinese_ui_panels": {
                    "hud_panel": {"title": "HUD", "readable_simplified_chinese_labels": ["分数"]},
                    "shop_panel": {"title": "商店", "readable_simplified_chinese_labels": ["购买"]},
                    "gallery_panel": {"title": "图鉴", "readable_simplified_chinese_labels": ["皮肤"]},
                    "settings_panel": {"title": "设置", "readable_simplified_chinese_labels": ["音乐"]},
                    "failure_revive_panel": {"title": "复活", "readable_simplified_chinese_labels": ["复活"]},
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (evidence_dir / "audio_asset_manifest_evidence.json").write_text(
        json.dumps({"fresh_worker_receipt": {"generated_artifacts": ["assets/resources/commercial_assets/audio/bank.json"]}}),
        encoding="utf-8",
    )
    (evidence_dir / "audio_feedback_polish_evidence.json").write_text(
        json.dumps(
            {
                "audioPlaybackVerified": True,
                "bgmStarted": True,
                "sfxPlaybackVerified": True,
                "volumeToggleUsable": True,
            }
        ),
        encoding="utf-8",
    )

    result = collect_project_runtime_evidence(
        project_dir=project_dir,
        creator_exe=tmp_path / "CocosCreator.exe",
        require_build=False,
        require_playtest=False,
    )

    assert result["product_body_evidence"]["go"] is True
    assert result["product_depth_evidence"]["go"] is True
    assert result["commercial_feature_coverage"]["generatedAudioAssets"] is True
    assert result["commercial_feature_coverage"]["shopOwnershipStates"] is True
    assert result["commercial_feature_coverage"]["chineseUiPanelsVisible"] is True
    assert result["commercial_feature_coverage"]["failureReviveFeedback"] is True
    assert result["product_body_evidence"]["source"]["scene_node_count"] >= 3


def test_split_audio_feedback_polish_evidence_merges_for_feature_coverage() -> None:
    from packages.contributions.pipelines.commercial_game_task_worker import (
        _combined_audio_feedback_polish_evidence,
        _merge_audio_asset_manifest_evidence,
        _merge_audio_feedback_polish_evidence,
    )

    merged: dict[str, object] = {}
    combined = _combined_audio_feedback_polish_evidence(
        audio_polish={"audio_runtime_evidence": {"runtime_bound": True, "event_bindings_count": 5}},
        feedback_animation={
            "feedback_animation_evidence": {
                "placement_animation_runtime_bound": True,
                "line_clear_animation_runtime_bound": True,
                "failure_animation_runtime_bound": True,
                "success_animation_runtime_bound": True,
                "runtime_event_bindings": ["onPiecePlaced", "onLinesCleared", "onFailure", "onSuccess"],
            }
        },
        input_polish={
            "input_controller_features": [{"feature": "snap_preview_tracking"}],
            "board_view_features": [{"feature": "invalid_target_feedback"}],
            "defect_reproduction_prevention": {"drag_lag": {"verified": True}},
        },
    )

    _merge_audio_feedback_polish_evidence(merged, combined)

    assert merged["commercial_feature_coverage"]["audioPlaybackVerified"] is True
    assert merged["commercial_feature_coverage"]["animationFeedbackVerified"] is True
    assert merged["commercial_feature_coverage"]["failureReviveFeedback"] is True
    assert merged["player_visible_checks"]["polishEffectsApplied"] is True
    _merge_audio_asset_manifest_evidence(
        merged,
        {
            "manifest_paths": ["assets/resources/commercial_assets/audio/commercial_audio_manifest.json"],
            "bgm_tracks": [{"id": "main_bgm"}],
            "sfx_events": [{"id": "place"}],
        },
    )
    assert merged["commercial_feature_coverage"]["generatedAudioAssets"] is True
    assert merged["product_depth_evidence"]["audio_design_depth"]["bgm_track_count"] == 1


def test_level_goal_fallback_and_chinese_ui_mojibake_gate() -> None:
    from packages.contributions.pipelines.commercial_game_task_worker import (
        _merge_chinese_ui_panels_evidence,
        _merge_level_goal_evidence,
    )

    merged: dict[str, object] = {}
    _merge_level_goal_evidence(
        merged,
        {
            "level_goals": [
                {"goal_id": f"goal_{index}", "label": f"目标{index}"}
                for index in range(1, 9)
            ]
        },
    )
    assert merged["product_depth_evidence"]["distinctLevelGoalCount"] == 8

    _merge_chinese_ui_panels_evidence(
        merged,
        {
            "chinese_ui_panels": [
                {"panel_id": "hud_panel", "chinese_name": "HUD", "chinese_labels": {"score": "寰楀垎"}},
                {"panel_id": "shop_panel", "chinese_name": "商店", "chinese_labels": {"buy": "购买"}},
                {"panel_id": "gallery_panel", "chinese_name": "画廊", "chinese_labels": {"skin": "皮肤"}},
                {"panel_id": "settings_panel", "chinese_name": "设置", "chinese_labels": {"music": "音乐"}},
                {"panel_id": "failure_revive_panel", "chinese_name": "复活", "chinese_labels": {"revive": "复活"}},
            ]
        },
    )
    assert merged.get("commercial_feature_coverage", {}).get("chineseUiPanelsVisible") is not True

    _merge_chinese_ui_panels_evidence(
        merged,
        {
            "chinese_ui_panels": {
                "hud_panel": {"panel_id": "hud_panel", "chinese_name": "HUD", "readable_simplified_chinese_labels": ["得分", "最高分"]},
                "shop_panel": {"panel_id": "shop_panel", "chinese_name": "商店", "readable_simplified_chinese_labels": ["购买", "关闭"]},
                "gallery_panel": {"panel_id": "gallery_panel", "chinese_name": "画廊", "readable_simplified_chinese_labels": ["收藏图鉴", "返回"]},
                "settings_panel": {"panel_id": "settings_panel", "chinese_name": "设置", "readable_simplified_chinese_labels": ["音乐音量", "保存"]},
                "failure_revive_panel": {"panel_id": "failure_revive_panel", "chinese_name": "复活", "readable_simplified_chinese_labels": ["游戏结束", "再来一局"]},
            }
        },
    )
    assert merged["commercial_feature_coverage"]["chineseUiPanelsVisible"] is True


def test_collect_project_runtime_evidence_merges_engine_native_worker_schema_v2(tmp_path: Path) -> None:
    from packages.contributions.pipelines.commercial_game_task_worker import collect_project_runtime_evidence

    project_dir = tmp_path / "cocos_project"
    evidence_dir = project_dir / "workflow_runtime_evidence"
    content_dir = project_dir / "assets" / "resources" / "content"
    evidence_dir.mkdir(parents=True)
    content_dir.mkdir(parents=True)
    (evidence_dir / "gameplay_semantic_evidence.raw.json").write_text(
        json.dumps(
            {
                "board_state": {"rows": 10, "cols": 10},
                "piece_shapes": [{"cells": [[0, 0]]}],
                "candidate_tray": [{}, {}, {}],
                "runtime_phase": True,
                "semantic_traces": {"placement": True, "line_clear": True},
                "model_transition_traces": [{"transition": "placement", "before": {}, "after": {}}],
            }
        ),
        encoding="utf-8",
    )
    (evidence_dir / "product_body_evidence.raw.json").write_text(
        json.dumps(
            {
                "runtime_components": [
                    {"component_name": "BlockPuzzleRuntimeController", "path": "assets/scripts/runtime/gameplay/BlockPuzzleRuntimeController.ts"},
                    {"component_name": "BlockPuzzleModel", "path": "assets/scripts/runtime/model/BlockPuzzleModel.ts"},
                ],
                "scene_prefab_component_binding": {
                    "launch_scene": {
                        "scene_path": "assets/scene/block_puzzle_player_visible.scene",
                        "scene_meta_path": "assets/scene/block_puzzle_player_visible.scene.meta",
                        "settings_path": "settings/v2/packages/scene.json",
                    },
                    "live_component_instance": {
                        "node_path": "Canvas",
                        "component_type": "WorkflowBlockPuzzleSceneRuntime",
                        "bound_runtime_model_components": ["BlockPuzzleRuntimeController", "BlockPuzzleModel"],
                    },
                    "prefab_paths": ["assets/prefabs/block_candidate_bar.prefab"],
                    "player_visible_surfaces": [{"node_name": "HUD_简体中文"}, {"node_name": "Board_10x10_RuntimeGrid"}],
                },
                "baseline_only": False,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (evidence_dir / "scene_prefab_binding_evidence.json").write_text(
        json.dumps(
            {
                "launch_scene_binding": {
                    "scene_path": "assets/scene/block_puzzle_player_visible.scene",
                    "scene_meta_path": "assets/scene/block_puzzle_player_visible.scene.meta",
                    "settings_path": "settings/v2/packages/scene.json",
                },
                "live_component_binding": {
                    "valid": True,
                    "component_instance_type": "WorkflowBlockPuzzleSceneRuntime",
                    "runtime_component_node_path": "Canvas",
                    "bound_runtime_model_components": ["BlockPuzzleRuntimeController", "BlockPuzzleModel"],
                },
                "player_visible_surfaces": {
                    "hud_shell": {"node_name": "HUD_简体中文"},
                    "board_shell": {"node_name": "Board_10x10_RuntimeGrid"},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (content_dir / "level_goal_matrix.json").write_text(
        json.dumps(
            {
                "content_matrix_state_proof": {
                    "classic_mode": {"revive_limit_per_run": 3},
                    "authored_level_count": 8,
                },
                "levels": [
                    {
                        "level_id": index,
                        "title_zh_cn": f"第{index}关",
                        "target_score": index * 100,
                        "color_targets": {"red": index},
                        "failure_condition": "game_over_before_goal_complete",
                    }
                    for index in range(1, 9)
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (evidence_dir / "commercial_shop_skin_gallery_evidence.json").write_text(
        json.dumps(
            {
                "gallery_unlock_trace": [{"reward_id": "gallery_1", "unlocks_skin_id": "skin_1"}],
                "shop_skin_gallery_state_proof": {
                    "default_owned_skin": "skin_default",
                    "unlockable_skin_count": 1,
                    "gallery_reward_count": 1,
                    "persistent_fields": ["ownedSkinIds", "selectedSkinId"],
                },
            }
        ),
        encoding="utf-8",
    )
    (evidence_dir / "chinese_ui_panels_evidence.json").write_text(
        json.dumps(
            {
                "chinese_ui_panels": {
                    "hud_panel": {"title": "对局界面", "labels": ["分数", "最高分"]},
                    "shop_panel": {"title": "商店", "labels": ["购买", "关闭"]},
                    "gallery_panel": {"title": "收藏图鉴", "labels": ["拼图碎片", "返回"]},
                    "settings_panel": {"title": "设置", "labels": ["音乐", "音效"]},
                    "failure_revive_panel": {"title": "游戏结束", "labels": ["复活", "再来一局"]},
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (evidence_dir / "audio_asset_manifest_evidence.json").write_text(
        json.dumps({"audio_assets": [{"id": "bgm"}], "generatedAudioAssets": True}),
        encoding="utf-8",
    )
    (evidence_dir / "audio_feedback_polish_evidence.json").write_text(
        json.dumps({"audio_runtime_evidence": {"runtime_bound": True, "event_bindings_count": 4}}),
        encoding="utf-8",
    )
    (evidence_dir / "feedback_animation_evidence.json").write_text(
        json.dumps({"feedback_animation_evidence": {"runtime_bound": True, "binding_count": 4, "feedback_types": ["failure", "success"]}}),
        encoding="utf-8",
    )

    result = collect_project_runtime_evidence(
        project_dir=project_dir,
        creator_exe=tmp_path / "CocosCreator.exe",
        require_build=False,
        require_playtest=False,
    )

    assert result["product_body_evidence"]["go"] is True
    assert result["product_depth_evidence"]["go"] is True
    assert result["commercial_feature_coverage"]["shopOwnershipStates"] is True
    assert result["commercial_feature_coverage"]["skinEquippedVisualChange"] is True
    assert result["commercial_feature_coverage"]["chineseUiPanelsVisible"] is True
    assert result["commercial_feature_coverage"]["failureReviveFeedback"] is True
    assert result["product_depth_evidence"]["source"]["distinct_level_goal_count"] == 8


def test_same_project_patch_ledger_retries_review_failures_until_success(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import execute_same_project_task_cards

    card = TaskCard(
        run_id="pipeline_retry_review_failure",
        task_card_id="tc_revive",
        title="Task tc_revive",
        description="Task tc_revive",
        goal="Patch revive prompt state in the same project with fresh receipt retry accounting.",
        write_set=["state/pipeline_runs/<run>/cocos_project/assets/scripts"],
        read_set=["brief.md"],
        test_commands=["python -m pytest tests/test_commercial_game_evidence_contracts.py -q"],
        acceptance_criteria=["same project patched", "tests passed"],
        evidence_requirements=["same_project_patch"],
        blocking_conditions=["same_project_patch_review_failed"],
        model_guidance=["Retry the same card only with fresh receipts."],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    receipts: list[str] = []

    def _runner(**_kwargs):
        attempt_index = len(receipts) + 1
        receipts.append(f"receipt_revive_{attempt_index}")
        if attempt_index < 3:
            return {
                "status": "failed",
                "failure_class": "same_project_patch_review_failed",
                "receipt_id": receipts[-1],
                "review_decision": "fail",
                "watchdog": {"stream_event_count": attempt_index, "provider_output_event_count": attempt_index},
            }
        return {
            "status": "completed",
            "failure_class": None,
            "receipt_id": receipts[-1],
            "child_run_id": "run_revive",
            "child_attempt_id": f"attempt_revive_{attempt_index}",
            "worker_adapter": "codex",
            "mutation_result": {
                "changed_files": ["state/project/assets/scripts/RevivePromptState.ts"],
                "final_test_status": "passed",
            },
            "watchdog": {"stream_event_count": 3, "provider_output_event_count": 3, "material_progress_event_count": 1},
            "visible_cli_session": _visible_cli_session(tmp_path, "tc_revive"),
        }

    ledger = execute_same_project_task_cards(
        root=tmp_path,
        run_root=tmp_path / "pipeline_evidence",
        project_dir=tmp_path / "cocos_project",
        pipeline_id="pipeline_retry_review_failure",
        db_path=tmp_path / "workflow.db",
        task_cards=[card],
        max_repair_attempts=1,
        task_card_runner=_runner,
    )

    entry = ledger["entries"][0]
    assert ledger["same_project_worker_patch_go"] is True
    assert ledger["blockers"] == []
    assert receipts == ["receipt_revive_1", "receipt_revive_2", "receipt_revive_3"]
    assert entry["status"] == "completed"
    assert entry["consecutive_failure_count"] == 0
    assert entry["retry_exhausted"] is False
    assert [attempt["failure_class"] for attempt in entry["attempts"]] == [
        "same_project_patch_review_failed",
        "same_project_patch_review_failed",
        None,
    ]


def test_same_project_patch_ledger_fail_fast_precondition_does_not_retry(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import execute_same_project_task_cards

    card = TaskCard(
        run_id="pipeline_preflight_blocker",
        task_card_id="tc_levels",
        title="Implement levels",
        description="Implement level goals in the same Cocos project.",
        goal="Implement level goals in the same Cocos project with preflight validation.",
        write_set=["state/pipeline_runs/<run>/cocos_project/assets/scripts"],
        read_set=["brief.md"],
        test_commands=["python -m pytest tests/test_commercial_game_evidence_contracts.py -q"],
        acceptance_criteria=["same project patched", "tests passed"],
        evidence_requirements=["same_project_patch"],
        blocking_conditions=["provider_live_proof_missing"],
        model_guidance=["Do not retry hard precondition failures."],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )
    calls = 0

    def _preflight_runner(**_kwargs):
        nonlocal calls
        calls += 1
        return {
            "status": "blocked",
            "failure_class": "provider_live_proof_missing",
            "receipt_id": None,
            "watchdog": {},
        }

    ledger = execute_same_project_task_cards(
        root=tmp_path,
        run_root=tmp_path / "pipeline_evidence",
        project_dir=tmp_path / "cocos_project",
        pipeline_id="pipeline_preflight_blocker",
        db_path=tmp_path / "workflow.db",
        task_cards=[card],
        max_repair_attempts=1,
        task_card_runner=_preflight_runner,
    )

    entry = ledger["entries"][0]
    assert calls == 1
    assert entry["preflight_blocker"] is True
    assert entry["retry_exhausted"] is False
    assert entry["failure_class"] == "provider_live_proof_missing"
    assert "blocked_after_three_attempts" not in ledger["blockers"]


def test_same_project_patch_ledger_resumes_after_prior_completed_entry(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import execute_same_project_task_cards

    def _card(task_card_id: str) -> TaskCard:
        return TaskCard(
            run_id="pipeline_resume",
            task_card_id=task_card_id,
            title=f"Task {task_card_id}",
            description=f"Task {task_card_id} patches the same Cocos project with fresh worker evidence.",
            goal=f"Patch {task_card_id} in the same Cocos project while preserving fresh receipt and test evidence.",
            write_set=["state/pipeline_runs/<run>/cocos_project/assets/scripts"],
            read_set=["brief.md"],
            test_commands=["python -m pytest tests/test_commercial_game_evidence_contracts.py -q"],
            acceptance_criteria=["same project patched", "fresh worker evidence remains valid"],
            evidence_requirements=["same_project_patch"],
            blocking_conditions=["provider_timeout"],
            model_guidance=["Patch only the same project."],
            execution_mode="same_project_patch",
            risk_level="high",
            status="active",
        )

    ledger_root = tmp_path / "pipeline_evidence" / "task_card_worker"
    ledger_root.mkdir(parents=True)
    (ledger_root / "same_project_patch_ledger.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "task_card_id": "tc_levels",
                        "title": "Task tc_levels",
                        "status": "completed",
                        "failure_class": None,
                        "receipt_id": "receipt_levels_prior",
                        "child_run_id": "run_levels_prior",
                        "child_attempt_id": "attempt_levels_prior",
                            "worker_adapter": "codex",
                            "execution_visibility_mode": "human_visible_cli_enforced",
                            "visible_cli_session": _visible_cli_session(tmp_path, "tc_levels"),
                            "changed_files": ["state/project/assets/scripts/LevelGoalProgression.ts"],
                            "mutation_result": {
                                "changed_files": ["state/project/assets/scripts/LevelGoalProgression.ts"],
                                "final_test_status": "passed",
                            },
                        "continuation_required": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    runner_calls: list[str] = []

    def _runner(**kwargs):
        runner_calls.append(kwargs["task_card"].task_card_id)
        return {
            "status": "completed",
            "failure_class": None,
            "receipt_id": "receipt_shop",
            "child_run_id": "run_shop",
            "child_attempt_id": "attempt_shop",
            "worker_adapter": "codex",
            "mutation_result": {
                "changed_files": ["state/project/assets/scripts/Shop.ts"],
                "final_test_status": "passed",
            },
            "watchdog": {"stream_event_count": 5},
            "visible_cli_session": _visible_cli_session(tmp_path, "tc_shop"),
        }

    ledger = execute_same_project_task_cards(
        root=tmp_path,
        run_root=tmp_path / "pipeline_evidence",
        project_dir=tmp_path / "cocos_project",
        pipeline_id="pipeline_resume",
        db_path=tmp_path / "workflow.db",
        task_cards=[_card("tc_levels"), _card("tc_shop")],
        max_repair_attempts=1,
        task_card_runner=_runner,
    )

    assert runner_calls == ["tc_shop"]
    assert ledger["same_project_worker_patch_go"] is True
    assert ledger["completed_count"] == 2
    assert [entry["task_card_id"] for entry in ledger["entries"]] == ["tc_levels", "tc_shop"]


def test_same_project_patch_ledger_revalidates_prior_completed_artifacts_before_skip(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import execute_same_project_task_cards

    project_dir = tmp_path / "cocos_project"
    scene_path = project_dir / "assets/scene/main.scene"
    scene_path.parent.mkdir(parents=True)
    (project_dir / "settings/v2/packages").mkdir(parents=True)
    (project_dir / "workflow_runtime_evidence").mkdir(parents=True)
    scene_path.write_text(
        json.dumps(
            [
                {"__type__": "cc.SceneAsset"},
                {"__type__": "cc.Scene"},
                {"__type__": "cc.Node", "_components": [{"__id__": 3}]},
                {"__type__": "cc.CompPrefabInfo", "component": "RuntimeBinding", "script": "assets/scripts/RuntimeBinding.ts"},
            ]
        ),
        encoding="utf-8",
    )
    scene_path.with_suffix(".scene.meta").write_text(json.dumps({"uuid": "scene-uuid"}), encoding="utf-8")
    (project_dir / "settings/v2/packages/scene.json").write_text(
        json.dumps({"current-scene": "scene-uuid"}),
        encoding="utf-8",
    )
    (project_dir / "workflow_runtime_evidence/scene_prefab_binding_evidence.json").write_text(
        json.dumps({"scene_path": "assets/scene/main.scene"}),
        encoding="utf-8",
    )

    card = TaskCard(
        run_id="pipeline_revalidate_prior",
        task_card_id="tc_scene_prefab_component_binding",
        title="Scene component binding",
        description="Bind actual runtime components in the launch scene.",
        goal="Bind actual custom Cocos runtime components in the launch scene.",
        write_set=["state/pipeline_runs/<run>/cocos_project/assets/scene/main.scene"],
        read_set=["brief.md"],
        test_commands=["python -m pytest tests/test_cocos_e2e.py -q"],
        expected_artifacts=[
            "assets/scene/main.scene",
            "workflow_runtime_evidence/scene_prefab_binding_evidence.json",
        ],
        acceptance_criteria=["actual runtime component exists", "launch scene is bound to the generated component scene"],
        evidence_requirements=["scene_prefab_component_binding"],
        blocking_conditions=["cocos_scene_runtime_component_binding_missing"],
        model_guidance=["cc.CompPrefabInfo metadata is not enough; add an actual custom component object to a scene node."],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    ledger_root = tmp_path / "pipeline_evidence" / "task_card_worker"
    ledger_root.mkdir(parents=True)
    (ledger_root / "same_project_patch_ledger.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "task_card_id": "tc_scene_prefab_component_binding",
                        "title": "Scene component binding",
                        "status": "completed",
                        "failure_class": None,
                        "receipt_id": "receipt_scene_prior",
                        "child_run_id": "run_scene_prior",
                        "child_attempt_id": "attempt_scene_prior",
                        "worker_adapter": "codex",
                        "execution_visibility_mode": "human_visible_cli_enforced",
                        "visible_cli_session": _visible_cli_session(tmp_path, "tc_scene_prefab_component_binding"),
                        "changed_files": ["state/project/assets/scene/main.scene"],
                        "mutation_result": {
                            "changed_files": ["state/project/assets/scene/main.scene"],
                            "final_test_status": "passed",
                        },
                        "continuation_required": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    runner_calls: list[str] = []

    def _runner(**kwargs):
        runner_calls.append(kwargs["task_card"].task_card_id)
        scene_path.write_text(
            json.dumps(
                [
                    {"__type__": "cc.SceneAsset"},
                    {"__type__": "cc.Scene"},
                    {"__type__": "cc.Node", "_components": [{"__id__": 3}]},
                    {"__type__": "WorkflowRuntimeSceneBinding", "_enabled": True},
                ]
            ),
            encoding="utf-8",
        )
        return {
            "status": "completed",
            "failure_class": None,
            "receipt_id": "receipt_scene_fresh",
            "child_run_id": "run_scene_fresh",
            "child_attempt_id": "attempt_scene_fresh",
            "worker_adapter": "codex",
            "mutation_result": {
                "changed_files": ["state/project/assets/scene/main.scene"],
                "final_test_status": "passed",
            },
            "watchdog": {"stream_event_count": 5, "provider_output_event_count": 5, "material_progress_event_count": 1},
            "visible_cli_session": _visible_cli_session(tmp_path, "tc_scene_prefab_component_binding"),
        }

    ledger = execute_same_project_task_cards(
        root=tmp_path,
        run_root=tmp_path / "pipeline_evidence",
        project_dir=project_dir,
        pipeline_id="pipeline_revalidate_prior",
        db_path=tmp_path / "workflow.db",
        task_cards=[card],
        max_repair_attempts=1,
        task_card_runner=_runner,
    )

    entry = ledger["entries"][0]
    assert runner_calls == ["tc_scene_prefab_component_binding"]
    assert ledger["same_project_worker_patch_go"] is True
    assert entry["receipt_id"] == "receipt_scene_fresh"
    assert entry["prior_completed_entry_invalidated"] is True
    assert entry["prior_completed_entry_failure_class"] == "prior_completed_entry_artifact_contract_no_go"
    assert entry["prior_completed_entry_artifact_validation"]["scene_component_blockers"] == [
        "cocos_scene_runtime_component_binding_missing"
    ]
    assert entry["artifact_validation"]["go"] is True


def test_same_project_patch_ledger_treats_existing_shop_evidence_as_reference_only(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import execute_same_project_task_cards

    project_dir = tmp_path / "cocos_project"
    (project_dir / "assets/scripts").mkdir(parents=True)
    (project_dir / "assets/resources/commercial_assets").mkdir(parents=True)
    (project_dir / "playtest_evidence").mkdir(parents=True)
    (project_dir / "assets/scripts/ShopSkinSystem.ts").write_text("export const shop = true;\n", encoding="utf-8")
    (project_dir / "assets/resources/commercial_assets/skin_catalog.json").write_text("{}", encoding="utf-8")
    screenshot = project_dir / "playtest_evidence/shop_panel.png"
    screenshot.write_bytes(b"png")
    (project_dir / "workflow_commercial_feature_evidence.json").write_text(
        json.dumps(
            {
                "commercial_feature_coverage": {
                    "shopOwnershipStates": True,
                    "skinEquippedVisualChange": True,
                },
                "player_visible_checks": {
                    "shopOwnershipStates": True,
                    "skinEquippedVisualChange": True,
                },
                "same_project_patch_files": [
                    "assets/scripts/ShopSkinSystem.ts",
                    "assets/resources/commercial_assets/skin_catalog.json",
                ],
                "screenshots": [screenshot.as_posix()],
                "open_panels": ["皮肤图鉴"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    card = TaskCard(
        run_id="pipeline_existing_shop",
        task_card_id="tc_shop",
        title="Implement shop skin collection ownership and equip flow",
        description="Use existing same-project shop evidence.",
        goal="Use existing same-project shop evidence as reference while still running a fresh worker patch.",
        write_set=[
            "state/pipeline_runs/<run>/cocos_project/assets/scripts",
            "state/pipeline_runs/<run>/cocos_project/assets/resources",
        ],
        read_set=["commercial_asset_bindings.json"],
        test_commands=["python -m pytest tests/test_cocos_e2e.py -q"],
        acceptance_criteria=["shop states visible", "fresh worker patch is recorded"],
        evidence_requirements=["shopOwnershipStates", "skinEquippedVisualChange", "collection_panel_screenshot"],
        blocking_conditions=["skin_panel_event_only"],
        model_guidance=["Do not rerun provider when evidence is already real."],
        provider_lane="codex_cli",
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    def _fresh_runner(**_kwargs):
        return {
            "status": "completed",
            "receipt_id": "receipt_shop_fresh",
            "child_run_id": "run_shop_fresh",
            "child_attempt_id": "attempt_shop_fresh",
            "worker_adapter": "codex",
            "mutation_result": {
                "changed_files": ["assets/scripts/ShopSkinSystem.ts"],
                "final_test_status": "passed",
            },
            "watchdog": {"stream_event_count": 3},
            "visible_cli_session": _visible_cli_session(tmp_path, "tc_shop"),
        }

    ledger = execute_same_project_task_cards(
        root=tmp_path,
        run_root=tmp_path / "pipeline_evidence",
        project_dir=project_dir,
        pipeline_id="pipeline_existing_shop",
        db_path=tmp_path / "workflow.db",
        task_cards=[card],
        max_repair_attempts=1,
        task_card_runner=_fresh_runner,
    )

    assert ledger["same_project_worker_patch_go"] is True
    assert ledger["completed_count"] == 1
    entry = ledger["entries"][0]
    assert entry["status"] == "completed"
    assert entry["receipt_id"] == "receipt_shop_fresh"
    assert entry["worker_adapter"] == "codex"
    assert entry["reference_evidence"]["satisfaction_mode"] == "reused_reference_only"
    assert entry["reference_evidence"]["evidence_reuse_real_files"] is True
    assert set(entry["reference_evidence"]["evidence_requirements_satisfied"]) == {
        "shopOwnershipStates",
        "skinEquippedVisualChange",
        "collection_panel_screenshot",
    }
    assert any(path.endswith("ShopSkinSystem.ts") for path in entry["reference_evidence"]["reference_files"])


def test_same_project_patch_ledger_treats_existing_core_loop_evidence_as_reference_only(
    tmp_path: Path,
) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import execute_same_project_task_cards

    project_dir = tmp_path / "cocos_project"
    (project_dir / "assets/scripts").mkdir(parents=True)
    (project_dir / "assets/scene").mkdir(parents=True)
    (project_dir / "assets/scripts/level_manifest.json").write_text(
        json.dumps(
            {
                "levels": [
                    {
                        "id": "level_01_score_sprint",
                        "reward": {"coins": 80, "unlock_level_ids": ["level_02_combo_chain"]},
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (project_dir / "assets/scene/level_goal_preview.json").write_text(
        json.dumps(
            {
                "ui_bindings": {"unlock_progress_node": "Canvas/HUD/LevelGoalPanel/UnlockProgress"},
                "sections": [{"section_id": "unlock_progress", "title_zh": "解锁进度"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (project_dir / "workflow_commercial_feature_evidence.json").write_text(
        json.dumps(
            {
                "player_visible_checks": {
                    "rewardPreviewConfigured": True,
                    "sessionUnlockChainConfigured": True,
                },
                "same_project_patch_files": [
                    "assets/scripts/level_manifest.json",
                    "assets/scene/level_goal_preview.json",
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    card = TaskCard(
        run_id="pipeline_existing_rewards",
        task_card_id="tc_core_loop",
        title="Implement core loop rewards and growth economy",
        description="Use existing same-project core loop evidence.",
        goal="Use existing same-project core loop evidence as reference while still running a fresh worker patch.",
        write_set=["state/pipeline_runs/<run>/cocos_project/assets/scripts"],
        read_set=["role_output:product_gameplay_agent"],
        test_commands=["python -m pytest tests/test_cocos_e2e.py -q"],
        acceptance_criteria=["core loop reward state is visible", "fresh worker patch is recorded"],
        evidence_requirements=["rewardCurrencyChanges", "unlockProgressVisible", "same_project_patch"],
        blocking_conditions=["reward_event_only"],
        model_guidance=["Do not rerun provider when evidence is already real."],
        provider_lane="codex_cli",
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    def _fresh_runner(**_kwargs):
        return {
            "status": "completed",
            "receipt_id": "receipt_core_loop_fresh",
            "child_run_id": "run_core_loop_fresh",
            "child_attempt_id": "attempt_core_loop_fresh",
            "worker_adapter": "codex",
            "mutation_result": {
                "changed_files": ["assets/scripts/level_manifest.json"],
                "final_test_status": "passed",
            },
            "watchdog": {"stream_event_count": 3},
            "visible_cli_session": _visible_cli_session(tmp_path, "tc_core_loop"),
        }

    ledger = execute_same_project_task_cards(
        root=tmp_path,
        run_root=tmp_path / "pipeline_evidence",
        project_dir=project_dir,
        pipeline_id="pipeline_existing_rewards",
        db_path=tmp_path / "workflow.db",
        task_cards=[card],
        max_repair_attempts=1,
        task_card_runner=_fresh_runner,
    )

    assert ledger["same_project_worker_patch_go"] is True
    entry = ledger["entries"][0]
    assert entry["status"] == "completed"
    assert entry["receipt_id"] == "receipt_core_loop_fresh"
    assert entry["reference_evidence"]["satisfaction_mode"] == "reused_reference_only"
    assert set(entry["reference_evidence"]["evidence_requirements_satisfied"]) == {
        "rewardCurrencyChanges",
        "unlockProgressVisible",
        "same_project_patch",
    }
    assert any(path.endswith("level_manifest.json") for path in entry["reference_evidence"]["reference_files"])


def test_same_project_patch_ledger_keeps_human_review_packet_as_reference_until_fresh_run(
    tmp_path: Path,
) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import execute_same_project_task_cards

    project_dir = tmp_path / "cocos_project"
    (project_dir / "playtest_evidence").mkdir(parents=True)
    screenshot = project_dir / "playtest_evidence" / "review.png"
    screenshot.write_bytes(b"png")
    (project_dir / "workflow_commercial_feature_evidence.json").write_text(
        json.dumps(
            {
                "screenshots": [screenshot.as_posix()],
                "same_project_patch_files": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    card = TaskCard(
        run_id="pipeline_existing_human_review",
        task_card_id="tc_human_review",
        title="Prepare human player review packet",
        description="Generate an unattended review packet without self-approval.",
        goal="Stop at AWAITING_HUMAN_REVIEW unless a real reviewer accepts.",
        write_set=[
            "state/pipeline_runs/<run>/cocos_project/player_visible_evidence",
            "state/pipeline_runs/<run>/cocos_project/workflow_commercial_feature_evidence.json",
        ],
        read_set=["playtest_evidence"],
        test_commands=[
            "python -m pytest tests/test_pipeline_and_automation_cli.py::test_commercial_gate_v2_can_stop_at_human_review_only -q"
        ],
        acceptance_criteria=["review packet exists", "no human acceptance is fabricated"],
        evidence_requirements=["human_review_packet", "awaiting_human_review_status"],
        blocking_conditions=["fabricated_human_acceptance"],
        model_guidance=["Do not self-approve."],
        provider_lane="codex_cli",
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    def _fresh_runner(**_kwargs):
        return {
            "status": "completed",
            "receipt_id": "receipt_human_review_fresh",
            "child_run_id": "run_human_review_fresh",
            "child_attempt_id": "attempt_human_review_fresh",
            "worker_adapter": "codex",
            "mutation_result": {
                "changed_files": ["player_visible_evidence/human_player_review_packet.json"],
                "final_test_status": "passed",
            },
            "watchdog": {"stream_event_count": 3},
            "visible_cli_session": _visible_cli_session(tmp_path, "tc_human_review"),
        }

    ledger = execute_same_project_task_cards(
        root=tmp_path,
        run_root=tmp_path / "pipeline_evidence",
        project_dir=project_dir,
        pipeline_id="pipeline_existing_human_review",
        db_path=tmp_path / "workflow.db",
        task_cards=[card],
        max_repair_attempts=1,
        task_card_runner=_fresh_runner,
    )

    packet = json.loads((project_dir / "player_visible_evidence/human_player_review_packet.json").read_text())
    assert ledger["same_project_worker_patch_go"] is True
    entry = ledger["entries"][0]
    assert entry["status"] == "completed"
    assert entry["receipt_id"] == "receipt_human_review_fresh"
    assert entry["reference_evidence"]["satisfaction_mode"] == "reused_reference_only"
    assert packet["status"] == "AWAITING_HUMAN_REVIEW"
    assert packet["accepted_by_human"] is False
    assert packet["human_player_review_go"] is False
    assert packet["commercial_playable_go_allowed"] is False


def test_task_card_worker_cli_rejects_zero_patch_review_failed_payload() -> None:
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    status = worker_cli._implementation_status_from_payload(
        executed={"status": "completed"},
        payload={
            "review_decision": "fail",
            "pr_ready_summary": {
                "readiness": "review_required",
                "bounded_patch": {"changed_files": []},
                "tests": {"status": "not_requested"},
                "review": {"latest_review_decision": "fail"},
            },
        },
        mutation_result={},
    )

    assert status == {
        "status": "failed",
        "failure_class": "same_project_patch_review_failed",
        "readiness": "review_required",
    }


def test_task_card_worker_cli_maps_patch_generation_failure_to_provider_execution_failed() -> None:
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    status = worker_cli._implementation_status_from_payload(
        executed={"status": "completed"},
        payload={
            "review_decision": "fail",
            "pr_ready_summary": {
                "readiness": "blocked",
                "bounded_patch": {"changed_files": []},
                "tests": {"status": "patch_generation_failed"},
                "review": {"latest_review_decision": "fail"},
            },
        },
        mutation_result={},
    )

    assert status == {
        "status": "failed",
        "failure_class": "provider_execution_failed",
        "readiness": "blocked",
    }


def test_task_card_worker_cli_maps_patch_apply_failure_to_retryable_failure() -> None:
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    status = worker_cli._implementation_status_from_payload(
        executed={"status": "completed"},
        payload={
            "review_decision": "fail",
            "pr_ready_summary": {
                "readiness": "blocked",
                "bounded_patch": {"changed_files": []},
                "tests": {"status": "patch_apply_failed"},
                "review": {"latest_review_decision": "fail"},
            },
        },
        mutation_result={"changed_files": [], "final_test_status": "patch_apply_failed"},
    )

    assert status == {
        "status": "failed",
        "failure_class": "same_project_patch_apply_failed",
        "readiness": "blocked",
    }


def test_task_card_worker_cli_accepts_orchestration_coder_mutation_report() -> None:
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    payload = {
        "review_decision": "pass",
        "pr_ready_summary": {
            "readiness": "not_ready",
            "bounded_patch": {"changed_files": []},
            "tests": {"status": "not_requested"},
            "review": {"latest_review_decision": "pass"},
        },
        "orchestration": {
            "role_progress": {
                "coder": {
                    "mutation_report": {
                        "mutation_result": {
                            "changed_files": ["state/project/assets/scripts/LevelGoalProgression.ts"],
                            "final_test_status": "passed",
                        }
                    }
                }
            }
        },
    }
    mutation_result = worker_cli._mutation_result_from_payload(payload)

    status = worker_cli._implementation_status_from_payload(
        executed={"status": "completed"},
        payload=payload,
        mutation_result=mutation_result,
    )

    assert mutation_result["changed_files"] == ["state/project/assets/scripts/LevelGoalProgression.ts"]
    assert status == {
        "status": "completed",
        "failure_class": None,
        "readiness": "ready_via_orchestration_coder",
    }


def test_task_card_worker_cli_invokes_from_task_card_with_codex_patch_adapter(
    monkeypatch, tmp_path: Path
) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    calls: list[dict[str, object]] = []

    def _fake_run_json_command(command, **_kwargs):
        calls.append({"command": command, "kwargs": _kwargs})
        if "issue-receipt" in command:
            return {"status": "completed", "payload": {"receipt_id": "receipt_codex_patch"}}
        return {
            "status": "completed",
            "payload": {
                "run": {"run_id": "run_codex_patch"},
                "review_decision": "pass",
                "pr_ready_summary": {
                    "readiness": "ready",
                    "bounded_patch": {"changed_files": ["state/project/assets/scripts/Game.ts"]},
                    "tests": {"status": "passed"},
                    "review": {"latest_review_decision": "pass"},
                },
            },
            "watchdog_source": "workflowctl_payload",
        }

    monkeypatch.setattr(worker_cli, "_run_json_command", _fake_run_json_command)
    task_card_path = tmp_path / "tc_levels.md"
    task_card_path.write_text("# Implement levels\n", encoding="utf-8")
    card = TaskCard(
        run_id="pipeline_codex_adapter",
        task_card_id="tc_levels",
        title="Implement levels",
        description="Implement level goals in the same project.",
        goal="Implement level goals in the same project.",
        write_set=["state/project/assets/scripts"],
        read_set=["brief.md"],
        test_commands=["python -m pytest tests/test_commercial_game_evidence_contracts.py -q"],
        acceptance_criteria=["same project patched"],
        evidence_requirements=["same_project_patch"],
        blocking_conditions=["provider_timeout"],
        model_guidance=["Use the same project only."],
        provider_lane="codex_cli",
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    result = worker_cli.run_task_card_patch_via_workflowctl(
        root=tmp_path,
        db_path=tmp_path / "workflow.db",
        project_dir=tmp_path / "project",
        pipeline_id="pipeline_codex_adapter",
        task_card=card,
        task_card_path=task_card_path,
        write_set=card.write_set,
        read_set=card.read_set,
        test_commands=card.test_commands,
        max_fix_iterations=1,
    )

    issue_command = calls[0]["command"]
    run_command = calls[1]["command"]
    env_overrides = calls[1]["kwargs"]["env_overrides"]
    assert result["status"] == "completed"
    assert result["requested_adapter"] == "codex"
    assert result["changed_files"] == ["state/project/assets/scripts/Game.ts"]
    assert result["final_test_status"] == "passed"
    assert "--adapter" in issue_command
    assert issue_command[issue_command.index("--adapter") + 1] == "codex"
    assert "--preset" in issue_command
    assert issue_command[issue_command.index("--preset") + 1] == "feature_delivery"
    assert "--adapter" in run_command
    assert run_command[run_command.index("--adapter") + 1] == "codex"
    assert "--preset" in run_command
    assert run_command[run_command.index("--preset") + 1] == "feature_delivery"
    assert env_overrides["WORKFLOW_CODEX_TIMEOUT_SECONDS"] == "1800"
    assert env_overrides["WORKFLOW_CODEX_IDLE_TIMEOUT_SECONDS"] == "900"
    assert env_overrides["WORKFLOW_OPENCODE_TIMEOUT_SECONDS"] == "1800"
    assert env_overrides["WORKFLOW_OPENCODE_IDLE_TIMEOUT_SECONDS"] == "900"
    assert env_overrides["WORKFLOW_PROVIDER_TIMEOUT_SECONDS"] == "1800"
    assert env_overrides["WORKFLOW_PROVIDER_IDLE_TIMEOUT_SECONDS"] == "900"
    assert env_overrides["WORKFLOW_PROVIDER_OUTPUT_IDLE_TIMEOUT_SECONDS"] == "900"
    assert env_overrides["WORKFLOW_PROVIDER_MATERIAL_PROGRESS_IDLE_TIMEOUT_SECONDS"] == "720"
    assert env_overrides["WORKFLOW_PROVIDER_ADAPTIVE_WALL_TIMEOUT_INITIAL_SECONDS"] == "900"
    assert env_overrides["WORKFLOW_PROVIDER_ADAPTIVE_WALL_TIMEOUT_EXTENSION_SECONDS"] == "900"
    assert env_overrides["WORKFLOW_PROVIDER_ADAPTIVE_WALL_TIMEOUT_MAX_EXTENSIONS"] == "1"
    assert env_overrides["WORKFLOW_PROVIDER_ADAPTIVE_WALL_TIMEOUT_ABSOLUTE_MAX_SECONDS"] == "1800"
    assert calls[1]["kwargs"]["provider_output_idle_timeout_seconds"] == 900
    assert calls[1]["kwargs"]["material_progress_idle_timeout_seconds"] == 720
    assert calls[1]["kwargs"]["adaptive_wall_timeout_extension_seconds"] == 900
    assert calls[1]["kwargs"]["adaptive_wall_timeout_max_extensions"] == 1
    assert calls[1]["kwargs"]["adaptive_wall_timeout_absolute_max_seconds"] == 1800
    assert calls[1]["kwargs"]["adaptive_wall_timeout_progress_window_seconds"] == 720
    assert calls[1]["kwargs"]["execution_visibility_mode"] is None
    assert "shell" not in run_command
    assert "noop" not in run_command


def test_task_card_worker_cli_finalizes_existing_evidence_repair_after_worker_failure(
    monkeypatch, tmp_path: Path
) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    calls: list[list[str]] = []

    def _fake_run_json_command(command, **_kwargs):
        calls.append(command)
        if "issue-receipt" in command:
            return {"status": "completed", "payload": {"receipt_id": "receipt_finalize"}}
        return {
            "status": "failed",
            "failure_class": "provider_execution_failed",
            "visible_cli_session": {"status": "completed", "mode": "human_visible_cli_enforced"},
            "payload": {},
        }

    monkeypatch.setattr(worker_cli, "_run_json_command", _fake_run_json_command)
    monkeypatch.setattr(
        worker_cli,
        "run_safe_commands",
        lambda commands, working_directory: [
            {
                "command": str(commands[0].command),
                "argv": ["python", "-m", "pytest"],
                "return_code": 0,
                "passed": True,
                "status": "passed",
            }
        ],
    )
    project_dir = tmp_path / "project"
    evidence_dir = project_dir / "workflow_runtime_evidence"
    evidence_dir.mkdir(parents=True)
    evidence_path = evidence_dir / "shop_ownership_state.json"
    evidence_path.write_text('{"go": true}', encoding="utf-8")
    task_card_path = tmp_path / "tc_shop_finalize.md"
    task_card_path.write_text(
        "\n".join(
            [
                "# Finalize shop evidence",
                "",
                "## Metadata",
                "```json",
                json.dumps(
                    {
                        "ai_finding_id": "shop_skin_finalize",
                        "execution_visibility_mode": "human_visible_cli_enforced",
                        "evidence_paths": [evidence_path.as_posix()],
                        "covered_requirement_ids": ["REQ-1"],
                    }
                ),
                "```",
            ]
        ),
        encoding="utf-8",
    )
    card = TaskCard(
        run_id="run_finalize",
        task_card_id="tc_shop_finalize",
        title="Finalize shop evidence",
        description="Finalize existing workflow evidence after a worker failure.",
        goal="Finalize existing workflow evidence after a worker failure.",
        write_set=[evidence_dir.as_posix()],
        read_set=[evidence_path.as_posix()],
        test_commands=["python -m pytest tests/test_ai_playtest_quality_gate.py -q"],
        acceptance_criteria=["evidence exists", "tests pass"],
        evidence_requirements=["fresh_worker_receipt", "state_snapshot_after_repair"],
        blocking_conditions=["missing_replay_evidence", "requirement_coverage_missing"],
        model_guidance=["Only finalize existing evidence when it is present."],
        execution_mode="same_project_patch",
        risk_level="high",
        metadata={"execution_visibility_mode": "human_visible_cli_enforced"},
    )

    result = worker_cli.run_task_card_patch_via_workflowctl(
        root=tmp_path,
        db_path=tmp_path / "workflow.db",
        project_dir=project_dir,
        pipeline_id="run_finalize",
        task_card=card,
        task_card_path=task_card_path,
        write_set=card.write_set,
        read_set=card.read_set,
        test_commands=card.test_commands,
        max_fix_iterations=1,
        adapter_name="opencode",
        execution_visibility_mode="human_visible_cli_enforced",
    )

    assert result["status"] == "completed"
    assert result["failure_class"] is None
    assert result["mutation_result"]["finalized_existing_evidence"] is True
    assert result["changed_files"]
    assert Path(result["changed_files"][0]).exists()
    assert "--ttl-seconds" in calls[0]
    assert calls[0][calls[0].index("--ttl-seconds") + 1] == "7200"


def test_task_card_worker_cli_does_not_finalize_without_runtime_evidence_json(
    monkeypatch, tmp_path: Path
) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    def _fake_run_json_command(command, **_kwargs):
        if "issue-receipt" in command:
            return {"status": "completed", "payload": {"receipt_id": "receipt_finalize"}}
        return {
            "status": "failed",
            "failure_class": "provider_execution_failed",
            "visible_cli_session": {"status": "completed", "mode": "human_visible_cli_enforced"},
            "payload": {},
        }

    monkeypatch.setattr(worker_cli, "_run_json_command", _fake_run_json_command)
    monkeypatch.setattr(
        worker_cli,
        "run_safe_commands",
        lambda commands, working_directory: [
            {
                "command": str(commands[0].command),
                "argv": ["python", "-m", "pytest"],
                "return_code": 0,
                "passed": True,
                "status": "passed",
            }
        ],
    )
    project_dir = tmp_path / "project"
    evidence_dir = project_dir / "workflow_runtime_evidence"
    source_dir = project_dir / "assets" / "scripts"
    evidence_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)
    source_path = source_dir / "AudioFeedbackController.ts"
    coverage_path = evidence_dir / "requirement_coverage_trace.json"
    source_path.write_text("export class AudioFeedbackController {}", encoding="utf-8")
    coverage_path.write_text('{"covered_requirement_ids": ["REQ-1"]}', encoding="utf-8")
    task_card_path = tmp_path / "tc_audio_finalize.md"
    task_card_path.write_text(
        "\n".join(
            [
                "# Finalize audio evidence",
                "",
                "## Metadata",
                "```json",
                json.dumps(
                    {
                        "ai_finding_id": "audio_runtime_finalize",
                        "execution_visibility_mode": "human_visible_cli_enforced",
                        "evidence_paths": [source_path.as_posix(), coverage_path.as_posix()],
                        "covered_requirement_ids": ["REQ-1"],
                    }
                ),
                "```",
            ]
        ),
        encoding="utf-8",
    )
    card = TaskCard(
        run_id="run_finalize",
        task_card_id="tc_audio_finalize",
        title="Finalize audio evidence",
        description="Finalize existing workflow evidence after a worker failure.",
        goal="Finalize existing workflow evidence after a worker failure.",
        write_set=[evidence_dir.as_posix(), source_dir.as_posix()],
        read_set=[source_path.as_posix(), coverage_path.as_posix()],
        test_commands=["python -m pytest tests/test_ai_playtest_quality_gate.py -q"],
        acceptance_criteria=["evidence exists", "tests pass"],
        evidence_requirements=["fresh_worker_receipt", "state_snapshot_after_repair"],
        blocking_conditions=["missing_replay_evidence", "requirement_coverage_missing"],
        model_guidance=["Only finalize existing evidence when it is present."],
        execution_mode="same_project_patch",
        risk_level="high",
        metadata={"execution_visibility_mode": "human_visible_cli_enforced"},
    )

    result = worker_cli.run_task_card_patch_via_workflowctl(
        root=tmp_path,
        db_path=tmp_path / "workflow.db",
        project_dir=project_dir,
        pipeline_id="run_finalize",
        task_card=card,
        task_card_path=task_card_path,
        write_set=card.write_set,
        read_set=card.read_set,
        test_commands=card.test_commands,
        max_fix_iterations=1,
        adapter_name="opencode",
        execution_visibility_mode="human_visible_cli_enforced",
    )

    assert result["status"] == "failed"
    assert result["failure_class"] == "provider_execution_failed"
    assert "finalized_existing_evidence" not in result.get("mutation_result", {})


def test_task_card_worker_cli_passes_human_visible_cli_mode_and_metadata(
    monkeypatch, tmp_path: Path
) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    calls: list[dict[str, object]] = []

    def _fake_run_json_command(command, **kwargs):
        calls.append({"command": command, "kwargs": kwargs})
        if "issue-receipt" in command:
            return {"status": "completed", "payload": {"receipt_id": "receipt_visible"}}
        return {
            "status": "completed",
            "payload": {
                "run": {"run_id": "run_visible"},
                "review_decision": "pass",
                "pr_ready_summary": {
                    "readiness": "ready",
                    "bounded_patch": {"changed_files": ["state/project/assets/scripts/Game.ts"]},
                    "tests": {"status": "passed"},
                    "review": {"latest_review_decision": "pass"},
                },
            },
            "watchdog_source": "human_visible_cli_mirrored_logs",
            "visible_cli_session": {
                "pid": 1234,
                "argv": ["python", "-m", "apps.operator_cli.main"],
                "cwd": tmp_path.as_posix(),
                "stdout_log_path": (tmp_path / "stdout.log").as_posix(),
                "stderr_log_path": (tmp_path / "stderr.log").as_posix(),
                "stream_log_path": (tmp_path / "stream.jsonl").as_posix(),
                "started_at": "2026-05-03T00:00:00+00:00",
                "status": "completed",
            },
            "visible_cli_log_paths": {
                "stdout_log_path": (tmp_path / "stdout.log").as_posix(),
                "stderr_log_path": (tmp_path / "stderr.log").as_posix(),
                "stream_log_path": (tmp_path / "stream.jsonl").as_posix(),
            },
        }

    monkeypatch.setattr(worker_cli, "_run_json_command", _fake_run_json_command)
    task_card_path = tmp_path / "tc_visible.md"
    task_card_path.write_text("# Visible CLI\n", encoding="utf-8")
    card = TaskCard(
        run_id="pipeline_visible",
        task_card_id="tc_visible",
        title="Visible CLI card",
        description="Run high-risk commercial implementation in a visible terminal.",
        goal="Run high-risk commercial implementation in a visible terminal.",
        write_set=["state/project/assets/scripts"],
        read_set=["brief.md"],
        test_commands=["python -m pytest tests/test_commercial_game_evidence_contracts.py -q"],
        acceptance_criteria=["visible session recorded"],
        evidence_requirements=["same_project_patch", "human_visible_cli_session"],
        blocking_conditions=["headless_success_claimed"],
        model_guidance=["Use human_visible_cli_enforced."],
        provider_lane="codex_cli",
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
        metadata={"execution_visibility_mode": "human_visible_cli_enforced"},
    )

    result = worker_cli.run_task_card_patch_via_workflowctl(
        root=tmp_path,
        db_path=tmp_path / "workflow.db",
        project_dir=tmp_path / "project",
        pipeline_id="pipeline_visible",
        task_card=card,
        task_card_path=task_card_path,
        write_set=card.write_set,
        read_set=card.read_set,
        test_commands=card.test_commands,
        max_fix_iterations=1,
        execution_visibility_mode="human_visible_cli_enforced",
    )

    run_kwargs = calls[1]["kwargs"]
    assert result["status"] == "completed"
    assert result["execution_visibility_mode"] == "human_visible_cli_enforced"
    assert result["visible_cli_session"]["pid"] == 1234
    assert result["visible_cli_log_paths"]["stream_log_path"].endswith("stream.jsonl")
    assert run_kwargs["execution_visibility_mode"] == "human_visible_cli_enforced"
    assert run_kwargs["material_progress_idle_timeout_seconds"] is None
    assert run_kwargs["adaptive_wall_timeout_requires_material_progress"] is False
    assert run_kwargs["adaptive_wall_timeout_progress_window_seconds"] == 900
    assert run_kwargs["visible_session_dir"].as_posix().endswith("visible_cli_sessions/tc_visible")
    assert run_kwargs["visible_session_metadata"]["receipt_id"] == "receipt_visible"
    assert run_kwargs["visible_session_metadata"]["task_card_id"] == "tc_visible"
    assert run_kwargs["env_overrides"]["WORKFLOW_PROVIDER_DIRECT_VISIBLE_CLI"] == "1"
    assert run_kwargs["env_overrides"]["WORKFLOW_PROVIDER_VISIBLE_CLI_REQUIRED"] == "1"
    assert run_kwargs["env_overrides"]["WORKFLOW_PROVIDER_VISIBLE_PARENT_TASK_CARD_ID"] == "tc_visible"
    assert run_kwargs["env_overrides"]["WORKFLOW_PROVIDER_VISIBLE_PARENT_RECEIPT_ID"] == "receipt_visible"
    assert run_kwargs["env_overrides"]["WORKFLOW_PROVIDER_VISIBLE_SESSION_ROOT"].endswith(
        "visible_cli_sessions/tc_visible/provider_subprocesses"
    )
    assert run_kwargs["env_overrides"]["WORKFLOW_CONTROL_PLANE_VISIBILITY"] == "resident"
    assert run_kwargs["env_overrides"]["WORKFLOW_PROVIDER_VISIBILITY"] == "direct_visible"
    assert json.loads(run_kwargs["env_overrides"]["WORKFLOW_MUTATION_EXTERNAL_ROOTS"]) == [
        (tmp_path / "project").resolve().as_posix()
    ]
    assert worker_cli._powershell_quote_arg("D:\\Universal Agentic workflow\\python.exe") == "'D:\\Universal Agentic workflow\\python.exe'"


def test_resident_control_plane_mode_records_provider_visible_cli_without_outer_window(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    def _unexpected_outer_visible(*_args, **_kwargs):
        raise AssertionError("resident provider-visible mode must not launch an outer visible workflowctl window")

    def _fake_run_subprocess(command, **kwargs):
        callback = kwargs.get("on_output")
        assert callable(callback)
        assert kwargs["env"]["WORKFLOW_CONTROL_PLANE_VISIBILITY"] == "resident"
        callback(
            {
                "stream": "stderr",
                "text": "workflow_progress {\"event\":\"workflow_progress\"}\n",
                "byte_count": 48,
                "observed_at": "2026-05-04T00:00:00+00:00",
                "is_control": True,
                "is_material_progress": False,
            }
        )
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"run": {"run_id": "child_run_001"}, "pr_ready_summary": {"readiness": "ready"}}),
            stderr="",
        )

    monkeypatch.setattr(worker_cli, "_run_visible_json_command", _unexpected_outer_visible)
    monkeypatch.setattr(worker_cli, "run_subprocess_with_tree_timeout", _fake_run_subprocess)
    monkeypatch.setattr(
        worker_cli,
        "_inspect_child_workflow_state",
        lambda **_kwargs: {
            "run_id": "child_run_001",
            "attempt_id": "attempt_001",
            "provider_visible_cli_session": {
                "status": "completed",
                "provider": "codex",
                "provider_pid": 5678,
                "argv": ["codex", "exec", "-"],
                "cwd": tmp_path.as_posix(),
                "stdout_log_path": (tmp_path / "provider_stdout.log").as_posix(),
                "stderr_log_path": (tmp_path / "provider_stderr.log").as_posix(),
                "stream_log_path": (tmp_path / "provider_stream.jsonl").as_posix(),
                "started_at": "2026-05-04T00:00:00+00:00",
            },
            "provider_visible_cli_log_paths": {"session_path": (tmp_path / "provider_session.json").as_posix()},
        },
    )

    result = worker_cli._run_json_command(
        ["python", "-m", "apps.operator_cli.main", "run", "from-task-card"],
        cwd=tmp_path,
        timeout_seconds=900,
        idle_timeout_seconds=240,
        provider_output_idle_timeout_seconds=480,
        material_progress_idle_timeout_seconds=720,
        db_path=tmp_path / "workflow.db",
        task_goal="Patch same project from task card: tc_visible",
        receipt_id="receipt_visible",
        execution_visibility_mode="human_visible_cli_enforced",
        visible_session_dir=tmp_path / "visible_cli_sessions" / "tc_visible",
        visible_session_metadata={"task_card_id": "tc_visible"},
        env_overrides={
            "WORKFLOW_CONTROL_PLANE_VISIBILITY": "resident",
            "WORKFLOW_PROVIDER_VISIBILITY": "direct_visible",
            "WORKFLOW_PROVIDER_DIRECT_VISIBLE_CLI": "1",
        },
    )

    assert result["status"] == "completed"
    assert result["control_plane_visibility"] == "resident"
    assert result["provider_visibility"] == "direct_visible"
    assert result["visible_cli_session"]["mode"] == "resident_control_plane_provider_visible_enforced"
    assert result["provider_visible_cli_session"]["provider"] == "codex"
    assert result["child_attempt_id"] == "attempt_001"
    stream_log = Path(result["visible_cli_log_paths"]["stream_log_path"])
    assert stream_log.exists()
    assert "resident_control_plane_stderr" in stream_log.read_text(encoding="utf-8")


def test_task_card_worker_cli_normalizes_patch_adapter_aliases() -> None:
    from types import SimpleNamespace

    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    assert worker_cli._resolve_task_card_adapter(SimpleNamespace(provider_lane="codex_cli"), None) == "codex"
    assert worker_cli._resolve_task_card_adapter(SimpleNamespace(provider_lane="codex-cli"), None) == "codex"
    assert worker_cli._resolve_task_card_adapter(SimpleNamespace(provider_lane="opencode_cli"), None) == "opencode"
    assert worker_cli._resolve_task_card_adapter(SimpleNamespace(provider_lane="opencode-cli"), None) == "opencode"
    assert worker_cli._resolve_task_card_adapter(SimpleNamespace(provider_lane="shell"), None) == "codex"
    assert worker_cli._resolve_task_card_adapter(SimpleNamespace(provider_lane="noop"), None) == "codex"
    assert worker_cli._resolve_task_card_adapter(SimpleNamespace(provider_lane="codex"), "codex_cli") == "codex"


def test_task_card_worker_cli_honors_explicit_real_adapter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    calls: list[dict[str, object]] = []

    def _fake_run_json_command(command: list[str], **kwargs: object) -> dict[str, object]:
        calls.append({"command": command, "kwargs": kwargs})
        if "issue-receipt" in command:
            return {"status": "completed", "payload": {"receipt_id": "receipt_opencode"}}
        return {
            "status": "completed",
            "payload": {
                "run": {"run_id": "run_opencode"},
                "capability_adapter": "opencode",
                "review_decision": "pass",
                "pr_ready_summary": {
                    "readiness": "ready",
                    "bounded_patch": {"changed_files": ["state/project/workflow_commercial_feature_evidence.json"]},
                    "tests": {"status": "passed"},
                    "review": {"latest_review_decision": "pass"},
                },
            },
            "watchdog_source": "workflowctl_payload",
        }

    monkeypatch.setattr(worker_cli, "_run_json_command", _fake_run_json_command)
    task_card_path = tmp_path / "tc_feedback.md"
    task_card_path.write_text("# Feedback evidence\n", encoding="utf-8")
    card = TaskCard(
        run_id="pipeline_opencode_adapter",
        task_card_id="tc_feedback",
        title="Feedback evidence",
        description="Patch feedback evidence in the same project.",
        goal="Patch feedback evidence in the same project.",
        write_set=["state/project/workflow_commercial_feature_evidence.json"],
        read_set=["state/project/workflow_commercial_feature_evidence.json"],
        test_commands=["python -m json.tool state/project/workflow_commercial_feature_evidence.json"],
        acceptance_criteria=["same project patched"],
        evidence_requirements=["same_project_patch"],
        blocking_conditions=["provider_timeout"],
        model_guidance=["Use the same project only."],
        provider_lane="codex",
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    result = worker_cli.run_task_card_patch_via_workflowctl(
        root=tmp_path,
        db_path=tmp_path / "workflow.db",
        project_dir=tmp_path / "project",
        pipeline_id="pipeline_opencode_adapter",
        task_card=card,
        task_card_path=task_card_path,
        write_set=card.write_set,
        read_set=card.read_set,
        test_commands=card.test_commands,
        max_fix_iterations=1,
        adapter_name="opencode",
    )

    issue_command = calls[0]["command"]
    run_command = calls[1]["command"]
    assert result["status"] == "completed"
    assert result["requested_adapter"] == "opencode"
    assert issue_command[issue_command.index("--adapter") + 1] == "opencode"
    assert run_command[run_command.index("--adapter") + 1] == "opencode"
    assert "shell" not in run_command
    assert "noop" not in run_command


def test_task_card_worker_cli_close_child_workflow_marks_runtime_task_terminal(tmp_path: Path) -> None:
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    db_path = tmp_path / "workflow.db"
    now = datetime.now(UTC).isoformat()
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE runs (run_id TEXT PRIMARY KEY, status TEXT, updated_at TEXT);
            CREATE TABLE runtime_tasks (runtime_task_id TEXT PRIMARY KEY, status TEXT);
            CREATE TABLE runtime_attempts (attempt_id TEXT PRIMARY KEY, status TEXT, closed_at TEXT, close_reason TEXT);
            CREATE TABLE worker_leases (lease_id TEXT PRIMARY KEY, status TEXT, released_at TEXT, release_reason TEXT);
            CREATE TABLE runtime_claims (claim_id TEXT PRIMARY KEY, runtime_task_id TEXT, status TEXT, released_at TEXT, release_reason TEXT);
            CREATE TABLE scheduler_lease_decisions (decision_id TEXT PRIMARY KEY, runtime_task_id TEXT, released_at TEXT, release_reason TEXT);
            CREATE TABLE scheduler_committed_leases (committed_lease_id TEXT PRIMARY KEY, runtime_task_id TEXT, status TEXT, released_at TEXT, release_reason TEXT);
            CREATE TABLE run_events (
              event_id TEXT PRIMARY KEY,
              run_id TEXT,
              event_type TEXT,
              object_type TEXT,
              object_id TEXT,
              summary TEXT,
              payload_json TEXT,
              schema_version TEXT,
              created_at TEXT
            );
            """
        )
        connection.execute("INSERT INTO runs VALUES (?, ?, ?)", ("run_child", "running", now))
        connection.execute("INSERT INTO runtime_tasks VALUES (?, ?)", ("task_child", "running"))
        connection.execute("INSERT INTO runtime_attempts VALUES (?, ?, ?, ?)", ("attempt_child", "current", None, None))
        connection.execute("INSERT INTO worker_leases VALUES (?, ?, ?, ?)", ("lease_child", "active", None, None))
        connection.execute("INSERT INTO runtime_claims VALUES (?, ?, ?, ?, ?)", ("claim_child", "task_child", "active", None, None))
        connection.execute("INSERT INTO scheduler_lease_decisions VALUES (?, ?, ?, ?)", ("decision_child", "task_child", None, None))
        connection.execute("INSERT INTO scheduler_committed_leases VALUES (?, ?, ?, ?, ?)", ("committed_child", "task_child", "active", None, None))
        connection.commit()

    worker_cli._close_child_workflow(
        db_path=db_path,
        child_state={
            "run_id": "run_child",
            "runtime_task_id": "task_child",
            "attempt_id": "attempt_child",
            "worker_lease_id": "lease_child",
        },
        failure_class="provider_output_idle_timeout",
        receipt_id="receipt_child",
        command=["workflowctl", "run", "from-task-card"],
    )

    with sqlite3.connect(db_path) as connection:
        run_status = connection.execute("SELECT status FROM runs WHERE run_id = 'run_child'").fetchone()[0]
        task_status = connection.execute("SELECT status FROM runtime_tasks WHERE runtime_task_id = 'task_child'").fetchone()[0]
        attempt = connection.execute("SELECT status, close_reason FROM runtime_attempts WHERE attempt_id = 'attempt_child'").fetchone()
        lease = connection.execute("SELECT status, release_reason FROM worker_leases WHERE lease_id = 'lease_child'").fetchone()
        claim = connection.execute("SELECT status, release_reason FROM runtime_claims WHERE claim_id = 'claim_child'").fetchone()
        committed = connection.execute("SELECT status, release_reason FROM scheduler_committed_leases WHERE committed_lease_id = 'committed_child'").fetchone()

    assert run_status == "failed"
    assert task_status == "failed"
    assert attempt == ("closed", "provider_output_idle_timeout")
    assert lease == ("released", "provider_output_idle_timeout")
    assert claim == ("released", "provider_output_idle_timeout")
    assert committed == ("released", "provider_output_idle_timeout")


def test_same_project_patch_ledger_rejects_no_changed_files_as_implementation(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import execute_same_project_task_cards

    card = TaskCard(
        run_id="pipeline_zero_patch",
        task_card_id="tc_levels",
        title="Implement levels",
        description="Implement level goals in the same Cocos project.",
        goal="Implement level goals in the same Cocos project with changed files and evidence.",
        write_set=["state/pipeline_runs/<run>/cocos_project/assets/scripts"],
        read_set=["brief.md"],
        test_commands=["python -m pytest tests/test_commercial_game_evidence_contracts.py -q"],
        acceptance_criteria=["files changed", "tests passed"],
        evidence_requirements=["same_project_patch"],
        blocking_conditions=["zero_patch_false_positive"],
        model_guidance=["Do not claim completion without changed files."],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    def _zero_patch_runner(**_kwargs):
        return {
            "status": "failed",
            "failure_class": "same_project_patch_no_changed_files",
            "receipt_id": "receipt_zero_patch",
            "mutation_result": {"changed_files": []},
            "watchdog": {"stream_event_count": 1},
        }

    ledger = execute_same_project_task_cards(
        root=tmp_path,
        run_root=tmp_path / "pipeline_evidence",
        project_dir=tmp_path / "cocos_project",
        pipeline_id="pipeline_zero_patch",
        db_path=tmp_path / "workflow.db",
        task_cards=[card],
        max_repair_attempts=1,
        task_card_runner=_zero_patch_runner,
    )

    assert ledger["same_project_worker_patch_go"] is False
    assert "same_project_patch_no_changed_files" in ledger["blockers"]


def test_same_project_patch_ledger_blocks_visible_cli_required_without_session(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import execute_same_project_task_cards

    card = TaskCard(
        run_id="pipeline_visible_required",
        task_card_id="tc_visible",
        title="Visible commercial patch",
        description="High-risk commercial task card must not complete headlessly.",
        goal="High-risk commercial task card must not complete headlessly.",
        write_set=["state/pipeline_runs/<run>/cocos_project/assets/scripts"],
        read_set=["brief.md"],
        test_commands=["python -m pytest tests/test_commercial_game_evidence_contracts.py -q"],
        acceptance_criteria=["visible session metadata exists", "tests passed"],
        evidence_requirements=["same_project_patch", "human_visible_cli_session"],
        blocking_conditions=["headless_success_claimed"],
        model_guidance=["Use human_visible_cli_enforced."],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
        metadata={
            "human_visible_cli_required": True,
            "execution_visibility_mode": "human_visible_cli_enforced",
        },
    )
    runner_modes: list[str | None] = []

    def _headless_runner(**kwargs):
        runner_modes.append(kwargs.get("execution_visibility_mode"))
        return {
            "status": "completed",
            "receipt_id": "receipt_visible",
            "child_run_id": "run_visible",
            "child_attempt_id": "attempt_visible",
            "worker_adapter": "codex",
            "mutation_result": {
                "changed_files": ["state/project/assets/scripts/Game.ts"],
                "final_test_status": "passed",
            },
            "watchdog": {"stream_event_count": 3},
        }

    ledger = execute_same_project_task_cards(
        root=tmp_path,
        run_root=tmp_path / "pipeline_evidence",
        project_dir=tmp_path / "cocos_project",
        pipeline_id="pipeline_visible_required",
        db_path=tmp_path / "workflow.db",
        task_cards=[card],
        max_repair_attempts=1,
        task_card_runner=_headless_runner,
    )

    entry = ledger["entries"][0]
    assert runner_modes == ["human_visible_cli_enforced"]
    assert ledger["same_project_worker_patch_go"] is False
    assert "human_visible_cli_metadata_missing" in ledger["blockers"]
    assert entry["status"] == "failed"
    assert entry["failure_class"] == "human_visible_cli_metadata_missing"
    assert entry["preflight_blocker"] is True


def test_same_project_worker_normalizes_strong_model_lane_to_patch_adapter() -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import _adapter_attempt_sequence

    card = TaskCard(
        run_id="pipeline_strong_lane",
        task_card_id="tc_strong_lane",
        title="Strong model lane patch",
        description="Strong model aliases must resolve to a patch-capable worker adapter.",
        goal="Strong model aliases must resolve to a patch-capable worker adapter.",
        write_set=["project/runtime/gameplay/**"],
        read_set=["GameDesignSpec"],
        test_commands=["python -m pytest tests/test_game_design_ir.py -q"],
        acceptance_criteria=["adapter is patch-capable"],
        evidence_requirements=["same_project_patch"],
        blocking_conditions=["mutation_contract_invalid"],
        model_guidance=["Use configured strong model lane."],
        execution_mode="same_project_patch",
        provider_lane="codex_or_configured_strong_model",
        risk_level="high",
        status="active",
    )

    assert _adapter_attempt_sequence(card) == ["codex", "opencode"]


def test_task_worker_cli_protects_glob_write_set_literals() -> None:
    from apps.operator_cli.run_commands import _normalize_literal_cli_args
    from packages.contributions.pipelines.commercial_game_task_worker_cli import _literal_cli_arg

    protected = _literal_cli_arg("project/runtime/input/**")

    assert protected == '"project/runtime/input/**"'
    assert _normalize_literal_cli_args([protected]) == ["project/runtime/input/**"]


def test_same_project_materializes_cocos_project_relative_paths_to_external_root(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import _materialize_task_card

    project_dir = tmp_path / "fresh_cocos_project"
    card = TaskCard(
        run_id="pipeline_project_scope",
        task_card_id="tc_project_scope",
        title="Project-scoped Cocos patch",
        description="Cocos task cards should mutate the generated project, not the workflow repo.",
        goal="Patch Cocos project runtime files.",
        write_set=["assets/scripts/runtime/**", "workflow_runtime_evidence/**"],
        read_set=["assets/scene/**", "GameDesignSpec"],
        test_commands=["python -m json.tool workflow_runtime_evidence/gameplay_semantic_evidence.raw.json"],
        acceptance_criteria=["project root paths are externalized"],
        evidence_requirements=["same_project_patch"],
        blocking_conditions=["repo_root_assets_mutated"],
        model_guidance=["Use the generated Cocos project root."],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    materialized = _materialize_task_card(card, project_dir=project_dir, pipeline_id="pipeline_project_scope")

    assert materialized["write_set"] == [
        (project_dir / "assets/scripts/runtime/**").resolve().as_posix(),
        (project_dir / "workflow_runtime_evidence/**").resolve().as_posix(),
    ]
    assert materialized["read_set"][0] == (project_dir / "assets/scene/**").resolve().as_posix()
    assert materialized["read_set"][1] == "GameDesignSpec"
    assert (project_dir / "workflow_runtime_evidence/gameplay_semantic_evidence.raw.json").resolve().as_posix() in materialized[
        "test_commands"
    ][0]


def test_task_card_artifact_validation_rejects_missing_referenced_scene_prefab(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import (
        _materialize_task_card,
        _task_card_artifact_validation,
    )

    project_dir = tmp_path / "cocos_project"
    evidence_path = project_dir / "workflow_runtime_evidence" / "scene_prefab_binding_evidence.json"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text(
        json.dumps(
            {
                "schema_version": "scene_prefab_binding_evidence_v1",
                "scene_bindings": [
                    {
                        "scene_path": "assets/scene/commercial.scene",
                        "prefabs": ["assets/prefabs/runtime/hud.prefab"],
                        "components": ["HudComponent"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    card = TaskCard(
        run_id="pipeline_artifact_check",
        task_card_id="tc_scene",
        title="Scene binding",
        description="Scene evidence must point to real files.",
        goal="Create scene binding.",
        write_set=["assets/scene/**", "assets/prefabs/**", "workflow_runtime_evidence/scene_prefab_binding_evidence.json"],
        read_set=[],
        expected_artifacts=["workflow_runtime_evidence/scene_prefab_binding_evidence.json"],
        evidence_requirements=["workflow_runtime_evidence/scene_prefab_binding_evidence.json"],
        acceptance_criteria=["referenced scene and prefabs exist"],
        blocking_conditions=["referenced_artifact_missing"],
        model_guidance=[],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    materialized = _materialize_task_card(card, project_dir=project_dir, pipeline_id=card.run_id)
    validation = _task_card_artifact_validation(card, materialized=materialized, project_dir=project_dir)

    assert validation["go"] is False
    assert "referenced_artifact_missing" in validation["blockers"]
    assert (project_dir / "assets/scene/commercial.scene").as_posix() in validation["referenced_missing_artifacts"]


def test_task_card_artifact_validation_reports_concatenated_json_artifact(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import (
        _materialize_task_card,
        _task_card_artifact_validation,
    )

    project_dir = tmp_path / "cocos_project"
    evidence_path = project_dir / "workflow_runtime_evidence" / "machine_gate_repair_evidence.json"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text('{"attempt": 1}\n{"attempt": 2}\n', encoding="utf-8")
    card = TaskCard(
        run_id="pipeline_artifact_check",
        task_card_id="tc_machine_gate_repair",
        title="Machine repair",
        description="Machine repair evidence must stay parseable JSON.",
        goal="Repair machine evidence.",
        write_set=["workflow_runtime_evidence/**"],
        read_set=[],
        expected_artifacts=["workflow_runtime_evidence/machine_gate_repair_evidence.json"],
        evidence_requirements=["workflow_runtime_evidence/machine_gate_repair_evidence.json"],
        acceptance_criteria=["valid JSON evidence"],
        blocking_conditions=["expected_json_artifact_invalid"],
        model_guidance=[],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    materialized = _materialize_task_card(card, project_dir=project_dir, pipeline_id=card.run_id)
    validation = _task_card_artifact_validation(card, materialized=materialized, project_dir=project_dir)

    assert validation["go"] is False
    assert "expected_json_artifact_invalid" in validation["blockers"]
    assert evidence_path.as_posix() in validation["invalid_json_artifacts"]
    assert validation["invalid_json_reasons"][0]["reason"] == "multiple_top_level_json_documents"
    assert validation["invalid_json_reasons"][0]["json_document_count"] == 2
    assert "replace the artifact with exactly one JSON object" in validation["invalid_json_reasons"][0]["repair_hint"]


def test_task_card_artifact_validation_rejects_contract_only_scene_and_launch_miss(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import (
        _materialize_task_card,
        _task_card_artifact_validation,
    )

    project_dir = tmp_path / "cocos_project"
    scene_path = project_dir / "assets" / "scene" / "commercial.scene"
    prefab_path = project_dir / "assets" / "prefabs" / "hud.prefab"
    evidence_path = project_dir / "workflow_runtime_evidence" / "scene_prefab_binding_evidence.json"
    settings_path = project_dir / "settings" / "v2" / "packages" / "scene.json"
    scene_path.parent.mkdir(parents=True)
    prefab_path.parent.mkdir(parents=True)
    evidence_path.parent.mkdir(parents=True)
    settings_path.parent.mkdir(parents=True)
    scene_path.write_text(json.dumps({"schema_version": "contract_only_scene_v1"}), encoding="utf-8")
    scene_path.with_suffix(".scene.meta").write_text(json.dumps({"uuid": "scene-uuid"}), encoding="utf-8")
    prefab_path.write_text("{}", encoding="utf-8")
    settings_path.write_text(json.dumps({"current-scene": "scene-uuid"}), encoding="utf-8")
    evidence_path.write_text(
        json.dumps(
            {
                "schema_version": "scene_prefab_binding_evidence_v1",
                "scene": {"scene_path": "assets/scene/commercial.scene"},
                "prefabs": [{"prefab_path": "assets/prefabs/hud.prefab"}],
            }
        ),
        encoding="utf-8",
    )
    card = TaskCard(
        run_id="pipeline_artifact_check",
        task_card_id="tc_scene_prefab_component_binding",
        title="Scene binding",
        description="Scene evidence must point to a real Cocos launch scene.",
        goal="Create scene binding.",
        write_set=["assets/scene/**", "assets/prefabs/**", "settings/v2/packages/scene.json"],
        read_set=[],
        expected_artifacts=["workflow_runtime_evidence/scene_prefab_binding_evidence.json"],
        evidence_requirements=["workflow_runtime_evidence/scene_prefab_binding_evidence.json"],
        acceptance_criteria=["referenced scene is valid Cocos scene"],
        blocking_conditions=["expected_cocos_scene_artifact_invalid"],
        model_guidance=[],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    materialized = _materialize_task_card(card, project_dir=project_dir, pipeline_id=card.run_id)
    validation = _task_card_artifact_validation(card, materialized=materialized, project_dir=project_dir)

    assert validation["go"] is False
    assert "expected_cocos_scene_artifact_invalid" in validation["blockers"]
    assert "cocos_launch_scene_valid_scene_missing" in validation["blockers"]


def test_task_card_artifact_validation_rejects_fake_scene_component_metadata(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import (
        _materialize_task_card,
        _task_card_artifact_validation,
    )

    project_dir = tmp_path / "cocos_project"
    scene_path = project_dir / "assets" / "scene" / "commercial.scene"
    evidence_path = project_dir / "workflow_runtime_evidence" / "scene_prefab_binding_evidence.json"
    settings_path = project_dir / "settings" / "v2" / "packages" / "scene.json"
    script_path = project_dir / "assets" / "scripts" / "runtime" / "CommercialRuntimeController.ts"
    scene_path.parent.mkdir(parents=True)
    evidence_path.parent.mkdir(parents=True)
    settings_path.parent.mkdir(parents=True)
    script_path.parent.mkdir(parents=True)
    scene_path.write_text(
        json.dumps(
            [
                {"__type__": "cc.SceneAsset"},
                {"__type__": "cc.Scene", "_name": "CommercialScene"},
                {"__type__": "cc.Node", "_name": "RuntimeController", "_components": [{"__id__": 3}]},
                {
                    "__type__": "cc.CompPrefabInfo",
                    "component": "CommercialRuntimeController",
                    "script": "assets/scripts/runtime/CommercialRuntimeController.ts",
                },
            ]
        ),
        encoding="utf-8",
    )
    scene_path.with_suffix(".scene.meta").write_text(json.dumps({"uuid": "scene-uuid"}), encoding="utf-8")
    settings_path.write_text(json.dumps({"current-scene": "scene-uuid"}), encoding="utf-8")
    script_path.write_text("export class CommercialRuntimeController {}\n", encoding="utf-8")
    evidence_path.write_text(
        json.dumps(
            {
                "schema_version": "scene_prefab_binding_evidence_v1",
                "scene": {
                    "scene_path": "assets/scene/commercial.scene",
                    "component_bindings": [{"component_path": "assets/scripts/runtime/CommercialRuntimeController.ts"}],
                },
            }
        ),
        encoding="utf-8",
    )
    card = TaskCard(
        run_id="pipeline_artifact_check",
        task_card_id="tc_scene_prefab_component_binding",
        title="Scene binding",
        description="Scene evidence must include a runtime component instance.",
        goal="Create scene binding.",
        write_set=["assets/scene/**", "assets/scripts/runtime/**", "settings/v2/packages/scene.json"],
        read_set=[],
        expected_artifacts=["workflow_runtime_evidence/scene_prefab_binding_evidence.json"],
        evidence_requirements=["workflow_runtime_evidence/scene_prefab_binding_evidence.json"],
        acceptance_criteria=["scene node has actual component instance"],
        blocking_conditions=["cocos_scene_runtime_component_binding_missing"],
        model_guidance=[],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    materialized = _materialize_task_card(card, project_dir=project_dir, pipeline_id=card.run_id)
    validation = _task_card_artifact_validation(card, materialized=materialized, project_dir=project_dir)

    assert validation["go"] is False
    assert "cocos_scene_runtime_component_binding_missing" in validation["blockers"]


def test_task_card_artifact_validation_rejects_mojibake_localization(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import (
        _materialize_task_card,
        _task_card_artifact_validation,
    )

    project_dir = tmp_path / "cocos_project"
    localization_path = project_dir / "assets" / "resources" / "localization" / "zh-CN.json"
    localization_path.parent.mkdir(parents=True)
    localization_path.write_text(
        json.dumps({"game": {"title": "1010 \u93c2\u7470\u6f61\u5a11\u5809\u6ace"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    card = TaskCard(
        run_id="pipeline_artifact_check",
        task_card_id="tc_player_visible_ui_flow",
        title="Chinese UI",
        description="Chinese localization must be readable.",
        goal="Create Chinese UI.",
        write_set=["assets/resources/localization/zh-CN.json"],
        read_set=[],
        expected_artifacts=["assets/resources/localization/zh-CN.json"],
        evidence_requirements=["assets/resources/localization/zh-CN.json"],
        acceptance_criteria=["readable Chinese"],
        blocking_conditions=["player_visible_chinese_mojibake_detected"],
        model_guidance=[],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    materialized = _materialize_task_card(card, project_dir=project_dir, pipeline_id=card.run_id)
    validation = _task_card_artifact_validation(card, materialized=materialized, project_dir=project_dir)

    assert validation["go"] is False
    assert "player_visible_chinese_mojibake_detected" in validation["blockers"]
    assert localization_path.as_posix() in validation["mojibake_json_artifacts"]


def test_task_card_artifact_validation_accepts_json_pointer_references(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import (
        _materialize_task_card,
        _task_card_artifact_validation,
    )

    project_dir = tmp_path / "cocos_project"
    manifest_path = project_dir / "assets" / "resources" / "commercial_assets" / "art" / "art_direction_manifest.json"
    feature_path = project_dir / "workflow_commercial_feature_evidence.json"
    manifest_path.parent.mkdir(parents=True)
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    feature_path.write_text(
        json.dumps({"asset_graph": {"nodes": []}, "requirement_coverage_trace": []}),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "commercial_art_direction_manifest_v1",
                "evidence": {
                    "asset_graph": "workflow_commercial_feature_evidence.json#/asset_graph",
                    "requirements": "workflow_commercial_feature_evidence.json#/requirement_coverage_trace",
                },
            }
        ),
        encoding="utf-8",
    )
    card = TaskCard(
        run_id="pipeline_artifact_check",
        task_card_id="tc_art",
        title="Art evidence",
        description="JSON pointer references should resolve inside existing evidence files.",
        goal="Create art evidence.",
        write_set=["assets/resources/commercial_assets/art/art_direction_manifest.json"],
        read_set=[],
        expected_artifacts=["assets/resources/commercial_assets/art/art_direction_manifest.json"],
        evidence_requirements=["assets/resources/commercial_assets/art/art_direction_manifest.json"],
        acceptance_criteria=["json pointers resolve"],
        blocking_conditions=["referenced_artifact_missing"],
        model_guidance=[],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    materialized = _materialize_task_card(card, project_dir=project_dir, pipeline_id=card.run_id)
    validation = _task_card_artifact_validation(card, materialized=materialized, project_dir=project_dir)

    assert validation["go"] is True
    assert validation["referenced_missing_artifacts"] == []


def test_task_card_artifact_validation_rejects_mojibake_art_tokens(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import (
        _materialize_task_card,
        _task_card_artifact_validation,
    )

    project_dir = tmp_path / "cocos_project"
    tokens_path = project_dir / "assets" / "resources" / "commercial_assets" / "art" / "feedback_text_tokens.json"
    tokens_path.parent.mkdir(parents=True)
    tokens_path.write_text(
        json.dumps({"tokens": [{"id": "score", "text_zh": "寰楀垎"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    card = TaskCard(
        run_id="pipeline_artifact_check",
        task_card_id="tc_art",
        title="Art tokens",
        description="Player-visible art feedback tokens must be readable Chinese.",
        goal="Create art token evidence.",
        write_set=["assets/resources/commercial_assets/art/feedback_text_tokens.json"],
        read_set=[],
        expected_artifacts=["assets/resources/commercial_assets/art/feedback_text_tokens.json"],
        evidence_requirements=["assets/resources/commercial_assets/art/feedback_text_tokens.json"],
        acceptance_criteria=["readable Chinese feedback tokens"],
        blocking_conditions=["player_visible_chinese_mojibake_detected"],
        model_guidance=[],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    materialized = _materialize_task_card(card, project_dir=project_dir, pipeline_id=card.run_id)
    validation = _task_card_artifact_validation(card, materialized=materialized, project_dir=project_dir)

    assert validation["go"] is False
    assert "player_visible_chinese_mojibake_detected" in validation["blockers"]
    assert tokens_path.as_posix() in validation["mojibake_json_artifacts"]


def test_task_card_artifact_validation_allows_forbidden_mojibake_marker_metadata(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import (
        _materialize_task_card,
        _task_card_artifact_validation,
    )

    project_dir = tmp_path / "cocos_project"
    tokens_path = project_dir / "assets" / "resources" / "commercial_assets" / "art" / "feedback_text_tokens.json"
    tokens_path.parent.mkdir(parents=True)
    tokens_path.write_text(
        json.dumps(
            {
                "tokens": [{"id": "score", "text_zh": "得分"}],
                "readability_checks": {"forbidden_garbled_sequences": ["锟斤拷", "�"]},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    card = TaskCard(
        run_id="pipeline_artifact_check",
        task_card_id="tc_art",
        title="Art tokens",
        description="Mojibake marker metadata is not player-visible text.",
        goal="Create art token evidence.",
        write_set=["assets/resources/commercial_assets/art/feedback_text_tokens.json"],
        read_set=[],
        expected_artifacts=["assets/resources/commercial_assets/art/feedback_text_tokens.json"],
        evidence_requirements=["assets/resources/commercial_assets/art/feedback_text_tokens.json"],
        acceptance_criteria=["readable Chinese feedback tokens"],
        blocking_conditions=["player_visible_chinese_mojibake_detected"],
        model_guidance=[],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    materialized = _materialize_task_card(card, project_dir=project_dir, pipeline_id=card.run_id)
    validation = _task_card_artifact_validation(card, materialized=materialized, project_dir=project_dir)

    assert validation["go"] is True
    assert validation["mojibake_json_artifacts"] == []


def test_task_card_artifact_validation_defers_pending_browser_screenshots(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import (
        _materialize_task_card,
        _task_card_artifact_validation,
    )

    project_dir = tmp_path / "cocos_project"
    evidence_path = project_dir / "workflow_runtime_evidence" / "feedback_animation_evidence.json"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text(
        json.dumps(
            {
                "schema_version": "feedback_animation_evidence_v1",
                "vision_review_screenshots": {
                    "paths": ["workflow_runtime_evidence/screenshots/line_clear_combo_feedback.png"],
                    "status": "pending_runtime_capture",
                },
            }
        ),
        encoding="utf-8",
    )
    card = TaskCard(
        run_id="pipeline_artifact_check",
        task_card_id="tc_art",
        title="Art binding",
        description="Art evidence can defer screenshots to browser playtest.",
        goal="Create art evidence.",
        write_set=["workflow_runtime_evidence/feedback_animation_evidence.json"],
        read_set=[],
        expected_artifacts=["workflow_runtime_evidence/feedback_animation_evidence.json"],
        evidence_requirements=["workflow_runtime_evidence/feedback_animation_evidence.json"],
        acceptance_criteria=["browser screenshots are captured by later playtest"],
        blocking_conditions=["referenced_artifact_missing"],
        model_guidance=[],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    materialized = _materialize_task_card(card, project_dir=project_dir, pipeline_id=card.run_id)
    validation = _task_card_artifact_validation(card, materialized=materialized, project_dir=project_dir)

    assert validation["go"] is True
    assert validation["referenced_missing_artifacts"] == []


def test_task_card_artifact_validation_defers_runtime_capture_contract_screenshots(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import (
        _materialize_task_card,
        _task_card_artifact_validation,
    )

    project_dir = tmp_path / "cocos_project"
    evidence_path = project_dir / "workflow_runtime_evidence" / "player_visible_screenshots.json"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text(
        json.dumps(
            {
                "schema_version": "player_visible_screenshots_contract_v1",
                "screenshots": [
                    {
                        "id": "drag_follow_anti_occlusion",
                        "evidence_path": "workflow_runtime_evidence/screenshots/drag_follow_anti_occlusion.png",
                        "acceptance": {"status": "contract_bound"},
                    }
                ],
                "quality_gate_notes": {"evidence_is_contract_until_runner_capture": True},
            }
        ),
        encoding="utf-8",
    )
    card = TaskCard(
        run_id="pipeline_artifact_check",
        task_card_id="tc_input_feedback",
        title="Input feedback",
        description="Screenshot capture contract is fulfilled by later browser playtest.",
        goal="Create screenshot capture contract.",
        write_set=["workflow_runtime_evidence/player_visible_screenshots.json"],
        read_set=[],
        expected_artifacts=["workflow_runtime_evidence/player_visible_screenshots.json"],
        evidence_requirements=["workflow_runtime_evidence/player_visible_screenshots.json"],
        acceptance_criteria=["browser screenshots are captured by later playtest"],
        blocking_conditions=["referenced_artifact_missing"],
        model_guidance=[],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    materialized = _materialize_task_card(card, project_dir=project_dir, pipeline_id=card.run_id)
    validation = _task_card_artifact_validation(card, materialized=materialized, project_dir=project_dir)

    assert validation["go"] is True
    assert validation["referenced_missing_artifacts"] == []


def test_task_card_artifact_validation_defers_runner_capture_target_screenshots(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import (
        _materialize_task_card,
        _task_card_artifact_validation,
    )

    project_dir = tmp_path / "cocos_project"
    evidence_path = project_dir / "workflow_runtime_evidence" / "feedback_animation_evidence.json"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text(
        json.dumps(
            {
                "schema_version": "feedback_animation_evidence_v1",
                "vision_review_screenshots": {
                    "expected_capture_paths": [
                        "workflow_runtime_evidence/screenshots/line_clear_combo_mobile_portrait.png"
                    ],
                    "review_contract": {"feedback_text_not_overlapping_board_or_tray": True},
                },
            }
        ),
        encoding="utf-8",
    )
    card = TaskCard(
        run_id="pipeline_artifact_check",
        task_card_id="tc_art",
        title="Art evidence",
        description="Art screenshot targets are captured by the later runner.",
        goal="Create art evidence.",
        write_set=["workflow_runtime_evidence/feedback_animation_evidence.json"],
        read_set=[],
        expected_artifacts=["workflow_runtime_evidence/feedback_animation_evidence.json"],
        evidence_requirements=["workflow_runtime_evidence/feedback_animation_evidence.json"],
        acceptance_criteria=["runner captures screenshots later"],
        blocking_conditions=["referenced_artifact_missing"],
        model_guidance=[],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    materialized = _materialize_task_card(card, project_dir=project_dir, pipeline_id=card.run_id)
    validation = _task_card_artifact_validation(card, materialized=materialized, project_dir=project_dir)

    assert validation["go"] is True
    assert validation["referenced_missing_artifacts"] == []


def test_task_card_artifact_validation_ignores_prose_path_mentions(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import (
        _materialize_task_card,
        _task_card_artifact_validation,
    )

    project_dir = tmp_path / "cocos_project"
    evidence_path = project_dir / "workflow_runtime_evidence" / "input_feedback_trace.json"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text(
        json.dumps(
            {
                "schema_version": "input_feedback_trace_v1",
                "scene_source": "workflow_runtime_evidence/scene_prefab_binding_evidence.json and settings/v2/packages/scene.json",
            }
        ),
        encoding="utf-8",
    )
    card = TaskCard(
        run_id="pipeline_artifact_check",
        task_card_id="tc_input_feedback",
        title="Input feedback",
        description="Prose mentions of two paths are not artifact references.",
        goal="Create input evidence.",
        write_set=["workflow_runtime_evidence/input_feedback_trace.json"],
        read_set=[],
        expected_artifacts=["workflow_runtime_evidence/input_feedback_trace.json"],
        evidence_requirements=["workflow_runtime_evidence/input_feedback_trace.json"],
        acceptance_criteria=[],
        blocking_conditions=["referenced_artifact_missing"],
        model_guidance=[],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
    )

    materialized = _materialize_task_card(card, project_dir=project_dir, pipeline_id=card.run_id)
    validation = _task_card_artifact_validation(card, materialized=materialized, project_dir=project_dir)

    assert validation["go"] is True
    assert validation["referenced_missing_artifacts"] == []


def test_task_card_retry_context_includes_artifact_validation_details(tmp_path: Path) -> None:
    from packages.contributions.pipelines.commercial_game_task_worker import _task_card_path_with_retry_context

    card_path = tmp_path / "task.md"
    card_path.write_text("# Bind input\n", encoding="utf-8")

    retry_path = _task_card_path_with_retry_context(
        card_path,
        attempt_index=2,
        prior_entry={
            "artifact_validation": {
                "go": False,
                "blockers": ["referenced_artifact_missing"],
                "invalid_json_reasons": [
                    {
                        "path": "D:/game/workflow_runtime_evidence/machine_gate_repair_evidence.json",
                        "reason": "multiple_top_level_json_documents",
                        "json_document_count": 2,
                    }
                ],
                "referenced_missing_artifacts": ["D:/game/assets/scene/WorkflowCommercialGame.scene"],
            }
        },
    )

    assert retry_path != card_path
    text = retry_path.read_text(encoding="utf-8")
    assert "Previous Artifact Validation Failure" in text
    assert "WorkflowCommercialGame.scene" in text
    assert "settings/v2/packages/scene.json" in text
    assert "multiple_top_level_json_documents" in text
    assert "do not append a second JSON object" in text
    assert "do not emit a delete-plus-add diff" in text


def test_resume_task_card_markdown_preserves_artifact_requirements(tmp_path: Path) -> None:
    from packages.contributions.pipelines.commercial_game_task_card_resume import _task_card_from_markdown

    card_path = tmp_path / "machine_repair.md"
    card_path.write_text(
        "# Repair Cocos build\n\n"
        "## Goal\n\n"
        "Repair the same Cocos project.\n\n"
        "## Acceptance Criteria\n\n"
        "- next machine gate passes\n\n"
        "## Evidence Requirements\n\n"
        "- fresh_worker_receipt\n"
        "- workflow_runtime_evidence/machine_gate_repair_evidence.json\n\n"
        "## Blocking Conditions\n\n"
        "- invalid_json_artifact\n\n"
        "## Model Guidance\n\n"
        "- update JSON in place as one document\n",
        encoding="utf-8",
    )

    card = _task_card_from_markdown(
        card_path,
        pipeline_id="pipeline_resume",
        task_card_ref="tc_resume",
        adapter="codex",
        execution_visibility_mode="human_visible_cli_enforced",
        write_set=["D:/game/workflow_runtime_evidence/**"],
        read_set=[],
        test_commands=[],
    )

    assert card.goal == "Repair the same Cocos project."
    assert "workflow_runtime_evidence/machine_gate_repair_evidence.json" in card.evidence_requirements
    assert "workflow_runtime_evidence/machine_gate_repair_evidence.json" in card.expected_artifacts
    assert card.metadata["human_visible_cli_required"] is True


def test_resume_same_project_task_card_retries_invalid_artifacts(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import resume_same_project_task_card

    project_dir = tmp_path / "cocos_project"
    evidence_path = project_dir / "workflow_runtime_evidence" / "generic_invalid_evidence.json"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text('{"first": true}\n{"second": true}\n', encoding="utf-8")
    card_path = tmp_path / "machine_repair.md"
    card_path.write_text("# Repair Cocos build\n", encoding="utf-8")
    card = TaskCard(
        run_id="pipeline_resume_retry",
        task_card_id="tc_resume_retry",
        title="Repair Cocos build",
        description="Repair invalid machine evidence.",
        goal="Repair invalid machine evidence.",
        write_set=[(project_dir / "workflow_runtime_evidence" / "**").as_posix()],
        read_set=[],
        test_commands=[],
        expected_artifacts=["workflow_runtime_evidence/generic_invalid_evidence.json"],
        evidence_requirements=["workflow_runtime_evidence/generic_invalid_evidence.json"],
        acceptance_criteria=["artifact validation passes"],
        blocking_conditions=["expected_json_artifact_invalid"],
        model_guidance=["update JSON in place as one document"],
        execution_mode="same_project_patch",
        provider_lane="codex",
        risk_level="high",
    )
    seen_task_card_texts: list[str] = []

    def _runner(**kwargs):
        seen_task_card_texts.append(Path(kwargs["task_card_path"]).read_text(encoding="utf-8"))
        attempt_no = len(seen_task_card_texts)
        if attempt_no == 2:
            evidence_path.write_text('{"go": true}\n', encoding="utf-8")
        return {
            "status": "completed",
            "receipt_id": f"receipt_{attempt_no}",
            "child_run_id": f"run_{attempt_no}",
            "child_attempt_id": f"attempt_{attempt_no}",
            "worker_adapter": "codex",
            "mutation_result": {
                "changed_files": [evidence_path.as_posix()],
                "final_test_status": "passed",
                "applied_patch_hash": f"hash_{attempt_no}",
            },
            "changed_files": [evidence_path.as_posix()],
            "final_test_status": "passed",
            "review_decision": "pass",
            "evidence_id": f"evidence_{attempt_no}",
        }

    result = resume_same_project_task_card(
        root=tmp_path,
        db_path=tmp_path / "workflow.db",
        project_dir=project_dir,
        pipeline_id="pipeline_resume_retry",
        task_card=card,
        task_card_path=card_path,
        write_set=card.write_set,
        read_set=[],
        test_commands=[],
        max_fix_iterations=1,
        adapter_name="codex",
        execution_visibility_mode=None,
        task_card_runner=_runner,
    )

    assert result["status"] == "completed"
    assert result["artifact_validation"]["go"] is True
    assert len(seen_task_card_texts) == 2
    assert "Previous Artifact Validation Failure" in seen_task_card_texts[1]
    assert "expected_json_artifact_invalid" in seen_task_card_texts[1]


def test_resume_same_project_task_card_repairs_machine_gate_json_artifact_deterministically(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import resume_same_project_task_card

    project_dir = tmp_path / "cocos_project"
    evidence_path = project_dir / "workflow_runtime_evidence" / "machine_gate_repair_evidence.json"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text('{"first": true}\n{"second": true}\n', encoding="utf-8")
    card_path = tmp_path / "machine_repair.md"
    card_path.write_text("# Repair Cocos build\n", encoding="utf-8")
    card = TaskCard(
        run_id="pipeline_deterministic_json_repair",
        task_card_id="tc_machine_gate_json_repair",
        title="Repair Cocos build",
        description="Repair invalid machine evidence.",
        goal="Repair invalid machine evidence.",
        write_set=[(project_dir / "workflow_runtime_evidence" / "**").as_posix()],
        read_set=[],
        test_commands=["python -m pytest tests/test_commercial_game_evidence_contracts.py -q"],
        expected_artifacts=["workflow_runtime_evidence/machine_gate_repair_evidence.json"],
        evidence_requirements=["workflow_runtime_evidence/machine_gate_repair_evidence.json"],
        acceptance_criteria=["artifact validation passes"],
        blocking_conditions=["expected_json_artifact_invalid"],
        model_guidance=["update JSON in place as one document"],
        execution_mode="same_project_patch",
        provider_lane="codex",
        risk_level="high",
    )
    seen_task_card_texts: list[str] = []

    def _runner(**kwargs):
        seen_task_card_texts.append(Path(kwargs["task_card_path"]).read_text(encoding="utf-8"))
        return {
            "status": "completed",
            "receipt_id": "receipt_1",
            "child_run_id": "run_1",
            "child_attempt_id": "attempt_1",
            "worker_adapter": "codex",
            "mutation_result": {
                "changed_files": [evidence_path.as_posix()],
                "final_test_status": "passed",
                "applied_patch_hash": "hash_1",
            },
            "changed_files": [evidence_path.as_posix()],
            "final_test_status": "passed",
            "review_decision": "pass",
            "evidence_id": "evidence_1",
        }

    result = resume_same_project_task_card(
        root=tmp_path,
        db_path=tmp_path / "workflow.db",
        project_dir=project_dir,
        pipeline_id="pipeline_deterministic_json_repair",
        task_card=card,
        task_card_path=card_path,
        write_set=card.write_set,
        read_set=[],
        test_commands=card.test_commands,
        max_fix_iterations=1,
        adapter_name="codex",
        execution_visibility_mode=None,
        task_card_runner=_runner,
    )

    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert result["status"] == "completed"
    assert result["artifact_validation"]["go"] is True
    assert result["artifact_validation"]["deterministic_artifact_repair"]["repaired_artifacts"] == [
        evidence_path.resolve().as_posix()
    ]
    assert payload["schema_version"] == "machine_gate_repair_evidence_v2"
    assert payload["artifact_repair"]["method"] == "workflow_deterministic_json_artifact_rewrite"
    assert len(seen_task_card_texts) == 1


def test_resume_same_project_task_card_repairs_cocos_ecosystem_json_append(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import resume_same_project_task_card

    project_dir = tmp_path / "cocos_project"
    evidence_path = project_dir / "workflow_runtime_evidence" / "cocos_ecosystem_bridge_evidence.json"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text(
        '{"schema_version":"cocos_ecosystem_bridge_evidence_v3","ecosystem_integration_go":true}\n'
        '{"schema_version":"legacy_appended_evidence"}\n',
        encoding="utf-8",
    )
    card_path = tmp_path / "machine_repair.md"
    card_path.write_text("# Repair Cocos bridge evidence\n", encoding="utf-8")
    card = TaskCard(
        run_id="pipeline_ecosystem_json_repair",
        task_card_id="tc_ecosystem_json_repair",
        title="Repair Cocos bridge evidence",
        description="Repair invalid ecosystem evidence.",
        goal="Repair invalid ecosystem evidence.",
        write_set=[(project_dir / "workflow_runtime_evidence" / "**").as_posix()],
        read_set=[],
        test_commands=[],
        expected_artifacts=["workflow_runtime_evidence/cocos_ecosystem_bridge_evidence.json"],
        evidence_requirements=["workflow_runtime_evidence/cocos_ecosystem_bridge_evidence.json"],
        acceptance_criteria=["artifact validation passes"],
        blocking_conditions=["expected_json_artifact_invalid"],
        model_guidance=["update JSON in place as one document"],
        execution_mode="same_project_patch",
        provider_lane="codex",
        risk_level="high",
    )

    def _runner(**kwargs):
        return {
            "status": "completed",
            "receipt_id": "receipt_1",
            "child_run_id": "run_1",
            "child_attempt_id": "attempt_1",
            "worker_adapter": "codex",
            "mutation_result": {
                "changed_files": [evidence_path.as_posix()],
                "final_test_status": "passed",
                "applied_patch_hash": "hash_1",
            },
            "changed_files": [evidence_path.as_posix()],
            "final_test_status": "passed",
            "review_decision": "pass",
            "evidence_id": "evidence_1",
        }

    result = resume_same_project_task_card(
        root=tmp_path,
        db_path=tmp_path / "workflow.db",
        project_dir=project_dir,
        pipeline_id="pipeline_ecosystem_json_repair",
        task_card=card,
        task_card_path=card_path,
        write_set=card.write_set,
        read_set=[],
        test_commands=[],
        max_fix_iterations=1,
        adapter_name="codex",
        execution_visibility_mode=None,
        task_card_runner=_runner,
    )

    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert result["status"] == "completed"
    assert result["artifact_validation"]["go"] is True
    assert result["artifact_validation"]["deterministic_artifact_repair"]["repaired_artifacts"] == [
        evidence_path.resolve().as_posix()
    ]
    assert payload["schema_version"] == "cocos_ecosystem_bridge_evidence_v3"
    assert payload["artifact_repair"]["method"] == "workflow_first_valid_json_document_rewrite"


def test_task_card_attempt_record_includes_artifact_validation_details() -> None:
    from packages.contributions.pipelines.commercial_game_task_worker import _patch_attempt_record

    validation = {
        "go": False,
        "blockers": ["expected_artifact_missing"],
        "missing_artifacts": ["D:/game/workflow_runtime_evidence/audio_feedback_polish_evidence.json"],
    }

    record = _patch_attempt_record(
        entry={
            "status": "failed",
            "failure_class": "task_card_expected_artifacts_missing",
            "artifact_validation": validation,
            "mutation_result": {"changed_files": ["assets/scripts/runtime/audio/CommercialAudioRuntime.ts"]},
            "final_test_status": "passed",
        },
        attempt_index=1,
        max_attempts=3,
        continuation_argv=["workflowctl", "run"],
    )

    assert record["artifact_validation"] == validation
    assert record["changed_files"] == ["assets/scripts/runtime/audio/CommercialAudioRuntime.ts"]


def test_same_project_patch_ledger_accepts_visible_cli_session_metadata(tmp_path: Path) -> None:
    from packages.contracts import TaskCard
    from packages.contributions.pipelines.commercial_game_task_worker import execute_same_project_task_cards

    card = TaskCard(
        run_id="pipeline_visible_ok",
        task_card_id="tc_visible_ok",
        title="Visible commercial patch",
        description="High-risk commercial task card records visible terminal metadata.",
        goal="High-risk commercial task card records visible terminal metadata.",
        write_set=["state/pipeline_runs/<run>/cocos_project/assets/scripts"],
        read_set=["brief.md"],
        test_commands=["python -m pytest tests/test_commercial_game_evidence_contracts.py -q"],
        acceptance_criteria=["visible session metadata exists", "tests passed"],
        evidence_requirements=["same_project_patch", "human_visible_cli_session"],
        blocking_conditions=["headless_success_claimed"],
        model_guidance=["Use human_visible_cli_enforced."],
        execution_mode="same_project_patch",
        risk_level="high",
        status="active",
        metadata={
            "human_visible_cli_required": True,
            "execution_visibility_mode": "human_visible_cli_enforced",
        },
    )

    def _visible_runner(**_kwargs):
        return {
            "status": "completed",
            "receipt_id": "receipt_visible_ok",
            "child_run_id": "run_visible_ok",
            "child_attempt_id": "attempt_visible_ok",
            "worker_adapter": "codex",
            "mutation_result": {
                "changed_files": ["state/project/assets/scripts/Game.ts"],
                "final_test_status": "passed",
            },
            "watchdog": {"stream_event_count": 3},
            "visible_cli_session": {
                "pid": 4321,
                "argv": ["python", "-m", "apps.operator_cli.main"],
                "cwd": tmp_path.as_posix(),
                "stdout_log_path": (tmp_path / "stdout.log").as_posix(),
                "stderr_log_path": (tmp_path / "stderr.log").as_posix(),
                "stream_log_path": (tmp_path / "stream.jsonl").as_posix(),
                "started_at": "2026-05-03T00:00:00+00:00",
                "status": "completed",
            },
        }

    ledger = execute_same_project_task_cards(
        root=tmp_path,
        run_root=tmp_path / "pipeline_evidence",
        project_dir=tmp_path / "cocos_project",
        pipeline_id="pipeline_visible_ok",
        db_path=tmp_path / "workflow.db",
        task_cards=[card],
        max_repair_attempts=1,
        task_card_runner=_visible_runner,
    )

    entry = ledger["entries"][0]
    assert ledger["same_project_worker_patch_go"] is True
    assert ledger["blockers"] == []
    assert entry["execution_visibility_mode"] == "human_visible_cli_enforced"
    assert entry["visible_cli_session"]["pid"] == 4321
    assert entry["visible_cli_log_paths"]["stdout_log_path"].endswith("stdout.log")


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
            status="active",
        )
    )
    source = tmp_path / "brief.md"
    source.write_text("# 商业小游戏\n必须实现八个不同关卡目标。\n必须有中文 UI 和 BGM。", encoding="utf-8")
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


def test_commercial_worker_blocks_draft_task_card_lifecycle(tmp_path: Path) -> None:
    from packages.contracts import Run, TaskCard
    from packages.contributions.pipelines.commercial_game_production import execute_commercial_game_task_card_worker
    from packages.core_domain.db import migrate
    from packages.core_domain.repositories import RunRepository, TaskRepository

    db_path = tmp_path / "workflow.db"
    pipeline_id = "pipeline_draft_card"
    migrate(db_path)
    RunRepository(db_path).create(Run(run_id=pipeline_id, goal="commercial worker", preset_id="commercial_game_production"))
    TaskRepository(db_path).create_task_card(
        TaskCard(
            run_id=pipeline_id,
            task_card_id="tc_draft_gameplay",
            title="Draft gameplay implementation",
            description="Draft card has enough details but is not active in the DB lifecycle.",
            goal="Draft card has enough details but must not execute until the lifecycle is active.",
            write_set=["state/pipeline_runs/<run>/cocos_project/assets/scripts"],
            read_set=["brief.md"],
            test_commands=["python -m pytest tests/test_task_card_store.py -q"],
            acceptance_criteria=["draft blocks", "runner not called"],
            evidence_requirements=["task_card_lifecycle_no_go"],
            blocking_conditions=["draft_card_executed"],
            model_guidance=["Do not execute this card while it is draft."],
            execution_mode="same_project_patch",
            risk_level="high",
            status="draft",
        )
    )

    def _unexpected_runner(**_kwargs):
        raise AssertionError("draft task card must block before worker execution")

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
        task_card_runner=_unexpected_runner,
    )

    assert payload["status"] == "blocked"
    assert payload["failure_class"] == "task_card_lifecycle_no_go"
    assert payload["output"]["task_card_quality"]["lifecycle_blocked_count"] == 1


def test_commercial_worker_blocks_requirement_coverage_missing(tmp_path: Path) -> None:
    from packages.contracts import Run, TaskCard
    from packages.contributions.pipelines.commercial_game_production import execute_commercial_game_task_card_worker
    from packages.core_domain.db import migrate
    from packages.core_domain.repositories import RunRepository, TaskRepository

    db_path = tmp_path / "workflow.db"
    pipeline_id = "pipeline_requirement_coverage_missing"
    migrate(db_path)
    RunRepository(db_path).create(Run(run_id=pipeline_id, goal="commercial worker", preset_id="commercial_game_production"))
    TaskRepository(db_path).create_task_card(
        TaskCard(
            run_id=pipeline_id,
            task_card_id="tc_gameplay_without_req_ids",
            title="Gameplay implementation without requirement coverage",
            description="Active same-project implementation card is complete except for source requirement coverage.",
            goal="Active same-project implementation card must be blocked when it does not cite covered source requirement IDs.",
            write_set=["state/pipeline_runs/<run>/cocos_project/assets/scripts"],
            read_set=["brief.md"],
            test_commands=["python -m pytest tests/test_task_card_store.py -q"],
            acceptance_criteria=["requirement coverage blocks", "runner not called"],
            evidence_requirements=["requirement_coverage_trace"],
            blocking_conditions=["requirement_coverage_missing"],
            model_guidance=["Do not execute implementation cards without req_id coverage."],
            execution_mode="same_project_patch",
            risk_level="high",
            status="active",
            metadata={"requirement_coverage_required": True},
        )
    )

    def _unexpected_runner(**_kwargs):
        raise AssertionError("missing requirement coverage must block before worker execution")

    payload = execute_commercial_game_task_card_worker(
        root=tmp_path,
        target_dir=tmp_path / "pipeline_evidence",
        shared_outputs={},
        pipeline_id=pipeline_id,
        db_path=db_path,
        source_path=None,
        creator_exe=None,
        output_dir=tmp_path / "cocos_project",
        require_build=False,
        require_playtest=False,
        require_commercial=True,
        task_card_runner=_unexpected_runner,
    )

    quality = payload["output"]["task_card_quality"]
    assert payload["status"] == "blocked"
    assert payload["failure_class"] == "task_card_quality_no_go"
    assert quality["requirement_coverage_blocked_count"] == 1
    assert quality["task_cards"][0]["requirement_coverage_issues"][0]["code"] == "requirement_coverage_missing"


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


def test_commercial_task_worker_cli_parses_last_json_after_visible_progress_noise() -> None:
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    noisy_stdout = "\n".join(
        [
            'python.exe : workflow_progress {"event": "workflow_progress", "run_id": "run_noise"}',
            "NativeCommandError: progress stream was mirrored by the visible PowerShell session",
            '{"run": {"run_id": "run_final"}, "pr_ready_summary": {"ready": true}}',
        ]
    )

    payload = worker_cli._parse_json_from_stdout(noisy_stdout)

    assert payload == {"run": {"run_id": "run_final"}, "pr_ready_summary": {"ready": True}}


def test_commercial_task_worker_cli_reads_utf16_visible_log(tmp_path: Path) -> None:
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    log_path = tmp_path / "stdout.log"
    log_text = (
        '\ufeffpython.exe : workflow_progress {"event": "workflow_progress"}\r\n'
        '{"run": {"run_id": "run_utf16"}, "pr_ready_summary": {"ready": true}}\r\n'
    )
    log_path.write_bytes(log_text.encode("utf-16-le"))

    text = worker_cli._read_log_text(log_path)
    payload = worker_cli._parse_json_from_stdout(text)

    assert payload == {"run": {"run_id": "run_utf16"}, "pr_ready_summary": {"ready": True}}


def test_commercial_task_worker_cli_visible_no_material_progress_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    class _FakeVisibleProcess:
        pid = 4321
        returncode = 124

        def __init__(self, *args, **kwargs):
            self._terminated = False

        def poll(self):
            return self.returncode if self._terminated else None

        def terminate(self):
            self._terminated = True

        def kill(self):
            self._terminated = True

        def wait(self, timeout=None):
            self._terminated = True
            return self.returncode

    ticks = iter([0.0, 13.0, 13.0, 13.0, 13.0])
    db_path = tmp_path / "workflow.db"
    task_goal = "Patch same project from task card: tc_audio"
    _seed_child_workflow_state(db_path, goal=task_goal, receipt_id="receipt_visible", heartbeat_age_seconds=5)

    monkeypatch.setattr(worker_cli.subprocess, "CREATE_NEW_CONSOLE", 0, raising=False)
    monkeypatch.setattr(worker_cli.subprocess, "Popen", _FakeVisibleProcess)
    monkeypatch.setattr(worker_cli, "_terminate_visible_process_tree", lambda proc: proc.terminate())
    monkeypatch.setattr(worker_cli.time, "monotonic", lambda: next(ticks, 13.0))
    monkeypatch.setattr(worker_cli.time, "sleep", lambda _seconds: None)

    result = worker_cli._run_json_command(
        ["python", "-m", "apps.operator_cli.main", "run", "from-task-card"],
        cwd=tmp_path,
        timeout_seconds=900,
        idle_timeout_seconds=240,
        provider_output_idle_timeout_seconds=480,
        material_progress_idle_timeout_seconds=12,
        adaptive_wall_timeout_extension_seconds=900,
        adaptive_wall_timeout_max_extensions=1,
        adaptive_wall_timeout_absolute_max_seconds=1800,
        adaptive_wall_timeout_progress_window_seconds=720,
        db_path=db_path,
        task_goal=task_goal,
        receipt_id="receipt_visible",
        execution_visibility_mode="human_visible_cli_enforced",
        visible_session_dir=tmp_path / "visible",
        visible_session_metadata={"task_card_id": "tc_audio"},
    )

    assert result["status"] == "failed"
    assert result["failure_class"] == "provider_no_material_progress_timeout"
    assert result["watchdog"]["timeout_type"] == "provider_no_material_progress_timeout"
    assert result["watchdog"]["adaptive_wall_timeout_extension_count"] == 0
    assert result["visible_cli_session"]["status"] == "timeout"
    with sqlite3.connect(db_path) as connection:
        run_status = connection.execute("SELECT status FROM runs WHERE run_id = 'child_run_001'").fetchone()[0]
        attempt_status, close_reason = connection.execute(
            "SELECT status, close_reason FROM runtime_attempts WHERE attempt_id = 'attempt_001'"
        ).fetchone()
        lease_status, release_reason = connection.execute(
            "SELECT status, release_reason FROM worker_leases WHERE lease_id = 'lease_001'"
        ).fetchone()
    assert run_status == "failed"
    assert (attempt_status, close_reason) == ("closed", "provider_no_material_progress_timeout")
    assert (lease_status, release_reason) == ("released", "provider_no_material_progress_timeout")


def test_commercial_task_worker_cli_visible_provider_output_defers_material_progress_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    class _FakeVisibleProcess:
        pid = 4321
        returncode = 0

        def __init__(self, *args, **kwargs):
            self._poll_count = 0

        def poll(self):
            self._poll_count += 1
            return None if self._poll_count <= 2 else self.returncode

        def wait(self, timeout=None):
            return self.returncode

    db_path = tmp_path / "workflow.db"
    task_goal = "Patch same project from task card: tc_shop"
    _seed_child_workflow_state(db_path, goal=task_goal, receipt_id="receipt_visible", heartbeat_age_seconds=5)
    ticks = iter([0.0, 0.0, 13.0, 20.0, 20.0, 20.0])
    probe_payloads = iter(
        [
            {"provider_output_event_count": 0, "material_progress_event_count": 0},
            {"provider_output_event_count": 1, "material_progress_event_count": 0},
        ]
    )

    monkeypatch.setattr(worker_cli.subprocess, "CREATE_NEW_CONSOLE", 0, raising=False)
    monkeypatch.setattr(worker_cli.subprocess, "Popen", _FakeVisibleProcess)
    monkeypatch.setattr(worker_cli.time, "monotonic", lambda: next(ticks, 20.0))
    monkeypatch.setattr(worker_cli.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(worker_cli, "_parse_json_from_stdout", lambda _stdout: {"run": {"run_id": "child_run_001"}})
    monkeypatch.setattr(
        worker_cli,
        "_child_provider_activity_probe",
        lambda **_kwargs: lambda: next(
            probe_payloads, {"provider_output_event_count": 1, "material_progress_event_count": 0}
        ),
    )

    result = worker_cli._run_json_command(
        ["python", "-m", "apps.operator_cli.main", "run", "from-task-card"],
        cwd=tmp_path,
        timeout_seconds=900,
        idle_timeout_seconds=240,
        provider_output_idle_timeout_seconds=480,
        material_progress_idle_timeout_seconds=12,
        adaptive_wall_timeout_extension_seconds=900,
        adaptive_wall_timeout_max_extensions=1,
        adaptive_wall_timeout_absolute_max_seconds=1800,
        adaptive_wall_timeout_progress_window_seconds=720,
        db_path=db_path,
        task_goal=task_goal,
        receipt_id="receipt_visible",
        execution_visibility_mode="human_visible_cli_enforced",
        visible_session_dir=tmp_path / "visible",
        visible_session_metadata={"task_card_id": "tc_shop"},
    )

    assert result["status"] == "completed"
    assert result["failure_class"] is None
    assert result["watchdog"]["timeout_type"] is None
    assert result["watchdog"]["provider_output_event_count"] == 1
    assert result["watchdog"]["material_progress_event_count"] == 0
    assert result["visible_cli_session"]["status"] == "completed"


def test_commercial_task_worker_recovers_completed_visible_attempt_after_parser_repair(tmp_path: Path) -> None:
    from packages.contributions.pipelines.commercial_game_task_worker import _prior_completed_patch_entries

    ledger_root = tmp_path / "task_card_worker"
    session_root = ledger_root / "cards" / "visible_cli_sessions" / "tc_core"
    session_root.mkdir(parents=True)
    stdout_path = session_root / "stdout.log"
    log_text = (
        '\ufeffpython.exe : workflow_progress {"event": "workflow_progress"}\r\n'
        '{"run": {"run_id": "run_core"}, "evidence_id": "evidence_core", "review_decision": "pass", '
        '"pr_ready_summary": {"bounded_patch": {"changed_files": ["assets/scripts/Core.ts"], '
        '"applied_patch_hash": "hash_core"}, "tests": {"status": "passed"}}}\r\n'
    )
    stdout_path.write_bytes(log_text.encode("utf-16-le"))
    ledger = {
        "schema_version": "commercial_game_same_project_patch_ledger_v1",
        "entries": [
            {
                "task_card_id": "tc_core",
                "status": "failed",
                "failure_class": "workflowctl_child_json_parse_failed",
                "attempts": [
                    {
                        "status": "failed",
                        "failure_class": "workflowctl_child_json_parse_failed",
                        "receipt_id": "receipt_core",
                        "child_run_id": "run_core",
                        "child_attempt_id": "attempt_core",
                        "worker_adapter": "codex",
                        "execution_visibility_mode": "human_visible_cli_enforced",
                        "visible_cli_session": {
                            "status": "completed",
                            "pid": 1234,
                            "argv": ["workflowctl", "run", "from-task-card"],
                            "cwd": tmp_path.as_posix(),
                            "stdout_log_path": stdout_path.as_posix(),
                            "stderr_log_path": (session_root / "stderr.log").as_posix(),
                            "stream_log_path": (session_root / "stream.jsonl").as_posix(),
                            "started_at": "2026-05-03T00:00:00+00:00",
                            "return_code": 0,
                        },
                    }
                ],
            }
        ],
    }
    (ledger_root / "same_project_patch_ledger.json").write_text(json.dumps(ledger), encoding="utf-8")

    completed = _prior_completed_patch_entries(ledger_root)

    recovered = completed["tc_core"]
    assert recovered["status"] == "completed"
    assert recovered["receipt_id"] == "receipt_core"
    assert recovered["changed_files"] == ["assets/scripts/Core.ts"]
    assert recovered["final_test_status"] == "passed"
    assert recovered["mutation_result"]["recovered_from_visible_cli_log"] is True


def test_commercial_task_worker_cli_classifies_stdout_silence_with_live_db_heartbeat(
    monkeypatch, tmp_path: Path
) -> None:
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    db_path = tmp_path / "workflow.db"
    task_goal = "Patch same project from task card: tc_levels"
    _seed_child_workflow_state(db_path, goal=task_goal, receipt_id="receipt_001", heartbeat_age_seconds=5)

    def _fake_tree_runner(command, cwd, capture_output, text, timeout, idle_timeout, check):
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
        db_path=db_path,
        task_goal=task_goal,
        receipt_id="receipt_001",
    )

    assert result["failure_class"] == "child_stdout_silent"
    assert result["watchdog_source"] == "db_runtime_state"
    assert result["child_run_id"] == "child_run_001"
    assert result["child_workflow_state"]["worker_adapter"] == "codex"
    assert "resume_with_fresh_receipt" in result["recoverable_suggestion"]
    with sqlite3.connect(db_path) as connection:
        run_status = connection.execute("SELECT status FROM runs WHERE run_id = 'child_run_001'").fetchone()[0]
        event_count = connection.execute(
            "SELECT COUNT(*) FROM run_events WHERE event_type = 'watchdog_terminated_without_child_closure'"
        ).fetchone()[0]
    assert run_status == "failed"
    assert event_count == 1


def test_commercial_task_worker_cli_classifies_provider_output_idle_without_fallback_to_stdout_silence(
    monkeypatch, tmp_path: Path
) -> None:
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    db_path = tmp_path / "workflow.db"
    task_goal = "Patch same project from task card: tc_panels"
    _seed_child_workflow_state(db_path, goal=task_goal, receipt_id="receipt_001", heartbeat_age_seconds=5)

    def _fake_tree_runner(
        command,
        cwd,
        capture_output,
        text,
        timeout,
        idle_timeout,
        provider_output_idle_timeout,
        check,
        material_progress_idle_timeout=None,
        env=None,
    ):
        completed = subprocess.CompletedProcess(command, 124, stdout="", stderr="workflow_progress alive\ncommand timed out")
        setattr(completed, "timeout_type", "provider_output_idle_timeout")
        setattr(completed, "stdout_event_count", 0)
        setattr(completed, "stderr_event_count", 1)
        setattr(completed, "stream_event_count", 1)
        setattr(completed, "control_output_event_count", 1)
        setattr(completed, "provider_output_event_count", 0)
        setattr(completed, "last_provider_output_age_seconds", float(provider_output_idle_timeout))
        return completed

    monkeypatch.setattr(worker_cli, "run_subprocess_with_tree_timeout", _fake_tree_runner)

    result = worker_cli._run_json_command(
        ["python", "-m", "apps.operator_cli.main", "run", "from-task-card"],
        cwd=tmp_path,
        timeout_seconds=900,
        idle_timeout_seconds=240,
        provider_output_idle_timeout_seconds=480,
        material_progress_idle_timeout_seconds=720,
        db_path=db_path,
        task_goal=task_goal,
        receipt_id="receipt_001",
    )

    assert result["failure_class"] == "provider_output_idle_timeout"
    assert result["watchdog"]["timeout_type"] == "provider_output_idle_timeout"
    assert result["watchdog"]["control_output_event_count"] == 1
    assert result["watchdog_source"] == "db_runtime_state"


def test_commercial_task_worker_cli_closes_stalled_child_run(monkeypatch, tmp_path: Path) -> None:
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    db_path = tmp_path / "workflow.db"
    task_goal = "Patch same project from task card: tc_levels"
    _seed_child_workflow_state(db_path, goal=task_goal, receipt_id="receipt_001", heartbeat_age_seconds=600)

    def _fake_tree_runner(command, cwd, capture_output, text, timeout, idle_timeout, check):
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
        db_path=db_path,
        task_goal=task_goal,
        receipt_id="receipt_001",
    )

    assert result["failure_class"] == "workflow_child_stalled"
    assert result["child_attempt_id"] == "attempt_001"
    with sqlite3.connect(db_path) as connection:
        attempt_status, close_reason = connection.execute(
            "SELECT status, close_reason FROM runtime_attempts WHERE attempt_id = 'attempt_001'"
        ).fetchone()
        lease_status, release_reason = connection.execute(
            "SELECT status, release_reason FROM worker_leases WHERE lease_id = 'lease_001'"
        ).fetchone()
    assert (attempt_status, close_reason) == ("closed", "workflow_child_stalled")
    assert (lease_status, release_reason) == ("released", "workflow_child_stalled")


def test_commercial_task_worker_cli_closes_nested_child_runs_after_outer_timeout(
    monkeypatch, tmp_path: Path
) -> None:
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    db_path = tmp_path / "workflow.db"
    task_goal = "Patch same project from task card: tc_shop"
    _seed_child_workflow_state(db_path, goal=task_goal, receipt_id="receipt_001", heartbeat_age_seconds=5)
    now = datetime.now(UTC)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "INSERT INTO runs (run_id, goal, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (
                "nested_run_001",
                f"Implement the primary delivery slice for: {task_goal}",
                "running",
                (now - timedelta(seconds=20)).isoformat(),
                (now - timedelta(seconds=20)).isoformat(),
            ),
        )
        connection.execute(
            """
            INSERT INTO runtime_attempts (
              attempt_id, run_id, runtime_task_id, status, created_at, closed_at, close_reason, sequence_no
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("nested_attempt_001", "nested_run_001", "nested_task_001", "current", now.isoformat(), None, None, 1),
        )
        connection.execute(
            """
            INSERT INTO worker_leases (
              lease_id, run_id, adapter_name, status, heartbeat_at, lease_expires_at, released_at, release_reason, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "nested_lease_001",
                "nested_run_001",
                "codex",
                "active",
                (now - timedelta(seconds=5)).isoformat(),
                (now + timedelta(seconds=300)).isoformat(),
                None,
                None,
                now.isoformat(),
            ),
        )
        connection.commit()

    def _fake_tree_runner(command, cwd, capture_output, text, timeout, idle_timeout, check, env=None):
        completed = subprocess.CompletedProcess(command, 124, stdout="", stderr="command timed out after 900s (wall_timeout)")
        setattr(completed, "timeout_type", "wall_timeout")
        setattr(completed, "timeout_failure_class", "provider_wall_timeout")
        setattr(completed, "stdout_event_count", 0)
        setattr(completed, "stderr_event_count", 1)
        setattr(completed, "stream_event_count", 1)
        setattr(completed, "last_output_age_seconds", 0.0)
        return completed

    monkeypatch.setattr(worker_cli, "run_subprocess_with_tree_timeout", _fake_tree_runner)

    result = worker_cli._run_json_command(
        ["python", "-m", "apps.operator_cli.main", "run", "from-task-card"],
        cwd=tmp_path,
        timeout_seconds=900,
        idle_timeout_seconds=240,
        db_path=db_path,
        task_goal=task_goal,
        receipt_id="receipt_001",
        env_overrides={"WORKFLOW_CODEX_TIMEOUT_SECONDS": "900"},
    )

    assert result["failure_class"] == "provider_timeout"
    nested_state = result["child_workflow_state"]["nested_child_states"][0]
    assert nested_state["run_id"] == "nested_run_001"
    with sqlite3.connect(db_path) as connection:
        nested_run_status = connection.execute("SELECT status FROM runs WHERE run_id = 'nested_run_001'").fetchone()[0]
        nested_attempt_status, nested_close_reason = connection.execute(
            "SELECT status, close_reason FROM runtime_attempts WHERE attempt_id = 'nested_attempt_001'"
        ).fetchone()
        nested_lease_status, nested_release_reason = connection.execute(
            "SELECT status, release_reason FROM worker_leases WHERE lease_id = 'nested_lease_001'"
        ).fetchone()
    assert nested_run_status == "failed"
    assert (nested_attempt_status, nested_close_reason) == ("closed", "provider_timeout")
    assert (nested_lease_status, nested_release_reason) == ("released", "provider_timeout")


def test_commercial_task_worker_cli_classifies_adaptive_wall_timeout_exhaustion(
    monkeypatch, tmp_path: Path
) -> None:
    from packages.contributions.pipelines import commercial_game_task_worker_cli as worker_cli

    db_path = tmp_path / "workflow.db"
    task_goal = "Patch same project from task card: tc_panels"
    _seed_child_workflow_state(db_path, goal=task_goal, receipt_id="receipt_001", heartbeat_age_seconds=5)

    def _fake_tree_runner(
        command,
        cwd,
        capture_output,
        text,
        timeout,
        idle_timeout,
        check,
        provider_output_idle_timeout=None,
        material_progress_idle_timeout=None,
        adaptive_wall_timeout_extension=None,
        adaptive_wall_timeout_max_extensions=None,
        adaptive_wall_timeout_absolute_max=None,
        adaptive_wall_timeout_progress_window=None,
        adaptive_wall_timeout_requires_material_progress=None,
        activity_probe=None,
        activity_probe_interval=None,
        env=None,
    ):
        completed = subprocess.CompletedProcess(
            command,
            124,
            stdout="",
            stderr="command timed out after 1800s (adaptive_wall_timeout_exhausted)",
        )
        setattr(completed, "timeout_type", "adaptive_wall_timeout_exhausted")
        setattr(completed, "stdout_event_count", 0)
        setattr(completed, "stderr_event_count", 30)
        setattr(completed, "stream_event_count", 30)
        setattr(completed, "provider_output_event_count", 25)
        setattr(completed, "material_progress_event_count", 4)
        setattr(completed, "adaptive_wall_timeout_extension_count", 1)
        setattr(completed, "adaptive_wall_timeout_effective_seconds", 1800)
        setattr(completed, "adaptive_wall_timeout_absolute_max_seconds", 1800)
        setattr(completed, "adaptive_wall_timeout_exhausted", True)
        return completed

    monkeypatch.setattr(worker_cli, "run_subprocess_with_tree_timeout", _fake_tree_runner)

    result = worker_cli._run_json_command(
        ["python", "-m", "apps.operator_cli.main", "run", "from-task-card"],
        cwd=tmp_path,
        timeout_seconds=900,
        idle_timeout_seconds=240,
        provider_output_idle_timeout_seconds=480,
        material_progress_idle_timeout_seconds=720,
        adaptive_wall_timeout_extension_seconds=900,
        adaptive_wall_timeout_max_extensions=1,
        adaptive_wall_timeout_absolute_max_seconds=1800,
        adaptive_wall_timeout_progress_window_seconds=720,
        db_path=db_path,
        task_goal=task_goal,
        receipt_id="receipt_001",
    )

    assert result["failure_class"] == "task_scope_too_large_after_adaptive_wall_timeout"
    assert result["watchdog"]["timeout_type"] == "adaptive_wall_timeout_exhausted"
    assert result["watchdog"]["adaptive_wall_timeout_extension_count"] == 1
    assert result["recoverable_suggestion"] == "split_or_narrow_task_after_adaptive_wall_timeout_exhausted"
    with sqlite3.connect(db_path) as connection:
        attempt_status, close_reason = connection.execute(
            "SELECT status, close_reason FROM runtime_attempts WHERE attempt_id = 'attempt_001'"
        ).fetchone()
    assert (attempt_status, close_reason) == (
        "closed",
        "task_scope_too_large_after_adaptive_wall_timeout",
    )


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


def test_commercial_game_repair_packet_classifies_same_project_provider_watchdog() -> None:
    from packages.contributions.pipelines.commercial_game_production import build_supervisor_repair_packets

    packets = build_supervisor_repair_packets(
        structured_output={},
        shared_outputs={
            "commercial_game_production": {
                "commercial_playable_blockers": [
                    "child_stdout_silent_recoverable",
                    "workflow_child_stalled",
                    "provider_timeout_recoverable",
                ]
            }
        },
    )

    assert [packet["failure_class"] for packet in packets] == [
        "child_stdout_silent",
        "workflow_child_stalled",
        "provider_timeout",
    ]
    assert all(packet["repair_mode"] != "same_project_incremental_patch" for packet in packets)


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
