from __future__ import annotations

from pathlib import Path

from packages.contracts import Phase, Run, RunEvent, RunEventType, RuntimeTask, TaskCard, TaskKind, TaskPacket
from packages.core_domain.db import get_journal_mode, migrate, reset_db
from packages.core_domain.repositories import EventRepository, PresetRepository, RunRepository, TaskRepository


def test_migrate_and_wal_mode(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    applied = migrate(db_path)
    assert "001_init.sql" in applied
    assert get_journal_mode(db_path) == "wal"

    second_apply = migrate(db_path)
    assert second_apply == []


def test_seed_presets_into_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)

    presets = PresetRepository(db_path).seed_defaults()
    stored = PresetRepository(db_path).list()

    assert len(presets) == 2
    assert [preset.preset_id for preset in stored] == ["feature_delivery", "research_spike"]


def test_run_task_and_timeline_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()

    run_repo = RunRepository(db_path)
    task_repo = TaskRepository(db_path)
    event_repo = EventRepository(db_path)

    run = run_repo.create(Run(goal="Create one task", preset_id="feature_delivery"))
    phase = task_repo.create_phase(Phase(run_id=run.run_id, name="compile", order_index=0))
    task_card = task_repo.create_task_card(
        TaskCard(
            run_id=run.run_id,
            title="Write one artifact",
            description="Create a single task packet",
            acceptance_criteria=["runtime task exists"],
        )
    )
    runtime_task = task_repo.create_runtime_task(
        RuntimeTask(
            run_id=run.run_id,
            phase_id=phase.phase_id,
            task_card_id=task_card.task_card_id,
            task_kind=TaskKind.shell_exec,
            summary="Compile a single shell task",
        )
    )
    task_repo.create_task_packet(
        TaskPacket(
            runtime_task_id=runtime_task.runtime_task_id,
            run_id=run.run_id,
            task_kind=TaskKind.shell_exec,
            command=["python", "-c", "print('ok')"],
            working_directory=".",
        )
    )

    event_repo.append(
        RunEvent(
            run_id=run.run_id,
            event_type=RunEventType.run_created,
            object_type="run",
            object_id=run.run_id,
            summary="Run created",
            payload_json={"goal": run.goal, "preset_id": run.preset_id},
        )
    )
    event_repo.append(
        RunEvent(
            run_id=run.run_id,
            event_type=RunEventType.runtime_task_created,
            object_type="runtime_task",
            object_id=runtime_task.runtime_task_id,
            summary="Task created",
            payload_json={
                "runtime_task_id": runtime_task.runtime_task_id,
                "task_kind": runtime_task.task_kind,
                "summary": runtime_task.summary,
            },
        )
    )

    events = event_repo.list_for_run(run.run_id)
    assert [event.event_type for event in events] == [
        RunEventType.run_created,
        RunEventType.runtime_task_created,
    ]
    assert "stdout" not in events[1].payload_json


def test_reset_db_removes_sqlite_file(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    assert db_path.exists()
    reset_db(db_path)
    assert not db_path.exists()
