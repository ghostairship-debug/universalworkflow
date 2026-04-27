from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.contracts import WorkflowPipeline
from packages.core_domain.pipeline import run_workflow_pipeline as run_core_workflow_pipeline
from packages.core_domain.pipeline import preview_workflow_pipeline as preview_core_workflow_pipeline
from packages.contributions.pipelines.registry import (
    execute_contribution_capability,
    execute_contribution_validation,
    preview_contribution_pipeline,
)


def preview_workflow_pipeline(
    goal: str,
    *,
    pipeline_id: str | None = None,
    template: str | None = None,
) -> WorkflowPipeline:
    contribution = preview_contribution_pipeline(goal, pipeline_id=pipeline_id, template=template)
    if contribution is not None:
        return contribution
    return preview_core_workflow_pipeline(goal, pipeline_id=pipeline_id, template=template)


def run_workflow_pipeline(
    goal: str,
    *,
    workspace_root: str | Path,
    evidence_dir: str | Path | None = None,
    pipeline_id: str | None = None,
    automation_lease_id: str | None = None,
    execute_capabilities: bool = False,
    template: str | None = None,
    source_path: str | Path | None = None,
    creator_exe: str | Path | None = None,
    output_dir: str | Path | None = None,
    require_build: bool = False,
    require_playtest: bool = True,
    require_commercial: bool = True,
    command_runner: Any | None = None,
    command_timeout_seconds: int = 180,
) -> dict[str, Any]:
    return run_core_workflow_pipeline(
        goal,
        workspace_root=workspace_root,
        evidence_dir=evidence_dir,
        pipeline_id=pipeline_id,
        automation_lease_id=automation_lease_id,
        execute_capabilities=execute_capabilities,
        template=template,
        require_build=require_build,
        require_playtest=require_playtest,
        require_commercial=require_commercial,
        command_runner=command_runner,
        command_timeout_seconds=command_timeout_seconds,
        pipeline_previewer=preview_workflow_pipeline,
        capability_executor=execute_contribution_capability,
        validation_executor=execute_contribution_validation,
        capability_inputs={
            "source_path": source_path,
            "creator_exe": creator_exe,
            "output_dir": output_dir,
        },
    )
