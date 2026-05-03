from __future__ import annotations

from typing import Any

from packages.contributions.games.game_design_ir import GameDesignSpec


AI_PLAYTEST_PLAN_SCHEMA = "universal_ai_playtest_lab_plan_v1"

AI_PLAYTEST_PERSONAS = [
    "novice_player",
    "expert_player",
    "impatient_player",
    "completionist_player",
    "monetization_sensitive_player",
    "accessibility_sensitive_player",
]
AI_PLAYTEST_MODES = [
    "scripted_bot",
    "exploratory_bot",
    "persona_agent",
    "vision_reviewer",
    "design_red_team",
    "performance_agent",
    "device_matrix_agent",
    "regression_agent",
]


def build_ai_playtest_plan(spec: GameDesignSpec | dict[str, Any]) -> dict[str, Any]:
    payload = spec.to_dict() if isinstance(spec, GameDesignSpec) else dict(spec)
    oracle = payload.get("test_oracle_spec") if isinstance(payload.get("test_oracle_spec"), dict) else {}
    genre = payload.get("genre_model") if isinstance(payload.get("genre_model"), dict) else {}
    requirement_ids = [str(item) for item in payload.get("preserved_requirement_ids") or []]
    scripted_scenarios = _string_list(oracle.get("scripted_scenarios"))
    return {
        "schema_version": AI_PLAYTEST_PLAN_SCHEMA,
        "game_title": payload.get("title"),
        "genre": genre.get("genre"),
        "camera": genre.get("camera"),
        "target_platforms": _string_list(genre.get("target_platforms")),
        "requirement_ids": requirement_ids,
        "modes": list(AI_PLAYTEST_MODES),
        "personas": list(AI_PLAYTEST_PERSONAS),
        "scripted_scenarios": scripted_scenarios,
        "exploratory_budget": {
            "minimum_runs": max(8, len(requirement_ids) * 2),
            "minimum_minutes": 30,
            "mutation_seed_policy": "record_all_replay_seeds",
        },
        "vision_review_targets": _string_list(oracle.get("screenshot_expectations")),
        "state_assertions": _string_list(oracle.get("state_assertions")),
        "performance_budgets": _string_list(oracle.get("performance_budgets")),
        "device_matrix": _string_list(oracle.get("device_matrix")),
        "required_artifacts": [
            "replay_jsonl",
            "screenshots",
            "state_snapshots",
            "console_page_error_log",
            "ai_findings_json",
            "quality_scorecard_json",
        ],
        "blocking_policy": {
            "p0_allowed": 0,
            "p1_allowed": 0,
            "minimum_ai_quality_score": 85,
            "missing_replay_blocks": True,
            "missing_screenshots_blocks": True,
        },
    }


def validate_ai_playtest_plan(plan: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    modes = set(_string_list(plan.get("modes")))
    missing_modes = [mode for mode in AI_PLAYTEST_MODES if mode not in modes]
    if plan.get("schema_version") != AI_PLAYTEST_PLAN_SCHEMA:
        blockers.append("ai_playtest_plan_schema_invalid")
    if missing_modes:
        blockers.append("ai_playtest_modes_missing")
    if not _string_list(plan.get("scripted_scenarios")):
        blockers.append("scripted_scenarios_missing")
    if not _string_list(plan.get("vision_review_targets")):
        blockers.append("vision_review_targets_missing")
    if not _string_list(plan.get("device_matrix")):
        blockers.append("device_matrix_missing")
    if not _string_list(plan.get("requirement_ids")):
        blockers.append("requirement_ids_missing")
    return {
        "schema_version": "universal_ai_playtest_lab_plan_validation_v1",
        "go": not blockers,
        "blockers": blockers,
        "missing_modes": missing_modes,
        "scenario_count": len(_string_list(plan.get("scripted_scenarios"))),
        "persona_count": len(_string_list(plan.get("personas"))),
        "requirement_count": len(_string_list(plan.get("requirement_ids"))),
    }


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
