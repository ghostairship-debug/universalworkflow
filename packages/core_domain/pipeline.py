from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from packages.contracts import PipelineStage, PipelineStageKind, TaskKind, WorkflowPipeline
from packages.contracts.models import new_id
from packages.core_domain.automation_lease import record_automation_lease_use, validate_automation_lease
from packages.core_domain.cocos_commercial_assets import generate_cocos_commercial_asset_manifest
from packages.core_domain.cocos_e2e import run_cocos_game_e2e


CommandRunner = Callable[[str, Path, int], dict[str, Any]]
COMMERCIAL_COCOS_GAME_TEMPLATE = "commercial_cocos_game"


def _stage(
    *,
    name: str,
    kind: PipelineStageKind,
    order_index: int,
    goal: str,
    preset_id: str | None = None,
    task_kind: TaskKind | None = None,
    adapter_name: str | None = None,
    depends_on: list[str] | None = None,
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
        depends_on=list(depends_on or []),
        write_set=list(write_set or []),
        validation_commands=list(validation_commands or []),
        metadata=metadata or {},
    )


def _is_h5_game_goal(goal: str) -> bool:
    normalized = goal.lower()
    markers = ("h5", "cocos", "1010", "game", "block puzzle", "小游戏", "游戏", "俄罗斯方块")
    return any(marker in normalized for marker in markers)


def _normalized_template(template: str | None) -> str | None:
    value = (template or "").strip().lower().replace("-", "_")
    if not value:
        return None
    if value in {COMMERCIAL_COCOS_GAME_TEMPLATE, "commercial_cocos", "cocos_commercial_game"}:
        return COMMERCIAL_COCOS_GAME_TEMPLATE
    return value


def _commercial_cocos_game_stages(template_id: str) -> list[PipelineStage]:
    intake = _stage(
        name="PDF/brief requirement mapping",
        kind=PipelineStageKind.agent_role,
        order_index=0,
        goal="Map the source PDF or brief into game requirements, commercial checks, and acceptance criteria.",
        preset_id="research_spike",
        task_kind=TaskKind.shell_exec,
        metadata={"planning_mode": "template", "direct_mutation_allowed": False, "template": template_id},
    )
    asset_factory = _stage(
        name="Commercial asset factory",
        kind=PipelineStageKind.capability,
        order_index=1,
        goal="Generate required commercial image, audio, music, voice, provenance, and QA assets.",
        preset_id="feature_delivery",
        task_kind=TaskKind.shell_exec,
        depends_on=[intake.stage_id],
        write_set=["state/pipeline_runs"],
        metadata={
            "planning_mode": "template",
            "capability": "cocos_asset_factory",
            "template": template_id,
            "required_for_go": True,
        },
    )
    cocos_generation = _stage(
        name="Cocos production generation",
        kind=PipelineStageKind.capability,
        order_index=2,
        goal="Generate, build, and optionally browser-playtest the Cocos Creator Web Mobile project.",
        preset_id="feature_delivery",
        task_kind=TaskKind.shell_exec,
        depends_on=[asset_factory.stage_id],
        write_set=["state/pipeline_runs"],
        metadata={
            "planning_mode": "manual",
            "capability": "cocos_creator_cli",
            "template": template_id,
            "requires_asset_factory_manifest": True,
        },
    )
    readiness_gate = _stage(
        name="Commercial readiness gate",
        kind=PipelineStageKind.validation_gate,
        order_index=3,
        goal="Validate technical build, commercial UI/assets, browser playtest, and final GO/NO-GO.",
        depends_on=[cocos_generation.stage_id],
        validation_commands=["workflowctl game cocos-e2e --require-commercial"],
        metadata={
            "planning_mode": "template",
            "direct_mutation_allowed": False,
            "validation": "cocos_manifest_go_no_go",
            "template": template_id,
        },
    )
    return [intake, asset_factory, cocos_generation, readiness_gate]


