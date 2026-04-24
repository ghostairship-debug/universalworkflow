from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from apps.orchestrator_api.main import create_app as create_control_plane_app
from apps.remote_worker_api.main import create_app as create_remote_worker_app
from packages.core_domain.db import migrate
from packages.core_domain.db import unit_of_work
from packages.core_domain.external_workers import ExternalWorkerGateway
from packages.core_domain.repositories import PresetRepository


def _client_post(client: TestClient, url: str, payload: dict, headers: dict | None, _: int) -> dict:
    response = client.post(urlsplit(url).path, json=payload, headers=headers or {})
    response.raise_for_status()
    return response.json()


def test_remote_worker_dispatch_and_callbacks_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UAWO_ENABLE_EXTERNAL_WORKER_POOLS", "1")
    monkeypatch.setenv("WORKFLOW_WORKER_POOL_ID", "remote_http_shell")
    monkeypatch.setenv("WORKFLOW_REMOTE_WORKER_SHARED_SECRET", "secret-demo")

    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()

    control_plane_holder: dict[str, TestClient] = {}

    remote_app = create_remote_worker_app(
        callback_post=lambda url, payload, headers, timeout: _client_post(
            control_plane_holder["client"],
            url,
            payload,
            headers,
            timeout,
        )
    )
    remote_client = TestClient(remote_app)
    gateway = ExternalWorkerGateway(
        http_post=lambda url, payload, headers, timeout: _client_post(remote_client, url, payload, headers, timeout)
    )
    control_client = TestClient(create_control_plane_app(db_path, external_worker_gateway=gateway))
    control_plane_holder["client"] = control_client

    run = control_client.post("/runs", json={"goal": "Remote worker roundtrip", "preset_id": "feature_delivery"}).json()
    compile_response = control_client.post(f"/runs/{run['run_id']}/compile")
    resume_response = control_client.post(f"/runs/{run['run_id']}/resume")
    detail_response = control_client.get(f"/runs/{run['run_id']}/status-detail")
    timeline_response = control_client.get(f"/runs/{run['run_id']}/timeline")

    assert compile_response.status_code == 200
    assert resume_response.status_code == 200
    assert resume_response.json()["run"]["status"] == "completed"
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["execution_target"]["dispatch_mode"] == "remote_http"
    assert detail["execution_target"]["worker_pool_id"] == "remote_http_shell"
    assert detail["execution_target"]["authority_term_no"] == detail["execution_target"]["term_no"]
    assert detail["execution_target"]["decision_index"] == detail["execution_target"]["commit_index"]
    assert detail["worker_lease_projection"]["latest_worker_name"] == "Remote HTTP Shell Pool"
    assert len(detail["lease_renewals"]) >= 1
    assert detail["lease_renewals"][0]["authority_term_no"] == detail["lease_renewals"][0]["term_no"]
    assert detail["lease_renewals"][0]["decision_index"] == detail["lease_renewals"][0]["commit_index"]
    assert (
        detail["last_runtime_state"]["state_payload"]["committed_scheduler_lease"]["authority_term_no"]
        == detail["last_runtime_state"]["state_payload"]["committed_scheduler_lease"]["term_no"]
    )
    assert (
        detail["last_runtime_state"]["state_payload"]["committed_scheduler_lease"]["decision_index"]
        == detail["last_runtime_state"]["state_payload"]["committed_scheduler_lease"]["commit_index"]
    )
    assert detail["last_runtime_state"]["state_payload"]["worker_callbacks"]["heartbeat"]
    assert detail["last_runtime_state"]["state_payload"]["worker_callbacks"]["completion"]
    assert timeline_response.status_code == 200
    assert {
        item["event_type"]
        for item in timeline_response.json()
    } >= {"worker_dispatch_accepted", "worker_heartbeat_received", "worker_completion_recorded"}


def test_remote_worker_completion_callback_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UAWO_ENABLE_EXTERNAL_WORKER_POOLS", "1")
    monkeypatch.setenv("WORKFLOW_WORKER_POOL_ID", "remote_http_shell")
    monkeypatch.setenv("WORKFLOW_REMOTE_WORKER_SHARED_SECRET", "secret-demo")

    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()

    control_plane_holder: dict[str, TestClient] = {}
    remote_app = create_remote_worker_app(
        callback_post=lambda url, payload, headers, timeout: _client_post(
            control_plane_holder["client"],
            url,
            payload,
            headers,
            timeout,
        )
    )
    remote_client = TestClient(remote_app)
    gateway = ExternalWorkerGateway(
        http_post=lambda url, payload, headers, timeout: _client_post(remote_client, url, payload, headers, timeout)
    )
    control_client = TestClient(create_control_plane_app(db_path, external_worker_gateway=gateway))
    control_plane_holder["client"] = control_client

    run = control_client.post("/runs", json={"goal": "Duplicate callback", "preset_id": "feature_delivery"}).json()
    control_client.post(f"/runs/{run['run_id']}/compile")
    control_client.post(f"/runs/{run['run_id']}/resume")

    detail = control_client.get(f"/runs/{run['run_id']}/status-detail").json()
    callback_history = detail["last_runtime_state"]["state_payload"]["worker_callback_history"]
    completion_callback = next(item for item in callback_history if item["type"] == "completion")

    duplicate_response = control_client.post(
        "/worker-callbacks/completion",
        json={
            "callback_id": completion_callback["callback_id"],
            "dispatch_id": completion_callback["dispatch_id"],
            "run_id": run["run_id"],
            "runtime_task_id": detail["runtime_task_ids"][0],
            "lease_id": completion_callback["lease_id"],
            "worker_pool_id": "remote_http_shell",
            "execution_target": detail["execution_target"],
            "lease_renewals": detail["lease_renewals"],
            "execution_result": detail["last_runtime_state"]["state_payload"]["remote_execution_result"],
        },
        headers={"X-Workflow-Shared-Secret": "secret-demo"},
    )

    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["duplicate"] is True


