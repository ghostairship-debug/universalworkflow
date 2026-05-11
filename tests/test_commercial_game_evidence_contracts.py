from __future__ import annotations

import json

from infra.scripts.validate_animation_artifact_integrity import validate_animation_artifact_integrity
from packages.contributions.games.cocos.no_degradation import evaluate_no_degradation_contract
from packages.contributions.pipelines.commercial_game_development_readiness import (
    build_commercial_game_development_readiness_evidence,
)
from packages.contributions.pipelines.commercial_game_evidence_contracts import (
    BROWSER_PLAYTEST_LEDGER_SCHEMA,
    BUILD_LEDGER_SCHEMA,
    PRODUCT_DEPTH_EVIDENCE_SCHEMA,
    build_gameplay_semantic_evidence,
    build_product_body_evidence,
    build_asset_graph_contract,
    build_browser_playtest_ledger,
    build_build_ledger,
    build_cocos_bridge_evidence_contract,
    build_commercial_final_gate_evidence,
    build_product_depth_evidence,
    build_same_project_patch_ledger_contract,
)


def _passing_ai_surrogate_evidence() -> dict:
    return {
        "workflow_generated_product_go": True,
        "core_loop_playable": True,
        "first_session_flow_go": True,
        "requirement_fidelity_go": True,
        "ai_playtest_modes_run": [
            "scripted_bot",
            "exploratory_bot",
            "persona_agent",
            "vision_reviewer",
            "design_red_team",
            "performance_agent",
            "device_matrix_agent",
            "regression_agent",
        ],
        "area_scores": {
            "requirement_fidelity": 12,
            "core_gameplay_correctness": 14,
            "player_experience": 12,
            "ui_ux_polish": 10,
            "art_direction": 10,
            "audio": 8,
            "input_feel": 10,
            "content_depth": 8,
            "performance": 8,
            "robustness": 8,
        },
        "findings": [],
        "screenshots": ["first.png"],
        "replay_artifacts": ["replay.jsonl"],
        "visual_review_evidence": {
            "visual_go": True,
            "visual_quality_score": 90,
            "screenshots_reviewed": ["first.png"],
            "blockers": [],
        },
        "audio_review_evidence": {
            "audio_go": True,
            "bgm_runtime_verified": True,
            "sfx_runtime_verified": True,
            "mix_go": True,
            "blockers": [],
        },
        "engine_native_product_body": {
            "engine": "cocos",
            "product_body_mode": "engine_native",
            "required_components": ["GameModel"],
            "component_bindings": ["GameModel"],
            "scene_or_prefab_bindings": ["main.scene"],
            "semantic_trace_source": "model_transition",
            "runtime_state_authoritative": True,
            "build_launch_evidence": {"go": True},
        },
    }


def test_build_ledger_rejects_missing_artifact_and_build_output() -> None:
    ledger = build_build_ledger({"creator_exit_code": 0, "fatal_marker_detected": False})

    assert ledger["go"] is False
    assert ledger["status"] == "failed"
    assert "cocos_build_no_artifact_success" in ledger["blockers"]
    assert "cocos_build_output_path_missing" in ledger["blockers"]


def test_build_ledger_accepts_cocos_success_exit_code_36_with_artifact() -> None:
    ledger = build_build_ledger(
        {
            "creator_exit_code": 36,
            "fatal_marker_detected": False,
            "artifact_success": True,
            "build_output_path": "build/web-mobile",
        }
    )

    assert ledger["go"] is True
    assert ledger["status"] == "completed"
    assert "cocos_build_nonzero_exit" not in ledger["blockers"]


def test_browser_playtest_ledger_requires_http_screenshots_mobile_and_no_audio_errors() -> None:
    ledger = build_browser_playtest_ledger(
        {
            "passed": True,
            "url": "http://127.0.0.1:3000/index.html",
            "screenshots": ["shot.png"],
            "console_errors": ["NotSupportedError: media decode failed"],
            "page_errors": [],
            "feature_coverage": {},
        }
    )

    assert ledger["go"] is False
    assert "browser_or_audio_runtime_error" in ledger["blockers"]
    assert "mobile_viewport_evidence_missing" in ledger["blockers"]
    assert "audio_runtime_not_verified" in ledger["blockers"]
    assert "bgm_runtime_not_verified" in ledger["blockers"]
    assert "sfx_runtime_not_verified" in ledger["blockers"]
    assert "volume_toggle_missing" in ledger["blockers"]


