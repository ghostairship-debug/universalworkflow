from __future__ import annotations

from pathlib import Path


BUSINESS_ROOT = Path("packages/contributions")
DEFAULT_BUSINESS_FILE_LINE_LIMIT = 500
BUSINESS_FILE_SIZE_EXCEPTIONS = {
    Path("packages/contributions/asset_factory/asset_generation.py"): {
        "limit": 850,
        "remove_after_milestone": "M110",
        "reason": "M108.5 review and M109 no-degradation repair extended the split window for provider-specific asset adapters while Cocos next-step direction is decided",
    },
    Path("packages/contributions/games/cocos/e2e.py"): {
        "limit": 2000,
        "remove_after_milestone": "M110",
        "reason": "M108.5 review and M109 no-degradation repair keep the legacy Cocos generator frozen under ratchet until the M109 direction is approved or declined",
    },
    Path("packages/contributions/games/cocos/ecosystem_bridge.py"): {
        "limit": 1200,
        "remove_after_milestone": "M110",
        "reason": "M108.5 review and M109 no-degradation repair added the unattended Cocos Editor bridge runner and project-local extension contract; split runner/templates after ecosystem smoke stabilizes",
    },
    Path("packages/contributions/games/local_game_arcade_templates.py"): {
        "limit": 650,
        "remove_after_milestone": "M110",
        "reason": "M108.5 review extends the legacy arcade template split until the post-M108 game direction decision is complete",
    },
    Path("packages/contributions/pipelines/commercial_game_production.py"): {
        "limit": 720,
        "remove_after_milestone": "M110",
        "reason": "M108.5 review and M109 no-degradation repair keep commercial pipeline orchestration in contributions until a post-M109 split is scheduled",
    },
    Path("packages/contributions/pipelines/registry.py"): {
        "limit": 560,
        "remove_after_milestone": "M110",
        "reason": "M108.5 review and M109 no-degradation repair keep contribution registry gate wiring in place until the M110 split window",
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
        assert metadata["remove_after_milestone"] in {"M109", "M110"}
        assert "M108.5 review" in metadata["reason"]
        assert metadata["reason"]
