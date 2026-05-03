from __future__ import annotations

from typing import Any


ENGINE_NATIVE_PRODUCT_BODY_SCHEMA = "universal_engine_native_product_body_contract_v1"

_SUBSTITUTE_MODES = {
    "browser_bridge",
    "browser_overlay",
    "canvas_overlay",
    "runtime_hook",
    "event_only",
    "feature_flag_only",
    "screenshot_only",
}


def build_engine_native_product_body_contract(evidence: dict[str, Any] | None) -> dict[str, Any]:
    payload = evidence if isinstance(evidence, dict) else {}
    blockers: list[str] = []
    if not payload:
        blockers.append("engine_native_product_body_missing")
    engine = str(payload.get("engine") or "").strip().lower()
    if not engine:
        blockers.append("engine_missing")
    product_body_mode = str(payload.get("product_body_mode") or payload.get("runtime_mode") or "").strip().lower()
    if product_body_mode in _SUBSTITUTE_MODES:
        blockers.append(f"{product_body_mode}_cannot_satisfy_product_body")
    if payload.get("browser_bridge_product_body") or payload.get("canvas_overlay_product_body"):
        blockers.append("browser_bridge_or_canvas_overlay_product_body")
    if payload.get("baseline_only"):
        blockers.append("baseline_only_cannot_satisfy_engine_native_contract")
    required_components = _string_list(payload.get("required_components"))
    component_bindings = _string_list(payload.get("component_bindings") or payload.get("bound_components"))
    if required_components:
        missing = [component for component in required_components if component not in set(component_bindings)]
        if missing:
            blockers.append("engine_component_bindings_missing")
    elif not component_bindings:
        blockers.append("engine_component_bindings_missing")
    if not _string_list(payload.get("scene_or_prefab_bindings")):
        blockers.append("scene_or_prefab_bindings_missing")
    trace_source = str(payload.get("semantic_trace_source") or "").strip().lower()
    if trace_source not in {"model_transition", "engine_runtime_model_transition", "semantic_test_bridge_model_transition"}:
        blockers.append("semantic_trace_not_model_transition")
    if not payload.get("runtime_state_authoritative"):
        blockers.append("runtime_state_not_authoritative")
    if not payload.get("build_launch_evidence"):
        blockers.append("build_launch_evidence_missing")
    if payload.get("stale_evidence_reused"):
        blockers.append("fresh_engine_evidence_missing")
    return {
        "schema_version": ENGINE_NATIVE_PRODUCT_BODY_SCHEMA,
        "go": not blockers,
        "status": "completed" if not blockers else "blocked",
        "blockers": blockers,
        "source": {
            "engine": engine or None,
            "product_body_mode": product_body_mode or None,
            "required_components": required_components,
            "component_bindings": component_bindings,
            "scene_or_prefab_bindings": _string_list(payload.get("scene_or_prefab_bindings")),
            "semantic_trace_source": payload.get("semantic_trace_source"),
        },
    }


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
