from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app
from packages.contracts import Run, TaskCard
from packages.core_domain.db import migrate
from packages.core_domain.repositories import RunRepository, TaskRepository
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
    assert all(item["provenance"]["traceability_status"] == "complete" for item in manifest["milestones"])
    assert all(item["provenance"]["task_card_paths"] for item in manifest["milestones"])
    assert all(item["provenance"]["evidence_paths"] for item in manifest["milestones"])
    assert all(item["provenance"]["schema_version"] == "m73_manifest_provenance_v2" for item in manifest["milestones"])
    assert all(item["provenance"]["trace_links"] for item in manifest["milestones"])


def test_self_development_manifest_accepts_archived_execution_report(tmp_path: Path) -> None:
    _write_milestone_fixture(tmp_path, "M70")
    _archive_milestone_report(tmp_path, "M70")

    manifest = build_self_development_manifest(tmp_path, milestones=["M70"])

    assert manifest["go_no_go"] == "GO"
    assert manifest["blocking_issue_count"] == 0
    assert manifest["milestones"][0]["execution_report"]["path"] == "docs/archive/evaluations/M70_EXECUTION_REPORT.md"
    assert "M70_EXECUTION_REPORT.md" in manifest["milestones"][0]["execution_report"]["lookup_paths"][0]
    assert manifest["milestones"][0]["provenance"]["execution_report_path"] == "docs/archive/evaluations/M70_EXECUTION_REPORT.md"


def test_self_development_manifest_accepts_flat_milestone_closeout_artifacts(tmp_path: Path) -> None:
    state_dir = tmp_path / "state" / "m105_demo"
    state_dir.mkdir(parents=True)
    (state_dir / "task_cards.md").write_text("# M105 task cards\n", encoding="utf-8")
    (state_dir / "plan_graph.json").write_text('{"status":"completed"}', encoding="utf-8")
    (state_dir / "policy_preview.json").write_text('{"status":"completed"}', encoding="utf-8")
    (state_dir / "goal_packet.json").write_text('{"status":"completed"}', encoding="utf-8")
    (state_dir / "closeout_summary.json").write_text('{"status":"completed"}', encoding="utf-8")
    (state_dir / "operator_packet.json").write_text('{"status":"completed"}', encoding="utf-8")

    manifest = build_self_development_manifest(
        tmp_path,
        milestones=["M105"],
        min_task_cards_per_phase=1,
    )

    milestone = manifest["milestones"][0]
    assert manifest["go_no_go"] == "GO"
    assert manifest["blocking_issue_count"] == 0
    assert milestone["execution_report"]["kind"] == "closeout_summary"
    assert milestone["task_card_count"] == 1
    assert milestone["task_card_file_count"] == 1
    assert milestone["operator_packet_count"] == 1
    assert milestone["provenance"]["evidence_category_counts"]["plan_graph"] == 1
    assert milestone["provenance"]["traceability_status"] == "complete"


def test_self_development_manifest_counts_cards_inside_flat_task_card_markdown(tmp_path: Path) -> None:
    state_dir = tmp_path / "state" / "m106_demo"
    state_dir.mkdir(parents=True)
    (state_dir / "task_cards.md").write_text(
        "\n".join(
            [
                "# M106 task cards",
                "",
                "## M106.1 UI",
                "",
                "## M106.2 Scene",
                "",
                "## M106.3 Assets",
                "",
                "## M106.4 Gameplay",
            ]
        ),
        encoding="utf-8",
    )
    (state_dir / "plan_graph.json").write_text('{"status":"completed"}', encoding="utf-8")
    (state_dir / "policy_preview.json").write_text('{"status":"completed"}', encoding="utf-8")
    (state_dir / "goal_packet.json").write_text('{"status":"completed"}', encoding="utf-8")
    (state_dir / "closeout_summary.json").write_text('{"status":"completed"}', encoding="utf-8")
    (state_dir / "operator_packet.json").write_text('{"status":"completed"}', encoding="utf-8")

    manifest = build_self_development_manifest(tmp_path, milestones=["M106"])

    milestone = manifest["milestones"][0]
    assert manifest["go_no_go"] == "GO"
    assert milestone["task_card_count"] == 4
    assert milestone["task_card_file_count"] == 1


