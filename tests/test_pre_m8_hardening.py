from __future__ import annotations

from pathlib import Path

from infra.validation.doc_hygiene import check_living_doc_links
from infra.validation.source_package import build_source_package_manifest


def test_check_living_doc_links_detects_absolute_local_and_missing_targets(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    living_doc = tmp_path / "docs" / "current.md"
    living_doc.write_text(
        "[ok](./target.md)\n[bad-abs](/D:/workspace/file.md)\n[bad-missing](./missing.md)\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "target.md").write_text("ok", encoding="utf-8")

    report = check_living_doc_links(tmp_path, [Path("docs/current.md")])

    assert report["passed"] is False
    assert report["issue_count"] == 2
    assert {item["kind"] for item in report["issues"]} == {"absolute_local_link", "missing_target"}


def test_build_source_package_manifest_excludes_state_and_cache_noise(tmp_path: Path) -> None:
    (tmp_path / "packages").mkdir()
    (tmp_path / "packages" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "workflow.db").write_text("db", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.pyc").write_bytes(b"pyc")

    manifest = build_source_package_manifest(tmp_path)

    assert manifest["passed"] is True
    assert "packages/app.py" in manifest["included_paths"]
    assert "state/workflow.db" not in manifest["included_paths"]
    assert "__pycache__/x.pyc" not in manifest["included_paths"]
    assert manifest["db_artifacts_excluded"] is True
