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
from packages.core_domain.errors import WorkerAdapterUnavailableError
from packages.worker_adapters.base import ExecutionResult, WorkerAdapter, resolve_artifact_paths, utc_now


DEFAULT_AGENT_MODEL = "gpt-5.4-mini"


@dataclass(slots=True)
class AgentExecutionResponse:
    content: str
    tool_call_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


AgentRunner = Callable[[TaskPacket, Any | None], AgentExecutionResponse]
MCPToolCaller = Callable[[str, dict[str, Any]], str]


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
        self.model = model or os.getenv("WORKFLOW_AGENT_MODEL", DEFAULT_AGENT_MODEL)
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

    def launch(self, packet: TaskPacket) -> ExecutionResult:
        started_at = utc_now()
        manifest = load_tool_projection_manifest(packet.env.get(TOOL_PROJECTION_MANIFEST_ENV_KEY))
        runner = self._runner or self._run_langchain_agent
        response = runner(packet, manifest)
        self._write_artifact(packet, response.content, manifest)
        finished_at = utc_now()
        return ExecutionResult(
            runtime_task_id=packet.runtime_task_id,
            return_code=0,
            stdout=response.content,
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
                **response.metadata,
            },
        )

    def _artifact_path_for(self, packet: TaskPacket) -> Path:
        artifact = packet.expected_artifacts[0] if packet.expected_artifacts else "state/artifacts/agent_output.md"
        path = Path(artifact)
        if not path.is_absolute():
            path = Path(packet.working_directory) / path
        return path.resolve()

    def _write_artifact(self, packet: TaskPacket, content: str, manifest: Any | None) -> None:
        artifact_path = self._artifact_path_for(packet)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        if not content.strip():
            tool_names = [item.tool_name for item in manifest.tools] if manifest is not None else []
            content = build_artifact_content(
                preset_id=packet.env.get("WORKFLOW_PRESET_ID", ""),
                goal=packet.env.get("WORKFLOW_RUN_GOAL", ""),
                adapter_name=self.normalized_name(),
                domain_pack_id=packet.env.get("WORKFLOW_DOMAIN_PACK_ID") or None,
                runtime_gateway=packet.env.get("WORKFLOW_RUNTIME_GATEWAY_PROVIDER") or None,
                runtime_model=self.model,
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

        model = ChatOpenAI(model=self.model)
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
            metadata={"agent_model": self.model},
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
        if isinstance(result, dict):
            messages = result.get("messages") or []
            for message in reversed(messages):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text" and item.get("text"):
                            parts.append(str(item["text"]))
                    if parts:
                        return "\n".join(parts)
        return ""
