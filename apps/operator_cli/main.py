from __future__ import annotations

import json
import os
from pathlib import Path

import typer

from packages.core_domain.db import DEFAULT_DB_PATH, migrate, reset_db
from packages.core_domain.repositories import PresetRepository, TaskRepository
from packages.core_domain.services import OrchestratorService

app = typer.Typer(help="Workflow operator CLI.")
run_app = typer.Typer(help="Run lifecycle commands.")
task_app = typer.Typer(help="Task inspection commands.")
preset_app = typer.Typer(help="Preset inspection commands.")
db_app = typer.Typer(help="Development database commands.")

app.add_typer(run_app, name="run")
app.add_typer(task_app, name="task")
app.add_typer(preset_app, name="preset")
app.add_typer(db_app, name="db")


def _db_path_from_context(ctx: typer.Context) -> Path:
    return Path(ctx.obj["db_path"])


def _service(ctx: typer.Context) -> OrchestratorService:
    db_path = _db_path_from_context(ctx)
    migrate(db_path)
    return OrchestratorService(db_path)


def _emit_json(payload: dict | list) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@app.callback()
def main(
    ctx: typer.Context,
    db_path: str = typer.Option(
        os.getenv("WORKFLOW_DB_PATH", str(DEFAULT_DB_PATH)),
        "--db-path",
        help="SQLite database path.",
    ),
) -> None:
    ctx.obj = {"db_path": db_path}


@preset_app.command("list")
def preset_list(ctx: typer.Context, as_json: bool = typer.Option(False, "--json")) -> None:
    presets = _service(ctx).list_presets()
    if as_json:
        _emit_json([preset.model_dump(mode="json") for preset in presets])
        return
    for preset in presets:
        typer.echo(
            f"{preset.preset_id} | review={preset.default_review_policy} | task_kinds={','.join(preset.allowed_task_kinds)}"
        )


@run_app.command("create")
def run_create(
    ctx: typer.Context,
    goal: str = typer.Option(..., "--goal"),
    preset: str = typer.Option(..., "--preset"),
    prepare: bool = typer.Option(False, "--prepare", help="Prepare the run internally after creation."),
    execute: bool = typer.Option(False, "--execute", help="Execute the prepared run internally."),
) -> None:
    service = _service(ctx)
    run = service.create_run(goal=goal, preset_id=preset)
    payload: dict = {"run": run.model_dump(mode="json")}
    if prepare or execute:
        prepared = service.prepare_run(run.run_id)
        payload["prepared_task_id"] = prepared.task_packet.runtime_task_id
        payload["expected_artifacts"] = prepared.task_packet.expected_artifacts
    if execute:
        executed = service.execute_run(run.run_id)
        payload["review_decision"] = executed.review_verdict.decision
        payload["evidence_id"] = executed.evidence.evidence_id
    _emit_json(payload)


@run_app.command("cancel")
def run_cancel(ctx: typer.Context, run_id: str) -> None:
    _emit_json(_service(ctx).cancel_run(run_id).model_dump(mode="json"))


@run_app.command("status")
def run_status(ctx: typer.Context, run_id: str) -> None:
    service = _service(ctx)
    run = service.get_run(run_id)
    runtime_tasks = TaskRepository(_db_path_from_context(ctx)).list_runtime_tasks_for_run(run_id)
    payload = run.model_dump(mode="json")
    payload["runtime_task_ids"] = [task.runtime_task_id for task in runtime_tasks]
    _emit_json(payload)


@run_app.command("timeline")
def run_timeline(ctx: typer.Context, run_id: str, as_json: bool = typer.Option(False, "--json")) -> None:
    timeline = _service(ctx).get_timeline(run_id)
    if as_json:
        _emit_json([event.model_dump(mode="json") for event in timeline])
        return
    for event in timeline:
        typer.echo(f"{event.created_at.isoformat()} | {event.event_type} | {event.summary}")


@task_app.command("evidence")
def task_evidence(ctx: typer.Context, runtime_task_id: str) -> None:
    _emit_json(_service(ctx).get_task_evidence(runtime_task_id).model_dump(mode="json"))


@db_app.command("reset")
def db_reset(
    ctx: typer.Context,
    seed_presets: bool = typer.Option(True, "--seed-presets/--no-seed-presets", help="Seed bootstrap presets."),
) -> None:
    db_path = _db_path_from_context(ctx)
    reset_db(db_path)
    migrate(db_path)
    seeded = []
    if seed_presets:
        seeded = [preset.preset_id for preset in PresetRepository(db_path).seed_defaults()]
    _emit_json({"db_path": db_path.as_posix(), "seeded_presets": seeded})


def run() -> None:
    app()


if __name__ == "__main__":
    run()
