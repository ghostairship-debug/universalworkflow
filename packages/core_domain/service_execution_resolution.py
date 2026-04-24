from __future__ import annotations

from typing import Any

from packages.contracts import (
    AgentRoleType,
    DomainPackResolution,
    ExecutionScopeContext,
    MutationContract,
    PresetDefinition,
    ResolvedExecutionProfile,
    TaskKind,
)
from packages.core_domain.execution_profiles import resolve_execution_profile


def _agent_profile_definition(service: Any, agent_profile_id: str | None):
    if not agent_profile_id:
        return None
    return next((profile for profile in service.list_agent_profiles() if profile.profile_id == agent_profile_id), None)


def _cluster_template_definition(service: Any, cluster_template_id: str | None):
    if not cluster_template_id:
        return None
    return next(
        (template for template in service.list_cluster_templates() if template.template_id == cluster_template_id),
        None,
    )


def _cluster_member_definition(service: Any, cluster_template_id: str | None, cluster_member_id: str | None):
    template = _cluster_template_definition(service, cluster_template_id)
    if template is None or not cluster_member_id:
        return None
    return next((member for member in template.member_specs if member.member_id == cluster_member_id), None)


def resolve_execution_profile_for_service(
    service: Any,
    *,
    preset: PresetDefinition,
    task_kind: TaskKind,
    domain_pack: DomainPackResolution | None,
    mutation_contract: MutationContract | None = None,
    requested_adapter: str | None = None,
    requested_agent_model: str | None = None,
    requested_codex_model: str | None = None,
    requested_opencode_model: str | None = None,
    requested_opencode_variant: str | None = None,
    requested_runtime_gateway_provider: str | None = None,
    requested_runtime_gateway_model: str | None = None,
    requested_runtime_reasoning_effort: str | None = None,
    requested_worker_pool_id: str | None = None,
    agent_profile_id: str | None = None,
    cluster_template_id: str | None = None,
    cluster_member_id: str | None = None,
    public_role: AgentRoleType | str | None = None,
    role_label: str | None = None,
) -> ResolvedExecutionProfile:
    cluster_member = _cluster_member_definition(service, cluster_template_id, cluster_member_id)
    template = _cluster_template_definition(service, cluster_template_id)
    resolved_agent_profile_id = (
        agent_profile_id
        or (cluster_member.agent_profile_id if cluster_member is not None and cluster_member.agent_profile_id else None)
    )
    agent_profile = _agent_profile_definition(service, resolved_agent_profile_id)
    scope_context = ExecutionScopeContext(
        preset_id=preset.preset_id,
        agent_profile_id=resolved_agent_profile_id,
        cluster_template_id=cluster_template_id,
        cluster_member_id=cluster_member_id,
        public_role=public_role,
        role_label=role_label,
    )
    resolved = resolve_execution_profile(
        effective_config=service.effective_config,
        explicit_profile=service._execution_override_profile(
            adapter_name=requested_adapter,
            agent_model=requested_agent_model,
            codex_model=requested_codex_model,
            opencode_model=requested_opencode_model,
            opencode_variant=requested_opencode_variant,
            runtime_gateway_provider=requested_runtime_gateway_provider,
            runtime_gateway_model=requested_runtime_gateway_model,
            runtime_reasoning_effort=requested_runtime_reasoning_effort,
            worker_pool_id=requested_worker_pool_id,
        ),
        cluster_member_profile=cluster_member.execution_profile if cluster_member is not None else None,
        agent_profile=agent_profile.execution_profile if agent_profile is not None else None,
        preset_profile=preset.execution_profile,
        cluster_template_profile=template.default_execution_profile if template is not None else None,
        compatibility_adapter=service._default_adapter_for_preset(preset, task_kind, domain_pack),
        routing_default_adapter=service._router_default_adapter_for_task_kind(task_kind),
        scope_context=scope_context,
    )
    selected_adapter = resolved.adapter_name
    if (
        selected_adapter is not None
        and service._capability_route_for(task_kind, adapter_name=selected_adapter) is None
        and resolved.source_map.get("adapter_name", {}).get("scope") != "explicit_invocation"
    ):
        fallback_adapter = service._router_default_adapter_for_task_kind(task_kind)
        selected_model = None
        selected_model_kind = None
        model_variant = None
        if fallback_adapter == "agent":
            selected_model = resolved.agent_model
            selected_model_kind = "agent_model"
        elif fallback_adapter == "codex":
            selected_model = resolved.codex_model
            selected_model_kind = "codex_model"
        elif fallback_adapter in {"opencode", "opencode_session"}:
            selected_model = resolved.opencode_model
            selected_model_kind = "opencode_model"
            model_variant = resolved.opencode_variant
        source_map = dict(resolved.source_map)
        source_map["adapter_name"] = {
            "scope": "compatibility_fallback",
            "source": "worker_router_default",
            "value": fallback_adapter,
        }
        resolved = ResolvedExecutionProfile.model_validate(
            {
                **resolved.model_dump(mode="json"),
                "adapter_name": fallback_adapter,
                "selected_model": selected_model,
                "selected_model_kind": selected_model_kind,
                "model_variant": model_variant,
                "compatibility_fallback": "worker_router_default",
                "source_map": source_map,
            }
        )
    lane = service._resolve_execution_lane(
        preset=preset,
        task_kind=task_kind,
        selected_adapter=resolved.adapter_name,
        mutation_contract=mutation_contract,
    )
    source_map = dict(resolved.source_map)
    source_map["execution_lane"] = {
        "scope": "derived_lane_rules",
        "source": "execution_lane_resolution",
        "value": str(lane),
    }
    return ResolvedExecutionProfile.model_validate(
        {
            **resolved.model_dump(mode="json"),
            "execution_lane": str(lane),
            "source_map": source_map,
        }
    )
