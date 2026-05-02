from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from packages.contracts import TaskCard
from packages.core_domain.repositories import TaskRepository

RISK_LEVELS = {"low", "medium", "high"}
EXECUTION_ELIGIBLE_STATUSES = {"active", "approved"}
_NON_EXECUTABLE_STATUS_ISSUES = {
    "": "task_card_not_active",
    "draft": "task_card_not_active",
    "archived": "task_card_archived",
    "blocked": "task_card_blocked",
    "failed": "task_card_failed",
    "running": "task_card_already_running",
    "completed": "task_card_already_completed",
}


def task_card_quality_issues(task_card: TaskCard) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not task_card.title.strip():
        issues.append({"code": "missing_title", "field": "title"})
    if len((task_card.goal or task_card.description).strip()) < 40:
        issues.append({"code": "thin_goal", "field": "goal"})
    if not task_card.write_set:
        issues.append({"code": "missing_write_set", "field": "write_set"})
    if len(task_card.acceptance_criteria) < 2:
        issues.append({"code": "thin_acceptance", "field": "acceptance_criteria"})
    if not task_card.test_commands:
        issues.append({"code": "missing_tests", "field": "test_commands"})
    if not task_card.evidence_requirements:
        issues.append({"code": "missing_evidence_requirements", "field": "evidence_requirements"})
    if not task_card.blocking_conditions:
        issues.append({"code": "missing_blocking_conditions", "field": "blocking_conditions"})
    if not task_card.model_guidance:
        issues.append({"code": "missing_model_guidance", "field": "model_guidance"})
    if task_card.risk_level not in RISK_LEVELS:
        issues.append({"code": "invalid_risk_level", "field": "risk_level", "value": task_card.risk_level})
    issues.extend(task_card_requirement_coverage_issues(task_card))
    return issues


def task_card_requirement_coverage_issues(task_card: TaskCard) -> list[dict[str, Any]]:
    metadata = task_card.metadata if isinstance(task_card.metadata, dict) else {}
    required_ids = _metadata_string_list(metadata.get("required_requirement_ids"))
    covered_ids = _metadata_string_list(
        metadata.get("covered_requirement_ids") or metadata.get("source_requirement_ids") or metadata.get("requirement_ids")
    )
    coverage_required = _truthy(metadata.get("requirement_coverage_required")) or bool(required_ids)
    if not coverage_required:
        return []
    if not covered_ids:
        return [
            {
                "code": "requirement_coverage_missing",
                "field": "metadata.covered_requirement_ids",
            }
        ]
    missing = [req_id for req_id in required_ids if req_id not in set(covered_ids)]
    if missing:
        return [
            {
                "code": "requirement_coverage_incomplete",
                "field": "metadata.covered_requirement_ids",
                "missing_requirement_ids": missing,
            }
        ]
    return []


def task_card_requirement_coverage_status(task_card: TaskCard) -> str:
    metadata = task_card.metadata if isinstance(task_card.metadata, dict) else {}
    required_ids = _metadata_string_list(metadata.get("required_requirement_ids"))
    coverage_required = _truthy(metadata.get("requirement_coverage_required")) or bool(required_ids)
    if not coverage_required:
        return "not_required"
    return "passed" if not task_card_requirement_coverage_issues(task_card) else "blocked"


def task_card_quality_status(task_card: TaskCard) -> str:
    return "passed" if not task_card_quality_issues(task_card) else "blocked"


def task_card_lifecycle_status(task_card: TaskCard) -> str:
    return str(task_card.status or "draft").strip().lower()


def task_card_execution_eligibility(task_card: TaskCard) -> dict[str, Any]:
    lifecycle_status = task_card_lifecycle_status(task_card)
    lifecycle_issues: list[dict[str, Any]] = []
    if lifecycle_status not in EXECUTION_ELIGIBLE_STATUSES:
        lifecycle_issues.append(
            {
                "code": _NON_EXECUTABLE_STATUS_ISSUES.get(lifecycle_status, "task_card_lifecycle_not_executable"),
                "field": "status",
                "value": lifecycle_status or task_card.status,
            }
        )
    quality_issues = task_card_quality_issues(task_card)
    return {
        "execution_eligible": not quality_issues and not lifecycle_issues,
        "lifecycle_status": lifecycle_status,
        "quality_status": "passed" if not quality_issues else "blocked",
        "blockers": [issue["code"] for issue in lifecycle_issues],
        "issues": lifecycle_issues,
        "quality_issues": quality_issues,
    }


