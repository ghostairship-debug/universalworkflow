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
        RunEventType.phase_created,
        RunEventType.runtime_task_created,
    ]
