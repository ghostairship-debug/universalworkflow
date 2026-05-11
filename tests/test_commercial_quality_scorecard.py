from __future__ import annotations

from packages.contributions.games.commercial_quality_score import evaluate_commercial_quality_scorecard
from packages.contributions.pipelines.commercial_game_evidence_contracts import build_commercial_final_gate_evidence


def _passing_playtest() -> dict:
    return {
        "passed": True,
        "real_pointer_drag_go": True,
        "real_pointer_drag": {"go": True, "board_state_changed": True, "score_changed": True},
        "portrait_orientation_go": True,
        "portrait_orientation": {
            "go": True,
            "viewport": {"width": 390, "height": 844},
            "screen_orientation": "portrait",
            "design_resolution": {"width": 1080, "height": 1920},
        },
        "screenshots": ["mobile.png", "desktop.png"],
        "feature_coverage": {
            "dragPlacement": True,
            "mobilePortraitUi": True,
            "chineseUi": True,
            "generatedArtAssets": True,
            "cocosAssetBindings": True,
            "animationFeedbackVerified": True,
            "audioPlaybackVerified": True,
            "bgmStarted": True,
            "sfxPlaybackVerified": True,
            "volumeToggleUsable": True,
        },
    }


def _passing_ai_quality() -> dict:
    return {
        "ai_surrogate_playtest_go": True,
        "visual_quality_score": 92,
        "audio_review": {
            "bgm_runtime_verified": True,
            "sfx_runtime_verified": True,
        },
    }


def test_commercial_quality_score_agent_passes_only_real_drag_and_portrait_product_body() -> None:
    scorecard = evaluate_commercial_quality_scorecard(
        playtest=_passing_playtest(),
        browser_playtest_ledger={"go": True, "blockers": []},
        reference_quality_evidence={"go": True, "blockers": []},
        ai_surrogate_playtest_evidence=_passing_ai_quality(),
        product_depth_evidence={"go": True, "blockers": []},
        product_body_evidence={"go": True, "blockers": []},
    )

    assert scorecard["go"] is True
    assert scorecard["total_score"] >= 85
    assert scorecard["hard_blockers"] == []


def test_commercial_quality_score_agent_rejects_bridge_only_drag_and_landscape() -> None:
    playtest = _passing_playtest()
    playtest["real_pointer_drag_go"] = False
    playtest["real_pointer_drag"] = {"go": False}
    playtest["portrait_orientation_go"] = False
    playtest["portrait_orientation"] = {
        "go": False,
        "screen_orientation": "auto",
        "design_resolution": {"width": 1280, "height": 720},
    }
    playtest["used_bridge_actions_for_core_drag"] = True

    scorecard = evaluate_commercial_quality_scorecard(
        playtest=playtest,
        browser_playtest_ledger={"go": False, "blockers": ["real_pointer_drag_failed"]},
        reference_quality_evidence={"go": True, "blockers": []},
        ai_surrogate_playtest_evidence=_passing_ai_quality(),
        product_depth_evidence={"go": True, "blockers": []},
        product_body_evidence={"go": True, "blockers": []},
    )

    assert scorecard["go"] is False
    assert "real_pointer_drag_failed" in scorecard["blockers"]
    assert "portrait_orientation_failed" in scorecard["blockers"]
    assert "bridge_event_miscounted_as_product_body" in scorecard["blockers"]


def test_final_gate_requires_commercial_quality_scorecard() -> None:
    complete = {"go": True, "blockers": [], "status": "completed", "schema_version": "test", "source": {}}

    gate = build_commercial_final_gate_evidence(
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
        live_role_provider_proof_go=True,
        human_player_review_go=False,
        gameplay_semantic_evidence=complete,
        product_body_evidence=complete,
    )

    assert gate["go_no_go"] == "NO-GO"
    assert "commercial_quality_scorecard_missing" in gate["machine_blockers"]
