from __future__ import annotations

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


@dataclass(frozen=True)
class MatrixSelection:
    suite: str
    targets: list[str]
    run_slow: bool = False


def _unique_basetemp(workspace_root: Path) -> Path:
    root = workspace_root / "state" / ".pytest-tmp-workflow"
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="matrix-", dir=root)).resolve()


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
    command, selection, basetemp = build_pytest_command(
        suite=suite,
        workspace_root=workspace_root,
        shard=shard,
    )
    if dry_run:
        return {
            "suite": suite,
            "shard": shard,
            "targets": selection.targets,
            "run_slow": selection.run_slow,
            "basetemp": basetemp.as_posix(),
            "command": command,
            "dry_run": True,
            "return_code": None,
        }
    result = subprocess.run(command, cwd=workspace_root, capture_output=True, text=True)
    finished_at = datetime.now(UTC)
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
    }
