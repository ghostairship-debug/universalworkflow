from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from apps.operator_cli.main import app
from packages.core_domain.test_matrix import select_matrix


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
    assert "tests/test_service_decomposition.py" in payload["targets"]
