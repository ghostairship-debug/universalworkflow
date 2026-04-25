from __future__ import annotations

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

interaction_app = typer.Typer(help="Interaction-plane session, profile, and cluster commands.")

@interaction_app.command("profiles")
def interaction_profiles(ctx: typer.Context) -> None:
    registry = _run_workflow_action(lambda: _service(ctx).get_agent_profile_registry())
    _emit_json(registry.model_dump(mode="json"))


@interaction_app.command("clusters")
def interaction_clusters(ctx: typer.Context) -> None:
    templates = _run_workflow_action(lambda: _service(ctx).list_cluster_templates())
    _emit_json([template.model_dump(mode="json") for template in templates])


@interaction_app.command("create-session")
def interaction_create_session(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal"),
    preset: Optional[str] = typer.Option(None, "--preset"),
    cluster: Optional[str] = typer.Option(None, "--cluster"),
    constraint: Optional[list[str]] = typer.Option(None, "--constraint"),
    assumption: Optional[list[str]] = typer.Option(None, "--assumption"),
    artifact: Optional[list[str]] = typer.Option(None, "--artifact"),
    followup_context: Optional[list[str]] = typer.Option(None, "--followup-context"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).create_intent_session(
                goal=goal,
                preferred_preset_id=preset,
                preferred_cluster_template_ids=[cluster] if cluster else None,
                constraints=constraint,
                assumptions=assumption,
                referenced_artifact_paths=artifact,
                followup_context=followup_context,
            )
        )
    )


@interaction_app.command("sessions")
def interaction_sessions(
    ctx: typer.Context,
    limit: int = typer.Option(10, "--limit", min=1),
    status: Optional[str] = typer.Option(None, "--status"),
) -> None:
    sessions = _run_workflow_action(lambda: _service(ctx).list_intent_sessions(limit=limit, status=status))
    _emit_json([session.model_dump(mode="json") for session in sessions])


@interaction_app.command("generated-profiles")
def interaction_generated_profiles(
    ctx: typer.Context,
    session_id: Optional[str] = typer.Option(None, "--session-id"),
    run_id: Optional[str] = typer.Option(None, "--run-id"),
    limit: int = typer.Option(20, "--limit", min=1),
) -> None:
    profiles = _run_workflow_action(
        lambda: _service(ctx).list_generated_agent_profiles(session_id=session_id, run_id=run_id, limit=limit)
    )
    _emit_json([profile.model_dump(mode="json") for profile in profiles])


@interaction_app.command("generate-profiles")
def interaction_generate_profiles(ctx: typer.Context, session_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).generate_session_profiles(session_id)))


@interaction_app.command("get-session")
def interaction_get_session(ctx: typer.Context, session_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_intent_session_payload(session_id)))


@interaction_app.command("clarify")
def interaction_clarify(
    ctx: typer.Context,
    session_id: str,
    answer: Optional[list[str]] = typer.Option(None, "--answer", help="prompt_id=value"),
    preset: Optional[str] = typer.Option(None, "--preset"),
    cluster: Optional[str] = typer.Option(None, "--cluster"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).continue_intent_session(
                session_id,
                answers=_parse_key_value_pairs(answer),
                preferred_preset_id=preset,
                preferred_cluster_template_ids=[cluster] if cluster else None,
            )
        )
    )


@interaction_app.command("plan-draft")
def interaction_plan_draft(
    ctx: typer.Context,
    session_id: str,
    preset: Optional[str] = typer.Option(None, "--preset"),
    cluster: Optional[str] = typer.Option(None, "--cluster"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).create_intent_plan_draft(
                session_id,
                preferred_preset_id=preset,
                preferred_cluster_template_ids=[cluster] if cluster else None,
            )
        )
    )


@interaction_app.command("launch")
def interaction_launch(
    ctx: typer.Context,
    session_id: str,
    execute: bool = typer.Option(False, "--execute"),
    preset: Optional[str] = typer.Option(None, "--preset"),
    cluster: Optional[str] = typer.Option(None, "--cluster"),
    rationale: Optional[str] = typer.Option(None, "--rationale"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).launch_intent_session(
                session_id,
                execute=execute,
                rationale=rationale,
                selected_preset_id=preset,
                selected_cluster_template_ids=[cluster] if cluster else None,
            )
        )
    )


@interaction_app.command("followup")
def interaction_followup(
    ctx: typer.Context,
    session_id: str,
    instruction: str = typer.Option(..., "--instruction"),
    intent: str = typer.Option("continue", "--intent"),
    blocking: bool = typer.Option(False, "--blocking"),
    run_id: Optional[str] = typer.Option(None, "--run-id"),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).create_followup_request(
                session_id,
                instruction=instruction,
                intent=intent,
                blocking=blocking,
                run_id=run_id,
            )
        )
    )


@interaction_app.command("followups")
def interaction_followups(
    ctx: typer.Context,
    session_id: str,
    limit: int = typer.Option(20, "--limit", min=1),
) -> None:
    followups = _run_workflow_action(lambda: _service(ctx).list_followup_requests(session_id, limit=limit))
    _emit_json([item.model_dump(mode="json") for item in followups])


@interaction_app.command("watchdogs")
def interaction_watchdogs(
    ctx: typer.Context,
    session_id: Optional[str] = typer.Option(None, "--session-id"),
    run_id: Optional[str] = typer.Option(None, "--run-id"),
    status: Optional[str] = typer.Option(None, "--status"),
    limit: int = typer.Option(20, "--limit", min=1),
) -> None:
    watchdogs = _run_workflow_action(
        lambda: _service(ctx).list_automation_watchdogs(
            session_id=session_id,
            run_id=run_id,
            status=status,
            limit=limit,
        )
    )
    _emit_json([item.model_dump(mode="json") for item in watchdogs])


@interaction_app.command("evaluate-watchdogs")
def interaction_evaluate_watchdogs(
    ctx: typer.Context,
    session_id: Optional[str] = typer.Option(None, "--session-id"),
    run_id: Optional[str] = typer.Option(None, "--run-id"),
    auto_apply: bool = typer.Option(False, "--auto-apply"),
    limit: int = typer.Option(20, "--limit", min=1),
) -> None:
    _emit_json(
        _run_workflow_action(
            lambda: _service(ctx).evaluate_watchdogs(
                session_id=session_id,
                run_id=run_id,
                auto_apply=auto_apply,
                limit=limit,
            )
        )
    )
