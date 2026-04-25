from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from apps.orchestrator_api.main import create_app
from packages.contracts import RunEventType, RuntimeClaim, RuntimeGateway, RuntimeGraphStep, RuntimeStateRef, WorkerLease
from packages.core_domain.db import unit_of_work
from packages.core_domain.db import migrate
from packages.core_domain.repositories import PresetRepository
from packages.core_domain.services import OrchestratorService
from packages.runtime_langgraph.chat_runtime import ChatActionDecision, ChatLLMRuntime, DegradedChatLLMRuntime
from packages.runtime_langgraph.gateway import OpenAIRuntimeGateway
from packages.worker_adapters.base import ExecutionResult, resolve_artifact_paths, utc_now
from packages.worker_adapters.codex_adapter import CodexAdapter
from packages.worker_adapters.langchain_agent_adapter import LangChainAgentAdapter
from packages.worker_adapters.opencode_adapter import OpenCodeAdapter
from packages.worker_adapters.opencode_session_adapter import OpenCodeSessionAdapter
from conftest import ReceiptAwareTestClient


pytestmark = pytest.mark.slow

class _FakeApiGatewayResponse:
    id = "resp_api"
    output_text = "Outcome: produce artifact Risk: command drift Check: review artifact file"


class _FakeApiResponses:
    def create(self, **kwargs):
        return _FakeApiGatewayResponse()


class _FakeApiClient:
    def __init__(self):
        self.responses = _FakeApiResponses()


OPEN_DEBT_IDS: list[str] = []

AVAILABLE_SHELL_EXEC_ADAPTERS = [
    "shell",
    "codex",
    "claude_architect",
    "mmx_multimodal",
    "vertex_multimodal",
    "opencode",
]


def build_client(
    db_path: Path,
    runtime_gateway: RuntimeGateway | None = None,
    chat_llm_runtime: ChatLLMRuntime | None = None,
) -> ReceiptAwareTestClient:
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    return ReceiptAwareTestClient(
        create_app(
            db_path,
            runtime_gateway=runtime_gateway,
            chat_llm_runtime=chat_llm_runtime or DegradedChatLLMRuntime(),
        )
    )


