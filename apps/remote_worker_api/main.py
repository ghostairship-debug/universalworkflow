from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from packages.contracts import (
    ExecutionTargetKind,
    ExecutionTargetRef,
    LeaseRenewalRecord,
    TaskPacket,
    WorkerPoolProfile,
)
from packages.worker_adapters.noop_adapter import NoopAdapter
from packages.worker_adapters.opencode_adapter import OpenCodeAdapter
from packages.worker_adapters.router import WorkerRouter
from packages.worker_adapters.shell_adapter import ShellAdapter


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _default_json_post(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None,
    timeout_seconds: int,
) -> dict[str, Any]:
    request = Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"callback HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"callback request failed: {exc}") from exc


class DispatchRequest(BaseModel):
    dispatch_id: str = Field(min_length=1)
    lease_id: str = Field(min_length=1)
    packet: dict[str, Any]
    profile: dict[str, Any]
    callback_base_url: str | None = None
    timeout_seconds: int = Field(default=120, ge=1)
    scheduler_context: dict[str, Any] | None = None


def create_app(
    *,
    callback_post: Callable[[str, dict[str, Any], dict[str, str] | None, int], dict[str, Any]] | None = None,
    worker_router: WorkerRouter | None = None,
) -> FastAPI:
    post_json = callback_post or _default_json_post
    router = worker_router or WorkerRouter([ShellAdapter(), OpenCodeAdapter(), NoopAdapter()])
    app = FastAPI(title="Universal Agentic Workflow Remote Worker API", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {"ok": True, "adapter_count": len(router.routes())}

    @app.post("/dispatches")
    def dispatch(
        payload: DispatchRequest,
        x_workflow_shared_secret: str | None = Header(default=None),
    ) -> dict[str, Any]:
        packet = TaskPacket.model_validate(payload.packet)
        profile = WorkerPoolProfile.model_validate(payload.profile)
        if profile.auth_mode == "shared_secret":
            if not profile.shared_secret_env:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="shared_secret auth requires shared_secret_env",
                )
            expected_secret = os.getenv(profile.shared_secret_env)
            if not expected_secret or x_workflow_shared_secret != expected_secret:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="shared secret validation failed",
                )

        adapter = router.route(packet)
        started_at = _utc_now()
        heartbeat_at = _utc_now()
        lease_expires_at = heartbeat_at + timedelta(seconds=profile.lease_ttl_seconds)
        authority_term_no = (payload.scheduler_context or {}).get("authority_term_no") or (
            payload.scheduler_context or {}
        ).get("term_no")
        decision_index = (payload.scheduler_context or {}).get("decision_index") or (
            payload.scheduler_context or {}
        ).get("commit_index")
        execution_target = ExecutionTargetRef(
            target_kind=ExecutionTargetKind.external_worker_pool,
            worker_pool_id=profile.worker_pool_id,
            adapter_name=adapter.normalized_name(),
            dispatch_mode=profile.dispatch_mode,
            worker_name=profile.name,
            worker_id=f"remote_{profile.worker_pool_id}",
            dispatched_at=started_at.isoformat(),
            dispatch_id=payload.dispatch_id,
            base_url=profile.base_url,
            callback_base_url=payload.callback_base_url,
            auth_mode=profile.auth_mode,
            last_callback_at=heartbeat_at.isoformat(),
            control_plane_id=(payload.scheduler_context or {}).get("control_plane_id"),
            committed_lease_id=(payload.scheduler_context or {}).get("committed_lease_id"),
            fencing_token=(payload.scheduler_context or {}).get("fencing_token"),
            term_no=(payload.scheduler_context or {}).get("term_no"),
            authority_term_no=authority_term_no,
            commit_index=(payload.scheduler_context or {}).get("commit_index"),
            decision_index=decision_index,
        )
        renewal = LeaseRenewalRecord(
            run_id=packet.run_id,
            runtime_task_id=packet.runtime_task_id,
            worker_pool_id=profile.worker_pool_id,
            lease_id=payload.lease_id,
            status="renewed",
            renewed_at=heartbeat_at,
            heartbeat_at=heartbeat_at,
            lease_expires_at=lease_expires_at,
            callback_id=f"callback_{uuid4().hex[:12]}",
            source="remote_worker",
            control_plane_id=(payload.scheduler_context or {}).get("control_plane_id"),
            committed_lease_id=(payload.scheduler_context or {}).get("committed_lease_id"),
            fencing_token=(payload.scheduler_context or {}).get("fencing_token"),
            term_no=(payload.scheduler_context or {}).get("term_no"),
            authority_term_no=authority_term_no,
            commit_index=(payload.scheduler_context or {}).get("commit_index"),
            decision_index=decision_index,
        )

        callback_headers = {"X-Workflow-Shared-Secret": x_workflow_shared_secret} if x_workflow_shared_secret else {}
        if payload.callback_base_url:
            post_json(
                f"{payload.callback_base_url.rstrip('/')}/worker-callbacks/heartbeat",
                {
                    "callback_id": renewal.callback_id,
                    "dispatch_id": payload.dispatch_id,
                    "run_id": packet.run_id,
                    "runtime_task_id": packet.runtime_task_id,
                    "lease_id": payload.lease_id,
                    "worker_pool_id": profile.worker_pool_id,
                    "execution_target": execution_target.model_dump(mode="json"),
                    "heartbeat_at": heartbeat_at.isoformat(),
                    "lease_expires_at": lease_expires_at.isoformat(),
                },
                callback_headers,
                payload.timeout_seconds,
            )

        execution_result = adapter.launch(packet)
        execution_target.last_callback_at = _utc_now().isoformat()
        completion_callback_id = f"callback_{uuid4().hex[:12]}"
        execution_metadata = {
            **execution_result.metadata,
            "execution_target": execution_target.model_dump(mode="json"),
            "lease_renewals": [renewal.model_dump(mode="json")],
            "dispatch_id": payload.dispatch_id,
        }
        execution_result_payload = {
            "runtime_task_id": execution_result.runtime_task_id,
            "return_code": execution_result.return_code,
            "stdout": execution_result.stdout,
            "stderr": execution_result.stderr,
            "started_at": execution_result.started_at.isoformat(),
            "finished_at": execution_result.finished_at.isoformat(),
            "duration_ms": execution_result.duration_ms,
            "artifact_paths": execution_result.artifact_paths,
            "adapter_name": execution_result.adapter_name,
            "metadata": execution_metadata,
        }

        if payload.callback_base_url:
            post_json(
                f"{payload.callback_base_url.rstrip('/')}/worker-callbacks/completion",
                {
                    "callback_id": completion_callback_id,
                    "dispatch_id": payload.dispatch_id,
                    "run_id": packet.run_id,
                    "runtime_task_id": packet.runtime_task_id,
                    "lease_id": payload.lease_id,
                    "worker_pool_id": profile.worker_pool_id,
                    "execution_target": execution_target.model_dump(mode="json"),
                    "lease_renewals": [renewal.model_dump(mode="json")],
                    "execution_result": execution_result_payload,
                },
                callback_headers,
                payload.timeout_seconds,
            )

        return {
            "dispatch_id": payload.dispatch_id,
            "execution_target": execution_target.model_dump(mode="json"),
            "lease_renewals": [renewal.model_dump(mode="json")],
            "execution_result": execution_result_payload,
        }

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("apps.remote_worker_api.main:app", host="127.0.0.1", port=8011, reload=False)


if __name__ == "__main__":
    run()
