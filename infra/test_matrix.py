from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence


UNIT_TARGETS = [
    "tests/test_contracts.py",
    "tests/test_repositories.py",
    "tests/test_operator_action_receipt.py",
    "tests/test_repo_mutation_atomicity.py",
    "tests/test_workspace_root.py",
    "tests/test_service_decomposition.py",
    "tests/test_scheduler_flag_off_isolation.py",
]

CORE_TARGETS = [
    "tests/test_contracts.py",
    "tests/test_repositories.py",
    "tests/test_doctor.py",
    "tests/test_api_startup.py",
    "tests/test_scheduler_flag_off_isolation.py",
    "tests/test_service_decomposition.py",
    "tests/test_runtime_boundary.py",
    "tests/test_m41_capabilities.py",
]

INTEGRATION_TARGETS = [
    "tests/test_api.py",
    "tests/test_cli.py",
    "tests/test_remote_worker_api.py",
    "tests/test_scheduler_authority_api.py",
    "tests/test_web_ui.py",
]

SLOW_TARGETS = [
    "tests/test_api.py",
    "tests/test_cli.py",
    "tests/test_web_ui.py",
    "tests/test_release_closeout.py",
]

COMMERCIAL_FAST_TARGETS = [
    "tests/test_active_truth_check.py",
    "tests/test_commercial_game_evidence_contracts.py",
]

COMMERCIAL_INTEGRATION_TARGETS = [
    "tests/test_pipeline_and_automation_cli.py",
    "tests/test_m109_unified_brief.py",
]

COMMERCIAL_COCOS_BROWSER_TARGETS = [
    "tests/test_cocos_e2e.py",
]

COMMERCIAL_PROVIDER_CONTRACT_TARGETS = [
    "tests/test_capability_probe.py",
    "tests/test_capability_control_plane.py",
]

PYTEST_TEMP_ROOT_NAME = ".pytest-tmp-workflow"
PYTEST_TEMP_PREFIXES = ("matrix-", "default-")
KEEP_TEST_TEMP_ENV = "WORKFLOW_KEEP_TEST_TEMP"
TEST_TEMP_TTL_HOURS_ENV = "WORKFLOW_TEST_TEMP_TTL_HOURS"
TEST_TEMP_MAX_MB_ENV = "WORKFLOW_TEST_TEMP_MAX_MB"
DEFAULT_TEST_TEMP_TTL_HOURS = 24.0
DEFAULT_TEST_TEMP_MAX_MB = 256.0


@dataclass(frozen=True)
class MatrixSelection:
    suite: str
    targets: list[str]
    run_slow: bool = False


def _cleanup_enabled() -> bool:
    value = os.getenv(KEEP_TEST_TEMP_ENV, "").strip().lower()
    return value not in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed = float(raw_value)
    except ValueError:
        return default
    return max(parsed, 0.0)


def _pytest_temp_root(workspace_root: Path) -> Path:
    return (workspace_root / "state" / PYTEST_TEMP_ROOT_NAME).resolve()


def _unique_basetemp(workspace_root: Path) -> Path:
    root = _pytest_temp_root(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="matrix-", dir=root)).resolve()


def _is_safe_pytest_temp_child(path: Path, temp_root: Path) -> bool:
    resolved = path.resolve()
    resolved_root = temp_root.resolve()
    if resolved == resolved_root:
        return False
    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        return False
    return resolved.name.startswith(PYTEST_TEMP_PREFIXES)


def _directory_size_bytes(path: Path) -> int:
    total = 0
    if not path.exists():
        return total
    for item in path.rglob("*"):
        try:
            if item.is_file() or item.is_symlink():
                total += item.stat().st_size
        except OSError:
            continue
    return total


def _remove_pytest_temp_dir(path: Path, temp_root: Path) -> dict[str, object]:
    resolved = path.resolve()
    if not _is_safe_pytest_temp_child(resolved, temp_root):
        return {
            "path": resolved.as_posix(),
            "status": "skipped",
            "reason": "outside_pytest_temp_root_or_unknown_prefix",
        }
    if not resolved.exists():
        return {"path": resolved.as_posix(), "status": "missing", "bytes_removed": 0}
    bytes_removed = _directory_size_bytes(resolved)
    try:
        shutil.rmtree(resolved)
    except OSError as exc:
        return {
            "path": resolved.as_posix(),
            "status": "failed",
            "bytes_removed": 0,
            "error": str(exc),
        }
    return {"path": resolved.as_posix(), "status": "deleted", "bytes_removed": bytes_removed}


