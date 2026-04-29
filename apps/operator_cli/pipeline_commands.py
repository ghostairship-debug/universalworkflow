from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from apps.operator_cli.shared import _db_path_from_context, _emit_json, _workspace_root_from_context
from packages.contributions.games.cocos.e2e import discover_cocos_creator_exe
from packages.contributions.pipelines import preview_workflow_pipeline, run_workflow_pipeline
from packages.core_domain.pipeline_truth import build_pipeline_truth_report

pipeline_app = typer.Typer(help="WorkflowPipeline preview and serial execution commands.")


def _resolve_pipeline_goal(goal: str | None, template: str | None) -> str:
    if goal:
        return goal
    if template:
        return f"Run {template} pipeline"
    _emit_json(
        {
            "error": {
                "code": "pipeline_goal_or_template_required",
                "message": "pipeline preview/run requires --goal or --template",
                "details": {},
            }
        }
    )
    raise typer.Exit(code=1)


@pipeline_app.command("preview")
def pipeline_preview(
    goal: Optional[str] = typer.Option(None, "--goal"),
    template: Optional[str] = typer.Option(None, "--template", help="Reusable pipeline template id."),
    pipeline_id: Optional[str] = typer.Option(None, "--pipeline-id"),
) -> None:
    pipeline = preview_workflow_pipeline(_resolve_pipeline_goal(goal, template), pipeline_id=pipeline_id, template=template)
    _emit_json(pipeline.model_dump(mode="json"))


@pipeline_app.command("truth-report")
def pipeline_truth_report(
    goal: Optional[str] = typer.Option(None, "--goal"),
    template: Optional[str] = typer.Option(None, "--template", help="Reusable pipeline template id."),
    pipeline_id: Optional[str] = typer.Option(None, "--pipeline-id"),
) -> None:
    pipeline = preview_workflow_pipeline(_resolve_pipeline_goal(goal, template), pipeline_id=pipeline_id, template=template)
    _emit_json(build_pipeline_truth_report(pipeline))


@pipeline_app.command("run")
def pipeline_run(
    ctx: typer.Context,
    goal: Optional[str] = typer.Option(None, "--goal"),
    template: Optional[str] = typer.Option(None, "--template", help="Reusable pipeline template id."),
    pipeline_id: Optional[str] = typer.Option(None, "--pipeline-id"),
    evidence_dir: Optional[str] = typer.Option(None, "--evidence-dir"),
    automation_lease_id: Optional[str] = typer.Option(None, "--automation-lease-id"),
    execute_capabilities: bool = typer.Option(
        False,
        "--execute-capabilities/--preview-only-capabilities",
        help="Actually run registered capability stages instead of blocking them as explicit handoff points.",
    ),
    execute_agent_roles: bool = typer.Option(
        False,
        "--execute-agent-roles/--stub-agent-roles",
        help="Actually run registered single-agent role stages instead of recording them as stubbed handoff points.",
    ),
    live_agent_roles: bool = typer.Option(
        False,
        "--live-agent-roles/--offline-agent-roles",
        help="Require role stages to call a configured live LLM provider instead of deterministic offline role evidence.",
    ),
    repair_loop: bool = typer.Option(
        False,
        "--repair-loop/--no-repair-loop",
        help="Allow supervisor stages to emit bounded repair packets for local targeted repair.",
    ),
    max_repair_attempts: int = typer.Option(3, "--max-repair-attempts", min=0),
    require_real_assets: bool = typer.Option(
        False,
        "--require-real-assets/--allow-placeholder-assets",
        help="Require real asset provider evidence for commercial GO; placeholder-only assets stay NO-GO.",
    ),
    require_cocos_ecosystem: bool = typer.Option(
        False,
        "--require-cocos-ecosystem/--allow-cli-cocos-only",
        help="Require Cocos Editor bridge/AssetDB/Scene/Prefab ecosystem evidence for commercial GO.",
    ),
    require_human_player_review: bool = typer.Option(
        False,
        "--require-human-player-review/--allow-automated-player-review",
        help="Require explicit operator/player review evidence before commercial GO.",
    ),
    cocos_bridge_mode: str = typer.Option(
        "auto",
        "--cocos-bridge-mode",
        help="Cocos ecosystem bridge mode: auto launches the Editor bridge runner; report_only only validates an existing report.",
    ),
    cocos_bridge_timeout_seconds: int = typer.Option(
        180,
        "--cocos-bridge-timeout-seconds",
        min=0,
        help="Wall timeout for waiting on the Cocos Editor bridge report.",
    ),
    cocos_bridge_report_path: Optional[Path] = typer.Option(
        None,
        "--cocos-bridge-report-path",
        help="Explicit cocos_editor_bridge_report.json path to validate or poll.",
    ),
    allow_existing_cocos_process: bool = typer.Option(
        False,
        "--allow-existing-cocos-process/--block-existing-cocos-process",
        help="Allow running the bridge while an existing CocosCreator.exe process is present.",
    ),
    source_path: Optional[Path] = typer.Option(None, "--source-path", help="Source brief/PDF/markdown for game pipelines."),
    pdf_path: Optional[Path] = typer.Option(None, "--pdf-path", help="Source PDF for Cocos game pipelines."),
    unified_brief_dir: Optional[Path] = typer.Option(None, "--unified-brief-dir", help="Prebuilt unified project brief bundle directory."),
    cocos_creator_exe: Optional[Path] = typer.Option(None, "--creator-exe", help="Cocos Creator executable for Cocos game pipelines."),
    cocos_output_dir: Optional[Path] = typer.Option(None, "--cocos-output-dir", help="Cocos project output directory."),
    require_build: bool = typer.Option(False, "--require-build", help="Require Cocos Creator build when executing Cocos stages."),
    require_playtest: bool = typer.Option(True, "--require-playtest/--skip-playtest", help="Run browser playtest after Cocos build."),
    require_commercial: bool = typer.Option(
        True,
        "--require-commercial/--allow-technical-smoke",
        help="Require commercial Cocos readiness when executing game pipeline templates.",
    ),
) -> None:
    resolved_creator_exe = discover_cocos_creator_exe(cocos_creator_exe) if (cocos_creator_exe is not None or require_build) else None
    payload = run_workflow_pipeline(
        _resolve_pipeline_goal(goal, template),
        workspace_root=_workspace_root_from_context(ctx),
        evidence_dir=evidence_dir,
        pipeline_id=pipeline_id,
        automation_lease_id=automation_lease_id,
        execute_capabilities=execute_capabilities,
        execute_agent_roles=execute_agent_roles,
        live_agent_roles=live_agent_roles,
        repair_loop=repair_loop,
        max_repair_attempts=max_repair_attempts,
        require_real_assets=require_real_assets,
        require_cocos_ecosystem=require_cocos_ecosystem,
        require_human_player_review=require_human_player_review,
        template=template,
        cocos_bridge_mode=cocos_bridge_mode,
        cocos_bridge_timeout_seconds=cocos_bridge_timeout_seconds,
        cocos_bridge_report_path=cocos_bridge_report_path,
        allow_existing_cocos_process=allow_existing_cocos_process,
        source_path=source_path or pdf_path,
        unified_brief_dir=unified_brief_dir,
        db_path=_db_path_from_context(ctx),
        creator_exe=resolved_creator_exe,
        output_dir=cocos_output_dir,
        require_build=require_build,
        require_playtest=require_playtest,
        require_commercial=require_commercial,
    )
    _emit_json(payload)
    if payload["status"] != "completed":
        raise typer.Exit(code=1)
