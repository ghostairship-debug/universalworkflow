from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.orchestrator_api.main import create_app
from packages.core_domain.db import migrate
from packages.core_domain.repositories import PresetRepository


def _client(db_path: Path, workspace_root: Path) -> TestClient:
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    return TestClient(create_app(db_path, workspace_root=workspace_root))


def _receipt(client: TestClient, action_type: str) -> str:
    response = client.post("/operator-action-receipts", json={"action_type": action_type})
    assert response.status_code == 201
    return str(response.json()["receipt_id"])


def test_high_risk_api_requires_matching_single_use_operator_receipt(tmp_path: Path) -> None:
    client = _client(tmp_path / "workflow.db", tmp_path)
    run = client.post("/runs", json={"goal": "Receipt guarded resume", "preset_id": "feature_delivery"}).json()
    compile_response = client.post(f"/runs/{run['run_id']}/compile")
    assert compile_response.status_code == 200

    missing = client.post(f"/runs/{run['run_id']}/resume")
    assert missing.status_code == 403

    wrong_receipt = _receipt(client, "approve_run")
    wrong = client.post(
        f"/runs/{run['run_id']}/resume",
        headers={"X-Operator-Action-Receipt": wrong_receipt},
    )
    assert wrong.status_code == 403

    resume_receipt = _receipt(client, "resume_run")
    resumed = client.post(
        f"/runs/{run['run_id']}/resume",
        headers={"X-Operator-Action-Receipt": resume_receipt},
    )
    assert resumed.status_code == 200
    assert resumed.json()["run"]["status"] == "completed"

    reused = client.post(
        f"/runs/{run['run_id']}/resume",
        headers={"X-Operator-Action-Receipt": resume_receipt},
    )
    assert reused.status_code == 403
