from __future__ import annotations

from typing import Optional

import typer

from apps.operator_cli.shared import _emit_json, _workspace_root_from_context
from packages.core_domain.automation_lease import (
    create_automation_lease,
    list_automation_leases,
    revoke_automation_lease,
)

automation_app = typer.Typer(help="Bounded unattended automation commands.")
lease_app = typer.Typer(help="Automation lease commands.")
automation_app.add_typer(lease_app, name="lease")


@lease_app.command("create")
def lease_create(
    ctx: typer.Context,
    allowed_action: list[str] = typer.Option(..., "--allowed-action", help="Action allowed by the lease."),
    write_set: Optional[list[str]] = typer.Option(None, "--write-set", help="Writable paths allowed by the lease."),
    denied_action: Optional[list[str]] = typer.Option(None, "--denied-action", help="Explicitly denied action."),
    ttl_seconds: int = typer.Option(3600, "--ttl-seconds", min=1),
    max_resume_count: int = typer.Option(20, "--max-resume-count", min=0),
    max_fix_iterations: int = typer.Option(2, "--max-fix-iterations", min=0),
) -> None:
    lease = create_automation_lease(
        workspace_root=_workspace_root_from_context(ctx),
        allowed_actions=list(allowed_action),
        denied_actions=list(denied_action or []),
        write_set_allowlist=list(write_set or []),
        ttl_seconds=ttl_seconds,
        max_resume_count=max_resume_count,
        max_fix_iterations=max_fix_iterations,
    )
    _emit_json(lease.model_dump(mode="json"))


@lease_app.command("status")
def lease_status(ctx: typer.Context, lease_id: Optional[str] = typer.Argument(None)) -> None:
    leases = list_automation_leases(_workspace_root_from_context(ctx))
    if lease_id:
        leases = [lease for lease in leases if lease.lease_id == lease_id]
    payload = [lease.model_dump(mode="json") for lease in leases]
    _emit_json(payload[0] if lease_id and payload else payload)
    if lease_id and not payload:
        raise typer.Exit(code=1)


@lease_app.command("revoke")
def lease_revoke(ctx: typer.Context, lease_id: str) -> None:
    lease = revoke_automation_lease(_workspace_root_from_context(ctx), lease_id)
    _emit_json(lease.model_dump(mode="json"))
