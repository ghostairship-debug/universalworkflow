from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _operator_action_for_post(url: str, payload: dict | None = None) -> str | None:
    path = str(url).split("?", 1)[0].rstrip("/")
    if path == "/operator-action-receipts":
        return None
    if path == "/runs/batch-resume":
        return "batch_resume_runs"
    if path.startswith("/runs/") and path.endswith("/resume"):
        return "resume_run"
    if path.startswith("/runs/") and path.endswith("/approve"):
        return "approve_run"
    if path.startswith("/runs/") and path.endswith("/reject"):
        return "reject_run"
    if path.startswith("/runs/") and path.endswith("/cancel"):
        return "cancel_run"
    if path.startswith("/runs/") and path.endswith("/reconcile") and payload and payload.get("apply"):
        return "reconcile_apply"
    if path.startswith("/interaction/sessions/") and path.endswith("/launch") and payload and payload.get("execute"):
        return "launch_execute"
    return None


class ReceiptAwareTestClient(TestClient):
    def post(self, url, *args, **kwargs):  # type: ignore[override]
        headers = dict(kwargs.pop("headers", {}) or {})
        payload = kwargs.get("json") if isinstance(kwargs.get("json"), dict) else None
        action_type = _operator_action_for_post(str(url), payload)
        if action_type and "X-Operator-Action-Receipt" not in headers:
            receipt = super().post("/operator-action-receipts", json={"action_type": action_type})
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


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-slow"):
        return
    skip_slow = pytest.mark.skip(reason="slow test skipped by default; use --run-slow for full validation")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
