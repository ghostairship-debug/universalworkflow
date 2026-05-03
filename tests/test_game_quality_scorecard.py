from __future__ import annotations

from packages.contributions.games.ai_playtest_quality import QUALITY_AREAS, evaluate_ai_surrogate_playtest


def _engine_native() -> dict:
    return {
        "engine": "cocos",
        "product_body_mode": "engine_native",
        "required_components": ["RuntimeModel"],
        "component_bindings": ["RuntimeModel"],
        "scene_or_prefab_bindings": ["main.scene"],
        "semantic_trace_source": "model_transition",
        "runtime_state_authoritative": True,
        "build_launch_evidence": {"go": True},
    }


def test_quality_scorecard_caps_area_scores_by_weight() -> None:
    report = evaluate_ai_surrogate_playtest(
        {
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
            "area_scores": {area: 999 for area in QUALITY_AREAS},
            "findings": [],
            "screenshots": ["screen.png"],
            "replay_artifacts": ["replay.jsonl"],
            "engine_native_product_body": _engine_native(),
        }
    )

    assert report["ai_quality_score"] == sum(QUALITY_AREAS.values())
    assert report["area_scores"] == QUALITY_AREAS
    assert report["production_vertical_slice_go"] is True


def test_quality_scorecard_blocks_below_85_even_without_blocking_findings() -> None:
    report = evaluate_ai_surrogate_playtest(
        {
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
            "area_scores": {area: 6 for area in QUALITY_AREAS},
            "findings": [{"severity": "P3", "finding_id": "minor-polish"}],
            "screenshots": ["screen.png"],
            "replay_artifacts": ["replay.jsonl"],
            "engine_native_product_body": _engine_native(),
        }
    )

    assert report["ai_quality_score"] < 85
    assert report["production_vertical_slice_go"] is False
    assert "ai_quality_score_below_85" in report["blockers"]
    assert report["prototype_floor_go"] is False
