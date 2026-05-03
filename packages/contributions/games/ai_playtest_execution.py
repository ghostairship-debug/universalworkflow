from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.contributions.games.ai_playtest_lab import AI_PLAYTEST_MODES, AI_PLAYTEST_PLAN_SCHEMA
from packages.contributions.games.ai_playtest_quality import QUALITY_AREAS, evaluate_ai_surrogate_playtest


AI_PLAYTEST_EXECUTION_PACKET_SCHEMA = "universal_ai_playtest_execution_packet_v1"
AI_PLAYTEST_EXECUTION_REPORT_SCHEMA = "universal_ai_playtest_execution_report_v1"


def build_ai_quality_evidence_from_execution_packet(packet: dict[str, Any]) -> dict[str, Any]:
    mode_results = _mode_results(packet)
    findings = []
    screenshots: list[str] = []
    replay_artifacts: list[str] = []
    for mode, result in mode_results.items():
        for finding in _dict_list(result.get("findings")):
            finding.setdefault("mode", mode)
            findings.append(finding)
        screenshots.extend(_string_list(result.get("screenshots")))
        replay_artifacts.extend(_string_list(result.get("replay_artifacts")))
    return {
        "workflow_generated_product_go": bool(packet.get("workflow_generated_product_go")),
        "core_loop_playable": bool(packet.get("core_loop_playable")),
        "first_session_flow_go": bool(packet.get("first_session_flow_go")),
        "requirement_fidelity_go": bool(packet.get("requirement_fidelity_go")),
        "ai_playtest_modes_run": sorted(
            mode for mode, result in mode_results.items() if str(result.get("status") or "") == "completed"
        ),
        "area_scores": _area_scores(packet.get("area_scores")),
        "findings": findings,
        "screenshots": _dedupe(screenshots),
        "replay_artifacts": _dedupe(replay_artifacts),
        "engine_native_product_body": packet.get("engine_native_product_body"),
        "omitted_requirement_ids": _string_list(packet.get("omitted_requirement_ids")),
        "placeholder_only": bool(packet.get("placeholder_only")),
        "stale_evidence_reused": bool(packet.get("stale_evidence_reused")),
    }


def validate_ai_playtest_execution_packet(
    packet: dict[str, Any] | None,
    *,
    workspace_root: str | Path | None = None,
    require_artifact_files: bool = False,
) -> dict[str, Any]:
    payload = packet if isinstance(packet, dict) else {}
    blockers: list[str] = []
    if payload.get("schema_version") != AI_PLAYTEST_EXECUTION_PACKET_SCHEMA:
        blockers.append("ai_playtest_execution_packet_schema_invalid")
    plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else {}
    if plan.get("schema_version") != AI_PLAYTEST_PLAN_SCHEMA:
        blockers.append("ai_playtest_plan_missing_or_invalid")
    scripted_scenarios = _string_list(plan.get("scripted_scenarios"))
    state_assertions = _string_list(plan.get("state_assertions"))
    vision_targets = _string_list(plan.get("vision_review_targets"))
    planned_devices = _string_list(plan.get("device_matrix"))
    mode_results = _mode_results(payload)
    missing_modes = [mode for mode in AI_PLAYTEST_MODES if mode not in mode_results]
    if missing_modes:
        blockers.append("ai_playtest_execution_modes_missing")
    incomplete_modes = [
        mode for mode, result in mode_results.items() if str(result.get("status") or "") != "completed"
    ]
    if incomplete_modes:
        blockers.append("ai_playtest_execution_modes_incomplete")
    stale_modes = [mode for mode, result in mode_results.items() if not bool(result.get("fresh_run"))]
    if stale_modes:
        blockers.append("ai_playtest_fresh_run_missing")
    modes_missing_replay = [mode for mode, result in mode_results.items() if not _string_list(result.get("replay_artifacts"))]
    if modes_missing_replay:
        blockers.append("ai_playtest_replay_missing")
    modes_missing_screenshot = [mode for mode, result in mode_results.items() if not _string_list(result.get("screenshots"))]
    if modes_missing_screenshot:
        blockers.append("ai_playtest_screenshots_missing")
    console_modes = [
        mode
        for mode, result in mode_results.items()
        if _string_list(result.get("console_errors")) or _string_list(result.get("page_errors"))
    ]
    if console_modes:
        blockers.append("ai_playtest_console_or_page_errors")
    scenario_status = _named_status_map(payload.get("scripted_scenario_results"), name_key="scenario")
    missing_scenarios = [scenario for scenario in scripted_scenarios if scenario not in scenario_status]
    failed_scenarios = [
        scenario
        for scenario in scripted_scenarios
        if scenario in scenario_status and scenario_status[scenario] not in {"passed", "pass", "completed"}
    ]
    if missing_scenarios:
        blockers.append("scripted_scenario_coverage_missing")
    if failed_scenarios:
        blockers.append("scripted_scenario_no_go")
    assertion_status = _named_status_map(payload.get("state_assertion_results"), name_key="assertion")
    missing_assertions = [assertion for assertion in state_assertions if assertion not in assertion_status]
    failed_assertions = [
        assertion
        for assertion in state_assertions
        if assertion in assertion_status and assertion_status[assertion] not in {"passed", "pass", "completed"}
    ]
    if missing_assertions:
        blockers.append("state_assertion_coverage_missing")
    if failed_assertions:
        blockers.append("state_assertion_no_go")
    if require_artifact_files:
        missing_artifacts = _missing_artifacts(mode_results, workspace_root=workspace_root)
        if missing_artifacts:
            blockers.append("ai_playtest_artifact_file_missing")
    else:
        missing_artifacts = []
    device_results = _dict_list(payload.get("device_matrix_results"))
    failed_devices = [
        str(item.get("device") or index)
        for index, item in enumerate(device_results, start=1)
        if str(item.get("status") or "") not in {"passed", "pass", "completed"}
    ]
    if not device_results:
        blockers.append("device_matrix_results_missing")
    if failed_devices:
        blockers.append("device_matrix_no_go")
    completed_devices = {str(item.get("device") or "") for item in device_results if str(item.get("status") or "") in {"passed", "pass", "completed"}}
    missing_planned_devices = [device for device in planned_devices if device not in completed_devices]
    if missing_planned_devices:
        blockers.append("device_matrix_coverage_missing")
    performance = payload.get("performance_metrics") if isinstance(payload.get("performance_metrics"), dict) else {}
    if not performance:
        blockers.append("performance_metrics_missing")
    if _number(performance.get("min_fps")) < 45:
        blockers.append("performance_min_fps_below_floor")
    if _number(performance.get("input_latency_ms")) > 100:
        blockers.append("input_latency_above_floor")
    vision_review = payload.get("vision_review") if isinstance(payload.get("vision_review"), dict) else {}
    if not vision_review:
        blockers.append("vision_review_missing")
    if vision_review and not bool(vision_review.get("visual_go")):
        blockers.append("vision_review_no_go")
    if _string_list(vision_review.get("blockers")):
        blockers.append("vision_review_blockers_present")
    checked_vision_targets = set(_string_list(vision_review.get("targets_checked")))
    missing_vision_targets = [target for target in vision_targets if target not in checked_vision_targets]
    if missing_vision_targets:
        blockers.append("vision_target_coverage_missing")
    return {
        "schema_version": "universal_ai_playtest_execution_packet_validation_v1",
        "go": not blockers,
        "blockers": _dedupe(blockers),
        "missing_modes": missing_modes,
        "incomplete_modes": incomplete_modes,
        "stale_modes": stale_modes,
        "modes_missing_replay": modes_missing_replay,
        "modes_missing_screenshot": modes_missing_screenshot,
        "console_error_modes": console_modes,
        "missing_scenarios": missing_scenarios,
        "failed_scenarios": failed_scenarios,
        "missing_state_assertions": missing_assertions,
        "failed_state_assertions": failed_assertions,
        "failed_devices": failed_devices,
        "missing_planned_devices": missing_planned_devices,
        "missing_vision_targets": missing_vision_targets,
        "missing_artifacts": missing_artifacts,
        "artifact_existence_checked": bool(require_artifact_files),
    }