def test_browser_playtest_ledger_exposes_missing_runtime_feature_coverage() -> None:
    ledger = build_browser_playtest_ledger(
        {
            "passed": False,
            "url": "http://127.0.0.1:3000/index.html",
            "screenshots": ["mobile.png", "desktop.png"],
            "console_errors": [],
            "page_errors": [],
            "feature_coverage": {
                "mobilePortraitUi": True,
                "nativeCocosUiNodes": True,
            },
            "required_playtest_features": [
                "board10x10",
                "dragPlacement",
                "audioPlaybackVerified",
            ],
            "commercial_playtest_features": [
                "nativeCocosUiNodes",
                "volumeToggleUsable",
            ],
        }
    )

    assert ledger["go"] is False
    assert "browser_required_playtest_features_missing" in ledger["blockers"]
    assert "missing_playtest_feature_board10x10" in ledger["blockers"]
    assert "missing_playtest_feature_dragPlacement" in ledger["blockers"]
    assert "missing_playtest_feature_audioPlaybackVerified" in ledger["blockers"]
    assert "browser_commercial_playtest_features_missing" in ledger["blockers"]
    assert "missing_commercial_feature_volumeToggleUsable" in ledger["blockers"]
    assert ledger["source"]["missing_required_features"] == [
        "board10x10",
        "dragPlacement",
        "audioPlaybackVerified",
    ]
    assert ledger["source"]["missing_commercial_features"] == ["volumeToggleUsable"]


def test_browser_playtest_ledger_blocks_static_canvas_and_desktop_splash() -> None:
    feature_coverage = {
        "mobilePortraitUi": True,
        "audioPlaybackVerified": True,
        "bgmStarted": True,
        "sfxPlaybackVerified": True,
        "volumeToggleUsable": True,
    }
    ledger = build_browser_playtest_ledger(
        {
            "passed": True,
            "url": "http://127.0.0.1:3000/index.html",
            "screenshots": ["mobile.png", "after.png", "desktop.png"],
            "canvas_hashes": ["same", "same"],
            "desktop_runtime_started": False,
            "desktop_splash_detected": True,
            "console_errors": [],
            "page_errors": [],
            "feature_coverage": feature_coverage,
        }
    )

    assert ledger["go"] is False
    assert "browser_canvas_hash_static_after_actions" in ledger["blockers"]
    assert "desktop_cocos_splash_only" in ledger["blockers"]
    assert "desktop_runtime_not_started" in ledger["blockers"]


def test_browser_playtest_ledger_prefers_screenshot_change_over_stale_webgl_canvas_hash() -> None:
    feature_coverage = {
        "mobilePortraitUi": True,
        "audioPlaybackVerified": True,
        "bgmStarted": True,
        "sfxPlaybackVerified": True,
        "volumeToggleUsable": True,
    }
    ledger = build_browser_playtest_ledger(
        {
            "passed": True,
            "url": "http://127.0.0.1:3000/index.html",
            "screenshots": ["mobile.png", "after.png", "desktop.png"],
            "canvas_hashes": ["same", "same"],
            "screenshot_hashes": ["before", "after", "desktop"],
            "desktop_runtime_started": True,
            "desktop_splash_detected": False,
            "console_errors": [],
            "page_errors": [],
            "feature_coverage": feature_coverage,
        }
    )

    assert ledger["go"] is True
    assert "browser_canvas_hash_static_after_actions" not in ledger["blockers"]


