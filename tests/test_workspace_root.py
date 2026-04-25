from __future__ import annotations

from pathlib import Path

from packages.core_domain.config import build_effective_config
from packages.core_domain.db import migrate
from packages.core_domain.services import OrchestratorService


def test_workspace_root_prefers_explicit_over_env_and_cwd(tmp_path: Path, monkeypatch) -> None:
    explicit = tmp_path / "explicit"
    env_root = tmp_path / "env"
    explicit.mkdir()
    env_root.mkdir()
    monkeypatch.setenv("WORKFLOW_WORKSPACE_ROOT", str(env_root))

    effective = build_effective_config(explicit_workspace_root=explicit, cwd=tmp_path)

    assert effective["workspace"]["root"] == explicit.resolve().as_posix()
    assert effective["workspace"]["root_source"] == "explicit"
    assert effective["workspace"]["implicit_cwd_fallback"] is False


def test_workspace_root_env_beats_cwd(tmp_path: Path, monkeypatch) -> None:
    env_root = tmp_path / "env"
    env_root.mkdir()
    monkeypatch.setenv("WORKFLOW_WORKSPACE_ROOT", str(env_root))

    effective = build_effective_config(cwd=tmp_path)

    assert effective["workspace"]["root"] == env_root.resolve().as_posix()
    assert effective["workspace"]["root_source"] == "env:WORKFLOW_WORKSPACE_ROOT"


def test_orchestrator_compile_uses_explicit_workspace_root(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    migrate(db_path)
    service = OrchestratorService(db_path, workspace_root=workspace_root)

    run = service.create_run("Compile with explicit workspace", "feature_delivery")
    bundle = service.compile_run(run.run_id)

    assert bundle.task_packet.working_directory == workspace_root.resolve().as_posix()
