from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return payload


def validate_animation_artifact_integrity(project_dir: Path) -> list[str]:
    scripts_dir = project_dir / "assets" / "scripts"
    resources_dir = project_dir / "assets" / "resources" / "commercial_assets"
    state_path = scripts_dir / "FeedbackAnimationState.ts"
    manifest_path = resources_dir / "feedback_animation_manifest.json"
    evidence_path = project_dir / "workflow_commercial_feature_evidence.json"

    issues: list[str] = []
    for path in (state_path, manifest_path, evidence_path):
        if not path.exists():
            issues.append(f"missing:{path.as_posix()}")

    if issues:
        return issues

    state_text = state_path.read_text(encoding="utf-8")
    expected_single_markers = [
        "export type FeedbackAnimationTriggerId",
        "export type FeedbackAnimationClipId",
        "export const FEEDBACK_ANIMATION_BINDINGS",
        "export const FEEDBACK_ANIMATION_MANIFEST",
        "export const FEEDBACK_ANIMATION_STATE",
        "export function buildFeedbackAnimationSnapshot",
    ]
    for marker in expected_single_markers:
        count = state_text.count(marker)
        if count != 1:
            issues.append(f"unexpected_marker_count:{marker}:{count}")

    try:
        manifest = _load_json_object(manifest_path)
    except Exception as exc:
        issues.append(f"invalid_manifest_json:{exc}")
        manifest = {}

    clip_library = manifest.get("clip_library")
    trigger_bindings = manifest.get("trigger_bindings")
    if not isinstance(clip_library, list) or len(clip_library) != 8:
        issues.append("feedback_manifest_clip_library_not_eight")
    if not isinstance(trigger_bindings, list) or len(trigger_bindings) != 8:
        issues.append("feedback_manifest_trigger_bindings_not_eight")
    if manifest.get("total_clips") != 8:
        issues.append("feedback_manifest_total_clips_not_eight")
    if manifest.get("total_bindings") != 8:
        issues.append("feedback_manifest_total_bindings_not_eight")

    try:
        evidence = _load_json_object(evidence_path)
    except Exception as exc:
        issues.append(f"invalid_feature_evidence_json:{exc}")
        evidence = {}

    animation_evidence = evidence.get("animation_feedback_evidence")
    if not isinstance(animation_evidence, dict):
        issues.append("animation_feedback_evidence_missing")
    else:
        if animation_evidence.get("animation_feedback_hooks_configured") is not True:
            issues.append("animation_feedback_hooks_not_configured")
        if animation_evidence.get("hook_binding_count") != 8:
            issues.append("animation_hook_binding_count_not_eight")
        if animation_evidence.get("clip_count") != 8:
            issues.append("animation_clip_count_not_eight")

    if evidence.get("commercial_playable_go") is True:
        issues.append("commercial_playable_go_claimed")
    if evidence.get("animationFeedbackVerified") is True:
        issues.append("runtime_animation_feedback_claimed_without_runtime_gate")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate same-project animation feedback artifact integrity.")
    parser.add_argument("--project-dir", required=True, type=Path)
    args = parser.parse_args()
    issues = validate_animation_artifact_integrity(args.project_dir.resolve())
    if issues:
        print(json.dumps({"status": "failed", "issues": issues}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"status": "passed", "issues": []}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
