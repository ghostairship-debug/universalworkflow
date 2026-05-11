from __future__ import annotations

import json
from typing import Any

from packages.contributions.games.ai_playtest_quality import AI_PLAYTEST_QUALITY_SCHEMA, evaluate_ai_surrogate_playtest
from packages.contributions.games.cocos.e2e import COCOS_BUILD_SUCCESS_EXIT_CODES


COMMERCIAL_GAME_EVIDENCE_CONTRACT_SCHEMA = "commercial_game_evidence_contracts_v1"
ASSET_GRAPH_SCHEMA = "commercial_game_asset_graph_v1"
COCOS_BRIDGE_EVIDENCE_SCHEMA = "commercial_game_cocos_bridge_evidence_v1"
SAME_PROJECT_PATCH_LEDGER_SCHEMA = "commercial_game_same_project_patch_ledger_contract_v1"
BUILD_LEDGER_SCHEMA = "commercial_game_build_ledger_v1"
BROWSER_PLAYTEST_LEDGER_SCHEMA = "commercial_game_browser_playtest_ledger_v1"
COMMERCIAL_FINAL_GATE_EVIDENCE_SCHEMA = "commercial_game_final_gate_evidence_v1"
PRODUCT_DEPTH_EVIDENCE_SCHEMA = "commercial_game_product_depth_evidence_v1"
GAMEPLAY_SEMANTIC_EVIDENCE_SCHEMA = "commercial_game_gameplay_semantic_evidence_v1"
PRODUCT_BODY_EVIDENCE_SCHEMA = "commercial_game_product_body_evidence_v1"
HUMAN_REVIEW_PACKET_SCHEMA = "commercial_game_human_review_packet_v1"

_NON_REAL_STATUS = {"skipped", "stubbed", "simulated", "filesystem_only", "offline_only", "build_only"}
_NON_IMPLEMENTATION_ADAPTERS = {"shell", "noop", "dry_run", "dry-run"}
_PRODUCT_DEPTH_REQUIREMENTS = {
    "shopOwnershipStates": "shop_ownership_states_missing",
    "skinEquippedVisualChange": "skin_system_not_player_visible",
    "chineseUiPanelsVisible": "chinese_ui_panels_missing",
    "levelFlowPlayable": "level_flow_not_verified",
    "failureReviveFeedback": "failure_revive_feedback_missing",
    "audioPlaybackVerified": "audio_runtime_not_verified",
    "bgmStarted": "bgm_runtime_not_verified",
    "sfxPlaybackVerified": "sfx_runtime_not_verified",
    "volumeToggleUsable": "volume_toggle_missing",
    "animationFeedbackVerified": "animation_feedback_missing",
}


def build_asset_graph_contract(assets_stage: dict[str, Any] | None) -> dict[str, Any]:
    payload = _dict_from(assets_stage)
    if _is_contract(payload, ASSET_GRAPH_SCHEMA):
        return payload
    blockers: list[str] = []
    if not payload:
        blockers.append("commercial_assets_missing")
    if _has_non_real_status(payload):
        blockers.append("commercial_assets_not_real_execution")
    if payload.get("asset_generation_skipped"):
        blockers.append("commercial_asset_generation_skipped")
    if payload.get("placeholder_only"):
        blockers.append("placeholder_assets_only")
    blockers.extend(_strings(payload.get("commercial_asset_blockers")))
    manifest = _dict_from(payload.get("asset_manifest"))
    if manifest and manifest.get("go_no_go") not in {None, "GO"}:
        blockers.extend(_strings(manifest.get("blockers")) or ["commercial_asset_manifest_no_go"])
    go = bool(payload.get("commercial_assets_go")) and not blockers
    return _contract(
        schema_version=ASSET_GRAPH_SCHEMA,
        status="completed" if go else "blocked",
        go=go,
        blockers=blockers,
        source={
            "asset_manifest_path": payload.get("asset_manifest_path") or manifest.get("manifest_path"),
            "provider_evidence_count": len(payload.get("provider_evidence") or []),
            "placeholder_only": bool(payload.get("placeholder_only")),
        },
    )


def build_cocos_bridge_evidence_contract(ecosystem: dict[str, Any] | None) -> dict[str, Any]:
    payload = _dict_from(ecosystem)
    if _is_contract(payload, COCOS_BRIDGE_EVIDENCE_SCHEMA):
        return payload
    blockers: list[str] = []
    if not payload:
        blockers.append("cocos_ecosystem_bridge_missing")
    if _has_non_real_status(payload):
        blockers.append("cocos_bridge_not_real_execution")
    blockers.extend(_strings(payload.get("blockers")))
    failure_class = str(payload.get("failure_class") or "")
    if failure_class:
        blockers.append(failure_class)
    if str(payload.get("bridge_mode") or "").lower() in {"filesystem", "filesystem_only"}:
        blockers.append("filesystem_only_bridge_claim")
    if str(payload.get("bridge_mode") or "").lower() == "report_only" and not payload.get("bridge_runner_evidence"):
        blockers.append("report_only_bridge_without_fresh_runner")
    go = bool(payload.get("ecosystem_integration_go")) and not blockers
    if not go and "cocos_ecosystem_bridge_missing" not in blockers:
        blockers.append("cocos_ecosystem_bridge_missing")
    return _contract(
        schema_version=COCOS_BRIDGE_EVIDENCE_SCHEMA,
        status="completed" if go else "blocked",
        go=go,
        blockers=blockers,
        source={
            "evidence_path": payload.get("evidence_path"),
            "bridge_mode": payload.get("bridge_mode"),
            "has_bridge_runner_evidence": bool(payload.get("bridge_runner_evidence")),
            "checks": payload.get("checks") if isinstance(payload.get("checks"), dict) else {},
        },
    )


