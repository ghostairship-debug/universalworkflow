from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contributions.games.cocos.capabilities import (
    cocos_capability_contracts,
    judge_commercial_readiness_layers,
)
from packages.contracts.models import new_id
from packages.runtime_langgraph.checkpoint_store import persist_graph_checkpoint
from packages.runtime_langgraph.checkpointer_factory import open_graph_checkpointer


COCOS_GRAPH_PRESSURE_SCHEMA = "m104_cocos_graph_pressure_test_v1"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _stable_ref(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def run_cocos_graph_pressure_test(
    *,
    workspace_root: str | Path,
    project_path: str | Path,
    evidence_dir: str | Path | None = None,
    technical_smoke: bool = True,
    production_scaffold: bool = True,
    player_visible_checks: dict[str, bool] | None = None,
    manual_player_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    project = Path(project_path).resolve()
    evidence_root = Path(evidence_dir).resolve() if evidence_dir else workspace / "state" / "cocos_graph_pressure"
    evidence_root.mkdir(parents=True, exist_ok=True)
    attempt_id = new_id("attempt")
    run_id = _stable_ref("run", f"cocos:{project.as_posix()}:{attempt_id}")
    thread_id = _stable_ref("thread", f"cocos:{run_id}:{attempt_id}")
    handle = open_graph_checkpointer(workspace, graph_id="cocos_pressure")
    try:
        from langgraph.graph import END, START, StateGraph

        def capability_contract(state: dict[str, Any]) -> dict[str, Any]:
            contracts = cocos_capability_contracts(state["project_path"])
            return {
                **state,
                "node_path": [*state.get("node_path", []), "capability_contract"],
                "capability_contracts": contracts,
            }

        def readiness_judge(state: dict[str, Any]) -> dict[str, Any]:
            readiness = judge_commercial_readiness_layers(
                technical_smoke=bool(state["technical_smoke"]),
                production_scaffold=bool(state["production_scaffold"]),
                player_visible_checks=state.get("player_visible_checks") or {},
                manual_player_evidence=state.get("manual_player_evidence") or {},
            )
            awaiting_human = bool(readiness.get("machine_player_visible_go")) and not bool(readiness.get("human_player_review_go"))
            return {
                **state,
                "node_path": [*state.get("node_path", []), "readiness_judge"],
                "readiness": readiness,
                "status": "completed" if readiness["commercial_playable_go"] else "blocked",
                "failure_class": None
                if readiness["commercial_playable_go"]
                else "awaiting_human_player_review"
                if awaiting_human
                else "commercial_playable_no_go",
            }

        def closeout(state: dict[str, Any]) -> dict[str, Any]:
            return {**state, "node_path": [*state.get("node_path", []), "closeout"], "closed_at": _utc_now_iso()}

        builder = StateGraph(dict)
        builder.add_node("capability_contract", capability_contract)
        builder.add_node("readiness_judge", readiness_judge)
        builder.add_node("closeout", closeout)
        builder.add_edge(START, "capability_contract")
        builder.add_edge("capability_contract", "readiness_judge")
        builder.add_edge("readiness_judge", "closeout")
        builder.add_edge("closeout", END)
        graph = builder.compile(checkpointer=handle.saver) if handle.saver else builder.compile()
        config = {"configurable": {"thread_id": thread_id}}
        initial_state = {
            "schema_version": COCOS_GRAPH_PRESSURE_SCHEMA,
            "run_id": run_id,
            "attempt_id": attempt_id,
            "thread_id": thread_id,
            "project_path": project.as_posix(),
            "technical_smoke": bool(technical_smoke),
            "production_scaffold": bool(production_scaffold),
            "player_visible_checks": dict(player_visible_checks or {}),
            "manual_player_evidence": dict(manual_player_evidence or {}),
            "node_path": [],
            "status": "running",
            "created_at": _utc_now_iso(),
            "checkpoint_backend": handle.describe(),
        }
        stream_parts: list[dict[str, Any]] = []
        final_state = initial_state
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
                final_state = safe_part["data"]
        history: list[dict[str, Any]] = []
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
        latest_checkpoint = next((item for item in history if item.get("checkpoint_id")), {})
        evidence_run_root = evidence_root / run_id / attempt_id
        evidence_run_root.mkdir(parents=True, exist_ok=True)
        evidence_path = evidence_run_root / "cocos_graph_pressure.json"
        payload = {
            "schema_version": COCOS_GRAPH_PRESSURE_SCHEMA,
            "status": final_state.get("status"),
            "failure_class": final_state.get("failure_class"),
            "run_id": run_id,
            "attempt_id": attempt_id,
            "thread_id": thread_id,
            "project_path": project.as_posix(),
            "node_path": final_state.get("node_path", []),
            "capability_contracts": final_state.get("capability_contracts"),
            "readiness": final_state.get("readiness"),
            "checkpoint_backend": handle.describe(),
            "langgraph_checkpoint_history": history,
            "langgraph_latest_checkpoint_id": latest_checkpoint.get("checkpoint_id"),
            "stream_parts": stream_parts,
            "evidence_path": evidence_path.as_posix(),
            "created_at": _utc_now_iso(),
        }
        evidence_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        checkpoint = persist_graph_checkpoint(
            workspace_root=workspace,
            graph_state={
                "run_id": run_id,
                "thread_id": thread_id,
                "phase_id": "M104",
                "metadata": {"attempt_id": attempt_id},
                "write_set": [],
                "checkpoint_refs": [
                    {
                        "checkpoint_id": latest_checkpoint.get("checkpoint_id"),
                        "thread_id": thread_id,
                        "source": "langgraph",
                    }
                ],
            },
            status=str(payload["status"] or "unknown"),
            node="cocos_graph_pressure",
            evidence_path=evidence_path.as_posix(),
            checkpoint_id=latest_checkpoint.get("checkpoint_id"),
            thread_id=thread_id,
            metadata={
                "graph_kind": "cocos_graph_pressure",
                "attempt_id": attempt_id,
                "checkpoint_backend": handle.describe(),
                "langgraph_checkpoint_id": latest_checkpoint.get("checkpoint_id"),
                "langgraph_checkpoint_history": history,
                "cocos_readiness": final_state.get("readiness"),
            },
        )
        payload["persistent_checkpoint"] = checkpoint.model_dump(mode="json")
        return payload
    finally:
        handle.close()
