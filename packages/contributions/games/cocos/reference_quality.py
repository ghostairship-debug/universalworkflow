from __future__ import annotations

import json
import math
import struct
from pathlib import Path
from typing import Any


REFERENCE_QUALITY_EVIDENCE_SCHEMA = "commercial_game_reference_quality_evidence_v1"


def load_reference_playtest(
    *,
    reference_project_dir: str | Path | None = None,
    reference_playtest_path: str | Path | None = None,
) -> dict[str, Any]:
    path = _reference_playtest_path(
        reference_project_dir=reference_project_dir,
        reference_playtest_path=reference_playtest_path,
    )
    return _read_json_dict(path) if path else {}


def build_reference_quality_evidence(
    *,
    candidate_playtest: dict[str, Any] | None,
    reference_playtest: dict[str, Any] | None,
    candidate_project_dir: str | Path | None = None,
    reference_project_dir: str | Path | None = None,
    reference_playtest_path: str | Path | None = None,
    min_score_ratio: float = 1.0,
    min_event_ratio: float = 1.0,
    min_visual_density_ratio: float = 0.60,
) -> dict[str, Any]:
    candidate = _dict_from(candidate_playtest)
    reference = _dict_from(reference_playtest)
    blockers: list[str] = []
    if not reference:
        blockers.append("reference_quality_reference_playtest_missing")
    if not candidate:
        blockers.append("reference_quality_candidate_playtest_missing")

    reference_features = _true_features(reference)
    candidate_features = _true_features(candidate)
    missing_features = [key for key in sorted(reference_features) if key not in candidate_features]
    if missing_features:
        blockers.append("reference_quality_missing_features")
        blockers.extend(f"missing_reference_feature_{key}" for key in missing_features)

    reference_score = _int_value(reference.get("score"))
    candidate_score = _int_value(candidate.get("score"))
    required_score = math.ceil(reference_score * min_score_ratio)
    if reference_score > 0 and candidate_score < required_score:
        blockers.append("reference_quality_score_below_reference")

    reference_event_count = len(_strings(reference.get("events")))
    candidate_event_count = len(_strings(candidate.get("events")))
    required_event_count = math.ceil(reference_event_count * min_event_ratio)
    if reference_event_count > 0 and candidate_event_count < required_event_count:
        blockers.append("reference_quality_event_count_below_reference")

    reference_panel_count = len(_strings(reference.get("open_panels")))
    candidate_panel_count = len(_strings(candidate.get("open_panels")))
    if reference_panel_count > 0 and candidate_panel_count < reference_panel_count:
        blockers.append("reference_quality_open_panel_count_below_reference")

    reference_screens = _screenshot_metrics(
        reference.get("screenshots"),
        project_dir=reference_project_dir,
    )
    candidate_screens = _screenshot_metrics(
        candidate.get("screenshots"),
        project_dir=candidate_project_dir,
    )
    reference_screen_count = sum(1 for item in reference_screens if item.get("exists"))
    candidate_screen_count = sum(1 for item in candidate_screens if item.get("exists"))
    if reference_screen_count > 0 and candidate_screen_count < reference_screen_count:
        blockers.append("reference_quality_screenshot_count_below_reference")

    reference_density = _average_bytes(reference_screens)
    candidate_density = _average_bytes(candidate_screens)
    visual_density_ratio = candidate_density / reference_density if reference_density else None
    if visual_density_ratio is not None and visual_density_ratio < min_visual_density_ratio:
        blockers.append("reference_quality_visual_density_below_reference")

    blockers = _dedupe(blockers)
    go = not blockers
    return {
        "schema_version": REFERENCE_QUALITY_EVIDENCE_SCHEMA,
        "status": "completed" if go else "blocked",
        "go": go,
        "blockers": blockers,
        "candidate_reference_quality_go": go,
        "reference_playtest_path": str(reference_playtest_path or ""),
        "source": {
            "reference_project_dir": str(reference_project_dir or ""),
            "candidate_project_dir": str(candidate_project_dir or ""),
            "reference_feature_count": len(reference_features),
            "candidate_feature_count": len(candidate_features),
            "missing_reference_features": missing_features,
            "reference_score": reference_score,
            "candidate_score": candidate_score,
            "required_score": required_score,
            "reference_event_count": reference_event_count,
            "candidate_event_count": candidate_event_count,
            "required_event_count": required_event_count,
            "reference_open_panel_count": reference_panel_count,
            "candidate_open_panel_count": candidate_panel_count,
            "reference_screenshot_count": reference_screen_count,
            "candidate_screenshot_count": candidate_screen_count,
            "reference_average_screenshot_bytes": reference_density,
            "candidate_average_screenshot_bytes": candidate_density,
            "visual_density_ratio": visual_density_ratio,
        },
    }


def _reference_playtest_path(
    *,
    reference_project_dir: str | Path | None,
    reference_playtest_path: str | Path | None,
) -> Path | None:
    if reference_playtest_path:
        return Path(reference_playtest_path)
    if reference_project_dir:
        return Path(reference_project_dir) / "playtest_evidence" / "cocos_playtest_result.json"
    return None


def _read_json_dict(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _screenshot_metrics(raw_paths: Any, *, project_dir: str | Path | None) -> list[dict[str, Any]]:
    paths = _strings(raw_paths)
    root = Path(project_dir) if project_dir else None
    return [_png_metrics(_resolve_path(path, root)) for path in paths]


def _resolve_path(value: str, root: Path | None) -> Path:
    path = Path(value)
    if path.exists() or root is None or path.is_absolute():
        return path
    return root / value


def _png_metrics(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": path.as_posix(), "exists": False}
    try:
        data = path.read_bytes()
    except OSError:
        return {"path": path.as_posix(), "exists": False}
    width = None
    height = None
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        try:
            width, height = struct.unpack(">II", data[16:24])
        except struct.error:
            width, height = None, None
    return {
        "path": path.as_posix(),
        "exists": True,
        "byte_length": len(data),
        "width": width,
        "height": height,
        "unique_byte_count": len(set(data)),
    }


def _average_bytes(metrics: list[dict[str, Any]]) -> int:
    sizes = [int(item.get("byte_length") or 0) for item in metrics if item.get("exists")]
    if not sizes:
        return 0
    return int(sum(sizes) / len(sizes))


def _true_features(payload: dict[str, Any]) -> set[str]:
    features = payload.get("feature_coverage")
    if not isinstance(features, dict):
        return set()
    return {str(key) for key, value in features.items() if bool(value)}


def _dict_from(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str) and value:
        return [value]
    return []


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
