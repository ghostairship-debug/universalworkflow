from __future__ import annotations

import os

from packages.core_domain.config import build_effective_config

from .base import ChatLLMRuntime, DegradedChatLLMRuntime
from .fallback import FallbackChatLLMRuntime
from .openai_compatible import DeepSeekChatLLMRuntime, MiniMaxChatLLMRuntime
from .openai_runtime import OpenAIChatLLMRuntime

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
