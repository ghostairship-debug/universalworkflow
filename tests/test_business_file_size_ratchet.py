from __future__ import annotations

from pathlib import Path


BUSINESS_ROOT = Path("packages/contributions")
DEFAULT_BUSINESS_FILE_LINE_LIMIT = 500
BUSINESS_FILE_SIZE_EXCEPTIONS = {
    Path("packages/contributions/asset_factory/asset_generation.py"): {
        "limit": 700,
        "remove_after_milestone": "M86",
        "reason": "provider-specific asset adapters need a follow-up module split",
    },
    Path("packages/contributions/games/cocos/e2e.py"): {
        "limit": 1800,
        "remove_after_milestone": "M90",
        "reason": "legacy Cocos project generation is retained until vertical rebase splits it",
    },
    Path("packages/contributions/games/local_game_arcade_templates.py"): {
        "limit": 650,
        "remove_after_milestone": "M90",
        "reason": "legacy arcade template strings are retained until game pressure-test cleanup",
    },
}


def _line_count(path: Path) -> int:
    return sum(1 for _ in path.open(encoding="utf-8"))


def test_business_contribution_files_are_size_ratcheted() -> None:
    oversized: list[str] = []
    for path in sorted(BUSINESS_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        exception = BUSINESS_FILE_SIZE_EXCEPTIONS.get(path)
        limit = int(exception["limit"]) if exception else DEFAULT_BUSINESS_FILE_LINE_LIMIT
        line_count = _line_count(path)
        if line_count > limit:
            oversized.append(f"{path.as_posix()} has {line_count} lines, limit {limit}")

    assert oversized == []


def test_business_file_size_exceptions_have_expiry_metadata() -> None:
    for path, metadata in BUSINESS_FILE_SIZE_EXCEPTIONS.items():
        assert path.exists()
        assert metadata["remove_after_milestone"] in {"M86", "M87", "M88", "M89", "M90"}
        assert metadata["reason"]
