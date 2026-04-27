from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contracts import GraphRepairDecision, WorkflowGraphNodeResult
from packages.runtime_langgraph.checkpoint_store import build_graph_repair_decision, get_graph_checkpoint
from packages.runtime_langgraph.checkpointer_factory import open_graph_checkpointer


GRAPH_REPAIR_LOOP_SCHEMA = "m94_graph_repair_loop_v1"
GRAPH_REPAIR_RUNTIME_SCHEMA = "m102_conditional_repair_graph_v1"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _run_conditional_repair_graph(
    *,
    workspace_root: str | Path,
    checkpoint_id: str,
    decision: GraphRepairDecision,
) -> dict[str, Any]:
    handle = open_graph_checkpointer(workspace_root, graph_id="repair_loop")
    try:
        from langgraph.graph import END, START, StateGraph

        def diagnose(state: dict[str, Any]) -> dict[str, Any]:
            return {**state, "node_path": [*state.get("node_path", []), "diagnose"]}

        def repair_plan(state: dict[str, Any]) -> dict[str, Any]:
            return {**state, "node_path": [*state.get("node_path", []), "repair_plan"], "repair_attempted": True}

        def retest(state: dict[str, Any]) -> dict[str, Any]:
            return {
                **state,
                "node_path": [*state.get("node_path", []), state.get("next_node") or "validate"],
                "status": "repair_retry_planned",
            }

        def human_review(state: dict[str, Any]) -> dict[str, Any]:
            return {**state, "node_path": [*state.get("node_path", []), "human_review"], "status": "blocked"}

        def closeout(state: dict[str, Any]) -> dict[str, Any]:
            return {**state, "node_path": [*state.get("node_path", []), "closeout"], "status": "completed"}

        def route(state: dict[str, Any]) -> str:
            if state["decision_action"] == "retry_from_checkpoint":
                return "repair_plan"
            if state["decision_action"] == "request_human_review":
                return "human_review"
            return "closeout"

        builder = StateGraph(dict)
        builder.add_node("diagnose", diagnose)
        builder.add_node("repair_plan", repair_plan)
        builder.add_node("retest", retest)
        builder.add_node("human_review", human_review)
        builder.add_node("closeout", closeout)
        builder.add_edge(START, "diagnose")
        builder.add_conditional_edges(
            "diagnose",
            route,
            {
                "repair_plan": "repair_plan",
                "human_review": "human_review",
                "closeout": "closeout",
            },
        )
        builder.add_edge("repair_plan", "retest")
        builder.add_edge("retest", END)
        builder.add_edge("human_review", END)
        builder.add_edge("closeout", END)
        graph = builder.compile(checkpointer=handle.saver) if handle.saver else builder.compile()
        thread_id = f"repair:{checkpoint_id}"
        config = {"configurable": {"thread_id": thread_id}}
        initial_state = {
            "schema_version": GRAPH_REPAIR_RUNTIME_SCHEMA,
            "checkpoint_id": checkpoint_id,
            "decision_action": decision.action,
            "failure_class": decision.failure_class,
            "next_node": decision.next_node,
            "node_path": ["execute", "validate"],
            "status": "running",
            "created_at": _utc_now_iso(),
        }
        stream_parts: list[dict[str, Any]] = []
        final_values = initial_state
        for part in graph.stream(
            initial_state,
            config=config,
            stream_mode=["values", "updates", "tasks"],
            durability="sync",
            version="v2",
        ):
            safe_part = _json_safe(part)
            stream_parts.append(safe_part)
            if safe_part.get("type") == "values" and isinstance(safe_part.get("data"), dict):
                final_values = safe_part["data"]
        history = []
        try:
            for snapshot in graph.get_state_history(config):
                cfg = getattr(snapshot, "config", {}) or {}
                configurable = cfg.get("configurable", {}) if isinstance(cfg, dict) else {}
                history.append(
                    {
                        "thread_id": configurable.get("thread_id"),
                        "checkpoint_id": configurable.get("checkpoint_id"),
                        "next": list(getattr(snapshot, "next", ()) or ()),
                        "created_at": getattr(snapshot, "created_at", None),
                    }
                )
        except Exception as exc:
            history.append({"error": f"{type(exc).__name__}: {exc}"})
        return {
            "schema_version": GRAPH_REPAIR_RUNTIME_SCHEMA,
            "execution_backend": "langgraph_conditional_stategraph",
            "checkpoint_backend": handle.describe(),
            "thread_id": thread_id,
            "final_state": final_values,
            "stream_parts": stream_parts,
            "checkpoint_history": history,
        }
    except Exception as exc:
        return {
            "schema_version": GRAPH_REPAIR_RUNTIME_SCHEMA,
            "execution_backend": "deterministic_fallback",
            "checkpoint_backend": handle.describe(),
            "fallback_reason": f"{type(exc).__name__}: {exc}",
        }
    finally:
        handle.close()


def build_repair_loop_plan(
    *,
    workspace_root: str | Path,
    checkpoint_id: str,
    failure_class: str | None = None,
    fix_iteration: int = 0,
    max_fix_iterations: int = 2,
    evidence_dir: str | Path | None = None,
) -> dict[str, Any]:
    checkpoint = get_graph_checkpoint(workspace_root=workspace_root, checkpoint_id=checkpoint_id)
    if checkpoint is None:
        return {
            "schema_version": GRAPH_REPAIR_LOOP_SCHEMA,
            "status": "failed",
            "failure_class": "checkpoint_not_found",
            "checkpoint_id": checkpoint_id,
        }
    decision: GraphRepairDecision = build_graph_repair_decision(
        checkpoint=checkpoint,
        failure_class=failure_class,
        fix_iteration=fix_iteration,
        max_fix_iterations=max_fix_iterations,
    )
    repair_runtime = _run_conditional_repair_graph(
        workspace_root=workspace_root,
        checkpoint_id=checkpoint_id,
        decision=decision,
    )
    node_path = repair_runtime.get("final_state", {}).get("node_path") if isinstance(repair_runtime.get("final_state"), dict) else None
    if not node_path:
        node_path = ["execute", "validate"]
        if decision.action == "retry_from_checkpoint":
            node_path.extend(["diagnose", "repair_plan", decision.next_node or "execute"])
        elif decision.action == "request_human_review":
            node_path.extend(["diagnose", "human_review"])
        else:
            node_path.append("closeout")
    node_results = [
        WorkflowGraphNodeResult(
            node_id=node,
            status="completed" if node not in {"human_review"} else "blocked",
            failure_class=decision.failure_class if node in {"validate", "human_review"} else None,
            next_action=node_path[index + 1] if index + 1 < len(node_path) else "done",
        ).model_dump(mode="json")
        for index, node in enumerate(node_path)
    ]
    payload = {
        "schema_version": GRAPH_REPAIR_LOOP_SCHEMA,
        "status": "completed" if not decision.human_review_required else "blocked",
        "checkpoint_id": checkpoint_id,
        "node_path": node_path,
        "node_results": node_results,
        "repair_decision": decision.model_dump(mode="json"),
        "repair_runtime": repair_runtime,
        "checkpoint_lineage": {
            "checkpoint_id": checkpoint.checkpoint_id,
            "parent_checkpoint_id": checkpoint.parent_checkpoint_id,
            "thread_id": checkpoint.thread_id,
        },
        "created_at": _utc_now_iso(),
    }
    if evidence_dir is not None:
        root = Path(evidence_dir).resolve()
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"repair_loop_{checkpoint_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["evidence_path"] = path.as_posix()
    return payload
