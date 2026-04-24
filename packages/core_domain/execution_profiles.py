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

DOGFOOD_CORE_MODEL_FIELDS = {
    "agent_model",
    "codex_model",
    "codex_reasoning_effort",
    "runtime_gateway_model",
    "runtime_reasoning_effort",
}

DOGFOOD_CODEX_CLUSTER_TEMPLATE_IDS = {
    "architecture_delivery_cluster",
    "search_cluster",
    "design_cluster",
    "multimodal_cluster",
    "review_cluster",
    "management_cluster",
}

EXTERNAL_ADAPTER_MODEL_LABELS = {
    "claude_architect": ("claude-code-cli", "external_cli_model"),
    "mmx_multimodal": ("mmx-cli-default", "external_cli_model"),
    "vertex_multimodal": ("vertex-cli-default", "external_cli_model"),
}


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
    dogfood = effective_config.get("dogfood") or {}
    strong_enabled = bool(dogfood.get("strong_model_enabled"))
    dogfood_backend = str(dogfood.get("execution_backend") or "codex_cli").strip().lower()
    dogfood_model = str(dogfood.get("model") or "gpt-5.5")
    dogfood_codex_model = str(dogfood.get("codex_model") or dogfood_model)
    dogfood_reasoning = str(dogfood.get("reasoning_effort") or "xhigh")
    dogfood_source = "derived:dogfood_strong_default"
    dogfood_codex_source = (
        dogfood.get("codex_model_source")
        if dogfood.get("codex_model")
        else "derived:dogfood_codex_cli_backend_default"
    )
    return (
        ExecutionProfileDefinition(
            agent_model=dogfood_model if strong_enabled else agent["model"],
            codex_model=(
                dogfood_codex_model
                if strong_enabled and dogfood_backend == "codex_cli"
                else dogfood_model
                if strong_enabled
                else codex["model"]
            ),
            codex_reasoning_effort=dogfood_reasoning if strong_enabled else codex["reasoning_effort"],
            opencode_model=opencode["model"],
            opencode_variant=opencode["variant"],
            runtime_gateway_provider=runtime_gateway["provider"],
            runtime_gateway_model=dogfood_model if strong_enabled else runtime_gateway["openai_model"],
            runtime_reasoning_effort=dogfood_reasoning if strong_enabled else runtime_gateway["openai_reasoning_effort"],
            worker_pool_id=worker_pools["default_pool_id"],
        ),
        {
            "agent_model": dogfood_source if strong_enabled else agent["model_source"],
            "codex_model": (
                dogfood_codex_source
                if strong_enabled and dogfood_backend == "codex_cli"
                else dogfood_source
                if strong_enabled
                else codex["model_source"]
            ),
            "codex_reasoning_effort": dogfood_source if strong_enabled else codex["reasoning_effort_source"],
            "opencode_model": opencode["model_source"],
            "opencode_variant": opencode["variant_source"],
            "runtime_gateway_provider": runtime_gateway["provider_source"],
            "runtime_gateway_model": dogfood_source if strong_enabled else runtime_gateway["openai_model_source"],
            "runtime_reasoning_effort": dogfood_source if strong_enabled else runtime_gateway["openai_reasoning_effort_source"],
            "worker_pool_id": worker_pools["default_pool_id_source"],
        },
    )


