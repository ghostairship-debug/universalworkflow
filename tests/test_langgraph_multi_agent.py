from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app
from packages.runtime_langgraph.multi_agent_graph import MULTI_AGENT_ROLES, run_multi_agent_artifact_graph


def test_multi_agent_graph_runs_five_artifact_only_tasks_in_parallel(tmp_path: Path) -> None:
    payload = run_multi_agent_artifact_graph(
        goal="Multi-agent proposal bundle",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "multi_agent",
        max_workers=2,
    )

    assert payload["status"] == "completed"
    assert payload["parallel_artifact_only"] is True
    assert payload["provider_readiness_unchanged"] is True
    assert payload["supervisor_probe"]["enabled_by_default"] is False
    assert payload["supervisor_probe"]["adoption_decision"] == "probe_only"
    assert payload["task_count"] == 5
    assert [item["role"] for item in payload["artifacts"]] == MULTI_AGENT_ROLES
    for item in payload["artifacts"]:
        assert Path(item["artifact_path"]).exists()


def test_multi_agent_graph_blocks_duplicate_write_set_before_execution(tmp_path: Path) -> None:
    conflict_path = (tmp_path / "multi_agent" / "same.md").as_posix()
    tasks = [
        {"task_id": "agent_a", "role": "planner", "goal": "plan", "write_set": [conflict_path]},
        {"task_id": "agent_b", "role": "reviewer", "goal": "review", "write_set": [conflict_path]},
    ]

    payload = run_multi_agent_artifact_graph(
        goal="Conflicting graph",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "multi_agent",
        tasks=tasks,
    )

    assert payload["status"] == "blocked"
    assert payload["failure_class"] == "write_set_conflict"
    assert payload["conflicts"] == [conflict_path]
    assert not Path(conflict_path).exists()
    evidence_files = list((tmp_path / "multi_agent").glob("multi_agent_graph_*.json"))
    assert evidence_files


def test_multi_agent_graph_cli_runs_with_route_mapping(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "graph",
            "multi-agent-run",
            "--goal",
            "CLI multi-agent bundle",
            "--evidence-dir",
            str(tmp_path / "multi_agent"),
            "--route-lane",
            "medium",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "completed"
    assert payload["route_decision"]["fallback"] == "codex"
    assert payload["route_decision"]["readiness_claim"] == "unchanged"
