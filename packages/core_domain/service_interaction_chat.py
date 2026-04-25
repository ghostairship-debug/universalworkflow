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




class ChatCommandControllerMixin:
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
        receipt = self.issue_operator_action_receipt(
            action_type=action_type,
            risk_level=risk_level,
            metadata={
                "source": "chat_confirmation",
                "session_id": session.session_id,
                "run_id": target,
                "source_message_id": source_message_id,
            },
        )
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
                    "operator_action_receipt_id": receipt.receipt_id,
                    "operator_action_receipt_expires_at": receipt.expires_at.isoformat(),
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
        self.consume_operator_action_receipt(
            receipt_id=str(confirmation.get("operator_action_receipt_id") or ""),
            action_type=action_type,
        )

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

