from __future__ import annotations

from pathlib import Path

import pytest

from infra.scripts.manage import run_demo
from infra.scripts.m21_rebaseline_report import build_m21_rebaseline_report
from packages.worker_adapters.base import ExecutionResult, resolve_artifact_paths, utc_now
from packages.worker_adapters.codex_adapter import CodexAdapter
from packages.worker_adapters.langchain_agent_adapter import LangChainAgentAdapter


pytestmark = pytest.mark.slow

def _fake_release_external_launch(self, packet):  # type: ignore[override]
    started_at = utc_now()
    artifact_paths = resolve_artifact_paths(
        packet,
        create_missing=True,
        placeholder=f"# Fake external adapter\n\nadapter={self.normalized_name()}\n",
    )
    finished_at = utc_now()
    return ExecutionResult(
        runtime_task_id=packet.runtime_task_id,
        return_code=0,
        stdout=f"{self.normalized_name()} fake ok",
        stderr="",
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=max(int((finished_at - started_at).total_seconds() * 1000), 0),
        artifact_paths=artifact_paths,
        adapter_name=self.normalized_name(),
        metadata={"test_fake_external_adapter": True},
    )


def test_manage_demo_projects_canonical_closeout_packet(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(CodexAdapter, "launch", _fake_release_external_launch)
    monkeypatch.setattr(LangChainAgentAdapter, "launch", _fake_release_external_launch)
    db_path = tmp_path / "workflow.db"

    payload = run_demo(db_path)

    assert payload["status"] == "completed"
    assert payload["capability_routes"] == [
        {"capability": "noop", "adapter_name": "noop", "adapter_class": "NoopAdapter"},
        {"capability": "shell_exec", "adapter_name": "shell", "adapter_class": "ShellAdapter"},
        {"capability": "shell_exec", "adapter_name": "codex", "adapter_class": "CodexAdapter"},
        {"capability": "shell_exec", "adapter_name": "claude_architect", "adapter_class": "ClaudeArchitectAdapter"},
        {"capability": "shell_exec", "adapter_name": "mmx_multimodal", "adapter_class": "MMXMultimodalAdapter"},
        {"capability": "shell_exec", "adapter_name": "vertex_multimodal", "adapter_class": "VertexMultimodalAdapter"},
        {"capability": "shell_exec", "adapter_name": "opencode", "adapter_class": "OpenCodeAdapter"},
    ]
    assert [item["domain_pack_id"] for item in payload["domain_packs"]] == ["software_delivery_pack"]
    assert payload["paths"]["auto"]["status"] == "completed"
    assert payload["paths"]["auto"]["domain_pack"]["domain_pack_id"] == "software_delivery_pack"
    assert payload["paths"]["human_review"]["intermediate_status"] == "awaiting_review"
    assert payload["paths"]["human_review"]["status"] == "completed"
    assert payload["paths"]["recommended"]["intermediate_status"] == "awaiting_review"
    assert payload["paths"]["recommended"]["status"] == "completed"
    assert payload["paths"]["mandatory"]["intermediate_status"] == "awaiting_review"
    assert payload["paths"]["mandatory"]["status"] == "completed"
    assert payload["paths"]["noop"]["task_kind"] == "noop"
    assert payload["paths"]["noop"]["adapter_name"] == "noop"
    assert payload["paths"]["noop"]["status"] == "completed"
    assert Path(payload["paths"]["auto"]["artifact_path"]).exists()


def test_m21_rebaseline_report_covers_canonical_demo_matrix(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(CodexAdapter, "launch", _fake_release_external_launch)
    monkeypatch.setattr(LangChainAgentAdapter, "launch", _fake_release_external_launch)
    db_path = tmp_path / "m21_rebaseline.db"

    payload = build_m21_rebaseline_report(db_path)

    assert payload["status"] == "completed"
    assert payload["migration_status"]["up_to_date"] is True
    assert payload["baseline_contract"]["source_package_truth"].startswith("export manifest")
    assert payload["canonical_demo_matrix"]["feature_delivery"]["status"] == "completed"
    assert payload["canonical_demo_matrix"]["guarded_delivery"]["status"] == "completed"
    assert payload["canonical_demo_matrix"]["project_delivery"]["orchestration_enabled"] is True
    assert payload["canonical_demo_matrix"]["project_delivery"]["orchestration_plan_graph"]["execution_mode"].startswith("planner_")
    assert payload["source_package"]["db_artifacts_excluded"] is True