def preview_workflow_pipeline(
    goal: str,
    *,
    pipeline_id: str | None = None,
    template: str | None = None,
) -> WorkflowPipeline:
    template_id = _normalized_template(template)
    if template_id == COMMERCIAL_COCOS_GAME_TEMPLATE:
        stages = _commercial_cocos_game_stages(template_id)
        name = "commercial_cocos_game_pipeline"
    elif _is_h5_game_goal(goal):
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
                metadata={
                    "planning_mode": "template",
                    "direct_mutation_allowed": False,
                    "validation": "cocos_manifest_go_no_go",
                },
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
            "template_id": template_id,
        },
    )


def _stage_dir(root: Path, stage: PipelineStage) -> Path:
    return root / f"{stage.order_index:02d}_{stage.stage_id}"


def _write_stage_artifact(root: Path, stage: PipelineStage, payload: dict[str, Any]) -> str:
    directory = _stage_dir(root, stage)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "stage_result.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path.as_posix()


def _default_command_runner(command: str, cwd: Path, timeout_seconds: int) -> dict[str, Any]:
    started_at = datetime.now(UTC)
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return {
        "command": command,
        "cwd": cwd.as_posix(),
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-12000:],
        "stderr": completed.stderr[-12000:],
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
    }


def _command_result_for_error(command: str, cwd: Path, error: Exception) -> dict[str, Any]:
    return {
        "command": command,
        "cwd": cwd.as_posix(),
        "exit_code": 124 if isinstance(error, subprocess.TimeoutExpired) else 1,
        "stdout": getattr(error, "stdout", "") or "",
        "stderr": f"{type(error).__name__}: {error}",
        "finished_at": datetime.now(UTC).isoformat(),
    }


