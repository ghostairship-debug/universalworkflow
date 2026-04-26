from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from apps.operator_cli.shared import _emit_json, _workspace_root_from_context
from packages.core_domain.pipeline import preview_workflow_pipeline, run_workflow_pipeline

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
    pdf_path: Optional[Path] = typer.Option(None, "--pdf-path", help="Source PDF for Cocos game pipelines."),
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
    payload = run_workflow_pipeline(
        _resolve_pipeline_goal(goal, template),
        workspace_root=_workspace_root_from_context(ctx),
        evidence_dir=evidence_dir,
        pipeline_id=pipeline_id,
        automation_lease_id=automation_lease_id,
        execute_capabilities=execute_capabilities,
        template=template,
        pdf_path=pdf_path,
        cocos_creator_exe=cocos_creator_exe,
        cocos_output_dir=cocos_output_dir,
        require_build=require_build,
        require_playtest=require_playtest,
        require_commercial=require_commercial,
    )
    _emit_json(payload)
    if payload["status"] != "completed":
        raise typer.Exit(code=1)