def build_same_project_patch_ledger_contract(patch_ledger: dict[str, Any] | None) -> dict[str, Any]:
    payload = _dict_from(patch_ledger)
    if _is_contract(payload, SAME_PROJECT_PATCH_LEDGER_SCHEMA):
        return payload
    entries = [entry for entry in payload.get("entries") or [] if isinstance(entry, dict)]
    blockers = _strings(payload.get("blockers"))
    if not payload:
        blockers.append("same_project_patch_ledger_missing")
    if _has_non_real_status(payload):
        blockers.append("same_project_patch_not_real_execution")
    if not entries:
        blockers.append("same_project_worker_patch_missing")
    for entry in entries:
        adapter = str(entry.get("worker_adapter") or entry.get("adapter") or entry.get("capability_adapter") or "").strip().lower()
        if adapter in _NON_IMPLEMENTATION_ADAPTERS:
            blockers.append("same_project_patch_non_provider_adapter")
        satisfaction_mode = str(entry.get("satisfaction_mode") or "").strip().lower()
        if adapter in {"existing_same_project_evidence", "reference_evidence"} or satisfaction_mode in {
            "existing_same_project_evidence",
            "reused_reference_only",
        }:
            blockers.append("fresh_cli_execution_missing")
        if entry.get("implementation_gate_satisfied") is False:
            blockers.append("fresh_cli_execution_missing")
        if str(entry.get("execution_visibility_mode") or "") == "human_visible_cli_enforced" and not _visible_cli_session_valid(entry):
            blockers.append("human_visible_cli_metadata_missing")
        if _provider_visible_cli_required(entry) and not _provider_visible_cli_session_valid(entry):
            blockers.append("direct_provider_visible_cli_metadata_missing")
        if entry.get("fallback_only"):
            blockers.append("fallback_provider_unavailable")
        if entry.get("fallback_provider") and not entry.get("fallback_provider_live_proof"):
            blockers.append("fallback_provider_unavailable")
        mutation_result = _dict_from(entry.get("mutation_result"))
        changed_files = mutation_result.get("changed_files") or entry.get("changed_files") or []
        final_test_status = str(mutation_result.get("final_test_status") or entry.get("final_test_status") or "").strip().lower()
        attempts = entry.get("attempts") if isinstance(entry.get("attempts"), list) else []
        if entry.get("status") == "completed":
            if not attempts and not entry.get("attempt_id") and not entry.get("child_attempt_id"):
                blockers.append("same_project_patch_attempts_missing")
            if not entry.get("receipt_id") or not entry.get("child_run_id") or not (entry.get("child_attempt_id") or entry.get("attempt_id")):
                blockers.append("fresh_cli_execution_missing")
            if not changed_files:
                blockers.append("same_project_patch_changed_files_missing")
            if final_test_status != "passed":
                blockers.append("same_project_patch_tests_not_passed")
        if entry.get("product_implementation_by_operator_fallback"):
            blockers.append("operator_fallback_product_implementation_not_allowed")
    failed_entries = [entry for entry in entries if entry.get("status") != "completed"]
    if failed_entries:
        blockers.append("same_project_task_card_patch_failed")
    go = bool(payload.get("same_project_worker_patch_go")) and entries and not blockers
    return _contract(
        schema_version=SAME_PROJECT_PATCH_LEDGER_SCHEMA,
        status="completed" if go else "failed" if failed_entries else "blocked",
        go=bool(go),
        blockers=blockers,
        source={
            "ledger_path": payload.get("ledger_path"),
            "task_card_count": payload.get("task_card_count"),
            "completed_count": payload.get("completed_count"),
            "entry_count": len(entries),
            "next_continuation_command": payload.get("next_continuation_command"),
        },
    )


def build_build_ledger(build: dict[str, Any] | None) -> dict[str, Any]:
    payload = _dict_from(build)
    if _is_contract(payload, BUILD_LEDGER_SCHEMA):
        return payload
    blockers: list[str] = []
    if not payload:
        blockers.append("cocos_build_missing")
    if _has_non_real_status(payload):
        blockers.append("cocos_build_not_real_execution")
    exit_code = payload.get("creator_exit_code")
    if not _is_cocos_success_exit_code(exit_code):
        blockers.append("cocos_build_nonzero_exit")
    if payload.get("fatal_marker_detected"):
        blockers.append("cocos_build_fatal_marker_detected")
    if not payload.get("artifact_success"):
        blockers.append("cocos_build_no_artifact_success")
    if not payload.get("build_output_path"):
        blockers.append("cocos_build_output_path_missing")
    go = bool(payload) and not blockers
    return _contract(
        schema_version=BUILD_LEDGER_SCHEMA,
        status="completed" if go else "failed" if payload else "blocked",
        go=go,
        blockers=blockers,
        source={
            "build_command": payload.get("build_command"),
            "creator_exit_code": exit_code,
            "artifact_path": payload.get("build_output_path"),
            "artifact_success": bool(payload.get("artifact_success")),
            "fatal_markers": payload.get("fatal_markers") or [],
            "missing_classes": payload.get("missing_classes") or [],
            "error_summary": payload.get("error_summary") or [],
        },
    )


