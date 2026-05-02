from __future__ import annotations

import json
import sqlite3
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

import typer

from apps.operator_cli.shared import (
    _db_path_from_context,
    _emit_json,
    _goal_from_task_card,
    _parse_key_value_pairs,
    _run_workflow_action,
    _service,
    _workspace_root_from_context,
)
from packages.core_domain.db import get_migration_status, migrate, reset_db, workspace_scoped_db_path
from packages.core_domain.governance import (
    build_domain_pack_platform_report,
    build_governance_alert_report,
    build_governance_metrics_report,
    build_release_readiness_report,
    build_review_policy_report,
    build_tech_debt_report,
)
from packages.core_domain.repositories import PresetRepository

run_app = typer.Typer(help="Run lifecycle commands.")


def _normal_task_card_path(task_card_path: str | Path | None) -> str | None:
    if task_card_path is None:
        return None
    return Path(task_card_path).resolve().as_posix()


def _emit_from_task_card_progress(
    *,
    db_path: Path,
    run_id: str,
    runtime_task_id: str,
    capability_adapter: str | None,
    task_card_ref: str,
) -> None:
    payload = {
        "event": "workflow_progress",
        "source": "from-task-card",
        "run_id": run_id,
        "runtime_task_id": runtime_task_id,
        "task_card_ref": task_card_ref,
        "capability_adapter": capability_adapter,
        "emitted_at": datetime.now(UTC).isoformat(),
        "runtime_state": _from_task_card_runtime_state(db_path=db_path, run_id=run_id),
    }
    typer.echo("workflow_progress " + json.dumps(payload, ensure_ascii=False, sort_keys=True), err=True)


