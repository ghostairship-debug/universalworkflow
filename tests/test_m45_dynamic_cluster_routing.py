from __future__ import annotations

from pathlib import Path

from packages.core_domain.cluster_router import ClusterRouter, load_cluster_route_markers
from packages.core_domain.db import migrate
from packages.core_domain.interaction_catalog import list_default_cluster_templates
from packages.core_domain.repositories import PresetRepository
from packages.core_domain.services import OrchestratorService


def test_m45_dynamic_cluster_routing_composes_multimodal_game_delivery(monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_DYNAMIC_CLUSTER_ROUTING_ENABLED", "1")
    router = ClusterRouter(list_default_cluster_templates())

    suggested = router.suggest_template_ids(
        goal="Analyze PDF evidence, design UI, implement a commercial browser game, and run QA review"
    )

    assert suggested == ["multimodal_cluster", "search_cluster", "design_cluster", "dev_cluster", "review_cluster"]


def test_m58_cluster_route_markers_are_loaded_from_seed_config() -> None:
    marker_catalog = load_cluster_route_markers()
    router = ClusterRouter(list_default_cluster_templates(), marker_catalog=marker_catalog)

    assert "多模态" in marker_catalog["multimodal_cluster"]
    assert router.suggest_template_ids(goal="需要多模态证据和截图核验") == ["multimodal_cluster"]


def test_m45_dynamic_cluster_routing_keeps_explicit_preference(monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_DYNAMIC_CLUSTER_ROUTING_ENABLED", "1")
    router = ClusterRouter(list_default_cluster_templates())

    assert router.suggest_template_ids(
        goal="Analyze PDF and implement game",
        preferred_template_ids=["management_cluster"],
    ) == ["management_cluster"]


def test_m45_dynamic_cluster_routing_is_opt_in(monkeypatch) -> None:
    monkeypatch.delenv("WORKFLOW_DYNAMIC_CLUSTER_ROUTING_ENABLED", raising=False)
    router = ClusterRouter(list_default_cluster_templates())

    assert router.suggest_template_ids(
        goal="Analyze PDF evidence, design UI, implement a commercial browser game, and run QA review"
    ) == ["multimodal_cluster"]


def test_m46_dynamic_cluster_graph_projects_all_selected_clusters(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_DYNAMIC_CLUSTER_ROUTING_ENABLED", "1")
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    payload = service.launch_goal(
        goal="Analyze PDF evidence, design UI, implement a commercial browser game, and run QA review",
        execute=False,
    )
    detail = service.get_status_detail(payload["run"]["run_id"])

    expected = ["multimodal_cluster", "search_cluster", "design_cluster", "dev_cluster", "review_cluster"]
    assert [item["template_id"] for item in payload["selected_clusters"]] == expected
    assert detail["cluster_graph"]["cluster_template_ids"] == expected
    assert [item["template_id"] for item in detail["selected_clusters"]] == expected
    assert len(detail["cluster_graph"]["cluster_graphs"]) == len(expected)
