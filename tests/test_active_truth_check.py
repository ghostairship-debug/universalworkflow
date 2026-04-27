from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app
from packages.core_domain.active_truth import build_active_truth_check


def _write_minimal_truth_set(root: Path, *, stale_m79: bool = False) -> None:
    (root / "docs" / "governance").mkdir(parents=True)
    (root / "docs").mkdir(exist_ok=True)
    (root / "README.md").write_text(
        "## Current Version: M79 Cocos Commercial Pipeline Repair Planned\n"
        if stale_m79
        else "## Current Version: M81 Multimodal Asset Factory\n",
        encoding="utf-8",
    )
    (root / "docs" / "current_development_workflow.md").write_text(
        "- M79 通过前，不恢复能力层开发。\n" if stale_m79 else "- M81 asset factory is complete.\n",
        encoding="utf-8",
    )
    (root / "docs" / "milestone_history.md").write_text(
        "- 最新接受实现基线：`M78`\n" if stale_m79 else "- 最新接受实现基线：`M79`\n",
        encoding="utf-8",
    )
    (root / "docs" / "tech-debt-registry.md").write_text("# 技术债登记表\n", encoding="utf-8")
    (root / "docs" / "governance" / "tech_debt_registry.json").write_text(
        json.dumps(
            {
                "schema_version": "test",
                "repaid_items": [{"debt_id": "M77-COCOS-001"}],
                "open_items": [{"debt_id": "M77-PIPE-001", "current_status": "partially_repaid"}],
                "obsolete_items": [],
                "freeze_review_questions": [],
            }
        ),
        encoding="utf-8",
    )
    (root / "state" / "m79_cocos_commercial_pipeline").mkdir(parents=True)
    (root / "state" / "m79_cocos_commercial_pipeline" / "checkpoint.json").write_text("{}", encoding="utf-8")


def test_active_truth_check_catches_stale_m79_planned_docs(tmp_path: Path) -> None:
    _write_minimal_truth_set(tmp_path, stale_m79=True)

    payload = build_active_truth_check(tmp_path)

    assert payload["go_no_go"] == "NO-GO"
    assert {issue["code"] for issue in payload["issues"]} >= {
        "m79_planned_title",
        "m79_pre_completion_gate",
        "milestone_baseline_stale_after_m79",
    }


def test_active_truth_check_passes_consistent_truth_set(tmp_path: Path) -> None:
    _write_minimal_truth_set(tmp_path, stale_m79=False)

    payload = build_active_truth_check(tmp_path)

    assert payload["go_no_go"] == "GO"
    assert payload["issue_count"] == 0


def test_active_truth_check_blocks_debt_id_in_repaid_and_open(tmp_path: Path) -> None:
    _write_minimal_truth_set(tmp_path, stale_m79=False)
    registry_path = tmp_path / "docs" / "governance" / "tech_debt_registry.json"
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    payload["open_items"].append({"debt_id": "M77-COCOS-001", "current_status": "repaid"})
    registry_path.write_text(json.dumps(payload), encoding="utf-8")

    report = build_active_truth_check(tmp_path)

    assert report["go_no_go"] == "NO-GO"
    assert "debt_id_in_repaid_and_open" in {issue["code"] for issue in report["issues"]}
    assert "repaid_status_inside_open_items" in {issue["code"] for issue in report["issues"]}


def test_cli_governance_active_truth_check_writes_output(tmp_path: Path) -> None:
    _write_minimal_truth_set(tmp_path, stale_m79=False)
    output_path = tmp_path / "truth" / "active_truth.json"

    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "governance",
            "active-truth-check",
            "--output-path",
            str(output_path),
            "--strict",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["go_no_go"] == "GO"
    assert output_path.exists()
