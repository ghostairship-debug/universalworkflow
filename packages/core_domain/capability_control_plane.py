from __future__ import annotations

from typing import Any

from packages.contracts import CapabilityDescriptor, CapabilityProbeResult, MutationMode


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


def provider_key_for_descriptor(descriptor: CapabilityDescriptor) -> str:
    if descriptor.provider_kind == "adapter_route" and descriptor.adapter_name:
        return ADAPTER_PROVIDER_KEYS.get(str(descriptor.adapter_name), str(descriptor.adapter_name))
    if descriptor.provider_kind == "runtime_gateway" and descriptor.scopes:
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
