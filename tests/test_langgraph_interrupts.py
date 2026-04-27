from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from apps.operator_cli.main import app
from packages.contracts import HumanApprovalInterrupt, SideEffectLevel
from packages.core_domain.automation_lease import create_automation_lease
from packages.core_domain.db import migrate
from packages.core_domain.errors import OperatorActionReceiptError
from packages.core_domain.repositories import OperatorActionReceiptRepository
from packages.core_domain.service_operator_action_guard import OperatorActionGuard
from packages.runtime_langgraph.execution_kernel import run_graph_with_side_effect_policy
from packages.runtime_langgraph.approval_graph import start_human_approval_graph
from packages.runtime_langgraph.interrupts import (
    build_human_approval_interrupt,
    resume_interrupt_with_automation_lease,
    resume_interrupt_with_receipt,
)


def _receipt_guard(tmp_path: Path) -> OperatorActionGuard:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    return OperatorActionGuard(OperatorActionReceiptRepository(db_path), workspace_root=tmp_path)


def test_human_approval_interrupt_is_json_serializable(tmp_path: Path) -> None:
    interrupt = build_human_approval_interrupt(
        run_id="run_graph",
        requested_side_effect_level=SideEffectLevel.repo_mutation,
        write_set=["docs/example.md"],
        workspace_root=tmp_path,
        thread_id="thread_1",
        checkpoint_id="checkpoint_1",
    )

    payload = interrupt.model_dump(mode="json")
    assert json.loads(json.dumps(payload))["status"] == "pending"
    assert payload["receipt_required"] is True
    assert payload["idempotent_resume_contract"]["side_effect_before_interrupt"] is False


def test_graph_high_risk_path_returns_human_interrupt_before_side_effect(tmp_path: Path) -> None:
    payload = run_graph_with_side_effect_policy(
        goal="Apply repo mutation",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "evidence",
        requested_side_effect_level=SideEffectLevel.repo_mutation,
    )

    assert payload["status"] == "blocked"
    interrupt = HumanApprovalInterrupt.model_validate(payload["human_interrupt"])
    assert interrupt.status == "pending"
    assert interrupt.requested_action == "launch_execute"
    assert interrupt.idempotent_resume_contract["side_effect_before_interrupt"] is False
    assert interrupt.scope_payload["requested_side_effect_level"] == "repo_mutation"


def test_interrupt_resume_rejects_missing_or_wrong_receipt(tmp_path: Path) -> None:
    guard = _receipt_guard(tmp_path)
    interrupt = build_human_approval_interrupt(
        run_id="run_graph",
        requested_side_effect_level=SideEffectLevel.repo_mutation,
        write_set=["docs/example.md"],
        workspace_root=tmp_path,
        checkpoint_id="checkpoint_1",
    )

    with pytest.raises(OperatorActionReceiptError):
        resume_interrupt_with_receipt(
            interrupt=interrupt,
            receipt_id=None,
            receipt_repository=guard.repository,
            workspace_root=tmp_path,
        )

    wrong = guard.issue_receipt(
        action_type=interrupt.requested_action,
        scope_payload={**interrupt.scope_payload, "checkpoint_id": "wrong_checkpoint"},
        requested_write_set=interrupt.write_set,
    )
    with pytest.raises(OperatorActionReceiptError, match="scope_hash mismatch"):
        resume_interrupt_with_receipt(
            interrupt=interrupt,
            receipt_id=wrong.receipt_id,
            receipt_repository=guard.repository,
            workspace_root=tmp_path,
        )


def test_interrupt_resume_accepts_scope_bound_receipt(tmp_path: Path) -> None:
    guard = _receipt_guard(tmp_path)
    interrupt = build_human_approval_interrupt(
        run_id="run_graph",
        requested_side_effect_level=SideEffectLevel.repo_mutation,
        write_set=["docs/example.md"],
        workspace_root=tmp_path,
        checkpoint_id="checkpoint_1",
    )
    receipt = guard.issue_receipt(
        action_type=interrupt.requested_action,
        scope_payload=interrupt.scope_payload,
        requested_write_set=interrupt.write_set,
    )

    result = resume_interrupt_with_receipt(
        interrupt=interrupt,
        receipt_id=receipt.receipt_id,
        receipt_repository=guard.repository,
        workspace_root=tmp_path,
    )

    assert result["status"] == "approved"
    assert result["authorization"] == "operator_action_receipt"
    assert guard.repository.get(receipt.receipt_id).status == "consumed"


def test_interrupt_resume_accepts_matching_automation_lease_and_rejects_write_set_mismatch(tmp_path: Path) -> None:
    interrupt = build_human_approval_interrupt(
        run_id="run_graph",
        requested_side_effect_level=SideEffectLevel.repo_mutation,
        write_set=["docs/example.md"],
        workspace_root=tmp_path,
        checkpoint_id="checkpoint_1",
    )
    wrong_lease = create_automation_lease(
        workspace_root=tmp_path,
        allowed_actions=[interrupt.requested_action],
        write_set_allowlist=["docs/other.md"],
    )
    with pytest.raises(OperatorActionReceiptError, match="write_set outside allowlist"):
        resume_interrupt_with_automation_lease(
            interrupt=interrupt,
            lease_id=wrong_lease.lease_id,
            workspace_root=tmp_path,
        )

    lease = create_automation_lease(
        workspace_root=tmp_path,
        allowed_actions=[interrupt.requested_action],
        write_set_allowlist=interrupt.write_set,
    )
    result = resume_interrupt_with_automation_lease(
        interrupt=interrupt,
        lease_id=lease.lease_id,
        workspace_root=tmp_path,
    )

    assert result["status"] == "approved"
    assert result["authorization"] == "automation_lease"


def test_graph_cli_interrupt_preview_emits_pending_interrupt(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "graph",
            "interrupt-preview",
            "--goal",
            "Patch repo",
            "--side-effect",
            "repo_mutation",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "blocked"
    assert payload["human_interrupt"]["status"] == "pending"
    assert payload["human_interrupt"]["receipt_required"] is True
    assert payload["langgraph_interrupt"]["used_dynamic_interrupt"] is True
    assert payload["persistent_checkpoint"]["metadata"]["graph_kind"] == "human_approval_interrupt"


def test_graph_cli_resume_uses_langgraph_command_for_dynamic_interrupt(tmp_path: Path) -> None:
    start = start_human_approval_graph(
        goal="Dynamic approval",
        requested_side_effect_level="repo_mutation",
        workspace_root=tmp_path,
    )
    lease = create_automation_lease(
        workspace_root=tmp_path,
        allowed_actions=["launch_execute"],
        write_set_allowlist=start["human_interrupt"]["write_set"],
    )
    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "graph",
            "resume",
            "--checkpoint-id",
            start["persistent_checkpoint"]["checkpoint_id"],
            "--lease-id",
            lease.lease_id,
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "approved_for_resume"
    assert payload["langgraph_resume"]["status"] == "approved_for_resume"
    assert payload["langgraph_resume"]["langgraph_resume"]["used_command_resume"] is True
