from __future__ import annotations

from packages.contributions.games.engine_native_contract import build_engine_native_product_body_contract


def test_engine_native_product_body_rejects_browser_bridge_overlay() -> None:
    contract = build_engine_native_product_body_contract(
        {
            "engine": "cocos",
            "product_body_mode": "browser_bridge",
            "browser_bridge_product_body": True,
            "required_components": ["BoardModel", "InputController"],
            "component_bindings": ["BoardModel", "InputController"],
            "scene_or_prefab_bindings": ["Main.scene"],
            "semantic_trace_source": "model_transition",
            "runtime_state_authoritative": True,
            "build_launch_evidence": {"go": True},
        }
    )

    assert contract["go"] is False
    assert "browser_bridge_cannot_satisfy_product_body" in contract["blockers"]
    assert "browser_bridge_or_canvas_overlay_product_body" in contract["blockers"]


def test_engine_native_product_body_requires_components_scene_and_model_trace() -> None:
    contract = build_engine_native_product_body_contract(
        {
            "engine": "cocos",
            "product_body_mode": "engine_native",
            "required_components": ["BoardModel", "InputController", "AudioFeedbackController"],
            "component_bindings": ["BoardModel"],
            "semantic_trace_source": "browser_event_hook",
            "runtime_state_authoritative": False,
        }
    )

    assert contract["go"] is False
    assert "engine_component_bindings_missing" in contract["blockers"]
    assert "scene_or_prefab_bindings_missing" in contract["blockers"]
    assert "semantic_trace_not_model_transition" in contract["blockers"]
    assert "runtime_state_not_authoritative" in contract["blockers"]
    assert "build_launch_evidence_missing" in contract["blockers"]


def test_engine_native_product_body_accepts_real_engine_native_evidence() -> None:
    contract = build_engine_native_product_body_contract(
        {
            "engine": "cocos",
            "product_body_mode": "engine_native",
            "required_components": ["BoardModel", "InputController", "AudioFeedbackController"],
            "component_bindings": ["BoardModel", "InputController", "AudioFeedbackController"],
            "scene_or_prefab_bindings": ["assets/scene/main.scene", "assets/prefabs/HUD.prefab"],
            "semantic_trace_source": "engine_runtime_model_transition",
            "runtime_state_authoritative": True,
            "build_launch_evidence": {"go": True, "url": "http://127.0.0.1:3000"},
        }
    )

    assert contract["go"] is True
    assert contract["blockers"] == []
