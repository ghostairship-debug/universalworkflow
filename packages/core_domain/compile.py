from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from packages.contracts import (
    CapabilityRoute,
    DomainPackResolution,
    HandoffLite,
    MemoryRetrievalPreview,
    Phase,
    PresetDefinition,
    RuntimeTask,
    TaskCard,
    TaskKind,
    TaskPacket,
)
from packages.core_domain.domain_packs import DOMAIN_PACK_RESOLUTION_ENV_KEY, dump_domain_pack_resolution
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


def _python_command_for(
    goal: str,
    preset_id: str,
    artifact_path: Path,
    *,
    domain_pack: DomainPackResolution | None = None,
    capability_route: CapabilityRoute | None = None,
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
        "runtime_brief=os.environ.get('WORKFLOW_RUNTIME_BRIEF'))\n"
        "path.write_text(content, encoding='utf-8')\n"
        "print(path.as_posix())\n"
    )
    return ["python", "-c", body]


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


def compile_run(
    goal: str,
    preset: PresetDefinition,
    run_id: str,
    working_directory: str = ".",
    task_kind: TaskKind | str | None = None,
    domain_pack: DomainPackResolution | None = None,
    capability_route: CapabilityRoute | None = None,
    memory_preview: MemoryRetrievalPreview | None = None,
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

    artifact_path = _artifact_path_for(run_id, preset.preset_id, domain_pack=domain_pack)
    command = (
        []
        if resolved_task_kind == TaskKind.noop
        else _python_command_for(
            goal,
            preset.preset_id,
            artifact_path,
            domain_pack=domain_pack,
            capability_route=capability_route,
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
                "WORKFLOW_DOMAIN_PACK_ID": domain_pack.domain_pack_id,
                DOMAIN_PACK_RESOLUTION_ENV_KEY: dump_domain_pack_resolution(domain_pack),
                "WORKFLOW_CAPABILITY_ADAPTER": capability_route.adapter_name if capability_route is not None else "",
                MEMORY_RETRIEVAL_PREVIEW_ENV_KEY: dump_memory_retrieval_preview(memory_preview),
            }
            if domain_pack is not None
            else {
                "WORKFLOW_RUN_GOAL": effective_goal,
                "WORKFLOW_PRESET_ID": preset.preset_id,
                "WORKFLOW_TASK_KIND": str(resolved_task_kind),
                "WORKFLOW_CAPABILITY_ADAPTER": capability_route.adapter_name if capability_route is not None else "",
                MEMORY_RETRIEVAL_PREVIEW_ENV_KEY: dump_memory_retrieval_preview(memory_preview),
            }
        ),
        expected_artifacts=[artifact_path.as_posix()],
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
    )
