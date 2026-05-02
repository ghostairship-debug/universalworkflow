from __future__ import annotations

from typing import Any

from packages.contributions.games.cocos.e2e import COCOS_BUILD_SUCCESS_EXIT_CODES


COMMERCIAL_GAME_EVIDENCE_CONTRACT_SCHEMA = "commercial_game_evidence_contracts_v1"
ASSET_GRAPH_SCHEMA = "commercial_game_asset_graph_v1"
COCOS_BRIDGE_EVIDENCE_SCHEMA = "commercial_game_cocos_bridge_evidence_v1"
SAME_PROJECT_PATCH_LEDGER_SCHEMA = "commercial_game_same_project_patch_ledger_contract_v1"
BUILD_LEDGER_SCHEMA = "commercial_game_build_ledger_v1"
BROWSER_PLAYTEST_LEDGER_SCHEMA = "commercial_game_browser_playtest_ledger_v1"
COMMERCIAL_FINAL_GATE_EVIDENCE_SCHEMA = "commercial_game_final_gate_evidence_v1"
PRODUCT_DEPTH_EVIDENCE_SCHEMA = "commercial_game_product_depth_evidence_v1"
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
        if entry.get("fallback_only"):
            blockers.append("fallback_provider_unavailable")
        if entry.get("fallback_provider") and not entry.get("fallback_provider_live_proof"):
            blockers.append("fallback_provider_unavailable")
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
            "feature_coverage_keys": sorted(feature_coverage),
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
) -> dict[str, Any]:
    machine_blockers: list[str] = []
    if require_commercial:
        for contract in [asset_graph, same_project_patch_ledger, build_ledger, browser_playtest_ledger]:
            if not contract.get("go"):
                machine_blockers.extend(_strings(contract.get("blockers")))
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
    if require_human_player_review and not human_player_review_go:
        blockers.append("awaiting_human_player_review")
    blockers = _dedupe(blockers)

    machine_evidence_go = not machine_blockers
    awaiting_human_only = machine_evidence_go and require_human_player_review and not human_player_review_go
    commercial_playable_go = bool(
        require_commercial
        and machine_evidence_go
        and (human_player_review_go or not require_human_player_review)
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


def _feature_proven(feature_name: str, *payloads: dict[str, Any]) -> bool:
    for payload in payloads:
        if bool(payload.get(feature_name)):
            return True
    return False


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
