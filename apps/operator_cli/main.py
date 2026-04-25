from __future__ import annotations

from typing import Optional

import typer

from apps.operator_cli.admin_commands import config_app, db_app, governance_app, task_app
from apps.operator_cli.catalog_commands import (
    capability_app,
    domain_pack_app,
    memory_app,
    preset_app,
    simulation_app,
)
from apps.operator_cli.doctor_payload import _build_doctor_payload
from apps.operator_cli.interaction_commands import interaction_app
from apps.operator_cli.run_commands import run_app
from apps.operator_cli.scheduler_commands import scheduler_app
from apps.operator_cli.shared import _emit_json, _service
from apps.operator_cli.test_commands import test_app
from apps.operator_cli.validation_commands import validation_app
from apps.operator_tui.dashboard import run_dashboard
from packages.core_domain.config import build_effective_config

app = typer.Typer(help="Workflow operator CLI.")

app.add_typer(test_app, name="test")
app.add_typer(validation_app, name="validation")
app.add_typer(run_app, name="run")
app.add_typer(interaction_app, name="interaction")
app.add_typer(task_app, name="task")
app.add_typer(preset_app, name="preset")
app.add_typer(domain_pack_app, name="domain-pack")
app.add_typer(capability_app, name="capability")
app.add_typer(simulation_app, name="simulation")
app.add_typer(memory_app, name="memory")
app.add_typer(scheduler_app, name="scheduler")
app.add_typer(db_app, name="db")
app.add_typer(governance_app, name="governance")
app.add_typer(config_app, name="config")


@app.callback()
def main(
    ctx: typer.Context,
    db_path: Optional[str] = typer.Option(None, "--db-path", help="SQLite database path."),
    workspace_root: Optional[str] = typer.Option(None, "--workspace-root", help="Explicit workspace root for file mutations."),
) -> None:
    effective = build_effective_config(explicit_db_path=db_path, explicit_workspace_root=workspace_root)
    ctx.obj = {
        "db_path": effective["db"]["path"],
        "workspace_root": effective["workspace"]["root"],
        "effective_config": effective,
    }


@app.command("tui")
def launch_tui(
    ctx: typer.Context,
    run_id: Optional[str] = typer.Option(None, "--run-id", help="Focus a specific run in the dashboard."),
    limit: int = typer.Option(8, "--limit", min=1, help="Maximum number of recent runs to render."),
    refresh_seconds: float = typer.Option(2.0, "--refresh-seconds", min=0.2, help="Refresh interval in watch mode."),
    once: bool = typer.Option(False, "--once", help="Render one snapshot instead of entering watch mode."),
    cycles: Optional[int] = typer.Option(
        None,
        "--cycles",
        min=1,
        help="Maximum refresh cycles in watch mode. Useful for tests.",
    ),
) -> None:
    service = _service(ctx)
    run_dashboard(
        service,
        run_id=run_id,
        limit=limit,
        refresh_seconds=refresh_seconds,
        once=once,
        cycles=cycles,
    )


@app.command("doctor")
def doctor(
    ctx: typer.Context,
    strict: bool = typer.Option(False, "--strict", help="Exit non-zero when doctor reports any issue."),
) -> None:
    payload = _build_doctor_payload(ctx)
    _emit_json(payload)
    if strict and payload.get("issues"):
        raise typer.Exit(code=1)


def run() -> None:
    app()


if __name__ == "__main__":
    run()
