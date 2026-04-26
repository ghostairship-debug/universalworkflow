from __future__ import annotations

from typing import Any

from packages.contracts import CapabilityDescriptor, CapabilityProbeResult, MutationMode
from packages.core_domain.provider_access import list_provider_access_contracts, provider_access_contract_for_key


ADAPTER_PROVIDER_KEYS = {
    "shell": "shell",
    "codex": "codex",
    "opencode": "opencode",
    "mmx_multimodal": "mmx",
    "vertex_multimodal": "vertex",
    "claude_architect": "claude",
    "langchain_agent": "langchain",
    "agent": "langchain",
}

PROVIDER_CONTRACTS: dict[str, dict[str, Any]] = {
    "shell": {
        "provider": "shell",
        "adapter_name": "shell",
        "cli_dependency": "local_python",
        "auth_sources": ["local_process"],
        "route_role": "local deterministic shell/noop baseline",
        "failure_taxonomy": ["execution_failed", "artifact_missing", "timeout", "process_launch_failed"],
        "notes": ["Shell is local-only and does not require external credentials."],
    },
    "codex": {
        "provider": "codex",
        "adapter_name": "codex",
        "cli_dependency": "codex",
        "auth_sources": ["codex_cli_login", "OPENAI_API_KEY"],
        "route_role": "strong coding fallback and complex local CLI worker",
        "failure_taxonomy": ["adapter_unavailable", "provider_auth_missing", "provider_timeout", "execution_failed"],
        "notes": [
            "Codex remains the medium/complex fallback when cheaper lanes fail.",
            "Current OpenAI-family execution is through Codex CLI; OPENAI_API_KEY is not assumed.",
        ],
    },
    "opencode": {
        "provider": "opencode",
        "adapter_name": "opencode",
        "cli_dependency": "opencode",
        "auth_sources": ["MINIMAX_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"],
        "route_role": "simple/free-model coding lane through OpenCode",
        "failure_taxonomy": ["adapter_unavailable", "provider_auth_missing", "artifact_output_mismatch", "execution_failed"],
        "notes": [
            "Default simple lane model is minimax/MiniMax-M2.7 unless overridden.",
            "OMO/OpenCode plugin ecosystem is not integrated in this repository yet.",
        ],
    },
    "mmx": {
        "provider": "mmx",
        "adapter_name": "mmx_multimodal",
        "cli_dependency": "mmx",
        "auth_sources": ["MINIMAX_API_KEY", "MINIMAX_TOKEN"],
        "route_role": "MiniMax multimodal evidence lane",
        "failure_taxonomy": ["adapter_unavailable", "provider_auth_missing", "multimodal_probe_failed", "execution_failed"],
        "notes": [
            "MMX text evidence is not the same as OpenCode using a MiniMax text model.",
            "True MiniMax image/speech/music generation is represented by mmx_generation_api.",
        ],
    },
    "vertex": {
        "provider": "vertex",
        "adapter_name": "vertex_multimodal",
        "cli_dependency": "gcloud",
        "auth_sources": ["GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT"],
        "route_role": "Vertex/GCP Gemini-family multimodal entrypoint",
        "failure_taxonomy": ["adapter_unavailable", "gcloud_missing", "provider_auth_missing", "vertex_probe_failed"],
        "notes": [
            "Gemini CLI is not currently an adapter.",
            "Gemini-family access currently goes through Vertex.",
            "gcloud is a credential/environment tool, not an independent worker adapter.",
            "True Vertex Imagen image generation and Gemini visual review are represented by vertex_generation_api.",
            "Cloud Text-to-Speech is represented separately by gcp_tts_api.",
        ],
    },
    "claude": {
        "provider": "claude",
        "adapter_name": "claude_architect",
        "cli_dependency": "claude",
        "auth_sources": ["ANTHROPIC_API_KEY", "claude_cli_login"],
        "route_role": "architect/review artifact lane",
        "failure_taxonomy": ["adapter_unavailable", "provider_auth_missing", "artifact_missing", "execution_failed"],
        "notes": ["Claude is an external artifact adapter and should not mutate repo state directly."],
    },
    "langchain": {
        "provider": "langchain",
        "adapter_name": "langchain_agent",
        "cli_dependency": "python_langchain_deps",
        "auth_sources": ["MINIMAX_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"],
        "route_role": "agent fallback abstraction over configured chat providers",
        "failure_taxonomy": ["dependency_missing", "provider_auth_missing", "agent_runtime_failed", "fallback_route_failed"],
        "notes": ["LangChain provider selection is route-dependent; fallback-only output is not verified_ready."],
    },
}


