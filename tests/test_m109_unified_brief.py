from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app
from packages.contributions.pipelines import preview_workflow_pipeline
from packages.contracts import PipelineStage
from packages.core_domain.multimodal_route_plan import build_multimodal_route_plan
from packages.core_domain.pipeline_truth import build_pipeline_truth_report
from packages.core_domain.role_agent_executor import execute_single_agent_role_stage
from packages.core_domain.task_card_store import TaskCardStore
from packages.core_domain.unified_project_brief import build_unified_project_brief


runner = CliRunner()


def _invoke(tmp_path: Path, *args: str):
    return runner.invoke(
        app,
        ["--db-path", str(tmp_path / "workflow.db"), "--workspace-root", str(tmp_path), *args],
    )


def test_unified_project_brief_preserves_long_text_and_writes_agent_packets(tmp_path: Path) -> None:
    source = tmp_path / "brief.md"
    long_text = "玩法目标：玩家需要清晰的关卡目标。\n\n" + ("UI 面板必须可见可点，资产风格必须统一。\n" * 900)
    source.write_text("# 商业小游戏策划\n\n" + long_text, encoding="utf-8")
    image = tmp_path / "ui_ref.png"
    image.write_bytes(b"not-a-real-png-but-a-stable-binary-reference")

    payload = build_unified_project_brief(
        input_paths=[source, image],
        output_dir=tmp_path / "bundle",
        title="Test Brief",
    )

    full_brief = Path(payload["project_brief_path"]).read_text(encoding="utf-8")
    assert "UI 面板必须可见可点" in full_brief
    assert len(full_brief) > len(long_text)
    assert payload["chunk_count"] >= 2
    assert payload["media_count"] == 1
    assert payload["requirement_count"] >= 2

    ui_packet = Path(payload["agent_packets"]["ui_agent"]).read_text(encoding="utf-8")
    assert "packet_policy: `selected_full_chunks_not_summary_replacement`" in ui_packet
    assert "requirement_matrix_path:" in ui_packet
    assert "REQ-S001" in ui_packet
    assert "UI 面板必须可见可点" in ui_packet
    requirement_matrix = json.loads(Path(payload["requirement_matrix_path"]).read_text(encoding="utf-8"))
    assert requirement_matrix["schema_version"] == "post_m109_requirement_matrix_v1"
    assert requirement_matrix["requirements"][0]["req_id"].startswith("REQ-S001")
    assert requirement_matrix["requirements"][0]["original_quote"]
    assert requirement_matrix["requirements"][0]["normalized_requirement"]
    media_manifest = json.loads(Path(payload["media_manifest_path"]).read_text(encoding="utf-8"))
    assert media_manifest["media"][0]["sha256"]


