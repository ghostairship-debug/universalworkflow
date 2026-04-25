from __future__ import annotations

import json
from pathlib import Path

from packages.runtime_langgraph.focused_runtime import FOCUSED_RUNTIME_NODES, FocusedLangGraphRuntime


def _workflow_route() -> dict:
    return {
        "selected_preset_id": "project_delivery",
        "plan_graph": {
            "execution_mode": "planner_generated_graph_with_parallel_children",
            "cluster_template_ids": ["dev_cluster"],
            "summary": "Shared orchestration plan.",
            "risk_summary": ["repo mutation stays isolated to coder lanes"],
            "nodes": [
                {
                    "role": "planner",
                    "role_label": "architect",
                    "cluster_template_id": "dev_cluster",
                    "preferred_adapter": "opencode",
                    "side_effect_level": "advisory_only",
                    "execution_profile": {
                        "adapter_name": "opencode",
                        "selected_model": "minimax/MiniMax-M2.7",
                        "model_selection_source": "adaptive_llm_router",
                    },
                },
                {
                    "role": "coder",
                    "role_label": "implementer",
                    "cluster_template_id": "dev_cluster",
                    "preferred_adapter": "codex",
                    "side_effect_level": "repo_mutation_controlled",
                    "execution_profile": {
                        "adapter_name": "codex",
                        "selected_model": "gpt-5.5",
                        "model_selection_source": "strong_model_fallback",
                    },
                },
            ],
        },
    }


def test_focused_langgraph_runtime_is_advisory_only_and_writes_evidence(tmp_path: Path) -> None:
    runtime = FocusedLangGraphRuntime()

    result = runtime.compare_with_workflow_route(
        goal="Compare workflow and LangGraph routes",
        preset_id="project_delivery",
        workflow_route=_workflow_route(),
        workflow_latency_ms=12,
        evidence_dir=tmp_path,
    )

    assert runtime.describe()["mutation_allowed"] is False
    assert result["comparison"]["passed"] is True
    assert result["comparison"]["mutation_allowed"] is False
    assert result["comparison"]["direct_mutation_disabled"] is True
    assert result["langgraph_route"]["path"] == FOCUSED_RUNTIME_NODES
    assert result["workflow_route"]["nodes"][0]["adapter_name"] == "opencode"
    assert result["workflow_route"]["nodes"][1]["side_effect_level"] == "repo_mutation_controlled"
    assert result["review"]["decision"] == "observe_only"
    assert result["review"]["mutation_risk_node_count"] == 1

    evidence_path = Path(result["evidence"]["evidence_path"])
    assert evidence_path.exists()
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["comparison"]["direct_mutation_disabled"] is True
    assert evidence["evidence"]["contains_repo_mutation"] is False


def test_focused_langgraph_runtime_uses_deterministic_fallback_shape() -> None:
    runtime = FocusedLangGraphRuntime()

    result = runtime.compare_with_workflow_route(
        goal="No evidence write",
        preset_id=None,
        workflow_route={},
        workflow_latency_ms=None,
    )

    assert result["langgraph_route"]["provider"] in {"langgraph", "linear"}
    assert result["langgraph_route"]["path"] == FOCUSED_RUNTIME_NODES
    assert result["comparison"]["opt_in"] is True
    assert "evidence_path" not in result["langgraph_route"]
