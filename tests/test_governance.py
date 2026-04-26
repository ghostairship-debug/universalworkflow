import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from packages.core_domain import governance as governance_module
from packages.core_domain.governance import (
    build_domain_pack_platform_report,
    build_governance_alert_report,
    build_governance_metrics_report,
    build_release_readiness_report,
    build_review_policy_report,
    build_tech_debt_report,
)

OPEN_DEBT_IDS: list[str] = [
    "M77-PROVIDER-001",
    "M77-MMX-001",
    "M77-VERTEX-001",
    "M77-LANGCHAIN-001",
    "M77-PIPE-001",
    "M67-CARRY-001",
]
BLOCKING_OPEN_DEBT_IDS: list[str] = []


def test_optional_modules_registry_records_review_and_delete_conditions() -> None:
    registry_path = Path("docs/governance/optional_modules.json")
    payload = json.loads(registry_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "m73_optional_modules_v1"
    modules = {item["module_id"]: item for item in payload["modules"]}
    assert {
        "scheduler_authority_cluster_runtime",
        "remote_worker_api",
        "external_worker_pools",
    } <= set(modules)
    for item in modules.values():
        assert item["paths"]
        assert item["review_at"]
        assert item["rationale"]
        assert item["delete_condition"]
        assert item["doctor_behavior"] == "warn_after_review_at"


def test_build_tech_debt_report_parses_registry_sections(tmp_path: Path) -> None:
    registry_path = tmp_path / "tech-debt-registry.md"
    registry_path.write_text(
        """# Technical Debt Registry

# 2. Repaid Debt

| ID | Description | Introduced In | Repaid In | Result |
| --- | --- | --- | --- | --- |
| TD-002 | resolver gap | M0 | M1 | fixed |

# 3. Open Debt

| ID | Description | Introduced In | Planned Repayment Phase | Current Status | Blocking Impact |
| --- | --- | --- | --- | --- | --- |
| TD-007 | events minimal | M0 | M3 | partially_repaid | blocks observability |
| TD-010 | debt docs only | M0 | M3 | partially_repaid | blocks dashboard |

# 4. Freeze Review Questions

1. Are all accepted deferrals recorded?
2. Is any moved work still missing from the registry?
""",
        encoding="utf-8",
    )

    report = build_tech_debt_report(registry_path)

    assert report["repaid_debt_count"] == 1
    assert report["open_debt_count"] == 2
    assert report["status_counts"] == {"partially_repaid": 2}
    assert report["planned_phase_counts"] == {"M3": 2}
    assert [item["debt_id"] for item in report["m3_focus_items"]] == ["TD-007", "TD-010"]
    assert report["freeze_review_questions"] == [
        "Are all accepted deferrals recorded?",
        "Is any moved work still missing from the registry?",
    ]
    assert report["source_contract"] == "markdown_compatibility"


def test_build_tech_debt_report_prefers_structured_sources_when_json_is_provided(tmp_path: Path) -> None:
    registry_path = tmp_path / "tech-debt-registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "v1",
                "repaid_items": [
                    {
                        "debt_id": "TD-001",
                        "description": "resolved",
                        "introduced_in": "M0",
                        "repaid_in": "M1",
                        "result": "fixed",
                    }
                ],
                "open_items": [
                    {
                        "debt_id": "TD-010",
                        "description": "still open",
                        "introduced_in": "M1",
                        "planned_repayment_phase": "Pre-M8",
                        "current_status": "active",
                        "blocking_impact": "blocks freeze gate",
                    }
                ],
                "freeze_review_questions": ["Is the structured source readable?"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_tech_debt_report(registry_path)

    assert report["source_contract"] == "structured_json"
    assert report["repaid_debt_count"] == 1
    assert report["open_debt_count"] == 1
    assert report["blocking_open_count"] == 0
    assert report["carry_forward_count"] == 0
    assert report["active_gate_focus_items"][0]["debt_id"] == "TD-010"


def test_build_tech_debt_report_projects_blocking_and_carry_forward_items(tmp_path: Path) -> None:
    registry_path = tmp_path / "tech-debt-registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "v1",
                "repaid_items": [],
                "open_items": [
                    {
                        "debt_id": "M67-BLOCKING",
                        "description": "must close",
                        "introduced_in": "M67",
                        "planned_repayment_phase": "M67",
                        "current_status": "blocking_open",
                        "blocking_impact": "blocks release",
                    },
                    {
                        "debt_id": "M67-CARRY",
                        "description": "can carry",
                        "introduced_in": "M67",
                        "planned_repayment_phase": "Post-M67",
                        "current_status": "carry_forward",
                        "blocking_impact": "non-blocking",
                    },
                ],
                "obsolete_items": [{"debt_id": "OLD", "result": "superseded"}],
                "freeze_review_questions": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_tech_debt_report(registry_path)

    assert report["open_debt_count"] == 2
    assert report["blocking_open_count"] == 1
    assert report["carry_forward_count"] == 1
    assert report["obsolete_debt_count"] == 1
    assert [item["debt_id"] for item in report["blocking_open_items"]] == ["M67-BLOCKING"]
    assert [item["debt_id"] for item in report["carry_forward_items"]] == ["M67-CARRY"]


def test_build_tech_debt_report_structured_source_projects_compatibility_path_when_available(
    tmp_path: Path,
    monkeypatch,
) -> None:
    registry_path = tmp_path / "tech-debt-registry.json"
    compatibility_path = tmp_path / "tech-debt-registry.md"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "v1",
                "repaid_items": [],
                "open_items": [],
                "freeze_review_questions": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    compatibility_path.write_text("# Technical Debt Registry\n", encoding="utf-8")
    monkeypatch.setattr(governance_module, "DEFAULT_TECH_DEBT_REGISTRY_PATH", compatibility_path)

    report = build_tech_debt_report(registry_path)

    assert report["source_contract"] == "structured_json"
    assert report["source_path"] == registry_path.as_posix()
    assert report["source_paths"]["canonical"] == registry_path.as_posix()
    assert report["source_paths"]["compatibility_markdown"] == compatibility_path.as_posix()


def test_build_tech_debt_report_structured_source_leaves_compatibility_path_optional(
    tmp_path: Path,
    monkeypatch,
) -> None:
    registry_path = tmp_path / "tech-debt-registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "v1",
                "repaid_items": [],
                "open_items": [],
                "freeze_review_questions": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    missing_compatibility_path = tmp_path / "missing-tech-debt-registry.md"
    monkeypatch.setattr(governance_module, "DEFAULT_TECH_DEBT_REGISTRY_PATH", missing_compatibility_path)

    report = build_tech_debt_report(registry_path)

    assert report["source_contract"] == "structured_json"
    assert report["source_paths"]["canonical"] == registry_path.as_posix()
    assert report["source_paths"]["compatibility_markdown"] is None


def test_build_review_policy_report_projects_current_and_future_policy_catalog(tmp_path: Path) -> None:
    registry_path = tmp_path / "tech-debt-registry.md"
    registry_path.write_text(
        """# Technical Debt Registry

# 2. Repaid Debt

| ID | Description | Introduced In | Repaid In | Result |
| --- | --- | --- | --- | --- |
| TD-002 | resolver gap | M0 | M1 | fixed |

# 3. Open Debt

| ID | Description | Introduced In | Planned Repayment Phase | Current Status | Blocking Impact |
| --- | --- | --- | --- | --- | --- |
| TD-006 | review policy narrow | M0 | M4 | partially_repaid | blocks richer policy |

# 4. Freeze Review Questions

1. Are all accepted deferrals recorded?
""",
        encoding="utf-8",
    )
    decision_table_path = tmp_path / "decision-table.md"
    decision_table_path.write_text(
        """# M1 Review Semantics Decision Table

## Cases

| Path | Latest Verdict | Effective Review State |
| --- | --- | --- |
| `auto_only` run completed successfully | auto pass | `auto_passed` |
| `auto_only` run completed with failing review | auto fail | `auto_failed` |
| `optional` run completed after advisory auto pass | auto pass | `advisory_passed` |
| `optional` run failed during execution after advisory auto fail | auto fail | `advisory_failed` |
| `recommended` run completed after auto pass | auto pass | `auto_passed` |
| `recommended` run escalated after auto fail and is waiting for operator decision | auto fail | `human_pending` |
| `human_required` run waiting for operator decision | none | `human_pending` |
| `mandatory` run is waiting for operator decision after auto pass | auto pass | `human_pending` |
| `mandatory` run rejected by operator | human fail | `human_rejected` |

## Notes

- Keep current states backward compatible.
- `optional` is now executable as an advisory-only terminal policy.
""",
        encoding="utf-8",
    )

    report = build_review_policy_report(
        decision_table_path=decision_table_path,
        registry_path=registry_path,
    )

    assert report["supported_policy_count"] == 5
    assert [item["policy"] for item in report["supported_policies"]] == [
        "auto_only",
        "optional",
        "recommended",
        "human_required",
        "mandatory",
    ]
    assert report["expansion_readiness"]["reference_only_candidates"] == []
    assert report["expansion_readiness"]["fully_executable"] is True
    assert report["debt_linkage"]["debt_id"] == "TD-006"
    assert "human_pending" in report["operator_effective_states"]
    assert "advisory_failed" in report["operator_effective_states"]
    assert "mandatory" in report["expansion_readiness"]["implemented_policies"]
    optional = next(item for item in report["preset_policy_map"] if item["preset_id"] == "optional_delivery")
    advisory = next(item for item in report["preset_policy_map"] if item["preset_id"] == "advisory_delivery")
    guarded = next(item for item in report["preset_policy_map"] if item["preset_id"] == "guarded_delivery")
    assert optional["runtime_shape"] == "execution_then_advisory_review_terminal"
    assert advisory["runtime_shape"] == "execution_then_auto_review_or_human_escalation"
    assert guarded["requires_manual_approval"] is True
    assert report["source_contracts"]["decision_table"] == "markdown_compatibility"


def test_build_release_readiness_report_projects_current_closeout_gates(tmp_path: Path) -> None:
    validation_report_path = tmp_path / "offline_validation_report.json"
    validation_report_path.write_text(
        json.dumps(
            {
                "overall_passed": True,
                "checks": {
                    "cli_flow": {"passed": True},
                    "smoke_flow": {"passed": True},
                    "api_flow": {"passed": True},
                    "cluster_flow": {"passed": True},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_release_readiness_report(validation_report_path=validation_report_path)

    assert report["overall_ready"] is False
    assert [gate["gate"] for gate in report["gates"]] == [
        "offline_validation",
        "review_policy_runtime",
        "capability_registry",
        "domain_pack_baseline",
        "governance_automation",
        "local_foundation_closure",
        "orchestration_baseline",
        "cluster_failover_core_completion",
    ]
    assert report["validation_summary"]["overall_passed"] is True
    assert report["review_policy_summary"]["supported_policy_count"] == 5
    assert report["capability_routes"] == [
        {"capability": "noop", "adapter_name": "noop", "adapter_class": "NoopAdapter"},
        {"capability": "shell_exec", "adapter_name": "shell", "adapter_class": "ShellAdapter"},
        {"capability": "shell_exec", "adapter_name": "codex", "adapter_class": "CodexAdapter"},
        {"capability": "shell_exec", "adapter_name": "opencode", "adapter_class": "OpenCodeAdapter"},
    ]
    assert [item["domain_pack_id"] for item in report["domain_packs"]] == ["software_delivery_pack"]
    assert "platformized domain pack" in report["gates"][3]["detail"]
    assert report["remaining_gaps"] == []
    assert report["open_debt_ids"] == OPEN_DEBT_IDS
    assert report["governance_alerts"]["overall_status"] == "blocking"
    assert any(alert["alert_id"] == "open_tech_debt_remaining" for alert in report["governance_alerts"]["alerts"])
    assert report["governance_metrics"]["review_policy"]["supported_policy_count"] == 5
    assert report["validation_evidence"]["report_present"] is True
    assert report["validation_evidence"]["source_mode"] == "explicit_arg"
    assert report["validation_summary"]["generated_at"] is None
    assert report["validation_summary"]["is_fresh"] is False


def test_build_release_readiness_report_rejects_stale_validation_success(tmp_path: Path) -> None:
    validation_report_path = tmp_path / "offline_validation_report.json"
    validation_report_path.write_text(
        json.dumps(
            {
                "generated_at": (datetime.now(UTC) - timedelta(days=2)).isoformat(),
                "overall_passed": True,
                "checks": {
                    "cli_flow": {"passed": True},
                    "smoke_flow": {"passed": True},
                    "api_flow": {"passed": True},
                    "cluster_flow": {"passed": True},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_release_readiness_report(validation_report_path=validation_report_path)
    offline_gate = next(gate for gate in report["gates"] if gate["gate"] == "offline_validation")

    assert offline_gate["passed"] is False
    assert report["validation_summary"]["overall_passed"] is True
    assert report["validation_summary"]["is_fresh"] is False
    assert report["validation_summary"]["stale_reason"] == "stale_generated_at"
    assert any(alert["alert_id"] == "validation_report_stale" for alert in report["governance_alerts"]["alerts"])


def test_build_domain_pack_platform_report_projects_platform_sections() -> None:
    report = build_domain_pack_platform_report()

    assert report["platformized_pack_count"] == 1
    assert report["overall_platformized"] is True
    pack = report["pack_summaries"][0]
    assert pack["domain_pack_id"] == "software_delivery_pack"
    assert pack["preferred_adapter_name"] == "shell"
    assert pack["artifact_label"] == "software_delivery"
    assert pack["operator_label"] == "software-delivery"
    assert all(pack["platform_sections_present"].values())


def test_build_review_policy_report_falls_back_to_seed_presets_when_db_is_not_bootstrapped(tmp_path: Path) -> None:
    report = build_review_policy_report(db_path=tmp_path / "missing.db")

    assert report["supported_policy_count"] == 5
    assert [item["preset_id"] for item in report["preset_policy_map"]] == [
        "feature_delivery",
        "optional_delivery",
        "research_spike",
        "advisory_delivery",
        "guarded_delivery",
        "research_spike_reviewable",
        "project_delivery",
        "guarded_project_delivery",
    ]


def test_build_governance_metrics_report_projects_quantitative_inventory(tmp_path: Path) -> None:
    validation_report_path = tmp_path / "offline_validation_report.json"
    validation_report_path.write_text(
        json.dumps(
            {
                "overall_passed": True,
                "checks": {
                    "cli_flow": {"passed": True},
                    "smoke_flow": {"passed": True},
                    "api_flow": {"passed": True},
                    "cluster_flow": {"passed": True},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_governance_metrics_report(
        db_path=tmp_path / "missing.db",
        validation_report_path=validation_report_path,
    )

    assert report["metrics_version"] == "m20_core_complete_v1"
    assert report["tech_debt"]["open_debt_ids"] == OPEN_DEBT_IDS
    assert report["tech_debt"]["blocking_open_debt_ids"] == BLOCKING_OPEN_DEBT_IDS
    assert report["review_policy"]["supported_policy_count"] == 5
    assert report["review_policy"]["reference_only_candidates"] == []
    assert report["validation"]["overall_passed"] is True
    assert report["automation"]["governance_alerts_available"] is True


def test_build_governance_alert_report_is_blocking_when_m67_debt_is_open(tmp_path: Path) -> None:
    validation_report_path = tmp_path / "offline_validation_report.json"
    validation_report_path.write_text(
        json.dumps(
            {
                "overall_passed": True,
                "checks": {
                    "cli_flow": {"passed": True},
                    "smoke_flow": {"passed": True},
                    "api_flow": {"passed": True},
                    "cluster_flow": {"passed": True},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_governance_alert_report(
        db_path=tmp_path / "missing.db",
        validation_report_path=validation_report_path,
    )

    assert report["overall_status"] == "blocking"
    assert any(alert["alert_id"] == "open_tech_debt_remaining" for alert in report["alerts"])
    assert not any(alert["alert_id"] == "reference_only_review_policy_remaining" for alert in report["alerts"])
