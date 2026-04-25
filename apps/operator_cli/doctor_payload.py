from __future__ import annotations

import os
import shutil
import sys
from importlib import metadata
from pathlib import Path

import typer

from apps.operator_cli.shared import _db_path_from_context, _workspace_root_from_context
from packages.core_domain.capability_plane import (
    DEFAULT_MCP_PROFILE_SEED_PATH,
    load_seed_mcp_server_profiles,
    mcp_dependency_available,
    mcp_dependency_reason,
)
from packages.core_domain.config import build_effective_config
from packages.core_domain.db import DEFAULT_DB_PATH, get_migration_status, workspace_scoped_db_path
from packages.core_domain.external_workers import validate_callback_base_url
from packages.worker_adapters.langchain_agent_adapter import describe_langchain_agent_llm

def _package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _optional_command_status(name: str) -> dict[str, object]:
    path = shutil.which(name)
    return {
        "name": name,
        "status": "available" if path else "missing",
        "path": path,
        "required": False,
    }


def _redacted_env_status(names: list[str]) -> dict[str, dict[str, object]]:
    return {
        name: {
            "present": bool(os.getenv(name)),
            "value": "[REDACTED]" if os.getenv(name) else None,
        }
        for name in names
    }


def _any_env_present(names: list[str]) -> bool:
    return any(bool(os.getenv(name)) for name in names)


