from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from apps.orchestrator_api.main import create_app
from packages.contracts import RunEventType, RuntimeClaim, RuntimeGateway, RuntimeGraphStep, RuntimeStateRef, WorkerLease
from packages.core_domain.db import unit_of_work
from packages.core_domain.db import migrate
from packages.core_domain.repositories import PresetRepository
from packages.core_domain.services import OrchestratorService
from packages.runtime_langgraph.gateway import OpenAIRuntimeGateway


class _FakeApiGatewayResponse:
    id = "resp_api"
    output_text = "Outcome: produce artifact Risk: command drift Check: review artifact file"


class _FakeApiResponses:
    def create(self, **kwargs):
        return _FakeApiGatewayResponse()


class _FakeApiClient:
    def __init__(self):
        self.responses = _FakeApiResponses()


def build_client(db_path: Path, runtime_gateway: RuntimeGateway | None = None) -> TestClient:
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    return TestClient(create_app(db_path, runtime_gateway=runtime_gateway))


def test_api_can_create_run_and_read_timeline(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post(
        "/runs",
        json={"goal": "Build the bootstrap artifact", "preset_id": "feature_delivery"},
    )
    assert create_response.status_code == 201
    run = create_response.json()

    get_response = client.get(f"/runs/{run['run_id']}")
    assert get_response.status_code == 200
    assert get_response.json()["run_id"] == run["run_id"]

    timeline_response = client.get(f"/runs/{run['run_id']}/timeline")
    assert timeline_response.status_code == 200
    timeline = timeline_response.json()
    assert [item["event_type"] for item in timeline] == [
        RunEventType.run_created,
        RunEventType.preset_selected,
    ]


def test_api_returns_structured_error_for_invalid_preset(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    response = client.post("/runs", json={"goal": "Build it", "preset_id": "missing"})
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "preset_not_found"


def test_api_lists_seeded_presets(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    response = client.get("/presets")
    assert response.status_code == 200
    assert {item["preset_id"] for item in response.json()} == {
        "feature_delivery",
        "research_spike",
        "advisory_delivery",
        "guarded_delivery",
    }


def test_api_lists_domain_packs_and_capability_routes(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    domain_pack_response = client.get("/domain-packs")
    capability_response = client.get("/capability-routes")

    assert domain_pack_response.status_code == 200
    assert [item["domain_pack_id"] for item in domain_pack_response.json()] == ["software_delivery_pack"]
    assert domain_pack_response.json()[0]["compile_projection"]["artifact_label"] == "software_delivery"
    assert domain_pack_response.json()[0]["runtime_projection"]["operator_label"] == "software-delivery"
    assert capability_response.status_code == 200
    assert capability_response.json() == [
        {"capability": "noop", "adapter_name": "noop", "adapter_class": "NoopAdapter"},
        {"capability": "shell_exec", "adapter_name": "shell", "adapter_class": "ShellAdapter"},
        {"capability": "shell_exec", "adapter_name": "opencode", "adapter_class": "OpenCodeAdapter"},
    ]


def test_api_lists_simulation_policies(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    response = client.get("/simulation/policies")

    assert response.status_code == 200
    assert [item["policy_id"] for item in response.json()] == [
        "advisory_failure_simulation",
        "delivery_consistency_simulation",
        "research_no_simulation",
    ]


def test_api_can_preview_and_validate_domain_pack_catalog(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    preview_response = client.get("/domain-packs/resolve", params={"preset_id": "feature_delivery", "task_kind": "shell_exec"})
    validate_response = client.get("/domain-packs/validate")

    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["resolved"] is True
    assert preview_payload["domain_pack"]["domain_pack_id"] == "software_delivery_pack"
    assert preview_payload["capability_resolution"]["adapter_name"] == "shell"

    assert validate_response.status_code == 200
    validate_payload = validate_response.json()
    assert validate_payload["passed"] is True
    assert validate_payload["issue_count"] == 0


def test_api_exposes_memory_namespace_and_run_memory_candidates(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    namespaces_response = client.get("/memory/namespaces")
    run = client.post("/runs", json={"goal": "Memory API candidate", "preset_id": "feature_delivery"}).json()
    client.post(f"/runs/{run['run_id']}/compile")
    client.post(f"/runs/{run['run_id']}/resume")
    candidates_response = client.get(f"/runs/{run['run_id']}/memory-candidates")

    assert namespaces_response.status_code == 200
    assert [item["namespace_id"] for item in namespaces_response.json()] == ["repo", "failure", "policy", "release"]
    assert candidates_response.status_code == 200
    assert {item["namespace_id"] for item in candidates_response.json()} == {"repo", "policy", "release"}

    selected_candidate = next(item for item in candidates_response.json() if item["namespace_id"] == "policy")
    materialize_response = client.post(
        f"/runs/{run['run_id']}/memory-items",
        json={"candidate_id": selected_candidate["candidate_id"]},
    )
    run_items_response = client.get(f"/runs/{run['run_id']}/memory-items")
    namespace_items_response = client.get("/memory/items", params={"namespace_id": "policy"})
    retrieval_preview_response = client.get(
        "/memory/retrieval-preview",
        params={"preset_id": "feature_delivery", "namespace_id": "policy"},
    )

    assert materialize_response.status_code == 201
    assert materialize_response.json()["namespace_id"] == "policy"
    assert run_items_response.status_code == 200
    assert [item["namespace_id"] for item in run_items_response.json()] == ["policy"]
    assert namespace_items_response.status_code == 200
    assert [item["run_id"] for item in namespace_items_response.json()] == [run["run_id"]]
    assert retrieval_preview_response.status_code == 200
    assert retrieval_preview_response.json()["selected_memory_item_ids"] == [materialize_response.json()["memory_item_id"]]


def test_api_compile_supports_explicit_memory_item_selection(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    source_run = client.post("/runs", json={"goal": "Source memory", "preset_id": "feature_delivery"}).json()
    client.post(f"/runs/{source_run['run_id']}/compile")
    client.post(f"/runs/{source_run['run_id']}/resume")
    source_candidates = client.get(f"/runs/{source_run['run_id']}/memory-candidates").json()
    policy_candidate = next(item for item in source_candidates if item["namespace_id"] == "policy")
    materialized_item = client.post(
        f"/runs/{source_run['run_id']}/memory-items",
        json={"candidate_id": policy_candidate["candidate_id"]},
    ).json()

    target_run = client.post("/runs", json={"goal": "Target memory-aware compile", "preset_id": "feature_delivery"}).json()
    compile_response = client.post(
        f"/runs/{target_run['run_id']}/compile",
        json={"memory_item_ids": [materialized_item["memory_item_id"]]},
    )
    detail_response = client.get(f"/runs/{target_run['run_id']}/status-detail")

    assert compile_response.status_code == 200
    assert compile_response.json()["memory_preview"]["selected_memory_item_ids"] == [materialized_item["memory_item_id"]]
    assert detail_response.status_code == 200
    assert detail_response.json()["memory_retrieval_preview"]["selected_memory_item_ids"] == [
        materialized_item["memory_item_id"]
    ]


def test_api_exposes_run_simulation_report(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    run = client.post("/runs", json={"goal": "Simulation API path", "preset_id": "feature_delivery"}).json()
    client.post(f"/runs/{run['run_id']}/compile")
    client.post(f"/runs/{run['run_id']}/resume")

    simulation_response = client.get(f"/runs/{run['run_id']}/simulation")
    summary_response = client.get(f"/runs/{run['run_id']}/summary")
    audit_response = client.get(f"/runs/{run['run_id']}/audit-report")

    assert simulation_response.status_code == 200
    assert simulation_response.json()["policy_id"] == "delivery_consistency_simulation"
    assert simulation_response.json()["status"] == "passed"
    assert summary_response.status_code == 200
    assert summary_response.json()["simulation_summary"]["status"] == "passed"
    assert audit_response.status_code == 200
    assert audit_response.json()["simulation_report"]["status"] == "passed"


def test_api_can_record_and_list_simulation_records(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    run = client.post("/runs", json={"goal": "Simulation API record path", "preset_id": "feature_delivery"}).json()
    client.post(f"/runs/{run['run_id']}/compile")
    client.post(f"/runs/{run['run_id']}/resume")

    record_response = client.post(f"/runs/{run['run_id']}/simulation-records")
    list_response = client.get(f"/runs/{run['run_id']}/simulation-records")
    detail_response = client.get(f"/runs/{run['run_id']}/status-detail")
    audit_response = client.get(f"/runs/{run['run_id']}/audit-report")

    assert record_response.status_code == 201
    assert record_response.json()["policy_id"] == "delivery_consistency_simulation"
    assert record_response.json()["recorded_from"] == "manual_request"
    assert list_response.status_code == 200
    assert [item["recorded_from"] for item in list_response.json()] == [
        "lifecycle_terminal",
        "manual_request",
    ]
    assert detail_response.status_code == 200
    assert detail_response.json()["latest_simulation_record"]["record_id"] == record_response.json()["record_id"]
    assert audit_response.status_code == 200
    assert audit_response.json()["latest_simulation_record"]["record_id"] == record_response.json()["record_id"]


def test_api_exposes_governance_tech_debt_report(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    response = client.get("/governance/tech-debt")
    assert response.status_code == 200
    payload = response.json()
    assert payload["open_debt_count"] >= 1
    assert "TD-010" in [item["debt_id"] for item in payload["open_items"]]
    assert payload["planned_phase_counts"]["M3"] >= 1


def test_api_exposes_governance_review_policy_report(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    response = client.get("/governance/review-policy")
    assert response.status_code == 200
    payload = response.json()
    assert payload["supported_policy_count"] == 4
    assert [item["policy"] for item in payload["supported_policies"]] == [
        "auto_only",
        "recommended",
        "human_required",
        "mandatory",
    ]
    assert payload["expansion_readiness"]["reference_only_candidates"] == ["optional"]
    assert "TD-006" == payload["debt_linkage"]["debt_id"]


def test_api_exposes_governance_release_readiness_report(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)
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

    response = client.get("/governance/release-readiness", params={"validation_report_path": str(validation_report_path)})
    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_ready"] is True
    assert payload["validation_summary"]["overall_passed"] is True
    assert [item["domain_pack_id"] for item in payload["domain_packs"]] == ["software_delivery_pack"]
    assert "platformized domain pack" in payload["gates"][3]["detail"]


def test_api_exposes_governance_domain_pack_platform_report(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    response = client.get("/governance/domain-packs")
    assert response.status_code == 200
    payload = response.json()
    assert payload["platformized_pack_count"] == 1
    assert payload["overall_platformized"] is True
    assert payload["pack_summaries"][0]["domain_pack_id"] == "software_delivery_pack"


def test_prepare_run_is_internal_and_persists_compile_bundle(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Compile me", "feature_delivery")
    bundle = service.prepare_run(run.run_id)

    assert bundle.run.status == "prepared"
    assert bundle.task_packet.expected_artifacts
    timeline = service.get_timeline(run.run_id)
    assert [event.event_type for event in timeline][-4:] == [
        RunEventType.runtime_task_created,
        RunEventType.domain_pack_selected,
        RunEventType.run_compiled,
        RunEventType.run_snapshot_created,
    ]


def test_api_compile_and_status_detail_are_public_in_m1(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Compile via API", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]

    compile_response = client.post(f"/runs/{run_id}/compile")
    assert compile_response.status_code == 200
    compile_payload = compile_response.json()
    assert compile_payload["run"]["status"] == "prepared"
    assert compile_payload["domain_pack_id"] == "software_delivery_pack"
    assert compile_payload["capability_adapter"] == "shell"

    status_detail = client.get(f"/runs/{run_id}/status-detail")
    assert status_detail.status_code == 200
    detail_payload = status_detail.json()
    assert detail_payload["run"]["status"] == "prepared"
    assert detail_payload["next_action"] == "resume"
    assert detail_payload["waiting_reason"] == "awaiting_runtime_resume"
    assert detail_payload["failure_reason"] is None
    assert detail_payload["last_runtime_state"]["graph_step"] == "compiled"
    assert detail_payload["last_review_verdict"] is None
    assert detail_payload["domain_pack"]["domain_pack_id"] == "software_delivery_pack"
    assert detail_payload["domain_pack"]["compile_projection"]["artifact_label"] == "software_delivery"
    assert detail_payload["capability_resolution"]["adapter_name"] == "shell"
    assert detail_payload["recoverability_hint"] == "resume_run"
    assert detail_payload["handoffs"]
    assert detail_payload["runtime_state_refs"]

    inspection_response = client.get(f"/runs/{run_id}/inspection")
    assert inspection_response.status_code == 200
    inspection_payload = inspection_response.json()
    assert inspection_payload["passed"] is True
    assert inspection_payload["problem_count"] == 0
    assert inspection_payload["recommended_action"] == "none"

    handoffs_response = client.get(f"/runs/{run_id}/handoffs")
    assert handoffs_response.status_code == 200
    assert len(handoffs_response.json()) == 1


def test_api_compile_can_pin_opencode_adapter(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Compile via opencode adapter", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]

    compile_response = client.post(f"/runs/{run_id}/compile", json={"adapter_name": "opencode"})
    assert compile_response.status_code == 200
    compile_payload = compile_response.json()
    assert compile_payload["capability_adapter"] == "opencode"

    detail_response = client.get(f"/runs/{run_id}/status-detail")
    assert detail_response.status_code == 200
    assert detail_response.json()["capability_resolution"]["adapter_name"] == "opencode"


def test_api_compile_rejects_unknown_adapter(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Compile via missing adapter", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]

    compile_response = client.post(f"/runs/{run_id}/compile", json={"adapter_name": "missing_adapter"})
    assert compile_response.status_code == 422
    error = compile_response.json()["error"]
    assert error["code"] == "capability_adapter_not_found"
    assert error["details"]["available_adapters"] == ["shell", "opencode"]


def test_api_status_detail_projects_runtime_gateway_brief_when_openai_gateway_is_active(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(
        db_path,
        runtime_gateway=OpenAIRuntimeGateway(client=_FakeApiClient(), model="gpt-5.4-mini"),
    )

    create_response = client.post("/runs", json={"goal": "Compile via live gateway", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")
    client.post(f"/runs/{run_id}/resume")

    status_detail = client.get(f"/runs/{run_id}/status-detail")
    assert status_detail.status_code == 200
    payload = status_detail.json()
    assert payload["runtime_gateway"]["provider"] == "openai"
    assert payload["last_runtime_state"]["state_payload"]["runtime_brief"].startswith("Outcome:")


def test_api_summary_projects_success_and_pending_states(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    auto_run = client.post("/runs", json={"goal": "Summary auto via API", "preset_id": "feature_delivery"}).json()
    auto_run_id = auto_run["run_id"]
    client.post(f"/runs/{auto_run_id}/compile")
    client.post(f"/runs/{auto_run_id}/resume")
    auto_summary = client.get(f"/runs/{auto_run_id}/summary")

    human_run = client.post("/runs", json={"goal": "Summary human via API", "preset_id": "research_spike"}).json()
    human_run_id = human_run["run_id"]
    client.post(f"/runs/{human_run_id}/compile")
    client.post(f"/runs/{human_run_id}/resume")
    human_summary = client.get(f"/runs/{human_run_id}/summary")

    assert auto_summary.status_code == 200
    assert human_summary.status_code == 200
    assert auto_summary.json()["failure_taxonomy"]["category"] == "success"
    assert auto_summary.json()["timeline_summary"]["terminal_event_type"] == "run_completed"
    assert auto_summary.json()["closure_summary"]["state"] == "closed"
    assert auto_summary.json()["review_summary"]["review_submitted_count"] == 1
    assert human_summary.json()["failure_taxonomy"]["category"] == "review_pending"
    assert human_summary.json()["review_summary"]["effective_review_state"] == "human_pending"
    assert human_summary.json()["review_summary"]["review_requested_count"] == 1
    assert human_summary.json()["closure_summary"]["state"] == "awaiting_review"


def test_api_event_inspection_projects_closed_and_review_wait_states(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    auto_run = client.post("/runs", json={"goal": "Event inspection auto via API", "preset_id": "feature_delivery"}).json()
    auto_run_id = auto_run["run_id"]
    client.post(f"/runs/{auto_run_id}/compile")
    client.post(f"/runs/{auto_run_id}/resume")
    auto_event_inspection = client.get(f"/runs/{auto_run_id}/event-inspection")

    human_run = client.post(
        "/runs",
        json={"goal": "Event inspection human via API", "preset_id": "research_spike"},
    ).json()
    human_run_id = human_run["run_id"]
    client.post(f"/runs/{human_run_id}/compile")
    client.post(f"/runs/{human_run_id}/resume")
    human_event_inspection = client.get(f"/runs/{human_run_id}/event-inspection")

    assert auto_event_inspection.status_code == 200
    assert human_event_inspection.status_code == 200
    assert auto_event_inspection.json()["closure_audit"]["state"] == "closed"
    assert auto_event_inspection.json()["closure_audit"]["passed"] is True
    assert auto_event_inspection.json()["event_digest"]["terminal_event_type"] == "run_completed"
    assert human_event_inspection.json()["closure_audit"]["state"] == "awaiting_review"
    assert human_event_inspection.json()["review_digest"]["review_requested_count"] == 1
    assert human_event_inspection.json()["review_digest"]["pending_human_review"] is True


def test_api_audit_report_projects_closed_and_review_wait_states(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    auto_run = client.post("/runs", json={"goal": "Audit report auto via API", "preset_id": "feature_delivery"}).json()
    auto_run_id = auto_run["run_id"]
    client.post(f"/runs/{auto_run_id}/compile")
    client.post(f"/runs/{auto_run_id}/resume")
    auto_report = client.get(f"/runs/{auto_run_id}/audit-report")

    human_run = client.post("/runs", json={"goal": "Audit report human via API", "preset_id": "research_spike"}).json()
    human_run_id = human_run["run_id"]
    client.post(f"/runs/{human_run_id}/compile")
    client.post(f"/runs/{human_run_id}/resume")
    human_report = client.get(f"/runs/{human_run_id}/audit-report")

    assert auto_report.status_code == 200
    assert human_report.status_code == 200
    assert auto_report.json()["review_packet"]["closure_summary"]["state"] == "closed"
    assert auto_report.json()["summary"]["failure_taxonomy"]["category"] == "success"
    assert human_report.json()["review_packet"]["closure_summary"]["state"] == "awaiting_review"
    assert human_report.json()["review_packet"]["effective_review_state"] == "human_pending"


def test_api_compile_accepts_noop_task_kind_for_research_spike(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Noop research via API", "preset_id": "research_spike"})
    run_id = create_response.json()["run_id"]

    compile_response = client.post(f"/runs/{run_id}/compile", json={"task_kind": "noop"})
    assert compile_response.status_code == 200
    assert compile_response.json()["run"]["status"] == "prepared"

    detail = client.get(f"/runs/{run_id}/status-detail").json()
    assert detail["runtime_tasks"][0]["task_kind"] == "noop"

    resume_response = client.post(f"/runs/{run_id}/resume")
    assert resume_response.status_code == 200
    assert resume_response.json()["run"]["status"] == "awaiting_review"

    service = OrchestratorService(db_path)
    runtime_task_id = detail["runtime_tasks"][0]["runtime_task_id"]
    evidence = service.get_task_evidence(runtime_task_id)
    assert evidence.raw_execution["adapter_name"] == "noop"
    assert evidence.artifact_refs


def test_api_rejects_task_kind_outside_preset_allow_list(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Noop feature via API", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]

    compile_response = client.post(f"/runs/{run_id}/compile", json={"task_kind": "noop"})
    assert compile_response.status_code == 409
    body = compile_response.json()
    assert body["error"]["code"] == "task_kind_not_allowed"
    assert body["error"]["details"]["allowed_task_kinds"] == ["shell_exec"]


def test_api_rejects_unknown_task_kind(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Unknown kind via API", "preset_id": "research_spike"})
    run_id = create_response.json()["run_id"]

    compile_response = client.post(f"/runs/{run_id}/compile", json={"task_kind": "unknown_kind"})
    assert compile_response.status_code == 422
    body = compile_response.json()
    assert body["error"]["code"] == "unsupported_task_kind"
    assert set(body["error"]["details"]["available_task_kinds"]) == {"shell_exec", "noop"}


def test_api_recompile_requires_prepared_run(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Recompile via API", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]

    invalid_recompile = client.post(f"/runs/{run_id}/recompile")
    assert invalid_recompile.status_code == 409

    compile_response = client.post(f"/runs/{run_id}/compile")
    assert compile_response.status_code == 200

    recompile_response = client.post(f"/runs/{run_id}/recompile")
    assert recompile_response.status_code == 200
    assert recompile_response.json()["run"]["status"] == "prepared"


def test_api_resume_runs_prepared_execution_path(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Resume via API", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")

    resume_response = client.post(f"/runs/{run_id}/resume")
    assert resume_response.status_code == 200
    assert resume_response.json()["run"]["status"] == "completed"

    timeline = client.get(f"/runs/{run_id}/timeline").json()
    assert "runtime_resumed" in [item["event_type"] for item in timeline]


def test_api_human_review_path_requires_approval(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Research via API", "preset_id": "research_spike"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")

    resume_response = client.post(f"/runs/{run_id}/resume")
    assert resume_response.status_code == 200
    assert resume_response.json()["run"]["status"] == "awaiting_review"
    assert resume_response.json()["review_decision"] is None

    detail_response = client.get(f"/runs/{run_id}/status-detail")
    assert detail_response.status_code == 200
    assert detail_response.json()["effective_review_state"] == "human_pending"
    assert detail_response.json()["latest_review_verdict"] is None

    approve_response = client.post(f"/runs/{run_id}/approve")
    assert approve_response.status_code == 200
    assert approve_response.json()["run"]["status"] == "completed"

    approved_detail = client.get(f"/runs/{run_id}/status-detail")
    assert approved_detail.status_code == 200
    assert approved_detail.json()["effective_review_state"] == "human_approved"
    assert approved_detail.json()["latest_review_verdict"]["reviewer_type"] == "human"


def test_api_recommended_review_escalates_after_auto_fail(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Advisory fail via API", "preset_id": "advisory_delivery"})
    run_id = create_response.json()["run_id"]
    compile_response = client.post(f"/runs/{run_id}/compile")
    runtime_task_id = compile_response.json()["runtime_task_id"]
    with unit_of_work(db_path) as connection:
        connection.execute(
            "UPDATE task_packets SET command_json = ? WHERE runtime_task_id = ?",
            (json.dumps(["python", "-c", "import sys; sys.exit(2)"]), runtime_task_id),
        )

    resume_response = client.post(f"/runs/{run_id}/resume")
    assert resume_response.status_code == 200
    assert resume_response.json()["run"]["status"] == "awaiting_review"
    assert resume_response.json()["review_decision"] == "fail"

    detail_response = client.get(f"/runs/{run_id}/status-detail")
    assert detail_response.status_code == 200
    assert detail_response.json()["review_policy"] == "recommended"
    assert detail_response.json()["effective_review_state"] == "human_pending"
    assert detail_response.json()["latest_review_verdict"]["reviewer_type"] == "auto"
    assert detail_response.json()["latest_review_verdict"]["decision"] == "fail"


def test_api_mandatory_review_waits_even_after_auto_pass(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Guarded via API", "preset_id": "guarded_delivery"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")

    resume_response = client.post(f"/runs/{run_id}/resume")
    assert resume_response.status_code == 200
    assert resume_response.json()["run"]["status"] == "awaiting_review"
    assert resume_response.json()["review_decision"] == "pass"

    detail_response = client.get(f"/runs/{run_id}/status-detail")
    assert detail_response.status_code == 200
    assert detail_response.json()["review_policy"] == "mandatory"
    assert detail_response.json()["effective_review_state"] == "human_pending"
    assert detail_response.json()["latest_review_verdict"]["reviewer_type"] == "auto"
    assert detail_response.json()["latest_review_verdict"]["decision"] == "pass"
    assert detail_response.json()["latest_simulation_record"]["recorded_from"] == "lifecycle_awaiting_review"

    records_response = client.get(f"/runs/{run_id}/simulation-records")
    assert records_response.status_code == 200
    assert [item["recorded_from"] for item in records_response.json()] == ["lifecycle_awaiting_review"]

    approve_response = client.post(f"/runs/{run_id}/approve")
    assert approve_response.status_code == 200

    post_approve_records = client.get(f"/runs/{run_id}/simulation-records")
    assert post_approve_records.status_code == 200
    assert [item["recorded_from"] for item in post_approve_records.json()] == [
        "lifecycle_awaiting_review",
        "lifecycle_terminal",
    ]


def test_api_human_review_reject_fails_run(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Research reject via API", "preset_id": "research_spike"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")
    client.post(f"/runs/{run_id}/resume")

    reject_response = client.post(f"/runs/{run_id}/reject")
    assert reject_response.status_code == 200
    assert reject_response.json()["run"]["status"] == "failed"

    detail_response = client.get(f"/runs/{run_id}/status-detail")
    assert detail_response.status_code == 200
    assert detail_response.json()["effective_review_state"] == "human_rejected"
    assert detail_response.json()["latest_review_verdict"]["decision"] == "fail"
    assert detail_response.json()["failure_reason"] == "human_review_rejected"
    assert detail_response.json()["recoverability_hint"] == "inspect_evidence_then_recompile"


def test_api_reconcile_can_apply_completed_runtime_state_alignment(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Repair via API", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")
    client.post(f"/runs/{run_id}/resume")

    service = OrchestratorService(db_path)
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

    plan_response = client.post(f"/runs/{run_id}/reconcile")
    assert plan_response.status_code == 200
    assert plan_response.json()["problems"][0]["repair_action"] == "align_completed_runtime_state"

    apply_response = client.post(f"/runs/{run_id}/reconcile", json={"apply": True})
    assert apply_response.status_code == 200
    assert apply_response.json()["action"] == "align_completed_runtime_state"

    inspection_response = client.get(f"/runs/{run_id}/inspection")
    assert inspection_response.status_code == 200
    assert inspection_response.json()["passed"] is True


def test_api_reconcile_rejects_manual_only_problem(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Manual only repair via API", "preset_id": "research_spike"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")
    client.post(f"/runs/{run_id}/resume")
    with unit_of_work(db_path) as connection:
        connection.execute("DELETE FROM evidence WHERE run_id = ?", (run_id,))

    apply_response = client.post(f"/runs/{run_id}/reconcile", json={"apply": True})
    assert apply_response.status_code == 409
    assert apply_response.json()["error"]["code"] == "repair_action_not_available"


def test_api_exposes_claim_history_and_status_projection(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Claim projection via API", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")
    client.post(f"/runs/{run_id}/resume")

    detail_response = client.get(f"/runs/{run_id}/status-detail")
    claims_response = client.get(f"/runs/{run_id}/claims")

    assert detail_response.status_code == 200
    assert claims_response.status_code == 200
    detail_payload = detail_response.json()
    claims_payload = claims_response.json()
    assert detail_payload["active_claims"] == []
    assert detail_payload["latest_claim"]["status"] == "released"
    assert claims_payload[0]["release_reason"] == "run_terminal"


def test_api_exposes_worker_lease_projection_via_status_and_inspection(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Worker lease projection via API", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")
    client.post(f"/runs/{run_id}/resume")

    detail_response = client.get(f"/runs/{run_id}/status-detail")
    inspection_response = client.get(f"/runs/{run_id}/inspection")

    assert detail_response.status_code == 200
    assert inspection_response.status_code == 200
    detail_payload = detail_response.json()
    inspection_payload = inspection_response.json()
    assert detail_payload["active_worker_leases"] == []
    assert detail_payload["latest_worker_lease"]["status"] == "released"
    assert detail_payload["worker_lease_projection"]["latest_adapter_name"] == "shell"
    assert inspection_payload["latest_worker_lease"]["status"] == "released"
    assert inspection_payload["worker_lease_projection"]["active_lease_count"] == 0


def test_api_exposes_runtime_attempt_projection_via_status_and_inspection(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Attempt projection via API", "preset_id": "research_spike"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")
    client.post(f"/runs/{run_id}/resume")

    detail_payload = client.get(f"/runs/{run_id}/status-detail").json()
    inspection_payload = client.get(f"/runs/{run_id}/inspection").json()

    assert detail_payload["current_runtime_attempt"]["trigger"] == "resume"
    assert detail_payload["runtime_attempt_projection"]["attempt_count"] == 2
    assert len(detail_payload["runtime_attempt_projection"]["superseded_attempt_ids"]) == 1
    assert inspection_payload["current_runtime_attempt"]["status"] == "current"
    assert inspection_payload["runtime_attempt_projection"]["current_trigger"] == "resume"


def test_api_exposes_worker_lease_history_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Worker lease history via API", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")
    client.post(f"/runs/{run_id}/resume")

    leases_response = client.get(f"/runs/{run_id}/leases")

    assert leases_response.status_code == 200
    payload = leases_response.json()
    assert len(payload) == 1
    assert payload[0]["status"] == "released"
    assert payload[0]["adapter_name"] == "shell"


def test_api_exposes_runtime_attempt_history_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Attempt history via API", "preset_id": "research_spike"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")
    client.post(f"/runs/{run_id}/resume")

    attempts_response = client.get(f"/runs/{run_id}/attempts")

    assert attempts_response.status_code == 200
    payload = attempts_response.json()
    assert [item["trigger"] for item in payload] == ["compile", "resume"]
    assert payload[0]["status"] == "superseded"
    assert payload[1]["status"] == "current"


def test_api_status_and_inspection_project_latest_snapshot(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Snapshot projection via API", "preset_id": "research_spike"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")

    prepared_detail = client.get(f"/runs/{run_id}/status-detail").json()
    assert prepared_detail["latest_snapshot"]["stage"] == "compiled"
    assert prepared_detail["snapshot_count"] == 1

    client.post(f"/runs/{run_id}/resume")
    inspection_payload = client.get(f"/runs/{run_id}/inspection").json()
    assert inspection_payload["latest_snapshot"]["stage"] == "awaiting_review"


def test_api_exposes_snapshot_history_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Snapshot history via API", "preset_id": "research_spike"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")
    client.post(f"/runs/{run_id}/resume")
    client.post(f"/runs/{run_id}/approve")

    snapshots_response = client.get(f"/runs/{run_id}/snapshots")

    assert snapshots_response.status_code == 200
    assert [item["stage"] for item in snapshots_response.json()] == ["compiled", "awaiting_review", "completed"]


def test_api_status_detail_projects_budget_ledger(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Budget projection via API", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")
    client.post(f"/runs/{run_id}/resume")

    detail_response = client.get(f"/runs/{run_id}/status-detail")

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["budget_ledger"] is not None
    assert detail_payload["budget_projection"]["execution_count"] == 1
    assert detail_payload["budget_projection"]["last_return_code"] == 0


def test_api_recompile_rejects_when_retry_budget_is_exhausted(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Budget exhausted via API", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")
    first_recompile = client.post(f"/runs/{run_id}/recompile")
    assert first_recompile.status_code == 200

    second_recompile = client.post(f"/runs/{run_id}/recompile")

    assert second_recompile.status_code == 409
    assert second_recompile.json()["error"]["code"] == "budget_exhausted"


def test_api_exposes_budget_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Budget endpoint via API", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")

    budget_response = client.get(f"/runs/{run_id}/budget")

    assert budget_response.status_code == 200
    payload = budget_response.json()
    assert payload["budget_ledger"] is not None
    assert payload["budget_projection"]["remaining_retries"] == 1


def test_api_resume_rejects_runtime_claim_conflict(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Claim conflict via API", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]
    compile_response = client.post(f"/runs/{run_id}/compile")
    runtime_task_id = compile_response.json()["runtime_task_id"]
    service = OrchestratorService(db_path)
    service.runtime_claim_repo.create(
        RuntimeClaim(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
    )

    resume_response = client.post(f"/runs/{run_id}/resume")

    assert resume_response.status_code == 409
    assert resume_response.json()["error"]["code"] == "runtime_claim_conflict"


def test_api_reconcile_can_expire_stale_claim(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Expire stale claim via API", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]
    compile_response = client.post(f"/runs/{run_id}/compile")
    runtime_task_id = compile_response.json()["runtime_task_id"]
    service = OrchestratorService(db_path)
    service.runtime_claim_repo.create(
        RuntimeClaim(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            lease_expires_at=datetime.now(UTC) - timedelta(minutes=5),
        )
    )

    inspection_response = client.get(f"/runs/{run_id}/inspection")
    apply_response = client.post(
        f"/runs/{run_id}/reconcile",
        json={"apply": True, "action": "expire_runtime_claim"},
    )
    claims_response = client.get(f"/runs/{run_id}/claims")

    assert inspection_response.status_code == 200
    assert {problem["problem"] for problem in inspection_response.json()["problems"]} >= {
        "runtime_claim_expired",
        "non_running_run_has_active_claim",
    }
    assert apply_response.status_code == 200
    assert apply_response.json()["action"] == "expire_runtime_claim"
    assert claims_response.status_code == 200
    assert claims_response.json()[0]["status"] == "expired"


def test_api_reconcile_can_expire_stale_worker_lease(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Expire stale worker lease via API", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]
    compile_response = client.post(f"/runs/{run_id}/compile")
    runtime_task_id = compile_response.json()["runtime_task_id"]
    service = OrchestratorService(db_path)
    service.worker_lease_repo.create(
        WorkerLease(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            adapter_name="shell",
            lease_expires_at=datetime.now(UTC) - timedelta(minutes=5),
        )
    )

    inspection_response = client.get(f"/runs/{run_id}/inspection")
    apply_response = client.post(
        f"/runs/{run_id}/reconcile",
        json={"apply": True, "action": "expire_worker_lease"},
    )
    detail_response = client.get(f"/runs/{run_id}/status-detail")

    assert inspection_response.status_code == 200
    assert {problem["problem"] for problem in inspection_response.json()["problems"]} >= {
        "worker_lease_expired",
        "non_running_run_has_active_worker_lease",
    }
    assert apply_response.status_code == 200
    assert apply_response.json()["action"] == "expire_worker_lease"
    assert detail_response.status_code == 200
    assert detail_response.json()["latest_worker_lease"]["status"] == "expired"


def test_api_reconcile_can_create_repair_runtime_attempt(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Repair attempt via API", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")

    service = OrchestratorService(db_path)
    current_attempt = service.runtime_attempt_repo.current_for_run(run_id)
    assert current_attempt is not None
    service.runtime_attempt_repo.close(
        current_attempt.attempt_id,
        status="interrupted",
        closed_at=datetime.now(UTC).isoformat(),
        close_reason="test_missing_current_attempt",
    )

    inspection_response = client.get(f"/runs/{run_id}/inspection")
    assert inspection_response.status_code == 200
    assert {problem["problem"] for problem in inspection_response.json()["problems"]} >= {"missing_current_runtime_attempt"}

    apply_response = client.post(
        f"/runs/{run_id}/reconcile",
        json={"apply": True, "action": "create_repair_runtime_attempt"},
    )
    assert apply_response.status_code == 200

    detail_response = client.get(f"/runs/{run_id}/status-detail")
    assert detail_response.status_code == 200
    assert detail_response.json()["current_runtime_attempt"]["trigger"] == "repair"


def test_api_blocks_resume_before_compile(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Resume too early", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]

    response = client.post(f"/runs/{run_id}/resume")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_state_transition"
    assert response.json()["error"]["details"]["allowed_statuses"] == ["prepared"]


def test_api_blocks_review_before_awaiting_review(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Review too early", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")

    approve_response = client.post(f"/runs/{run_id}/approve")
    assert approve_response.status_code == 409
    assert approve_response.json()["error"]["code"] == "invalid_state_transition"


def test_api_blocks_recompile_after_terminal_run(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Terminal recompile", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]
    client.post(f"/runs/{run_id}/compile")
    client.post(f"/runs/{run_id}/resume")

    recompile_response = client.post(f"/runs/{run_id}/recompile")
    assert recompile_response.status_code == 409
    assert recompile_response.json()["error"]["code"] == "invalid_state_transition"
