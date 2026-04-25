from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import sys

from packages.contracts import (
    CapabilityRoute,
    DomainPackResolution,
    ExecutionLaneType,
    HandoffLite,
    MemoryRetrievalPreview,
    MCPServerProfile,
    MutationContract,
    MutationMode,
    Phase,
    PresetDefinition,
    ResolvedExecutionProfile,
    RuntimeTask,
    TaskCard,
    TaskKind,
    TaskPacket,
    ToolProjectionManifest,
)
from packages.core_domain.capability_plane import TOOL_PROJECTION_MANIFEST_ENV_KEY, dump_tool_projection_manifest
from packages.core_domain.domain_packs import DOMAIN_PACK_RESOLUTION_ENV_KEY, dump_domain_pack_resolution
from packages.contributions.games.local_game_artifacts import local_artifacts_for_goal
from packages.core_domain.memory import MEMORY_RETRIEVAL_PREVIEW_ENV_KEY, dump_memory_retrieval_preview


def build_artifact_content(
    *,
    preset_id: str,
    goal: str,
    adapter_name: str,
    domain_pack_id: str | None = None,
    domain_pack_operator_label: str | None = None,
    domain_pack_capability_tags: list[str] | None = None,
    domain_pack_evidence_expectations: list[str] | None = None,
    domain_pack_artifact_context_lines: list[str] | None = None,
    memory_item_ids: list[str] | None = None,
    memory_brief_lines: list[str] | None = None,
    runtime_gateway: str | None = None,
    runtime_model: str | None = None,
    runtime_brief: str | None = None,
    execution_lane: str | None = None,
    projected_tools: list[str] | None = None,
) -> str:
    lines = [f"preset: {preset_id}"]
    if domain_pack_id:
        lines.append(f"domain_pack: {domain_pack_id}")
    if domain_pack_operator_label:
        lines.append(f"domain_pack_operator_label: {domain_pack_operator_label}")
    if domain_pack_capability_tags:
        lines.append(f"domain_pack_capability_tags: {','.join(domain_pack_capability_tags)}")
    if domain_pack_evidence_expectations:
        lines.append(f"domain_pack_evidence_expectations: {','.join(domain_pack_evidence_expectations)}")
    if adapter_name:
        lines.append(f"adapter: {adapter_name}")
    lines.append(f"goal: {goal}")
    if runtime_gateway:
        lines.append(f"runtime_gateway: {runtime_gateway}")
    if runtime_model:
        lines.append(f"runtime_model: {runtime_model}")
    if runtime_brief:
        lines.append(f"runtime_brief: {runtime_brief}")
    if execution_lane:
        lines.append(f"execution_lane: {execution_lane}")
    if projected_tools:
        lines.append(f"projected_tools: {','.join(projected_tools)}")
    if memory_item_ids:
        lines.append(f"memory_item_ids: {','.join(memory_item_ids)}")
    if memory_brief_lines:
        for brief_line in memory_brief_lines:
            lines.append(f"memory_brief: {brief_line}")
    if domain_pack_artifact_context_lines:
        lines.extend(domain_pack_artifact_context_lines)
    return "\n".join(lines) + "\n"


def _artifact_path_for(run_id: str, preset_id: str, domain_pack: DomainPackResolution | None = None) -> Path:
    suffix = f"_{domain_pack.compile_projection.artifact_label}" if domain_pack is not None else ""
    return Path("state") / "artifacts" / f"{run_id}_{preset_id}{suffix}.md"


def _mutation_artifact_path_for(run_id: str, preset_id: str) -> Path:
    return Path("state") / "artifacts" / f"{run_id}_{preset_id}_mutation.patch"


