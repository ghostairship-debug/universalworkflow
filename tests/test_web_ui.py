from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.orchestrator_api.main import create_app
from packages.core_domain.db import migrate
from packages.core_domain.repositories import PresetRepository


def build_client(db_path: Path) -> TestClient:
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    return TestClient(create_app(db_path))


def test_api_and_web_ui_expose_operator_surfaces(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    feature_run = client.post("/runs", json={"goal": "Ship UI route", "preset_id": "feature_delivery"}).json()
    client.post(f"/runs/{feature_run['run_id']}/compile")
    client.post(f"/runs/{feature_run['run_id']}/resume")

    review_run = client.post("/runs", json={"goal": "Need human review", "preset_id": "research_spike"}).json()
    client.post(f"/runs/{review_run['run_id']}/compile")
    client.post(f"/runs/{review_run['run_id']}/resume")

    runs_response = client.get("/runs", params={"limit": 10})
    pending_response = client.get("/reviews/pending")
    operator_response = client.get(f"/runs/{review_run['run_id']}/operator-view")
    dashboard_response = client.get("/ui")
    runs_page_response = client.get("/ui/runs")
    run_page_response = client.get(f"/ui/runs/{review_run['run_id']}")
    reviews_page_response = client.get("/ui/reviews")
    governance_page_response = client.get("/ui/governance")
    config_page_response = client.get("/ui/config")

    assert runs_response.status_code == 200
    assert {item["run"]["run_id"] for item in runs_response.json()} == {
        feature_run["run_id"],
        review_run["run_id"],
    }
    assert pending_response.status_code == 200
    assert [item["run"]["run_id"] for item in pending_response.json()] == [review_run["run_id"]]
    assert operator_response.status_code == 200
    assert operator_response.json()["run"]["run_id"] == review_run["run_id"]
    assert operator_response.json()["status_detail"]["effective_review_state"] == "human_pending"
    assert "Run Explorer" in runs_page_response.text
    assert "Pending Review Console" in reviews_page_response.text
    assert "Governance" in governance_page_response.text
    assert "Effective Configuration" in config_page_response.text
    assert "Operator Dashboard" in dashboard_response.text
    assert review_run["run_id"] in run_page_response.text


def test_web_ui_action_routes_redirect_and_mutate_run_state(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    run = client.post("/runs", json={"goal": "Approve from web UI", "preset_id": "research_spike"}).json()
    client.post(f"/runs/{run['run_id']}/compile")
    client.post(f"/runs/{run['run_id']}/resume")

    approve_response = client.post(f"/ui/actions/{run['run_id']}/approve", follow_redirects=False)
    assert approve_response.status_code == 303
    assert f"/ui/runs/{run['run_id']}?" in approve_response.headers["location"]

    operator_response = client.get(f"/runs/{run['run_id']}/operator-view")
    assert operator_response.status_code == 200
    assert operator_response.json()["run"]["status"] == "completed"

    batch_ready_run = client.post("/runs", json={"goal": "Prepared batch resume", "preset_id": "feature_delivery"}).json()
    client.post(f"/runs/{batch_ready_run['run_id']}/compile")

    batch_resume_response = client.post(
        "/ui/actions/batch-resume",
        data={"run_id": [batch_ready_run["run_id"]]},
        follow_redirects=False,
    )
    assert batch_resume_response.status_code == 303
    assert "/ui/reviews?" in batch_resume_response.headers["location"]