def evaluate_ai_playtest_execution_packet(
    packet: dict[str, Any] | None,
    *,
    workspace_root: str | Path | None = None,
    require_artifact_files: bool = False,
) -> dict[str, Any]:
    payload = packet if isinstance(packet, dict) else {}
    validation = validate_ai_playtest_execution_packet(
        payload,
        workspace_root=workspace_root,
        require_artifact_files=require_artifact_files,
    )
    quality_evidence = build_ai_quality_evidence_from_execution_packet(payload)
    if validation["blockers"]:
        quality_evidence["findings"] = [
            *quality_evidence.get("findings", []),
            {
                "finding_id": "ai_playtest_execution_packet_invalid",
                "severity": "P1",
                "category": "robustness",
                "observed": ",".join(validation["blockers"]),
            },
        ]
    quality = evaluate_ai_surrogate_playtest(quality_evidence)
    return {
        "schema_version": AI_PLAYTEST_EXECUTION_REPORT_SCHEMA,
        "go": bool(validation["go"] and quality["ai_surrogate_playtest_go"]),
        "validation": validation,
        "quality": quality,
        "quality_evidence": quality_evidence,
        "governance": quality["governance"],
    }


def _mode_results(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = packet.get("mode_results")
    if not isinstance(raw, dict):
        return {}
    return {str(mode): result for mode, result in raw.items() if isinstance(result, dict)}


def _missing_artifacts(mode_results: dict[str, dict[str, Any]], *, workspace_root: str | Path | None) -> list[str]:
    root = Path(workspace_root).resolve() if workspace_root is not None else None
    missing: list[str] = []
    for mode, result in mode_results.items():
        for field in ("replay_artifacts", "screenshots", "state_snapshots"):
            for raw_path in _string_list(result.get(field)):
                path = Path(raw_path)
                resolved = path if path.is_absolute() else (root / path if root is not None else path)
                if not resolved.exists():
                    missing.append(f"{mode}:{field}:{raw_path}")
    return missing


def _area_scores(value: Any) -> dict[str, int]:
    provided = value if isinstance(value, dict) else {}
    scores: dict[str, int] = {}
    for area, weight in QUALITY_AREAS.items():
        scores[area] = max(0, min(weight, int(_number(provided.get(area)))))
    return scores


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _named_status_map(value: Any, *, name_key: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in _dict_list(value):
        name = str(item.get(name_key) or item.get("name") or "").strip()
        if not name:
            continue
        result[name] = str(item.get("status") or "").strip()
    return result


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
