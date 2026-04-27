from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contracts import GraphCheckpointRecord, PipelineStage, PipelineStageKind, TaskKind, WorkflowPipeline
from packages.contracts.models import new_id
from packages.contributions.games.cocos.capabilities import judge_commercial_readiness_layers
from packages.runtime_integrations.cocos import generate_cocos_commercial_asset_manifest, run_cocos_game_e2e
from packages.runtime_langgraph.checkpoint_store import build_graph_repair_decision
from packages.runtime_langgraph.execution_kernel import run_artifact_only_graph


COMMERCIAL_COCOS_GAME_TEMPLATE = "commercial_cocos_game"


def preview_contribution_pipeline(
    goal: str,
    *,
    pipeline_id: str | None = None,
    template: str | None = None,
) -> WorkflowPipeline | None:
    template_id = _normalized_template(template)
    if template_id == COMMERCIAL_COCOS_GAME_TEMPLATE:
        stages = _commercial_cocos_game_stages(template_id)
        name = "commercial_cocos_game_pipeline"
    elif _is_h5_game_goal(goal):
        stages = _h5_game_stages()
        name = "h5_game_commercialization_pipeline"
    else:
        return None
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
            "template_registry": "packages.contributions.pipelines",
        },
    )


def execute_contribution_capability(
    capability: str,
    *,
    stage: PipelineStage,
    root: Path,
    target_dir: Path,
    shared_outputs: dict[str, Any],
    source_path: str | Path | None = None,
    creator_exe: str | Path | None = None,
    output_dir: str | Path | None = None,
    require_build: bool = False,
    require_playtest: bool = True,
    require_commercial: bool = True,
) -> dict[str, Any]:
    if capability == "cocos_asset_factory":
        commercial_assets = generate_cocos_commercial_asset_manifest(output_dir=target_dir / "commercial_asset_factory")
        go_no_go = commercial_assets.get("go_no_go")
        return {
            "handled": True,
            "shared_outputs": {"commercial_assets": commercial_assets},
            "result": {
                "status": "completed" if go_no_go == "GO" else "failed",
                "failure_class": None if go_no_go == "GO" else "asset_factory_no_go",
                "execution_backend": "asset_factory",
                "output": {
                    "manifest_path": commercial_assets.get("manifest_path"),
                    "go_no_go": go_no_go,
                    "blockers": commercial_assets.get("blockers", []),
                    "feature_coverage": commercial_assets.get("feature_coverage", {}),
                },
            },
            "pipeline_status": "completed" if go_no_go == "GO" else "failed",
            "stop_reason": None if go_no_go == "GO" else "asset_factory_no_go",
        }
    if capability == "cocos_graph_pressure_test":
        graph_payload = run_artifact_only_graph(
            goal=stage.goal,
            workspace_root=root,
            evidence_dir=target_dir / "cocos_graph_pressure",
            preset_id=stage.preset_id,
            phase_id="M105.0",
        )
        checkpoint_payload = graph_payload.get("persistent_checkpoint") or {}
        repair_decision = None
        if checkpoint_payload:
            repair_decision = build_graph_repair_decision(
                checkpoint=GraphCheckpointRecord.model_validate(checkpoint_payload),
                failure_class=graph_payload.get("failure_class"),
            ).model_dump(mode="json")
        graph_completed = graph_payload.get("status") == "completed"
        return {
            "handled": True,
            "shared_outputs": {"cocos_graph_pressure": graph_payload},
            "result": {
                "status": "completed" if graph_completed else "failed",
                "failure_class": None if graph_completed else graph_payload.get("failure_class") or "cocos_graph_pressure_failed",
                "execution_backend": "langgraph_artifact_only_kernel",
                "output": {
                    "graph_status": graph_payload.get("status"),
                    "graph_evidence_path": graph_payload.get("evidence_path"),
                    "graph_state_path": graph_payload.get("graph_state_path"),
                    "persistent_checkpoint": checkpoint_payload,
                    "repair_decision": repair_decision,
                    "commercial_claim": "pressure_test_only_not_commercial_ready",
                },
            },
            "pipeline_status": "completed" if graph_completed else "failed",
            "stop_reason": None if graph_completed else "cocos_graph_pressure_failed",
        }
    if capability == "cocos_creator_cli":
        if source_path is None or creator_exe is None:
            return {
                "handled": True,
                "result": {
                    "status": "blocked",
                    "failure_class": "cocos_execution_missing_inputs",
                    "output": {"required_inputs": ["pdf_path", "creator_exe"]},
                },
                "pipeline_status": "blocked",
                "stop_reason": "cocos_inputs_missing",
            }
        project_output_dir = output_dir or root / "state" / "pipeline_runs" / stage.stage_id / "cocos_project"
        commercial_assets = shared_outputs.get("commercial_assets")
        payload = run_cocos_game_e2e(
            pdf_path=source_path,
            output_dir=project_output_dir,
            creator_exe=creator_exe,
            require_build=require_build,
            require_playtest=require_playtest,
            require_commercial=require_commercial,
            generate_commercial_assets=commercial_assets is None,
            commercial_assets_payload=commercial_assets if isinstance(commercial_assets, dict) else None,
        )
        go_no_go = payload["manifest"]["go_no_go"]
        return {
            "handled": True,
            "shared_outputs": {"cocos_e2e": payload},
            "result": {
                "status": "completed" if go_no_go == "GO" else "failed",
                "failure_class": None if go_no_go == "GO" else "cocos_e2e_no_go",
                "output": {
                    "manifest_path": payload["manifest_path"],
                    "go_no_go": go_no_go,
                    "blockers": payload["manifest"].get("blockers", []),
                    "commercial_readiness": _cocos_readiness(payload),
                },
            },
            "pipeline_status": "completed" if go_no_go == "GO" else "failed",
            "stop_reason": None if go_no_go == "GO" else "cocos_e2e_no_go",
        }
    return {"handled": False}


