from __future__ import annotations

from fastapi import APIRouter, status

from apps.orchestrator_api.request_models import (
    SchedulerHeartbeatRequest,
    SchedulerProposalRequest,
    SchedulerReleaseRequest,
)
from packages.core_domain.services import OrchestratorService


def build_scheduler_router(service: OrchestratorService) -> APIRouter:
    router = APIRouter()

    @router.post("/scheduler/proposals", status_code=status.HTTP_201_CREATED)
    def submit_scheduler_proposal(payload: SchedulerProposalRequest) -> dict:
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
        return service.record_scheduler_peer_heartbeat(
            control_plane_id=payload.control_plane_id,
            status=payload.status,
            lease_count=payload.lease_count,
            observed_at=payload.observed_at,
        )

    @router.post("/scheduler/releases/{lease_id}")
    def release_scheduler_lease(lease_id: str, payload: SchedulerReleaseRequest | None = None) -> dict:
        return service.release_scheduler_lease(
            lease_id,
            release_reason=payload.release_reason if payload is not None else "control_plane_release",
        )

    @router.get("/scheduler/leases/{lease_id}")
    def get_scheduler_lease(lease_id: str) -> dict:
        return service.get_scheduler_lease(lease_id)

    @router.get("/scheduler/cluster")
    def get_scheduler_cluster() -> dict:
        return service.scheduler_authority_cluster.cluster_snapshot()

    return router
