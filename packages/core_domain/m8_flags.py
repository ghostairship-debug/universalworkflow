from __future__ import annotations

import os


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "enabled"}


def is_agent_lane_enabled() -> bool:
    return _env_flag("UAWO_ENABLE_AGENT_LANE")


def is_mcp_source_enabled() -> bool:
    return _env_flag("UAWO_ENABLE_MCP_SOURCE")


def is_external_trace_export_enabled() -> bool:
    return _env_flag("UAWO_ENABLE_EXTERNAL_TRACE_EXPORT")


def is_durable_pilot_enabled() -> bool:
    return _env_flag("UAWO_ENABLE_DURABLE_PILOT")


def is_skill_export_enabled() -> bool:
    return _env_flag("UAWO_ENABLE_SKILL_EXPORT")


def active_feature_flags() -> dict[str, bool]:
    return {
        "UAWO_ENABLE_AGENT_LANE": is_agent_lane_enabled(),
        "UAWO_ENABLE_MCP_SOURCE": is_mcp_source_enabled(),
        "UAWO_ENABLE_EXTERNAL_TRACE_EXPORT": is_external_trace_export_enabled(),
        "UAWO_ENABLE_DURABLE_PILOT": is_durable_pilot_enabled(),
        "UAWO_ENABLE_SKILL_EXPORT": is_skill_export_enabled(),
    }
