from __future__ import annotations

from typing import Any

from packages.contracts import TaskCard


AI_REPAIR_TASK_CARD_SCHEMA = "universal_ai_playtest_repair_task_cards_v1"
AI_REPAIR_LOOP_SCHEMA = "universal_ai_no_go_repair_loop_v1"

_OWNER_WRITE_SET = {
    "correctness": ["project/runtime/gameplay/**"],
    "ux": ["project/runtime/ui/**"],
    "visual": ["project/assets/**", "project/runtime/ui/**"],
    "audio": ["project/assets/audio/**", "project/runtime/audio/**"],
    "performance": ["project/runtime/**"],
    "content": ["project/content/**"],
    "economy": ["project/runtime/systems/**", "project/content/economy/**"],
    "localization": ["project/runtime/ui/**", "project/localization/**"],
    "device": ["project/runtime/input/**", "project/runtime/ui/**"],
    "accessibility": ["project/runtime/ui/**", "project/runtime/input/**"],
}


def build_repair_task_cards_from_ai_findings(
    *,
    run_id: str,
    phase_name: str,
    findings: list[dict[str, Any]],
    required_requirement_ids: list[str] | None = None,
    status: str = "draft",
) -> list[TaskCard]:
    cards: list[TaskCard] = []
    for index, finding in enumerate(findings, start=1):
        if not isinstance(finding, dict):
            continue
        finding_id = str(finding.get("finding_id") or f"ai_finding_{index:04d}")
        severity = str(finding.get("severity") or "P2").upper()
        category = str(finding.get("category") or "correctness").lower()
        requirement_ids = _string_list(finding.get("requirement_ids")) or list(required_requirement_ids or [])
        title = str(finding.get("title") or f"Repair AI playtest finding {finding_id}")
        reproduction = str(finding.get("reproduction") or "Replay the captured AI playtest path and verify the defect.")
        expected = str(finding.get("expected") or "The player-visible experience satisfies the source requirement and AI review.")
        evidence_paths = _string_list(finding.get("evidence_paths"))
        write_set = _string_list(finding.get("write_set")) or list(_OWNER_WRITE_SET.get(category, ["project/runtime/**"]))
        cards.append(
            TaskCard(
                run_id=run_id,
                task_card_id=f"{run_id}_{finding_id}_repair",
                title=title[:120],
                description=(
                    f"Repair AI surrogate playtest finding {finding_id}. "
                    f"Severity {severity}; category {category}. "
                    f"Observed: {str(finding.get('observed') or title)}"
                ),
                goal=(
                    f"Fix AI finding {finding_id} so the replayed player path no longer reproduces the defect. "
                    f"Reproduction: {reproduction}. Expected result: {expected}."
                ),
                milestone="Universal Game Production Quality",
                phase_name=phase_name,
                write_set=write_set,
                read_set=[
                    "UNIVERSAL_GAME_PRODUCTION_AI_PLAYTEST_UPGRADE_PLAN_2026_05_03.md",
                    *evidence_paths,
                ],
                test_commands=[
                    "python -m pytest tests/test_ai_playtest_quality_gate.py tests/test_game_repair_loop_from_ai_findings.py -q",
                    "python -m infra.scripts.check_doc_links",
                ],
                acceptance_criteria=[
                    "AI finding replay no longer reproduces the defect",
                    "Player-visible evidence shows the repaired state",
                    "No new P0/P1 AI findings are introduced",
                ],
                evidence_requirements=[
                    "ai_finding_replay_before_after",
                    "screenshots_or_video_for_repaired_path",
                    "state_snapshot_after_repair",
                    "fresh_worker_receipt",
                ],
                blocking_conditions=[
                    "missing_replay_evidence",
                    "requirement_coverage_missing",
                    "repair_only_changes_feature_flags",
                    "AI red-team still reports P0/P1 finding",
                ],
                model_guidance=[
                    "Repair the underlying gameplay/UI/audio/runtime behavior, not only the evidence flag.",
                    "Keep the fix scoped to the finding write_set and preserve source requirement ids.",
                ],
                risk_level=_risk_for_severity(severity),
                execution_mode="same_project_patch",
                status=status,
                metadata={
                    "schema_version": AI_REPAIR_TASK_CARD_SCHEMA,
                    "ai_finding_id": finding_id,
                    "ai_finding_category": category,
                    "ai_finding_severity": severity,
                    "requirement_coverage_required": True,
                    "required_requirement_ids": requirement_ids,
                    "covered_requirement_ids": requirement_ids,
                    "human_visible_cli_required": severity in {"P0", "P1"},
                    "execution_visibility_mode": "human_visible_cli_enforced" if severity in {"P0", "P1"} else "headless_allowed",
                    "replay_artifact_paths": _string_list(finding.get("replay_artifact_paths")),
                    "evidence_paths": evidence_paths,
                },
            )
        )
    return cards


