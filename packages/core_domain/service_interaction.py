from __future__ import annotations

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


class InteractionServiceMixin:
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

    def list_chat_messages(
        self,
        session_id: str,
        *,
        limit: int | None = 100,
        after_message_id: str | None = None,
    ) -> list[ChatMessage]:
        if self.intent_session_repo.get(session_id) is None:
            raise EntityNotFoundError("intent_session", session_id)
        return self.chat_message_repo.list_for_session(
            session_id,
            limit=limit,
            after_message_id=after_message_id,
        )

    def _create_chat_message(
        self,
        *,
        session_id: str,
        content: str,
        role: ChatMessageRole | str = ChatMessageRole.assistant,
        run_id: str | None = None,
        message_type: ChatMessageType | str = ChatMessageType.text,
        action_type: str | None = None,
        status: ChatMessageStatus | str = ChatMessageStatus.posted,
        payload_json: dict[str, Any] | None = None,
        provider_message_id: str | None = None,
        parent_message_id: str | None = None,
        stream_status: str | None = None,
        graph_node: str | None = None,
        token_usage: dict[str, Any] | None = None,
        client_message_id: str | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            session_id=session_id,
            run_id=run_id,
            role=ChatMessageRole(role),
            content=content,
            message_type=ChatMessageType(message_type),
            action_type=action_type,
            status=ChatMessageStatus(status),
            payload_json=dict(payload_json or {}),
            provider_message_id=provider_message_id,
            parent_message_id=parent_message_id,
            stream_status=stream_status,
            graph_node=graph_node,
            token_usage=token_usage,
            client_message_id=client_message_id,
        )
        return self.chat_message_repo.create(message)

    def _create_chat_stream_event(
        self,
        *,
        session_id: str,
        event_type: ChatStreamEventType | str,
        payload_json: dict[str, Any],
        run_id: str | None = None,
        message_id: str | None = None,
    ) -> ChatStreamEvent:
        event = ChatStreamEvent(
            session_id=session_id,
            run_id=run_id,
            message_id=message_id,
            event_type=ChatStreamEventType(event_type),
            payload_json=dict(payload_json),
        )
        return self.chat_stream_event_repo.create(event)

    def _pending_confirmation_payload(self, session_id: str) -> dict[str, Any] | None:
        pending = [
            message
            for message in self.chat_message_repo.list_for_session(session_id, limit=100)
            if str(message.status) == str(ChatMessageStatus.pending_confirmation)
        ]
        if not pending:
            return None
        return pending[-1].model_dump(mode="json")

    def _chat_confirmation_reply(self, content: str, *, pending_action_type: str | None = None) -> str | None:
        normalized = content.strip().lower()
        if not normalized:
            return None
        decline_markers = {
            "不确认",
            "不要",
            "取消",
            "拒绝",
            "否",
            "先别",
            "no",
            "nope",
            "reject",
            "cancel",
            "stop",
        }
        confirm_markers = {
            "确认",
            "确认执行",
            "通过",
            "同意",
            "继续",
            "执行",
            "启动并执行",
            "可以",
            "好的",
            "是",
            "yes",
            "ok",
            "okay",
            "approve",
            "confirm",
            "proceed",
            "continue",
            "run",
        }
        if pending_action_type == "launch_execute":
            confirm_markers.update({"launch", "start", "启动", "开始", "启动执行", "执行启动"})
        if pending_action_type == "resume_run":
            confirm_markers.update({"resume", "继续执行", "执行下一步"})
        if any(marker in normalized for marker in decline_markers):
            return "decline"
        if any(marker in normalized for marker in confirm_markers):
            return "confirm"
        return None

    def _decline_chat_confirmation(
        self,
        *,
        pending_confirmation: dict[str, Any],
        user_message: ChatMessage,
    ) -> dict[str, Any]:
        action_id = str(pending_confirmation.get("message_id") or "")
        message = self.chat_message_repo.get(action_id)
        if message is None:
            raise EntityNotFoundError("chat_message", action_id)
        confirmation = message.payload_json.get("confirmation")
        if not isinstance(confirmation, dict):
            confirmation = {}
        declined_payload = {
            **message.payload_json,
            "confirmation": {
                **confirmation,
                "declined_at": self._utc_now().isoformat(),
                "decline_source_message_id": user_message.message_id,
            },
        }
        self.chat_message_repo.update_status(action_id, ChatMessageStatus.blocked, payload_json=declined_payload)
        session_id = str(confirmation.get("session_id") or message.session_id)
        run_id = confirmation.get("run_id")
        action_type = str(confirmation.get("action_type") or message.action_type or "unknown")
        result_message = self._create_chat_message(
            session_id=session_id,
            run_id=run_id if isinstance(run_id, str) else None,
            role=ChatMessageRole.assistant,
            content=f"已取消待确认动作 `{action_type}`，当前 workflow 状态保持不变。",
            message_type=ChatMessageType.confirmation_result,
            action_type=action_type,
            status=ChatMessageStatus.blocked,
            payload_json={"source_action_id": action_id, "declined": True},
            parent_message_id=user_message.message_id,
        )
        stream_event = self._create_chat_stream_event(
            session_id=session_id,
            run_id=run_id if isinstance(run_id, str) else None,
            message_id=result_message.message_id,
            event_type=ChatStreamEventType.confirmation_result,
            payload_json=result_message.model_dump(mode="json"),
        )
        return self._chat_payload(
            session_id,
            chat_events=[user_message, result_message],
            stream_events=[stream_event],
            action_result={"action_type": action_type, "declined": True, "requires_confirmation": False},
        )

    def _execute_confirmed_active_run_from_chat(
        self,
        *,
        session: IntentSession,
        user_message: ChatMessage,
        stream_events: list[ChatStreamEvent],
        rationale: str,
    ) -> dict[str, Any] | None:
        run_id = session.active_run_id
        if not run_id:
            return None
        run = self.run_repo.get(run_id)
        if run is None:
            return None
        action_type: str | None = None
        if str(run.status) == str(RunStatus.prepared):
            action_type = "resume_run"
            result = self.resume_run(run_id)
        elif str(run.status) == str(RunStatus.awaiting_review):
            action_type = "approve_run"
            result = self.approve_run_review(run_id, rationale)
        else:
            return None

        result_payload = self._chat_action_result_payload(result)
        result_run_id = result_payload.get("run", {}).get("run_id") if isinstance(result_payload.get("run"), dict) else run_id
        result_message = self._create_chat_message(
            session_id=session.session_id,
            run_id=result_run_id if isinstance(result_run_id, str) else run_id,
            role=ChatMessageRole.assistant,
            content=f"已确认并完成动作 `{action_type}`。",
            message_type=ChatMessageType.confirmation_result,
            action_type=action_type,
            payload_json={"direct_chat_confirmation": True, "result": result_payload},
            parent_message_id=user_message.message_id,
        )
        result_events = [
            self._create_chat_stream_event(
                session_id=session.session_id,
                run_id=result_run_id if isinstance(result_run_id, str) else run_id,
                message_id=result_message.message_id,
                event_type=ChatStreamEventType.confirmation_result,
                payload_json=result_message.model_dump(mode="json"),
            ),
            self._create_chat_stream_event(
                session_id=session.session_id,
                run_id=result_run_id if isinstance(result_run_id, str) else run_id,
                message_id=result_message.message_id,
                event_type=ChatStreamEventType.run_update,
                payload_json={"action_type": action_type, "result": result_payload},
            ),
        ]
        return self._chat_payload(
            session.session_id,
            chat_events=[user_message, result_message],
            stream_events=[*stream_events, *result_events],
            action_result=result_payload,
        )

    def _chat_payload(
        self,
        session_id: str,
        *,
        chat_events: list[ChatMessage] | None = None,
        stream_events: list[ChatStreamEvent] | None = None,
        action_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = self.get_intent_session_payload(session_id)
        payload["chat_events"] = [message.model_dump(mode="json") for message in chat_events or []]
        payload["chat_stream_events"] = [event.model_dump(mode="json") for event in stream_events or []]
        payload["chat_llm"] = self.chat_llm_runtime.describe()
        payload["chat_graph"] = self.chat_control_graph.describe()
        payload["pending_confirmation"] = self._pending_confirmation_payload(session_id)
        if action_result is not None:
            payload["action_result"] = action_result
        return payload

    def _active_run_id_for_chat(self, session: IntentSession, explicit_run_id: str | None = None) -> str | None:
        return explicit_run_id or session.active_run_id

    def _chat_contains_any(self, normalized_content: str, markers: set[str]) -> bool:
        return any(marker in normalized_content for marker in markers)

    def _confirmation_card(
        self,
        *,
        session: IntentSession,
        action_type: str,
        content: str,
        run_id: str | None = None,
        source_message_id: str | None = None,
        risk_level: str = "high",
    ) -> ChatMessage:
        target = run_id or session.active_run_id
        return self._create_chat_message(
            session_id=session.session_id,
            run_id=target,
            role=ChatMessageRole.assistant,
            content=content,
            message_type=ChatMessageType.confirmation_required,
            action_type=action_type,
            status=ChatMessageStatus.pending_confirmation,
            payload_json={
                "confirmation": {
                    "action_type": action_type,
                    "session_id": session.session_id,
                    "run_id": target,
                    "risk_level": risk_level,
                    "source_message_id": source_message_id,
                    "requires_confirmation": True,
                }
            },
        )

    def _chat_no_active_run_message(self, session: IntentSession, action_type: str) -> ChatMessage:
        return self._create_chat_message(
            session_id=session.session_id,
            role=ChatMessageRole.assistant,
            content="当前会话还没有 active run。你可以先说“预览计划”或“启动”。",
            message_type=ChatMessageType.error,
            action_type=action_type,
            status=ChatMessageStatus.blocked,
            payload_json={"reason": "missing_active_run", "action_type": action_type},
        )

    def _chat_action_result_payload(self, result: Any) -> dict[str, Any]:
        if hasattr(result, "run") and hasattr(result.run, "model_dump"):
            payload: dict[str, Any] = {"run": result.run.model_dump(mode="json")}
            if hasattr(result, "evidence") and result.evidence is not None:
                payload["evidence"] = result.evidence.model_dump(mode="json")
            if hasattr(result, "review_verdict") and result.review_verdict is not None:
                payload["review_verdict"] = result.review_verdict.model_dump(mode="json")
            return payload
        if hasattr(result, "model_dump"):
            return result.model_dump(mode="json")
        if isinstance(result, dict):
            return result
        return {"result": str(result)}

    def _summarize_active_run_for_chat(
        self,
        *,
        session: IntentSession,
        run_id: str,
        action_type: str,
    ) -> ChatMessage:
        summary = self.get_run_summary(run_id)
        return self._create_chat_message(
            session_id=session.session_id,
            run_id=run_id,
            role=ChatMessageRole.assistant,
            content=summary["headline"],
            message_type=ChatMessageType.workflow_event,
            action_type=action_type,
            payload_json={"run_summary": summary},
        )

    def _create_pr_ready_summary_message(self, session: IntentSession, run_id: str) -> ChatMessage:
        summary = self.get_run_pr_ready_summary(run_id)
        title = summary.get("title") or summary.get("headline") or f"PR-ready summary for {run_id}"
        return self._create_chat_message(
            session_id=session.session_id,
            run_id=run_id,
            role=ChatMessageRole.assistant,
            content=f"PR-ready summary 已生成：{title}",
            message_type=ChatMessageType.workflow_event,
            action_type="pr_ready_summary",
            payload_json={"pr_ready_summary": summary},
        )

    def _route_chat_message(
        self,
        *,
        session: IntentSession,
        user_message: ChatMessage,
        content: str,
        run_id: str | None = None,
    ) -> tuple[list[ChatMessage], dict[str, Any] | None]:
        normalized = content.strip().lower()
        active_run_id = self._active_run_id_for_chat(session, run_id)
        created: list[ChatMessage] = []

        if self._chat_contains_any(normalized, {"approve", "通过", "同意"}):
            if active_run_id is None:
                return [self._chat_no_active_run_message(session, "approve_run")], None
            return [
                self._confirmation_card(
                    session=session,
                    run_id=active_run_id,
                    action_type="approve_run",
                    content=f"确认通过 `{active_run_id}` 的人工 review？确认后 run 会进入 completed。",
                    source_message_id=user_message.message_id,
                )
            ], None

        if self._chat_contains_any(normalized, {"reject", "拒绝", "驳回"}):
            if active_run_id is None:
                return [self._chat_no_active_run_message(session, "reject_run")], None
            return [
                self._confirmation_card(
                    session=session,
                    run_id=active_run_id,
                    action_type="reject_run",
                    content=f"确认拒绝 `{active_run_id}` 的人工 review？确认后 run 会进入 failed。",
                    source_message_id=user_message.message_id,
                )
            ], None

        if self._chat_contains_any(normalized, {"cancel", "取消", "停止", "终止"}):
            if active_run_id is None:
                return [self._chat_no_active_run_message(session, "cancel_run")], None
            return [
                self._confirmation_card(
                    session=session,
                    run_id=active_run_id,
                    action_type="cancel_run",
                    content=f"确认取消 `{active_run_id}`？这个操作会关闭当前 run。",
                    source_message_id=user_message.message_id,
                )
            ], None

        if self._chat_contains_any(normalized, {"resume", "continue", "继续", "执行下一步"}):
            if active_run_id is None:
                return [self._chat_no_active_run_message(session, "resume_run")], None
            return [
                self._confirmation_card(
                    session=session,
                    run_id=active_run_id,
                    action_type="resume_run",
                    content=f"确认继续执行 `{active_run_id}`？这可能触发 worker adapter 和本地命令。",
                    source_message_id=user_message.message_id,
                )
            ], None

        if self._chat_contains_any(normalized, {"pr summary", "pr-ready", "pr 摘要", "pr摘要", "pr 总结"}):
            if active_run_id is None:
                return [self._chat_no_active_run_message(session, "pr_ready_summary")], None
            return [self._create_pr_ready_summary_message(session, active_run_id)], None

        if self._chat_contains_any(normalized, {"排查失败", "失败原因", "diagnose", "failure"}):
            if active_run_id is None:
                return [self._chat_no_active_run_message(session, "diagnose_failure")], None
            return [self._summarize_active_run_for_chat(session=session, run_id=active_run_id, action_type="diagnose_failure")], None

        if self._chat_contains_any(normalized, {"总结", "summary", "状态", "status"}):
            if active_run_id is None:
                return [self._chat_no_active_run_message(session, "summarize_run")], None
            return [self._summarize_active_run_for_chat(session=session, run_id=active_run_id, action_type="summarize_run")], None

        if self._chat_contains_any(normalized, {"启动", "launch", "start", "开始"}):
            if self._chat_contains_any(normalized, {"并执行", "execute", "直接执行"}):
                return [
                    self._confirmation_card(
                        session=session,
                        action_type="launch_execute",
                        content="确认启动并立即执行？这会创建 run，并继续触发本地执行链路。",
                        source_message_id=user_message.message_id,
                    )
                ], None
            payload = self.launch_intent_session(session.session_id, execute=False, rationale="launched from chat")
            launched_run_id = payload["launch_payload"]["run"]["run_id"]
            created.append(
                self._create_chat_message(
                    session_id=session.session_id,
                    run_id=launched_run_id,
                    role=ChatMessageRole.assistant,
                    content=f"已启动并准备 run `{launched_run_id}`。需要执行时请说“继续”。",
                    message_type=ChatMessageType.workflow_event,
                    action_type="launch_prepare",
                    payload_json={"launch_payload": payload["launch_payload"]},
                )
            )
            return created, {"action_type": "launch_prepare", "run_id": launched_run_id}

        if self._chat_contains_any(normalized, {"预览", "计划", "plan"}):
            payload = self.get_intent_session_payload(session.session_id)
            plan_draft = payload.get("plan_draft")
            summary = plan_draft.get("summary") if isinstance(plan_draft, dict) else "计划仍需要补充信息。"
            return [
                self._create_chat_message(
                    session_id=session.session_id,
                    role=ChatMessageRole.assistant,
                    content=f"计划预览：{summary}",
                    message_type=ChatMessageType.workflow_event,
                    action_type="plan_preview",
                    payload_json={"plan_draft": plan_draft, "goal_packet": payload.get("goal_packet")},
                )
            ], None

        if self._chat_contains_any(normalized, {"follow-up", "followup", "后续", "待办", "加入"}):
            payload = self.create_followup_request(
                session.session_id,
                instruction=content,
                intent="continue",
                blocking=False,
                run_id=active_run_id,
            )
            followup = payload.get("followup_request")
            return [
                self._create_chat_message(
                    session_id=session.session_id,
                    run_id=active_run_id,
                    role=ChatMessageRole.assistant,
                    content="已加入 follow-up 队列，会在工作台里持续可见。",
                    message_type=ChatMessageType.workflow_event,
                    action_type="create_followup",
                    payload_json={"followup_request": followup},
                )
            ], None

        return [
            self._create_chat_message(
                session_id=session.session_id,
                run_id=active_run_id,
                role=ChatMessageRole.assistant,
                content="已记录。你可以继续说：预览计划、启动、继续、总结、PR summary、排查失败，或加入 follow-up。",
                message_type=ChatMessageType.text,
                action_type="chat_guidance",
                payload_json={"supported_actions": self.chat_supported_actions()},
            )
        ], None

    def chat_supported_actions(self) -> list[dict[str, Any]]:
        return [
            {"action_type": "plan_preview", "risk_level": "low", "examples": ["预览计划", "plan"]},
            {"action_type": "launch_prepare", "risk_level": "medium", "examples": ["启动"]},
            {"action_type": "launch_execute", "risk_level": "high", "requires_confirmation": True},
            {"action_type": "resume_run", "risk_level": "high", "requires_confirmation": True},
            {"action_type": "approve_run", "risk_level": "high", "requires_confirmation": True},
            {"action_type": "reject_run", "risk_level": "high", "requires_confirmation": True},
            {"action_type": "cancel_run", "risk_level": "high", "requires_confirmation": True},
            {"action_type": "summarize_run", "risk_level": "low", "examples": ["总结", "状态"]},
            {"action_type": "pr_ready_summary", "risk_level": "low", "examples": ["PR summary"]},
            {"action_type": "create_followup", "risk_level": "low", "examples": ["加入 follow-up"]},
        ]

    def _chat_llm_context(self, session: IntentSession, run_id: str | None = None) -> dict[str, Any]:
        active_run_id = self._active_run_id_for_chat(session, run_id)
        active_run_view = self.get_operator_view(active_run_id) if active_run_id else None
        return {
            "session": session.model_dump(mode="json"),
            "active_run_id": active_run_id,
            "active_run_summary": active_run_view.get("summary") if isinstance(active_run_view, dict) else None,
            "active_model_selection": active_run_view.get("resolved_execution") if isinstance(active_run_view, dict) else None,
            "pending_confirmation": self._pending_confirmation_payload(session.session_id),
            "supported_actions": self.chat_supported_actions(),
            "llm": self.chat_llm_runtime.describe(),
        }

    def _chat_action_result_summary(self, action_type: str, result: dict[str, Any] | None) -> str:
        if not result:
            return f"已处理动作 `{action_type}`。"
        if action_type == "launch_prepare":
            run = result.get("run") if isinstance(result.get("run"), dict) else result.get("launch_payload", {}).get("run", {})
            run_id = run.get("run_id") if isinstance(run, dict) else None
            return f"已创建并准备运行 `{run_id}`。需要真正执行时，请确认“继续”。"
        if action_type == "plan_preview":
            plan = result.get("plan_draft") if isinstance(result, dict) else None
            if isinstance(plan, dict):
                return f"计划预览已生成：{plan.get('summary')}"
        if action_type == "create_followup":
            return "已加入后续事项队列。"
        if action_type in {"summarize_run", "diagnose_failure"}:
            summary = result.get("summary") if isinstance(result, dict) else None
            if isinstance(summary, dict):
                return str(summary.get("headline") or "运行摘要已生成。")
        if action_type == "pr_ready_summary":
            return "PR 摘要已生成。"
        return f"已处理动作 `{action_type}`。"

    def _execute_low_risk_chat_action(
        self,
        *,
        session: IntentSession,
        content: str,
        decision: ChatActionDecision,
        run_id: str | None = None,
    ) -> dict[str, Any] | None:
        action_type = decision.action_type
        active_run_id = self._active_run_id_for_chat(session, run_id)
        if action_type == "answer_only":
            return {
                "action_type": "answer_only",
                "summary": "直接回答，无需执行 workflow 动作。",
            }
        if action_type == "plan_preview":
            payload = self.get_intent_session_payload(session.session_id)
            return {
                "action_type": "plan_preview",
                "plan_draft": payload.get("plan_draft"),
                "goal_packet": payload.get("goal_packet"),
                "summary": self._chat_action_result_summary("plan_preview", payload),
            }
        if action_type == "launch_prepare":
            payload = self.launch_intent_session(session.session_id, execute=False, rationale="prepared from LLM chat")
            launch_payload = payload.get("launch_payload") or {}
            return {
                "action_type": "launch_prepare",
                "run_id": launch_payload.get("run", {}).get("run_id") if isinstance(launch_payload.get("run"), dict) else None,
                "launch_payload": launch_payload,
                "summary": self._chat_action_result_summary("launch_prepare", launch_payload),
            }
        if action_type in {"summarize_run", "diagnose_failure"}:
            if active_run_id is None:
                return {"action_type": action_type, "summary": "当前会话还没有 active run。"}
            summary = self.get_run_summary(active_run_id)
            return {"action_type": action_type, "run_id": active_run_id, "summary": summary}
        if action_type == "pr_ready_summary":
            if active_run_id is None:
                return {"action_type": action_type, "summary": "当前会话还没有 active run。"}
            return {
                "action_type": action_type,
                "run_id": active_run_id,
                "pr_ready_summary": self.get_run_pr_ready_summary(active_run_id),
                "summary": "PR 摘要已生成。",
            }
        if action_type == "create_followup":
            payload = self.create_followup_request(
                session.session_id,
                instruction=content,
                intent="continue",
                blocking=False,
                run_id=active_run_id,
            )
            return {
                "action_type": action_type,
                "followup_request": payload.get("followup_request"),
                "summary": self._chat_action_result_summary(action_type, payload),
            }
        return {"action_type": "answer_only", "summary": "我已记录这条消息，可以继续帮你预览、启动、总结或排查。"}

    @staticmethod
    def _is_new_plan_chat_request(content: str) -> bool:
        normalized = content.strip().lower()
        markers = {
            "新计划",
            "新的计划",
            "新任务",
            "新的任务",
            "新会话",
            "新的会话",
            "另起",
            "重新开始",
            "new plan",
            "new task",
            "new session",
            "start over",
        }
        return any(marker in normalized for marker in markers)

    @staticmethod
    def _new_plan_goal_from_chat(content: str) -> str:
        goal = content.strip()
        separators = ["：", ":", "\n"]
        for separator in separators:
            if separator in goal:
                prefix, rest = goal.split(separator, 1)
                if InteractionServiceMixin._is_new_plan_chat_request(prefix):
                    return rest.strip() or goal
        prefixes = [
            "启动一个新计划",
            "启动新计划",
            "创建一个新计划",
            "创建新计划",
            "开始一个新任务",
            "开始新任务",
            "new plan",
            "new task",
        ]
        lowered = goal.lower()
        for prefix in prefixes:
            if lowered.startswith(prefix.lower()):
                stripped = goal[len(prefix) :].strip(" ：:，,")
                return stripped or goal
        return goal

    def _emit_assistant_stream(
        self,
        *,
        session: IntentSession,
        content: str,
        decision: ChatActionDecision,
        action_result: dict[str, Any] | None,
        parent_message_id: str,
        run_id: str | None = None,
    ) -> tuple[ChatMessage, list[ChatStreamEvent]]:
        chunks = list(
            self.chat_llm_runtime.stream_reply(
                content=content,
                context=self._chat_llm_context(session, run_id=run_id),
                decision=decision,
                action_result=action_result,
            )
        )
        final_content = "".join(chunks).strip() or self._chat_action_result_summary(decision.action_type, action_result)
        assistant_message = self._create_chat_message(
            session_id=session.session_id,
            run_id=run_id or session.active_run_id,
            role=ChatMessageRole.assistant,
            content=final_content,
            message_type=ChatMessageType.text,
            action_type=decision.action_type,
            payload_json={"action_result": action_result or {}, "decision": decision.raw},
            parent_message_id=parent_message_id,
            stream_status="completed",
            graph_node="final_summary",
        )
        events: list[ChatStreamEvent] = []
        for index, chunk in enumerate(chunks):
            events.append(
                self._create_chat_stream_event(
                    session_id=session.session_id,
                    run_id=run_id or session.active_run_id,
                    message_id=assistant_message.message_id,
                    event_type=ChatStreamEventType.assistant_delta,
                    payload_json={
                        "message_id": assistant_message.message_id,
                        "delta": chunk,
                        "index": index,
                        "action_type": decision.action_type,
                    },
                )
            )
        events.append(
            self._create_chat_stream_event(
                session_id=session.session_id,
                run_id=run_id or session.active_run_id,
                message_id=assistant_message.message_id,
                event_type=ChatStreamEventType.assistant_final,
                payload_json=assistant_message.model_dump(mode="json"),
            )
        )
        return assistant_message, events

    def _post_chat_message_llm_assisted(
        self,
        *,
        content: str,
        session_id: str | None = None,
        run_id: str | None = None,
        client_message_id: str | None = None,
    ) -> dict[str, Any]:
        if session_id is None:
            payload = self.create_intent_session(goal=content)
            session = IntentSession.model_validate(payload["session"])
        else:
            if self._is_new_plan_chat_request(content):
                payload = self.create_intent_session(goal=self._new_plan_goal_from_chat(content))
                session = IntentSession.model_validate(payload["session"])
            else:
                session = self.intent_session_repo.get(session_id)
                if session is None:
                    raise EntityNotFoundError("intent_session", session_id)

        user_message = self._create_chat_message(
            session_id=session.session_id,
            run_id=run_id or session.active_run_id,
            role=ChatMessageRole.user,
            content=content,
            message_type=ChatMessageType.text,
            action_type="user_input",
            client_message_id=client_message_id,
            stream_status="completed",
            graph_node="user_input",
        )
        stream_events = [
            self._create_chat_stream_event(
                session_id=session.session_id,
                run_id=run_id or session.active_run_id,
                message_id=user_message.message_id,
                event_type=ChatStreamEventType.user_message,
                payload_json=user_message.model_dump(mode="json"),
            )
        ]
        pending_confirmation = self._pending_confirmation_payload(session.session_id)
        pending_action_type = (
            str(pending_confirmation.get("action_type") or "")
            if pending_confirmation is not None
            else None
        )
        confirmation_reply = self._chat_confirmation_reply(content, pending_action_type=pending_action_type)
        if pending_confirmation is not None and confirmation_reply == "confirm":
            confirmed_payload = self.confirm_chat_action(
                str(pending_confirmation["message_id"]),
                rationale=f"confirmed from chat: {content}",
            )
            confirmed_payload["chat_events"] = [
                user_message.model_dump(mode="json"),
                *confirmed_payload.get("chat_events", []),
            ]
            confirmed_payload["chat_stream_events"] = [
                *[event.model_dump(mode="json") for event in stream_events],
                *confirmed_payload.get("chat_stream_events", []),
            ]
            return confirmed_payload
        if pending_confirmation is not None and confirmation_reply == "decline":
            return self._decline_chat_confirmation(
                pending_confirmation=pending_confirmation,
                user_message=user_message,
            )
        if pending_confirmation is None and confirmation_reply == "confirm":
            confirmed_active_run_payload = self._execute_confirmed_active_run_from_chat(
                session=session,
                user_message=user_message,
                stream_events=stream_events,
                rationale=f"confirmed from chat: {content}",
            )
            if confirmed_active_run_payload is not None:
                return confirmed_active_run_payload

        context = self._chat_llm_context(session, run_id=run_id)
        decision = self.chat_llm_runtime.infer_action(content, context)
        graph_state = self.chat_control_graph.run(
            session_id=session.session_id,
            action_type=decision.action_type,
            requires_confirmation=decision.requires_confirmation,
            degraded=decision.degraded,
        )
        stream_events.append(
            self._create_chat_stream_event(
                session_id=session.session_id,
                message_id=user_message.message_id,
                event_type=ChatStreamEventType.graph_update,
                payload_json=graph_state,
            )
        )

        created_messages = [user_message]
        action_result: dict[str, Any] | None = None
        active_run_id = self._active_run_id_for_chat(session, run_id)
        try:
            if decision.action_type in HIGH_RISK_CHAT_ACTIONS or decision.requires_confirmation:
                confirmation_message = self._confirmation_card(
                    session=session,
                    run_id=active_run_id,
                    action_type=decision.action_type,
                    content=f"LLM 建议执行 `{decision.action_type}`。这是高风险动作，需要你确认后才会继续。",
                    source_message_id=user_message.message_id,
                )
                created_messages.append(confirmation_message)
                stream_events.append(
                    self._create_chat_stream_event(
                        session_id=session.session_id,
                        run_id=active_run_id,
                        message_id=confirmation_message.message_id,
                        event_type=ChatStreamEventType.confirmation_required,
                        payload_json=confirmation_message.model_dump(mode="json"),
                    )
                )
                action_result = {"action_type": decision.action_type, "requires_confirmation": True}
            else:
                action_result = self._execute_low_risk_chat_action(
                    session=session,
                    content=content,
                    decision=decision,
                    run_id=run_id,
                )
                if action_result and isinstance(action_result.get("run_id"), str):
                    active_run_id = str(action_result["run_id"])
                stream_events.append(
                    self._create_chat_stream_event(
                        session_id=session.session_id,
                        run_id=active_run_id,
                        message_id=user_message.message_id,
                        event_type=ChatStreamEventType.tool_action_proposed,
                        payload_json={"decision": decision.__dict__, "action_result": action_result or {}},
                    )
                )

            assistant_message, assistant_events = self._emit_assistant_stream(
                session=session,
                content=content,
                decision=decision,
                action_result=action_result,
                parent_message_id=user_message.message_id,
                run_id=active_run_id,
            )
            created_messages.append(assistant_message)
            stream_events.extend(assistant_events)
        except Exception as exc:  # noqa: BLE001
            action_result = {
                "action_type": decision.action_type,
                "failed": True,
                "error": str(exc),
            }
            error_message = self._create_chat_message(
                session_id=session.session_id,
                run_id=active_run_id,
                role=ChatMessageRole.assistant,
                content=f"处理失败：{exc}",
                message_type=ChatMessageType.error,
                action_type=decision.action_type or "error",
                status=ChatMessageStatus.failed,
                payload_json={"error": str(exc), "decision": decision.__dict__},
                parent_message_id=user_message.message_id,
                stream_status="completed",
                graph_node=graph_state.get("graph_node"),
            )
            created_messages.append(error_message)
            stream_events.append(
                self._create_chat_stream_event(
                    session_id=session.session_id,
                    run_id=active_run_id,
                    message_id=error_message.message_id,
                    event_type=ChatStreamEventType.error,
                    payload_json=error_message.model_dump(mode="json"),
                )
            )
        stream_events.append(
            self._create_chat_stream_event(
                session_id=session.session_id,
                run_id=active_run_id,
                message_id=created_messages[-1].message_id if created_messages else user_message.message_id,
                event_type=ChatStreamEventType.status_patch,
                payload_json={
                    "session_id": session.session_id,
                    "active_run_id": active_run_id,
                    "action_type": decision.action_type,
                    "llm": self.chat_llm_runtime.describe(),
                    "model_selection": context.get("active_model_selection"),
                },
            )
        )
        return self._chat_payload(
            session.session_id,
            chat_events=created_messages,
            stream_events=stream_events,
            action_result=action_result,
        )

    def post_chat_message(
        self,
        *,
        content: str,
        session_id: str | None = None,
        run_id: str | None = None,
        mode: str = "llm_assisted",
        client_message_id: str | None = None,
    ) -> dict[str, Any]:
        clean_content = content.strip()
        if not clean_content:
            raise WorkflowError("chat message content is required", {"field": "content"})
        if mode != "rule_based":
            return self._post_chat_message_llm_assisted(
                content=clean_content,
                session_id=session_id,
                run_id=run_id,
                client_message_id=client_message_id,
            )

        created_messages: list[ChatMessage] = []
        action_result: dict[str, Any] | None = None
        if session_id is None:
            payload = self.create_intent_session(goal=clean_content)
            session = IntentSession.model_validate(payload["session"])
            created_messages.append(
                self._create_chat_message(
                    session_id=session.session_id,
                    run_id=run_id,
                    role=ChatMessageRole.user,
                    content=clean_content,
                    message_type=ChatMessageType.text,
                    action_type="create_session",
                )
            )
            plan_draft = payload.get("plan_draft")
            if session.clarification_state.blocking:
                assistant_content = "已创建会话，但计划前需要补充澄清信息。"
            elif isinstance(plan_draft, dict):
                assistant_content = f"已创建会话并生成计划预览：{plan_draft.get('summary')}"
            else:
                assistant_content = "已创建会话，计划预览会在补齐信息后生成。"
            created_messages.append(
                self._create_chat_message(
                    session_id=session.session_id,
                    role=ChatMessageRole.assistant,
                    content=assistant_content,
                    message_type=ChatMessageType.workflow_event,
                    action_type="plan_preview",
                    payload_json={"plan_draft": plan_draft, "goal_packet": payload.get("goal_packet")},
                )
            )
            return self._chat_payload(session.session_id, chat_events=created_messages)

        session = self.intent_session_repo.get(session_id)
        if session is None:
            raise EntityNotFoundError("intent_session", session_id)
        user_message = self._create_chat_message(
            session_id=session.session_id,
            run_id=run_id or session.active_run_id,
            role=ChatMessageRole.user,
            content=clean_content,
            message_type=ChatMessageType.text,
        )
        created_messages.append(user_message)
        routed_messages, action_result = self._route_chat_message(
            session=session,
            user_message=user_message,
            content=clean_content,
            run_id=run_id,
        )
        created_messages.extend(routed_messages)
        return self._chat_payload(session.session_id, chat_events=created_messages, action_result=action_result)

    def confirm_chat_action(self, action_id: str, *, rationale: str | None = None) -> dict[str, Any]:
        message = self.chat_message_repo.get(action_id)
        if message is None:
            raise EntityNotFoundError("chat_message", action_id)
        if str(message.message_type) != str(ChatMessageType.confirmation_required):
            raise WorkflowError("chat message is not a confirmation card", {"message_id": action_id})
        if str(message.status) != str(ChatMessageStatus.pending_confirmation):
            raise WorkflowError(
                "chat confirmation is not pending",
                {"message_id": action_id, "status": str(message.status)},
            )
        confirmation = message.payload_json.get("confirmation")
        if not isinstance(confirmation, dict):
            raise WorkflowError("chat confirmation payload is invalid", {"message_id": action_id})
        action_type = str(confirmation.get("action_type") or "")
        run_id = confirmation.get("run_id")
        session_id = confirmation.get("session_id") or message.session_id
        if not isinstance(session_id, str):
            raise WorkflowError("chat confirmation missing session_id", {"message_id": action_id})

        try:
            if action_type == "resume_run":
                if not isinstance(run_id, str):
                    raise WorkflowError("resume confirmation missing run_id", {"message_id": action_id})
                result = self.resume_run(run_id)
            elif action_type == "approve_run":
                if not isinstance(run_id, str):
                    raise WorkflowError("approve confirmation missing run_id", {"message_id": action_id})
                result = self.approve_run_review(run_id, rationale or "approved from chat")
            elif action_type == "reject_run":
                if not isinstance(run_id, str):
                    raise WorkflowError("reject confirmation missing run_id", {"message_id": action_id})
                result = self.reject_run_review(run_id, rationale or "rejected from chat")
            elif action_type == "cancel_run":
                if not isinstance(run_id, str):
                    raise WorkflowError("cancel confirmation missing run_id", {"message_id": action_id})
                result = self.cancel_run(run_id)
            elif action_type == "launch_execute":
                result = self.launch_intent_session(session_id, execute=True, rationale=rationale or "executed from chat")
            else:
                raise WorkflowError("unsupported chat confirmation action", {"action_type": action_type})
        except Exception as exc:
            failed_payload = {
                **message.payload_json,
                "confirmation": {
                    **confirmation,
                    "failed_at": self._utc_now().isoformat(),
                    "error": str(exc),
                },
            }
            self.chat_message_repo.update_status(action_id, ChatMessageStatus.failed, payload_json=failed_payload)
            self._create_chat_message(
                session_id=session_id,
                run_id=run_id if isinstance(run_id, str) else None,
                role=ChatMessageRole.assistant,
                content=f"确认动作失败：{exc}",
                message_type=ChatMessageType.error,
                action_type=action_type or "unknown",
                status=ChatMessageStatus.failed,
                payload_json={"error": str(exc), "source_action_id": action_id},
            )
            raise

        result_payload = self._chat_action_result_payload(result)
        confirmed_payload = {
            **message.payload_json,
            "confirmation": {
                **confirmation,
                "confirmed_at": self._utc_now().isoformat(),
                "rationale": rationale,
            },
            "result": result_payload,
        }
        self.chat_message_repo.update_status(action_id, ChatMessageStatus.confirmed, payload_json=confirmed_payload)
        result_run_id = result_payload.get("run", {}).get("run_id") if isinstance(result_payload.get("run"), dict) else run_id
        result_message = self._create_chat_message(
            session_id=session_id,
            run_id=result_run_id if isinstance(result_run_id, str) else None,
            role=ChatMessageRole.assistant,
            content=f"已确认并完成动作 `{action_type}`。",
            message_type=ChatMessageType.confirmation_result,
            action_type=action_type,
            payload_json={"source_action_id": action_id, "result": result_payload},
        )
        stream_events = [
            self._create_chat_stream_event(
                session_id=session_id,
                run_id=result_run_id if isinstance(result_run_id, str) else None,
                message_id=result_message.message_id,
                event_type=ChatStreamEventType.confirmation_result,
                payload_json=result_message.model_dump(mode="json"),
            ),
            self._create_chat_stream_event(
                session_id=session_id,
                run_id=result_run_id if isinstance(result_run_id, str) else None,
                message_id=result_message.message_id,
                event_type=ChatStreamEventType.run_update,
                payload_json={"action_type": action_type, "result": result_payload},
            ),
        ]
        return self._chat_payload(
            session_id,
            chat_events=[result_message],
            stream_events=stream_events,
            action_result=result_payload,
        )

    def build_interaction_stream_events(
        self,
        session_id: str,
        *,
        after_message_id: str | None = None,
        after_event_id: str | None = None,
    ) -> list[dict[str, Any]]:
        payload = self.get_intent_session_payload(session_id)
        session_payload = payload["session"]
        active_run_view = payload.get("active_run_operator_view")
        events: list[dict[str, Any]] = []
        persisted_events = self.chat_stream_event_repo.list_for_session(
            session_id,
            limit=100,
            after_event_id=after_event_id,
        )
        if not persisted_events and after_event_id is None:
            for message in self.chat_message_repo.list_for_session(
                session_id,
                limit=100,
                after_message_id=after_message_id,
            ):
                event_type = (
                    ChatStreamEventType.user_message
                    if str(message.role) == str(ChatMessageRole.user)
                    else ChatStreamEventType.assistant_final
                )
                persisted_events.append(
                    ChatStreamEvent(
                        event_id=message.message_id,
                        session_id=session_id,
                        run_id=message.run_id,
                        message_id=message.message_id,
                        event_type=event_type,
                        payload_json=message.model_dump(mode="json"),
                    )
                )
        for stream_event in persisted_events:
            events.append(
                {
                    "event": str(stream_event.event_type),
                    "id": stream_event.event_id,
                    "data": stream_event.payload_json,
                }
            )
        events.append(
            {
                "event": "status_patch",
                "id": f"status:{session_id}",
                "data": {
                    "session": session_payload,
                    "plan_draft": payload.get("plan_draft"),
                    "pending_confirmation": payload.get("pending_confirmation"),
                    "llm": self.chat_llm_runtime.describe(),
                    "model_selection": (
                        active_run_view.get("resolved_execution")
                        if isinstance(active_run_view, dict)
                        else None
                    ),
                    "graph": self.chat_control_graph.describe(),
                },
            }
        )

        if isinstance(active_run_view, dict):
            run = active_run_view.get("run", {})
            run_id = run.get("run_id")
            events.append(
                {
                    "event": "run_update",
                    "id": f"run:{run_id}",
                    "data": {
                        "run": run,
                        "headline": active_run_view.get("summary", {}).get("headline"),
                        "next_action": active_run_view.get("summary", {}).get("next_action"),
                        "inspection": active_run_view.get("inspection"),
                        "resolved_execution": active_run_view.get("resolved_execution"),
                    },
                }
            )
            for timeline_event in active_run_view.get("timeline", [])[-10:]:
                event_id = timeline_event.get("event_id") if isinstance(timeline_event, dict) else None
                events.append(
                    {
                        "event": "timeline_event",
                        "id": event_id or f"timeline:{run_id}",
                        "data": timeline_event,
                    }
                )
            if run.get("status") == str(RunStatus.awaiting_review):
                events.append(
                    {
                    "event": "review_required",
                        "id": f"review:{run_id}",
                        "data": {
                            "run": run,
                            "review_summary": active_run_view.get("summary", {}).get("review_summary"),
                            "mutation_report": active_run_view.get("mutation_report"),
                        },
                    }
                )
            mutation_result = active_run_view.get("mutation_report", {}).get("mutation_result")
            if mutation_result:
                events.append(
                    {
                        "event": "test_evidence",
                        "id": f"tests:{run_id}",
                        "data": {"run_id": run_id, "mutation_result": mutation_result},
                    }
                )
            if isinstance(run_id, str):
                events.append(
                    {
                        "event": "pr_ready_summary",
                        "id": f"pr:{run_id}",
                        "data": self.get_run_pr_ready_summary(run_id),
                    }
                )

        events.append(
            {
                "event": "heartbeat",
                "id": f"heartbeat:{session_id}",
                "data": {"session_id": session_id, "emitted_at": self._utc_now().isoformat()},
            }
        )
        return events

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

    def list_cluster_templates(self) -> list[ExecutionClusterTemplate]:
        return list_default_cluster_templates()

    def get_cluster_template(self, template_id: str) -> ExecutionClusterTemplate:
        template = next((item for item in self.list_cluster_templates() if item.template_id == template_id), None)
        if template is None:
            raise EntityNotFoundError("cluster_template", template_id)
        return template

    def _cluster_router(self) -> ClusterRouter:
        return ClusterRouter(self.list_cluster_templates())

    @staticmethod
    def _contains_cjk(text: str) -> bool:
        return any("\u4e00" <= char <= "\u9fff" for char in text)

    def _goal_needs_target_clarification(self, goal: str) -> bool:
        normalized = goal.strip()
        if self._contains_cjk(normalized):
            concrete_markers = {
                "产出",
                "输出",
                "生成",
                "创建",
                "编写",
                "写",
                "实现",
                "修复",
                "改造",
                "清理",
                "测试",
                "验证",
                "报告",
                "文档",
                "说明",
                "计划",
                "摘要",
                "评估",
                "代码",
                "补丁",
                "文件",
                "界面",
                "功能",
            }
            return len(normalized) < 12 or not any(marker in normalized for marker in concrete_markers)
        return len(normalized) < 24 or len(normalized.split()) < 4

    def _default_clarification_state(self, intent_packet: IntentPacket) -> ClarificationState:
        prompts: list[ClarificationPrompt] = []
        normalized_goal = intent_packet.goal.strip()
        if self._goal_needs_target_clarification(normalized_goal):
            prompts.append(
                ClarificationPrompt(
                    prompt_id="clarify_target_artifact",
                    question="这次要产出的具体文档、代码改动、决策或结果是什么？",
                    required=True,
                    source="interaction_plane",
                )
            )
        if (
            any(
                marker in normalized_goal.lower()
                for marker in {"project", "delivery", "multi", "cluster", "research", "项目", "交付", "多", "集群", "研究", "调研"}
            )
            and not intent_packet.preferred_cluster_template_ids
        ):
            prompts.append(
                ClarificationPrompt(
                    prompt_id="clarify_cluster_preference",
                    question="这次保持单预设路径即可，还是需要使用集群模板？",
                    required=False,
                    source="interaction_plane",
                    status="not_needed",
                )
            )
        return ClarificationState(prompts=prompts) if prompts else ClarificationState()

    def _selected_cluster_template_ids(
        self,
        *,
        goal: str,
        preset_id: str | None = None,
        preferred_cluster_template_ids: list[str] | None = None,
        plan_graph: dict[str, Any] | None = None,
    ) -> list[str]:
        if preferred_cluster_template_ids:
            return self._cluster_router().suggest_template_ids(
                goal=goal,
                preset_id=preset_id,
                preferred_template_ids=preferred_cluster_template_ids,
            )
        graph_template_ids = (
            plan_graph.get("cluster_template_ids", [])
            if isinstance(plan_graph, dict)
            else []
        )
        if graph_template_ids:
            return self._cluster_router().suggest_template_ids(
                goal=goal,
                preset_id=preset_id,
                preferred_template_ids=list(graph_template_ids),
            )
        return self._cluster_router().suggest_template_ids(goal=goal, preset_id=preset_id)

    def _cluster_templates_for_ids(self, template_ids: list[str]) -> list[ExecutionClusterTemplate]:
        templates: list[ExecutionClusterTemplate] = []
        seen: set[str] = set()
        for template_id in template_ids:
            if template_id in seen:
                continue
            seen.add(template_id)
            template = self._cluster_router().get_template(template_id)
            if template is not None:
                templates.append(template)
        return templates

    def _cluster_member_goal(self, goal: str, template_id: str, role_label: str, public_role: AgentRoleType) -> str:
        role_map = {
            "architect": f"Design the work breakdown and integration handoffs for: {goal}",
            "implementer": f"Implement the primary delivery slice for: {goal}",
            "risk_mapper": f"Research risks, supporting evidence, and open questions for: {goal}",
            "quality_gate": f"Review the implementation and supporting evidence for: {goal}",
            "launch_guard": f"Prepare the operator-facing launch and follow-up checkpoint for: {goal}",
            "research_analyst": f"Investigate and summarize findings for: {goal}",
            "citation_checker": f"Verify citations, claims, and confidence posture for: {goal}",
        }
        if role_label in role_map:
            return role_map[role_label]
        if public_role == AgentRoleType.planner:
            return f"Plan the work for: {goal}"
        if public_role == AgentRoleType.coder:
            return f"Implement the requested change for: {goal}"
        if public_role == AgentRoleType.researcher:
            return f"Research and summarize evidence for: {goal}"
        if public_role == AgentRoleType.reviewer:
            return f"Review the output for: {goal}"
        return f"Keep operator control visible for: {goal}"

    def _cluster_orchestration_plan(
        self,
        *,
        template: ExecutionClusterTemplate,
        goal: str,
        selected_preset_id: str | None = None,
        run_id: str | None = None,
    ) -> OrchestrationPlan:
        return self.orchestration_service.build_cluster_orchestration_plan(
            template=template,
            selected_preset_id=selected_preset_id,
            run_id=run_id,
            include_operator_step=False,
        )

    def _preview_cluster_graph(
        self,
        *,
        goal: str,
        selected_preset_id: str | None,
        selected_cluster_template_ids: list[str],
        plan_graph: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        templates = self._cluster_templates_for_ids(selected_cluster_template_ids)
        if not templates:
            return None
        template = templates[0]
        plan = self._cluster_orchestration_plan(
            template=template,
            goal=goal,
            selected_preset_id=selected_preset_id,
        )
        graph = self.orchestration_engine.build_graph_from_plan(
            run_id=None,
            preset_id=selected_preset_id or plan.preset_id,
            goal=goal,
            plan=plan,
            role_goal_for=lambda parent_goal, role: self._cluster_member_goal(
                parent_goal,
                template.template_id,
                next(
                    (
                        member.role_label
                        for member in template.member_specs
                        if member.public_role == role
                    ),
                    str(role),
                ),
                role,
            ),
            side_effect_level_for_adapter=self._side_effect_level_for_adapter,
            recommended_preset_id=selected_preset_id or plan.preset_id,
            summary=f"{template.name} preview graph for `{selected_preset_id or plan.preset_id}`.",
            risk_summary=[
                f"cluster template `{template.template_id}` is a preview projection layered on top of the shared execution substrate",
            ],
        )
        return graph.model_dump(mode="json")

    def _cluster_policy_preview_payload(
        self,
        *,
        cluster_graph: dict[str, Any] | None,
        selected_clusters: list[ExecutionClusterTemplate],
    ) -> dict[str, Any]:
        if cluster_graph is None:
            return {"enabled": False, "cluster_policy_preview": None}
        capability_policy = self._capability_policy_preview_for_plan_graph(cluster_graph)
        return {
            "enabled": True,
            "selected_cluster_template_ids": [template.template_id for template in selected_clusters],
            "template_summaries": [
                {
                    "template_id": template.template_id,
                    "name": template.name,
                    "execution_mode": str(template.execution_mode),
                    "member_count": len(template.member_specs),
                    "default_review_policy": str(template.default_review_policy),
                }
                for template in selected_clusters
            ],
            "policy_preview": capability_policy,
            "recommended_operator_mode": capability_policy["recommended_operator_mode"],
            "requires_human_checkpoint": capability_policy["requires_human_checkpoint"],
        }

    def _cluster_execution_plans(
        self,
        *,
        goal: str,
        selected_clusters: list[ExecutionClusterTemplate],
        session_id: str | None = None,
        run_id: str | None = None,
    ) -> list[ClusterExecutionPlan]:
        plans: list[ClusterExecutionPlan] = []
        for template in selected_clusters:
            sequence_groups: dict[int, list[str]] = {}
            for member in template.member_specs:
                sequence_groups.setdefault(
                    sequence_no_for_cluster_member(template.template_id, member.role_label, member.public_role),
                    [],
                ).append(member.role_label)
            plans.append(
                ClusterExecutionPlan(
                    cluster_plan_id=f"{template.template_id}_{session_id or run_id or 'preview'}",
                    cluster_template_id=template.template_id,
                    run_id=run_id,
                    session_id=session_id,
                    objective=goal,
                    selected_member_ids=[member.member_id for member in template.member_specs],
                    handoff_points=[
                        " -> ".join(sequence_groups[sequence_no])
                        for sequence_no in sorted(sequence_groups)
                    ],
                    success_criteria=(
                        list(template.review_rubric.criteria)
                        if template.review_rubric is not None
                        else [f"{template.name} completes without blocking escalations"]
                    ),
                    status="planned" if run_id is None else "active",
                )
            )
        return plans

    def _cluster_preview_bundle(
        self,
        *,
        goal: str,
        selected_preset_id: str | None,
        plan_graph: dict[str, Any] | None,
        preferred_cluster_template_ids: list[str] | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        selected_cluster_template_ids = self._selected_cluster_template_ids(
            goal=goal,
            preset_id=selected_preset_id,
            preferred_cluster_template_ids=preferred_cluster_template_ids,
            plan_graph=plan_graph,
        )
        selected_clusters = self._cluster_templates_for_ids(selected_cluster_template_ids)
        cluster_graph = self._preview_cluster_graph(
            goal=goal,
            selected_preset_id=selected_preset_id,
            selected_cluster_template_ids=selected_cluster_template_ids,
            plan_graph=plan_graph,
        )
        return {
            "selected_cluster_template_ids": selected_cluster_template_ids,
            "selected_clusters": selected_clusters,
            "cluster_graph": cluster_graph,
            "cluster_policy_preview": self._cluster_policy_preview_payload(
                cluster_graph=cluster_graph,
                selected_clusters=selected_clusters,
            ),
            "cluster_execution_plans": self._cluster_execution_plans(
                goal=goal,
                selected_clusters=selected_clusters,
                session_id=session_id,
                run_id=run_id,
            ),
        }

    def _cluster_member_progress(
        self,
        *,
        template: ExecutionClusterTemplate,
        run_status: str,
        orchestration: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        role_progress = orchestration.get("role_progress", {}) if isinstance(orchestration, dict) else {}
        member_progress: list[dict[str, Any]] = []
        for member in template.member_specs:
            progress = role_progress.get(str(member.public_role), {})
            member_status = str(progress.get("status") or ("completed" if run_status == "completed" else "pending"))
            member_progress.append(
                {
                    "member_id": member.member_id,
                    "role": str(member.public_role),
                    "role_label": member.role_label,
                    "status": member_status,
                    "run_id": progress.get("run_id"),
                    "parallel_group": member.parallel_group,
                }
            )
        return member_progress

    def _cluster_handoff_packets_for_template(
        self,
        *,
        template: ExecutionClusterTemplate,
        goal: str,
        member_progress: list[dict[str, Any]],
    ) -> list[ClusterHandoffPacket]:
        member_by_sequence: dict[int, list[dict[str, Any]]] = {}
        spec_by_id = {member.member_id: member for member in template.member_specs}
        for item in member_progress:
            spec = spec_by_id[item["member_id"]]
            sequence = sequence_no_for_cluster_member(template.template_id, spec.role_label, spec.public_role)
            member_by_sequence.setdefault(sequence, []).append(item)
        handoffs: list[ClusterHandoffPacket] = []
        ordered_sequences = sorted(member_by_sequence)
        for index, source_sequence in enumerate(ordered_sequences[:-1]):
            target_sequence = ordered_sequences[index + 1]
            for source in member_by_sequence[source_sequence]:
                for target in member_by_sequence[target_sequence]:
                    blocking = []
                    if source["status"] not in {"completed", "awaiting_review"}:
                        blocking.append(f"{source['role_label']} has not completed its handoff output yet")
                    handoffs.append(
                        ClusterHandoffPacket(
                            cluster_handoff_id=(
                                f"{template.template_id}_{source['member_id']}_{target['member_id']}"
                            ),
                            cluster_template_id=template.template_id,
                            from_member_id=source["member_id"],
                            to_member_id=target["member_id"],
                            handoff_summary=(
                                f"{source['role_label']} hands execution to {target['role_label']} for `{goal}`"
                            ),
                            artifact_refs=(
                                [f"run:{source['run_id']}"] if source.get("run_id") else []
                            ),
                            blocking_risks=blocking,
                            escalation_flags=["pending_source_output"] if blocking else [],
                        )
                    )
        return handoffs

    def _cluster_runtime_bundle(
        self,
        *,
        goal: str,
        run_id: str,
        run_status: str,
        selected_preset_id: str,
        plan_graph: dict[str, Any] | None,
        orchestration: dict[str, Any] | None,
        summary_text: str,
    ) -> dict[str, Any]:
        preview_bundle = self._cluster_preview_bundle(
            goal=goal,
            selected_preset_id=selected_preset_id,
            plan_graph=plan_graph,
            run_id=run_id,
        )
        cluster_progress: list[dict[str, Any]] = []
        cluster_packets: list[dict[str, Any]] = []
        cluster_handoffs: list[dict[str, Any]] = []
        child_runs = orchestration.get("child_runs", []) if isinstance(orchestration, dict) else []
        for template in preview_bundle["selected_clusters"]:
            member_progress = self._cluster_member_progress(
                template=template,
                run_status=run_status,
                orchestration=orchestration,
            )
            completed_count = sum(1 for item in member_progress if item["status"] == "completed")
            handoff_packets = self._cluster_handoff_packets_for_template(
                template=template,
                goal=goal,
                member_progress=member_progress,
            )
            cluster_progress.append(
                {
                    "template_id": template.template_id,
                    "name": template.name,
                    "status": run_status,
                    "completed_member_count": completed_count,
                    "total_member_count": len(member_progress),
                    "member_progress": member_progress,
                }
            )
            cluster_handoffs.extend([packet.model_dump(mode="json") for packet in handoff_packets])
            cluster_packets.append(
                ClusterOutputPacket(
                    cluster_output_id=f"{template.template_id}_{run_id}",
                    cluster_template_id=template.template_id,
                    run_id=run_id,
                    objective=goal,
                    summary=summary_text,
                    risks=[
                        item.blocking_risks[0]
                        for item in handoff_packets
                        if item.blocking_risks
                    ],
                    artifact_refs=[f"run:{item['run_id']}" for item in child_runs if item.get("run_id")],
                    quality_verdict=(
                        "completed"
                        if run_status == "completed"
                        else ("awaiting_review" if run_status == "awaiting_review" else "in_progress")
                    ),
                    escalation_flags=[
                        "review_gate_open"
                        for item in handoff_packets
                        if item.blocking_risks
                    ],
                    handoff_packets=handoff_packets,
                ).model_dump(mode="json")
            )
        return {
            **preview_bundle,
            "cluster_progress": cluster_progress,
            "cluster_packets": cluster_packets,
            "cluster_handoffs": cluster_handoffs,
            "cluster_execution_lineage": {
                "selected_cluster_template_ids": preview_bundle["selected_cluster_template_ids"],
                "cluster_plan_ids": [
                    plan.cluster_plan_id
                    for plan in preview_bundle["cluster_execution_plans"]
                ],
                "orchestration_id": orchestration.get("orchestration_id") if isinstance(orchestration, dict) else None,
                "child_runs": child_runs,
                "member_run_count": len(child_runs),
            },
        }

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
