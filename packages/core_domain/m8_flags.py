from __future__ import annotations

from packages.core_domain.config import build_effective_config


def _flag_value(name: str) -> bool:
    effective = build_effective_config()
    feature_flags = effective["feature_flags"]
    mapping = {
        "UAWO_ENABLE_AGENT_LANE": feature_flags["agent_lane"]["enabled"],
        "UAWO_ENABLE_MCP_SOURCE": feature_flags["mcp_source"]["enabled"],
        "UAWO_ENABLE_EXTERNAL_TRACE_EXPORT": feature_flags["external_trace_export"]["enabled"],
        "UAWO_ENABLE_DURABLE_PILOT": feature_flags["durable_pilot"]["enabled"],
        "UAWO_ENABLE_SKILL_EXPORT": feature_flags["skill_export"]["enabled"],
        "UAWO_ENABLE_EXTERNAL_WORKER_POOLS": feature_flags["external_worker_pools"]["enabled"],
        "UAWO_ENABLE_SESSIONFUL_EXTERNAL_AGENTS": feature_flags["sessionful_external_agents"]["enabled"],
    }
    return bool(mapping[name])


def is_agent_lane_enabled() -> bool:
    return _flag_value("UAWO_ENABLE_AGENT_LANE")


def is_mcp_source_enabled() -> bool:
    return _flag_value("UAWO_ENABLE_MCP_SOURCE")


def is_external_trace_export_enabled() -> bool:
    return _flag_value("UAWO_ENABLE_EXTERNAL_TRACE_EXPORT")


def is_durable_pilot_enabled() -> bool:
    return _flag_value("UAWO_ENABLE_DURABLE_PILOT")


def is_skill_export_enabled() -> bool:
    return _flag_value("UAWO_ENABLE_SKILL_EXPORT")


def is_external_worker_pools_enabled() -> bool:
    return _flag_value("UAWO_ENABLE_EXTERNAL_WORKER_POOLS")


def is_sessionful_external_agents_enabled() -> bool:
    return _flag_value("UAWO_ENABLE_SESSIONFUL_EXTERNAL_AGENTS")


def active_feature_flags() -> dict[str, bool]:
    return {
        "UAWO_ENABLE_AGENT_LANE": is_agent_lane_enabled(),
        "UAWO_ENABLE_MCP_SOURCE": is_mcp_source_enabled(),
        "UAWO_ENABLE_EXTERNAL_TRACE_EXPORT": is_external_trace_export_enabled(),
        "UAWO_ENABLE_DURABLE_PILOT": is_durable_pilot_enabled(),
        "UAWO_ENABLE_SKILL_EXPORT": is_skill_export_enabled(),
        "UAWO_ENABLE_EXTERNAL_WORKER_POOLS": is_external_worker_pools_enabled(),
        "UAWO_ENABLE_SESSIONFUL_EXTERNAL_AGENTS": is_sessionful_external_agents_enabled(),
    }
