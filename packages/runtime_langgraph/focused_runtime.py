from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


FOCUSED_RUNTIME_NODES = ["planning", "review", "evidence"]


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _elapsed_ms(started_at: float) -> int:
    return max(int((time.perf_counter() - started_at) * 1000), 0)


def _summarize_workflow_route(workflow_route: dict[str, Any] | None) -> dict[str, Any]:
    route = workflow_route or {}
    plan_graph = route.get("plan_graph") if isinstance(route.get("plan_graph"), dict) else {}
    nodes = plan_graph.get("nodes") if isinstance(plan_graph.get("nodes"), list) else []
    summarized_nodes: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        profile = node.get("execution_profile") if isinstance(node.get("execution_profile"), dict) else {}
        summarized_nodes.append(
            {
                "role": node.get("role"),
                "role_label": node.get("role_label"),
                "cluster_template_id": node.get("cluster_template_id"),
                "preferred_adapter": node.get("preferred_adapter"),
                "adapter_name": profile.get("adapter_name"),
                "selected_model": profile.get("selected_model"),
                "model_selection_source": profile.get("model_selection_source"),
                "side_effect_level": node.get("side_effect_level"),
            }
        )
    return {
        "selected_preset_id": route.get("selected_preset_id") or plan_graph.get("preset_id"),
        "execution_mode": plan_graph.get("execution_mode"),
        "cluster_template_ids": plan_graph.get("cluster_template_ids") or [],
        "summary": plan_graph.get("summary"),
        "risk_summary": plan_graph.get("risk_summary") or [],
        "nodes": summarized_nodes,
    }


class FocusedLangGraphRuntime:
    """Advisory-only planning/review/evidence graph.

    The runtime intentionally does not compile, resume, or mutate workflow runs.
    It may write evidence JSON when an evidence directory is explicitly provided.
    """

    def __init__(self) -> None:
        self.provider = "linear"
        self._compiled_graph = None
        try:
            from langgraph.graph import END, START, StateGraph

            builder = StateGraph(dict)
            builder.add_node("planning", self._planning_node)
            builder.add_node("review", self._review_node)
            builder.add_node("evidence", self._evidence_node)
            builder.add_edge(START, "planning")
            builder.add_edge("planning", "review")
            builder.add_edge("review", "evidence")
            builder.add_edge("evidence", END)
            self._compiled_graph = builder.compile()
            self.provider = "langgraph"
        except Exception:
            self._compiled_graph = None

    def describe(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "nodes": list(FOCUSED_RUNTIME_NODES),
            "opt_in": True,
            "mutation_allowed": False,
            "scope": "planning_review_evidence",
        }

    def compare_with_workflow_route(
        self,
        *,
        goal: str,
        preset_id: str | None,
        workflow_route: dict[str, Any] | None,
        workflow_latency_ms: int | None = None,
        evidence_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        state: dict[str, Any] = {
            "goal": goal,
            "preset_id": preset_id,
            "created_at": _utc_now_iso(),
            "path": [],
            "node_timings": [],
            "workflow_route": _summarize_workflow_route(workflow_route),
            "workflow_latency_ms": workflow_latency_ms,
            "opt_in": True,
            "mutation_allowed": False,
        }
        failure_class: str | None = None
        try:
            if self._compiled_graph is not None:
                state = self._compiled_graph.invoke(state)
            else:
                for node_name in FOCUSED_RUNTIME_NODES:
                    state = getattr(self, f"_{node_name}_node")(state)
        except Exception as exc:
            failure_class = exc.__class__.__name__
            state = {**state, "error": str(exc)}

        completed_at = _utc_now_iso()
        latency_ms = _elapsed_ms(started_at)
        result: dict[str, Any] = {
            "goal": goal,
            "preset_id": preset_id,
            "workflow_route": state.get("workflow_route"),
            "langgraph_route": {
                "provider": self.provider,
                "nodes": list(FOCUSED_RUNTIME_NODES),
                "path": state.get("path", []),
                "node_timings": state.get("node_timings", []),
                "latency_ms": latency_ms,
                "failure_class": failure_class,
            },
            "comparison": {
                "workflow_latency_ms": workflow_latency_ms,
                "langgraph_latency_ms": latency_ms,
                "passed": failure_class is None and state.get("path") == FOCUSED_RUNTIME_NODES,
                "opt_in": True,
                "mutation_allowed": False,
                "direct_mutation_disabled": True,
            },
            "review": state.get("review"),
            "evidence": state.get("evidence"),
            "created_at": state.get("created_at"),
            "completed_at": completed_at,
        }
        self._write_evidence(result, evidence_dir=evidence_dir)
        return result

    def _planning_node(self, state: dict[str, Any]) -> dict[str, Any]:
        def _apply(updated: dict[str, Any]) -> dict[str, Any]:
            route = updated.get("workflow_route") if isinstance(updated.get("workflow_route"), dict) else {}
            return {
                **updated,
                "planning": {
                    "goal": updated.get("goal"),
                    "selected_preset_id": updated.get("preset_id") or route.get("selected_preset_id"),
                    "workflow_execution_mode": route.get("execution_mode"),
                    "cluster_template_ids": route.get("cluster_template_ids", []),
                },
            }

        return self._with_node_timing(state, "planning", _apply)

    def _review_node(self, state: dict[str, Any]) -> dict[str, Any]:
        def _apply(updated: dict[str, Any]) -> dict[str, Any]:
            route_nodes = (updated.get("workflow_route") or {}).get("nodes") or []
            mutation_risk_nodes = [
                node
                for node in route_nodes
                if str(node.get("side_effect_level") or "").startswith("repo_mutation")
            ]
            return {
                **updated,
                "review": {
                    "advisory_only": True,
                    "mutation_allowed": False,
                    "direct_mutation_disabled": True,
                    "route_node_count": len(route_nodes),
                    "mutation_risk_node_count": len(mutation_risk_nodes),
                    "decision": "observe_only",
                },
            }

        return self._with_node_timing(state, "review", _apply)

    def _evidence_node(self, state: dict[str, Any]) -> dict[str, Any]:
        def _apply(updated: dict[str, Any]) -> dict[str, Any]:
            return {
                **updated,
                "evidence": {
                    "schema_version": "m68_focused_runtime_v1",
                    "evidence_id": f"m68_langgraph_{uuid4().hex[:12]}",
                    "contains_repo_mutation": False,
                    "path": list(updated.get("path", [])),
                },
            }

        return self._with_node_timing(state, "evidence", _apply)

    def _with_node_timing(
        self,
        state: dict[str, Any],
        node_name: str,
        apply_node: Any,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        path = list(state.get("path", []))
        path.append(node_name)
        updated = apply_node({**state, "path": path})
        timings = list(updated.get("node_timings", []))
        timings.append({"node": node_name, "elapsed_ms": _elapsed_ms(started_at)})
        return {**updated, "node_timings": timings}

    def _write_evidence(self, result: dict[str, Any], *, evidence_dir: str | Path | None) -> str | None:
        if evidence_dir is None:
            return None
        resolved_dir = Path(evidence_dir).resolve()
        resolved_dir.mkdir(parents=True, exist_ok=True)
        evidence_id = (result.get("evidence") or {}).get("evidence_id") or f"m68_langgraph_{uuid4().hex[:12]}"
        path = resolved_dir / f"{evidence_id}.json"
        result.setdefault("evidence", {})["evidence_path"] = path.as_posix()
        result.setdefault("langgraph_route", {})["evidence_path"] = path.as_posix()
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return path.as_posix()
