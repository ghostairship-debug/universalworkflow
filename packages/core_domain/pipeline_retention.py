from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PIPELINE_RETENTION_SCHEMA = "pipeline_retention_manifest_v1"


def build_pipeline_retention_manifest(
    payload: dict[str, Any],
    *,
    workspace_root: str | Path,
    target_dir: str | Path,
    allow_external_target: bool = False,
) -> dict[str, Any]:
    root = Path(workspace_root).resolve()
    target = Path(target_dir).resolve()
    workspace_bound = _is_within(target, root)
    if not workspace_bound and not allow_external_target:
        raise ValueError(f"pipeline retention target must stay inside workspace: {target}")

    status = str(payload.get("status") or "unknown")
    stage_results = [item for item in payload.get("stage_results") or [] if isinstance(item, dict)]
    stage_evidence_paths = _dedupe_paths(item.get("evidence_path") for item in stage_results)
    summary_path = str(payload.get("evidence_path") or "")
    heartbeat_path = str(payload.get("heartbeat_path") or "")
    key_artifacts = _dedupe_paths([summary_path, heartbeat_path, *stage_evidence_paths])
    failed_stage = next((item for item in stage_results if item.get("status") in {"failed", "blocked"}), None)
    retention_status = "retain_success_summary_and_key_evidence" if status == "completed" else "retain_failure_scene_and_recovery_pointer"
    return {
        "schema_version": PIPELINE_RETENTION_SCHEMA,
        "created_at": datetime.now(UTC).isoformat(),
        "pipeline_id": (payload.get("pipeline") or {}).get("pipeline_id"),
        "status": status,
        "stop_reason": payload.get("stop_reason"),
        "retention_status": retention_status,
        "workspace_root": root.as_posix(),
        "target_dir": target.as_posix(),
        "cleanup_safety": {
            "workspace_bound": workspace_bound,
            "external_target_allowed": bool(allow_external_target and not workspace_bound),
            "cleanup_performed": False,
            "cleanup_allowed_after_boundary_check": workspace_bound,
            "reason": "manifest_only_retention_no_artifact_deletion",
        },
        "retained_artifacts": {
            "pipeline_summary": summary_path or None,
            "heartbeat": heartbeat_path or None,
            "stage_evidence": stage_evidence_paths,
            "key_artifacts": key_artifacts,
        },
        "recovery": _recovery_pointer(payload, failed_stage),
    }


def _recovery_pointer(payload: dict[str, Any], failed_stage: dict[str, Any] | None) -> dict[str, Any] | None:
    if str(payload.get("status") or "") == "completed":
        return None
    execution_options = payload.get("execution_options") if isinstance(payload.get("execution_options"), dict) else {}
    pipeline = payload.get("pipeline") if isinstance(payload.get("pipeline"), dict) else {}
    return {
        "failed_stage_id": failed_stage.get("stage_id") if failed_stage else None,
        "failed_stage_name": failed_stage.get("name") if failed_stage else None,
        "failure_class": failed_stage.get("failure_class") if failed_stage else payload.get("stop_reason"),
        "continuation_mode": "rerun_pipeline_after_blocker_repair",
        "pipeline_template": pipeline.get("metadata", {}).get("template_id") if isinstance(pipeline.get("metadata"), dict) else None,
        "execution_options": execution_options,
        "continuation_command_hint": "rerun workflowctl pipeline run with the same template, source-path, creator-exe, and required evidence flags after repairing the blocker",
    }


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _dedupe_paths(values: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    iterable = values if isinstance(values, list) else list(values or [])
    for value in iterable:
        text = str(value or "")
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
