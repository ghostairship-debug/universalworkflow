from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contracts import PresetDefinition, ReviewPolicy
from packages.core_domain.db import DEFAULT_DB_PATH, get_connection
from packages.core_domain.domain_packs import DomainPackRegistry
from packages.core_domain.presets import load_seed_presets
from packages.core_domain.repositories import PresetRepository
from packages.worker_adapters.router import WorkerRouter


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TECH_DEBT_REGISTRY_PATH = REPO_ROOT / "docs" / "tech-debt-registry.md"
DEFAULT_REVIEW_DECISION_TABLE_PATH = REPO_ROOT / "docs" / "reviews" / "m1_review_semantics_decision_table.md"
DEFAULT_TECH_DEBT_CANONICAL_PATH = REPO_ROOT / "docs" / "governance" / "tech_debt_registry.json"
DEFAULT_REVIEW_DECISION_CANONICAL_PATH = REPO_ROOT / "docs" / "governance" / "review_policy_cases.json"
DEFAULT_VALIDATION_REPORT_PATH = REPO_ROOT / "state" / "offline_validation_report.json"


def _extract_numbered_section(text: str, section_number: int) -> str:
    pattern = re.compile(rf"^# {section_number}\.\s.*$", re.MULTILINE)
    match = pattern.search(text)
    if match is None:
        return ""
    start = match.end()
    remainder = text[start:]
    next_match = re.search(r"^# \d+\.\s.*$", remainder, re.MULTILINE)
    if next_match is None:
        return remainder
    return remainder[: next_match.start()]


