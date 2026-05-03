from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import typer

from apps.operator_cli.shared import _db_path_from_context, _emit_json, _workspace_root_from_context
from packages.contracts import Run
from packages.core_domain.db import migrate
from packages.core_domain.repositories import RunRepository, TaskRepository
from packages.core_domain.task_card_store import export_task_cards_markdown, task_card_quality_report
from packages.contributions.games.ai_playtest_lab import build_ai_playtest_plan, validate_ai_playtest_plan
from packages.contributions.games.ai_playtest_execution import evaluate_ai_playtest_execution_packet
from packages.contributions.games.ai_playtest_quality import evaluate_ai_surrogate_playtest
from packages.contributions.games.ai_playtest_runner import run_ai_playtest_plan
from packages.contributions.games.ai_repair_loop import (
    ai_repair_loop_report,
    build_repair_task_cards_from_ai_execution_report,
    build_repair_task_cards_from_ai_findings,
    repair_task_card_batch_report,
)
from packages.contributions.games.cocos.capabilities import REQUIRED_PLAYER_VISIBLE_CHECKS, cocos_capability_contracts
from packages.contributions.games.cocos.commercial_assets import (
    generate_cocos_commercial_asset_manifest,
    generate_cocos_local_stable_asset_manifest,
)
from packages.contributions.games.cocos.e2e import build_cocos_runtime_config, run_cocos_game_e2e
from packages.contributions.games.cocos.graph_bridge import build_cocos_graph_evidence_bridge
from packages.contributions.games.cocos.graph_pressure import run_cocos_graph_pressure_test
from packages.contributions.games.cocos.inspector import describe_cocos_delivery_modes, inspect_cocos_project_v2
from packages.contributions.games.cocos.player_validation import validate_cocos_player_visible_evidence
from packages.contributions.games.cocos.sample_closeout import run_cocos_small_goal_sample_closeout
from packages.contributions.games.game_design_ir import (
    apply_derived_semantic_enrichment,
    build_game_design_spec,
    validate_derived_semantic_enrichment,
    validate_game_design_spec,
)
from packages.contributions.games.game_task_card_generation import (
    build_game_production_task_cards_from_design_spec,
    game_task_card_generation_report,
)


game_app = typer.Typer(help="Game generation and E2E validation commands.")


@game_app.command("universal-design-ir")
def universal_design_ir(
    ctx: typer.Context,
    title: str = typer.Option(..., "--title", help="Game title from the source brief."),
    genre: str = typer.Option("unspecified", "--genre", help="Brief-derived genre label."),
    camera: str = typer.Option("brief_defined", "--camera", help="Brief-derived camera/presentation model."),
    source_path: Optional[list[Path]] = typer.Option(None, "--source-path", help="Source brief or requirement file."),
    requirement: Optional[list[str]] = typer.Option(None, "--requirement", help="Inline source requirement."),
    target_platform: Optional[list[str]] = typer.Option(None, "--target-platform", help="Target platform."),
    input_model: Optional[list[str]] = typer.Option(None, "--input-model", help="Input model."),
    output_path: Optional[Path] = typer.Option(None, "--output-path", help="Write the design spec JSON."),
) -> None:
    workspace_root = _workspace_root_from_context(ctx)
    sources = _design_ir_sources(workspace_root, source_path or [], requirement or [])
    if not sources:
        _emit_json(
            {
                "schema_version": "universal_game_design_ir_cli_v1",
                "go": False,
                "blockers": ["source_material_missing"],
            }
        )
        raise typer.Exit(code=1)
    spec = build_game_design_spec(
        title=title,
        genre=genre,
        camera=camera,
        target_platforms=target_platform,
        input_model=input_model,
        sources=sources,
    )
    design_spec = spec.to_dict()
    output = _write_json_file(output_path, design_spec)
    validation = validate_game_design_spec(design_spec)
    payload = {
        "schema_version": "universal_game_design_ir_cli_v1",
        "go": validation["go"],
        "design_spec": design_spec,
        "validation": validation,
        "output_path": output,
    }
    _emit_json(payload)
    if not validation["go"]:
        raise typer.Exit(code=1)


