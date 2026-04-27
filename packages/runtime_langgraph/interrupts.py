from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.contracts import HumanApprovalInterrupt, OperatorActionReceipt
from packages.core_domain.automation_lease import record_automation_lease_use, validate_automation_lease
from packages.core_domain.repositories import OperatorActionReceiptRepository
from packages.core_domain.service_operator_action_guard import OperatorActionGuard


GRAPH_HIGH_RISK_ACTION = "launch_execute"


def build_human_approval_interrupt(
    *,
    run_id: str,
    requested_action: str = GRAPH_HIGH_RISK_ACTION,
    requested_side_effect_level: str,
    write_set: list[str],
    workspace_root: str | Path,
    thread_id: str | None = None,
    checkpoint_id: str | None = None,
    operator_hint: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> HumanApprovalInterrupt:
    scope_payload = {
        "run_id": run_id,
        "checkpoint_id": checkpoint_id,
        "requested_action": requested_action,
        "requested_side_effect_level": requested_side_effect_level,
        "requested_write_set": sorted(str(item) for item in write_set),
        "workspace_root": Path(workspace_root).resolve().as_posix(),
    }
    return HumanApprovalInterrupt(
        run_id=run_id,
        thread_id=thread_id,
        checkpoint_id=checkpoint_id,
        requested_action=requested_action,
        scope_payload=scope_payload,
        write_set=sorted(str(item) for item in write_set),
        risk_level="high",
        operator_hint=operator_hint
        or "Approve only if the requested side effect and write_set match the current graph handoff.",
        idempotent_resume_contract={
            "resume_requires": "scope_bound_receipt_or_automation_lease",
            "side_effect_before_interrupt": False,
            "safe_to_retry": True,
        },
        metadata=metadata or {},
    )


def resume_interrupt_with_receipt(
    *,
    interrupt: HumanApprovalInterrupt,
    receipt_id: str | None,
    receipt_repository: OperatorActionReceiptRepository,
    workspace_root: str | Path,
) -> dict[str, Any]:
    guard = OperatorActionGuard(receipt_repository, workspace_root=workspace_root)
    receipt: OperatorActionReceipt = guard.consume_receipt(
        receipt_id=receipt_id,
        action_type=interrupt.requested_action,
        workspace_root=workspace_root,
        scope_payload=interrupt.scope_payload,
    )
    return {
        "status": "approved",
        "authorization": "operator_action_receipt",
        "receipt_id": receipt.receipt_id,
        "interrupt_id": interrupt.interrupt_id,
        "requested_action": interrupt.requested_action,
    }


def resume_interrupt_with_automation_lease(
    *,
    interrupt: HumanApprovalInterrupt,
    lease_id: str | None,
    workspace_root: str | Path,
) -> dict[str, Any]:
    if not lease_id:
        raise ValueError("automation lease id is required")
    lease = validate_automation_lease(
        workspace_root=workspace_root,
        lease_id=lease_id,
        action=interrupt.requested_action,
        write_set=interrupt.write_set,
    )
    record_automation_lease_use(workspace_root, lease.lease_id, action=interrupt.requested_action)
    return {
        "status": "approved",
        "authorization": "automation_lease",
        "lease_id": lease.lease_id,
        "interrupt_id": interrupt.interrupt_id,
        "requested_action": interrupt.requested_action,
    }
