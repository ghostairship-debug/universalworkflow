from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from packages.contracts import OperatorActionReceipt
from packages.core_domain.errors import EntityNotFoundError, OperatorActionReceiptError
from packages.core_domain.repositories import OperatorActionReceiptRepository


HIGH_RISK_ACTIONS = {
    "resume_run",
    "approve_run",
    "reject_run",
    "cancel_run",
    "batch_resume_runs",
    "confirm_chat_action",
    "launch_execute",
    "reconcile_apply",
    "watchdog_auto_apply",
}

ORDER_INSENSITIVE_SCOPE_LISTS = {"requested_write_set", "run_ids", "write_set", "read_set"}


def _normalize_scope_value(value: Any, *, key: str | None = None) -> Any:
    if isinstance(value, Path):
        return value.resolve().as_posix()
    if isinstance(value, dict):
        return {str(item_key): _normalize_scope_value(item_value, key=str(item_key)) for item_key, item_value in sorted(value.items())}
    if isinstance(value, (list, tuple, set)):
        normalized = [_normalize_scope_value(item) for item in value]
        if key in ORDER_INSENSITIVE_SCOPE_LISTS:
            return sorted(str(item) for item in normalized)
        return normalized
    return value


def canonicalize_operator_action_scope(scope_payload: dict[str, Any] | None) -> dict[str, Any]:
    return _normalize_scope_value(dict(scope_payload or {}))


def operator_action_scope_hash(scope_payload: dict[str, Any] | None) -> str:
    canonical_payload = canonicalize_operator_action_scope(scope_payload)
    encoded = json.dumps(canonical_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class OperatorActionGuard:
    def __init__(
        self,
        repository: OperatorActionReceiptRepository,
        *,
        workspace_root: str | Path,
        default_ttl_seconds: int = 300,
    ) -> None:
        self.repository = repository
        self.workspace_root = Path(workspace_root).resolve()
        self.default_ttl_seconds = default_ttl_seconds

    def issue_receipt(
        self,
        *,
        action_type: str,
        risk_level: str = "high",
        operator_id: str = "local_operator",
        requested_write_set: list[str] | None = None,
        scope_payload: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OperatorActionReceipt:
        now = datetime.now(UTC)
        normalized_scope_payload = canonicalize_operator_action_scope(scope_payload)
        if requested_write_set:
            normalized_scope_payload.setdefault("requested_write_set", sorted(str(item) for item in requested_write_set))
        receipt = OperatorActionReceipt(
            action_type=action_type,
            workspace_root=self.workspace_root.as_posix(),
            risk_level=risk_level,
            operator_id=operator_id,
            requested_write_set=list(requested_write_set or []),
            scope_hash=operator_action_scope_hash(normalized_scope_payload),
            scope_payload=normalized_scope_payload,
            expires_at=now + timedelta(seconds=ttl_seconds or self.default_ttl_seconds),
            audit_timestamp=now,
            metadata=metadata or {},
        )
        return self.repository.create(receipt)

    def consume_receipt(
        self,
        *,
        receipt_id: str | None,
        action_type: str,
        workspace_root: str | Path | None = None,
        scope_payload: dict[str, Any] | None = None,
    ) -> OperatorActionReceipt:
        if not receipt_id:
            raise OperatorActionReceiptError(
                "operator action receipt is required",
                {"action_type": action_type, "required_for": sorted(HIGH_RISK_ACTIONS)},
            )
        receipt = self.repository.get(receipt_id)
        if receipt is None:
            raise EntityNotFoundError("operator_action_receipt", receipt_id)
        expected_root = Path(workspace_root or self.workspace_root).resolve()
        receipt_root = Path(receipt.workspace_root).resolve()
        now = datetime.now(UTC)
        if receipt.action_type != action_type:
            raise OperatorActionReceiptError(
                "operator action receipt action_type mismatch",
                {"receipt_id": receipt_id, "expected": action_type, "actual": receipt.action_type},
            )
        if receipt_root != expected_root:
            raise OperatorActionReceiptError(
                "operator action receipt workspace_root mismatch",
                {"receipt_id": receipt_id, "expected": expected_root.as_posix(), "actual": receipt_root.as_posix()},
            )
        if receipt.status != "issued":
            raise OperatorActionReceiptError(
                "operator action receipt is not issued",
                {"receipt_id": receipt_id, "status": receipt.status},
            )
        if action_type in HIGH_RISK_ACTIONS:
            if not receipt.scope_hash:
                raise OperatorActionReceiptError(
                    "operator action receipt is missing scope_hash",
                    {"receipt_id": receipt_id, "action_type": action_type},
                )
            actual_scope_hash = operator_action_scope_hash(scope_payload)
            if actual_scope_hash != receipt.scope_hash:
                raise OperatorActionReceiptError(
                    "operator action receipt scope_hash mismatch",
                    {
                        "receipt_id": receipt_id,
                        "action_type": action_type,
                        "expected_scope_hash": receipt.scope_hash,
                        "actual_scope_hash": actual_scope_hash,
                        "expected_scope_payload": receipt.scope_payload,
                        "actual_scope_payload": canonicalize_operator_action_scope(scope_payload),
                    },
                )
        expires_at = receipt.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= now:
            raise OperatorActionReceiptError(
                "operator action receipt expired",
                {"receipt_id": receipt_id, "expires_at": receipt.expires_at.isoformat()},
            )
        consumed = self.repository.mark_consumed(receipt_id, consumed_at=now.isoformat())
        if consumed is None:
            raise OperatorActionReceiptError(
                "operator action receipt could not be consumed",
                {"receipt_id": receipt_id},
            )
        return consumed