def task_card_quality_report(task_cards: Iterable[TaskCard]) -> dict[str, Any]:
    cards = list(task_cards)
    items = []
    for card in cards:
        quality_issues = task_card_quality_issues(card)
        requirement_coverage_issues = task_card_requirement_coverage_issues(card)
        eligibility = task_card_execution_eligibility(card)
        quality_status = "passed" if not quality_issues else "blocked"
        lifecycle_issues = list(eligibility["issues"])
        items.append(
            {
                "task_card_id": card.task_card_id,
                "title": card.title,
                "status": quality_status,
                "quality_status": quality_status,
                "lifecycle_status": eligibility["lifecycle_status"],
                "execution_eligible": bool(eligibility["execution_eligible"]),
                "issues": [*quality_issues, *lifecycle_issues],
                "quality_issues": quality_issues,
                "lifecycle_issues": lifecycle_issues,
                "requirement_coverage_status": task_card_requirement_coverage_status(card),
                "requirement_coverage_issues": requirement_coverage_issues,
            }
        )
    quality_blocked = [item for item in items if item["quality_status"] != "passed"]
    lifecycle_blocked = [item for item in items if item["lifecycle_issues"]]
    requirement_coverage_blocked = [item for item in items if item["requirement_coverage_issues"]]
    eligible = [item for item in items if item["execution_eligible"]]
    return {
        "schema_version": "m108_task_card_quality_v2",
        "task_card_count": len(cards),
        "blocked_count": len(cards) - len(eligible),
        "quality_blocked_count": len(quality_blocked),
        "lifecycle_blocked_count": len(lifecycle_blocked),
        "requirement_coverage_blocked_count": len(requirement_coverage_blocked),
        "execution_eligible_count": len(eligible),
        "go_no_go": "GO" if cards and len(eligible) == len(cards) else "NO-GO",
        "task_cards": items,
    }


def _md_list(items: list[str]) -> str:
    return "\n".join(f"- `{item}`" for item in items) if items else "- none"


def _metadata_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "required"}
    return bool(value)


def render_task_cards_markdown(task_cards: Iterable[TaskCard], *, title: str = "Task Cards") -> str:
    lines = [f"# {title}", "", "> Generated from the workflow task card database. Markdown is a review snapshot, not the source of truth.", ""]
    for card in task_cards:
        issues = task_card_quality_issues(card)
        eligibility = task_card_execution_eligibility(card)
        lines.extend(
            [
                f"## {card.task_card_id}: {card.title}",
                "",
                f"- status: `{card.status}`",
                f"- quality: `{'passed' if not issues else 'blocked'}`",
                f"- execution_eligible: `{str(eligibility['execution_eligible']).lower()}`",
                f"- requirement_coverage: `{task_card_requirement_coverage_status(card)}`",
                f"- milestone: `{card.milestone or '-'}`",
                f"- phase: `{card.phase_name or '-'}`",
                f"- risk_level: `{card.risk_level}`",
                f"- provider_lane: `{card.provider_lane or '-'}`",
                f"- execution_mode: `{card.execution_mode or '-'}`",
                "",
                "### Goal",
                card.goal or card.description,
                "",
                "### Write Set",
                _md_list(card.write_set),
                "",
                "### Read Set",
                _md_list(card.read_set),
                "",
                "### Acceptance",
                _md_list(card.acceptance_criteria),
                "",
                "### Tests",
                _md_list(card.test_commands),
                "",
                "### Evidence Requirements",
                _md_list(card.evidence_requirements),
                "",
                "### Blocking Conditions",
                _md_list(card.blocking_conditions),
                "",
                "### Model Guidance",
                _md_list(card.model_guidance),
                "",
            ]
        )
        metadata = card.metadata if isinstance(card.metadata, dict) else {}
        covered_requirement_ids = _metadata_string_list(metadata.get("covered_requirement_ids"))
        required_requirement_ids = _metadata_string_list(metadata.get("required_requirement_ids"))
        if covered_requirement_ids or required_requirement_ids:
            lines.extend(
                [
                    "### Requirement Coverage",
                    "required:",
                    _md_list(required_requirement_ids),
                    "covered:",
                    _md_list(covered_requirement_ids),
                    "",
                ]
            )
        if issues:
            lines.extend(["### Quality Issues", _md_list([issue["code"] for issue in issues]), ""])
    return "\n".join(lines).rstrip() + "\n"


def export_task_cards_markdown(task_cards: Iterable[TaskCard], output_path: str | Path, *, title: str = "Task Cards") -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_task_cards_markdown(task_cards, title=title), encoding="utf-8")
    return path


class TaskCardStore:
    def __init__(self, db_path: str | Path | None = None):
        self.task_repo = TaskRepository(db_path)

    def list_for_run(self, run_id: str) -> list[TaskCard]:
        return self.task_repo.list_task_cards_for_run(run_id)

    def list_for_milestone(self, milestone: str) -> list[TaskCard]:
        return self.task_repo.list_task_cards_for_milestone(milestone)

    def quality_report_for_run(self, run_id: str) -> dict[str, Any]:
        return task_card_quality_report(self.list_for_run(run_id))

    def export_run_markdown(self, run_id: str, output_path: str | Path) -> dict[str, Any]:
        cards = self.list_for_run(run_id)
        path = export_task_cards_markdown(cards, output_path, title=f"Task Cards for {run_id}")
        return {
            "schema_version": "m108_task_card_export_v1",
            "run_id": run_id,
            "task_card_count": len(cards),
            "output_path": path.as_posix(),
            "quality": task_card_quality_report(cards),
        }
