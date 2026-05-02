from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from apps.operator_cli.main import app
from infra.test_matrix import build_pytest_command, prune_pytest_temp_workspace, run_matrix, select_matrix
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


def test_commercial_game_matrix_layers_are_named_and_separated() -> None:
    fast = select_matrix("commercial_fast")
    integration = select_matrix("commercial_integration")
    cocos_browser = select_matrix("commercial_cocos_browser")
    provider_contract = select_matrix("commercial_provider_contract")

    assert fast.run_slow is False
    assert "tests/test_commercial_game_evidence_contracts.py" in fast.targets
    assert "tests/test_pipeline_and_automation_cli.py" in integration.targets
    assert cocos_browser.run_slow is True
    assert cocos_browser.targets == ["tests/test_cocos_e2e.py"]
    assert "tests/test_capability_probe.py" in provider_contract.targets
    assert set(fast.targets).isdisjoint(cocos_browser.targets)
    assert set(provider_contract.targets).isdisjoint(cocos_browser.targets)


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


def test_test_matrix_success_removes_current_basetemp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=["pytest"], returncode=0, stdout="passed", stderr="")

    monkeypatch.delenv("WORKFLOW_KEEP_TEST_TEMP", raising=False)
    monkeypatch.setattr("infra.test_matrix.subprocess.run", fake_run)

    payload = run_matrix(suite="unit", workspace_root=tmp_path)

    basetemp = Path(payload["basetemp"])
    assert payload["return_code"] == 0
    assert payload["cleanup"]["post_run"]["status"] == "deleted"
    assert not basetemp.exists()


def test_test_matrix_failure_keeps_current_basetemp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=["pytest"], returncode=1, stdout="", stderr="failed")

    monkeypatch.delenv("WORKFLOW_KEEP_TEST_TEMP", raising=False)
    monkeypatch.setattr("infra.test_matrix.subprocess.run", fake_run)

    payload = run_matrix(suite="unit", workspace_root=tmp_path)

    basetemp = Path(payload["basetemp"])
    assert payload["return_code"] == 1
    assert payload["cleanup"]["post_run"]["reason"] == "test_failed"
    assert payload["cleanup"]["kept_current_on_failure"] is True
    assert basetemp.exists()


def test_test_matrix_prunes_old_pytest_temp_dirs(tmp_path: Path) -> None:
    temp_root = tmp_path / "state" / ".pytest-tmp-workflow"
    old_dir = temp_root / "matrix-old"
    old_dir.mkdir(parents=True)
    (old_dir / "workflow.db").write_bytes(b"old")
    old_timestamp = 1000
    os.utime(old_dir, (old_timestamp, old_timestamp))

    payload = prune_pytest_temp_workspace(tmp_path, ttl_hours=1, now_timestamp=old_timestamp + 7200)

    assert payload["status"] == "ok"
    assert payload["bytes_removed"] > 0
    assert not old_dir.exists()


def test_test_matrix_keep_env_disables_success_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=["pytest"], returncode=0, stdout="passed", stderr="")

    monkeypatch.setenv("WORKFLOW_KEEP_TEST_TEMP", "1")
    monkeypatch.setattr("infra.test_matrix.subprocess.run", fake_run)

    payload = run_matrix(suite="unit", workspace_root=tmp_path)

    basetemp = Path(payload["basetemp"])
    assert payload["cleanup"]["post_run"]["reason"] == "WORKFLOW_KEEP_TEST_TEMP"
    assert basetemp.exists()
