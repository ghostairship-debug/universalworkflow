from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import anyio

from packages.contracts import (
    CapabilityDescriptor,
    CapabilityHealth,
    CapabilitySourceType,
    ExecutionLaneType,
    MCPServerProfile,
    MCPTransport,
    ReviewPolicy,
    TaskKind,
    ToolProjectionEntry,
    ToolProjectionManifest,
    TrustTier,
    WorkerPoolProfile,
)
from packages.core_domain.agent_tools import built_in_tool_specs


DEFAULT_MCP_PROFILE_SEED_PATH = Path("infra/seeds/mcp_server_profiles.json")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_PROJECTION_MANIFEST_ENV_KEY = "WORKFLOW_TOOL_PROJECTION_MANIFEST"
_MCP_IMPORT_CACHE: tuple[Any | None, Any | None, Any | None] | None = None
_MCP_IMPORT_ERROR: ImportError | None = None


def load_seed_mcp_server_profiles(seed_path: Path | str = DEFAULT_MCP_PROFILE_SEED_PATH) -> list[MCPServerProfile]:
    path = Path(seed_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
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


def _load_mcp_client() -> tuple[Any | None, Any | None, Any | None]:
    global _MCP_IMPORT_CACHE, _MCP_IMPORT_ERROR
    if _MCP_IMPORT_CACHE is not None or _MCP_IMPORT_ERROR is not None:
        return _MCP_IMPORT_CACHE or (None, None, None)
    try:
        session_module = importlib.import_module("mcp.client.session")
        stdio_module = importlib.import_module("mcp.client.stdio")
    except ImportError as exc:
        _MCP_IMPORT_ERROR = exc
        return (None, None, None)
    _MCP_IMPORT_CACHE = (
        getattr(session_module, "ClientSession"),
        getattr(stdio_module, "StdioServerParameters"),
        getattr(stdio_module, "stdio_client"),
    )
    return _MCP_IMPORT_CACHE


def mcp_dependency_available() -> bool:
    client_session, _, _ = _load_mcp_client()
    return client_session is not None


def mcp_dependency_reason() -> str | None:
    _load_mcp_client()
    if _MCP_IMPORT_ERROR is None:
        return None
    return "mcp_dependency_missing"


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
        if not mcp_dependency_available():
            return []
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
        self._require_mcp_dependency()
        for profile in self.list_profiles():
            if profile.allowed_tools and tool_name not in profile.allowed_tools:
                continue
            tools = self._list_tools_for_profile(profile)
            if any(tool["name"] == tool_name for tool in tools):
                return anyio.run(self._call_tool_async, profile, tool_name, arguments)
        raise ValueError(f"MCP tool not found: {tool_name}")

    async def _list_tools_async(self, profile: MCPServerProfile) -> list[dict[str, Any]]:
        client_session, _, stdio_client_fn = self._require_mcp_dependency()
        params = self._server_parameters_for(profile)
        async with stdio_client_fn(params) as (read_stream, write_stream):
            async with client_session(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                return [tool.model_dump(mode="json") for tool in result.tools]

    async def _call_tool_async(self, profile: MCPServerProfile, tool_name: str, arguments: dict[str, Any]) -> str:
        client_session, _, stdio_client_fn = self._require_mcp_dependency()
        params = self._server_parameters_for(profile)
        async with stdio_client_fn(params) as (read_stream, write_stream):
            async with client_session(read_stream, write_stream) as session:
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
        try:
            tools = anyio.run(self._list_tools_async, profile)
        except Exception:
            # Projection preview should remain available even when the host process
            # cannot safely bootstrap the stdio MCP transport (for example inside
            # test harnesses with non-file stderr handles).
            tools = self._fallback_tools_for_profile(profile)
        self._tool_cache[profile.profile_id] = tools
        return tools

    def _fallback_tools_for_profile(self, profile: MCPServerProfile) -> list[dict[str, Any]]:
        return [
            {
                "name": tool_name,
                "description": f"Fallback MCP tool entry from profile `{profile.profile_id}`",
                "inputSchema": {},
            }
            for tool_name in profile.allowed_tools[: profile.max_tools]
        ]

    def _server_parameters_for(self, profile: MCPServerProfile) -> Any:
        _, stdio_server_parameters_cls, _ = self._require_mcp_dependency()
        command = self._resolve_startup_command(profile)
        return stdio_server_parameters_cls(
            command=command[0],
            args=command[1:],
            cwd=str(self._workspace_root),
            env={
                "PYTHONUTF8": "1",
                "WORKSPACE_ROOT": self._workspace_root.as_posix(),
                **self._resolve_startup_env(profile),
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

    def _resolve_startup_env(self, profile: MCPServerProfile) -> dict[str, str]:
        resolved: dict[str, str] = {}
        for name, value in profile.startup_env.items():
            token = str(value)
            if token.startswith("${ENV:") and token.endswith("}"):
                source_name = token.removeprefix("${ENV:").removesuffix("}")
                source_value = os.getenv(source_name)
                if source_value:
                    resolved[name] = source_value
                continue
            if token == "${WORKSPACE_ROOT}":
                resolved[name] = self._workspace_root.as_posix()
                continue
            resolved[name] = token
        return resolved

    def _require_mcp_dependency(self) -> tuple[Any, Any, Any]:
        client_session, stdio_server_parameters_cls, stdio_client_fn = _load_mcp_client()
        if client_session is None or stdio_server_parameters_cls is None or stdio_client_fn is None:
            raise RuntimeError("MCP dependency is unavailable; install the optional `mcp` extra to enable MCP tool execution")
        return client_session, stdio_server_parameters_cls, stdio_client_fn


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

    def list_capability_descriptors(
        self,
        *,
        worker_pool_profiles: list[WorkerPoolProfile] | None = None,
        runtime_gateway_description: dict[str, Any] | None = None,
        capability_routes: list[dict[str, Any]] | None = None,
        default_worker_pool_id: str | None = None,
    ) -> list[CapabilityDescriptor]:
        descriptors: list[CapabilityDescriptor] = [
            CapabilityDescriptor(
                capability_id="built_in:local",
                provider_kind="built_in",
                transport="local",
                auth_mode="none",
                scopes=[spec["tool_name"] for spec in built_in_tool_specs()],
                allowed_task_kinds=[TaskKind.shell_exec],
                cost_class="local_low",
                latency_class="local_low",
                side_effect_level="read_only",
                evidence_schema={
                    "result_envelope": "v1",
                    "tool_projection_manifest": "v1",
                },
                display_name="Built-in Local Tools",
                source_type=CapabilitySourceType.built_in,
            )
        ]
        for profile in self.mcp_source.list_profiles():
            source_type = (
                CapabilitySourceType.mcp_stdio if profile.transport == MCPTransport.stdio else CapabilitySourceType.mcp_http
            )
            descriptors.append(
                CapabilityDescriptor(
                    capability_id=f"mcp_profile:{profile.profile_id}",
                    provider_kind="mcp_profile",
                    transport=str(profile.transport),
                    auth_mode=profile.auth_mode,
                    scopes=list(profile.allowed_tools),
                    allowed_task_kinds=[TaskKind.shell_exec],
                    cost_class="local_low" if profile.transport == MCPTransport.stdio else "remote_variable",
                    latency_class="local_low" if profile.transport == MCPTransport.stdio else "remote_medium",
                    side_effect_level="read_only",
                    evidence_schema={
                        "result_envelope": "v1",
                        "tool_projection_manifest": "v1",
                        "server_profile_id": profile.profile_id,
                    },
                    display_name=profile.name,
                    source_type=source_type,
                    profile_id=profile.profile_id,
                    enabled=profile.enabled,
                )
            )
        for route in capability_routes or []:
            capability = str(route.get("capability") or "")
            adapter_name = str(route.get("adapter_name") or "")
            if not capability or not adapter_name:
                continue
            side_effect_level = "repo_mutation_controlled" if adapter_name in {"codex", "opencode"} else "artifact_only"
            if adapter_name in {"agent", "opencode_session"}:
                side_effect_level = "session_read_write"
            display_names = {
                "claude_architect": "Claude Architect Gate route",
                "mmx_multimodal": "MMX multimodal evidence route",
                "vertex_multimodal": "Vertex multimodal fallback route",
            }
            descriptors.append(
                CapabilityDescriptor(
                    capability_id=f"adapter_route:{capability}:{adapter_name}",
                    provider_kind="adapter_route",
                    transport="local_cli",
                    auth_mode="local_process",
                    scopes=[str(route.get("adapter_class") or adapter_name)],
                    allowed_task_kinds=[TaskKind(capability)],
                    cost_class="local_low" if adapter_name in {"shell", "noop"} else "provider_variable",
                    latency_class="local_low" if adapter_name in {"shell", "noop"} else "provider_variable",
                    side_effect_level=side_effect_level,
                    evidence_schema={
                        "result_envelope": "v1",
                        "task_evidence": "v1",
                    },
                    display_name=display_names.get(adapter_name, f"{adapter_name} route for {capability}"),
                    adapter_name=adapter_name,
                    enabled=True,
                    default_selected=adapter_name in {"shell", "noop"},
                )
            )
        for profile in worker_pool_profiles or []:
            descriptors.append(
                CapabilityDescriptor(
                    capability_id=f"worker_pool:{profile.worker_pool_id}",
                    provider_kind="worker_pool",
                    transport=str(profile.transport),
                    auth_mode=profile.auth_mode,
                    scopes=[profile.adapter_name, profile.dispatch_mode],
                    allowed_task_kinds=[TaskKind.shell_exec],
                    cost_class="local_low" if str(profile.transport) == "local" else "remote_variable",
                    latency_class="local_low" if str(profile.transport) == "local" else "remote_medium",
                    side_effect_level="artifact_only" if str(profile.transport) == "local" else "remote_dispatch",
                    evidence_schema={
                        "result_envelope": "v1",
                        "execution_target": "v1",
                        "lease_renewals": "v1",
                    },
                    display_name=profile.name,
                    profile_id=profile.worker_pool_id,
                    adapter_name=profile.adapter_name,
                    enabled=profile.enabled,
                    default_selected=profile.worker_pool_id == default_worker_pool_id,
                )
            )
        if runtime_gateway_description is not None:
            provider = str(runtime_gateway_description.get("provider") or "null")
            model = runtime_gateway_description.get("model")
            scopes = [provider]
            if model:
                scopes.append(str(model))
            descriptors.append(
                CapabilityDescriptor(
                    capability_id=f"runtime_gateway:{provider}",
                    provider_kind="runtime_gateway",
                    transport="hosted" if provider != "null" else "local",
                    auth_mode="env" if provider != "null" else "none",
                    scopes=scopes,
                    allowed_task_kinds=[TaskKind.shell_exec],
                    cost_class="provider_variable" if provider != "null" else "none",
                    latency_class="provider_variable" if provider != "null" else "local_low",
                    side_effect_level="read_only",
                    evidence_schema={
                        "result_envelope": "v1",
                        "runtime_gateway": "v1",
                    },
                    display_name=f"Runtime gateway ({provider})",
                    enabled=provider != "null",
                )
            )
        return sorted(descriptors, key=lambda item: (item.provider_kind, item.capability_id))

    def list_capability_health(
        self,
        *,
        worker_pool_profiles: list[WorkerPoolProfile] | None = None,
        runtime_gateway_description: dict[str, Any] | None = None,
        capability_routes: list[dict[str, Any]] | None = None,
        default_worker_pool_id: str | None = None,
    ) -> list[CapabilityHealth]:
        descriptors = self.list_capability_descriptors(
            worker_pool_profiles=worker_pool_profiles,
            runtime_gateway_description=runtime_gateway_description,
            capability_routes=capability_routes,
            default_worker_pool_id=default_worker_pool_id,
        )
        health: list[CapabilityHealth] = []
        for descriptor in descriptors:
            failure_classes = self._failure_classes_for_descriptor(descriptor)
            probe_status, probe_reason, probe_detail = self._runtime_probe_for_descriptor(descriptor)
            if descriptor.enabled and probe_status in {"ready", "assumed_ready", "runtime_ready"}:
                status = "ready"
            elif descriptor.enabled:
                status = "degraded"
            else:
                status = "disabled"
            reason = None if descriptor.enabled and status == "ready" else probe_reason or "descriptor_disabled"
            health.append(
                CapabilityHealth(
                    descriptor=descriptor,
                    status=status,
                    reason=reason,
                    tool_count=len(descriptor.scopes),
                    failure_classes=failure_classes,
                    recent_call_summary={
                        "recent_success_count": 0,
                        "recent_failure_count": 0,
                    },
                    runtime_probe_status=probe_status,
                    runtime_probe_reason=probe_reason,
                    runtime_probe_detail=probe_detail,
                )
            )
        return health

    def _failure_classes_for_descriptor(self, descriptor: CapabilityDescriptor) -> list[str]:
        if descriptor.provider_kind == "mcp_profile":
            return ["profile_disabled", "tool_unavailable", "startup_failed", "call_timeout"]
        if descriptor.provider_kind == "worker_pool":
            return ["pool_disabled", "dispatch_failed", "callback_timeout"]
        if descriptor.provider_kind == "runtime_gateway":
            return ["provider_not_configured", "provider_call_failed", "provider_timeout"]
        if descriptor.provider_kind == "adapter_route":
            return ["adapter_unavailable", "execution_failed", "artifact_missing"]
        return ["schema_mismatch"]

    def _runtime_probe_for_descriptor(self, descriptor: CapabilityDescriptor) -> tuple[str, str | None, dict[str, Any]]:
        if descriptor.provider_kind == "mcp_profile":
            if not mcp_dependency_available():
                return ("dependency_missing", mcp_dependency_reason(), {"dependency": "mcp", "installed": False})
            return ("runtime_ready", None, {"dependency": "mcp", "installed": True})
        if descriptor.provider_kind == "runtime_gateway":
            if not descriptor.enabled:
                return ("provider_not_configured", "provider_not_configured", {"provider": descriptor.scopes[0] if descriptor.scopes else None})
            return ("runtime_ready", None, {"provider": descriptor.scopes[0] if descriptor.scopes else None})
        if descriptor.provider_kind == "worker_pool":
            if not descriptor.enabled:
                return ("pool_disabled", "pool_disabled", {"worker_pool_id": descriptor.profile_id})
            return ("assumed_ready", None, {"worker_pool_id": descriptor.profile_id, "transport": descriptor.transport})
        if descriptor.provider_kind == "adapter_route":
            return (
                "assumed_ready" if descriptor.enabled else "adapter_disabled",
                None if descriptor.enabled else "adapter_disabled",
                {"adapter_name": descriptor.adapter_name},
            )
        return ("ready", None, {"provider_kind": descriptor.provider_kind})

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
        if lane_type in {
            ExecutionLaneType.standard_agent,
            ExecutionLaneType.durable_incremental,
            ExecutionLaneType.graph_native_complex,
            ExecutionLaneType.sessionful_external_agent,
        }:
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
