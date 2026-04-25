from __future__ import annotations

import os
from typing import Any

from packages.contracts import (
    AgentRoleType,
    AutomationWatchdog,
    ChatMessage,
    ChatMessageRole,
    ChatMessageStatus,
    ChatStreamEvent,
    ChatStreamEventType,
    ChatMessageType,
    ClarificationPrompt,
    ClarificationState,
    ClusterExecutionPlan,
    ClusterHandoffPacket,
    ClusterOutputPacket,
    ClusterRouteDecision,
    ExecutionClusterTemplate,
    FollowupRequest,
    GeneratedAgentProfile,
    GeneratedProfileSource,
    IntentPacket,
    IntentSession,
    IntentSessionStatus,
    LaunchDecision,
    OrchestrationBarrier,
    OrchestrationPlan,
    OrchestrationStep,
    PlanDraft,
    PlanDraftStatus,
    RoleAssignment,
    RunStatus,
    TerminationRule,
)
from packages.core_domain.cluster_router import ClusterRouter
from packages.core_domain.errors import EntityNotFoundError, WorkflowError
from packages.core_domain.interaction_catalog import (
    build_default_agent_profile_registry,
    default_preset_id_for_cluster_template,
    fallback_adapter_for_cluster_member,
    list_default_cluster_templates,
    member_preset_id,
    preferred_adapter_for_cluster_member,
    sequence_no_for_cluster_member,
)
from packages.runtime_langgraph.chat_runtime import HIGH_RISK_CHAT_ACTIONS, ChatActionDecision




