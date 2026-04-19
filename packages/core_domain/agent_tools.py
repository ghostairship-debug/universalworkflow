from __future__ import annotations

from pathlib import Path
from typing import Any


BUILT_IN_TOOL_SPECS: list[dict[str, Any]] = [
    {
        "tool_name": "list_workspace_files",
        "description": "List up to 50 files under the current working directory. Read-only.",
        "read_only": True,
    },
    {
        "tool_name": "read_workspace_text",
        "description": "Read a UTF-8 text file under the current working directory. Read-only.",
        "read_only": True,
    },
    {
        "tool_name": "read_execution_brief",
        "description": "Return the current workflow goal, preset, task kind, and runtime brief. Read-only.",
        "read_only": True,
    },
]


def built_in_tool_specs() -> list[dict[str, Any]]:
    return [dict(item) for item in BUILT_IN_TOOL_SPECS]


def list_workspace_files(working_directory: str, *, limit: int = 50) -> list[str]:
    root = Path(working_directory).resolve()
    files = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    ]
    return sorted(files)[:limit]


def read_workspace_text(working_directory: str, relative_path: str, *, max_chars: int = 8000) -> str:
    root = Path(working_directory).resolve()
    target = (root / relative_path).resolve()
    if root not in target.parents and target != root:
        raise ValueError("requested path is outside the working directory")
    return target.read_text(encoding="utf-8")[:max_chars]


def read_execution_brief(env: dict[str, str]) -> dict[str, str | None]:
    return {
        "goal": env.get("WORKFLOW_RUN_GOAL"),
        "preset_id": env.get("WORKFLOW_PRESET_ID"),
        "task_kind": env.get("WORKFLOW_TASK_KIND"),
        "runtime_brief": env.get("WORKFLOW_RUNTIME_BRIEF"),
        "domain_pack_id": env.get("WORKFLOW_DOMAIN_PACK_ID"),
        "execution_lane": env.get("WORKFLOW_EXECUTION_LANE"),
    }
