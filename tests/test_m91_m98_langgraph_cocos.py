from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app
from packages.contributions.games.cocos.capabilities import (
    COCOS_CAPABILITIES,
    cocos_capability_contracts,
    judge_commercial_readiness_layers,
)
from packages.contributions.games.cocos.graph_pressure import run_cocos_graph_pressure_test
from packages.core_domain.automation_lease import create_automation_lease
from packages.runtime_langgraph.dogfood import write_dogfood_coverage
from packages.runtime_langgraph.execution_kernel import GRAPH_KERNEL_VERSION, run_graph_with_side_effect_policy
from packages.runtime_langgraph.multi_agent_graph import run_multi_agent_artifact_graph
from packages.runtime_langgraph.repair_loop import build_repair_loop_plan
from packages.runtime_langgraph.checkpoint_store import describe_graph_checkpointer_backend


def test_m91_kernel_labels_compiled_or_fallback_backend_and_streams(tmp_path: Path) -> None:
    payload = run_graph_with_side_effect_policy(
        goal="M91 typed graph evidence",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "graph",
        requested_side_effect_level="artifact_only",
    )

    assert payload["kernel_version"] == GRAPH_KERNEL_VERSION
    assert payload["execution_backend"] in {"langgraph_compiled_stategraph", "deterministic_fallback"}
    assert payload["graph_state"]["authority_mode"] == "projection_not_source_of_truth"
    assert Path(payload["stream_path"]).exists()
    stream_lines = Path(payload["stream_path"]).read_text(encoding="utf-8").splitlines()
    assert any(json.loads(line)["event"] == "node_started" for line in stream_lines)
    result = CliRunner().invoke(app, ["graph", "stream", "--stream-path", payload["stream_path"], "--limit", "2"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["event_count"] == 2


def test_m91_dogfood_coverage_requires_codex_direct_reasons(tmp_path: Path) -> None:
    payload = write_dogfood_coverage(
        milestone_id="M91",
        phase_id="P1",
        evidence_dir=tmp_path,
        task_cards=[{"task_card_id": "tc_graph_kernel"}],
        workflow_executed_task_cards=["tc_graph_kernel"],
        codex_direct_task_cards=[{"task_card_id": "tc_kernel_patch", "reason": "graph kernel internals"}],
    )

    assert payload["co_development_claim_allowed"] is True
    assert Path(payload["evidence_path"]).exists()


def test_m92_graph_history_and_resume_with_automation_lease(tmp_path: Path) -> None:
    backend = describe_graph_checkpointer_backend()
    assert backend["schema_version"] == "m92_graph_checkpointer_backend_v1"
    assert backend["selected_backend"] in {"langgraph_sqlite", "langgraph_memory", "workflow_file_index"}
    assert backend["workflow_index_backend"] == "workflow_file_index"

    blocked = run_graph_with_side_effect_policy(
        goal="M92 high risk resume",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "graph",
        requested_side_effect_level="repo_mutation",
    )
    lease = create_automation_lease(
        workspace_root=tmp_path,
        allowed_actions=["launch_execute"],
        write_set_allowlist=blocked["human_interrupt"]["write_set"],
    )
    runner = CliRunner()
    history = runner.invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "graph",
            "history",
            "--run-id",
            blocked["persistent_checkpoint"]["run_id"],
        ],
    )
    assert history.exit_code == 0
    assert json.loads(history.stdout)["history_count"] == 1

    resumed = runner.invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "graph",
            "resume",
            "--checkpoint-id",
            blocked["persistent_checkpoint"]["checkpoint_id"],
            "--lease-id",
            lease.lease_id,
        ],
    )
    assert resumed.exit_code == 0
    assert json.loads(resumed.stdout)["status"] == "approved_for_resume"


def test_m93_multi_agent_records_route_parity_and_subgraph_backend(tmp_path: Path) -> None:
    payload = run_multi_agent_artifact_graph(
        goal="M93 route parity",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "multi",
        route_lane="medium",
    )

    assert payload["status"] == "completed"
    assert payload["route_parity"]["provider_model_routing"] == "keep"
    assert payload["subgraph_backend"]["backend"] in {"compiled_role_subgraph", "deterministic_fallback"}


def test_m94_repair_loop_writes_retry_and_human_review_evidence(tmp_path: Path) -> None:
    invalid_artifact = tmp_path / "missing_goal.md"
    invalid_artifact.write_text("not the requested goal", encoding="utf-8")
    failed = run_graph_with_side_effect_policy(
        goal="M94 repair source",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "graph",
        requested_side_effect_level="artifact_only",
        artifact_path=invalid_artifact,
    )
    checkpoint_id = failed["persistent_checkpoint"]["checkpoint_id"]
    retry = build_repair_loop_plan(
        workspace_root=tmp_path,
        checkpoint_id=checkpoint_id,
        failure_class="artifact_validation_failed",
        evidence_dir=tmp_path / "repair",
    )
    exhausted = build_repair_loop_plan(
        workspace_root=tmp_path,
        checkpoint_id=checkpoint_id,
        failure_class="artifact_validation_failed",
        fix_iteration=2,
        max_fix_iterations=2,
    )

    assert retry["repair_decision"]["action"] == "retry_from_checkpoint"
    assert retry["repair_runtime"]["execution_backend"] == "langgraph_conditional_stategraph"
    assert Path(retry["evidence_path"]).exists()
    assert exhausted["repair_decision"]["action"] == "request_human_review"


def test_m96_m98_cocos_contracts_and_player_visible_gate(tmp_path: Path) -> None:
    contracts = cocos_capability_contracts(tmp_path / "cocos_project")
    assert [item["capability"] for item in contracts["capabilities"]] == COCOS_CAPABILITIES

    missing_player = judge_commercial_readiness_layers(
        technical_smoke=True,
        production_scaffold=True,
        player_visible_checks={},
    )
    accepted = judge_commercial_readiness_layers(
        technical_smoke=True,
        production_scaffold=True,
        player_visible_checks={"ui": True, "mobile": True, "audio": True, "levels": True},
    )
    assert missing_player["commercial_playable_go"] is False
    assert "player_visible_evidence" in missing_player["commercial_playable_blockers"]
    assert accepted["commercial_playable_go"] is True


def test_m104_cocos_graph_pressure_preserves_commercial_no_go_without_player_evidence(tmp_path: Path) -> None:
    payload = run_cocos_graph_pressure_test(
        workspace_root=tmp_path,
        project_path=tmp_path / "cocos_project",
        evidence_dir=tmp_path / "pressure",
        technical_smoke=True,
        production_scaffold=True,
    )

    assert payload["status"] == "blocked"
    assert payload["readiness"]["technical_smoke_go"] is True
    assert payload["readiness"]["production_scaffold_go"] is True
    assert payload["readiness"]["commercial_playable_go"] is False
    assert payload["checkpoint_backend"]["backend"] == "sqlite"
    assert Path(payload["evidence_path"]).exists()


def test_m104_cocos_graph_pressure_cli_can_record_player_visible_go(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "cocos-graph-pressure",
            "--project-path",
            str(tmp_path / "cocos_project"),
            "--evidence-dir",
            str(tmp_path / "pressure"),
            "--player-visible-evidence",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "completed"
    assert payload["readiness"]["commercial_playable_go"] is True
