from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_FILE_NAME = "workflow.toml"


@dataclass(frozen=True)
class ConfigValue:
    value: Any
    source: str


def _find_default_config_path(*, cwd: str | Path | None = None) -> Path | None:
    current = Path(cwd or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        config_path = candidate / DEFAULT_CONFIG_FILE_NAME
        if config_path.exists():
            return config_path
    return None


def resolve_config_path(
    *,
    explicit_path: str | Path | None = None,
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
) -> Path | None:
    environment = env or os.environ
    if explicit_path is not None:
        return Path(explicit_path).resolve()
    env_path = environment.get("WORKFLOW_CONFIG_PATH")
    if env_path:
        return Path(env_path).resolve()
    return _find_default_config_path(cwd=cwd)


def load_raw_workflow_config(
    *,
    explicit_path: str | Path | None = None,
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
) -> tuple[Path | None, dict[str, Any]]:
    path = resolve_config_path(explicit_path=explicit_path, env=env, cwd=cwd)
    if path is None or not path.exists():
        return path, {}
    with path.open("rb") as handle:
        return path, tomllib.load(handle)


def _get_nested(mapping: dict[str, Any], dotted_key: str) -> Any:
    current: Any = mapping
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}
    return bool(value)


def _coerce_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    return int(str(value).strip())


def _resolve_value(
    *,
    explicit: Any = None,
    explicit_source: str = "explicit",
    env: dict[str, str],
    env_key: str | None,
    config: dict[str, Any],
    config_key: str | None,
    default: Any,
    coerce: Any = None,
) -> ConfigValue:
    if explicit is not None:
        resolved = explicit
        source = explicit_source
    elif env_key and env_key in env and env[env_key] != "":
        resolved = env[env_key]
        source = f"env:{env_key}"
    elif config_key is not None:
        config_value = _get_nested(config, config_key)
        if config_value is not None:
            resolved = config_value
            source = f"toml:{config_key}"
        else:
            resolved = default
            source = "default"
    else:
        resolved = default
        source = "default"
    if coerce is not None:
        resolved = coerce(resolved)
    return ConfigValue(value=resolved, source=source)


