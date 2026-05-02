from __future__ import annotations

from pathlib import Path


PRODUCTION_ROOTS = (Path("packages"), Path("apps"), Path("infra"))
PRODUCTION_SUFFIXES = {".css", ".js", ".json", ".ps1", ".py", ".sql"}
# M99-M108.5 added the local LangGraph runtime, Studio config, Cocos graph
# pressure-test surface, contribution pipeline boundary, Cocos foundation
# inspectors, local native-content scaffolds, player-visible validation, and
# sample closeout reporting. M108.5 also repaired manifest evidence counting,
# strict player-visible inspector gates, and database-backed task cards with
# markdown snapshot export. M109 adds pipeline truth reporting, unified project
# brief intake, opt-in single-agent role evidence, DB task-card handoff, and a
# machine-readable multimodal route truth table. M109 no-degradation repair adds
# strict commercial gate contracts, Cocos ecosystem bridge evidence collection,
# source-path intake, persisted evidence-path fixes, receipt-bound same-project
# task-card worker execution, and progress-aware child workflow watchdog
# evidence. The 2026-04-29 validation bug-first pass also added structured
# HTTP timeout/failure-class trace evidence for API validation. The 2026-04-29
# Cocos ecosystem repair added the unattended Editor runner plus project-local
# extension code for AssetDB/Scene/Prefab/Build API evidence. The 2026-05-02
# post-review commercial hardening added DB lifecycle/fresh-execution gates,
# semantic/product-body contracts, and source requirement coverage. The
# development-readiness loop then added a separate readiness contract plus
# active-phase-only product-body runtime task-card materialization. Keep this
# tight enough to catch accidental growth while preserving the accepted baseline.
PRODUCTION_LOC_LIMIT = 65_500


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
