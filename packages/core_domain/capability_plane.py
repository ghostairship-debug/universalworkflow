from __future__ import annotations

import hashlib
import json
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import anyio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from packages.contracts import (
    CapabilitySourceType,
    ExecutionLaneType,
    MCPServerProfile,
    MCPTransport,
    ReviewPolicy,
    TaskKind,
    ToolProjectionEntry,
    ToolProjectionManifest,
    TrustTier,
)
from packages.core_domain.agent_tools import built_in_tool_specs


DEFAULT_MCP_PROFILE_SEED_PATH = Path("infra/seeds/mcp_server_profiles.json")
TOOL_PROJECTION_MANIFEST_ENV_KEY = "WORKFLOW_TOOL_PROJECTION_MANIFEST"


def load_seed_mcp_server_profiles(seed_path: Path | str = DEFAULT_MCP_PROFILE_SEED_PATH) -> list[MCPServerProfile]:
    path = Path(seed_path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [MCPServerProfile.model_validate(item) for item in data]


def dump_tool_projection_manifest(manifest: ToolProjectionManifest | None) -> str:
    return json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False) if manifest is not None else ""


def load_tool_projection_manifest(payload: str | None) -> ToolProjectionManifest | None:
    if payload is None or not payload.strip():
        return None
    return ToolProjectionManifest.model_validate(json.loads(payload))


def _schema_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _trust_tier_for_source(source_type: CapabilitySourceType) -> TrustTier:
    if source_type == CapabilitySourceType.built_in:
        return TrustTier.t0_builtin_local
    if source_type == CapabilitySourceType.mcp_stdio:
        return TrustTier.t1_local_stdio_mcp
    if source_type == CapabilitySourceType.mcp_http:
        return TrustTier.t2_internal_managed_http_mcp
    return TrustTier.t3_third_party_remote_http_mcp


class CapabilitySource(ABC):
    source_type: CapabilitySourceType

    @abstractmethod
    def list_tool_entries(
        self,
        *,
        preset_id: str,
        task_kind: TaskKind,
        review_policy: ReviewPolicy,
    ) -> list[ToolProjectionEntry]:
        raise NotImplementedError

    def list_profiles(self) -> list[MCPServerProfile]:
        return []

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        raise NotImplementedError


class BuiltInCapabilitySource(CapabilitySource):
    source_type = CapabilitySourceType.built_in

    def list_tool_entries(
        self,
        *,
        preset_id: str,
        task_kind: TaskKind,
        review_policy: ReviewPolicy,
    ) -> list[ToolProjectionEntry]:
        entries: list[ToolProjectionEntry] = []
        for spec in built_in_tool_specs():
            schema = {
                "type": "built_in_tool",
                "tool_name": spec["tool_name"],
                "description": spec["description"],
            }
            entries.append(
                ToolProjectionEntry(
                    capability_id=str(task_kind),
                    tool_name=spec["tool_name"],
                    description=spec["description"],
                    source_type=self.source_type,
                    trust_tier=_trust_tier_for_source(self.source_type),
                    read_only=bool(spec.get("read_only", True)),
                    review_requirement="none" if review_policy != ReviewPolicy.mandatory else "human_visible",
                    timeout_budget_ms=2000,
                    schema_hash=_schema_hash(schema),
                    enabled_for_preset=preset_id,
                    redaction_rules=["truncate_text:8000"],
                )
            )
        return entries


