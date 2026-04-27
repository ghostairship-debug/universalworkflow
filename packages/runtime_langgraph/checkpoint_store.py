from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contracts import GraphCheckpointRecord, GraphRepairDecision
from packages.runtime_langgraph.checkpointer_factory import (
    GRAPH_CHECKPOINTER_FACTORY_SCHEMA,
    graph_checkpoint_db_path,
    graph_memory_available,
    graph_sqlite_available,
)


CHECKPOINT_STORE_SCHEMA = "m88_graph_checkpoint_store_v1"
CHECKPOINT_BACKEND_SCHEMA = "m92_graph_checkpointer_backend_v1"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _store_path(workspace_root: str | Path) -> Path:
    return Path(workspace_root).resolve() / "state" / "graph_checkpoints" / "checkpoints.json"


def _read_store(workspace_root: str | Path) -> dict[str, Any]:
    path = _store_path(workspace_root)
    if not path.exists():
        return {"schema_version": CHECKPOINT_STORE_SCHEMA, "checkpoints": {}}
    payload = json.loads(path.read_text(encoding="utf-8") or "{}")
    payload.setdefault("schema_version", CHECKPOINT_STORE_SCHEMA)
    payload.setdefault("checkpoints", {})
    return payload


def _write_store(workspace_root: str | Path, payload: dict[str, Any]) -> None:
    path = _store_path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"


def describe_graph_checkpointer_backend(workspace_root: str | Path | None = None) -> dict[str, Any]:
    sqlite_available = graph_sqlite_available()
    memory_available = graph_memory_available()
    selected_backend = "langgraph_sqlite" if sqlite_available else "langgraph_memory" if memory_available else "workflow_file_index"
    backend = {
        "schema_version": CHECKPOINT_BACKEND_SCHEMA,
        "factory_schema_version": GRAPH_CHECKPOINTER_FACTORY_SCHEMA,
        "selected_backend": selected_backend,
        "workflow_index_backend": "workflow_file_index",
        "langgraph_memory_available": memory_available,
        "langgraph_sqlite_available": sqlite_available,
        "sqlite_db_path": graph_checkpoint_db_path(workspace_root or Path.cwd()).as_posix() if sqlite_available else None,
        "notes": [
            "LangGraph SQLite is the preferred local durable graph-state backend when installed",
            "workflow_file_index remains the local evidence index",
            "LangGraph checkpointer state must not replace workflow evidence authority",
        ],
    }
    if sqlite_available:
        backend["selected_langgraph_checkpointer"] = "SqliteSaver"
    elif memory_available:
        backend["selected_langgraph_checkpointer"] = "InMemorySaver"
        backend["fallback_reason"] = "langgraph_sqlite_package_missing"
    else:
        backend["selected_langgraph_checkpointer"] = None
        backend["fallback_reason"] = "langgraph_checkpointer_packages_missing"
    return backend


def _checkpoint_ref_from_graph_state(graph_state: dict[str, Any]) -> tuple[str, str | None]:
    refs = graph_state.get("checkpoint_refs") if isinstance(graph_state.get("checkpoint_refs"), list) else []
    if refs:
        ref = refs[-1]
        if isinstance(ref, dict):
            checkpoint_id = str(ref.get("checkpoint_id") or "")
            thread_id = str(ref.get("thread_id") or "") or None
            if checkpoint_id:
                return checkpoint_id, thread_id
    run_id = str(graph_state.get("run_id") or "graph")
    return _stable_id("checkpoint", f"{run_id}:final"), _stable_id("thread", run_id)


