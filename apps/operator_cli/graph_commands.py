from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from apps.operator_cli.shared import _db_path_from_context, _emit_json, _workspace_root_from_context
from packages.contracts import HumanApprovalInterrupt
from packages.core_domain.repositories import OperatorActionReceiptRepository
from packages.runtime_langgraph.checkpoint_store import (
    build_graph_checkpoint_history,
    build_graph_checkpoint_state,
    build_graph_repair_decision,
    describe_graph_checkpointer_backend,
    fork_graph_checkpoint,
    get_graph_checkpoint,
    list_graph_checkpoints,
)
from packages.runtime_langgraph.approval_graph import (
    resume_human_approval_graph,
    start_human_approval_graph,
)
from packages.runtime_langgraph.interrupts import (
    resume_interrupt_with_automation_lease,
    resume_interrupt_with_receipt,
)
from packages.runtime_langgraph.execution_kernel import (
    preview_graph_execution,
    run_artifact_only_graph,
)
from packages.runtime_langgraph.multi_agent_graph import run_multi_agent_artifact_graph
from packages.runtime_langgraph.repair_loop import build_repair_loop_plan


graph_app = typer.Typer(help="LangGraph-backed workflow execution previews and artifact-only runs.")
checkpoints_app = typer.Typer(help="Graph checkpoint inspection commands.")
graph_app.add_typer(checkpoints_app, name="checkpoints")


@graph_app.command("preview")
def graph_preview(
    goal: str = typer.Option(..., "--goal"),
    preset_id: Optional[str] = typer.Option(None, "--preset"),
) -> None:
    _emit_json(preview_graph_execution(goal=goal, preset_id=preset_id))


@graph_app.command("run")
def graph_run(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal"),
    preset_id: Optional[str] = typer.Option(None, "--preset"),
    evidence_dir: Optional[Path] = typer.Option(None, "--evidence-dir"),
    artifact_only: bool = typer.Option(False, "--artifact-only", help="Allow only artifact-only graph execution."),
) -> None:
    if not artifact_only:
        _emit_json(
            {
                "status": "blocked",
                "failure_class": "artifact_only_flag_required",
                "message": "M86 graph run requires --artifact-only.",
            }
        )
        raise typer.Exit(code=1)

    payload = run_artifact_only_graph(
        goal=goal,
        workspace_root=_workspace_root_from_context(ctx),
        evidence_dir=evidence_dir,
        preset_id=preset_id,
    )
    _emit_json(payload)
    if payload["status"] != "completed":
        raise typer.Exit(code=1)


@graph_app.command("interrupt-preview")
def graph_interrupt_preview(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal"),
    side_effect: str = typer.Option("repo_mutation", "--side-effect"),
    evidence_dir: Optional[Path] = typer.Option(None, "--evidence-dir"),
) -> None:
    payload = start_human_approval_graph(
        goal=goal,
        workspace_root=_workspace_root_from_context(ctx),
        evidence_dir=evidence_dir,
        requested_side_effect_level=side_effect,
    )
    _emit_json(payload)


@checkpoints_app.command("list")
def graph_checkpoints_list(
    ctx: typer.Context,
    run_id: Optional[str] = typer.Option(None, "--run-id"),
    thread_id: Optional[str] = typer.Option(None, "--thread-id"),
) -> None:
    records = list_graph_checkpoints(
        workspace_root=_workspace_root_from_context(ctx),
        run_id=run_id,
        thread_id=thread_id,
    )
    _emit_json({"checkpoints": [record.model_dump(mode="json") for record in records]})


@graph_app.command("history")
def graph_history(
    ctx: typer.Context,
    run_id: Optional[str] = typer.Option(None, "--run-id"),
    thread_id: Optional[str] = typer.Option(None, "--thread-id"),
) -> None:
    _emit_json(
        build_graph_checkpoint_history(
            workspace_root=_workspace_root_from_context(ctx),
            run_id=run_id,
            thread_id=thread_id,
        )
    )


@graph_app.command("checkpointer")
def graph_checkpointer(ctx: typer.Context) -> None:
    _emit_json(describe_graph_checkpointer_backend(_workspace_root_from_context(ctx)))


@graph_app.command("state")
def graph_state(
    ctx: typer.Context,
    checkpoint_id: str = typer.Option(..., "--checkpoint-id"),
) -> None:
    payload = build_graph_checkpoint_state(
        workspace_root=_workspace_root_from_context(ctx),
        checkpoint_id=checkpoint_id,
    )
    _emit_json(payload)
    if payload.get("status") == "failed":
        raise typer.Exit(code=1)


@graph_app.command("stream")
def graph_stream(
    stream_path: Path = typer.Option(..., "--stream-path"),
    limit: int = typer.Option(20, "--limit", min=1),
) -> None:
    if not stream_path.exists():
        _emit_json({"status": "failed", "failure_class": "stream_not_found", "stream_path": stream_path.as_posix()})
        raise typer.Exit(code=1)
    lines = stream_path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines[-limit:] if line.strip()]
    _emit_json({"status": "completed", "stream_path": stream_path.as_posix(), "event_count": len(events), "events": events})


