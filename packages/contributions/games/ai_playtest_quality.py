from __future__ import annotations

from typing import Any

from packages.contributions.games.engine_native_contract import build_engine_native_product_body_contract


AI_PLAYTEST_QUALITY_SCHEMA = "universal_ai_surrogate_playtest_quality_v1"
PRODUCTION_VERTICAL_SLICE_FLOOR_SCHEMA = "production_vertical_slice_floor_v1"

QUALITY_AREAS = {
    "requirement_fidelity": 12,
    "core_gameplay_correctness": 14,
    "player_experience": 12,
    "ui_ux_polish": 10,
    "art_direction": 10,
    "audio": 8,
    "input_feel": 10,
    "content_depth": 8,
    "performance": 8,
    "robustness": 8,
}
REQUIRED_AI_PLAYTEST_MODES = {
    "scripted_bot",
    "exploratory_bot",
    "persona_agent",
    "vision_reviewer",
    "design_red_team",
    "performance_agent",
    "device_matrix_agent",
    "regression_agent",
}
BLOCKING_SEVERITIES = {"P0", "P1"}


def evaluate_ai_surrogate_playtest(evidence: dict[str, Any] | None) -> dict[str, Any]:
    payload = evidence if isinstance(evidence, dict) else {}
    blockers: list[str] = []
    area_scores = _area_scores(payload)
    score = sum(score for score in area_scores.values())
    findings = _findings(payload)
    blocking_findings = [
        finding for finding in findings if str(finding.get("severity") or "").upper() in BLOCKING_SEVERITIES
    ]
    modes_run = set(_string_list(payload.get("ai_playtest_modes_run")))
    missing_modes = sorted(REQUIRED_AI_PLAYTEST_MODES - modes_run)
    if missing_modes:
        blockers.append("ai_playtest_modes_incomplete")
    if blocking_findings:
        blockers.append("blocking_ai_findings_present")
    if _string_list(payload.get("omitted_requirement_ids")):
        blockers.append("must_requirement_omission_present")
    if not payload.get("requirement_fidelity_go"):
        blockers.append("requirement_fidelity_not_proven")
    if payload.get("placeholder_only"):
        blockers.append("placeholder_only_required_surface")
    if payload.get("stale_evidence_reused"):
        blockers.append("fresh_ai_playtest_evidence_missing")
    if not _string_list(payload.get("replay_artifacts")):
        blockers.append("ai_playtest_replay_artifacts_missing")
    if not _string_list(payload.get("screenshots")):
        blockers.append("ai_playtest_screenshots_missing")
    engine_contract = build_engine_native_product_body_contract(payload.get("engine_native_product_body"))
    if not engine_contract["go"]:
        blockers.append("engine_native_product_body_not_proven")
    workflow_generated = bool(payload.get("workflow_generated_product_go"))
    if not workflow_generated:
        blockers.append("workflow_generated_product_not_proven")
    if payload.get("codex_local_patch_repair_go") and not workflow_generated:
        blockers.append("codex_local_patch_cannot_count_as_workflow_product")
    prototype_floor_go = score >= 70 and "blocking_ai_findings_present" not in blockers and bool(payload.get("core_loop_playable"))
    production_vertical_slice_go = (
        score >= 85
        and not blockers
        and engine_contract["go"]
        and workflow_generated
        and bool(payload.get("core_loop_playable"))
        and bool(payload.get("first_session_flow_go"))
    )
    if score < 85:
        blockers.append("ai_quality_score_below_85")
    if not payload.get("first_session_flow_go"):
        blockers.append("first_session_flow_not_proven")
    if not payload.get("core_loop_playable"):
        blockers.append("core_loop_not_playable")
    # Recompute after late blockers so the gate stays honest.
    production_vertical_slice_go = (
        score >= 85
        and not blockers
        and engine_contract["go"]
        and workflow_generated
        and bool(payload.get("core_loop_playable"))
        and bool(payload.get("first_session_flow_go"))
    )
    return {
        "schema_version": AI_PLAYTEST_QUALITY_SCHEMA,
        "floor_schema_version": PRODUCTION_VERTICAL_SLICE_FLOOR_SCHEMA,
        "ai_surrogate_playtest_go": production_vertical_slice_go,
        "production_vertical_slice_go": production_vertical_slice_go,
        "prototype_floor_go": prototype_floor_go,
        "ai_quality_score": score,
        "target_score": 85,
        "status": "completed" if production_vertical_slice_go else "blocked",
        "blockers": _dedupe(blockers),
        "area_scores": area_scores,
        "blocking_findings": blocking_findings,
        "finding_count": len(findings),
        "ai_playtest_modes_run": sorted(modes_run),
        "missing_ai_playtest_modes": missing_modes,
        "engine_native_product_body": engine_contract,
        "governance": {
            "ai_can_set_human_player_review_go": False,
            "human_player_review_go": False,
            "commercial_playable_go": False,
            "ai_pass_meaning": "ready_for_human_review_or_next_repair_phase",
        },
    }


def _area_scores(payload: dict[str, Any]) -> dict[str, int]:
    provided = payload.get("area_scores") if isinstance(payload.get("area_scores"), dict) else {}
    result: dict[str, int] = {}
    for area, weight in QUALITY_AREAS.items():
        raw = provided.get(area, 0)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = 0
        result[area] = max(0, min(weight, value))
    return result


def _findings(payload: dict[str, Any]) -> list[dict[str, Any]]:
    findings = payload.get("findings")
    if not isinstance(findings, list):
        return []
    return [finding for finding in findings if isinstance(finding, dict)]


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
