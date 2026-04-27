from __future__ import annotations

import importlib.util
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


GRAPH_CHECKPOINTER_FACTORY_SCHEMA = "m99_langgraph_checkpointer_factory_v1"


@dataclass
class GraphCheckpointerHandle:
    backend: str
    saver: Any | None
    db_path: Path | None = None
    connection: Any | None = None
    fallback_reason: str | None = None

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def describe(self) -> dict[str, Any]:
        return {
            "schema_version": GRAPH_CHECKPOINTER_FACTORY_SCHEMA,
            "backend": self.backend,
            "db_path": self.db_path.as_posix() if self.db_path else None,
            "durable": self.backend == "sqlite",
            "fallback_reason": self.fallback_reason,
        }


def graph_checkpoint_db_path(workspace_root: str | Path, *, graph_id: str = "workflow_graph") -> Path:
    safe_graph_id = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in graph_id)
    return Path(workspace_root).resolve() / "state" / "langgraph" / "checkpoints" / f"{safe_graph_id}.sqlite"


def graph_sqlite_available() -> bool:
    return importlib.util.find_spec("langgraph.checkpoint.sqlite") is not None


def graph_memory_available() -> bool:
    return importlib.util.find_spec("langgraph.checkpoint.memory") is not None


def open_graph_checkpointer(
    workspace_root: str | Path,
    *,
    preferred_backend: str = "sqlite",
    graph_id: str = "workflow_graph",
) -> GraphCheckpointerHandle:
    if preferred_backend == "sqlite":
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver

            db_path = graph_checkpoint_db_path(workspace_root, graph_id=graph_id)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(db_path, check_same_thread=False)
            saver = SqliteSaver(connection)
            saver.setup()
            return GraphCheckpointerHandle(
                backend="sqlite",
                saver=saver,
                db_path=db_path,
                connection=connection,
            )
        except Exception as exc:
            return _open_memory_fallback(f"sqlite_unavailable: {type(exc).__name__}: {exc}")
    return _open_memory_fallback(f"preferred_backend_not_sqlite: {preferred_backend}")


def _open_memory_fallback(reason: str) -> GraphCheckpointerHandle:
    try:
        from langgraph.checkpoint.memory import InMemorySaver

        return GraphCheckpointerHandle(
            backend="memory",
            saver=InMemorySaver(),
            fallback_reason=reason,
        )
    except Exception as exc:
        return GraphCheckpointerHandle(
            backend="unavailable",
            saver=None,
            fallback_reason=f"{reason}; memory_unavailable: {type(exc).__name__}: {exc}",
        )