def build_browser_playtest_ledger(playtest: dict[str, Any] | None) -> dict[str, Any]:
    payload = _dict_from(playtest)
    if _is_contract(payload, BROWSER_PLAYTEST_LEDGER_SCHEMA):
        return payload
    blockers: list[str] = []
    if not payload:
        blockers.append("browser_playtest_missing")
    if _has_non_real_status(payload):
        blockers.append("browser_playtest_not_real_execution")
    failure_class = str(payload.get("failure_class") or "")
    if failure_class:
        blockers.append(f"browser_playtest_{failure_class}")
    if str(payload.get("status") or "").lower() in {"failed", "blocked"}:
        blockers.append("browser_playtest_execution_failed")
    if payload and not bool(payload.get("passed") or payload.get("playtest_go")):
        blockers.append("browser_playtest_no_go")
    quality_blockers = _strings(
        payload.get("quality_blockers") or payload.get("visual_quality_blockers") or payload.get("playtest_blockers")
    )
    blockers.extend(quality_blockers)
    canvas_hashes = _strings(payload.get("canvas_hashes"))
    screenshot_hashes = _strings(payload.get("screenshot_hashes"))
    action_screenshot_hashes = screenshot_hashes[:2]
    if len(action_screenshot_hashes) >= 2 and len(set(action_screenshot_hashes)) == 1:
        blockers.append("browser_screenshot_static_after_actions")
    elif len(action_screenshot_hashes) < 2 and len(canvas_hashes) >= 2 and len(set(canvas_hashes)) == 1:
        blockers.append("browser_canvas_hash_static_after_actions")
    if payload.get("desktop_splash_detected"):
        blockers.append("desktop_cocos_splash_only")
    if payload.get("desktop_runtime_started") is False:
        blockers.append("desktop_runtime_not_started")
    screenshots = list(payload.get("screenshots") or [])
    if not screenshots:
        blockers.append("browser_playtest_screenshots_missing")
    if not payload.get("url"):
        blockers.append("browser_http_launch_missing")
    console_and_page_errors = [*list(payload.get("console_errors") or []), *list(payload.get("page_errors") or [])]
    runtime_errors = runtime_error_markers(console_and_page_errors)
    if console_and_page_errors:
        blockers.append("browser_console_or_page_errors")
    if runtime_errors:
        blockers.append("browser_or_audio_runtime_error")
    feature_coverage = _dict_from(payload.get("feature_coverage"))
    required_features = _strings(payload.get("required_playtest_features"))
    commercial_features = _strings(payload.get("commercial_playtest_features"))
    missing_required_features = [key for key in required_features if not feature_coverage.get(key)]
    missing_commercial_features = [key for key in commercial_features if not feature_coverage.get(key)]
    if missing_required_features:
        blockers.append("browser_required_playtest_features_missing")
        blockers.extend(f"missing_playtest_feature_{key}" for key in missing_required_features)
    if missing_commercial_features:
        blockers.append("browser_commercial_playtest_features_missing")
        blockers.extend(f"missing_commercial_feature_{key}" for key in missing_commercial_features)
    if not feature_coverage.get("mobilePortraitUi"):
        blockers.append("mobile_viewport_evidence_missing")
    audio_runtime_proof = {
        "audioPlaybackVerified": bool(feature_coverage.get("audioPlaybackVerified")),
        "bgmStarted": bool(feature_coverage.get("bgmStarted")),
        "sfxPlaybackVerified": bool(feature_coverage.get("sfxPlaybackVerified")),
        "volumeToggleUsable": bool(feature_coverage.get("volumeToggleUsable")),
    }
    if not audio_runtime_proof["audioPlaybackVerified"]:
        blockers.append("audio_runtime_not_verified")
    if not audio_runtime_proof["bgmStarted"]:
        blockers.append("bgm_runtime_not_verified")
    if not audio_runtime_proof["sfxPlaybackVerified"]:
        blockers.append("sfx_runtime_not_verified")
    if not audio_runtime_proof["volumeToggleUsable"]:
        blockers.append("volume_toggle_missing")
    go = bool(payload) and not blockers
    return _contract(
        schema_version=BROWSER_PLAYTEST_LEDGER_SCHEMA,
        status="completed" if go else "failed" if payload else "blocked",
        go=go,
        blockers=blockers,
        source={
            "url": payload.get("url"),
            "screenshot_count": len(screenshots),
            "result_path": payload.get("result_path"),
            "runtime_error_markers": runtime_errors,
            "audio_runtime_proof": audio_runtime_proof,
            "quality_blockers": quality_blockers,
            "canvas_hash_count": len(canvas_hashes),
            "screenshot_hash_count": len(screenshot_hashes),
            "desktop_runtime_started": payload.get("desktop_runtime_started"),
            "desktop_splash_detected": bool(payload.get("desktop_splash_detected")),
            "feature_coverage_keys": sorted(feature_coverage),
            "missing_required_features": missing_required_features,
            "missing_commercial_features": missing_commercial_features,
        },
    )


