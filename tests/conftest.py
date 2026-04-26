from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _operator_action_for_post(url: str, payload: dict | None = None) -> tuple[str, dict] | None:
    path = str(url).split("?", 1)[0].rstrip("/")
    if path == "/operator-action-receipts":
        return None
    parts = [part for part in path.split("/") if part]
    if path == "/runs/launch" and payload and payload.get("execute"):
        return (
            "launch_execute",
            {"goal": payload.get("goal"), "preset_id": payload.get("preset_id"), "execute": True},
        )
    if path == "/runs/batch-resume":
        return "batch_resume_runs", {"run_ids": (payload or {}).get("run_ids", []), "max_workers": (payload or {}).get("max_workers")}
    if len(parts) >= 3 and parts[0] == "runs":
        run_id = parts[1]
        if parts[2] == "resume":
            return "resume_run", {"run_id": run_id}
        if parts[2] == "approve":
            return "approve_run", {"run_id": run_id}
        if parts[2] == "reject":
            return "reject_run", {"run_id": run_id}
        if parts[2] == "cancel":
            return "cancel_run", {"run_id": run_id}
    if path.startswith("/runs/") and path.endswith("/reconcile") and payload and payload.get("apply"):
        return "reconcile_apply", {"run_id": parts[1] if len(parts) > 1 else None, "apply": True, "action": payload.get("action")}
    if path == "/interaction/watchdogs/evaluate/apply":
        return "watchdog_auto_apply", {
            "session_id": (payload or {}).get("session_id"),
            "run_id": (payload or {}).get("run_id"),
            "limit": (payload or {}).get("limit", 20),
        }
    if len(parts) >= 3 and parts[0] == "interaction" and parts[1] == "sessions" and parts[-1] == "launch" and payload and payload.get("execute"):
        return "launch_execute", {
            "session_id": parts[2],
            "execute": True,
            "selected_preset_id": payload.get("selected_preset_id"),
            "selected_cluster_template_ids": payload.get("selected_cluster_template_ids", []),
        }
    return None


class ReceiptAwareTestClient(TestClient):
    def post(self, url, *args, **kwargs):  # type: ignore[override]
        headers = dict(kwargs.pop("headers", {}) or {})
        payload = kwargs.get("json") if isinstance(kwargs.get("json"), dict) else None
        operator_action = _operator_action_for_post(str(url), payload)
        if operator_action and "X-Operator-Action-Receipt" not in headers:
            action_type, scope_payload = operator_action
            receipt = super().post(
                "/operator-action-receipts",
                json={"action_type": action_type, "scope_payload": scope_payload},
            )
            if receipt.status_code == 201:
                headers["X-Operator-Action-Receipt"] = receipt.json()["receipt_id"]
        if headers:
            kwargs["headers"] = headers
        return super().post(url, *args, **kwargs)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow end-to-end CLI/API/Web/release tests.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "slow: slow end-to-end tests skipped by default")
    if getattr(config.option, "basetemp", None):
        return
    root_path = Path(str(config.rootpath)).resolve()
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    basetemp_root = root_path / "state" / ".pytest-tmp-workflow"
    basetemp_root.mkdir(parents=True, exist_ok=True)
    config.option.basetemp = str(basetemp_root / f"default-{os.getpid()}-{timestamp}")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-slow"):
        return
    skip_slow = pytest.mark.skip(reason="slow test skipped by default; use --run-slow for full validation")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
