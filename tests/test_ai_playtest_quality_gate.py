from __future__ import annotations

from packages.contributions.games.ai_playtest_quality import (
    QUALITY_AREAS,
    REQUIRED_AI_PLAYTEST_MODES,
    evaluate_ai_surrogate_playtest,
)


def _passing_evidence() -> dict:
    return {
        "workflow_generated_product_go": True,
        "core_loop_playable": True,
        "first_session_flow_go": True,
        "requirement_fidelity_go": True,
        "ai_playtest_modes_run": sorted(REQUIRED_AI_PLAYTEST_MODES),
        "area_scores": dict(QUALITY_AREAS),
        "findings": [{"finding_id": "polish-1", "severity": "P2", "category": "visual"}],
        "screenshots": ["first.png", "success.png", "failure.png"],
        "replay_artifacts": ["boot_to_success.jsonl", "failure_retry.jsonl"],
        "visual_review_evidence": {
            "visual_go": True,
            "visual_quality_score": 92,
            "screenshots_reviewed": ["first.png", "success.png", "failure.png"],
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
            "required_components": ["GameModel", "InputController", "AudioFeedbackController"],
            "component_bindings": ["GameModel", "InputController", "AudioFeedbackController"],
            "scene_or_prefab_bindings": ["main.scene"],
            "semantic_trace_source": "engine_runtime_model_transition",
            "runtime_state_authoritative": True,
            "build_launch_evidence": {"go": True},
        },
    }


def test_ai_surrogate_playtest_pass_requires_high_score_all_modes_and_engine_native_body() -> None:
    report = evaluate_ai_surrogate_playtest(_passing_evidence())

    assert report["ai_quality_score"] == 100
    assert report["ai_surrogate_playtest_go"] is True
    assert report["production_vertical_slice_go"] is True
    assert report["prototype_floor_go"] is True
    assert report["governance"]["human_player_review_go"] is False
    assert report["governance"]["commercial_playable_go"] is False


def test_ai_surrogate_playtest_rejects_codex_rescue_browser_bridge_even_when_feature_like_score_is_high() -> None:
    evidence = _passing_evidence()
    evidence["workflow_generated_product_go"] = False
    evidence["codex_local_patch_repair_go"] = True
    evidence["engine_native_product_body"] = {
        "engine": "cocos",
        "product_body_mode": "browser_bridge",
        "browser_bridge_product_body": True,
        "required_components": ["GameModel"],
        "component_bindings": ["GameModel"],
        "scene_or_prefab_bindings": ["main.scene"],
        "semantic_trace_source": "model_transition",
        "runtime_state_authoritative": True,
        "build_launch_evidence": {"go": True},
    }

    report = evaluate_ai_surrogate_playtest(evidence)

    assert report["ai_surrogate_playtest_go"] is False
    assert "workflow_generated_product_not_proven" in report["blockers"]
    assert "codex_local_patch_cannot_count_as_workflow_product" in report["blockers"]
    assert "engine_native_product_body_not_proven" in report["blockers"]
    assert report["engine_native_product_body"]["go"] is False


def test_ai_surrogate_playtest_rejects_missing_modes_and_p1_findings() -> None:
    evidence = _passing_evidence()
    evidence["ai_playtest_modes_run"] = ["scripted_bot", "vision_reviewer"]
    evidence["findings"] = [{"finding_id": "core-loop-break", "severity": "P1", "category": "correctness"}]

    report = evaluate_ai_surrogate_playtest(evidence)

    assert report["ai_surrogate_playtest_go"] is False
    assert "ai_playtest_modes_incomplete" in report["blockers"]
    assert "blocking_ai_findings_present" in report["blockers"]
    assert report["blocking_findings"][0]["finding_id"] == "core-loop-break"


def test_ai_surrogate_playtest_rejects_missing_visual_and_audio_review() -> None:
    evidence = _passing_evidence()
    evidence.pop("visual_review_evidence")
    evidence.pop("audio_review_evidence")

    report = evaluate_ai_surrogate_playtest(evidence)

    assert report["ai_surrogate_playtest_go"] is False
    assert "ai_visual_review_missing" in report["blockers"]
    assert "ai_audio_review_missing" in report["blockers"]