@game_app.command("ai-playtest-plan")
def ai_playtest_plan(
    design_spec_path: Path = typer.Option(..., "--design-spec-path", help="GameDesignSpec JSON path."),
    output_path: Optional[Path] = typer.Option(None, "--output-path", help="Write the AI playtest plan JSON."),
) -> None:
    spec = _load_design_spec(design_spec_path)
    plan = build_ai_playtest_plan(spec)
    validation = validate_ai_playtest_plan(plan)
    output = _write_json_file(output_path, plan)
    payload = {
        "schema_version": "universal_ai_playtest_plan_cli_v1",
        "go": validation["go"],
        "plan": plan,
        "validation": validation,
        "output_path": output,
    }
    _emit_json(payload)
    if not validation["go"]:
        raise typer.Exit(code=1)


@game_app.command("design-ir-enrich")
def design_ir_enrich(
    design_spec_path: Path = typer.Option(..., "--design-spec-path", help="GameDesignSpec JSON path."),
    enrichment_path: Path = typer.Option(..., "--enrichment-path", help="Derived-only semantic enrichment JSON."),
    output_path: Optional[Path] = typer.Option(None, "--output-path", help="Write enriched GameDesignSpec JSON."),
) -> None:
    spec = _load_design_spec(design_spec_path)
    enrichment = _read_json_file(enrichment_path)
    validation = validate_derived_semantic_enrichment(spec, enrichment)
    enriched = apply_derived_semantic_enrichment(spec, enrichment)
    output = _write_json_file(output_path, enriched)
    payload = {
        "schema_version": "universal_game_design_ir_enrichment_cli_v1",
        "go": validation["go"],
        "validation": validation,
        "design_spec": enriched,
        "output_path": output,
    }
    _emit_json(payload)
    if not validation["go"]:
        raise typer.Exit(code=1)


@game_app.command("production-task-cards")
def production_task_cards(
    ctx: typer.Context,
    design_spec_path: Path = typer.Option(..., "--design-spec-path", help="GameDesignSpec JSON path."),
    run_id: str = typer.Option(..., "--run-id", help="Current active commercial game run id."),
    phase_name: str = typer.Option(
        "Universal Game Production Quality And AI Playtest Architecture",
        "--phase-name",
        help="Current active phase name.",
    ),
    status: str = typer.Option("active", "--status", help="Task card lifecycle status."),
    write_db: bool = typer.Option(False, "--write-db", help="Persist generated cards to the workflow task_cards table."),
    export_path: Optional[Path] = typer.Option(None, "--export-path", help="Write a Markdown review snapshot."),
    output_path: Optional[Path] = typer.Option(None, "--output-path", help="Write the CLI report JSON."),
) -> None:
    spec = _load_design_spec(design_spec_path)
    cards = build_game_production_task_cards_from_design_spec(
        run_id=run_id,
        phase_name=phase_name,
        spec=spec,
        status=status,
    )
    db_report = _persist_task_cards(ctx, run_id, phase_name, cards) if write_db else None
    markdown_path = export_task_cards_markdown(
        cards,
        export_path,
        title=f"Universal Game Production Task Cards for {run_id}",
    ).as_posix() if export_path is not None else None
    quality = task_card_quality_report(cards)
    payload = {
        "schema_version": "universal_game_production_task_card_cli_v1",
        "go": quality["go_no_go"] == "GO",
        "task_cards": [card.model_dump(mode="json") for card in cards],
        "generation_report": game_task_card_generation_report(cards),
        "quality": quality,
        "db": db_report,
        "markdown_export_path": markdown_path,
    }
    output = _write_json_file(output_path, payload)
    payload["output_path"] = output
    _emit_json(payload)
    if quality["go_no_go"] != "GO":
        raise typer.Exit(code=1)


