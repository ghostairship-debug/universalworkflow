from __future__ import annotations

from typing import Any, Iterable

from .actions import ChatActionDecision
from .base import ChatLLMRuntime

class FallbackChatLLMRuntime(ChatLLMRuntime):
    def __init__(self, *, primary: ChatLLMRuntime, fallback: ChatLLMRuntime) -> None:
        self.primary = primary
        self.fallback = fallback

    def describe(self) -> dict[str, Any]:
        primary = self.primary.describe()
        fallback = self.fallback.describe()
        return {
            **primary,
            "fallback_provider": fallback.get("provider"),
            "fallback_model": fallback.get("model"),
        }

    def infer_action(self, content: str, context: dict[str, Any]) -> ChatActionDecision:
        decision = self.primary.infer_action(content, context)
        if decision.degraded:
            fallback_decision = self.fallback.infer_action(content, context)
            if not fallback_decision.degraded:
                return fallback_decision
        return decision

    def stream_reply(
        self,
        *,
        content: str,
        context: dict[str, Any],
        decision: ChatActionDecision,
        action_result: dict[str, Any] | None = None,
    ) -> Iterable[str]:
        try:
            chunks = list(
                self.primary.stream_reply(
                    content=content,
                    context=context,
                    decision=decision,
                    action_result=action_result,
                )
            )
            if chunks:
                yield from chunks
                return
        except Exception:
            pass
        yield from self.fallback.stream_reply(
            content=content,
            context=context,
            decision=decision,
            action_result=action_result,
        )
