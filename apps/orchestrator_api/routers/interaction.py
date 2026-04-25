from __future__ import annotations

import json

from fastapi import APIRouter, Header, status
from fastapi.responses import StreamingResponse

from apps.orchestrator_api.request_models import (
    ChatActionConfirmRequest,
    ChatMessageRequest,
    ClarificationUpdateRequest,
    CreateIntentSessionRequest,
    FollowupRequestPayload,
    IntentLaunchRequest,
    IntentPlanDraftRequest,
)
from packages.core_domain.services import OrchestratorService


def build_interaction_router(service: OrchestratorService) -> APIRouter:
    router = APIRouter()

    @router.get("/interaction/sessions")
    def list_intent_sessions(limit: int = 10, status: str | None = None) -> list[dict]:
        return [session.model_dump(mode="json") for session in service.list_intent_sessions(limit=limit, status=status)]

    @router.get("/interaction/generated-profiles")
    def list_generated_agent_profiles(
        session_id: str | None = None,
        run_id: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        return [
            item.model_dump(mode="json")
            for item in service.list_generated_agent_profiles(session_id=session_id, run_id=run_id, limit=limit)
        ]

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

    @router.post("/interaction/chat/messages", status_code=status.HTTP_201_CREATED)
    def post_chat_message(payload: ChatMessageRequest) -> dict:
        return service.post_chat_message(
            session_id=payload.session_id,
            run_id=payload.run_id,
            content=payload.content,
            mode=payload.mode,
            client_message_id=payload.client_message_id,
        )

    @router.post("/interaction/chat/actions/{action_id}/confirm")
    def confirm_chat_action(
        action_id: str,
        payload: ChatActionConfirmRequest | None = None,
    ) -> dict:
        return service.confirm_chat_action(
            action_id,
            rationale=payload.rationale if payload is not None else None,
        )

    @router.get("/interaction/sessions/{session_id}")
    def get_intent_session(session_id: str) -> dict:
        return service.get_intent_session_payload(session_id)

    @router.get("/interaction/sessions/{session_id}/stream")
    def stream_intent_session(
        session_id: str,
        after_message_id: str | None = None,
        after_event_id: str | None = None,
    ) -> StreamingResponse:
        def _event_stream():
            for item in service.build_interaction_stream_events(
                session_id,
                after_message_id=after_message_id,
                after_event_id=after_event_id,
            ):
                event_id = item.get("id")
                if event_id is not None:
                    yield f"id: {event_id}\n"
                yield f"event: {item['event']}\n"
                yield f"data: {json.dumps(item['data'], ensure_ascii=False)}\n\n"

        return StreamingResponse(_event_stream(), media_type="text/event-stream")

    @router.get("/interaction/sessions/{session_id}/generated-profiles")
    def list_session_generated_profiles(session_id: str, limit: int = 20) -> list[dict]:
        return [
            item.model_dump(mode="json")
            for item in service.list_generated_agent_profiles(session_id=session_id, limit=limit)
        ]

    @router.post("/interaction/sessions/{session_id}/generated-profiles", status_code=status.HTTP_201_CREATED)
    def generate_session_profiles(session_id: str) -> dict:
        return service.generate_session_profiles(session_id)

    @router.get("/interaction/sessions/{session_id}/followups")
    def list_intent_session_followups(session_id: str, limit: int = 20) -> list[dict]:
        return [item.model_dump(mode="json") for item in service.list_followup_requests(session_id, limit=limit)]

    @router.get("/interaction/sessions/{session_id}/watchdogs")
    def list_intent_session_watchdogs(session_id: str, limit: int = 20) -> list[dict]:
        return [
            item.model_dump(mode="json")
            for item in service.list_automation_watchdogs(session_id=session_id, limit=limit)
        ]

    @router.get("/interaction/watchdogs/evaluate")
    def evaluate_watchdogs(
        session_id: str | None = None,
        run_id: str | None = None,
        auto_apply: bool = False,
        limit: int = 20,
    ) -> dict:
        return service.evaluate_watchdogs(session_id=session_id, run_id=run_id, auto_apply=auto_apply, limit=limit)

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
    def launch_intent_session(
        session_id: str,
        payload: IntentLaunchRequest | None = None,
        operator_action_receipt: str | None = Header(default=None, alias="X-Operator-Action-Receipt"),
    ) -> dict:
        execute = payload.execute if payload is not None else False
        if execute:
            service.consume_operator_action_receipt(
                receipt_id=operator_action_receipt,
                action_type="launch_execute",
            )
        return service.launch_intent_session(
            session_id,
            execute=execute,
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
