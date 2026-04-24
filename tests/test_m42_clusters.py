from __future__ import annotations

from pathlib import Path

from packages.contracts import AgentRoleType
from packages.core_domain.cluster_router import ClusterRouter
from packages.core_domain.db import migrate
from packages.core_domain.interaction_catalog import list_default_cluster_templates
from packages.core_domain.repositories import PresetRepository
from packages.core_domain.services import OrchestratorService


def _service(tmp_path: Path) -> OrchestratorService:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    return OrchestratorService(db_path)


def test_m42_cluster_catalog_contains_priority_clusters() -> None:
    templates = {template.template_id: template for template in list_default_cluster_templates()}

    assert [member.role_label for member in templates["review_cluster"].member_specs] == [
        "quality_gate",
        "test_sentinel",
        "governance_sentinel",
        "doc_curator",
        "launch_guard",
    ]
    assert [member.role_label for member in templates["management_cluster"].member_specs] == [
        "roadmap_manager",
        "phase_designer",
        "governance_sentinel",
        "doc_curator",
        "launch_guard",
    ]
    assert [member.role_label for member in templates["multimodal_cluster"].member_specs] == [
        "multimodal_evidence",
        "multimodal_synthesizer",
        "citation_checker",
        "launch_guard",
    ]
    assert [member.role_label for member in templates["search_cluster"].member_specs] == [
        "search_scout",
        "source_synthesizer",
        "citation_checker",
        "launch_guard",
    ]
    assert [member.role_label for member in templates["design_cluster"].member_specs] == [
        "product_designer",
        "visual_interaction_designer",
        "design_critic",
        "launch_guard",
    ]


def test_m42_router_suggests_specialized_clusters() -> None:
    router = ClusterRouter(list_default_cluster_templates())

    assert router.suggest_template_ids(goal="search sources and verify citation trail") == ["search_cluster"]
    assert router.suggest_template_ids(goal="design a Chinese streaming chat UI") == ["design_cluster"]
    assert router.suggest_template_ids(goal="analyze PDF and screenshot evidence") == ["multimodal_cluster"]
    assert router.suggest_template_ids(goal="run regression test review and QA gate") == ["review_cluster"]
    assert router.suggest_template_ids(goal="maintain roadmap phase task card closeout") == ["management_cluster"]
    assert router.suggest_template_ids(goal="M41 architecture dogfood with Claude gate") == [
        "architecture_delivery_cluster"
    ]


def test_m42_strong_codex_backend_routes_core_cluster_roles_to_codex(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED", "1")
    monkeypatch.setenv("WORKFLOW_DOGFOOD_EXECUTION_BACKEND", "codex_cli")
    monkeypatch.setenv("WORKFLOW_DOGFOOD_MODEL", "gpt-5.5")
    monkeypatch.setenv("WORKFLOW_DOGFOOD_REASONING_EFFORT", "xhigh")
    monkeypatch.delenv("WORKFLOW_CODEX_MODEL", raising=False)
    monkeypatch.delenv("WORKFLOW_DOGFOOD_CODEX_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    service = _service(tmp_path)
    preset = service.preset_repo.get("advisory_delivery")
    assert preset is not None
    task_kind = preset.allowed_task_kinds[0]
    domain_pack = service._resolve_domain_pack(preset, task_kind)

    cases = [
        ("search_cluster", "search_cluster_scout", AgentRoleType.researcher, "search_scout"),
        ("design_cluster", "design_cluster_product_designer", AgentRoleType.planner, "product_designer"),
        ("multimodal_cluster", "multimodal_cluster_synthesizer", AgentRoleType.researcher, "multimodal_synthesizer"),
        ("review_cluster", "review_cluster_test_sentinel", AgentRoleType.reviewer, "test_sentinel"),
        ("management_cluster", "management_cluster_roadmap_manager", AgentRoleType.planner, "roadmap_manager"),
    ]
    for cluster_template_id, cluster_member_id, public_role, role_label in cases:
        resolved = service._resolve_execution_profile_for_run(
            preset=preset,
            task_kind=task_kind,
            domain_pack=domain_pack,
            cluster_template_id=cluster_template_id,
            cluster_member_id=cluster_member_id,
            public_role=public_role,
            role_label=role_label,
        )

        assert resolved.adapter_name == "codex"
        assert resolved.selected_model == "gpt-5.5"
        assert resolved.codex_reasoning_effort == "xhigh"
        assert resolved.model_selection_source == "dogfood_strong_codex_cli"
        assert resolved.source_map["adapter_name"]["original_value"] == "agent"
        assert resolved.role_responsibilities


def test_m42_external_multimodal_member_keeps_mmx_adapter(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED", "1")
    monkeypatch.setenv("WORKFLOW_DOGFOOD_EXECUTION_BACKEND", "codex_cli")
    service = _service(tmp_path)
    preset = service.preset_repo.get("research_spike_reviewable")
    assert preset is not None
    task_kind = preset.allowed_task_kinds[0]

    resolved = service._resolve_execution_profile_for_run(
        preset=preset,
        task_kind=task_kind,
        domain_pack=service._resolve_domain_pack(preset, task_kind),
        cluster_template_id="multimodal_cluster",
        cluster_member_id="multimodal_cluster_mmx_evidence",
        public_role=AgentRoleType.researcher,
        role_label="multimodal_evidence",
    )

    assert resolved.adapter_name == "mmx_multimodal"
    assert resolved.selected_model == "mmx-cli-default"
    assert resolved.model_selection_source == "role_default"


def test_m42_management_cluster_launch_preview_projects_cluster_payload(tmp_path: Path) -> None:
    service = _service(tmp_path)

    payload = service.launch_goal(
        goal="M42 roadmap phase task card closeout",
        preferred_cluster_template_ids=["management_cluster"],
        execute=False,
    )
    detail = service.get_status_detail(payload["run"]["run_id"])

    assert payload["selected_clusters"][0]["template_id"] == "management_cluster"
    assert detail["cluster_graph"]["cluster_template_ids"] == ["management_cluster"]
    assert payload["goal_packet"]["cluster_execution_plans"][0]["handoff_points"] == [
        "roadmap_manager",
        "phase_designer",
        "governance_sentinel",
        "doc_curator",
        "launch_guard",
    ]
