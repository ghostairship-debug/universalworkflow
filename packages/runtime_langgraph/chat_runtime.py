from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Iterable

from packages.core_domain.config import build_effective_config


SUPPORTED_CHAT_ACTIONS = {
    "answer_only",
    "plan_preview",
    "launch_prepare",
    "launch_execute",
    "resume_run",
    "approve_run",
    "reject_run",
    "cancel_run",
    "summarize_run",
    "diagnose_failure",
    "pr_ready_summary",
    "create_followup",
}

HIGH_RISK_CHAT_ACTIONS = {
    "launch_execute",
    "resume_run",
    "approve_run",
    "reject_run",
    "cancel_run",
    "repo_mutation",
    "git_commit",
    "git_push",
    "github_pr",
}


@dataclass(frozen=True)
class ChatActionDecision:
    action_type: str = "answer_only"
    confidence: float = 0.0
    rationale: str = ""
    requires_confirmation: bool = False
    degraded: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


def _contains_any(value: str, markers: set[str]) -> bool:
    normalized = value.strip().lower()
    return any(marker in normalized for marker in markers)


def infer_rule_based_chat_action(content: str) -> ChatActionDecision:
    normalized = content.strip().lower()
    action_type = "answer_only"
    if _contains_any(normalized, {"通过", "同意", "approve"}):
        action_type = "approve_run"
    elif _contains_any(normalized, {"拒绝", "驳回", "reject"}):
        action_type = "reject_run"
    elif _contains_any(normalized, {"取消", "停止", "终止", "cancel"}):
        action_type = "cancel_run"
    elif _contains_any(normalized, {"继续", "执行下一步", "resume", "continue"}):
        action_type = "resume_run"
    elif _contains_any(normalized, {"并执行", "直接执行", "execute"}):
        action_type = "launch_execute"
    elif _contains_any(normalized, {"启动", "开始", "launch", "start"}):
        action_type = "launch_prepare"
    elif _contains_any(normalized, {"pr summary", "pr-ready", "pr 摘要", "pr摘要", "pr 总结"}):
        action_type = "pr_ready_summary"
    elif _contains_any(normalized, {"排查失败", "失败原因", "diagnose", "failure"}):
        action_type = "diagnose_failure"
    elif _contains_any(normalized, {"总结", "状态", "summary", "status"}):
        action_type = "summarize_run"
    elif _contains_any(normalized, {"follow-up", "followup", "后续", "待办", "加入"}):
        action_type = "create_followup"
    elif _contains_any(normalized, {"预览", "计划", "plan"}):
        action_type = "plan_preview"
    return ChatActionDecision(
        action_type=action_type,
        confidence=0.72 if action_type != "answer_only" else 0.45,
        rationale="rule-based fallback",
        requires_confirmation=action_type in HIGH_RISK_CHAT_ACTIONS,
        degraded=True,
    )


def chunk_text(text: str, *, chunk_size: int = 28) -> list[str]:
    clean = text or ""
    if not clean:
        return []
    return [clean[index : index + chunk_size] for index in range(0, len(clean), chunk_size)]


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


def _load_json_object(raw_text: str) -> dict[str, Any]:
    try:
        loaded = json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start < 0 or end <= start:
            raise
        loaded = json.loads(raw_text[start : end + 1])
    if not isinstance(loaded, dict):
        raise ValueError("chat action response must be a JSON object")
    return loaded


def _iter_response_text_deltas(response_stream: Any) -> Iterable[str]:
    for event in response_stream:
        event_type = str(getattr(event, "type", ""))
        delta = getattr(event, "delta", None)
        if delta is None and hasattr(event, "model_dump"):
            data = event.model_dump(mode="json")
            event_type = str(data.get("type", event_type))
            delta = data.get("delta")
        if event_type == "response.output_text.delta" and delta:
            yield str(delta)


