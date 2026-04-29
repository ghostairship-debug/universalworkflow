from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contracts import GraphCheckpointRecord, PipelineStage, PipelineStageKind, TaskKind, WorkflowPipeline
from packages.contracts.models import new_id
from packages.contributions.games.cocos.capabilities import judge_commercial_readiness_layers
from packages.contributions.games.cocos.e2e import discover_cocos_creator_exe
from packages.contributions.games.cocos.no_degradation import evaluate_no_degradation_contract
from packages.contributions.pipelines.m109_single_agent import (
    REAL_COMMERCIAL_GAME_PIPELINE_ID,
    commercial_game_production_stages,
    m109_single_agent_cocos_stages,
)
from packages.contributions.pipelines.commercial_game_production import (
    build_supervisor_repair_packets,
    execute_commercial_game_asset_generation,
    execute_commercial_game_task_card_worker,
)
from packages.core_domain.role_agent_executor import execute_single_agent_role_stage
from packages.runtime_integrations.cocos import generate_cocos_commercial_asset_manifest, run_cocos_game_e2e
from packages.runtime_langgraph.checkpoint_store import build_graph_repair_decision
from packages.runtime_langgraph.execution_kernel import run_artifact_only_graph


LEGACY_COMMERCIAL_COCOS_GAME_TEMPLATE = "commercial_cocos_game"
M109_SINGLE_AGENT_COCOS_TEMPLATE = "m109_single_agent_cocos"
COMMERCIAL_GAME_PRODUCTION_PIPELINE = REAL_COMMERCIAL_GAME_PIPELINE_ID


def preview_contribution_pipeline(
    goal: str,
    *,
    pipeline_id: str | None = None,
    template: str | None = None,
) -> WorkflowPipeline | None:
    template_id = _normalized_template(template)
    if template_id == LEGACY_COMMERCIAL_COCOS_GAME_TEMPLATE:
        stages = _deprecated_commercial_cocos_template_stages(template_id)
        name = "deprecated_commercial_cocos_game_pipeline"
    elif template_id == COMMERCIAL_GAME_PRODUCTION_PIPELINE:
        stages = commercial_game_production_stages(template_id)
        name = "commercial_game_production_pipeline"
    elif template_id == M109_SINGLE_AGENT_COCOS_TEMPLATE:
        stages = m109_single_agent_cocos_stages(template_id)
        name = "commercial_game_production_pipeline"
    elif _is_h5_game_goal(goal):
        stages = commercial_game_production_stages(COMMERCIAL_GAME_PRODUCTION_PIPELINE)
        name = "commercial_game_production_pipeline"
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
            "planning_modes": ["source_preserving_intake", "single_agent_role", "task_card_driven", "graph_backed_repair"],
            "direct_mutation_allowed": False,
            "template_id": template_id,
            "pipeline_recipe_id": template_id or (COMMERCIAL_GAME_PRODUCTION_PIPELINE if _is_h5_game_goal(goal) else None),
            "template_registry": "packages.contributions.pipelines",
            "fixed_template_delivery_allowed": False,
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
    require_real_assets: bool = False,
    require_cocos_ecosystem: bool = False,
    cocos_bridge_mode: str = "auto",
    cocos_bridge_timeout_seconds: int = 180,
    cocos_bridge_report_path: str | Path | None = None,
    allow_existing_cocos_process: bool = False,
    max_repair_attempts: int = 3,
    **_kwargs: Any,
) -> dict[str, Any]:
    resolved_creator_exe = discover_cocos_creator_exe(creator_exe) if (creator_exe is not None or require_build) else creator_exe
    if capability == "deprecated_cocos_template_removed":
        return {
            "handled": True,
            "result": {
                "status": "blocked",
                "failure_class": "legacy_cocos_template_removed",
                "execution_backend": "deprecation_guard",
                "output": {
                    "legacy_template": LEGACY_COMMERCIAL_COCOS_GAME_TEMPLATE,
                    "replacement_pipeline": COMMERCIAL_GAME_PRODUCTION_PIPELINE,
                    "reason": "The fixed Cocos template delivery path was removed because it can only prove technical smoke, not real commercial game production.",
                    "next_command": "workflowctl pipeline preview --goal \"完整中文版商业化小游戏\"",
                },
            },
            "pipeline_status": "blocked",
            "stop_reason": "legacy_cocos_template_removed",
        }
    if capability == "commercial_game_asset_generation":
        payload = execute_commercial_game_asset_generation(
            root=root,
            target_dir=target_dir,
            shared_outputs=shared_outputs,
            pipeline_id=str(_kwargs.get("pipeline_id") or stage.metadata.get("pipeline_recipe") or COMMERCIAL_GAME_PRODUCTION_PIPELINE),
            require_real_assets=require_real_assets,
            source_path=source_path,
            creator_exe=resolved_creator_exe,
            require_build=require_build,
        )
        return {
            "handled": True,
            "shared_outputs": payload.get("shared_outputs") or {},
            "result": {
                "status": payload["status"],
                "failure_class": payload["failure_class"],
                "execution_backend": payload["execution_backend"],
                "output": payload["output"],
            },
            "pipeline_status": "completed",
            "stop_reason": None,
        }
    if capability == "commercial_game_task_card_worker":
        payload = execute_commercial_game_task_card_worker(
            root=root,
            target_dir=target_dir,
            shared_outputs=shared_outputs,
            pipeline_id=str(_kwargs.get("pipeline_id") or stage.metadata.get("pipeline_recipe") or COMMERCIAL_GAME_PRODUCTION_PIPELINE),
            db_path=_kwargs.get("db_path"),
            source_path=source_path,
            creator_exe=resolved_creator_exe,
            output_dir=output_dir,
            require_build=require_build,
            require_playtest=require_playtest,
            require_commercial=require_commercial,
            require_cocos_ecosystem=require_cocos_ecosystem,
            cocos_bridge_mode=cocos_bridge_mode,
            cocos_bridge_timeout_seconds=cocos_bridge_timeout_seconds,
            cocos_bridge_report_path=cocos_bridge_report_path,
            allow_existing_cocos_process=allow_existing_cocos_process,
            max_repair_attempts=max_repair_attempts,
        )
        return {
            "handled": True,
            "shared_outputs": payload.get("shared_outputs") or {},
            "result": {
                "status": payload["status"],
                "failure_class": payload["failure_class"],
                "execution_backend": payload["execution_backend"],
                "output": payload["output"],
            },
            "pipeline_status": "completed" if payload["status"] == "completed" else payload["status"],
            "stop_reason": None if payload["status"] == "completed" else payload["failure_class"],
        }
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
        if not bool(stage.metadata.get("diagnostic_scaffold_allowed")):
            return {
                "handled": True,
                "result": {
                    "status": "blocked",
                    "failure_class": "cocos_scaffold_not_allowed_for_production_pipeline",
                    "execution_backend": "deprecation_guard",
                    "output": {
                        "capability": "cocos_creator_cli",
                        "reason": "The fixed Cocos scaffold generator is diagnostic-only in pipeline execution and cannot be used as a commercial game production worker.",
                        "replacement_pipeline": COMMERCIAL_GAME_PRODUCTION_PIPELINE,
                        "required_worker": "commercial_game_task_card_worker",
                    },
                },
                "pipeline_status": "blocked",
                "stop_reason": "cocos_scaffold_not_allowed_for_production_pipeline",
            }
        if source_path is None or resolved_creator_exe is None:
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
            creator_exe=resolved_creator_exe,
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