@graph_app.command("resume")
def graph_resume(
    ctx: typer.Context,
    checkpoint_id: str = typer.Option(..., "--checkpoint-id"),
    receipt_id: Optional[str] = typer.Option(None, "--receipt-id"),
    lease_id: Optional[str] = typer.Option(None, "--lease-id"),
) -> None:
    checkpoint = get_graph_checkpoint(workspace_root=_workspace_root_from_context(ctx), checkpoint_id=checkpoint_id)
    if checkpoint is None:
        _emit_json({"status": "failed", "failure_class": "checkpoint_not_found", "checkpoint_id": checkpoint_id})
        raise typer.Exit(code=1)
    interrupt_payload = checkpoint.metadata.get("human_interrupt")
    if not isinstance(interrupt_payload, dict):
        _emit_json(
            {
                "status": "blocked",
                "failure_class": "checkpoint_has_no_pending_interrupt",
                "checkpoint_id": checkpoint_id,
            }
        )
        raise typer.Exit(code=1)
    interrupt = HumanApprovalInterrupt.model_validate(interrupt_payload)
    if receipt_id:
        authorization = resume_interrupt_with_receipt(
            interrupt=interrupt,
            receipt_id=receipt_id,
            receipt_repository=OperatorActionReceiptRepository(_db_path_from_context(ctx)),
            workspace_root=_workspace_root_from_context(ctx),
        )
    elif lease_id:
        authorization = resume_interrupt_with_automation_lease(
            interrupt=interrupt,
            lease_id=lease_id,
            workspace_root=_workspace_root_from_context(ctx),
        )
    else:
        _emit_json(
            {
                "status": "blocked",
                "failure_class": "receipt_or_lease_required",
                "checkpoint_id": checkpoint_id,
            }
        )
        raise typer.Exit(code=1)
    resume_payload = None
    if checkpoint.metadata.get("graph_kind") == "human_approval_interrupt":
        resume_payload = resume_human_approval_graph(
            workspace_root=_workspace_root_from_context(ctx),
            checkpoint_id=checkpoint_id,
            authorization=authorization,
        )
    _emit_json(
        {
            "status": "approved_for_resume",
            "checkpoint_id": checkpoint_id,
            "thread_id": checkpoint.thread_id,
            "authorization": authorization,
            "side_effect_before_interrupt": interrupt.idempotent_resume_contract.get("side_effect_before_interrupt"),
            "next_action": "resume_graph_from_checkpoint_under_workflow_control",
            "langgraph_resume": resume_payload,
        }
    )


@graph_app.command("fork")
def graph_fork(
    ctx: typer.Context,
    checkpoint_id: str = typer.Option(..., "--checkpoint-id"),
    reason: str = typer.Option(..., "--reason"),
) -> None:
    try:
        record = fork_graph_checkpoint(
            workspace_root=_workspace_root_from_context(ctx),
            checkpoint_id=checkpoint_id,
            reason=reason,
        )
    except KeyError as exc:
        _emit_json({"status": "failed", "failure_class": "checkpoint_not_found", "message": str(exc)})
        raise typer.Exit(code=1) from exc
    _emit_json({"status": "forked", "checkpoint": record.model_dump(mode="json")})


@graph_app.command("repair-plan")
def graph_repair_plan(
    ctx: typer.Context,
    checkpoint_id: str = typer.Option(..., "--checkpoint-id"),
    failure_class: Optional[str] = typer.Option(None, "--failure-class"),
    fix_iteration: int = typer.Option(0, "--fix-iteration", min=0),
    max_fix_iterations: int = typer.Option(2, "--max-fix-iterations", min=0),
) -> None:
    checkpoint = get_graph_checkpoint(workspace_root=_workspace_root_from_context(ctx), checkpoint_id=checkpoint_id)
    if checkpoint is None:
        _emit_json({"status": "failed", "failure_class": "checkpoint_not_found", "checkpoint_id": checkpoint_id})
        raise typer.Exit(code=1)
    decision = build_graph_repair_decision(
        checkpoint=checkpoint,
        failure_class=failure_class,
        fix_iteration=fix_iteration,
        max_fix_iterations=max_fix_iterations,
    )
    _emit_json(decision.model_dump(mode="json"))


@graph_app.command("repair-loop")
def graph_repair_loop(
    ctx: typer.Context,
    checkpoint_id: str = typer.Option(..., "--checkpoint-id"),
    failure_class: Optional[str] = typer.Option(None, "--failure-class"),
    evidence_dir: Optional[Path] = typer.Option(None, "--evidence-dir"),
    fix_iteration: int = typer.Option(0, "--fix-iteration", min=0),
    max_fix_iterations: int = typer.Option(2, "--max-fix-iterations", min=0),
) -> None:
    payload = build_repair_loop_plan(
        workspace_root=_workspace_root_from_context(ctx),
        checkpoint_id=checkpoint_id,
        failure_class=failure_class,
        fix_iteration=fix_iteration,
        max_fix_iterations=max_fix_iterations,
        evidence_dir=evidence_dir,
    )
    _emit_json(payload)
    if payload.get("status") == "failed":
        raise typer.Exit(code=1)


@graph_app.command("multi-agent-run")
def graph_multi_agent_run(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal"),
    evidence_dir: Optional[Path] = typer.Option(None, "--evidence-dir"),
    route_lane: str = typer.Option("simple", "--route-lane"),
    max_workers: int = typer.Option(2, "--max-workers", min=1, max=2),
) -> None:
    payload = run_multi_agent_artifact_graph(
        goal=goal,
        workspace_root=_workspace_root_from_context(ctx),
        evidence_dir=evidence_dir,
        route_lane=route_lane,
        max_workers=max_workers,
    )
    _emit_json(payload)
    if payload["status"] != "completed":
        raise typer.Exit(code=1)