def _extract_subsection(text: str, heading: str) -> str:
    pattern = re.compile(rf"^{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(text)
    if match is None:
        return ""
    start = match.end()
    remainder = text[start:]
    next_match = re.search(r"^## .*$", remainder, re.MULTILINE)
    if next_match is None:
        return remainder
    return remainder[: next_match.start()]


def _parse_markdown_table(section_text: str) -> list[dict[str, str]]:
    table_lines = [line.strip() for line in section_text.splitlines() if line.strip().startswith("|")]
    if len(table_lines) < 2:
        return []
    headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        values = [cell.strip() for cell in line.strip("|").split("|")]
        if len(values) != len(headers):
            continue
        rows.append(dict(zip(headers, values, strict=True)))
    return rows


def _parse_numbered_lines(section_text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in section_text.splitlines():
        stripped = raw_line.strip()
        if re.match(r"^\d+\.\s", stripped):
            lines.append(re.sub(r"^\d+\.\s*", "", stripped))
    return lines


def _parse_bullets(section_text: str) -> list[str]:
    bullets: list[str] = []
    for raw_line in section_text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
    return bullets


def _strip_code_ticks(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("`") and stripped.endswith("`"):
        return stripped[1:-1]
    return stripped


def _normalize_repaid_item(row: dict[str, str]) -> dict[str, str]:
    values = list(row.values())
    if len(values) < 5:
        raise ValueError(f"unexpected repaid debt row shape: {row}")
    return {
        "debt_id": values[0],
        "description": values[1],
        "introduced_in": values[2],
        "repaid_in": values[3],
        "result": values[4],
    }


def _normalize_open_item(row: dict[str, str]) -> dict[str, str]:
    values = list(row.values())
    if len(values) < 6:
        raise ValueError(f"unexpected open debt row shape: {row}")
    return {
        "debt_id": values[0],
        "description": values[1],
        "introduced_in": values[2],
        "planned_repayment_phase": values[3],
        "current_status": values[4],
        "blocking_impact": values[5],
    }


def _build_tech_debt_report_payload(
    *,
    source_path: Path,
    repaid_items: list[dict[str, str]],
    open_items: list[dict[str, str]],
    freeze_review_questions: list[str],
    source_contract: str,
    compatibility_source_path: Path | None = None,
) -> dict[str, Any]:
    status_counts = Counter(item["current_status"] for item in open_items)
    planned_phase_counts = Counter(item["planned_repayment_phase"] for item in open_items)
    introduced_phase_counts = Counter(item["introduced_in"] for item in open_items)
    m3_focus_items = [item for item in open_items if item["planned_repayment_phase"] == "M3"]
    m9_focus_items = [item for item in open_items if item["planned_repayment_phase"] == "M9"]
    m10_focus_items = [item for item in open_items if item["planned_repayment_phase"] == "M10"]
    m11_focus_items = [item for item in open_items if item["planned_repayment_phase"] == "M11"]
    m12_focus_items = [item for item in open_items if item["planned_repayment_phase"] == "M12"]
    m13_focus_items = [item for item in open_items if item["planned_repayment_phase"] == "M13"]
    m14_focus_items = [item for item in open_items if item["planned_repayment_phase"] == "M14"]
    m15_focus_items = [item for item in open_items if item["planned_repayment_phase"] == "M15"]
    pre_m8_focus_items = [item for item in open_items if item["planned_repayment_phase"] == "Pre-M8"]
    next_cycle_focus_items = [
        item
        for item in open_items
        if item["planned_repayment_phase"] in {"Next Cycle", "M10", "M11", "M12", "M13", "M14", "M15", "M16", "M17", "M18", "M19+"}
    ]
    active_gate_focus_items = (
        pre_m8_focus_items
        or m3_focus_items
        or m9_focus_items
        or m10_focus_items
        or m11_focus_items
        or m12_focus_items
        or m13_focus_items
        or m14_focus_items
        or m15_focus_items
        or next_cycle_focus_items
        or open_items
    )
    return {
        "source_path": source_path.as_posix(),
        "source_contract": source_contract,
        "source_paths": {
            "canonical": source_path.as_posix(),
            "compatibility_markdown": compatibility_source_path.as_posix() if compatibility_source_path is not None else None,
        },
        "repaid_debt_count": len(repaid_items),
        "open_debt_count": len(open_items),
        "status_counts": dict(status_counts),
        "planned_phase_counts": dict(planned_phase_counts),
        "introduced_phase_counts": dict(introduced_phase_counts),
        "m3_focus_items": m3_focus_items,
        "m9_focus_items": m9_focus_items,
        "m10_focus_items": m10_focus_items,
        "m11_focus_items": m11_focus_items,
        "m12_focus_items": m12_focus_items,
        "m13_focus_items": m13_focus_items,
        "m14_focus_items": m14_focus_items,
        "m15_focus_items": m15_focus_items,
        "pre_m8_focus_items": pre_m8_focus_items,
        "next_cycle_focus_items": next_cycle_focus_items,
        "active_gate_focus_items": active_gate_focus_items,
        "open_items": open_items,
        "repaid_items": repaid_items,
        "freeze_review_questions": freeze_review_questions,
    }


def _load_structured_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_tech_debt_report_from_structured(path: Path) -> dict[str, Any]:
    payload = _load_structured_json(path)
    repaid_items = [dict(item) for item in payload.get("repaid_items", [])]
    open_items = [dict(item) for item in payload.get("open_items", [])]
    return _build_tech_debt_report_payload(
        source_path=path,
        repaid_items=repaid_items,
        open_items=open_items,
        freeze_review_questions=list(payload.get("freeze_review_questions", [])),
        source_contract="structured_json",
        compatibility_source_path=DEFAULT_TECH_DEBT_REGISTRY_PATH if DEFAULT_TECH_DEBT_REGISTRY_PATH.exists() else None,
    )


def _build_tech_debt_report_from_markdown(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")

    repaid_section = _extract_numbered_section(text, 2)
    open_section = _extract_numbered_section(text, 3)
    freeze_review_section = _extract_numbered_section(text, 4)

    repaid_items = [_normalize_repaid_item(row) for row in _parse_markdown_table(repaid_section)]
    open_items = [_normalize_open_item(row) for row in _parse_markdown_table(open_section)]
    return _build_tech_debt_report_payload(
        source_path=path,
        repaid_items=repaid_items,
        open_items=open_items,
        freeze_review_questions=_parse_numbered_lines(freeze_review_section),
        source_contract="markdown_compatibility",
    )


def build_tech_debt_report(registry_path: str | Path | None = None) -> dict[str, Any]:
    if registry_path is not None:
        path = Path(registry_path)
        if path.suffix.lower() == ".json":
            return _build_tech_debt_report_from_structured(path)
        return _build_tech_debt_report_from_markdown(path)
    if DEFAULT_TECH_DEBT_CANONICAL_PATH.exists():
        return _build_tech_debt_report_from_structured(DEFAULT_TECH_DEBT_CANONICAL_PATH)
    return _build_tech_debt_report_from_markdown(DEFAULT_TECH_DEBT_REGISTRY_PATH)


def _load_policy_presets(db_path: str | Path | None = None) -> list[PresetDefinition]:
    if db_path is not None:
        try:
            presets = PresetRepository(db_path).list()
        except sqlite3.OperationalError:
            presets = []
        if presets:
            return presets
    return load_seed_presets()


def _parse_review_decision_table_from_markdown(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    cases_section = _extract_subsection(text, "## Cases")
    notes_section = _extract_subsection(text, "## Notes")
    rows = _parse_markdown_table(cases_section)
    return {
        "source_path": path.as_posix(),
        "source_contract": "markdown_compatibility",
        "source_paths": {
            "canonical": path.as_posix(),
            "compatibility_markdown": None,
        },
        "cases": [
            {
                "path": _strip_code_ticks(list(row.values())[0]),
                "latest_verdict": _strip_code_ticks(list(row.values())[1]),
                "effective_review_state": _strip_code_ticks(list(row.values())[2]),
            }
            for row in rows
            if len(row) >= 3
        ],
        "notes": _parse_bullets(notes_section),
    }


def _parse_review_decision_table_from_structured(path: Path) -> dict[str, Any]:
    payload = _load_structured_json(path)
    return {
        "source_path": path.as_posix(),
        "source_contract": "structured_json",
        "source_paths": {
            "canonical": path.as_posix(),
            "compatibility_markdown": (
                DEFAULT_REVIEW_DECISION_TABLE_PATH.as_posix() if DEFAULT_REVIEW_DECISION_TABLE_PATH.exists() else None
            ),
        },
        "cases": [dict(item) for item in payload.get("cases", [])],
        "notes": list(payload.get("notes", [])),
    }


def _parse_review_decision_table(decision_table_path: str | Path | None = None) -> dict[str, Any]:
    if decision_table_path is not None:
        path = Path(decision_table_path)
        if path.suffix.lower() == ".json":
            return _parse_review_decision_table_from_structured(path)
        return _parse_review_decision_table_from_markdown(path)
    if DEFAULT_REVIEW_DECISION_CANONICAL_PATH.exists():
        return _parse_review_decision_table_from_structured(DEFAULT_REVIEW_DECISION_CANONICAL_PATH)
    return _parse_review_decision_table_from_markdown(DEFAULT_REVIEW_DECISION_TABLE_PATH)


def _runtime_shape_for_policy(policy: str) -> str:
    if policy == str(ReviewPolicy.auto_only):
        return "execution_then_auto_review_terminal"
    if policy == str(ReviewPolicy.optional):
        return "execution_then_advisory_review_terminal"
    if policy == str(ReviewPolicy.recommended):
        return "execution_then_auto_review_or_human_escalation"
    if policy == str(ReviewPolicy.human_required):
        return "execution_then_await_human_review"
    if policy == str(ReviewPolicy.mandatory):
        return "execution_then_auto_review_then_human_signoff"
    return "reference_only"


def _reference_only_policy_candidates() -> list[dict[str, str]]:
    return []


def _load_validation_report(validation_report_path: str | Path | None = None) -> dict[str, Any] | None:
    path = Path(validation_report_path) if validation_report_path is not None else DEFAULT_VALIDATION_REPORT_PATH
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_capability_routes() -> list[dict[str, str]]:
    return WorkerRouter().routes()


def _load_domain_pack_catalog() -> list[dict[str, Any]]:
    return [domain_pack.model_dump(mode="json") for domain_pack in DomainPackRegistry().list()]


def _load_runtime_inventory(db_path: str | Path | None = None) -> dict[str, Any]:
    resolved_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    if not resolved_path.exists():
        return {
            "db_path": resolved_path.as_posix(),
            "db_present": False,
            "counts": {},
        }
    table_map = {
        "runs": "runs",
        "events": "run_events",
        "snapshots": "run_snapshots",
        "evidence": "evidence",
        "review_verdicts": "review_verdicts",
        "runtime_attempts": "runtime_attempts",
        "claims": "runtime_claims",
        "worker_leases": "worker_leases",
        "simulation_records": "simulation_records",
        "memory_items": "memory_items",
    }
    counts: dict[str, int] = {}
    run_status_counts: dict[str, int] = {}
    try:
        with get_connection(resolved_path) as connection:
            for key, table_name in table_map.items():
                try:
                    counts[key] = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()["count"]
                except sqlite3.OperationalError:
                    counts[key] = 0
            try:
                rows = connection.execute(
                    "SELECT status, COUNT(*) AS count FROM runs GROUP BY status ORDER BY status"
                ).fetchall()
                run_status_counts = {row["status"]: row["count"] for row in rows}
            except sqlite3.OperationalError:
                run_status_counts = {}
    except sqlite3.OperationalError:
        return {
            "db_path": resolved_path.as_posix(),
            "db_present": False,
            "counts": {},
        }
    return {
        "db_path": resolved_path.as_posix(),
        "db_present": True,
        "counts": counts,
        "run_status_counts": run_status_counts,
        "awaiting_review_runs": run_status_counts.get("awaiting_review", 0),
        "terminal_runs": (
            run_status_counts.get("completed", 0)
            + run_status_counts.get("failed", 0)
            + run_status_counts.get("cancelled", 0)
        ),
    }


def build_domain_pack_platform_report() -> dict[str, Any]:
    domain_packs = _load_domain_pack_catalog()
    pack_summaries = []
    for domain_pack in domain_packs:
        match = domain_pack.get("match", {})
        capability_exposure = domain_pack.get("capability_exposure", {})
        compile_projection = domain_pack.get("compile_projection", {})
        runtime_projection = domain_pack.get("runtime_projection", {})
        pack_summaries.append(
            {
                "domain_pack_id": domain_pack["domain_pack_id"],
                "enabled": domain_pack["enabled"],
                "matched_presets": match.get("preset_ids", []),
                "matched_task_kinds": match.get("task_kinds", []),
                "preferred_adapter_name": capability_exposure.get("preferred_adapter_name"),
                "capability_tags": capability_exposure.get("capability_tags", []),
                "artifact_label": compile_projection.get("artifact_label"),
                "goal_prefix": compile_projection.get("goal_prefix"),
                "artifact_context_lines": compile_projection.get("artifact_context_lines", []),
                "operator_label": runtime_projection.get("operator_label"),
                "evidence_expectations": runtime_projection.get("evidence_expectations", []),
                "platform_sections_present": {
                    "match": bool(match),
                    "capability_exposure": bool(capability_exposure),
                    "compile_projection": bool(compile_projection),
                    "runtime_projection": bool(runtime_projection),
                },
            }
        )

    overall_platformized = bool(pack_summaries) and all(
        all(item["platform_sections_present"].values()) for item in pack_summaries
    )
    return {
        "platformized_pack_count": len(pack_summaries),
        "overall_platformized": overall_platformized,
        "pack_summaries": pack_summaries,
        "recommended_next_step": "keep the first pack family narrow and deepen reusable platform boundaries before adding new families",
    }


def build_review_policy_report(
    db_path: str | Path | None = None,
    decision_table_path: str | Path | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    presets = _load_policy_presets(db_path)
    decision_table = _parse_review_decision_table(decision_table_path)
    debt_report = build_tech_debt_report(registry_path)
    debt_item = next((item for item in debt_report["open_items"] if item["debt_id"] == "TD-006"), None)
    if debt_item is None:
        debt_item = next((item for item in debt_report["repaid_items"] if item["debt_id"] == "TD-006"), None)

    presets_by_policy: dict[str, list[PresetDefinition]] = defaultdict(list)
    for preset in presets:
        presets_by_policy[str(preset.default_review_policy)].append(preset)

    policy_cases: dict[str, list[dict[str, str]]] = defaultdict(list)
    for case in decision_table["cases"]:
        path_label = case["path"]
        for policy in ReviewPolicy:
            if str(policy) in path_label:
                policy_cases[str(policy)].append(case)
                break

    supported_policies: list[dict[str, Any]] = []
    for policy in ReviewPolicy:
        policy_key = str(policy)
        policy_presets = presets_by_policy.get(policy_key, [])
        supported_policies.append(
            {
                "policy": policy_key,
                "implemented": True,
                "runtime_shape": _runtime_shape_for_policy(policy_key),
                "preset_ids": [preset.preset_id for preset in policy_presets],
                "operator_effective_states": [case["effective_review_state"] for case in policy_cases.get(policy_key, [])],
                "requires_manual_approval": any(preset.requires_manual_approval for preset in policy_presets),
                "default_task_kinds": sorted(
                    {str(task_kind) for preset in policy_presets for task_kind in preset.allowed_task_kinds}
                ),
            }
        )

    preset_policy_map = [
        {
            "preset_id": preset.preset_id,
            "preset_name": preset.name,
            "default_review_policy": str(preset.default_review_policy),
            "requires_manual_approval": preset.requires_manual_approval,
            "allowed_task_kinds": [str(task_kind) for task_kind in preset.allowed_task_kinds],
            "runtime_shape": _runtime_shape_for_policy(str(preset.default_review_policy)),
            "future_expansion_ready": True,
        }
        for preset in presets
    ]

    effective_states = sorted({case["effective_review_state"] for case in decision_table["cases"]})
    reference_only_candidates = _reference_only_policy_candidates()

    return {
        "source_paths": {
            "decision_table": decision_table["source_path"],
            "decision_table_markdown_compatibility": decision_table["source_paths"]["compatibility_markdown"],
            "tech_debt_registry": debt_report["source_path"],
            "tech_debt_markdown_compatibility": debt_report["source_paths"]["compatibility_markdown"],
        },
        "source_contracts": {
            "decision_table": decision_table["source_contract"],
            "tech_debt_registry": debt_report["source_contract"],
        },
        "supported_policy_count": len(supported_policies),
        "supported_policies": supported_policies,
        "preset_policy_map": preset_policy_map,
        "decision_table_cases": decision_table["cases"],
        "operator_effective_states": effective_states,
        "future_policy_candidates": reference_only_candidates,
        "debt_linkage": debt_item,
        "governance_notes": decision_table["notes"],
        "expansion_readiness": {
            "implemented_policies": [item["policy"] for item in supported_policies],
            "reference_only_candidates": [item["policy"] for item in reference_only_candidates],
            "fully_executable": not reference_only_candidates,
            "manual_review_preset_ids": [
                item["preset_id"] for item in preset_policy_map if item["requires_manual_approval"]
            ],
            "auto_review_preset_ids": [
                item["preset_id"] for item in preset_policy_map if not item["requires_manual_approval"]
            ],
        },
    }


def build_governance_metrics_report(
    db_path: str | Path | None = None,
    validation_report_path: str | Path | None = None,
    decision_table_path: str | Path | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    tech_debt = build_tech_debt_report(registry_path)
    review_policy = build_review_policy_report(
        db_path=db_path,
        decision_table_path=decision_table_path,
        registry_path=registry_path,
    )
    validation_report = _load_validation_report(validation_report_path)
    capability_routes = _load_capability_routes()
    domain_packs = _load_domain_pack_catalog()
    runtime_inventory = _load_runtime_inventory(db_path)
    checks = (validation_report or {}).get("checks", {})
    passed_check_count = sum(1 for item in checks.values() if item.get("passed") is True)
    return {
        "metrics_version": "m20_core_complete_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "source_paths": {
            "tech_debt_registry": tech_debt["source_path"],
            "decision_table": review_policy["source_paths"]["decision_table"],
            "validation_report": (
                Path(validation_report_path).as_posix()
                if validation_report_path is not None
                else DEFAULT_VALIDATION_REPORT_PATH.as_posix()
            ),
            "runtime_db": runtime_inventory["db_path"],
        },
        "tech_debt": {
            "open_debt_count": tech_debt["open_debt_count"],
            "repaid_debt_count": tech_debt["repaid_debt_count"],
            "status_counts": tech_debt["status_counts"],
            "planned_phase_counts": tech_debt["planned_phase_counts"],
            "open_debt_ids": [item["debt_id"] for item in tech_debt["open_items"]],
        },
        "review_policy": {
            "supported_policy_count": review_policy["supported_policy_count"],
            "implemented_policy_ids": review_policy["expansion_readiness"]["implemented_policies"],
            "reference_only_candidates": review_policy["expansion_readiness"]["reference_only_candidates"],
            "operator_effective_state_count": len(review_policy["operator_effective_states"]),
            "manual_review_preset_count": len(review_policy["expansion_readiness"]["manual_review_preset_ids"]),
        },
        "validation": {
            "report_present": validation_report is not None,
            "overall_passed": bool((validation_report or {}).get("overall_passed")),
            "check_count": len(checks),
            "passed_check_count": passed_check_count,
            "failed_or_missing_check_count": len(checks) - passed_check_count,
            "cluster_flow_passed": checks.get("cluster_flow", {}).get("passed"),
        },
        "platform": {
            "capability_route_count": len(capability_routes),
            "domain_pack_count": len(domain_packs),
            "enabled_domain_pack_count": sum(1 for item in domain_packs if item.get("enabled")),
        },
        "runtime_inventory": runtime_inventory,
        "automation": {
            "governance_metrics_available": True,
            "governance_alerts_available": True,
        },
    }


def build_governance_alert_report(
    db_path: str | Path | None = None,
    validation_report_path: str | Path | None = None,
    decision_table_path: str | Path | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    metrics = build_governance_metrics_report(
        db_path=db_path,
        validation_report_path=validation_report_path,
        decision_table_path=decision_table_path,
        registry_path=registry_path,
    )
    alerts: list[dict[str, Any]] = []
    if metrics["validation"]["report_present"] is False:
        alerts.append(
            {
                "alert_id": "validation_report_missing",
                "severity": "blocking",
                "message": "offline validation report is missing",
                "recommended_action": "run offline validation before freeze or release",
            }
        )
    elif metrics["validation"]["overall_passed"] is False:
        alerts.append(
            {
                "alert_id": "validation_report_failed",
                "severity": "blocking",
                "message": "offline validation report is present but not fully green",
                "recommended_action": "resolve validation failures before freeze or release",
            }
        )
    if metrics["validation"].get("cluster_flow_passed") is not True:
        alerts.append(
            {
                "alert_id": "cluster_cutover_validation_missing_or_failed",
                "severity": "blocking",
                "message": "cluster cutover validation is missing or not fully green",
                "recommended_action": "run the M20 cluster demo or offline validation cluster flow before claiming core completion",
            }
        )
    if metrics["review_policy"]["reference_only_candidates"]:
        alerts.append(
            {
                "alert_id": "reference_only_review_policy_remaining",
                "severity": "blocking",
                "message": "at least one review policy remains reference-only",
                "recommended_action": "complete runtime implementation or re-scope the policy debt explicitly",
            }
        )
    if metrics["tech_debt"]["open_debt_count"] > 0:
        alerts.append(
            {
                "alert_id": "open_tech_debt_remaining",
                "severity": "degraded",
                "message": f"{metrics['tech_debt']['open_debt_count']} tech-debt item(s) remain open",
                "recommended_action": "carry the remaining items into the next planned milestone with explicit entry-gate notes",
            }
        )
    awaiting_review_runs = metrics["runtime_inventory"].get("awaiting_review_runs", 0)
    if awaiting_review_runs > 0:
        alerts.append(
            {
                "alert_id": "awaiting_review_backlog",
                "severity": "degraded",
                "message": f"{awaiting_review_runs} run(s) are currently waiting for human review",
                "recommended_action": "clear manual review backlog before claiming a clean operator baseline",
            }
        )
    if any(alert["severity"] == "blocking" for alert in alerts):
        overall_status = "blocking"
    elif any(alert["severity"] == "degraded" for alert in alerts):
        overall_status = "degraded"
    else:
        overall_status = "clear"
    return {
        "alerts_version": "m20_core_complete_v1",
        "overall_status": overall_status,
        "alert_count": len(alerts),
        "alerts": alerts,
        "metrics_snapshot": {
            "open_debt_count": metrics["tech_debt"]["open_debt_count"],
            "supported_policy_count": metrics["review_policy"]["supported_policy_count"],
            "validation_overall_passed": metrics["validation"]["overall_passed"],
            "cluster_flow_passed": metrics["validation"].get("cluster_flow_passed"),
            "awaiting_review_runs": awaiting_review_runs,
        },
    }


def build_release_readiness_report(
    db_path: str | Path | None = None,
    validation_report_path: str | Path | None = None,
    decision_table_path: str | Path | None = None,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    review_policy = build_review_policy_report(
        db_path=db_path,
        decision_table_path=decision_table_path,
        registry_path=registry_path,
    )
    tech_debt = build_tech_debt_report(registry_path)
    governance_metrics = build_governance_metrics_report(
        db_path=db_path,
        validation_report_path=validation_report_path,
        decision_table_path=decision_table_path,
        registry_path=registry_path,
    )
    governance_alerts = build_governance_alert_report(
        db_path=db_path,
        validation_report_path=validation_report_path,
        decision_table_path=decision_table_path,
        registry_path=registry_path,
    )
    validation_report = _load_validation_report(validation_report_path)
    capability_routes = _load_capability_routes()
    domain_packs = _load_domain_pack_catalog()
    validation_summary = None
    validation_evidence = {
        "source_path": (
            Path(validation_report_path).as_posix()
            if validation_report_path is not None
            else DEFAULT_VALIDATION_REPORT_PATH.as_posix()
        ),
        "source_mode": "explicit_arg" if validation_report_path is not None else "default_path",
        "report_present": validation_report is not None,
        "generated_at": validation_report.get("generated_at") if validation_report is not None else None,
        "available_checks": sorted((validation_report or {}).get("checks", {}).keys()),
    }
    if validation_report is not None:
        checks = validation_report.get("checks", {})
        validation_summary = {
            "overall_passed": bool(validation_report.get("overall_passed")),
            "cli_flow_passed": checks.get("cli_flow", {}).get("passed"),
            "smoke_flow_passed": checks.get("smoke_flow", {}).get("passed"),
            "api_flow_passed": checks.get("api_flow", {}).get("passed"),
            "cluster_flow_passed": checks.get("cluster_flow", {}).get("passed"),
            "source_path": validation_evidence["source_path"],
            "generated_at": validation_evidence["generated_at"],
        }

    presets = _load_policy_presets(db_path)
    preset_ids = [item.preset_id for item in presets]

    foundation_open_debt_ids = {"TD-001", "TD-009"} & {
        item["debt_id"] for item in tech_debt["open_items"]
    }
    gates = [
        {
            "gate": "offline_validation",
            "passed": validation_summary is not None and validation_summary["overall_passed"] is True,
            "detail": "latest offline validation report is present and fully green",
        },
        {
            "gate": "review_policy_runtime",
            "passed": review_policy["supported_policy_count"] == 5,
            "detail": "five executable run-level review policies are available, including optional advisory review",
        },
        {
            "gate": "capability_registry",
            "passed": capability_routes
            == [
                {"capability": "noop", "adapter_name": "noop", "adapter_class": "NoopAdapter"},
                {"capability": "shell_exec", "adapter_name": "shell", "adapter_class": "ShellAdapter"},
                {"capability": "shell_exec", "adapter_name": "codex", "adapter_class": "CodexAdapter"},
                {"capability": "shell_exec", "adapter_name": "opencode", "adapter_class": "OpenCodeAdapter"},
            ],
            "detail": "shipped local and coding adapters are visible through CapabilityRegistry",
        },
        {
            "gate": "domain_pack_baseline",
            "passed": any(item["domain_pack_id"] == "software_delivery_pack" and item["enabled"] for item in domain_packs),
            "detail": "one enabled platformized domain pack exists with reusable match/capability/compile/runtime sections",
        },
        {
            "gate": "governance_automation",
            "passed": governance_alerts["overall_status"] != "blocking",
            "detail": "quantitative governance metrics and automated alerting are available without blocking conditions",
        },
        {
            "gate": "local_foundation_closure",
            "passed": not foundation_open_debt_ids,
            "detail": "the ownership-topology and local barrier/concurrency debt set remains retired from the open registry",
        },
        {
            "gate": "orchestration_baseline",
            "passed": "project_delivery" in preset_ids,
            "detail": "the shipped preset catalog includes the formal project_delivery orchestration baseline",
        },
        {
            "gate": "cluster_failover_core_completion",
            "passed": (
                validation_summary is not None
                and validation_summary["cluster_flow_passed"] is True
                and not any(item["debt_id"] == "TD-021" for item in tech_debt["open_items"])
            ),
            "detail": "multi-authority cluster cutover validation is green and TD-021 is retired from the open registry",
        },
    ]
    remaining_gap_map: dict[str, str] = {}
    remaining_gaps = [
        remaining_gap_map[item["debt_id"]]
        for item in tech_debt["open_items"]
        if item["debt_id"] in remaining_gap_map
    ]

    return {
        "readiness_version": "m20_core_complete_v1",
        "overall_ready": all(gate["passed"] for gate in gates),
        "gates": gates,
        "validation_summary": validation_summary,
        "validation_evidence": validation_evidence,
        "review_policy_summary": {
            "supported_policy_count": review_policy["supported_policy_count"],
            "reference_only_candidates": review_policy["expansion_readiness"]["reference_only_candidates"],
            "source_contract": review_policy["source_contracts"]["decision_table"],
        },
        "capability_routes": capability_routes,
        "domain_packs": domain_packs,
        "open_debt_ids": [item["debt_id"] for item in tech_debt["open_items"]],
        "remaining_gaps": remaining_gaps,
        "governance_metrics": governance_metrics,
        "governance_alerts": governance_alerts,
        "recommended_next_step": "use the accepted M31 Phase 0 freeze as the baseline, carry the remaining TD-STRUCT items into M32, and explicitly open an interaction-first M32 phase before new breadth work",
        "source_paths": {
            "validation_report": validation_evidence["source_path"],
            "tech_debt_registry": tech_debt["source_path"],
            "decision_table": review_policy["source_paths"]["decision_table"],
        },
        "source_contracts": {
            "tech_debt_registry": tech_debt["source_contract"],
            "decision_table": review_policy["source_contracts"]["decision_table"],
        },
    }
