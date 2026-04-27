from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contracts import HumanApprovalInterrupt
from packages.runtime_langgraph.checkpoint_store import get_graph_checkpoint, persist_graph_checkpoint
from packages.runtime_langgraph.checkpointer_factory import open_graph_checkpointer
from packages.runtime_langgraph.interrupts import build_human_approval_interrupt


GRAPH_APPROVAL_INTERRUPT_SCHEMA = "m101_langgraph_approval_interrupt_v1"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _stable_ref(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"


def _safe_goal_path(goal: str) -> str:
    return hashlib.sha256(goal.encode("utf-8")).hexdigest()[:12]


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _build_approval_graph(checkpointer: Any | None) -> Any:
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import interrupt

    def approval_node(state: dict[str, Any]) -> dict[str, Any]:
        resume_value = interrupt(state["human_interrupt"])
        return {
            **state,
            "status": "approved_for_resume",
            "resume_value": _json_safe(resume_value),
            "resumed_at": _utc_now_iso(),
        }

    builder = StateGraph(dict)
    builder.add_node("approval_interrupt", approval_node)
    builder.add_edge(START, "approval_interrupt")
    builder.add_edge("approval_interrupt", END)
    return builder.compile(checkpointer=checkpointer) if checkpointer is not None else builder.compile()


def _snapshot_summary(snapshot: Any) -> dict[str, Any]:
    config = getattr(snapshot, "config", None) or {}
    configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
    return {
        "thread_id": configurable.get("thread_id"),
        "checkpoint_ns": configurable.get("checkpoint_ns", ""),
        "checkpoint_id": configurable.get("checkpoint_id"),
        "created_at": getattr(snapshot, "created_at", None),
        "next": list(getattr(snapshot, "next", ()) or ()),
        "interrupt_count": len(getattr(snapshot, "interrupts", ()) or ()),
        "metadata": _json_safe(getattr(snapshot, "metadata", {}) or {}),
    }


def _history(graph: Any, config: dict[str, Any]) -> list[dict[str, Any]]:
    return [_snapshot_summary(snapshot) for snapshot in graph.get_state_history(config)]


def start_human_approval_graph(
    *,
    goal: str,
    requested_side_effect_level: str,
    workspace_root: str | Path,
    evidence_dir: str | Path | None = None,
    write_set: list[str] | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    evidence_root = Path(evidence_dir).resolve() if evidence_dir else workspace / "state" / "langgraph" / "approvals"
    evidence_root.mkdir(parents=True, exist_ok=True)
    run_id = _stable_ref("run", goal)
    thread_id = _stable_ref("thread", f"approval:{run_id}")
    requested_write_set = write_set or [(evidence_root / f"approval_{_safe_goal_path(goal)}.json").as_posix()]
    interrupt = build_human_approval_interrupt(
        run_id=run_id,
        requested_side_effect_level=requested_side_effect_level,
        write_set=requested_write_set,
        workspace_root=workspace,
        thread_id=thread_id,
        checkpoint_id=None,
        operator_hint="Approve only after checking this LangGraph dynamic interrupt payload.",
        metadata={"goal": goal, "graph_kind": "human_approval_interrupt"},
    )
    handle = open_graph_checkpointer(workspace, graph_id="approval_interrupts")
    try:
        graph = _build_approval_graph(handle.saver)
        config = {"configurable": {"thread_id": thread_id}}
        initial_state = {
            "schema_version": GRAPH_APPROVAL_INTERRUPT_SCHEMA,
            "status": "pending_interrupt",
            "goal": goal,
            "run_id": run_id,
            "thread_id": thread_id,
            "workspace_root": workspace.as_posix(),
            "requested_side_effect_level": requested_side_effect_level,
            "human_interrupt": interrupt.model_dump(mode="json"),
            "created_at": _utc_now_iso(),
            "checkpoint_backend": handle.describe(),
        }
        result = graph.invoke(initial_state, config=config, durability="sync", version="v2")
        snapshot = graph.get_state(config)
        snapshot_payload = _snapshot_summary(snapshot)
        checkpoint_id = snapshot_payload.get("checkpoint_id")
        updated_interrupt = build_human_approval_interrupt(
            run_id=run_id,
            requested_side_effect_level=requested_side_effect_level,
            write_set=requested_write_set,
            workspace_root=workspace,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            operator_hint=interrupt.operator_hint,
            metadata={"goal": goal, "graph_kind": "human_approval_interrupt"},
        )
        evidence_path = evidence_root / f"approval_interrupt_{thread_id}.json"
        payload = {
            "schema_version": GRAPH_APPROVAL_INTERRUPT_SCHEMA,
            "status": "blocked",
            "failure_class": "side_effect_requires_workflow_gate",
            "goal": goal,
            "run_id": run_id,
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "human_interrupt": updated_interrupt.model_dump(mode="json"),
            "langgraph_interrupt": {
                "used_dynamic_interrupt": True,
                "graph_output": _json_safe(result),
                "state_snapshot": snapshot_payload,
                "checkpoint_history": _history(graph, config),
            },
            "checkpoint_backend": handle.describe(),
            "evidence_path": evidence_path.as_posix(),
            "created_at": _utc_now_iso(),
        }
        evidence_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        checkpoint = persist_graph_checkpoint(
            workspace_root=workspace,
            graph_state={
                "run_id": run_id,
                "thread_id": thread_id,
                "checkpoint_refs": [{"checkpoint_id": checkpoint_id, "thread_id": thread_id, "source": "langgraph"}],
            },
            status="blocked",
            node="approval_interrupt",
            evidence_path=evidence_path.as_posix(),
            checkpoint_id=checkpoint_id,
            thread_id=thread_id,
            metadata={
                "graph_kind": "human_approval_interrupt",
                "human_interrupt": updated_interrupt.model_dump(mode="json"),
                "checkpoint_backend": handle.describe(),
                "langgraph_checkpoint_id": checkpoint_id,
                "langgraph_checkpoint_history": payload["langgraph_interrupt"]["checkpoint_history"],
                "langgraph_state_snapshot": snapshot_payload,
                "langgraph_config": config,
            },
        )
        payload["persistent_checkpoint"] = checkpoint.model_dump(mode="json")
        return payload
    finally:
        handle.close()

def resume_human_approval_graph(
    *,
    workspace_root: str | Path,
    checkpoint_id: str,
    authorization: dict[str, Any],
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    checkpoint = get_graph_checkpoint(workspace_root=workspace, checkpoint_id=checkpoint_id)
    if checkpoint is None:
        return {
            "schema_version": GRAPH_APPROVAL_INTERRUPT_SCHEMA,
            "status": "failed",
            "failure_class": "checkpoint_not_found",
            "checkpoint_id": checkpoint_id,
        }
    handle = open_graph_checkpointer(workspace, graph_id="approval_interrupts")
    try:
        from langgraph.types import Command

        graph = _build_approval_graph(handle.saver)
        config = checkpoint.metadata.get("langgraph_config") or {"configurable": {"thread_id": checkpoint.thread_id}}
        result = graph.invoke(Command(resume=authorization), config=config, durability="sync", version="v2")
        snapshot = graph.get_state(config)
        snapshot_payload = _snapshot_summary(snapshot)
        new_checkpoint_id = snapshot_payload.get("checkpoint_id") or _stable_ref("checkpoint", f"resume:{checkpoint_id}")
        evidence_root = workspace / "state" / "langgraph" / "approvals"
        evidence_root.mkdir(parents=True, exist_ok=True)
        evidence_path = evidence_root / f"approval_resume_{new_checkpoint_id}.json"
        payload = {
            "schema_version": GRAPH_APPROVAL_INTERRUPT_SCHEMA,
            "status": "approved_for_resume",
            "checkpoint_id": checkpoint_id,
            "resumed_checkpoint_id": new_checkpoint_id,
            "thread_id": checkpoint.thread_id,
            "authorization": authorization,
            "langgraph_resume": {
                "used_command_resume": True,
                "graph_output": _json_safe(result),
                "state_snapshot": snapshot_payload,
                "checkpoint_history": _history(graph, config),
            },
            "checkpoint_backend": handle.describe(),
            "evidence_path": evidence_path.as_posix(),
            "created_at": _utc_now_iso(),
        }
        evidence_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        resumed = persist_graph_checkpoint(
            workspace_root=workspace,
            graph_state={
                "run_id": checkpoint.run_id,
                "thread_id": checkpoint.thread_id,
                "checkpoint_refs": [
                    {"checkpoint_id": checkpoint_id, "thread_id": checkpoint.thread_id, "source": "langgraph"},
                    {"checkpoint_id": new_checkpoint_id, "thread_id": checkpoint.thread_id, "source": "langgraph"},
                ],
            },
            status="approved_for_resume",
            node="approval_interrupt",
            evidence_path=evidence_path.as_posix(),
            checkpoint_id=new_checkpoint_id,
            thread_id=checkpoint.thread_id,
            parent_checkpoint_id=checkpoint_id,
            metadata={
                "graph_kind": "human_approval_interrupt",
                "authorization": authorization,
                "checkpoint_backend": handle.describe(),
                "langgraph_checkpoint_id": new_checkpoint_id,
                "langgraph_checkpoint_history": payload["langgraph_resume"]["checkpoint_history"],
                "langgraph_state_snapshot": snapshot_payload,
                "langgraph_config": config,
                "resume_command_used": True,
            },
        )
        payload["persistent_checkpoint"] = resumed.model_dump(mode="json")
        return payload
    finally:
        handle.close()
