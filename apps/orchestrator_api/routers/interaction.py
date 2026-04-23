from __future__ import annotations

from fastapi import APIRouter, status

from apps.orchestrator_api.request_models import (
    ClarificationUpdateRequest,
    CreateIntentSessionRequest,
    FollowupRequestPayload,
    IntentLaunchRequest,
    IntentPlanDraftRequest,
)
from packages.core_domain.services import OrchestratorService


def build_interaction_router(service: OrchestratorService) -> APIRouter:
    router = APIRouter()

    @router.get("/interaction/agent-profiles")
    def list_agent_profiles() -> list[dict]:
        return [profile.model_dump(mode="json") for profile in service.list_agent_profiles()]

    @router.get("/interaction/agent-profiles/registry")
    def get_agent_profile_registry() -> dict:
        return service.get_agent_profile_registry().model_dump(mode="json")

    @router.get("/interaction/clusters/templates")
    def list_cluster_templates() -> list[dict]:
        return [template.model_dump(mode="json") for template in service.list_cluster_templates()]

    @router.get("/interaction/clusters/templates/{template_id}")
    def get_cluster_template(template_id: str) -> dict:
        return service.get_cluster_template(template_id).model_dump(mode="json")

    @router.post("/interaction/sessions", status_code=status.HTTP_201_CREATED)
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

    @router.get("/interaction/sessions/{session_id}")
    def get_intent_session(session_id: str) -> dict:
        return service.get_intent_session_payload(session_id)

    @router.post("/interaction/sessions/{session_id}/clarifications")
    def update_intent_session_clarifications(session_id: str, payload: ClarificationUpdateRequest) -> dict:
        return service.continue_intent_session(
            session_id,
            answers=payload.answers,
            preferred_preset_id=payload.preferred_preset_id,
            preferred_cluster_template_ids=payload.preferred_cluster_template_ids,
        )

    @router.post("/interaction/sessions/{session_id}/plan-draft")
    def create_intent_plan_draft(session_id: str, payload: IntentPlanDraftRequest | None = None) -> dict:
        return service.create_intent_plan_draft(
            session_id,
            preferred_preset_id=payload.preferred_preset_id if payload is not None else None,
            preferred_cluster_template_ids=payload.preferred_cluster_template_ids if payload is not None else None,
        )

    @router.post("/interaction/sessions/{session_id}/launch")
    def launch_intent_session(session_id: str, payload: IntentLaunchRequest | None = None) -> dict:
        return service.launch_intent_session(
            session_id,
            execute=payload.execute if payload is not None else False,
            rationale=payload.rationale if payload is not None else None,
            selected_preset_id=payload.selected_preset_id if payload is not None else None,
            selected_cluster_template_ids=payload.selected_cluster_template_ids if payload is not None else None,
        )

    @router.post("/interaction/sessions/{session_id}/followups", status_code=status.HTTP_201_CREATED)
    def create_interaction_followup(session_id: str, payload: FollowupRequestPayload) -> dict:
        return service.create_followup_request(
            session_id,
            instruction=payload.instruction,
            intent=payload.intent,
            blocking=payload.blocking,
            run_id=payload.run_id,
        )

    return router
