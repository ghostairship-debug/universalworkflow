from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from packages.contracts import CapabilitySourceType, TaskKind, TaskPacket
from packages.core_domain.agent_tools import (
    list_workspace_files,
    read_execution_brief,
    read_workspace_text,
)
from packages.core_domain.capability_plane import TOOL_PROJECTION_MANIFEST_ENV_KEY, load_tool_projection_manifest
from packages.core_domain.compile import build_artifact_content
from packages.core_domain.config import build_effective_config
from packages.core_domain.errors import WorkerAdapterUnavailableError
from packages.worker_adapters.base import ExecutionResult, WorkerAdapter, resolve_artifact_paths, utc_now


DEFAULT_AGENT_MODEL = "gpt-5.4-mini"
DEFAULT_LANGCHAIN_AGENT_PROVIDER = "auto"
DEFAULT_MINIMAX_MODEL = "MiniMax-M2.7"
DEFAULT_MINIMAX_BASE_URL = "https://api.minimaxi.com/v1"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


@dataclass(slots=True)
class AgentExecutionResponse:
    content: str
    tool_call_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LangChainAgentLLMSelection:
    provider: str
    model: str | None
    base_url: str | None
    api_key_env: str | None
    fallback_provider: str | None = None
    fallback_model: str | None = None
    fallback_base_url: str | None = None
    fallback_api_key_env: str | None = None
    degraded_reason: str | None = None


AgentRunner = Callable[[TaskPacket, Any | None], AgentExecutionResponse]
MCPToolCaller = Callable[[str, dict[str, Any]], str]


def _present_env(env: dict[str, str], names: list[str]) -> str | None:
    for name in names:
        if env.get(name):
            return name
    return None


def _minimax_base_url_from_env(env: dict[str, str], configured_base_url: str | None) -> str:
    if configured_base_url:
        return configured_base_url.rstrip("/")
    if env.get("MINIMAX_BASE_URL"):
        return str(env["MINIMAX_BASE_URL"]).rstrip("/")
    api_host = env.get("MINIMAX_API_HOST")
    if api_host:
        host = str(api_host).rstrip("/")
        return host if host.endswith("/v1") else f"{host}/v1"
    return DEFAULT_MINIMAX_BASE_URL


def resolve_langchain_agent_llm_selection(
    *,
    effective_config: dict[str, Any] | None = None,
    env: dict[str, str] | None = None,
) -> LangChainAgentLLMSelection:
    environment = dict(env or os.environ)
    effective = effective_config or build_effective_config()
    langchain_config = effective.get("langchain_agent") or {}
    provider = str(
        environment.get("WORKFLOW_LANGCHAIN_AGENT_PROVIDER")
        or langchain_config.get("provider")
        or DEFAULT_LANGCHAIN_AGENT_PROVIDER
    ).strip().lower()
    configured_model = environment.get("WORKFLOW_LANGCHAIN_AGENT_MODEL") or langchain_config.get("model")
    configured_base_url = environment.get("WORKFLOW_LANGCHAIN_AGENT_BASE_URL") or langchain_config.get("base_url")
    provider_order = ["minimax", "deepseek", "openai"] if provider in {"", "auto", "null"} else [provider]

    selections: list[LangChainAgentLLMSelection] = []
    for candidate in provider_order:
        if candidate == "minimax":
            key_env = _present_env(environment, ["MINIMAX_API_KEY", "MINIMAX_TOKEN"])
            selections.append(
                LangChainAgentLLMSelection(
                    provider="minimax",
                    model=str(configured_model or environment.get("WORKFLOW_MINIMAX_MODEL") or DEFAULT_MINIMAX_MODEL),
                    base_url=_minimax_base_url_from_env(environment, str(configured_base_url) if configured_base_url else None),
                    api_key_env=key_env,
                    degraded_reason=None if key_env else "missing MINIMAX_API_KEY or MINIMAX_TOKEN",
                )
            )
        elif candidate == "deepseek":
            key_env = _present_env(environment, ["DEEPSEEK_API_KEY"])
            selections.append(
                LangChainAgentLLMSelection(
                    provider="deepseek",
                    model=str(configured_model or environment.get("WORKFLOW_DEEPSEEK_MODEL") or DEFAULT_DEEPSEEK_MODEL),
                    base_url=str(configured_base_url or environment.get("DEEPSEEK_BASE_URL") or DEFAULT_DEEPSEEK_BASE_URL).rstrip("/"),
                    api_key_env=key_env,
                    degraded_reason=None if key_env else "missing DEEPSEEK_API_KEY",
                )
            )
        elif candidate == "openai":
            key_env = _present_env(environment, ["OPENAI_API_KEY"])
            selections.append(
                LangChainAgentLLMSelection(
                    provider="openai",
                    model=str(configured_model or environment.get("WORKFLOW_AGENT_MODEL") or effective["agent"]["model"] or DEFAULT_AGENT_MODEL),
                    base_url=str(configured_base_url).rstrip("/") if configured_base_url else None,
                    api_key_env=key_env,
                    degraded_reason=None if key_env else "missing OPENAI_API_KEY",
                )
            )

    ready = [item for item in selections if item.api_key_env]
    if not ready:
        reason = "; ".join(item.degraded_reason or f"{item.provider} unavailable" for item in selections)
        return LangChainAgentLLMSelection(
            provider=provider or "auto",
            model=str(configured_model) if configured_model else None,
            base_url=str(configured_base_url).rstrip("/") if configured_base_url else None,
            api_key_env=None,
            degraded_reason=reason or "no LangChain agent provider configured",
        )

    primary = ready[0]
    fallback = next((item for item in ready[1:] if item.provider != primary.provider), None)
    if fallback is not None:
        primary.fallback_provider = fallback.provider
        primary.fallback_model = fallback.model
        primary.fallback_base_url = fallback.base_url
        primary.fallback_api_key_env = fallback.api_key_env
    return primary


