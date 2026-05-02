from __future__ import annotations

import json
from pathlib import Path

from packages.contributions.games.cocos.product_body_baseline import (
    COCOS_PRODUCT_BODY_BASELINE_SCHEMA,
    REQUIRED_COMPONENT_BINDINGS,
    build_model_transition_traces,
    write_cocos_product_body_baseline,
)
from packages.contributions.pipelines.commercial_game_evidence_contracts import (
    build_gameplay_semantic_evidence,
    build_product_body_evidence,
)
from packages.contributions.pipelines.commercial_game_task_worker import bootstrap_cocos_project_shell


def test_cocos_product_body_baseline_writes_component_and_semantic_evidence(tmp_path: Path) -> None:
    project_dir = tmp_path / "cocos_project"

    manifest = write_cocos_product_body_baseline(project_dir)

    assert manifest["schema_version"] == COCOS_PRODUCT_BODY_BASELINE_SCHEMA
    assert manifest["baseline_only"] is True
    assert manifest["commercial_playable_go"] is False
    assert manifest["forbidden_delivery_claim"] == "product_body_baseline_is_not_commercial_playable_game"
    assert len(manifest["required_component_bindings"]) == len(REQUIRED_COMPONENT_BINDINGS)
    assert (project_dir / "assets/scripts/BoardModel.ts").exists()
    assert (project_dir / "assets/scripts/SemanticTestBridge.ts").exists()
    assert (project_dir / "assets/scene/product_body_scene_manifest.json").exists()
    board_model_source = (project_dir / "assets/scripts/BoardModel.ts").read_text(encoding="utf-8")
    rule_engine_source = (project_dir / "assets/scripts/RuleEngine.ts").read_text(encoding="utf-8")
    tray_source = (project_dir / "assets/scripts/CandidateTray.ts").read_text(encoding="utf-8")
    bridge_source = (project_dir / "assets/scripts/SemanticTestBridge.ts").read_text(encoding="utf-8")
    assert "canPlace" in board_model_source
    assert "clearCompletedLines" in board_model_source
    assert "isGameOver" in rule_engine_source
    assert "ensureAntiStall" in rule_engine_source
    assert "consumeAndRefresh" in tray_source
    assert "source: 'model_transition'" in bridge_source
    assert manifest["product_body_evidence"]["empty_component_only"] is False
    assert manifest["product_body_evidence"]["component_runtime_bindings"]["BoardModel"].endswith("BoardModel.ts")
    assert manifest["gameplay_semantic_evidence"]["trace_source"] == "model_transition"
    assert manifest["gameplay_semantic_evidence"]["model_transition_traces"]["placement"]["before_board"]
    assert manifest["gameplay_semantic_evidence"]["model_transition_traces"]["placement"]["after_board"]

    semantic_contract = build_gameplay_semantic_evidence(manifest["gameplay_semantic_evidence"])
    product_body_contract = build_product_body_evidence(
        manifest["product_body_evidence"],
        gameplay_semantic_evidence=semantic_contract,
    )

    assert semantic_contract["go"] is True
    assert semantic_contract["source"]["candidate_count"] == 3
    assert product_body_contract["go"] is True
    assert product_body_contract["source"]["component_binding_count"] == len(REQUIRED_COMPONENT_BINDINGS)


def test_model_transition_traces_cover_required_runtime_state_changes() -> None:
    traces = build_model_transition_traces()

    assert set(traces) == {"placement", "line_clear", "candidate_refresh", "game_over", "anti_stall"}
    assert traces["placement"]["before_board"] != traces["placement"]["after_board"]
    assert traces["placement"]["piece"]["cells"]
    assert traces["line_clear"]["line_clear_result"]["rows_cleared"] == [0]
    assert traces["candidate_refresh"]["candidate_refresh_trigger"] == "all_three_candidates_consumed"
    assert traces["game_over"]["game_over_result"] is True
    assert traces["anti_stall"]["anti_stall_fallback"] == "inject_single_cell_candidate_when_no_legal_move_exists"


def test_bootstrap_cocos_shell_includes_non_commercial_product_body_baseline(tmp_path: Path) -> None:
    project_dir = tmp_path / "cocos_project"
    source = tmp_path / "brief.md"
    creator = tmp_path / "CocosCreator.exe"
    source.write_text("# brief", encoding="utf-8")
    creator.write_text("", encoding="utf-8")

    bootstrap_cocos_project_shell(
        project_dir=project_dir,
        source_path=source,
        creator_exe=creator,
        asset_manifest=None,
    )

    project_source = json.loads((project_dir / "workflow_project_source.json").read_text(encoding="utf-8"))
    baseline_path = Path(project_source["product_body_baseline_manifest_path"])
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    assert project_source["product_body_baseline_only"] is True
    assert project_source["forbidden_delivery_claim"] == "bootstrap_shell_is_not_commercial_game"
    assert baseline["commercial_playable_go"] is False
    assert not (project_dir / "workflow_commercial_feature_evidence.json").exists()
