from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import apps.operator_cli.doctor_payload as doctor_payload
from apps.operator_cli.main import app
from packages.contracts import AgentRoleType, ExecutionProfileDefinition, ExecutionScopeContext
from packages.core_domain.config import build_effective_config
from packages.core_domain.execution_profiles import resolve_execution_profile


def _effective(**env: str) -> dict[str, object]:
    return build_effective_config(env=env)


def test_m44_adaptive_routes_complex_coder_to_codex() -> None:
    resolved = resolve_execution_profile(
        effective_config=_effective(WORKFLOW_ADAPTIVE_LLM_ROUTING_ENABLED="1"),
        cluster_member_profile=ExecutionProfileDefinition(adapter_name="agent"),
        scope_context=ExecutionScopeContext(
            cluster_template_id="dev_cluster",
            cluster_member_id="dev_cluster_implementer",
            public_role=AgentRoleType.coder,
            role_label="implementer",
        ),
    )

    assert resolved.adapter_name == "codex"
    assert resolved.selected_model == "gpt-5.5"
    assert resolved.model_selection_source == "adaptive_llm_router"
    assert resolved.adaptive_route_tier == "complex"
    assert resolved.source_map["adapter_name"]["original_value"] == "agent"


def test_m44_adaptive_routes_review_to_deepseek_flash() -> None:
    resolved = resolve_execution_profile(
        effective_config=_effective(WORKFLOW_ADAPTIVE_LLM_ROUTING_ENABLED="1"),
        cluster_member_profile=ExecutionProfileDefinition(adapter_name="agent"),
        scope_context=ExecutionScopeContext(
            cluster_template_id="review_cluster",
            cluster_member_id="review_cluster_test_sentinel",
            public_role=AgentRoleType.reviewer,
            role_label="test_sentinel",
        ),
    )

    assert resolved.adapter_name == "agent"
    assert resolved.selected_model == "deepseek/deepseek-v4-flash"
    assert resolved.model_selection_source == "adaptive_llm_router"
    assert resolved.adaptive_route_tier == "medium"


def test_m44_adaptive_routes_simple_research_to_minimax() -> None:
    resolved = resolve_execution_profile(
        effective_config=_effective(WORKFLOW_ADAPTIVE_LLM_ROUTING_ENABLED="1"),
        cluster_member_profile=ExecutionProfileDefinition(adapter_name="agent"),
        scope_context=ExecutionScopeContext(
            cluster_template_id="search_cluster",
            cluster_member_id="search_cluster_scout",
            public_role=AgentRoleType.researcher,
            role_label="search_scout",
        ),
    )

    assert resolved.adapter_name == "agent"
    assert resolved.selected_model == "minimax/MiniMax-M2.7"
    assert resolved.model_selection_source == "adaptive_llm_router"
    assert resolved.adaptive_route_tier == "simple"


def test_m44_strong_dogfood_still_overrides_adaptive_routing() -> None:
    resolved = resolve_execution_profile(
        effective_config=_effective(
            WORKFLOW_ADAPTIVE_LLM_ROUTING_ENABLED="1",
            WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED="1",
            WORKFLOW_DOGFOOD_EXECUTION_BACKEND="codex_cli",
            WORKFLOW_DOGFOOD_MODEL="gpt-5.5",
            WORKFLOW_DOGFOOD_REASONING_EFFORT="xhigh",
        ),
        cluster_member_profile=ExecutionProfileDefinition(adapter_name="agent"),
        scope_context=ExecutionScopeContext(
            cluster_template_id="search_cluster",
            cluster_member_id="search_cluster_scout",
            public_role=AgentRoleType.researcher,
            role_label="search_scout",
        ),
    )

    assert resolved.adapter_name == "codex"
    assert resolved.selected_model == "gpt-5.5"
    assert resolved.model_selection_source == "dogfood_strong_codex_cli"
    assert resolved.adaptive_route_tier is None


def test_m44_doctor_projects_adaptive_routing(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    db_path = tmp_path / "workflow.db"
    monkeypatch.setenv("WORKFLOW_ADAPTIVE_LLM_ROUTING_ENABLED", "1")
    monkeypatch.setattr(doctor_payload.shutil, "which", lambda name: f"C:/fake/{name}.exe")

    result = runner.invoke(app, ["--db-path", str(db_path), "doctor"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    adaptive = payload["external_capabilities"]["adaptive_llm_routing"]
    assert adaptive["status"] == "enabled"
    assert adaptive["simple_model"] == "minimax/MiniMax-M2.7"
    assert adaptive["medium_model"] == "deepseek/deepseek-v4-flash"
    assert adaptive["complex_model"] == "gpt-5.5"
    assert adaptive["coding_adapter"] == "codex"


def test_m46_doctor_projects_dynamic_cluster_routing(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    db_path = tmp_path / "workflow.db"
    monkeypatch.setenv("WORKFLOW_DYNAMIC_CLUSTER_ROUTING_ENABLED", "1")
    monkeypatch.setattr(doctor_payload.shutil, "which", lambda name: f"C:/fake/{name}.exe")

    result = runner.invoke(app, ["--db-path", str(db_path), "doctor"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    dynamic = payload["external_capabilities"]["dynamic_cluster_routing"]
    assert dynamic["status"] == "enabled"
    assert dynamic["strategy"] == "compose_specialized_clusters"
    assert dynamic["default_order"][:3] == ["multimodal_cluster", "search_cluster", "design_cluster"]
