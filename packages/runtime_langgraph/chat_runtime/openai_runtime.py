from __future__ import annotations

import json
import os
from typing import Any, Iterable

from .actions import HIGH_RISK_CHAT_ACTIONS, SUPPORTED_CHAT_ACTIONS, ChatActionDecision, chunk_text, infer_rule_based_chat_action
from .base import ChatLLMRuntime
from .response_utils import _extract_response_text, _iter_response_text_deltas, _load_json_object

class OpenAIChatLLMRuntime(ChatLLMRuntime):
    def __init__(
        self,
        *,
        client: Any | None = None,
        model: str,
        reasoning_effort: str = "low",
        max_output_tokens: int = 360,
    ) -> None:
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.max_output_tokens = max_output_tokens
        if client is not None:
            self._client = client
            return
        from openai import OpenAI

        self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def describe(self) -> dict[str, Any]:
        return {
            "provider": "openai",
            "configured": True,
            "live": True,
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
        }

    def infer_action(self, content: str, context: dict[str, Any]) -> ChatActionDecision:
        fallback = infer_rule_based_chat_action(content)
        prompt = (
            "你是本地个人 workflow 的聊天控制器。请只输出 JSON，字段为 "
            "action_type、confidence、rationale。action_type 必须是以下之一："
            f"{sorted(SUPPORTED_CHAT_ACTIONS)}。\n"
            "高风险执行动作只需要分类，不要执行。\n"
            f"当前上下文：{json.dumps(context, ensure_ascii=False)[:4000]}\n"
            f"用户输入：{content}"
        )
        try:
            response = self._client.responses.create(
                model=self.model,
                instructions="只输出紧凑 JSON，不要 markdown。",
                input=prompt,
                reasoning={"effort": self.reasoning_effort},
                max_output_tokens=180,
                store=False,
                text={"format": {"type": "text"}},
            )
            raw_text = _extract_response_text(response).strip()
            data = _load_json_object(raw_text)
            action_type = str(data.get("action_type") or fallback.action_type)
            if action_type not in SUPPORTED_CHAT_ACTIONS:
                action_type = fallback.action_type
            confidence = float(data.get("confidence") or fallback.confidence)
            return ChatActionDecision(
                action_type=action_type,
                confidence=confidence,
                rationale=str(data.get("rationale") or "llm inferred"),
                requires_confirmation=action_type in HIGH_RISK_CHAT_ACTIONS,
                degraded=False,
                raw=data,
            )
        except Exception:
            return fallback

    def stream_reply(
        self,
        *,
        content: str,
        context: dict[str, Any],
        decision: ChatActionDecision,
        action_result: dict[str, Any] | None = None,
    ) -> Iterable[str]:
        prompt = (
            "请用中文给本地 operator 一段简洁回复，说明你理解到的目标、当前动作、确认门或执行结果。"
            "不要声称已经执行未执行的高风险动作。\n"
            f"用户输入：{content}\n"
            f"动作：{decision.action_type}\n"
            f"上下文：{json.dumps(context, ensure_ascii=False)[:4000]}\n"
            f"动作结果：{json.dumps(action_result or {}, ensure_ascii=False)[:4000]}"
        )
        try:
            response_stream = self._client.responses.create(
                model=self.model,
                instructions="你是个人本地 workflow 的中文聊天驾驶舱助手。",
                input=prompt,
                reasoning={"effort": self.reasoning_effort},
                max_output_tokens=self.max_output_tokens,
                store=False,
                text={"format": {"type": "text"}},
                stream=True,
            )
            emitted = False
            for delta in _iter_response_text_deltas(response_stream):
                emitted = True
                yield delta
            if emitted:
                return
        except Exception:
            pass

        try:
            response = self._client.responses.create(
                model=self.model,
                instructions="你是个人本地 workflow 的中文聊天驾驶舱助手。",
                input=prompt,
                reasoning={"effort": self.reasoning_effort},
                max_output_tokens=self.max_output_tokens,
                store=False,
                text={"format": {"type": "text"}},
            )
            text = _extract_response_text(response).strip()
        except Exception:
            text = f"已识别动作为 `{decision.action_type}`，但 LLM 回复生成失败，已保留 workflow 状态。"
        yield from chunk_text(text)
