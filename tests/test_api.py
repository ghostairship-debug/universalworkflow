from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.orchestrator_api.main import create_app
from packages.contracts import RunEventType
from packages.core_domain.db import migrate
from packages.core_domain.repositories import PresetRepository
from packages.core_domain.services import OrchestratorService


def build_client(db_path: Path) -> TestClient:
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    return TestClient(create_app(db_path))


def test_api_can_create_run_and_read_timeline(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post(
        "/runs",
        json={"goal": "Build the bootstrap artifact", "preset_id": "feature_delivery"},
    )
    assert create_response.status_code == 201
    run = create_response.json()

    get_response = client.get(f"/runs/{run['run_id']}")
    assert get_response.status_code == 200
    assert get_response.json()["run_id"] == run["run_id"]

    timeline_response = client.get(f"/runs/{run['run_id']}/timeline")
    assert timeline_response.status_code == 200
    timeline = timeline_response.json()
    assert [item["event_type"] for item in timeline] == [
        RunEventType.run_created,
        RunEventType.preset_selected,
    ]


def test_api_returns_structured_error_for_invalid_preset(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    response = client.post("/runs", json={"goal": "Build it", "preset_id": "missing"})
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "preset_not_found"


def test_api_lists_seeded_presets(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    response = client.get("/presets")
    assert response.status_code == 200
    assert {item["preset_id"] for item in response.json()} == {"feature_delivery", "research_spike"}


def test_prepare_run_is_internal_and_persists_compile_bundle(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Compile me", "feature_delivery")
    bundle = service.prepare_run(run.run_id)

    assert bundle.run.status == "prepared"
    assert bundle.task_packet.expected_artifacts
    timeline = service.get_timeline(run.run_id)
    assert [event.event_type for event in timeline][-2:] == [
        RunEventType.runtime_task_created,
        RunEventType.run_compiled,
    ]


def test_api_compile_and_status_detail_are_public_in_m1(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Compile via API", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]

    compile_response = client.post(f"/runs/{run_id}/compile")
    assert compile_response.status_code == 200
    compile_payload = compile_response.json()
    assert compile_payload["run"]["status"] == "prepared"

    status_detail = client.get(f"/runs/{run_id}/status-detail")
    assert status_detail.status_code == 200
    detail_payload = status_detail.json()
    assert detail_payload["run"]["status"] == "prepared"
    assert detail_payload["next_action"] == "resume"
    assert detail_payload["waiting_reason"] == "awaiting_runtime_resume"
    assert detail_payload["failure_reason"] is None
    assert detail_payload["last_runtime_state"]["graph_step"] == "compiled"
    assert detail_payload["last_review_verdict"] is None
    assert detail_payload["recoverability_hint"] == "resume_run"
    assert detail_payload["handoffs"]
    assert detail_payload["runtime_state_refs"]

    inspection_response = client.get(f"/runs/{run_id}/inspection")
    assert inspection_response.status_code == 200
    inspection_payload = inspection_response.json()
    assert inspection_payload["passed"] is True
    assert inspection_payload["problem_count"] == 0
    assert inspection_payload["recommended_action"] == "none"

    handoffs_response = client.get(f"/runs/{run_id}/handoffs")
    assert handoffs_response.status_code == 200
    assert len(handoffs_response.json()) == 1


def test_api_recompile_requires_prepared_run(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Recompile via API", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]

    invalid_recompile = client.post(f"/runs/{run_id}/recompile")
    assert invalid_recompile.status_code == 409

    compile_response = client.post(f"/runs/{run_id}/compile")
    assert compile_response.status_code == 200

    recompile_response = client.post(f"/runs/{run_id}/recompile")
    assert recompile_response.status_code == 200
    assert recompile_response.json()["run"]["status"] == "prepared"


def test_api_resume_runs_prepared_execution_path(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Resume via API", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")

    resume_response = client.post(f"/runs/{run_id}/resume")
    assert resume_response.status_code == 200
    assert resume_response.json()["run"]["status"] == "completed"

    timeline = client.get(f"/runs/{run_id}/timeline").json()
    assert "runtime_resumed" in [item["event_type"] for item in timeline]


def test_api_human_review_path_requires_approval(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Research via API", "preset_id": "research_spike"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")

    resume_response = client.post(f"/runs/{run_id}/resume")
    assert resume_response.status_code == 200
    assert resume_response.json()["run"]["status"] == "awaiting_review"
    assert resume_response.json()["review_decision"] is None

    detail_response = client.get(f"/runs/{run_id}/status-detail")
    assert detail_response.status_code == 200
    assert detail_response.json()["effective_review_state"] == "human_pending"
    assert detail_response.json()["latest_review_verdict"] is None

    approve_response = client.post(f"/runs/{run_id}/approve")
    assert approve_response.status_code == 200
    assert approve_response.json()["run"]["status"] == "completed"

    approved_detail = client.get(f"/runs/{run_id}/status-detail")
    assert approved_detail.status_code == 200
    assert approved_detail.json()["effective_review_state"] == "human_approved"
    assert approved_detail.json()["latest_review_verdict"]["reviewer_type"] == "human"


def test_api_human_review_reject_fails_run(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Research reject via API", "preset_id": "research_spike"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")
    client.post(f"/runs/{run_id}/resume")

    reject_response = client.post(f"/runs/{run_id}/reject")
    assert reject_response.status_code == 200
    assert reject_response.json()["run"]["status"] == "failed"

    detail_response = client.get(f"/runs/{run_id}/status-detail")
    assert detail_response.status_code == 200
    assert detail_response.json()["effective_review_state"] == "human_rejected"
    assert detail_response.json()["latest_review_verdict"]["decision"] == "fail"
    assert detail_response.json()["failure_reason"] == "human_review_rejected"
    assert detail_response.json()["recoverability_hint"] == "inspect_evidence_then_recompile"


def test_api_blocks_resume_before_compile(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Resume too early", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]

    response = client.post(f"/runs/{run_id}/resume")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_state_transition"
    assert response.json()["error"]["details"]["allowed_statuses"] == ["prepared"]


def test_api_blocks_review_before_awaiting_review(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Review too early", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")

    approve_response = client.post(f"/runs/{run_id}/approve")
    assert approve_response.status_code == 409
    assert approve_response.json()["error"]["code"] == "invalid_state_transition"


def test_api_blocks_recompile_after_terminal_run(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Terminal recompile", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")
    client.post(f"/runs/{run_id}/resume")

    recompile_response = client.post(f"/runs/{run_id}/recompile")
    assert recompile_response.status_code == 409
    assert recompile_response.json()["error"]["code"] == "invalid_state_transition"
