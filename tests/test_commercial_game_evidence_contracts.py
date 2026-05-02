from __future__ import annotations

import json

from infra.scripts.validate_animation_artifact_integrity import validate_animation_artifact_integrity
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
    build_commercial_final_gate_evidence,
    build_product_depth_evidence,
    build_same_project_patch_ledger_contract,
)


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
    assert "semantic_board_state_missing" in evidence["blockers"]
    assert "semantic_placement_trace_missing" in evidence["blockers"]


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