def test_contracts_reject_skipped_stubbed_simulated_and_placeholder_dependencies() -> None:
    assert build_asset_graph_contract({"status": "skipped", "commercial_assets_go": True})["go"] is False
    assert build_same_project_patch_ledger_contract({"status": "simulated", "same_project_worker_patch_go": True, "entries": [{"status": "completed"}]})["go"] is False
    assert build_build_ledger({"status": "stubbed", "creator_exit_code": 0, "artifact_success": True, "build_output_path": "build/web-mobile"})["go"] is False
    assert build_browser_playtest_ledger(
        {
            "evidence_mode": "build_only",
            "passed": True,
            "url": "http://x",
            "screenshots": ["x"],
            "feature_coverage": {
                "mobilePortraitUi": True,
                "audioPlaybackVerified": True,
                "bgmStarted": True,
                "sfxPlaybackVerified": True,
                "volumeToggleUsable": True,
            },
        }
    )["go"] is False


def test_cocos_bridge_contract_blocks_report_only_without_fresh_runner() -> None:
    ledger = build_cocos_bridge_evidence_contract(
        {
            "ecosystem_integration_go": True,
            "bridge_mode": "report_only",
            "checks": {
                "assetdb_import_query_evidence": True,
                "scene_create_save_evidence": True,
                "node_component_binding_evidence": True,
                "prefab_create_instantiate_evidence": True,
                "build_api_evidence": True,
            },
            "blockers": [],
        }
    )

    assert ledger["go"] is False
    assert "report_only_bridge_without_fresh_runner" in ledger["blockers"]


def test_same_project_contract_rejects_shell_noop_and_fallback_only_execution() -> None:
    for entry in [
        {"status": "completed", "worker_adapter": "shell"},
        {"status": "completed", "worker_adapter": "noop"},
        {"status": "completed", "fallback_only": True},
        {"status": "completed", "fallback_provider": "opencode", "fallback_provider_live_proof": False},
    ]:
        contract = build_same_project_patch_ledger_contract(
            {"same_project_worker_patch_go": True, "task_card_count": 1, "completed_count": 1, "entries": [entry]}
        )
        assert contract["go"] is False
        assert {"same_project_patch_non_provider_adapter", "fallback_provider_unavailable"} & set(contract["blockers"])


def test_same_project_contract_rejects_existing_same_project_evidence_entries() -> None:
    contract = build_same_project_patch_ledger_contract(
        {
            "same_project_worker_patch_go": True,
            "task_card_count": 1,
            "completed_count": 1,
            "entries": [
                {
                    "status": "completed",
                    "worker_adapter": "existing_same_project_evidence",
                    "satisfaction_mode": "existing_same_project_evidence",
                    "evidence_reuse_real_files": True,
                    "changed_files": ["state/project/assets/scripts/ShopSkinSystem.ts"],
                }
            ],
        }
    )

    assert contract["go"] is False
    assert "fresh_cli_execution_missing" in contract["blockers"]
    assert "same_project_patch_attempts_missing" in contract["blockers"]


def test_same_project_contract_rejects_visible_cli_required_without_session() -> None:
    contract = build_same_project_patch_ledger_contract(
        {
            "same_project_worker_patch_go": True,
            "task_card_count": 1,
            "completed_count": 1,
            "entries": [
                {
                    "status": "completed",
                    "worker_adapter": "codex",
                    "receipt_id": "receipt_visible",
                    "child_run_id": "run_visible",
                    "child_attempt_id": "attempt_visible",
                    "execution_visibility_mode": "human_visible_cli_enforced",
                    "changed_files": ["state/project/assets/scripts/Game.ts"],
                    "mutation_result": {
                        "changed_files": ["state/project/assets/scripts/Game.ts"],
                        "final_test_status": "passed",
                    },
                    "attempts": [{"attempt_index": 1, "receipt_id": "receipt_visible"}],
                }
            ],
        }
    )

    assert contract["go"] is False
    assert "human_visible_cli_metadata_missing" in contract["blockers"]


