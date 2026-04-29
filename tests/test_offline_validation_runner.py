from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from apps.operator_cli.main import app
from infra.validation.common import _operator_action_scope_for_post, http_get_json, review_policy_debt_linkage_is_current, run_command
from infra.validation import runner


def _passed_flow(*args):
    return {"passed": True, "arg_count": len(args)}


def _large_payload_flow() -> dict:
    return {"passed": True, "payload": "x" * 2_000_000}


def test_offline_validation_supports_sharded_full_suite(monkeypatch) -> None:
    monkeypatch.setattr(runner, "validate_cli_flow", _passed_flow)
    monkeypatch.setattr(runner, "validate_smoke_flow", _passed_flow)
    monkeypatch.setattr(runner, "validate_api_flow", _passed_flow)
    monkeypatch.setattr(runner, "validate_cluster_flow", _passed_flow)
    args = SimpleNamespace(
        report_path="unused.json",
        api_port=8011,
        suite="full",
        shard="1/2",
        timeout_seconds=0,
        skip_offline_probe=True,
    )

    report = runner.build_report(args)

    assert report["overall_passed"] is True
    assert report["selected_flows"] == ["cli_flow", "api_flow"]
    assert report["checks"]["cli_flow"]["selected"] is True
    assert report["checks"]["api_flow"]["selected"] is True
    assert report["checks"]["smoke_flow"]["skipped"] is True
    assert report["checks"]["cluster_flow"]["skipped"] is True


def test_offline_validation_quick_uses_short_cli_flow(monkeypatch) -> None:
    def _quick_flow(*args):
        return {"passed": True, "quick": True, "arg_count": len(args)}

    def _full_flow(*args):
        return {"passed": False, "full": True, "arg_count": len(args)}

    monkeypatch.setattr(runner, "validate_cli_quick_flow", _quick_flow)
    monkeypatch.setattr(runner, "validate_cli_flow", _full_flow)
    monkeypatch.setattr(runner, "validate_smoke_flow", _passed_flow)
    args = SimpleNamespace(
        report_path="unused.json",
        api_port=8011,
        suite="quick",
        shard="1/2",
        timeout_seconds=0,
        skip_offline_probe=True,
    )

    report = runner.build_report(args)

    assert report["overall_passed"] is True
    assert report["selected_flows"] == ["cli_flow"]
    assert report["checks"]["cli_flow"]["quick"] is True


def test_offline_validation_timeout_returns_failure_payload() -> None:
    payload = runner._with_elapsed("sleep_flow", time.sleep, (1,), timeout_seconds=0.01)

    assert payload["passed"] is False
    assert payload["timed_out"] is True
    assert "timed out" in payload["error"]
    assert payload["elapsed_ms"] >= 0


def test_offline_validation_command_trace_records_last_command(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.jsonl"
    env = {"WORKFLOW_OFFLINE_VALIDATION_TRACE": trace_path.as_posix()}

    payload = runner._with_elapsed(
        "slow_command",
        run_command,
        ([sys.executable, "-c", "import time; time.sleep(5)"], env),
        timeout_seconds=1.5,
        trace_path=trace_path,
    )

    assert payload["passed"] is False
    assert payload["timed_out"] is True
    assert payload["trace_path"] == trace_path.as_posix()
    assert payload["last_command"]["command"][:3] == [sys.executable, "-c", "import time; time.sleep(5)"]
    assert payload["last_command"]["last_event"] == "command_started"


def test_offline_validation_http_timeout_includes_url_and_failure_class(monkeypatch, tmp_path: Path) -> None:
    def _timeout(*_args, **_kwargs):
        raise TimeoutError("timed out")

    trace_path = tmp_path / "http.jsonl"
    monkeypatch.setenv("WORKFLOW_OFFLINE_VALIDATION_TRACE", trace_path.as_posix())
    monkeypatch.setattr("urllib.request.urlopen", _timeout)

    try:
        http_get_json("http://127.0.0.1:8011/slow", timeout=0.1)
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected timeout")

    assert "validation_http_timeout" in message
    assert "http://127.0.0.1:8011/slow" in message
    events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert events[-1]["event"] == "http_failed"
    assert events[-1]["failure_class"] == "validation_http_timeout"


def test_offline_validation_subprocess_returns_large_payload_without_queue_deadlock(tmp_path: Path) -> None:
    trace_path = tmp_path / "large.jsonl"

    payload = runner._with_elapsed(
        "large_payload",
        _large_payload_flow,
        (),
        timeout_seconds=10,
        trace_path=trace_path,
    )

    assert payload["passed"] is True
    assert payload["payload"] == "x" * 2_000_000
    assert Path(payload["flow_result_path"]).exists()


def test_offline_validation_receipt_scope_matches_high_risk_posts() -> None:
    assert _operator_action_scope_for_post("http://127.0.0.1:8011/runs/run_a/resume") == {"run_id": "run_a"}
    assert _operator_action_scope_for_post(
        "http://127.0.0.1:8011/runs/batch-resume",
        {"run_ids": ["run_a", "run_b"], "max_workers": 2},
    ) == {"run_ids": ["run_a", "run_b"], "max_workers": 2}
    assert _operator_action_scope_for_post(
        "http://127.0.0.1:8011/runs/run_a/reconcile",
        {"apply": True, "action": "align_completed_runtime_state"},
    ) == {"run_id": "run_a", "apply": True, "action": "align_completed_runtime_state"}


def test_offline_validation_accepts_current_or_legacy_review_policy_debt_linkage() -> None:
    assert review_policy_debt_linkage_is_current("TD-006") is True
    assert review_policy_debt_linkage_is_current(None) is True
    assert review_policy_debt_linkage_is_current("unrelated-debt") is False


def test_offline_validation_main_writes_failure_report_for_invalid_shard(tmp_path: Path) -> None:
    report_path = tmp_path / "offline_validation_report.json"

    runner.main(
        [
            "--suite",
            "full",
            "--shard",
            "3/2",
            "--report-path",
            str(report_path),
            "--skip-offline-probe",
            "--timeout-seconds",
            "0",
        ]
    )

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["overall_passed"] is False
    assert "--shard must satisfy" in payload["error"]


def test_cli_validation_run_writes_report(tmp_path: Path, monkeypatch) -> None:
    report_path = tmp_path / "validation.json"

    def _fake_build_report(args):
        return {
            "generated_at": "2026-04-26T00:00:00+00:00",
            "suite": args.suite,
            "shard": args.shard,
            "checks": {},
            "overall_passed": True,
        }

    monkeypatch.setattr(runner, "build_report", _fake_build_report)
    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "validation",
            "run",
            "--suite",
            "quick",
            "--report-path",
            str(report_path),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["suite"] == "quick"
    assert payload["report_path"] == report_path.as_posix()
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert persisted["overall_passed"] is True
    assert persisted["report_path"] == report_path.as_posix()