def findings_from_ai_execution_report(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    payload = report if isinstance(report, dict) else {}
    quality = _dict_from(payload.get("quality"))
    quality_evidence = _dict_from(payload.get("quality_evidence"))
    validation = _dict_from(payload.get("validation"))
    fallback_requirement_ids = _string_list(quality_evidence.get("requirement_ids")) or _string_list(
        quality_evidence.get("preserved_requirement_ids")
    )
    evidence_paths = _string_list(payload.get("output_path"))
    evidence_paths.extend(_string_list(quality_evidence.get("replay_artifacts")))
    evidence_paths.extend(_string_list(quality_evidence.get("screenshots")))

    findings: list[dict[str, Any]] = []
    for finding in _dict_list(quality.get("blocking_findings")):
        findings.append(_normalize_ai_finding(finding, fallback_requirement_ids=fallback_requirement_ids, evidence_paths=evidence_paths))
    for finding in _dict_list(quality_evidence.get("findings")):
        severity = str(finding.get("severity") or "").upper()
        if severity in {"P0", "P1"}:
            findings.append(
                _normalize_ai_finding(finding, fallback_requirement_ids=fallback_requirement_ids, evidence_paths=evidence_paths)
            )
    for blocker in _string_list(validation.get("blockers")):
        findings.append(_finding_from_blocker(blocker, source="validation", requirement_ids=fallback_requirement_ids, evidence_paths=evidence_paths))
    for blocker in _string_list(quality.get("blockers")):
        if blocker == "blocking_ai_findings_present":
            continue
        findings.append(_finding_from_blocker(blocker, source="quality", requirement_ids=fallback_requirement_ids, evidence_paths=evidence_paths))
    return _dedupe_findings(findings)


def build_repair_task_cards_from_ai_execution_report(
    *,
    run_id: str,
    phase_name: str,
    report: dict[str, Any] | None,
    required_requirement_ids: list[str] | None = None,
    status: str = "active",
) -> list[TaskCard]:
    findings = findings_from_ai_execution_report(report)
    return build_repair_task_cards_from_ai_findings(
        run_id=run_id,
        phase_name=phase_name,
        findings=findings,
        required_requirement_ids=required_requirement_ids,
        status=status,
    )


def ai_repair_loop_report(*, execution_report: dict[str, Any] | None, cards: list[TaskCard]) -> dict[str, Any]:
    payload = execution_report if isinstance(execution_report, dict) else {}
    findings = findings_from_ai_execution_report(payload)
    repair_required = not bool(payload.get("go")) or bool(findings)
    return {
        "schema_version": AI_REPAIR_LOOP_SCHEMA,
        "repair_required": repair_required,
        "source_ai_execution_go": bool(payload.get("go")),
        "source_ai_surrogate_playtest_go": bool(_dict_from(payload.get("quality")).get("ai_surrogate_playtest_go")),
        "finding_count": len(findings),
        "findings": findings,
        "generation_report": repair_task_card_batch_report(cards),
    }


def repair_task_card_batch_report(cards: list[TaskCard]) -> dict[str, Any]:
    return {
        "schema_version": AI_REPAIR_TASK_CARD_SCHEMA,
        "task_card_count": len(cards),
        "p0_p1_count": sum(1 for card in cards if card.metadata.get("ai_finding_severity") in {"P0", "P1"}),
        "task_card_ids": [card.task_card_id for card in cards],
        "covered_requirement_ids": sorted(
            {
                str(req_id)
                for card in cards
                for req_id in (card.metadata.get("covered_requirement_ids") or [])
                if str(req_id).strip()
            }
        ),
    }


def _risk_for_severity(severity: str) -> str:
    if severity in {"P0", "P1"}:
        return "high"
    if severity == "P2":
        return "medium"
    return "low"


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _dict_from(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _normalize_ai_finding(
    finding: dict[str, Any],
    *,
    fallback_requirement_ids: list[str],
    evidence_paths: list[str],
) -> dict[str, Any]:
    normalized = dict(finding)
    normalized["finding_id"] = _safe_finding_id(str(normalized.get("finding_id") or normalized.get("id") or "ai_blocking_finding"))
    normalized["severity"] = str(normalized.get("severity") or "P1").upper()
    normalized["category"] = str(normalized.get("category") or "correctness").lower()
    normalized["requirement_ids"] = _string_list(normalized.get("requirement_ids")) or list(fallback_requirement_ids)
    normalized["evidence_paths"] = _dedupe_strings([*_string_list(normalized.get("evidence_paths")), *evidence_paths])
    normalized["replay_artifact_paths"] = _dedupe_strings(
        [*_string_list(normalized.get("replay_artifact_paths")), *_string_list(normalized.get("replay_artifacts"))]
    )
    return normalized


def _finding_from_blocker(
    blocker: str,
    *,
    source: str,
    requirement_ids: list[str],
    evidence_paths: list[str],
) -> dict[str, Any]:
    finding_id = _safe_finding_id(f"{source}_{blocker}")
    return {
        "finding_id": finding_id,
        "severity": "P1",
        "category": _category_for_blocker(blocker),
        "title": f"Repair AI {source} blocker: {blocker}",
        "observed": blocker,
        "expected": "AI surrogate playtest gate passes without this blocker.",
        "reproduction": f"Rerun the AI playtest execution gate and confirm `{blocker}` is absent.",
        "requirement_ids": requirement_ids,
        "evidence_paths": evidence_paths,
    }


def _category_for_blocker(blocker: str) -> str:
    text = blocker.lower()
    if "audio" in text or "bgm" in text or "sfx" in text:
        return "audio"
    if "vision" in text or "screenshot" in text or "visual" in text or "ui" in text:
        return "visual"
    if "device" in text or "input" in text or "latency" in text or "mobile" in text:
        return "device"
    if "performance" in text or "fps" in text:
        return "performance"
    if "requirement" in text or "omission" in text:
        return "content"
    if "score" in text or "first_session" in text:
        return "ux"
    return "correctness"


def _dedupe_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for finding in findings:
        key = str(finding.get("finding_id") or finding.get("title") or finding)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    return result


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _safe_finding_id(value: str) -> str:
    result = []
    for char in value.strip().lower():
        if char.isalnum():
            result.append(char)
        elif char in {"-", "_", ".", ":"}:
            result.append("_" if char in {".", ":"} else char)
        elif char.isspace():
            result.append("_")
    safe = "".join(result).strip("_")
    return safe or "ai_blocking_finding"