class MCPCapabilitySource(CapabilitySource):
    source_type = CapabilitySourceType.mcp_stdio

    def __init__(self, profiles: list[MCPServerProfile] | None = None, *, workspace_root: str | Path = "."):
        self._profiles = {profile.profile_id: profile for profile in (profiles or load_seed_mcp_server_profiles())}
        self._workspace_root = Path(workspace_root).resolve()
        self._tool_cache: dict[str, list[dict[str, Any]]] = {}

    def list_profiles(self) -> list[MCPServerProfile]:
        return sorted(self._profiles.values(), key=lambda item: item.profile_id)

    def list_tool_entries(
        self,
        *,
        preset_id: str,
        task_kind: TaskKind,
        review_policy: ReviewPolicy,
    ) -> list[ToolProjectionEntry]:
        entries: list[ToolProjectionEntry] = []
        for profile in self.list_profiles():
            if not profile.enabled or profile.transport != MCPTransport.stdio:
                continue
            tools = self._list_tools_for_profile(profile)
            consumed_schema_bytes = 0
            for tool in tools[: profile.max_tools]:
                if profile.allowed_tools and tool["name"] not in profile.allowed_tools:
                    continue
                schema_json = tool.get("inputSchema") or {}
                schema_bytes = len(json.dumps(schema_json, ensure_ascii=False))
                if profile.max_schema_bytes and consumed_schema_bytes + schema_bytes > profile.max_schema_bytes:
                    break
                consumed_schema_bytes += schema_bytes
                entries.append(
                    ToolProjectionEntry(
                        capability_id=str(task_kind),
                        tool_name=tool["name"],
                        description=str(tool.get("description") or ""),
                        source_type=self.source_type,
                        trust_tier=_trust_tier_for_source(self.source_type),
                        read_only=True,
                        review_requirement="none" if review_policy != ReviewPolicy.mandatory else "human_visible",
                        timeout_budget_ms=profile.call_timeout_ms,
                        schema_hash=_schema_hash(schema_json),
                        enabled_for_preset=preset_id,
                        redaction_rules=["no_env_leakage"],
                        server_profile_id=profile.profile_id,
                    )
                )
        return entries

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        for profile in self.list_profiles():
            if profile.allowed_tools and tool_name not in profile.allowed_tools:
                continue
            tools = self._list_tools_for_profile(profile)
            if any(tool["name"] == tool_name for tool in tools):
                return anyio.run(self._call_tool_async, profile, tool_name, arguments)
        raise ValueError(f"MCP tool not found: {tool_name}")

    async def _list_tools_async(self, profile: MCPServerProfile) -> list[dict[str, Any]]:
        params = self._server_parameters_for(profile)
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                return [tool.model_dump(mode="json") for tool in result.tools]

    async def _call_tool_async(self, profile: MCPServerProfile, tool_name: str, arguments: dict[str, Any]) -> str:
        params = self._server_parameters_for(profile)
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                chunks: list[str] = []
                for item in result.content:
                    payload = item.model_dump(mode="json")
                    text = payload.get("text")
                    if text:
                        chunks.append(str(text))
                return "\n".join(chunks)

    def _list_tools_for_profile(self, profile: MCPServerProfile) -> list[dict[str, Any]]:
        cached = self._tool_cache.get(profile.profile_id)
        if cached is not None:
            return cached
        tools = anyio.run(self._list_tools_async, profile)
        self._tool_cache[profile.profile_id] = tools
        return tools

    def _server_parameters_for(self, profile: MCPServerProfile) -> StdioServerParameters:
        command = self._resolve_startup_command(profile)
        return StdioServerParameters(
            command=command[0],
            args=command[1:],
            cwd=str(self._workspace_root),
            env={
                "PYTHONUTF8": "1",
                "WORKSPACE_ROOT": self._workspace_root.as_posix(),
            },
        )

    def _resolve_startup_command(self, profile: MCPServerProfile) -> list[str]:
        resolved: list[str] = []
        for item in profile.startup_command:
            if item == "${PYTHON_EXECUTABLE}":
                resolved.append(sys.executable)
                continue
            if item == "${WORKSPACE_ROOT}":
                resolved.append(self._workspace_root.as_posix())
                continue
            resolved.append(item)
        return resolved


class CapabilityPlane:
    def __init__(
        self,
        *,
        workspace_root: str | Path = ".",
        mcp_profiles: list[MCPServerProfile] | None = None,
    ):
        self.built_in_source = BuiltInCapabilitySource()
        self.mcp_source = MCPCapabilitySource(mcp_profiles, workspace_root=workspace_root)

    def list_mcp_profiles(self) -> list[MCPServerProfile]:
        return self.mcp_source.list_profiles()

    def list_capability_sources(self) -> list[dict[str, Any]]:
        sources = [
            {
                "source_type": CapabilitySourceType.built_in,
                "profile_id": None,
                "transport": None,
                "trust_tier": TrustTier.t0_builtin_local,
                "enabled": True,
                "tool_count": len(built_in_tool_specs()),
            }
        ]
        for profile in self.mcp_source.list_profiles():
            sources.append(
                {
                    "source_type": CapabilitySourceType.mcp_stdio if profile.transport == MCPTransport.stdio else CapabilitySourceType.mcp_http,
                    "profile_id": profile.profile_id,
                    "transport": profile.transport,
                    "trust_tier": _trust_tier_for_source(
                        CapabilitySourceType.mcp_stdio if profile.transport == MCPTransport.stdio else CapabilitySourceType.mcp_http
                    ),
                    "enabled": profile.enabled,
                    "tool_count": min(profile.max_tools, len(profile.allowed_tools) or profile.max_tools),
                }
            )
        return sources

    def build_projection_manifest(
        self,
        *,
        run_id: str | None,
        preset_id: str,
        task_kind: TaskKind,
        review_policy: ReviewPolicy,
        lane_type: ExecutionLaneType,
        domain_pack_id: str | None = None,
        include_mcp: bool = False,
    ) -> tuple[ToolProjectionManifest, list[MCPServerProfile]]:
        entries: list[ToolProjectionEntry] = []
        profiles: list[MCPServerProfile] = []
        if lane_type in {ExecutionLaneType.standard_agent, ExecutionLaneType.durable_incremental, ExecutionLaneType.graph_native_complex}:
            entries.extend(
                self.built_in_source.list_tool_entries(
                    preset_id=preset_id,
                    task_kind=task_kind,
                    review_policy=review_policy,
                )
            )
            if include_mcp:
                profiles = [profile for profile in self.mcp_source.list_profiles() if profile.enabled]
                entries.extend(
                    self.mcp_source.list_tool_entries(
                        preset_id=preset_id,
                        task_kind=task_kind,
                        review_policy=review_policy,
                    )
                )
        trust_tiers = sorted({entry.trust_tier for entry in entries}, key=str)
        manifest = ToolProjectionManifest(
            run_id=run_id,
            preset_id=preset_id,
            task_kind=task_kind,
            review_policy=review_policy,
            lane_type=lane_type,
            domain_pack_id=domain_pack_id,
            tools=entries,
            max_schema_bytes=sum(len(entry.schema_hash) for entry in entries),
            trust_tiers=trust_tiers,
        )
        return manifest, profiles