def execute_contribution_agent_role(
    *,
    stage: PipelineStage,
    root: Path,
    target_dir: Path,
    shared_outputs: dict[str, Any],
    source_path: str | Path | None = None,
    unified_brief_dir: str | Path | None = None,
    db_path: str | Path | None = None,
    pipeline_id: str | None = None,
    pipeline_goal: str | None = None,
    pipeline_template: str | None = None,
    pipeline_name: str | None = None,
    live_agent_roles: bool = False,
    repair_loop: bool = False,
    max_repair_attempts: int = 3,
    **_kwargs: Any,
) -> dict[str, Any]:
    if str(stage.metadata.get("role_executor") or "") != "single_agent_role_v1":
        return {"handled": False}
    payload = execute_single_agent_role_stage(
        stage,
        root=root,
        target_dir=target_dir,
        shared_outputs=shared_outputs,
        source_path=source_path,
        unified_brief_dir=unified_brief_dir,
        db_path=db_path,
        pipeline_id=pipeline_id,
        pipeline_goal=pipeline_goal,
        pipeline_template=pipeline_template,
        pipeline_name=pipeline_name,
        live_agent_roles=live_agent_roles,
    )
    if (
        payload.get("handled")
        and repair_loop
        and str(stage.metadata.get("role_id") or "") == "supervisor"
        and payload.get("result", {}).get("status") == "completed"
    ):
        output = dict(payload["result"].get("output") or {})
        structured = dict(output.get("structured_output") or {})
        repair_packets = build_supervisor_repair_packets(
            structured_output=structured,
            shared_outputs=shared_outputs,
            max_repair_attempts=max_repair_attempts,
        )
        structured["repair_packets"] = repair_packets
        structured["repair_loop_enabled"] = True
        output["structured_output"] = structured
        payload["result"]["output"] = output
        payload.setdefault("shared_outputs", {})["supervisor_repair_packets"] = repair_packets
    return payload


