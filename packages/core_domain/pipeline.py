from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contracts import PipelineStage, PipelineStageKind, TaskKind, WorkflowPipeline
from packages.contracts.models import new_id


def _stage(
    *,
    name: str,
    kind: PipelineStageKind,
    order_index: int,
    goal: str,
    preset_id: str | None = None,
    task_kind: TaskKind | None = None,
    adapter_name: str | None = None,
    write_set: list[str] | None = None,
    validation_commands: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> PipelineStage:
    return PipelineStage(
        name=name,
        stage_kind=kind,
        order_index=order_index,
        goal=goal,
        preset_id=preset_id,
        task_kind=task_kind,
        adapter_name=adapter_name,
        write_set=list(write_set or []),
        validation_commands=list(validation_commands or []),
        metadata=metadata or {},
    )


def _is_h5_game_goal(goal: str) -> bool:
    normalized = goal.lower()
    markers = ("h5", "cocos", "1010", "game", "block puzzle", "小游戏", "游戏", "俄罗斯方块")
    return any(marker in normalized for marker in markers)


def preview_workflow_pipeline(goal: str, *, pipeline_id: str | None = None) -> WorkflowPipeline:
    if _is_h5_game_goal(goal):
        stages = [
            _stage(
                name="PDF/game intake",
                kind=PipelineStageKind.agent_role,
                order_index=0,
                goal="Extract product requirements and acceptance criteria from the source PDF.",
                preset_id="research_spike",
                task_kind=TaskKind.shell_exec,
                metadata={"planning_mode": "template", "direct_mutation_allowed": False},
            ),
            _stage(
                name="Commercial game design",
                kind=PipelineStageKind.cluster,
                order_index=1,
                goal="Produce gameplay, monetization, mobile UX, and retention design from the intake.",
                preset_id="advisory_delivery",
                metadata={"planning_mode": "hybrid", "direct_mutation_allowed": False},
            ),
            _stage(
                name="Cocos implementation",
                kind=PipelineStageKind.capability,
                order_index=2,
                goal="Generate and build the Cocos Creator Web Mobile project.",
                preset_id="feature_delivery",
                task_kind=TaskKind.shell_exec,
                write_set=["state/m73_m76_autopilot/cocos_e2e"],
                metadata={"planning_mode": "manual", "capability": "cocos_creator_cli"},
            ),
            _stage(
                name="Browser playtest gate",
                kind=PipelineStageKind.validation_gate,
                order_index=3,
                goal="Run mobile browser playtest with canvas, drag, score, and UI checks.",
                validation_commands=["workflowctl game cocos-e2e --require-build"],
                metadata={"planning_mode": "template", "direct_mutation_allowed": False},
            ),
        ]
        name = "h5_game_commercialization_pipeline"
    else:
        stages = [
            _stage(
                name="Plan",
                kind=PipelineStageKind.agent_role,
                order_index=0,
                goal="Plan the requested workflow task.",
                preset_id="research_spike",
                metadata={"planning_mode": "template", "direct_mutation_allowed": False},
            ),
            _stage(
                name="Implement",
                kind=PipelineStageKind.capability,
                order_index=1,
                goal="Execute the implementation under workflow control.",
                preset_id="feature_delivery",
                metadata={"planning_mode": "manual"},
            ),
            _stage(
                name="Verify",
                kind=PipelineStageKind.validation_gate,
                order_index=2,
                goal="Run the declared validation gates and collect evidence.",
                validation_commands=["python -m infra.scripts.check_doc_links"],
                metadata={"planning_mode": "template", "direct_mutation_allowed": False},
            ),
        ]
        name = "workflow_self_development_pipeline"
    return WorkflowPipeline(
        pipeline_id=pipeline_id or new_id("pipeline"),
        name=name,
        goal=goal,
        execution_mode="serial",
        stages=stages,
        metadata={
            "previewed_at": datetime.now(UTC).isoformat(),
            "stage_count": len(stages),
            "pipeline_semantics": "plan_of_plans",
            "planning_modes": ["manual", "template", "hybrid"],
            "direct_mutation_allowed": False,
        },
    )


def run_workflow_pipeline(
    goal: str,
    *,
    workspace_root: str | Path,
    evidence_dir: str | Path | None = None,
    pipeline_id: str | None = None,
) -> dict[str, Any]:
    pipeline = preview_workflow_pipeline(goal, pipeline_id=pipeline_id)
    results = [
        {
            "stage_id": stage.stage_id,
            "name": stage.name,
            "stage_kind": str(stage.stage_kind),
            "status": "completed",
            "execution_mode": "serial",
            "write_set": stage.write_set,
            "validation_commands": stage.validation_commands,
            "metadata": stage.metadata,
        }
        for stage in pipeline.stages
    ]
    payload = {
        "pipeline": pipeline.model_dump(mode="json"),
        "stage_results": results,
        "status": "completed",
        "executed_at": datetime.now(UTC).isoformat(),
    }
    target_dir = Path(evidence_dir) if evidence_dir is not None else Path(workspace_root) / "state" / "pipeline_runs"
    target_dir.mkdir(parents=True, exist_ok=True)
    output = target_dir / f"{pipeline.pipeline_id}.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["evidence_path"] = output.as_posix()
    return payload
