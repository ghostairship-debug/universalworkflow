from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


DEFAULT_DB_PATH = Path("state/workflow.db")
MIGRATIONS_DIR = Path("infra/migrations")


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def resolve_db_path(db_path: str | Path | None = None) -> Path:
    return Path(db_path) if db_path is not None else DEFAULT_DB_PATH


@contextmanager
def get_connection(db_path: str | Path | None = None):
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    apply_sqlite_pragmas(connection)
    try:
        yield connection
    finally:
        connection.close()


def apply_sqlite_pragmas(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA journal_mode = WAL;")
    connection.execute("PRAGMA synchronous = NORMAL;")


def get_journal_mode(db_path: str | Path | None = None) -> str:
    with get_connection(db_path) as connection:
        return str(connection.execute("PRAGMA journal_mode;").fetchone()[0]).lower()


def reset_db(db_path: str | Path | None = None) -> Path:
    path = resolve_db_path(db_path)
    if path.exists():
        path.unlink()
    wal_path = path.with_suffix(path.suffix + "-wal")
    shm_path = path.with_suffix(path.suffix + "-shm")
    for extra_path in (wal_path, shm_path):
        if extra_path.exists():
            extra_path.unlink()
    return path


def migrate(db_path: str | Path | None = None, migrations_dir: str | Path | None = None) -> list[str]:
    path = resolve_db_path(db_path)
    migration_dir = Path(migrations_dir) if migrations_dir is not None else MIGRATIONS_DIR
    applied: list[str] = []
    with get_connection(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS _migrations (
              migration_id TEXT PRIMARY KEY,
              applied_at TEXT NOT NULL
            )
            """
        )
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
