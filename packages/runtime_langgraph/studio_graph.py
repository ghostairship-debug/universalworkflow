from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph


def _plan(state: dict[str, Any]) -> dict[str, Any]:
    goal = str(state.get("goal") or "Inspect local workflow graph runtime")
    return {
        **state,
        "goal": goal,
        "path": [*state.get("path", []), "plan"],
        "summary": f"Studio preview for: {goal}",
    }


def _policy_review(state: dict[str, Any]) -> dict[str, Any]:
    return {
        **state,
        "path": [*state.get("path", []), "policy_review"],
        "policy": {
            "approval_authority": "workflow_receipt_or_automation_lease",
            "provider_truth_authority": "provider_live_proof_ledger",
            "side_effects_allowed": False,
        },
    }


def _closeout(state: dict[str, Any]) -> dict[str, Any]:
    return {
        **state,
        "path": [*state.get("path", []), "closeout"],
        "status": "completed",
    }


builder = StateGraph(dict)
builder.add_node("plan", _plan)
builder.add_node("policy_review", _policy_review)
builder.add_node("closeout", _closeout)
builder.add_edge(START, "plan")
builder.add_edge("plan", "policy_review")
builder.add_edge("policy_review", "closeout")
builder.add_edge("closeout", END)

graph = builder.compile()
