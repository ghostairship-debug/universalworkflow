from __future__ import annotations

from urllib.parse import urlencode
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from apps.orchestrator_api.web_ui import (
    render_config as render_config_page,
    render_dashboard as render_dashboard_page,
    render_governance as render_governance_page,
    render_reviews as render_reviews_page,
    render_run_focus as render_run_focus_page,
    render_runs as render_runs_page,
    render_workbench as render_workbench_page,
)
from packages.contracts import RuntimeGateway
from packages.core_domain.config import build_effective_config
from packages.core_domain.db import DEFAULT_DB_PATH, migrate
from packages.core_domain.errors import WorkflowError
from packages.core_domain.external_workers import ExternalWorkerGateway
from packages.core_domain.governance import (
    build_domain_pack_platform_report,
    build_governance_alert_report,
    build_governance_metrics_report,
    build_release_readiness_report,
    build_review_policy_report,
    build_tech_debt_report,
)
from packages.core_domain.services import OrchestratorService


class CreateRunRequest(BaseModel):
    goal: str = Field(min_length=1)
    preset_id: str = Field(min_length=1)


class GoalPlanRequest(BaseModel):
    goal: str = Field(min_length=1)
    preset_id: str | None = None


class LaunchGoalRequest(BaseModel):
    goal: str = Field(min_length=1)
    preset_id: str | None = None
    execute: bool = False


class CreateIntentSessionRequest(BaseModel):
    goal: str = Field(min_length=1)
    preferred_preset_id: str | None = None
    preferred_cluster_template_ids: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    referenced_artifact_paths: list[str] = Field(default_factory=list)
    followup_context: list[str] = Field(default_factory=list)


class ClarificationUpdateRequest(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)
    preferred_preset_id: str | None = None
    preferred_cluster_template_ids: list[str] = Field(default_factory=list)


class IntentPlanDraftRequest(BaseModel):
    preferred_preset_id: str | None = None
    preferred_cluster_template_ids: list[str] = Field(default_factory=list)


class IntentLaunchRequest(BaseModel):
    execute: bool = False
    rationale: str | None = None
    selected_preset_id: str | None = None
    selected_cluster_template_ids: list[str] = Field(default_factory=list)


class FollowupRequestPayload(BaseModel):
    instruction: str = Field(min_length=1)
    intent: str = Field(default="continue", min_length=1)
    blocking: bool = False
    run_id: str | None = None


class TaskKindOverrideRequest(BaseModel):
    task_kind: str | None = Field(default=None)
    adapter_name: str | None = Field(default=None)
    memory_item_ids: list[str] = Field(default_factory=list)
    task_card_ref: str | None = Field(default=None)
    task_card_path: str | None = Field(default=None)
    write_set: list[str] = Field(default_factory=list)
    read_set: list[str] = Field(default_factory=list)
    test_commands: list[str] = Field(default_factory=list)
    max_fix_iterations: int = Field(default=0, ge=0)
    mutation_mode: str | None = Field(default=None)


class BatchResumeRequest(BaseModel):
    run_ids: list[str] = Field(min_length=1)
    max_workers: int | None = Field(default=None, ge=1)


class ReconcileRunRequest(BaseModel):
    apply: bool = False
    action: str | None = None


class MaterializeMemoryItemRequest(BaseModel):
    candidate_id: str = Field(min_length=1)


class WorkerHeartbeatCallbackRequest(BaseModel):
    callback_id: str = Field(min_length=1)
    dispatch_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    runtime_task_id: str = Field(min_length=1)
    lease_id: str = Field(min_length=1)
    worker_pool_id: str = Field(min_length=1)
    execution_target: dict | None = None
    heartbeat_at: str = Field(min_length=1)
    lease_expires_at: str = Field(min_length=1)


class WorkerCompletionCallbackRequest(BaseModel):
    callback_id: str = Field(min_length=1)
    dispatch_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    runtime_task_id: str = Field(min_length=1)
    lease_id: str = Field(min_length=1)
    worker_pool_id: str = Field(min_length=1)
    execution_target: dict
    lease_renewals: list[dict] = Field(default_factory=list)
    execution_result: dict | None = None


class SchedulerProposalRequest(BaseModel):
    control_plane_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    runtime_task_id: str = Field(min_length=1)
    domain_kind: str = Field(default="runtime_task", min_length=1)
    domain_key: str = Field(min_length=1)
    requested_lease_seconds: int = Field(default=300, ge=1)
    requested_epoch: int = Field(default=1, ge=1)


