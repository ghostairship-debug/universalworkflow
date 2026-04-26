from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from apps.operator_cli.shared import _emit_json, _workspace_root_from_context
from packages.core_domain.cocos_e2e import run_cocos_game_e2e


game_app = typer.Typer(help="Game generation and E2E validation commands.")


@game_app.command("cocos-e2e")
def cocos_e2e(
    ctx: typer.Context,
    pdf_path: Path = typer.Option(..., "--pdf-path", help="Source game design PDF."),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", help="Cocos project output directory."),
    creator_exe: Path = typer.Option(
        Path(r"C:\ProgramData\cocos\editors\Creator\3.8.8\CocosCreator.exe"),
        "--creator-exe",
        help="Cocos Creator executable.",
    ),
    require_build: bool = typer.Option(False, "--require-build", help="Run Cocos Creator Web Mobile build."),
    require_playtest: bool = typer.Option(True, "--require-playtest/--skip-playtest", help="Run browser playtest after build."),
) -> None:
    workspace_root = _workspace_root_from_context(ctx)
    resolved_output = output_dir or workspace_root / "state" / "m73_m76_autopilot" / "cocos_e2e" / "1010_block_puzzle_cocos"
    payload = run_cocos_game_e2e(
        pdf_path=pdf_path,
        output_dir=resolved_output,
        creator_exe=creator_exe,
        require_build=require_build,
        require_playtest=require_playtest,
    )
    _emit_json(payload)
    if payload["manifest"]["go_no_go"] != "GO":
        raise typer.Exit(code=1)