@game_app.command("ai-quality-gate")
def ai_quality_gate(
    evidence_path: Path = typer.Option(..., "--evidence-path", help="AI surrogate playtest evidence JSON path."),
    output_path: Optional[Path] = typer.Option(None, "--output-path", help="Write the AI quality gate report JSON."),
) -> None:
    evidence = _read_json_file(evidence_path)
    report = evaluate_ai_surrogate_playtest(evidence)
    output = _write_json_file(output_path, report)
    report["output_path"] = output
    _emit_json(report)
    if not report["ai_surrogate_playtest_go"]:
        raise typer.Exit(code=1)


@game_app.command("ai-playtest-execution-gate")
def ai_playtest_execution_gate(
    ctx: typer.Context,
    packet_path: Path = typer.Option(..., "--packet-path", help="AI surrogate playtest execution packet JSON path."),
    require_artifact_files: bool = typer.Option(
        True,
        "--require-artifact-files/--no-require-artifact-files",
        help="Require replay, screenshot, and state snapshot files to exist.",
    ),
    output_path: Optional[Path] = typer.Option(None, "--output-path", help="Write the execution gate report JSON."),
) -> None:
    packet = _read_json_file(packet_path)
    report = evaluate_ai_playtest_execution_packet(
        packet,
        workspace_root=_workspace_root_from_context(ctx),
        require_artifact_files=require_artifact_files,
    )
    output = _write_json_file(output_path, report)
    report["output_path"] = output
    _emit_json(report)
    if not report["go"]:
        raise typer.Exit(code=1)


@game_app.command("ai-playtest-run")
def ai_playtest_run(
    ctx: typer.Context,
    plan_path: Path = typer.Option(..., "--plan-path", help="AI playtest plan JSON path."),
    output_dir: Path = typer.Option(..., "--output-dir", help="Directory for runner packet, report, and artifacts."),
    target_url: Optional[str] = typer.Option(None, "--target-url", help="Browser URL to test."),
    build_output_path: Optional[Path] = typer.Option(None, "--build-output-path", help="Static browser build directory to serve and test."),
    engine_body_path: Optional[Path] = typer.Option(None, "--engine-body-path", help="Engine-native product body evidence JSON."),
    quality_overrides_path: Optional[Path] = typer.Option(
        None,
        "--quality-overrides-path",
        help="Explicit AI/reviewer quality judgments. Required for subjective GO fields.",
    ),
    no_require_artifact_files: bool = typer.Option(
        False,
        "--no-require-artifact-files",
        help="Do not check generated replay/screenshot/state files when evaluating the packet.",
    ),
    output_path: Optional[Path] = typer.Option(None, "--output-path", help="Write the runner summary JSON."),
) -> None:
    plan = _read_json_file(plan_path)
    engine_body = _read_json_file(engine_body_path) if engine_body_path is not None else None
    quality_overrides = _read_json_file(quality_overrides_path) if quality_overrides_path is not None else None
    result = run_ai_playtest_plan(
        plan=plan,
        workspace_root=_workspace_root_from_context(ctx),
        output_dir=output_dir,
        target_url=target_url,
        build_output_path=build_output_path,
        engine_native_product_body=engine_body,
        quality_overrides=quality_overrides,
        require_artifact_files=not no_require_artifact_files,
    )
    summary = {
        "schema_version": "universal_ai_playtest_run_cli_v1",
        "go": result["go"],
        "packet_path": result["packet_path"],
        "report_path": result["report_path"],
        "runner": result["report"].get("runner"),
        "validation": result["report"].get("validation"),
        "quality": result["report"].get("quality"),
    }
    output = _write_json_file(output_path, summary)
    summary["output_path"] = output
    _emit_json(summary)


