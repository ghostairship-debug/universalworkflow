from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from packages.contracts import CapabilityDescriptor, CapabilityProbeResult, MutationMode, TaskKind
from packages.core_domain.capability_plane import CapabilityPlane
from packages.core_domain.capability_control_plane import (
    evaluate_capability_policy,
    list_provider_contracts,
    provider_contract_for_key,
    provider_key_for_descriptor,
)
from packages.core_domain.db import migrate
from packages.core_domain.errors import CapabilityPolicyEnforcementError
from packages.core_domain.services import OrchestratorService
from packages.worker_adapters.opencode_adapter import OpenCodeAdapter
from packages.worker_adapters.router import WorkerRouter


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


def _fake_patch_runner(_command, **_kwargs):
    patch_text = "--- target.txt\n+++ target.txt\n@@ -1 +1 @@\n-before\n+after\n"
    return subprocess.CompletedProcess(
        args=_command,
        returncode=0,
        stdout=patch_text,
        stderr="",
    )


def test_capability_enforcement_pilot_blocks_real_patch_path_without_receipt_or_live_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKFLOW_CAPABILITY_ENFORCEMENT_PILOT_ENABLED", "1")
    target = tmp_path / "target.txt"
    target.write_text("before\n", encoding="utf-8")
    migrate(tmp_path / "workflow.db")
    service = OrchestratorService(
        tmp_path / "workflow.db",
        workspace_root=tmp_path,
        worker_router=WorkerRouter([OpenCodeAdapter(runner=_fake_patch_runner)]),
    )
    run = service.create_run(goal="enforced patch", preset_id="feature_delivery")
    service.compile_run(
        run.run_id,
        adapter_name="opencode",
        mutation_mode="patch_apply",
        write_set=["target.txt"],
        task_card_ref="enforced-card",
    )

    with pytest.raises(CapabilityPolicyEnforcementError) as excinfo:
        service.resume_run(run.run_id)

    assert excinfo.value.details["decision"] in {"needs_live_probe", "needs_receipt"}
    assert "provider_live_proof_missing" in excinfo.value.details["reasons"]
    assert target.read_text(encoding="utf-8") == "before\n"


def test_patch_apply_blocks_without_receipt_even_when_pilot_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WORKFLOW_CAPABILITY_ENFORCEMENT_PILOT_ENABLED", raising=False)
    target = tmp_path / "target.txt"
    target.write_text("before\n", encoding="utf-8")
    migrate(tmp_path / "workflow.db")
    service = OrchestratorService(
        tmp_path / "workflow.db",
        workspace_root=tmp_path,
        worker_router=WorkerRouter([OpenCodeAdapter(runner=_fake_patch_runner)]),
    )
    service.capability_probe_result_repo.create(_verified_probe("opencode"))
    run = service.create_run(goal="receipt required patch", preset_id="feature_delivery")
    service.compile_run(
        run.run_id,
        adapter_name="opencode",
        mutation_mode="patch_apply",
        write_set=["target.txt"],
        task_card_ref="receipt-required-card",
    )

    with pytest.raises(CapabilityPolicyEnforcementError) as excinfo:
        service.resume_run(run.run_id)

    assert excinfo.value.details["decision"] == "needs_receipt"
    assert "operator_receipt_not_attached_to_invocation" in excinfo.value.details["reasons"]
    assert target.read_text(encoding="utf-8") == "before\n"


def test_capability_enforcement_pilot_allows_real_patch_path_with_receipt_and_live_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKFLOW_CAPABILITY_ENFORCEMENT_PILOT_ENABLED", "1")
    target = tmp_path / "target.txt"
    target.write_text("before\n", encoding="utf-8")
    migrate(tmp_path / "workflow.db")
    service = OrchestratorService(
        tmp_path / "workflow.db",
        workspace_root=tmp_path,
        worker_router=WorkerRouter([OpenCodeAdapter(runner=_fake_patch_runner)]),
    )
    service.capability_probe_result_repo.create(_verified_probe("opencode"))
    run = service.create_run(goal="allowed patch", preset_id="feature_delivery")
    service.compile_run(
        run.run_id,
        adapter_name="opencode",
        mutation_mode="patch_apply",
        write_set=["target.txt"],
        task_card_ref="allowed-card",
    )

    bundle = service.resume_run(run.run_id, operator_receipt_id="opreceipt_allowed")

    assert bundle.run.status == "completed"
    assert target.read_text(encoding="utf-8") == "after\n"
    detail = service.get_status_detail(run.run_id)
    receipt = detail["last_runtime_state"]["state_payload"]["capability_execution_receipt"]
    assert receipt["operator_receipt_id"] == "opreceipt_allowed"
    assert receipt["policy_decision"]["decision"] == "allowed"
