from __future__ import annotations

from pathlib import Path


PRODUCTION_ROOTS = (Path("packages"), Path("apps"), Path("infra"))
PRODUCTION_SUFFIXES = {".css", ".js", ".json", ".ps1", ".py", ".sql"}
# M99-M104 added the local SQLite LangGraph runtime, dynamic interrupt/resume,
# Studio config, and Cocos graph pressure-test surface. Keep this tight enough
# to catch accidental growth while allowing the accepted local graph runtime.
PRODUCTION_LOC_LIMIT = 52_000


def _is_production_source(path: Path) -> bool:
    if path.suffix not in PRODUCTION_SUFFIXES:
        return False
    if "__pycache__" in path.parts:
        return False
    if any(part in {"test", "tests"} for part in path.parts):
        return False
    if path.name.startswith("test_") or path.name.endswith("_test.py"):
        return False
    return True


def test_production_source_loc_is_ratcheted() -> None:
    total = 0
    counted_paths: list[Path] = []
    for root in PRODUCTION_ROOTS:
        for path in root.rglob("*"):
            if path.is_file() and _is_production_source(path):
                counted_paths.append(path)
                total += sum(1 for _ in path.open(encoding="utf-8"))

    assert counted_paths
    assert total <= PRODUCTION_LOC_LIMIT, f"production source LOC is {total}, limit is {PRODUCTION_LOC_LIMIT}"
