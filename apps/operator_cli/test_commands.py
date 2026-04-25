from __future__ import annotations

from typing import Optional

import typer

from apps.operator_cli.shared import _emit_json, _workspace_root_from_context

test_app = typer.Typer(help="Workflow test matrix commands.")

@test_app.command("matrix")
def test_matrix(
    ctx: typer.Context,
    suite: str = typer.Option(..., "--suite", help="Suite: unit, core, integration, slow, or full."),
    shard: Optional[str] = typer.Option(None, "--shard", help="Optional shard in N/M form, for example 1/4."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the selected pytest command without running it."),
) -> None:
    from packages.core_domain.test_matrix import run_matrix

    payload = run_matrix(
        suite=suite,
        shard=shard,
        workspace_root=_workspace_root_from_context(ctx),
        dry_run=dry_run,
    )
    _emit_json(payload)
    if payload.get("return_code"):
        raise typer.Exit(code=int(payload["return_code"]))
