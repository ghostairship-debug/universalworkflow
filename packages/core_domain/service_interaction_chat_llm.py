from __future__ import annotations

from typing import Any

from packages.contracts import (
    ChatMessage,
    ChatMessageRole,
    ChatMessageStatus,
    ChatMessageType,
    ChatStreamEvent,
    ChatStreamEventType,
    IntentSession,
)
from packages.core_domain.errors import EntityNotFoundError
from packages.runtime_langgraph.chat_runtime import HIGH_RISK_CHAT_ACTIONS, ChatActionDecision


class ChatLLMInteractionMixin:
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
                if ChatLLMInteractionMixin._is_new_plan_chat_request(prefix):
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
