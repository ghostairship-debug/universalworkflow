from __future__ import annotations

from packages.contributions.games.ai_playtest_lab import (
    AI_PLAYTEST_MODES,
    AI_PLAYTEST_PERSONAS,
    build_ai_playtest_plan,
    validate_ai_playtest_plan,
)
from packages.contributions.games.game_design_ir import build_game_design_spec


def test_ai_playtest_plan_is_generated_from_test_oracle_and_requirements() -> None:
    spec = build_game_design_spec(
        title="Narrative choice scene",
        genre="narrative",
        camera="scene_view",
        sources=[
            {
                "source_id": "brief",
                "requirements": [
                    "Player chooses one of three dialogue options.",
                    "Choice changes the next scene and persists in save state.",
                    "Chinese UI and readable text are required.",
                ],
            }
        ],
    )

    plan = build_ai_playtest_plan(spec)
    validation = validate_ai_playtest_plan(plan)

    assert plan["genre"] == "narrative"
    assert set(plan["modes"]) == set(AI_PLAYTEST_MODES)
    assert set(plan["personas"]) == set(AI_PLAYTEST_PERSONAS)
    assert plan["requirement_ids"] == spec.input_requirement_ids
    assert plan["exploratory_budget"]["minimum_runs"] >= len(spec.input_requirement_ids) * 2
    assert validation["go"] is True


def test_ai_playtest_plan_validation_blocks_thin_plan() -> None:
    validation = validate_ai_playtest_plan({"schema_version": "wrong", "modes": ["scripted_bot"]})

    assert validation["go"] is False
    assert "ai_playtest_plan_schema_invalid" in validation["blockers"]
    assert "ai_playtest_modes_missing" in validation["blockers"]
    assert "scripted_scenarios_missing" in validation["blockers"]
    assert "requirement_ids_missing" in validation["blockers"]
