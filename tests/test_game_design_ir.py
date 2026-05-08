from __future__ import annotations

from packages.contributions.games.game_design_ir import (
    GAME_DESIGN_SPEC_SCHEMA,
    SOURCE_MATERIAL_POLICY,
    apply_derived_semantic_enrichment,
    build_game_design_spec,
    build_game_design_spec_from_requirement_matrix,
    validate_derived_semantic_enrichment,
    validate_game_design_spec,
)


def test_game_design_ir_preserves_all_source_requirements_losslessly() -> None:
    spec = build_game_design_spec(
        title="Tiny platformer test",
        genre="platformer",
        camera="side_view",
        sources=[
            {
                "source_id": "brief",
                "original_path": "brief.md",
                "raw_text": "Jump, collect keys, avoid spikes, and retry after failure.",
                "requirements": [
                    "Player must jump with responsive input.",
                    "Keys unlock the exit door.",
                    "Spike collision enters failure and retry state.",
                    "BGM and jump SFX must play at runtime.",
                ],
            }
        ],
    )
    payload = spec.to_dict()

    assert payload["schema_version"] == GAME_DESIGN_SPEC_SCHEMA
    assert payload["source_material_policy"] == SOURCE_MATERIAL_POLICY
    assert payload["source_count"] == 1
    assert payload["input_count"] == 1
    assert payload["requirement_count"] == 4
    assert set(payload["input_requirement_ids"]) == set(payload["preserved_requirement_ids"])
    assert payload["omitted_requirement_ids"] == []
    assert payload["raw_source_receipts"][0]["sha256"]
    assert validate_game_design_spec(spec)["go"] is True


def test_game_design_spec_from_requirement_matrix_preserves_unified_req_ids() -> None:
    intake_manifest = {
        "input_count": 1,
        "source_count": 1,
        "source_receipts": [
            {
                "original_path": "brief.pdf",
                "sha256": "a" * 64,
                "size_bytes": 128,
            }
        ],
    }
    requirement_matrix = {
        "requirements": [
            {
                "req_id": "REQ-S001-C001-001",
                "source_id": "source_001",
                "original_path": "brief.pdf",
                "original_quote": "必须有中文 UI 和 BGM。",
                "normalized_requirement": "必须有中文 UI 和 BGM。",
                "category": "ui",
                "priority": "must",
                "acceptance_method": "player_visible_screenshot_and_layout_review",
                "downstream_owner": "ui_experience_agent",
            },
            {
                "req_id": "REQ-S001-C002-001",
                "source_id": "source_001",
                "original_path": "brief.pdf",
                "original_quote": "拖拽交互必须跟手。",
                "normalized_requirement": "拖拽交互必须跟手。",
                "category": "mechanic",
                "priority": "must",
                "acceptance_method": "scripted_playtest_and_state_assertion",
                "downstream_owner": "gameplay_engineer_agent",
            },
        ]
    }

    spec = build_game_design_spec_from_requirement_matrix(
        title="Unified brief game",
        intake_manifest=intake_manifest,
        requirement_matrix=requirement_matrix,
        source_index=[
            {
                "source_id": "source_001",
                "original_path": "brief.pdf",
                "sha256": "a" * 64,
                "size_bytes": 128,
            }
        ],
    )
    payload = spec.to_dict()

    assert payload["input_requirement_ids"] == ["REQ-S001-C001-001", "REQ-S001-C002-001"]
    assert payload["preserved_requirement_ids"] == payload["input_requirement_ids"]
    assert payload["requirements"][0]["original_text"] == "必须有中文 UI 和 BGM。"
    assert payload["raw_source_receipts"][0]["requirement_count"] == 2
    assert validate_game_design_spec(payload)["go"] is True


def test_block_puzzle_requirements_do_not_become_universal_genre_baseline() -> None:
    spec = build_game_design_spec(
        title="Block puzzle fixture",
        genre="puzzle",
        sources=[
            {
                "source_id": "block_fixture",
                "requirements": [
                    "10x10 board is required for this brief.",
                    "3 candidates, placement, clear, refresh, failure, and revive are playable.",
                    "Chinese UI and BGM are required.",
                ],
            }
        ],
    )
    payload = spec.to_dict()

    requirement_text = "\n".join(item["normalized_requirement"] for item in payload["requirements"])
    assert "10x10" in requirement_text
    assert "10x10" not in str(payload["genre_model"])
    assert payload["genre_model"]["genre"] == "puzzle"
    assert validate_game_design_spec(spec)["go"] is True


def test_game_design_ir_blocks_omitted_requirements_and_count_mismatch() -> None:
    spec = build_game_design_spec(
        title="Card battler",
        genre="card_battler",
        sources=[{"source_id": "brief", "requirements": ["Draw a card.", "End the turn."]}],
    ).to_dict()
    spec["omitted_requirement_ids"] = [spec["input_requirement_ids"][1]]
    spec["preserved_requirement_ids"] = [spec["input_requirement_ids"][0]]
    spec["requirement_count"] = 1

    validation = validate_game_design_spec(spec)

    assert validation["go"] is False
    assert "omitted_requirement_ids_block_execution" in validation["blockers"]
    assert "preserved_requirement_ids_incomplete" in validation["blockers"]
    assert "requirement_count_mismatch" in validation["blockers"]


def test_derived_semantic_enrichment_can_only_augment_not_rewrite_source_requirements() -> None:
    spec = build_game_design_spec(
        title="Runner",
        genre="runner",
        sources=[{"source_id": "brief", "requirements": ["Jump over hazards.", "Collect coins."]}],
    ).to_dict()
    enrichment = {
        "derived_requirements": [
            {
                "source_requirement_ids": [spec["input_requirement_ids"][0]],
                "requirement": "Add a scripted jump timing oracle.",
            }
        ],
        "test_oracle_spec": {"scripted_scenarios": ["jump_timing_path"]},
        "quality_rubric": {"genre_specific_checks": ["runner_jump_arc_feel"]},
    }

    validation = validate_derived_semantic_enrichment(spec, enrichment)
    enriched = apply_derived_semantic_enrichment(spec, enrichment)

    assert validation["go"] is True
    assert enriched["input_requirement_ids"] == spec["input_requirement_ids"]
    assert enriched["preserved_requirement_ids"] == spec["preserved_requirement_ids"]
    assert enriched["requirements"] == spec["requirements"]
    assert enriched["derived_requirements"][0]["source_requirement_ids"] == [spec["input_requirement_ids"][0]]
    assert "jump_timing_path" in enriched["test_oracle_spec"]["scripted_scenarios"]


def test_derived_semantic_enrichment_rejects_requirement_mutation() -> None:
    spec = build_game_design_spec(
        title="Runner",
        genre="runner",
        sources=[{"source_id": "brief", "requirements": ["Jump over hazards."]}],
    ).to_dict()
    validation = validate_derived_semantic_enrichment(
        spec,
        {
            "requirements": [],
            "omitted_requirement_ids": [spec["input_requirement_ids"][0]],
            "preserved_requirement_ids": [],
        },
    )

    assert validation["go"] is False
    assert "enrichment_cannot_replace_requirements" in validation["blockers"]
    assert "enrichment_cannot_omit_requirements" in validation["blockers"]
    assert "enrichment_cannot_change_preserved_requirement_ids" in validation["blockers"]