def test_same_project_contract_rejects_resident_mode_without_direct_provider_session() -> None:
    contract = build_same_project_patch_ledger_contract(
        {
            "same_project_worker_patch_go": True,
            "task_card_count": 1,
            "completed_count": 1,
            "entries": [
                {
                    "status": "completed",
                    "worker_adapter": "codex",
                    "receipt_id": "receipt_visible",
                    "child_run_id": "run_visible",
                    "child_attempt_id": "attempt_visible",
                    "execution_visibility_mode": "human_visible_cli_enforced",
                    "control_plane_visibility": "resident",
                    "provider_visibility": "direct_visible",
                    "provider_visible_cli_required": True,
                    "visible_cli_session": {
                        "pid": 1234,
                        "argv": ["workflowctl", "run", "from-task-card"],
                        "cwd": "D:/Universal Agentic workflow",
                        "stdout_log_path": "stdout.log",
                        "stderr_log_path": "stderr.log",
                        "stream_log_path": "stream.jsonl",
                        "started_at": "2026-05-04T00:00:00+00:00",
                        "status": "completed",
                    },
                    "changed_files": ["state/project/assets/scripts/Game.ts"],
                    "mutation_result": {
                        "changed_files": ["state/project/assets/scripts/Game.ts"],
                        "final_test_status": "passed",
                    },
                    "attempts": [{"attempt_index": 1, "receipt_id": "receipt_visible"}],
                }
            ],
        }
    )

    assert contract["go"] is False
    assert "direct_provider_visible_cli_metadata_missing" in contract["blockers"]


def test_final_gate_reports_upstream_short_circuit_without_product_noise() -> None:
    complete = {"go": True, "blockers": [], "status": "completed", "schema_version": "test", "source": {}}
    patch = {
        "go": False,
        "blockers": ["same_project_task_card_patch_failed", "provider_timeout_recoverable"],
        "status": "failed",
        "schema_version": "test",
        "source": {},
    }
    build = {
        "schema_version": BUILD_LEDGER_SCHEMA,
        "status": "blocked",
        "go": False,
        "blockers": ["blocked_by_same_project_worker"],
        "source": {
            "stage": "cocos_build",
            "skip_reason": "skipped_due_to_upstream_failure",
            "blocked_downstream_stages": [
                "cocos_build",
                "browser_playtest",
                "audio_runtime",
                "product_depth",
                "human_player_review",
            ],
        },
    }
    browser = {
        "schema_version": BROWSER_PLAYTEST_LEDGER_SCHEMA,
        "status": "blocked",
        "go": False,
        "blockers": ["blocked_by_same_project_worker"],
        "source": {"stage": "browser_playtest", "skip_reason": "skipped_due_to_upstream_failure"},
    }
    product = {
        "schema_version": PRODUCT_DEPTH_EVIDENCE_SCHEMA,
        "status": "blocked",
        "go": False,
        "blockers": ["blocked_by_same_project_worker"],
        "source": {"stage": "product_depth", "skip_reason": "skipped_due_to_upstream_failure"},
    }

    gate = build_commercial_final_gate_evidence(
        technical_smoke_go=True,
        production_scaffold_go=False,
        require_commercial=True,
        require_cocos_ecosystem=False,
        require_live_agent_roles=False,
        require_human_player_review=True,
        asset_graph=complete,
        cocos_bridge_evidence=complete,
        same_project_patch_ledger=patch,
        build_ledger=build,
        browser_playtest_ledger=browser,
        product_feature_depth_go=False,
        product_feature_blockers=product["blockers"],
        live_role_provider_proof_go=True,
        human_player_review_go=False,
    )

    assert gate["go_no_go"] == "NO-GO"
    assert "provider_timeout_recoverable" in gate["machine_blockers"]
    assert "blocked_by_same_project_worker" in gate["machine_blockers"]
    assert "levels_not_distinct_or_less_than_eight" not in gate["machine_blockers"]
    assert gate["blocked_downstream_stages"] == [
        "cocos_build",
        "browser_playtest",
        "audio_runtime",
        "product_depth",
        "human_player_review",
    ]


