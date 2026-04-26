from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from packages.contracts import AutomationLease, AutomationLeaseStatus
from packages.core_domain.errors import OperatorActionReceiptError


DEFAULT_DENIED_ACTIONS = [
    "git_push",
    "create_pr",
    "publish",
    "secrets",
    "workspace_root_expand",
]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _store_path(workspace_root: str | Path) -> Path:
    return Path(workspace_root).resolve() / "state" / "automation_leases.json"


def _read_store(workspace_root: str | Path) -> dict[str, dict]:
    path = _store_path(workspace_root)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8") or "{}")


def _write_store(workspace_root: str | Path, payload: dict[str, dict]) -> None:
    path = _store_path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _normalize_write_set(paths: list[str]) -> list[str]:
    return sorted(str(Path(item).as_posix()).lstrip("./") for item in paths)


def create_automation_lease(
    *,
    workspace_root: str | Path,
    allowed_actions: list[str],
    write_set_allowlist: list[str] | None = None,
    denied_actions: list[str] | None = None,
    ttl_seconds: int = 3600,
    max_resume_count: int = 20,
    max_fix_iterations: int = 2,
    metadata: dict | None = None,
) -> AutomationLease:
    lease = AutomationLease(
        workspace_root=Path(workspace_root).resolve().as_posix(),
        allowed_actions=sorted(set(allowed_actions)),
        denied_actions=sorted(set(denied_actions or DEFAULT_DENIED_ACTIONS)),
        write_set_allowlist=_normalize_write_set(list(write_set_allowlist or [])),
        expires_at=_utc_now() + timedelta(seconds=ttl_seconds),
        max_resume_count=max_resume_count,
        max_fix_iterations=max_fix_iterations,
        metadata=metadata or {},
    )
    store = _read_store(workspace_root)
    store[lease.lease_id] = lease.model_dump(mode="json")
    _write_store(workspace_root, store)
    return lease


def list_automation_leases(workspace_root: str | Path) -> list[AutomationLease]:
    return [AutomationLease.model_validate(item) for item in _read_store(workspace_root).values()]


def get_automation_lease(workspace_root: str | Path, lease_id: str) -> AutomationLease | None:
    payload = _read_store(workspace_root).get(lease_id)
    return AutomationLease.model_validate(payload) if payload else None


def revoke_automation_lease(workspace_root: str | Path, lease_id: str) -> AutomationLease:
    store = _read_store(workspace_root)
    if lease_id not in store:
        raise OperatorActionReceiptError("automation lease not found", {"lease_id": lease_id})
    lease = AutomationLease.model_validate(store[lease_id])
    lease = AutomationLease.model_validate(
        {
            **lease.model_dump(mode="json"),
            "status": AutomationLeaseStatus.revoked,
            "revoked_at": _utc_now().isoformat(),
        }
    )
    store[lease_id] = lease.model_dump(mode="json")
    _write_store(workspace_root, store)
    return lease


def validate_automation_lease(
    *,
    workspace_root: str | Path,
    lease_id: str,
    action: str,
    write_set: list[str] | None = None,
) -> AutomationLease:
    lease = get_automation_lease(workspace_root, lease_id)
    if lease is None:
        raise OperatorActionReceiptError("automation lease not found", {"lease_id": lease_id})
    if Path(lease.workspace_root).resolve() != Path(workspace_root).resolve():
        raise OperatorActionReceiptError(
            "automation lease workspace_root mismatch",
            {"lease_id": lease_id, "workspace_root": lease.workspace_root},
        )
    if lease.status != AutomationLeaseStatus.active:
        raise OperatorActionReceiptError("automation lease is not active", {"lease_id": lease_id, "status": lease.status})
    expires_at = lease.expires_at if lease.expires_at.tzinfo else lease.expires_at.replace(tzinfo=UTC)
    if expires_at <= _utc_now():
        raise OperatorActionReceiptError("automation lease expired", {"lease_id": lease_id})
    if action in lease.denied_actions or action not in lease.allowed_actions:
        raise OperatorActionReceiptError("automation lease does not allow action", {"lease_id": lease_id, "action": action})
    requested = _normalize_write_set(list(write_set or []))
    allowlist = set(_normalize_write_set(lease.write_set_allowlist))
    if requested and allowlist and not set(requested).issubset(allowlist):
        raise OperatorActionReceiptError(
            "automation lease write_set outside allowlist",
            {"lease_id": lease_id, "requested_write_set": requested, "write_set_allowlist": sorted(allowlist)},
        )
    if action in {"resume_run", "batch_resume_runs"} and lease.max_resume_count and lease.resume_count >= lease.max_resume_count:
        raise OperatorActionReceiptError("automation lease resume count exhausted", {"lease_id": lease_id})
    return lease


def record_automation_lease_use(workspace_root: str | Path, lease_id: str, *, action: str) -> AutomationLease:
    store = _read_store(workspace_root)
    if lease_id not in store:
        raise OperatorActionReceiptError("automation lease not found", {"lease_id": lease_id})
    lease = AutomationLease.model_validate(store[lease_id])
    updates = lease.model_dump(mode="json")
    if action in {"resume_run", "batch_resume_runs"}:
        updates["resume_count"] = int(updates.get("resume_count") or 0) + 1
    store[lease_id] = updates
    _write_store(workspace_root, store)
    return AutomationLease.model_validate(updates)
