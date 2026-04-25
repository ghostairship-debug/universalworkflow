from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.orchestrator_api.main import create_app
from packages.core_domain.db import get_connection, migrate
from packages.core_domain.repositories import PresetRepository


def _client(db_path: Path, workspace_root: Path) -> TestClient:
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    return TestClient(create_app(db_path, workspace_root=workspace_root))


def _receipt(client: TestClient, action_type: str, scope_payload: dict | None = None) -> str:
    response = client.post(
        "/operator-action-receipts",
        json={"action_type": action_type, "scope_payload": scope_payload or {}},
    )
    assert response.status_code == 201
    return str(response.json()["receipt_id"])


def test_high_risk_api_requires_matching_single_use_operator_receipt(tmp_path: Path) -> None:
    client = _client(tmp_path / "workflow.db", tmp_path)
    run = client.post("/runs", json={"goal": "Receipt guarded resume", "preset_id": "feature_delivery"}).json()
    compile_response = client.post(f"/runs/{run['run_id']}/compile")
    assert compile_response.status_code == 200

    missing = client.post(f"/runs/{run['run_id']}/resume")
    assert missing.status_code == 403

    wrong_receipt = _receipt(client, "approve_run", {"run_id": run["run_id"]})
    wrong = client.post(
        f"/runs/{run['run_id']}/resume",
        headers={"X-Operator-Action-Receipt": wrong_receipt},
    )
    assert wrong.status_code == 403

    resume_receipt = _receipt(client, "resume_run", {"run_id": run["run_id"]})
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


def test_receipt_scope_hash_rejects_tampered_run_id(tmp_path: Path) -> None:
    client = _client(tmp_path / "workflow.db", tmp_path)
    run_a = client.post("/runs", json={"goal": "Receipt guarded run A", "preset_id": "feature_delivery"}).json()
    run_b = client.post("/runs", json={"goal": "Receipt guarded run B", "preset_id": "feature_delivery"}).json()
    assert client.post(f"/runs/{run_b['run_id']}/compile").status_code == 200

    receipt = _receipt(client, "resume_run", {"run_id": run_a["run_id"]})
    tampered = client.post(
        f"/runs/{run_b['run_id']}/resume",
        headers={"X-Operator-Action-Receipt": receipt},
    )

    assert tampered.status_code == 403
    assert "scope_hash mismatch" in tampered.text


def test_old_receipt_without_scope_hash_is_rejected_for_high_risk_action(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = _client(db_path, tmp_path)
    run = client.post("/runs", json={"goal": "Legacy receipt run", "preset_id": "feature_delivery"}).json()
    assert client.post(f"/runs/{run['run_id']}/compile").status_code == 200
    receipt = _receipt(client, "resume_run", {"run_id": run["run_id"]})
    with get_connection(db_path) as connection:
        connection.execute("UPDATE operator_action_receipts SET scope_hash = NULL WHERE receipt_id = ?", (receipt,))
        connection.commit()

    response = client.post(
        f"/runs/{run['run_id']}/resume",
        headers={"X-Operator-Action-Receipt": receipt},
    )

    assert response.status_code == 403
    assert "missing scope_hash" in response.text


def test_launch_execute_receipt_scope_rejects_body_tamper(tmp_path: Path) -> None:
    client = _client(tmp_path / "workflow.db", tmp_path)
    receipt = _receipt(
        client,
        "launch_execute",
        {"goal": "Launch the original goal", "preset_id": "project_delivery", "execute": True},
    )

    response = client.post(
        "/runs/launch",
        json={"goal": "Launch the tampered goal", "preset_id": "project_delivery", "execute": True},
        headers={"X-Operator-Action-Receipt": receipt},
    )

    assert response.status_code == 403
    assert "scope_hash mismatch" in response.text


def test_batch_resume_receipt_scope_rejects_run_ids_tamper(tmp_path: Path) -> None:
    client = _client(tmp_path / "workflow.db", tmp_path)
    run_a = client.post("/runs", json={"goal": "Batch run A", "preset_id": "feature_delivery"}).json()
    run_b = client.post("/runs", json={"goal": "Batch run B", "preset_id": "feature_delivery"}).json()
    receipt = _receipt(client, "batch_resume_runs", {"run_ids": [run_a["run_id"]], "max_workers": 1})

    response = client.post(
        "/runs/batch-resume",
        json={"run_ids": [run_b["run_id"]], "max_workers": 1},
        headers={"X-Operator-Action-Receipt": receipt},
    )

    assert response.status_code == 403
    assert "scope_hash mismatch" in response.text


def test_watchdog_auto_apply_requires_post_receipt(tmp_path: Path) -> None:
    client = _client(tmp_path / "workflow.db", tmp_path)

    read_only_response = client.get("/interaction/watchdogs/evaluate", params={"auto_apply": True})
    assert read_only_response.status_code == 400

    missing_receipt = client.post("/interaction/watchdogs/evaluate/apply", json={"limit": 20})
    assert missing_receipt.status_code == 403

    receipt = _receipt(client, "watchdog_auto_apply", {"session_id": None, "run_id": None, "limit": 20})
    applied = client.post(
        "/interaction/watchdogs/evaluate/apply",
        json={"limit": 20},
        headers={"X-Operator-Action-Receipt": receipt},
    )
    assert applied.status_code == 200