def execute_contribution_validation(
    validation: str,
    *,
    shared_outputs: dict[str, Any],
    require_commercial: bool = True,
) -> dict[str, Any]:
    if validation != "cocos_manifest_go_no_go":
        return {"handled": False}
    payload = shared_outputs.get("cocos_e2e")
    go_no_go = (payload or {}).get("manifest", {}).get("go_no_go")
    readiness = _cocos_readiness(payload if isinstance(payload, dict) else None)
    gate_go = bool(readiness["commercial_playable_go"] if require_commercial else readiness["technical_smoke_go"])
    return {
        "handled": True,
        "result": {
            "status": "completed" if gate_go else "failed",
            "failure_class": None if gate_go else "cocos_validation_failed",
            "output": {
                "go_no_go": go_no_go,
                "manifest_path": (payload or {}).get("manifest_path"),
                "blockers": (payload or {}).get("manifest", {}).get("blockers", []),
                "commercial_go_no_go": (payload or {}).get("commercial_go_no_go"),
                "commercial_blockers": (payload or {}).get("commercial_blockers", []),
                "commercial_readiness": readiness,
                "required_gate": "commercial_playable_go" if require_commercial else "technical_smoke_go",
            },
        },
        "pipeline_status": "completed" if gate_go else "failed",
        "stop_reason": None if gate_go else "cocos_validation_failed",
    }


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
    graph_pressure = _stage(
        name="Cocos graph pressure preflight",
        kind=PipelineStageKind.capability,
        order_index=1,
        goal="Run a small Cocos improvement planning artifact through the graph checkpoint and repair path.",
        preset_id="advisory_delivery",
        task_kind=TaskKind.shell_exec,
        write_set=["state/pipeline_runs"],
        metadata={
            "planning_mode": "graph_backed",
            "capability": "cocos_graph_pressure_test",
            "template": template_id,
            "graph_backed": True,
            "side_effect_level": "artifact_only",
        },
    )
    asset_factory = _stage(
        name="Commercial asset factory",
        kind=PipelineStageKind.capability,
        order_index=2,
        goal="Generate required commercial image, audio, music, voice, provenance, and QA assets.",
        preset_id="feature_delivery",
        task_kind=TaskKind.shell_exec,
        depends_on=[graph_pressure.stage_id],
        write_set=["state/pipeline_runs"],
        metadata={
            "planning_mode": "template",
            "capability": "cocos_asset_factory",
            "template": template_id,
            "required_for_go": True,
        },
    )
    production = _stage(
        name="Cocos production generation",
        kind=PipelineStageKind.capability,
        order_index=3,
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
        order_index=4,
        goal="Validate technical build, commercial UI/assets, browser playtest, and final GO/NO-GO.",
        depends_on=[production.stage_id],
        validation_commands=["workflowctl game cocos-e2e --require-commercial"],
        metadata={
            "planning_mode": "template",
            "direct_mutation_allowed": False,
            "validation": "cocos_manifest_go_no_go",
            "template": template_id,
        },
    )
    return [intake, graph_pressure, asset_factory, production, readiness_gate]


def _h5_game_stages() -> list[PipelineStage]:
    return [
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


def _cocos_readiness(cocos_payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = cocos_payload or {}
    manifest = payload.get("manifest") or {}
    metadata = manifest.get("metadata") or {}
    commercial_feature_coverage = (
        payload.get("commercial_feature_coverage")
        or metadata.get("commercial_feature_coverage")
        or {}
    )
    commercial_blockers = list(payload.get("commercial_blockers") or metadata.get("commercial_blockers") or [])
    technical_smoke_go = manifest.get("go_no_go") == "GO"
    production_scaffold_go = bool(
        payload.get("production_scaffold_go")
        or metadata.get("production_scaffold_go")
        or payload.get("commercial_go_no_go") == "GO"
        or metadata.get("commercial_go_no_go") == "GO"
    )
    readiness = judge_commercial_readiness_layers(
        technical_smoke=technical_smoke_go,
        production_scaffold=production_scaffold_go,
        player_visible_checks=payload.get("player_visible_checks") or metadata.get("player_visible_checks") or {},
        manual_player_evidence=payload.get("manual_player_evidence") or metadata.get("manual_player_evidence") or {},
    )
    return {
        **readiness,
        "commercial_go_no_go": "GO" if readiness["commercial_playable_go"] else "NO-GO",
        "commercial_blockers": commercial_blockers,
        "commercial_feature_coverage": commercial_feature_coverage,
    }