def build_effective_config(
    *,
    explicit_db_path: str | Path | None = None,
    explicit_runtime_gateway_provider: str | None = None,
    explicit_config_path: str | Path | None = None,
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
) -> dict[str, Any]:
    environment = dict(env or os.environ)
    config_path, raw_config = load_raw_workflow_config(
        explicit_path=explicit_config_path,
        env=environment,
        cwd=cwd,
    )

    db_path = _resolve_value(
        explicit=Path(explicit_db_path).as_posix() if explicit_db_path is not None else None,
        env=environment,
        env_key="WORKFLOW_DB_PATH",
        config=raw_config,
        config_key="db.path",
        default="state/workflow.db",
        coerce=lambda item: Path(str(item)).as_posix(),
    )
    runtime_gateway_provider = _resolve_value(
        explicit=explicit_runtime_gateway_provider,
        env=environment,
        env_key="WORKFLOW_RUNTIME_GATEWAY",
        config=raw_config,
        config_key="runtime_gateway.provider",
        default="null",
        coerce=lambda item: str(item).strip().lower(),
    )
    config_values = {
        "db": {
            "path": db_path.value,
            "path_source": db_path.source,
        },
        "runtime_gateway": {
            "provider": runtime_gateway_provider.value,
            "provider_source": runtime_gateway_provider.source,
            "openai_model": _resolve_value(
                env=environment,
                env_key="WORKFLOW_OPENAI_MODEL",
                config=raw_config,
                config_key="runtime_gateway.openai_model",
                default="gpt-5.4-mini",
                coerce=str,
            ),
            "openai_reasoning_effort": _resolve_value(
                env=environment,
                env_key="WORKFLOW_OPENAI_REASONING_EFFORT",
                config=raw_config,
                config_key="runtime_gateway.openai_reasoning_effort",
                default="low",
                coerce=str,
            ),
        },
        "feature_flags": {
            "agent_lane": _resolve_value(
                env=environment,
                env_key="UAWO_ENABLE_AGENT_LANE",
                config=raw_config,
                config_key="feature_flags.agent_lane",
                default=False,
                coerce=_coerce_bool,
            ),
            "mcp_source": _resolve_value(
                env=environment,
                env_key="UAWO_ENABLE_MCP_SOURCE",
                config=raw_config,
                config_key="feature_flags.mcp_source",
                default=False,
                coerce=_coerce_bool,
            ),
            "external_trace_export": _resolve_value(
                env=environment,
                env_key="UAWO_ENABLE_EXTERNAL_TRACE_EXPORT",
                config=raw_config,
                config_key="feature_flags.external_trace_export",
                default=False,
                coerce=_coerce_bool,
            ),
            "durable_pilot": _resolve_value(
                env=environment,
                env_key="UAWO_ENABLE_DURABLE_PILOT",
                config=raw_config,
                config_key="feature_flags.durable_pilot",
                default=False,
                coerce=_coerce_bool,
            ),
            "skill_export": _resolve_value(
                env=environment,
                env_key="UAWO_ENABLE_SKILL_EXPORT",
                config=raw_config,
                config_key="feature_flags.skill_export",
                default=False,
                coerce=_coerce_bool,
            ),
            "external_worker_pools": _resolve_value(
                env=environment,
                env_key="UAWO_ENABLE_EXTERNAL_WORKER_POOLS",
                config=raw_config,
                config_key="feature_flags.external_worker_pools",
                default=False,
                coerce=_coerce_bool,
            ),
        },
        "agent": {
            "model": _resolve_value(
                env=environment,
                env_key="WORKFLOW_AGENT_MODEL",
                config=raw_config,
                config_key="agent.model",
                default="gpt-5.4-mini",
                coerce=str,
            )
        },
        "opencode": {
            "model": _resolve_value(
                env=environment,
                env_key="WORKFLOW_OPENCODE_MODEL",
                config=raw_config,
                config_key="opencode.model",
                default="openai/gpt-5.4-mini",
                coerce=str,
            ),
            "variant": _resolve_value(
                env=environment,
                env_key="WORKFLOW_OPENCODE_VARIANT",
                config=raw_config,
                config_key="opencode.variant",
                default=None,
            ),
        },
        "trace_exporter": {
            "provider": _resolve_value(
                env=environment,
                env_key="UAWO_TRACE_EXPORTER",
                config=raw_config,
                config_key="trace_exporter.provider",
                default="langfuse",
                coerce=lambda item: str(item).strip().lower(),
            ),
            "langfuse_endpoint": _resolve_value(
                env=environment,
                env_key="LANGFUSE_OTEL_ENDPOINT",
                config=raw_config,
                config_key="trace_exporter.langfuse_endpoint",
                default=environment.get("LANGFUSE_ENDPOINT"),
            ),
            "langfuse_api_key": _resolve_value(
                env=environment,
                env_key="LANGFUSE_API_KEY",
                config=raw_config,
                config_key="trace_exporter.langfuse_api_key",
                default=None,
            ),
            "langfuse_public_key": _resolve_value(
                env=environment,
                env_key="LANGFUSE_PUBLIC_KEY",
                config=raw_config,
                config_key="trace_exporter.langfuse_public_key",
                default=None,
            ),
        },
        "durable_pilot": {
            "provider": _resolve_value(
                env=environment,
                env_key="UAWO_DURABLE_PILOT_PROVIDER",
                config=raw_config,
                config_key="durable_pilot.provider",
                default="langgraph",
                coerce=lambda item: str(item).strip().lower(),
            ),
            "state_dir": _resolve_value(
                env=environment,
                env_key="UAWO_DURABLE_STATE_DIR",
                config=raw_config,
                config_key="durable_pilot.state_dir",
                default="state/durable",
                coerce=lambda item: Path(str(item)).as_posix(),
            ),
        },
        "worker_pools": {
            "default_pool_id": _resolve_value(
                env=environment,
                env_key="WORKFLOW_WORKER_POOL_ID",
                config=raw_config,
                config_key="worker_pools.default_pool_id",
                default=None,
            ),
            "seed_path": _resolve_value(
                env=environment,
                env_key="WORKFLOW_WORKER_POOL_SEED_PATH",
                config=raw_config,
                config_key="worker_pools.seed_path",
                default="infra/seeds/worker_pool_profiles.json",
                coerce=lambda item: Path(str(item)).as_posix(),
            ),
            "dispatch_timeout_seconds": _resolve_value(
                env=environment,
                env_key="WORKFLOW_WORKER_POOL_DISPATCH_TIMEOUT_SECONDS",
                config=raw_config,
                config_key="worker_pools.dispatch_timeout_seconds",
                default=60,
                coerce=_coerce_int,
            ),
        },
    }

    effective = {
        "config_path": config_path.as_posix() if config_path is not None else None,
        "db": config_values["db"],
        "runtime_gateway": {
            "provider": config_values["runtime_gateway"]["provider"],
            "provider_source": config_values["runtime_gateway"]["provider_source"],
            "openai_model": config_values["runtime_gateway"]["openai_model"].value,
            "openai_model_source": config_values["runtime_gateway"]["openai_model"].source,
            "openai_reasoning_effort": config_values["runtime_gateway"]["openai_reasoning_effort"].value,
            "openai_reasoning_effort_source": config_values["runtime_gateway"]["openai_reasoning_effort"].source,
        },
        "feature_flags": {
            key: {"enabled": value.value, "source": value.source}
            for key, value in config_values["feature_flags"].items()
        },
        "agent": {
            "model": config_values["agent"]["model"].value,
            "model_source": config_values["agent"]["model"].source,
        },
        "opencode": {
            "model": config_values["opencode"]["model"].value,
            "model_source": config_values["opencode"]["model"].source,
            "variant": config_values["opencode"]["variant"].value,
            "variant_source": config_values["opencode"]["variant"].source,
        },
        "trace_exporter": {
            "provider": config_values["trace_exporter"]["provider"].value,
            "provider_source": config_values["trace_exporter"]["provider"].source,
            "langfuse_endpoint": config_values["trace_exporter"]["langfuse_endpoint"].value,
            "langfuse_endpoint_source": config_values["trace_exporter"]["langfuse_endpoint"].source,
            "langfuse_api_key_present": bool(config_values["trace_exporter"]["langfuse_api_key"].value),
            "langfuse_api_key_source": config_values["trace_exporter"]["langfuse_api_key"].source,
            "langfuse_public_key_present": bool(config_values["trace_exporter"]["langfuse_public_key"].value),
            "langfuse_public_key_source": config_values["trace_exporter"]["langfuse_public_key"].source,
        },
        "durable_pilot": {
            "provider": config_values["durable_pilot"]["provider"].value,
            "provider_source": config_values["durable_pilot"]["provider"].source,
            "state_dir": config_values["durable_pilot"]["state_dir"].value,
            "state_dir_source": config_values["durable_pilot"]["state_dir"].source,
        },
        "worker_pools": {
            "default_pool_id": config_values["worker_pools"]["default_pool_id"].value,
            "default_pool_id_source": config_values["worker_pools"]["default_pool_id"].source,
            "seed_path": config_values["worker_pools"]["seed_path"].value,
            "seed_path_source": config_values["worker_pools"]["seed_path"].source,
            "dispatch_timeout_seconds": config_values["worker_pools"]["dispatch_timeout_seconds"].value,
            "dispatch_timeout_seconds_source": config_values["worker_pools"]["dispatch_timeout_seconds"].source,
        },
    }
    return effective

