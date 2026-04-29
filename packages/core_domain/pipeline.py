from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any, Callable

from packages.contracts import PipelineStage, PipelineStageKind, TaskKind, WorkflowPipeline
from packages.contracts.models import new_id
from packages.core_domain.automation_lease import record_automation_lease_use, validate_automation_lease
from packages.runtime_security.safe_command_runner import SAFE_COMMAND_TIMEOUT_EXIT_CODE, run_safe_command


CommandRunner = Callable[[str, Path, int], dict[str, Any]]
PipelinePreviewer = Callable[[str], WorkflowPipeline]
CapabilityExecutor = Callable[..., dict[str, Any]]
ValidationExecutor = Callable[..., dict[str, Any]]
AgentRoleExecutor = Callable[..., dict[str, Any]]


def _stage(
    *,
    name: str,
    kind: PipelineStageKind,
    order_index: int,
    goal: str,
    preset_id: str | None = None,
    task_kind: TaskKind | None = None,
    adapter_name: str | None = None,
    depends_on: list[str] | None = None,
    write_set: list[str] | None = None,
    validation_commands: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> PipelineStage:
    return PipelineStage(
        name=name,
        stage_kind=kind,
        order_index=order_index,
        goal=goal,
        preset_id=preset_id,
        task_kind=task_kind,
        adapter_name=adapter_name,
        depends_on=list(depends_on or []),
        write_set=list(write_set or []),
        validation_commands=list(validation_commands or []),
        metadata=metadata or {},
    )


def preview_workflow_pipeline(
    goal: str,
    *,
    pipeline_id: str | None = None,
    template: str | None = None,
) -> WorkflowPipeline:
    stages = [
        _stage(
            name="Plan",
            kind=PipelineStageKind.agent_role,
            order_index=0,
            goal="Plan the requested workflow task.",
            preset_id="research_spike",
            metadata={"planning_mode": "template", "direct_mutation_allowed": False},
        ),
        _stage(
            name="Implement",
            kind=PipelineStageKind.capability,
            order_index=1,
            goal="Execute the implementation under workflow control.",
            preset_id="feature_delivery",
            metadata={"planning_mode": "manual"},
        ),
        _stage(
            name="Verify",
            kind=PipelineStageKind.validation_gate,
            order_index=2,
            goal="Run the declared validation gates and collect evidence.",
            validation_commands=["python -m infra.scripts.check_doc_links"],
            metadata={"planning_mode": "template", "direct_mutation_allowed": False},
        ),
    ]
    return WorkflowPipeline(
        pipeline_id=pipeline_id or new_id("pipeline"),
        name="workflow_self_development_pipeline",
        goal=goal,
        execution_mode="serial",
        stages=stages,
        metadata={
            "previewed_at": datetime.now(UTC).isoformat(),
            "stage_count": len(stages),
            "pipeline_semantics": "plan_of_plans",
            "planning_modes": ["manual", "template", "hybrid"],
            "direct_mutation_allowed": False,
            "template_id": template,
            "template_registry": "core_domain_default",
        },
    )


def _stage_dir(root: Path, stage: PipelineStage) -> Path:
    return root / f"{stage.order_index:02d}_{stage.stage_id}"


def _write_stage_artifact(root: Path, stage: PipelineStage, payload: dict[str, Any]) -> str:
    directory = _stage_dir(root, stage)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "stage_result.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path.as_posix()


def _default_command_runner(command: str, cwd: Path, timeout_seconds: int) -> dict[str, Any]:
    return run_safe_command(
        command,
        working_directory=cwd,
        timeout_seconds=timeout_seconds,
        output_limit_bytes=12_000,
    )


def _command_result_for_error(command: str, cwd: Path, error: Exception) -> dict[str, Any]:
    return {
        "command": command,
        "cwd": cwd.as_posix(),
        "exit_code": SAFE_COMMAND_TIMEOUT_EXIT_CODE if error.__class__.__name__ == "TimeoutExpired" else 1,
        "stdout": getattr(error, "stdout", "") or "",
        "stderr": f"{type(error).__name__}: {error}",
        "finished_at": datetime.now(UTC).isoformat(),
    }


def _pipeline_heartbeat_interval_seconds() -> float:
    raw_value = os.getenv("WORKFLOW_PIPELINE_HEARTBEAT_INTERVAL_SECONDS") or "30"
    try:
        interval = float(raw_value)
    except (TypeError, ValueError):
        interval = 30.0
    return max(interval, 0.05)


def _append_pipeline_heartbeat(
    path: Path,
    *,
    pipeline_id: str,
    sequence_no: int,
    status: str,
    current_stage: dict[str, Any],
) -> None:
    payload = {
        "schema_version": "workflow_pipeline_heartbeat_v1",
        "pipeline_id": pipeline_id,
        "sequence_no": sequence_no,
        "status": status,
        "heartbeat_at": datetime.now(UTC).isoformat(),
        "current_stage": dict(current_stage),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _start_pipeline_heartbeat(
    *,
    target_dir: Path,
    pipeline_id: str,
) -> tuple[Event, Thread, dict[str, Any], Lock, Path]:
    heartbeat_path = target_dir / f"{pipeline_id}.heartbeat.jsonl"
    interval_seconds = _pipeline_heartbeat_interval_seconds()
    stop_event = Event()
    current_stage: dict[str, Any] = {"stage_id": None, "stage_name": None, "order_index": None}
    current_stage_lock = Lock()

    def _snapshot_stage() -> dict[str, Any]:
        with current_stage_lock:
            return dict(current_stage)

    def _run() -> None:
        sequence_no = 0
        _append_pipeline_heartbeat(
            heartbeat_path,
            pipeline_id=pipeline_id,
            sequence_no=sequence_no,
            status="running",
            current_stage=_snapshot_stage(),
        )
        while not stop_event.wait(interval_seconds):
            sequence_no += 1
            _append_pipeline_heartbeat(
                heartbeat_path,
                pipeline_id=pipeline_id,
                sequence_no=sequence_no,
                status="running",
                current_stage=_snapshot_stage(),
            )

    thread = Thread(target=_run, name=f"pipeline-heartbeat-{pipeline_id}", daemon=True)
    thread.start()
    return stop_event, thread, current_stage, current_stage_lock, heartbeat_path


def _stage_executor_exception_output(executor: str, error: Exception) -> dict[str, Any]:
    return {
        "executor": executor,
        "error_type": type(error).__name__,
        "message": str(error),
    }


def _default_previewer(goal: str, *, pipeline_id: str | None = None, template: str | None = None) -> WorkflowPipeline:
    return preview_workflow_pipeline(goal, pipeline_id=pipeline_id, template=template)


def run_workflow_pipeline(
    goal: str,
    *,
    workspace_root: str | Path,
    evidence_dir: str | Path | None = None,
    pipeline_id: str | None = None,
    automation_lease_id: str | None = None,
    execute_capabilities: bool = False,
    execute_agent_roles: bool = False,
    live_agent_roles: bool = False,
    repair_loop: bool = False,
    max_repair_attempts: int = 3,
    require_real_assets: bool = False,
    require_cocos_ecosystem: bool = False,
    require_human_player_review: bool = False,
    template: str | None = None,
    cocos_bridge_mode: str = "auto",
    cocos_bridge_timeout_seconds: int = 180,
    cocos_bridge_report_path: str | Path | None = None,
    allow_existing_cocos_process: bool = False,
    require_build: bool = False,
    require_playtest: bool = True,
    require_commercial: bool = True,
    command_runner: CommandRunner | None = None,
    command_timeout_seconds: int = 180,
    pipeline_previewer: Callable[..., WorkflowPipeline] | None = None,
    capability_executor: CapabilityExecutor | None = None,
    validation_executor: ValidationExecutor | None = None,
    agent_role_executor: AgentRoleExecutor | None = None,
    capability_inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    previewer = pipeline_previewer or _default_previewer
    pipeline = previewer(goal, pipeline_id=pipeline_id, template=template)
    root = Path(workspace_root).resolve()
    target_dir = Path(evidence_dir) if evidence_dir is not None else root / "state" / "pipeline_runs"
    target_dir.mkdir(parents=True, exist_ok=True)

    write_set = sorted({item for stage in pipeline.stages for item in stage.write_set})
    if automation_lease_id:
        validate_automation_lease(
            workspace_root=root,
            lease_id=automation_lease_id,
            action="pipeline_run",
            write_set=write_set,
        )

    heartbeat_stop, heartbeat_thread, heartbeat_stage, heartbeat_stage_lock, heartbeat_path = _start_pipeline_heartbeat(
        target_dir=target_dir,
        pipeline_id=pipeline.pipeline_id,
    )
    results: list[dict[str, Any]] = []
    status_by_stage: dict[str, str] = {}
    pipeline_status = "completed"
    stop_reason: str | None = None
    runner = command_runner or _default_command_runner
    shared_outputs: dict[str, Any] = {}
    resolved_capability_inputs = dict(capability_inputs or {})
    resolved_capability_inputs.setdefault("pipeline_id", pipeline.pipeline_id)
    resolved_capability_inputs.setdefault("pipeline_goal", pipeline.goal)
    resolved_capability_inputs.setdefault("pipeline_name", pipeline.name)
    resolved_capability_inputs.setdefault("pipeline_template", template or pipeline.metadata.get("template_id"))
    resolved_capability_inputs.setdefault("live_agent_roles", live_agent_roles)
    resolved_capability_inputs.setdefault("repair_loop", repair_loop)
    resolved_capability_inputs.setdefault("max_repair_attempts", max_repair_attempts)
    resolved_capability_inputs.setdefault("require_real_assets", require_real_assets)
    resolved_capability_inputs.setdefault("require_cocos_ecosystem", require_cocos_ecosystem)
    resolved_capability_inputs.setdefault("require_human_player_review", require_human_player_review)
    resolved_capability_inputs.setdefault("cocos_bridge_mode", cocos_bridge_mode)
    resolved_capability_inputs.setdefault("cocos_bridge_timeout_seconds", cocos_bridge_timeout_seconds)
    resolved_capability_inputs.setdefault("cocos_bridge_report_path", cocos_bridge_report_path)
    resolved_capability_inputs.setdefault("allow_existing_cocos_process", allow_existing_cocos_process)

    for stage in sorted(pipeline.stages, key=lambda item: item.order_index):
        with heartbeat_stage_lock:
            heartbeat_stage.update(
                {
                    "stage_id": stage.stage_id,
                    "stage_name": stage.name,
                    "order_index": stage.order_index,
                    "stage_kind": str(stage.stage_kind),
                }
            )
        dependency_statuses = [status_by_stage.get(stage_id) for stage_id in stage.depends_on]
        if any(status != "completed" for status in dependency_statuses):
            result = {
                "stage_id": stage.stage_id,
                "name": stage.name,
                "stage_kind": str(stage.stage_kind),
                "status": "skipped",
                "execution_mode": "serial",
                "failure_class": "dependency_not_completed",
                "write_set": stage.write_set,
                "validation_commands": stage.validation_commands,
                "metadata": stage.metadata,
            }
            result["evidence_path"] = _write_stage_artifact(target_dir, stage, result)
            results.append(result)
            status_by_stage[stage.stage_id] = "skipped"
            if pipeline_status == "completed":
                pipeline_status = "blocked"
                stop_reason = "dependency_not_completed"
            continue

        stage_kind = str(stage.stage_kind)
        result = {
            "stage_id": stage.stage_id,
            "name": stage.name,
            "stage_kind": stage_kind,
            "execution_mode": "serial",
            "write_set": stage.write_set,
            "validation_commands": stage.validation_commands,
            "metadata": stage.metadata,
        }

        if stage_kind in {str(PipelineStageKind.agent_role), str(PipelineStageKind.cluster)}:
            role_payload = {"handled": False}
            if execute_agent_roles and agent_role_executor is not None:
                try:
                    role_payload = agent_role_executor(
                        stage=stage,
                        root=root,
                        target_dir=target_dir,
                        shared_outputs=shared_outputs,
                        **resolved_capability_inputs,
                    )
                except Exception as exc:
                    result.update(
                        {
                            "status": "failed",
                            "failure_class": "agent_role_executor_exception",
                            "output": _stage_executor_exception_output("agent_role_executor", exc),
                        }
                    )
                    role_payload = {"handled": True}
            if role_payload.get("handled"):
                shared_outputs.update(role_payload.get("shared_outputs") or {})
                result.update(role_payload.get("result") or {})
                if result.get("status") in {"failed", "blocked"}:
                    pipeline_status = str(role_payload.get("pipeline_status") or result["status"])
                    stop_reason = str(role_payload.get("stop_reason") or result.get("failure_class") or "agent_role_stage_failed")
            else:
                result.update(
                    {
                        "status": "stubbed",
                        "failure_class": "stage_executor_not_registered",
                        "execution_backend": "artifact_only_planning",
                        "output": {
                            "goal": stage.goal,
                            "direct_mutation_allowed": bool(stage.metadata.get("direct_mutation_allowed")),
                            "note": "Planning/review stage has no registered executor in this serial pipeline and is recorded as stubbed evidence, not completed work.",
                            "execute_agent_roles": execute_agent_roles,
                        },
                    }
                )
        elif stage_kind == str(PipelineStageKind.capability):
            capability = str(stage.metadata.get("capability") or "")
            if not execute_capabilities:
                result.update(
                    {
                        "status": "blocked",
                        "failure_class": "capability_execution_requires_explicit_enable",
                        "output": {
                            "required_flag": "execute_capabilities",
                            "note": "Capability stages are no longer marked completed unless they actually execute.",
                        },
                    }
                )
                pipeline_status = "blocked"
                stop_reason = "capability_stage_not_executed"
            elif capability_executor is not None:
                try:
                    capability_payload = capability_executor(
                        capability,
                        stage=stage,
                        root=root,
                        target_dir=target_dir,
                        shared_outputs=shared_outputs,
                        require_build=require_build,
                        require_playtest=require_playtest,
                        require_commercial=require_commercial,
                        **resolved_capability_inputs,
                    )
                except Exception as exc:
                    result.update(
                        {
                            "status": "failed",
                            "failure_class": "capability_executor_exception",
                            "output": _stage_executor_exception_output("capability_executor", exc),
                        }
                    )
                    capability_payload = {"handled": True}
                if capability_payload.get("handled"):
                    shared_outputs.update(capability_payload.get("shared_outputs") or {})
                    result.update(capability_payload.get("result") or {})
                    if result.get("status") in {"failed", "blocked"}:
                        pipeline_status = str(capability_payload.get("pipeline_status") or result["status"])
                        stop_reason = str(capability_payload.get("stop_reason") or result.get("failure_class") or "capability_stage_failed")
                else:
                    result.update(_unsupported_capability_result(capability))
                    pipeline_status = "blocked"
                    stop_reason = "unsupported_capability_stage"
            else:
                result.update(_unsupported_capability_result(capability))
                pipeline_status = "blocked"
                stop_reason = "unsupported_capability_stage"
        elif stage_kind == str(PipelineStageKind.validation_gate):
            validation_name = str(stage.metadata.get("validation") or "")
            validation_payload = {"handled": False}
            if validation_executor is not None:
                try:
                    validation_payload = validation_executor(
                        validation_name,
                        shared_outputs=shared_outputs,
                        require_commercial=require_commercial,
                        require_cocos_ecosystem=require_cocos_ecosystem,
                        require_live_agent_roles=live_agent_roles,
                        require_human_player_review=require_human_player_review,
                    )
                except Exception as exc:
                    result.update(
                        {
                            "status": "failed",
                            "failure_class": "validation_executor_exception",
                            "output": _stage_executor_exception_output("validation_executor", exc),
                        }
                    )
                    validation_payload = {"handled": True}
            if validation_payload.get("handled"):
                result.update(validation_payload.get("result") or {})
                if result.get("status") in {"failed", "blocked"}:
                    pipeline_status = str(validation_payload.get("pipeline_status") or result["status"])
                    stop_reason = str(validation_payload.get("stop_reason") or result.get("failure_class") or "validation_failed")
            else:
                command_results: list[dict[str, Any]] = []
                failed = False
                for command in stage.validation_commands:
                    try:
                        command_result = runner(command, root, command_timeout_seconds)
                    except Exception as exc:
                        command_result = _command_result_for_error(command, root, exc)
                    command_results.append(command_result)
                    if int(command_result.get("exit_code") or 0) != 0:
                        failed = True
                        break
                result.update(
                    {
                        "status": "failed" if failed else "completed",
                        "failure_class": "validation_command_failed" if failed else None,
                        "output": {"command_results": command_results},
                    }
                )
                if failed:
                    pipeline_status = "failed"
                    stop_reason = "validation_command_failed"
        else:
            result.update(
                {
                    "status": "blocked",
                    "failure_class": "unsupported_stage_kind",
                    "output": {"stage_kind": stage_kind},
                }
            )
            pipeline_status = "blocked"
            stop_reason = "unsupported_stage_kind"

        result["evidence_path"] = _write_stage_artifact(target_dir, stage, result)
        results.append(result)
        status_by_stage[stage.stage_id] = result["status"]
        if result["status"] in {"failed", "blocked"}:
            for downstream in sorted(pipeline.stages, key=lambda item: item.order_index):
                if downstream.order_index <= stage.order_index:
                    continue
                skipped = {
                    "stage_id": downstream.stage_id,
                    "name": downstream.name,
                    "stage_kind": str(downstream.stage_kind),
                    "status": "skipped",
                    "execution_mode": "serial",
                    "failure_class": "previous_stage_not_completed",
                    "write_set": downstream.write_set,
                    "validation_commands": downstream.validation_commands,
                    "metadata": downstream.metadata,
                }
                skipped["evidence_path"] = _write_stage_artifact(target_dir, downstream, skipped)
                results.append(skipped)
                status_by_stage[downstream.stage_id] = "skipped"
            break

    payload = {
        "pipeline": pipeline.model_dump(mode="json"),
        "stage_results": results,
        "status": pipeline_status,
        "stop_reason": stop_reason,
        "executed_at": datetime.now(UTC).isoformat(),
        "execution_semantics": "real_stage_execution_with_short_circuit",
        "execution_options": {
            "execute_capabilities": execute_capabilities,
            "execute_agent_roles": execute_agent_roles,
            "live_agent_roles": live_agent_roles,
            "repair_loop": repair_loop,
            "max_repair_attempts": max_repair_attempts,
            "require_real_assets": require_real_assets,
            "require_cocos_ecosystem": require_cocos_ecosystem,
            "require_human_player_review": require_human_player_review,
            "cocos_bridge_mode": cocos_bridge_mode,
            "cocos_bridge_timeout_seconds": cocos_bridge_timeout_seconds,
            "cocos_bridge_report_path": str(cocos_bridge_report_path) if cocos_bridge_report_path is not None else None,
            "allow_existing_cocos_process": allow_existing_cocos_process,
            "require_build": require_build,
            "require_playtest": require_playtest,
            "require_commercial": require_commercial,
        },
        "heartbeat_path": heartbeat_path.as_posix(),
    }
    heartbeat_stop.set()
    heartbeat_thread.join(timeout=1.0)
    _append_pipeline_heartbeat(
        heartbeat_path,
        pipeline_id=pipeline.pipeline_id,
        sequence_no=-1,
        status=pipeline_status,
        current_stage=dict(heartbeat_stage),
    )
    output = target_dir / f"{pipeline.pipeline_id}.json"
    payload["evidence_path"] = output.as_posix()
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if automation_lease_id:
        record_automation_lease_use(root, automation_lease_id, action="pipeline_run")
    return payload


def _unsupported_capability_result(capability: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "failure_class": "unsupported_capability_stage",
        "output": {
            "capability": capability or None,
            "note": "No real executor is registered for this capability stage.",
        },
    }
