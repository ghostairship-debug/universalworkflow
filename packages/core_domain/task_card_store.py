from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from packages.contracts import TaskCard
from packages.core_domain.repositories import TaskRepository

RISK_LEVELS = {"low", "medium", "high"}


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
    return issues


def task_card_quality_status(task_card: TaskCard) -> str:
    return "passed" if not task_card_quality_issues(task_card) else "blocked"


def task_card_quality_report(task_cards: Iterable[TaskCard]) -> dict[str, Any]:
    cards = list(task_cards)
    items = [
        {
            "task_card_id": card.task_card_id,
            "title": card.title,
            "status": task_card_quality_status(card),
            "issues": task_card_quality_issues(card),
        }
        for card in cards
    ]
    blocked = [item for item in items if item["status"] != "passed"]
    return {
        "schema_version": "m108_task_card_quality_v1",
        "task_card_count": len(cards),
        "blocked_count": len(blocked),
        "go_no_go": "GO" if not blocked and cards else "NO-GO",
        "task_cards": items,
    }


def _md_list(items: list[str]) -> str:
    return "\n".join(f"- `{item}`" for item in items) if items else "- none"


def render_task_cards_markdown(task_cards: Iterable[TaskCard], *, title: str = "Task Cards") -> str:
    lines = [f"# {title}", "", "> Generated from the workflow task card database. Markdown is a review snapshot, not the source of truth.", ""]
    for card in task_cards:
        issues = task_card_quality_issues(card)
        lines.extend(
            [
                f"## {card.task_card_id}: {card.title}",
                "",
                f"- status: `{card.status}`",
                f"- quality: `{'passed' if not issues else 'blocked'}`",
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
