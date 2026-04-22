from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from apps.orchestrator_api.main import create_app as create_control_plane_app
from apps.remote_worker_api.main import create_app as create_remote_worker_app
from apps.scheduler_authority_api.main import create_app as create_authority_app
from packages.core_domain.db import migrate, unit_of_work
from packages.core_domain.external_workers import ExternalWorkerGateway
from packages.core_domain.repositories import PresetRepository


@contextmanager
def _temporary_env(overrides: dict[str, str | None]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in overrides}
    try:
        for key, value in overrides.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _client_post(client: TestClient, url: str, payload: dict[str, Any], headers: dict | None, _: int) -> dict:
    response = client.post(urlsplit(url).path, json=payload, headers=headers or {})
    response.raise_for_status()
    return response.json()


def run_cluster_cutover_demo(db_path: Path) -> dict[str, Any]:
    db_path = Path(db_path)
    base_env = {
        "UAWO_ENABLE_EXTERNAL_WORKER_POOLS": "1",
        "WORKFLOW_WORKER_POOL_ID": "remote_http_shell",
        "WORKFLOW_REMOTE_WORKER_SHARED_SECRET": "secret-demo",
    }
    with _temporary_env(base_env):
        migrate(db_path)
        PresetRepository(db_path).seed_defaults()

        with _temporary_env(
            {
                "WORKFLOW_SCHEDULER_AUTHORITY_NODE_ID": "authority-a",
                "WORKFLOW_SCHEDULER_AUTHORITY_BIND_URL": "http://authority-a.internal",
            }
        ):
            authority_client = TestClient(create_authority_app(db_path))
        authority_client.post(
            "/authority/heartbeats",
            json={"node_id": "authority-b", "bind_url": "http://authority-b.internal"},
        )
        authority_client.post(
            "/authority/heartbeats",
            json={"node_id": "authority-c", "bind_url": "http://authority-c.internal"},
        )
        cluster_before = authority_client.get("/authority/cluster").json()

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

        with _temporary_env({"WORKFLOW_CONTROL_PLANE_ID": "control_plane_alpha"}):
            alpha_client = TestClient(create_control_plane_app(db_path, external_worker_gateway=gateway))
        control_plane_holder["client"] = alpha_client

        dogfood_run = alpha_client.post(
            "/runs",
            json={"goal": "Cluster-backed remote worker dogfood", "preset_id": "feature_delivery"},
        ).json()
        alpha_client.post(f"/runs/{dogfood_run['run_id']}/compile")
        alpha_resume = alpha_client.post(f"/runs/{dogfood_run['run_id']}/resume")
        dogfood_detail = alpha_client.get(f"/runs/{dogfood_run['run_id']}/status-detail").json()
        dogfood_execution_target = dogfood_detail.get("execution_target") or (
            (dogfood_detail.get("last_runtime_state") or {}).get("state_payload") or {}
        ).get("execution_target")

        takeover_run = alpha_client.post(
            "/runs",
            json={"goal": "Cluster takeover drill", "preset_id": "feature_delivery"},
        ).json()
        takeover_compile = alpha_client.post(f"/runs/{takeover_run['run_id']}/compile").json()
        runtime_task_id = takeover_compile["runtime_task_id"]
        alpha_proposal = alpha_client.post(
            "/scheduler/proposals",
            json={
                "control_plane_id": "control_plane_alpha",
                "run_id": takeover_run["run_id"],
                "runtime_task_id": runtime_task_id,
                "domain_key": runtime_task_id,
                "requested_lease_seconds": 1,
            },
        ).json()

        with unit_of_work(db_path) as connection:
            expired = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
            connection.execute(
                "UPDATE scheduler_committed_leases SET lease_expires_at = ? WHERE committed_lease_id = ?",
                (expired, alpha_proposal["committed_lease"]["committed_lease_id"]),
            )
            connection.execute(
                "UPDATE authority_node_identities SET last_heartbeat_at = ? WHERE node_id = ?",
                (expired, "authority-a"),
            )

        with _temporary_env({"WORKFLOW_CONTROL_PLANE_ID": "control_plane_beta"}):
            beta_client = TestClient(create_control_plane_app(db_path, external_worker_gateway=gateway))
        beta_proposal = beta_client.post(
            "/scheduler/proposals",
            json={
                "control_plane_id": "control_plane_beta",
                "run_id": takeover_run["run_id"],
                "runtime_task_id": runtime_task_id,
                "domain_key": runtime_task_id,
                "requested_epoch": 2,
            },
        ).json()
        control_plane_holder["client"] = beta_client
        beta_resume = beta_client.post(f"/runs/{takeover_run['run_id']}/resume")
        operator_view = beta_client.get(f"/runs/{takeover_run['run_id']}/operator-view").json()

        stale_callback = alpha_client.post(
            "/worker-callbacks/completion",
            json={
                "callback_id": "callback_cluster_demo_stale_alpha",
                "dispatch_id": "dispatch_cluster_demo_stale_alpha",
                "run_id": takeover_run["run_id"],
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
        alpha_detail = alpha_client.get(f"/runs/{takeover_run['run_id']}/status-detail").json()
        cluster_after = beta_client.get("/scheduler/cluster").json()

    result = {
        "cluster_before": cluster_before,
        "cluster_after": cluster_after,
        "dogfood_run_id": dogfood_run["run_id"],
        "dogfood_run_status": alpha_resume.json()["run"]["status"],
        "dogfood_dispatch_mode": (
            dogfood_execution_target.get("dispatch_mode") if isinstance(dogfood_execution_target, dict) else None
        ),
        "takeover_run_id": takeover_run["run_id"],
        "takeover_run_status": beta_resume.json()["run"]["status"],
        "takeover_committed_owner": beta_proposal["committed_lease"]["control_plane_id"],
        "takeover_leader_node_id": cluster_after["leader_node_id"],
        "stale_callback_status_code": stale_callback.status_code,
        "stale_callback_error_code": stale_callback.json().get("error", {}).get("code"),
        "alpha_stale_plane_detected": alpha_detail["scheduler_authority"]["stale_plane_detected"],
        "alpha_active_committed_owner": alpha_detail["scheduler_authority"]["active_committed_lease"][
            "control_plane_id"
        ],
        "operator_handoff_count": len(operator_view.get("handoffs") or []),
        "operator_cluster_topology_nodes": len(
            ((operator_view.get("cluster_overview") or {}).get("cluster") or {}).get("nodes")
            or (operator_view.get("cluster_overview") or {}).get("nodes")
            or []
        ),
        "operator_cluster_topology_leader": (operator_view.get("cluster_overview") or {}).get("leader_node_id"),
    }
    result["passed"] = all(
        [
            result["cluster_before"]["mode"] == "quorum",
            result["cluster_before"]["node_count"] >= 3,
            result["dogfood_run_status"] == "completed",
            result["dogfood_dispatch_mode"] == "remote_http",
            result["takeover_run_status"] == "completed",
            result["takeover_committed_owner"] == "control_plane_beta",
            result["takeover_leader_node_id"] != "authority-a",
            result["stale_callback_status_code"] == 409,
            result["stale_callback_error_code"] == "scheduler_arbitration_error",
            result["alpha_stale_plane_detected"] is True,
            result["alpha_active_committed_owner"] == "control_plane_beta",
            result["operator_handoff_count"] >= 1,
            result["operator_cluster_topology_nodes"] >= 3,
        ]
    )
    return result


def validate_cluster_flow(_: dict[str, str], db_path: Path) -> dict[str, Any]:
    result = run_cluster_cutover_demo(db_path)
    return result
