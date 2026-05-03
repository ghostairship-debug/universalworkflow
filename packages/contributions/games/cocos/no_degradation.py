from __future__ import annotations

from typing import Any

from packages.contributions.pipelines.commercial_game_evidence_contracts import (
    BROWSER_PLAYTEST_LEDGER_SCHEMA,
    BUILD_LEDGER_SCHEMA,
    GAMEPLAY_SEMANTIC_EVIDENCE_SCHEMA,
    PRODUCT_DEPTH_EVIDENCE_SCHEMA,
    PRODUCT_BODY_EVIDENCE_SCHEMA,
    build_asset_graph_contract,
    build_browser_playtest_ledger,
    build_build_ledger,
    build_cocos_bridge_evidence_contract,
    build_commercial_final_gate_evidence,
    build_gameplay_semantic_evidence,
    build_product_body_evidence,
    build_product_depth_evidence,
    build_same_project_patch_ledger_contract,
    runtime_error_markers,
)


NO_DEGRADATION_CONTRACT_SCHEMA = "commercial_game_no_degradation_contract_v1"

_PRODUCT_FEATURES = {
    "eightDistinctLevelGoals": "levels_not_distinct_or_less_than_eight",
    "skinEquippedVisualChange": "skin_system_not_player_visible",
    "shopOwnershipStates": "shop_ownership_states_missing",
    "chineseUiPanelsVisible": "chinese_ui_panels_missing",
    "levelFlowPlayable": "level_flow_not_verified",
    "failureReviveFeedback": "failure_revive_feedback_missing",
    "audioPlaybackVerified": "audio_runtime_not_verified",
    "bgmStarted": "bgm_runtime_not_verified",
    "sfxPlaybackVerified": "sfx_runtime_not_verified",
    "volumeToggleUsable": "volume_toggle_missing",
    "animationFeedbackVerified": "animation_feedback_missing",
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
    asset_graph = build_asset_graph_contract(
        _dict_from(production_payload.get("assets")) or _dict_from(shared_outputs.get("commercial_game_assets"))
    )
    patch_ledger = build_same_project_patch_ledger_contract(_dict_from(production_payload.get("same_project_patch_ledger")))
    build_ledger = build_build_ledger(_dict_from(production_payload.get("build_ledger")) or build)
    browser_playtest_ledger = build_browser_playtest_ledger(
        _dict_from(production_payload.get("browser_playtest_ledger")) or playtest
    )

    ecosystem = _dict_from(shared_outputs.get("cocos_ecosystem_evidence")) or _dict_from(
        production_payload.get("cocos_ecosystem_evidence")
    )
    cocos_bridge_evidence = build_cocos_bridge_evidence_contract(ecosystem)
    product_depth_evidence = build_product_depth_evidence(
        product_depth=_dict_from(production_payload.get("product_depth_evidence")),
        feature_coverage=feature_coverage,
        player_visible_checks=_dict_from(production_payload.get("player_visible_checks")),
        playtest=playtest,
    )
    gameplay_semantic_evidence = build_gameplay_semantic_evidence(
        _dict_from(production_payload.get("gameplay_semantic_evidence")),
        feature_coverage=feature_coverage,
        playtest=playtest,
    )
    product_body_evidence = build_product_body_evidence(
        _dict_from(production_payload.get("product_body_evidence")),
        gameplay_semantic_evidence=gameplay_semantic_evidence,
        playtest=playtest,
    )
    ecosystem_go = bool(cocos_bridge_evidence["go"])
    live_role_go = _live_role_provider_proof_go(shared_outputs)
    same_project_worker_patch_go = bool(patch_ledger["go"])
    upstream_implementation_failed = bool(require_commercial and not same_project_worker_patch_go)
    if upstream_implementation_failed:
        upstream_source = {
            "upstream_stage": "same_project_worker_patch",
            "upstream_blockers": list(patch_ledger.get("blockers") or []),
            "skip_reason": "skipped_due_to_upstream_failure",
        }
        build_ledger = _blocked_by_same_project_worker_contract(
            schema_version=BUILD_LEDGER_SCHEMA,
            stage="cocos_build",
            source=upstream_source,
        )
        browser_playtest_ledger = _blocked_by_same_project_worker_contract(
            schema_version=BROWSER_PLAYTEST_LEDGER_SCHEMA,
            stage="browser_playtest",
            source=upstream_source,
        )
        product_depth_evidence = _blocked_by_same_project_worker_contract(
            schema_version=PRODUCT_DEPTH_EVIDENCE_SCHEMA,
            stage="product_depth",
            source=upstream_source,
        )
        gameplay_semantic_evidence = _blocked_by_same_project_worker_contract(
            schema_version=GAMEPLAY_SEMANTIC_EVIDENCE_SCHEMA,
            stage="gameplay_semantic",
            source=upstream_source,
        )
        product_body_evidence = _blocked_by_same_project_worker_contract(
            schema_version=PRODUCT_BODY_EVIDENCE_SCHEMA,
            stage="product_body",
            source=upstream_source,
        )
    human_player_review_go = _human_player_review_go(shared_outputs, production_payload)
    product_feature_depth_go = bool(product_depth_evidence["go"])
    product_feature_blockers = list(product_depth_evidence["blockers"])
    build_exit_go = bool(build_ledger["go"])
    browser_runtime_go = bool(browser_playtest_ledger["go"])
    require_ai_surrogate_playtest = bool(require_commercial and not upstream_implementation_failed)
    ai_surrogate_playtest_evidence = _ai_surrogate_playtest_evidence(shared_outputs, production_payload)
    final_gate_evidence = build_commercial_final_gate_evidence(
        technical_smoke_go=bool(production_payload.get("technical_smoke_go")),
        production_scaffold_go=bool(production_payload.get("production_scaffold_go")),
        require_commercial=require_commercial,
        require_cocos_ecosystem=require_cocos_ecosystem,
        require_live_agent_roles=require_live_agent_roles,
        require_human_player_review=require_human_player_review,
        asset_graph=asset_graph,
        cocos_bridge_evidence=cocos_bridge_evidence,
        same_project_patch_ledger=patch_ledger,
        build_ledger=build_ledger,
        browser_playtest_ledger=browser_playtest_ledger,
        product_feature_depth_go=product_feature_depth_go,
        product_feature_blockers=product_feature_blockers,
        live_role_provider_proof_go=live_role_go,
        human_player_review_go=human_player_review_go,
        gameplay_semantic_evidence=gameplay_semantic_evidence,
        product_body_evidence=product_body_evidence,
        require_ai_surrogate_playtest=require_ai_surrogate_playtest,
        ai_surrogate_playtest_evidence=ai_surrogate_playtest_evidence,
    )

    findings: list[dict[str, Any]] = []
    if require_commercial:
        _append_if_false(findings, same_project_worker_patch_go, "same_project_worker_patch_missing")
        if require_live_agent_roles:
            _append_if_false(findings, live_role_go, "live_role_provider_proof_missing")
        if upstream_implementation_failed:
            for blocker in patch_ledger["blockers"]:
                findings.append({"finding": blocker, "severity": "high"})
            findings.append({"finding": "blocked_by_same_project_worker", "severity": "high"})
        else:
            _append_if_false(findings, product_feature_depth_go, "product_feature_depth_missing")
            for blocker in build_ledger["blockers"]:
                findings.append({"finding": blocker, "severity": "high"})
            for blocker in browser_playtest_ledger["blockers"]:
                findings.append({"finding": blocker, "severity": "high"})
            for blocker in product_depth_evidence["blockers"]:
                findings.append({"finding": blocker, "severity": "high"})
            for blocker in gameplay_semantic_evidence["blockers"]:
                findings.append({"finding": blocker, "severity": "high"})
            for blocker in product_body_evidence["blockers"]:
                findings.append({"finding": blocker, "severity": "high"})
            if require_ai_surrogate_playtest:
                ai_contract = _dict_from(final_gate_evidence.get("contracts")).get("ai_surrogate_playtest_evidence")
                if isinstance(ai_contract, dict) and not bool(ai_contract.get("ai_surrogate_playtest_go")):
                    for blocker in ai_contract.get("blockers") or ["ai_surrogate_playtest_missing"]:
                        findings.append({"finding": str(blocker), "severity": "high"})
        for blocker in asset_graph["blockers"]:
            findings.append({"finding": blocker, "severity": "high"})
    if require_cocos_ecosystem and not ecosystem_go:
        for blocker in cocos_bridge_evidence["blockers"] or ["cocos_ecosystem_bridge_missing"]:
            findings.append({"finding": blocker, "severity": "high"})
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
        "gameplay_semantic_go": bool(gameplay_semantic_evidence["go"]),
        "product_body_go": bool(product_body_evidence["go"]),
        "build_exit_go": build_exit_go,
        "browser_runtime_go": browser_runtime_go,
        "asset_graph_go": bool(asset_graph["go"]),
        "build_ledger_go": bool(build_ledger["go"]),
        "browser_playtest_ledger_go": bool(browser_playtest_ledger["go"]),
        "machine_evidence_go": bool(final_gate_evidence["machine_evidence_go"]),
        "required_product_features": sorted(_PRODUCT_FEATURES),
        "feature_coverage": feature_coverage,
        "runtime_error_markers": runtime_error_markers(console_and_page_errors),
        "evidence_contracts": {
            "asset_graph": asset_graph,
            "cocos_bridge_evidence": cocos_bridge_evidence,
            "same_project_patch_ledger": patch_ledger,
            "build_ledger": build_ledger,
            "browser_playtest_ledger": browser_playtest_ledger,
            "gameplay_semantic_evidence": gameplay_semantic_evidence,
            "product_body_evidence": product_body_evidence,
            "product_depth_evidence": product_depth_evidence,
        },
        "commercial_final_gate_evidence": final_gate_evidence,
        "gameplay_semantic_evidence": gameplay_semantic_evidence,
        "product_body_evidence": product_body_evidence,
        "product_depth_evidence": product_depth_evidence,
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


def _ai_surrogate_playtest_evidence(shared_outputs: dict[str, Any], production: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        production.get("ai_surrogate_playtest_evidence"),
        production.get("ai_playtest_quality_report"),
        _dict_from(production.get("ai_playtest_execution_report")).get("quality"),
        shared_outputs.get("ai_surrogate_playtest_evidence"),
        shared_outputs.get("ai_playtest_quality_report"),
        _dict_from(shared_outputs.get("ai_playtest_execution_report")).get("quality"),
    ]
    for candidate in candidates:
        payload = _dict_from(candidate)
        if payload:
            return payload
    return {}


def _append_if_false(findings: list[dict[str, Any]], passed: bool, finding: str) -> None:
    if not passed:
        findings.append({"finding": finding, "severity": "high"})


def _blocked_by_same_project_worker_contract(*, schema_version: str, stage: str, source: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "status": "blocked",
        "go": False,
        "blockers": ["blocked_by_same_project_worker"],
        "source": {"stage": stage, **source},
    }


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