def persist_graph_checkpoint(
    *,
    workspace_root: str | Path,
    graph_state: dict[str, Any],
    status: str,
    node: str | None = None,
    evidence_path: str | None = None,
    graph_state_path: str | None = None,
    checkpoint_id: str | None = None,
    thread_id: str | None = None,
    parent_checkpoint_id: str | None = None,
    fork_reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> GraphCheckpointRecord:
    default_checkpoint_id, default_thread_id = _checkpoint_ref_from_graph_state(graph_state)
    record = GraphCheckpointRecord(
        checkpoint_id=checkpoint_id or default_checkpoint_id,
        run_id=str(graph_state.get("run_id") or _stable_id("run", json.dumps(graph_state, sort_keys=True))),
        thread_id=thread_id or default_thread_id,
        status=status,
        node=node,
        evidence_path=evidence_path,
        graph_state_path=graph_state_path,
        parent_checkpoint_id=parent_checkpoint_id,
        fork_reason=fork_reason,
        metadata={
            "recorded_at": _utc_now_iso(),
            "graph_state": graph_state,
            **(metadata or {}),
        },
    )
    store = _read_store(workspace_root)
    store["checkpoints"][record.checkpoint_id] = record.model_dump(mode="json")
    _write_store(workspace_root, store)
    return record


def list_graph_checkpoints(
    *,
    workspace_root: str | Path,
    run_id: str | None = None,
    thread_id: str | None = None,
) -> list[GraphCheckpointRecord]:
    records = [GraphCheckpointRecord.model_validate(item) for item in _read_store(workspace_root)["checkpoints"].values()]
    if run_id:
        records = [record for record in records if record.run_id == run_id]
    if thread_id:
        records = [record for record in records if record.thread_id == thread_id]
    return sorted(records, key=lambda item: item.created_at)


def build_graph_checkpoint_history(
    *,
    workspace_root: str | Path,
    run_id: str | None = None,
    thread_id: str | None = None,
) -> dict[str, Any]:
    records = list_graph_checkpoints(workspace_root=workspace_root, run_id=run_id, thread_id=thread_id)
    return {
        "schema_version": CHECKPOINT_STORE_SCHEMA,
        "history_count": len(records),
        "checkpoints": [
            {
                "checkpoint_id": record.checkpoint_id,
                "run_id": record.run_id,
                "thread_id": record.thread_id,
                "status": record.status,
                "node": record.node,
                "parent_checkpoint_id": record.parent_checkpoint_id,
                "fork_reason": record.fork_reason,
                "evidence_path": record.evidence_path,
                "graph_state_path": record.graph_state_path,
                "failure_class": record.metadata.get("failure_class"),
                "kernel_version": record.metadata.get("kernel_version"),
                "checkpoint_backend": record.metadata.get("checkpoint_backend"),
                "langgraph_checkpoint_id": record.metadata.get("langgraph_checkpoint_id"),
                "langgraph_history_count": len(record.metadata.get("langgraph_checkpoint_history") or []),
                "graph_kind": record.metadata.get("graph_kind"),
            }
            for record in records
        ],
    }


def build_graph_checkpoint_state(
    *,
    workspace_root: str | Path,
    checkpoint_id: str,
) -> dict[str, Any]:
    record = get_graph_checkpoint(workspace_root=workspace_root, checkpoint_id=checkpoint_id)
    if record is None:
        return {
            "schema_version": CHECKPOINT_STORE_SCHEMA,
            "status": "failed",
            "failure_class": "checkpoint_not_found",
            "checkpoint_id": checkpoint_id,
        }
    return {
        "schema_version": CHECKPOINT_STORE_SCHEMA,
        "status": "completed",
        "checkpoint_id": record.checkpoint_id,
        "thread_id": record.thread_id,
        "record": record.model_dump(mode="json"),
        "graph_state": record.metadata.get("graph_state"),
        "langgraph_checkpoint_history": record.metadata.get("langgraph_checkpoint_history") or [],
        "langgraph_state_snapshot": record.metadata.get("langgraph_state_snapshot"),
    }


def get_graph_checkpoint(*, workspace_root: str | Path, checkpoint_id: str) -> GraphCheckpointRecord | None:
    payload = _read_store(workspace_root)["checkpoints"].get(checkpoint_id)
    return GraphCheckpointRecord.model_validate(payload) if payload else None


def fork_graph_checkpoint(
    *,
    workspace_root: str | Path,
    checkpoint_id: str,
    reason: str,
) -> GraphCheckpointRecord:
    parent = get_graph_checkpoint(workspace_root=workspace_root, checkpoint_id=checkpoint_id)
    if parent is None:
        raise KeyError(f"graph checkpoint not found: {checkpoint_id}")
    graph_state = dict(parent.metadata.get("graph_state") or {})
    fork_id = _stable_id("checkpoint_fork", f"{checkpoint_id}:{reason}:{_utc_now_iso()}")
    thread_id = _stable_id("thread_fork", fork_id)
    return persist_graph_checkpoint(
        workspace_root=workspace_root,
        graph_state=graph_state,
        status="forked",
        node=parent.node,
        evidence_path=parent.evidence_path,
        graph_state_path=parent.graph_state_path,
        checkpoint_id=fork_id,
        thread_id=thread_id,
        parent_checkpoint_id=checkpoint_id,
        fork_reason=reason,
        metadata={"forked_from": checkpoint_id, "original_status": parent.status},
    )


def build_graph_repair_decision(
    *,
    checkpoint: GraphCheckpointRecord,
    failure_class: str | None = None,
    fix_iteration: int = 0,
    max_fix_iterations: int = 2,
) -> GraphRepairDecision:
    effective_failure = failure_class or checkpoint.metadata.get("failure_class")
    if checkpoint.status == "completed":
        action = "no_repair_needed"
        next_node = None
        human_review = False
        reason = "checkpoint already completed"
    elif fix_iteration >= max_fix_iterations:
        action = "request_human_review"
        next_node = None
        human_review = True
        reason = "max fix iterations reached"
    else:
        action = "retry_from_checkpoint"
        next_node = "validate" if effective_failure == "artifact_validation_failed" else "policy_review"
        human_review = False
        reason = "repair loop can retry from checkpoint"
    return GraphRepairDecision(
        checkpoint_id=checkpoint.checkpoint_id,
        status=checkpoint.status,
        action=action,
        failure_class=effective_failure,
        next_node=next_node,
        max_fix_iterations=max_fix_iterations,
        human_review_required=human_review,
        evidence_path=checkpoint.evidence_path,
        reason=reason,
        metadata={"run_id": checkpoint.run_id, "thread_id": checkpoint.thread_id, "fix_iteration": fix_iteration},
    )
