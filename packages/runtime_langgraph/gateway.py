from __future__ import annotations

import os
from typing import Any

from packages.contracts.runtime import RuntimeGateway, RuntimeStateRef
from packages.core_domain.config import build_effective_config
from packages.core_domain.context_budget import (
    DEFAULT_CONTEXT_HARD_LIMIT_CHARS,
    DEFAULT_CONTEXT_WARN_CHARS,
    build_context_budget_report,
)
from packages.core_domain.errors import RuntimeGatewayConfigurationError, RuntimeGatewayExecutionError


DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
DEFAULT_OPENAI_REASONING_EFFORT = "low"


class NullRuntimeGateway(RuntimeGateway):
    def describe(self) -> dict[str, Any]:
        return {
            "provider": "null",
            "configured": False,
            "live": False,
            "model": None,
            "reasoning_effort": None,
        }

    def start(self, run_id: str, runtime_task_id: str) -> RuntimeStateRef:
        return RuntimeStateRef(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            graph_step="compiled",
            state_payload={
                "entrypoint": "resume",
                "runtime_gateway_provider": "null",
                "llm_enabled": False,
            },
        )

    def resume(self, state_ref: RuntimeStateRef) -> RuntimeStateRef:
        return RuntimeStateRef(
            state_ref_id=state_ref.state_ref_id,
            run_id=state_ref.run_id,
            runtime_task_id=state_ref.runtime_task_id,
            graph_step="resuming",
            state_payload={
                **state_ref.state_payload,
                "resumed_from": state_ref.graph_step,
                "runtime_gateway_provider": "null",
                "llm_enabled": False,
            },
            is_terminal=state_ref.is_terminal,
            created_at=state_ref.created_at,
        )


