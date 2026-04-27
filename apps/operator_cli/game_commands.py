from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from apps.operator_cli.shared import _emit_json, _workspace_root_from_context
from packages.contributions.games.cocos.capabilities import cocos_capability_contracts
from packages.contributions.games.cocos.commercial_assets import generate_cocos_commercial_asset_manifest
from packages.contributions.games.cocos.e2e import run_cocos_game_e2e
from packages.contributions.games.cocos.graph_pressure import run_cocos_graph_pressure_test


game_app = typer.Typer(help="Game generation and E2E validation commands.")


@game_app.command("cocos-capabilities")
def cocos_capabilities(
    ctx: typer.Context,
    project_path: Optional[Path] = typer.Option(None, "--project-path", help="Optional Cocos project path."),
) -> None:
    workspace_root = _workspace_root_from_context(ctx)
    _emit_json(cocos_capability_contracts(project_path=project_path or workspace_root))


@game_app.command("cocos-graph-pressure")
def cocos_graph_pressure(
    ctx: typer.Context,
    project_path: Optional[Path] = typer.Option(None, "--project-path", help="Optional Cocos project path."),
    evidence_dir: Optional[Path] = typer.Option(None, "--evidence-dir"),
    technical_smoke: bool = typer.Option(True, "--technical-smoke/--no-technical-smoke"),
    production_scaffold: bool = typer.Option(True, "--production-scaffold/--no-production-scaffold"),
    player_visible_evidence: bool = typer.Option(False, "--player-visible-evidence/--no-player-visible-evidence"),
) -> None:
    workspace_root = _workspace_root_from_context(ctx)
    resolved_project = project_path or workspace_root / "state" / "cocos_graph_pressure" / "project"
    player_checks = {
        "hud_usable": True,
        "level_flow_visible": True,
        "audio_feedback_acceptable": True,
    } if player_visible_evidence else {}
    payload = run_cocos_graph_pressure_test(
        workspace_root=workspace_root,
        project_path=resolved_project,
        evidence_dir=evidence_dir,
        technical_smoke=technical_smoke,
        production_scaffold=production_scaffold,
        player_visible_checks=player_checks,
    )
    _emit_json(payload)


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
    require_commercial: bool = typer.Option(False, "--require-commercial", help="Fail unless commercial art/audio/UI/animation coverage is present."),
    generate_commercial_assets: bool = typer.Option(False, "--generate-commercial-assets", help="Generate MMX/GCP commercial art and audio assets before commercial gate."),
) -> None:
    workspace_root = _workspace_root_from_context(ctx)
    resolved_output = output_dir or workspace_root / "state" / "m73_m76_autopilot" / "cocos_e2e" / "1010_block_puzzle_cocos"
    payload = run_cocos_game_e2e(
        pdf_path=pdf_path,
        output_dir=resolved_output,
        creator_exe=creator_exe,
        require_build=require_build,
        require_playtest=require_playtest,
        require_commercial=require_commercial,
        generate_commercial_assets=generate_commercial_assets,
    )
    _emit_json(payload)
    if payload["manifest"]["go_no_go"] != "GO":
        raise typer.Exit(code=1)


@game_app.command("cocos-assets")
def cocos_assets(
    ctx: typer.Context,
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", help="Asset manifest output directory."),
    style_prompt: str = typer.Option(
        "premium neon 1010 block puzzle mobile game, polished casual commercial art",
        "--style-prompt",
        help="Commercial art direction prompt.",
    ),
    skip_vertex_review: bool = typer.Option(False, "--skip-vertex-review", help="Skip Vertex Gemini visual review."),
) -> None:
    workspace_root = _workspace_root_from_context(ctx)
    resolved_output = output_dir or workspace_root / "state" / "m77_integrated_repair" / "cocos_assets"
    payload = generate_cocos_commercial_asset_manifest(
        output_dir=resolved_output,
        style_prompt=style_prompt,
        include_vertex_review=not skip_vertex_review,
    )
    _emit_json(payload)
    if payload["go_no_go"] != "GO":
        raise typer.Exit(code=1)
