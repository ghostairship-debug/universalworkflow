from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from packages.core_domain.provider_access import provider_access_contract_for_key


ROUTE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "lane": "image_or_sprite",
        "primary_provider": "mmx_generation_api",
        "fallback_provider": "vertex_generation_api",
        "required_modalities": ["image"],
        "asset_examples": ["ui_theme_reference", "gameplay_tiles", "panel_backgrounds", "button_states"],
    },
    {
        "lane": "speech_or_voice",
        "primary_provider": "mmx_generation_api",
        "fallback_provider": "gcp_tts_api",
        "required_modalities": ["audio"],
        "asset_examples": ["short_voice_prompt", "tutorial_voice"],
    },
    {
        "lane": "music_or_sfx",
        "primary_provider": "mmx_generation_api",
        "fallback_provider": None,
        "required_modalities": ["music", "audio"],
        "asset_examples": ["short_loop_music", "success_sfx", "failure_sfx"],
    },
    {
        "lane": "visual_review",
        "primary_provider": "vertex_generation_api",
        "fallback_provider": "rule_based_screenshot_checklist",
        "required_modalities": ["vision_review"],
        "asset_examples": ["screenshot_quality_review", "ui_overlap_review"],
    },
)


def build_multimodal_route_plan(environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    env = os.environ if environ is None else environ
    lanes = [_build_lane(spec, env) for spec in ROUTE_SPECS]
    return {
        "schema_version": "m109_multimodal_route_plan_v1",
        "route_policy": "api_first_with_live_proof_required",
        "mmx_cli_policy": "compatibility_probe_or_temporary_evidence_only_not_primary_asset_generation",
        "verified_ready_policy": "Only provider-specific live proof can set verified_ready true.",
        "lanes": lanes,
        "go_no_go": "GO" if lanes and all(lane["route_status"] in {"configured_needs_live_proof", "blocked_auth_missing"} for lane in lanes) else "NO-GO",
    }


def _build_lane(spec: dict[str, Any], env: Mapping[str, str]) -> dict[str, Any]:
    primary = provider_access_contract_for_key(str(spec["primary_provider"])) or {}
    fallback_key = spec.get("fallback_provider")
    fallback = provider_access_contract_for_key(str(fallback_key)) if fallback_key and str(fallback_key).endswith("_api") else None
    auth_sources = list(primary.get("auth_sources") or [])
    present_auth = [source for source in auth_sources if _auth_source_present(source, env)]
    route_status = "configured_needs_live_proof" if present_auth else "blocked_auth_missing"
    return {
        "lane": spec["lane"],
        "primary_provider": primary.get("provider_key") or spec["primary_provider"],
        "primary_display_name": primary.get("display_name"),
        "fallback_provider": (fallback or {}).get("provider_key") or fallback_key,
        "fallback_display_name": (fallback or {}).get("display_name") if fallback else None,
        "required_modalities": list(spec["required_modalities"]),
        "asset_examples": list(spec["asset_examples"]),
        "auth_sources": auth_sources,
        "auth_sources_present": present_auth,
        "route_status": route_status,
        "verified_ready": False,
        "live_proof_required": True,
        "failure_taxonomy": list(primary.get("failure_taxonomy") or []),
    }


def _auth_source_present(source: str, env: Mapping[str, str]) -> bool:
    if source in {"gcloud_adc", "codex_cli_login", "opencode_auth"}:
        return False
    return bool(env.get(source))
