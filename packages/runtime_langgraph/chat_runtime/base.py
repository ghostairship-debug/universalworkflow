from __future__ import annotations

from typing import Any, Iterable

from .actions import ChatActionDecision, chunk_text, infer_rule_based_chat_action

class ChatLLMRuntime:
    def describe(self) -> dict[str, Any]:
        raise NotImplementedError

    def infer_action(self, content: str, context: dict[str, Any]) -> ChatActionDecision:
        raise NotImplementedError

    def stream_reply(
        self,
        *,
        content: str,
        context: dict[str, Any],
        decision: ChatActionDecision,
        action_result: dict[str, Any] | None = None,
    ) -> Iterable[str]:
        raise NotImplementedError


class DegradedChatLLMRuntime(ChatLLMRuntime):
    def describe(self) -> dict[str, Any]:
        return {
            "provider": "degraded",
            "configured": False,
            "live": False,
            "model": None,
            "reason": "LLM 未配置，已退回规则路由。",
        }

    def infer_action(self, content: str, context: dict[str, Any]) -> ChatActionDecision:
        return infer_rule_based_chat_action(content)

    def stream_reply(
        self,
        *,
        content: str,
        context: dict[str, Any],
        decision: ChatActionDecision,
        action_result: dict[str, Any] | None = None,
    ) -> Iterable[str]:
        action_label = decision.action_type
        if decision.requires_confirmation:
            text = f"LLM 未配置，我已按规则识别到高风险动作 `{action_label}`，需要你确认后才会执行。"
        elif action_result and action_result.get("summary"):
            text = str(action_result["summary"])
        else:
            text = f"LLM 未配置，我已按规则处理这条消息，动作类型为 `{action_label}`。"
        yield from chunk_text(text)
