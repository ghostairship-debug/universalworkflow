from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request, status

from apps.orchestrator_api.request_models import WorkerCompletionCallbackRequest, WorkerHeartbeatCallbackRequest
from packages.core_domain.services import OrchestratorService


def build_workers_router(service: OrchestratorService) -> APIRouter:
    router = APIRouter()

    def _worker_pool_profile(worker_pool_id: str) -> dict:
        for profile in service.list_worker_pool_profiles():
            if profile["worker_pool_id"] == worker_pool_id:
                return profile
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"worker pool `{worker_pool_id}` not found")

    def _validate_worker_callback_secret(worker_pool_id: str, secret: str | None) -> None:
        profile = _worker_pool_profile(worker_pool_id)
        auth_mode = str(profile.get("auth_mode") or "none")
        if auth_mode != "shared_secret":
            return
        shared_secret_env = profile.get("shared_secret_env")
        if not shared_secret_env:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="shared_secret_env missing")
        expected = os.getenv(str(shared_secret_env))
        if not expected or secret != expected:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="shared secret validation failed")

    @router.post("/worker-callbacks/heartbeat")
    def worker_heartbeat_callback(
        payload: WorkerHeartbeatCallbackRequest,
        request: Request,
    ) -> dict:
        _validate_worker_callback_secret(payload.worker_pool_id, request.headers.get("X-Workflow-Shared-Secret"))
        return service.record_worker_heartbeat(
            callback_id=payload.callback_id,
            dispatch_id=payload.dispatch_id,
            run_id=payload.run_id,
            runtime_task_id=payload.runtime_task_id,
            lease_id=payload.lease_id,
            worker_pool_id=payload.worker_pool_id,
            heartbeat_at=payload.heartbeat_at,
            lease_expires_at=payload.lease_expires_at,
            execution_target=payload.execution_target,
        )

    @router.post("/worker-callbacks/completion")
    def worker_completion_callback(
        payload: WorkerCompletionCallbackRequest,
        request: Request,
    ) -> dict:
        _validate_worker_callback_secret(payload.worker_pool_id, request.headers.get("X-Workflow-Shared-Secret"))
        return service.record_worker_completion(
            callback_id=payload.callback_id,
            dispatch_id=payload.dispatch_id,
            run_id=payload.run_id,
            runtime_task_id=payload.runtime_task_id,
            lease_id=payload.lease_id,
            worker_pool_id=payload.worker_pool_id,
            execution_target=payload.execution_target,
            lease_renewals=payload.lease_renewals,
            execution_result=payload.execution_result,
        )

    return router
