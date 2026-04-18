from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app
from packages.contracts import RuntimeClaim, RuntimeGraphStep, RuntimeStateRef, WorkerLease
from packages.core_domain.db import unit_of_work
from packages.core_domain.services import OrchestratorService


runner = CliRunner()


def _invoke(tmp_path: Path, *args: str):
    return runner.invoke(app, ["--db-path", str(tmp_path / "workflow.db"), *args])


def test_cli_db_reset_and_preset_list(tmp_path: Path) -> None:
    reset_result = _invoke(tmp_path, "db", "reset")
    assert reset_result.exit_code == 0
    payload = json.loads(reset_result.stdout)
    assert payload["seeded_presets"] == [
        "feature_delivery",
        "research_spike",
        "advisory_delivery",
        "guarded_delivery",
    ]

    preset_result = _invoke(tmp_path, "preset", "list", "--json")
    assert preset_result.exit_code == 0
    presets = json.loads(preset_result.stdout)
    assert {preset["preset_id"] for preset in presets} == {
        "feature_delivery",
        "research_spike",
        "advisory_delivery",
        "guarded_delivery",
    }

    domain_pack_result = _invoke(tmp_path, "domain-pack", "list", "--json")
    assert domain_pack_result.exit_code == 0
    domain_packs = json.loads(domain_pack_result.stdout)
    assert [domain_pack["domain_pack_id"] for domain_pack in domain_packs] == ["software_delivery_pack"]
    assert domain_packs[0]["compile_projection"]["artifact_label"] == "software_delivery"
    assert domain_packs[0]["runtime_projection"]["operator_label"] == "software-delivery"

    domain_pack_preview = _invoke(
        tmp_path,
        "domain-pack",
        "resolve",
        "--preset",
        "feature_delivery",
        "--task-kind",
        "shell_exec",
    )
    assert domain_pack_preview.exit_code == 0
    preview_payload = json.loads(domain_pack_preview.stdout)
    assert preview_payload["resolved"] is True
    assert preview_payload["domain_pack"]["domain_pack_id"] == "software_delivery_pack"

    domain_pack_validate = _invoke(tmp_path, "domain-pack", "validate")
    assert domain_pack_validate.exit_code == 0
    validate_payload = json.loads(domain_pack_validate.stdout)
    assert validate_payload["passed"] is True
    assert validate_payload["issue_count"] == 0

    capability_result = _invoke(tmp_path, "capability", "list")
    assert capability_result.exit_code == 0
    capability_routes = json.loads(capability_result.stdout)
    assert capability_routes == [
        {"capability": "noop", "adapter_name": "noop", "adapter_class": "NoopAdapter"},
        {"capability": "shell_exec", "adapter_name": "shell", "adapter_class": "ShellAdapter"},
        {"capability": "shell_exec", "adapter_name": "opencode", "adapter_class": "OpenCodeAdapter"},
    ]

    simulation_policy_result = _invoke(tmp_path, "simulation", "policy", "list")
    assert simulation_policy_result.exit_code == 0
    simulation_policies = json.loads(simulation_policy_result.stdout)
    assert [item["policy_id"] for item in simulation_policies] == [
        "advisory_failure_simulation",
        "delivery_consistency_simulation",
        "research_no_simulation",
    ]

    suggest_result = _invoke(tmp_path, "run", "suggest-presets", "--goal", "Research the current architecture")
    assert suggest_result.exit_code == 0
    suggestions = json.loads(suggest_result.stdout)
    assert suggestions[0]["preset_id"] == "research_spike"

    memory_namespace_result = _invoke(tmp_path, "memory", "namespace", "list")
    assert memory_namespace_result.exit_code == 0
    memory_namespaces = json.loads(memory_namespace_result.stdout)
    assert [item["namespace_id"] for item in memory_namespaces] == ["repo", "failure", "policy", "release"]

    memory_item_result = _invoke(tmp_path, "memory", "item", "list")
    assert memory_item_result.exit_code == 0
    assert json.loads(memory_item_result.stdout) == []


def test_cli_governance_tech_debt_report(tmp_path: Path) -> None:
    result = _invoke(tmp_path, "governance", "tech-debt")
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["open_debt_count"] >= 1
    assert "TD-010" in [item["debt_id"] for item in payload["open_items"]]
    assert payload["planned_phase_counts"]["M3"] >= 1


