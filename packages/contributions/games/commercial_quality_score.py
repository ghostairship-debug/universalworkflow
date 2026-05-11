from __future__ import annotations

from typing import Any


COMMERCIAL_QUALITY_SCORECARD_SCHEMA = "commercial_game_quality_scorecard_v1"

QUALITY_AREAS = {
    "core_playability": 20,
    "portrait_mobile_ux": 15,
    "ui_polish": 15,
    "art_completeness": 15,
    "animation_feedback": 10,
    "audio_fit": 10,
    "content_depth": 10,
    "r5_no_regression": 5,
}

AREA_MINIMUMS = {
    "core_playability": 18,
    "portrait_mobile_ux": 13,
    "ui_polish": 12,
    "art_completeness": 12,
}

TARGET_SCORE = 85


def evaluate_commercial_quality_scorecard(
    scorecard: dict[str, Any] | None = None,
    *,
    playtest: dict[str, Any] | None = None,
    browser_playtest_ledger: dict[str, Any] | None = None,
    reference_quality_evidence: dict[str, Any] | None = None,
    ai_surrogate_playtest_evidence: dict[str, Any] | None = None,
    product_depth_evidence: dict[str, Any] | None = None,
    product_body_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _dict(scorecard)
    if payload.get("schema_version") == COMMERCIAL_QUALITY_SCORECARD_SCHEMA:
        return _normalize_scorecard(payload)
    if not payload and not any(
        _dict(value)
        for value in (
            playtest,
            browser_playtest_ledger,
            reference_quality_evidence,
            ai_surrogate_playtest_evidence,
            product_depth_evidence,
            product_body_evidence,
        )
    ):
        return _missing_scorecard()

    playtest_payload = _dict(playtest)
    browser_ledger = _dict(browser_playtest_ledger)
    reference = _dict(reference_quality_evidence)
    ai_quality = _dict(ai_surrogate_playtest_evidence)
    product_depth = _dict(product_depth_evidence)
    product_body = _dict(product_body_evidence)

    hard_blockers = _hard_blockers(
        playtest=playtest_payload,
        browser_playtest_ledger=browser_ledger,
        reference_quality_evidence=reference,
        product_body_evidence=product_body,
    )
    area_scores = {
        "core_playability": QUALITY_AREAS["core_playability"]
        if _real_pointer_drag_go(playtest_payload) and _ledger_go(browser_ledger)
        else 0,
        "portrait_mobile_ux": QUALITY_AREAS["portrait_mobile_ux"] if _portrait_go(playtest_payload) else 0,
        "ui_polish": _ui_polish_score(playtest_payload, product_depth, ai_quality, hard_blockers),
        "art_completeness": _art_score(playtest_payload, ai_quality, hard_blockers),
        "animation_feedback": QUALITY_AREAS["animation_feedback"] if _feature(playtest_payload, "animationFeedbackVerified") else 0,
        "audio_fit": QUALITY_AREAS["audio_fit"] if _audio_go(playtest_payload, ai_quality) else 0,
        "content_depth": QUALITY_AREAS["content_depth"] if bool(product_depth.get("go")) else 0,
        "r5_no_regression": QUALITY_AREAS["r5_no_regression"] if bool(reference.get("go")) else 0,
    }
    return _build_scorecard(
        area_scores=area_scores,
        hard_blockers=hard_blockers,
        source={
            "score_source": "deterministic_commercial_quality_score_agent_v1",
            "playtest_result_path": playtest_payload.get("result_path"),
            "browser_playtest_ledger_go": browser_ledger.get("go"),
            "reference_quality_go": reference.get("go") if reference else None,
            "ai_surrogate_playtest_go": ai_quality.get("ai_surrogate_playtest_go") if ai_quality else None,
            "product_body_go": product_body.get("go") if product_body else None,
            "product_depth_go": product_depth.get("go") if product_depth else None,
        },
        screenshots=_strings(playtest_payload.get("product_screenshots") or playtest_payload.get("screenshots")),
        replays=_strings(playtest_payload.get("real_pointer_drag_replay") or playtest_payload.get("replay_artifacts")),
        r5_reference_summary=_dict(reference.get("source")),
    )


def scorecard_go(scorecard: dict[str, Any] | None) -> bool:
    payload = _normalize_scorecard(_dict(scorecard))
    return bool(payload.get("go"))


def _normalize_scorecard(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        return _missing_scorecard()
    area_scores = _area_scores(_dict(payload.get("area_scores")))
    hard_blockers = _dedupe(_strings(payload.get("hard_blockers") or payload.get("blockers")))
    return _build_scorecard(
        area_scores=area_scores,
        hard_blockers=hard_blockers,
        source=_dict(payload.get("source")),
        screenshots=_strings(payload.get("screenshots")),
        replays=_strings(payload.get("replay_artifacts")),
        r5_reference_summary=_dict(payload.get("r5_reference_summary")),
    )


def _missing_scorecard() -> dict[str, Any]:
    return _build_scorecard(
        area_scores={key: 0 for key in QUALITY_AREAS},
        hard_blockers=["commercial_quality_scorecard_missing"],
        source={"score_source": "missing"},
        screenshots=[],
        replays=[],
        r5_reference_summary={},
    )


def _build_scorecard(
    *,
    area_scores: dict[str, int],
    hard_blockers: list[str],
    source: dict[str, Any],
    screenshots: list[str],
    replays: list[str],
    r5_reference_summary: dict[str, Any],
) -> dict[str, Any]:
    normalized_scores = _area_scores(area_scores)
    area_blockers = [
        f"commercial_quality_{area}_below_minimum"
        for area, minimum in AREA_MINIMUMS.items()
        if normalized_scores.get(area, 0) < minimum
    ]
    total_score = sum(normalized_scores.values())
    blockers = _dedupe([*hard_blockers, *area_blockers])
    if (
        normalized_scores.get("ui_polish", 0) < AREA_MINIMUMS["ui_polish"]
        or normalized_scores.get("art_completeness", 0) < AREA_MINIMUMS["art_completeness"]
    ):
        blockers.append("commercial_visual_quality_below_bar")
    if total_score < TARGET_SCORE:
        blockers.append("commercial_quality_score_below_85")
    blockers = _dedupe(blockers)
    go = total_score >= TARGET_SCORE and not blockers
    return {
        "schema_version": COMMERCIAL_QUALITY_SCORECARD_SCHEMA,
        "status": "completed" if go else "blocked",
        "go": go,
        "total_score": total_score,
        "target_score": TARGET_SCORE,
        "area_scores": normalized_scores,
        "area_minimums": dict(AREA_MINIMUMS),
        "hard_blockers": blockers,
        "blockers": blockers,
        "screenshots": screenshots,
        "replay_artifacts": replays,
        "r5_reference_summary": r5_reference_summary,
        "repair_task_card_suggestions": _repair_suggestions(blockers),
        "source": source,
    }


def _hard_blockers(
    *,
    playtest: dict[str, Any],
    browser_playtest_ledger: dict[str, Any],
    reference_quality_evidence: dict[str, Any],
    product_body_evidence: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if not _real_pointer_drag_go(playtest):
        blockers.append("real_pointer_drag_failed")
    if not _portrait_go(playtest):
        blockers.append("portrait_orientation_failed")
    if _bridge_or_overlay_counted(playtest, product_body_evidence):
        blockers.append("bridge_event_miscounted_as_product_body")
    if browser_playtest_ledger and not browser_playtest_ledger.get("go"):
        blockers.extend(_strings(browser_playtest_ledger.get("blockers")))
    if reference_quality_evidence and not reference_quality_evidence.get("go"):
        blockers.extend(_strings(reference_quality_evidence.get("blockers")) or ["reference_quality_no_go"])
    return _dedupe(blockers)


def _area_scores(value: dict[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    for area, weight in QUALITY_AREAS.items():
        try:
            raw = int(value.get(area, 0))
        except (TypeError, ValueError):
            raw = 0
        result[area] = max(0, min(weight, raw))
    return result


def _ui_polish_score(
    playtest: dict[str, Any],
    product_depth: dict[str, Any],
    ai_quality: dict[str, Any],
    hard_blockers: list[str],
) -> int:
    if "bridge_event_miscounted_as_product_body" in hard_blockers:
        return 0
    visual_score = _int(ai_quality.get("visual_quality_score"))
    if visual_score >= 90 and bool(product_depth.get("go")) and _feature(playtest, "chineseUi"):
        return QUALITY_AREAS["ui_polish"]
    if bool(product_depth.get("go")) and _feature(playtest, "chineseUi"):
        return 12
    return 0


def _art_score(playtest: dict[str, Any], ai_quality: dict[str, Any], hard_blockers: list[str]) -> int:
    if "bridge_event_miscounted_as_product_body" in hard_blockers:
        return 0
    visual_score = _int(ai_quality.get("visual_quality_score"))
    has_art = _feature(playtest, "generatedArtAssets") and _feature(playtest, "cocosAssetBindings")
    if visual_score >= 90 and has_art:
        return QUALITY_AREAS["art_completeness"]
    if has_art:
        return 12
    return 0


def _audio_go(playtest: dict[str, Any], ai_quality: dict[str, Any]) -> bool:
    audio_review = _dict(ai_quality.get("audio_review"))
    return all(
        [
            _feature(playtest, "audioPlaybackVerified"),
            _feature(playtest, "bgmStarted") or bool(audio_review.get("bgm_runtime_verified")),
            _feature(playtest, "sfxPlaybackVerified") or bool(audio_review.get("sfx_runtime_verified")),
        ]
    )


def _real_pointer_drag_go(playtest: dict[str, Any]) -> bool:
    pointer = _dict(playtest.get("real_pointer_drag"))
    return bool(playtest.get("real_pointer_drag_go") or pointer.get("go"))


def _portrait_go(playtest: dict[str, Any]) -> bool:
    portrait = _dict(playtest.get("portrait_orientation"))
    return bool(playtest.get("portrait_orientation_go") or portrait.get("go"))


def _ledger_go(payload: dict[str, Any]) -> bool:
    return bool(payload.get("go")) if payload else False


def _bridge_or_overlay_counted(playtest: dict[str, Any], product_body_evidence: dict[str, Any]) -> bool:
    if playtest.get("used_bridge_actions_for_core_drag") or playtest.get("bridge_only_drag"):
        return True
    overlay = _dict(playtest.get("inspection_overlay"))
    if overlay.get("counts_as_product_body") is True:
        return True
    if product_body_evidence.get("runtime_hook") or product_body_evidence.get("canvas_only"):
        return True
    return False


def _feature(playtest: dict[str, Any], key: str) -> bool:
    features = _dict(playtest.get("feature_coverage"))
    return bool(features.get(key))


def _repair_suggestions(blockers: list[str]) -> list[dict[str, str]]:
    suggestions = []
    for blocker in blockers:
        owner = "commercial_game_task_card_worker"
        if "portrait" in blocker or "ui" in blocker:
            owner = "ui_ux_polish_agent"
        elif "art" in blocker or "visual" in blocker:
            owner = "art_direction_agent"
        elif "pointer" in blocker or "drag" in blocker:
            owner = "mechanics_system_designer_agent"
        suggestions.append(
            {
                "blocker": blocker,
                "owner_role": owner,
                "repair_mode": "same_project_incremental_patch",
            }
        )
    return suggestions


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _int(value: Any) -> int:
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
