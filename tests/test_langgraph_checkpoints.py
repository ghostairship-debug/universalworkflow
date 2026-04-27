from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app
from packages.runtime_langgraph.checkpoint_store import (
    build_graph_repair_decision,
    describe_graph_checkpointer_backend,
    fork_graph_checkpoint,
    list_graph_checkpoints,
    persist_graph_checkpoint,
)
from packages.runtime_langgraph.execution_kernel import run_artifact_only_graph


def test_graph_run_persists_checkpoint_record(tmp_path: Path) -> None:
    payload = run_artifact_only_graph(
        goal="Checkpointed graph run",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "evidence",
    )

    checkpoint = payload["persistent_checkpoint"]
    records = list_graph_checkpoints(workspace_root=tmp_path, run_id=checkpoint["run_id"])

    assert payload["status"] == "completed"
    assert checkpoint["status"] == "completed"
    assert [record.checkpoint_id for record in records] == [checkpoint["checkpoint_id"]]
    assert records[0].evidence_path == payload["evidence_path"]
    assert payload["checkpoint_backend"]["backend"] == "sqlite"
    assert payload["langgraph_checkpoint_history"]


def test_graph_checkpointer_backend_prefers_sqlite_when_installed(tmp_path: Path) -> None:
    backend = describe_graph_checkpointer_backend(tmp_path)

    assert backend["selected_backend"] == "langgraph_sqlite"
    assert backend["selected_langgraph_checkpointer"] == "SqliteSaver"
    assert backend["workflow_index_backend"] == "workflow_file_index"
    assert backend["sqlite_db_path"].endswith("workflow_graph.sqlite")


def test_graph_checkpoint_fork_does_not_overwrite_parent(tmp_path: Path) -> None:
    payload = run_artifact_only_graph(
        goal="Forkable graph run",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "evidence",
    )
    parent_id = payload["persistent_checkpoint"]["checkpoint_id"]
    parent_evidence = payload["evidence_path"]

    forked = fork_graph_checkpoint(
        workspace_root=tmp_path,
        checkpoint_id=parent_id,
        reason="try alternate validation",
    )
    parent = list_graph_checkpoints(workspace_root=tmp_path, run_id=payload["persistent_checkpoint"]["run_id"])[0]

    assert forked.status == "forked"
    assert forked.parent_checkpoint_id == parent_id
    assert forked.evidence_path == parent_evidence
    assert parent.checkpoint_id == parent_id
    assert parent.status == "completed"


def test_graph_repair_decision_retries_validation_failure(tmp_path: Path) -> None:
    checkpoint = persist_graph_checkpoint(
        workspace_root=tmp_path,
        graph_state={"run_id": "run_failed", "checkpoint_refs": [{"checkpoint_id": "checkpoint_failed"}]},
        status="failed",
        node="validate",
        evidence_path=(tmp_path / "failed_evidence.json").as_posix(),
        metadata={"failure_class": "artifact_validation_failed"},
    )

    decision = build_graph_repair_decision(checkpoint=checkpoint)
    exhausted = build_graph_repair_decision(checkpoint=checkpoint, fix_iteration=2, max_fix_iterations=2)

    assert decision.action == "retry_from_checkpoint"
    assert decision.next_node == "validate"
    assert exhausted.action == "request_human_review"
    assert exhausted.human_review_required is True


def test_graph_checkpoint_cli_list_fork_and_repair_plan(tmp_path: Path) -> None:
    runner = CliRunner()
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
            "CLI checkpoint run",
            "--artifact-only",
            "--evidence-dir",
            str(tmp_path / "evidence"),
        ],
    )
    assert run.exit_code == 0
    run_payload = json.loads(run.stdout)
    checkpoint_id = run_payload["persistent_checkpoint"]["checkpoint_id"]

    listed = runner.invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "graph",
            "checkpoints",
            "list",
            "--run-id",
            run_payload["persistent_checkpoint"]["run_id"],
        ],
    )
    assert listed.exit_code == 0
    listed_payload = json.loads(listed.stdout)
    assert listed_payload["checkpoints"][0]["checkpoint_id"] == checkpoint_id

    fork = runner.invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "graph",
            "fork",
            "--checkpoint-id",
            checkpoint_id,
            "--reason",
            "alternate evidence branch",
        ],
    )
    assert fork.exit_code == 0
    fork_payload = json.loads(fork.stdout)
    assert fork_payload["checkpoint"]["parent_checkpoint_id"] == checkpoint_id

    repair = runner.invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "graph",
            "repair-plan",
            "--checkpoint-id",
            checkpoint_id,
        ],
    )
    assert repair.exit_code == 0
    repair_payload = json.loads(repair.stdout)
    assert repair_payload["action"] == "no_repair_needed"

    state = runner.invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "graph",
            "state",
            "--checkpoint-id",
            checkpoint_id,
        ],
    )
    assert state.exit_code == 0
    state_payload = json.loads(state.stdout)
    assert state_payload["status"] == "completed"
    assert state_payload["langgraph_checkpoint_history"]
