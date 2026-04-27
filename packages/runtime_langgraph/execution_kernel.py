from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contracts import (
    GraphCheckpointRef,
    GraphEvidenceManifest,
    SideEffectLevel,
    TaskCard,
    WorkflowGraphNodeResult,
    WorkflowGraphState,
)
from packages.runtime_langgraph.interrupts import build_human_approval_interrupt
from packages.runtime_langgraph.checkpoint_store import persist_graph_checkpoint
from packages.runtime_langgraph.checkpointer_factory import open_graph_checkpointer


GRAPH_KERNEL_NODES = ["plan", "policy_review", "execute_artifact_only", "validate", "evidence", "closeout"]
GRAPH_KERNEL_EVIDENCE_SCHEMA = "m86_graph_execution_kernel_v1"
GRAPH_KERNEL_VERSION = "m91_graph_execution_kernel_v2"
GRAPH_STREAM_MODES = ["values", "updates", "tasks", "debug"]


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _elapsed_ms(started_at: float) -> int:
    return max(int((time.perf_counter() - started_at) * 1000), 0)


def _stable_ref(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _safe_filename(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"artifact_{digest}.md"


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


class ArtifactOnlyGraphExecutionKernel:
    """M86 graph execution kernel for artifact-only work.

    The kernel may use LangGraph when installed, but the contract and safety
    behavior are identical in the deterministic fallback path.
    """

    def __init__(self) -> None:
        self.node_registry = self._build_node_registry()
        self.provider = "linear"
        self.execution_backend = "deterministic_fallback"
        self.fallback_reason: str | None = "langgraph_not_compiled"
        self._compiled_graph = self._compile_graph()
        if self._compiled_graph is not None:
            self.provider = "langgraph"
            self.execution_backend = "langgraph_compiled_stategraph"
            self.fallback_reason = None

    def _compile_graph(self, checkpointer: Any | None = None) -> Any | None:
        try:
            from langgraph.graph import END, START, StateGraph

            builder = StateGraph(dict)
            for node_name, node_fn in self.node_registry.items():
                builder.add_node(node_name, node_fn)
            builder.add_edge(START, "plan")
            builder.add_edge("plan", "policy_review")
            builder.add_edge("policy_review", "execute_artifact_only")
            builder.add_edge("execute_artifact_only", "validate")
            builder.add_edge("validate", "evidence")
            builder.add_edge("evidence", "closeout")
            builder.add_edge("closeout", END)
            if checkpointer is not None:
                return builder.compile(checkpointer=checkpointer)
            return builder.compile()
        except Exception as exc:
            self.fallback_reason = f"{type(exc).__name__}: {exc}"
            return None

    def _build_node_registry(self) -> dict[str, Any]:
        return {
            "plan": self._plan_node,
            "policy_review": self._policy_review_node,
            "execute_artifact_only": self._execute_artifact_only_node,
            "validate": self._validate_node,
            "evidence": self._evidence_node,
            "closeout": self._closeout_node,
        }

    def describe(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "kernel_version": GRAPH_KERNEL_VERSION,
            "execution_backend": self.execution_backend,
            "fallback_reason": self.fallback_reason,
            "nodes": list(GRAPH_KERNEL_NODES),
            "registered_nodes": list(self.node_registry),
            "stream_modes": list(GRAPH_STREAM_MODES),
            "side_effect_policy": {
                "allowed": [SideEffectLevel.none.value, SideEffectLevel.artifact_only.value],
                "blocked_requires_workflow_gate": [
                    SideEffectLevel.workspace_write.value,
                    SideEffectLevel.repo_mutation.value,
                    SideEffectLevel.external_action.value,
                ],
            },
        }

    def preview(self, *, goal: str, preset_id: str | None = None) -> dict[str, Any]:
        run_id = _stable_ref("run", goal)
        graph_state = WorkflowGraphState(
            run_id=run_id,
            phase_id="M86-preview",
            task_cards=[
                TaskCard(
                    run_id=run_id,
                    title="Graph artifact preview",
                    description=goal,
                    acceptance_criteria=["artifact-only graph path is safe to execute"],
                )
            ],
        )
        return {
            "schema_version": GRAPH_KERNEL_EVIDENCE_SCHEMA,
            "kernel_version": GRAPH_KERNEL_VERSION,
            "mode": "preview",
            "goal": goal,
            "preset_id": preset_id,
            "provider": self.provider,
            "execution_backend": self.execution_backend,
            "fallback_reason": self.fallback_reason,
            "nodes": list(GRAPH_KERNEL_NODES),
            "graph_state": graph_state.model_dump(mode="json"),
            "side_effect_policy": self.describe()["side_effect_policy"],
        }

    def _snapshot_from_compiled_graph(self, compiled_graph: Any, config: dict[str, Any]) -> dict[str, Any] | None:
        try:
            return self._state_snapshot_summary(compiled_graph.get_state(config))
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    def _history_from_compiled_graph(self, compiled_graph: Any, config: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            return [self._state_snapshot_summary(snapshot) for snapshot in compiled_graph.get_state_history(config)]
        except Exception as exc:
            return [{"error": f"{type(exc).__name__}: {exc}"}]

    def _state_snapshot_summary(self, snapshot: Any) -> dict[str, Any]:
        config = getattr(snapshot, "config", None) or {}
        configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
        tasks = []
        for task in getattr(snapshot, "tasks", ()) or ():
            tasks.append(
                {
                    "id": getattr(task, "id", None),
                    "name": getattr(task, "name", None),
                    "error": _json_safe(getattr(task, "error", None)),
                    "interrupt_count": len(getattr(task, "interrupts", ()) or ()),
                }
            )
        return {
            "thread_id": configurable.get("thread_id"),
            "checkpoint_ns": configurable.get("checkpoint_ns", ""),
            "checkpoint_id": configurable.get("checkpoint_id"),
            "created_at": getattr(snapshot, "created_at", None),
            "next": list(getattr(snapshot, "next", ()) or ()),
            "metadata": _json_safe(getattr(snapshot, "metadata", {}) or {}),
            "tasks": tasks,
            "interrupt_count": len(getattr(snapshot, "interrupts", ()) or ()),
            "values": _json_safe(getattr(snapshot, "values", None)),
        }

    def _latest_langgraph_checkpoint(self, history: list[dict[str, Any]]) -> dict[str, Any] | None:
        for item in history:
            if item.get("checkpoint_id"):
                return item
        return None

    def run(
        self,
        *,
        goal: str,
        workspace_root: str | Path,
        evidence_dir: str | Path | None = None,
        preset_id: str | None = None,
        requested_side_effect_level: SideEffectLevel | str = SideEffectLevel.artifact_only,
        artifact_path: str | Path | None = None,
    ) -> dict[str, Any]:
        workspace = Path(workspace_root).resolve()
        evidence_root = Path(evidence_dir).resolve() if evidence_dir else workspace / "state" / "graph_kernel"
        evidence_root.mkdir(parents=True, exist_ok=True)
        requested_level = SideEffectLevel(requested_side_effect_level)
        default_artifact_path = evidence_root / _safe_filename(goal)
        state: dict[str, Any] = {
            "schema_version": GRAPH_KERNEL_EVIDENCE_SCHEMA,
            "kernel_version": GRAPH_KERNEL_VERSION,
            "goal": goal,
            "preset_id": preset_id,
            "workspace_root": workspace.as_posix(),
            "evidence_dir": evidence_root.as_posix(),
            "requested_side_effect_level": requested_level.value,
            "artifact_path": Path(artifact_path).resolve().as_posix() if artifact_path else default_artifact_path.as_posix(),
            "run_id": _stable_ref("run", goal),
            "path": [],
            "node_timings": [],
            "node_results": [],
            "status": "running",
            "stream_events": [],
            "langgraph_stream_parts": [],
            "created_at": _utc_now_iso(),
        }
        thread_id = _stable_ref("thread", state["run_id"])
        state["thread_id"] = thread_id
        checkpointer_handle = open_graph_checkpointer(workspace, graph_id="artifact_kernel")
        state["checkpoint_backend"] = checkpointer_handle.describe()
        compiled_graph = self._compile_graph(checkpointer=checkpointer_handle.saver) if checkpointer_handle.saver else None
        try:
            if compiled_graph is not None:
                config = {"configurable": {"thread_id": thread_id}}
                state["langgraph_config"] = config
                final_values: dict[str, Any] | None = None
                stream_parts: list[dict[str, Any]] = []
                for part in compiled_graph.stream(
                    state,
                    config=config,
                    stream_mode=GRAPH_STREAM_MODES,
                    durability="sync",
                    version="v2",
                ):
                    safe_part = _json_safe(part)
                    stream_parts.append(safe_part)
                    if safe_part.get("type") == "values" and isinstance(safe_part.get("data"), dict):
                        final_values = safe_part["data"]
                state = dict(_json_safe(final_values)) if final_values is not None else state
                state["langgraph_stream_parts"] = stream_parts
                state["langgraph_state_snapshot"] = self._snapshot_from_compiled_graph(compiled_graph, config)
                state["langgraph_checkpoint_history"] = self._history_from_compiled_graph(compiled_graph, config)
                latest = self._latest_langgraph_checkpoint(state.get("langgraph_checkpoint_history", []))
                if latest:
                    state["langgraph_latest_checkpoint_id"] = latest.get("checkpoint_id")
                state["checkpoint_backend"] = checkpointer_handle.describe()
            elif self._compiled_graph is not None:
                state = self._compiled_graph.invoke(state)
            else:
                for node_name in GRAPH_KERNEL_NODES:
                    state = getattr(self, f"_{node_name}_node")(state)
            return self._result_from_state(state)
        finally:
            checkpointer_handle.close()

    def _plan_node(self, state: dict[str, Any]) -> dict[str, Any]:
        def _apply(updated: dict[str, Any]) -> dict[str, Any]:
            task_card = TaskCard(
                run_id=updated["run_id"],
                title="M86 artifact-only graph task",
                description=str(updated["goal"]),
                acceptance_criteria=["artifact exists", "evidence manifest references graph state"],
            )
            graph_state = WorkflowGraphState(
                run_id=updated["run_id"],
                phase_id="M86",
                task_cards=[task_card],
                write_set=[updated["artifact_path"]],
                checkpoint_refs=[
                    GraphCheckpointRef(
                        checkpoint_id=_stable_ref("checkpoint", f"{updated['run_id']}:plan"),
                        thread_id=_stable_ref("thread", updated["run_id"]),
                        source="m86_artifact_kernel",
                    )
                ],
            )
            return {
                **updated,
                "graph_state": graph_state.model_dump(mode="json"),
                "node_results": [
                    *updated.get("node_results", []),
                    WorkflowGraphNodeResult(
                        node_id="plan",
                        status="completed",
                        side_effect_level=SideEffectLevel.none,
                        next_action="policy_review",
                    ).model_dump(mode="json"),
                ],
            }

        return self._with_timing(state, "plan", _apply)

    def _policy_review_node(self, state: dict[str, Any]) -> dict[str, Any]:
        def _apply(updated: dict[str, Any]) -> dict[str, Any]:
            requested_level = SideEffectLevel(updated["requested_side_effect_level"])
            if requested_level in {
                SideEffectLevel.workspace_write,
                SideEffectLevel.repo_mutation,
                SideEffectLevel.external_action,
            }:
                interrupt = build_human_approval_interrupt(
                    run_id=updated["run_id"],
                    requested_side_effect_level=requested_level.value,
                    write_set=[updated["artifact_path"]],
                    workspace_root=updated["workspace_root"],
                    thread_id=_stable_ref("thread", updated["run_id"]),
                    checkpoint_id=_stable_ref("checkpoint", f"{updated['run_id']}:policy_review"),
                    operator_hint="Review the graph handoff before allowing any high-risk side effect.",
                    metadata={"goal": updated["goal"], "node_id": "policy_review"},
                )
                blocked = WorkflowGraphNodeResult(
                    node_id="policy_review",
                    status="blocked",
                    side_effect_level=requested_level,
                    workflow_gate_required=True,
                    next_action="return_to_workflow_receipt_or_lease_gate",
                    failure_class="side_effect_requires_workflow_gate",
                    metadata={"interrupt_id": interrupt.interrupt_id},
                )
                return {
                    **updated,
                    "status": "blocked",
                    "failure_class": "side_effect_requires_workflow_gate",
                    "human_interrupt": interrupt.model_dump(mode="json"),
                    "node_results": [*updated.get("node_results", []), blocked.model_dump(mode="json")],
                }
            completed = WorkflowGraphNodeResult(
                node_id="policy_review",
                status="completed",
                side_effect_level=SideEffectLevel.none,
                next_action="execute_artifact_only",
            )
            return {**updated, "node_results": [*updated.get("node_results", []), completed.model_dump(mode="json")]}

        return self._with_timing(state, "policy_review", _apply)

    def _execute_artifact_only_node(self, state: dict[str, Any]) -> dict[str, Any]:
        if state.get("status") == "blocked":
            return self._skip_node(state, "execute_artifact_only")

        def _apply(updated: dict[str, Any]) -> dict[str, Any]:
            artifact_path = Path(updated["artifact_path"])
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            reused = artifact_path.exists()
            if not reused:
                artifact_path.write_text(
                "\n".join(
                        [
                            "# Graph Artifact-Only Output",
                            "",
                            f"Goal: {updated['goal']}",
                            f"Created at: {_utc_now_iso()}",
                            "",
                            "This artifact was written by the graph execution kernel.",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )
            result = WorkflowGraphNodeResult(
                node_id="execute_artifact_only",
                status="completed",
                side_effect_level=SideEffectLevel.artifact_only,
                evidence_path=artifact_path.as_posix(),
                next_action="validate",
                metadata={"reused_existing_artifact": reused},
            )
            return {
                **updated,
                "artifact_reused": reused,
                "node_results": [*updated.get("node_results", []), result.model_dump(mode="json")],
            }

        return self._with_timing(state, "execute_artifact_only", _apply)

    def _validate_node(self, state: dict[str, Any]) -> dict[str, Any]:
        if state.get("status") == "blocked":
            return self._skip_node(state, "validate")

        def _apply(updated: dict[str, Any]) -> dict[str, Any]:
            artifact_path = Path(updated["artifact_path"])
            valid = artifact_path.exists() and str(updated["goal"]) in artifact_path.read_text(encoding="utf-8")
            status = "completed" if valid else "failed"
            result = WorkflowGraphNodeResult(
                node_id="validate",
                status=status,
                side_effect_level=SideEffectLevel.none,
                evidence_path=artifact_path.as_posix() if artifact_path.exists() else None,
                next_action="evidence" if valid else "repair_required",
                failure_class=None if valid else "artifact_validation_failed",
            )
            return {
                **updated,
                "status": "running" if valid else "failed",
                "failure_class": updated.get("failure_class") or (None if valid else "artifact_validation_failed"),
                "node_results": [*updated.get("node_results", []), result.model_dump(mode="json")],
            }

        return self._with_timing(state, "validate", _apply)

    def _evidence_node(self, state: dict[str, Any]) -> dict[str, Any]:
        if state.get("status") == "blocked":
            return self._skip_node(state, "evidence")

        def _apply(updated: dict[str, Any]) -> dict[str, Any]:
            evidence_root = Path(updated["evidence_dir"])
            evidence_id = _stable_ref("graphevidence", updated["goal"])
            evidence_path = evidence_root / f"{evidence_id}.json"
            state_path = evidence_root / f"{_stable_ref('graphstate', updated['goal'])}.json"
            stream_path = evidence_root / f"{_stable_ref('graphstream', updated['goal'])}.jsonl"
            manifest = GraphEvidenceManifest(
                evidence_id=evidence_id,
                evidence_path=evidence_path.as_posix(),
                stage_evidence_paths=[updated["artifact_path"]],
                metadata={"schema_version": GRAPH_KERNEL_EVIDENCE_SCHEMA, "kernel_version": GRAPH_KERNEL_VERSION},
            )
            graph_state = WorkflowGraphState.model_validate(updated["graph_state"])
            graph_state.evidence_refs = [evidence_path.as_posix(), updated["artifact_path"]]
            graph_state.node_results = [WorkflowGraphNodeResult.model_validate(item) for item in updated["node_results"]]
            graph_state.checkpoint_refs.append(
                GraphCheckpointRef(
                    checkpoint_id=_stable_ref("checkpoint", f"{updated['run_id']}:evidence"),
                    thread_id=_stable_ref("thread", updated["run_id"]),
                    source="m86_artifact_kernel",
                )
            )
            state_payload = graph_state.model_dump(mode="json")
            evidence_payload = {
                "schema_version": GRAPH_KERNEL_EVIDENCE_SCHEMA,
                "kernel_version": GRAPH_KERNEL_VERSION,
                "goal": updated["goal"],
                "provider": self.provider,
                "execution_backend": self.execution_backend,
                "fallback_reason": self.fallback_reason,
                "status": updated.get("status"),
                "artifact_path": updated["artifact_path"],
                "artifact_reused": updated.get("artifact_reused", False),
                "graph_state_path": state_path.as_posix(),
                "evidence_manifest": manifest.model_dump(mode="json"),
                "node_results": updated["node_results"],
                "node_timings": updated["node_timings"],
                "stream_events": updated.get("stream_events", []),
                "stream_path": stream_path.as_posix(),
            }
            state_path.write_text(json.dumps(state_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            evidence_path.write_text(json.dumps(evidence_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            stream_path.write_text(
                "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in updated.get("stream_events", [])),
                encoding="utf-8",
            )
            result = WorkflowGraphNodeResult(
                node_id="evidence",
                status="completed",
                side_effect_level=SideEffectLevel.artifact_only,
                evidence_path=evidence_path.as_posix(),
                next_action="closeout",
            )
            return {
                **updated,
                "graph_state": state_payload,
                "evidence_manifest": manifest.model_dump(mode="json"),
                "evidence_path": evidence_path.as_posix(),
                "graph_state_path": state_path.as_posix(),
                "stream_path": stream_path.as_posix(),
                "node_results": [*updated.get("node_results", []), result.model_dump(mode="json")],
            }

        return self._with_timing(state, "evidence", _apply)

    def _closeout_node(self, state: dict[str, Any]) -> dict[str, Any]:
        if state.get("status") == "blocked":
            return self._skip_node(state, "closeout")

        def _apply(updated: dict[str, Any]) -> dict[str, Any]:
            final_status = "completed" if updated.get("status") not in {"failed", "blocked"} else updated["status"]
            result = WorkflowGraphNodeResult(
                node_id="closeout",
                status=final_status,
                side_effect_level=SideEffectLevel.none,
                evidence_path=updated.get("evidence_path"),
                next_action="done" if final_status == "completed" else "repair_required",
                failure_class=updated.get("failure_class"),
            )
            node_results = [*updated.get("node_results", []), result.model_dump(mode="json")]
            self._sync_final_evidence_payload(updated, final_status=final_status, node_results=node_results)
            graph_state = dict(updated.get("graph_state") or {})
            graph_state["node_results"] = node_results
            return {
                **updated,
                "status": final_status,
                "completed_at": _utc_now_iso(),
                "node_results": node_results,
                "graph_state": graph_state,
            }

        return self._with_timing(state, "closeout", _apply)

    def _sync_final_evidence_payload(
        self,
        state: dict[str, Any],
        *,
        final_status: str,
        node_results: list[dict[str, Any]],
    ) -> None:
        evidence_path = state.get("evidence_path")
        graph_state_path = state.get("graph_state_path")
        stream_path = state.get("stream_path")
        if not evidence_path or not graph_state_path:
            return
        evidence_file = Path(evidence_path)
        graph_state_file = Path(graph_state_path)
        if evidence_file.exists():
            evidence_payload = json.loads(evidence_file.read_text(encoding="utf-8"))
            evidence_payload["status"] = final_status
            evidence_payload["node_results"] = node_results
            evidence_payload["stream_events"] = state.get("stream_events", [])
            evidence_file.write_text(json.dumps(evidence_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if graph_state_file.exists():
            graph_state_payload = json.loads(graph_state_file.read_text(encoding="utf-8"))
            graph_state_payload["node_results"] = node_results
            graph_state_file.write_text(json.dumps(graph_state_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if stream_path:
            Path(stream_path).write_text(
                "".join(
                    json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n"
                    for item in state.get("stream_events", [])
                ),
                encoding="utf-8",
            )

    def _skip_node(self, state: dict[str, Any], node_name: str) -> dict[str, Any]:
        def _apply(updated: dict[str, Any]) -> dict[str, Any]:
            result = WorkflowGraphNodeResult(
                node_id=node_name,
                status="skipped",
                side_effect_level=SideEffectLevel.none,
                next_action="blocked",
                failure_class=updated.get("failure_class"),
            )
            return {**updated, "node_results": [*updated.get("node_results", []), result.model_dump(mode="json")]}

        return self._with_timing(state, node_name, _apply)

    def _with_timing(self, state: dict[str, Any], node_name: str, apply_node: Any) -> dict[str, Any]:
        started_at = time.perf_counter()
        path = list(state.get("path", []))
        path.append(node_name)
        stream_events = list(state.get("stream_events", []))
        stream_events.append({"event": "node_started", "node": node_name, "recorded_at": _utc_now_iso()})
        updated = apply_node({**state, "path": path, "stream_events": stream_events})
        timings = list(updated.get("node_timings", []))
        elapsed = _elapsed_ms(started_at)
        timings.append({"node": node_name, "elapsed_ms": elapsed})
        completed_events = list(updated.get("stream_events", []))
        completed_events.append(
            {"event": "node_completed", "node": node_name, "elapsed_ms": elapsed, "recorded_at": _utc_now_iso()}
        )
        return {**updated, "node_timings": timings, "stream_events": completed_events}

    def _result_from_state(self, state: dict[str, Any]) -> dict[str, Any]:
        graph_state = dict(state.get("graph_state") or {})
        if graph_state and state.get("node_results"):
            graph_state["node_results"] = state.get("node_results", [])
        self._sync_runtime_metadata_payload(state)
        persistent_checkpoint = self._persist_result_checkpoint(state, graph_state)
        return {
            "schema_version": GRAPH_KERNEL_EVIDENCE_SCHEMA,
            "kernel_version": GRAPH_KERNEL_VERSION,
            "provider": self.provider,
            "execution_backend": self.execution_backend,
            "fallback_reason": self.fallback_reason,
            "status": state.get("status"),
            "goal": state.get("goal"),
            "preset_id": state.get("preset_id"),
            "path": state.get("path", []),
            "node_timings": state.get("node_timings", []),
            "node_results": state.get("node_results", []),
            "stream_events": state.get("stream_events", []),
            "langgraph_stream_parts": state.get("langgraph_stream_parts", []),
            "checkpoint_backend": state.get("checkpoint_backend"),
            "langgraph_state_snapshot": state.get("langgraph_state_snapshot"),
            "langgraph_checkpoint_history": state.get("langgraph_checkpoint_history", []),
            "langgraph_latest_checkpoint_id": state.get("langgraph_latest_checkpoint_id"),
            "stream_path": state.get("stream_path"),
            "artifact_path": state.get("artifact_path"),
            "artifact_reused": state.get("artifact_reused", False),
            "evidence_path": state.get("evidence_path"),
            "graph_state_path": state.get("graph_state_path"),
            "evidence_manifest": state.get("evidence_manifest"),
            "graph_state": graph_state or state.get("graph_state"),
            "human_interrupt": state.get("human_interrupt"),
            "persistent_checkpoint": persistent_checkpoint,
            "failure_class": state.get("failure_class"),
            "created_at": state.get("created_at"),
            "completed_at": state.get("completed_at"),
        }

    def _sync_runtime_metadata_payload(self, state: dict[str, Any]) -> None:
        evidence_path = state.get("evidence_path")
        graph_state_path = state.get("graph_state_path")
        if evidence_path and Path(evidence_path).exists():
            evidence_payload = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
            evidence_payload["checkpoint_backend"] = state.get("checkpoint_backend")
            evidence_payload["langgraph_stream_parts"] = state.get("langgraph_stream_parts", [])
            evidence_payload["langgraph_state_snapshot"] = state.get("langgraph_state_snapshot")
            evidence_payload["langgraph_checkpoint_history"] = state.get("langgraph_checkpoint_history", [])
            evidence_payload["langgraph_latest_checkpoint_id"] = state.get("langgraph_latest_checkpoint_id")
            Path(evidence_path).write_text(json.dumps(evidence_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if graph_state_path and Path(graph_state_path).exists():
            graph_state_payload = json.loads(Path(graph_state_path).read_text(encoding="utf-8"))
            graph_state_payload.setdefault("metadata", {})
            graph_state_payload["metadata"]["checkpoint_backend"] = state.get("checkpoint_backend")
            graph_state_payload["metadata"]["langgraph_latest_checkpoint_id"] = state.get("langgraph_latest_checkpoint_id")
            Path(graph_state_path).write_text(json.dumps(graph_state_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _persist_result_checkpoint(self, state: dict[str, Any], graph_state: dict[str, Any]) -> dict[str, Any] | None:
        workspace_root = state.get("workspace_root")
        if not workspace_root or not graph_state:
            return None
        human_interrupt = state.get("human_interrupt") if isinstance(state.get("human_interrupt"), dict) else {}
        blocked_node = next(
            (item.get("node_id") for item in state.get("node_results", []) if item.get("status") == "blocked"),
            None,
        )
        checkpoint = persist_graph_checkpoint(
            workspace_root=workspace_root,
            graph_state=graph_state,
            status=str(state.get("status") or "unknown"),
            node=blocked_node or (state.get("path") or [None])[-1],
            evidence_path=state.get("evidence_path"),
            graph_state_path=state.get("graph_state_path"),
            checkpoint_id=human_interrupt.get("checkpoint_id") or state.get("langgraph_latest_checkpoint_id"),
            thread_id=human_interrupt.get("thread_id") or state.get("thread_id"),
            metadata={
                "path": state.get("path", []),
                "failure_class": state.get("failure_class"),
                "node_result_count": len(state.get("node_results", [])),
                "human_interrupt": human_interrupt or None,
                "kernel_version": GRAPH_KERNEL_VERSION,
                "execution_backend": self.execution_backend,
                "graph_kind": "artifact_execution_kernel",
                "checkpoint_backend": state.get("checkpoint_backend"),
                "langgraph_checkpoint_id": state.get("langgraph_latest_checkpoint_id"),
                "langgraph_checkpoint_history": state.get("langgraph_checkpoint_history", []),
                "langgraph_state_snapshot": state.get("langgraph_state_snapshot"),
                "langgraph_config": state.get("langgraph_config"),
            },
        )
        return checkpoint.model_dump(mode="json")


def preview_graph_execution(*, goal: str, preset_id: str | None = None) -> dict[str, Any]:
    return ArtifactOnlyGraphExecutionKernel().preview(goal=goal, preset_id=preset_id)


def run_artifact_only_graph(
    *,
    goal: str,
    workspace_root: str | Path,
    evidence_dir: str | Path | None = None,
    preset_id: str | None = None,
    artifact_path: str | Path | None = None,
) -> dict[str, Any]:
    return ArtifactOnlyGraphExecutionKernel().run(
        goal=goal,
        workspace_root=workspace_root,
        evidence_dir=evidence_dir,
        preset_id=preset_id,
        artifact_path=artifact_path,
        requested_side_effect_level=SideEffectLevel.artifact_only,
    )


def run_graph_with_side_effect_policy(
    *,
    goal: str,
    workspace_root: str | Path,
    requested_side_effect_level: SideEffectLevel | str,
    evidence_dir: str | Path | None = None,
    preset_id: str | None = None,
    artifact_path: str | Path | None = None,
) -> dict[str, Any]:
    return ArtifactOnlyGraphExecutionKernel().run(
        goal=goal,
        workspace_root=workspace_root,
        evidence_dir=evidence_dir,
        preset_id=preset_id,
        artifact_path=artifact_path,
        requested_side_effect_level=requested_side_effect_level,
    )
