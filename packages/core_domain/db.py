from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.core_domain.config import build_effective_config
from packages.core_domain.errors import DatabaseBusyError


DEFAULT_DB_PATH = Path("state/workflow.db")
MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "infra" / "migrations"
SQLITE_BUSY_TIMEOUT_MS = 5_000


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def configured_default_db_path(*, cwd: str | Path | None = None) -> Path:
    effective = build_effective_config(cwd=cwd)
    return Path(effective["db"]["path"])


def workspace_scoped_db_path(
    *,
    workspace_root: str | Path | None = None,
    label: str = "workflow",
    db_root: str | Path = "state/workspaces",
) -> Path:
    root = Path(workspace_root or Path.cwd()).resolve()
    digest = hashlib.sha1(root.as_posix().encode("utf-8")).hexdigest()[:10]
    safe_label = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in label.strip()) or "workflow"
    return Path(db_root) / digest / f"{safe_label}.db"


def resolve_db_path(db_path: str | Path | None = None) -> Path:
    return Path(db_path) if db_path is not None else configured_default_db_path()


@contextmanager
def get_connection(db_path: str | Path | None = None):
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)
    connection.row_factory = sqlite3.Row
    apply_sqlite_pragmas(connection)
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def unit_of_work(db_path: str | Path | None = None):
    with get_connection(db_path) as connection:
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def apply_sqlite_pragmas(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA journal_mode = WAL;")
    connection.execute("PRAGMA synchronous = NORMAL;")
    connection.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS};")


def get_journal_mode(db_path: str | Path | None = None) -> str:
    with get_connection(db_path) as connection:
        return str(connection.execute("PRAGMA journal_mode;").fetchone()[0]).lower()


def reset_db(db_path: str | Path | None = None) -> Path:
    path = resolve_db_path(db_path)
    try:
        if path.exists():
            path.unlink()
        wal_path = path.with_suffix(path.suffix + "-wal")
        shm_path = path.with_suffix(path.suffix + "-shm")
        for extra_path in (wal_path, shm_path):
            if extra_path.exists():
                extra_path.unlink()
    except PermissionError as exc:
        raise DatabaseBusyError(
            path.as_posix(),
            "reset_db",
            {
                "hint": "close other processes or use a workspace-scoped DB path before retrying reset",
                "wal_path": path.with_suffix(path.suffix + "-wal").as_posix(),
                "shm_path": path.with_suffix(path.suffix + "-shm").as_posix(),
            },
        ) from exc
    except OSError as exc:
        if getattr(exc, "winerror", None) == 32:
            raise DatabaseBusyError(
                path.as_posix(),
                "reset_db",
                {
                    "hint": "the SQLite database is locked by another process; use an isolated DB path for parallel work",
                    "winerror": 32,
                },
            ) from exc
        raise
    return path


def _ensure_migrations_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS _migrations (
          migration_id TEXT PRIMARY KEY,
          applied_at TEXT NOT NULL
        )
        """
    )


def get_migration_status(db_path: str | Path | None = None, migrations_dir: str | Path | None = None) -> dict[str, Any]:
    path = resolve_db_path(db_path)
    migration_dir = Path(migrations_dir) if migrations_dir is not None else MIGRATIONS_DIR
    migration_files = sorted(migration_dir.glob("*.sql"))
    available_ids = [migration_file.name for migration_file in migration_files]
    with get_connection(path) as connection:
        _ensure_migrations_table(connection)
        applied_rows = connection.execute(
            "SELECT migration_id, applied_at FROM _migrations ORDER BY migration_id"
        ).fetchall()
    applied = [
        {"migration_id": str(row["migration_id"]), "applied_at": str(row["applied_at"])}
        for row in applied_rows
    ]
    applied_ids = {item["migration_id"] for item in applied}
    available_id_set = set(available_ids)
    pending = [migration_id for migration_id in available_ids if migration_id not in applied_ids]
    unknown_applied = [migration_id for migration_id in applied_ids if migration_id not in available_id_set]
    return {
        "db_path": path.resolve().as_posix(),
        "migrations_dir": migration_dir.resolve().as_posix(),
        "available_count": len(available_ids),
        "applied_count": len(applied),
        "pending_count": len(pending),
        "up_to_date": not pending,
        "available": available_ids,
        "applied": applied,
        "pending": pending,
        "unknown_applied": sorted(unknown_applied),
    }


def migrate(db_path: str | Path | None = None, migrations_dir: str | Path | None = None) -> list[str]:
    path = resolve_db_path(db_path)
    migration_dir = Path(migrations_dir) if migrations_dir is not None else MIGRATIONS_DIR
    applied: list[str] = []
    with get_connection(path) as connection:
        _ensure_migrations_table(connection)
        existing = {
            row["migration_id"]
            for row in connection.execute("SELECT migration_id FROM _migrations").fetchall()
        }
        for migration_file in sorted(migration_dir.glob("*.sql")):
            if migration_file.name in existing:
                continue
            connection.executescript(migration_file.read_text(encoding="utf-8"))
            connection.execute(
                "INSERT INTO _migrations (migration_id, applied_at) VALUES (?, ?)",
                (migration_file.name, utc_now_iso()),
            )
            applied.append(migration_file.name)
        connection.commit()
    return applied