def test_remote_worker_callback_rejects_stale_control_plane_after_takeover(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UAWO_ENABLE_EXTERNAL_WORKER_POOLS", "1")
    monkeypatch.setenv("UAWO_ENABLE_SCHEDULER_AUTHORITY_CLUSTER", "1")
    monkeypatch.setenv("WORKFLOW_REMOTE_WORKER_SHARED_SECRET", "secret-demo")

    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()

    monkeypatch.setenv("WORKFLOW_CONTROL_PLANE_ID", "control_plane_alpha")
    alpha_client = TestClient(create_control_plane_app(db_path))

    run = alpha_client.post("/runs", json={"goal": "Takeover stale callback", "preset_id": "feature_delivery"}).json()
    compile_response = alpha_client.post(f"/runs/{run['run_id']}/compile")
    runtime_task_id = compile_response.json()["runtime_task_id"]
    alpha_proposal = alpha_client.post(
        "/scheduler/proposals",
        json={
            "control_plane_id": "control_plane_alpha",
            "run_id": run["run_id"],
            "runtime_task_id": runtime_task_id,
            "domain_key": runtime_task_id,
            "requested_lease_seconds": 1,
        },
    ).json()

    with unit_of_work(db_path) as connection:
        connection.execute(
            "UPDATE scheduler_committed_leases SET lease_expires_at = ? WHERE committed_lease_id = ?",
            (
                (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
                alpha_proposal["committed_lease"]["committed_lease_id"],
            ),
        )

    monkeypatch.setenv("WORKFLOW_CONTROL_PLANE_ID", "control_plane_beta")
    beta_client = TestClient(create_control_plane_app(db_path))
    beta_proposal = beta_client.post(
        "/scheduler/proposals",
        json={
            "control_plane_id": "control_plane_beta",
            "run_id": run["run_id"],
            "runtime_task_id": runtime_task_id,
            "domain_key": runtime_task_id,
            "requested_epoch": 2,
        },
    ).json()

    stale_callback = alpha_client.post(
        "/worker-callbacks/completion",
        json={
            "callback_id": "callback_stale_alpha_completion",
            "dispatch_id": "dispatch_stale_alpha",
            "run_id": run["run_id"],
            "runtime_task_id": runtime_task_id,
            "lease_id": alpha_proposal["decision"]["lease_id"],
            "worker_pool_id": "remote_http_shell",
            "execution_target": {
                "target_kind": "external_worker",
                "dispatch_mode": "remote_http",
                "worker_pool_id": "remote_http_shell",
                "worker_kind": "worker",
                "worker_name": "Remote HTTP Shell Pool",
                "worker_id": "remote_http_shell",
                "adapter_name": "shell",
                "control_plane_id": "control_plane_alpha",
                "committed_lease_id": alpha_proposal["committed_lease"]["committed_lease_id"],
                "fencing_token": alpha_proposal["committed_lease"]["fencing_token"],
                "term_no": alpha_proposal["committed_lease"]["term_no"],
                "authority_term_no": alpha_proposal["committed_lease"]["authority_term_no"],
                "commit_index": alpha_proposal["committed_lease"]["commit_index"],
                "decision_index": alpha_proposal["committed_lease"]["decision_index"],
            },
            "lease_renewals": [],
            "execution_result": {"return_code": 0},
        },
        headers={"X-Workflow-Shared-Secret": "secret-demo"},
    )
    alpha_detail = alpha_client.get(f"/runs/{run['run_id']}/status-detail").json()

    assert beta_proposal["granted"] is True
    assert beta_proposal["committed_lease"]["control_plane_id"] == "control_plane_beta"
    assert stale_callback.status_code == 409
    assert stale_callback.json()["error"]["code"] == "scheduler_arbitration_error"
    assert alpha_detail["scheduler_authority"]["stale_plane_detected"] is True
    assert alpha_detail["scheduler_authority"]["active_committed_lease"]["control_plane_id"] == "control_plane_beta"