def _extract_chat_completion_text(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if content:
            return str(content)
    if hasattr(response, "model_dump"):
        data = response.model_dump(mode="json")
        for choice in data.get("choices", []):
            message = choice.get("message", {})
            content = message.get("content")
            if content:
                return str(content)
    if isinstance(response, dict):
        for choice in response.get("choices", []):
            message = choice.get("message", {})
            content = message.get("content")
            if content:
                return str(content)
    return ""


def _iter_chat_completion_deltas(response_stream: Any) -> Iterable[str]:
    for event in response_stream:
        choices = getattr(event, "choices", None) or []
        yielded_from_attributes = False
        for choice in choices:
            delta = getattr(choice, "delta", None)
            content = getattr(delta, "content", None)
            if content:
                yielded_from_attributes = True
                yield str(content)
        if yielded_from_attributes:
            continue
        if hasattr(event, "model_dump"):
            data = event.model_dump(mode="json")
            for choice in data.get("choices", []):
                content = choice.get("delta", {}).get("content")
                if content:
                    yield str(content)
        elif isinstance(event, dict):
            for choice in event.get("choices", []):
                content = choice.get("delta", {}).get("content")
                if content:
                    yield str(content)


def _coalesce_text_deltas(deltas: Iterable[str], *, min_chars: int = 18) -> Iterable[str]:
    buffer = ""
    for delta in deltas:
        buffer += delta
        if len(buffer) >= min_chars or buffer.endswith(("\n", "。", "！", "？", ".", "!", "?")):
            yield buffer
            buffer = ""
    if buffer:
        yield buffer


_REASONING_OPEN_TAG = "<think"
_REASONING_CLOSE_TAG = "</think>"


def _strip_reasoning_markup(text: str) -> str:
    remaining = text or ""
    visible: list[str] = []
    while remaining:
        lower = remaining.lower()
        start = lower.find(_REASONING_OPEN_TAG)
        dangling_close = lower.find(_REASONING_CLOSE_TAG)
        if dangling_close >= 0 and (start < 0 or dangling_close < start):
            remaining = remaining[dangling_close + len(_REASONING_CLOSE_TAG) :]
            continue
        if start < 0:
            visible.append(remaining)
            break
        visible.append(remaining[:start])
        tag_end = lower.find(">", start)
        if tag_end < 0:
            break
        close_start = lower.find(_REASONING_CLOSE_TAG, tag_end + 1)
        if close_start < 0:
            break
        remaining = remaining[close_start + len(_REASONING_CLOSE_TAG) :]
    return "".join(visible).strip()


def _reasoning_open_tag_prefix_length(text: str) -> int:
    lower = text.lower()
    max_prefix = min(len(lower), len(_REASONING_OPEN_TAG))
    for size in range(max_prefix, 0, -1):
        if _REASONING_OPEN_TAG.startswith(lower[-size:]):
            return size
    return 0


def _iter_visible_text_deltas(
    deltas: Iterable[str],
    *,
    suppress_leading_dangling_reasoning: bool = False,
) -> Iterable[str]:
    pending = ""
    suppressing_reasoning = False
    emitted_visible = False
    for delta in deltas:
        pending += delta
        while pending:
            lower = pending.lower()
            if suppressing_reasoning:
                close_start = lower.find(_REASONING_CLOSE_TAG)
                if close_start < 0:
                    pending = pending[-(len(_REASONING_CLOSE_TAG) - 1) :]
                    break
                pending = pending[close_start + len(_REASONING_CLOSE_TAG) :]
                suppressing_reasoning = False
                continue

            open_start = lower.find(_REASONING_OPEN_TAG)
            dangling_close = lower.find(_REASONING_CLOSE_TAG)
            if dangling_close >= 0 and (open_start < 0 or dangling_close < open_start):
                pending = pending[dangling_close + len(_REASONING_CLOSE_TAG) :]
                suppress_leading_dangling_reasoning = False
                continue
            if suppress_leading_dangling_reasoning and not emitted_visible and open_start < 0:
                break
            if open_start < 0:
                keep = _reasoning_open_tag_prefix_length(pending)
                visible = pending[:-keep] if keep else pending
                if visible:
                    emitted_visible = True
                    yield visible
                pending = pending[-keep:] if keep else ""
                break

            visible = pending[:open_start]
            if visible:
                emitted_visible = True
                yield visible
            tag_end = lower.find(">", open_start)
            if tag_end < 0:
                pending = pending[open_start:]
                break
            pending = pending[tag_end + 1 :]
            suppressing_reasoning = True

    if pending and not suppressing_reasoning:
        visible = _strip_reasoning_markup(pending)
        if visible:
            emitted_visible = True
            yield visible


def _extract_response_text(response: Any) -> str:
    helper_text = getattr(response, "output_text", None)
    if helper_text:
        return str(helper_text)
    output = getattr(response, "output", None) or []
    parts: list[str] = []
    for item in output:
        content = getattr(item, "content", None) or []
        for part in content:
            if getattr(part, "type", None) == "output_text":
                text = getattr(part, "text", None)
                if text:
                    parts.append(str(text))
    if parts:
        return "\n".join(parts)
    if hasattr(response, "model_dump"):
        data = response.model_dump(mode="json")
        return str(data.get("output_text", ""))
    return ""


def _minimax_base_url_from_env() -> str:
    explicit_base_url = os.getenv("MINIMAX_BASE_URL")
    if explicit_base_url:
        return explicit_base_url.rstrip("/")
    api_host = os.getenv("MINIMAX_API_HOST")
    if api_host:
        host = api_host.rstrip("/")
        return host if host.endswith("/v1") else f"{host}/v1"
    return "https://api.minimaxi.com/v1"


def build_chat_llm_runtime_from_env() -> ChatLLMRuntime:
    effective = build_effective_config()
    provider = str(os.getenv("WORKFLOW_CHAT_LLM_PROVIDER") or effective["runtime_gateway"]["provider"] or "").strip().lower()
    chat_model = os.getenv("WORKFLOW_CHAT_LLM_MODEL")
    minimax_api_key = os.getenv("MINIMAX_API_KEY")
    if (provider in {"", "auto", "null", "minimax"} and minimax_api_key) or provider == "minimax":
        if not minimax_api_key:
            return DegradedChatLLMRuntime()
        try:
            primary = MiniMaxChatLLMRuntime(
                model=str(chat_model or os.getenv("WORKFLOW_MINIMAX_MODEL") or "MiniMax-M2.7"),
                base_url=_minimax_base_url_from_env(),
                raise_on_reply_failure=bool(os.getenv("DEEPSEEK_API_KEY")),
            )
            if os.getenv("DEEPSEEK_API_KEY"):
                fallback = DeepSeekChatLLMRuntime(
                    model=str(os.getenv("WORKFLOW_DEEPSEEK_MODEL") or "deepseek-v4-flash"),
                    base_url=str(os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"),
                )
                return FallbackChatLLMRuntime(primary=primary, fallback=fallback)
            return primary
        except Exception:
            return DegradedChatLLMRuntime()
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    if (provider in {"", "auto", "null", "deepseek"} and deepseek_api_key) or provider == "deepseek":
        if not deepseek_api_key:
            return DegradedChatLLMRuntime()
        try:
            return DeepSeekChatLLMRuntime(
                model=str(chat_model or os.getenv("WORKFLOW_DEEPSEEK_MODEL") or "deepseek-v4-flash"),
                base_url=str(os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"),
            )
        except Exception:
            return DegradedChatLLMRuntime()
    api_key = os.getenv("OPENAI_API_KEY")
    if provider == "openai" and api_key:
        try:
            return OpenAIChatLLMRuntime(
                model=str(chat_model or effective["runtime_gateway"]["openai_model"] or "gpt-5.4-mini"),
                reasoning_effort=str(effective["runtime_gateway"]["openai_reasoning_effort"] or "low"),
            )
        except Exception:
            return DegradedChatLLMRuntime()
    return DegradedChatLLMRuntime()
