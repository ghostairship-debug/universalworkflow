from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from packages.core_domain.db import DEFAULT_DB_PATH, migrate
from packages.core_domain.errors import WorkflowError
from packages.core_domain.services import OrchestratorService


class CreateRunRequest(BaseModel):
    goal: str = Field(min_length=1)
    preset_id: str = Field(min_length=1)


def error_body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def create_app(db_path: str | Path | None = None) -> FastAPI:
    resolved_db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    migrate(resolved_db_path)
    service = OrchestratorService(resolved_db_path)
    app = FastAPI(title="Universal Agentic Workflow Orchestrator API", version="0.1.0")

    @app.exception_handler(WorkflowError)
    async def workflow_error_handler(_: Request, exc: WorkflowError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_body("validation_error", "request validation failed", {"errors": exc.errors()}),
        )

    @app.get("/presets")
    def list_presets() -> list[dict]:
        return [preset.model_dump(mode="json") for preset in service.list_presets()]

    @app.post("/runs", status_code=status.HTTP_201_CREATED)
    def create_run(payload: CreateRunRequest) -> dict:
        run = service.create_run(goal=payload.goal, preset_id=payload.preset_id)
        return run.model_dump(mode="json")

    @app.get("/runs/{run_id}")
    def get_run(run_id: str) -> dict:
        return service.get_run(run_id).model_dump(mode="json")

    @app.post("/runs/{run_id}/compile")
    def compile_run(run_id: str) -> dict:
        bundle = service.compile_run(run_id)
        return {
            "run": bundle.run.model_dump(mode="json"),
            "runtime_task_id": bundle.task_packet.runtime_task_id,
            "handoff_id": bundle.handoff.handoff_id,
            "state_ref_id": bundle.state_ref.state_ref_id,
        }

    @app.post("/runs/{run_id}/recompile")
    def recompile_run(run_id: str) -> dict:
        bundle = service.recompile_run(run_id)
        return {
            "run": bundle.run.model_dump(mode="json"),
            "runtime_task_id": bundle.task_packet.runtime_task_id,
            "handoff_id": bundle.handoff.handoff_id,
            "state_ref_id": bundle.state_ref.state_ref_id,
        }

    @app.post("/runs/{run_id}/resume")
    def resume_run(run_id: str) -> dict:
        bundle = service.resume_run(run_id)
        return {
            "run": bundle.run.model_dump(mode="json"),
            "evidence_id": bundle.evidence.evidence_id,
            "review_decision": bundle.review_verdict.decision if bundle.review_verdict is not None else None,
        }

    @app.post("/runs/{run_id}/approve")
    def approve_run(run_id: str) -> dict:
        bundle = service.approve_run_review(run_id)
        return {
            "run": bundle.run.model_dump(mode="json"),
            "evidence_id": bundle.evidence.evidence_id,
            "review_decision": bundle.review_verdict.decision,
        }

    @app.post("/runs/{run_id}/reject")
    def reject_run(run_id: str) -> dict:
        bundle = service.reject_run_review(run_id)
        return {
            "run": bundle.run.model_dump(mode="json"),
            "evidence_id": bundle.evidence.evidence_id,
            "review_decision": bundle.review_verdict.decision,
        }

    @app.get("/runs/{run_id}/timeline")
    def get_run_timeline(run_id: str) -> list[dict]:
        return [event.model_dump(mode="json") for event in service.get_timeline(run_id)]

    @app.get("/runs/{run_id}/status-detail")
    def get_run_status_detail(run_id: str) -> dict:
        return service.get_status_detail(run_id)

    @app.get("/runs/{run_id}/handoffs")
    def get_run_handoffs(run_id: str) -> list[dict]:
        return [handoff.model_dump(mode="json") for handoff in service.list_handoffs(run_id)]

    @app.get("/tasks/{runtime_task_id}/evidence")
    def get_task_evidence(runtime_task_id: str) -> dict:
        return service.get_task_evidence(runtime_task_id).model_dump(mode="json")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("apps.orchestrator_api.main:app", host="127.0.0.1", port=8000, reload=False)