def build_gameplay_semantic_evidence(
    gameplay: dict[str, Any] | None = None,
    *,
    feature_coverage: dict[str, Any] | None = None,
    playtest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _dict_from(gameplay)
    if _is_contract(payload, GAMEPLAY_SEMANTIC_EVIDENCE_SCHEMA):
        return payload
    features = _merge_dicts(_dict_from(_dict_from(playtest).get("feature_coverage")), _dict_from(feature_coverage), _dict_from(payload.get("feature_coverage")))
    traces = _semantic_trace_map(payload)
    blockers: list[str] = []
    if payload and _has_non_real_status(payload):
        blockers.append("gameplay_semantic_not_real_execution")
    if features and not payload:
        blockers.append("feature_flag_only_evidence")
    if payload.get("events") and not traces:
        blockers.append("event_only_gameplay_evidence")
    if payload.get("runtime_phase") and not payload.get("model_transition_traces"):
        blockers.append("model_transition_trace_missing")
    if payload.get("trace_source") in {"dom", "canvas", "browser_event", "runtime_hook"}:
        blockers.append("runtime_hook_not_semantic_model")
    blockers.extend(_template_leak_blockers(payload))
    required_traces = _required_semantic_traces(payload, traces)
    if not traces and not _has_model_transition_traces(payload):
        blockers.append("semantic_model_transition_trace_missing")
    for trace_name in required_traces:
        if not _has_semantic_trace(payload, traces, trace_name):
            blockers.append(f"semantic_{trace_name}_trace_missing")
    go = not blockers
    return _contract(
        schema_version=GAMEPLAY_SEMANTIC_EVIDENCE_SCHEMA,
        status="completed" if go else "blocked",
        go=go,
        blockers=blockers,
        source={
            "board_size": _board_size_source(payload),
            "piece_shape_count": _piece_shape_count(payload),
            "candidate_count": _candidate_count(payload),
            "trace_keys": sorted(traces),
            "required_trace_keys": sorted(required_traces),
            "feature_coverage_keys": sorted(features),
            "baseline_only": bool(payload.get("baseline_only")),
            "template_leak_checked": True,
        },
    )


def build_product_body_evidence(
    product_body: dict[str, Any] | None = None,
    *,
    gameplay_semantic_evidence: dict[str, Any] | None = None,
    playtest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _dict_from(product_body)
    if _is_contract(payload, PRODUCT_BODY_EVIDENCE_SCHEMA):
        return payload
    playtest_payload = _dict_from(playtest)
    blockers: list[str] = []
    if payload and _has_non_real_status(payload):
        blockers.append("product_body_not_real_execution")
    if payload.get("runtime_hook") or payload.get("runtimeHook") or playtest_payload.get("runtime_hook"):
        blockers.append("runtime_hook_not_product_body")
    if payload.get("canvas_only") or payload.get("canvasOnly") or playtest_payload.get("canvas_only"):
        blockers.append("canvas_only_product_body")
    if payload.get("events") and not _has_component_binding(payload):
        blockers.append("event_only_gameplay_evidence")
    if payload.get("feature_coverage") and not _has_component_binding(payload):
        blockers.append("feature_flag_only_evidence")
    if payload.get("empty_component_only"):
        blockers.append("empty_component_shell_not_runtime_product_body")
    blockers.extend(_template_leak_blockers(payload))
    if not _has_component_binding(payload):
        blockers.append("cocos_component_binding_missing")
    if not _has_scene_body(payload):
        blockers.append("scene_product_body_missing")
    semantic = _dict_from(gameplay_semantic_evidence)
    if semantic and not semantic.get("go"):
        blockers.extend(_strings(semantic.get("blockers")))
    elif not semantic:
        blockers.append("gameplay_semantic_evidence_missing")
    go = not blockers
    return _contract(
        schema_version=PRODUCT_BODY_EVIDENCE_SCHEMA,
        status="completed" if go else "blocked",
        go=go,
        blockers=blockers,
        source={
            "component_binding_count": _component_binding_count(payload),
            "scene_node_count": _scene_node_count(payload),
            "semantic_go": bool(semantic.get("go")) if semantic else False,
            "product_body_path": payload.get("product_body_path") or payload.get("evidence_path"),
            "baseline_only": bool(payload.get("baseline_only")),
        },
    )


def build_commercial_final_gate_evidence(
    *,
    technical_smoke_go: bool,
    production_scaffold_go: bool,
    require_commercial: bool,
    require_cocos_ecosystem: bool,
    require_live_agent_roles: bool,
    require_human_player_review: bool,
    asset_graph: dict[str, Any],
    cocos_bridge_evidence: dict[str, Any],
    same_project_patch_ledger: dict[str, Any],
    build_ledger: dict[str, Any],
    browser_playtest_ledger: dict[str, Any],
    product_feature_depth_go: bool,
    product_feature_blockers: list[str],
    live_role_provider_proof_go: bool,
    human_player_review_go: bool,
    gameplay_semantic_evidence: dict[str, Any] | None = None,
    product_body_evidence: dict[str, Any] | None = None,
    reference_quality_evidence: dict[str, Any] | None = None,
    require_ai_surrogate_playtest: bool = False,
    ai_surrogate_playtest_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gameplay_semantic_contract = gameplay_semantic_evidence or build_gameplay_semantic_evidence(None)
    product_body_contract = product_body_evidence or build_product_body_evidence(
        None,
        gameplay_semantic_evidence=gameplay_semantic_contract,
    )
    reference_quality_contract = _dict_from(reference_quality_evidence)
    ai_surrogate_contract = _ai_surrogate_contract(ai_surrogate_playtest_evidence)
    machine_blockers: list[str] = []
    if require_commercial:
        for contract in [
            asset_graph,
            same_project_patch_ledger,
            build_ledger,
            browser_playtest_ledger,
            gameplay_semantic_contract,
            product_body_contract,
        ]:
            if not contract.get("go"):
                machine_blockers.extend(_strings(contract.get("blockers")))
            if _dict_from(contract.get("source")).get("baseline_only"):
                machine_blockers.append("baseline_only_cannot_pass_commercial_final_gate")
        if require_ai_surrogate_playtest:
            if not ai_surrogate_contract.get("ai_surrogate_playtest_go"):
                machine_blockers.extend(_strings(ai_surrogate_contract.get("blockers")) or ["ai_surrogate_playtest_missing"])
        if reference_quality_contract and not reference_quality_contract.get("go"):
            machine_blockers.extend(_strings(reference_quality_contract.get("blockers")) or ["reference_quality_no_go"])
        if not product_feature_depth_go:
            machine_blockers.extend(product_feature_blockers or ["product_feature_depth_missing"])
    if require_cocos_ecosystem and not cocos_bridge_evidence.get("go"):
        machine_blockers.extend(_strings(cocos_bridge_evidence.get("blockers")) or ["cocos_ecosystem_bridge_missing"])
    if require_live_agent_roles and not live_role_provider_proof_go:
        machine_blockers.append("live_role_provider_proof_missing")
    machine_blockers = _dedupe(machine_blockers)
    blocked_downstream_stages = _blocked_downstream_stages(
        build_ledger=build_ledger,
        browser_playtest_ledger=browser_playtest_ledger,
        product_feature_depth_go=product_feature_depth_go,
        product_feature_blockers=product_feature_blockers,
    )

    blockers = list(machine_blockers)
    if require_commercial and not human_player_review_go:
        blockers.append("awaiting_human_player_review")
    blockers = _dedupe(blockers)

    machine_evidence_go = not machine_blockers
    awaiting_human_only = machine_evidence_go and require_commercial and not human_player_review_go
    commercial_playable_go = bool(
        require_commercial
        and machine_evidence_go
        and human_player_review_go
    )
    go_no_go = "GO" if commercial_playable_go else "AWAITING_HUMAN_REVIEW" if awaiting_human_only else "NO-GO"
    return {
        "schema_version": COMMERCIAL_FINAL_GATE_EVIDENCE_SCHEMA,
        "status": "completed" if commercial_playable_go else "blocked" if awaiting_human_only else "failed",
        "go_no_go": go_no_go,
        "technical_smoke_go": bool(technical_smoke_go),
        "production_scaffold_go": bool(production_scaffold_go),
        "machine_evidence_go": machine_evidence_go,
        "commercial_playable_go": commercial_playable_go,
        "human_player_review_go": bool(human_player_review_go),
        "blockers": blockers,
        "machine_blockers": machine_blockers,
        "blocked_downstream_stages": blocked_downstream_stages,
        "awaiting_human_player_review": awaiting_human_only,
        "contracts": {
            "asset_graph": asset_graph,
            "cocos_bridge_evidence": cocos_bridge_evidence,
            "same_project_patch_ledger": same_project_patch_ledger,
            "build_ledger": build_ledger,
            "browser_playtest_ledger": browser_playtest_ledger,
            "gameplay_semantic_evidence": gameplay_semantic_contract,
            "product_body_evidence": product_body_contract,
            "reference_quality_evidence": reference_quality_contract,
            "ai_surrogate_playtest_evidence": ai_surrogate_contract,
        },
    }


def build_product_depth_evidence(
    *,
    product_depth: dict[str, Any] | None = None,
    feature_coverage: dict[str, Any] | None = None,
    player_visible_checks: dict[str, Any] | None = None,
    playtest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _dict_from(product_depth)
    if _is_contract(payload, PRODUCT_DEPTH_EVIDENCE_SCHEMA):
        return payload
    playtest_payload = _dict_from(playtest)
    features = _merge_dicts(
        _dict_from(playtest_payload.get("feature_coverage")),
        _dict_from(feature_coverage),
        _dict_from(payload.get("feature_coverage")),
    )
    visible = _merge_dicts(_dict_from(player_visible_checks), _dict_from(payload.get("player_visible_checks")))
    level_goals = _level_goals_from(payload, features, visible)
    distinct_level_goal_count = _distinct_level_goal_count(level_goals, payload, features, visible)

    blockers: list[str] = []
    if payload and _has_non_real_status(payload):
        blockers.append("product_depth_not_real_execution")
    if distinct_level_goal_count < 8:
        blockers.append("levels_not_distinct_or_less_than_eight")
    if _contains_mojibake_text(level_goals):
        blockers.append("level_goal_labels_mojibake")
    proof_map = {"eightDistinctLevelGoals": distinct_level_goal_count >= 8}
    for feature_name, blocker in _PRODUCT_DEPTH_REQUIREMENTS.items():
        proof_map[feature_name] = _feature_proven(feature_name, features, visible, payload)
        if not proof_map[feature_name]:
            blockers.append(blocker)
    if payload.get("events") and not any(proof_map.values()):
        blockers.append("event_only_player_visible_evidence")

    go = not blockers
    return _contract(
        schema_version=PRODUCT_DEPTH_EVIDENCE_SCHEMA,
        status="completed" if go else "blocked",
        go=go,
        blockers=blockers,
        source={
            "distinct_level_goal_count": distinct_level_goal_count,
            "level_goals": level_goals,
            "level_goal_labels_readable": not _contains_mojibake_text(level_goals),
            "proof_map": proof_map,
            "feature_coverage_keys": sorted(features),
            "player_visible_check_keys": sorted(visible),
            "events_recorded": len(payload.get("events") or []),
            "screenshots": list(payload.get("screenshots") or playtest_payload.get("screenshots") or []),
        },
    )


def build_human_review_packet(
    *,
    product_depth_evidence: dict[str, Any],
    evidence_contracts: dict[str, Any],
    manual_player_evidence: dict[str, Any] | None = None,
    screenshots: list[Any] | None = None,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    manual = _dict_from(manual_player_evidence)
    accepted_by_human = bool(manual.get("accepted_by_human") and manual.get("reviewer") and manual.get("evidence_path"))
    machine_blockers = _dedupe(
        [
            *list(blockers or []),
            *[
                blocker
                for contract in evidence_contracts.values()
                if isinstance(contract, dict)
                for blocker in _strings(contract.get("blockers"))
            ],
        ]
    )
    ready_for_human_review = not machine_blockers and bool(product_depth_evidence.get("go"))
    status = "completed" if accepted_by_human and ready_for_human_review else "AWAITING_HUMAN_REVIEW" if ready_for_human_review else "blocked"
    return {
        "schema_version": HUMAN_REVIEW_PACKET_SCHEMA,
        "status": status,
        "reviewer_required": True,
        "accepted_by_human": accepted_by_human,
        "human_player_review_go": accepted_by_human and ready_for_human_review,
        "commercial_playable_go_allowed": accepted_by_human and ready_for_human_review,
        "ready_for_human_review": ready_for_human_review,
        "machine_blockers": machine_blockers,
        "product_depth_evidence": product_depth_evidence,
        "screenshots": [str(item) for item in screenshots or []],
        "review_items": [
            "eight distinct level goals",
            "shop and skin ownership states",
            "equipped skin visual change",
            "Chinese UI panels",
            "level flow",
            "failure and revive feedback",
            "audio, BGM, SFX, and volume behavior",
            "animation and feedback polish",
        ],
        "manual_player_evidence": manual,
        "forbidden_claim": "unattended_packet_is_not_human_review",
    }


def runtime_error_markers(errors: list[Any]) -> list[str]:
    markers = ("NotSupportedError", "media", "audio", "decode", "play() failed", "DOMException")
    result: list[str] = []
    for error in errors:
        text = str(error)
        if any(marker.lower() in text.lower() for marker in markers):
            result.append(text[:500])
    return result


def _contract(*, schema_version: str, status: str, go: bool, blockers: list[str], source: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "status": status,
        "go": bool(go),
        "blockers": _dedupe(blockers),
        "source": source,
    }


def _ai_surrogate_contract(evidence: dict[str, Any] | None) -> dict[str, Any]:
    payload = _dict_from(evidence)
    if not payload:
        return {
            "schema_version": AI_PLAYTEST_QUALITY_SCHEMA,
            "status": "blocked",
            "ai_surrogate_playtest_go": False,
            "production_vertical_slice_go": False,
            "blockers": ["ai_surrogate_playtest_missing"],
        }
    if payload.get("schema_version") == AI_PLAYTEST_QUALITY_SCHEMA:
        return payload
    return evaluate_ai_surrogate_playtest(payload)


def _blocked_downstream_stages(
    *,
    build_ledger: dict[str, Any],
    browser_playtest_ledger: dict[str, Any],
    product_feature_depth_go: bool,
    product_feature_blockers: list[str],
) -> list[str]:
    stages: list[str] = []
    for contract, fallback_stage in [
        (build_ledger, "cocos_build"),
        (browser_playtest_ledger, "browser_playtest"),
    ]:
        if "blocked_by_same_project_worker" not in _strings(contract.get("blockers")):
            continue
        source = _dict_from(contract.get("source"))
        blocked = source.get("blocked_downstream_stages")
        if isinstance(blocked, list):
            stages.extend(str(item) for item in blocked)
        else:
            stages.append(str(source.get("stage") or fallback_stage))
    if not product_feature_depth_go and "blocked_by_same_project_worker" in _strings(product_feature_blockers):
        stages.append("product_depth")
    return _dedupe(stages)


def _dict_from(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _is_cocos_success_exit_code(value: Any) -> bool:
    if value is None:
        return True
    if value in COCOS_BUILD_SUCCESS_EXIT_CODES:
        return True
    try:
        return int(value) in COCOS_BUILD_SUCCESS_EXIT_CODES
    except (TypeError, ValueError):
        return False


def _merge_dicts(*values: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for value in values:
        merged.update(value)
    return merged


def _is_contract(payload: dict[str, Any], schema_version: str) -> bool:
    return (
        payload.get("schema_version") == schema_version
        and "go" in payload
        and isinstance(payload.get("blockers"), list)
        and isinstance(payload.get("source"), dict)
    )


def _level_goals_from(*payloads: dict[str, Any]) -> list[str]:
    for payload in payloads:
        for key in ("level_goals", "levelGoals", "distinct_level_goals"):
            raw = payload.get(key)
            if isinstance(raw, list):
                goals = []
                for item in raw:
                    if isinstance(item, dict):
                        text = str(item.get("goal") or item.get("name") or item.get("id") or "").strip()
                    else:
                        text = str(item).strip()
                    if text:
                        goals.append(text)
                if goals:
                    return goals
    return []


def _distinct_level_goal_count(level_goals: list[str], *payloads: dict[str, Any]) -> int:
    explicit_counts = []
    for payload in payloads:
        for key in ("distinctLevelGoalCount", "distinct_level_goal_count", "levelGoalCount"):
            value = payload.get(key)
            if isinstance(value, int):
                explicit_counts.append(value)
            elif isinstance(value, str) and value.isdigit():
                explicit_counts.append(int(value))
    unique_goals = len({goal.lower() for goal in level_goals})
    return max([unique_goals, *explicit_counts], default=0)


def _board_is_10x10(payload: dict[str, Any]) -> bool:
    board = _dict_from(payload.get("board_state") or payload.get("board"))
    runtime_state = _dict_from(payload.get("engine_native_runtime_state"))
    size = payload.get("board_size") or board.get("size") or runtime_state.get("board_size")
    if isinstance(size, str):
        return size.lower().replace(" ", "") in {"10x10", "10*10"}
    if isinstance(size, (list, tuple)) and len(size) == 2:
        return list(size) == [10, 10]
    rows = board.get("rows") or payload.get("rows") or runtime_state.get("rows")
    cols = board.get("cols") or board.get("columns") or payload.get("cols") or payload.get("columns") or runtime_state.get("cols")
    return rows == 10 and cols == 10


def _board_size_source(payload: dict[str, Any]) -> Any:
    board = _dict_from(payload.get("board_state") or payload.get("board"))
    runtime_state = _dict_from(payload.get("engine_native_runtime_state"))
    return payload.get("board_size") or board.get("size") or runtime_state.get("board_size") or {
        "rows": board.get("rows") or runtime_state.get("rows"),
        "cols": board.get("cols") or board.get("columns") or runtime_state.get("cols"),
    }


def _required_semantic_traces(payload: dict[str, Any], traces: dict[str, Any]) -> list[str]:
    explicit = _strings(
        payload.get("required_semantic_traces")
        or payload.get("requiredSemanticTraces")
        or _dict_from(payload.get("state_model_contract")).get("transitions")
    )
    if explicit:
        return [_trace_key(value) for value in explicit]
    model_traces = payload.get("model_transition_traces")
    if isinstance(model_traces, dict) and model_traces:
        return [_trace_key(key) for key in model_traces]
    if isinstance(model_traces, list) and model_traces:
        result = []
        for item in model_traces:
            trace = item.get("trace") or item.get("transition") if isinstance(item, dict) else item
            if trace:
                result.append(_trace_key(str(trace)))
        return result
    transition_examples = payload.get("transition_examples")
    if isinstance(transition_examples, list) and transition_examples:
        result = []
        for item in transition_examples:
            if not isinstance(item, dict):
                continue
            trace = item.get("trace") or item.get("transition") or item.get("verb")
            if trace:
                result.append(_trace_key(str(trace)))
        if result:
            return result
    contract = _dict_from(payload.get("semantic_trace_contract"))
    covered_verbs = _strings(contract.get("covered_verbs"))
    if covered_verbs:
        return [_trace_key(value) for value in covered_verbs]
    return [_trace_key(key) for key in traces]


def _trace_key(value: str) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def _has_model_transition_traces(payload: dict[str, Any]) -> bool:
    model_traces = payload.get("model_transition_traces")
    if isinstance(model_traces, dict):
        return bool(model_traces)
    if isinstance(model_traces, list):
        return bool(model_traces)
    transition_examples = payload.get("transition_examples")
    if isinstance(transition_examples, list) and transition_examples:
        return True
    contract = _dict_from(payload.get("semantic_trace_contract"))
    if _strings(contract.get("covered_verbs")):
        return True
    return bool(payload.get("semantic_traces") or payload.get("traces"))


def _semantic_trace_map(payload: dict[str, Any]) -> dict[str, Any]:
    traces = _dict_from(payload.get("semantic_traces") or payload.get("traces"))
    model_traces = payload.get("model_transition_traces")
    if isinstance(model_traces, dict):
        traces.update({_trace_key(str(key)): value for key, value in model_traces.items()})
    elif isinstance(model_traces, list):
        for item in model_traces:
            if isinstance(item, dict):
                key = item.get("trace") or item.get("transition") or item.get("verb") or item.get("id")
                if key:
                    traces.setdefault(_trace_key(str(key)), item)
            elif item:
                traces.setdefault(_trace_key(str(item)), True)
    transition_examples = payload.get("transition_examples")
    if isinstance(transition_examples, list):
        for index, item in enumerate(transition_examples):
            if not isinstance(item, dict):
                continue
            key = item.get("trace") or item.get("transition") or item.get("verb") or f"transition_{index + 1}"
            traces.setdefault(_trace_key(str(key)), item)
            for event in _strings(item.get("events")):
                traces.setdefault(_trace_key(event), item)
    contract = _dict_from(payload.get("semantic_trace_contract"))
    for verb in _strings(contract.get("covered_verbs")):
        traces.setdefault(_trace_key(verb), True)
    return traces


_BLOCK_PUZZLE_TEMPLATE_MARKERS = {
    "10x10",
    "candidate_tray",
    "candidatetray",
    "anti_stall",
    "boardmodel",
    "piecemodel",
    "ruleengine",
    "line_clear",
    "candidate_refresh",
    "block_puzzle",
}


def _template_leak_blockers(payload: dict[str, Any]) -> list[str]:
    if payload.get("template_leak_detected"):
        return ["template_leak_detected"]
    if payload.get("block_puzzle_required") or payload.get("allows_block_puzzle_template"):
        return []
    source = payload.get("game_design_spec") or payload.get("source_requirements") or payload.get("requirements")
    if not source:
        return []
    source_text = json.dumps(source, ensure_ascii=False).lower()
    if any(marker in source_text for marker in _BLOCK_PUZZLE_TEMPLATE_MARKERS):
        return []
    payload_text = json.dumps(
        {
            "scene_nodes": payload.get("scene_nodes") or payload.get("sceneNodes"),
            "components": payload.get("cocos_component_bindings") or payload.get("component_bindings") or payload.get("components"),
            "semantic_traces": payload.get("semantic_traces") or payload.get("traces"),
            "model_transition_traces": payload.get("model_transition_traces"),
            "board_state": payload.get("board_state") or payload.get("board"),
        },
        ensure_ascii=False,
    ).lower()
    return ["template_leak_detected"] if any(marker in payload_text for marker in _BLOCK_PUZZLE_TEMPLATE_MARKERS) else []


def _has_piece_model(payload: dict[str, Any]) -> bool:
    return _piece_shape_count(payload) > 0 or bool(payload.get("piece_model") or payload.get("pieceModel"))


def _piece_shape_count(payload: dict[str, Any]) -> int:
    shapes = payload.get("piece_shapes") or payload.get("pieceShapes") or _dict_from(payload.get("piece_model")).get("shapes")
    runtime_state = _dict_from(payload.get("engine_native_runtime_state"))
    if not isinstance(shapes, list):
        shapes = runtime_state.get("piece_shapes") or runtime_state.get("pieceShapes")
    return len(shapes) if isinstance(shapes, list) else 0


def _candidate_tray_has_three(payload: dict[str, Any]) -> bool:
    return _candidate_count(payload) == 3


def _candidate_count(payload: dict[str, Any]) -> int:
    tray = payload.get("candidate_tray") or payload.get("candidateTray") or payload.get("candidates")
    if isinstance(tray, list):
        return len(tray)
    tray_dict = _dict_from(tray)
    runtime_state = _dict_from(payload.get("engine_native_runtime_state"))
    count = tray_dict.get("count") or payload.get("candidate_count") or payload.get("candidateCount") or runtime_state.get("candidate_batch_size")
    try:
        return int(count)
    except (TypeError, ValueError):
        return 0


def _has_semantic_trace(payload: dict[str, Any], traces: dict[str, Any], trace_name: str) -> bool:
    keys = {
        trace_name,
        f"{trace_name}_trace",
        f"{trace_name}_trace_path",
        trace_name.replace("_", ""),
    }
    return any(bool(payload.get(key) or traces.get(key)) for key in keys)


def _has_component_binding(payload: dict[str, Any]) -> bool:
    return _component_binding_count(payload) > 0


def _component_binding_count(payload: dict[str, Any]) -> int:
    bindings = payload.get("cocos_component_bindings") or payload.get("component_bindings") or payload.get("components")
    if not bindings and isinstance(payload.get("implemented_components"), list):
        bindings = payload.get("implemented_components")
    if not bindings:
        scene_contract = _dict_from(payload.get("scene_binding_contract"))
        contract_components = [
            scene_contract.get("component"),
            scene_contract.get("input_component"),
            *(_strings(scene_contract.get("components"))),
        ]
        bindings = [item for item in contract_components if item]
    if isinstance(bindings, list):
        return len(bindings)
    value = payload.get("component_binding_count") or payload.get("componentBindingCount")
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _visible_cli_session_valid(entry: dict[str, Any]) -> bool:
    session = _dict_from(entry.get("visible_cli_session"))
    required = ["pid", "argv", "cwd", "stdout_log_path", "stderr_log_path", "stream_log_path", "started_at"]
    if any(not session.get(key) for key in required):
        return False
    return str(session.get("status") or "") not in {"blocked", "unavailable"}


def _provider_visible_cli_required(entry: dict[str, Any]) -> bool:
    if bool(entry.get("provider_visible_cli_required")):
        return True
    return (
        str(entry.get("control_plane_visibility") or "").strip().lower() == "resident"
        and str(entry.get("provider_visibility") or "").strip().lower() == "direct_visible"
    )


def _provider_visible_cli_session_valid(entry: dict[str, Any]) -> bool:
    session = _dict_from(entry.get("provider_visible_cli_session"))
    required = ["argv", "cwd", "stdout_log_path", "stderr_log_path", "stream_log_path", "started_at"]
    if any(not session.get(key) for key in required):
        return False
    if not (session.get("provider_pid") or session.get("wrapper_pid")):
        return False
    return str(session.get("status") or "") not in {"blocked", "unavailable"}


def _has_scene_body(payload: dict[str, Any]) -> bool:
    return _scene_node_count(payload) > 0 or bool(
        payload.get("scene_path")
        or payload.get("sceneGraph")
        or payload.get("scene_bindings")
        or payload.get("scene_binding_contract")
    )


def _scene_node_count(payload: dict[str, Any]) -> int:
    nodes = payload.get("scene_nodes") or payload.get("sceneNodes") or payload.get("node_hierarchy")
    if isinstance(nodes, list):
        return len(nodes)
    scene_bindings = payload.get("scene_bindings")
    if isinstance(scene_bindings, list) and scene_bindings:
        count = 0
        for binding in scene_bindings:
            if not isinstance(binding, dict):
                continue
            count += 1
            count += len(binding.get("prefabs") or [])
            count += len(binding.get("components") or [])
        return count
    value = payload.get("scene_node_count") or payload.get("sceneNodeCount")
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _feature_proven(feature_name: str, *payloads: dict[str, Any]) -> bool:
    for payload in payloads:
        if bool(payload.get(feature_name)):
            return True
    return False


def _contains_mojibake_text(values: list[Any]) -> bool:
    text = "\n".join(str(value) for value in values)
    if not text:
        return False
    markers = [
        "鏂",
        "涓",
        "鐨",
        "寰",
        "杈",
        "娑",
        "闄",
        "褰",
        "绗",
        "鍏",
        "櫙",
        "棌",
        "姝",
        "€",
        "�",
    ]
    return any(marker in text for marker in markers)


def _strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str) and value:
        return [value]
    return []


def _has_non_real_status(payload: dict[str, Any]) -> bool:
    status = str(payload.get("status") or payload.get("execution_truth") or payload.get("evidence_mode") or "").lower()
    if status in _NON_REAL_STATUS:
        return True
    mode = str(payload.get("mode") or payload.get("delivery_mode") or "").lower()
    return mode in _NON_REAL_STATUS


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
