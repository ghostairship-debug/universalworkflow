from __future__ import annotations

from pathlib import Path


CORE_DOMAIN_ROOT = Path("packages/core_domain")
ALLOWED_CORE_CONTRIBUTION_IMPORTS: dict[Path, dict[str, str]] = {}


def test_business_contribution_modules_are_only_compatibility_shims_in_core_domain() -> None:
    business_named_paths = {
        path
        for path in CORE_DOMAIN_ROOT.glob("*.py")
        if any(token in path.name for token in ("asset_generation", "asset_factory", "cocos", "game"))
    }

    assert business_named_paths == set()


def test_core_domain_has_no_expired_business_shims() -> None:
    for path in CORE_DOMAIN_ROOT.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "Deprecated compatibility shim" not in source
        assert "REMOVE_AFTER_MILESTONE" not in source


def test_core_domain_does_not_import_contribution_implementations_outside_shims() -> None:
    offenders: list[str] = []
    for path in CORE_DOMAIN_ROOT.glob("*.py"):
        if path in ALLOWED_CORE_CONTRIBUTION_IMPORTS:
            continue
        source = path.read_text(encoding="utf-8")
        if "packages.contributions" in source:
            offenders.append(path.as_posix())

    assert offenders == []


def test_core_domain_contribution_import_exceptions_have_expiry_metadata() -> None:
    for path, metadata in ALLOWED_CORE_CONTRIBUTION_IMPORTS.items():
        assert path.exists()
        assert "packages.contributions" in path.read_text(encoding="utf-8")
        assert metadata["remove_after_milestone"] in {"M86", "M87", "M88", "M89", "M90"}
        assert metadata["reason"]