def test_final_gate_can_require_ai_surrogate_playtest_before_human_review() -> None:
    complete = {"go": True, "blockers": [], "status": "completed", "schema_version": "test", "source": {}}

    missing_ai = build_commercial_final_gate_evidence(
        technical_smoke_go=True,
        production_scaffold_go=False,
        require_commercial=True,
        require_cocos_ecosystem=False,
        require_live_agent_roles=False,
        require_human_player_review=True,
        asset_graph=complete,
        cocos_bridge_evidence=complete,
        same_project_patch_ledger=complete,
        build_ledger=complete,
        browser_playtest_ledger=complete,
        product_feature_depth_go=True,
        product_feature_blockers=[],
        live_role_provider_proof_go=True,
        human_player_review_go=False,
        gameplay_semantic_evidence=complete,
        product_body_evidence=complete,
        require_ai_surrogate_playtest=True,
    )

    assert missing_ai["go_no_go"] == "NO-GO"
    assert "ai_surrogate_playtest_missing" in missing_ai["machine_blockers"]

    passing_ai = build_commercial_final_gate_evidence(
        technical_smoke_go=True,
        production_scaffold_go=False,
        require_commercial=True,
        require_cocos_ecosystem=False,
        require_live_agent_roles=False,
        require_human_player_review=True,
        asset_graph=complete,
        cocos_bridge_evidence=complete,
        same_project_patch_ledger=complete,
        build_ledger=complete,
        browser_playtest_ledger=complete,
        product_feature_depth_go=True,
        product_feature_blockers=[],
        live_role_provider_proof_go=True,
        human_player_review_go=False,
        gameplay_semantic_evidence=complete,
        product_body_evidence=complete,
        require_ai_surrogate_playtest=True,
        ai_surrogate_playtest_evidence=_passing_ai_surrogate_evidence(),
    )

    assert passing_ai["machine_evidence_go"] is True
    assert passing_ai["go_no_go"] == "AWAITING_HUMAN_REVIEW"
    assert passing_ai["contracts"]["ai_surrogate_playtest_evidence"]["ai_surrogate_playtest_go"] is True
    assert passing_ai["commercial_playable_go"] is False


def test_final_gate_stops_at_awaiting_human_review_when_machine_evidence_is_complete() -> None:
    complete = {"go": True, "blockers": [], "status": "completed", "schema_version": "test", "source": {}}
    evidence = build_commercial_final_gate_evidence(
        technical_smoke_go=True,
        production_scaffold_go=True,
        require_commercial=True,
        require_cocos_ecosystem=True,
        require_live_agent_roles=True,
        require_human_player_review=True,
        asset_graph=complete,
        cocos_bridge_evidence=complete,
        same_project_patch_ledger=complete,
        build_ledger=complete,
        browser_playtest_ledger=complete,
        product_feature_depth_go=True,
        product_feature_blockers=[],
        live_role_provider_proof_go=True,
        human_player_review_go=False,
        gameplay_semantic_evidence=complete,
        product_body_evidence=complete,
    )

    assert evidence["go_no_go"] == "AWAITING_HUMAN_REVIEW"
    assert evidence["status"] == "blocked"
    assert evidence["machine_evidence_go"] is True
    assert evidence["commercial_playable_go"] is False
    assert evidence["blockers"] == ["awaiting_human_player_review"]


def test_no_degradation_only_requires_live_roles_when_flagged() -> None:
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
        "technical_smoke_go": True,
        "production_scaffold_go": True,
        "commercial_playable_go": False,
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
            "artifact_success": True,
            "fatal_marker_detected": False,
            "build_output_path": "build/web-mobile",
        },
        "playtest": {
            "passed": True,
            "url": "http://127.0.0.1:3000/index.html",
            "screenshots": ["mobile.png"],
            "console_errors": [],
            "page_errors": [],
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
    }
    no_degradation = evaluate_no_degradation_contract(
        shared_outputs={
            "commercial_game_production": production,
            "commercial_game_assets": {
                "commercial_assets_go": True,
                "asset_manifest": {"go_no_go": "GO", "manifest_path": "assets/manifest.json"},
                "commercial_asset_blockers": [],
            },
        },
        production=production,
        require_commercial=True,
        require_live_agent_roles=False,
        require_human_player_review=True,
    )

    assert no_degradation["go_no_go"] == "AWAITING_HUMAN_REVIEW"
    assert no_degradation["machine_evidence_go"] is True
    assert "live_role_provider_proof_missing" not in no_degradation["blockers"]
    assert no_degradation["blockers"] == ["awaiting_human_player_review"]


