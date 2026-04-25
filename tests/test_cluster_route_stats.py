from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from apps.operator_cli.main import app
from apps.orchestrator_api.main import create_app
from packages.core_domain.db import migrate
from packages.core_domain.repositories import PresetRepository
from packages.core_domain.services import OrchestratorService


def _service(tmp_path: Path) -> OrchestratorService:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    return OrchestratorService(db_path, workspace_root=tmp_path)


def test_cluster_route_decisions_are_recorded_and_summarized(tmp_path: Path) -> None:
    service = _service(tmp_path)

    service.launch_goal(goal="search sources and verify citation trail", execute=False)
    stats = service.get_cluster_route_stats(days=30)

    assert stats["decision_count"] >= 1
    assert stats["source_counts"]["cluster_router"] >= 1
    assert stats["dynamic_decision_count"] == 0
    assert stats["window"]["days"] == 30
    assert stats["template_counts"]["search_cluster"] >= 1
    assert stats["recent_decisions"][0]["selected_template_ids"] == ["search_cluster"]


def test_api_and_cli_expose_cluster_route_stats(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    service = _service(tmp_path)
    service.launch_goal(goal="design a Chinese streaming chat UI", execute=False)

    api_payload = TestClient(create_app(db_path, workspace_root=tmp_path)).get("/cluster-routes/stats").json()
    cli_result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--workspace-root",
            str(tmp_path),
            "scheduler",
            "route-stats",
        ],
    )

    assert api_payload["template_counts"]["design_cluster"] >= 1
    assert api_payload["source_counts"]["cluster_router"] >= 1
    assert cli_result.exit_code == 0
    cli_payload = json.loads(cli_result.stdout)
    assert cli_payload["template_counts"]["design_cluster"] >= 1
    assert cli_payload["window"]["days"] == 30
