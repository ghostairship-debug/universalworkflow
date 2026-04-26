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
from packages.core_domain.active_truth import build_active_truth_check
from packages.core_domain.governance import (
    build_domain_pack_platform_report,
    build_governance_alert_report,
    build_governance_metrics_report,
    build_release_readiness_report,
    build_review_policy_report,
    build_tech_debt_report,
)
from packages.core_domain.repositories import PresetRepository
from packages.core_domain.self_development_manifest import (
    DEFAULT_SELF_DEVELOPMENT_MILESTONES,
    build_self_development_manifest,
)

task_app = typer.Typer(help="Task inspection commands.")
db_app = typer.Typer(help="Development database commands.")
governance_app = typer.Typer(help="Governance and debt visibility commands.")
config_app = typer.Typer(help="Unified configuration inspection commands.")

@task_app.command("evidence")
def task_evidence(ctx: typer.Context, runtime_task_id: str) -> None:
    evidence = _run_workflow_action(lambda: _service(ctx).get_task_evidence(runtime_task_id))
    _emit_json(evidence.model_dump(mode="json"))


@db_app.command("reset")
def db_reset(
    ctx: typer.Context,
    seed_presets: bool = typer.Option(True, "--seed-presets/--no-seed-presets", help="Seed bootstrap presets."),
) -> None:
    db_path = _db_path_from_context(ctx)
    _run_workflow_action(lambda: reset_db(db_path))
    migrate(db_path)
    seeded = []
    if seed_presets:
        seeded = [preset.preset_id for preset in PresetRepository(db_path).seed_defaults()]
    _emit_json({"db_path": db_path.as_posix(), "seeded_presets": seeded})


@db_app.command("migrate")
def db_migrate(ctx: typer.Context) -> None:
    db_path = _db_path_from_context(ctx)
    applied = migrate(db_path)
    status = get_migration_status(db_path)
    _emit_json(
        {
            "db_path": db_path.as_posix(),
            "applied": applied,
            "applied_count": len(applied),
            "available_count": status["available_count"],
            "pending_count": status["pending_count"],
            "up_to_date": status["up_to_date"],
        }
    )


@db_app.command("migration-status")
def db_migration_status(ctx: typer.Context) -> None:
    _emit_json(get_migration_status(_db_path_from_context(ctx)))


@db_app.command("workspace-path")
def db_workspace_path(
    label: str = typer.Option("workflow", "--label", help="Stable label for the workspace-scoped DB."),
) -> None:
    _emit_json({"db_path": workspace_scoped_db_path(label=label).resolve().as_posix(), "label": label})


@governance_app.command("tech-debt")
def governance_tech_debt(
    registry_path: Optional[str] = typer.Option(None, "--registry-path", help="Override tech-debt registry path."),
) -> None:
    _emit_json(build_tech_debt_report(registry_path))


@governance_app.command("review-policy")
def governance_review_policy(
    ctx: typer.Context,
    decision_table_path: Optional[str] = typer.Option(None, "--decision-table-path", help="Override decision table path."),
    registry_path: Optional[str] = typer.Option(None, "--registry-path", help="Override tech-debt registry path."),
) -> None:
    _emit_json(
        build_review_policy_report(
            db_path=_db_path_from_context(ctx),
            decision_table_path=decision_table_path,
            registry_path=registry_path,
        )
    )


@governance_app.command("metrics")
def governance_metrics(
    ctx: typer.Context,
    validation_report_path: Optional[str] = typer.Option(
        None,
        "--validation-report-path",
        help="Override offline validation report path.",
    ),
    decision_table_path: Optional[str] = typer.Option(None, "--decision-table-path", help="Override decision table path."),
    registry_path: Optional[str] = typer.Option(None, "--registry-path", help="Override tech-debt registry path."),
) -> None:
    _emit_json(
        build_governance_metrics_report(
            db_path=_db_path_from_context(ctx),
            validation_report_path=validation_report_path,
            decision_table_path=decision_table_path,
            registry_path=registry_path,
        )
    )


@governance_app.command("alerts")
def governance_alerts(
    ctx: typer.Context,
    validation_report_path: Optional[str] = typer.Option(
        None,
        "--validation-report-path",
        help="Override offline validation report path.",
    ),
    decision_table_path: Optional[str] = typer.Option(None, "--decision-table-path", help="Override decision table path."),
    registry_path: Optional[str] = typer.Option(None, "--registry-path", help="Override tech-debt registry path."),
) -> None:
    _emit_json(
        build_governance_alert_report(
            db_path=_db_path_from_context(ctx),
            validation_report_path=validation_report_path,
            decision_table_path=decision_table_path,
            registry_path=registry_path,
        )
    )


@governance_app.command("release-readiness")
def governance_release_readiness(
    ctx: typer.Context,
    validation_report_path: Optional[str] = typer.Option(
        None,
        "--validation-report-path",
        help="Override offline validation report path.",
    ),
    decision_table_path: Optional[str] = typer.Option(None, "--decision-table-path", help="Override decision table path."),
    registry_path: Optional[str] = typer.Option(None, "--registry-path", help="Override tech-debt registry path."),
) -> None:
    _emit_json(
        build_release_readiness_report(
            db_path=_db_path_from_context(ctx),
            validation_report_path=validation_report_path,
            decision_table_path=decision_table_path,
            registry_path=registry_path,
        )
    )


@governance_app.command("domain-pack")
def governance_domain_pack() -> None:
    _emit_json(build_domain_pack_platform_report())


@governance_app.command("self-development-manifest")
def governance_self_development_manifest(
    ctx: typer.Context,
    milestone: Optional[list[str]] = typer.Option(
        None,
        "--milestone",
        help="Milestone id to include. Repeat to override the default M67-M72 closeout set.",
    ),
    state_root: str = typer.Option("state", "--state-root", help="State root containing milestone evidence."),
    output_path: Optional[str] = typer.Option(None, "--output-path", help="Optional JSON output path."),
    min_task_cards: int = typer.Option(3, "--min-task-cards", min=1),
) -> None:
    _emit_json(
        build_self_development_manifest(
            _workspace_root_from_context(ctx),
            milestones=list(milestone or DEFAULT_SELF_DEVELOPMENT_MILESTONES),
            state_root=state_root,
            output_path=output_path,
            min_task_cards_per_phase=min_task_cards,
        )
    )


@governance_app.command("active-truth-check")
def governance_active_truth_check(
    ctx: typer.Context,
    output_path: Optional[str] = typer.Option(None, "--output-path", help="Optional JSON output path."),
    strict: bool = typer.Option(False, "--strict", help="Exit non-zero when active truth issues are found."),
) -> None:
    payload = build_active_truth_check(_workspace_root_from_context(ctx), output_path=output_path)
    _emit_json(payload)
    if strict and payload["issue_count"]:
        raise typer.Exit(code=1)


@config_app.command("show")
def config_show(ctx: typer.Context) -> None:
    _emit_json(ctx.obj["effective_config"])