def test_development_readiness_go_is_separate_from_commercial_playable_go() -> None:
    semantic = build_gameplay_semantic_evidence(
        {
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
            "baseline_only": True,
        }
    )
    product_body = build_product_body_evidence(
        {
            "scene_nodes": ["Canvas", "Board", "CandidateTray"],
            "cocos_component_bindings": ["BoardModel", "RuleEngine", "CandidateTray"],
            "baseline_only": True,
        },
        gameplay_semantic_evidence=semantic,
    )

    readiness = build_commercial_game_development_readiness_evidence(
        task_card_quality={
            "schema_version": "m108_task_card_quality_v2",
            "task_card_count": 3,
            "execution_eligible_count": 3,
            "lifecycle_blocked_count": 0,
            "requirement_coverage_blocked_count": 0,
            "go_no_go": "GO",
        },
        same_project_patch_ledger={
            "schema_version": "commercial_game_same_project_patch_ledger_contract_v1",
            "go": True,
            "blockers": [],
            "source": {},
        },
        gameplay_semantic_evidence=semantic,
        product_body_evidence=product_body,
        product_body_baseline={"baseline_only": True, "commercial_playable_go": False},
        validation_gates={
            "doc_links_go": True,
            "active_truth_go": True,
            "targeted_tests_go": True,
            "full_matrix_go": True,
            "diff_check_go": True,
        },
    )

    assert readiness["commercial_game_development_readiness_go"] is True
    assert readiness["commercial_playable_go"] is False
    assert readiness["baseline_only"] is True
    assert readiness["forbidden_claim"] == "development_readiness_is_not_commercial_playable_completion"


def test_final_gate_rejects_baseline_only_product_body_even_when_other_machine_contracts_pass() -> None:
    complete = {"go": True, "blockers": [], "status": "completed", "schema_version": "test", "source": {}}
    semantic = build_gameplay_semantic_evidence(
        {
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
            "baseline_only": True,
        }
    )
    product_body = build_product_body_evidence(
        {"scene_nodes": ["Canvas"], "cocos_component_bindings": ["BoardModel"], "baseline_only": True},
        gameplay_semantic_evidence=semantic,
    )

    evidence = build_commercial_final_gate_evidence(
        technical_smoke_go=True,
        production_scaffold_go=True,
        require_commercial=True,
        require_cocos_ecosystem=False,
        require_live_agent_roles=False,
        require_human_player_review=False,
        asset_graph=complete,
        cocos_bridge_evidence=complete,
        same_project_patch_ledger=complete,
        build_ledger=complete,
        browser_playtest_ledger=complete,
        product_feature_depth_go=True,
        product_feature_blockers=[],
        live_role_provider_proof_go=False,
        human_player_review_go=False,
        gameplay_semantic_evidence=semantic,
        product_body_evidence=product_body,
    )

    assert evidence["commercial_playable_go"] is False
    assert "baseline_only_cannot_pass_commercial_final_gate" in evidence["machine_blockers"]


def test_development_readiness_blocks_commercial_claim_and_missing_req_id_gate() -> None:
    readiness = build_commercial_game_development_readiness_evidence(
        task_card_quality={"task_card_count": 1, "go_no_go": "GO"},
        same_project_worker_gate_present=True,
        gameplay_semantic_evidence={"go": True, "blockers": [], "source": {}},
        product_body_evidence={"go": True, "blockers": [], "source": {}},
        product_body_baseline={"baseline_only": True, "commercial_playable_go": True},
        commercial_playable_go=True,
        human_player_review_go=False,
    )

    assert readiness["commercial_game_development_readiness_go"] is False
    assert "requirement_coverage_gate_missing" in readiness["blockers"]
    assert "baseline_claimed_as_commercial_playable" in readiness["blockers"]
    assert "commercial_playable_go_claimed_before_human_review" in readiness["blockers"]


def test_product_depth_contract_rejects_event_only_markers() -> None:
    evidence = build_product_depth_evidence(
        product_depth={
            "events": [
                "skin_panel_opened",
                "level_switching_ui_opened",
                "audio_toggle",
                "revive_reward",
            ]
        },
        feature_coverage={},
        player_visible_checks={},
    )

    assert evidence["go"] is False
    assert "event_only_player_visible_evidence" in evidence["blockers"]
    assert "levels_not_distinct_or_less_than_eight" in evidence["blockers"]
    assert "skin_system_not_player_visible" in evidence["blockers"]


