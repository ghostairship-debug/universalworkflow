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


def test_workflowctl_doctor_reports_strong_dogfood_codex_backend_without_openai_key(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "workflow.db"
    monkeypatch.setenv("WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED", "1")
    monkeypatch.setenv("WORKFLOW_DOGFOOD_MODEL", "gpt-5.5")
    monkeypatch.setenv("WORKFLOW_DOGFOOD_REASONING_EFFORT", "xhigh")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_TOKEN", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(cli_main.shutil, "which", lambda name: f"C:/fake/{name}.exe")

    result = runner.invoke(app, ["--db-path", str(db_path), "doctor"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "degraded"
    assert payload["external_capabilities"]["dogfood_strong_model"] == {
        "status": "ready",
        "enabled": True,
        "execution_backend": "codex_cli",
        "model": "gpt-5.5",
        "codex_model": "gpt-5.5",
        "reasoning_effort": "xhigh",
        "auth": "codex_cli_login",
    }
    assert payload["external_capabilities"]["langchain_agent"]["status"] == "missing_auth"


def test_workflowctl_doctor_reports_agent_lane_auth_when_selected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "workflow.db"
    monkeypatch.setenv("WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED", "1")
    monkeypatch.setenv("WORKFLOW_DOGFOOD_EXECUTION_BACKEND", "agent_lane")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_TOKEN", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr(cli_main.shutil, "which", lambda name: f"C:/fake/{name}.exe")

    result = runner.invoke(app, ["--db-path", str(db_path), "doctor"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["external_capabilities"]["dogfood_strong_model"]["execution_backend"] == "agent_lane"
    assert payload["external_capabilities"]["dogfood_strong_model"]["status"] == "missing_auth"
    assert payload["external_capabilities"]["langchain_agent"]["degraded_reason"]
