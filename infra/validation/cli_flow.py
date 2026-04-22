from __future__ import annotations

from typing import Any

from infra.validation.common import *  # noqa: F401,F403

def validate_cli_flow(env: dict[str, str], db_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"passed": False}
    env = {
        **env,
        "UAWO_ENABLE_AGENT_LANE": "1",
        "UAWO_ENABLE_MCP_SOURCE": "1",
        "UAWO_ENABLE_SKILL_EXPORT": "1",
    }
    release_validation_report_path = PROJECT_ROOT / "state" / "offline_validate_release_readiness.json"
    release_validation_report_path.write_text(
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
            indent=2,
        ),
        encoding="utf-8",
    )
    reset_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "db", "reset"],
        env,
    )
    preset_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "preset", "list", "--json"],
        env,
    )
    domain_pack_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "domain-pack", "list", "--json"],
        env,
    )
    domain_pack_preview_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "domain-pack",
            "resolve",
            "--preset",
            "feature_delivery",
            "--task-kind",
            "shell_exec",
        ],
        env,
    )
    domain_pack_validate_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "domain-pack", "validate"],
        env,
    )
    memory_namespace_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "memory", "namespace", "list"],
        env,
    )
    capability_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "capability", "list"],
        env,
    )
    capability_sources_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "capability", "sources"],
        env,
    )
    capability_mcp_profiles_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "capability", "mcp-profiles"],
        env,
    )
    capability_projection_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "capability",
            "projection",
            "--preset",
            "research_spike_reviewable",
        ],
        env,
    )
    skill_export_root = PROJECT_ROOT / "state" / "offline_validate_skill_export"
    skill_export_root.mkdir(parents=True, exist_ok=True)
    skill_export_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "domain-pack",
            "export-skill",
            "--domain-pack-id",
            "software_delivery_pack",
            "--output-root",
            skill_export_root.as_posix(),
        ],
        env,
    )
    simulation_policy_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "simulation", "policy", "list"],
        env,
    )
    governance_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "governance", "tech-debt"],
        env,
    )
    governance_review_policy_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "governance", "review-policy"],
        env,
    )
    governance_release_readiness_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "governance",
            "release-readiness",
            "--validation-report-path",
            release_validation_report_path.as_posix(),
        ],
        env,
    )
    scheduler_cluster_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "scheduler", "cluster"],
        env,
    )
    governance_domain_pack_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "governance", "domain-pack"],
        env,
    )
    suggest_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "suggest-presets",
            "--goal",
            "Research runtime architecture",
        ],
        env,
    )

    auto_create_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "create",
            "--goal",
            "Offline validation auto run",
            "--preset",
            "feature_delivery",
            "--prepare",
            "--execute",
        ],
        env,
    )
    auto_run_id = auto_create_payload["run"]["run_id"]
    auto_runtime_task_id = auto_create_payload["prepared_task_id"]
    auto_memory_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "memory-candidates",
            auto_run_id,
        ],
        env,
    )
    auto_selected_memory_candidate = next(item for item in auto_memory_payload if item["namespace_id"] == "policy")
    auto_materialized_memory_item_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "materialize-memory",
            auto_run_id,
            "--candidate-id",
            auto_selected_memory_candidate["candidate_id"],
        ],
        env,
    )
    auto_memory_items_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "memory-items",
            auto_run_id,
        ],
        env,
    )
    auto_namespace_memory_items_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "memory",
            "item",
            "list",
            "--namespace",
            "policy",
        ],
        env,
    )
    auto_retrieval_preview_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "memory",
            "retrieve-preview",
            "--preset",
            "feature_delivery",
            "--namespace",
            "policy",
            "--memory-item-id",
            auto_materialized_memory_item_payload["memory_item_id"],
        ],
        env,
    )
    bridge_create_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "create",
            "--goal",
            "Offline validation memory-aware compile",
            "--preset",
            "feature_delivery",
        ],
        env,
    )
    bridge_run_id = bridge_create_payload["run"]["run_id"]
    bridge_compile_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "compile",
            bridge_run_id,
            "--memory-item-id",
            auto_materialized_memory_item_payload["memory_item_id"],
        ],
        env,
    )
    bridge_detail_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "status-detail",
            bridge_run_id,
        ],
        env,
    )
    bridge_resume_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "resume",
            bridge_run_id,
        ],
        env,
    )
    bridge_evidence_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "task",
            "evidence",
            bridge_compile_payload["runtime_task_id"],
        ],
        env,
    )
    auto_status_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "status", auto_run_id],
        env,
    )
    auto_detail_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "status-detail", auto_run_id],
        env,
    )
    auto_summary_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "summary", auto_run_id],
        env,
    )
    auto_simulation_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "simulation", auto_run_id],
        env,
    )
    auto_recorded_simulation_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "record-simulation",
            auto_run_id,
        ],
        env,
    )
    auto_post_record_detail_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "status-detail",
            auto_run_id,
        ],
        env,
    )
    auto_simulation_records_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "simulations",
            auto_run_id,
        ],
        env,
    )
    auto_event_inspection_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "event-inspection",
            auto_run_id,
        ],
        env,
    )
    auto_audit_report_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "audit-report", auto_run_id],
        env,
    )
    auto_inspection_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "inspect", auto_run_id],
        env,
    )
    auto_timeline_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "timeline", auto_run_id, "--json"],
        env,
    )
    auto_evidence_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "task", "evidence", auto_runtime_task_id],
        env,
    )
    auto_claims_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "claims", auto_run_id],
        env,
    )
    auto_leases_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "leases", auto_run_id],
        env,
    )
    auto_attempts_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "attempts", auto_run_id],
        env,
    )
    auto_snapshots_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "snapshots", auto_run_id],
        env,
    )
    auto_budget_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "budget", auto_run_id],
        env,
    )
    auto_artifact_path = Path(auto_create_payload["expected_artifacts"][0])
    if not auto_artifact_path.is_absolute():
        auto_artifact_path = PROJECT_ROOT / auto_artifact_path
    auto_artifact_text = auto_artifact_path.read_text(encoding="utf-8")

    human_create_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "create",
            "--goal",
            "Offline validation human run",
            "--preset",
            "research_spike",
        ],
        env,
    )
    human_run_id = human_create_payload["run"]["run_id"]
    human_compile_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "compile", human_run_id],
        env,
    )
    human_detail_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "status-detail", human_run_id],
        env,
    )
    human_summary_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "summary", human_run_id],
        env,
    )
    human_simulation_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "simulation", human_run_id],
        env,
    )
    human_inspection_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "inspect", human_run_id],
        env,
    )
    human_resume_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "resume", human_run_id],
        env,
    )
    human_event_inspection_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "event-inspection",
            human_run_id,
        ],
        env,
    )
    human_audit_report_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "audit-report", human_run_id],
        env,
    )
    human_approve_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "approve", human_run_id],
        env,
    )
    human_handoffs_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "handoffs", human_run_id],
        env,
    )
    human_timeline_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "timeline", human_run_id, "--json"],
        env,
    )
    human_claims_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "claims", human_run_id],
        env,
    )
    human_leases_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "leases", human_run_id],
        env,
    )
    human_attempts_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "attempts", human_run_id],
        env,
    )
    human_snapshots_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "snapshots", human_run_id],
        env,
    )
    human_budget_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "budget", human_run_id],
        env,
    )

    recommended_create_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "create",
            "--goal",
            "Offline validation recommended run",
            "--preset",
            "advisory_delivery",
        ],
        env,
    )
    recommended_run_id = recommended_create_payload["run"]["run_id"]
    recommended_compile_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "compile", recommended_run_id],
        env,
    )
    mutate_task_packet_command(
        db_path,
        recommended_compile_payload["runtime_task_id"],
        ["python", "-c", "import sys; sys.exit(2)"],
    )
    recommended_resume_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "resume", recommended_run_id],
        env,
    )
    recommended_detail_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "status-detail", recommended_run_id],
        env,
    )
    recommended_approve_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "approve", recommended_run_id],
        env,
    )

    mandatory_create_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "create",
            "--goal",
            "Offline validation mandatory run",
            "--preset",
            "guarded_delivery",
            "--prepare",
            "--execute",
        ],
        env,
    )
    mandatory_run_id = mandatory_create_payload["run"]["run_id"]
    mandatory_detail_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "status-detail", mandatory_run_id],
        env,
    )
    mandatory_simulations_before_approve_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "simulations", mandatory_run_id],
        env,
    )
    mandatory_approve_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "approve", mandatory_run_id],
        env,
    )
    mandatory_simulations_after_approve_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "simulations", mandatory_run_id],
        env,
    )

    noop_create_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "create",
            "--goal",
            "Offline validation noop run",
            "--preset",
            "research_spike",
        ],
        env,
    )
    noop_run_id = noop_create_payload["run"]["run_id"]
    noop_compile_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "compile",
            noop_run_id,
            "--task-kind",
            "noop",
        ],
        env,
    )
    noop_detail_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "status-detail", noop_run_id],
        env,
    )
    noop_runtime_task_id = noop_detail_payload["runtime_tasks"][0]["runtime_task_id"]
    noop_resume_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "resume", noop_run_id],
        env,
    )
    noop_evidence_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "task", "evidence", noop_runtime_task_id],
        env,
    )
    noop_approve_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "approve", noop_run_id],
        env,
    )

    repair_create_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "create",
            "--goal",
            "Offline validation repair run",
            "--preset",
            "feature_delivery",
        ],
        env,
    )
    repair_run_id = repair_create_payload["run"]["run_id"]
    run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "compile", repair_run_id],
        env,
    )
    run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "resume", repair_run_id],
        env,
    )
    corrupt_runtime_state_for_run(
        db_path,
        repair_run_id,
        graph_step="awaiting_review",
        is_terminal=False,
        extra_payload={"corrupted": True},
    )
    repair_plan_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "reconcile", repair_run_id],
        env,
    )
    repair_apply_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "reconcile",
            repair_run_id,
            "--apply",
        ],
        env,
    )
    repair_inspection_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "inspect", repair_run_id],
        env,
    )

    cancel_create_payload, _ = run_json_command(
        [
            sys.executable,
            "-m",
            "apps.operator_cli.main",
            "--db-path",
            db_path.as_posix(),
            "run",
            "create",
            "--goal",
            "Offline validation cancel run",
            "--preset",
            "feature_delivery",
        ],
        env,
    )
    cancel_run_id = cancel_create_payload["run"]["run_id"]
    run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "cancel", cancel_run_id],
        env,
    )
    run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "cancel", cancel_run_id],
        env,
    )
    cancel_status_payload, _ = run_json_command(
        [sys.executable, "-m", "apps.operator_cli.main", "--db-path", db_path.as_posix(), "run", "status", cancel_run_id],
        env,
    )

    artifact_refs = auto_evidence_payload.get("artifact_refs", [])
    artifact_paths_exist = all(Path(item["path"]).exists() for item in artifact_refs)
    bridge_artifact_refs = bridge_evidence_payload.get("artifact_refs", [])
    bridge_artifact_text = (
        Path(bridge_artifact_refs[0]["path"]).read_text(encoding="utf-8")
        if bridge_artifact_refs and Path(bridge_artifact_refs[0]["path"]).exists()
        else ""
    )
    auto_timeline_events = [item["event_type"] for item in auto_timeline_payload]
    human_timeline_events = [item["event_type"] for item in human_timeline_payload]
    result.update(
        {
            "db_reset_seeded": reset_payload.get("seeded_presets", []),
            "preset_ids": [item["preset_id"] for item in preset_payload],
            "domain_pack_ids": [item["domain_pack_id"] for item in domain_pack_payload],
            "domain_pack_preview_id": (
                domain_pack_preview_payload.get("domain_pack", {}).get("domain_pack_id")
                if domain_pack_preview_payload.get("resolved")
                else None
            ),
            "domain_pack_preview_adapter": (
                domain_pack_preview_payload.get("capability_resolution", {}).get("adapter_name")
            ),
            "domain_pack_validation_passed": domain_pack_validate_payload.get("passed"),
            "domain_pack_validation_issue_count": domain_pack_validate_payload.get("issue_count"),
            "memory_namespace_ids": [item["namespace_id"] for item in memory_namespace_payload],
            "capability_routes": capability_payload,
            "m8_capability_source_types": [item["source_type"] for item in capability_sources_payload],
            "m8_mcp_profile_id": (
                capability_mcp_profiles_payload[0]["profile_id"] if capability_mcp_profiles_payload else None
            ),
            "m8_projection_lane": capability_projection_payload["execution_lane"],
            "m8_projection_adapter": capability_projection_payload["capability_resolution"]["adapter_name"],
            "m8_projection_tool_names": [
                item["tool_name"] for item in capability_projection_payload["tool_projection_manifest"]["tools"]
            ],
            "m8_projection_trust_tiers": capability_projection_payload["tool_projection_manifest"]["trust_tiers"],
            "m8_skill_export_domain_pack_id": skill_export_payload["domain_pack_id"],
            "m8_skill_export_bundle_has_readme": (Path(skill_export_payload["bundle_path"]) / "README.md").exists(),
            "m8_skill_export_bundle_has_manifest": (Path(skill_export_payload["bundle_path"]) / "skill.json").exists(),
            "simulation_policy_ids": [item["policy_id"] for item in simulation_policy_payload],
            "governance_open_debt_count": governance_payload["open_debt_count"],
            "governance_active_gate_focus_ids": [item["debt_id"] for item in governance_payload["active_gate_focus_items"]],
            "governance_supported_review_policies": [
                item["policy"] for item in governance_review_policy_payload["supported_policies"]
            ],
            "governance_review_policy_debt_id": (
                governance_review_policy_payload["debt_linkage"]["debt_id"]
                if governance_review_policy_payload["debt_linkage"] is not None
                else None
            ),
            "governance_release_ready": governance_release_readiness_payload["overall_ready"],
            "governance_release_domain_pack_ids": [
                item["domain_pack_id"] for item in governance_release_readiness_payload["domain_packs"]
            ],
            "governance_domain_pack_platformized": governance_domain_pack_payload["overall_platformized"],
            "scheduler_cluster_mode": scheduler_cluster_payload["mode"],
            "scheduler_cluster_leader": scheduler_cluster_payload["leader_node_id"],
            "scheduler_cluster_quorum_size": scheduler_cluster_payload["quorum_size"],
            "suggest_top_preset": suggest_payload[0]["preset_id"] if suggest_payload else None,
            "auto_run_status": auto_status_payload.get("status"),
            "auto_review_decision": auto_create_payload.get("review_decision"),
            "auto_domain_pack_id": auto_status_payload.get("domain_pack", {}).get("domain_pack_id"),
            "auto_capability_adapter": auto_status_payload.get("capability_resolution", {}).get("adapter_name"),
            "auto_memory_namespace_ids": [item["namespace_id"] for item in auto_memory_payload],
            "auto_materialized_memory_namespace": auto_materialized_memory_item_payload["namespace_id"],
            "auto_materialized_memory_source_candidate_id": auto_materialized_memory_item_payload["source_candidate_id"],
            "auto_memory_item_namespace_ids": [item["namespace_id"] for item in auto_memory_items_payload],
            "auto_policy_memory_item_run_ids": [item["run_id"] for item in auto_namespace_memory_items_payload],
            "auto_retrieval_preview_item_count": auto_retrieval_preview_payload["item_count"],
            "auto_retrieval_preview_namespace_ids": auto_retrieval_preview_payload["namespace_ids"],
            "auto_retrieval_preview_selected_ids": auto_retrieval_preview_payload["selected_memory_item_ids"],
            "bridge_compile_status": bridge_compile_payload["run"]["status"],
            "bridge_resume_status": bridge_resume_payload["run"]["status"],
            "bridge_memory_preview_selected_ids": bridge_compile_payload["memory_preview"]["selected_memory_item_ids"],
            "bridge_detail_memory_preview_selected_ids": bridge_detail_payload["memory_retrieval_preview"][
                "selected_memory_item_ids"
            ],
            "bridge_artifact_contains_memory_item_ids": "memory_item_ids:" in bridge_artifact_text,
            "bridge_artifact_contains_memory_brief": "memory_brief:" in bridge_artifact_text,
            "auto_artifact_contains_domain_pack": "domain_pack: software_delivery_pack" in auto_artifact_text,
            "auto_artifact_contains_goal_prefix": "goal: [software-delivery]" in auto_artifact_text,
            "auto_failure_reason": auto_detail_payload.get("failure_reason"),
            "auto_last_runtime_step": auto_detail_payload.get("last_runtime_state", {}).get("graph_step"),
            "auto_summary_category": auto_summary_payload["failure_taxonomy"]["category"],
            "auto_simulation_status": auto_simulation_payload["status"],
            "auto_simulation_policy_id": auto_simulation_payload["policy_id"],
            "auto_recorded_simulation_status": auto_recorded_simulation_payload["status"],
            "auto_recorded_simulation_sources": [item["recorded_from"] for item in auto_simulation_records_payload],
            "auto_recorded_simulation_record_count": len(auto_simulation_records_payload),
            "auto_latest_simulation_record_id": (
                auto_post_record_detail_payload.get("latest_simulation_record") or {}
            ).get("record_id"),
            "auto_event_inspection_passed": auto_event_inspection_payload["closure_audit"]["passed"],
            "auto_event_closure_state": auto_event_inspection_payload["closure_audit"]["state"],
            "auto_audit_closure_state": auto_audit_report_payload["review_packet"]["closure_summary"]["state"],
            "auto_inspection_passed": auto_inspection_payload.get("passed"),
            "auto_inspection_problem_count": auto_inspection_payload.get("problem_count"),
            "auto_timeline_events": auto_timeline_events,
            "auto_active_claims": auto_status_payload.get("active_claims", []),
            "auto_latest_claim": auto_status_payload.get("latest_claim"),
            "auto_active_worker_leases": auto_status_payload.get("active_worker_leases", []),
            "auto_latest_worker_lease": auto_status_payload.get("latest_worker_lease"),
            "auto_claim_statuses": [item["status"] for item in auto_claims_payload],
            "auto_attempt_statuses": [item["status"] for item in auto_attempts_payload],
            "auto_attempt_triggers": [item["trigger"] for item in auto_attempts_payload],
            "auto_worker_lease_statuses": [item["status"] for item in auto_leases_payload],
            "auto_snapshot_stages": [item["stage"] for item in auto_snapshots_payload],
            "auto_remaining_retries": auto_budget_payload["budget_projection"]["remaining_retries"],
            "human_compile_status": human_compile_payload["run"]["status"],
            "human_next_action": human_detail_payload.get("next_action"),
            "human_waiting_reason": human_detail_payload.get("waiting_reason"),
            "human_last_runtime_step": human_detail_payload.get("last_runtime_state", {}).get("graph_step"),
            "human_summary_category": human_summary_payload["failure_taxonomy"]["category"],
            "human_simulation_status": human_simulation_payload["status"],
            "human_simulation_policy_id": human_simulation_payload["policy_id"],
            "human_event_inspection_passed": human_event_inspection_payload["closure_audit"]["passed"],
            "human_event_closure_state": human_event_inspection_payload["closure_audit"]["state"],
            "human_audit_closure_state": human_audit_report_payload["review_packet"]["closure_summary"]["state"],
            "human_recoverability_hint": human_detail_payload.get("recoverability_hint"),
            "human_inspection_passed": human_inspection_payload.get("passed"),
            "human_inspection_problem_count": human_inspection_payload.get("problem_count"),
            "human_resume_status": human_resume_payload["run"]["status"],
            "human_approve_status": human_approve_payload["run"]["status"],
            "human_handoffs_count": len(human_handoffs_payload),
            "human_timeline_events": human_timeline_events,
            "human_claim_statuses": [item["status"] for item in human_claims_payload],
            "human_attempt_statuses": [item["status"] for item in human_attempts_payload],
            "human_attempt_triggers": [item["trigger"] for item in human_attempts_payload],
            "human_worker_lease_statuses": [item["status"] for item in human_leases_payload],
            "human_snapshot_stages": [item["stage"] for item in human_snapshots_payload],
            "human_remaining_retries": human_budget_payload["budget_projection"]["remaining_retries"],
            "recommended_resume_status": recommended_resume_payload["run"]["status"],
            "recommended_review_decision": recommended_resume_payload["review_decision"],
            "recommended_review_policy": recommended_detail_payload["review_policy"],
            "recommended_effective_review_state": recommended_detail_payload["effective_review_state"],
            "recommended_latest_reviewer_type": recommended_detail_payload["latest_review_verdict"]["reviewer_type"],
            "recommended_latest_decision": recommended_detail_payload["latest_review_verdict"]["decision"],
            "recommended_approve_status": recommended_approve_payload["run"]["status"],
            "mandatory_run_status": mandatory_create_payload["run"]["status"],
            "mandatory_review_decision": mandatory_create_payload["review_decision"],
            "mandatory_review_policy": mandatory_detail_payload["review_policy"],
            "mandatory_effective_review_state": mandatory_detail_payload["effective_review_state"],
            "mandatory_latest_reviewer_type": mandatory_detail_payload["latest_review_verdict"]["reviewer_type"],
            "mandatory_latest_decision": mandatory_detail_payload["latest_review_verdict"]["decision"],
            "mandatory_latest_simulation_record_source": (
                mandatory_detail_payload.get("latest_simulation_record") or {}
            ).get("recorded_from"),
            "mandatory_simulation_sources_before_approve": [
                item["recorded_from"] for item in mandatory_simulations_before_approve_payload
            ],
            "mandatory_approve_status": mandatory_approve_payload["run"]["status"],
            "mandatory_simulation_sources_after_approve": [
                item["recorded_from"] for item in mandatory_simulations_after_approve_payload
            ],
            "noop_compile_status": noop_compile_payload["run"]["status"],
            "noop_task_kind": noop_detail_payload["runtime_tasks"][0]["task_kind"],
            "noop_resume_status": noop_resume_payload["run"]["status"],
            "noop_approve_status": noop_approve_payload["run"]["status"],
            "noop_adapter_name": noop_evidence_payload.get("raw_execution", {}).get("adapter_name"),
            "noop_artifact_paths_exist": all(
                Path(item["path"]).exists() for item in noop_evidence_payload.get("artifact_refs", [])
            ),
            "repair_plan_action": repair_plan_payload["problems"][0]["repair_action"],
            "repair_apply_action": repair_apply_payload["action"],
            "repair_inspection_passed": repair_inspection_payload["passed"],
            "artifact_ref_fields": list(artifact_refs[0].keys()) if artifact_refs else [],
            "artifact_paths_exist": artifact_paths_exist,
            "cancel_status": cancel_status_payload.get("status"),
        }
    )
    result["passed"] = all(
        [
            result["db_reset_seeded"]
            == [
                "feature_delivery",
                "optional_delivery",
                "research_spike",
                "advisory_delivery",
                "guarded_delivery",
                "research_spike_reviewable",
                "project_delivery",
                "guarded_project_delivery",
            ],
            set(result["preset_ids"])
                == {
                    "feature_delivery",
                    "optional_delivery",
                    "research_spike",
                    "advisory_delivery",
                    "guarded_delivery",
                    "research_spike_reviewable",
                    "project_delivery",
                    "guarded_project_delivery",
                },
            result["domain_pack_ids"] == ["software_delivery_pack"],
            result["domain_pack_preview_id"] == "software_delivery_pack",
            result["domain_pack_preview_adapter"] == "shell",
            result["domain_pack_validation_passed"] is True,
            result["domain_pack_validation_issue_count"] == 0,
            result["memory_namespace_ids"] == ["repo", "failure", "policy", "release"],
            result["capability_routes"]
            == [
                {"capability": "noop", "adapter_name": "noop", "adapter_class": "NoopAdapter"},
                {"capability": "shell_exec", "adapter_name": "shell", "adapter_class": "ShellAdapter"},
                {"capability": "shell_exec", "adapter_name": "agent", "adapter_class": "LangChainAgentAdapter"},
                {"capability": "shell_exec", "adapter_name": "opencode", "adapter_class": "OpenCodeAdapter"},
            ],
            result["m8_capability_source_types"] == ["built_in", "mcp_stdio"],
            result["m8_mcp_profile_id"] == "local_workspace_readonly",
            result["m8_projection_lane"] == "standard_agent",
            result["m8_projection_adapter"] == "agent",
            "mcp_list_workspace_files" in result["m8_projection_tool_names"],
            "mcp_read_workspace_text" in result["m8_projection_tool_names"],
            result["m8_projection_trust_tiers"] == ["t0_builtin_local", "t1_local_stdio_mcp"],
            result["m8_skill_export_domain_pack_id"] == "software_delivery_pack",
            result["m8_skill_export_bundle_has_readme"] is True,
            result["m8_skill_export_bundle_has_manifest"] is True,
            result["simulation_policy_ids"]
            == [
                "advisory_failure_simulation",
                "delivery_consistency_simulation",
                "research_no_simulation",
            ],
            result["governance_open_debt_count"] == 4,
            result["governance_active_gate_focus_ids"]
            == ["TD-STRUCT-001", "TD-STRUCT-003", "TD-STRUCT-005", "TD-STRUCT-006"],
            result["governance_supported_review_policies"]
            == ["auto_only", "optional", "recommended", "human_required", "mandatory"],
            result["governance_review_policy_debt_id"] == "TD-006",
            result["governance_release_ready"] is True,
            result["governance_release_domain_pack_ids"] == ["software_delivery_pack"],
            result["governance_domain_pack_platformized"] is True,
            result["scheduler_cluster_mode"] == "quorum",
            result["scheduler_cluster_leader"] is not None,
            result["scheduler_cluster_quorum_size"] >= 1,
            result["suggest_top_preset"] == "research_spike",
            result["auto_run_status"] == "completed",
            result["auto_review_decision"] == "pass",
            result["auto_domain_pack_id"] == "software_delivery_pack",
            result["auto_capability_adapter"] == "shell",
            set(result["auto_memory_namespace_ids"]) == {"repo", "policy", "release"},
            result["auto_materialized_memory_namespace"] == "policy",
            result["auto_materialized_memory_source_candidate_id"].endswith("_policy"),
            result["auto_memory_item_namespace_ids"] == ["policy"],
            result["auto_policy_memory_item_run_ids"] == [auto_run_id],
            result["auto_retrieval_preview_item_count"] == 1,
            result["auto_retrieval_preview_namespace_ids"] == ["policy"],
            len(result["auto_retrieval_preview_selected_ids"]) == 1,
            result["bridge_compile_status"] == "prepared",
            result["bridge_resume_status"] == "completed",
            len(result["bridge_memory_preview_selected_ids"]) == 1,
            result["bridge_detail_memory_preview_selected_ids"] == result["bridge_memory_preview_selected_ids"],
            result["bridge_artifact_contains_memory_item_ids"] is True,
            result["bridge_artifact_contains_memory_brief"] is True,
            result["auto_artifact_contains_domain_pack"] is True,
            result["auto_artifact_contains_goal_prefix"] is True,
            result["auto_failure_reason"] is None,
            result["auto_last_runtime_step"] == "completed",
            result["auto_summary_category"] == "success",
            result["auto_simulation_status"] == "passed",
            result["auto_simulation_policy_id"] == "delivery_consistency_simulation",
            result["auto_recorded_simulation_status"] == "passed",
            result["auto_recorded_simulation_sources"] == ["lifecycle_terminal", "manual_request"],
            result["auto_recorded_simulation_record_count"] == 2,
            result["auto_latest_simulation_record_id"] == auto_recorded_simulation_payload["record_id"],
            result["auto_event_inspection_passed"] is True,
            result["auto_event_closure_state"] == "closed",
            result["auto_audit_closure_state"] == "closed",
            result["auto_inspection_passed"] is True,
            result["auto_inspection_problem_count"] == 0,
            timeline_contains_required_events(result["auto_timeline_events"], AUTO_TIMELINE),
            CLAIM_EVENTS.issubset(set(result["auto_timeline_events"])),
            LEASE_EVENTS.issubset(set(result["auto_timeline_events"])),
            ATTEMPT_EVENTS.issubset(set(result["auto_timeline_events"])),
            result["auto_active_claims"] == [],
            result["auto_latest_claim"] is not None,
            result["auto_latest_claim"]["status"] == "released",
            result["auto_active_worker_leases"] == [],
            result["auto_latest_worker_lease"] is not None,
            result["auto_latest_worker_lease"]["status"] == "released",
            result["auto_claim_statuses"] == ["released"],
            result["auto_attempt_statuses"] == ["superseded", "completed"],
            result["auto_attempt_triggers"] == ["compile", "resume"],
            result["auto_worker_lease_statuses"] == ["released"],
            result["auto_snapshot_stages"] == ["compiled", "completed"],
            result["auto_remaining_retries"] == 1,
            result["human_compile_status"] == "prepared",
            result["human_next_action"] == "resume",
            result["human_waiting_reason"] == "awaiting_runtime_resume",
            result["human_last_runtime_step"] == "compiled",
            result["human_summary_category"] == "pending_work",
            result["human_simulation_status"] == "skipped",
            result["human_simulation_policy_id"] == "research_no_simulation",
            result["human_event_inspection_passed"] is True,
            result["human_event_closure_state"] == "awaiting_review",
            result["human_audit_closure_state"] == "awaiting_review",
            result["human_recoverability_hint"] == "resume_run",
            result["human_inspection_passed"] is True,
            result["human_inspection_problem_count"] == 0,
            result["human_resume_status"] == "awaiting_review",
            result["human_approve_status"] == "completed",
            result["human_handoffs_count"] == 1,
            timeline_contains_required_events(result["human_timeline_events"], HUMAN_TIMELINE),
            CLAIM_EVENTS.issubset(set(result["human_timeline_events"])),
            LEASE_EVENTS.issubset(set(result["human_timeline_events"])),
            ATTEMPT_EVENTS.issubset(set(result["human_timeline_events"])),
            result["human_claim_statuses"] == ["released"],
            result["human_attempt_statuses"] == ["superseded", "completed"],
            result["human_attempt_triggers"] == ["compile", "resume"],
            result["human_worker_lease_statuses"] == ["released"],
            result["human_snapshot_stages"] == ["compiled", "awaiting_review", "completed"],
            result["human_remaining_retries"] == 0,
            result["recommended_resume_status"] == "awaiting_review",
            result["recommended_review_decision"] == "fail",
            result["recommended_review_policy"] == "recommended",
            result["recommended_effective_review_state"] == "human_pending",
            result["recommended_latest_reviewer_type"] == "auto",
            result["recommended_latest_decision"] == "fail",
            result["recommended_approve_status"] == "completed",
            result["mandatory_run_status"] == "awaiting_review",
            result["mandatory_review_decision"] == "pass",
            result["mandatory_review_policy"] == "mandatory",
            result["mandatory_effective_review_state"] == "human_pending",
            result["mandatory_latest_reviewer_type"] == "auto",
            result["mandatory_latest_decision"] == "pass",
            result["mandatory_latest_simulation_record_source"] == "lifecycle_awaiting_review",
            result["mandatory_simulation_sources_before_approve"] == ["lifecycle_awaiting_review"],
            result["mandatory_approve_status"] == "completed",
            result["mandatory_simulation_sources_after_approve"]
            == ["lifecycle_awaiting_review", "lifecycle_terminal"],
            result["noop_compile_status"] == "prepared",
            result["noop_task_kind"] == "noop",
            result["noop_resume_status"] == "awaiting_review",
            result["noop_approve_status"] == "completed",
            result["noop_adapter_name"] == "noop",
            result["noop_artifact_paths_exist"],
            result["repair_plan_action"] == "align_completed_runtime_state",
            result["repair_apply_action"] == "align_completed_runtime_state",
            result["repair_inspection_passed"] is True,
            set(result["artifact_ref_fields"]) == {"path", "sha256", "mtime", "size_bytes"},
            result["artifact_paths_exist"],
            result["cancel_status"] == "cancelled",
        ]
    )
    return result
