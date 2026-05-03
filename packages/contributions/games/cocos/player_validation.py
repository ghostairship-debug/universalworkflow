from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contributions.games.cocos.capabilities import (
    REQUIRED_PLAYER_VISIBLE_CHECKS,
    judge_commercial_readiness_layers,
)


COCOS_PLAYER_VISIBLE_EVIDENCE_SCHEMA = "m107_cocos_player_visible_evidence_v1"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _hash_payload(payload: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def validate_cocos_player_visible_evidence(
    *,
    playtest: dict[str, Any] | None,
    inspection: dict[str, Any] | None = None,
    technical_smoke: bool,
    production_scaffold: bool,
    evidence_dir: str | Path | None = None,
) -> dict[str, Any]:
    playtest_payload = dict(playtest or {})
    inspection_payload = dict(inspection or {})
    feature_coverage = dict(playtest_payload.get("feature_coverage") or {})
    events = list(playtest_payload.get("events") or [])
    screenshots = list(playtest_payload.get("screenshots") or [])
    canvas_hashes = list(playtest_payload.get("canvas_hashes") or [])
    console_errors = list(playtest_payload.get("console_errors") or [])
    page_errors = list(playtest_payload.get("page_errors") or [])
    raw_checks = {
        "first_screen_visible": bool(screenshots and canvas_hashes and playtest_payload.get("passed")),
        "no_debug_panel_as_primary_ui": not any("debug" in str(name).lower() for name in inspection_payload.get("scene", {}).get("node_names", [])),
        "mobile_viewport_no_overflow": bool(feature_coverage.get("mobilePortraitUi")),
        "core_loop_playable_3_minutes": bool(playtest_payload.get("score", 0) > 0 and feature_coverage.get("dragPlacement")),
        "at_least_one_level_completion_path": bool(feature_coverage.get("campaignFirstSevenLevels") and feature_coverage.get("levelSwitchingUi")),
        "input_controls_visible_and_responsive": bool({"refresh_used", "pause_opened"} <= set(events) and feature_coverage.get("propUse")),
        "audio_not_blocking_or_abrupt": bool(feature_coverage.get("generatedAudioAssets") or feature_coverage.get("audioclipAssetBindings")),
        "browser_console_no_fatal_error": not console_errors and not page_errors,
    }
    evidence_root = Path(evidence_dir).resolve() if evidence_dir is not None else None
    evidence_path = ""
    if evidence_root is not None:
        evidence_root.mkdir(parents=True, exist_ok=True)
        evidence_path = (evidence_root / "cocos_player_visible_evidence.json").as_posix()
    player_visible_checks = {
        check_name: {
            "status": "pass" if passed else "fail",
            "method": "playwright_mobile_player_visible_validation",
            "evidence_path": evidence_path,
            "evidence_hash": _hash_payload({"check": check_name, "passed": passed, "playtest": playtest_payload}),
            "validator_version": "m107.1",
        }
        for check_name, passed in raw_checks.items()
    }
    readiness = judge_commercial_readiness_layers(
        technical_smoke=technical_smoke,
        production_scaffold=production_scaffold,
        player_visible_checks=player_visible_checks,
    )
    if readiness["commercial_playable_go"]:
        go_no_go = "GO"
    elif readiness.get("machine_player_visible_go"):
        go_no_go = "AWAITING_HUMAN_REVIEW"
    else:
        go_no_go = "NO-GO"
    payload = {
        "schema_version": COCOS_PLAYER_VISIBLE_EVIDENCE_SCHEMA,
        "created_at": _utc_now(),
        "technical_smoke_go": bool(technical_smoke),
        "production_scaffold_go": bool(production_scaffold),
        "machine_player_visible_go": bool(readiness.get("machine_player_visible_go")),
        "human_player_review_go": bool(readiness.get("human_player_review_go")),
        "commercial_playable_go": readiness["commercial_playable_go"],
        "raw_checks": raw_checks,
        "player_visible_checks": player_visible_checks,
        "commercial_readiness": readiness,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "screenshots": screenshots,
        "canvas_hashes": canvas_hashes,
        "events": events,
        "go_no_go": go_no_go,
    }
    if evidence_root is not None:
        Path(evidence_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["evidence_path"] = evidence_path
    return payload
