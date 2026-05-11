from __future__ import annotations

from pathlib import Path

from packages.contributions.pipelines.commercial_game_evidence_contracts import (
    build_browser_playtest_ledger,
    build_build_ledger,
    build_gameplay_semantic_evidence,
    build_product_body_evidence,
    build_product_depth_evidence,
)
from packages.contributions.pipelines.commercial_game_task_worker import (
    _collect_ai_surrogate_playtest_evidence,
    production_payload_from_worker,
)


def _product_features() -> dict[str, bool]:
    return {
        "board10x10": True,
        "dragPlacement": True,
        "lineClear": True,
        "refresh": True,
        "mobilePortraitUi": True,
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


def test_runtime_evidence_synthesizes_gate_ready_ai_surrogate_report(tmp_path: Path) -> None:
    project_dir = tmp_path / "cocos_project"
    project_dir.mkdir()
    screenshots = []
    for name in ("initial", "after", "desktop"):
        path = project_dir / "playtest_evidence" / f"{name}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"png")
        screenshots.append(path.as_posix())
    scene = project_dir / "assets" / "scene" / "main.scene"
    scene.parent.mkdir(parents=True, exist_ok=True)
    scene.write_text("{}", encoding="utf-8")

    features = _product_features()
    playtest = {
        "passed": True,
        "url": "http://127.0.0.1:3000/index.html",
        "screenshots": screenshots,
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
        "feature_coverage": features,
        "result_path": (project_dir / "playtest_evidence" / "cocos_playtest_result.json").as_posix(),
    }
    build = {
        "creator_exit_code": 0,
        "fatal_marker_detected": False,
        "artifact_success": True,
        "build_output_path": (project_dir / "build" / "web-mobile").as_posix(),
    }
    build_ledger = build_build_ledger(build)
    browser_ledger = build_browser_playtest_ledger(playtest)
    gameplay = build_gameplay_semantic_evidence(
        {
            "board_state": {"rows": 10, "cols": 10},
            "piece_shapes": [{"cells": [[0, 0]]}],
            "candidate_tray": [{}, {}, {}],
            "semantic_traces": {
                "placement": True,
                "line_clear": True,
                "candidate_refresh": True,
                "game_over": True,
                "anti_stall": True,
            },
            "model_transition_traces": [{"transition": "placement", "before": {}, "after": {}}],
        },
        feature_coverage=features,
        playtest=playtest,
    )
    raw_product_body = {
        "workflow_generated_product_go": True,
        "scene_path": scene.as_posix(),
        "component_bindings": ["BlockPuzzleModel", "BlockPuzzleRuntimeController", "BlockPuzzleInputController"],
        "scene_nodes": ["Canvas", "Board", "CandidateTray"],
    }
    product_body = build_product_body_evidence(
        raw_product_body,
        gameplay_semantic_evidence=gameplay,
        playtest=playtest,
    )
    product_depth = build_product_depth_evidence(
        product_depth={"level_goals": [f"goal-{index}" for index in range(8)]},
        feature_coverage=features,
        player_visible_checks=features,
        playtest=playtest,
    )
    reference = {
        "go": True,
        "blockers": [],
        "source": {"visual_density_ratio": 1.5},
        "evidence_path": (project_dir / "workflow_runtime_evidence" / "reference_quality_evidence.json").as_posix(),
    }

    result = _collect_ai_surrogate_playtest_evidence(
        project_dir=project_dir,
        build=build,
        playtest=playtest,
        build_ledger=build_ledger,
        browser_playtest_ledger=browser_ledger,
        gameplay_semantic_evidence=gameplay,
        product_body_evidence=product_body,
        product_depth_evidence=product_depth,
        reference_quality_evidence=reference,
        feature_evidence={
            "commercial_feature_coverage": features,
            "product_body_evidence": raw_product_body,
        },
    )

    assert result["go"] is True
    assert result["quality"]["ai_surrogate_playtest_go"] is True
    assert result["quality"]["governance"]["human_player_review_go"] is False
    assert Path(result["packet_path"]).exists()
    assert Path(result["report_path"]).exists()


def test_production_payload_promotes_ai_surrogate_contract_into_machine_evidence(tmp_path: Path) -> None:
    project_dir = tmp_path / "cocos_project"
    project_dir.mkdir()
    ai_quality = {
        "schema_version": "universal_ai_surrogate_playtest_quality_v1",
        "ai_surrogate_playtest_go": True,
        "blockers": [],
    }

    payload = production_payload_from_worker(
        schema_version="commercial_game_worker_v1",
        created_at="2026-05-08T00:00:00Z",
        pipeline_id="pipeline_ai",
        project_dir=project_dir,
        task_card_quality={"task_card_count": 1},
        runtime_evidence={
            "technical_smoke_go": True,
            "production_scaffold_go": True,
            "commercial_playable_blockers": [],
            "commercial_feature_coverage": _product_features(),
            "player_visible_checks": _product_features(),
            "build_ledger": {"schema_version": "commercial_game_build_ledger_v1", "go": True, "blockers": [], "source": {}},
            "browser_playtest_ledger": {
                "schema_version": "commercial_game_browser_playtest_ledger_v1",
                "go": True,
                "blockers": [],
                "source": {},
            },
            "gameplay_semantic_evidence": {
                "schema_version": "commercial_game_gameplay_semantic_evidence_v1",
                "go": True,
                "blockers": [],
                "source": {},
            },
            "product_body_evidence": {
                "schema_version": "commercial_game_product_body_evidence_v1",
                "go": True,
                "blockers": [],
                "source": {},
            },
            "product_depth_evidence": {
                "schema_version": "commercial_game_product_depth_evidence_v1",
                "go": True,
                "blockers": [],
                "source": {},
            },
            "ai_surrogate_playtest_evidence": ai_quality,
            "commercial_quality_scorecard": {
                "schema_version": "commercial_game_quality_scorecard_v1",
                "go": True,
                "blockers": [],
                "hard_blockers": [],
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
            },
            "playtest": {"screenshots": []},
        },
        assets_stage={"commercial_assets_go": True, "commercial_asset_blockers": []},
        ecosystem_evidence={"ecosystem_integration_go": True, "blockers": []},
        patch_ledger={"same_project_worker_patch_go": True, "entries": [{"status": "completed"}]},
        skipped_task_cards=[],
        max_repair_attempts=1,
        dedupe_strings=lambda values: list(dict.fromkeys(str(value) for value in values)),
        blocker_details=lambda blockers: [{"blocker": blocker} for blocker in blockers],
        recoverable_suggestions=lambda blockers: [f"repair:{blocker}" for blocker in blockers],
    )

    assert payload["ai_surrogate_playtest_go"] is True
    assert payload["evidence_contracts"]["ai_surrogate_playtest_evidence"]["go"] is True