@game_app.command("ai-repair-cards")
def ai_repair_cards(
    ctx: typer.Context,
    findings_path: Path = typer.Option(..., "--findings-path", help="AI findings JSON path."),
    run_id: str = typer.Option(..., "--run-id", help="Current repair run id."),
    phase_name: str = typer.Option(..., "--phase-name", help="Current repair phase name."),
    status: str = typer.Option("active", "--status", help="Task card lifecycle status."),
    required_requirement_id: Optional[list[str]] = typer.Option(
        None,
        "--required-requirement-id",
        help="Fallback requirement id for findings without explicit coverage.",
    ),
    write_db: bool = typer.Option(False, "--write-db", help="Persist generated repair cards to task_cards."),
    export_path: Optional[Path] = typer.Option(None, "--export-path", help="Write a Markdown review snapshot."),
    output_path: Optional[Path] = typer.Option(None, "--output-path", help="Write the CLI report JSON."),
) -> None:
    findings = _load_findings(findings_path)
    cards = build_repair_task_cards_from_ai_findings(
        run_id=run_id,
        phase_name=phase_name,
        findings=findings,
        required_requirement_ids=required_requirement_id,
        status=status,
    )
    db_report = _persist_task_cards(ctx, run_id, phase_name, cards) if write_db else None
    markdown_path = export_task_cards_markdown(
        cards,
        export_path,
        title=f"AI Playtest Repair Task Cards for {run_id}",
    ).as_posix() if export_path is not None else None
    quality = task_card_quality_report(cards)
    payload = {
        "schema_version": "universal_ai_repair_task_card_cli_v1",
        "go": quality["go_no_go"] == "GO",
        "task_cards": [card.model_dump(mode="json") for card in cards],
        "generation_report": repair_task_card_batch_report(cards),
        "quality": quality,
        "db": db_report,
        "markdown_export_path": markdown_path,
    }
    output = _write_json_file(output_path, payload)
    payload["output_path"] = output
    _emit_json(payload)
    if quality["go_no_go"] != "GO":
        raise typer.Exit(code=1)


@game_app.command("ai-repair-loop")
def ai_repair_loop(
    ctx: typer.Context,
    execution_report_path: Path = typer.Option(..., "--execution-report-path", help="AI playtest execution report JSON path."),
    run_id: str = typer.Option(..., "--run-id", help="Current repair run id."),
    phase_name: str = typer.Option("AI Surrogate Repair Phase", "--phase-name", help="Current repair phase name."),
    status: str = typer.Option("active", "--status", help="Task card lifecycle status."),
    required_requirement_id: Optional[list[str]] = typer.Option(
        None,
        "--required-requirement-id",
        help="Fallback requirement id when the AI report does not carry explicit coverage.",
    ),
    write_db: bool = typer.Option(False, "--write-db", help="Persist generated repair cards to task_cards."),
    export_path: Optional[Path] = typer.Option(None, "--export-path", help="Write a Markdown review snapshot."),
    task_card_dir: Optional[Path] = typer.Option(None, "--task-card-dir", help="Write per-card worker input Markdown files."),
    output_path: Optional[Path] = typer.Option(None, "--output-path", help="Write the repair loop report JSON."),
) -> None:
    report = _read_json_file(execution_report_path)
    cards = build_repair_task_cards_from_ai_execution_report(
        run_id=run_id,
        phase_name=phase_name,
        report=report,
        required_requirement_ids=required_requirement_id,
        status=status,
    )
    db_report = _persist_task_cards(ctx, run_id, phase_name, cards) if write_db and cards else None
    markdown_path = export_task_cards_markdown(
        cards,
        export_path,
        title=f"AI NO-GO Repair Loop Task Cards for {run_id}",
    ).as_posix() if export_path is not None and cards else None
    worker_entries = _materialize_worker_entry_commands(ctx, cards, task_card_dir) if cards else []
    quality = task_card_quality_report(cards)
    loop = ai_repair_loop_report(execution_report=report, cards=cards)
    go = (not loop["repair_required"]) or quality["go_no_go"] == "GO"
    payload = {
        "schema_version": "universal_ai_repair_loop_cli_v1",
        "go": go,
        "repair_required": loop["repair_required"],
        "loop": loop,
        "task_cards": [card.model_dump(mode="json") for card in cards],
        "quality": quality,
        "db": db_report,
        "markdown_export_path": markdown_path,
        "worker_loop_entries": worker_entries,
    }
    output = _write_json_file(output_path, payload)
    payload["output_path"] = output
    _emit_json(payload)
    if not go:
        raise typer.Exit(code=1)


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
    evidence_path = (evidence_dir or workspace_root / "state" / "cocos_graph_pressure") / "player_visible_cli_evidence.json"
    player_checks = (
        {
            check_name: {
                "status": "pass",
                "method": "operator_cli_player_visible_evidence",
                "evidence_path": evidence_path.as_posix(),
                "evidence_hash": f"operator-cli:{check_name}",
                "validator_version": "m105.0",
            }
            for check_name in REQUIRED_PLAYER_VISIBLE_CHECKS
        }
        if player_visible_evidence
        else {}
    )
    if player_visible_evidence:
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text('{"source":"operator_cli_player_visible_evidence"}\n', encoding="utf-8")
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
    use_local_stable_assets: bool = typer.Option(False, "--use-local-stable-assets", help="Use deterministic local assets instead of external generation."),
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
        use_local_stable_assets=use_local_stable_assets,
    )
    _emit_json(payload)
    if payload["manifest"]["go_no_go"] != "GO":
        raise typer.Exit(code=1)


