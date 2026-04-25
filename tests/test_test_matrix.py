from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from apps.operator_cli.main import app
from infra.test_matrix import build_pytest_command, select_matrix
from packages.core_domain.test_matrix import select_matrix as select_matrix_compat


def test_test_matrix_selects_slow_shards_without_overlap() -> None:
    first = select_matrix("slow", "1/2")
    second = select_matrix("slow", "2/2")

    assert first.run_slow is True
    assert second.run_slow is True
    assert set(first.targets).isdisjoint(second.targets)
    assert sorted(first.targets + second.targets) == sorted(select_matrix("slow").targets)


def test_test_matrix_rejects_invalid_shard() -> None:
    with pytest.raises(ValueError):
        select_matrix("slow", "3/2")


def test_core_domain_test_matrix_import_remains_compatible() -> None:
    assert select_matrix_compat("unit").targets == select_matrix("unit").targets


def test_cli_test_matrix_dry_run_uses_workspace_root(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "test",
            "matrix",
            "--suite",
            "unit",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["dry_run"] is True
    assert payload["suite"] == "unit"
    assert str(tmp_path).replace("\\", "/") in payload["basetemp"]
    assert ".pytest-tmp-workflow" in payload["basetemp"]
    assert "m61m66" not in payload["basetemp"]
    assert "tests/test_service_decomposition.py" in payload["targets"]


def test_test_matrix_uses_milestone_neutral_basetemp(tmp_path: Path) -> None:
    _, _, basetemp = build_pytest_command(suite="unit", workspace_root=tmp_path)

    basetemp_text = basetemp.as_posix()
    assert ".pytest-tmp-workflow" in basetemp_text
    assert "m48m51" not in basetemp_text
    assert "m61m66" not in basetemp_text