def prune_pytest_temp_workspace(
    workspace_root: Path,
    *,
    ttl_hours: float | None = None,
    max_mb: float | None = None,
    now_timestamp: float | None = None,
) -> dict[str, object]:
    if not _cleanup_enabled():
        return {"enabled": False, "status": "skipped", "reason": KEEP_TEST_TEMP_ENV}

    temp_root = _pytest_temp_root(workspace_root)
    if not temp_root.exists():
        return {
            "enabled": True,
            "status": "ok",
            "root": temp_root.as_posix(),
            "deleted": [],
            "bytes_removed": 0,
        }

    resolved_ttl_hours = DEFAULT_TEST_TEMP_TTL_HOURS if ttl_hours is None else ttl_hours
    resolved_max_mb = DEFAULT_TEST_TEMP_MAX_MB if max_mb is None else max_mb
    cutoff = (now_timestamp or datetime.now(UTC).timestamp()) - (resolved_ttl_hours * 60 * 60)
    max_bytes = int(resolved_max_mb * 1024 * 1024)

    entries = [
        item.resolve()
        for item in temp_root.iterdir()
        if item.is_dir() and item.name.startswith(PYTEST_TEMP_PREFIXES) and _is_safe_pytest_temp_child(item, temp_root)
    ]
    entries.sort(key=lambda item: item.stat().st_mtime)

    deleted: list[dict[str, object]] = []
    deleted_paths: set[Path] = set()

    for entry in entries:
        try:
            if entry.stat().st_mtime > cutoff:
                continue
        except OSError:
            continue
        result = _remove_pytest_temp_dir(entry, temp_root)
        deleted.append(result)
        if result["status"] == "deleted":
            deleted_paths.add(entry)

    remaining = [entry for entry in entries if entry not in deleted_paths and entry.exists()]
    total_bytes = sum(_directory_size_bytes(entry) for entry in remaining)
    for entry in remaining:
        if total_bytes <= max_bytes:
            break
        entry_size = _directory_size_bytes(entry)
        result = _remove_pytest_temp_dir(entry, temp_root)
        deleted.append(result)
        if result["status"] == "deleted":
            total_bytes -= entry_size

    return {
        "enabled": True,
        "status": "ok",
        "root": temp_root.as_posix(),
        "ttl_hours": resolved_ttl_hours,
        "max_mb": resolved_max_mb,
        "deleted": deleted,
        "bytes_removed": sum(int(item.get("bytes_removed") or 0) for item in deleted),
        "remaining_bytes": max(total_bytes, 0),
    }


def _parse_shard(value: str | None) -> tuple[int, int] | None:
    if value is None:
        return None
    if "/" not in value:
        raise ValueError("--shard must use N/M form")
    raw_index, raw_total = value.split("/", 1)
    index = int(raw_index)
    total = int(raw_total)
    if index < 1 or total < 1 or index > total:
        raise ValueError("--shard must satisfy 1 <= N <= M")
    return index, total


def _apply_shard(targets: Sequence[str], shard: tuple[int, int] | None) -> list[str]:
    if shard is None:
        return list(targets)
    index, total = shard
    return [target for position, target in enumerate(targets, start=1) if ((position - 1) % total) + 1 == index]


def select_matrix(suite: str, shard: str | None = None) -> MatrixSelection:
    parsed_shard = _parse_shard(shard)
    if suite == "unit":
        return MatrixSelection(suite=suite, targets=_apply_shard(UNIT_TARGETS, parsed_shard))
    if suite == "core":
        return MatrixSelection(suite=suite, targets=_apply_shard(CORE_TARGETS, parsed_shard))
    if suite == "integration":
        return MatrixSelection(suite=suite, targets=_apply_shard(INTEGRATION_TARGETS, parsed_shard))
    if suite == "slow":
        return MatrixSelection(suite=suite, targets=_apply_shard(SLOW_TARGETS, parsed_shard), run_slow=True)
    if suite == "commercial_fast":
        return MatrixSelection(suite=suite, targets=_apply_shard(COMMERCIAL_FAST_TARGETS, parsed_shard))
    if suite == "commercial_integration":
        return MatrixSelection(suite=suite, targets=_apply_shard(COMMERCIAL_INTEGRATION_TARGETS, parsed_shard))
    if suite == "commercial_cocos_browser":
        return MatrixSelection(
            suite=suite,
            targets=_apply_shard(COMMERCIAL_COCOS_BROWSER_TARGETS, parsed_shard),
            run_slow=True,
        )
    if suite == "commercial_provider_contract":
        return MatrixSelection(suite=suite, targets=_apply_shard(COMMERCIAL_PROVIDER_CONTRACT_TARGETS, parsed_shard))
    if suite == "full":
        targets = [*CORE_TARGETS, *INTEGRATION_TARGETS]
        return MatrixSelection(suite=suite, targets=_apply_shard(targets, parsed_shard))
    raise ValueError(f"unsupported suite: {suite}")


