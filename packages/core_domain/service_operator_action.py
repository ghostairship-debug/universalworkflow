from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from packages.contracts import OperatorActionReceipt

if TYPE_CHECKING:
    from packages.core_domain.services import OrchestratorService


class OperatorActionServiceMixin:
    def issue_operator_action_receipt(
        self: "OrchestratorService",
        *,
        action_type: str,
        risk_level: str = "high",
        operator_id: str = "local_operator",
        requested_write_set: list[str] | None = None,
        scope_payload: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OperatorActionReceipt:
        return self.operator_action_guard.issue_receipt(
            action_type=action_type,
            risk_level=risk_level,
            operator_id=operator_id,
            requested_write_set=requested_write_set,
            scope_payload=scope_payload,
            ttl_seconds=ttl_seconds,
            metadata=metadata,
        )

    def consume_operator_action_receipt(
        self: "OrchestratorService",
        *,
        receipt_id: str | None,
        action_type: str,
        scope_payload: dict[str, Any] | None = None,
    ) -> OperatorActionReceipt:
        return self.operator_action_guard.consume_receipt(
            receipt_id=receipt_id,
            action_type=action_type,
            scope_payload=scope_payload,
            workspace_root=Path(str(self.effective_config.get("workspace", {}).get("root") or Path.cwd())).resolve(),
        )
