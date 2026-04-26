from __future__ import annotations

from pathlib import Path


def test_default_pytest_basetemp_is_workflow_scoped(tmp_path: Path) -> None:
    normalized = tmp_path.as_posix()
    assert "/state/.pytest-tmp-workflow/" in normalized
    assert "pytest-of-" not in normalized