class SchedulerHeartbeatRequest(BaseModel):
    control_plane_id: str = Field(min_length=1)
    status: str = Field(default="active", min_length=1)
    lease_count: int = Field(default=0, ge=0)
    observed_at: str | None = None


class SchedulerReleaseRequest(BaseModel):
    release_reason: str = Field(default="control_plane_release", min_length=1)


def error_body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def create_app(
    db_path: str | Path | None = None,
    runtime_gateway: RuntimeGateway | None = None,
    external_worker_gateway: ExternalWorkerGateway | None = None,
) -> FastAPI:
    effective_config = build_effective_config(explicit_db_path=db_path)
    resolved_db_path = Path(effective_config["db"]["path"]) if db_path is not None or effective_config["db"]["path"] else DEFAULT_DB_PATH
    migrate(resolved_db_path)
    service = OrchestratorService(
        resolved_db_path,
        runtime_gateway=runtime_gateway,
        external_worker_gateway=external_worker_gateway,
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

    @app.post("/domain-packs/{domain_pack_id}/skill-export", status_code=status.HTTP_201_CREATED)
    def export_domain_pack_skill(domain_pack_id: str, output_root: str = "state/skills") -> dict:
        return service.export_domain_pack_skill(domain_pack_id, output_root=output_root)

    @app.get("/capability-routes")
    def list_capability_routes() -> list[dict]:
        return service.list_capability_routes()

    @app.get("/capability-sources")
    def list_capability_sources() -> list[dict]:
        return service.list_capability_sources()

    @app.get("/capability-descriptors")
    def list_capability_descriptors() -> list[dict]:
        return service.list_capability_descriptors()

    @app.get("/capability-health")
    def list_capability_health() -> list[dict]:
        return service.list_capability_health()

    @app.get("/capability-sources/mcp-profiles")
    def list_mcp_server_profiles() -> list[dict]:
        return service.list_mcp_server_profiles()

    @app.get("/worker-pools")
    def list_worker_pools() -> list[dict]:
        return service.list_worker_pool_profiles()

    @app.get("/capability-projections/preview")
    def preview_tool_projection(
        preset_id: str,
        task_kind: str | None = None,
        adapter_name: str | None = None,
    ) -> dict:
        return service.preview_tool_projection(
            preset_id=preset_id,
            task_kind=task_kind,
            adapter_name=adapter_name,
        )

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

    @app.get("/governance/metrics")
    def get_governance_metrics(
        validation_report_path: str | None = None,
        decision_table_path: str | None = None,
        registry_path: str | None = None,
    ) -> dict:
        return build_governance_metrics_report(
            db_path=resolved_db_path,
            validation_report_path=validation_report_path,
            decision_table_path=decision_table_path,
            registry_path=registry_path,
        )

    @app.get("/governance/alerts")
    def get_governance_alerts(
        validation_report_path: str | None = None,
        decision_table_path: str | None = None,
        registry_path: str | None = None,
    ) -> dict:
        return build_governance_alert_report(
            db_path=resolved_db_path,
            validation_report_path=validation_report_path,
            decision_table_path=decision_table_path,
            registry_path=registry_path,
        )

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

    @app.get("/runs")
    def list_runs(
        status: str | None = None,
        preset_id: str | None = None,
        limit: int = Query(default=10, ge=1),
    ) -> list[dict]:
        return service.list_run_operator_rows(limit=limit, status=status, preset_id=preset_id)

    @app.get("/reviews/pending")
    def get_pending_reviews(limit: int = Query(default=20, ge=1)) -> list[dict]:
        return service.list_pending_review_runs(limit=limit)

    @app.post("/runs", status_code=status.HTTP_201_CREATED)
    def create_run(payload: CreateRunRequest) -> dict:
        run = service.create_run(goal=payload.goal, preset_id=payload.preset_id)
        return run.model_dump(mode="json")

    @app.post("/runs/plan-graph")
    def preview_goal_plan_graph(payload: GoalPlanRequest) -> dict:
        return service.preview_orchestration_plan_graph(goal=payload.goal, preset_id=payload.preset_id)

    @app.post("/runs/policy-preview")
    def preview_goal_policy(payload: GoalPlanRequest) -> dict:
        return service.preview_capability_policy(goal=payload.goal, preset_id=payload.preset_id)

    @app.post("/runs/goal-packet")
    def preview_goal_packet(payload: GoalPlanRequest) -> dict:
        return service.preview_goal_packet(goal=payload.goal, preset_id=payload.preset_id)

    @app.post("/runs/launch")
    def launch_goal(payload: LaunchGoalRequest) -> dict:
        return service.launch_goal(goal=payload.goal, preset_id=payload.preset_id, execute=payload.execute)

    @app.get("/interaction/agent-profiles")
    def list_agent_profiles() -> list[dict]:
        return [profile.model_dump(mode="json") for profile in service.list_agent_profiles()]

    @app.get("/interaction/agent-profiles/registry")
    def get_agent_profile_registry() -> dict:
        return service.get_agent_profile_registry().model_dump(mode="json")

    @app.get("/interaction/clusters/templates")
    def list_cluster_templates() -> list[dict]:
        return [template.model_dump(mode="json") for template in service.list_cluster_templates()]

    @app.get("/interaction/clusters/templates/{template_id}")
    def get_cluster_template(template_id: str) -> dict:
        return service.get_cluster_template(template_id).model_dump(mode="json")

    @app.post("/interaction/sessions", status_code=status.HTTP_201_CREATED)
    def create_intent_session(payload: CreateIntentSessionRequest) -> dict:
        return service.create_intent_session(
            goal=payload.goal,
            preferred_preset_id=payload.preferred_preset_id,
            preferred_cluster_template_ids=payload.preferred_cluster_template_ids,
            constraints=payload.constraints,
            assumptions=payload.assumptions,
            referenced_artifact_paths=payload.referenced_artifact_paths,
            followup_context=payload.followup_context,
        )

    @app.get("/interaction/sessions/{session_id}")
    def get_intent_session(session_id: str) -> dict:
        return service.get_intent_session_payload(session_id)

    @app.post("/interaction/sessions/{session_id}/clarifications")
    def update_intent_session_clarifications(session_id: str, payload: ClarificationUpdateRequest) -> dict:
        return service.continue_intent_session(
            session_id,
            answers=payload.answers,
            preferred_preset_id=payload.preferred_preset_id,
            preferred_cluster_template_ids=payload.preferred_cluster_template_ids,
        )

    @app.post("/interaction/sessions/{session_id}/plan-draft")
    def create_intent_plan_draft(session_id: str, payload: IntentPlanDraftRequest | None = None) -> dict:
        return service.create_intent_plan_draft(
            session_id,
            preferred_preset_id=payload.preferred_preset_id if payload is not None else None,
            preferred_cluster_template_ids=payload.preferred_cluster_template_ids if payload is not None else None,
        )

    @app.post("/interaction/sessions/{session_id}/launch")
    def launch_intent_session(session_id: str, payload: IntentLaunchRequest | None = None) -> dict:
        return service.launch_intent_session(
            session_id,
            execute=payload.execute if payload is not None else False,
            rationale=payload.rationale if payload is not None else None,
            selected_preset_id=payload.selected_preset_id if payload is not None else None,
            selected_cluster_template_ids=payload.selected_cluster_template_ids if payload is not None else None,
        )

    @app.post("/interaction/sessions/{session_id}/followups", status_code=status.HTTP_201_CREATED)
    def create_interaction_followup(session_id: str, payload: FollowupRequestPayload) -> dict:
        return service.create_followup_request(
            session_id,
            instruction=payload.instruction,
            intent=payload.intent,
            blocking=payload.blocking,
            run_id=payload.run_id,
        )

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
            task_card_ref=payload.task_card_ref if payload is not None else None,
            task_card_path=payload.task_card_path if payload is not None else None,
            write_set=payload.write_set if payload is not None and payload.write_set else None,
            read_set=payload.read_set if payload is not None and payload.read_set else None,
            test_commands=payload.test_commands if payload is not None and payload.test_commands else None,
            max_fix_iterations=payload.max_fix_iterations if payload is not None else 0,
            mutation_mode=payload.mutation_mode if payload is not None else None,
        )
        return {
            "run": bundle.run.model_dump(mode="json"),
            "runtime_task_id": bundle.task_packet.runtime_task_id,
            "handoff_id": bundle.handoff.handoff_id,
            "state_ref_id": bundle.state_ref.state_ref_id,
            "domain_pack_id": bundle.domain_pack.domain_pack_id if bundle.domain_pack is not None else None,
            "capability_adapter": bundle.capability_route.adapter_name if bundle.capability_route is not None else None,
            "execution_lane": str(bundle.execution_lane),
            "mutation_contract": bundle.task_packet.mutation_contract.model_dump(mode="json") if bundle.task_packet.mutation_contract is not None else None,
            "tool_projection_manifest": (
                bundle.tool_projection_manifest.model_dump(mode="json")
                if bundle.tool_projection_manifest is not None
                else None
            ),
            "mcp_server_profiles": [profile.model_dump(mode="json") for profile in bundle.mcp_server_profiles],
            "memory_preview": bundle.memory_preview.model_dump(mode="json") if bundle.memory_preview is not None else None,
        }

    @app.post("/runs/{run_id}/recompile")
    def recompile_run(run_id: str, payload: TaskKindOverrideRequest | None = None) -> dict:
        bundle = service.recompile_run(
            run_id,
            task_kind=payload.task_kind if payload is not None else None,
            adapter_name=payload.adapter_name if payload is not None else None,
            memory_item_ids=payload.memory_item_ids if payload is not None and payload.memory_item_ids else None,
            task_card_ref=payload.task_card_ref if payload is not None else None,
            task_card_path=payload.task_card_path if payload is not None else None,
            write_set=payload.write_set if payload is not None and payload.write_set else None,
            read_set=payload.read_set if payload is not None and payload.read_set else None,
            test_commands=payload.test_commands if payload is not None and payload.test_commands else None,
            max_fix_iterations=payload.max_fix_iterations if payload is not None else 0,
            mutation_mode=payload.mutation_mode if payload is not None else None,
        )
        return {
            "run": bundle.run.model_dump(mode="json"),
            "runtime_task_id": bundle.task_packet.runtime_task_id,
            "handoff_id": bundle.handoff.handoff_id,
            "state_ref_id": bundle.state_ref.state_ref_id,
            "domain_pack_id": bundle.domain_pack.domain_pack_id if bundle.domain_pack is not None else None,
            "capability_adapter": bundle.capability_route.adapter_name if bundle.capability_route is not None else None,
            "execution_lane": str(bundle.execution_lane),
            "mutation_contract": bundle.task_packet.mutation_contract.model_dump(mode="json") if bundle.task_packet.mutation_contract is not None else None,
            "tool_projection_manifest": (
                bundle.tool_projection_manifest.model_dump(mode="json")
                if bundle.tool_projection_manifest is not None
                else None
            ),
            "mcp_server_profiles": [profile.model_dump(mode="json") for profile in bundle.mcp_server_profiles],
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

    @app.post("/runs/batch-resume")
    def batch_resume_runs(payload: BatchResumeRequest) -> dict:
        return service.resume_runs_parallel(payload.run_ids, max_workers=payload.max_workers)

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

    @app.get("/runs/{run_id}/replay-packet")
    def get_run_replay_packet(run_id: str) -> dict:
        return service.get_run_replay_packet(run_id)

    @app.get("/runs/{run_id}/orchestration")
    def get_run_orchestration(run_id: str) -> dict:
        return service.get_run_orchestration(run_id)

    @app.get("/runs/{run_id}/plan-graph")
    def get_run_plan_graph(run_id: str) -> dict:
        return service.get_run_orchestration_plan_graph(run_id)

    @app.get("/runs/{run_id}/policy-preview")
    def get_run_policy_preview(run_id: str) -> dict:
        return service.get_run_capability_policy_preview(run_id)

    @app.get("/runs/{run_id}/operator-packet")
    def get_run_operator_packet(run_id: str) -> dict:
        return service.get_run_operator_packet(run_id)

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

    @app.get("/runs/{run_id}/mutation-report")
    def get_run_mutation_report(run_id: str) -> dict:
        return service.get_run_mutation_report(run_id)

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

    @app.get("/runs/{run_id}/operator-view")
    def get_run_operator_view(run_id: str) -> dict:
        return service.get_operator_view(run_id)

    @app.get("/config/effective")
    def get_effective_config() -> dict:
        return effective_config

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

    @app.post("/runs/{run_id}/cancel")
    def cancel_run(run_id: str) -> dict:
        return service.cancel_run(run_id).model_dump(mode="json")

    @app.post("/worker-callbacks/heartbeat")
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

    @app.post("/worker-callbacks/completion")
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

    @app.post("/scheduler/proposals", status_code=status.HTTP_201_CREATED)
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

    @app.post("/scheduler/heartbeats", status_code=status.HTTP_201_CREATED)
    def record_scheduler_heartbeat(payload: SchedulerHeartbeatRequest) -> dict:
        return service.record_scheduler_peer_heartbeat(
            control_plane_id=payload.control_plane_id,
            status=payload.status,
            lease_count=payload.lease_count,
            observed_at=payload.observed_at,
        )

    @app.post("/scheduler/releases/{lease_id}")
    def release_scheduler_lease(lease_id: str, payload: SchedulerReleaseRequest | None = None) -> dict:
        return service.release_scheduler_lease(
            lease_id,
            release_reason=payload.release_reason if payload is not None else "control_plane_release",
        )

    @app.get("/scheduler/leases/{lease_id}")
    def get_scheduler_lease(lease_id: str) -> dict:
        return service.get_scheduler_lease(lease_id)

    @app.get("/scheduler/cluster")
    def get_scheduler_cluster() -> dict:
        return service.scheduler_authority_cluster.cluster_snapshot()

    @app.get("/runs/{run_id}/handoffs")
    def get_run_handoffs(run_id: str) -> list[dict]:
        return [handoff.model_dump(mode="json") for handoff in service.list_handoffs(run_id)]

    @app.get("/tasks/{runtime_task_id}/evidence")
    def get_task_evidence(runtime_task_id: str) -> dict:
        return service.get_task_evidence(runtime_task_id).model_dump(mode="json")

    def _governance_reports() -> dict[str, dict]:
        return {
            "tech_debt": build_tech_debt_report(),
            "review_policy": build_review_policy_report(db_path=resolved_db_path),
            "metrics": build_governance_metrics_report(db_path=resolved_db_path),
            "alerts": build_governance_alert_report(db_path=resolved_db_path),
            "release_readiness": build_release_readiness_report(db_path=resolved_db_path),
            "domain_packs": build_domain_pack_platform_report(),
        }

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
        import os

        expected = os.getenv(str(shared_secret_env))
        if not expected or secret != expected:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="shared secret validation failed")

    def _redirect_with_notice(path: str, notice: str) -> RedirectResponse:
        separator = "&" if "?" in path else "?"
        return RedirectResponse(url=f"{path}{separator}{urlencode({'notice': notice})}", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/ui", response_class=HTMLResponse)
    def web_dashboard(notice: str | None = None) -> HTMLResponse:
        snapshot = service.get_dashboard_snapshot(limit=8)
        html = render_dashboard_page(
            snapshot=snapshot,
            pending_reviews=service.list_pending_review_runs(limit=8),
            governance=_governance_reports(),
            effective_config=effective_config,
            cluster_overview=snapshot.get("cluster_overview"),
            notice=notice,
        )
        return HTMLResponse(html)

    @app.get("/ui/runs", response_class=HTMLResponse)
    def web_runs(
        status: str | None = None,
        preset_id: str | None = None,
        limit: int = Query(default=20, ge=1),
        notice: str | None = None,
    ) -> HTMLResponse:
        html = render_runs_page(
            rows=service.list_run_operator_rows(limit=limit, status=status, preset_id=preset_id),
            status_filter=status,
            preset_filter=preset_id,
            limit=limit,
            notice=notice,
        )
        return HTMLResponse(html)

    @app.get("/ui/runs/{run_id}", response_class=HTMLResponse)
    def web_run_focus(run_id: str, notice: str | None = None) -> HTMLResponse:
        return HTMLResponse(render_run_focus_page(operator_view=service.get_operator_view(run_id), notice=notice))

    @app.get("/ui/reviews", response_class=HTMLResponse)
    def web_reviews(notice: str | None = None) -> HTMLResponse:
        return HTMLResponse(render_reviews_page(rows=service.list_pending_review_runs(limit=20), notice=notice))

    @app.get("/ui/governance", response_class=HTMLResponse)
    def web_governance(notice: str | None = None) -> HTMLResponse:
        return HTMLResponse(
            render_governance_page(
                reports=_governance_reports(),
                cluster_overview=service.scheduler_authority_cluster.cluster_snapshot(),
                notice=notice,
            )
        )

    @app.get("/ui/workbench", response_class=HTMLResponse)
    def web_workbench(session_id: str | None = None, notice: str | None = None) -> HTMLResponse:
        session_payload = service.get_intent_session_payload(session_id) if session_id else None
        return HTMLResponse(
            render_workbench_page(
                session_payload=session_payload,
                presets=[preset.model_dump(mode="json") for preset in service.list_presets()],
                cluster_templates=[template.model_dump(mode="json") for template in service.list_cluster_templates()],
                notice=notice,
            )
        )

    @app.get("/ui/config", response_class=HTMLResponse)
    def web_config(notice: str | None = None) -> HTMLResponse:
        return HTMLResponse(render_config_page(effective_config=effective_config, notice=notice))

    @app.post("/ui/workbench/preview")
    async def web_workbench_preview(request: Request) -> RedirectResponse:
        form = await request.form()
        goal = str(form.get("goal") or "").strip()
        if not goal:
            return _redirect_with_notice("/ui/workbench", "preview skipped: goal is required")
        preset_id = str(form.get("preset_id") or "").strip() or None
        cluster_template_id = str(form.get("cluster_template_id") or "").strip()
        payload = service.create_intent_session(
            goal=goal,
            preferred_preset_id=preset_id,
            preferred_cluster_template_ids=[cluster_template_id] if cluster_template_id else None,
        )
        return _redirect_with_notice(
            f"/ui/workbench?session_id={payload['session']['session_id']}",
            "workbench preview refreshed",
        )

    @app.post("/ui/workbench/{session_id}/clarify")
    async def web_workbench_clarify(session_id: str, request: Request) -> RedirectResponse:
        form = await request.form()
        answers = {
            str(key).removeprefix("answer_"): str(value).strip()
            for key, value in form.multi_items()
            if str(key).startswith("answer_") and str(value).strip()
        }
        preset_id = str(form.get("preset_id") or "").strip() or None
        cluster_template_id = str(form.get("cluster_template_id") or "").strip()
        service.continue_intent_session(
            session_id,
            answers=answers,
            preferred_preset_id=preset_id,
            preferred_cluster_template_ids=[cluster_template_id] if cluster_template_id else None,
        )
        return _redirect_with_notice(f"/ui/workbench?session_id={session_id}", "clarifications updated")

    @app.post("/ui/workbench/{session_id}/launch")
    async def web_workbench_launch(session_id: str, request: Request) -> RedirectResponse:
        form = await request.form()
        execute = str(form.get("execute") or "").lower() in {"1", "true", "on", "yes"}
        payload = service.launch_intent_session(session_id, execute=execute)
        run_id = payload["launch_payload"]["run"]["run_id"]
        return _redirect_with_notice(
            f"/ui/runs/{run_id}",
            f"launch completed: preset={payload['launch_payload']['selected_preset_id']}",
        )

    @app.post("/ui/actions/{run_id}/resume")
    def web_resume_run(run_id: str) -> RedirectResponse:
        bundle = service.resume_run(run_id)
        return _redirect_with_notice(
            f"/ui/runs/{run_id}",
            f"resume completed: status={bundle.run.status} evidence={bundle.evidence.evidence_id}",
        )

    @app.post("/ui/actions/{run_id}/approve")
    def web_approve_run(run_id: str) -> RedirectResponse:
        bundle = service.approve_run_review(run_id)
        return _redirect_with_notice(
            f"/ui/runs/{run_id}",
            f"approve completed: review={bundle.review_verdict.decision} status={bundle.run.status}",
        )

    @app.post("/ui/actions/{run_id}/reject")
    def web_reject_run(run_id: str) -> RedirectResponse:
        bundle = service.reject_run_review(run_id)
        return _redirect_with_notice(
            f"/ui/runs/{run_id}",
            f"reject completed: review={bundle.review_verdict.decision} status={bundle.run.status}",
        )

    @app.post("/ui/actions/{run_id}/reconcile")
    def web_reconcile_run(run_id: str) -> RedirectResponse:
        result = service.reconcile_run(run_id)
        return _redirect_with_notice(
            f"/ui/runs/{run_id}",
            f"reconcile inspected: passed={result['passed']} problems={result['problem_count']}",
        )

    @app.post("/ui/actions/{run_id}/cancel")
    def web_cancel_run(run_id: str) -> RedirectResponse:
        run = service.cancel_run(run_id)
        return _redirect_with_notice(f"/ui/runs/{run_id}", f"cancel completed: status={run.status}")

    @app.post("/ui/actions/batch-resume")
    async def web_batch_resume_runs(request: Request) -> RedirectResponse:
        form = await request.form()
        run_ids = [str(item) for item in form.getlist("run_id") if str(item).strip()]
        if not run_ids:
            return _redirect_with_notice("/ui/reviews", "batch-resume skipped: no runs selected")
        result = service.resume_runs_parallel(run_ids, max_workers=min(len(run_ids), 4))
        return _redirect_with_notice(
            "/ui/reviews",
            f"batch-resume completed: requested={len(run_ids)} results={len(result['results'])}",
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("apps.orchestrator_api.main:app", host="127.0.0.1", port=8000, reload=False)