def test_cli_governance_review_policy_report(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    result = _invoke(tmp_path, "governance", "review-policy")
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["supported_policy_count"] == 4
    assert [item["policy"] for item in payload["supported_policies"]] == [
        "auto_only",
        "recommended",
        "human_required",
        "mandatory",
    ]
    assert payload["expansion_readiness"]["reference_only_candidates"] == ["optional"]
    assert payload["debt_linkage"]["debt_id"] == "TD-006"


def test_cli_governance_release_readiness_report(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    validation_report_path = tmp_path / "offline_validation_report.json"
    validation_report_path.write_text(
        json.dumps(
            {
                "overall_passed": True,
                "checks": {
                    "cli_flow": {"passed": True},
                    "smoke_flow": {"passed": True},
                    "api_flow": {"passed": True},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = _invoke(
        tmp_path,
        "governance",
        "release-readiness",
        "--validation-report-path",
        str(validation_report_path),
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["overall_ready"] is True
    assert payload["validation_summary"]["overall_passed"] is True
    assert [item["domain_pack_id"] for item in payload["domain_packs"]] == ["software_delivery_pack"]
    assert "platformized domain pack" in payload["gates"][3]["detail"]


def test_cli_governance_release_readiness_report_works_without_bootstrapped_db(tmp_path: Path) -> None:
    validation_report_path = tmp_path / "offline_validation_report.json"
    validation_report_path.write_text(
        json.dumps(
            {
                "overall_passed": True,
                "checks": {
                    "cli_flow": {"passed": True},
                    "smoke_flow": {"passed": True},
                    "api_flow": {"passed": True},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = _invoke(
        tmp_path,
        "governance",
        "release-readiness",
        "--validation-report-path",
        str(validation_report_path),
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["overall_ready"] is True


def test_cli_governance_domain_pack_report(tmp_path: Path) -> None:
    result = _invoke(tmp_path, "governance", "domain-pack")
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["platformized_pack_count"] == 1
    assert payload["overall_platformized"] is True
    assert payload["pack_summaries"][0]["domain_pack_id"] == "software_delivery_pack"


def test_cli_tui_renders_single_snapshot(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Render one dashboard run",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]

    result = _invoke(tmp_path, "tui", "--once", "--run-id", run_id)
    assert result.exit_code == 0
    assert "Universal Agentic Workflow OS TUI" in result.stdout
    assert run_id in result.stdout


def test_cli_run_create_status_timeline_and_evidence(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")

    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Build one CLI artifact",
        "--preset",
        "feature_delivery",
        "--prepare",
        "--execute",
    )
    assert create_result.exit_code == 0
    create_payload = json.loads(create_result.stdout)
    run_id = create_payload["run"]["run_id"]
    runtime_task_id = create_payload["prepared_task_id"]
    assert create_payload["run"]["status"] == "completed"
    assert create_payload["review_decision"] == "pass"
    assert create_payload["domain_pack_id"] == "software_delivery_pack"
    assert create_payload["capability_adapter"] == "shell"

    status_result = _invoke(tmp_path, "run", "status", run_id)
    assert status_result.exit_code == 0
    status_payload = json.loads(status_result.stdout)
    assert status_payload["status"] == "completed"
    assert runtime_task_id in status_payload["runtime_task_ids"]
    assert status_payload["runtime_gateway"]["provider"] == "null"
    assert status_payload["effective_review_state"] == "auto_passed"
    assert status_payload["domain_pack"]["domain_pack_id"] == "software_delivery_pack"
    assert status_payload["domain_pack"]["matched_preset_id"] == "feature_delivery"
    assert status_payload["capability_resolution"]["adapter_name"] == "shell"
    assert status_payload["latest_review_verdict"]["decision"] == "pass"
    assert status_payload["failure_reason"] is None
    assert status_payload["recoverability_hint"] == "none"

    timeline_result = _invoke(tmp_path, "run", "timeline", run_id, "--json")
    assert timeline_result.exit_code == 0
    timeline = json.loads(timeline_result.stdout)
    assert "run_completed" in [item["event_type"] for item in timeline]

    evidence_result = _invoke(tmp_path, "task", "evidence", runtime_task_id)
    assert evidence_result.exit_code == 0
    evidence = json.loads(evidence_result.stdout)
    assert evidence["artifact_refs"]

    memory_result = _invoke(tmp_path, "run", "memory-candidates", run_id)
    assert memory_result.exit_code == 0
    memory_candidates = json.loads(memory_result.stdout)
    assert {item["namespace_id"] for item in memory_candidates} == {"repo", "policy", "release"}

    selected_candidate = next(item for item in memory_candidates if item["namespace_id"] == "policy")
    materialize_result = _invoke(
        tmp_path,
        "run",
        "materialize-memory",
        run_id,
        "--candidate-id",
        selected_candidate["candidate_id"],
    )
    assert materialize_result.exit_code == 0
    materialized_item = json.loads(materialize_result.stdout)
    assert materialized_item["namespace_id"] == "policy"

    run_memory_items_result = _invoke(tmp_path, "run", "memory-items", run_id)
    assert run_memory_items_result.exit_code == 0
    run_memory_items = json.loads(run_memory_items_result.stdout)
    assert [item["namespace_id"] for item in run_memory_items] == ["policy"]

    namespace_memory_items_result = _invoke(tmp_path, "memory", "item", "list", "--namespace", "policy")
    assert namespace_memory_items_result.exit_code == 0
    namespace_memory_items = json.loads(namespace_memory_items_result.stdout)
    assert [item["run_id"] for item in namespace_memory_items] == [run_id]

    retrieval_preview_result = _invoke(
        tmp_path,
        "memory",
        "retrieve-preview",
        "--preset",
        "feature_delivery",
        "--namespace",
        "policy",
    )
    assert retrieval_preview_result.exit_code == 0
    retrieval_preview = json.loads(retrieval_preview_result.stdout)
    assert retrieval_preview["selected_memory_item_ids"] == [materialized_item["memory_item_id"]]

    simulation_result = _invoke(tmp_path, "run", "simulation", run_id)
    assert simulation_result.exit_code == 0
    simulation_payload = json.loads(simulation_result.stdout)
    assert simulation_payload["policy_id"] == "delivery_consistency_simulation"
    assert simulation_payload["status"] == "passed"

    record_simulation_result = _invoke(tmp_path, "run", "record-simulation", run_id)
    assert record_simulation_result.exit_code == 0
    record_simulation_payload = json.loads(record_simulation_result.stdout)
    assert record_simulation_payload["policy_id"] == "delivery_consistency_simulation"
    assert record_simulation_payload["recorded_from"] == "manual_request"

    simulations_result = _invoke(tmp_path, "run", "simulations", run_id)
    assert simulations_result.exit_code == 0
    simulations_payload = json.loads(simulations_result.stdout)
    assert [item["recorded_from"] for item in simulations_payload] == ["lifecycle_terminal", "manual_request"]
    assert simulations_payload[-1]["record_id"] == record_simulation_payload["record_id"]
    assert retrieval_preview["namespace_ids"] == ["policy"]


def test_cli_run_create_with_human_required_returns_awaiting_review(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")

    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Research from create path",
        "--preset",
        "research_spike",
        "--prepare",
        "--execute",
    )
    assert create_result.exit_code == 0
    create_payload = json.loads(create_result.stdout)
    run_id = create_payload["run"]["run_id"]

    assert create_payload["run"]["status"] == "awaiting_review"
    assert create_payload["review_decision"] is None
    assert create_payload["evidence_id"]


def test_cli_compile_supports_explicit_memory_item_selection(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")

    source_create = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Source memory item",
        "--preset",
        "feature_delivery",
        "--prepare",
        "--execute",
    )
    source_payload = json.loads(source_create.stdout)
    source_run_id = source_payload["run"]["run_id"]
    source_candidates = json.loads(_invoke(tmp_path, "run", "memory-candidates", source_run_id).stdout)
    policy_candidate = next(item for item in source_candidates if item["namespace_id"] == "policy")
    materialized_item = json.loads(
        _invoke(
            tmp_path,
            "run",
            "materialize-memory",
            source_run_id,
            "--candidate-id",
            policy_candidate["candidate_id"],
        ).stdout
    )

    target_create = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Target memory-aware compile",
        "--preset",
        "feature_delivery",
    )
    target_run_id = json.loads(target_create.stdout)["run"]["run_id"]

    compile_result = _invoke(
        tmp_path,
        "run",
        "compile",
        target_run_id,
        "--memory-item-id",
        materialized_item["memory_item_id"],
    )
    assert compile_result.exit_code == 0
    compile_payload = json.loads(compile_result.stdout)
    assert compile_payload["memory_preview"]["selected_memory_item_ids"] == [materialized_item["memory_item_id"]]

    detail_result = _invoke(tmp_path, "run", "status-detail", target_run_id)
    assert detail_result.exit_code == 0
    detail_payload = json.loads(detail_result.stdout)
    assert detail_payload["memory_retrieval_preview"]["selected_memory_item_ids"] == [materialized_item["memory_item_id"]]


def test_cli_recommended_review_escalates_after_auto_fail(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")

    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Advisory escalate via CLI",
        "--preset",
        "advisory_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]
    compile_result = _invoke(tmp_path, "run", "compile", run_id)
    runtime_task_id = json.loads(compile_result.stdout)["runtime_task_id"]
    with unit_of_work(tmp_path / "workflow.db") as connection:
        connection.execute(
            "UPDATE task_packets SET command_json = ? WHERE runtime_task_id = ?",
            (json.dumps(["python", "-c", "import sys; sys.exit(2)"]), runtime_task_id),
        )

    resume_result = _invoke(tmp_path, "run", "resume", run_id)
    assert resume_result.exit_code == 0
    resume_payload = json.loads(resume_result.stdout)
    assert resume_payload["run"]["status"] == "awaiting_review"
    assert resume_payload["review_decision"] == "fail"

    status_result = _invoke(tmp_path, "run", "status", run_id)
    assert status_result.exit_code == 0
    status_payload = json.loads(status_result.stdout)
    assert status_payload["review_policy"] == "recommended"
    assert status_payload["effective_review_state"] == "human_pending"
    assert status_payload["latest_review_verdict"]["reviewer_type"] == "auto"
    assert status_payload["latest_review_verdict"]["decision"] == "fail"


def test_cli_mandatory_review_waits_even_after_auto_pass(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")

    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Guarded delivery via CLI",
        "--preset",
        "guarded_delivery",
        "--prepare",
        "--execute",
    )
    assert create_result.exit_code == 0
    create_payload = json.loads(create_result.stdout)
    run_id = create_payload["run"]["run_id"]

    assert create_payload["run"]["status"] == "awaiting_review"
    assert create_payload["review_decision"] == "pass"

    status_result = _invoke(tmp_path, "run", "status", run_id)
    assert status_result.exit_code == 0
    status_payload = json.loads(status_result.stdout)
    assert status_payload["review_policy"] == "mandatory"
    assert status_payload["effective_review_state"] == "human_pending"
    assert status_payload["latest_review_verdict"]["reviewer_type"] == "auto"
    assert status_payload["latest_review_verdict"]["decision"] == "pass"
    assert status_payload["latest_simulation_record"]["recorded_from"] == "lifecycle_awaiting_review"

    simulations_before_approve = _invoke(tmp_path, "run", "simulations", run_id)
    assert simulations_before_approve.exit_code == 0
    assert [item["recorded_from"] for item in json.loads(simulations_before_approve.stdout)] == [
        "lifecycle_awaiting_review"
    ]

    approve_result = _invoke(tmp_path, "run", "approve", run_id)
    assert approve_result.exit_code == 0
    assert json.loads(approve_result.stdout)["run"]["status"] == "completed"

    simulations_after_approve = _invoke(tmp_path, "run", "simulations", run_id)
    assert simulations_after_approve.exit_code == 0
    assert [item["recorded_from"] for item in json.loads(simulations_after_approve.stdout)] == [
        "lifecycle_awaiting_review",
        "lifecycle_terminal",
    ]


def test_cli_compile_with_noop_task_kind_for_research_spike(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")

    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Noop research via CLI",
        "--preset",
        "research_spike",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]

    compile_result = _invoke(tmp_path, "run", "compile", run_id, "--task-kind", "noop")
    assert compile_result.exit_code == 0
    compile_payload = json.loads(compile_result.stdout)
    assert compile_payload["run"]["status"] == "prepared"

    detail_result = _invoke(tmp_path, "run", "status-detail", run_id)
    detail_payload = json.loads(detail_result.stdout)
    runtime_task_id = detail_payload["runtime_tasks"][0]["runtime_task_id"]
    assert detail_payload["runtime_tasks"][0]["task_kind"] == "noop"

    resume_result = _invoke(tmp_path, "run", "resume", run_id)
    assert resume_result.exit_code == 0
    assert json.loads(resume_result.stdout)["run"]["status"] == "awaiting_review"

    evidence_result = _invoke(tmp_path, "task", "evidence", runtime_task_id)
    evidence_payload = json.loads(evidence_result.stdout)
    assert evidence_payload["raw_execution"]["adapter_name"] == "noop"
    assert evidence_payload["artifact_refs"]


def test_cli_rejects_task_kind_outside_preset_allow_list(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Noop feature via CLI",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]

    compile_result = _invoke(tmp_path, "run", "compile", run_id, "--task-kind", "noop")
    assert compile_result.exit_code != 0
    error = json.loads(compile_result.stdout)["error"]
    assert error["code"] == "task_kind_not_allowed"
    assert error["details"]["allowed_task_kinds"] == ["shell_exec"]


def test_cli_rejects_unknown_task_kind(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Unknown kind via CLI",
        "--preset",
        "research_spike",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]

    compile_result = _invoke(tmp_path, "run", "compile", run_id, "--task-kind", "unknown_kind")
    assert compile_result.exit_code != 0
    error = json.loads(compile_result.stdout)["error"]
    assert error["code"] == "unsupported_task_kind"
    assert set(error["details"]["available_task_kinds"]) == {"shell_exec", "noop"}


def test_cli_compile_can_pin_opencode_adapter(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Pin opencode adapter via CLI",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]

    compile_result = _invoke(tmp_path, "run", "compile", run_id, "--adapter", "opencode")
    assert compile_result.exit_code == 0
    compile_payload = json.loads(compile_result.stdout)
    assert compile_payload["capability_adapter"] == "opencode"

    detail_result = _invoke(tmp_path, "run", "status-detail", run_id)
    detail_payload = json.loads(detail_result.stdout)
    assert detail_payload["capability_resolution"]["adapter_name"] == "opencode"
    assert detail_payload["runtime_tasks"][0]["task_kind"] == "shell_exec"


def test_cli_compile_rejects_unknown_adapter(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Unknown adapter via CLI",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]

    compile_result = _invoke(tmp_path, "run", "compile", run_id, "--adapter", "missing_adapter")
    assert compile_result.exit_code != 0
    error = json.loads(compile_result.stdout)["error"]
    assert error["code"] == "capability_adapter_not_found"
    assert error["details"]["available_adapters"] == ["shell", "opencode"]


def test_cli_compile_recompile_status_detail_and_handoffs(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Compile me from CLI",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]

    compile_result = _invoke(tmp_path, "run", "compile", run_id)
    assert compile_result.exit_code == 0
    compile_payload = json.loads(compile_result.stdout)
    assert compile_payload["run"]["status"] == "prepared"

    detail_result = _invoke(tmp_path, "run", "status-detail", run_id)
    assert detail_result.exit_code == 0
    detail_payload = json.loads(detail_result.stdout)
    assert detail_payload["next_action"] == "resume"
    assert detail_payload["waiting_reason"] == "awaiting_runtime_resume"
    assert detail_payload["failure_reason"] is None
    assert detail_payload["last_runtime_state"]["graph_step"] == "compiled"
    assert detail_payload["last_review_verdict"] is None
    assert detail_payload["recoverability_hint"] == "resume_run"
    assert detail_payload["handoffs"]
    assert detail_payload["effective_review_state"] == "not_requested"

    inspection_result = _invoke(tmp_path, "run", "inspect", run_id)
    assert inspection_result.exit_code == 0
    inspection_payload = json.loads(inspection_result.stdout)
    assert inspection_payload["passed"] is True
    assert inspection_payload["problem_count"] == 0
    assert inspection_payload["recommended_action"] == "none"

    handoffs_result = _invoke(tmp_path, "run", "handoffs", run_id)
    assert handoffs_result.exit_code == 0
    handoffs_payload = json.loads(handoffs_result.stdout)
    assert len(handoffs_payload) == 1

    recompile_result = _invoke(tmp_path, "run", "recompile", run_id)
    assert recompile_result.exit_code == 0
    recompile_payload = json.loads(recompile_result.stdout)
    assert recompile_payload["run"]["status"] == "prepared"


def test_cli_summary_projects_success_and_pending_states(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")

    auto_create = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Summary auto via CLI",
        "--preset",
        "feature_delivery",
    )
    auto_run_id = json.loads(auto_create.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", auto_run_id)
    _invoke(tmp_path, "run", "resume", auto_run_id)
    auto_summary = _invoke(tmp_path, "run", "summary", auto_run_id)

    human_create = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Summary human via CLI",
        "--preset",
        "research_spike",
    )
    human_run_id = json.loads(human_create.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", human_run_id)
    _invoke(tmp_path, "run", "resume", human_run_id)
    human_summary = _invoke(tmp_path, "run", "summary", human_run_id)

    assert auto_summary.exit_code == 0
    assert human_summary.exit_code == 0
    assert json.loads(auto_summary.stdout)["failure_taxonomy"]["category"] == "success"
    assert json.loads(auto_summary.stdout)["timeline_summary"]["terminal_event_type"] == "run_completed"
    assert json.loads(auto_summary.stdout)["closure_summary"]["state"] == "closed"
    assert json.loads(auto_summary.stdout)["review_summary"]["review_submitted_count"] == 1
    assert json.loads(human_summary.stdout)["failure_taxonomy"]["category"] == "review_pending"
    assert json.loads(human_summary.stdout)["review_summary"]["effective_review_state"] == "human_pending"
    assert json.loads(human_summary.stdout)["review_summary"]["review_requested_count"] == 1
    assert json.loads(human_summary.stdout)["closure_summary"]["state"] == "awaiting_review"


def test_cli_event_inspection_projects_closed_and_review_wait_states(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")

    auto_create = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Event inspection auto via CLI",
        "--preset",
        "feature_delivery",
    )
    auto_run_id = json.loads(auto_create.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", auto_run_id)
    _invoke(tmp_path, "run", "resume", auto_run_id)
    auto_event_inspection = _invoke(tmp_path, "run", "event-inspection", auto_run_id)

    human_create = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Event inspection human via CLI",
        "--preset",
        "research_spike",
    )
    human_run_id = json.loads(human_create.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", human_run_id)
    _invoke(tmp_path, "run", "resume", human_run_id)
    human_event_inspection = _invoke(tmp_path, "run", "event-inspection", human_run_id)

    assert auto_event_inspection.exit_code == 0
    assert human_event_inspection.exit_code == 0
    assert json.loads(auto_event_inspection.stdout)["closure_audit"]["state"] == "closed"
    assert json.loads(auto_event_inspection.stdout)["closure_audit"]["passed"] is True
    assert json.loads(auto_event_inspection.stdout)["event_digest"]["terminal_event_type"] == "run_completed"
    assert json.loads(human_event_inspection.stdout)["closure_audit"]["state"] == "awaiting_review"
    assert json.loads(human_event_inspection.stdout)["review_digest"]["review_requested_count"] == 1
    assert json.loads(human_event_inspection.stdout)["review_digest"]["pending_human_review"] is True


def test_cli_audit_report_projects_closed_and_review_wait_states(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")

    auto_create = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Audit report auto via CLI",
        "--preset",
        "feature_delivery",
    )
    auto_run_id = json.loads(auto_create.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", auto_run_id)
    _invoke(tmp_path, "run", "resume", auto_run_id)
    auto_report = _invoke(tmp_path, "run", "audit-report", auto_run_id)

    human_create = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Audit report human via CLI",
        "--preset",
        "research_spike",
    )
    human_run_id = json.loads(human_create.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", human_run_id)
    _invoke(tmp_path, "run", "resume", human_run_id)
    human_report = _invoke(tmp_path, "run", "audit-report", human_run_id)

    assert auto_report.exit_code == 0
    assert human_report.exit_code == 0
    assert json.loads(auto_report.stdout)["review_packet"]["closure_summary"]["state"] == "closed"
    assert json.loads(auto_report.stdout)["summary"]["failure_taxonomy"]["category"] == "success"
    assert json.loads(human_report.stdout)["review_packet"]["closure_summary"]["state"] == "awaiting_review"
    assert json.loads(human_report.stdout)["review_packet"]["effective_review_state"] == "human_pending"


def test_cli_run_cancel(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Cancel me",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]

    cancel_result = _invoke(tmp_path, "run", "cancel", run_id)
    assert cancel_result.exit_code == 0
    payload = json.loads(cancel_result.stdout)
    assert payload["status"] == "cancelled"

    second_cancel_result = _invoke(tmp_path, "run", "cancel", run_id)
    assert second_cancel_result.exit_code == 0
    second_payload = json.loads(second_cancel_result.stdout)
    assert second_payload["status"] == "cancelled"


def test_cli_resume_runs_compiled_task(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Resume me from CLI",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]

    _invoke(tmp_path, "run", "compile", run_id)
    resume_result = _invoke(tmp_path, "run", "resume", run_id)
    assert resume_result.exit_code == 0
    resume_payload = json.loads(resume_result.stdout)
    assert resume_payload["run"]["status"] == "completed"

    timeline_result = _invoke(tmp_path, "run", "timeline", run_id, "--json")
    timeline = json.loads(timeline_result.stdout)
    assert "runtime_resumed" in [item["event_type"] for item in timeline]


def test_cli_reconcile_can_apply_completed_runtime_state_alignment(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Repair via CLI",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", run_id)
    _invoke(tmp_path, "run", "resume", run_id)

    service = OrchestratorService(tmp_path / "workflow.db")
    state_ref = service.runtime_state_repo.list_for_run(run_id)[0]
    service.runtime_state_repo.upsert(
        RuntimeStateRef(
            state_ref_id=state_ref.state_ref_id,
            run_id=state_ref.run_id,
            runtime_task_id=state_ref.runtime_task_id,
            graph_step=RuntimeGraphStep.awaiting_review,
            state_payload={**state_ref.state_payload, "corrupted": True},
            is_terminal=False,
            created_at=state_ref.created_at,
        )
    )

    plan_result = _invoke(tmp_path, "run", "reconcile", run_id)
    assert plan_result.exit_code == 0
    plan_payload = json.loads(plan_result.stdout)
    assert plan_payload["problems"][0]["repair_action"] == "align_completed_runtime_state"

    apply_result = _invoke(tmp_path, "run", "reconcile", run_id, "--apply")
    assert apply_result.exit_code == 0
    apply_payload = json.loads(apply_result.stdout)
    assert apply_payload["action"] == "align_completed_runtime_state"

    inspection_result = _invoke(tmp_path, "run", "inspect", run_id)
    assert json.loads(inspection_result.stdout)["passed"] is True


def test_cli_reconcile_rejects_manual_only_problem(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Manual only repair via CLI",
        "--preset",
        "research_spike",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", run_id)
    _invoke(tmp_path, "run", "resume", run_id)

    with unit_of_work(tmp_path / "workflow.db") as connection:
        connection.execute("DELETE FROM evidence WHERE run_id = ?", (run_id,))

    apply_result = _invoke(tmp_path, "run", "reconcile", run_id, "--apply")
    assert apply_result.exit_code != 0
    error = json.loads(apply_result.stdout)["error"]
    assert error["code"] == "repair_action_not_available"


def test_cli_human_review_approve_and_reject_paths(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")

    approve_create = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Research and approve",
        "--preset",
        "research_spike",
    )
    approve_run_id = json.loads(approve_create.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", approve_run_id)
    resume_result = _invoke(tmp_path, "run", "resume", approve_run_id)
    resume_payload = json.loads(resume_result.stdout)
    assert resume_payload["run"]["status"] == "awaiting_review"
    assert resume_payload["review_decision"] is None

    waiting_status = _invoke(tmp_path, "run", "status", approve_run_id)
    waiting_payload = json.loads(waiting_status.stdout)
    assert waiting_payload["effective_review_state"] == "human_pending"
    assert waiting_payload["latest_review_verdict"] is None

    approve_result = _invoke(tmp_path, "run", "approve", approve_run_id)
    assert approve_result.exit_code == 0
    assert json.loads(approve_result.stdout)["run"]["status"] == "completed"

    approved_status = _invoke(tmp_path, "run", "status", approve_run_id)
    approved_payload = json.loads(approved_status.stdout)
    assert approved_payload["effective_review_state"] == "human_approved"
    assert approved_payload["latest_review_verdict"]["reviewer_type"] == "human"

    reject_create = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Research and reject",
        "--preset",
        "research_spike",
    )
    reject_run_id = json.loads(reject_create.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", reject_run_id)
    _invoke(tmp_path, "run", "resume", reject_run_id)

    reject_result = _invoke(tmp_path, "run", "reject", reject_run_id)
    assert reject_result.exit_code == 0
    assert json.loads(reject_result.stdout)["run"]["status"] == "failed"

    rejected_status = _invoke(tmp_path, "run", "status", reject_run_id)
    rejected_payload = json.loads(rejected_status.stdout)
    assert rejected_payload["effective_review_state"] == "human_rejected"
    assert rejected_payload["latest_review_verdict"]["decision"] == "fail"
    assert rejected_payload["failure_reason"] == "human_review_rejected"
    assert rejected_payload["recoverability_hint"] == "inspect_evidence_then_recompile"


def test_cli_status_and_claims_expose_claim_history(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Claim projection via CLI",
        "--preset",
        "feature_delivery",
        "--prepare",
        "--execute",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]

    status_result = _invoke(tmp_path, "run", "status", run_id)
    claims_result = _invoke(tmp_path, "run", "claims", run_id)

    assert status_result.exit_code == 0
    assert claims_result.exit_code == 0
    status_payload = json.loads(status_result.stdout)
    claims_payload = json.loads(claims_result.stdout)
    assert status_payload["active_claims"] == []
    assert status_payload["latest_claim"]["status"] == "released"
    assert claims_payload[0]["release_reason"] == "run_terminal"


def test_cli_status_detail_and_inspect_expose_worker_lease_projection(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Worker lease projection via CLI",
        "--preset",
        "feature_delivery",
        "--prepare",
        "--execute",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]

    detail_result = _invoke(tmp_path, "run", "status-detail", run_id)
    inspect_result = _invoke(tmp_path, "run", "inspect", run_id)

    assert detail_result.exit_code == 0
    assert inspect_result.exit_code == 0
    detail_payload = json.loads(detail_result.stdout)
    inspect_payload = json.loads(inspect_result.stdout)
    assert detail_payload["active_worker_leases"] == []
    assert detail_payload["latest_worker_lease"]["status"] == "released"
    assert detail_payload["worker_lease_projection"]["latest_adapter_name"] == "shell"
    assert inspect_payload["latest_worker_lease"]["status"] == "released"
    assert inspect_payload["worker_lease_projection"]["active_lease_count"] == 0


def test_cli_status_detail_and_inspect_expose_runtime_attempt_projection(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Attempt projection via CLI",
        "--preset",
        "research_spike",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", run_id)
    _invoke(tmp_path, "run", "resume", run_id)

    detail_result = _invoke(tmp_path, "run", "status-detail", run_id)
    inspect_result = _invoke(tmp_path, "run", "inspect", run_id)

    assert detail_result.exit_code == 0
    assert inspect_result.exit_code == 0
    detail_payload = json.loads(detail_result.stdout)
    inspect_payload = json.loads(inspect_result.stdout)
    assert detail_payload["current_runtime_attempt"]["trigger"] == "resume"
    assert detail_payload["runtime_attempt_projection"]["attempt_count"] == 2
    assert len(detail_payload["runtime_attempt_projection"]["superseded_attempt_ids"]) == 1
    assert inspect_payload["current_runtime_attempt"]["status"] == "current"
    assert inspect_payload["runtime_attempt_projection"]["current_trigger"] == "resume"


def test_cli_run_leases_lists_history(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Worker lease history via CLI",
        "--preset",
        "feature_delivery",
        "--prepare",
        "--execute",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]

    leases_result = _invoke(tmp_path, "run", "leases", run_id)

    assert leases_result.exit_code == 0
    payload = json.loads(leases_result.stdout)
    assert len(payload) == 1
    assert payload[0]["status"] == "released"
    assert payload[0]["adapter_name"] == "shell"


def test_cli_run_attempts_lists_history(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Attempt history via CLI",
        "--preset",
        "research_spike",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", run_id)
    _invoke(tmp_path, "run", "resume", run_id)

    attempts_result = _invoke(tmp_path, "run", "attempts", run_id)

    assert attempts_result.exit_code == 0
    payload = json.loads(attempts_result.stdout)
    assert [item["trigger"] for item in payload] == ["compile", "resume"]
    assert payload[0]["status"] == "superseded"
    assert payload[1]["status"] == "current"


def test_cli_status_detail_and_inspect_project_latest_snapshot(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Snapshot projection via CLI",
        "--preset",
        "research_spike",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", run_id)

    prepared_detail = _invoke(tmp_path, "run", "status-detail", run_id)
    prepared_payload = json.loads(prepared_detail.stdout)
    assert prepared_payload["latest_snapshot"]["stage"] == "compiled"
    assert prepared_payload["snapshot_count"] == 1

    _invoke(tmp_path, "run", "resume", run_id)
    inspect_result = _invoke(tmp_path, "run", "inspect", run_id)
    inspect_payload = json.loads(inspect_result.stdout)
    assert inspect_payload["latest_snapshot"]["stage"] == "awaiting_review"


def test_cli_snapshots_lists_history(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Snapshot history via CLI",
        "--preset",
        "research_spike",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", run_id)
    _invoke(tmp_path, "run", "resume", run_id)
    _invoke(tmp_path, "run", "approve", run_id)

    snapshots_result = _invoke(tmp_path, "run", "snapshots", run_id)

    assert snapshots_result.exit_code == 0
    assert [item["stage"] for item in json.loads(snapshots_result.stdout)] == [
        "compiled",
        "awaiting_review",
        "completed",
    ]


def test_cli_status_detail_projects_budget_ledger(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Budget projection via CLI",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", run_id)
    _invoke(tmp_path, "run", "resume", run_id)

    detail_result = _invoke(tmp_path, "run", "status-detail", run_id)
    detail_payload = json.loads(detail_result.stdout)

    assert detail_payload["budget_ledger"] is not None
    assert detail_payload["budget_projection"]["execution_count"] == 1
    assert detail_payload["budget_projection"]["last_return_code"] == 0


def test_cli_recompile_rejects_when_retry_budget_is_exhausted(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Budget exhausted via CLI",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", run_id)
    first_recompile = _invoke(tmp_path, "run", "recompile", run_id)
    assert first_recompile.exit_code == 0

    second_recompile = _invoke(tmp_path, "run", "recompile", run_id)

    assert second_recompile.exit_code != 0
    assert json.loads(second_recompile.stdout)["error"]["code"] == "budget_exhausted"


def test_cli_budget_reports_projection(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Budget endpoint via CLI",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", run_id)

    budget_result = _invoke(tmp_path, "run", "budget", run_id)

    assert budget_result.exit_code == 0
    payload = json.loads(budget_result.stdout)
    assert payload["budget_ledger"] is not None
    assert payload["budget_projection"]["remaining_retries"] == 1


def test_cli_resume_rejects_runtime_claim_conflict(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Claim conflict via CLI",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]
    compile_result = _invoke(tmp_path, "run", "compile", run_id)
    runtime_task_id = json.loads(compile_result.stdout)["runtime_task_id"]
    service = OrchestratorService(tmp_path / "workflow.db")
    service.runtime_claim_repo.create(
        RuntimeClaim(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
    )

    resume_result = _invoke(tmp_path, "run", "resume", run_id)

    assert resume_result.exit_code != 0
    assert json.loads(resume_result.stdout)["error"]["code"] == "runtime_claim_conflict"


def test_cli_reconcile_can_expire_stale_claim_and_list_history(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Expire stale claim via CLI",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]
    compile_result = _invoke(tmp_path, "run", "compile", run_id)
    runtime_task_id = json.loads(compile_result.stdout)["runtime_task_id"]
    service = OrchestratorService(tmp_path / "workflow.db")
    service.runtime_claim_repo.create(
        RuntimeClaim(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            lease_expires_at=datetime.now(UTC) - timedelta(minutes=5),
        )
    )

    inspect_result = _invoke(tmp_path, "run", "inspect", run_id)
    apply_result = _invoke(
        tmp_path,
        "run",
        "reconcile",
        run_id,
        "--apply",
        "--action",
        "expire_runtime_claim",
    )
    claims_result = _invoke(tmp_path, "run", "claims", run_id)

    assert inspect_result.exit_code == 0
    assert {problem["problem"] for problem in json.loads(inspect_result.stdout)["problems"]} >= {
        "runtime_claim_expired",
        "non_running_run_has_active_claim",
    }
    assert apply_result.exit_code == 0
    assert json.loads(apply_result.stdout)["action"] == "expire_runtime_claim"
    assert claims_result.exit_code == 0
    assert json.loads(claims_result.stdout)[0]["status"] == "expired"


def test_cli_reconcile_can_expire_stale_worker_lease(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Expire stale worker lease via CLI",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]
    compile_result = _invoke(tmp_path, "run", "compile", run_id)
    runtime_task_id = json.loads(compile_result.stdout)["runtime_task_id"]
    service = OrchestratorService(tmp_path / "workflow.db")
    service.worker_lease_repo.create(
        WorkerLease(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            adapter_name="shell",
            lease_expires_at=datetime.now(UTC) - timedelta(minutes=5),
        )
    )

    inspect_result = _invoke(tmp_path, "run", "inspect", run_id)
    apply_result = _invoke(
        tmp_path,
        "run",
        "reconcile",
        run_id,
        "--apply",
        "--action",
        "expire_worker_lease",
    )
    detail_result = _invoke(tmp_path, "run", "status-detail", run_id)

    assert inspect_result.exit_code == 0
    assert {problem["problem"] for problem in json.loads(inspect_result.stdout)["problems"]} >= {
        "worker_lease_expired",
        "non_running_run_has_active_worker_lease",
    }
    assert apply_result.exit_code == 0
    assert json.loads(apply_result.stdout)["action"] == "expire_worker_lease"
    assert detail_result.exit_code == 0
    assert json.loads(detail_result.stdout)["latest_worker_lease"]["status"] == "expired"


def test_cli_reconcile_can_create_repair_runtime_attempt(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Repair attempt via CLI",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]
    _invoke(tmp_path, "run", "compile", run_id)

    service = OrchestratorService(tmp_path / "workflow.db")
    current_attempt = service.runtime_attempt_repo.current_for_run(run_id)
    assert current_attempt is not None
    service.runtime_attempt_repo.close(
        current_attempt.attempt_id,
        status="interrupted",
        closed_at=datetime.now(UTC).isoformat(),
        close_reason="test_missing_current_attempt",
    )

    inspect_result = _invoke(tmp_path, "run", "inspect", run_id)
    assert inspect_result.exit_code == 0
    assert {problem["problem"] for problem in json.loads(inspect_result.stdout)["problems"]} >= {
        "missing_current_runtime_attempt"
    }

    apply_result = _invoke(
        tmp_path,
        "run",
        "reconcile",
        run_id,
        "--apply",
        "--action",
        "create_repair_runtime_attempt",
    )
    assert apply_result.exit_code == 0

    detail_result = _invoke(tmp_path, "run", "status-detail", run_id)
    assert detail_result.exit_code == 0
    assert json.loads(detail_result.stdout)["current_runtime_attempt"]["trigger"] == "repair"
