from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app
from packages.core_domain.self_development_manifest import build_self_development_manifest


def _write_milestone_fixture(root: Path, milestone: str, *, task_cards: int = 3, evidence: bool = True) -> None:
    (root / f"{milestone}_EXECUTION_REPORT.md").write_text(f"# {milestone} report\n", encoding="utf-8")
    state_dir = root / "state" / f"{milestone.lower()}_demo"
    task_card_dir = state_dir / "task_cards"
    evidence_dir = state_dir / "evidence"
    operator_packet_dir = state_dir / "operator_packets"
    task_card_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    operator_packet_dir.mkdir(parents=True, exist_ok=True)
    for index in range(task_cards):
        (task_card_dir / f"{milestone}_{index}.md").write_text("# task\n", encoding="utf-8")
    if evidence:
        (evidence_dir / f"{milestone}.json").write_text("{}", encoding="utf-8")
    (operator_packet_dir / f"{milestone}.json").write_text("{}", encoding="utf-8")


def _archive_milestone_report(root: Path, milestone: str) -> None:
    archive_dir = root / "docs" / "archive" / "evaluations"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (root / f"{milestone}_EXECUTION_REPORT.md").replace(archive_dir / f"{milestone}_EXECUTION_REPORT.md")


def test_self_development_manifest_go_when_milestone_evidence_is_complete(tmp_path: Path) -> None:
    for milestone in ["M70", "M71"]:
        _write_milestone_fixture(tmp_path, milestone)

    manifest = build_self_development_manifest(tmp_path, milestones=["M70", "M71"])

    assert manifest["go_no_go"] == "GO"
    assert manifest["blocking_issue_count"] == 0
    assert manifest["task_card_mechanism"]["min_task_cards_per_phase"] == 3
    assert all(item["task_card_policy"]["status"] == "passed" for item in manifest["milestones"])


def test_self_development_manifest_accepts_archived_execution_report(tmp_path: Path) -> None:
    _write_milestone_fixture(tmp_path, "M70")
    _archive_milestone_report(tmp_path, "M70")

    manifest = build_self_development_manifest(tmp_path, milestones=["M70"])

    assert manifest["go_no_go"] == "GO"
    assert manifest["blocking_issue_count"] == 0
    assert manifest["milestones"][0]["execution_report"]["path"] == "docs/archive/evaluations/M70_EXECUTION_REPORT.md"
    assert "M70_EXECUTION_REPORT.md" in manifest["milestones"][0]["execution_report"]["lookup_paths"][0]


def test_self_development_manifest_blocks_single_card_phase_without_exception(tmp_path: Path) -> None:
    _write_milestone_fixture(tmp_path, "M72", task_cards=1)

    manifest = build_self_development_manifest(tmp_path, milestones=["M72"])

    assert manifest["go_no_go"] == "NO-GO"
    assert manifest["blocking_issue_count"] == 1
    assert manifest["milestones"][0]["task_card_policy"]["status"] == "failed"
    assert manifest["blocking_issues"][0]["code"] == "task_card_policy_failed"


def test_cli_governance_self_development_manifest_writes_output(tmp_path: Path) -> None:
    _write_milestone_fixture(tmp_path, "M71")
    output_path = tmp_path / "manifest.json"

    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "governance",
            "self-development-manifest",
            "--milestone",
            "M71",
            "--output-path",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["go_no_go"] == "GO"
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8"))["milestones"][0]["milestone"] == "M71"
