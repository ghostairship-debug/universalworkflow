from __future__ import annotations

from typing import Any


def _normalize_path(path: str) -> str:
    normalized = str(path).strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    return normalized.rstrip("/").lower()


def _run_write_set(contract: dict[str, Any]) -> list[str]:
    raw_write_set = contract.get("write_set") or []
    return sorted({_normalize_path(str(item)) for item in raw_write_set if str(item).strip()})


def build_parallel_batch_plan(
    run_contracts: list[dict[str, Any]],
    *,
    requested_max_workers: int | None,
    dirty_paths: list[str] | None = None,
    sqlite_ready: bool = True,
    sqlite_error: str | None = None,
) -> dict[str, Any]:
    member_count = len(run_contracts)
    requested_workers = max(1, int(requested_max_workers or member_count)) if member_count else 0
    effective_workers = min(requested_workers, member_count) if member_count else 0
    degraded_reasons: list[str] = []
    write_set_by_path: dict[str, list[str]] = {}
    write_set_by_run: dict[str, list[str]] = {}

    for contract in run_contracts:
        run_id = str(contract.get("run_id") or "")
        write_set = _run_write_set(contract)
        write_set_by_run[run_id] = write_set
        for path in write_set:
            write_set_by_path.setdefault(path, []).append(run_id)

    write_set_conflicts = [
        {"path": path, "run_ids": sorted(set(run_ids))}
        for path, run_ids in sorted(write_set_by_path.items())
        if len(set(run_ids)) > 1
    ]
    if write_set_conflicts:
        degraded_reasons.append("write_set_conflict")

    dirty_set = {_normalize_path(path) for path in (dirty_paths or []) if str(path).strip()}
    dirty_write_set_paths = sorted(path for path in dirty_set if path in write_set_by_path)
    if dirty_write_set_paths:
        degraded_reasons.append("dirty_write_set")

    if not sqlite_ready:
        degraded_reasons.append("sqlite_lock_detected")

    if member_count <= 1:
        execution_mode = "serial_single_member"
        barrier_enabled = False
        effective_workers = member_count
    elif degraded_reasons:
        execution_mode = "serial_degraded"
        barrier_enabled = False
        effective_workers = 1
    elif effective_workers <= 1:
        execution_mode = "serial_requested"
        barrier_enabled = False
    else:
        execution_mode = "parallel"
        barrier_enabled = True

    return {
        "schema_version": "m71_parallel_batch_contract_v1",
        "member_count": member_count,
        "requested_max_workers": requested_max_workers,
        "effective_max_workers": effective_workers,
        "execution_mode": execution_mode,
        "barrier_enabled": barrier_enabled,
        "degraded_to_serial": execution_mode == "serial_degraded",
        "degraded_reasons": degraded_reasons,
        "audit": {
            "run_contracts": run_contracts,
            "write_set_by_run": write_set_by_run,
            "write_set_conflicts": write_set_conflicts,
            "dirty_write_set_paths": dirty_write_set_paths,
            "sqlite_ready": sqlite_ready,
            "sqlite_error": sqlite_error,
        },
    }


def build_partial_failure_resume(
    *,
    run_ids: list[str],
    errors: list[dict[str, Any]],
    requested_max_workers: int | None,
) -> dict[str, Any]:
    failed_run_ids = sorted({str(error["run_id"]) for error in errors if error.get("run_id")})
    if not failed_run_ids:
        return {
            "enabled": False,
            "failed_run_ids": [],
            "recommended_max_workers": 0,
            "resume_command": None,
        }
    recommended_max_workers = min(max(1, int(requested_max_workers or len(failed_run_ids))), len(failed_run_ids))
    return {
        "enabled": True,
        "failed_run_ids": failed_run_ids,
        "completed_run_ids": sorted(set(str(run_id) for run_id in run_ids) - set(failed_run_ids)),
        "recommended_max_workers": recommended_max_workers,
        "resume_command": (
            "workflowctl run batch-resume "
            + " ".join(failed_run_ids)
            + f" --max-workers {recommended_max_workers}"
        ),
    }