def build_pytest_command(
    *,
    suite: str,
    workspace_root: Path,
    shard: str | None = None,
    basetemp: Path | None = None,
) -> tuple[list[str], MatrixSelection, Path]:
    selection = select_matrix(suite, shard)
    resolved_basetemp = basetemp or _unique_basetemp(workspace_root)
    command = [
        sys.executable,
        "-m",
        "pytest",
        *selection.targets,
        "-q",
        "--tb=short",
        "--durations=20",
        f"--basetemp={resolved_basetemp.as_posix()}",
    ]
    if selection.run_slow:
        command.insert(3, "--run-slow")
    return command, selection, resolved_basetemp


def run_matrix(
    *,
    suite: str,
    workspace_root: Path,
    shard: str | None = None,
    dry_run: bool = False,
) -> dict[str, object]:
    started_at = datetime.now(UTC)
    pre_run_cleanup = (
        {"enabled": False, "status": "skipped", "reason": "dry_run"}
        if dry_run
        else prune_pytest_temp_workspace(
            workspace_root,
            ttl_hours=_float_env(TEST_TEMP_TTL_HOURS_ENV, DEFAULT_TEST_TEMP_TTL_HOURS),
            max_mb=_float_env(TEST_TEMP_MAX_MB_ENV, DEFAULT_TEST_TEMP_MAX_MB),
        )
    )
    command, selection, basetemp = build_pytest_command(
        suite=suite,
        workspace_root=workspace_root,
        shard=shard,
    )
    if dry_run:
        dry_run_cleanup = (
            _remove_pytest_temp_dir(basetemp, _pytest_temp_root(workspace_root))
            if _cleanup_enabled()
            else {"enabled": False, "status": "skipped", "reason": KEEP_TEST_TEMP_ENV}
        )
        return {
            "suite": suite,
            "shard": shard,
            "targets": selection.targets,
            "run_slow": selection.run_slow,
            "basetemp": basetemp.as_posix(),
            "command": command,
            "dry_run": True,
            "return_code": None,
            "cleanup": {
                "pre_run": pre_run_cleanup,
                "post_run": dry_run_cleanup,
                "kept_current_on_failure": False,
            },
        }
    result = subprocess.run(command, cwd=workspace_root, capture_output=True, text=True)
    finished_at = datetime.now(UTC)
    temp_root = _pytest_temp_root(workspace_root)
    if result.returncode == 0 and _cleanup_enabled():
        post_run_cleanup = _remove_pytest_temp_dir(basetemp, temp_root)
        post_success_prune = prune_pytest_temp_workspace(
            workspace_root,
            ttl_hours=_float_env(TEST_TEMP_TTL_HOURS_ENV, DEFAULT_TEST_TEMP_TTL_HOURS),
            max_mb=_float_env(TEST_TEMP_MAX_MB_ENV, DEFAULT_TEST_TEMP_MAX_MB),
        )
    elif result.returncode == 0:
        post_run_cleanup = {"enabled": False, "status": "skipped", "reason": KEEP_TEST_TEMP_ENV}
        post_success_prune = post_run_cleanup
    else:
        post_run_cleanup = {
            "enabled": _cleanup_enabled(),
            "status": "skipped",
            "reason": "test_failed",
            "kept_path": basetemp.as_posix(),
        }
        post_success_prune = {"status": "skipped", "reason": "test_failed"}
    return {
        "suite": suite,
        "shard": shard,
        "targets": selection.targets,
        "run_slow": selection.run_slow,
        "basetemp": basetemp.as_posix(),
        "command": command,
        "dry_run": False,
        "return_code": result.returncode,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_ms": int((finished_at - started_at).total_seconds() * 1000),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "cleanup": {
            "pre_run": pre_run_cleanup,
            "post_run": post_run_cleanup,
            "post_success_prune": post_success_prune,
            "kept_current_on_failure": result.returncode != 0,
        },
    }