class OpenAIRuntimeGateway(RuntimeGateway):
    def __init__(
        self,
        *,
        client: Any | None = None,
        model: str = DEFAULT_OPENAI_MODEL,
        reasoning_effort: str = DEFAULT_OPENAI_REASONING_EFFORT,
        max_output_tokens: int = 160,
        warn_input_chars: int = DEFAULT_CONTEXT_WARN_CHARS,
        max_input_chars: int = DEFAULT_CONTEXT_HARD_LIMIT_CHARS,
    ):
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.max_output_tokens = max_output_tokens
        self.warn_input_chars = warn_input_chars
        self.max_input_chars = max_input_chars

        if client is not None:
            self._client = client
            return

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeGatewayConfigurationError(
                "openai runtime gateway requires OPENAI_API_KEY",
                {"provider": "openai"},
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeGatewayConfigurationError(
                "openai runtime gateway requires the openai package",
                {"provider": "openai"},
            ) from exc
        self._client = OpenAI(api_key=api_key)

    def describe(self) -> dict[str, Any]:
        return {
            "provider": "openai",
            "configured": True,
            "live": True,
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "context_budget_warn_chars": self.warn_input_chars,
            "context_budget_hard_limit_chars": self.max_input_chars,
        }

    def copy_with(
        self,
        *,
        model: str | None = None,
        reasoning_effort: str | None = None,
    ) -> "OpenAIRuntimeGateway":
        return OpenAIRuntimeGateway(
            client=self._client,
            model=model or self.model,
            reasoning_effort=reasoning_effort or self.reasoning_effort,
            max_output_tokens=self.max_output_tokens,
            warn_input_chars=self.warn_input_chars,
            max_input_chars=self.max_input_chars,
        )

    def start(self, run_id: str, runtime_task_id: str) -> RuntimeStateRef:
        return RuntimeStateRef(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            graph_step="compiled",
            state_payload={
                "entrypoint": "resume",
                "runtime_gateway_provider": "openai",
                "llm_enabled": True,
                "llm_model": self.model,
                "llm_reasoning_effort": self.reasoning_effort,
            },
        )

    def resume(self, state_ref: RuntimeStateRef) -> RuntimeStateRef:
        prompt = self._build_brief_prompt(state_ref)
        context_budget = build_context_budget_report(
            state_ref.state_payload,
            prompt_text=prompt,
            warn_limit_chars=self.warn_input_chars,
            hard_limit_chars=self.max_input_chars,
        )
        if context_budget["over_budget"]:
            raise RuntimeGatewayExecutionError(
                "runtime brief prompt exceeds the configured context budget",
                {
                    "provider": "openai",
                    "model": self.model,
                    "context_budget": context_budget,
                },
            )
        try:
            response = self._client.responses.create(
                model=self.model,
                instructions=(
                    "You are preparing a short execution brief for a local workflow runtime. "
                    "Return plain text in at most three short lines using the labels Outcome, Risk, and Check."
                ),
                input=prompt,
                reasoning={"effort": self.reasoning_effort},
                max_output_tokens=self.max_output_tokens,
                store=False,
                text={"format": {"type": "text"}},
            )
        except Exception as exc:
            raise RuntimeGatewayExecutionError(
                "openai runtime gateway failed to create an execution brief",
                {"provider": "openai", "model": self.model},
            ) from exc

        output_text = self._extract_output_text(response).strip()
        runtime_brief = " ".join(output_text.split()) if output_text else None
        return RuntimeStateRef(
            state_ref_id=state_ref.state_ref_id,
            run_id=state_ref.run_id,
            runtime_task_id=state_ref.runtime_task_id,
            graph_step="resuming",
            state_payload={
                **state_ref.state_payload,
                "resumed_from": state_ref.graph_step,
                "runtime_gateway_provider": "openai",
                "llm_enabled": True,
                "llm_model": self.model,
                "llm_reasoning_effort": self.reasoning_effort,
                "runtime_brief": runtime_brief,
                "llm_response_id": getattr(response, "id", None),
                "context_budget": context_budget,
            },
            is_terminal=state_ref.is_terminal,
            created_at=state_ref.created_at,
        )

    def _build_brief_prompt(self, state_ref: RuntimeStateRef) -> str:
        payload = state_ref.state_payload
        expected_artifacts = payload.get("expected_artifacts") or []
        return (
            "Prepare a short execution brief for the following local workflow run.\n"
            f"goal: {payload.get('goal', '')}\n"
            f"preset_id: {payload.get('preset_id', '')}\n"
            f"task_kind: {payload.get('task_kind', '')}\n"
            f"domain_pack_id: {payload.get('domain_pack_id', '')}\n"
            f"capability_adapter: {payload.get('capability_adapter', '')}\n"
            f"expected_artifacts: {', '.join(str(item) for item in expected_artifacts)}\n"
            "Return at most three short lines:\n"
            "Outcome: <expected artifact/result>\n"
            "Risk: <main execution risk>\n"
            "Check: <one verification step>"
        )

    def _extract_output_text(self, response: Any) -> str:
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


def build_runtime_gateway_from_env(
    *,
    explicit_provider: str | None = None,
    explicit_model: str | None = None,
    explicit_reasoning_effort: str | None = None,
) -> RuntimeGateway:
    effective = build_effective_config(explicit_runtime_gateway_provider=explicit_provider)
    provider = str(explicit_provider or effective["runtime_gateway"]["provider"]).strip().lower()
    if provider in {"", "null", "none", "disabled"}:
        return NullRuntimeGateway()
    if provider == "openai":
        return OpenAIRuntimeGateway(
            model=str(explicit_model or effective["runtime_gateway"]["openai_model"] or DEFAULT_OPENAI_MODEL),
            reasoning_effort=str(
                explicit_reasoning_effort
                or effective["runtime_gateway"]["openai_reasoning_effort"]
                or DEFAULT_OPENAI_REASONING_EFFORT
            ),
        )
    raise RuntimeGatewayConfigurationError(
        f"unsupported runtime gateway provider: {provider}",
        {"provider": provider, "available_providers": ["null", "openai"]},
    )


def resolve_runtime_gateway(
    base_gateway: RuntimeGateway,
    *,
    provider: str | None = None,
    model: str | None = None,
    reasoning_effort: str | None = None,
) -> RuntimeGateway:
    base_description = base_gateway.describe()
    requested_provider = str(provider or base_description.get("provider") or "null").strip().lower()
    base_provider = str(base_description.get("provider") or "null").strip().lower()
    if requested_provider == base_provider:
        if requested_provider == "openai" and isinstance(base_gateway, OpenAIRuntimeGateway):
            requested_model = model or base_gateway.model
            requested_reasoning = reasoning_effort or base_gateway.reasoning_effort
            if requested_model != base_gateway.model or requested_reasoning != base_gateway.reasoning_effort:
                return base_gateway.copy_with(
                    model=requested_model,
                    reasoning_effort=requested_reasoning,
                )
        return base_gateway
    return build_runtime_gateway_from_env(
        explicit_provider=requested_provider,
        explicit_model=model,
        explicit_reasoning_effort=reasoning_effort,
    )
