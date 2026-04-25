from __future__ import annotations

from pathlib import Path

import pytest

from packages.core_domain.repo_mutation import apply_unified_diff


def test_apply_unified_diff_does_not_partially_write_when_later_hunk_fails(tmp_path: Path) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("before\n", encoding="utf-8")
    second.write_text("actual\n", encoding="utf-8")
    patch = "\n".join(
        [
            "--- first.txt",
            "+++ first.txt",
            "@@ -1 +1 @@",
            "-before",
            "+after",
            "--- second.txt",
            "+++ second.txt",
            "@@ -1 +1 @@",
            "-expected",
            "+changed",
            "",
        ]
    )

    with pytest.raises(ValueError):
        apply_unified_diff(tmp_path, patch, allowed_paths=["first.txt", "second.txt"])

    assert first.read_text(encoding="utf-8") == "before\n"
    assert second.read_text(encoding="utf-8") == "actual\n"