def _python_command_for(
    goal: str,
    preset_id: str,
    artifact_path: Path,
    *,
    domain_pack: DomainPackResolution | None = None,
    capability_route: CapabilityRoute | None = None,
    execution_lane: ExecutionLaneType | None = None,
    tool_projection_manifest: ToolProjectionManifest | None = None,
) -> list[str]:
    effective_goal = (
        f"{domain_pack.compile_projection.goal_prefix} {goal}"
        if domain_pack is not None and domain_pack.compile_projection.goal_prefix
        else goal
    )
    body = (
        "import os\n"
        "import json\n"
        "from pathlib import Path\n"
        "from packages.core_domain.compile import build_artifact_content\n"
        f"path = Path(r'{artifact_path.as_posix()}')\n"
        "path.parent.mkdir(parents=True, exist_ok=True)\n"
        "memory_preview = os.environ.get('WORKFLOW_MEMORY_RETRIEVAL_PREVIEW')\n"
        "memory_preview = json.loads(memory_preview) if memory_preview else None\n"
        "tool_projection = json.loads(os.environ.get('WORKFLOW_TOOL_PROJECTION_MANIFEST', '{}') or '{}')\n"
        "projected_tools = [item.get('tool_name') for item in (tool_projection.get('tools') or [])]\n"
        f"content = build_artifact_content(preset_id={preset_id!r}, goal={effective_goal!r}, "
        f"adapter_name={(capability_route.adapter_name if capability_route is not None else '')!r}, "
        f"domain_pack_id={(domain_pack.domain_pack_id if domain_pack is not None else None)!r}, "
        f"domain_pack_operator_label={(domain_pack.runtime_projection.operator_label if domain_pack is not None else None)!r}, "
        f"domain_pack_capability_tags={(domain_pack.capability_exposure.capability_tags if domain_pack is not None else None)!r}, "
        f"domain_pack_evidence_expectations={(domain_pack.runtime_projection.evidence_expectations if domain_pack is not None else None)!r}, "
        f"domain_pack_artifact_context_lines={(domain_pack.compile_projection.artifact_context_lines if domain_pack is not None else None)!r}, "
        "memory_item_ids=(memory_preview.get('selected_memory_item_ids') if memory_preview else None), "
        "memory_brief_lines=(memory_preview.get('brief_lines') if memory_preview else None), "
        "runtime_gateway=os.environ.get('WORKFLOW_RUNTIME_GATEWAY_PROVIDER'), "
        "runtime_model=os.environ.get('WORKFLOW_LLM_MODEL'), "
        "runtime_brief=os.environ.get('WORKFLOW_RUNTIME_BRIEF'), "
        f"execution_lane={(str(execution_lane) if execution_lane is not None else None)!r}, "
        "projected_tools=projected_tools"
        ")\n"
        "path.write_text(content, encoding='utf-8')\n"
        "from packages.contributions.games.local_game_artifacts import local_artifacts_for_goal\n"
        "for local_path, local_content in local_artifacts_for_goal("
        f"{effective_goal!r}"
        "):\n"
        "    local_target = Path(local_path)\n"
        "    local_target.parent.mkdir(parents=True, exist_ok=True)\n"
        "    local_target.write_text(local_content, encoding='utf-8')\n"
        "    print(local_target.as_posix())\n"
        "print(path.as_posix())\n"
    )
    return [sys.executable, "-c", body]


@dataclass(slots=True)
class CompileSnapshot:
    compile_phase: Phase
    execution_phase: Phase
    handoff: HandoffLite
    task_card: TaskCard
    runtime_task: RuntimeTask
    task_packet: TaskPacket
    domain_pack: DomainPackResolution | None
    capability_route: CapabilityRoute | None
    memory_preview: MemoryRetrievalPreview | None
    execution_lane: ExecutionLaneType
    resolved_execution: ResolvedExecutionProfile
    tool_projection_manifest: ToolProjectionManifest | None
    mcp_server_profiles: list[MCPServerProfile]