class InteractionSessionServiceMixin:
    def get_agent_profile_registry(self):
        registry = build_default_agent_profile_registry()
        registry.generated_profiles = self.generated_agent_profile_repo.list(limit=50)
        return registry

    def list_agent_profiles(self):
        return self.get_agent_profile_registry().profiles

    def list_intent_sessions(self, *, limit: int = 10, status: str | None = None) -> list[IntentSession]:
        return self.intent_session_repo.list(limit=limit, status=status)

    def list_followup_requests(self, session_id: str, *, limit: int = 20) -> list[FollowupRequest]:
        if self.intent_session_repo.get(session_id) is None:
            raise EntityNotFoundError("intent_session", session_id)
        return self.followup_request_repo.list_for_session(session_id, limit=limit)


    def list_generated_agent_profiles(
        self,
        *,
        session_id: str | None = None,
        run_id: str | None = None,
        limit: int = 20,
    ) -> list[GeneratedAgentProfile]:
        return self.generated_agent_profile_repo.list(session_id=session_id, run_id=run_id, limit=limit)

    def list_automation_watchdogs(
        self,
        *,
        session_id: str | None = None,
        run_id: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[AutomationWatchdog]:
        return self.automation_watchdog_repo.list(
            session_id=session_id,
            run_id=run_id,
            status=status,
            limit=limit,
        )


    def _plan_draft_for_session(self, session: IntentSession) -> tuple[PlanDraft | None, dict[str, Any] | None]:
        if session.clarification_state.blocking:
            return None, None
        selected_cluster_template_ids = self._selected_cluster_template_ids(
            goal=session.intent_packet.goal,
            preset_id=session.intent_packet.preferred_preset_id,
            preferred_cluster_template_ids=session.intent_packet.preferred_cluster_template_ids,
        )
        selected_preset_id = session.intent_packet.preferred_preset_id
        if selected_preset_id is None and selected_cluster_template_ids:
            selected_preset_id = default_preset_id_for_cluster_template(selected_cluster_template_ids[0])
        goal_packet = self.preview_goal_packet(
            goal=session.intent_packet.goal,
            preset_id=selected_preset_id,
            preferred_cluster_template_ids=selected_cluster_template_ids,
        )
        selected_cluster_template_ids = [
            item["template_id"]
            for item in goal_packet.get("selected_clusters", [])
            if isinstance(item, dict) and item.get("template_id")
        ]
        draft = PlanDraft(
            draft_id=f"plan_draft_{session.session_id}",
            session_id=session.session_id,
            status=PlanDraftStatus.ready,
            summary=(
                f"Prepare `{goal_packet['selected_preset_id']}`"
                + (
                    f" with {', '.join(selected_cluster_template_ids)}"
                    if selected_cluster_template_ids
                    else " on the single-path preset route"
                )
            ),
            selected_preset_id=goal_packet["selected_preset_id"],
            selected_cluster_template_ids=selected_cluster_template_ids,
            plan_graph=goal_packet["plan_graph"],
            policy_preview=goal_packet["capability_policy_preview"],
            capability_preview=goal_packet,
            notes=[
                f"matched_capability_descriptors={len(goal_packet['matched_capability_descriptors'])}",
                f"selected_clusters={len(selected_cluster_template_ids)}",
            ],
        )
        return draft, goal_packet

    def _persist_session(self, session: IntentSession) -> IntentSession:
        self.intent_session_repo.upsert(session)
        return session

    def _base_profile_map(self) -> dict[str, Any]:
        return {
            profile.profile_id: profile
            for profile in build_default_agent_profile_registry().profiles
        }

    def _ensure_watchdog(
        self,
        *,
        session_id: str,
        run_id: str | None,
        trigger: str,
        objective: str,
        auto_action_enabled: bool = False,
        notes: list[str] | None = None,
    ) -> AutomationWatchdog:
        existing = self.automation_watchdog_repo.find_active(
            session_id=session_id,
            run_id=run_id,
            trigger=trigger,
        )
        if existing is not None:
            return existing
        watchdog = AutomationWatchdog(
            session_id=session_id,
            run_id=run_id,
            trigger=trigger,
            objective=objective,
            auto_action_enabled=auto_action_enabled,
            notes=list(notes or []),
        )
        self.automation_watchdog_repo.upsert(watchdog)
        return watchdog

    def generate_session_profiles(self, session_id: str) -> dict[str, Any]:
        session = self.intent_session_repo.get(session_id)
        if session is None:
            raise EntityNotFoundError("intent_session", session_id)
        existing_profiles = self.generated_agent_profile_repo.list(session_id=session_id, limit=50)
        if existing_profiles:
            return self.get_intent_session_payload(session_id)

        plan_draft, goal_packet = self._plan_draft_for_session(session)
        selected_template_ids = (
            list(plan_draft.selected_cluster_template_ids)
            if plan_draft is not None
            else self._selected_cluster_template_ids(
                goal=session.intent_packet.goal,
                preset_id=session.intent_packet.preferred_preset_id,
                preferred_cluster_template_ids=session.intent_packet.preferred_cluster_template_ids,
            )
        )
        selected_clusters = self._cluster_templates_for_ids(selected_template_ids)
        profile_map = self._base_profile_map()
        session_suffix = session.session_id.split("_")[-1][:6]
        repo_scope_paths = (
            list(session.intent_packet.referenced_artifact_paths)
            or ["."]
        )
        followup_context = list(session.intent_packet.followup_context)
        constraint_lines = list(session.intent_packet.constraints)

        if not selected_clusters:
            fallback_profile_ids = ["planner_architect", "operator_launch_guard"]
            for profile_id in fallback_profile_ids:
                base_profile = profile_map.get(profile_id)
                if base_profile is None:
                    continue
                generated_profile = GeneratedAgentProfile(
                    base_profile_id=base_profile.profile_id,
                    source_type=GeneratedProfileSource.interaction_generated,
                    public_role=base_profile.public_role,
                    role_label=f"{base_profile.role_label}_{session_suffix}",
                    session_id=session_id,
                    run_id=session.active_run_id,
                    repo_scope_paths=repo_scope_paths,
                    capability_scope_tags=sorted(
                        set(list(base_profile.capability_scope_tags) + ["generated_profile", "interaction_session"])
                    ),
                    system_brief=(
                        f"{base_profile.system_brief or ''} Session goal: {session.intent_packet.goal}. "
                        f"Constraints: {'; '.join(constraint_lines) if constraint_lines else 'none'}."
                    ).strip(),
                    termination_rule=base_profile.termination_rule,
                    evaluation_rubric=base_profile.evaluation_rubric,
                    execution_profile=base_profile.execution_profile,
                )
                self.generated_agent_profile_repo.create(generated_profile)
            return self.get_intent_session_payload(session_id)

        for template in selected_clusters:
            for member in template.member_specs:
                base_profile = profile_map.get(str(member.agent_profile_id or ""))
                base_scope_tags = list(base_profile.capability_scope_tags) if base_profile is not None else []
                system_brief_prefix = base_profile.system_brief if base_profile is not None else ""
                generated_profile = GeneratedAgentProfile(
                    base_profile_id=member.agent_profile_id,
                    source_type=GeneratedProfileSource.cluster_generated,
                    public_role=member.public_role,
                    role_label=f"{member.role_label}_{session_suffix}",
                    session_id=session_id,
                    run_id=session.active_run_id,
                    cluster_template_id=template.template_id,
                    repo_scope_paths=repo_scope_paths,
                    capability_scope_tags=sorted(
                        set(base_scope_tags + ["generated_profile", template.template_id, member.role_label])
                    ),
                    system_brief=(
                        f"{system_brief_prefix or ''} Session goal: {session.intent_packet.goal}. "
                        f"Constraints: {'; '.join(constraint_lines) if constraint_lines else 'none'}. "
                        f"Follow-up context: {'; '.join(followup_context) if followup_context else 'none'}."
                    ).strip(),
                    termination_rule=(
                        base_profile.termination_rule
                        if base_profile is not None
                        else TerminationRule(
                            max_turns=8,
                            completion_signals=["session-scoped generated profile delivered"],
                            escalate_on=["missing session context"],
                        )
                    ),
                    evaluation_rubric=base_profile.evaluation_rubric if base_profile is not None else None,
                    execution_profile=member.execution_profile or (base_profile.execution_profile if base_profile is not None else None),
                )
                if base_profile is not None:
                    generated_profile.termination_rule = base_profile.termination_rule
                self.generated_agent_profile_repo.create(generated_profile)
        return self._interaction_payload(session=session, plan_draft=plan_draft, goal_packet=goal_packet)

    def evaluate_watchdogs(
        self,
        *,
        session_id: str | None = None,
        run_id: str | None = None,
        auto_apply: bool = False,
        limit: int = 20,
    ) -> dict[str, Any]:
        watchdogs = self.list_automation_watchdogs(
            session_id=session_id,
            run_id=run_id,
            status="active",
            limit=limit,
        )
        actions: list[dict[str, Any]] = []
        auto_applied_actions: list[dict[str, Any]] = []
        resolved_watchdog_ids: list[str] = []
        for watchdog in watchdogs:
            session = self.intent_session_repo.get(watchdog.session_id) if watchdog.session_id else None
            target_run_id = watchdog.run_id or (session.active_run_id if session is not None else None)
            run = self.run_repo.get(target_run_id) if target_run_id else None
            pending_followups = (
                self.followup_request_repo.list_for_session(session.session_id, limit=50)
                if session is not None
                else []
            )
            pending_followups = [item for item in pending_followups if item.status == "pending"]
            pending_blocking = [item for item in pending_followups if item.blocking]
            action = {
                "watchdog_id": watchdog.watchdog_id,
                "trigger": watchdog.trigger,
                "objective": watchdog.objective,
                "session_id": watchdog.session_id,
                "run_id": target_run_id,
                "action_type": "none",
                "requires_review": False,
                "risk_level": "low",
                "summary": "watchdog is currently satisfied",
                "auto_applied": False,
            }

            if watchdog.trigger == "review_gate":
                if run is None:
                    action["summary"] = "review-gate watchdog has no target run"
                elif str(run.status) == "awaiting_review":
                    action.update(
                        {
                            "action_type": "review_active_run",
                            "requires_review": True,
                            "risk_level": "high",
                            "summary": f"run `{run.run_id}` is awaiting review",
                        }
                    )
                elif str(run.status) in {"completed", "failed", "cancelled"} and not pending_blocking and session is not None:
                    action.update(
                        {
                            "action_type": "close_session",
                            "requires_review": False,
                            "risk_level": "low",
                            "summary": f"session `{session.session_id}` can close because the active run is terminal",
                        }
                    )
                    if auto_apply and watchdog.auto_action_enabled and str(session.status) != str(IntentSessionStatus.closed):
                        session.status = IntentSessionStatus.closed
                        self._persist_session(session)
                        watchdog.status = "resolved"
                        self.automation_watchdog_repo.upsert(watchdog)
                        action["auto_applied"] = True
                        auto_applied_actions.append(action)
                        resolved_watchdog_ids.append(watchdog.watchdog_id)
                else:
                    action.update(
                        {
                            "action_type": "monitor_run",
                            "summary": f"run `{run.run_id}` is still progressing toward a review checkpoint",
                        }
                    )
            elif watchdog.trigger == "followup_pending":
                if not pending_followups:
                    action["summary"] = "no pending follow-up requests remain"
                    if auto_apply and watchdog.auto_action_enabled:
                        watchdog.status = "resolved"
                        self.automation_watchdog_repo.upsert(watchdog)
                        resolved_watchdog_ids.append(watchdog.watchdog_id)
                elif run is not None and str(run.status) == "awaiting_review":
                    action.update(
                        {
                            "action_type": "review_then_replan",
                            "requires_review": True,
                            "risk_level": "high",
                            "summary": f"pending follow-up for `{session.session_id if session else watchdog.session_id}` is blocked on review of `{run.run_id}`",
                        }
                    )
                elif run is not None and str(run.status) in {"prepared", "running"}:
                    action.update(
                        {
                            "action_type": "wait_for_run_checkpoint",
                            "summary": f"pending follow-up remains queued while `{run.run_id}` is {run.status}",
                        }
                    )
                else:
                    action.update(
                        {
                            "action_type": "replan_session",
                            "requires_review": True,
                            "risk_level": "medium",
                            "summary": f"pending follow-up for `{session.session_id if session else watchdog.session_id}` should open a new plan or operator decision",
                        }
                    )
            actions.append(action)
        return {
            "watchdogs": [watchdog.model_dump(mode="json") for watchdog in watchdogs],
            "actions": actions,
            "auto_applied_actions": auto_applied_actions,
            "resolved_watchdog_ids": resolved_watchdog_ids,
        }

    def _interaction_payload(
        self,
        *,
        session: IntentSession,
        plan_draft: PlanDraft | None,
        goal_packet: dict[str, Any] | None,
        launch_decision: LaunchDecision | None = None,
        launch_payload: dict[str, Any] | None = None,
        followup_request: FollowupRequest | None = None,
    ) -> dict[str, Any]:
        persisted_followups = self.followup_request_repo.list_for_session(session.session_id, limit=20)
        chat_messages = self.chat_message_repo.list_for_session(session.session_id, limit=100)
        active_run_operator_view = self.get_operator_view(session.active_run_id) if session.active_run_id else None
        generated_profiles = self.generated_agent_profile_repo.list(session_id=session.session_id, limit=20)
        automation_watchdogs = self.automation_watchdog_repo.list(session_id=session.session_id, limit=20)
        return {
            "session": session.model_dump(mode="json"),
            "plan_draft": plan_draft.model_dump(mode="json") if plan_draft is not None else None,
            "goal_packet": goal_packet,
            "launch_decision": launch_decision.model_dump(mode="json") if launch_decision is not None else None,
            "launch_payload": launch_payload,
            "followup_request": followup_request.model_dump(mode="json") if followup_request is not None else None,
            "followup_requests": [item.model_dump(mode="json") for item in persisted_followups],
            "chat_messages": [item.model_dump(mode="json") for item in chat_messages],
            "pending_confirmation": self._pending_confirmation_payload(session.session_id),
            "active_run_operator_view": active_run_operator_view,
            "generated_profiles": [item.model_dump(mode="json") for item in generated_profiles],
            "automation_watchdogs": [item.model_dump(mode="json") for item in automation_watchdogs],
            "automation_evaluation": self.evaluate_watchdogs(session_id=session.session_id, auto_apply=False, limit=20),
            "agent_profile_registry": self.get_agent_profile_registry().model_dump(mode="json"),
            "available_cluster_templates": [
                template.model_dump(mode="json") for template in self.list_cluster_templates()
            ],
        }

    def create_intent_session(
        self,
        *,
        goal: str,
        preferred_preset_id: str | None = None,
        preferred_cluster_template_ids: list[str] | None = None,
        constraints: list[str] | None = None,
        assumptions: list[str] | None = None,
        referenced_artifact_paths: list[str] | None = None,
        followup_context: list[str] | None = None,
    ) -> dict[str, Any]:
        intent_packet = IntentPacket(
            goal=goal,
            constraints=list(constraints or []),
            assumptions=list(assumptions or []),
            preferred_preset_id=preferred_preset_id,
            preferred_cluster_template_ids=list(preferred_cluster_template_ids or []),
            referenced_artifact_paths=list(referenced_artifact_paths or []),
            followup_context=list(followup_context or []),
        )
        clarification_state = self._default_clarification_state(intent_packet)
        session = IntentSession(
            status=IntentSessionStatus.clarifying if clarification_state.blocking else IntentSessionStatus.planning,
            intent_packet=intent_packet,
            clarification_state=clarification_state,
        )
        plan_draft, goal_packet = self._plan_draft_for_session(session)
        if plan_draft is not None:
            session.latest_plan_draft_id = plan_draft.draft_id
            session.status = IntentSessionStatus.ready_to_launch
        self._persist_session(session)
        return self._interaction_payload(session=session, plan_draft=plan_draft, goal_packet=goal_packet)

    def get_intent_session_payload(self, session_id: str) -> dict[str, Any]:
        session = self.intent_session_repo.get(session_id)
        if session is None:
            raise EntityNotFoundError("intent_session", session_id)
        plan_draft, goal_packet = self._plan_draft_for_session(session)
        if plan_draft is not None:
            session.latest_plan_draft_id = plan_draft.draft_id
            if session.active_run_id is None:
                session.status = IntentSessionStatus.ready_to_launch
            self._persist_session(session)
        return self._interaction_payload(session=session, plan_draft=plan_draft, goal_packet=goal_packet)

    def continue_intent_session(
        self,
        session_id: str,
        *,
        answers: dict[str, str] | None = None,
        preferred_preset_id: str | None = None,
        preferred_cluster_template_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        session = self.intent_session_repo.get(session_id)
        if session is None:
            raise EntityNotFoundError("intent_session", session_id)
        if preferred_preset_id is not None:
            session.intent_packet.preferred_preset_id = preferred_preset_id
        if preferred_cluster_template_ids is not None and preferred_cluster_template_ids:
            session.intent_packet.preferred_cluster_template_ids = list(preferred_cluster_template_ids)
        updated_prompts: list[ClarificationPrompt] = []
        answer_map = {key: value.strip() for key, value in (answers or {}).items() if value and value.strip()}
        for prompt in session.clarification_state.prompts:
            if prompt.prompt_id in answer_map:
                prompt.answer = answer_map[prompt.prompt_id]
            updated_prompts.append(prompt)
        session.clarification_state = ClarificationState(prompts=updated_prompts) if updated_prompts else ClarificationState()
        plan_draft, goal_packet = self._plan_draft_for_session(session)
        if session.clarification_state.blocking:
            session.status = IntentSessionStatus.clarifying
        elif plan_draft is not None:
            session.latest_plan_draft_id = plan_draft.draft_id
            session.status = IntentSessionStatus.ready_to_launch
        else:
            session.status = IntentSessionStatus.planning
        self._persist_session(session)
        return self._interaction_payload(session=session, plan_draft=plan_draft, goal_packet=goal_packet)

    def create_intent_plan_draft(
        self,
        session_id: str,
        *,
        preferred_preset_id: str | None = None,
        preferred_cluster_template_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        return self.continue_intent_session(
            session_id,
            answers={},
            preferred_preset_id=preferred_preset_id,
            preferred_cluster_template_ids=preferred_cluster_template_ids,
        )

    def launch_intent_session(
        self,
        session_id: str,
        *,
        execute: bool = False,
        rationale: str | None = None,
        selected_preset_id: str | None = None,
        selected_cluster_template_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        session = self.intent_session_repo.get(session_id)
        if session is None:
            raise EntityNotFoundError("intent_session", session_id)
        if session.clarification_state.blocking:
            raise WorkflowError(
                "intent session still requires clarification before launch",
                {"session_id": session_id, "status": session.clarification_state.status},
            )
        if selected_preset_id is not None:
            session.intent_packet.preferred_preset_id = selected_preset_id
        if selected_cluster_template_ids is not None and selected_cluster_template_ids:
            session.intent_packet.preferred_cluster_template_ids = list(selected_cluster_template_ids)
        plan_draft, goal_packet = self._plan_draft_for_session(session)
        if plan_draft is None or goal_packet is None:
            raise WorkflowError("intent session could not produce a launchable plan draft", {"session_id": session_id})
        launch_payload = self.launch_goal(
            goal=session.intent_packet.goal,
            preset_id=plan_draft.selected_preset_id,
            preferred_cluster_template_ids=plan_draft.selected_cluster_template_ids,
            execute=execute,
        )
        launch_decision = LaunchDecision(
            session_id=session.session_id,
            approved=True,
            execute=execute,
            selected_preset_id=plan_draft.selected_preset_id,
            selected_cluster_template_ids=plan_draft.selected_cluster_template_ids,
            rationale=rationale,
            target_run_id=launch_payload["run"]["run_id"],
        )
        session.latest_plan_draft_id = plan_draft.draft_id
        session.active_run_id = launch_decision.target_run_id
        session.status = IntentSessionStatus.launched
        self._persist_session(session)
        self._ensure_watchdog(
            session_id=session.session_id,
            run_id=session.active_run_id,
            trigger="review_gate",
            objective="Track the active run until it reaches review or closeout.",
            auto_action_enabled=True,
            notes=["auto-created on launch"],
        )
        return self._interaction_payload(
            session=session,
            plan_draft=plan_draft,
            goal_packet=goal_packet,
            launch_decision=launch_decision,
            launch_payload=launch_payload,
        )

    def create_followup_request(
        self,
        session_id: str,
        *,
        instruction: str,
        intent: str = "continue",
        blocking: bool = False,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        session = self.intent_session_repo.get(session_id)
        if session is None:
            raise EntityNotFoundError("intent_session", session_id)
        followup_request = FollowupRequest(
            session_id=session_id,
            run_id=run_id or session.active_run_id,
            instruction=instruction,
            intent=intent,
            blocking=blocking,
            status="pending",
        )
        self.followup_request_repo.create(followup_request)
        self._ensure_watchdog(
            session_id=session_id,
            run_id=followup_request.run_id,
            trigger="followup_pending",
            objective="Keep the follow-up queue visible until it is replanned or cleared.",
            auto_action_enabled=True,
            notes=["auto-created on follow-up"],
        )
        return self._interaction_payload(
            session=session,
            plan_draft=None,
            goal_packet=None,
            followup_request=followup_request,
        )
