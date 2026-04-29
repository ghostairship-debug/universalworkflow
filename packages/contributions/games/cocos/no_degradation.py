from __future__ import annotations

from typing import Any


NO_DEGRADATION_CONTRACT_SCHEMA = "commercial_game_no_degradation_contract_v1"

_PRODUCT_FEATURES = {
    "eightDistinctLevelGoals": "levels_not_distinct_or_less_than_eight",
    "skinEquippedVisualChange": "skin_system_not_player_visible",
    "shopOwnershipStates": "shop_ownership_states_missing",
    "audioPlaybackVerified": "audio_runtime_not_verified",
    "bgmStarted": "bgm_runtime_not_verified",
    "volumeToggleUsable": "volume_toggle_missing",
}


def evaluate_no_degradation_contract(
    *,
    shared_outputs: dict[str, Any],
    production: dict[str, Any] | None,
    require_commercial: bool,
    require_cocos_ecosystem: bool = False,
    require_live_agent_roles: bool = False,
    require_human_player_review: bool = False,
) -> dict[str, Any]:
    production_payload = dict(production or {})
    cocos_e2e = shared_outputs.get("cocos_e2e") if isinstance(shared_outputs.get("cocos_e2e"), dict) else {}
    playtest = _dict_from(production_payload.get("playtest")) or _dict_from(cocos_e2e.get("playtest"))
    build = _dict_from(production_payload.get("build")) or _dict_from(cocos_e2e.get("build"))
    feature_coverage = _feature_coverage(production_payload, cocos_e2e, playtest)
    console_and_page_errors = [*list(playtest.get("console_errors") or []), *list(playtest.get("page_errors") or [])]

    ecosystem = _dict_from(shared_outputs.get("cocos_ecosystem_evidence")) or _dict_from(
        production_payload.get("cocos_ecosystem_evidence")
    )
    ecosystem_go = bool(production_payload.get("ecosystem_integration_go") or ecosystem.get("ecosystem_integration_go"))
    live_role_go = _live_role_provider_proof_go(shared_outputs)
    same_project_worker_patch_go = bool(production_payload.get("same_project_worker_patch_go"))
    human_player_review_go = _human_player_review_go(shared_outputs, production_payload)
    product_feature_depth_go = all(bool(feature_coverage.get(key)) for key in _PRODUCT_FEATURES)
    build_exit_go = _build_exit_go(build)
    browser_runtime_go = not _runtime_errors(console_and_page_errors)

    findings: list[dict[str, Any]] = []
    if require_commercial:
        _append_if_false(findings, same_project_worker_patch_go, "same_project_worker_patch_missing")
        _append_if_false(findings, live_role_go, "live_role_provider_proof_missing")
        _append_if_false(findings, product_feature_depth_go, "product_feature_depth_missing")
        _append_if_false(findings, build_exit_go, "cocos_build_nonzero_exit")
        _append_if_false(findings, browser_runtime_go, "browser_or_audio_runtime_error")
        for feature_name, blocker in _PRODUCT_FEATURES.items():
            if not bool(feature_coverage.get(feature_name)):
                findings.append({"finding": blocker, "feature": feature_name, "severity": "high"})
    if require_cocos_ecosystem:
        _append_if_false(findings, ecosystem_go, "cocos_ecosystem_bridge_missing")
    if require_live_agent_roles:
        _append_if_false(findings, live_role_go, "live_role_provider_proof_missing")
    if require_human_player_review:
        _append_if_false(findings, human_player_review_go, "awaiting_human_player_review")

    blockers = _dedupe([str(item["finding"]) for item in findings])
    awaiting_human = blockers == ["awaiting_human_player_review"] or (
        "awaiting_human_player_review" in blockers and len(blockers) == 1
    )
    go = not blockers
    return {
        "schema_version": NO_DEGRADATION_CONTRACT_SCHEMA,
        "go_no_go": "GO" if go else "AWAITING_HUMAN_REVIEW" if awaiting_human else "NO-GO",
        "ecosystem_integration_go": ecosystem_go,
        "live_role_provider_proof_go": live_role_go,
        "same_project_worker_patch_go": same_project_worker_patch_go,
        "human_player_review_go": human_player_review_go,
        "product_feature_depth_go": product_feature_depth_go,
        "build_exit_go": build_exit_go,
        "browser_runtime_go": browser_runtime_go,
        "required_product_features": sorted(_PRODUCT_FEATURES),
        "feature_coverage": feature_coverage,
        "runtime_error_markers": _runtime_errors(console_and_page_errors),
        "degradation_findings": findings,
        "blockers": blockers,
    }


def _dict_from(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _feature_coverage(*payloads: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for payload in payloads:
        for key in ("commercial_feature_coverage", "feature_coverage"):
            value = payload.get(key)
            if isinstance(value, dict):
                merged.update(value)
        playtest = payload.get("playtest")
        if isinstance(playtest, dict) and isinstance(playtest.get("feature_coverage"), dict):
            merged.update(playtest["feature_coverage"])
    return merged


def _live_role_provider_proof_go(shared_outputs: dict[str, Any]) -> bool:
    role_outputs = [value for key, value in shared_outputs.items() if key.startswith("role_output:") and isinstance(value, dict)]
    if not role_outputs:
        return False
    return all(
        output.get("llm_call_status") == "called"
        and isinstance(output.get("llm_provider_evidence"), dict)
        and bool(output["llm_provider_evidence"].get("configured"))
        for output in role_outputs
    )


def _human_player_review_go(shared_outputs: dict[str, Any], production: dict[str, Any]) -> bool:
    manual = _dict_from(production.get("manual_player_evidence")) or _dict_from(shared_outputs.get("manual_player_evidence"))
    return bool(manual.get("accepted_by_human") and manual.get("reviewer") and manual.get("evidence_path"))


def _build_exit_go(build: dict[str, Any]) -> bool:
    if not build:
        return False
    if bool(build.get("fatal_marker_detected")):
        return False
    exit_code = build.get("creator_exit_code")
    return exit_code in (0, "0", None)


def _runtime_errors(errors: list[Any]) -> list[str]:
    markers = ("NotSupportedError", "media", "audio", "decode", "play() failed", "DOMException")
    result = []
    for error in errors:
        text = str(error)
        if any(marker.lower() in text.lower() for marker in markers):
            result.append(text[:500])
    return result


def _append_if_false(findings: list[dict[str, Any]], passed: bool, finding: str) -> None:
    if not passed:
        findings.append({"finding": finding, "severity": "high"})


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