def _env_bool(name: str) -> bool:
    return str(os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _external_capability_status(effective: dict[str, object], optional_commands: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    claude_config = effective.get("claude_architect", {}) if isinstance(effective, dict) else {}
    multimodal_config = effective.get("multimodal", {}) if isinstance(effective, dict) else {}
    dogfood_config = effective.get("dogfood", {}) if isinstance(effective, dict) else {}
    adaptive_config = effective.get("adaptive_llm_routing", {}) if isinstance(effective, dict) else {}
    dogfood_enabled = bool(dogfood_config.get("strong_model_enabled")) if isinstance(dogfood_config, dict) else False
    dogfood_backend = (
        str(dogfood_config.get("execution_backend") or "codex_cli")
        if isinstance(dogfood_config, dict)
        else "codex_cli"
    )
    langchain_agent = describe_langchain_agent_llm(effective_config=effective if isinstance(effective, dict) else None)
    if not dogfood_enabled:
        dogfood_status = "disabled"
    elif dogfood_backend == "codex_cli":
        dogfood_status = "ready" if optional_commands["codex"]["status"] == "available" else "missing_cli"
    elif dogfood_backend == "agent_lane":
        dogfood_status = "ready" if langchain_agent["status"] == "ready" else str(langchain_agent["status"])
    else:
        dogfood_status = "degraded"

    claude_cli_status = optional_commands["claude"]["status"]
    claude_enabled = bool(claude_config.get("enabled")) if isinstance(claude_config, dict) else False
    if claude_cli_status != "available":
        claude_status = "missing_cli"
    elif not claude_enabled:
        claude_status = "disabled"
    else:
        claude_status = "quota_guarded"

    mmx_cli_status = optional_commands["mmx"]["status"]
    if mmx_cli_status != "available":
        mmx_status = "missing_cli"
    elif not _any_env_present(["MINIMAX_API_KEY", "MINIMAX_TOKEN"]):
        mmx_status = "missing_auth"
    else:
        mmx_status = "ready"

    vertex_cli_status = optional_commands["gcloud"]["status"]
    if vertex_cli_status != "available":
        vertex_status = "missing_cli"
    elif not _any_env_present(["GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT", "CLOUDSDK_CONFIG"]):
        vertex_status = "missing_auth"
    else:
        vertex_status = "ready"

    return {
        "dogfood_strong_model": {
            "status": dogfood_status,
            "enabled": dogfood_enabled,
            "execution_backend": dogfood_backend,
            "model": dogfood_config.get("model") if isinstance(dogfood_config, dict) else "gpt-5.5",
            "codex_model": (
                (dogfood_config.get("codex_model") or dogfood_config.get("model"))
                if isinstance(dogfood_config, dict)
                else "gpt-5.5"
            ),
            "reasoning_effort": (
                dogfood_config.get("reasoning_effort") if isinstance(dogfood_config, dict) else "xhigh"
            ),
            "auth": "codex_cli_login" if dogfood_backend == "codex_cli" else langchain_agent.get("auth"),
        },
        "langchain_agent": {
            "status": langchain_agent["status"],
            "provider": langchain_agent["provider"],
            "model": langchain_agent["model"],
            "base_url": langchain_agent["base_url"],
            "auth": langchain_agent["auth"],
            "fallback_provider": langchain_agent["fallback_provider"],
            "fallback_model": langchain_agent["fallback_model"],
            "degraded_reason": langchain_agent["degraded_reason"],
        },
        "adaptive_llm_routing": {
            "status": "enabled" if bool(adaptive_config.get("enabled")) else "disabled",
            "enabled": bool(adaptive_config.get("enabled")) if isinstance(adaptive_config, dict) else False,
            "simple_model": (
                adaptive_config.get("simple_model") if isinstance(adaptive_config, dict) else "minimax/MiniMax-M2.7"
            ),
            "medium_model": (
                adaptive_config.get("medium_model") if isinstance(adaptive_config, dict) else "deepseek/deepseek-v4-flash"
            ),
            "complex_model": (
                adaptive_config.get("complex_model") if isinstance(adaptive_config, dict) else "minimax/MiniMax-M2.7"
            ),
            "coding_adapter": adaptive_config.get("coding_adapter") if isinstance(adaptive_config, dict) else "opencode",
        },
        "dynamic_cluster_routing": {
            "status": "enabled" if _env_bool("WORKFLOW_DYNAMIC_CLUSTER_ROUTING_ENABLED") else "disabled",
            "enabled": _env_bool("WORKFLOW_DYNAMIC_CLUSTER_ROUTING_ENABLED"),
            "strategy": "compose_specialized_clusters",
            "default_order": ["multimodal_cluster", "search_cluster", "design_cluster", "dev_cluster", "review_cluster"],
        },
        "claude_architect": {
            "status": claude_status,
            "cli": claude_config.get("cli") if isinstance(claude_config, dict) else "claude",
            "quota_guarded": True,
            "max_calls_per_session": (
                claude_config.get("max_calls_per_session") if isinstance(claude_config, dict) else 1
            ),
            "enabled": claude_enabled,
        },
        "mmx_multimodal": {
            "status": mmx_status,
            "cli": multimodal_config.get("mmx_cli") if isinstance(multimodal_config, dict) else "mmx",
            "role": "primary" if isinstance(multimodal_config, dict) and multimodal_config.get("primary") == "mmx" else "available",
        },
        "vertex_multimodal": {
            "status": vertex_status,
            "cli": multimodal_config.get("vertex_cli") if isinstance(multimodal_config, dict) else "gcloud",
            "role": "fallback" if isinstance(multimodal_config, dict) and multimodal_config.get("fallback") == "vertex" else "available",
        },
    }


def _state_path_status(db_path: str | Path, *, workspace_root: str | Path | None = None) -> dict[str, object]:
    state_dir = Path(db_path).expanduser().parent
    if not state_dir.is_absolute():
        state_dir = (Path(workspace_root or Path.cwd()) / state_dir).resolve()
    probe_target = state_dir if state_dir.exists() else state_dir.parent
    return {
        "path": state_dir.as_posix(),
        "exists": state_dir.exists(),
        "writable": os.access(probe_target, os.W_OK) if probe_target.exists() else False,
        "db_path": Path(db_path).as_posix(),
    }


def _worker_pool_boundary_status(effective: dict[str, object]) -> dict[str, object]:
    worker_pools = effective.get("worker_pools", {}) if isinstance(effective, dict) else {}
    callback_base_url = worker_pools.get("callback_base_url") if isinstance(worker_pools, dict) else None
    allowed_callback_origins = worker_pools.get("allowed_callback_origins") if isinstance(worker_pools, dict) else []
    if not isinstance(allowed_callback_origins, list):
        allowed_callback_origins = []
    if not callback_base_url:
        callback_status = "no_callback_base_url"
        callback_reason = None
    else:
        try:
            validate_callback_base_url(str(callback_base_url), [str(item) for item in allowed_callback_origins])
        except RuntimeError as exc:
            callback_status = "blocked"
            callback_reason = str(exc)
        else:
            callback_status = "allowed"
            callback_reason = None
    return {
        "callback_base_url": callback_base_url,
        "callback_base_url_source": worker_pools.get("callback_base_url_source") if isinstance(worker_pools, dict) else None,
        "allowed_callback_origins": allowed_callback_origins,
        "allowed_callback_origins_source": (
            worker_pools.get("allowed_callback_origins_source") if isinstance(worker_pools, dict) else None
        ),
        "callback_origin_status": callback_status,
        "callback_origin_reason": callback_reason,
        "shared_secret_present": worker_pools.get("shared_secret_present") if isinstance(worker_pools, dict) else None,
        "shared_secret_source": worker_pools.get("shared_secret_source") if isinstance(worker_pools, dict) else None,
    }


def _build_doctor_payload(ctx: typer.Context) -> dict[str, object]:
    effective = ctx.obj["effective_config"]
    optional_commands = {
        command_name: _optional_command_status(command_name)
        for command_name in ("opencode", "codex", "claude", "mmx", "gcloud")
    }
    external_capabilities = _external_capability_status(effective, optional_commands)
    state_path = _state_path_status(effective["db"]["path"], workspace_root=effective.get("workspace", {}).get("root"))
    worker_pool_boundaries = _worker_pool_boundary_status(effective)
    profiles = load_seed_mcp_server_profiles(DEFAULT_MCP_PROFILE_SEED_PATH)
    pytest_version = _package_version("pytest")
    mcp_available = mcp_dependency_available()
    issues: list[dict[str, object]] = []
    for command_name, command_status in optional_commands.items():
        if command_status["status"] != "available":
            issues.append(
                {
                    "kind": "optional_command_missing",
                    "command": command_name,
                    "severity": "degraded",
                }
            )
    for capability_name, capability_status in external_capabilities.items():
        if capability_status["status"] in {"missing_auth", "missing_cli"}:
            issues.append(
                {
                    "kind": "external_capability_degraded",
                    "capability": capability_name,
                    "status": capability_status["status"],
                    "severity": "degraded",
                }
            )
    if pytest_version is None:
        issues.append({"kind": "pytest_missing", "severity": "degraded"})
    if not state_path["writable"]:
        issues.append({"kind": "state_path_not_writable", "severity": "degraded"})
    if profiles and not mcp_available:
        issues.append(
            {
                "kind": "mcp_dependency_missing",
                "severity": "degraded",
                "reason": mcp_dependency_reason(),
            }
        )
    if worker_pool_boundaries["callback_origin_status"] == "blocked":
        issues.append(
            {
                "kind": "worker_callback_origin_blocked",
                "severity": "degraded",
                "reason": worker_pool_boundaries["callback_origin_reason"],
            }
        )
    return {
        "status": "ok" if not issues else "degraded",
        "read_only": True,
        "python": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
        },
        "pytest": {
            "status": "available" if pytest_version else "missing",
            "version": pytest_version,
        },
        "state_path": state_path,
        "workspace": effective.get("workspace", {}),
        "optional_commands": optional_commands,
        "external_capabilities": external_capabilities,
        "worker_pool_boundaries": worker_pool_boundaries,
        "mcp": {
            "seed_path": DEFAULT_MCP_PROFILE_SEED_PATH.as_posix(),
            "profile_count": len(profiles),
            "enabled_profile_count": len([profile for profile in profiles if profile.enabled]),
            "dependency_available": mcp_available,
            "dependency_reason": mcp_dependency_reason(),
        },
        "environment": {
            "secrets": _redacted_env_status(
                [
                    "OPENAI_API_KEY",
                    "ANTHROPIC_API_KEY",
                    "DEEPSEEK_API_KEY",
                    "MINIMAX_API_KEY",
                    "MINIMAX_TOKEN",
                    "GOOGLE_APPLICATION_CREDENTIALS",
                    "GOOGLE_CLOUD_PROJECT",
                    "GCLOUD_PROJECT",
                    "GITHUB_TOKEN",
                    "WORKFLOW_REMOTE_WORKER_SHARED_SECRET",
                ]
            ),
            "feature_flags": effective["feature_flags"],
        },
        "issues": issues,
    }