def test_gameplay_semantic_contract_rejects_feature_flags_and_events_only() -> None:
    evidence = build_gameplay_semantic_evidence(
        {"events": ["placed_piece", "line_clear"]},
        feature_coverage={"levelFlowPlayable": True},
    )

    assert evidence["go"] is False
    assert "event_only_gameplay_evidence" in evidence["blockers"]
    assert "semantic_model_transition_trace_missing" in evidence["blockers"]


def test_gameplay_semantic_contract_accepts_task_card_transition_examples() -> None:
    evidence = build_gameplay_semantic_evidence(
        {
            "schema_version": "gameplay_semantic_evidence_raw_v1",
            "engine_native_runtime_state": {"board_size": 10, "candidate_batch_size": 3},
            "semantic_trace_contract": {"covered_verbs": ["start_or_retry", "place_block"]},
            "transition_examples": [
                {"verb": "start_or_retry", "events": ["session_started"]},
                {"verb": "place_block", "events": ["candidate_placed", "line_clear_resolved"]},
            ],
        }
    )

    assert evidence["go"] is True
    assert evidence["source"]["board_size"] == 10
    assert set(evidence["source"]["trace_keys"]) >= {"start_or_retry", "place_block", "line_clear_resolved"}


def test_product_body_contract_accepts_implemented_components_and_scene_bindings() -> None:
    semantic = build_gameplay_semantic_evidence(
        {
            "engine_native_runtime_state": {"board_size": 10, "candidate_batch_size": 3},
            "transition_examples": [{"verb": "start_or_retry"}, {"verb": "place_block"}],
        }
    )
    evidence = build_product_body_evidence(
        {
            "schema_version": "product_body_evidence_raw_v1",
            "implemented_components": [
                {"path": "assets/scripts/runtime/model/GameState.ts", "role": "state"},
                {"path": "assets/scripts/runtime/input/Input.ts", "role": "input"},
            ],
            "scene_bindings": [
                {
                    "scene_path": "assets/scene/main.scene",
                    "prefabs": ["assets/prefabs/hud.prefab"],
                    "components": ["GameState", "Input"],
                }
            ],
        },
        gameplay_semantic_evidence=semantic,
    )

    assert evidence["go"] is True
    assert evidence["source"]["component_binding_count"] == 2
    assert evidence["source"]["scene_node_count"] >= 3


