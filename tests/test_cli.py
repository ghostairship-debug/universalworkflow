from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import sqlite3
from pathlib import Path
import sys

import pytest
from typer.testing import CliRunner

from apps.operator_cli.main import app
from packages.contracts import RuntimeClaim, RuntimeGraphStep, RuntimeStateRef, WorkerLease
from packages.core_domain.db import unit_of_work
from packages.core_domain.services import OrchestratorService
from packages.worker_adapters.base import ExecutionResult, resolve_artifact_paths, utc_now
from packages.worker_adapters.codex_adapter import CodexAdapter
from packages.worker_adapters.langchain_agent_adapter import LangChainAgentAdapter
from packages.worker_adapters.opencode_adapter import OpenCodeAdapter


pytestmark = pytest.mark.slow

runner = CliRunner()
OPEN_DEBT_IDS: list[str] = [
    "M77-COCOS-001",
    "M84-GAME-QA-001",
    "M77-LANGCHAIN-001",
    "M67-CARRY-001",
]
BLOCKING_OPEN_DEBT_IDS: list[str] = []

AVAILABLE_SHELL_EXEC_ADAPTERS = [
    "shell",
    "codex",
    "claude_architect",
    "mmx_multimodal",
    "vertex_multimodal",
    "opencode",
]


def _invoke(tmp_path: Path, *args: str, env: dict[str, str] | None = None):
    return runner.invoke(app, ["--db-path", str(tmp_path / "workflow.db"), *args], env=env)


def _load_json_after_progress(output: str):
    json_start = output.rfind("\n{")
    return json.loads(output[json_start + 1 :] if json_start >= 0 else output)


def _fake_cli_patch_launch(self, packet):  # type: ignore[override]
    started_at = utc_now()
    artifact_path = Path(packet.expected_artifacts[0])
    if not artifact_path.is_absolute():
        artifact_path = Path(packet.working_directory) / artifact_path
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    patch_text = (
        "--- cli_target.txt\n"
        "+++ cli_target.txt\n"
        "@@ -1 +1 @@\n"
        "-before\n"
        "+after\n"
    )
    artifact_path.write_text(patch_text, encoding="utf-8")
    finished_at = utc_now()
    return ExecutionResult(
        runtime_task_id=packet.runtime_task_id,
        return_code=0,
        stdout=patch_text,
        stderr="",
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=max(int((finished_at - started_at).total_seconds() * 1000), 0),
        artifact_paths=[artifact_path.resolve().as_posix()],
        adapter_name=self.normalized_name(),
        metadata={"mutation_mode": "patch_apply"},
    )


def _fake_cli_external_launch(self, packet):  # type: ignore[override]
    started_at = utc_now()
    artifact_paths = resolve_artifact_paths(
        packet,
        create_missing=True,
        placeholder=f"# Fake external adapter\n\nadapter={self.normalized_name()}\n",
    )
    finished_at = utc_now()
    return ExecutionResult(
        runtime_task_id=packet.runtime_task_id,
        return_code=0,
        stdout=f"{self.normalized_name()} fake ok",
        stderr="",
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=max(int((finished_at - started_at).total_seconds() * 1000), 0),
        artifact_paths=artifact_paths,
        adapter_name=self.normalized_name(),
        metadata={"test_fake_external_adapter": True},
    )


