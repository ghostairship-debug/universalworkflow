from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

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


def test_web_ui_workbench_post_flow_redirects_through_preview_clarify_and_launch(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    preview_response = client.post(
        "/ui/workbench/preview",
        data={
            "goal": "Coordinate a multi-role project delivery slice",
            "preset_id": "project_delivery",
            "cluster_template_id": "dev_cluster",
        },
        follow_redirects=False,
    )

    assert preview_response.status_code == 303
    preview_location = preview_response.headers["location"]
    preview_query = parse_qs(urlparse(preview_location).query)
    session_id = preview_query["session_id"][0]
    assert urlparse(preview_location).path == "/ui/workbench"
    assert preview_query["notice"] == ["workbench preview refreshed"]

    workbench_response = client.get(preview_location)
    assert workbench_response.status_code == 200
    assert "Interaction Workbench" in workbench_response.text
    assert session_id in workbench_response.text
    assert "ready_to_launch" in workbench_response.text

    clarify_response = client.post(
        f"/ui/workbench/{session_id}/clarify",
        data={
            "answer_scope": "Keep operator checkpoints visible",
            "preset_id": "project_delivery",
            "cluster_template_id": "dev_cluster",
        },
        follow_redirects=False,
    )

    assert clarify_response.status_code == 303
    clarify_location = clarify_response.headers["location"]
    clarify_query = parse_qs(urlparse(clarify_location).query)
    assert urlparse(clarify_location).path == "/ui/workbench"
    assert clarify_query["session_id"] == [session_id]
    assert clarify_query["notice"] == ["clarifications updated"]

    clarified_workbench_response = client.get(clarify_location)
    assert clarified_workbench_response.status_code == 200
    assert session_id in clarified_workbench_response.text
    assert "Plan Draft" in clarified_workbench_response.text

    launch_response = client.post(
        f"/ui/workbench/{session_id}/launch",
        data={},
        follow_redirects=False,
    )

    assert launch_response.status_code == 303
    launch_location = launch_response.headers["location"]
    parsed_launch = urlparse(launch_location)
    launch_query = parse_qs(parsed_launch.query)
    run_id = parsed_launch.path.removeprefix("/ui/runs/")
    assert parsed_launch.path == f"/ui/runs/{run_id}"
    assert launch_query["notice"] == ["launch completed: preset=project_delivery"]

    run_page_response = client.get(launch_location)
    operator_response = client.get(f"/runs/{run_id}/operator-view")
    assert run_page_response.status_code == 200
    assert run_id in run_page_response.text
    assert operator_response.status_code == 200
    assert operator_response.json()["run"]["run_id"] == run_id
    assert operator_response.json()["run"]["status"] == "prepared"