def test_gameplay_semantic_contract_rejects_runtime_hook_and_missing_model_transitions() -> None:
    evidence = build_gameplay_semantic_evidence(
        {
            "runtime_phase": True,
            "trace_source": "runtime_hook",
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
    )

    assert evidence["go"] is False
    assert "model_transition_trace_missing" in evidence["blockers"]
    assert "runtime_hook_not_semantic_model" in evidence["blockers"]


def test_product_body_contract_rejects_canvas_runtime_hook_without_components() -> None:
    semantic = build_gameplay_semantic_evidence(
        {
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
    )
    evidence = build_product_body_evidence(
        {"canvas_only": True, "runtime_hook": True, "events": ["button_clicked"]},
        gameplay_semantic_evidence=semantic,
    )

    assert semantic["go"] is True
    assert evidence["go"] is False
    assert "runtime_hook_not_product_body" in evidence["blockers"]
    assert "canvas_only_product_body" in evidence["blockers"]
    assert "cocos_component_binding_missing" in evidence["blockers"]


def test_product_body_contract_rejects_empty_component_shell_for_runtime_body() -> None:
    semantic = build_gameplay_semantic_evidence(
        {
            "runtime_phase": True,
            "trace_source": "model_transition",
            "model_transition_traces": [{"transition": "placement", "before": {}, "after": {}}],
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
    )
    evidence = build_product_body_evidence(
        {
            "scene_nodes": ["Canvas", "Board", "CandidateTray"],
            "cocos_component_bindings": ["BoardModel", "RuleEngine", "CandidateTray"],
            "empty_component_only": True,
            "baseline_only": False,
        },
        gameplay_semantic_evidence=semantic,
    )

    assert semantic["go"] is True
    assert evidence["go"] is False
    assert "empty_component_shell_not_runtime_product_body" in evidence["blockers"]


def test_semantic_and_product_body_contracts_reject_template_leak_against_non_puzzle_spec() -> None:
    spec = {
        "title": "Lantern platformer",
        "requirements": [
            {"req_id": "REQ-1", "normalized_requirement": "Player jumps across platforms with checkpoints."}
        ],
    }
    semantic = build_gameplay_semantic_evidence(
        {
            "game_design_spec": spec,
            "trace_source": "model_transition",
            "model_transition_traces": {"jump": {"before": {"grounded": True}, "after": {"airborne": True}}},
            "semantic_traces": {"jump": "trace/jump.json", "anti_stall": "trace/anti_stall.json"},
        }
    )
    product_body = build_product_body_evidence(
        {
            "game_design_spec": spec,
            "scene_nodes": ["Canvas", "CandidateTray"],
            "cocos_component_bindings": ["PlayerController", "CandidateTray"],
        },
        gameplay_semantic_evidence=semantic,
    )

    assert semantic["go"] is False
    assert product_body["go"] is False
    assert "template_leak_detected" in semantic["blockers"]
    assert "template_leak_detected" in product_body["blockers"]


def test_product_depth_contract_accepts_machine_visible_depth() -> None:
    features = {
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
    evidence = build_product_depth_evidence(
        product_depth={"level_goals": [f"goal-{index}" for index in range(8)]},
        feature_coverage=features,
        player_visible_checks={},
    )

    assert evidence["go"] is True
    assert evidence["blockers"] == []
    assert evidence["source"]["distinct_level_goal_count"] == 8


def test_product_depth_contract_rejects_mojibake_level_goal_labels() -> None:
    features = {
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
    evidence = build_product_depth_evidence(
        product_depth={
            "level_goals": [
                "寰楀垎杈炬爣",
                "娑堣杈炬爣",
                "杩炲嚮娆℃暟",
                "闄愭椂鎸戞垬",
                "鏃犲け璇€氬叧",
                "褰㈢姸澶氭牱鎬",
                "鏁堢巼鍔犳垚",
                "鐢熷瓨濂栧姳",
            ]
        },
        feature_coverage=features,
        player_visible_checks={},
    )

    assert evidence["go"] is False
    assert "level_goal_labels_mojibake" in evidence["blockers"]
    assert evidence["source"]["level_goal_labels_readable"] is False


def test_animation_artifact_integrity_validator_rejects_duplicate_state_and_commercial_go(tmp_path) -> None:
    project = tmp_path / "cocos_project"
    scripts = project / "assets" / "scripts"
    assets = project / "assets" / "resources" / "commercial_assets"
    scripts.mkdir(parents=True)
    assets.mkdir(parents=True)

    valid_state = "\n".join(
        [
            "export type FeedbackAnimationTriggerId = 'onGameStart';",
            "export type FeedbackAnimationClipId = 'anim_game_start_pulse';",
            "export const FEEDBACK_ANIMATION_BINDINGS = [];",
            "export const FEEDBACK_ANIMATION_MANIFEST = [];",
            "export const FEEDBACK_ANIMATION_STATE = {};",
            "export function buildFeedbackAnimationSnapshot() { return {}; }",
        ]
    )
    (scripts / "FeedbackAnimationState.ts").write_text(f"{valid_state}\n{valid_state}\n", encoding="utf-8")
    (assets / "feedback_animation_manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "feedback_animation_manifest_v1",
                "clip_library": [{} for _ in range(8)],
                "trigger_bindings": [{} for _ in range(8)],
                "total_clips": 8,
                "total_bindings": 8,
            }
        ),
        encoding="utf-8",
    )
    (project / "workflow_commercial_feature_evidence.json").write_text(
        json.dumps(
            {
                "animation_feedback_evidence": {
                    "animation_feedback_hooks_configured": True,
                    "hook_binding_count": 8,
                    "clip_count": 8,
                },
                "commercial_playable_go": True,
            }
        ),
        encoding="utf-8",
    )

    issues = validate_animation_artifact_integrity(project)

    assert "unexpected_marker_count:export type FeedbackAnimationTriggerId:2" in issues
    assert "commercial_playable_go_claimed" in issues
