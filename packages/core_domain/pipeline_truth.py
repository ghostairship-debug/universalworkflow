from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from packages.contracts import PipelineStageKind, WorkflowPipeline


_EXECUTED_CAPABILITIES = {
    "cocos_asset_factory",
    "cocos_graph_pressure_test",
    "commercial_game_asset_generation",
    "commercial_game_task_card_worker",
}

_EXECUTED_VALIDATIONS = {
    "cocos_manifest_go_no_go",
    "commercial_game_production_go_no_go",
}


def build_pipeline_truth_report(pipeline: WorkflowPipeline) -> dict[str, Any]:
    """Report which pipeline stages are executable and which remain handoff points."""

    stages: list[dict[str, Any]] = []
    blocker_counts: Counter[str] = Counter()
    kind_counts: Counter[str] = Counter()
    executable_count = 0

    for stage in sorted(pipeline.stages, key=lambda item: item.order_index):
        stage_kind = str(stage.stage_kind)
        kind_counts[stage_kind] += 1
        truth = _stage_truth(stage_kind=stage_kind, metadata=stage.metadata, validation_commands=stage.validation_commands)
        if truth["execution_truth"] == "executable":
            executable_count += 1
        else:
            blocker_counts[truth["truth_blocker"]] += 1
        stages.append(
            {
                "stage_id": stage.stage_id,
                "name": stage.name,
                "order_index": stage.order_index,
                "stage_kind": stage_kind,
                "execution_truth": truth["execution_truth"],
                "truth_blocker": truth["truth_blocker"],
                "execution_owner": truth["execution_owner"],
                "recommended_next": truth["recommended_next"],
                "metadata": stage.metadata,
            }
        )

    non_executable = len(stages) - executable_count
    return {
        "schema_version": "m109_pipeline_truth_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "pipeline_id": pipeline.pipeline_id,
        "pipeline_name": pipeline.name,
        "template_id": pipeline.metadata.get("template_id"),
        "stage_count": len(stages),
        "executable_stage_count": executable_count,
        "non_executable_stage_count": non_executable,
        "stage_kind_counts": dict(sorted(kind_counts.items())),
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "go_no_go": "GO" if non_executable == 0 else "NO-GO",
        "cluster_execution_policy": {
            "cluster_semantics": "role_or_capability_template",
            "execution_backend": "langgraph_subgraph_when_upgraded",
            "legacy_cluster_runtime": "do_not_extend_as_new_execution_path",
        },
        "stages": stages,
    }


def _stage_truth(*, stage_kind: str, metadata: dict[str, Any], validation_commands: list[str]) -> dict[str, str | None]:
    if stage_kind == str(PipelineStageKind.capability):
        capability = str(metadata.get("capability") or "")
        if capability == "deprecated_cocos_template_removed":
            return {
                "execution_truth": "blocked",
                "truth_blocker": "legacy_cocos_template_removed",
                "execution_owner": "deprecation_guard",
                "recommended_next": "use_commercial_game_production_pipeline",
            }
        if capability in _EXECUTED_CAPABILITIES:
            return {
                "execution_truth": "executable",
                "truth_blocker": None,
                "execution_owner": "registered_capability_executor",
                "recommended_next": "run_with_execute_capabilities_when_inputs_are_available",
            }
        return {
            "execution_truth": "blocked",
            "truth_blocker": "capability_executor_not_registered",
            "execution_owner": None,
            "recommended_next": "register_capability_executor_or_keep_as_explicit_handoff",
        }
    if stage_kind == str(PipelineStageKind.validation_gate):
        validation = str(metadata.get("validation") or "")
        if validation in _EXECUTED_VALIDATIONS or validation_commands:
            return {
                "execution_truth": "executable",
                "truth_blocker": None,
                "execution_owner": "validation_executor_or_safe_command_runner",
                "recommended_next": "run_validation_gate_after_dependencies_complete",
            }
        return {
            "execution_truth": "blocked",
            "truth_blocker": "validation_executor_not_registered",
            "execution_owner": None,
            "recommended_next": "register_validation_executor_or_add_safe_validation_commands",
        }
    if stage_kind == str(PipelineStageKind.agent_role):
        if metadata.get("role_executor") == "single_agent_role_v1":
            return {
                "execution_truth": "executable",
                "truth_blocker": None,
                "execution_owner": "single_agent_role_executor",
                "recommended_next": "run_with_execute_agent_roles_for_m109_trial",
            }
        return {
            "execution_truth": "stubbed",
            "truth_blocker": "agent_role_executor_not_registered",
            "execution_owner": None,
            "recommended_next": "route_to_single_agent_role_executor_before_m109_trial_run",
        }
    if stage_kind == str(PipelineStageKind.cluster):
        return {
            "execution_truth": "stubbed",
            "truth_blocker": "cluster_is_template_not_execution_backend",
            "execution_owner": "future_langgraph_subgraph",
            "recommended_next": "downgrade_to_single_agent_or_upgrade_to_cluster_template_plus_subgraph",
        }
    return {
        "execution_truth": "blocked",
        "truth_blocker": "unsupported_stage_kind",
        "execution_owner": None,
        "recommended_next": "define_stage_executor_contract",
    }
