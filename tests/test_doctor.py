from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import apps.operator_cli.main as cli_main
from apps.operator_cli.main import app


runner = CliRunner()


def test_workflowctl_doctor_reports_degraded_without_optional_commands_and_redacts_env(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "workflow.db"
    monkeypatch.setenv("OPENAI_API_KEY", "sk-doctor-secret")
    monkeypatch.setattr(cli_main.shutil, "which", lambda _name: None)

    result = runner.invoke(app, ["--db-path", str(db_path), "doctor"])

    assert result.exit_code == 0
    assert "sk-doctor-secret" not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["read_only"] is True
    assert payload["status"] == "degraded"
    assert payload["optional_commands"]["opencode"]["status"] == "missing"
    assert payload["optional_commands"]["codex"]["status"] == "missing"
    assert payload["environment"]["secrets"]["OPENAI_API_KEY"] == {
        "present": True,
        "value": "[REDACTED]",
    }
    assert payload["state_path"]["writable"] is True
    assert not db_path.exists()
