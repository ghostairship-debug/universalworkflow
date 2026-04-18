from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from packages.contracts import RuntimeGateway
from packages.core_domain.db import DEFAULT_DB_PATH, migrate
from packages.core_domain.errors import WorkflowError
from packages.core_domain.governance import (
    build_domain_pack_platform_report,
    build_release_readiness_report,
    build_review_policy_report,
    build_tech_debt_report,
)
from packages.core_domain.services import OrchestratorService


class CreateRunRequest(BaseModel):
    goal: str = Field(min_length=1)
    preset_id: str = Field(min_length=1)


class TaskKindOverrideRequest(BaseModel):
    task_kind: str | None = Field(default=None)
    adapter_name: str | None = Field(default=None)
    memory_item_ids: list[str] = Field(default_factory=list)


class ReconcileRunRequest(BaseModel):
    apply: bool = False
    action: str | None = None


class MaterializeMemoryItemRequest(BaseModel):
    candidate_id: str = Field(min_length=1)


def error_body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def create_app(
    db_path: str | Path | None = None,
    runtime_gateway: RuntimeGateway | None = None,
) -> FastAPI:
    resolved_db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    migrate(resolved_db_path)
    service = OrchestratorService(resolved_db_path, runtime_gateway=runtime_gateway)
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

    @app.get("/domain-packs")
    def list_domain_packs() -> list[dict]:
        return [domain_pack.model_dump(mode="json") for domain_pack in service.list_domain_packs()]

    @app.get("/domain-packs/resolve")
    def resolve_domain_pack(preset_id: str, task_kind: str | None = None, adapter_name: str | None = None) -> dict:
        return service.preview_domain_pack_resolution(
            preset_id=preset_id,
            task_kind=task_kind,
            adapter_name=adapter_name,
        )

    @app.get("/domain-packs/validate")
    def validate_domain_packs() -> dict:
        return service.validate_domain_pack_catalog()

    @app.get("/capability-routes")
    def list_capability_routes() -> list[dict]:
        return service.list_capability_routes()

    @app.get("/simulation/policies")
    def list_simulation_policies() -> list[dict]:
        return [policy.model_dump(mode="json") for policy in service.list_simulation_policies()]

    @app.get("/memory/namespaces")
    def list_memory_namespaces() -> list[dict]:
        return [namespace.model_dump(mode="json") for namespace in service.list_memory_namespaces()]

    @app.get("/memory/items")
    def list_memory_items(run_id: str | None = None, namespace_id: str | None = None) -> list[dict]:
        return [
            item.model_dump(mode="json")
            for item in service.list_memory_items(run_id=run_id, namespace_id=namespace_id)
        ]

    @app.get("/memory/retrieval-preview")
    def preview_memory_retrieval(
        preset_id: str | None = None,
        run_id: str | None = None,
        namespace_id: str | None = None,
        memory_item_id: list[str] = Query(default_factory=list),
        limit: int = 5,
    ) -> dict:
        return service.preview_memory_retrieval(
            preset_id=preset_id,
            run_id=run_id,
            namespace_id=namespace_id,
            memory_item_ids=memory_item_id or None,
            limit=limit,
        ).model_dump(mode="json")

    @app.get("/governance/tech-debt")
    def get_governance_tech_debt() -> dict:
        return build_tech_debt_report()

    @app.get("/governance/review-policy")
    def get_governance_review_policy() -> dict:
        return build_review_policy_report(db_path=resolved_db_path)

    @app.get("/governance/release-readiness")
    def get_governance_release_readiness(
        validation_report_path: str | None = None,
        decision_table_path: str | None = None,
        registry_path: str | None = None,
    ) -> dict:
        return build_release_readiness_report(
            db_path=resolved_db_path,
            validation_report_path=validation_report_path,
            decision_table_path=decision_table_path,
            registry_path=registry_path,
        )

    @app.get("/governance/domain-packs")
    def get_governance_domain_packs() -> dict:
        return build_domain_pack_platform_report()

    @app.post("/runs", status_code=status.HTTP_201_CREATED)
    def create_run(payload: CreateRunRequest) -> dict:
        run = service.create_run(goal=payload.goal, preset_id=payload.preset_id)
        return run.model_dump(mode="json")

    @app.get("/runs/{run_id}")
    def get_run(run_id: str) -> dict:
        return service.get_run(run_id).model_dump(mode="json")

    @app.post("/runs/{run_id}/compile")
    def compile_run(run_id: str, payload: TaskKindOverrideRequest | None = None) -> dict:
        bundle = service.compile_run(
            run_id,
            task_kind=payload.task_kind if payload is not None else None,
            adapter_name=payload.adapter_name if payload is not None else None,
            memory_item_ids=payload.memory_item_ids if payload is not None and payload.memory_item_ids else None,
        )
        return {
            "run": bundle.run.model_dump(mode="json"),
            "runtime_task_id": bundle.task_packet.runtime_task_id,
            "handoff_id": bundle.handoff.handoff_id,
            "state_ref_id": bundle.state_ref.state_ref_id,
            "domain_pack_id": bundle.domain_pack.domain_pack_id if bundle.domain_pack is not None else None,
            "capability_adapter": bundle.capability_route.adapter_name if bundle.capability_route is not None else None,
            "memory_preview": bundle.memory_preview.model_dump(mode="json") if bundle.memory_preview is not None else None,
        }

    @app.post("/runs/{run_id}/recompile")
    def recompile_run(run_id: str, payload: TaskKindOverrideRequest | None = None) -> dict:
        bundle = service.recompile_run(
            run_id,
            task_kind=payload.task_kind if payload is not None else None,
            adapter_name=payload.adapter_name if payload is not None else None,
            memory_item_ids=payload.memory_item_ids if payload is not None and payload.memory_item_ids else None,
        )
        return {
            "run": bundle.run.model_dump(mode="json"),
            "runtime_task_id": bundle.task_packet.runtime_task_id,
            "handoff_id": bundle.handoff.handoff_id,
            "state_ref_id": bundle.state_ref.state_ref_id,
            "domain_pack_id": bundle.domain_pack.domain_pack_id if bundle.domain_pack is not None else None,
            "capability_adapter": bundle.capability_route.adapter_name if bundle.capability_route is not None else None,
            "memory_preview": bundle.memory_preview.model_dump(mode="json") if bundle.memory_preview is not None else None,
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

    @app.get("/runs/{run_id}/summary")
    def get_run_summary(run_id: str) -> dict:
        return service.get_run_summary(run_id)

    @app.get("/runs/{run_id}/simulation")
    def get_run_simulation(run_id: str) -> dict:
        return service.get_run_simulation(run_id).model_dump(mode="json")

    @app.post("/runs/{run_id}/simulation-records", status_code=status.HTTP_201_CREATED)
    def record_run_simulation(run_id: str) -> dict:
        return service.record_run_simulation(run_id).model_dump(mode="json")

    @app.get("/runs/{run_id}/simulation-records")
    def list_run_simulation_records(run_id: str) -> list[dict]:
        return [record.model_dump(mode="json") for record in service.list_simulation_records(run_id)]

    @app.get("/runs/{run_id}/event-inspection")
    def get_run_event_inspection(run_id: str) -> dict:
        return service.get_event_inspection(run_id)

    @app.get("/runs/{run_id}/audit-report")
    def get_run_audit_report(run_id: str) -> dict:
        return service.get_run_audit_report(run_id)

    @app.get("/runs/{run_id}/memory-candidates")
    def get_run_memory_candidates(run_id: str) -> list[dict]:
        return [candidate.model_dump(mode="json") for candidate in service.get_run_memory_candidates(run_id)]

    @app.post("/runs/{run_id}/memory-items", status_code=status.HTTP_201_CREATED)
    def materialize_run_memory_item(run_id: str, payload: MaterializeMemoryItemRequest) -> dict:
        return service.materialize_run_memory_candidate(run_id, payload.candidate_id).model_dump(mode="json")

    @app.get("/runs/{run_id}/memory-items")
    def get_run_memory_items(run_id: str) -> list[dict]:
        return [item.model_dump(mode="json") for item in service.list_memory_items(run_id=run_id)]

    @app.get("/runs/{run_id}/inspection")
    def inspect_run_state(run_id: str) -> dict:
        return service.inspect_run_state(run_id)

    @app.get("/runs/{run_id}/claims")
    def get_run_claims(run_id: str) -> list[dict]:
        return [claim.model_dump(mode="json") for claim in service.list_claims(run_id)]

    @app.get("/runs/{run_id}/leases")
    def get_run_worker_leases(run_id: str) -> list[dict]:
        return [lease.model_dump(mode="json") for lease in service.list_worker_leases(run_id)]

    @app.get("/runs/{run_id}/attempts")
    def get_run_runtime_attempts(run_id: str) -> list[dict]:
        return [attempt.model_dump(mode="json") for attempt in service.list_runtime_attempts(run_id)]

    @app.get("/runs/{run_id}/snapshots")
    def get_run_snapshots(run_id: str) -> list[dict]:
        return [snapshot.model_dump(mode="json") for snapshot in service.list_snapshots(run_id)]

    @app.get("/runs/{run_id}/budget")
    def get_run_budget(run_id: str) -> dict:
        detail = service.get_status_detail(run_id)
        return {
            "run": detail["run"],
            "budget_ledger": detail["budget_ledger"],
            "budget_projection": detail["budget_projection"],
        }

    @app.post("/runs/{run_id}/reconcile")
    def reconcile_run(run_id: str, payload: ReconcileRunRequest | None = None) -> dict:
        if payload is not None and payload.apply:
            return service.apply_run_repair(run_id, action=payload.action)
        return service.reconcile_run(run_id)

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