def _fake_api_patch_launch(self, packet):  # type: ignore[override]
    started_at = utc_now()
    artifact_path = Path(packet.expected_artifacts[0])
    if not artifact_path.is_absolute():
        artifact_path = Path(packet.working_directory) / artifact_path
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    patch_text = (
        "--- api_target.txt\n"
        "+++ api_target.txt\n"
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


class _SwitchingChatRuntime(DegradedChatLLMRuntime):
    def infer_action(self, content: str, context: dict) -> ChatActionDecision:
        if "launch" in content.lower() or "启动" in content or "新计划" in content:
            return ChatActionDecision(action_type="launch_prepare", confidence=0.9, rationale="test launch")
        return ChatActionDecision(action_type="answer_only", confidence=0.9, rationale="test answer")

    def stream_reply(self, **kwargs):
        yield "测试回复"


def _fake_api_session_launch(self, packet):  # type: ignore[override]
    started_at = utc_now()
    artifact_path = Path(packet.expected_artifacts[0])
    if not artifact_path.is_absolute():
        artifact_path = Path(packet.working_directory) / artifact_path
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("# Sessionful external lane\n", encoding="utf-8")
    export_path = Path(packet.working_directory) / "state" / "sessions" / f"{packet.runtime_task_id}_sess_api_123.json"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text('{"session_id":"sess_api_123"}', encoding="utf-8")
    finished_at = utc_now()
    return ExecutionResult(
        runtime_task_id=packet.runtime_task_id,
        return_code=0,
        stdout="sessionful api output",
        stderr="",
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=max(int((finished_at - started_at).total_seconds() * 1000), 0),
        artifact_paths=[artifact_path.resolve().as_posix(), export_path.resolve().as_posix()],
        adapter_name=self.normalized_name(),
        metadata={
            "mutation_mode": "artifact_only",
            "external_session_id": "sess_api_123",
            "external_session_url": "https://example.com/sessions/api-123",
            "session_export_ref": export_path.resolve().as_posix(),
            "external_trace_id": "trace_api_session_123",
        },
    )


def _fake_api_external_launch(self, packet):  # type: ignore[override]
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
        "optional_delivery",
        "research_spike",
        "research_spike_reviewable",
        "advisory_delivery",
        "guarded_delivery",
        "project_delivery",
        "guarded_project_delivery",
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
        {"capability": "shell_exec", "adapter_name": "codex", "adapter_class": "CodexAdapter"},
        {"capability": "shell_exec", "adapter_name": "claude_architect", "adapter_class": "ClaudeArchitectAdapter"},
        {"capability": "shell_exec", "adapter_name": "mmx_multimodal", "adapter_class": "MMXMultimodalAdapter"},
        {"capability": "shell_exec", "adapter_name": "vertex_multimodal", "adapter_class": "VertexMultimodalAdapter"},
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


def test_api_exposes_m8_capability_sources_and_projection_preview(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UAWO_ENABLE_AGENT_LANE", "1")
    monkeypatch.setenv("UAWO_ENABLE_MCP_SOURCE", "1")
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    sources_response = client.get("/capability-sources")
    profiles_response = client.get("/capability-sources/mcp-profiles")
    projection_response = client.get(
        "/capability-projections/preview",
        params={"preset_id": "research_spike_reviewable"},
    )

    assert sources_response.status_code == 200
    assert any(item["source_type"] == "built_in" for item in sources_response.json())
    assert any(item["source_type"] == "mcp_stdio" for item in sources_response.json())
    assert profiles_response.status_code == 200
    assert profiles_response.json()[0]["profile_id"] == "local_workspace_readonly"
    assert projection_response.status_code == 200
    assert projection_response.json()["execution_lane"] == "standard_agent"
    assert projection_response.json()["capability_resolution"]["adapter_name"] == "agent"
    assert projection_response.json()["resolved_execution"]["adapter_name"] == "agent"
    assert projection_response.json()["execution_resolution_trace"]["source_map"]["adapter_name"]["scope"] == "preset"
    tools = projection_response.json()["tool_projection_manifest"]["tools"]
    tool_names = [item["tool_name"] for item in tools]
    canonical_tool_ids = [item["canonical_tool_id"] for item in tools]
    assert "mcp_list_workspace_files" in tool_names
    assert "mcp:local_workspace_readonly:mcp_list_workspace_files" in canonical_tool_ids
    assert all(item["raw_tool_name"] for item in tools)
    assert all(item["display_name"] for item in tools)


def test_api_can_create_get_and_launch_interaction_session(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    profiles_response = client.get("/interaction/agent-profiles")
    registry_response = client.get("/interaction/agent-profiles/registry")
    clusters_response = client.get("/interaction/clusters/templates")
    empty_sessions_response = client.get("/interaction/sessions")
    create_response = client.post(
        "/interaction/sessions",
        json={
            "goal": "Coordinate a multi-role project delivery slice",
            "preferred_preset_id": "project_delivery",
            "preferred_cluster_template_ids": ["dev_cluster"],
            "constraints": ["keep operator checkpoints visible"],
            "assumptions": ["workspace is clean"],
            "referenced_artifact_paths": ["docs/current_development_workflow.md"],
            "followup_context": ["prior review asked for a launch checkpoint"],
        },
    )

    assert profiles_response.status_code == 200
    assert registry_response.status_code == 200
    assert clusters_response.status_code == 200
    assert empty_sessions_response.status_code == 200
    assert empty_sessions_response.json() == []
    assert any(profile["profile_id"] == "planner_architect" for profile in profiles_response.json())
    assert registry_response.json()["generated_profiles"] == []
    assert clusters_response.json()[0]["template_id"] == "dev_cluster"

    create_payload = create_response.json()
    session_id = create_payload["session"]["session_id"]
    assert create_response.status_code == 201
    assert create_payload["session"]["status"] == "ready_to_launch"
    assert create_payload["plan_draft"]["selected_preset_id"] == "project_delivery"
    assert create_payload["plan_draft"]["selected_cluster_template_ids"] == ["dev_cluster"]
    assert create_payload["goal_packet"]["selected_clusters"][0]["template_id"] == "dev_cluster"
    assert create_payload["session"]["intent_packet"]["constraints"] == ["keep operator checkpoints visible"]
    assert create_payload["session"]["intent_packet"]["assumptions"] == ["workspace is clean"]
    assert create_payload["session"]["intent_packet"]["referenced_artifact_paths"] == ["docs/current_development_workflow.md"]
    assert create_payload["session"]["intent_packet"]["followup_context"] == ["prior review asked for a launch checkpoint"]
    assert create_payload["followup_requests"] == []
    assert create_payload["active_run_operator_view"] is None

    get_response = client.get(f"/interaction/sessions/{session_id}")
    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["session"]["latest_plan_draft_id"] == create_payload["plan_draft"]["draft_id"]
    assert get_payload["available_cluster_templates"][0]["template_id"] == "dev_cluster"
    assert get_payload["followup_requests"] == []
    assert get_payload["active_run_operator_view"] is None

    sessions_response = client.get("/interaction/sessions")
    assert sessions_response.status_code == 200
    assert [item["session_id"] for item in sessions_response.json()] == [session_id]

    launch_response = client.post(
        f"/interaction/sessions/{session_id}/launch",
        json={
            "execute": False,
            "rationale": "ready to launch",
            "selected_preset_id": "project_delivery",
            "selected_cluster_template_ids": ["dev_cluster"],
        },
    )
    assert launch_response.status_code == 200
    launch_payload = launch_response.json()
    assert launch_payload["session"]["status"] == "launched"
    assert launch_payload["session"]["active_run_id"] == launch_payload["launch_payload"]["run"]["run_id"]
    assert launch_payload["launch_decision"]["selected_cluster_template_ids"] == ["dev_cluster"]
    assert launch_payload["launch_payload"]["selected_clusters"][0]["template_id"] == "dev_cluster"
    assert launch_payload["launch_payload"]["cluster_policy_preview"]["selected_cluster_template_ids"] == ["dev_cluster"]
    assert launch_payload["launch_payload"]["run"]["status"] == "prepared"
    assert launch_payload["active_run_operator_view"]["run"]["run_id"] == launch_payload["launch_payload"]["run"]["run_id"]
    assert launch_payload["active_run_operator_view"]["status_detail"]["next_action"] in {"resume_run", "start_execution", "resume"}
    assert any(item["trigger"] == "review_gate" for item in launch_payload["automation_watchdogs"])
    assert any(item["action_type"] == "monitor_run" for item in launch_payload["automation_evaluation"]["actions"])

    generate_profiles_response = client.post(f"/interaction/sessions/{session_id}/generated-profiles")
    assert generate_profiles_response.status_code == 201
    generate_profiles_payload = generate_profiles_response.json()
    assert len(generate_profiles_payload["generated_profiles"]) >= 1
    assert any(item["cluster_template_id"] == "dev_cluster" for item in generate_profiles_payload["generated_profiles"])

    generated_profiles_response = client.get(
        "/interaction/generated-profiles",
        params={"session_id": session_id},
    )
    assert generated_profiles_response.status_code == 200
    assert len(generated_profiles_response.json()) >= 1

    registry_after_generation = client.get("/interaction/agent-profiles/registry")
    assert registry_after_generation.status_code == 200
    assert len(registry_after_generation.json()["generated_profiles"]) >= 1

    followup_response = client.post(
        f"/interaction/sessions/{session_id}/followups",
        json={
            "instruction": "Prepare the approval checkpoint after the implementation run completes.",
            "intent": "review_gate",
            "blocking": True,
        },
    )
    assert followup_response.status_code == 201
    followup_payload = followup_response.json()
    assert followup_payload["followup_request"]["instruction"].startswith("Prepare the approval checkpoint")
    assert len(followup_payload["followup_requests"]) == 1
    assert followup_payload["followup_requests"][0]["blocking"] is True
    assert followup_payload["active_run_operator_view"]["run"]["run_id"] == launch_payload["launch_payload"]["run"]["run_id"]
    assert {item["trigger"] for item in followup_payload["automation_watchdogs"]} >= {"review_gate", "followup_pending"}
    assert any(item["action_type"] == "wait_for_run_checkpoint" for item in followup_payload["automation_evaluation"]["actions"])

    followup_list_response = client.get(f"/interaction/sessions/{session_id}/followups")
    assert followup_list_response.status_code == 200
    assert len(followup_list_response.json()) == 1
    assert followup_list_response.json()[0]["intent"] == "review_gate"

    watchdog_list_response = client.get(f"/interaction/sessions/{session_id}/watchdogs")
    assert watchdog_list_response.status_code == 200
    assert {item["trigger"] for item in watchdog_list_response.json()} >= {"review_gate", "followup_pending"}

    watchdog_eval_response = client.get("/interaction/watchdogs/evaluate", params={"session_id": session_id})
    assert watchdog_eval_response.status_code == 200
    assert len(watchdog_eval_response.json()["actions"]) >= 1


def test_api_chat_messages_stream_and_confirmation_gate(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    chinese_create_response = client.post(
        "/interaction/chat/messages",
        json={"content": "为当前项目创建一个测试聊天功能的计划预览，产出一份简短说明文档"},
    )
    assert chinese_create_response.status_code == 201
    chinese_create_payload = chinese_create_response.json()
    assert chinese_create_payload["session"]["status"] == "ready_to_launch"
    assert chinese_create_payload["plan_draft"] is not None
    assert chinese_create_payload["chat_messages"][1]["action_type"] == "plan_preview"

    create_response = client.post(
        "/interaction/chat/messages",
        json={"content": "Build a small artifact for chat smoke test with visible operator evidence"},
    )
    assert create_response.status_code == 201
    create_payload = create_response.json()
    session_id = create_payload["session"]["session_id"]
    assert [item["role"] for item in create_payload["chat_messages"]] == ["user", "assistant"]
    assert create_payload["chat_messages"][1]["message_type"] == "text"
    assert create_payload["chat_messages"][1]["stream_status"] == "completed"
    create_stream_event_types = [item["event_type"] for item in create_payload["chat_stream_events"]]
    assert "user_message" in create_stream_event_types
    assert "graph_update" in create_stream_event_types
    assert "tool_action_proposed" in create_stream_event_types

    stream_response = client.get(f"/interaction/sessions/{session_id}/stream")
    assert stream_response.status_code == 200
    assert "event: user_message" in stream_response.text
    assert "event: assistant_delta" in stream_response.text
    assert "event: assistant_final" in stream_response.text
    assert "event: status_patch" in stream_response.text
    assert "event: heartbeat" in stream_response.text
    assert "event: session_update" not in stream_response.text

    last_stream_event_id = create_payload["chat_stream_events"][-1]["event_id"]
    reconnect_response = client.get(
        f"/interaction/sessions/{session_id}/stream",
        params={"after_event_id": last_stream_event_id},
    )
    assert reconnect_response.status_code == 200
    assert "event: user_message" not in reconnect_response.text
    assert "event: assistant_final" not in reconnect_response.text
    assert "event: heartbeat" in reconnect_response.text

    status_cursor_response = client.get(
        f"/interaction/sessions/{session_id}/stream",
        params={"after_event_id": f"heartbeat:{session_id}"},
    )
    assert status_cursor_response.status_code == 200
    assert "event: user_message" not in status_cursor_response.text
    assert "event: assistant_delta" not in status_cursor_response.text
    assert "event: status_patch" in status_cursor_response.text

    launch_response = client.post(
        "/interaction/chat/messages",
        json={"session_id": session_id, "content": "launch"},
    )
    assert launch_response.status_code == 201
    launch_payload = launch_response.json()
    run_id = launch_payload["session"]["active_run_id"]
    assert run_id is not None
    assert launch_payload["action_result"]["action_type"] == "launch_prepare"
    assert launch_payload["chat_events"][-1]["action_type"] == "launch_prepare"

    resume_response = client.post(
        "/interaction/chat/messages",
        json={"session_id": session_id, "content": "resume"},
    )
    assert resume_response.status_code == 201
    pending_confirmation = resume_response.json()["pending_confirmation"]
    assert pending_confirmation["message_type"] == "confirmation_required"
    assert pending_confirmation["action_type"] == "resume_run"
    assert pending_confirmation["status"] == "pending_confirmation"

    confirm_response = client.post(
        f"/interaction/chat/actions/{pending_confirmation['message_id']}/confirm",
        json={"rationale": "test resume from chat"},
    )
    assert confirm_response.status_code == 200
    confirm_payload = confirm_response.json()
    assert confirm_payload["chat_events"][0]["message_type"] == "confirmation_result"
    assert confirm_payload["action_result"]["run"]["run_id"] == run_id
    assert confirm_payload["action_result"]["run"]["status"] in {"awaiting_review", "completed", "failed"}

    updated_stream_response = client.get(f"/interaction/sessions/{session_id}/stream")
    assert "event: confirmation_result" in updated_stream_response.text
    assert "event: run_update" in updated_stream_response.text
    assert "event: timeline_event" in updated_stream_response.text
    assert "event: pr_ready_summary" in updated_stream_response.text


def test_api_chat_plain_confirmation_advances_pending_action(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post(
        "/interaction/chat/messages",
        json={"content": "Build a tiny artifact through chat confirmation"},
    )
    assert create_response.status_code == 201
    session_id = create_response.json()["session"]["session_id"]

    launch_response = client.post(
        "/interaction/chat/messages",
        json={"session_id": session_id, "content": "launch"},
    )
    assert launch_response.status_code == 201
    run_id = launch_response.json()["session"]["active_run_id"]

    resume_response = client.post(
        "/interaction/chat/messages",
        json={"session_id": session_id, "content": "resume"},
    )
    assert resume_response.status_code == 201
    assert resume_response.json()["pending_confirmation"]["status"] == "pending_confirmation"

    confirm_response = client.post(
        "/interaction/chat/messages",
        json={"session_id": session_id, "content": "confirm"},
    )
    assert confirm_response.status_code == 201, confirm_response.text
    confirm_payload = confirm_response.json()
    assert confirm_payload["pending_confirmation"] is None
    assert confirm_payload["chat_events"][0]["role"] == "user"
    assert confirm_payload["chat_events"][-1]["message_type"] == "confirmation_result"
    assert confirm_payload["action_result"]["run"]["run_id"] == run_id
    assert confirm_payload["action_result"]["run"]["status"] in {"awaiting_review", "completed", "failed"}


def test_api_chat_launch_keyword_confirms_pending_launch_execute(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post(
        "/interaction/chat/messages",
        json={"content": "启动并执行，生成 Build a tiny artifact from a pending launch_execute confirmation"},
    )
    assert create_response.status_code == 201
    session_id = create_response.json()["session"]["session_id"]
    pending_confirmation = create_response.json()["pending_confirmation"]
    assert pending_confirmation["action_type"] == "launch_execute"

    confirm_response = client.post(
        "/interaction/chat/messages",
        json={"session_id": session_id, "content": "launch"},
    )

    assert confirm_response.status_code == 201, confirm_response.text
    confirm_payload = confirm_response.json()
    assert confirm_payload["pending_confirmation"] is None
    assert confirm_payload["chat_events"][0]["role"] == "user"
    assert confirm_payload["chat_events"][-1]["message_type"] == "confirmation_result"
    assert confirm_payload["chat_events"][-1]["action_type"] == "launch_execute"
    assert confirm_payload["session"]["active_run_id"] is not None


def test_api_chat_plain_confirmation_resumes_prepared_active_run(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post(
        "/interaction/chat/messages",
        json={"content": "Build an artifact and wait for chat confirmation"},
    )
    assert create_response.status_code == 201
    session_id = create_response.json()["session"]["session_id"]

    launch_response = client.post(
        "/interaction/chat/messages",
        json={"session_id": session_id, "content": "launch"},
    )
    assert launch_response.status_code == 201
    run_id = launch_response.json()["session"]["active_run_id"]
    assert client.get(f"/runs/{run_id}/status-detail").json()["run"]["status"] == "prepared"

    confirm_response = client.post(
        "/interaction/chat/messages",
        json={"session_id": session_id, "content": "confirm"},
    )
    assert confirm_response.status_code == 201
    payload = confirm_response.json()
    assert payload["chat_events"][-1]["message_type"] == "confirmation_result"
    assert payload["chat_events"][-1]["action_type"] == "resume_run"
    assert payload["action_result"]["run"]["run_id"] == run_id
    assert payload["action_result"]["run"]["status"] in {"awaiting_review", "completed", "failed"}


def test_api_chat_new_plan_request_switches_to_new_session(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path, chat_llm_runtime=_SwitchingChatRuntime())

    first_response = client.post("/interaction/chat/messages", json={"content": "你是谁？"})
    assert first_response.status_code == 201
    old_session_id = first_response.json()["session"]["session_id"]

    new_plan_response = client.post(
        "/interaction/chat/messages",
        json={
            "session_id": old_session_id,
            "content": "启动一个新计划：Build a local snake game artifact with visible evidence",
        },
    )
    assert new_plan_response.status_code == 201
    payload = new_plan_response.json()
    new_session_id = payload["session"]["session_id"]

    assert new_session_id != old_session_id
    assert payload["session"]["status"] == "launched"
    assert payload["action_result"]["action_type"] == "launch_prepare"
    assert payload["session"]["active_run_id"] is not None
    assert [item["role"] for item in payload["chat_messages"]] == ["user", "assistant"]
    assert payload["chat_messages"][-1]["message_type"] == "text"


def test_api_chat_action_failure_returns_visible_error_message(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path, chat_llm_runtime=_SwitchingChatRuntime())

    first_response = client.post("/interaction/chat/messages", json={"content": "你是谁？"})
    assert first_response.status_code == 201
    session_id = first_response.json()["session"]["session_id"]

    launch_response = client.post(
        "/interaction/chat/messages",
        json={"session_id": session_id, "content": "launch"},
    )
    assert launch_response.status_code == 201
    payload = launch_response.json()

    assert payload["chat_messages"][-1]["message_type"] == "error"
    assert payload["chat_messages"][-1]["status"] == "failed"
    assert payload["action_result"]["failed"] is True
    assert any(item["event_type"] == "error" for item in payload["chat_stream_events"])


def test_api_lists_capability_descriptors_and_health(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    descriptors_response = client.get("/capability-descriptors")
    health_response = client.get("/capability-health")

    assert descriptors_response.status_code == 200
    assert any(item["provider_kind"] == "built_in" for item in descriptors_response.json())
    assert any(item["provider_kind"] == "adapter_route" and item["adapter_name"] == "shell" for item in descriptors_response.json())
    assert health_response.status_code == 200
    assert any(item["descriptor"]["provider_kind"] == "runtime_gateway" for item in health_response.json())
    assert all("recent_call_summary" in item for item in health_response.json())
    assert all("readiness_state" in item for item in health_response.json())
    assert all("runtime_ledger_summary" in item for item in health_response.json())
    assert all("runtime_probe_status" in item for item in health_response.json())


def test_api_exposes_plan_graph_and_launch_surfaces(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(CodexAdapter, "launch", _fake_api_external_launch)
    monkeypatch.setattr(LangChainAgentAdapter, "launch", _fake_api_external_launch)
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    plan_response = client.post(
        "/runs/plan-graph",
        json={"goal": "Coordinate a multi-role delivery slice", "preset_id": "project_delivery"},
    )
    assert plan_response.status_code == 200
    assert plan_response.json()["plan_graph"]["execution_mode"] == "planner_generated_graph_with_parallel_children"
    assert len(plan_response.json()["plan_graph"]["edges"]) >= 1
    assert len(plan_response.json()["plan_graph"]["barriers"]) == 1
    assert len(plan_response.json()["plan_graph"]["retry_policies"]) == 1

    policy_response = client.post(
        "/runs/policy-preview",
        json={"goal": "Coordinate a multi-role delivery slice", "preset_id": "project_delivery"},
    )
    assert policy_response.status_code == 200
    assert policy_response.json()["policy_preview"]["recommended_operator_mode"] == "human_visible"

    goal_packet_response = client.post(
        "/runs/goal-packet",
        json={"goal": "Coordinate a multi-role delivery slice", "preset_id": "project_delivery"},
    )
    assert goal_packet_response.status_code == 200
    assert goal_packet_response.json()["capability_policy_preview"]["recommended_operator_mode"] == "human_visible"
    assert len(goal_packet_response.json()["matched_capability_descriptors"]) >= 1

    launch_response = client.post(
        "/runs/launch",
        json={"goal": "Coordinate a multi-role delivery slice", "preset_id": "project_delivery", "execute": True},
    )
    assert launch_response.status_code == 200
    launch_payload = launch_response.json()
    assert launch_payload["selected_preset_id"] == "project_delivery"
    assert launch_payload["plan_graph"]["preset_id"] == "project_delivery"
    assert launch_payload["capability_policy_preview"]["recommended_operator_mode"] == "human_visible"

    plan_status_response = client.get(f"/runs/{launch_payload['run']['run_id']}/plan-graph")
    assert plan_status_response.status_code == 200
    assert plan_status_response.json()["enabled"] is True
    assert len(plan_status_response.json()["plan_graph"]["nodes"]) == 4
    assert len(plan_status_response.json()["plan_graph"]["edges"]) >= 1

    policy_status_response = client.get(f"/runs/{launch_payload['run']['run_id']}/policy-preview")
    assert policy_status_response.status_code == 200
    assert policy_status_response.json()["enabled"] is True
    assert policy_status_response.json()["policy_preview"]["recommended_operator_mode"] == "human_visible"

    operator_packet_response = client.get(f"/runs/{launch_payload['run']['run_id']}/operator-packet")
    assert operator_packet_response.status_code == 200
    assert operator_packet_response.json()["operator_projection"]["recommended_operator_mode"] == "human_visible"
    assert operator_packet_response.json()["capability_policy_preview"]["enabled"] is True


def test_api_sessionful_external_agent_lane_projects_session_refs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UAWO_ENABLE_SESSIONFUL_EXTERNAL_AGENTS", "1")
    monkeypatch.setattr(OpenCodeSessionAdapter, "launch", _fake_api_session_launch)
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    run = client.post("/runs", json={"goal": "Sessionful research via API", "preset_id": "research_spike_reviewable"}).json()
    compile_response = client.post(
        f"/runs/{run['run_id']}/compile",
        json={"adapter_name": "opencode_session"},
    )
    assert compile_response.status_code == 200
    assert compile_response.json()["execution_lane"] == "sessionful_external_agent"

    resume_response = client.post(f"/runs/{run['run_id']}/resume")
    assert resume_response.status_code == 200
    detail = client.get(f"/runs/{run['run_id']}/status-detail").json()
    if detail["run"]["status"] == "awaiting_review":
        client.post(f"/runs/{run['run_id']}/approve")
        detail = client.get(f"/runs/{run['run_id']}/status-detail").json()

    assert detail["trace_context"]["external_session_id"] == "sess_api_123"
    assert detail["trace_context"]["external_session_url"] == "https://example.com/sessions/api-123"
    assert detail["trace_context"]["session_export_ref"].endswith(".json")
    assert detail["result_envelope"]["session_ref"]["external_session_id"] == "sess_api_123"


def test_api_exposes_effective_config_and_worker_pools(tmp_path: Path, monkeypatch) -> None:
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
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    config_response = client.get("/config/effective")
    worker_pools_response = client.get("/worker-pools")

    assert config_response.status_code == 200
    assert config_response.json()["feature_flags"]["external_worker_pools"]["enabled"] is True
    assert config_response.json()["worker_pools"]["default_pool_id"] == "mock_remote_shell"
    assert config_response.json()["execution_defaults"]["worker_pool_id"]["value"] == "mock_remote_shell"
    assert config_response.json()["execution_defaults"]["worker_pool_id"]["source"] == "toml:worker_pools.default_pool_id"
    assert worker_pools_response.status_code == 200
    assert {item["worker_pool_id"] for item in worker_pools_response.json()} >= {
        "local_loopback",
        "mock_remote_shell",
    }


def test_api_can_export_domain_pack_skill_when_flag_enabled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UAWO_ENABLE_SKILL_EXPORT", "1")
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)
    output_root = tmp_path / "skills"

    response = client.post(
        "/domain-packs/software_delivery_pack/skill-export",
        params={"output_root": str(output_root)},
    )

    assert response.status_code == 201
    bundle_path = Path(response.json()["bundle_path"])
    assert response.json()["domain_pack_id"] == "software_delivery_pack"
    assert (bundle_path / "README.md").exists()
    assert (bundle_path / "skill.json").exists()


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


def test_api_exposes_project_delivery_orchestration(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    run = client.post("/runs", json={"goal": "Project delivery API path", "preset_id": "project_delivery"}).json()
    client.post(f"/runs/{run['run_id']}/compile")
    orchestration_response = client.get(f"/runs/{run['run_id']}/orchestration")
    detail_response = client.get(f"/runs/{run['run_id']}/status-detail")
    operator_packet_response = client.get(f"/runs/{run['run_id']}/operator-packet")
    replay_packet_response = client.get(f"/runs/{run['run_id']}/replay-packet")

    assert orchestration_response.status_code == 200
    assert operator_packet_response.status_code == 200
    assert replay_packet_response.status_code == 200
    assert orchestration_response.json()["enabled"] is True
    assert orchestration_response.json()["orchestration"]["cluster_template_ids"] == ["dev_cluster"]
    assert detail_response.json()["orchestration"]["cluster_template_ids"] == ["dev_cluster"]
    assert detail_response.json()["selected_clusters"][0]["template_id"] == "dev_cluster"
    assert detail_response.json()["cluster_policy_preview"]["selected_cluster_template_ids"] == ["dev_cluster"]
    assert detail_response.json()["cluster_packets"][0]["cluster_template_id"] == "dev_cluster"
    assert operator_packet_response.json()["selected_clusters"][0]["template_id"] == "dev_cluster"
    assert operator_packet_response.json()["cluster_policy_preview"]["selected_cluster_template_ids"] == ["dev_cluster"]
    assert replay_packet_response.json()["selected_clusters"][0]["template_id"] == "dev_cluster"
    assert replay_packet_response.json()["cluster_execution_lineage"]["selected_cluster_template_ids"] == ["dev_cluster"]
    assert replay_packet_response.json()["cluster_packets"][0]["cluster_template_id"] == "dev_cluster"


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
    assert payload["source_contract"] == "structured_json"
    assert payload["open_debt_count"] == 0
    assert payload["status_counts"] == {}
    assert [item["debt_id"] for item in payload["open_items"]] == OPEN_DEBT_IDS
    assert payload["source_path"].endswith("docs/governance/tech_debt_registry.json")
    assert payload["source_paths"]["canonical"].endswith("docs/governance/tech_debt_registry.json")


def test_api_exposes_governance_review_policy_report(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    response = client.get("/governance/review-policy")
    assert response.status_code == 200
    payload = response.json()
    assert payload["supported_policy_count"] == 5
    assert [item["policy"] for item in payload["supported_policies"]] == [
        "auto_only",
        "optional",
        "recommended",
        "human_required",
        "mandatory",
    ]
    assert payload["expansion_readiness"]["reference_only_candidates"] == []
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
                    "cluster_flow": {"passed": True},
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
    assert payload["gates"][5]["gate"] == "local_foundation_closure"
    assert payload["gates"][6]["gate"] == "orchestration_baseline"
    assert payload["gates"][7]["gate"] == "cluster_failover_core_completion"
    assert payload["remaining_gaps"] == []
    assert payload["governance_alerts"]["overall_status"] == "clear"


def test_api_exposes_governance_metrics_and_alerts_reports(tmp_path: Path) -> None:
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
                    "cluster_flow": {"passed": True},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    metrics_response = client.get("/governance/metrics", params={"validation_report_path": str(validation_report_path)})
    alerts_response = client.get("/governance/alerts", params={"validation_report_path": str(validation_report_path)})

    assert metrics_response.status_code == 200
    assert metrics_response.json()["tech_debt"]["open_debt_ids"] == OPEN_DEBT_IDS
    assert metrics_response.json()["review_policy"]["supported_policy_count"] == 5
    assert metrics_response.json()["automation"]["governance_metrics_available"] is True

    assert alerts_response.status_code == 200
    assert alerts_response.json()["overall_status"] == "clear"
    assert not any(item["alert_id"] == "open_tech_debt_remaining" for item in alerts_response.json()["alerts"])


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
    assert compile_payload["resolved_execution"]["adapter_name"] == "shell"

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
    assert detail_payload["resolved_execution"]["adapter_name"] == "shell"
    assert detail_payload["execution_resolution_trace"]["source_map"]["adapter_name"]["scope"] == "compatibility_fallback"
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


def test_api_compile_and_mutation_report_support_repo_mutation_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTHONPATH", repo_root.as_posix())
    monkeypatch.setattr(OpenCodeAdapter, "launch", _fake_api_patch_launch)
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)
    target_file = tmp_path / "api_target.txt"
    target_file.write_text("before\n", encoding="utf-8")
    task_card = tmp_path / "api_task_card.md"
    task_card.write_text("# API Mutation\n", encoding="utf-8")
    import sys

    verifier = tmp_path / "verify_api_target.py"
    verifier.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "sys.exit(0 if Path('api_target.txt').read_text(encoding='utf-8') == 'after\\n' else 1)\n",
        encoding="utf-8",
    )
    test_command = f"{sys.executable} {verifier.name}"

    run = client.post("/runs", json={"goal": "API repo mutation", "preset_id": "feature_delivery"}).json()
    compile_response = client.post(
        f"/runs/{run['run_id']}/compile",
        json={
            "adapter_name": "opencode",
            "task_card_ref": "M16-API",
            "task_card_path": task_card.as_posix(),
            "write_set": ["api_target.txt"],
            "test_commands": [test_command],
            "mutation_mode": "patch_apply",
        },
    )

    assert compile_response.status_code == 200
    assert compile_response.json()["mutation_contract"]["mutation_mode"] == "patch_apply"

    resume_response = client.post(f"/runs/{run['run_id']}/resume")
    mutation_report_response = client.get(f"/runs/{run['run_id']}/mutation-report")
    pr_ready_response = client.get(f"/runs/{run['run_id']}/pr-ready-summary")

    assert resume_response.status_code == 200
    assert mutation_report_response.status_code == 200
    assert pr_ready_response.status_code == 200
    assert mutation_report_response.json()["mutation_result"]["final_test_status"] == "passed"
    assert mutation_report_response.json()["result_envelope"]["mutations"]["final_test_status"] == "passed"
    assert pr_ready_response.json()["readiness"] == "ready"
    assert pr_ready_response.json()["bounded_patch"]["changed_files"] == ["api_target.txt"]
    assert pr_ready_response.json()["manual_git"]["create_pr"] == "not_performed"
    assert target_file.read_text(encoding="utf-8") == "after\n"


def test_api_scheduler_authority_grants_and_projects_first_slice(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UAWO_ENABLE_SCHEDULER_AUTHORITY_CLUSTER", "1")
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)
    service = OrchestratorService(db_path)

    run = service.create_run("Scheduler authority grant", "feature_delivery")
    service.compile_run(run.run_id)
    runtime_task_id = service.get_status_detail(run.run_id)["runtime_task_ids"][0]

    proposal_response = client.post(
        "/scheduler/proposals",
        json={
            "control_plane_id": "control_plane_alpha",
            "run_id": run.run_id,
            "runtime_task_id": runtime_task_id,
            "domain_key": runtime_task_id,
            "requested_lease_seconds": 120,
        },
    )
    assert proposal_response.status_code == 201
    payload = proposal_response.json()
    assert payload["granted"] is True
    assert payload["decision"]["control_plane_id"] == "control_plane_alpha"
    assert payload["decision"]["lease_epoch"] == 1

    lease_response = client.get(f"/scheduler/leases/{payload['decision']['lease_id']}")
    detail_response = client.get(f"/runs/{run.run_id}/status-detail")
    replay_response = client.get(f"/runs/{run.run_id}/replay-packet")

    assert lease_response.status_code == 200
    assert lease_response.json()["active"] is True
    assert detail_response.status_code == 200
    assert detail_response.json()["scheduler_authority"]["active_decision"]["lease_id"] == payload["decision"]["lease_id"]
    assert (
        detail_response.json()["scheduler_authority"]["active_committed_lease"]["authority_term_no"]
        == detail_response.json()["scheduler_authority"]["active_committed_lease"]["term_no"]
    )
    assert (
        detail_response.json()["scheduler_authority"]["active_committed_lease"]["decision_index"]
        == detail_response.json()["scheduler_authority"]["active_committed_lease"]["commit_index"]
    )
    assert replay_response.status_code == 200
    assert replay_response.json()["scheduler_authority"]["latest_decision"]["decision_id"] == payload["decision"]["decision_id"]


def test_api_scheduler_authority_conflict_duplicate_and_release_flow(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UAWO_ENABLE_SCHEDULER_AUTHORITY_CLUSTER", "1")
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)
    service = OrchestratorService(db_path)

    run = service.create_run("Scheduler authority conflict", "feature_delivery")
    service.compile_run(run.run_id)
    runtime_task_id = service.get_status_detail(run.run_id)["runtime_task_ids"][0]

    granted = client.post(
        "/scheduler/proposals",
        json={
            "control_plane_id": "control_plane_alpha",
            "run_id": run.run_id,
            "runtime_task_id": runtime_task_id,
            "domain_key": runtime_task_id,
        },
    )
    duplicate = client.post(
        "/scheduler/proposals",
        json={
            "control_plane_id": "control_plane_alpha",
            "run_id": run.run_id,
            "runtime_task_id": runtime_task_id,
            "domain_key": runtime_task_id,
        },
    )
    conflict = client.post(
        "/scheduler/proposals",
        json={
            "control_plane_id": "control_plane_beta",
            "run_id": run.run_id,
            "runtime_task_id": runtime_task_id,
            "domain_key": runtime_task_id,
        },
    )

    granted_payload = granted.json()
    duplicate_payload = duplicate.json()
    conflict_payload = conflict.json()

    assert granted.status_code == 201
    assert duplicate.status_code == 201
    assert duplicate_payload["duplicate"] is True
    assert duplicate_payload["decision"]["lease_id"] == granted_payload["decision"]["lease_id"]
    assert conflict.status_code == 201
    assert conflict_payload["granted"] is False
    assert conflict_payload["conflict"]["active_control_plane_id"] == "control_plane_alpha"

    heartbeat_response = client.post(
        "/scheduler/heartbeats",
        json={"control_plane_id": "control_plane_alpha", "lease_count": 1},
    )
    release_response = client.post(
        f"/scheduler/releases/{granted_payload['decision']['lease_id']}",
        json={"release_reason": "test_release"},
    )
    lease_response = client.get(f"/scheduler/leases/{granted_payload['decision']['lease_id']}")
    inspection_response = client.get(f"/runs/{run.run_id}/inspection")

    assert heartbeat_response.status_code == 201
    assert release_response.status_code == 200
    assert release_response.json()["decision"]["release_reason"] == "test_release"
    assert lease_response.status_code == 200
    assert lease_response.json()["active"] is False
    assert lease_response.json()["latest_peer_heartbeat"]["control_plane_id"] == "control_plane_alpha"
    assert inspection_response.status_code == 200
    assert inspection_response.json()["problem_count"] >= 1
    assert any(
        problem["problem"] == "scheduler_authority_conflict"
        for problem in inspection_response.json()["problems"]
    )


def test_api_scheduler_authority_regrants_after_expiry_and_survives_restart(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UAWO_ENABLE_SCHEDULER_AUTHORITY_CLUSTER", "1")
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)
    service = OrchestratorService(db_path)

    run = service.create_run("Scheduler authority stale lease", "feature_delivery")
    service.compile_run(run.run_id)
    runtime_task_id = service.get_status_detail(run.run_id)["runtime_task_ids"][0]

    first = client.post(
        "/scheduler/proposals",
        json={
            "control_plane_id": "control_plane_alpha",
            "run_id": run.run_id,
            "runtime_task_id": runtime_task_id,
            "domain_key": runtime_task_id,
            "requested_lease_seconds": 1,
        },
    )
    first_payload = first.json()
    with unit_of_work(db_path) as connection:
        connection.execute(
            "UPDATE scheduler_committed_leases SET lease_expires_at = ? WHERE lease_id = ?",
            ((datetime.now(UTC) - timedelta(minutes=1)).isoformat(), first_payload["decision"]["lease_id"]),
        )

    restarted_client = build_client(db_path)
    second = restarted_client.post(
        "/scheduler/proposals",
        json={
            "control_plane_id": "control_plane_beta",
            "run_id": run.run_id,
            "runtime_task_id": runtime_task_id,
            "domain_key": runtime_task_id,
            "requested_epoch": 2,
        },
    )
    second_payload = second.json()
    detail_response = restarted_client.get(f"/runs/{run.run_id}/status-detail")

    assert second.status_code == 201
    assert second_payload["granted"] is True
    assert second_payload["decision"]["control_plane_id"] == "control_plane_beta"
    assert second_payload["committed_lease"]["control_plane_id"] == "control_plane_beta"
    assert second_payload["decision"]["lease_epoch"] >= 2
    assert detail_response.status_code == 200
    assert detail_response.json()["scheduler_authority"]["active_decision"]["control_plane_id"] == "control_plane_beta"
    assert (
        detail_response.json()["scheduler_authority"]["active_committed_lease"]["control_plane_id"]
        == "control_plane_beta"
    )


def test_api_local_only_mode_exposes_disabled_scheduler_cluster_by_default(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    run = client.post("/runs", json={"goal": "Operator cluster projection", "preset_id": "feature_delivery"}).json()
    cluster_response = client.get("/scheduler/cluster")
    runs_response = client.get("/runs")
    operator_view = client.get(f"/runs/{run['run_id']}/operator-view")
    dashboard_html = client.get("/ui").text
    governance_html = client.get("/ui/governance").text

    assert cluster_response.status_code == 200
    assert runs_response.status_code == 200
    assert operator_view.status_code == 200
    cluster_payload = cluster_response.json()
    operator_payload = operator_view.json()
    assert cluster_payload["enabled"] is False
    assert cluster_payload["mode"] == "local_only"
    assert cluster_payload["leader_node_id"] is not None
    assert cluster_payload["authority_node_id"] == cluster_payload["leader_node_id"]
    assert cluster_payload["authority_term_no"] == cluster_payload["term_no"]
    assert cluster_payload["decision_index"] == cluster_payload["commit_index"]
    assert operator_payload["cluster_overview"]["enabled"] is False
    assert operator_payload["cluster_overview"]["leader_node_id"] == cluster_payload["leader_node_id"]
    assert operator_payload["cluster_overview"]["authority_node_id"] == cluster_payload["authority_node_id"]
    assert operator_payload["cluster_overview"]["authority_term_no"] == cluster_payload["authority_term_no"]
    assert operator_payload["cluster_overview"]["decision_index"] == cluster_payload["decision_index"]
    assert len(runs_response.json()) >= 1
    assert "调度权威拓扑" in dashboard_html
    assert "调度权威拓扑" in governance_html
    assert "调度权威集群已关闭，当前为本地单机模式。" in dashboard_html
    assert "调度权威集群已关闭，当前为本地单机模式。" in governance_html


def test_api_exposes_run_replay_packet(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    run = client.post("/runs", json={"goal": "Replay packet via API", "preset_id": "feature_delivery"}).json()
    client.post(f"/runs/{run['run_id']}/compile")
    client.post(f"/runs/{run['run_id']}/resume")

    response = client.get(f"/runs/{run['run_id']}/replay-packet")

    assert response.status_code == 200
    payload = response.json()
    assert payload["packet_version"] == "m9_phase_1_v1"
    assert payload["metrics"]["counts"]["events"] >= 1
    assert payload["review_lineage"]["effective_review_state"] == "auto_passed"


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


def test_api_compile_can_pin_codex_adapter(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Compile via codex adapter", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]

    compile_response = client.post(
        f"/runs/{run_id}/compile",
        json={"adapter_name": "codex", "codex_model": "gpt-5.1-codex-max"},
    )
    assert compile_response.status_code == 200
    compile_payload = compile_response.json()
    assert compile_payload["capability_adapter"] == "codex"
    assert compile_payload["resolved_execution"]["selected_model"] == "gpt-5.1-codex-max"

    detail_response = client.get(f"/runs/{run_id}/status-detail")
    assert detail_response.status_code == 200
    assert detail_response.json()["capability_resolution"]["adapter_name"] == "codex"


def test_api_compile_rejects_unknown_adapter(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    create_response = client.post("/runs", json={"goal": "Compile via missing adapter", "preset_id": "feature_delivery"})
    run_id = create_response.json()["run_id"]

    compile_response = client.post(f"/runs/{run_id}/compile", json={"adapter_name": "missing_adapter"})
    assert compile_response.status_code == 422
    error = compile_response.json()["error"]
    assert error["code"] == "capability_adapter_not_found"
    assert error["details"]["available_adapters"] == AVAILABLE_SHELL_EXEC_ADAPTERS


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
    assert auto_report.json()["result_envelope"]["verification"]["return_code"] == 0
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
    assert detail_payload["latest_claim"]["owner_kind"] == "control_plane"
    assert detail_payload["latest_claim"]["owner_id"] == "control_plane_local"
    assert detail_payload["ownership_topology"]["claim"]["domain_kind"] == "runtime_task"
    assert claims_payload[0]["release_reason"] == "run_terminal"
    assert claims_payload[0]["owner_id"] == "control_plane_local"


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
    assert detail_payload["latest_worker_lease"]["worker_kind"] == "worker"
    assert detail_payload["latest_worker_lease"]["claim_id"] == detail_payload["latest_claim"]["claim_id"]
    assert detail_payload["ownership_topology"]["worker_lease"]["worker_id"] == "worker_shell_local"
    assert detail_payload["ownership_topology"]["topology_aligned"] is True
    assert detail_payload["worker_lease_projection"]["latest_adapter_name"] == "shell"
    assert inspection_payload["latest_worker_lease"]["status"] == "released"
    assert inspection_payload["ownership_topology"]["worker_lease"]["domain_kind"] == "runtime_task"
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
    assert payload[0]["worker_id"] == "worker_shell_local"


def test_api_batch_resume_returns_parallel_batch_summary(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    first_create = client.post("/runs", json={"goal": "API parallel batch first", "preset_id": "feature_delivery"})
    second_create = client.post("/runs", json={"goal": "API parallel batch second", "preset_id": "feature_delivery"})
    first_run_id = first_create.json()["run_id"]
    second_run_id = second_create.json()["run_id"]
    client.post(f"/runs/{first_run_id}/compile")
    client.post(f"/runs/{second_run_id}/compile")

    batch_response = client.post(
        "/runs/batch-resume",
        json={"run_ids": [first_run_id, second_run_id], "max_workers": 2},
    )
    first_detail = client.get(f"/runs/{first_run_id}/status-detail")

    assert batch_response.status_code == 200
    payload = batch_response.json()
    assert payload["status"] == "completed"
    assert payload["member_count"] == 2
    assert len(payload["results"]) == 2
    assert first_detail.json()["parallel_batch"]["barrier_id"] == payload["barrier_id"]


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