def test_cli_db_reset_and_preset_list(tmp_path: Path) -> None:
    reset_result = _invoke(tmp_path, "db", "reset")
    assert reset_result.exit_code == 0
    payload = json.loads(reset_result.stdout)
    assert payload["seeded_presets"] == [
        "feature_delivery",
        "optional_delivery",
        "research_spike",
        "advisory_delivery",
        "guarded_delivery",
        "research_spike_reviewable",
        "project_delivery",
        "guarded_project_delivery",
    ]

    preset_result = _invoke(tmp_path, "preset", "list", "--json")
    assert preset_result.exit_code == 0
    presets = json.loads(preset_result.stdout)
    assert {preset["preset_id"] for preset in presets} == {
        "feature_delivery",
        "optional_delivery",
        "research_spike",
        "research_spike_reviewable",
        "advisory_delivery",
        "guarded_delivery",
        "project_delivery",
        "guarded_project_delivery",
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
        {"capability": "shell_exec", "adapter_name": "codex", "adapter_class": "CodexAdapter"},
        {"capability": "shell_exec", "adapter_name": "claude_architect", "adapter_class": "ClaudeArchitectAdapter"},
        {"capability": "shell_exec", "adapter_name": "mmx_multimodal", "adapter_class": "MMXMultimodalAdapter"},
        {"capability": "shell_exec", "adapter_name": "vertex_multimodal", "adapter_class": "VertexMultimodalAdapter"},
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


def test_cli_db_migrate_and_migration_status(tmp_path: Path) -> None:
    status_before = _invoke(tmp_path, "db", "migration-status")
    assert status_before.exit_code == 0
    before_payload = json.loads(status_before.stdout)
    assert before_payload["available_count"] >= 1
    assert before_payload["applied_count"] == 0
    assert before_payload["pending_count"] == before_payload["available_count"]
    assert before_payload["up_to_date"] is False

    migrate_result = _invoke(tmp_path, "db", "migrate")
    assert migrate_result.exit_code == 0
    migrate_payload = json.loads(migrate_result.stdout)
    assert migrate_payload["applied_count"] == migrate_payload["available_count"]
    assert migrate_payload["pending_count"] == 0
    assert migrate_payload["up_to_date"] is True

    status_after = _invoke(tmp_path, "db", "migration-status")
    assert status_after.exit_code == 0
    after_payload = json.loads(status_after.stdout)
    assert after_payload["applied_count"] == after_payload["available_count"]
    assert after_payload["pending_count"] == 0
    assert after_payload["up_to_date"] is True


def test_cli_can_preview_m8_capability_projection(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    env = {
        "UAWO_ENABLE_AGENT_LANE": "1",
        "UAWO_ENABLE_MCP_SOURCE": "1",
        "WORKFLOW_MCP_BROKER_PROFILE_IDS": "local_workspace_readonly",
    }

    sources_result = _invoke(tmp_path, "capability", "sources", env=env)
    profiles_result = _invoke(tmp_path, "capability", "mcp-profiles", env=env)
    projection_result = _invoke(
        tmp_path,
        "capability",
        "projection",
        "--preset",
        "research_spike_reviewable",
        env=env,
    )

    assert sources_result.exit_code == 0
    assert any(item["source_type"] == "built_in" for item in json.loads(sources_result.stdout))
    assert any(item["source_type"] == "mcp_stdio" for item in json.loads(sources_result.stdout))
    assert profiles_result.exit_code == 0
    assert json.loads(profiles_result.stdout)[0]["profile_id"] == "local_workspace_readonly"
    assert projection_result.exit_code == 0
    projection_payload = json.loads(projection_result.stdout)
    assert projection_payload["execution_lane"] == "standard_agent"
    assert projection_payload["capability_resolution"]["adapter_name"] == "agent"
    assert projection_payload["resolved_execution"]["adapter_name"] == "agent"
    assert projection_payload["execution_resolution_trace"]["source_map"]["adapter_name"]["scope"] == "preset"
    tools = projection_payload["tool_projection_manifest"]["tools"]
    assert "mcp_list_workspace_files" in [item["tool_name"] for item in tools]
    assert "mcp:local_workspace_readonly:mcp_list_workspace_files" in [
        item["canonical_tool_id"] for item in tools
    ]
    assert all(item["raw_tool_name"] for item in tools)
    assert all(item["display_name"] for item in tools)


def test_cli_interaction_profiles_clusters_and_session_flow(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")

    profiles_result = _invoke(tmp_path, "interaction", "profiles")
    clusters_result = _invoke(tmp_path, "interaction", "clusters")
    empty_sessions_result = _invoke(tmp_path, "interaction", "sessions")
    create_result = _invoke(
        tmp_path,
        "interaction",
        "create-session",
        "--goal",
        "Coordinate a multi-role project delivery slice",
        "--preset",
        "project_delivery",
        "--cluster",
        "dev_cluster",
        "--constraint",
        "keep operator checkpoints visible",
        "--assumption",
        "workspace is clean",
        "--artifact",
        "CURRENT_DEVELOPMENT_WORKFLOW.md",
        "--followup-context",
        "prior review asked for a launch checkpoint",
    )

    assert profiles_result.exit_code == 0
    assert clusters_result.exit_code == 0
    assert empty_sessions_result.exit_code == 0
    assert json.loads(empty_sessions_result.stdout) == []
    assert any(item["profile_id"] == "planner_architect" for item in json.loads(profiles_result.stdout)["profiles"])
    assert json.loads(profiles_result.stdout)["generated_profiles"] == []
    assert any(item["template_id"] == "dev_cluster" for item in json.loads(clusters_result.stdout))

    create_payload = json.loads(create_result.stdout)
    session_id = create_payload["session"]["session_id"]
    assert create_result.exit_code == 0
    assert create_payload["session"]["status"] == "ready_to_launch"
    assert create_payload["plan_draft"]["selected_cluster_template_ids"] == ["dev_cluster"]
    assert create_payload["goal_packet"]["selected_clusters"][0]["template_id"] == "dev_cluster"
    assert create_payload["session"]["intent_packet"]["constraints"] == ["keep operator checkpoints visible"]
    assert create_payload["session"]["intent_packet"]["assumptions"] == ["workspace is clean"]
    assert create_payload["session"]["intent_packet"]["referenced_artifact_paths"] == ["CURRENT_DEVELOPMENT_WORKFLOW.md"]
    assert create_payload["session"]["intent_packet"]["followup_context"] == ["prior review asked for a launch checkpoint"]
    assert create_payload["followup_requests"] == []
    assert create_payload["active_run_operator_view"] is None

    sessions_result = _invoke(tmp_path, "interaction", "sessions")
    get_result = _invoke(tmp_path, "interaction", "get-session", session_id)
    launch_result = _invoke(
        tmp_path,
        "interaction",
        "launch",
        session_id,
        "--preset",
        "project_delivery",
        "--cluster",
        "dev_cluster",
        "--rationale",
        "ready to launch",
    )

    assert get_result.exit_code == 0
    assert launch_result.exit_code == 0
    assert sessions_result.exit_code == 0
    get_payload = json.loads(get_result.stdout)
    launch_payload = json.loads(launch_result.stdout)
    sessions_payload = json.loads(sessions_result.stdout)
    assert get_payload["session"]["latest_plan_draft_id"] == create_payload["plan_draft"]["draft_id"]
    assert [item["session_id"] for item in sessions_payload] == [session_id]
    assert launch_payload["session"]["status"] == "launched"
    assert launch_payload["session"]["active_run_id"] == launch_payload["launch_payload"]["run"]["run_id"]
    assert launch_payload["launch_decision"]["selected_cluster_template_ids"] == ["dev_cluster"]
    assert launch_payload["launch_payload"]["selected_clusters"][0]["template_id"] == "dev_cluster"
    assert launch_payload["launch_payload"]["cluster_policy_preview"]["selected_cluster_template_ids"] == ["dev_cluster"]
    assert launch_payload["launch_payload"]["run"]["status"] == "prepared"
    assert launch_payload["active_run_operator_view"]["run"]["run_id"] == launch_payload["launch_payload"]["run"]["run_id"]
    assert any(item["trigger"] == "review_gate" for item in launch_payload["automation_watchdogs"])

    generate_profiles_result = _invoke(tmp_path, "interaction", "generate-profiles", session_id)
    generated_profiles_result = _invoke(
        tmp_path,
        "interaction",
        "generated-profiles",
        "--session-id",
        session_id,
    )

    assert generate_profiles_result.exit_code == 0
    assert generated_profiles_result.exit_code == 0
    generated_profiles_payload = json.loads(generated_profiles_result.stdout)
    assert len(generated_profiles_payload) >= 1
    assert any(item["cluster_template_id"] == "dev_cluster" for item in generated_profiles_payload)

    followup_result = _invoke(
        tmp_path,
        "interaction",
        "followup",
        session_id,
        "--instruction",
        "Prepare the approval checkpoint after the implementation run completes.",
        "--intent",
        "review_gate",
        "--blocking",
    )
    followups_result = _invoke(tmp_path, "interaction", "followups", session_id)
    watchdogs_result = _invoke(tmp_path, "interaction", "watchdogs", "--session-id", session_id)
    evaluate_watchdogs_result = _invoke(tmp_path, "interaction", "evaluate-watchdogs", "--session-id", session_id)

    assert followup_result.exit_code == 0
    assert followups_result.exit_code == 0
    assert watchdogs_result.exit_code == 0
    assert evaluate_watchdogs_result.exit_code == 0
    followup_payload = json.loads(followup_result.stdout)
    followups_payload = json.loads(followups_result.stdout)
    watchdogs_payload = json.loads(watchdogs_result.stdout)
    evaluation_payload = json.loads(evaluate_watchdogs_result.stdout)
    assert followup_payload["followup_request"]["intent"] == "review_gate"
    assert len(followup_payload["followup_requests"]) == 1
    assert followup_payload["active_run_operator_view"]["run"]["run_id"] == launch_payload["launch_payload"]["run"]["run_id"]
    assert {item["trigger"] for item in followup_payload["automation_watchdogs"]} >= {"review_gate", "followup_pending"}
    assert len(followups_payload) == 1
    assert followups_payload[0]["blocking"] is True
    assert {item["trigger"] for item in watchdogs_payload} >= {"review_gate", "followup_pending"}
    assert len(evaluation_payload["actions"]) >= 1


def test_cli_lists_capability_descriptors_and_health(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")

    descriptors_result = _invoke(tmp_path, "capability", "descriptors")
    health_result = _invoke(tmp_path, "capability", "health")

    assert descriptors_result.exit_code == 0
    descriptors_payload = json.loads(descriptors_result.stdout)
    assert any(item["provider_kind"] == "built_in" for item in descriptors_payload)
    assert any(item["provider_kind"] == "adapter_route" and item["adapter_name"] == "shell" for item in descriptors_payload)

    assert health_result.exit_code == 0
    health_payload = json.loads(health_result.stdout)
    assert any(item["descriptor"]["provider_kind"] == "runtime_gateway" for item in health_payload)
    assert all("recent_call_summary" in item for item in health_payload)
    assert all("runtime_probe_status" in item for item in health_payload)


def test_cli_exposes_plan_graph_and_launch_surfaces(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")

    plan_result = _invoke(
        tmp_path,
        "run",
        "plan-graph",
        "--goal",
        "Coordinate a multi-role delivery slice",
        "--preset",
        "project_delivery",
    )
    assert plan_result.exit_code == 0
    plan_payload = json.loads(plan_result.stdout)
    assert plan_payload["plan_graph"]["execution_mode"] == "planner_generated_graph_with_parallel_children"
    assert len(plan_payload["plan_graph"]["edges"]) >= 1
    assert len(plan_payload["plan_graph"]["barriers"]) == 1
    assert len(plan_payload["plan_graph"]["retry_policies"]) == 1

    policy_result = _invoke(
        tmp_path,
        "run",
        "policy-preview",
        "--goal",
        "Coordinate a multi-role delivery slice",
        "--preset",
        "project_delivery",
    )
    assert policy_result.exit_code == 0
    policy_payload = json.loads(policy_result.stdout)
    assert policy_payload["policy_preview"]["recommended_operator_mode"] == "human_visible"
    assert policy_payload["policy_preview"]["review_node_count"] == 1

    goal_packet_result = _invoke(
        tmp_path,
        "run",
        "goal-packet",
        "--goal",
        "Coordinate a multi-role delivery slice",
        "--preset",
        "project_delivery",
    )
    assert goal_packet_result.exit_code == 0
    goal_packet_payload = json.loads(goal_packet_result.stdout)
    assert goal_packet_payload["capability_policy_preview"]["recommended_operator_mode"] == "human_visible"
    assert len(goal_packet_payload["matched_capability_descriptors"]) >= 1

    launch_result = _invoke(
        tmp_path,
        "run",
        "launch",
        "--goal",
        "Coordinate a multi-role delivery slice",
        "--preset",
        "project_delivery",
    )
    assert launch_result.exit_code == 0
    launch_payload = json.loads(launch_result.stdout)
    assert launch_payload["selected_preset_id"] == "project_delivery"
    assert launch_payload["capability_policy_preview"]["recommended_operator_mode"] == "human_visible"

    plan_status_result = _invoke(tmp_path, "run", "plan-graph-status", launch_payload["run"]["run_id"])
    assert plan_status_result.exit_code == 0
    plan_status_payload = json.loads(plan_status_result.stdout)
    assert plan_status_payload["enabled"] is True
    assert len(plan_status_payload["plan_graph"]["nodes"]) == 4
    assert len(plan_status_payload["plan_graph"]["edges"]) >= 1
    assert plan_status_payload["plan_graph"]["cluster_template_ids"] == ["dev_cluster"]

    policy_status_result = _invoke(tmp_path, "run", "policy-preview-status", launch_payload["run"]["run_id"])
    assert policy_status_result.exit_code == 0
    policy_status_payload = json.loads(policy_status_result.stdout)
    assert policy_status_payload["enabled"] is True
    assert policy_status_payload["policy_preview"]["recommended_operator_mode"] == "human_visible"

    operator_packet_result = _invoke(tmp_path, "run", "operator-packet", launch_payload["run"]["run_id"])
    assert operator_packet_result.exit_code == 0
    operator_packet_payload = json.loads(operator_packet_result.stdout)
    assert operator_packet_payload["operator_projection"]["recommended_operator_mode"] == "human_visible"
    assert operator_packet_payload["capability_policy_preview"]["enabled"] is True
    assert operator_packet_payload["selected_clusters"][0]["template_id"] == "dev_cluster"
    assert operator_packet_payload["cluster_policy_preview"]["selected_cluster_template_ids"] == ["dev_cluster"]


def test_cli_run_langgraph_focus_writes_advisory_evidence(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "langgraph_evidence"

    result = _invoke(
        tmp_path,
        "run",
        "langgraph-focus",
        "--goal",
        "Compare workflow route with focused LangGraph runtime",
        "--preset",
        "project_delivery",
        "--evidence-dir",
        evidence_dir.as_posix(),
    )

    assert result.exit_code == 0
    payload = _load_json_after_progress(result.stdout)
    assert payload["comparison"]["passed"] is True
    assert payload["comparison"]["mutation_allowed"] is False
    assert payload["comparison"]["direct_mutation_disabled"] is True
    assert payload["comparison"]["workflow_latency_ms"] >= 0
    assert payload["workflow_route"]["selected_preset_id"] == "project_delivery"
    assert payload["langgraph_route"]["provider"] in {"langgraph", "linear"}
    assert payload["langgraph_route"]["path"] == ["planning", "review", "evidence"]
    evidence_path = Path(payload["evidence"]["evidence_path"])
    assert evidence_path.exists()
    assert evidence_path.parent == evidence_dir.resolve()


def test_cli_config_show_reads_workflow_toml_and_worker_pools(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "workflow.toml").write_text(
        """
[feature_flags]
external_worker_pools = true

[worker_pools]
default_pool_id = "mock_remote_shell"
""".strip(),
        encoding="utf-8",
    )
    _invoke(tmp_path, "db", "reset")

    config_result = _invoke(tmp_path, "config", "show")
    worker_pool_result = _invoke(tmp_path, "capability", "worker-pools")

    assert config_result.exit_code == 0
    config_payload = json.loads(config_result.stdout)
    assert config_payload["config_path"].endswith("workflow.toml")
    assert config_payload["feature_flags"]["external_worker_pools"]["enabled"] is True
    assert config_payload["worker_pools"]["default_pool_id"] == "mock_remote_shell"
    assert config_payload["execution_defaults"]["worker_pool_id"]["value"] == "mock_remote_shell"
    assert config_payload["execution_defaults"]["worker_pool_id"]["source"] == "toml:worker_pools.default_pool_id"

    assert worker_pool_result.exit_code == 0
    worker_pools = json.loads(worker_pool_result.stdout)
    assert {item["worker_pool_id"] for item in worker_pools} >= {"local_loopback", "mock_remote_shell"}
    assert any(
        item["default_selected"] is True for item in worker_pools if item["worker_pool_id"] == "mock_remote_shell"
    )


def test_cli_can_export_domain_pack_skill_when_flag_enabled(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    output_root = tmp_path / "skills"
    result = _invoke(
        tmp_path,
        "domain-pack",
        "export-skill",
        "--domain-pack-id",
        "software_delivery_pack",
        "--output-root",
        str(output_root),
        env={"UAWO_ENABLE_SKILL_EXPORT": "1"},
    )

    assert result.exit_code == 0
    payload = _load_json_after_progress(result.stdout)
    bundle_path = Path(payload["bundle_path"])
    assert payload["domain_pack_id"] == "software_delivery_pack"
    assert (bundle_path / "README.md").exists()
    assert (bundle_path / "skill.json").exists()


def test_cli_governance_tech_debt_report(tmp_path: Path) -> None:
    result = _invoke(tmp_path, "governance", "tech-debt")
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["source_contract"] == "structured_json"
    assert payload["open_debt_count"] == len(OPEN_DEBT_IDS)
    assert payload["blocking_open_count"] == len(BLOCKING_OPEN_DEBT_IDS)
    assert payload["carry_forward_count"] == 1
    assert payload["status_counts"] == {"partially_repaid": 2, "open": 1, "carry_forward": 1}
    assert [item["debt_id"] for item in payload["open_items"]] == OPEN_DEBT_IDS
    assert [item["debt_id"] for item in payload["blocking_open_items"]] == BLOCKING_OPEN_DEBT_IDS
    assert payload["source_path"].endswith("docs/governance/tech_debt_registry.json")
    assert payload["source_paths"]["canonical"].endswith("docs/governance/tech_debt_registry.json")


def test_cli_governance_review_policy_report(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    result = _invoke(tmp_path, "governance", "review-policy")
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["supported_policy_count"] == 5
    assert [item["policy"] for item in payload["supported_policies"]] == [
        "auto_only",
        "optional",
        "recommended",
        "human_required",
        "mandatory",
    ]
    assert payload["expansion_readiness"]["reference_only_candidates"] == []
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
                    "cluster_flow": {"passed": True},
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
    assert payload["overall_ready"] is False
    assert payload["validation_summary"]["overall_passed"] is True
    assert [item["domain_pack_id"] for item in payload["domain_packs"]] == ["software_delivery_pack"]
    assert "platformized domain pack" in payload["gates"][3]["detail"]
    assert payload["gates"][5]["gate"] == "local_foundation_closure"
    assert payload["gates"][6]["gate"] == "orchestration_baseline"
    assert payload["gates"][7]["gate"] == "cluster_failover_core_completion"
    assert payload["remaining_gaps"] == []
    assert payload["governance_alerts"]["overall_status"] == "blocking"


def test_cli_governance_metrics_and_alerts_reports(tmp_path: Path) -> None:
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
                    "cluster_flow": {"passed": True},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    metrics_result = _invoke(
        tmp_path,
        "governance",
        "metrics",
        "--validation-report-path",
        str(validation_report_path),
    )
    alerts_result = _invoke(
        tmp_path,
        "governance",
        "alerts",
        "--validation-report-path",
        str(validation_report_path),
    )

    assert metrics_result.exit_code == 0
    metrics_payload = json.loads(metrics_result.stdout)
    assert metrics_payload["tech_debt"]["open_debt_ids"] == OPEN_DEBT_IDS
    assert metrics_payload["tech_debt"]["blocking_open_debt_ids"] == BLOCKING_OPEN_DEBT_IDS
    assert metrics_payload["review_policy"]["supported_policy_count"] == 5
    assert metrics_payload["automation"]["governance_alerts_available"] is True

    assert alerts_result.exit_code == 0
    alerts_payload = json.loads(alerts_result.stdout)
    assert alerts_payload["overall_status"] == "blocking"
    assert any(item["alert_id"] == "open_tech_debt_remaining" for item in alerts_payload["alerts"])


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
                    "cluster_flow": {"passed": True},
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
    assert payload["overall_ready"] is False


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


def test_cli_run_replay_packet_projects_metrics(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Build one replayable CLI artifact",
        "--preset",
        "feature_delivery",
        "--prepare",
        "--execute",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]

    replay_result = _invoke(tmp_path, "run", "replay-packet", run_id)

    assert replay_result.exit_code == 0
    replay_payload = json.loads(replay_result.stdout)
    assert replay_payload["packet_version"] == "m9_phase_1_v1"
    assert replay_payload["metrics"]["counts"]["events"] >= 1
    assert replay_payload["review_lineage"]["effective_review_state"] == "auto_passed"

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


def test_cli_run_orchestration_projects_project_delivery(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(CodexAdapter, "launch", _fake_cli_external_launch)
    monkeypatch.setattr(LangChainAgentAdapter, "launch", _fake_cli_external_launch)
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Ship a complex project slice",
        "--preset",
        "project_delivery",
        "--prepare",
        "--execute",
    )
    create_payload = json.loads(create_result.stdout)
    run_id = create_payload["run"]["run_id"]

    orchestration_result = _invoke(tmp_path, "run", "orchestration", run_id)
    status_result = _invoke(tmp_path, "run", "status-detail", run_id)

    assert orchestration_result.exit_code == 0
    orchestration_payload = json.loads(orchestration_result.stdout)
    assert orchestration_payload["enabled"] is True
    assert orchestration_payload["orchestration"]["role_progress"]["planner"]["status"] == "completed"

    status_payload = json.loads(status_result.stdout)
    assert status_payload["orchestration"]["parallel_batch"]["member_count"] == 2
    assert status_payload["orchestration"]["role_progress"]["reviewer"]["status"] == "completed"


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


def test_cli_compile_and_mutation_report_support_repo_mutation_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTHONPATH", repo_root.as_posix())
    monkeypatch.setattr(OpenCodeAdapter, "launch", _fake_cli_patch_launch)
    target_file = tmp_path / "cli_target.txt"
    target_file.write_text("before\n", encoding="utf-8")
    task_card = tmp_path / "cli_task_card.md"
    task_card.write_text("# CLI Mutation\n", encoding="utf-8")
    verifier = tmp_path / "verify_cli_target.py"
    verifier.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "sys.exit(0 if Path('cli_target.txt').read_text(encoding='utf-8') == 'after\\n' else 1)\n",
        encoding="utf-8",
    )
    test_command = f"{sys.executable} {verifier.name}"

    _invoke(tmp_path, "db", "reset")
    run_id = json.loads(
        _invoke(
            tmp_path,
            "run",
            "create",
            "--goal",
            "CLI repo mutation",
            "--preset",
            "feature_delivery",
        ).stdout
    )["run"]["run_id"]
    compile_result = _invoke(
        tmp_path,
        "run",
        "compile",
        run_id,
        "--adapter",
        "opencode",
        "--task-card-ref",
        "M16-CLI",
        "--task-card-path",
        task_card.as_posix(),
        "--write-set",
        "cli_target.txt",
        "--test-command",
        test_command,
        "--mutation-mode",
        "patch_apply",
    )
    assert compile_result.exit_code == 0
    compile_payload = json.loads(compile_result.stdout)
    assert compile_payload["mutation_contract"]["mutation_mode"] == "patch_apply"
    receipt_result = _invoke(
        tmp_path,
        "run",
        "issue-receipt",
        "--action-type",
        "resume_run",
        "--run-id",
        run_id,
    )
    assert receipt_result.exit_code == 0
    receipt_id = json.loads(receipt_result.stdout)["receipt_id"]
    resume_result = _invoke(
        tmp_path,
        "run",
        "resume",
        run_id,
        "--operator-receipt-id",
        receipt_id,
    )
    assert resume_result.exit_code == 0
    mutation_report_result = _invoke(tmp_path, "run", "mutation-report", run_id)
    mutation_payload = json.loads(mutation_report_result.stdout)
    assert mutation_payload["mutation_result"]["final_test_status"] == "passed"
    assert mutation_payload["result_envelope"]["mutations"]["final_test_status"] == "passed"
    summary_result = _invoke(tmp_path, "run", "pr-ready-summary", run_id)
    summary_payload = json.loads(summary_result.stdout)
    assert summary_payload["readiness"] == "ready"
    assert summary_payload["bounded_patch"]["changed_files"] == ["cli_target.txt"]
    assert summary_payload["manual_git"]["push"] == "not_performed"
    assert target_file.read_text(encoding="utf-8") == "after\n"


def test_cli_from_task_card_executes_bounded_patch_and_returns_pr_ready_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTHONPATH", repo_root.as_posix())
    monkeypatch.setattr(OpenCodeAdapter, "launch", _fake_cli_patch_launch)
    target_file = tmp_path / "cli_target.txt"
    target_file.write_text("before\n", encoding="utf-8")
    task_card = tmp_path / "local_task_card.md"
    task_card.write_text("# Local task card from CLI\n\nImplement one bounded patch.\n", encoding="utf-8")
    verifier = tmp_path / "verify_cli_target.py"
    verifier.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "sys.exit(0 if Path('cli_target.txt').read_text(encoding='utf-8') == 'after\\n' else 1)\n",
        encoding="utf-8",
    )

    _invoke(tmp_path, "db", "reset")
    receipt_result = _invoke(
        tmp_path,
        "run",
        "issue-receipt",
        "--action-type",
        "launch_execute",
        "--goal",
        "Local task card from CLI",
        "--preset",
        "feature_delivery",
        "--adapter",
        "opencode",
        "--task-card-ref",
        "local_task_card",
        "--task-card-path",
        task_card.as_posix(),
        "--write-set",
        "cli_target.txt",
        "--test-command",
        f"{sys.executable} {verifier.name}",
        "--mutation-mode",
        "patch_apply",
    )
    assert receipt_result.exit_code == 0
    receipt_id = json.loads(receipt_result.stdout)["receipt_id"]
    result = _invoke(
        tmp_path,
        "run",
        "from-task-card",
        task_card.as_posix(),
        "--adapter",
        "opencode",
        "--write-set",
        "cli_target.txt",
        "--test-command",
        f"{sys.executable} {verifier.name}",
        "--execute",
        "--operator-receipt-id",
        receipt_id,
    )

    assert result.exit_code == 0
    payload = _load_json_after_progress(result.stdout)
    assert payload["run"]["goal"] == "Local task card from CLI"
    assert payload["capability_adapter"] == "opencode"
    assert payload["mutation_contract"]["task_card_ref"] == "local_task_card"
    assert payload["pr_ready_summary"]["readiness"] == "ready"
    assert payload["pr_ready_summary"]["tests"]["status"] == "passed"
    assert target_file.read_text(encoding="utf-8") == "after\n"


def test_cli_from_task_card_project_delivery_patch_apply_stays_direct(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTHONPATH", repo_root.as_posix())
    monkeypatch.setattr(OpenCodeAdapter, "launch", _fake_cli_patch_launch)
    target_file = tmp_path / "cli_target.txt"
    target_file.write_text("before\n", encoding="utf-8")
    task_card = tmp_path / "local_task_card.md"
    task_card.write_text("# Local direct task card\n\nImplement one bounded patch.\n", encoding="utf-8")

    _invoke(tmp_path, "db", "reset")
    receipt_result = _invoke(
        tmp_path,
        "run",
        "issue-receipt",
        "--action-type",
        "launch_execute",
        "--goal",
        "Local direct task card",
        "--preset",
        "project_delivery",
        "--adapter",
        "opencode",
        "--task-card-ref",
        "local_direct_task_card",
        "--task-card-path",
        task_card.as_posix(),
        "--write-set",
        "cli_target.txt",
        "--mutation-mode",
        "patch_apply",
    )
    receipt_id = json.loads(receipt_result.stdout)["receipt_id"]

    result = _invoke(
        tmp_path,
        "run",
        "from-task-card",
        task_card.as_posix(),
        "--preset",
        "project_delivery",
        "--adapter",
        "opencode",
        "--task-card-ref",
        "local_direct_task_card",
        "--write-set",
        "cli_target.txt",
        "--execute",
        "--operator-receipt-id",
        receipt_id,
    )

    assert result.exit_code == 0
    payload = _load_json_after_progress(result.stdout)
    assert payload["run"]["preset_id"] == "project_delivery"
    assert payload["pr_ready_summary"]["bounded_patch"]["changed_files"] == ["cli_target.txt"]
    assert target_file.read_text(encoding="utf-8") == "after\n"
    with sqlite3.connect(tmp_path / "workflow.db") as connection:
        runs = connection.execute("SELECT goal, preset_id FROM runs ORDER BY created_at").fetchall()
    assert runs == [("Local direct task card", "project_delivery")]


def test_cli_from_task_card_defaults_patch_apply_to_codex(tmp_path: Path) -> None:
    task_card = tmp_path / "local_task_card.md"
    task_card.write_text("# Local task card from CLI\n\nImplement one bounded patch.\n", encoding="utf-8")

    _invoke(tmp_path, "db", "reset")
    result = _invoke(
        tmp_path,
        "run",
        "from-task-card",
        task_card.as_posix(),
        "--write-set",
        "cli_target.txt",
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["capability_adapter"] == "codex"
    assert payload["resolved_execution"]["source_map"]["adapter_name"]["source"] == "patch_apply_enforcement"


def test_cli_resume_rejects_unissued_patch_receipt_before_adapter_launch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    launched = False

    def _unexpected_launch(self, packet):  # type: ignore[no-untyped-def]
        nonlocal launched
        launched = True
        return _fake_cli_patch_launch(self, packet)

    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTHONPATH", repo_root.as_posix())
    monkeypatch.setattr(OpenCodeAdapter, "launch", _unexpected_launch)
    target_file = tmp_path / "cli_target.txt"
    target_file.write_text("before\n", encoding="utf-8")

    _invoke(tmp_path, "db", "reset")
    run_id = json.loads(
        _invoke(
            tmp_path,
            "run",
            "create",
            "--goal",
            "CLI repo mutation with fake receipt",
            "--preset",
            "feature_delivery",
        ).stdout
    )["run"]["run_id"]
    compile_result = _invoke(
        tmp_path,
        "run",
        "compile",
        run_id,
        "--adapter",
        "opencode",
        "--task-card-ref",
        "M16-CLI",
        "--write-set",
        "cli_target.txt",
        "--mutation-mode",
        "patch_apply",
    )
    assert compile_result.exit_code == 0

    resume_result = _invoke(
        tmp_path,
        "run",
        "resume",
        run_id,
        "--operator-receipt-id",
        "not_a_real_receipt",
    )

    assert resume_result.exit_code == 1
    payload = json.loads(resume_result.stdout)
    assert payload["error"]["code"] == "entity_not_found"
    assert launched is False
    assert target_file.read_text(encoding="utf-8") == "before\n"


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
    assert evidence_payload["result_envelope"]["summary"] == evidence_payload["summary"]
    assert evidence_payload["result_envelope"]["verification"]["return_code"] == 0
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


def test_cli_compile_can_pin_codex_adapter(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    create_result = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "Pin codex adapter via CLI",
        "--preset",
        "feature_delivery",
    )
    run_id = json.loads(create_result.stdout)["run"]["run_id"]

    compile_result = _invoke(
        tmp_path,
        "run",
        "compile",
        run_id,
        "--adapter",
        "codex",
        "--codex-model",
        "gpt-5.1-codex-max",
    )
    assert compile_result.exit_code == 0
    compile_payload = json.loads(compile_result.stdout)
    assert compile_payload["capability_adapter"] == "codex"
    assert compile_payload["resolved_execution"]["selected_model"] == "gpt-5.1-codex-max"

    detail_result = _invoke(tmp_path, "run", "status-detail", run_id)
    detail_payload = json.loads(detail_result.stdout)
    assert detail_payload["capability_resolution"]["adapter_name"] == "codex"
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
    assert error["details"]["available_adapters"] == AVAILABLE_SHELL_EXEC_ADAPTERS


def test_cli_scheduler_cluster_exposes_local_only_snapshot_by_default(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")

    cluster_result = _invoke(tmp_path, "scheduler", "cluster")

    assert cluster_result.exit_code == 0
    payload = json.loads(cluster_result.stdout)
    assert payload["enabled"] is False
    assert payload["mode"] == "local_only"
    assert payload["leader_node_id"] is not None
    assert payload["authority_node_id"] == payload["leader_node_id"]
    assert payload["authority_term_no"] == payload["term_no"]
    assert payload["decision_index"] == payload["commit_index"]
    assert payload["quorum_size"] == 1


def test_cli_scheduler_cluster_exposes_quorum_snapshot_when_flag_enabled(tmp_path: Path) -> None:
    env = {"UAWO_ENABLE_SCHEDULER_AUTHORITY_CLUSTER": "1"}
    _invoke(tmp_path, "db", "reset", env=env)

    cluster_result = _invoke(tmp_path, "scheduler", "cluster", env=env)

    assert cluster_result.exit_code == 0
    payload = json.loads(cluster_result.stdout)
    assert payload["enabled"] is True
    assert payload["mode"] == "quorum"
    assert payload["leader_node_id"] is not None
    assert payload["authority_node_id"] == payload["leader_node_id"]
    assert payload["authority_term_no"] == payload["term_no"]
    assert payload["decision_index"] == payload["commit_index"]
    assert payload["quorum_size"] >= 1


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
    assert compile_payload["resolved_execution"]["adapter_name"] == "shell"

    detail_result = _invoke(tmp_path, "run", "status-detail", run_id)
    assert detail_result.exit_code == 0
    detail_payload = json.loads(detail_result.stdout)
    assert detail_payload["next_action"] == "resume"
    assert detail_payload["waiting_reason"] == "awaiting_runtime_resume"
    assert detail_payload["failure_reason"] is None
    assert detail_payload["last_runtime_state"]["graph_step"] == "compiled"
    assert detail_payload["last_review_verdict"] is None
    assert detail_payload["recoverability_hint"] == "resume_run"
    assert detail_payload["resolved_execution"]["adapter_name"] == "shell"
    assert detail_payload["execution_resolution_trace"]["source_map"]["adapter_name"]["scope"] == "compatibility_fallback"
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
    assert json.loads(auto_report.stdout)["result_envelope"]["verification"]["return_code"] == 0
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
    assert status_payload["latest_claim"]["owner_kind"] == "control_plane"
    assert status_payload["latest_claim"]["owner_id"] == "control_plane_local"
    assert status_payload["latest_claim"]["domain_kind"] == "runtime_task"
    assert status_payload["ownership_topology"]["claim"]["owner_id"] == "control_plane_local"
    assert claims_payload[0]["release_reason"] == "run_terminal"
    assert claims_payload[0]["owner_id"] == "control_plane_local"
    assert claims_payload[0]["domain_key"] == status_payload["latest_claim"]["domain_key"]


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
    assert detail_payload["latest_worker_lease"]["worker_kind"] == "worker"
    assert detail_payload["latest_worker_lease"]["claim_id"] == detail_payload["latest_claim"]["claim_id"]
    assert detail_payload["ownership_topology"]["worker_lease"]["worker_id"] == "worker_shell_local"
    assert detail_payload["ownership_topology"]["topology_aligned"] is True
    assert detail_payload["worker_lease_projection"]["latest_adapter_name"] == "shell"
    assert inspect_payload["latest_claim"]["owner_kind"] == "control_plane"
    assert inspect_payload["latest_worker_lease"]["status"] == "released"
    assert inspect_payload["ownership_topology"]["worker_lease"]["domain_kind"] == "runtime_task"
    assert inspect_payload["worker_lease_projection"]["active_lease_count"] == 0


def test_cli_batch_resume_returns_parallel_batch_summary(tmp_path: Path) -> None:
    _invoke(tmp_path, "db", "reset")
    first_create = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "CLI parallel batch first",
        "--preset",
        "feature_delivery",
        "--prepare",
    )
    second_create = _invoke(
        tmp_path,
        "run",
        "create",
        "--goal",
        "CLI parallel batch second",
        "--preset",
        "feature_delivery",
        "--prepare",
    )
    first_run_id = json.loads(first_create.stdout)["run"]["run_id"]
    second_run_id = json.loads(second_create.stdout)["run"]["run_id"]

    batch_result = _invoke(tmp_path, "run", "batch-resume", first_run_id, second_run_id, "--max-workers", "2")
    first_status_result = _invoke(tmp_path, "run", "status", first_run_id)
    first_detail_result = _invoke(tmp_path, "run", "status-detail", first_run_id)

    assert batch_result.exit_code == 0
    payload = json.loads(batch_result.stdout)
    assert payload["status"] == "completed"
    assert payload["member_count"] == 2
    assert payload["execution_mode"] == "parallel"
    assert payload["barrier_enabled"] is True
    assert payload["degraded_to_serial"] is False
    assert payload["partial_failure_resume"]["enabled"] is False
    assert len(payload["results"]) == 2
    assert json.loads(first_status_result.stdout)["parallel_batch"]["barrier_id"] == payload["barrier_id"]
    assert json.loads(first_detail_result.stdout)["parallel_batch"]["barrier_id"] == payload["barrier_id"]


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