def run_workflow_pipeline(
    goal: str,
    *,
    workspace_root: str | Path,
    evidence_dir: str | Path | None = None,
    pipeline_id: str | None = None,
    automation_lease_id: str | None = None,
    execute_capabilities: bool = False,
    template: str | None = None,
    pdf_path: str | Path | None = None,
    cocos_creator_exe: str | Path | None = None,
    cocos_output_dir: str | Path | None = None,
    require_build: bool = False,
    require_playtest: bool = True,
    require_commercial: bool = True,
    command_runner: CommandRunner | None = None,
    command_timeout_seconds: int = 180,
) -> dict[str, Any]:
    pipeline = preview_workflow_pipeline(goal, pipeline_id=pipeline_id, template=template)
    root = Path(workspace_root).resolve()
    target_dir = Path(evidence_dir) if evidence_dir is not None else root / "state" / "pipeline_runs"
    target_dir.mkdir(parents=True, exist_ok=True)

    write_set = sorted({item for stage in pipeline.stages for item in stage.write_set})
    if automation_lease_id:
        validate_automation_lease(
            workspace_root=root,
            lease_id=automation_lease_id,
            action="pipeline_run",
            write_set=write_set,
        )

    results: list[dict[str, Any]] = []
    status_by_stage: dict[str, str] = {}
    pipeline_status = "completed"
    stop_reason: str | None = None
    runner = command_runner or _default_command_runner
    shared_outputs: dict[str, Any] = {}

    for stage in sorted(pipeline.stages, key=lambda item: item.order_index):
        dependency_statuses = [status_by_stage.get(stage_id) for stage_id in stage.depends_on]
        if any(status not in {"completed", "skipped"} for status in dependency_statuses):
            result = {
                "stage_id": stage.stage_id,
                "name": stage.name,
                "stage_kind": str(stage.stage_kind),
                "status": "skipped",
                "execution_mode": "serial",
                "failure_class": "dependency_not_completed",
                "write_set": stage.write_set,
                "validation_commands": stage.validation_commands,
                "metadata": stage.metadata,
            }
            result["evidence_path"] = _write_stage_artifact(target_dir, stage, result)
            results.append(result)
            status_by_stage[stage.stage_id] = "skipped"
            continue

        stage_kind = str(stage.stage_kind)
        result = {
            "stage_id": stage.stage_id,
            "name": stage.name,
            "stage_kind": stage_kind,
            "execution_mode": "serial",
            "write_set": stage.write_set,
            "validation_commands": stage.validation_commands,
            "metadata": stage.metadata,
        }

        if stage_kind in {str(PipelineStageKind.agent_role), str(PipelineStageKind.cluster)}:
            result.update(
                {
                    "status": "completed",
                    "execution_backend": "artifact_only_planning",
                    "output": {
                        "goal": stage.goal,
                        "direct_mutation_allowed": bool(stage.metadata.get("direct_mutation_allowed")),
                        "note": "Planning/review stage produced evidence only; it did not mutate the workspace.",
                    },
                }
            )
        elif stage_kind == str(PipelineStageKind.capability):
            capability = str(stage.metadata.get("capability") or "")
            if not execute_capabilities:
                result.update(
                    {
                        "status": "blocked",
                        "failure_class": "capability_execution_requires_explicit_enable",
                        "output": {
                            "required_flag": "execute_capabilities",
                            "note": "Capability stages are no longer marked completed unless they actually execute.",
                        },
                    }
                )
                pipeline_status = "blocked"
                stop_reason = "capability_stage_not_executed"
            elif capability == "cocos_asset_factory":
                commercial_assets = generate_cocos_commercial_asset_manifest(output_dir=target_dir / "commercial_asset_factory")
                shared_outputs["commercial_assets"] = commercial_assets
                go_no_go = commercial_assets.get("go_no_go")
                result.update(
                    {
                        "status": "completed" if go_no_go == "GO" else "failed",
                        "failure_class": None if go_no_go == "GO" else "asset_factory_no_go",
                        "execution_backend": "asset_factory",
                        "output": {
                            "manifest_path": commercial_assets.get("manifest_path"),
                            "go_no_go": go_no_go,
                            "blockers": commercial_assets.get("blockers", []),
                            "feature_coverage": commercial_assets.get("feature_coverage", {}),
                        },
                    }
                )
                if go_no_go != "GO":
                    pipeline_status = "failed"
                    stop_reason = "asset_factory_no_go"
            elif capability == "cocos_creator_cli":
                if pdf_path is None or cocos_creator_exe is None:
                    result.update(
                        {
                            "status": "blocked",
                            "failure_class": "cocos_execution_missing_inputs",
                            "output": {
                                "required_inputs": ["pdf_path", "cocos_creator_exe"],
                            },
                        }
                    )
                    pipeline_status = "blocked"
                    stop_reason = "cocos_inputs_missing"
                else:
                    output_dir = cocos_output_dir or root / "state" / "pipeline_runs" / pipeline.pipeline_id / "cocos_project"
                    commercial_assets = shared_outputs.get("commercial_assets")
                    cocos_payload = run_cocos_game_e2e(
                        pdf_path=pdf_path,
                        output_dir=output_dir,
                        creator_exe=cocos_creator_exe,
                        require_build=require_build,
                        require_playtest=require_playtest,
                        require_commercial=require_commercial,
                        generate_commercial_assets=commercial_assets is None,
                        commercial_assets_payload=commercial_assets if isinstance(commercial_assets, dict) else None,
                    )
                    shared_outputs["cocos_e2e"] = cocos_payload
                    go_no_go = cocos_payload["manifest"]["go_no_go"]
                    result.update(
                        {
                            "status": "completed" if go_no_go == "GO" else "failed",
                            "failure_class": None if go_no_go == "GO" else "cocos_e2e_no_go",
                            "output": {
                                "manifest_path": cocos_payload["manifest_path"],
                                "go_no_go": go_no_go,
                                "blockers": cocos_payload["manifest"].get("blockers", []),
                            },
                        }
                    )
                    if go_no_go != "GO":
                        pipeline_status = "failed"
                        stop_reason = "cocos_e2e_no_go"
            else:
                result.update(
                    {
                        "status": "blocked",
                        "failure_class": "unsupported_capability_stage",
                        "output": {
                            "capability": capability or None,
                            "note": "No real executor is registered for this capability stage.",
                        },
                    }
                )
                pipeline_status = "blocked"
                stop_reason = "unsupported_capability_stage"
        elif stage_kind == str(PipelineStageKind.validation_gate):
            if stage.metadata.get("validation") == "cocos_manifest_go_no_go":
                cocos_payload = shared_outputs.get("cocos_e2e")
                go_no_go = (cocos_payload or {}).get("manifest", {}).get("go_no_go")
                result.update(
                    {
                        "status": "completed" if go_no_go == "GO" else "failed",
                        "failure_class": None if go_no_go == "GO" else "cocos_validation_failed",
                        "output": {
                            "go_no_go": go_no_go,
                            "manifest_path": (cocos_payload or {}).get("manifest_path"),
                            "blockers": (cocos_payload or {}).get("manifest", {}).get("blockers", []),
                            "commercial_go_no_go": (cocos_payload or {}).get("commercial_go_no_go"),
                            "commercial_blockers": (cocos_payload or {}).get("commercial_blockers", []),
                        },
                    }
                )
                if go_no_go != "GO":
                    pipeline_status = "failed" if pipeline_status == "completed" else pipeline_status
                    stop_reason = stop_reason or "cocos_validation_failed"
            else:
                command_results: list[dict[str, Any]] = []
                failed = False
                for command in stage.validation_commands:
                    try:
                        command_result = runner(command, root, command_timeout_seconds)
                    except Exception as exc:
                        command_result = _command_result_for_error(command, root, exc)
                    command_results.append(command_result)
                    if int(command_result.get("exit_code") or 0) != 0:
                        failed = True
                        break
                result.update(
                    {
                        "status": "failed" if failed else "completed",
                        "failure_class": "validation_command_failed" if failed else None,
                        "output": {"command_results": command_results},
                    }
                )
                if failed:
                    pipeline_status = "failed"
                    stop_reason = "validation_command_failed"
        else:
            result.update(
                {
                    "status": "blocked",
                    "failure_class": "unsupported_stage_kind",
                    "output": {"stage_kind": stage_kind},
                }
            )
            pipeline_status = "blocked"
            stop_reason = "unsupported_stage_kind"

        result["evidence_path"] = _write_stage_artifact(target_dir, stage, result)
        results.append(result)
        status_by_stage[stage.stage_id] = result["status"]
        if result["status"] in {"failed", "blocked"}:
            for downstream in sorted(pipeline.stages, key=lambda item: item.order_index):
                if downstream.order_index <= stage.order_index:
                    continue
                skipped = {
                    "stage_id": downstream.stage_id,
                    "name": downstream.name,
                    "stage_kind": str(downstream.stage_kind),
                    "status": "skipped",
                    "execution_mode": "serial",
                    "failure_class": "previous_stage_not_completed",
                    "write_set": downstream.write_set,
                    "validation_commands": downstream.validation_commands,
                    "metadata": downstream.metadata,
                }
                skipped["evidence_path"] = _write_stage_artifact(target_dir, downstream, skipped)
                results.append(skipped)
                status_by_stage[downstream.stage_id] = "skipped"
            break

    payload = {
        "pipeline": pipeline.model_dump(mode="json"),
        "stage_results": results,
        "status": pipeline_status,
        "stop_reason": stop_reason,
        "executed_at": datetime.now(UTC).isoformat(),
        "execution_semantics": "real_stage_execution_with_short_circuit",
    }
    output = target_dir / f"{pipeline.pipeline_id}.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["evidence_path"] = output.as_posix()
    if automation_lease_id:
        record_automation_lease_use(root, automation_lease_id, action="pipeline_run")
    return payload
