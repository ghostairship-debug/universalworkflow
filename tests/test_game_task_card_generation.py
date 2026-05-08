from __future__ import annotations

from packages.core_domain.task_card_store import task_card_execution_eligibility, task_card_quality_report
from packages.contributions.games.game_design_ir import build_game_design_spec
from packages.contributions.games.game_task_card_generation import (
    PHASE_EXECUTION_BLUEPRINT_SCHEMA,
    PRODUCT_PHASE_CANDIDATE_SCHEMA,
    build_phase_execution_blueprint,
    build_game_production_task_cards_from_design_spec,
    build_product_phase_candidates_from_design_spec,
    compile_task_cards_from_phase_execution_blueprint,
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
    assert report["task_card_generation_source"] == "active_phase_execution_blueprint"
    assert report["all_cards_blueprint_compiled"] is True
    assert all(task_card_execution_eligibility(card)["execution_eligible"] for card in cards)
    assert all(card.metadata["phase_execution_blueprint_schema"] == PHASE_EXECUTION_BLUEPRINT_SCHEMA for card in cards)
    assert any(card.task_card_id.endswith("_audio_asset_manifest_generation") for card in cards)
    assert any(card.task_card_id.endswith("_runtime_audio_bgm_sfx_controls") for card in cards)
    assert any(card.task_card_id.endswith("_product_rules_progression_content_depth") for card in cards)


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


def test_phase_candidates_blueprint_and_compile_report_cover_source_requirements() -> None:
    spec = build_game_design_spec(
        title="Lantern platformer",
        genre="platformer",
        sources=[
            {
                "source_id": "brief",
                "requirements": [
                    "Player jumps across platforms with checkpoints.",
                    "Camera follows the player and shows landing targets.",
                    "BGM and landing SFX are required.",
                    "Generated art assets and particle effects are required.",
                ],
            }
        ],
    )

    phase_candidates = build_product_phase_candidates_from_design_spec(run_id="platformer_run", spec=spec)
    blueprint = build_phase_execution_blueprint(
        run_id="platformer_run",
        phase_name="Commercial Game Core Content Implementation",
        spec=spec,
    )
    cards, compile_report = compile_task_cards_from_phase_execution_blueprint(
        run_id="platformer_run",
        phase_name="Commercial Game Core Content Implementation",
        spec=spec,
        blueprint=blueprint,
        status="active",
    )

    assert phase_candidates[0].schema_version == PRODUCT_PHASE_CANDIDATE_SCHEMA
    assert blueprint.schema_version == PHASE_EXECUTION_BLUEPRINT_SCHEMA
    assert compile_report.go is True
    assert compile_report.missing_requirement_ids == []
    assert set(compile_report.covered_requirement_ids) == set(spec.input_requirement_ids)
    assert all(card.metadata["task_card_generation_source"] == "active_phase_execution_blueprint" for card in cards)
    assert any(card.task_card_id.endswith("_audio_asset_manifest_generation") for card in cards)
    assert any(card.task_card_id.endswith("_runtime_audio_bgm_sfx_controls") for card in cards)
    assert all(not path.startswith("project/") for card in cards for path in card.write_set)
    assert any(path.startswith("assets/scripts/runtime/") for card in cards for path in card.write_set)
    assert any(path.startswith("workflow_runtime_evidence/") for card in cards for path in card.write_set)
    scene_card = next(card for card in cards if card.task_card_id.endswith("_scene_prefab_component_binding"))
    input_card = next(card for card in cards if card.task_card_id.endswith("_scene_input_feedback_binding"))
    audio_asset_card = next(card for card in cards if card.task_card_id.endswith("_audio_asset_manifest_generation"))
    audio_runtime_card = next(card for card in cards if card.task_card_id.endswith("_runtime_audio_bgm_sfx_controls"))
    assert "assets/scripts/workflow-e2e-runtime-bridge.js" in scene_card.write_set
    assert "assets/scripts/runtime/ui/**" not in scene_card.write_set
    assert "assets/scripts/runtime/input/**" not in scene_card.write_set
    assert "workflow_runtime_evidence/input_feedback_trace.json" in input_card.expected_artifacts
    assert "workflow_runtime_evidence/scene_prefab_binding_evidence.json" in input_card.read_set
    assert "settings/v2/packages/scene.json" in input_card.read_set
    assert any("WorkflowCommercialGame.scene" in item for item in input_card.evidence_requirements)
    assert "workflow_runtime_evidence/chinese_ui_panels_evidence.json" not in scene_card.write_set
    assert "assets/scripts/workflow-e2e-runtime-bridge.js" in scene_card.expected_artifacts
    assert any("cc.CompPrefabInfo" in item and "not a live component binding" in item for item in scene_card.model_guidance)
    assert "workflow_runtime_evidence/**" not in audio_asset_card.write_set
    assert "workflow_runtime_evidence/**" not in audio_runtime_card.write_set
    assert "assets/resources/commercial_assets/audio/commercial_audio_manifest.json" in audio_asset_card.expected_artifacts
    assert "assets/scripts/runtime/audio/CommercialAudioRuntime.ts" in audio_runtime_card.expected_artifacts


def test_multimodal_requirements_materialize_art_and_audio_cocos_slices() -> None:
    spec = {
        "schema_version": "universal_game_design_spec_v1",
        "preserved_requirement_ids": ["REQ-MULTI-001"],
        "requirements": [{"req_id": "REQ-MULTI-001", "category": "multimodal", "text": "Generate art, particles, BGM and SFX."}],
    }
    blueprint = build_phase_execution_blueprint(
        run_id="multimodal_run",
        phase_name="Commercial Game Core Content Implementation",
        spec=spec,
    )
    cards, compile_report = compile_task_cards_from_phase_execution_blueprint(
        run_id="multimodal_run",
        phase_name="Commercial Game Core Content Implementation",
        spec=spec,
        blueprint=blueprint,
        status="active",
    )

    assert compile_report.go is True
    assert any(card.task_card_id.endswith("_art_animation_asset_direction") for card in cards)
    assert any(card.task_card_id.endswith("_audio_asset_manifest_generation") for card in cards)
    assert any(card.task_card_id.endswith("_runtime_audio_bgm_sfx_controls") for card in cards)