def test_cli_intake_package_outputs_unified_brief(tmp_path: Path) -> None:
    source = tmp_path / "brief.txt"
    source.write_text("玩法和 UI 都要保留完整文字。\n", encoding="utf-8")

    result = _invoke(
        tmp_path,
        "intake",
        "package",
        "--input",
        source.as_posix(),
        "--output-dir",
        (tmp_path / "bundle").as_posix(),
        "--title",
        "CLI Brief",
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "m109_unified_project_brief_v1"
    assert Path(payload["project_brief_path"]).exists()
    assert Path(payload["requirement_matrix_path"]).exists()
    assert payload["requirement_ids"]
    assert "product_agent" in payload["agent_packets"]


def test_pipeline_truth_report_marks_real_game_workers_registered(tmp_path: Path) -> None:
    pipeline = preview_workflow_pipeline("基于 PDF 做 Cocos H5 俄罗斯方块小游戏")
    report = build_pipeline_truth_report(pipeline)

    assert report["schema_version"] == "m109_pipeline_truth_v1"
    assert report["go_no_go"] == "GO"
    assert report["pipeline_name"] == "commercial_game_production_pipeline"
    assert report["non_executable_stage_count"] == 0
    capabilities = [stage for stage in report["stages"] if stage["stage_kind"] == "capability"]
    assert {stage["metadata"]["capability"] for stage in capabilities} == {
        "commercial_game_asset_generation",
        "commercial_game_task_card_worker",
    }
    assert all(stage["execution_truth"] == "executable" for stage in capabilities)
    assert report["cluster_execution_policy"]["execution_backend"] == "langgraph_subgraph_when_upgraded"


def test_cli_pipeline_truth_report_blocks_removed_commercial_cocos_template(tmp_path: Path) -> None:
    result = _invoke(tmp_path, "pipeline", "truth-report", "--template", "commercial_cocos_game")

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["pipeline_name"] == "deprecated_commercial_cocos_game_pipeline"
    assert payload["go_no_go"] == "NO-GO"
    assert payload["non_executable_stage_count"] == 1
    assert payload["stages"][0]["truth_blocker"] == "legacy_cocos_template_removed"


def test_m109_single_agent_cocos_template_exposes_role_chain(tmp_path: Path) -> None:
    result = _invoke(tmp_path, "pipeline", "preview", "--template", "m109_single_agent_cocos")

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["name"] == "commercial_game_production_pipeline"
    role_ids = [stage["metadata"].get("role_id") for stage in payload["stages"] if stage["stage_kind"] == "agent_role"]
    assert role_ids == [
        "intake_packaging_agent",
        "product_gameplay_agent",
        "ui_experience_agent",
        "technical_plan_agent",
        "multimodal_generation_agent",
        "task_card_generation_agent",
        "qa_player_perspective_agent",
        "supervisor",
    ]
    assert payload["stages"][6]["metadata"]["capability"] == "commercial_game_asset_generation"
    assert payload["stages"][7]["metadata"]["capability"] == "commercial_game_task_card_worker"
    assert all(stage["metadata"].get("forbids_fixed_template") is True for stage in payload["stages"])


def test_pipeline_execute_agent_roles_writes_role_output_before_capability_block(tmp_path: Path) -> None:
    source = tmp_path / "brief.md"
    source.write_text("# 需求\n\n玩法目标、UI 面板、资产风格都要进入资料包。\n", encoding="utf-8")
    evidence_dir = tmp_path / "pipeline_evidence"

    result = _invoke(
        tmp_path,
        "pipeline",
        "run",
        "--template",
        "commercial_game_production",
        "--pdf-path",
        source.as_posix(),
        "--evidence-dir",
        evidence_dir.as_posix(),
        "--execute-agent-roles",
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert [stage["status"] for stage in payload["stage_results"][:6]] == ["completed"] * 6
    first_stage = payload["stage_results"][0]
    assert first_stage["execution_backend"] == "single_agent_role_protocol_v1"
    assert Path(first_stage["output"]["role_output_path"]).exists()
    assert first_stage["output"]["generation_mode"] == "deterministic_offline_role_builder"
    assert first_stage["output"]["structured_output"]["normalized_materials"]["project_brief_path"]
    assert payload["stage_results"][6]["status"] == "blocked"


def test_m109_template_execute_agent_roles_reaches_capability_handoff(tmp_path: Path) -> None:
    source = tmp_path / "brief.md"
    source.write_text("# 需求\n\n玩法、UI、技术、资产、QA 都要生成角色 evidence。\n", encoding="utf-8")
    result = _invoke(
        tmp_path,
        "pipeline",
        "run",
        "--template",
        "m109_single_agent_cocos",
        "--pipeline-id",
        "m109_role_db_smoke",
        "--pdf-path",
        source.as_posix(),
        "--execute-agent-roles",
        "--evidence-dir",
        (tmp_path / "pipeline_evidence").as_posix(),
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert [stage["status"] for stage in payload["stage_results"][:6]] == ["completed"] * 6
    assert payload["stage_results"][6]["status"] == "blocked"
    task_card_output = payload["stage_results"][5]["output"]
    assert task_card_output["role_id"] == "task_card_generation_agent"
    assert task_card_output["structured_output"]["quality_gate"]["authority_source"] == "sqlite_task_cards_table"
    phase_graph = task_card_output["structured_output"]["stage_internal_phase_graph"]
    assert phase_graph["active_materialization_policy"] == "only_open_active_phase_task_cards"
    assert phase_graph["future_phase_task_cards_materialized"] is False
    assert len(phase_graph["phases"]) >= 3
    persistence = task_card_output["structured_output"]["task_card_persistence"]
    assert persistence["task_card_count"] >= 4
    assert persistence["quality"]["go_no_go"] == "GO"

    quality = _invoke(tmp_path, "task", "card-quality", "--run-id", "m109_role_db_smoke")
    assert quality.exit_code == 0
    assert json.loads(quality.stdout)["go_no_go"] == "GO"
    cards = TaskCardStore(tmp_path / "workflow.db").list_for_run("m109_role_db_smoke")
    same_project_cards = [card for card in cards if card.execution_mode == "same_project_patch"]
    assert len(same_project_cards) >= 6
    assert all(card.metadata.get("stage_phase") for card in same_project_cards)
    assert any(card.metadata.get("depends_on_task_card_ids") for card in same_project_cards)
    assert all(card.metadata.get("requirement_coverage_required") is True for card in same_project_cards)
    assert all(card.metadata.get("covered_requirement_ids") for card in same_project_cards)
    assert all(card.metadata.get("required_requirement_ids") for card in same_project_cards)
    assert all(
        not command.startswith("workflowctl pipeline run")
        for card in same_project_cards
        for command in card.test_commands
    )


def test_product_body_runtime_goal_materializes_only_active_phase_task_cards(tmp_path: Path) -> None:
    source = tmp_path / "brief.md"
    source.write_text("# 需求\n\n先实现产品本体运行时、语义 trace 和 Cocos component evidence。\n", encoding="utf-8")
    result = _invoke(
        tmp_path,
        "pipeline",
        "run",
        "--template",
        "commercial_game_production",
        "--goal",
        "Product Body Runtime And Semantic Trace Implementation",
        "--pipeline-id",
        "product_body_runtime_phase",
        "--pdf-path",
        source.as_posix(),
        "--execute-agent-roles",
        "--evidence-dir",
        (tmp_path / "pipeline_evidence").as_posix(),
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    task_card_output = payload["stage_results"][5]["output"]
    phase_graph = task_card_output["structured_output"]["stage_internal_phase_graph"]
    assert phase_graph["future_phase_task_cards_materialized"] is False
    assert [phase["title"] for phase in phase_graph["phases"]] == ["Product Body Runtime And Semantic Trace Implementation"]

    persistence = task_card_output["structured_output"]["task_card_persistence"]
    assert persistence["task_card_count"] == 3
    assert persistence["quality"]["go_no_go"] == "GO"
    cards = TaskCardStore(tmp_path / "workflow.db").list_for_run("product_body_runtime_phase")
    assert len(cards) == 3
    assert {card.phase_name for card in cards} == {"Product Body Runtime And Semantic Trace Implementation"}
    assert all(card.execution_mode == "same_project_patch" for card in cards)
    assert all(card.metadata.get("requirement_coverage_required") is True for card in cards)


def test_m109_role_outputs_are_role_specific(tmp_path: Path) -> None:
    source = tmp_path / "brief.md"
    source.write_text("# 闇€姹俓n\nUI銆侀煶棰戙€佸叧鍗°€佽祫浜ч兘闇€瑕佽淇濈暀銆俓n", encoding="utf-8")
    result = _invoke(
        tmp_path,
        "pipeline",
        "run",
        "--template",
        "m109_single_agent_cocos",
        "--pipeline-id",
        "m109_role_specific_smoke",
        "--pdf-path",
        source.as_posix(),
        "--execute-agent-roles",
        "--evidence-dir",
        (tmp_path / "pipeline_evidence").as_posix(),
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    product = payload["stage_results"][1]["output"]["structured_output"]
    ui = payload["stage_results"][2]["output"]["structured_output"]
    tech = payload["stage_results"][3]["output"]["structured_output"]
    multimodal = payload["stage_results"][4]["output"]["structured_output"]
    assert product["core_loop"]
    assert ui["screen_flow"]
    assert tech["implementation_plan"]
    assert multimodal["provider_route_requirements"]
    assert multimodal["route_plan"]["schema_version"] == "m109_multimodal_route_plan_v1"
    assert {lane["lane"] for lane in multimodal["route_plan"]["lanes"]} == {
        "image_or_sprite",
        "speech_or_voice",
        "music_or_sfx",
        "visual_review",
    }


def test_m109_qa_role_uses_cocos_e2e_shared_output(tmp_path: Path) -> None:
    source = tmp_path / "brief.md"
    source.write_text("# QA\n\n玩家视角证据必须接入角色输出。\n", encoding="utf-8")
    stage = PipelineStage(
        name="QA player perspective agent",
        stage_kind="agent_role",
        order_index=9,
        goal="Review generated evidence from a player-visible quality perspective.",
        metadata={"role_id": "qa_player_perspective_agent", "role_kind": "single_agent"},
    )
    payload = execute_single_agent_role_stage(
        stage,
        root=tmp_path,
        target_dir=tmp_path / "evidence",
        source_path=source,
        pipeline_id="qa_shared_output_smoke",
        shared_outputs={
            "cocos_e2e": {
                "manifest_path": "state/example/cocos_game_e2e_manifest.json",
                "commercial_playable_go": True,
                "commercial_playable_blockers": [],
                "player_visible_checks": {
                    "browser_console_no_fatal_error": {
                        "status": "pass",
                        "evidence_path": "state/example/player_visible_evidence.json",
                    }
                },
                "playtest": {"console_errors": [], "page_errors": [], "screenshots": ["shot.png"]},
            }
        },
    )

    structured = payload["result"]["output"]["structured_output"]
    assert structured["evidence_source"] == "shared_outputs.cocos_e2e"
    assert structured["go_no_go_recommendation"] == "GO"
    assert structured["commercial_playable_go"] is True
    assert structured["repair_findings"] == []
    assert structured["player_visible_checks"][0]["status"] == "pass"


def test_m109_multimodal_route_plan_is_truthful_without_live_proof() -> None:
    payload = build_multimodal_route_plan(environ={})

    assert payload["go_no_go"] == "GO"
    assert payload["verified_ready_policy"].startswith("Only provider-specific")
    assert {lane["lane"] for lane in payload["lanes"]} == {
        "image_or_sprite",
        "speech_or_voice",
        "music_or_sfx",
        "visual_review",
    }
    assert all(lane["verified_ready"] is False for lane in payload["lanes"])
    assert all(lane["live_proof_required"] is True for lane in payload["lanes"])
    assert all(lane["route_status"] == "blocked_auth_missing" for lane in payload["lanes"])
