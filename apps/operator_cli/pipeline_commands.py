from __future__ import annotations

from typing import Optional

import typer

from apps.operator_cli.shared import _emit_json, _workspace_root_from_context
from packages.core_domain.pipeline import preview_workflow_pipeline, run_workflow_pipeline

pipeline_app = typer.Typer(help="WorkflowPipeline preview and serial execution commands.")


@pipeline_app.command("preview")
def pipeline_preview(
    goal: str = typer.Option(..., "--goal"),
    pipeline_id: Optional[str] = typer.Option(None, "--pipeline-id"),
) -> None:
    pipeline = preview_workflow_pipeline(goal, pipeline_id=pipeline_id)
    _emit_json(pipeline.model_dump(mode="json"))


@pipeline_app.command("run")
def pipeline_run(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal"),
    pipeline_id: Optional[str] = typer.Option(None, "--pipeline-id"),
    evidence_dir: Optional[str] = typer.Option(None, "--evidence-dir"),
) -> None:
    payload = run_workflow_pipeline(
        goal,
        workspace_root=_workspace_root_from_context(ctx),
        evidence_dir=evidence_dir,
        pipeline_id=pipeline_id,
    )
    _emit_json(payload)