def provider_contract_for_key(provider_key: str | None) -> dict[str, Any] | None:
    if provider_key is None:
        return None
    contract = PROVIDER_CONTRACTS.get(str(provider_key).strip().lower())
    if contract is not None:
        return dict(contract)
    access_contract = provider_access_contract_for_key(provider_key)
    if access_contract is None:
        return None
    return {
        "provider": access_contract["provider_key"],
        "adapter_name": None,
        "cli_dependency": None,
        "auth_sources": list(access_contract.get("auth_sources") or []),
        "route_role": access_contract.get("role") or "",
        "failure_taxonomy": list(access_contract.get("failure_taxonomy") or []),
        "notes": list(access_contract.get("notes") or []),
        "category": access_contract.get("category"),
        "transport": access_contract.get("transport"),
        "modalities": list(access_contract.get("modalities") or []),
        "default_model": access_contract.get("default_model"),
    }


def list_provider_contracts() -> list[dict[str, Any]]:
    contracts = [dict(PROVIDER_CONTRACTS[key]) for key in sorted(PROVIDER_CONTRACTS)]
    existing = {str(item["provider"]) for item in contracts if item.get("provider")}
    for item in list_provider_access_contracts():
        provider_key = str(item["provider_key"])
        if provider_key in existing:
            continue
        contracts.append(
            {
                "provider": provider_key,
                "adapter_name": None,
                "cli_dependency": None,
                "auth_sources": list(item.get("auth_sources") or []),
                "route_role": item.get("role") or "",
                "failure_taxonomy": list(item.get("failure_taxonomy") or []),
                "notes": list(item.get("notes") or []),
                "category": item.get("category"),
                "transport": item.get("transport"),
                "modalities": list(item.get("modalities") or []),
                "default_model": item.get("default_model"),
            }
        )
    return sorted(contracts, key=lambda item: str(item.get("provider") or ""))


def provider_key_for_descriptor(descriptor: CapabilityDescriptor) -> str:
    if descriptor.provider_kind == "adapter_route" and descriptor.adapter_name:
        return ADAPTER_PROVIDER_KEYS.get(str(descriptor.adapter_name), str(descriptor.adapter_name))
    if descriptor.provider_kind == "runtime_gateway" and descriptor.scopes:
        return str(descriptor.scopes[0])
    if descriptor.provider_kind in {"api_model", "cli_agent", "asset_generator", "mcp_tool", "experimental_agent_framework"} and descriptor.scopes:
        return str(descriptor.scopes[0])
    if descriptor.profile_id:
        return str(descriptor.profile_id)
    return str(descriptor.provider_kind)


def probe_result_payload(result: CapabilityProbeResult | dict[str, Any] | None) -> dict[str, Any]:
    if result is None:
        return {"status": "not_probed", "verified": False}
    payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else dict(result)
    status = str(payload.get("status") or "not_probed")
    return {
        "status": status,
        "verified": status == "verified_ready" and bool(payload.get("live_probe")),
        "live_probe": bool(payload.get("live_probe")),
        "provider": payload.get("provider"),
        "adapter_name": payload.get("adapter_name"),
        "latency_ms": payload.get("latency_ms"),
        "failure_class": payload.get("failure_class"),
        "evidence_path": payload.get("evidence_path"),
        "fallback_route": payload.get("fallback_route"),
        "auth_source": payload.get("auth_source"),
    }


def evaluate_capability_policy(
    *,
    descriptor: CapabilityDescriptor,
    mutation_mode: MutationMode | str | None = None,
    requested_write_set: list[str] | None = None,
    operator_receipt_id: str | None = None,
    latest_probe_results: dict[str, CapabilityProbeResult | dict[str, Any]] | None = None,
    require_live: bool = True,
) -> dict[str, Any]:
    provider_key = provider_key_for_descriptor(descriptor)
    normalized_mutation_mode = str(mutation_mode) if mutation_mode is not None else None
    normalized_write_set = sorted(str(item) for item in (requested_write_set or []))
    latest_probe_results = latest_probe_results or {}
    live_proof = probe_result_payload(latest_probe_results.get(provider_key))
    reasons: list[str] = []
    decision = "allowed"

    if normalized_mutation_mode == str(MutationMode.patch_apply) and not normalized_write_set:
        decision = "blocked"
        reasons.append("patch_apply_requires_write_set")

    if require_live and not live_proof["verified"]:
        reasons.append("provider_live_proof_missing")
        if decision != "blocked":
            decision = "needs_live_probe"

    if operator_receipt_id:
        receipt_status = "present"
    elif normalized_mutation_mode == str(MutationMode.patch_apply):
        receipt_status = "missing_for_mutation"
        reasons.append("operator_receipt_not_attached_to_invocation")
        if decision == "allowed":
            decision = "needs_receipt"
    else:
        receipt_status = "not_required"

    return {
        "schema_version": "m69_capability_policy_v1",
        "decision": decision,
        "provider_key": provider_key,
        "provider_contract": provider_contract_for_key(provider_key),
        "provider_kind": descriptor.provider_kind,
        "capability_id": descriptor.capability_id,
        "adapter_name": descriptor.adapter_name,
        "mutation_mode": normalized_mutation_mode,
        "requested_write_set": normalized_write_set,
        "operator_receipt_id": operator_receipt_id,
        "operator_receipt_status": receipt_status,
        "require_live": require_live,
        "live_proof": live_proof,
        "reasons": reasons,
    }
