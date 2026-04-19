from __future__ import annotations

import json
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
EXCLUDED_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "env",
    ".idea",
    ".vscode",
    "state",
}
EXCLUDED_FILE_GLOBS = [
    "*.pyc",
    "*.pyo",
    ".DS_Store",
    "Thumbs.db",
    "M*_Evaluation*.md",
]


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _is_excluded(relative_path: Path) -> bool:
    if any(part in EXCLUDED_DIR_NAMES for part in relative_path.parts):
        return True
    return any(relative_path.match(pattern) for pattern in EXCLUDED_FILE_GLOBS)


def _git_worktree_status(repo_root: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return {
            "available": False,
            "worktree_clean": None,
            "entries": [],
            "error": completed.stderr.strip() or completed.stdout.strip(),
        }
    entries = [line.rstrip() for line in completed.stdout.splitlines() if line.strip()]
    return {
        "available": True,
        "worktree_clean": not entries,
        "entries": entries,
        "error": None,
    }


def build_source_package_manifest(repo_root: Path | str | None = None) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    included_paths: list[str] = []
    excluded_paths: list[str] = []

    for path in root.rglob("*"):
        if path.is_dir():
            continue
        relative_path = path.relative_to(root)
        if _is_excluded(relative_path):
            excluded_paths.append(relative_path.as_posix())
            continue
        included_paths.append(relative_path.as_posix())

    worktree = _git_worktree_status(root)
    return {
        "generated_at": _utc_now_iso(),
        "repo_root": root.as_posix(),
        "included_file_count": len(included_paths),
        "excluded_file_count": len(excluded_paths),
        "included_paths": included_paths,
        "excluded_paths": excluded_paths,
        "excluded_rules": {
            "dir_names": sorted(EXCLUDED_DIR_NAMES),
            "file_globs": EXCLUDED_FILE_GLOBS,
        },
        "db_artifacts_excluded": not any(path.startswith("state/") for path in included_paths),
        "worktree": worktree,
        "passed": not any(path.startswith("state/") for path in included_paths),
    }


def export_source_package(
    output_path: Path | str,
    *,
    repo_root: Path | str | None = None,
    manifest_path: Path | str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    output = Path(output_path)
    manifest = build_source_package_manifest(root)
    manifest["output_path"] = output.as_posix()
    manifest["dry_run"] = dry_run

    if not dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for relative_path in manifest["included_paths"]:
                archive.write(root / relative_path, arcname=relative_path)
        manifest["archive_written"] = True
    else:
        manifest["archive_written"] = False

    if manifest_path is not None:
        manifest_file = Path(manifest_path)
        manifest_file.parent.mkdir(parents=True, exist_ok=True)
        manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest["manifest_path"] = manifest_file.as_posix()

    return manifest