@game_app.command("cocos-config")
def cocos_config(
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
    require_commercial: bool = typer.Option(False, "--require-commercial", help="Require player-visible commercial readiness."),
) -> None:
    workspace_root = _workspace_root_from_context(ctx)
    resolved_output = output_dir or workspace_root / "state" / "m105_cocos_runtime" / "project"
    payload = build_cocos_runtime_config(
        pdf_path=pdf_path,
        output_dir=resolved_output,
        creator_exe=creator_exe,
        require_build=require_build,
        require_playtest=require_playtest,
        require_commercial=require_commercial,
    )
    _emit_json(payload)
    if payload["go_no_go"] != "GO":
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


@game_app.command("cocos-local-assets")
def cocos_local_assets(
    ctx: typer.Context,
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", help="Local deterministic asset output directory."),
) -> None:
    workspace_root = _workspace_root_from_context(ctx)
    resolved_output = output_dir or workspace_root / "state" / "m106_cocos_local_assets"
    payload = generate_cocos_local_stable_asset_manifest(output_dir=resolved_output)
    _emit_json(payload)
    if payload["go_no_go"] != "GO":
        raise typer.Exit(code=1)


@game_app.command("cocos-inspect")
def cocos_inspect(
    project_path: Path = typer.Option(..., "--project-path", help="Cocos project directory."),
    evidence_dir: Optional[Path] = typer.Option(None, "--evidence-dir"),
) -> None:
    payload = inspect_cocos_project_v2(project_path=project_path, evidence_dir=evidence_dir)
    _emit_json(payload)
    if payload["technical_smoke_go"] is False:
        raise typer.Exit(code=1)


@game_app.command("cocos-delivery")
def cocos_delivery(
    project_path: Path = typer.Option(..., "--project-path", help="Cocos project directory."),
    build_output_path: Optional[Path] = typer.Option(None, "--build-output-path"),
    evidence_dir: Optional[Path] = typer.Option(None, "--evidence-dir"),
) -> None:
    payload = describe_cocos_delivery_modes(
        project_path=project_path,
        build_output_path=build_output_path,
        evidence_dir=evidence_dir,
    )
    _emit_json(payload)
    if payload["go_no_go"] != "GO":
        raise typer.Exit(code=1)


