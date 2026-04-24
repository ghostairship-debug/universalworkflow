from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from apps.orchestrator_api.request_models import (
    SchedulerHeartbeatRequest,
    SchedulerProposalRequest,
    SchedulerReleaseRequest,
)
from packages.core_domain.services import OrchestratorService


def build_scheduler_router(service: OrchestratorService) -> APIRouter:
    router = APIRouter()

    def _disabled_payload(**extra: object) -> dict:
        return {
            **service.scheduler_authority_cluster.cluster_snapshot(),
            **extra,
        }

    @router.post("/scheduler/proposals", status_code=status.HTTP_201_CREATED)
    def submit_scheduler_proposal(payload: SchedulerProposalRequest) -> dict:
        if not service.scheduler_authority_cluster_enabled:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=_disabled_payload(
                    granted=False,
                    reason="scheduler_authority_cluster_disabled_local_only",
                    requested_control_plane_id=payload.control_plane_id,
                    requested_run_id=payload.run_id,
                    requested_runtime_task_id=payload.runtime_task_id,
                ),
            )
        return service.submit_scheduler_proposal(
            control_plane_id=payload.control_plane_id,
            run_id=payload.run_id,
            runtime_task_id=payload.runtime_task_id,
            domain_kind=payload.domain_kind,
            domain_key=payload.domain_key,
            requested_lease_seconds=payload.requested_lease_seconds,
            requested_epoch=payload.requested_epoch,
        )

    @router.post("/scheduler/heartbeats", status_code=status.HTTP_201_CREATED)
    def record_scheduler_heartbeat(payload: SchedulerHeartbeatRequest) -> dict:
        if not service.scheduler_authority_cluster_enabled:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=_disabled_payload(
                    accepted=False,
                    reason="scheduler_authority_cluster_disabled_local_only",
                    requested_control_plane_id=payload.control_plane_id,
                ),
            )
        return service.record_scheduler_peer_heartbeat(
            control_plane_id=payload.control_plane_id,
            status=payload.status,
            lease_count=payload.lease_count,
            observed_at=payload.observed_at,
        )

    @router.post("/scheduler/releases/{lease_id}")
    def release_scheduler_lease(lease_id: str, payload: SchedulerReleaseRequest | None = None) -> dict:
        if not service.scheduler_authority_cluster_enabled:
            return _disabled_payload(
                released=False,
                lease_id=lease_id,
                reason="scheduler_authority_cluster_disabled_local_only",
            )
        return service.release_scheduler_lease(
            lease_id,
            release_reason=payload.release_reason if payload is not None else "control_plane_release",
        )

    @router.get("/scheduler/leases/{lease_id}")
    def get_scheduler_lease(lease_id: str) -> dict:
        if not service.scheduler_authority_cluster_enabled:
            return _disabled_payload(
                found=False,
                lease_id=lease_id,
                reason="scheduler_authority_cluster_disabled_local_only",
            )
        return service.get_scheduler_lease(lease_id)

    @router.get("/scheduler/cluster")
    def get_scheduler_cluster() -> dict:
        return service.scheduler_authority_cluster.cluster_snapshot()

    return router