def _from_task_card_runtime_state(*, db_path: Path, run_id: str) -> dict[str, object]:
    try:
        with sqlite3.connect(db_path) as connection:
            connection.row_factory = sqlite3.Row
            attempt = connection.execute(
                """
                SELECT attempt_id, runtime_task_id, status, created_at, closed_at, close_reason
                FROM runtime_attempts
                WHERE run_id = ?
                ORDER BY sequence_no DESC
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
            lease = connection.execute(
                """
                SELECT lease_id, adapter_name, status, heartbeat_at, lease_expires_at, released_at, release_reason
                FROM worker_leases
                WHERE run_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
            heartbeat = connection.execute(
                """
                SELECT created_at, payload_json
                FROM run_events
                WHERE run_id = ? AND event_type = 'worker_heartbeat_received'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
            provider_events = connection.execute(
                """
                SELECT created_at, payload_json
                FROM run_events
                WHERE run_id = ? AND event_type = 'provider_stream_observed'
                ORDER BY created_at
                """,
                (run_id,),
            ).fetchall()
    except sqlite3.Error as exc:
        return {"status": "db_probe_failed", "error": str(exc)}
    provider_output_events = []
    material_progress_events = []
    for event in provider_events:
        try:
            payload = json.loads(event["payload_json"])
        except (TypeError, json.JSONDecodeError):
            payload = {}
        if payload.get("classification") != "control":
            provider_output_events.append(event)
        if payload.get("is_material_progress"):
            material_progress_events.append(event)
    latest_provider_event = provider_output_events[-1] if provider_output_events else None
    latest_material_event = material_progress_events[-1] if material_progress_events else None
    return {
        "status": "observed",
        "attempt_id": attempt["attempt_id"] if attempt is not None else None,
        "attempt_status": attempt["status"] if attempt is not None else None,
        "worker_lease_id": lease["lease_id"] if lease is not None else None,
        "worker_lease_status": lease["status"] if lease is not None else None,
        "worker_adapter": lease["adapter_name"] if lease is not None else None,
        "worker_heartbeat_at": lease["heartbeat_at"] if lease is not None else None,
        "latest_event_heartbeat_at": heartbeat["created_at"] if heartbeat is not None else None,
        "provider_output_event_count": len(provider_output_events),
        "material_progress_event_count": len(material_progress_events),
        "last_provider_output_at": latest_provider_event["created_at"] if latest_provider_event is not None else None,
        "last_material_progress_at": latest_material_event["created_at"] if latest_material_event is not None else None,
    }


def _start_from_task_card_progress_thread(
    *,
    db_path: Path,
    run_id: str,
    runtime_task_id: str,
    capability_adapter: str | None,
    task_card_ref: str,
    interval_seconds: float = 30.0,
) -> threading.Event:
    stop_event = threading.Event()

    def _loop() -> None:
        while not stop_event.is_set():
            _emit_from_task_card_progress(
                db_path=db_path,
                run_id=run_id,
                runtime_task_id=runtime_task_id,
                capability_adapter=capability_adapter,
                task_card_ref=task_card_ref,
            )
            stop_event.wait(interval_seconds)

    thread = threading.Thread(target=_loop, name=f"from-task-card-progress-{run_id}", daemon=True)
    thread.start()
    return stop_event


def _resume_scope(run_id: str) -> dict[str, object]:
    return {"run_id": run_id}


def _batch_resume_scope(run_ids: list[str], *, max_workers: int | None = None) -> dict[str, object]:
    return {"run_ids": run_ids, "max_workers": max_workers}


def _launch_execute_scope(
    *,
    goal: str,
    preset_id: str,
    adapter_name: str | None = None,
    task_kind: str | None = None,
    task_card_ref: str | None = None,
    task_card_path: str | Path | None = None,
    write_set: list[str] | None = None,
    read_set: list[str] | None = None,
    test_commands: list[str] | None = None,
    max_fix_iterations: int = 0,
    mutation_mode: str | None = None,
    memory_item_ids: list[str] | None = None,
) -> dict[str, object]:
    scope: dict[str, object] = {
        "goal": goal,
        "preset_id": preset_id,
        "execute": True,
        "max_fix_iterations": max_fix_iterations,
    }
    optional_values: dict[str, object | None] = {
        "adapter_name": adapter_name,
        "task_kind": task_kind,
        "task_card_ref": task_card_ref,
        "task_card_path": _normal_task_card_path(task_card_path),
        "write_set": list(write_set or []),
        "requested_write_set": list(write_set or []),
        "read_set": list(read_set or []),
        "test_commands": list(test_commands or []),
        "mutation_mode": mutation_mode,
        "memory_item_ids": list(memory_item_ids or []),
    }
    for key, value in optional_values.items():
        if value not in (None, [], ""):
            scope[key] = value
    return scope


def _consume_cli_receipt(
    ctx: typer.Context,
    *,
    action_type: str,
    receipt_id: str | None,
    scope_payload: dict[str, object],
) -> None:
    service = _service(ctx)
    _run_workflow_action(
        lambda: service.consume_operator_action_receipt(
            receipt_id=receipt_id,
            action_type=action_type,
            scope_payload=scope_payload,
        )
    )


def _prepared_run_requires_repo_mutation_receipt(ctx: typer.Context, run_id: str) -> bool:
    detail = _run_workflow_action(lambda: _service(ctx).get_status_detail(run_id))
    mutation_contract = detail.get("mutation_contract")
    if not isinstance(mutation_contract, dict):
        return False
    return str(mutation_contract.get("mutation_mode") or "") == "patch_apply"


def _create_execute_requires_launch_receipt(
    *,
    mutation_mode: str | None,
    write_set: list[str] | None,
    task_card_path: str | None,
    task_card_ref: str | None,
) -> bool:
    return mutation_mode == "patch_apply" or bool(write_set) or bool(task_card_path) or bool(task_card_ref)


@run_app.command("issue-receipt")
def run_issue_receipt(
    ctx: typer.Context,
    action_type: str = typer.Option(..., "--action-type", help="High-risk action type to authorize."),
    risk_level: str = typer.Option("high", "--risk-level"),
    operator_id: str = typer.Option("local_operator", "--operator-id"),
    run_id: Optional[list[str]] = typer.Option(None, "--run-id", help="Run id for resume or batch resume scopes."),
    max_workers: Optional[int] = typer.Option(None, "--max-workers", min=1),
    goal: Optional[str] = typer.Option(None, "--goal"),
    preset: str = typer.Option("feature_delivery", "--preset"),
    adapter: Optional[str] = typer.Option(None, "--adapter"),
    task_kind: Optional[str] = typer.Option(None, "--task-kind"),
    task_card_ref: Optional[str] = typer.Option(None, "--task-card-ref"),
    task_card_path: Optional[str] = typer.Option(None, "--task-card-path"),
    write_set: Optional[list[str]] = typer.Option(None, "--write-set"),
    read_set: Optional[list[str]] = typer.Option(None, "--read-set"),
    test_command: Optional[list[str]] = typer.Option(None, "--test-command"),
    max_fix_iterations: int = typer.Option(0, "--max-fix-iterations", min=0),
    mutation_mode: Optional[str] = typer.Option(None, "--mutation-mode"),
    memory_item_id: Optional[list[str]] = typer.Option(None, "--memory-item-id"),
    scope_json: Optional[str] = typer.Option(None, "--scope-json", help="Raw JSON scope payload override."),
    ttl_seconds: Optional[int] = typer.Option(None, "--ttl-seconds", min=1),
) -> None:
    if scope_json:
        try:
            scope_payload = json.loads(scope_json)
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"invalid --scope-json: {exc}") from exc
        if not isinstance(scope_payload, dict):
            raise typer.BadParameter("--scope-json must decode to a JSON object")
    elif action_type == "resume_run":
        if not run_id or len(run_id) != 1:
            raise typer.BadParameter("--run-id must be provided exactly once for resume_run")
        scope_payload = _resume_scope(run_id[0])
    elif action_type == "batch_resume_runs":
        if not run_id:
            raise typer.BadParameter("--run-id must be provided at least once for batch_resume_runs")
        scope_payload = _batch_resume_scope(run_id, max_workers=max_workers)
    elif action_type == "launch_execute":
        if not goal:
            raise typer.BadParameter("--goal is required for launch_execute when --scope-json is not provided")
        scope_payload = _launch_execute_scope(
            goal=goal,
            preset_id=preset,
            adapter_name=adapter,
            task_kind=task_kind,
            task_card_ref=task_card_ref,
            task_card_path=task_card_path,
            write_set=write_set,
            read_set=read_set,
            test_commands=test_command,
            max_fix_iterations=max_fix_iterations,
            mutation_mode=mutation_mode,
            memory_item_ids=memory_item_id,
        )
    else:
        scope_payload = {}

    receipt = _run_workflow_action(
        lambda: _service(ctx).issue_operator_action_receipt(
            action_type=action_type,
            risk_level=risk_level,
            operator_id=operator_id,
            requested_write_set=write_set if action_type == "launch_execute" else None,
            scope_payload=scope_payload,
            ttl_seconds=ttl_seconds,
        )
    )
    _emit_json(receipt.model_dump(mode="json"))

@run_app.command("create")
def run_create(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal"),
    preset: str = typer.Option(..., "--preset"),
    task_kind: Optional[str] = typer.Option(None, "--task-kind", help="Requested task kind when compiling."),
    adapter: Optional[str] = typer.Option(None, "--adapter", help="Requested adapter override when compiling."),
    memory_item_id: Optional[list[str]] = typer.Option(None, "--memory-item-id", help="Explicit memory item ids."),
    task_card_ref: Optional[str] = typer.Option(None, "--task-card-ref", help="Detailed task card reference for repo mutation."),
    task_card_path: Optional[str] = typer.Option(None, "--task-card-path", help="Detailed task card path for repo mutation."),
    write_set: Optional[list[str]] = typer.Option(None, "--write-set", help="Explicit writable paths for repo mutation."),
    read_set: Optional[list[str]] = typer.Option(None, "--read-set", help="Explicit read-only context paths for repo mutation."),
    test_command: Optional[list[str]] = typer.Option(None, "--test-command", help="Explicit test commands to run after applying a patch."),
    max_fix_iterations: int = typer.Option(0, "--max-fix-iterations", min=0, help="Maximum bounded repair iterations."),
    mutation_mode: Optional[str] = typer.Option(None, "--mutation-mode", help="artifact_only or patch_apply."),
    prepare: bool = typer.Option(False, "--prepare", help="Prepare the run internally after creation."),
    execute: bool = typer.Option(False, "--execute", help="Execute the prepared run internally."),
    operator_receipt_id: Optional[str] = typer.Option(
        None,
        "--operator-receipt-id",
        help="Receipt id attached to a capability-enforced mutation invocation.",
    ),
) -> None:
    service = _service(ctx)
    run = _run_workflow_action(lambda: service.create_run(goal=goal, preset_id=preset))
    current_run = run
    payload: dict = {}
    if prepare or execute:
        prepared = _run_workflow_action(
            lambda: service.compile_run(
                run.run_id,
                task_kind=task_kind,
                adapter_name=adapter,
                memory_item_ids=memory_item_id,
                task_card_ref=task_card_ref,
                task_card_path=task_card_path,
                write_set=write_set,
                read_set=read_set,
                test_commands=test_command,
                max_fix_iterations=max_fix_iterations,
                mutation_mode=mutation_mode,
            )
        )
        current_run = prepared.run
        payload["prepared_task_id"] = prepared.task_packet.runtime_task_id
        payload["expected_artifacts"] = prepared.task_packet.expected_artifacts
        payload["handoff_id"] = prepared.handoff.handoff_id
        payload["state_ref_id"] = prepared.state_ref.state_ref_id
        payload["domain_pack_id"] = prepared.domain_pack.domain_pack_id if prepared.domain_pack is not None else None
        payload["capability_adapter"] = (
            prepared.capability_route.adapter_name if prepared.capability_route is not None else None
        )
        payload["execution_lane"] = str(prepared.execution_lane)
        payload["mutation_contract"] = (
            prepared.task_packet.mutation_contract.model_dump(mode="json")
            if prepared.task_packet.mutation_contract is not None
            else None
        )
        payload["tool_projection_manifest"] = (
            prepared.tool_projection_manifest.model_dump(mode="json")
            if prepared.tool_projection_manifest is not None
            else None
        )
        payload["mcp_server_profiles"] = [profile.model_dump(mode="json") for profile in prepared.mcp_server_profiles]
        payload["memory_preview"] = (
            prepared.memory_preview.model_dump(mode="json") if prepared.memory_preview is not None else None
        )
    if execute:
        if _create_execute_requires_launch_receipt(
            mutation_mode=mutation_mode,
            write_set=write_set,
            task_card_path=task_card_path,
            task_card_ref=task_card_ref,
        ):
            _consume_cli_receipt(
                ctx,
                action_type="launch_execute",
                receipt_id=operator_receipt_id,
                scope_payload=_launch_execute_scope(
                    goal=goal,
                    preset_id=preset,
                    adapter_name=adapter,
                    task_kind=task_kind,
                    task_card_ref=task_card_ref,
                    task_card_path=task_card_path,
                    write_set=write_set,
                    read_set=read_set,
                    test_commands=test_command,
                    max_fix_iterations=max_fix_iterations,
                    mutation_mode=mutation_mode,
                    memory_item_ids=memory_item_id,
                ),
            )
        executed = _run_workflow_action(lambda: service.resume_run(run.run_id, operator_receipt_id=operator_receipt_id))
        current_run = executed.run
        payload["review_decision"] = executed.review_verdict.decision if executed.review_verdict is not None else None
        payload["evidence_id"] = executed.evidence.evidence_id
    payload["run"] = current_run.model_dump(mode="json")
    _emit_json(payload)


@run_app.command("from-task-card")
def run_from_task_card(
    ctx: typer.Context,
    task_card_path: str = typer.Argument(..., help="Local markdown task card path."),
    preset: str = typer.Option("feature_delivery", "--preset"),
    adapter: Optional[str] = typer.Option(
        None,
        "--adapter",
        help="Patch-capable adapter override. Defaults to the workflow patch-apply route.",
    ),
    task_card_ref: Optional[str] = typer.Option(None, "--task-card-ref", help="Stable task card reference."),
    write_set: Optional[list[str]] = typer.Option(None, "--write-set", help="Explicit writable paths."),
    read_set: Optional[list[str]] = typer.Option(None, "--read-set", help="Explicit read-only context paths."),
    test_command: Optional[list[str]] = typer.Option(None, "--test-command", help="Safe test commands to run."),
    max_fix_iterations: int = typer.Option(0, "--max-fix-iterations", min=0),
    execute: bool = typer.Option(False, "--execute", help="Execute the prepared run immediately."),
    operator_receipt_id: Optional[str] = typer.Option(
        None,
        "--operator-receipt-id",
        help="Receipt id attached to a capability-enforced mutation invocation.",
    ),
) -> None:
    path = Path(task_card_path)
    if not path.exists():
        _emit_json(
            {
                "error": {
                    "code": "task_card_missing",
                    "message": "task card path does not exist",
                    "details": {"path": task_card_path},
                }
            }
        )
        raise typer.Exit(code=1)
    if not write_set:
        _emit_json(
            {
                "error": {
                    "code": "write_set_required",
                    "message": "from-task-card requires at least one --write-set path",
                    "details": {},
                }
            }
        )
        raise typer.Exit(code=1)
    service = _service(ctx)
    ref = task_card_ref or path.stem
    run = _run_workflow_action(lambda: service.create_run(goal=_goal_from_task_card(path), preset_id=preset))
    prepared = _run_workflow_action(
        lambda: service.compile_run(
            run.run_id,
            adapter_name=adapter,
            task_card_ref=ref,
            task_card_path=path.as_posix(),
            write_set=write_set,
            read_set=read_set,
            test_commands=test_command,
            max_fix_iterations=max_fix_iterations,
            mutation_mode="patch_apply",
        )
    )
    payload: dict[str, object] = {
        "run": prepared.run.model_dump(mode="json"),
        "runtime_task_id": prepared.task_packet.runtime_task_id,
        "capability_adapter": prepared.capability_route.adapter_name if prepared.capability_route is not None else None,
        "resolved_execution": prepared.resolved_execution.model_dump(mode="json"),
        "mutation_contract": (
            prepared.task_packet.mutation_contract.model_dump(mode="json")
            if prepared.task_packet.mutation_contract is not None
            else None
        ),
    }
    if execute:
        _consume_cli_receipt(
            ctx,
            action_type="launch_execute",
            receipt_id=operator_receipt_id,
            scope_payload=_launch_execute_scope(
                goal=_goal_from_task_card(path),
                preset_id=preset,
                adapter_name=adapter,
                task_card_ref=ref,
                task_card_path=path,
                write_set=write_set,
                read_set=read_set,
                test_commands=test_command,
                max_fix_iterations=max_fix_iterations,
                mutation_mode="patch_apply",
            ),
        )
        progress_stop = _start_from_task_card_progress_thread(
            db_path=_db_path_from_context(ctx),
            run_id=run.run_id,
            runtime_task_id=prepared.task_packet.runtime_task_id,
            capability_adapter=prepared.capability_route.adapter_name if prepared.capability_route is not None else None,
            task_card_ref=ref,
        )
        try:
            executed = _run_workflow_action(lambda: service.resume_run(run.run_id, operator_receipt_id=operator_receipt_id))
            payload["run"] = executed.run.model_dump(mode="json")
            payload["evidence_id"] = executed.evidence.evidence_id
            payload["review_decision"] = executed.review_verdict.decision if executed.review_verdict is not None else None
            payload["capability_adapter"] = (
                prepared.capability_route.adapter_name if prepared.capability_route is not None else None
            )
            payload["runtime_state"] = _from_task_card_runtime_state(db_path=_db_path_from_context(ctx), run_id=run.run_id)
        finally:
            progress_stop.set()
    payload["pr_ready_summary"] = _run_workflow_action(lambda: service.get_run_pr_ready_summary(run.run_id))
    status_detail = _run_workflow_action(lambda: service.get_status_detail(run.run_id))
    if isinstance(status_detail.get("orchestration"), dict):
        payload["orchestration"] = status_detail["orchestration"]
    _emit_json(payload)


@run_app.command("suggest-presets")
def run_suggest_presets(ctx: typer.Context, goal: str = typer.Option(..., "--goal")) -> None:
    suggestions = _run_workflow_action(lambda: _service(ctx).suggest_presets(goal))
    _emit_json([item.model_dump(mode="json") for item in suggestions])


@run_app.command("plan-graph")
def run_plan_graph(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal"),
    preset: Optional[str] = typer.Option(None, "--preset"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).preview_orchestration_plan_graph(
                goal=goal,
                preset_id=preset,
            )
        )
    )


@run_app.command("policy-preview")
def run_policy_preview(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal"),
    preset: Optional[str] = typer.Option(None, "--preset"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).preview_capability_policy(
                goal=goal,
                preset_id=preset,
            )
        )
    )


@run_app.command("goal-packet")
def run_goal_packet(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal"),
    preset: Optional[str] = typer.Option(None, "--preset"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).preview_goal_packet(
                goal=goal,
                preset_id=preset,
            )
        )
    )


@run_app.command("langgraph-focus")
def run_langgraph_focus(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal"),
    preset: Optional[str] = typer.Option(None, "--preset"),
    evidence_dir: Optional[str] = typer.Option(None, "--evidence-dir", help="Directory for advisory evidence JSON."),
) -> None:
    service = _service(ctx)
    route_started = time.perf_counter()
    workflow_route = _run_workflow_action(
        lambda: service.preview_orchestration_plan_graph(
            goal=goal,
            preset_id=preset,
        )
    )
    workflow_latency_ms = max(int((time.perf_counter() - route_started) * 1000), 0)
    from packages.runtime_langgraph.focused_runtime import FocusedLangGraphRuntime

    runtime = FocusedLangGraphRuntime()
    payload = runtime.compare_with_workflow_route(
        goal=goal,
        preset_id=preset,
        workflow_route=workflow_route,
        workflow_latency_ms=workflow_latency_ms,
        evidence_dir=evidence_dir,
    )
    _emit_json(payload)
    if not payload.get("comparison", {}).get("passed"):
        raise typer.Exit(code=1)


@run_app.command("launch")
def run_launch(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal"),
    preset: Optional[str] = typer.Option(None, "--preset"),
    execute: bool = typer.Option(False, "--execute", help="Execute after compile."),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).launch_goal(
                goal=goal,
                preset_id=preset,
                execute=execute,
            )
        )
    )

@run_app.command("compile")
def run_compile(
    ctx: typer.Context,
    run_id: str,
    task_kind: Optional[str] = typer.Option(None, "--task-kind", help="Requested task kind override."),
    adapter: Optional[str] = typer.Option(None, "--adapter", help="Requested adapter override."),
    agent_model: Optional[str] = typer.Option(None, "--agent-model", help="Requested agent model override."),
    codex_model: Optional[str] = typer.Option(None, "--codex-model", help="Requested codex model override."),
    opencode_model: Optional[str] = typer.Option(None, "--opencode-model", help="Requested opencode model override."),
    opencode_variant: Optional[str] = typer.Option(None, "--opencode-variant", help="Requested opencode variant override."),
    runtime_gateway_provider: Optional[str] = typer.Option(None, "--runtime-gateway-provider", help="Requested runtime gateway provider override."),
    runtime_gateway_model: Optional[str] = typer.Option(None, "--runtime-gateway-model", help="Requested runtime gateway model override."),
    runtime_reasoning_effort: Optional[str] = typer.Option(None, "--runtime-reasoning-effort", help="Requested runtime reasoning effort override."),
    worker_pool_id: Optional[str] = typer.Option(None, "--worker-pool-id", help="Requested worker pool override."),
    memory_item_id: Optional[list[str]] = typer.Option(None, "--memory-item-id", help="Explicit memory item ids."),
    task_card_ref: Optional[str] = typer.Option(None, "--task-card-ref", help="Detailed task card reference for repo mutation."),
    task_card_path: Optional[str] = typer.Option(None, "--task-card-path", help="Detailed task card path for repo mutation."),
    write_set: Optional[list[str]] = typer.Option(None, "--write-set", help="Explicit writable paths for repo mutation."),
    read_set: Optional[list[str]] = typer.Option(None, "--read-set", help="Explicit read-only context paths for repo mutation."),
    test_command: Optional[list[str]] = typer.Option(None, "--test-command", help="Explicit test commands to run after applying a patch."),
    max_fix_iterations: int = typer.Option(0, "--max-fix-iterations", min=0, help="Maximum bounded repair iterations."),
    mutation_mode: Optional[str] = typer.Option(None, "--mutation-mode", help="artifact_only or patch_apply."),
) -> None:
    prepared = _run_workflow_action(
        lambda: _service(ctx).compile_run(
            run_id,
            task_kind=task_kind,
            adapter_name=adapter,
            agent_model=agent_model,
            codex_model=codex_model,
            opencode_model=opencode_model,
            opencode_variant=opencode_variant,
            runtime_gateway_provider=runtime_gateway_provider,
            runtime_gateway_model=runtime_gateway_model,
            runtime_reasoning_effort=runtime_reasoning_effort,
            worker_pool_id=worker_pool_id,
            memory_item_ids=memory_item_id,
            task_card_ref=task_card_ref,
            task_card_path=task_card_path,
            write_set=write_set,
            read_set=read_set,
            test_commands=test_command,
            max_fix_iterations=max_fix_iterations,
            mutation_mode=mutation_mode,
        )
    )
    _emit_json(
        {
            "run": prepared.run.model_dump(mode="json"),
            "runtime_task_id": prepared.task_packet.runtime_task_id,
            "handoff_id": prepared.handoff.handoff_id,
            "state_ref_id": prepared.state_ref.state_ref_id,
            "domain_pack_id": prepared.domain_pack.domain_pack_id if prepared.domain_pack is not None else None,
            "capability_adapter": prepared.capability_route.adapter_name if prepared.capability_route is not None else None,
            "execution_lane": str(prepared.execution_lane),
            "resolved_execution": prepared.resolved_execution.model_dump(mode="json"),
            "mutation_contract": (
                prepared.task_packet.mutation_contract.model_dump(mode="json")
                if prepared.task_packet.mutation_contract is not None
                else None
            ),
            "tool_projection_manifest": (
                prepared.tool_projection_manifest.model_dump(mode="json")
                if prepared.tool_projection_manifest is not None
                else None
            ),
            "mcp_server_profiles": [profile.model_dump(mode="json") for profile in prepared.mcp_server_profiles],
            "memory_preview": prepared.memory_preview.model_dump(mode="json") if prepared.memory_preview is not None else None,
        }
    )


@run_app.command("recompile")
def run_recompile(
    ctx: typer.Context,
    run_id: str,
    task_kind: Optional[str] = typer.Option(None, "--task-kind", help="Requested task kind override."),
    adapter: Optional[str] = typer.Option(None, "--adapter", help="Requested adapter override."),
    agent_model: Optional[str] = typer.Option(None, "--agent-model", help="Requested agent model override."),
    codex_model: Optional[str] = typer.Option(None, "--codex-model", help="Requested codex model override."),
    opencode_model: Optional[str] = typer.Option(None, "--opencode-model", help="Requested opencode model override."),
    opencode_variant: Optional[str] = typer.Option(None, "--opencode-variant", help="Requested opencode variant override."),
    runtime_gateway_provider: Optional[str] = typer.Option(None, "--runtime-gateway-provider", help="Requested runtime gateway provider override."),
    runtime_gateway_model: Optional[str] = typer.Option(None, "--runtime-gateway-model", help="Requested runtime gateway model override."),
    runtime_reasoning_effort: Optional[str] = typer.Option(None, "--runtime-reasoning-effort", help="Requested runtime reasoning effort override."),
    worker_pool_id: Optional[str] = typer.Option(None, "--worker-pool-id", help="Requested worker pool override."),
    memory_item_id: Optional[list[str]] = typer.Option(None, "--memory-item-id", help="Explicit memory item ids."),
    task_card_ref: Optional[str] = typer.Option(None, "--task-card-ref", help="Detailed task card reference for repo mutation."),
    task_card_path: Optional[str] = typer.Option(None, "--task-card-path", help="Detailed task card path for repo mutation."),
    write_set: Optional[list[str]] = typer.Option(None, "--write-set", help="Explicit writable paths for repo mutation."),
    read_set: Optional[list[str]] = typer.Option(None, "--read-set", help="Explicit read-only context paths for repo mutation."),
    test_command: Optional[list[str]] = typer.Option(None, "--test-command", help="Explicit test commands to run after applying a patch."),
    max_fix_iterations: int = typer.Option(0, "--max-fix-iterations", min=0, help="Maximum bounded repair iterations."),
    mutation_mode: Optional[str] = typer.Option(None, "--mutation-mode", help="artifact_only or patch_apply."),
) -> None:
    prepared = _run_workflow_action(
        lambda: _service(ctx).recompile_run(
            run_id,
            task_kind=task_kind,
            adapter_name=adapter,
            agent_model=agent_model,
            codex_model=codex_model,
            opencode_model=opencode_model,
            opencode_variant=opencode_variant,
            runtime_gateway_provider=runtime_gateway_provider,
            runtime_gateway_model=runtime_gateway_model,
            runtime_reasoning_effort=runtime_reasoning_effort,
            worker_pool_id=worker_pool_id,
            memory_item_ids=memory_item_id,
            task_card_ref=task_card_ref,
            task_card_path=task_card_path,
            write_set=write_set,
            read_set=read_set,
            test_commands=test_command,
            max_fix_iterations=max_fix_iterations,
            mutation_mode=mutation_mode,
        )
    )
    _emit_json(
        {
            "run": prepared.run.model_dump(mode="json"),
            "runtime_task_id": prepared.task_packet.runtime_task_id,
            "handoff_id": prepared.handoff.handoff_id,
            "state_ref_id": prepared.state_ref.state_ref_id,
            "domain_pack_id": prepared.domain_pack.domain_pack_id if prepared.domain_pack is not None else None,
            "capability_adapter": prepared.capability_route.adapter_name if prepared.capability_route is not None else None,
            "execution_lane": str(prepared.execution_lane),
            "resolved_execution": prepared.resolved_execution.model_dump(mode="json"),
            "mutation_contract": (
                prepared.task_packet.mutation_contract.model_dump(mode="json")
                if prepared.task_packet.mutation_contract is not None
                else None
            ),
            "tool_projection_manifest": (
                prepared.tool_projection_manifest.model_dump(mode="json")
                if prepared.tool_projection_manifest is not None
                else None
            ),
            "mcp_server_profiles": [profile.model_dump(mode="json") for profile in prepared.mcp_server_profiles],
            "memory_preview": prepared.memory_preview.model_dump(mode="json") if prepared.memory_preview is not None else None,
        }
    )


@run_app.command("resume")
def run_resume(
    ctx: typer.Context,
    run_id: str,
    operator_receipt_id: Optional[str] = typer.Option(
        None,
        "--operator-receipt-id",
        help="Receipt id attached to a capability-enforced mutation invocation.",
    ),
) -> None:
    if operator_receipt_id or _prepared_run_requires_repo_mutation_receipt(ctx, run_id):
        _consume_cli_receipt(
            ctx,
            action_type="resume_run",
            receipt_id=operator_receipt_id,
            scope_payload=_resume_scope(run_id),
        )
    executed = _run_workflow_action(lambda: _service(ctx).resume_run(run_id, operator_receipt_id=operator_receipt_id))
    _emit_json(
        {
            "run": executed.run.model_dump(mode="json"),
            "evidence_id": executed.evidence.evidence_id,
            "review_decision": executed.review_verdict.decision if executed.review_verdict is not None else None,
        }
    )


@run_app.command("batch-resume")
def run_batch_resume(
    ctx: typer.Context,
    run_id: list[str] = typer.Argument(..., help="Prepared run ids to resume behind one local batch barrier."),
    max_workers: Optional[int] = typer.Option(None, "--max-workers", min=1),
    operator_receipt_id: Optional[str] = typer.Option(
        None,
        "--operator-receipt-id",
        help="Receipt id attached to capability-enforced mutation invocations.",
    ),
) -> None:
    if operator_receipt_id or any(_prepared_run_requires_repo_mutation_receipt(ctx, item) for item in run_id):
        _consume_cli_receipt(
            ctx,
            action_type="batch_resume_runs",
            receipt_id=operator_receipt_id,
            scope_payload=_batch_resume_scope(run_id, max_workers=max_workers),
        )
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).resume_runs_parallel(
                run_id,
                max_workers=max_workers,
                operator_receipt_id=operator_receipt_id,
            )
        )
    )


@run_app.command("approve")
def run_approve(ctx: typer.Context, run_id: str) -> None:
    reviewed = _run_workflow_action(lambda: _service(ctx).approve_run_review(run_id))
    _emit_json(
        {
            "run": reviewed.run.model_dump(mode="json"),
            "evidence_id": reviewed.evidence.evidence_id,
            "review_decision": reviewed.review_verdict.decision,
        }
    )


@run_app.command("reject")
def run_reject(ctx: typer.Context, run_id: str) -> None:
    reviewed = _run_workflow_action(lambda: _service(ctx).reject_run_review(run_id))
    _emit_json(
        {
            "run": reviewed.run.model_dump(mode="json"),
            "evidence_id": reviewed.evidence.evidence_id,
            "review_decision": reviewed.review_verdict.decision,
        }
    )


@run_app.command("cancel")
def run_cancel(ctx: typer.Context, run_id: str) -> None:
    run = _run_workflow_action(lambda: _service(ctx).cancel_run(run_id))
    _emit_json(run.model_dump(mode="json"))


@run_app.command("status")
def run_status(ctx: typer.Context, run_id: str) -> None:
    service = _service(ctx)
    detail = _run_workflow_action(lambda: service.get_status_detail(run_id))
    payload = detail["run"]
    payload["runtime_gateway"] = detail["runtime_gateway"]
    payload["review_policy"] = detail["review_policy"]
    payload["runtime_task_ids"] = detail["runtime_task_ids"]
    payload["current_runtime_attempt"] = detail["current_runtime_attempt"]
    payload["latest_runtime_attempt"] = detail["latest_runtime_attempt"]
    payload["runtime_attempt_projection"] = detail["runtime_attempt_projection"]
    payload["active_claims"] = detail["active_claims"]
    payload["latest_claim"] = detail["latest_claim"]
    payload["active_worker_leases"] = detail["active_worker_leases"]
    payload["latest_worker_lease"] = detail["latest_worker_lease"]
    payload["ownership_topology"] = detail["ownership_topology"]
    payload["parallel_batch"] = detail["parallel_batch"]
    payload["worker_lease_projection"] = detail["worker_lease_projection"]
    payload["execution_target"] = detail["execution_target"]
    payload["lease_renewals"] = detail["lease_renewals"]
    payload["mutation_contract"] = detail["mutation_contract"]
    payload["mutation_result"] = detail["mutation_result"]
    payload["orchestration"] = detail["orchestration"]
    payload["orchestration_plan_graph"] = detail["orchestration_plan_graph"]
    payload["capability_policy_preview"] = detail["capability_policy_preview"]
    payload["operator_projection"] = detail["operator_projection"]
    payload["effective_review_state"] = detail["effective_review_state"]
    payload["domain_pack"] = detail["domain_pack"]
    payload["capability_resolution"] = detail["capability_resolution"]
    payload["latest_review_verdict"] = detail["latest_review_verdict"]
    payload["latest_simulation_record"] = detail["latest_simulation_record"]
    payload["next_action"] = detail["next_action"]
    payload["failure_reason"] = detail["failure_reason"]
    payload["waiting_reason"] = detail["waiting_reason"]
    payload["recoverability_hint"] = detail["recoverability_hint"]
    _emit_json(payload)


@run_app.command("status-detail")
def run_status_detail(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_status_detail(run_id)))


@run_app.command("summary")
def run_summary(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_run_summary(run_id)))


@run_app.command("pr-ready-summary")
def run_pr_ready_summary(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_run_pr_ready_summary(run_id)))


@run_app.command("simulation")
def run_simulation(ctx: typer.Context, run_id: str) -> None:
    report = _run_workflow_action(lambda: _service(ctx).get_run_simulation(run_id))
    _emit_json(report.model_dump(mode="json"))


@run_app.command("record-simulation")
def run_record_simulation(ctx: typer.Context, run_id: str) -> None:
    record = _run_workflow_action(lambda: _service(ctx).record_run_simulation(run_id))
    _emit_json(record.model_dump(mode="json"))


@run_app.command("simulations")
def run_simulations(ctx: typer.Context, run_id: str) -> None:
    records = _run_workflow_action(lambda: _service(ctx).list_simulation_records(run_id))
    _emit_json([record.model_dump(mode="json") for record in records])


@run_app.command("event-inspection")
def run_event_inspection(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_event_inspection(run_id)))


@run_app.command("audit-report")
def run_audit_report(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_run_audit_report(run_id)))


@run_app.command("replay-packet")
def run_replay_packet(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_run_replay_packet(run_id)))


@run_app.command("mutation-report")
def run_mutation_report(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_run_mutation_report(run_id)))


@run_app.command("orchestration")
def run_orchestration(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_run_orchestration(run_id)))


@run_app.command("plan-graph-status")
def run_plan_graph_status(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_run_orchestration_plan_graph(run_id)))


@run_app.command("policy-preview-status")
def run_policy_preview_status(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_run_capability_policy_preview(run_id)))


@run_app.command("operator-packet")
def run_operator_packet(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_run_operator_packet(run_id)))


@run_app.command("memory-candidates")
def run_memory_candidates(ctx: typer.Context, run_id: str) -> None:
    candidates = _run_workflow_action(lambda: _service(ctx).get_run_memory_candidates(run_id))
    _emit_json([candidate.model_dump(mode="json") for candidate in candidates])


@run_app.command("materialize-memory")
def run_materialize_memory(
    ctx: typer.Context,
    run_id: str,
    candidate_id: str = typer.Option(..., "--candidate-id"),
) -> None:
    memory_item = _run_workflow_action(lambda: _service(ctx).materialize_run_memory_candidate(run_id, candidate_id))
    _emit_json(memory_item.model_dump(mode="json"))


@run_app.command("memory-items")
def run_memory_items(ctx: typer.Context, run_id: str) -> None:
    items = _run_workflow_action(lambda: _service(ctx).list_memory_items(run_id=run_id))
    _emit_json([item.model_dump(mode="json") for item in items])


@run_app.command("claims")
def run_claims(ctx: typer.Context, run_id: str) -> None:
    claims = _run_workflow_action(lambda: _service(ctx).list_claims(run_id))
    _emit_json([claim.model_dump(mode="json") for claim in claims])


@run_app.command("leases")
def run_leases(ctx: typer.Context, run_id: str) -> None:
    leases = _run_workflow_action(lambda: _service(ctx).list_worker_leases(run_id))
    _emit_json([lease.model_dump(mode="json") for lease in leases])


@run_app.command("attempts")
def run_attempts(ctx: typer.Context, run_id: str) -> None:
    attempts = _run_workflow_action(lambda: _service(ctx).list_runtime_attempts(run_id))
    _emit_json([attempt.model_dump(mode="json") for attempt in attempts])


@run_app.command("snapshots")
def run_snapshots(ctx: typer.Context, run_id: str) -> None:
    snapshots = _run_workflow_action(lambda: _service(ctx).list_snapshots(run_id))
    _emit_json([snapshot.model_dump(mode="json") for snapshot in snapshots])


@run_app.command("budget")
def run_budget(ctx: typer.Context, run_id: str) -> None:
    detail = _run_workflow_action(lambda: _service(ctx).get_status_detail(run_id))
    _emit_json(
        {
            "run": detail["run"],
            "budget_ledger": detail["budget_ledger"],
            "budget_projection": detail["budget_projection"],
        }
    )


@run_app.command("inspect")
def run_inspect(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).inspect_run_state(run_id)))


@run_app.command("reconcile")
def run_reconcile(
    ctx: typer.Context,
    run_id: str,
    apply: bool = typer.Option(False, "--apply", help="Apply the selected repair action instead of only planning it."),
    action: Optional[str] = typer.Option(None, "--action", help="Explicit repair action override."),
) -> None:
    service = _service(ctx)
    if apply:
        _emit_json(_run_workflow_action(lambda: service.apply_run_repair(run_id, action=action)))
        return
    _emit_json(_run_workflow_action(lambda: service.reconcile_run(run_id)))


@run_app.command("timeline")
def run_timeline(ctx: typer.Context, run_id: str, as_json: bool = typer.Option(False, "--json")) -> None:
    timeline = _run_workflow_action(lambda: _service(ctx).get_timeline(run_id))
    if as_json:
        _emit_json([event.model_dump(mode="json") for event in timeline])
        return
    for event in timeline:
        typer.echo(f"{event.created_at.isoformat()} | {event.event_type} | {event.summary}")


@run_app.command("handoffs")
def run_handoffs(ctx: typer.Context, run_id: str) -> None:
    handoffs = _run_workflow_action(lambda: _service(ctx).list_handoffs(run_id))
    _emit_json([handoff.model_dump(mode="json") for handoff in handoffs])
