from __future__ import annotations

from typing import Any

from packages.contracts import (
    ExecutionProfileDefinition,
    ExecutionScopeContext,
    ResolvedExecutionProfile,
)


EXECUTION_PROFILE_FIELDS = (
    "adapter_name",
    "agent_model",
    "codex_model",
    "codex_reasoning_effort",
    "opencode_model",
    "opencode_variant",
    "runtime_gateway_provider",
    "runtime_gateway_model",
    "runtime_reasoning_effort",
    "worker_pool_id",
)


def execution_profile_values(profile: ExecutionProfileDefinition | None) -> dict[str, Any]:
    if profile is None:
        return {}
    values: dict[str, Any] = {}
    for field_name in EXECUTION_PROFILE_FIELDS:
        value = getattr(profile, field_name, None)
        if value is not None:
            values[field_name] = value
    return values


def _global_execution_profile(effective_config: dict[str, Any]) -> tuple[ExecutionProfileDefinition, dict[str, str]]:
    runtime_gateway = effective_config["runtime_gateway"]
    agent = effective_config["agent"]
    codex = effective_config["codex"]
    opencode = effective_config["opencode"]
    worker_pools = effective_config["worker_pools"]
    return (
        ExecutionProfileDefinition(
            agent_model=agent["model"],
            codex_model=codex["model"],
            codex_reasoning_effort=codex["reasoning_effort"],
            opencode_model=opencode["model"],
            opencode_variant=opencode["variant"],
            runtime_gateway_provider=runtime_gateway["provider"],
            runtime_gateway_model=runtime_gateway["openai_model"],
            runtime_reasoning_effort=runtime_gateway["openai_reasoning_effort"],
            worker_pool_id=worker_pools["default_pool_id"],
        ),
        {
            "agent_model": agent["model_source"],
            "codex_model": codex["model_source"],
            "codex_reasoning_effort": codex["reasoning_effort_source"],
            "opencode_model": opencode["model_source"],
            "opencode_variant": opencode["variant_source"],
            "runtime_gateway_provider": runtime_gateway["provider_source"],
            "runtime_gateway_model": runtime_gateway["openai_model_source"],
            "runtime_reasoning_effort": runtime_gateway["openai_reasoning_effort_source"],
            "worker_pool_id": worker_pools["default_pool_id_source"],
        },
    )


def build_effective_execution_defaults(effective_config: dict[str, Any]) -> dict[str, Any]:
    profile, sources = _global_execution_profile(effective_config)
    values = execution_profile_values(profile)
    return {
        field_name: {
            "value": values.get(field_name),
            "source": sources.get(field_name, "default"),
        }
        for field_name in EXECUTION_PROFILE_FIELDS
        if field_name != "adapter_name"
    }


def resolve_execution_profile(
    *,
    effective_config: dict[str, Any],
    explicit_profile: ExecutionProfileDefinition | None = None,
    cluster_member_profile: ExecutionProfileDefinition | None = None,
    agent_profile: ExecutionProfileDefinition | None = None,
    preset_profile: ExecutionProfileDefinition | None = None,
    cluster_template_profile: ExecutionProfileDefinition | None = None,
    compatibility_adapter: str | None = None,
    routing_default_adapter: str | None = None,
    scope_context: ExecutionScopeContext | None = None,
) -> ResolvedExecutionProfile:
    global_profile, global_sources = _global_execution_profile(effective_config)
    scope_entries = [
        ("explicit_invocation", "compile_request", explicit_profile, {}),
        ("cluster_member", "cluster_member_spec", cluster_member_profile, {}),
        ("agent_profile", "agent_profile_definition", agent_profile, {}),
        ("preset", "preset_definition", preset_profile, {}),
        ("cluster_template_default", "cluster_template_definition", cluster_template_profile, {}),
        ("effective_global_defaults", "effective_config", global_profile, global_sources),
    ]

    applied_scopes: list[dict[str, Any]] = []
    source_map: dict[str, dict[str, Any]] = {}
    resolved_values: dict[str, Any] = {}

    for scope_name, source_name, profile, field_sources in scope_entries:
        values = execution_profile_values(profile)
        if not values:
            continue
        scope_payload: dict[str, Any] = {
            "scope": scope_name,
            "source": source_name,
            "values": values,
        }
        if field_sources:
            scope_payload["field_sources"] = dict(field_sources)
        applied_scopes.append(scope_payload)
        for field_name, value in values.items():
            if field_name in resolved_values:
                continue
            resolved_values[field_name] = value
            source_map[field_name] = {
                "scope": scope_name,
                "source": field_sources.get(field_name, source_name),
                "value": value,
            }

    compatibility_fallback = None
    if resolved_values.get("adapter_name") is None and compatibility_adapter is not None:
        compatibility_fallback = "legacy_adapter_resolution"
        resolved_values["adapter_name"] = compatibility_adapter
        source_map["adapter_name"] = {
            "scope": "compatibility_fallback",
            "source": compatibility_fallback,
            "value": compatibility_adapter,
        }
    if resolved_values.get("adapter_name") is None and routing_default_adapter is not None:
        compatibility_fallback = "worker_router_default"
        resolved_values["adapter_name"] = routing_default_adapter
        source_map["adapter_name"] = {
            "scope": "compatibility_fallback",
            "source": compatibility_fallback,
            "value": routing_default_adapter,
        }

    adapter_name = resolved_values.get("adapter_name")
    selected_model = None
    selected_model_kind = None
    model_variant = None
    if adapter_name == "agent":
        selected_model = resolved_values.get("agent_model")
        selected_model_kind = "agent_model"
    elif adapter_name == "codex":
        selected_model = resolved_values.get("codex_model")
        selected_model_kind = "codex_model"
    elif adapter_name in {"opencode", "opencode_session"}:
        selected_model = resolved_values.get("opencode_model")
        selected_model_kind = "opencode_model"
        model_variant = resolved_values.get("opencode_variant")

    return ResolvedExecutionProfile(
        adapter_name=adapter_name,
        selected_model=selected_model,
        selected_model_kind=selected_model_kind,
        model_variant=model_variant,
        agent_model=resolved_values.get("agent_model"),
        codex_model=resolved_values.get("codex_model"),
        codex_reasoning_effort=resolved_values.get("codex_reasoning_effort"),
        opencode_model=resolved_values.get("opencode_model"),
        opencode_variant=resolved_values.get("opencode_variant"),
        runtime_gateway_provider=resolved_values.get("runtime_gateway_provider"),
        runtime_gateway_model=resolved_values.get("runtime_gateway_model"),
        runtime_reasoning_effort=resolved_values.get("runtime_reasoning_effort"),
        worker_pool_id=resolved_values.get("worker_pool_id"),
        scope_context=scope_context,
        source_map=source_map,
        applied_scopes=applied_scopes,
        compatibility_fallback=compatibility_fallback,
    )