def compile_run(
    goal: str,
    preset: PresetDefinition,
    run_id: str,
    working_directory: str = ".",
    task_kind: TaskKind | str | None = None,
    domain_pack: DomainPackResolution | None = None,
    capability_route: CapabilityRoute | None = None,
    memory_preview: MemoryRetrievalPreview | None = None,
    execution_lane: ExecutionLaneType = ExecutionLaneType.native_deterministic,
    resolved_execution: ResolvedExecutionProfile | None = None,
    tool_projection_manifest: ToolProjectionManifest | None = None,
    mcp_server_profiles: list[MCPServerProfile] | None = None,
    mutation_contract: MutationContract | None = None,
) -> CompileSnapshot:
    compile_phase = Phase(run_id=run_id, name="compile", order_index=0)
    execution_phase = Phase(run_id=run_id, name="execution", order_index=1)
    resolved_task_kind = TaskKind(task_kind) if task_kind is not None else preset.allowed_task_kinds[0]
    effective_goal = (
        f"{domain_pack.compile_projection.goal_prefix} {goal}"
        if domain_pack is not None and domain_pack.compile_projection.goal_prefix
        else goal
    )
    domain_pack_note = (
        f" under domain pack `{domain_pack.domain_pack_id}` via `{capability_route.adapter_name}`"
        if domain_pack is not None and capability_route is not None
        else f" under domain pack `{domain_pack.domain_pack_id}`"
        if domain_pack is not None
        else ""
    )
    task_card = TaskCard(
        run_id=run_id,
        title=f"{preset.name} task",
        description=f"Execute the bootstrap task for preset `{preset.preset_id}` with `{resolved_task_kind}`{domain_pack_note}.",
        acceptance_criteria=["runtime task exists", "artifact path is known", "task kind is fixed"],
    )
    runtime_task = RuntimeTask(
        run_id=run_id,
        phase_id=execution_phase.phase_id,
        task_card_id=task_card.task_card_id,
        task_kind=resolved_task_kind,
        summary=f"Execute `{preset.preset_id}` for run `{run_id}` with `{resolved_task_kind}`{domain_pack_note}.",
    )

    artifact_path = (
        _mutation_artifact_path_for(run_id, preset.preset_id)
        if mutation_contract is not None and mutation_contract.mutation_mode == MutationMode.patch_apply
        else _artifact_path_for(run_id, preset.preset_id, domain_pack=domain_pack)
    )
    local_artifacts = (
        local_artifacts_for_goal(goal)
        if resolved_task_kind == TaskKind.shell_exec and mutation_contract is None
        else []
    )
    command = (
        []
        if resolved_task_kind == TaskKind.noop or (
            mutation_contract is not None and mutation_contract.mutation_mode == MutationMode.patch_apply
        )
        else _python_command_for(
            goal,
            preset.preset_id,
            artifact_path,
            domain_pack=domain_pack,
            capability_route=capability_route,
            execution_lane=execution_lane,
            tool_projection_manifest=tool_projection_manifest,
        )
    )
    task_packet = TaskPacket(
        runtime_task_id=runtime_task.runtime_task_id,
        run_id=run_id,
        task_kind=resolved_task_kind,
        command=command,
        working_directory=working_directory,
        env=(
            {
                "WORKFLOW_RUN_GOAL": effective_goal,
                "WORKFLOW_PRESET_ID": preset.preset_id,
                "WORKFLOW_TASK_KIND": str(resolved_task_kind),
                "WORKFLOW_EXECUTION_LANE": str(execution_lane),
                "WORKFLOW_MUTATION_MODE": (
                    str(mutation_contract.mutation_mode) if mutation_contract is not None else str(MutationMode.artifact_only)
                ),
                "WORKFLOW_RUNTIME_GATEWAY_PROVIDER": (
                    (resolved_execution.runtime_gateway_provider or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_RUNTIME_GATEWAY_MODEL": (
                    (resolved_execution.runtime_gateway_model or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_RUNTIME_REASONING_EFFORT": (
                    (resolved_execution.runtime_reasoning_effort or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_LLM_MODEL": (
                    (resolved_execution.selected_model or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_MODEL_SELECTION_SOURCE": (
                    (resolved_execution.model_selection_source or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_MODEL_SELECTION_REASON": (
                    (resolved_execution.model_selection_reason or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED": (
                    str(resolved_execution.dogfood_strong_model_enabled).lower()
                    if resolved_execution is not None
                    else "false"
                ),
                "WORKFLOW_DOGFOOD_EXECUTION_BACKEND": (
                    (resolved_execution.dogfood_execution_backend or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_ADAPTIVE_LLM_ROUTING_ENABLED": (
                    str(resolved_execution.adaptive_llm_routing_enabled).lower()
                    if resolved_execution is not None
                    else "false"
                ),
                "WORKFLOW_ADAPTIVE_ROUTE_TIER": (
                    (resolved_execution.adaptive_route_tier or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_ADAPTIVE_ROUTE_REASON": (
                    (resolved_execution.adaptive_route_reason or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_LANGCHAIN_AGENT_PROVIDER": (
                    (resolved_execution.langchain_agent_provider or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_LANGCHAIN_AGENT_MODEL": (
                    (resolved_execution.langchain_agent_model or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_LANGCHAIN_AGENT_DEGRADED_REASON": (
                    (resolved_execution.langchain_agent_degraded_reason or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_AGENT_PROFILE_ID": (
                    (resolved_execution.scope_context.agent_profile_id or "")
                    if resolved_execution is not None and resolved_execution.scope_context is not None
                    else ""
                ),
                "WORKFLOW_CLUSTER_TEMPLATE_ID": (
                    (resolved_execution.scope_context.cluster_template_id or "")
                    if resolved_execution is not None and resolved_execution.scope_context is not None
                    else ""
                ),
                "WORKFLOW_CLUSTER_MEMBER_ID": (
                    (resolved_execution.scope_context.cluster_member_id or "")
                    if resolved_execution is not None and resolved_execution.scope_context is not None
                    else ""
                ),
                "WORKFLOW_PUBLIC_ROLE": (
                    str(resolved_execution.scope_context.public_role or "")
                    if resolved_execution is not None and resolved_execution.scope_context is not None
                    else ""
                ),
                "WORKFLOW_ROLE_LABEL": (
                    (resolved_execution.scope_context.role_label or "")
                    if resolved_execution is not None and resolved_execution.scope_context is not None
                    else ""
                ),
                "WORKFLOW_ROLE_RESPONSIBILITIES": (
                    json.dumps(resolved_execution.role_responsibilities, ensure_ascii=False)
                    if resolved_execution is not None
                    else "[]"
                ),
                "WORKFLOW_CLAUDE_ARCHITECT_CALL_COUNT": (
                    str(resolved_execution.claude_architect_call_count) if resolved_execution is not None else "0"
                ),
                "WORKFLOW_MULTIMODAL_EVIDENCE_REFS": (
                    json.dumps(resolved_execution.multimodal_evidence_refs, ensure_ascii=False)
                    if resolved_execution is not None
                    else "[]"
                ),
                "WORKFLOW_AGENT_MODEL": (resolved_execution.agent_model or "") if resolved_execution is not None else "",
                "WORKFLOW_CODEX_MODEL": (resolved_execution.codex_model or "") if resolved_execution is not None else "",
                "WORKFLOW_CODEX_REASONING_EFFORT": (
                    (resolved_execution.codex_reasoning_effort or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_OPENCODE_MODEL": (
                    (resolved_execution.opencode_model or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_OPENCODE_VARIANT": (
                    (resolved_execution.opencode_variant or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_DOMAIN_PACK_ID": domain_pack.domain_pack_id,
                DOMAIN_PACK_RESOLUTION_ENV_KEY: dump_domain_pack_resolution(domain_pack),
                "WORKFLOW_CAPABILITY_ADAPTER": capability_route.adapter_name if capability_route is not None else "",
                TOOL_PROJECTION_MANIFEST_ENV_KEY: dump_tool_projection_manifest(tool_projection_manifest),
                MEMORY_RETRIEVAL_PREVIEW_ENV_KEY: dump_memory_retrieval_preview(memory_preview),
            }
            if domain_pack is not None
            else {
                "WORKFLOW_RUN_GOAL": effective_goal,
                "WORKFLOW_PRESET_ID": preset.preset_id,
                "WORKFLOW_TASK_KIND": str(resolved_task_kind),
                "WORKFLOW_EXECUTION_LANE": str(execution_lane),
                "WORKFLOW_MUTATION_MODE": (
                    str(mutation_contract.mutation_mode) if mutation_contract is not None else str(MutationMode.artifact_only)
                ),
                "WORKFLOW_RUNTIME_GATEWAY_PROVIDER": (
                    (resolved_execution.runtime_gateway_provider or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_RUNTIME_GATEWAY_MODEL": (
                    (resolved_execution.runtime_gateway_model or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_RUNTIME_REASONING_EFFORT": (
                    (resolved_execution.runtime_reasoning_effort or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_LLM_MODEL": (
                    (resolved_execution.selected_model or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_MODEL_SELECTION_SOURCE": (
                    (resolved_execution.model_selection_source or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_MODEL_SELECTION_REASON": (
                    (resolved_execution.model_selection_reason or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED": (
                    str(resolved_execution.dogfood_strong_model_enabled).lower()
                    if resolved_execution is not None
                    else "false"
                ),
                "WORKFLOW_DOGFOOD_EXECUTION_BACKEND": (
                    (resolved_execution.dogfood_execution_backend or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_ADAPTIVE_LLM_ROUTING_ENABLED": (
                    str(resolved_execution.adaptive_llm_routing_enabled).lower()
                    if resolved_execution is not None
                    else "false"
                ),
                "WORKFLOW_ADAPTIVE_ROUTE_TIER": (
                    (resolved_execution.adaptive_route_tier or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_ADAPTIVE_ROUTE_REASON": (
                    (resolved_execution.adaptive_route_reason or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_LANGCHAIN_AGENT_PROVIDER": (
                    (resolved_execution.langchain_agent_provider or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_LANGCHAIN_AGENT_MODEL": (
                    (resolved_execution.langchain_agent_model or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_LANGCHAIN_AGENT_DEGRADED_REASON": (
                    (resolved_execution.langchain_agent_degraded_reason or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_AGENT_PROFILE_ID": (
                    (resolved_execution.scope_context.agent_profile_id or "")
                    if resolved_execution is not None and resolved_execution.scope_context is not None
                    else ""
                ),
                "WORKFLOW_CLUSTER_TEMPLATE_ID": (
                    (resolved_execution.scope_context.cluster_template_id or "")
                    if resolved_execution is not None and resolved_execution.scope_context is not None
                    else ""
                ),
                "WORKFLOW_CLUSTER_MEMBER_ID": (
                    (resolved_execution.scope_context.cluster_member_id or "")
                    if resolved_execution is not None and resolved_execution.scope_context is not None
                    else ""
                ),
                "WORKFLOW_PUBLIC_ROLE": (
                    str(resolved_execution.scope_context.public_role or "")
                    if resolved_execution is not None and resolved_execution.scope_context is not None
                    else ""
                ),
                "WORKFLOW_ROLE_LABEL": (
                    (resolved_execution.scope_context.role_label or "")
                    if resolved_execution is not None and resolved_execution.scope_context is not None
                    else ""
                ),
                "WORKFLOW_ROLE_RESPONSIBILITIES": (
                    json.dumps(resolved_execution.role_responsibilities, ensure_ascii=False)
                    if resolved_execution is not None
                    else "[]"
                ),
                "WORKFLOW_CLAUDE_ARCHITECT_CALL_COUNT": (
                    str(resolved_execution.claude_architect_call_count) if resolved_execution is not None else "0"
                ),
                "WORKFLOW_MULTIMODAL_EVIDENCE_REFS": (
                    json.dumps(resolved_execution.multimodal_evidence_refs, ensure_ascii=False)
                    if resolved_execution is not None
                    else "[]"
                ),
                "WORKFLOW_AGENT_MODEL": (resolved_execution.agent_model or "") if resolved_execution is not None else "",
                "WORKFLOW_CODEX_MODEL": (resolved_execution.codex_model or "") if resolved_execution is not None else "",
                "WORKFLOW_CODEX_REASONING_EFFORT": (
                    (resolved_execution.codex_reasoning_effort or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_OPENCODE_MODEL": (
                    (resolved_execution.opencode_model or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_OPENCODE_VARIANT": (
                    (resolved_execution.opencode_variant or "") if resolved_execution is not None else ""
                ),
                "WORKFLOW_CAPABILITY_ADAPTER": capability_route.adapter_name if capability_route is not None else "",
                TOOL_PROJECTION_MANIFEST_ENV_KEY: dump_tool_projection_manifest(tool_projection_manifest),
                MEMORY_RETRIEVAL_PREVIEW_ENV_KEY: dump_memory_retrieval_preview(memory_preview),
            }
        ),
        expected_artifacts=[artifact_path.as_posix(), *[path.as_posix() for path, _content in local_artifacts]],
        mutation_contract=mutation_contract,
    )
    handoff = HandoffLite(
        run_id=run_id,
        from_phase_id=compile_phase.phase_id,
        to_phase_id=execution_phase.phase_id,
        summary=f"Compile prepared runtime task `{runtime_task.runtime_task_id}` for execution.",
    )
    return CompileSnapshot(
        compile_phase=compile_phase,
        execution_phase=execution_phase,
        handoff=handoff,
        task_card=task_card,
        runtime_task=runtime_task,
        task_packet=task_packet,
        domain_pack=domain_pack,
        capability_route=capability_route,
        memory_preview=memory_preview,
        execution_lane=execution_lane,
        resolved_execution=resolved_execution or ResolvedExecutionProfile(),
        tool_projection_manifest=tool_projection_manifest,
        mcp_server_profiles=list(mcp_server_profiles or []),
    )
