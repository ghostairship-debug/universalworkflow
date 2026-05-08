from __future__ import annotations

from pathlib import Path

from packages.contributions.games.ai_playtest_execution import (
    AI_PLAYTEST_EXECUTION_PACKET_SCHEMA,
    evaluate_ai_playtest_execution_packet,
    validate_ai_playtest_execution_packet,
)
from packages.contributions.games.ai_playtest_lab import AI_PLAYTEST_MODES, build_ai_playtest_plan
from packages.contributions.games.ai_playtest_quality import QUALITY_AREAS
from packages.contributions.games.game_design_ir import build_game_design_spec


def _packet(tmp_path: Path) -> dict:
    spec = build_game_design_spec(
        title="Runner",
        genre="runner",
        sources=[{"source_id": "brief", "requirements": ["Jump over hazards.", "Collect coins.", "Play BGM."]}],
    )
    plan = build_ai_playtest_plan(spec)
    mode_results = {}
    for mode in AI_PLAYTEST_MODES:
        replay = tmp_path / f"{mode}.jsonl"
        screenshot = tmp_path / f"{mode}.png"
        state = tmp_path / f"{mode}_state.json"
        replay.write_text('{"event":"boot"}\n', encoding="utf-8")
        screenshot.write_bytes(b"png")
        state.write_text('{"state":"ok"}', encoding="utf-8")
        mode_results[mode] = {
            "status": "completed",
            "fresh_run": True,
            "replay_artifacts": [replay.as_posix()],
            "screenshots": [screenshot.as_posix()],
            "state_snapshots": [state.as_posix()],
            "findings": [],
            "console_errors": [],
            "page_errors": [],
        }
    return {
        "schema_version": AI_PLAYTEST_EXECUTION_PACKET_SCHEMA,
        "plan": plan,
        "workflow_generated_product_go": True,
        "core_loop_playable": True,
        "first_session_flow_go": True,
        "requirement_fidelity_go": True,
        "area_scores": dict(QUALITY_AREAS),
        "mode_results": mode_results,
        "scripted_scenario_results": [
            {"scenario": scenario, "status": "passed"} for scenario in plan["scripted_scenarios"]
        ],
        "state_assertion_results": [
            {"assertion": assertion, "status": "passed"} for assertion in plan["state_assertions"]
        ],
        "device_matrix_results": [
            {"device": device, "status": "passed"} for device in plan["device_matrix"]
        ],
        "performance_metrics": {"min_fps": 58, "input_latency_ms": 42, "load_time_ms": 900},
        "vision_review": {
            "visual_go": True,
            "visual_quality_score": 90,
            "targets_checked": plan["vision_review_targets"],
            "screenshots_reviewed": [str(tmp_path / "scripted_bot.png")],
            "blockers": [],
        },
        "audio_review": {
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


def test_ai_playtest_execution_packet_requires_real_artifacts_and_all_modes(tmp_path: Path) -> None:
    packet = _packet(tmp_path)

    validation = validate_ai_playtest_execution_packet(
        packet,
        workspace_root=tmp_path,
        require_artifact_files=True,
    )
    report = evaluate_ai_playtest_execution_packet(packet, workspace_root=tmp_path, require_artifact_files=True)

    assert validation["go"] is True
    assert validation["artifact_existence_checked"] is True
    assert report["go"] is True
    assert report["quality"]["ai_surrogate_playtest_go"] is True


def test_ai_playtest_execution_packet_blocks_stale_missing_and_low_performance(tmp_path: Path) -> None:
    packet = _packet(tmp_path)
    packet["mode_results"].pop("vision_reviewer")
    packet["mode_results"]["scripted_bot"]["fresh_run"] = False
    packet["mode_results"]["scripted_bot"]["screenshots"] = ["missing.png"]
    packet["scripted_scenario_results"] = packet["scripted_scenario_results"][:-1]
    packet["state_assertion_results"][0]["status"] = "failed"
    packet["device_matrix_results"] = packet["device_matrix_results"][:-1]
    packet["performance_metrics"] = {"min_fps": 25, "input_latency_ms": 180}
    packet["vision_review"] = {"visual_go": False, "targets_checked": [], "blockers": ["text_overlaps_hud"]}

    report = evaluate_ai_playtest_execution_packet(packet, workspace_root=tmp_path, require_artifact_files=True)

    assert report["go"] is False
    blockers = set(report["validation"]["blockers"])
    assert "ai_playtest_execution_modes_missing" in blockers
    assert "ai_playtest_fresh_run_missing" in blockers
    assert "ai_playtest_artifact_file_missing" in blockers
    assert "scripted_scenario_coverage_missing" in blockers
    assert "state_assertion_no_go" in blockers
    assert "device_matrix_coverage_missing" in blockers
    assert "vision_target_coverage_missing" in blockers
    assert "performance_min_fps_below_floor" in blockers
    assert "input_latency_above_floor" in blockers
    assert "vision_review_no_go" in blockers
    assert report["quality"]["ai_surrogate_playtest_go"] is False
