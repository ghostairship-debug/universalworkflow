from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from apps.orchestrator_api.routers import (
    build_catalog_router,
    build_governance_router,
    build_interaction_router,
    build_runs_router,
    build_scheduler_router,
    build_ui_router,
    build_workers_router,
)
from packages.contracts import RuntimeGateway
from packages.core_domain.config import build_effective_config
from packages.core_domain.db import DEFAULT_DB_PATH, migrate
from packages.core_domain.errors import WorkflowError
from packages.core_domain.external_workers import ExternalWorkerGateway
from packages.core_domain.services import OrchestratorService
from packages.runtime_langgraph.chat_runtime import ChatLLMRuntime


def error_body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def create_app(
    db_path: str | Path | None = None,
    runtime_gateway: RuntimeGateway | None = None,
    external_worker_gateway: ExternalWorkerGateway | None = None,
    chat_llm_runtime: ChatLLMRuntime | None = None,
) -> FastAPI:
    effective_config = build_effective_config(explicit_db_path=db_path)
    resolved_db_path = Path(effective_config["db"]["path"]) if db_path is not None or effective_config["db"]["path"] else DEFAULT_DB_PATH
    migrate(resolved_db_path)
    service = OrchestratorService(
        resolved_db_path,
        runtime_gateway=runtime_gateway,
        external_worker_gateway=external_worker_gateway,
        chat_llm_runtime=chat_llm_runtime,
    )
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

    app.include_router(build_catalog_router(service, effective_config))
    app.include_router(build_governance_router(resolved_db_path))
    app.include_router(build_interaction_router(service))
    app.include_router(build_runs_router(service))
    app.include_router(build_workers_router(service))
    app.include_router(build_scheduler_router(service))
    app.include_router(build_ui_router(service, effective_config, resolved_db_path))

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("apps.orchestrator_api.main:app", host="127.0.0.1", port=8000, reload=False)
