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

scheduler_app = typer.Typer(help="Local scheduler lease arbiter and legacy cluster compatibility commands.")

@scheduler_app.command("cluster")
def scheduler_cluster(ctx: typer.Context) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).scheduler_authority_cluster.cluster_snapshot()))


@scheduler_app.command("lease")
def scheduler_lease(ctx: typer.Context, lease_id: str) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_scheduler_lease(lease_id)))


@scheduler_app.command("route-stats")
def scheduler_route_stats(ctx: typer.Context, days: int = typer.Option(30, "--days", min=0)) -> None:
    _emit_json(_run_workflow_action(lambda: _service(ctx).get_cluster_route_stats(days=days)))
