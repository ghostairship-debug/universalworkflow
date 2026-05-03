from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.contracts import PipelineStage, PipelineStageKind, WorkflowPipeline
from packages.core_domain.pipeline import run_workflow_pipeline
from packages.core_domain.pipeline_retention import build_pipeline_retention_manifest


def _retention_pipeline() -> WorkflowPipeline:
    stage = PipelineStage(
        stage_id="stage_retention_validation",
        name="Retention validation",
        stage_kind=PipelineStageKind.validation_gate,
        order_index=0,
        goal="Exercise retention manifest writing.",
        validation_commands=["retention-check"],
    )
    return WorkflowPipeline(
        pipeline_id="pipeline_retention_test",
        name="retention_pipeline",
        goal="retention",
        stages=[stage],
    )


def test_retention_manifest_records_success_summary_and_stage_evidence(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    target_dir = workspace / "pipeline_evidence"
    payload = {
        "pipeline": {"pipeline_id": "pipeline_success"},
        "status": "completed",
        "stop_reason": None,
        "evidence_path": (target_dir / "pipeline_success.json").as_posix(),
        "heartbeat_path": (target_dir / "pipeline_success.heartbeat.jsonl").as_posix(),
        "stage_results": [
            {"stage_id": "stage_1", "status": "completed", "evidence_path": (target_dir / "stage_1.json").as_posix()}
        ],
    }

    manifest = build_pipeline_retention_manifest(payload, workspace_root=workspace, target_dir=target_dir)

    assert manifest["retention_status"] == "retain_success_summary_and_key_evidence"
    assert manifest["recovery"] is None
    assert payload["evidence_path"] in manifest["retained_artifacts"]["key_artifacts"]
    assert payload["stage_results"][0]["evidence_path"] in manifest["retained_artifacts"]["stage_evidence"]
    assert manifest["cleanup_safety"]["cleanup_performed"] is False


def test_retention_manifest_rejects_target_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    outside_target = tmp_path / "outside"

    with pytest.raises(ValueError, match="inside workspace"):
        build_pipeline_retention_manifest({"status": "completed"}, workspace_root=workspace, target_dir=outside_target)


def test_retention_manifest_allows_explicit_external_evidence_target_without_cleanup(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    outside_target = tmp_path / "outside"

    manifest = build_pipeline_retention_manifest(
        {"status": "completed"},
        workspace_root=workspace,
        target_dir=outside_target,
        allow_external_target=True,
    )

    assert manifest["target_dir"] == outside_target.resolve().as_posix()
    assert manifest["cleanup_safety"]["workspace_bound"] is False
    assert manifest["cleanup_safety"]["external_target_allowed"] is True
    assert manifest["cleanup_safety"]["cleanup_allowed_after_boundary_check"] is False


def test_pipeline_run_writes_retention_manifest_with_failure_recovery_pointer(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"

    def _failing_runner(command: str, cwd: Path, timeout_seconds: int) -> dict:
        return {"command": command, "cwd": cwd.as_posix(), "exit_code": 7, "stdout": "", "stderr": "failed"}

    payload = run_workflow_pipeline(
        "retention",
        workspace_root=workspace,
        evidence_dir=workspace / "pipeline_evidence",
        pipeline_previewer=lambda *_args, **_kwargs: _retention_pipeline(),
        command_runner=_failing_runner,
    )

    retention_path = Path(payload["retention_manifest_path"])
    assert retention_path.exists()
    manifest = json.loads(retention_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert manifest["retention_status"] == "retain_failure_scene_and_recovery_pointer"
    assert manifest["recovery"]["failed_stage_id"] == "stage_retention_validation"
    assert manifest["recovery"]["continuation_mode"] == "rerun_pipeline_after_blocker_repair"
    assert manifest["manifest_path"] == retention_path.as_posix()
