from __future__ import annotations

from pathlib import Path


def test_architecture_docs_define_graph_state_authority() -> None:
    index = Path("docs/architecture/README.md")
    authority = Path("docs/architecture/langgraph_runtime_notes.md")

    assert index.exists()
    assert authority.exists()

    source = authority.read_text(encoding="utf-8")
    for token in (
        "WorkflowGraphState",
        "OrchestrationPlanGraph",
        "WorkflowPipeline",
        "RunSnapshot",
        "OperatorActionReceipt",
        "AutomationLease",
        "packages/runtime_security/safe_command_runner.py",
    ):
        assert token in source

    assert "projection and checkpoint envelope" in source


def test_m85_langgraph_fit_matrix_and_boundary_contract_exist() -> None:
    notes = Path("docs/architecture/langgraph_runtime_notes.md")

    assert notes.exists()

    matrix_source = notes.read_text(encoding="utf-8")
    rows = [
        line
        for line in matrix_source.splitlines()
        if line.startswith("| ")
        and " | " in line
        and not line.startswith("| ---")
        and not line.startswith("| Capability Surface")
    ]
    assert len(rows) >= 10
    for token in (
        "`OrchestrationPlanGraph`",
        "`WorkflowPipeline`",
        "`cluster_router`",
        "`scheduler_authority`",
        "`interaction_catalog`",
        "Capability plane",
        "Repo mutation",
        "Test matrix",
        "`commercial_cocos_game`",
    ):
        assert token in matrix_source

    boundary_source = matrix_source
    for token in (
        "WorkflowGraphState",
        "WorkflowGraphNodeResult",
        "HumanApprovalInterrupt",
        "SideEffectLevel",
        "OperatorActionReceipt",
        "AutomationLease",
        "side_effect_before_interrupt=false",
        "workflowctl graph interrupt-preview",
        "provider-specific live proof",
        "Commercial game work remains a pressure test",
    ):
        assert token in boundary_source

    checkpoint_source = matrix_source
    for token in (
        "GraphCheckpointRecord",
        "GraphRepairDecision",
        "workflowctl graph fork",
        "retry_from_checkpoint",
        "request_human_review",
    ):
        assert token in checkpoint_source

    cluster_source = matrix_source
    for token in (
        "planner/implementer/reviewer/validator/evidence",
        "readiness_claim=unchanged",
        "write_set_conflict",
        "workflowctl graph multi-agent-run",
    ):
        assert token in cluster_source

    cocos_source = matrix_source
    for token in (
        "cocos_graph_pressure_test",
        "commercial_claim=pressure_test_only_not_commercial_ready",
        "technical_smoke_go",
        "production_scaffold_go",
        "commercial_playable_go=false",
    ):
        assert token in cocos_source
