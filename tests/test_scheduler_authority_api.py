from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.scheduler_authority_api.main import create_app
from packages.core_domain.db import migrate
from packages.core_domain.repositories import PresetRepository
from packages.core_domain.services import OrchestratorService


def _build_client(db_path: Path) -> TestClient:
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    return TestClient(create_app(db_path))


def test_scheduler_authority_api_grants_quorum_committed_lease_and_releases_it(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("WORKFLOW_SCHEDULER_AUTHORITY_NODE_ID", "authority-a")
    monkeypatch.setenv("WORKFLOW_SCHEDULER_AUTHORITY_BIND_URL", "http://authority-a.internal")

    db_path = tmp_path / "workflow.db"
    client = _build_client(db_path)
    service = OrchestratorService(db_path)

    run = service.create_run("Authority API roundtrip", "feature_delivery")
    service.compile_run(run.run_id)
    runtime_task_id = service.get_status_detail(run.run_id)["runtime_task_ids"][0]

    first_heartbeat = client.post(
        "/authority/heartbeats",
        json={"node_id": "authority-b", "bind_url": "http://authority-b.internal"},
    )
    second_heartbeat = client.post(
        "/authority/heartbeats",
        json={"node_id": "authority-c", "bind_url": "http://authority-c.internal"},
    )
    proposal = client.post(
        "/authority/proposals",
        json={
            "control_plane_id": "control_plane_alpha",
            "run_id": run.run_id,
            "runtime_task_id": runtime_task_id,
            "domain_key": runtime_task_id,
            "requested_epoch": 2,
        },
    )

    proposal_payload = proposal.json()
    lease_id = proposal_payload["decision"]["lease_id"]
    lease_response = client.get(f"/authority/leases/{lease_id}")
    cluster_response = client.get("/authority/cluster")
    release_response = client.post(f"/authority/releases/{lease_id}", json={"release_reason": "test_release"})

    assert first_heartbeat.status_code == 201
    assert second_heartbeat.status_code == 201
    assert proposal.status_code == 201
    assert proposal_payload["granted"] is True
    assert proposal_payload["cluster"]["node_count"] >= 3
    assert proposal_payload["cluster"]["quorum_size"] == 2
    assert proposal_payload["term"]["leader_node_id"] == "authority-a"
    assert proposal_payload["term"]["authority_node_id"] == "authority-a"
    assert proposal_payload["term"]["authority_term_no"] == proposal_payload["term"]["term_no"]
    assert proposal_payload["term"]["decision_index"] == proposal_payload["term"]["commit_index"]
    assert len(proposal_payload["votes"]) >= 2
    assert proposal_payload["committed_lease"]["control_plane_id"] == "control_plane_alpha"
    assert proposal_payload["committed_lease"]["lease_epoch"] >= 2
    assert (
        proposal_payload["committed_lease"]["authority_term_no"]
        == proposal_payload["committed_lease"]["term_no"]
    )
    assert (
        proposal_payload["committed_lease"]["decision_index"]
        == proposal_payload["committed_lease"]["commit_index"]
    )
    assert lease_response.status_code == 200
    assert lease_response.json()["active"] is True
    assert (
        lease_response.json()["committed_lease"]["authority_term_no"]
        == lease_response.json()["committed_lease"]["term_no"]
    )
    assert (
        lease_response.json()["committed_lease"]["decision_index"]
        == lease_response.json()["committed_lease"]["commit_index"]
    )
    assert cluster_response.status_code == 200
    assert cluster_response.json()["leader_node_id"] == "authority-a"
    assert cluster_response.json()["authority_node_id"] == "authority-a"
    assert cluster_response.json()["authority_term_no"] == cluster_response.json()["term_no"]
    assert cluster_response.json()["decision_index"] == cluster_response.json()["commit_index"]
    assert release_response.status_code == 200
    assert release_response.json()["committed_lease"]["status"] == "released"
    assert (
        release_response.json()["committed_lease"]["authority_term_no"]
        == release_response.json()["committed_lease"]["term_no"]
    )
    assert (
        release_response.json()["committed_lease"]["decision_index"]
        == release_response.json()["committed_lease"]["commit_index"]
    )


def test_scheduler_authority_api_health_and_cluster_are_semantically_honest(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = _build_client(db_path)

    health_response = client.get("/healthz")
    cluster_response = client.get("/authority/cluster")

    assert health_response.status_code == 200
    assert health_response.json()["mode"] == "quorum"
    assert health_response.json()["authority_mode"] == "single_store_quorum"
    assert cluster_response.status_code == 200
    assert cluster_response.json()["mode"] == "quorum"
    assert cluster_response.json()["authority_mode"] == "single_store_quorum"
    assert cluster_response.json()["authority_node_id"] == cluster_response.json()["leader_node_id"]
    assert cluster_response.json()["authority_term_no"] == cluster_response.json()["term_no"]
    assert cluster_response.json()["decision_index"] == cluster_response.json()["commit_index"]