def describe_langchain_agent_llm(
    *,
    effective_config: dict[str, Any] | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    selection = resolve_langchain_agent_llm_selection(effective_config=effective_config, env=env)
    return {
        "status": "ready" if selection.api_key_env else "missing_auth",
        "provider": selection.provider,
        "model": selection.model,
        "base_url": selection.base_url,
        "auth": selection.api_key_env,
        "fallback_provider": selection.fallback_provider,
        "fallback_model": selection.fallback_model,
        "degraded_reason": selection.degraded_reason,
    }


class LangChainAgentAdapter(WorkerAdapter):
    adapter_name = "agent"
    route_priority = 90

    def __init__(
        self,
        *,
        model: str | None = None,
        runner: AgentRunner | None = None,
        mcp_tool_caller: MCPToolCaller | None = None,
    ):
        configured_model = build_effective_config()["agent"]["model"]
        self.model = model or str(configured_model or os.getenv("WORKFLOW_AGENT_MODEL", DEFAULT_AGENT_MODEL))
        self._runner = runner
        self._mcp_tool_caller = mcp_tool_caller

    def get_capabilities(self) -> list[str]:
        return [str(TaskKind.shell_exec)]

    def estimate_cost(self, packet: TaskPacket) -> dict[str, int]:
        manifest = load_tool_projection_manifest(packet.env.get(TOOL_PROJECTION_MANIFEST_ENV_KEY))
        return {
            "projected_tool_count": len(manifest.tools) if manifest is not None else 0,
            "timeout_seconds": 120,
        }

    def collect_artifacts(self, packet: TaskPacket) -> list[str]:
        return resolve_artifact_paths(packet, create_missing=False)

    def _model_for_packet(self, packet: TaskPacket) -> str:
        selection = resolve_langchain_agent_llm_selection(
            effective_config=build_effective_config(),
            env={**os.environ, **{key: value for key, value in packet.env.items() if value}},
        )
        return str(selection.model or packet.env.get("WORKFLOW_AGENT_MODEL") or self.model)

    def _chat_model_kwargs(self, selection: LangChainAgentLLMSelection) -> dict[str, Any]:
        if not selection.api_key_env:
            raise WorkerAdapterUnavailableError(
                self.normalized_name(),
                "LangChain agent lane has no configured MiniMax, DeepSeek, or OpenAI API key",
                {
                    "provider": selection.provider,
                    "selected_model": selection.model,
                    "degraded_reason": selection.degraded_reason,
                },
            )
        kwargs = {
            "model": selection.model,
            "api_key": os.getenv(selection.api_key_env),
        }
        if selection.base_url:
            kwargs["base_url"] = selection.base_url
        return kwargs

    def _build_chat_model(self, ChatOpenAI: Any, selection: LangChainAgentLLMSelection):
        primary = ChatOpenAI(**self._chat_model_kwargs(selection))
        if selection.fallback_provider and selection.fallback_api_key_env:
            fallback = LangChainAgentLLMSelection(
                provider=selection.fallback_provider,
                model=selection.fallback_model,
                base_url=selection.fallback_base_url,
                api_key_env=selection.fallback_api_key_env,
            )
            fallback_model = ChatOpenAI(**self._chat_model_kwargs(fallback))
            if hasattr(primary, "with_fallbacks"):
                return primary.with_fallbacks([fallback_model])
        return primary

    def launch(self, packet: TaskPacket) -> ExecutionResult:
        started_at = utc_now()
        manifest = load_tool_projection_manifest(packet.env.get(TOOL_PROJECTION_MANIFEST_ENV_KEY))
        runner = self._runner or self._run_langchain_agent
        response = runner(packet, manifest)
        content = response.content or ""
        self._write_artifact(packet, content, manifest)
        finished_at = utc_now()
        return ExecutionResult(
            runtime_task_id=packet.runtime_task_id,
            return_code=0,
            stdout=content,
            stderr="",
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=max(int((finished_at - started_at).total_seconds() * 1000), 0),
            artifact_paths=self.collect_artifacts(packet),
            adapter_name=self.normalized_name(),
            metadata={
                "execution_lane": packet.env.get("WORKFLOW_EXECUTION_LANE"),
                "projection_id": manifest.projection_id if manifest is not None else None,
                "tool_names": [item.tool_name for item in manifest.tools] if manifest is not None else [],
                "tool_call_ids": response.tool_call_ids,
                "agent_model": self._model_for_packet(packet),
                **response.metadata,
            },
        )

    def _artifact_path_for(self, packet: TaskPacket) -> Path:
        artifact = packet.expected_artifacts[0] if packet.expected_artifacts else "state/artifacts/agent_output.md"
        path = Path(artifact)
        if not path.is_absolute():
            path = Path(packet.working_directory) / path
        return path.resolve()

    def _write_artifact(self, packet: TaskPacket, content: str | None, manifest: Any | None) -> None:
        artifact_path = self._artifact_path_for(packet)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        content = content or ""
        if not content.strip():
            tool_names = [item.tool_name for item in manifest.tools] if manifest is not None else []
            content = build_artifact_content(
                preset_id=packet.env.get("WORKFLOW_PRESET_ID", ""),
                goal=packet.env.get("WORKFLOW_RUN_GOAL", ""),
                adapter_name=self.normalized_name(),
                domain_pack_id=packet.env.get("WORKFLOW_DOMAIN_PACK_ID") or None,
                runtime_gateway=packet.env.get("WORKFLOW_RUNTIME_GATEWAY_PROVIDER") or None,
                runtime_model=self._model_for_packet(packet),
                runtime_brief=packet.env.get("WORKFLOW_RUNTIME_BRIEF") or None,
                execution_lane=packet.env.get("WORKFLOW_EXECUTION_LANE"),
                projected_tools=tool_names,
            )
        artifact_path.write_text(content, encoding="utf-8")

    def _run_langchain_agent(self, packet: TaskPacket, manifest: Any | None) -> AgentExecutionResponse:
        try:
            from langchain.agents import create_agent
            from langchain_core.tools import StructuredTool
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise WorkerAdapterUnavailableError(
                self.normalized_name(),
                "langchain agent lane requires langchain, langchain-openai, and langgraph dependencies",
            ) from exc

        tools = []
        for entry in manifest.tools if manifest is not None else []:
            if entry.source_type == CapabilitySourceType.built_in:
                tools.append(self._built_in_langchain_tool(StructuredTool, packet, entry.tool_name))
            elif self._mcp_tool_caller is not None:
                tools.append(self._mcp_langchain_tool(StructuredTool, entry.tool_name))

        packet_env = {**os.environ, **{key: value for key, value in packet.env.items() if value}}
        selection = resolve_langchain_agent_llm_selection(
            effective_config=build_effective_config(),
            env=packet_env,
        )
        selected_model = str(selection.model or self._model_for_packet(packet))
        try:
            model = self._build_chat_model(ChatOpenAI, selection)
        except WorkerAdapterUnavailableError:
            raise
        except Exception as exc:
            raise WorkerAdapterUnavailableError(
                self.normalized_name(),
                "agent lane could not initialize LangChain ChatOpenAI-compatible provider",
                {
                    "provider": selection.provider,
                    "selected_model": selected_model,
                    "fallback_provider": selection.fallback_provider,
                    "degraded_reason": selection.degraded_reason,
                },
            ) from exc
        system_prompt = (
            "You are running inside a local workflow control plane. "
            "Use only the provided read-only tools when they help. "
            "Return plain text only and keep the final response concise."
        )
        prompt = (
            f"Goal: {packet.env.get('WORKFLOW_RUN_GOAL', '')}\n"
            f"Preset: {packet.env.get('WORKFLOW_PRESET_ID', '')}\n"
            f"Task kind: {packet.env.get('WORKFLOW_TASK_KIND', '')}\n"
            f"Execution lane: {packet.env.get('WORKFLOW_EXECUTION_LANE', '')}\n"
            f"Runtime brief: {packet.env.get('WORKFLOW_RUNTIME_BRIEF', '')}\n"
            "Produce a short markdown artifact summarizing the intended outcome, risks, and next checks."
        )
        agent = create_agent(model=model, tools=tools, system_prompt=system_prompt)
        result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        content = self._extract_content(result)
        return AgentExecutionResponse(
            content=content,
            metadata={
                "agent_model": selected_model,
                "langchain_agent_provider": selection.provider,
                "langchain_agent_model": selected_model,
                "langchain_agent_fallback_provider": selection.fallback_provider,
                "langchain_agent_fallback_model": selection.fallback_model,
            },
        )

    def _built_in_langchain_tool(self, structured_tool: Any, packet: TaskPacket, tool_name: str):
        if tool_name == "list_workspace_files":
            def _tool(limit: int = 50) -> list[str]:
                return list_workspace_files(packet.working_directory, limit=limit)

            return structured_tool.from_function(
                _tool,
                name=tool_name,
                description="List files under the current working directory.",
            )
        if tool_name == "read_workspace_text":
            def _tool(relative_path: str, max_chars: int = 8000) -> str:
                return read_workspace_text(packet.working_directory, relative_path, max_chars=max_chars)

            return structured_tool.from_function(
                _tool,
                name=tool_name,
                description="Read a UTF-8 text file under the current working directory.",
            )

        def _tool() -> dict[str, str | None]:
            return read_execution_brief(packet.env)

        return structured_tool.from_function(
            _tool,
            name=tool_name,
            description="Read the current execution brief and workflow metadata.",
        )

    def _mcp_langchain_tool(self, structured_tool: Any, tool_name: str):
        def _tool(**kwargs: Any) -> str:
            if self._mcp_tool_caller is None:
                raise RuntimeError("MCP tool caller is not configured")
            return self._mcp_tool_caller(tool_name, kwargs)

        return structured_tool.from_function(
            _tool,
            name=tool_name,
            description=f"Invoke projected MCP tool `{tool_name}`.",
        )

    def _extract_content(self, result: Any) -> str:
        if isinstance(result, str):
            return result
        messages = []
        if isinstance(result, dict):
            messages = result.get("messages") or []
        elif hasattr(result, "messages"):
            messages = getattr(result, "messages") or []
        for message in reversed(messages):
            content = message.get("content") if isinstance(message, dict) else getattr(message, "content", None)
            extracted = self._extract_text_content(content)
            if extracted:
                return extracted
        return ""

    def _extract_text_content(self, content: Any) -> str:
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                item_type = item.get("type") if isinstance(item, dict) else getattr(item, "type", None)
                item_text = item.get("text") if isinstance(item, dict) else getattr(item, "text", None)
                if item_type == "text" and item_text:
                    parts.append(str(item_text))
            if parts:
                return "\n".join(parts)
        return ""
