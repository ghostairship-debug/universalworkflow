from __future__ import annotations

from pathlib import Path

from packages.contributions.games.ai_playtest_lab import AI_PLAYTEST_MODES, build_ai_playtest_plan
from packages.contributions.games.ai_playtest_quality import QUALITY_AREAS
from packages.contributions.games.ai_playtest_runner import run_ai_playtest_plan
from packages.contributions.games.game_design_ir import build_game_design_spec


def test_ai_playtest_runner_generates_fresh_packet_from_browser_layer(tmp_path: Path) -> None:
    spec = build_game_design_spec(
        title="Runner",
        genre="runner",
        sources=[{"source_id": "brief", "requirements": ["Jump over hazards.", "BGM and SFX play."]}],
    )
    plan = build_ai_playtest_plan(spec)

    def fake_browser_runner(_context: dict, output_dir: Path) -> dict:
        screenshot = output_dir / "screenshots" / "desktop.png"
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        screenshot.write_bytes(b"png")
        return {
            "go": True,
            "url": "http://127.0.0.1:7777/index.html",
            "screenshots": [screenshot.as_posix()],
            "console_errors": [],
            "page_errors": [],
            "device_results": [
                {"device": "desktop", "status": "passed"},
                {"device": "mobile_portrait", "status": "passed"},
                {"device": "mobile_landscape_or_responsive_when_required", "status": "passed"},
            ],
            "performance_metrics": {"min_fps": 60, "input_latency_ms": 45, "load_time_ms": 500},
            "blockers": [],
        }

    result = run_ai_playtest_plan(
        plan=plan,
        workspace_root=tmp_path,
        output_dir=tmp_path / "ai_run",
        browser_runner=fake_browser_runner,
        quality_overrides={
            "workflow_generated_product_go": True,
            "core_loop_playable": True,
            "first_session_flow_go": True,
            "requirement_fidelity_go": True,
            "area_scores": dict(QUALITY_AREAS),
            "vision_review": {
                "visual_go": True,
                "visual_quality_score": 90,
                "targets_checked": plan["vision_review_targets"],
                "screenshots_reviewed": ["desktop.png"],
                "blockers": [],
            },
            "audio_review": {
                "audio_go": True,
                "bgm_runtime_verified": True,
                "sfx_runtime_verified": True,
                "mix_go": True,
                "blockers": [],
            },
        },
        engine_native_product_body={
            "engine": "cocos",
            "product_body_mode": "engine_native",
            "required_components": ["GameModel", "InputController", "AudioFeedbackController"],
            "component_bindings": ["GameModel", "InputController", "AudioFeedbackController"],
            "scene_or_prefab_bindings": ["main.scene"],
            "semantic_trace_source": "engine_runtime_model_transition",
            "runtime_state_authoritative": True,
            "build_launch_evidence": {"go": True},
        },
    )

    assert result["go"] is True
    assert Path(result["packet_path"]).exists()
    assert Path(result["report_path"]).exists()
    assert set(result["packet"]["mode_results"]) == set(AI_PLAYTEST_MODES)
    assert result["report"]["quality"]["ai_surrogate_playtest_go"] is True


def test_ai_playtest_runner_without_browser_target_is_honest_no_go(tmp_path: Path) -> None:
    spec = build_game_design_spec(
        title="Runner",
        genre="runner",
        sources=[{"source_id": "brief", "requirements": ["Jump over hazards."]}],
    )
    result = run_ai_playtest_plan(
        plan=build_ai_playtest_plan(spec),
        workspace_root=tmp_path,
        output_dir=tmp_path / "ai_run",
    )

    assert result["go"] is False
    assert "ai_playtest_browser_target_missing" in result["browser_result"]["blockers"]
    assert "ai_playtest_execution_modes_incomplete" in result["report"]["validation"]["blockers"]