def _model_selection_metadata(
    *,
    adapter_name: str | None,
    selected_model_kind: str | None,
    source_map: dict[str, dict[str, Any]],
    dogfood_strong_model_enabled: bool,
    dogfood_execution_backend: str | None,
    scope_context: ExecutionScopeContext | None,
) -> tuple[str, str]:
    adapter_source = source_map.get("adapter_name", {})
    model_source = source_map.get(selected_model_kind or "", {})
    if (
        dogfood_strong_model_enabled
        and dogfood_execution_backend == "codex_cli"
        and scope_context is not None
        and scope_context.cluster_template_id in DOGFOOD_CODEX_CLUSTER_TEMPLATE_IDS
        and adapter_name == "codex"
        and selected_model_kind == "codex_model"
        and str(model_source.get("source") or "").startswith(
            (
                "derived:dogfood_strong_default",
                "derived:dogfood_codex_cli_backend_default",
                "env:WORKFLOW_DOGFOOD_CODEX_MODEL",
                "toml:dogfood.codex_model",
            )
        )
    ):
        return (
            "dogfood_strong_codex_cli",
            "M41 dogfood is using Codex CLI as the strong execution backend to avoid OpenAI API dependency",
        )
    if model_source.get("scope") == "explicit_invocation" or (
        adapter_source.get("scope") == "explicit_invocation" and not selected_model_kind
    ):
        return ("manual", "explicit invocation or operator request selected the adapter/model")
    if (
        dogfood_strong_model_enabled
        and selected_model_kind in DOGFOOD_CORE_MODEL_FIELDS
        and str(model_source.get("source") or "").startswith(
            ("derived:dogfood_strong_default", "derived:dogfood_codex_cli_backend_default")
        )
    ):
        return (
            "dogfood_strong_default",
            "M41 dogfood is running core workflow roles on the strong default model for accuracy",
        )
    if adapter_name in EXTERNAL_ADAPTER_MODEL_LABELS:
        return ("role_default", "external artifact-only capability uses its configured local CLI default")
    if adapter_source.get("scope") == "compatibility_fallback":
        return ("fallback", "worker router compatibility fallback selected the adapter")
    return ("role_default", "resolved from role, preset, cluster, or effective global defaults")


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

    dogfood_config = effective_config.get("dogfood") or {}
    dogfood_strong_model_enabled = bool(dogfood_config.get("strong_model_enabled"))
    dogfood_execution_backend = str(dogfood_config.get("execution_backend") or "codex_cli").strip().lower()
    should_route_agent_to_codex_cli = (
        dogfood_strong_model_enabled
        and dogfood_execution_backend == "codex_cli"
        and scope_context is not None
        and scope_context.cluster_template_id in DOGFOOD_CODEX_CLUSTER_TEMPLATE_IDS
        and resolved_values.get("adapter_name") == "agent"
        and source_map.get("adapter_name", {}).get("scope") != "explicit_invocation"
    )
    if should_route_agent_to_codex_cli:
        resolved_values["adapter_name"] = "codex"
        source_map["adapter_name"] = {
            "scope": "dogfood_execution_backend",
            "source": "derived:dogfood_codex_cli_backend",
            "value": "codex",
            "original_value": "agent",
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
    elif adapter_name in EXTERNAL_ADAPTER_MODEL_LABELS:
        selected_model, selected_model_kind = EXTERNAL_ADAPTER_MODEL_LABELS[adapter_name]

    model_selection_source, model_selection_reason = _model_selection_metadata(
        adapter_name=adapter_name,
        selected_model_kind=selected_model_kind,
        source_map=source_map,
        dogfood_strong_model_enabled=dogfood_strong_model_enabled,
        dogfood_execution_backend=dogfood_execution_backend,
        scope_context=scope_context,
    )
    langchain_config = effective_config.get("langchain_agent") or {}

    return ResolvedExecutionProfile(
        adapter_name=adapter_name,
        selected_model=selected_model,
        selected_model_kind=selected_model_kind,
        model_variant=model_variant,
        model_selection_source=model_selection_source,
        model_selection_reason=model_selection_reason,
        dogfood_strong_model_enabled=dogfood_strong_model_enabled,
        dogfood_execution_backend=dogfood_execution_backend,
        langchain_agent_provider=str(langchain_config.get("provider") or "auto"),
        langchain_agent_model=(
            str(langchain_config.get("model"))
            if langchain_config.get("model") is not None
            else None
        ),
        langchain_agent_degraded_reason=None,
        role_responsibilities=[],
        claude_architect_call_count=0,
        multimodal_evidence_refs=[],
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
