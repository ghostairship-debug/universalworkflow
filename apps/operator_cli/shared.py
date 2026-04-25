from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable, Optional, TypeVar

import typer

from packages.core_domain.db import migrate
from packages.core_domain.errors import WorkflowError
from packages.core_domain.services import OrchestratorService

T = TypeVar("T")


def _db_path_from_context(ctx: typer.Context) -> Path:
    return Path(ctx.obj["db_path"])


def _service(ctx: typer.Context) -> OrchestratorService:
    db_path = _db_path_from_context(ctx)
    migrate(db_path)
    return OrchestratorService(db_path, workspace_root=ctx.obj.get("workspace_root"))


def _emit_json(payload: dict | list) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        typer.echo(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8", errors="replace") + b"\n")
        sys.stdout.buffer.flush()


def _workspace_root_from_context(ctx: typer.Context) -> Path:
    root = ctx.obj.get("workspace_root")
    return Path(root).resolve() if root else Path.cwd().resolve()


def _workflow_error_payload(exc: WorkflowError) -> dict:
    return {"error": {"code": exc.code, "message": exc.message, "details": exc.details}}


def _run_workflow_action(action: Callable[[], T]) -> T:
    try:
        return action()
    except WorkflowError as exc:
        _emit_json(_workflow_error_payload(exc))
        raise typer.Exit(code=1) from exc


def _parse_key_value_pairs(values: Optional[list[str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in values or []:
        if "=" not in item:
            raise typer.BadParameter("metadata entries must use key=value")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise typer.BadParameter("metadata key cannot be empty")
        result[key] = value.strip()
    return result


def _goal_from_task_card(task_card_path: Path) -> str:
    text = task_card_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip(" #")
        if stripped:
            return stripped[:240]
    return task_card_path.stem
