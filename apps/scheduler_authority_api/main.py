from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from packages.core_domain.config import build_effective_config
from packages.core_domain.db import DEFAULT_DB_PATH, migrate
from packages.core_domain.errors import WorkflowError
from packages.core_domain.scheduler_authority import SchedulerAuthorityClusterService


class AuthorityHeartbeatRequest(BaseModel):
    node_id: str | None = None
    bind_url: str | None = None
    status: str = Field(default="active", min_length=1)
    role: str = Field(default="peer", min_length=1)
    observed_at: str | None = None


class AuthorityProposalRequest(BaseModel):
    control_plane_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    runtime_task_id: str = Field(min_length=1)
    domain_kind: str = Field(default="runtime_task", min_length=1)
    domain_key: str = Field(min_length=1)
    requested_lease_seconds: int = Field(default=300, ge=1)
    requested_epoch: int = Field(default=1, ge=1)
    authority_node_id: str | None = None
    authority_bind_url: str | None = None


class AuthorityVoteRequest(BaseModel):
    proposal_id: str = Field(min_length=1)
    voter_node_id: str = Field(min_length=1)
    vote: str = Field(default="granted", min_length=1)
    reason: str = Field(default="manual_peer_accept", min_length=1)


class AuthorityReleaseRequest(BaseModel):
    release_reason: str = Field(default="authority_release", min_length=1)


def error_body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def create_app(db_path: str | Path | None = None) -> FastAPI:
    effective_config = build_effective_config(explicit_db_path=db_path)
    resolved_db_path = (
        Path(effective_config["db"]["path"])
        if db_path is not None or effective_config["db"]["path"]
        else DEFAULT_DB_PATH
    )
    migrate(resolved_db_path)
    cluster = SchedulerAuthorityClusterService(
        resolved_db_path,
        node_id=effective_config["scheduler_authority"]["node_id"],
        bind_url=effective_config["scheduler_authority"]["bind_url"],
        peer_urls=effective_config["scheduler_authority"]["peer_urls"],
        quorum_size=effective_config["scheduler_authority"]["quorum_size"],
        election_timeout_ms=effective_config["scheduler_authority"]["election_timeout_ms"],
        heartbeat_interval_ms=effective_config["scheduler_authority"]["heartbeat_interval_ms"],
    )
    app = FastAPI(title="Universal Agentic Workflow Scheduler Authority API", version="0.1.0")

    @app.exception_handler(WorkflowError)
    async def workflow_error_handler(_: Request, exc: WorkflowError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_body("validation_error", "request validation failed", {"errors": exc.errors()}),
        )

    @app.get("/healthz")
    def healthz() -> dict:
        return {
            "ok": True,
            "mode": effective_config["scheduler_authority"]["mode"],
            "authority_mode": effective_config["scheduler_authority"]["authority_mode"],
        }

    @app.post("/authority/heartbeats", status_code=status.HTTP_201_CREATED)
    def heartbeat_authority(payload: AuthorityHeartbeatRequest) -> dict:
        return cluster.heartbeat_node(
            node_id=payload.node_id,
            bind_url=payload.bind_url,
            status=payload.status,
            role=payload.role,
            observed_at=payload.observed_at,
        )

    @app.post("/authority/proposals", status_code=status.HTTP_201_CREATED)
    def submit_proposal(payload: AuthorityProposalRequest) -> dict:
        return cluster.submit_proposal(
            control_plane_id=payload.control_plane_id,
            run_id=payload.run_id,
            runtime_task_id=payload.runtime_task_id,
            domain_kind=payload.domain_kind,
            domain_key=payload.domain_key,
            requested_lease_seconds=payload.requested_lease_seconds,
            requested_epoch=payload.requested_epoch,
            authority_node_id=payload.authority_node_id,
            authority_bind_url=payload.authority_bind_url,
        )

    @app.post("/authority/votes", status_code=status.HTTP_201_CREATED)
    def record_vote(payload: AuthorityVoteRequest) -> dict:
        return cluster.record_vote(
            proposal_id=payload.proposal_id,
            voter_node_id=payload.voter_node_id,
            vote=payload.vote,
            reason=payload.reason,
        )

    @app.post("/authority/releases/{lease_id}")
    def release_lease(lease_id: str, payload: AuthorityReleaseRequest | None = None) -> dict:
        return cluster.release_lease(
            lease_id,
            release_reason=payload.release_reason if payload is not None else "authority_release",
        )

    @app.get("/authority/leases/{lease_id}")
    def get_lease(lease_id: str) -> dict:
        return cluster.get_lease(lease_id)

    @app.get("/authority/cluster")
    def get_cluster() -> dict:
        return cluster.cluster_snapshot()

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("apps.scheduler_authority_api.main:app", host="127.0.0.1", port=8020, reload=False)


if __name__ == "__main__":
    run()
