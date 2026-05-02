from __future__ import annotations

from packages.contracts import TaskCard
from packages.core_domain.task_card_store import (
    task_card_execution_eligibility,
    task_card_quality_report,
    task_card_requirement_coverage_status,
)


def _rich_task_card(*, status: str, metadata: dict | None = None) -> TaskCard:
    return TaskCard(
        run_id="run_task_card_lifecycle",
        task_card_id=f"tc_{status}",
        title="Lifecycle gated task card",
        description="A complete task card used to verify DB lifecycle execution gating.",
        goal="Verify that quality-passing task cards still cannot execute unless the DB lifecycle is active or approved.",
        write_set=["packages/core_domain/task_card_store.py"],
        read_set=["CURRENT_DEVELOPMENT_WORKFLOW.md"],
        test_commands=["python -m pytest tests/test_task_card_store.py -q"],
        acceptance_criteria=["quality passes", "lifecycle gate is enforced"],
        evidence_requirements=["quality_report_v2", "lifecycle_blocker"],
        blocking_conditions=["draft_card_executed"],
        model_guidance=["Do not execute draft, archived, blocked, failed, running, or completed cards as new work."],
        execution_mode="same_project_patch",
        risk_level="high",
        status=status,
        metadata=metadata or {},
    )


def test_draft_task_card_cannot_execute_even_if_quality_passed() -> None:
    report = task_card_quality_report([_rich_task_card(status="draft")])

    assert report["schema_version"] == "m108_task_card_quality_v2"
    assert report["go_no_go"] == "NO-GO"
    assert report["quality_blocked_count"] == 0
    assert report["lifecycle_blocked_count"] == 1
    assert report["execution_eligible_count"] == 0
    assert report["task_cards"][0]["quality_status"] == "passed"
    assert report["task_cards"][0]["execution_eligible"] is False
    assert report["task_cards"][0]["lifecycle_issues"][0]["code"] == "task_card_not_active"


def test_active_task_card_quality_report_is_execution_eligible() -> None:
    report = task_card_quality_report([_rich_task_card(status="active")])

    assert report["go_no_go"] == "GO"
    assert report["execution_eligible_count"] == 1
    assert report["task_cards"][0]["lifecycle_status"] == "active"
    assert report["task_cards"][0]["execution_eligible"] is True


def test_completed_task_card_is_not_new_execution_eligible() -> None:
    eligibility = task_card_execution_eligibility(_rich_task_card(status="completed"))

    assert eligibility["execution_eligible"] is False
    assert eligibility["blockers"] == ["task_card_already_completed"]


def test_requirement_coverage_required_card_without_req_ids_is_quality_blocked() -> None:
    card = _rich_task_card(status="active", metadata={"requirement_coverage_required": True})
    report = task_card_quality_report([card])

    assert report["go_no_go"] == "NO-GO"
    assert report["quality_blocked_count"] == 1
    assert report["requirement_coverage_blocked_count"] == 1
    assert report["task_cards"][0]["requirement_coverage_status"] == "blocked"
    assert report["task_cards"][0]["quality_issues"][0]["code"] == "requirement_coverage_missing"


def test_requirement_coverage_requires_all_required_req_ids() -> None:
    card = _rich_task_card(
        status="active",
        metadata={
            "requirement_coverage_required": True,
            "required_requirement_ids": ["REQ-1", "REQ-2"],
            "covered_requirement_ids": ["REQ-1"],
        },
    )
    eligibility = task_card_execution_eligibility(card)

    assert eligibility["execution_eligible"] is False
    assert eligibility["quality_issues"][0]["code"] == "requirement_coverage_incomplete"


def test_requirement_coverage_complete_card_is_execution_eligible() -> None:
    card = _rich_task_card(
        status="active",
        metadata={
            "requirement_coverage_required": True,
            "required_requirement_ids": ["REQ-1"],
            "covered_requirement_ids": ["REQ-1"],
        },
    )

    assert task_card_requirement_coverage_status(card) == "passed"
    assert task_card_execution_eligibility(card)["execution_eligible"] is True


def test_source_requirement_omission_blocks_quality() -> None:
    card = _rich_task_card(status="active", metadata={"omitted_requirement_ids": ["REQ-2"]})
    report = task_card_quality_report([card])

    assert report["go_no_go"] == "NO-GO"
    assert report["task_cards"][0]["quality_issues"][0]["code"] == "source_requirement_omitted"


def test_human_visible_cli_required_card_without_mode_is_quality_blocked() -> None:
    card = _rich_task_card(
        status="active",
        metadata={"human_visible_cli_required": True},
    )
    report = task_card_quality_report([card])

    assert report["go_no_go"] == "NO-GO"
    assert report["task_cards"][0]["quality_issues"][0]["code"] == "human_visible_cli_required"


def test_human_visible_cli_mode_satisfies_quality_requirement() -> None:
    card = _rich_task_card(
        status="active",
        metadata={
            "human_visible_cli_required": True,
            "execution_visibility_mode": "human_visible_cli_enforced",
        },
    )

    assert task_card_execution_eligibility(card)["execution_eligible"] is True
