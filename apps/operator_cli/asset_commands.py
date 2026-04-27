from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from apps.operator_cli.shared import _emit_json, _workspace_root_from_context
from packages.contributions.asset_factory.factory import qa_asset_factory_manifest, run_asset_factory


asset_app = typer.Typer(help="Asset factory commands.")
factory_app = typer.Typer(help="Batch asset generation and QA.")

asset_app.add_typer(factory_app, name="factory")


@factory_app.command("run")
def asset_factory_run(
    ctx: typer.Context,
    style_guide: str = typer.Option(..., "--style-guide", help="Style guide text or path to a UTF-8 style guide file."),
    manifest: Path = typer.Option(..., "--manifest", help="Asset prompt manifest JSON."),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", help="Output directory for generated assets."),
    max_attempts: int = typer.Option(2, "--max-attempts", min=1, help="Attempts per asset before marking it blocked."),
) -> None:
    workspace_root = _workspace_root_from_context(ctx)
    resolved_output = output_dir or workspace_root / "state" / "asset_factory"
    payload = run_asset_factory(
        style_guide=style_guide,
        manifest_path=manifest,
        output_dir=resolved_output,
        max_attempts=max_attempts,
    )
    _emit_json(payload)
    if payload["go_no_go"] != "GO":
        raise typer.Exit(code=1)


@factory_app.command("qa")
def asset_factory_qa(
    asset_manifest: Path = typer.Option(..., "--asset-manifest", help="Asset factory manifest JSON."),
    evidence_dir: Path = typer.Option(..., "--evidence-dir", help="Directory for visual QA evidence."),
) -> None:
    payload = qa_asset_factory_manifest(asset_manifest_path=asset_manifest, evidence_dir=evidence_dir)
    _emit_json(payload)
    if payload["go_no_go"] != "GO":
        raise typer.Exit(code=1)