def test_self_development_manifest_uses_database_task_cards_as_authority(tmp_path: Path) -> None:
    _write_milestone_fixture(tmp_path, "M109", task_cards=0)
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    run = RunRepository(db_path).create(Run(goal="M109 active phase", preset_id="feature_delivery"))
    task_repo = TaskRepository(db_path)
    for index in range(3):
        task_repo.create_task_card(
            TaskCard(
                run_id=run.run_id,
                title=f"M109.{index} rich task",
                description="A detailed DB task card that is safe for model execution.",
                acceptance_criteria=["implementation is complete", "tests pass"],
                milestone="M109",
                phase_name="M109.1",
                goal="Use the database task card as the source of truth for active phase execution.",
                write_set=[f"packages/example_{index}.py"],
                test_commands=["python -m pytest tests/test_self_development_manifest.py -q"],
                evidence_requirements=["test output", "closeout summary"],
                blocking_conditions=["write_set conflict"],
                model_guidance=["Use structured fields before editing."],
            )
        )

    manifest = build_self_development_manifest(tmp_path, milestones=["M109"], db_path=db_path)

    milestone = manifest["milestones"][0]
    assert manifest["go_no_go"] == "GO"
    assert milestone["task_card_source"] == "database"
    assert milestone["db_task_card_count"] == 3
    assert milestone["task_card_file_unit_count"] == 0
    assert milestone["provenance"]["db_task_card_quality_issues"] == []


def test_cli_task_card_quality_and_export_use_database_source(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    run = RunRepository(db_path).create(Run(goal="Task card CLI", preset_id="feature_delivery"))
    TaskRepository(db_path).create_task_card(
        TaskCard(
            run_id=run.run_id,
            title="Export rich task card",
            description="A detailed task card stored in SQLite and exported as a markdown snapshot.",
            acceptance_criteria=["quality is GO", "markdown export exists"],
            milestone="M109",
            phase_name="M109.1",
            goal="Use the task card database as source of truth and export a readable snapshot.",
            write_set=["packages/core_domain/task_card_store.py"],
            test_commands=["python -m pytest tests/test_self_development_manifest.py -q"],
            evidence_requirements=["quality payload", "markdown snapshot"],
            blocking_conditions=["database is unavailable"],
            model_guidance=["Read structured task fields before changing files."],
        )
    )

    quality = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--workspace-root",
            str(tmp_path),
            "task",
            "card-quality",
            "--run-id",
            run.run_id,
        ],
    )
    assert quality.exit_code == 0
    assert json.loads(quality.stdout)["go_no_go"] == "GO"

    output_path = tmp_path / "task_cards.md"
    export = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--workspace-root",
            str(tmp_path),
            "task",
            "export-cards",
            "--run-id",
            run.run_id,
            "--output-path",
            str(output_path),
        ],
    )
    assert export.exit_code == 0
    assert output_path.exists()
    assert "Generated from the workflow task card database" in output_path.read_text(encoding="utf-8")


def test_self_development_manifest_blocks_single_card_phase_without_exception(tmp_path: Path) -> None:
    _write_milestone_fixture(tmp_path, "M72", task_cards=1)

    manifest = build_self_development_manifest(tmp_path, milestones=["M72"])

    assert manifest["go_no_go"] == "NO-GO"
    assert manifest["blocking_issue_count"] == 1
    assert manifest["milestones"][0]["task_card_policy"]["status"] == "failed"
    assert manifest["blocking_issues"][0]["code"] == "task_card_policy_failed"
    assert manifest["milestones"][0]["provenance"]["traceability_status"] == "complete"


def test_self_development_manifest_reads_utf16_powershell_evidence(tmp_path: Path) -> None:
    _write_milestone_fixture(tmp_path, "M82")
    evidence_path = tmp_path / "state" / "m82_demo" / "evidence" / "M82-powershell.json"
    evidence_path.write_text(json.dumps({"status": "completed", "evidence_id": "evidence_utf16"}), encoding="utf-16")

    manifest = build_self_development_manifest(tmp_path, milestones=["M82"])

    assert manifest["go_no_go"] == "GO"
    utf16_link = next(
        item
        for item in manifest["milestones"][0]["provenance"]["trace_links"]
        if item["path"].endswith("M82-powershell.json")
    )
    assert utf16_link["status"] == "completed"
    assert utf16_link["evidence_id"] == "evidence_utf16"


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
