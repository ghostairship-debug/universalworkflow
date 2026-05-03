from __future__ import annotations

from packages.contributions.games.ai_playtest_lab import build_ai_playtest_plan, validate_ai_playtest_plan
from packages.contributions.games.game_design_ir import build_game_design_spec, validate_game_design_spec
from packages.contributions.games.game_task_card_generation import build_game_production_task_cards_from_design_spec


def test_universal_game_pipeline_contract_handles_puzzle_and_non_puzzle_without_hardcoding() -> None:
    block_puzzle = build_game_design_spec(
        title="Block puzzle fixture",
        genre="puzzle",
        sources=[
            {
                "source_id": "puzzle",
                "requirements": [
                    "10x10 board exists only for this puzzle brief.",
                    "3 candidates, placement, clear, refresh, failure, and revive are playable.",
                    "Chinese UI and BGM are required.",
                ],
            }
        ],
    )
    platformer = build_game_design_spec(
        title="Lantern platformer fixture",
        genre="platformer",
        camera="side_view",
        sources=[
            {
                "source_id": "platformer",
                "requirements": [
                    "Player jumps across platforms with coyote-time input forgiveness.",
                    "Camera follows the player and shows the next landing target.",
                    "Checkpoints, spike failure, retry, BGM, and landing SFX are required.",
                ],
            }
        ],
    )

    for spec in [block_puzzle, platformer]:
        assert validate_game_design_spec(spec)["go"] is True
        assert validate_ai_playtest_plan(build_ai_playtest_plan(spec))["go"] is True
        cards = build_game_production_task_cards_from_design_spec(
            run_id=f"run_{spec.genre_model.genre}",
            phase_name="Universal Game Production Quality And AI Playtest Architecture",
            spec=spec,
            status="active",
        )
        assert len(cards) == 3
        assert set(cards[-1].metadata["covered_requirement_ids"]) == set(spec.input_requirement_ids)

    assert "10x10" in "\n".join(req.normalized_requirement for req in block_puzzle.requirements)
    assert "10x10" not in "\n".join(req.normalized_requirement for req in platformer.requirements)
    assert block_puzzle.genre_model.genre == "puzzle"
    assert platformer.genre_model.genre == "platformer"