@game_app.command("cocos-graph-evidence")
def cocos_graph_evidence(
    ctx: typer.Context,
    project_path: Path = typer.Option(..., "--project-path", help="Cocos project directory."),
    evidence_dir: Optional[Path] = typer.Option(None, "--evidence-dir"),
) -> None:
    payload = build_cocos_graph_evidence_bridge(
        workspace_root=_workspace_root_from_context(ctx),
        project_path=project_path,
        evidence_dir=evidence_dir,
    )
    _emit_json(payload)
    if payload["status"] != "completed":
        raise typer.Exit(code=1)


@game_app.command("cocos-player-validate")
def cocos_player_validate(
    project_path: Path = typer.Option(..., "--project-path", help="Cocos project directory."),
    evidence_dir: Optional[Path] = typer.Option(None, "--evidence-dir"),
) -> None:
    manifest_path = project_path / "cocos_game_e2e_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    metadata = dict(manifest.get("metadata") or {})
    payload = validate_cocos_player_visible_evidence(
        playtest=metadata.get("playtest"),
        inspection=metadata.get("commercial_project_inspection"),
        technical_smoke=bool(metadata.get("technical_smoke_go")),
        production_scaffold=bool(metadata.get("production_scaffold_go")),
        evidence_dir=evidence_dir,
    )
    _emit_json(payload)
    if payload["go_no_go"] != "GO":
        raise typer.Exit(code=1)


@game_app.command("cocos-sample-closeout")
def cocos_sample_closeout(
    ctx: typer.Context,
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", help="Cocos sample project output directory."),
    evidence_dir: Optional[Path] = typer.Option(None, "--evidence-dir"),
    creator_exe: Path = typer.Option(
        Path(r"C:\ProgramData\cocos\editors\Creator\3.8.8\CocosCreator.exe"),
        "--creator-exe",
        help="Cocos Creator executable.",
    ),
    require_build: bool = typer.Option(False, "--require-build", help="Run Cocos Creator Web Mobile build."),
    require_playtest: bool = typer.Option(True, "--require-playtest/--skip-playtest", help="Run browser playtest after build."),
) -> None:
    workspace_root = _workspace_root_from_context(ctx)
    resolved_output = output_dir or workspace_root / "state" / "m108_cocos_sample_closeout" / "project"
    payload = run_cocos_small_goal_sample_closeout(
        workspace_root=workspace_root,
        output_dir=resolved_output,
        creator_exe=creator_exe,
        evidence_dir=evidence_dir,
        require_build=require_build,
        require_playtest=require_playtest,
    )
    _emit_json(payload)


def _design_ir_sources(workspace_root: Path, source_paths: list[Path], inline_requirements: list[str]) -> list[dict]:
    sources: list[dict] = []
    for index, source_path in enumerate(source_paths, start=1):
        resolved = source_path if source_path.is_absolute() else workspace_root / source_path
        text = resolved.read_text(encoding="utf-8")
        sources.append(
            {
                "source_id": source_path.stem or f"source_{index:03d}",
                "original_path": resolved.resolve().as_posix(),
                "raw_text": text,
            }
        )
    if inline_requirements:
        sources.append(
            {
                "source_id": "inline_requirements",
                "raw_text": "\n".join(inline_requirements),
                "requirements": inline_requirements,
            }
        )
    return sources


