from __future__ import annotations

from pathlib import Path

from packages.contracts import Phase, PresetDefinition, RuntimeTask, TaskCard, TaskKind, TaskPacket


def _artifact_path_for(run_id: str, preset_id: str) -> Path:
    return Path("state") / "artifacts" / f"{run_id}_{preset_id}.md"


def _python_command_for(goal: str, preset_id: str, artifact_path: Path) -> list[str]:
    body = (
        "from pathlib import Path\n"
        f"path = Path(r'{artifact_path.as_posix()}')\n"
        "path.parent.mkdir(parents=True, exist_ok=True)\n"
        f"path.write_text('preset: {preset_id}\\ngoal: {goal}\\n', encoding='utf-8')\n"
        "print(path.as_posix())\n"
    )
    return ["python", "-c", body]


def compile_run(goal: str, preset: PresetDefinition, run_id: str, working_directory: str = ".") -> tuple[Phase, TaskCard, RuntimeTask, TaskPacket]:
    phase = Phase(run_id=run_id, name="bootstrap_execution", order_index=0)
    task_card = TaskCard(
        run_id=run_id,
        title=f"{preset.name} task",
        description=f"Execute the bootstrap task for preset `{preset.preset_id}`.",
        acceptance_criteria=["runtime task exists", "artifact path is known"],
    )
    task_kind = preset.allowed_task_kinds[0]
    runtime_task = RuntimeTask(
        run_id=run_id,
        phase_id=phase.phase_id,
        task_card_id=task_card.task_card_id,
        task_kind=task_kind,
        summary=f"Execute `{preset.preset_id}` for run `{run_id}`.",
    )

    artifact_path = _artifact_path_for(run_id, preset.preset_id)
    command = [] if task_kind == TaskKind.noop else _python_command_for(goal, preset.preset_id, artifact_path)
    task_packet = TaskPacket(
        runtime_task_id=runtime_task.runtime_task_id,
        run_id=run_id,
        task_kind=task_kind,
        command=command,
        working_directory=working_directory,
        expected_artifacts=[artifact_path.as_posix()],
    )
    return phase, task_card, runtime_task, task_packet