def execute_contribution_validation(
    validation: str,
    *,
    shared_outputs: dict[str, Any],
    require_commercial: bool = True,
    require_cocos_ecosystem: bool = False,
    require_live_agent_roles: bool = False,
    require_human_player_review: bool = False,
) -> dict[str, Any]:
    if validation == "commercial_game_production_go_no_go":
        production = shared_outputs.get("commercial_game_production")
        production_payload = production if isinstance(production, dict) else None
        no_degradation = evaluate_no_degradation_contract(
            shared_outputs=shared_outputs,
            production=production_payload,
            require_commercial=require_commercial,
            require_cocos_ecosystem=require_cocos_ecosystem,
            require_live_agent_roles=require_live_agent_roles,
            require_human_player_review=require_human_player_review,
        )
        gate_go = (
            isinstance(production, dict)
            and bool(production.get("commercial_playable_go"))
            and no_degradation["go_no_go"] == "GO"
        )
        blockers = []
        if not isinstance(production, dict):
            blockers.append("missing_real_game_production_evidence")
        elif not production.get("commercial_playable_go"):
            blockers.extend(production.get("commercial_playable_blockers") or ["commercial_playable_no_go"])
        blockers.extend(no_degradation["blockers"])
        blockers = list(dict.fromkeys(blockers))
        awaiting_human = blockers == ["awaiting_human_player_review"]
        return {
            "handled": True,
            "result": {
                "status": "completed" if gate_go else "blocked" if awaiting_human else "failed",
                "failure_class": None
                if gate_go
                else "awaiting_human_player_review"
                if awaiting_human
                else "commercial_game_no_degradation_failed",
                "output": {
                    "go_no_go": "GO" if gate_go else "NO-GO",
                    "required_gate": "real_commercial_playable_go",
                    "blockers": blockers,
                    "forbids_fixed_template": True,
                    "ecosystem_integration_go": no_degradation["ecosystem_integration_go"],
                    "live_role_provider_proof_go": no_degradation["live_role_provider_proof_go"],
                    "same_project_worker_patch_go": no_degradation["same_project_worker_patch_go"],
                    "human_player_review_go": no_degradation["human_player_review_go"],
                    "degradation_findings": no_degradation["degradation_findings"],
                    "no_degradation_contract": no_degradation,
                    "accepted_evidence": [
                        "real implemented feature flows",
                        "player-visible screenshots/playtest",
                        "working shop/levels/audio/animation/UI",
                        "incremental repair history on the same project",
                    ],
                },
            },
            "pipeline_status": "completed" if gate_go else "blocked" if awaiting_human else "failed",
            "stop_reason": None
            if gate_go
            else "awaiting_human_player_review"
            if awaiting_human
            else "commercial_game_no_degradation_failed",
        }
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
    if value in {LEGACY_COMMERCIAL_COCOS_GAME_TEMPLATE, "commercial_cocos", "cocos_commercial_game"}:
        return LEGACY_COMMERCIAL_COCOS_GAME_TEMPLATE
    if value in {COMMERCIAL_GAME_PRODUCTION_PIPELINE, "real_commercial_game", "cocos_production_pipeline"}:
        return COMMERCIAL_GAME_PRODUCTION_PIPELINE
    if value in {M109_SINGLE_AGENT_COCOS_TEMPLATE, "m109_cocos", "single_agent_cocos"}:
        return M109_SINGLE_AGENT_COCOS_TEMPLATE
    return value


def _deprecated_commercial_cocos_template_stages(template_id: str) -> list[PipelineStage]:
    return [
        _stage(
            name="Legacy Cocos template removed",
            kind=PipelineStageKind.capability,
            order_index=0,
            goal="Block the removed fixed-template Cocos pipeline and direct callers to the real task-card-driven production pipeline.",
            preset_id="advisory_delivery",
            task_kind=TaskKind.shell_exec,
            metadata={
                "planning_mode": "removed_legacy_template",
                "capability": "deprecated_cocos_template_removed",
                "template": template_id,
                "replacement_pipeline": COMMERCIAL_GAME_PRODUCTION_PIPELINE,
                "fixed_template_delivery_allowed": False,
            },
        )
    ]


def _h5_game_stages() -> list[PipelineStage]:
    return commercial_game_production_stages(COMMERCIAL_GAME_PRODUCTION_PIPELINE)


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
