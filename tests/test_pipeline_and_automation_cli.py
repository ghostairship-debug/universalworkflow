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
                    "feature_coverage": {**product_features, "mobilePortraitUi": True},
                },
                "commercial_feature_coverage": product_features,
                "product_depth_evidence": {
                    "level_goals": [f"goal-{index}" for index in range(8)],
                    "feature_coverage": product_features,
                },
                "gameplay_semantic_evidence": semantic_evidence,
                "product_body_evidence": product_body_evidence,
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
            status="active",
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
        feature_coverage = {
            "mobilePortraitUi": True,
            "audioPlaybackVerified": True,
            "bgmStarted": True,
            "sfxPlaybackVerified": True,
            "volumeToggleUsable": True,
        }
        return {
            "technical_smoke_go": True,
            "production_scaffold_go": False,
            "commercial_playable_go": True,
            "commercial_playable_blockers": [],
            "commercial_feature_coverage": feature_coverage,
            "player_visible_checks": {},
                "manual_player_evidence": {},
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
                "build": {
                "creator_exit_code": 0,
                "fatal_marker_detected": False,
                "artifact_success": True,
                "build_output_path": (tmp_path / "cocos_project" / "build" / "web-mobile").as_posix(),
            },
            "playtest": {
                "passed": True,
                "url": "http://127.0.0.1:3000/index.html",
                "screenshots": ["mobile.png"],
                "console_errors": [],
                "page_errors": [],
                "feature_coverage": feature_coverage,
            },
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
    }
    assert output["build_ledger_go"] is True
    assert output["browser_playtest_ledger_go"] is True
    assert (tmp_path / "cocos_project" / "workflow_project_source.json").exists()


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
        )
    )
    source = tmp_path / "brief.md"
    source.write_text("# commercial game", encoding="utf-8")
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
        "audioPlaybackVerified": True,
        "bgmStarted": True,
        "sfxPlaybackVerified": True,
        "volumeToggleUsable": True,
    }

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
                "feature_coverage": {"mobilePortraitUi": True, **product_features},
            },
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
        json.dumps({"commercial_feature_coverage": {"chineseUiPanelsVisible": True}}),
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
    assert product_depth["go"] is True
    assert product_body["go"] is True
    assert product_body["source"]["baseline_only"] is False
    assert "blocked_by_same_project_worker" not in product_depth["blockers"]
    assert "blocked_by_same_project_worker" not in product_body["blockers"]
    assert "blocked_by_same_project_worker" not in build_ledger["blockers"]
    assert "blocked_by_same_project_worker" not in browser_ledger["blockers"]


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
    assert env_overrides["WORKFLOW_CODEX_IDLE_TIMEOUT_SECONDS"] == "480"
    assert env_overrides["WORKFLOW_OPENCODE_TIMEOUT_SECONDS"] == "1800"
    assert env_overrides["WORKFLOW_OPENCODE_IDLE_TIMEOUT_SECONDS"] == "480"
    assert env_overrides["WORKFLOW_PROVIDER_TIMEOUT_SECONDS"] == "1800"
    assert env_overrides["WORKFLOW_PROVIDER_IDLE_TIMEOUT_SECONDS"] == "480"
    assert env_overrides["WORKFLOW_PROVIDER_OUTPUT_IDLE_TIMEOUT_SECONDS"] == "480"
    assert env_overrides["WORKFLOW_PROVIDER_MATERIAL_PROGRESS_IDLE_TIMEOUT_SECONDS"] == "720"
    assert env_overrides["WORKFLOW_PROVIDER_ADAPTIVE_WALL_TIMEOUT_INITIAL_SECONDS"] == "900"
    assert env_overrides["WORKFLOW_PROVIDER_ADAPTIVE_WALL_TIMEOUT_EXTENSION_SECONDS"] == "900"
    assert env_overrides["WORKFLOW_PROVIDER_ADAPTIVE_WALL_TIMEOUT_MAX_EXTENSIONS"] == "1"
    assert env_overrides["WORKFLOW_PROVIDER_ADAPTIVE_WALL_TIMEOUT_ABSOLUTE_MAX_SECONDS"] == "1800"
    assert calls[1]["kwargs"]["provider_output_idle_timeout_seconds"] == 480
    assert calls[1]["kwargs"]["material_progress_idle_timeout_seconds"] == 720
    assert calls[1]["kwargs"]["adaptive_wall_timeout_extension_seconds"] == 900
    assert calls[1]["kwargs"]["adaptive_wall_timeout_max_extensions"] == 1
    assert calls[1]["kwargs"]["adaptive_wall_timeout_absolute_max_seconds"] == 1800
    assert calls[1]["kwargs"]["adaptive_wall_timeout_progress_window_seconds"] == 720
    assert calls[1]["kwargs"]["execution_visibility_mode"] is None
    assert "shell" not in run_command
    assert "noop" not in run_command


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
    assert run_kwargs["visible_session_dir"].as_posix().endswith("visible_cli_sessions/tc_visible")
    assert run_kwargs["visible_session_metadata"]["receipt_id"] == "receipt_visible"
    assert run_kwargs["visible_session_metadata"]["task_card_id"] == "tc_visible"
    assert worker_cli._powershell_quote_arg("D:\\Universal Agentic workflow\\python.exe") == "'D:\\Universal Agentic workflow\\python.exe'"


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
