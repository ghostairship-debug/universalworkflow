from __future__ import annotations

from typing import Any

from infra.validation.common import *  # noqa: F401,F403

def validate_api_flow(env: dict[str, str], db_path: Path, port: int) -> dict[str, Any]:
    result: dict[str, Any] = {"passed": False}
    env = {
        **env,
        "UAWO_ENABLE_AGENT_LANE": "1",
        "UAWO_ENABLE_MCP_SOURCE": "1",
        "UAWO_ENABLE_SKILL_EXPORT": "1",
    }
    scheduler_cluster_flag_enabled = str(env.get("UAWO_ENABLE_SCHEDULER_AUTHORITY_CLUSTER") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "enabled",
    }
    release_validation_report_path = PROJECT_ROOT / "state" / "offline_validate_release_readiness_api.json"
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
    run_json_command(
        [sys.executable, "-m", "infra.scripts.manage", "--db-path", db_path.as_posix(), "reset-db"],
        env,
    )
    base_url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-m",
            "infra.scripts.manage",
            "--db-path",
            db_path.as_posix(),
            "dev",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_api(base_url)
        presets = http_get_json(f"{base_url}/presets")
        domain_packs = http_get_json(f"{base_url}/domain-packs")
        domain_pack_preview = http_get_json(
            f"{base_url}/domain-packs/resolve?preset_id=feature_delivery&task_kind=shell_exec"
        )
        domain_pack_validation = http_get_json(f"{base_url}/domain-packs/validate")
        capability_routes = http_get_json(f"{base_url}/capability-routes")
        capability_sources = http_get_json(f"{base_url}/capability-sources")
        capability_mcp_profiles = http_get_json(f"{base_url}/capability-sources/mcp-profiles")
        capability_projection = http_get_json(
            f"{base_url}/capability-projections/preview?preset_id=research_spike_reviewable"
        )
        simulation_policies = http_get_json(f"{base_url}/simulation/policies")
        memory_namespaces = http_get_json(f"{base_url}/memory/namespaces")
        governance = http_get_json(f"{base_url}/governance/tech-debt")
        governance_review_policy = http_get_json(f"{base_url}/governance/review-policy")
        governance_domain_packs = http_get_json(f"{base_url}/governance/domain-packs")
        encoded_validation_report_path = urllib.parse.quote(release_validation_report_path.as_posix(), safe="")
        governance_release_readiness = http_get_json(
            f"{base_url}/governance/release-readiness?validation_report_path="
            f"{encoded_validation_report_path}"
        )
        skill_export_root = PROJECT_ROOT / "state" / "offline_validate_skill_export_api"
        skill_export_root.mkdir(parents=True, exist_ok=True)
        encoded_skill_export_root = urllib.parse.quote(skill_export_root.as_posix(), safe="")
        skill_export = http_post_json(
            f"{base_url}/domain-packs/software_delivery_pack/skill-export?output_root={encoded_skill_export_root}"
        )

        auto_run = http_post_json(f"{base_url}/runs", {"goal": "Offline API validation", "preset_id": "feature_delivery"})
        auto_run_id = auto_run["run_id"]
        auto_compile = http_post_json(f"{base_url}/runs/{auto_run_id}/compile")
        auto_detail = http_get_json(f"{base_url}/runs/{auto_run_id}/status-detail")
        auto_inspection = http_get_json(f"{base_url}/runs/{auto_run_id}/inspection")
        auto_handoffs = http_get_json(f"{base_url}/runs/{auto_run_id}/handoffs")
        auto_resume = http_post_json(f"{base_url}/runs/{auto_run_id}/resume")
        auto_summary = http_get_json(f"{base_url}/runs/{auto_run_id}/summary")
        auto_simulation = http_get_json(f"{base_url}/runs/{auto_run_id}/simulation")
        auto_recorded_simulation = http_post_json(f"{base_url}/runs/{auto_run_id}/simulation-records")
        auto_post_record_detail = http_get_json(f"{base_url}/runs/{auto_run_id}/status-detail")
        auto_simulation_records = http_get_json(f"{base_url}/runs/{auto_run_id}/simulation-records")
        auto_memory_candidates = http_get_json(f"{base_url}/runs/{auto_run_id}/memory-candidates")
        auto_selected_memory_candidate = next(item for item in auto_memory_candidates if item["namespace_id"] == "policy")
        auto_materialized_memory_item = http_post_json(
            f"{base_url}/runs/{auto_run_id}/memory-items",
            {"candidate_id": auto_selected_memory_candidate["candidate_id"]},
        )
        auto_memory_items = http_get_json(f"{base_url}/runs/{auto_run_id}/memory-items")
        auto_policy_memory_items = http_get_json(f"{base_url}/memory/items?namespace_id=policy")
        encoded_memory_item_id = urllib.parse.quote(auto_materialized_memory_item["memory_item_id"], safe="")
        auto_retrieval_preview = http_get_json(
            f"{base_url}/memory/retrieval-preview?preset_id=feature_delivery&namespace_id=policy"
            f"&memory_item_id={encoded_memory_item_id}"
        )
        bridge_run = http_post_json(
            f"{base_url}/runs",
            {"goal": "Offline API memory-aware compile", "preset_id": "feature_delivery"},
        )
        bridge_run_id = bridge_run["run_id"]
        bridge_compile = http_post_json(
            f"{base_url}/runs/{bridge_run_id}/compile",
            {"memory_item_ids": [auto_materialized_memory_item["memory_item_id"]]},
        )
        bridge_detail = http_get_json(f"{base_url}/runs/{bridge_run_id}/status-detail")
        bridge_resume = http_post_json(f"{base_url}/runs/{bridge_run_id}/resume")
        bridge_evidence = http_get_json(f"{base_url}/tasks/{bridge_compile['runtime_task_id']}/evidence")
        auto_event_inspection = http_get_json(f"{base_url}/runs/{auto_run_id}/event-inspection")
        auto_audit_report = http_get_json(f"{base_url}/runs/{auto_run_id}/audit-report")
        auto_timeline = http_get_json(f"{base_url}/runs/{auto_run_id}/timeline")
        auto_claims = http_get_json(f"{base_url}/runs/{auto_run_id}/claims")
        auto_leases = http_get_json(f"{base_url}/runs/{auto_run_id}/leases")
        auto_attempts = http_get_json(f"{base_url}/runs/{auto_run_id}/attempts")
        auto_snapshots = http_get_json(f"{base_url}/runs/{auto_run_id}/snapshots")
        auto_budget = http_get_json(f"{base_url}/runs/{auto_run_id}/budget")

        human_run = http_post_json(f"{base_url}/runs", {"goal": "Offline API human validation", "preset_id": "research_spike"})
        human_run_id = human_run["run_id"]
        http_post_json(f"{base_url}/runs/{human_run_id}/compile")
        human_detail = http_get_json(f"{base_url}/runs/{human_run_id}/status-detail")
        human_inspection = http_get_json(f"{base_url}/runs/{human_run_id}/inspection")
        human_resume = http_post_json(f"{base_url}/runs/{human_run_id}/resume")
        human_summary = http_get_json(f"{base_url}/runs/{human_run_id}/summary")
        human_simulation = http_get_json(f"{base_url}/runs/{human_run_id}/simulation")
        human_event_inspection = http_get_json(f"{base_url}/runs/{human_run_id}/event-inspection")
        human_audit_report = http_get_json(f"{base_url}/runs/{human_run_id}/audit-report")
        runs_catalog = http_get_json(f"{base_url}/runs?limit=20")
        pending_reviews = http_get_json(f"{base_url}/reviews/pending")
        operator_view = http_get_json(f"{base_url}/runs/{human_run_id}/operator-view")
        scheduler_cluster = http_get_json(f"{base_url}/scheduler/cluster")
        dashboard_html = http_get_text(f"{base_url}/ui")
        runs_html = http_get_text(f"{base_url}/ui/runs")
        reviews_html = http_get_text(f"{base_url}/ui/reviews")
        governance_html = http_get_text(f"{base_url}/ui/governance")
        config_html = http_get_text(f"{base_url}/ui/config")
        chat_create = http_post_json(
            f"{base_url}/interaction/chat/messages",
            {
                "content": "Build a small artifact for streaming chat validation with visible operator evidence",
                "mode": "llm_assisted",
            },
        )
        chat_session_id = chat_create["session"]["session_id"]
        chat_stream = http_get_text(f"{base_url}/interaction/sessions/{chat_session_id}/stream")
        chat_launch = http_post_json(
            f"{base_url}/interaction/chat/messages",
            {"session_id": chat_session_id, "content": "launch", "mode": "rule_based"},
        )
        chat_resume_gate = http_post_json(
            f"{base_url}/interaction/chat/messages",
            {"session_id": chat_session_id, "content": "resume", "mode": "rule_based"},
        )
        chat_workbench_html = http_get_text(f"{base_url}/ui/workbench?session_id={chat_session_id}")
        human_approve = http_post_json(f"{base_url}/runs/{human_run_id}/approve")
        human_claims = http_get_json(f"{base_url}/runs/{human_run_id}/claims")
        human_leases = http_get_json(f"{base_url}/runs/{human_run_id}/leases")
        human_attempts = http_get_json(f"{base_url}/runs/{human_run_id}/attempts")
        human_snapshots = http_get_json(f"{base_url}/runs/{human_run_id}/snapshots")
        human_budget = http_get_json(f"{base_url}/runs/{human_run_id}/budget")
        human_timeline = http_get_json(f"{base_url}/runs/{human_run_id}/timeline")

        recommended_run = http_post_json(
            f"{base_url}/runs",
            {"goal": "Offline API recommended validation", "preset_id": "advisory_delivery"},
        )
        recommended_run_id = recommended_run["run_id"]
        recommended_compile = http_post_json(f"{base_url}/runs/{recommended_run_id}/compile")
        mutate_task_packet_command(
            db_path,
            recommended_compile["runtime_task_id"],
            ["python", "-c", "import sys; sys.exit(2)"],
        )
        recommended_resume = http_post_json(f"{base_url}/runs/{recommended_run_id}/resume")
        recommended_detail = http_get_json(f"{base_url}/runs/{recommended_run_id}/status-detail")
        recommended_approve = http_post_json(f"{base_url}/runs/{recommended_run_id}/approve")

        mandatory_run = http_post_json(
            f"{base_url}/runs",
            {"goal": "Offline API mandatory validation", "preset_id": "guarded_delivery"},
        )
        mandatory_run_id = mandatory_run["run_id"]
        http_post_json(f"{base_url}/runs/{mandatory_run_id}/compile")
        mandatory_resume = http_post_json(f"{base_url}/runs/{mandatory_run_id}/resume")
        mandatory_detail = http_get_json(f"{base_url}/runs/{mandatory_run_id}/status-detail")
        mandatory_simulations_before_approve = http_get_json(f"{base_url}/runs/{mandatory_run_id}/simulation-records")
        mandatory_approve = http_post_json(f"{base_url}/runs/{mandatory_run_id}/approve")
        mandatory_simulations_after_approve = http_get_json(f"{base_url}/runs/{mandatory_run_id}/simulation-records")

        noop_run = http_post_json(f"{base_url}/runs", {"goal": "Offline API noop validation", "preset_id": "research_spike"})
        noop_run_id = noop_run["run_id"]
        noop_compile = http_post_json(f"{base_url}/runs/{noop_run_id}/compile", {"task_kind": "noop"})
        noop_detail = http_get_json(f"{base_url}/runs/{noop_run_id}/status-detail")
        noop_runtime_task_id = noop_detail["runtime_tasks"][0]["runtime_task_id"]
        noop_resume = http_post_json(f"{base_url}/runs/{noop_run_id}/resume")
        noop_evidence = http_get_json(f"{base_url}/tasks/{noop_runtime_task_id}/evidence")
        noop_approve = http_post_json(f"{base_url}/runs/{noop_run_id}/approve")

        repair_run = http_post_json(f"{base_url}/runs", {"goal": "Offline API repair validation", "preset_id": "feature_delivery"})
        repair_run_id = repair_run["run_id"]
        http_post_json(f"{base_url}/runs/{repair_run_id}/compile")
        http_post_json(f"{base_url}/runs/{repair_run_id}/resume")
        corrupt_runtime_state_for_run(
            db_path,
            repair_run_id,
            graph_step="awaiting_review",
            is_terminal=False,
            extra_payload={"corrupted": True},
        )
        repair_plan = http_post_json(f"{base_url}/runs/{repair_run_id}/reconcile")
        repair_apply = http_post_json(f"{base_url}/runs/{repair_run_id}/reconcile", {"apply": True})
        repair_inspection = http_get_json(f"{base_url}/runs/{repair_run_id}/inspection")

        auto_timeline_events = [item["event_type"] for item in auto_timeline]
        human_timeline_events = [item["event_type"] for item in human_timeline]
        bridge_artifact_refs = bridge_evidence.get("artifact_refs", [])
        bridge_artifact_text = (
            Path(bridge_artifact_refs[0]["path"]).read_text(encoding="utf-8")
            if bridge_artifact_refs and Path(bridge_artifact_refs[0]["path"]).exists()
            else ""
        )
        result.update(
            {
                "preset_ids": [item["preset_id"] for item in presets],
                "domain_pack_ids": [item["domain_pack_id"] for item in domain_packs],
                "domain_pack_preview_id": (
                    domain_pack_preview.get("domain_pack", {}).get("domain_pack_id")
                    if domain_pack_preview.get("resolved")
                    else None
                ),
                "domain_pack_preview_adapter": domain_pack_preview.get("capability_resolution", {}).get("adapter_name"),
                "domain_pack_validation_passed": domain_pack_validation.get("passed"),
                "domain_pack_validation_issue_count": domain_pack_validation.get("issue_count"),
                "memory_namespace_ids": [item["namespace_id"] for item in memory_namespaces],
                "capability_routes": capability_routes,
                "m8_capability_source_types": [item["source_type"] for item in capability_sources],
                "m8_mcp_profile_id": capability_mcp_profiles[0]["profile_id"] if capability_mcp_profiles else None,
                "m8_projection_lane": capability_projection["execution_lane"],
                "m8_projection_adapter": capability_projection["capability_resolution"]["adapter_name"],
                "m8_projection_tool_names": [
                    item["tool_name"] for item in capability_projection["tool_projection_manifest"]["tools"]
                ],
                "m8_projection_canonical_tool_ids": [
                    item["canonical_tool_id"] for item in capability_projection["tool_projection_manifest"]["tools"]
                ],
                "m8_projection_trust_tiers": capability_projection["tool_projection_manifest"]["trust_tiers"],
                "m8_skill_export_domain_pack_id": skill_export["domain_pack_id"],
                "m8_skill_export_bundle_has_readme": (Path(skill_export["bundle_path"]) / "README.md").exists(),
                "m8_skill_export_bundle_has_manifest": (Path(skill_export["bundle_path"]) / "skill.json").exists(),
                "simulation_policy_ids": [item["policy_id"] for item in simulation_policies],
                "governance_open_debt_count": governance["open_debt_count"],
                "governance_active_gate_focus_ids": [item["debt_id"] for item in governance["active_gate_focus_items"]],
                "governance_supported_review_policies": [
                    item["policy"] for item in governance_review_policy["supported_policies"]
                ],
                "governance_review_policy_debt_id": (
                    governance_review_policy["debt_linkage"]["debt_id"]
                    if governance_review_policy["debt_linkage"] is not None
                    else None
                ),
                "governance_release_ready": governance_release_readiness["overall_ready"],
                "governance_release_domain_pack_ids": [
                    item["domain_pack_id"] for item in governance_release_readiness["domain_packs"]
                ],
                "governance_domain_pack_platformized": governance_domain_packs["overall_platformized"],
                "scheduler_cluster_enabled": scheduler_cluster.get("enabled", True),
                "scheduler_cluster_mode": scheduler_cluster["mode"],
                "scheduler_cluster_leader": scheduler_cluster["leader_node_id"],
                "scheduler_cluster_quorum_size": scheduler_cluster["quorum_size"],
                "auto_run_status": auto_resume["run"]["status"],
                "auto_compile_status": auto_compile["run"]["status"],
                "auto_domain_pack_id": auto_detail["domain_pack"]["domain_pack_id"],
                "auto_capability_adapter": auto_detail["capability_resolution"]["adapter_name"],
                "auto_memory_namespace_ids": [item["namespace_id"] for item in auto_memory_candidates],
                "auto_materialized_memory_namespace": auto_materialized_memory_item["namespace_id"],
                "auto_materialized_memory_source_candidate_id": auto_materialized_memory_item["source_candidate_id"],
                "auto_memory_item_namespace_ids": [item["namespace_id"] for item in auto_memory_items],
                "auto_policy_memory_item_run_ids": [item["run_id"] for item in auto_policy_memory_items],
                "auto_retrieval_preview_item_count": auto_retrieval_preview["item_count"],
                "auto_retrieval_preview_namespace_ids": auto_retrieval_preview["namespace_ids"],
                "auto_retrieval_preview_selected_ids": auto_retrieval_preview["selected_memory_item_ids"],
                "bridge_compile_status": bridge_compile["run"]["status"],
                "bridge_resume_status": bridge_resume["run"]["status"],
                "bridge_memory_preview_selected_ids": bridge_compile["memory_preview"]["selected_memory_item_ids"],
                "bridge_detail_memory_preview_selected_ids": bridge_detail["memory_retrieval_preview"][
                    "selected_memory_item_ids"
                ],
                "bridge_artifact_contains_memory_item_ids": "memory_item_ids:" in bridge_artifact_text,
                "bridge_artifact_contains_memory_brief": "memory_brief:" in bridge_artifact_text,
                "auto_next_action": auto_detail["next_action"],
                "auto_waiting_reason": auto_detail["waiting_reason"],
                "auto_last_runtime_step": auto_detail["last_runtime_state"]["graph_step"],
                "auto_summary_category": auto_summary["failure_taxonomy"]["category"],
                "auto_simulation_status": auto_simulation["status"],
                "auto_simulation_policy_id": auto_simulation["policy_id"],
                "auto_recorded_simulation_status": auto_recorded_simulation["status"],
                "auto_recorded_simulation_sources": [item["recorded_from"] for item in auto_simulation_records],
                "auto_recorded_simulation_record_count": len(auto_simulation_records),
                "auto_latest_simulation_record_id": (auto_post_record_detail.get("latest_simulation_record") or {}).get(
                    "record_id"
                ),
                "auto_event_inspection_passed": auto_event_inspection["closure_audit"]["passed"],
                "auto_event_closure_state": auto_event_inspection["closure_audit"]["state"],
                "auto_audit_closure_state": auto_audit_report["review_packet"]["closure_summary"]["state"],
                "auto_inspection_passed": auto_inspection["passed"],
                "auto_inspection_problem_count": auto_inspection["problem_count"],
                "auto_handoffs_count": len(auto_handoffs),
                "auto_timeline_events": auto_timeline_events,
                "auto_active_claims": auto_detail.get("active_claims", []),
                "auto_active_worker_leases": auto_detail.get("active_worker_leases", []),
                "auto_claim_statuses": [item["status"] for item in auto_claims],
                "auto_attempt_statuses": [item["status"] for item in auto_attempts],
                "auto_attempt_triggers": [item["trigger"] for item in auto_attempts],
                "auto_worker_lease_statuses": [item["status"] for item in auto_leases],
                "auto_snapshot_stages": [item["stage"] for item in auto_snapshots],
                "auto_remaining_retries": auto_budget["budget_projection"]["remaining_retries"],
                "human_waiting_reason": human_detail["waiting_reason"],
                "human_last_runtime_step": human_detail["last_runtime_state"]["graph_step"],
                "human_summary_category": human_summary["failure_taxonomy"]["category"],
                "human_simulation_status": human_simulation["status"],
                "human_simulation_policy_id": human_simulation["policy_id"],
                "human_event_inspection_passed": human_event_inspection["closure_audit"]["passed"],
                "human_event_closure_state": human_event_inspection["closure_audit"]["state"],
                "human_audit_closure_state": human_audit_report["review_packet"]["closure_summary"]["state"],
                "operator_runs_count": len(runs_catalog),
                "pending_review_run_ids": [item["run"]["run_id"] for item in pending_reviews],
                "operator_view_run_id": operator_view["run"]["run_id"],
                "dashboard_html_ok": "操作台总览" in dashboard_html,
                "runs_html_ok": "运行目录" in runs_html,
                "reviews_html_ok": "待审查控制台" in reviews_html,
                "governance_html_ok": "治理" in governance_html,
                "dashboard_html_contains_cluster": "调度权威拓扑" in dashboard_html,
                "governance_html_contains_cluster": "调度权威拓扑" in governance_html,
                "dashboard_html_has_local_only_banner": (
                    "调度权威集群已关闭，当前为本地单机模式。" in dashboard_html
                ),
                "governance_html_has_local_only_banner": (
                    "调度权威集群已关闭，当前为本地单机模式。" in governance_html
                ),
                "config_html_ok": "有效配置" in config_html,
                "chat_message_roles": [item["role"] for item in chat_create["chat_messages"]],
                "chat_stream_has_user_message": "event: user_message" in chat_stream,
                "chat_stream_has_assistant_delta": "event: assistant_delta" in chat_stream,
                "chat_stream_has_assistant_final": "event: assistant_final" in chat_stream,
                "chat_stream_has_status_patch": "event: status_patch" in chat_stream,
                "chat_stream_has_heartbeat": "event: heartbeat" in chat_stream,
                "chat_launch_action_type": chat_launch["action_result"]["action_type"],
                "chat_launch_active_run_id": chat_launch["session"]["active_run_id"],
                "chat_resume_pending_action_type": chat_resume_gate["pending_confirmation"]["action_type"],
                "chat_resume_pending_status": chat_resume_gate["pending_confirmation"]["status"],
                "chat_workbench_html_ok": "流式聊天工作台" in chat_workbench_html,
                "chat_workbench_has_eventsource": "EventSource" in chat_workbench_html,
                "human_recoverability_hint": human_detail["recoverability_hint"],
                "human_inspection_passed": human_inspection["passed"],
                "human_inspection_problem_count": human_inspection["problem_count"],
                "human_resume_status": human_resume["run"]["status"],
                "human_approve_status": human_approve["run"]["status"],
                "human_timeline_events": human_timeline_events,
                "human_claim_statuses": [item["status"] for item in human_claims],
                "human_attempt_statuses": [item["status"] for item in human_attempts],
                "human_attempt_triggers": [item["trigger"] for item in human_attempts],
                "human_worker_lease_statuses": [item["status"] for item in human_leases],
                "human_snapshot_stages": [item["stage"] for item in human_snapshots],
                "human_remaining_retries": human_budget["budget_projection"]["remaining_retries"],
                "recommended_resume_status": recommended_resume["run"]["status"],
                "recommended_review_decision": recommended_resume["review_decision"],
                "recommended_review_policy": recommended_detail["review_policy"],
                "recommended_effective_review_state": recommended_detail["effective_review_state"],
                "recommended_latest_reviewer_type": recommended_detail["latest_review_verdict"]["reviewer_type"],
                "recommended_latest_decision": recommended_detail["latest_review_verdict"]["decision"],
                "recommended_approve_status": recommended_approve["run"]["status"],
                "mandatory_resume_status": mandatory_resume["run"]["status"],
                "mandatory_review_decision": mandatory_resume["review_decision"],
                "mandatory_review_policy": mandatory_detail["review_policy"],
                "mandatory_effective_review_state": mandatory_detail["effective_review_state"],
                "mandatory_latest_reviewer_type": mandatory_detail["latest_review_verdict"]["reviewer_type"],
                "mandatory_latest_decision": mandatory_detail["latest_review_verdict"]["decision"],
                "mandatory_latest_simulation_record_source": (
                    mandatory_detail.get("latest_simulation_record") or {}
                ).get("recorded_from"),
                "mandatory_simulation_sources_before_approve": [
                    item["recorded_from"] for item in mandatory_simulations_before_approve
                ],
                "mandatory_approve_status": mandatory_approve["run"]["status"],
                "mandatory_simulation_sources_after_approve": [
                    item["recorded_from"] for item in mandatory_simulations_after_approve
                ],
                "noop_compile_status": noop_compile["run"]["status"],
                "noop_task_kind": noop_detail["runtime_tasks"][0]["task_kind"],
                "noop_resume_status": noop_resume["run"]["status"],
                "noop_approve_status": noop_approve["run"]["status"],
                "noop_adapter_name": noop_evidence.get("raw_execution", {}).get("adapter_name"),
                "repair_plan_action": repair_plan["problems"][0]["repair_action"],
                "repair_apply_action": repair_apply["action"],
                "repair_inspection_passed": repair_inspection["passed"],
            }
        )
        result["passed"] = all(
            [
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
                    {"capability": "shell_exec", "adapter_name": "codex", "adapter_class": "CodexAdapter"},
                    {"capability": "shell_exec", "adapter_name": "claude_architect", "adapter_class": "ClaudeArchitectAdapter"},
                    {"capability": "shell_exec", "adapter_name": "mmx_multimodal", "adapter_class": "MMXMultimodalAdapter"},
                    {"capability": "shell_exec", "adapter_name": "vertex_multimodal", "adapter_class": "VertexMultimodalAdapter"},
                    {"capability": "shell_exec", "adapter_name": "opencode", "adapter_class": "OpenCodeAdapter"},
                ],
                result["m8_capability_source_types"] == ["built_in", "mcp_stdio", "mcp_stdio"],
                result["m8_mcp_profile_id"] == "local_workspace_readonly",
                result["m8_projection_lane"] == "standard_agent",
                result["m8_projection_adapter"] == "agent",
                "mcp_list_workspace_files" in result["m8_projection_tool_names"],
                "mcp_read_workspace_text" in result["m8_projection_tool_names"],
                "mcp:local_workspace_readonly:mcp_list_workspace_files" in result["m8_projection_canonical_tool_ids"],
                "web_search" in result["m8_projection_tool_names"],
                "understand_image" in result["m8_projection_tool_names"],
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
                isinstance(result["governance_open_debt_count"], int),
                isinstance(result["governance_active_gate_focus_ids"], list),
                result["governance_supported_review_policies"]
                == ["auto_only", "optional", "recommended", "human_required", "mandatory"],
                result["governance_review_policy_debt_id"] == "TD-006",
                isinstance(result["governance_release_ready"], bool),
                result["governance_release_domain_pack_ids"] == ["software_delivery_pack"],
                result["governance_domain_pack_platformized"] is True,
                result["auto_compile_status"] == "prepared",
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
                result["auto_next_action"] == "resume",
                result["auto_waiting_reason"] == "awaiting_runtime_resume",
                result["auto_last_runtime_step"] == "compiled",
                result["auto_summary_category"] == "success",
                result["auto_simulation_status"] == "passed",
                result["auto_simulation_policy_id"] == "delivery_consistency_simulation",
                result["auto_recorded_simulation_status"] == "passed",
                result["auto_recorded_simulation_sources"] == ["lifecycle_terminal", "manual_request"],
                result["auto_recorded_simulation_record_count"] == 2,
                result["auto_latest_simulation_record_id"] == auto_recorded_simulation["record_id"],
                result["auto_event_inspection_passed"] is True,
                result["auto_event_closure_state"] == "closed",
                result["auto_audit_closure_state"] == "closed",
                result["auto_inspection_passed"] is True,
                result["auto_inspection_problem_count"] == 0,
                result["auto_handoffs_count"] == 1,
                result["auto_run_status"] == "completed",
                timeline_contains_required_events(result["auto_timeline_events"], AUTO_TIMELINE),
                CLAIM_EVENTS.issubset(set(result["auto_timeline_events"])),
                LEASE_EVENTS.issubset(set(result["auto_timeline_events"])),
                ATTEMPT_EVENTS.issubset(set(result["auto_timeline_events"])),
                result["auto_active_claims"] == [],
                result["auto_active_worker_leases"] == [],
                result["auto_claim_statuses"] == ["released"],
                result["auto_attempt_statuses"] == ["superseded", "completed"],
                result["auto_attempt_triggers"] == ["compile", "resume"],
                result["auto_worker_lease_statuses"] == ["released"],
                result["auto_snapshot_stages"] == ["compiled", "completed"],
                result["auto_remaining_retries"] == 1,
                result["human_waiting_reason"] == "awaiting_runtime_resume",
                result["human_last_runtime_step"] == "compiled",
                result["human_summary_category"] == "review_pending",
                result["human_simulation_status"] == "skipped",
                result["human_simulation_policy_id"] == "research_no_simulation",
                result["human_event_inspection_passed"] is True,
                result["human_event_closure_state"] == "awaiting_review",
                result["human_audit_closure_state"] == "awaiting_review",
                result["operator_runs_count"] >= 2,
                human_run_id in result["pending_review_run_ids"],
                result["operator_view_run_id"] == human_run_id,
                (
                    result["scheduler_cluster_enabled"] is True
                    and result["scheduler_cluster_mode"] == "quorum"
                    and result["scheduler_cluster_leader"] is not None
                    and result["scheduler_cluster_quorum_size"] >= 1
                    and result["dashboard_html_has_local_only_banner"] is False
                    and result["governance_html_has_local_only_banner"] is False
                )
                if scheduler_cluster_flag_enabled
                else (
                    result["scheduler_cluster_enabled"] is False
                    and result["scheduler_cluster_mode"] == "local_only"
                    and result["scheduler_cluster_leader"] is not None
                    and result["scheduler_cluster_quorum_size"] == 1
                    and result["dashboard_html_has_local_only_banner"] is True
                    and result["governance_html_has_local_only_banner"] is True
                ),
                result["dashboard_html_ok"] is True,
                result["runs_html_ok"] is True,
                result["reviews_html_ok"] is True,
                result["governance_html_ok"] is True,
                result["dashboard_html_contains_cluster"] is True,
                result["governance_html_contains_cluster"] is True,
                result["config_html_ok"] is True,
                result["chat_message_roles"] == ["user", "assistant"],
                result["chat_stream_has_user_message"] is True,
                result["chat_stream_has_assistant_delta"] is True,
                result["chat_stream_has_assistant_final"] is True,
                result["chat_stream_has_status_patch"] is True,
                result["chat_stream_has_heartbeat"] is True,
                result["chat_launch_action_type"] == "launch_prepare",
                isinstance(result["chat_launch_active_run_id"], str),
                result["chat_resume_pending_action_type"] == "resume_run",
                result["chat_resume_pending_status"] == "pending_confirmation",
                result["chat_workbench_html_ok"] is True,
                result["chat_workbench_has_eventsource"] is True,
                result["human_recoverability_hint"] == "resume_run",
                result["human_inspection_passed"] is True,
                result["human_inspection_problem_count"] == 0,
                result["human_resume_status"] == "awaiting_review",
                result["human_approve_status"] == "completed",
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
                result["mandatory_resume_status"] == "awaiting_review",
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
                result["repair_plan_action"] == "align_completed_runtime_state",
                result["repair_apply_action"] == "align_completed_runtime_state",
                result["repair_inspection_passed"] is True,
            ]
        )
        return result
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
