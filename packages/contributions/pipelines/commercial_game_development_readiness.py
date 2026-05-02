from __future__ import annotations

from typing import Any


COMMERCIAL_GAME_DEVELOPMENT_READINESS_SCHEMA = "commercial_game_development_readiness_v1"
SAME_PROJECT_PATCH_LEDGER_SCHEMA = "commercial_game_same_project_patch_ledger_contract_v1"


def build_commercial_game_development_readiness_evidence(
    *,
    task_card_quality: dict[str, Any] | None = None,
    same_project_patch_ledger: dict[str, Any] | None = None,
    gameplay_semantic_evidence: dict[str, Any] | None = None,
    product_body_evidence: dict[str, Any] | None = None,
    product_body_baseline: dict[str, Any] | None = None,
    validation_gates: dict[str, Any] | None = None,
    commercial_playable_go: bool = False,
    human_player_review_go: bool = False,
    requirement_coverage_gate_present: bool | None = None,
    same_project_worker_gate_present: bool | None = None,
) -> dict[str, Any]:
    quality = _dict_from(task_card_quality)
    patch_ledger = _dict_from(same_project_patch_ledger)
    semantic = _dict_from(gameplay_semantic_evidence)
    product_body = _dict_from(product_body_evidence)
    baseline = _dict_from(product_body_baseline)
    validations = _dict_from(validation_gates)

    blockers: list[str] = []
    task_card_count = _as_int(quality.get("task_card_count"))
    if not quality:
        blockers.append("task_card_quality_missing")
    elif quality.get("go_no_go") != "GO":
        blockers.append("task_card_quality_no_go")
    if task_card_count < 1:
        blockers.append("active_phase_task_cards_missing")
    if _as_int(quality.get("lifecycle_blocked_count")) > 0:
        blockers.append("task_card_lifecycle_no_go")
    if _as_int(quality.get("requirement_coverage_blocked_count")) > 0:
        blockers.append("requirement_coverage_no_go")

    req_gate_present = _infer_requirement_coverage_gate(quality, requirement_coverage_gate_present)
    if not req_gate_present:
        blockers.append("requirement_coverage_gate_missing")

    worker_gate_present = _infer_same_project_worker_gate(patch_ledger, same_project_worker_gate_present)
    if not worker_gate_present:
        blockers.append("same_project_worker_gate_missing")
    if patch_ledger and patch_ledger.get("go") is False:
        blockers.extend(_strings(patch_ledger.get("blockers")) or ["same_project_worker_gate_no_go"])

    semantic_go = bool(semantic.get("go"))
    product_body_go = bool(product_body.get("go"))
    baseline_only = _is_baseline_only(baseline, semantic, product_body)
    if not semantic_go:
        blockers.append("gameplay_semantic_development_start_missing")
    if not product_body_go:
        blockers.append("product_body_development_start_missing")
    if baseline and baseline.get("commercial_playable_go"):
        blockers.append("baseline_claimed_as_commercial_playable")
    if commercial_playable_go and not human_player_review_go:
        blockers.append("commercial_playable_go_claimed_before_human_review")

    for gate_name, blocker in [
        ("doc_links_go", "doc_links_no_go"),
        ("active_truth_go", "active_truth_no_go"),
        ("targeted_tests_go", "targeted_tests_no_go"),
        ("full_matrix_go", "test_matrix_no_go"),
        ("diff_check_go", "diff_check_no_go"),
    ]:
        if gate_name in validations and not bool(validations.get(gate_name)):
            blockers.append(blocker)

    blockers = _dedupe(blockers)
    go = not blockers
    return {
        "schema_version": COMMERCIAL_GAME_DEVELOPMENT_READINESS_SCHEMA,
        "status": "completed" if go else "blocked",
        "go_no_go": "GO" if go else "NO-GO",
        "commercial_game_development_readiness_go": go,
        "commercial_playable_go": bool(commercial_playable_go and human_player_review_go),
        "commercial_playable_threshold_preserved": True,
        "baseline_only": baseline_only,
        "baseline_only_allowed_for": "development_start_only" if baseline_only else None,
        "blockers": blockers,
        "source": {
            "definition": "pipeline_can_safely_execute_real_product_task_cards_without_claiming_commercial_playable_go",
            "task_card_count": task_card_count,
            "execution_eligible_count": _as_int(quality.get("execution_eligible_count")),
            "requirement_coverage_gate_present": req_gate_present,
            "same_project_worker_gate_present": worker_gate_present,
            "gameplay_semantic_go": semantic_go,
            "product_body_go": product_body_go,
            "validation_gates": validations,
            "human_player_review_go": bool(human_player_review_go),
        },
        "forbidden_claim": "development_readiness_is_not_commercial_playable_completion",
    }


def _infer_requirement_coverage_gate(quality: dict[str, Any], explicit: bool | None) -> bool:
    if explicit is not None:
        return bool(explicit)
    if quality.get("schema_version") == "m108_task_card_quality_v2":
        return True
    if "requirement_coverage_blocked_count" in quality:
        return True
    cards = quality.get("task_cards")
    return isinstance(cards, list) and any("requirement_coverage_status" in _dict_from(card) for card in cards)


def _infer_same_project_worker_gate(patch_ledger: dict[str, Any], explicit: bool | None) -> bool:
    if explicit is not None:
        return bool(explicit)
    if patch_ledger.get("schema_version") == SAME_PROJECT_PATCH_LEDGER_SCHEMA:
        return True
    return "same_project_worker_patch_go" in patch_ledger or "go" in patch_ledger


def _is_baseline_only(*payloads: dict[str, Any]) -> bool:
    for payload in payloads:
        if payload.get("baseline_only"):
            return True
        source = _dict_from(payload.get("source"))
        if source.get("baseline_only"):
            return True
    return False


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


def _as_int(value: Any) -> int:
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
