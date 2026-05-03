from __future__ import annotations

from pathlib import Path

import pytest

from packages.core_domain.repo_mutation import apply_unified_diff, capture_workspace_snapshot, restore_workspace_snapshot


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


def test_apply_unified_diff_can_recover_from_inaccurate_hunk_line_numbers(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    patch = "\n".join(
        [
            "--- target.txt",
            "+++ target.txt",
            "@@ -99,3 +99,3 @@",
            " alpha",
            "-beta",
            "+bravo",
            " gamma",
            "",
        ]
    )

    changed = apply_unified_diff(tmp_path, patch, allowed_paths=["target.txt"])

    assert changed == ["target.txt"]
    assert target.read_text(encoding="utf-8") == "alpha\nbravo\ngamma\n"


def test_apply_unified_diff_failure_restore_preserves_lf_line_endings(tmp_path: Path) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_bytes(b"before\n")
    second.write_bytes(b"actual\n")
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

    assert first.read_bytes() == b"before\n"
    assert second.read_bytes() == b"actual\n"


def test_restore_workspace_snapshot_preserves_lf_line_endings(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_bytes(b"alpha\nbeta\n")
    snapshot = capture_workspace_snapshot(tmp_path, ["target.txt"])

    target.write_bytes(b"changed\r\n")
    restore_workspace_snapshot(tmp_path, snapshot)

    assert target.read_bytes() == b"alpha\nbeta\n"


def test_workspace_snapshot_preserves_binary_files_in_write_set_directory(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    binary = assets / "background.png"
    binary.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")

    snapshot = capture_workspace_snapshot(tmp_path, ["assets"])

    assert snapshot["assets/background.png"].binary is True
    binary.write_bytes(b"changed")
    restore_workspace_snapshot(tmp_path, snapshot)

    assert binary.read_bytes() == b"\x89PNG\r\n\x1a\n\x00\x00"