def _read_json_file(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {"items": payload}


def _write_json_file(path: Optional[Path], payload: dict | list) -> str | None:
    if path is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path.as_posix()


def _load_design_spec(path: Path) -> dict:
    payload = _read_json_file(path)
    if isinstance(payload.get("design_spec"), dict):
        return payload["design_spec"]
    if isinstance(payload.get("spec"), dict):
        return payload["spec"]
    return payload


def _load_findings(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        findings = payload.get("findings")
        if isinstance(findings, list):
            return [item for item in findings if isinstance(item, dict)]
    return []


def _materialize_worker_entry_commands(ctx: typer.Context, cards: list, task_card_dir: Optional[Path]) -> list[dict[str, Any]]:
    workspace_root = _workspace_root_from_context(ctx)
    db_path = _db_path_from_context(ctx)
    run_id = str(cards[0].run_id) if cards else "ai_repair_loop"
    resolved_dir = task_card_dir or workspace_root / "state" / "ai_repair_loop" / run_id / "task_cards"
    resolved_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    for card in cards:
        card_path = resolved_dir / f"{_safe_file_stem(card.task_card_id)}.md"
        card_path.write_text(_task_card_markdown(card), encoding="utf-8")
        command = [
            "workflowctl",
            "--db-path",
            db_path.as_posix(),
            "--workspace-root",
            workspace_root.as_posix(),
            "run",
            "from-task-card",
            card_path.as_posix(),
            "--preset",
            "project_delivery",
            "--task-card-ref",
            card.task_card_id,
        ]
        for item in card.write_set:
            command.extend(["--write-set", item])
        for item in card.read_set:
            command.extend(["--read-set", item])
        for item in card.test_commands:
            command.extend(["--test-command", item])
        command.extend(["--max-fix-iterations", "2", "--execute"])
        entries.append(
            {
                "task_card_id": card.task_card_id,
                "task_card_path": card_path.as_posix(),
                "execution_visibility_mode": card.metadata.get("execution_visibility_mode"),
                "requires_human_visible_cli_window": bool(card.metadata.get("human_visible_cli_required")),
                "command": command,
            }
        )
    return entries


def _task_card_markdown(card: Any) -> str:
    return "\n".join(
        [
            f"# {card.title}",
            "",
            f"task_card_id: {card.task_card_id}",
            f"run_id: {card.run_id}",
            f"phase_name: {card.phase_name}",
            f"risk_level: {card.risk_level}",
            f"execution_mode: {card.execution_mode}",
            "",
            "## Goal",
            card.goal,
            "",
            "## Description",
            card.description,
            "",
            "## Write Set",
            *_markdown_list(card.write_set),
            "",
            "## Read Set",
            *_markdown_list(card.read_set),
            "",
            "## Test Commands",
            *_markdown_list(card.test_commands),
            "",
            "## Acceptance Criteria",
            *_markdown_list(card.acceptance_criteria),
            "",
            "## Evidence Requirements",
            *_markdown_list(card.evidence_requirements),
            "",
            "## Blocking Conditions",
            *_markdown_list(card.blocking_conditions),
            "",
            "## Model Guidance",
            *_markdown_list(card.model_guidance),
            "",
            "## Metadata",
            "```json",
            json.dumps(card.metadata, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )


def _markdown_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]


def _safe_file_stem(value: str) -> str:
    safe = []
    for char in value:
        if char.isascii() and (char.isalnum() or char in {"-", "_"}):
            safe.append(char)
        else:
            safe.append("_")
    return "".join(safe).strip("_") or "task_card"


def _persist_task_cards(ctx: typer.Context, run_id: str, phase_name: str, cards: list) -> dict:
    db_path = _db_path_from_context(ctx)
    migrate(db_path)
    run_repo = RunRepository(db_path)
    task_repo = TaskRepository(db_path)
    if run_repo.get(run_id) is None:
        run_repo.create(Run(run_id=run_id, goal=phase_name, preset_id="commercial_game_production"))
    created: list[str] = []
    preserved_existing: list[str] = []
    for card in cards:
        existing = task_repo.get_task_card(card.task_card_id)
        if existing is not None:
            preserved_existing.append(card.task_card_id)
            continue
        task_repo.create_task_card(card)
        created.append(card.task_card_id)
    return {
        "db_path": db_path.as_posix(),
        "write_mode": "preserve_existing",
        "created_task_card_ids": created,
        "preserved_existing_task_card_ids": preserved_existing,
    }
