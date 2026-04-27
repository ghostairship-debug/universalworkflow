from __future__ import annotations

import hashlib
import importlib.util
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contracts import SideEffectLevel, WorkflowGraphNodeResult


MULTI_AGENT_GRAPH_SCHEMA = "m89_multi_agent_graph_v1"
MULTI_AGENT_SUBGRAPH_VERSION = "m93_role_subgraph_v1"
MULTI_AGENT_ROLES = ["planner", "implementer", "reviewer", "validator", "evidence"]
ROUTE_LANE_MAPPING = {
    "simple": {"adapter": "opencode", "model": "minimax/MiniMax-M2.7", "readiness_claim": "unchanged"},
    "medium": {"adapter": "deepseek", "model": "deepseek/deepseek-v4-flash", "fallback": "codex", "readiness_claim": "unchanged"},
    "complex": {"adapter": "codex", "model": "gpt-5.5", "readiness_claim": "unchanged"},
}


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _stable_file(goal: str, role: str, index: int) -> str:
    digest = hashlib.sha256(f"{goal}:{role}:{index}".encode("utf-8")).hexdigest()[:10]
    return f"{index:02d}_{role}_{digest}.md"


def _default_tasks(goal: str, evidence_root: Path) -> list[dict[str, Any]]:
    return [
        {
            "task_id": f"agent_{index}_{role}",
            "role": role,
            "goal": f"{role} proposal for {goal}",
            "write_set": [(evidence_root / _stable_file(goal, role, index)).as_posix()],
        }
        for index, role in enumerate(MULTI_AGENT_ROLES, start=1)
    ]


def _write_agent_artifact(task: dict[str, Any]) -> dict[str, Any]:
    started_at = time.perf_counter()
    path = Path(task["write_set"][0])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"# {task['role'].title()} Artifact",
                "",
                f"Task: {task['task_id']}",
                f"Goal: {task['goal']}",
                f"Created at: {_utc_now_iso()}",
                "",
                "This is artifact-only multi-agent graph evidence.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "task_id": task["task_id"],
        "role": task["role"],
        "status": "completed",
        "artifact_path": path.as_posix(),
        "elapsed_ms": max(int((time.perf_counter() - started_at) * 1000), 0),
    }


def _write_evidence(evidence_root: Path, payload: dict[str, Any]) -> Path:
    evidence_root.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    path = evidence_root / f"multi_agent_graph_{digest}.json"
    payload["evidence_path"] = path.as_posix()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_set_conflicts(tasks: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    conflicts: set[str] = set()
    for task in tasks:
        for item in task.get("write_set", []):
            normalized = Path(str(item)).as_posix()
            if normalized in seen:
                conflicts.add(normalized)
            seen.add(normalized)
    return sorted(conflicts)


def _subgraph_backend() -> dict[str, Any]:
    try:
        from langgraph.graph import END, START, StateGraph

        builder = StateGraph(dict)
        builder.add_node("route_parity", lambda state: {**state, "route_parity_checked": True})
        builder.add_edge(START, "route_parity")
        builder.add_edge("route_parity", END)
        graph = builder.compile()
        graph.invoke({"route_parity_checked": False})
        return {"provider": "langgraph", "backend": "compiled_role_subgraph"}
    except Exception as exc:
        return {"provider": "linear", "backend": "deterministic_fallback", "fallback_reason": f"{type(exc).__name__}: {exc}"}


def _supervisor_probe() -> dict[str, Any]:
    available = importlib.util.find_spec("langgraph_supervisor") is not None
    payload: dict[str, Any] = {
        "package": "langgraph-supervisor",
        "available": available,
        "enabled_by_default": False,
        "adoption_decision": "probe_only",
        "reason": "explicit StateGraph subgraphs keep write_set and receipt boundaries easier to audit",
    }
    if not available:
        payload["fallback_reason"] = "package_not_installed"
        return payload
    try:
        import langgraph_supervisor

        payload["module_file"] = getattr(langgraph_supervisor, "__file__", None)
        payload["probe_status"] = "imported"
    except Exception as exc:
        payload["probe_status"] = "failed"
        payload["fallback_reason"] = f"{type(exc).__name__}: {exc}"
    return payload


def run_multi_agent_artifact_graph(
    *,
    goal: str,
    workspace_root: str | Path,
    evidence_dir: str | Path | None = None,
    tasks: list[dict[str, Any]] | None = None,
    route_lane: str = "simple",
    max_workers: int = 2,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    evidence_root = Path(evidence_dir).resolve() if evidence_dir else workspace / "state" / "multi_agent_graph"
    planned_tasks = tasks or _default_tasks(goal, evidence_root)
    conflicts = _write_set_conflicts(planned_tasks)
    route = ROUTE_LANE_MAPPING.get(route_lane, ROUTE_LANE_MAPPING["simple"])
    subgraph = _subgraph_backend()
    payload: dict[str, Any] = {
        "schema_version": MULTI_AGENT_GRAPH_SCHEMA,
        "subgraph_version": MULTI_AGENT_SUBGRAPH_VERSION,
        "goal": goal,
        "route_lane": route_lane,
        "route_decision": route,
        "route_parity": {
            "cluster_template_selection": "wrap",
            "cluster_member_roles": "migrate",
            "provider_model_routing": "keep",
            "write_set_ownership": "keep",
        },
        "subgraph_backend": subgraph,
        "supervisor_probe": _supervisor_probe(),
        "provider_readiness_unchanged": True,
        "max_workers": max_workers,
        "task_count": len(planned_tasks),
        "created_at": _utc_now_iso(),
    }
    if conflicts:
        result = WorkflowGraphNodeResult(
            node_id="write_set_conflict_guard",
            status="blocked",
            side_effect_level=SideEffectLevel.none,
            next_action="downgrade_to_serial_or_replan_write_set",
            failure_class="write_set_conflict",
            metadata={"conflicts": conflicts},
        )
        payload.update(
            {
                "status": "blocked",
                "failure_class": "write_set_conflict",
                "conflicts": conflicts,
                "node_results": [result.model_dump(mode="json")],
                "artifacts": [],
            }
        )
        _write_evidence(evidence_root, payload)
        return payload

    artifacts: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
        futures = [executor.submit(_write_agent_artifact, task) for task in planned_tasks]
        for future in as_completed(futures):
            artifacts.append(future.result())
    artifacts = sorted(artifacts, key=lambda item: item["task_id"])
    node_results = [
        WorkflowGraphNodeResult(
            node_id=item["task_id"],
            status="completed",
            side_effect_level=SideEffectLevel.artifact_only,
            evidence_path=item["artifact_path"],
            next_action="merge_evidence",
            metadata={"role": item["role"], "elapsed_ms": item["elapsed_ms"]},
        ).model_dump(mode="json")
        for item in artifacts
    ]
    payload.update(
        {
            "status": "completed",
            "failure_class": None,
            "parallel_artifact_only": max_workers > 1,
            "node_results": node_results,
            "artifacts": artifacts,
        }
    )
    _write_evidence(evidence_root, payload)
    return payload
