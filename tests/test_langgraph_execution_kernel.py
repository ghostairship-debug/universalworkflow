from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app
from packages.contracts import SideEffectLevel
from packages.runtime_langgraph.execution_kernel import (
    GRAPH_KERNEL_NODES,
    preview_graph_execution,
    run_artifact_only_graph,
    run_graph_with_side_effect_policy,
)
from packages.runtime_langgraph.studio_graph import graph as studio_graph


def test_graph_execution_preview_is_artifact_only_contract() -> None:
    payload = preview_graph_execution(goal="Write a governance note", preset_id="advisory_delivery")

    assert payload["mode"] == "preview"
    assert payload["nodes"] == GRAPH_KERNEL_NODES
    assert payload["graph_state"]["authority_mode"] == "projection_not_source_of_truth"
    assert payload["side_effect_policy"]["allowed"] == ["none", "artifact_only"]


def test_graph_execution_kernel_runs_artifact_only_and_writes_evidence(tmp_path: Path) -> None:
    payload = run_artifact_only_graph(
        goal="Write a governance note",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "graph_evidence",
        preset_id="advisory_delivery",
    )

    assert payload["status"] == "completed"
    assert payload["path"] == GRAPH_KERNEL_NODES
    artifact_path = Path(payload["artifact_path"])
    evidence_path = Path(payload["evidence_path"])
    state_path = Path(payload["graph_state_path"])
    assert artifact_path.exists()
    assert evidence_path.exists()
    assert state_path.exists()
    assert "Write a governance note" in artifact_path.read_text(encoding="utf-8")

    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert evidence["schema_version"] == "m86_graph_execution_kernel_v1"
    assert evidence["evidence_manifest"]["stage_evidence_paths"] == [artifact_path.as_posix()]
    assert evidence["graph_state_path"] == state_path.as_posix()
    assert [item["node_id"] for item in state["node_results"]] == GRAPH_KERNEL_NODES
    assert [item["node_id"] for item in payload["graph_state"]["node_results"]] == GRAPH_KERNEL_NODES


def test_graph_execution_kernel_blocks_high_risk_side_effects(tmp_path: Path) -> None:
    payload = run_graph_with_side_effect_policy(
        goal="Apply a repo patch",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "graph_evidence",
        requested_side_effect_level=SideEffectLevel.repo_mutation,
    )

    assert payload["status"] == "blocked"
    assert payload["failure_class"] == "side_effect_requires_workflow_gate"
    policy_result = next(item for item in payload["node_results"] if item["node_id"] == "policy_review")
    assert policy_result["workflow_gate_required"] is True
    assert policy_result["next_action"] == "return_to_workflow_receipt_or_lease_gate"


def test_graph_execution_kernel_uses_unique_run_attempt_paths_by_default(tmp_path: Path) -> None:
    first = run_artifact_only_graph(
        goal="Idempotent graph artifact",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "graph_evidence",
    )
    second = run_artifact_only_graph(
        goal="Idempotent graph artifact",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "graph_evidence",
    )

    assert second["run_id"] != first["run_id"]
    assert second["attempt_id"] != first["attempt_id"]
    assert second["thread_id"] != first["thread_id"]
    assert second["artifact_path"] != first["artifact_path"]
    assert second["evidence_path"] != first["evidence_path"]
    assert second["graph_state_path"] != first["graph_state_path"]


def test_graph_execution_kernel_can_reuse_explicit_artifact_without_overwriting_evidence(tmp_path: Path) -> None:
    artifact_path = tmp_path / "graph_evidence" / "shared_artifact.md"
    first = run_artifact_only_graph(
        goal="Explicit graph artifact",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "graph_evidence",
        artifact_path=artifact_path,
        run_id="run_fixed",
        phase_id="M105.0",
        attempt_id="attempt_one",
    )
    second = run_artifact_only_graph(
        goal="Explicit graph artifact",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "graph_evidence",
        artifact_path=artifact_path,
        run_id="run_fixed",
        phase_id="M105.0",
        attempt_id="attempt_two",
    )

    assert second["artifact_reused"] is True
    assert second["artifact_path"] == first["artifact_path"]
    assert second["evidence_path"] != first["evidence_path"]


def test_graph_cli_preview_and_artifact_run(tmp_path: Path) -> None:
    runner = CliRunner()
    preview = runner.invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "graph",
            "preview",
            "--goal",
            "Preview graph path",
        ],
    )

    assert preview.exit_code == 0
    preview_payload = json.loads(preview.stdout)
    assert preview_payload["nodes"] == GRAPH_KERNEL_NODES

    run = runner.invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "graph",
            "run",
            "--goal",
            "Run graph path",
            "--artifact-only",
            "--evidence-dir",
            str(tmp_path / "evidence"),
        ],
    )

    assert run.exit_code == 0
    run_payload = json.loads(run.stdout)
    assert run_payload["status"] == "completed"
    assert Path(run_payload["artifact_path"]).exists()


def test_graph_cli_run_requires_artifact_only_flag(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "graph",
            "run",
            "--goal",
            "Blocked graph path",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["failure_class"] == "artifact_only_flag_required"


def test_langgraph_studio_config_exports_safe_preview_graph() -> None:
    config = json.loads(Path("langgraph.json").read_text(encoding="utf-8"))
    result = studio_graph.invoke({"goal": "Studio smoke"})

    assert config["graphs"]["workflow_studio_preview"] == "./packages/runtime_langgraph/studio_graph.py:graph"
    assert config["env"] == ".env.langgraph.example"
    assert result["status"] == "completed"
    assert result["policy"]["side_effects_allowed"] is False
