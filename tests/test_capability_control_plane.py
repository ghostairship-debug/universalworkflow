from __future__ import annotations

from packages.contracts import CapabilityDescriptor, CapabilityProbeResult, MutationMode, TaskKind
from packages.core_domain.capability_plane import CapabilityPlane
from packages.core_domain.capability_control_plane import (
    evaluate_capability_policy,
    list_provider_contracts,
    provider_contract_for_key,
    provider_key_for_descriptor,
)


def _descriptor(adapter_name: str = "opencode") -> CapabilityDescriptor:
    return CapabilityDescriptor(
        capability_id=f"adapter_route:shell_exec:{adapter_name}",
        provider_kind="adapter_route",
        transport="local_cli",
        auth_mode="local_process",
        scopes=[adapter_name],
        allowed_task_kinds=[TaskKind.shell_exec],
        adapter_name=adapter_name,
        display_name=f"{adapter_name} route",
    )


def _verified_probe(provider: str = "opencode") -> CapabilityProbeResult:
    return CapabilityProbeResult(
        provider=provider,
        adapter_name=provider,
        status="verified_ready",
        live_probe=True,
        latency_ms=42,
        evidence_path=f"state/capability_probes/{provider}.json",
    )


def test_capability_policy_blocks_patch_apply_without_write_set() -> None:
    decision = evaluate_capability_policy(
        descriptor=_descriptor(),
        mutation_mode=MutationMode.patch_apply,
        requested_write_set=[],
        latest_probe_results={"opencode": _verified_probe()},
    )

    assert decision["decision"] == "blocked"
    assert "patch_apply_requires_write_set" in decision["reasons"]
    assert decision["live_proof"]["verified"] is True


def test_capability_policy_requires_live_probe_when_requested() -> None:
    decision = evaluate_capability_policy(
        descriptor=_descriptor("codex"),
        mutation_mode=MutationMode.artifact_only,
        requested_write_set=[],
        latest_probe_results={},
        require_live=True,
    )

    assert decision["decision"] == "needs_live_probe"
    assert decision["provider_key"] == "codex"
    assert "provider_live_proof_missing" in decision["reasons"]


def test_capability_policy_allows_verified_provider_with_write_set() -> None:
    decision = evaluate_capability_policy(
        descriptor=_descriptor(),
        mutation_mode=MutationMode.patch_apply,
        requested_write_set=["packages/example.py"],
        operator_receipt_id="opreceipt_demo",
        latest_probe_results={"opencode": _verified_probe()},
        require_live=True,
    )

    assert decision["decision"] == "allowed"
    assert decision["provider_key"] == "opencode"
    assert decision["operator_receipt_status"] == "present"
    assert decision["requested_write_set"] == ["packages/example.py"]
    assert decision["live_proof"]["status"] == "verified_ready"
    assert decision["provider_contract"]["route_role"] == "simple/free-model coding lane through OpenCode"


def test_capability_policy_requires_receipt_for_patch_apply() -> None:
    decision = evaluate_capability_policy(
        descriptor=_descriptor(),
        mutation_mode=MutationMode.patch_apply,
        requested_write_set=["packages/example.py"],
        latest_probe_results={"opencode": _verified_probe()},
        require_live=True,
    )

    assert decision["decision"] == "needs_receipt"
    assert decision["operator_receipt_status"] == "missing_for_mutation"
    assert "operator_receipt_not_attached_to_invocation" in decision["reasons"]


def test_provider_key_maps_external_adapter_aliases() -> None:
    assert provider_key_for_descriptor(_descriptor("mmx_multimodal")) == "mmx"
    assert provider_key_for_descriptor(_descriptor("vertex_multimodal")) == "vertex"
    assert provider_key_for_descriptor(_descriptor("claude_architect")) == "claude"
    assert provider_key_for_descriptor(_descriptor("langchain_agent")) == "langchain"


def test_provider_contract_registry_explains_vertex_and_gcloud_boundary() -> None:
    vertex = provider_contract_for_key("vertex")

    assert vertex is not None
    assert vertex["adapter_name"] == "vertex_multimodal"
    assert vertex["cli_dependency"] == "gcloud"
    assert any("Gemini CLI is not currently an adapter" in note for note in vertex["notes"])
    assert any("gcloud is a credential/environment tool" in note for note in vertex["notes"])
    assert "vertex_probe_failed" in vertex["failure_taxonomy"]
    assert {item["provider"] for item in list_provider_contracts()} >= {"codex", "opencode", "vertex", "mmx"}


def test_capability_plane_uses_provider_contract_failure_taxonomy() -> None:
    plane = CapabilityPlane()

    failure_classes = plane._failure_classes_for_descriptor(_descriptor("vertex_multimodal"))

    assert failure_classes == provider_contract_for_key("vertex")["failure_taxonomy"]
