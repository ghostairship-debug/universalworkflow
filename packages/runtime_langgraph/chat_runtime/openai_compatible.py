from __future__ import annotations

import json
import os
from typing import Any, Iterable

from .actions import HIGH_RISK_CHAT_ACTIONS, SUPPORTED_CHAT_ACTIONS, ChatActionDecision, chunk_text, infer_rule_based_chat_action
from .base import ChatLLMRuntime
from .reasoning_filter import _iter_visible_text_deltas, _strip_reasoning_markup
from .response_utils import _coalesce_text_deltas, _extract_chat_completion_text, _iter_chat_completion_deltas, _load_json_object

class DeepSeekChatLLMRuntime(ChatLLMRuntime):
    def __init__(
        self,
        *,
        client: Any | None = None,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
        max_output_tokens: int = 480,
        provider_name: str = "deepseek",
        api_key_env: str = "DEEPSEEK_API_KEY",
        display_name: str = "DeepSeek",
        raise_on_reply_failure: bool = False,
        suppress_reasoning_markup: bool = False,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.max_output_tokens = max_output_tokens
        self.provider_name = provider_name
        self.api_key_env = api_key_env
        self.display_name = display_name
        self.raise_on_reply_failure = raise_on_reply_failure
        self.suppress_reasoning_markup = suppress_reasoning_markup
        if client is not None:
            self._client = client
            return
        from openai import OpenAI

        self._client = OpenAI(api_key=os.getenv(self.api_key_env), base_url=self.base_url)

    def describe(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "configured": True,
            "live": True,
            "model": self.model,
            "base_url": self.base_url,
        }

    def infer_action(self, content: str, context: dict[str, Any]) -> ChatActionDecision:
        fallback = infer_rule_based_chat_action(content)
        messages = [
            {
                "role": "system",
                "content": (
                    "你是本地个人 workflow 的聊天控制器。只输出紧凑 JSON，字段为 "
                    "action_type、confidence、rationale。不要执行动作，只分类。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"action_type 必须是以下之一：{sorted(SUPPORTED_CHAT_ACTIONS)}。\n"
                    "高风险动作只需要分类，后续由确认卡处理。\n"
                    f"当前上下文：{json.dumps(context, ensure_ascii=False)[:4000]}\n"
                    f"用户输入：{content}"
                ),
            },
        ]
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
                max_tokens=180,
                response_format={"type": "json_object"},
            )
            data = _load_json_object(_extract_chat_completion_text(response).strip())
            action_type = str(data.get("action_type") or fallback.action_type)
            if action_type not in SUPPORTED_CHAT_ACTIONS:
                action_type = fallback.action_type
            confidence = float(data.get("confidence") or fallback.confidence)
            return ChatActionDecision(
                action_type=action_type,
                confidence=confidence,
                rationale=str(data.get("rationale") or "deepseek inferred"),
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
        messages = [
            {
                "role": "system",
                "content": (
                    "你是个人本地 workflow 的中文聊天驾驶舱助手。解释目标、计划、确认门和执行结果；"
                    "不要声称已经执行未确认的高风险动作。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"用户输入：{content}\n"
                    f"动作：{decision.action_type}\n"
                    f"上下文：{json.dumps(context, ensure_ascii=False)[:4000]}\n"
                    f"动作结果：{json.dumps(action_result or {}, ensure_ascii=False)[:4000]}"
                ),
            },
        ]
        try:
            response_stream = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=self.max_output_tokens,
                stream=True,
            )
            emitted = False
            text_deltas = _iter_chat_completion_deltas(response_stream)
            if self.suppress_reasoning_markup:
                text_deltas = _iter_visible_text_deltas(text_deltas, suppress_leading_dangling_reasoning=True)
            for delta in _coalesce_text_deltas(text_deltas):
                emitted = True
                yield delta
            if emitted:
                return
        except Exception:
            if self.raise_on_reply_failure:
                raise

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=self.max_output_tokens,
            )
            text = _extract_chat_completion_text(response)
            if self.suppress_reasoning_markup:
                text = _strip_reasoning_markup(text)
            text = text.strip()
            if not text:
                raise ValueError(f"{self.display_name} returned no visible chat content")
        except Exception:
            if self.raise_on_reply_failure:
                raise
            text = f"已识别动作为 `{decision.action_type}`，但 {self.display_name} 回复生成失败，已保留 workflow 状态。"
        yield from chunk_text(text)


class MiniMaxChatLLMRuntime(DeepSeekChatLLMRuntime):
    def __init__(
        self,
        *,
        client: Any | None = None,
        model: str = "MiniMax-M2.7",
        base_url: str = "https://api.minimaxi.com/v1",
        max_output_tokens: int = 480,
        raise_on_reply_failure: bool = False,
    ) -> None:
        super().__init__(
            client=client,
            model=model,
            base_url=base_url,
            max_output_tokens=max_output_tokens,
            provider_name="minimax",
            api_key_env="MINIMAX_API_KEY",
            display_name="MiniMax",
            raise_on_reply_failure=raise_on_reply_failure,
            suppress_reasoning_markup=True,
        )
