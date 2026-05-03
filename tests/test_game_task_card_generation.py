from __future__ import annotations

from packages.core_domain.task_card_store import task_card_execution_eligibility, task_card_quality_report
from packages.contributions.games.game_design_ir import build_game_design_spec
from packages.contributions.games.game_task_card_generation import (
    build_game_production_task_cards_from_design_spec,
    game_task_card_generation_report,
)


def test_game_design_spec_generates_current_phase_workflow_product_task_cards() -> None:
    spec = build_game_design_spec(
        title="Arcade runner",
        genre="runner",
        sources=[
            {
                "source_id": "brief",
                "requirements": [
                    "Player jumps and slides to avoid obstacles.",
                    "Coins unlock skins in the shop.",
                    "BGM, jump SFX, and crash SFX play at runtime.",
                    "Mobile touch controls must feel responsive.",
                ],
            }
        ],
    )
    cards = build_game_production_task_cards_from_design_spec(
        run_id="universal_game_quality_20260503",
        phase_name="Universal Game Production Quality And AI Playtest Architecture",
        spec=spec,
        status="active",
    )
    report = game_task_card_generation_report(cards)
    quality = task_card_quality_report(cards)

    assert len(cards) >= 4
    assert quality["go_no_go"] == "GO"
    assert set(report["covered_requirement_ids"]) == set(spec.input_requirement_ids)
    assert report["workflow_generated_product_proof_required"] is True
    assert report["codex_local_patch_repair_counts_as_product"] is False
    assert all(task_card_execution_eligibility(card)["execution_eligible"] for card in cards)
    assert any(card.task_card_id.endswith("_runtime_audio_bgm_sfx_mix") for card in cards)
    assert any(card.task_card_id.endswith("_progression_economy_content_depth") for card in cards)


def test_high_risk_game_task_cards_require_visible_cli_and_workflow_proof() -> None:
    spec = build_game_design_spec(
        title="Card battler",
        genre="card_battler",
        sources=[{"source_id": "brief", "requirements": ["Draw cards.", "End turn.", "Opponent acts."]}],
    )
    cards = build_game_production_task_cards_from_design_spec(
        run_id="universal_game_quality_20260503",
        phase_name="Universal Game Production Quality And AI Playtest Architecture",
        spec=spec,
        status="active",
    )
    high_risk_cards = [card for card in cards if card.risk_level == "high"]

    assert high_risk_cards
    for card in high_risk_cards:
        assert card.metadata["human_visible_cli_required"] is True
        assert card.metadata["execution_visibility_mode"] == "human_visible_cli_enforced"
        assert card.metadata["workflow_generated_product_required"] is True
        assert card.metadata["codex_local_patch_repair_counts_as_product"] is False
