from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from packages.contracts import PresetDefinition, ReviewPolicy
from packages.core_domain.domain_packs import DomainPackRegistry
from packages.core_domain.presets import load_seed_presets
from packages.core_domain.repositories import PresetRepository
from packages.worker_adapters.router import WorkerRouter


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TECH_DEBT_REGISTRY_PATH = REPO_ROOT / "docs" / "tech-debt-registry.md"
DEFAULT_REVIEW_DECISION_TABLE_PATH = REPO_ROOT / "docs" / "reviews" / "m1_review_semantics_decision_table.md"
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


def build_tech_debt_report(registry_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(registry_path) if registry_path is not None else DEFAULT_TECH_DEBT_REGISTRY_PATH
    text = path.read_text(encoding="utf-8")

    repaid_section = _extract_numbered_section(text, 2)
    open_section = _extract_numbered_section(text, 3)
    freeze_review_section = _extract_numbered_section(text, 4)

    repaid_items = [_normalize_repaid_item(row) for row in _parse_markdown_table(repaid_section)]
    open_items = [_normalize_open_item(row) for row in _parse_markdown_table(open_section)]
    status_counts = Counter(item["current_status"] for item in open_items)
    planned_phase_counts = Counter(item["planned_repayment_phase"] for item in open_items)
    introduced_phase_counts = Counter(item["introduced_in"] for item in open_items)

    return {
        "source_path": path.as_posix(),
        "repaid_debt_count": len(repaid_items),
        "open_debt_count": len(open_items),
        "status_counts": dict(status_counts),
        "planned_phase_counts": dict(planned_phase_counts),
        "introduced_phase_counts": dict(introduced_phase_counts),
        "m3_focus_items": [item for item in open_items if item["planned_repayment_phase"] == "M3"],
        "open_items": open_items,
        "repaid_items": repaid_items,
        "freeze_review_questions": _parse_numbered_lines(freeze_review_section),
    }


def _load_policy_presets(db_path: str | Path | None = None) -> list[PresetDefinition]:
    if db_path is not None:
        try:
            presets = PresetRepository(db_path).list()
        except sqlite3.OperationalError:
            presets = []
        if presets:
            return presets
    return load_seed_presets()


def _parse_review_decision_table(decision_table_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(decision_table_path) if decision_table_path is not None else DEFAULT_REVIEW_DECISION_TABLE_PATH
    text = path.read_text(encoding="utf-8")
    cases_section = _extract_subsection(text, "## Cases")
    notes_section = _extract_subsection(text, "## Notes")
    rows = _parse_markdown_table(cases_section)
    return {
        "source_path": path.as_posix(),
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


def _runtime_shape_for_policy(policy: str) -> str:
    if policy == str(ReviewPolicy.auto_only):
        return "execution_then_auto_review_terminal"
    if policy == str(ReviewPolicy.recommended):
        return "execution_then_auto_review_or_human_escalation"
    if policy == str(ReviewPolicy.human_required):
        return "execution_then_await_human_review"
    if policy == str(ReviewPolicy.mandatory):
        return "execution_then_auto_review_then_human_signoff"
    return "reference_only"


def _reference_only_policy_candidates() -> list[dict[str, str]]:
    return [
        {
            "policy": "optional",
            "status": "reference_only",
            "adoption_mode": "decision_table_first",
            "note": "legacy-inspired candidate; current runtime still lacks a clean advisory-only terminal shape",
        }
    ]


def _load_validation_report(validation_report_path: str | Path | None = None) -> dict[str, Any] | None:
    path = Path(validation_report_path) if validation_report_path is not None else DEFAULT_VALIDATION_REPORT_PATH
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_capability_routes() -> list[dict[str, str]]:
    return WorkerRouter().routes()


def _load_domain_pack_catalog() -> list[dict[str, Any]]:
    return [domain_pack.model_dump(mode="json") for domain_pack in DomainPackRegistry().list()]


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
            "tech_debt_registry": debt_report["source_path"],
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
            "manual_review_preset_ids": [
                item["preset_id"] for item in preset_policy_map if item["requires_manual_approval"]
            ],
            "auto_review_preset_ids": [
                item["preset_id"] for item in preset_policy_map if not item["requires_manual_approval"]
            ],
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
    validation_report = _load_validation_report(validation_report_path)
    capability_routes = _load_capability_routes()
    domain_packs = _load_domain_pack_catalog()
    validation_summary = None
    if validation_report is not None:
        checks = validation_report.get("checks", {})
        validation_summary = {
            "overall_passed": bool(validation_report.get("overall_passed")),
            "cli_flow_passed": checks.get("cli_flow", {}).get("passed"),
            "smoke_flow_passed": checks.get("smoke_flow", {}).get("passed"),
            "api_flow_passed": checks.get("api_flow", {}).get("passed"),
            "source_path": (
                Path(validation_report_path).as_posix()
                if validation_report_path is not None
                else DEFAULT_VALIDATION_REPORT_PATH.as_posix()
            ),
        }

    gates = [
        {
            "gate": "offline_validation",
            "passed": validation_summary is not None and validation_summary["overall_passed"] is True,
            "detail": "latest offline validation report is present and fully green",
        },
        {
            "gate": "review_policy_runtime",
            "passed": review_policy["supported_policy_count"] == 4,
            "detail": "four executable run-level review policies are available",
        },
        {
            "gate": "capability_registry",
            "passed": capability_routes
            == [
                {"capability": "noop", "adapter_name": "noop", "adapter_class": "NoopAdapter"},
                {"capability": "shell_exec", "adapter_name": "shell", "adapter_class": "ShellAdapter"},
                {"capability": "shell_exec", "adapter_name": "opencode", "adapter_class": "OpenCodeAdapter"},
            ],
            "detail": "shipped local and CLI adapters are visible through CapabilityRegistry",
        },
        {
            "gate": "domain_pack_baseline",
            "passed": any(item["domain_pack_id"] == "software_delivery_pack" and item["enabled"] for item in domain_packs),
            "detail": "one enabled platformized domain pack exists with reusable match/capability/compile/runtime sections",
        },
    ]
    remaining_gaps = [
        "optional review policy remains reference-only",
        "Web/TUI operator surface remains intentionally deferred",
    ]

    return {
        "readiness_version": "m4_phase_2_v1",
        "overall_ready": all(gate["passed"] for gate in gates),
        "gates": gates,
        "validation_summary": validation_summary,
        "review_policy_summary": {
            "supported_policy_count": review_policy["supported_policy_count"],
            "reference_only_candidates": review_policy["expansion_readiness"]["reference_only_candidates"],
        },
        "capability_routes": capability_routes,
        "domain_packs": domain_packs,
        "open_debt_ids": [item["debt_id"] for item in tech_debt["open_items"]],
        "remaining_gaps": remaining_gaps,
        "recommended_next_step": "close current milestone or explicitly pull optional into a new phase",
        "source_paths": {
            "validation_report": validation_summary["source_path"] if validation_summary is not None else None,
            "tech_debt_registry": tech_debt["source_path"],
            "decision_table": review_policy["source_paths"]["decision_table"],
        },
    }
