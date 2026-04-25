from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from apps.orchestrator_api.main import create_app
from packages.core_domain.db import migrate
from packages.core_domain.repositories import PresetRepository
from conftest import ReceiptAwareTestClient


pytestmark = pytest.mark.slow

def build_client(db_path: Path) -> ReceiptAwareTestClient:
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    return ReceiptAwareTestClient(create_app(db_path))


def test_api_and_web_ui_expose_operator_surfaces(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    feature_run = client.post("/runs", json={"goal": "Ship UI route", "preset_id": "feature_delivery"}).json()
    client.post(f"/runs/{feature_run['run_id']}/compile")
    client.post(f"/runs/{feature_run['run_id']}/resume")

    review_run = client.post("/runs", json={"goal": "Need human review", "preset_id": "research_spike"}).json()
    client.post(f"/runs/{review_run['run_id']}/compile")
    client.post(f"/runs/{review_run['run_id']}/resume")

    runs_response = client.get("/runs", params={"limit": 10})
    pending_response = client.get("/reviews/pending")
    operator_response = client.get(f"/runs/{review_run['run_id']}/operator-view")
    dashboard_response = client.get("/ui")
    runs_page_response = client.get("/ui/runs")
    run_page_response = client.get(f"/ui/runs/{review_run['run_id']}")
    reviews_page_response = client.get("/ui/reviews")
    governance_page_response = client.get("/ui/governance")
    config_page_response = client.get("/ui/config")
    css_response = client.get("/static/operator.css")
    js_response = client.get("/static/workbench.js")

    assert runs_response.status_code == 200
    assert {item["run"]["run_id"] for item in runs_response.json()} == {
        feature_run["run_id"],
        review_run["run_id"],
    }
    assert pending_response.status_code == 200
    assert [item["run"]["run_id"] for item in pending_response.json()] == [review_run["run_id"]]
    assert operator_response.status_code == 200
    assert operator_response.json()["run"]["run_id"] == review_run["run_id"]
    assert operator_response.json()["status_detail"]["effective_review_state"] == "human_pending"
    assert operator_response.json()["cluster_overview"]["enabled"] is False
    assert dashboard_response.headers["x-frame-options"] == "DENY"
    assert dashboard_response.headers["x-content-type-options"] == "nosniff"
    csp = dashboard_response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in csp
    assert "unsafe-inline" not in csp
    assert "script-src 'self'" in csp
    assert "style-src 'self'" in csp
    assert css_response.status_code == 200
    assert js_response.status_code == 200
    assert "EventSource" in js_response.text
    assert "<style" not in dashboard_response.text
    assert "style=" not in dashboard_response.text
    assert '<script defer src="/static/workbench.js"' in dashboard_response.text
    assert "运行目录" in runs_page_response.text
    assert "待审查控制台" in reviews_page_response.text
    assert "治理" in governance_page_response.text
    assert "有效配置" in config_page_response.text
    assert "操作台总览" in dashboard_response.text
    assert "调度租约仲裁集群路径已关闭，当前为本地租约仲裁模式。" in dashboard_response.text
    assert "调度租约仲裁集群路径已关闭，当前为本地租约仲裁模式。" in governance_page_response.text
    assert review_run["run_id"] in run_page_response.text


def test_web_ui_action_routes_redirect_and_mutate_run_state(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    run = client.post("/runs", json={"goal": "Approve from web UI", "preset_id": "research_spike"}).json()
    client.post(f"/runs/{run['run_id']}/compile")
    client.post(f"/runs/{run['run_id']}/resume")

    approve_response = client.post(f"/ui/actions/{run['run_id']}/approve", follow_redirects=False)
    assert approve_response.status_code == 303
    approve_location = approve_response.headers["location"]
    approve_query = parse_qs(urlparse(approve_location).query)
    assert urlparse(approve_location).path == "/ui/actions/confirm"
    assert approve_query["receipt_id"][0].startswith("opreceipt_")

    pre_confirm_operator_response = client.get(f"/runs/{run['run_id']}/operator-view")
    assert pre_confirm_operator_response.status_code == 200
    assert pre_confirm_operator_response.json()["run"]["status"] != "completed"

    reconcile_response = client.post(f"/ui/actions/{run['run_id']}/reconcile", follow_redirects=False)
    assert reconcile_response.status_code == 303
    reconcile_location = reconcile_response.headers["location"]
    reconcile_query = parse_qs(urlparse(reconcile_location).query)
    assert urlparse(reconcile_location).path == "/ui/actions/confirm"
    assert reconcile_query["receipt_id"][0].startswith("opreceipt_")

    confirmation_page = client.get(approve_location)
    assert confirmation_page.status_code == 200
    assert "Confirm high-risk action" in confirmation_page.text
    assert approve_query["receipt_id"][0] in confirmation_page.text

    confirm_response = client.post(
        "/ui/actions/confirm",
        data={"receipt_id": approve_query["receipt_id"][0]},
        follow_redirects=False,
    )
    assert confirm_response.status_code == 303
    assert f"/ui/runs/{run['run_id']}?" in confirm_response.headers["location"]

    operator_response = client.get(f"/runs/{run['run_id']}/operator-view")
    assert operator_response.status_code == 200
    assert operator_response.json()["run"]["status"] == "completed"

    batch_ready_run = client.post("/runs", json={"goal": "Prepared batch resume", "preset_id": "feature_delivery"}).json()
    client.post(f"/runs/{batch_ready_run['run_id']}/compile")

    batch_resume_response = client.post(
        "/ui/actions/batch-resume",
        data={"run_id": [batch_ready_run["run_id"]]},
        follow_redirects=False,
    )
    assert batch_resume_response.status_code == 303
    batch_location = batch_resume_response.headers["location"]
    batch_query = parse_qs(urlparse(batch_location).query)
    assert urlparse(batch_location).path == "/ui/actions/confirm"
    assert batch_query["receipt_id"][0].startswith("opreceipt_")

    batch_confirm_response = client.post(
        "/ui/actions/confirm",
        data={"receipt_id": batch_query["receipt_id"][0]},
        follow_redirects=False,
    )
    assert batch_confirm_response.status_code == 303
    assert "/ui/reviews?" in batch_confirm_response.headers["location"]


def test_web_ui_workbench_post_flow_redirects_through_preview_clarify_and_launch(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    client = build_client(db_path)

    preview_response = client.post(
        "/ui/workbench/preview",
        data={
            "goal": "Coordinate a multi-role project delivery slice",
            "preset_id": "project_delivery",
            "cluster_template_id": "dev_cluster",
            "constraints": "keep operator checkpoints visible",
            "assumptions": "workspace is clean",
            "referenced_artifact_paths": "docs/current_development_workflow.md",
            "followup_context": "prior review asked for a launch checkpoint",
        },
        follow_redirects=False,
    )

    assert preview_response.status_code == 303
    preview_location = preview_response.headers["location"]
    preview_query = parse_qs(urlparse(preview_location).query)
    session_id = preview_query["session_id"][0]
    assert urlparse(preview_location).path == "/ui/workbench"
    assert preview_query["notice"] == ["工作台预览已刷新"]

    workbench_response = client.get(preview_location)
    workbench_js_response = client.get("/static/workbench.js")
    assert workbench_response.status_code == 200
    assert workbench_js_response.status_code == 200
    assert "交互式工作台" in workbench_response.text
    assert "流式聊天工作台" in workbench_response.text
    assert "chat-stream" in workbench_response.text
    assert "data-stream-url" in workbench_response.text
    assert "EventSource" in workbench_js_response.text
    assert "data-message-id" in workbench_js_response.text
    assert "after_event_id" in workbench_js_response.text
    assert "heartbeatReceived" in workbench_js_response.text
    assert "assistant_delta" in workbench_js_response.text
    assert 'eventId.indexOf("chatevt_") === 0' in workbench_js_response.text
    assert "data-chat-confirm-action" in workbench_js_response.text
    assert 'dataset.streaming !== "true"' in workbench_js_response.text
    assert "chat-llm-status" in workbench_response.text
    assert "workflow-status-feed" in workbench_response.text
    assert "事件流已断开" not in workbench_response.text
    assert "<style" not in workbench_response.text
    assert "style=" not in workbench_response.text
    assert session_id in workbench_response.text
    assert "可启动" in workbench_response.text
    assert "执行默认值" in workbench_response.text
    assert "最近会话" in workbench_response.text

    chat_response = client.post(
        "/ui/workbench/chat",
        data={"session_id": session_id, "message": "plan"},
        follow_redirects=False,
    )
    assert chat_response.status_code == 303
    chat_location = chat_response.headers["location"]
    chat_query = parse_qs(urlparse(chat_location).query)
    assert chat_query["session_id"] == [session_id]
    assert chat_query["notice"] == ["聊天消息已处理"]
    chat_page_response = client.get(chat_location)
    assert "计划预览" in chat_page_response.text
    assert "流式聊天工作台" in chat_page_response.text

    clarify_response = client.post(
        f"/ui/workbench/{session_id}/clarify",
        data={
            "answer_scope": "Keep operator checkpoints visible",
            "preset_id": "project_delivery",
            "cluster_template_id": "dev_cluster",
        },
        follow_redirects=False,
    )

    assert clarify_response.status_code == 303
    clarify_location = clarify_response.headers["location"]
    clarify_query = parse_qs(urlparse(clarify_location).query)
    assert urlparse(clarify_location).path == "/ui/workbench"
    assert clarify_query["session_id"] == [session_id]
    assert clarify_query["notice"] == ["澄清信息已更新"]

    clarified_workbench_response = client.get(clarify_location)
    assert clarified_workbench_response.status_code == 200
    assert session_id in clarified_workbench_response.text
    assert "计划草案" in clarified_workbench_response.text

    launch_response = client.post(
        f"/ui/workbench/{session_id}/launch",
        data={},
        follow_redirects=False,
    )

    assert launch_response.status_code == 303
    launch_location = launch_response.headers["location"]
    parsed_launch = urlparse(launch_location)
    launch_query = parse_qs(parsed_launch.query)
    run_id = parsed_launch.path.removeprefix("/ui/runs/")
    assert parsed_launch.path == f"/ui/runs/{run_id}"
    assert launch_query["notice"] == ["启动完成：预设=project_delivery"]

    run_page_response = client.get(launch_location)
    operator_response = client.get(f"/runs/{run_id}/operator-view")
    assert run_page_response.status_code == 200
    assert run_id in run_page_response.text
    assert operator_response.status_code == 200
    assert operator_response.json()["run"]["run_id"] == run_id
    assert operator_response.json()["run"]["status"] == "prepared"

    resume_chat_response = client.post(
        "/ui/workbench/chat",
        data={"session_id": session_id, "message": "resume"},
        follow_redirects=False,
    )
    assert resume_chat_response.status_code == 303
    resume_chat_page = client.get(resume_chat_response.headers["location"])
    assert "需要确认" in resume_chat_page.text
    assert "继续运行" in resume_chat_page.text

    generate_profiles_response = client.post(
        f"/ui/workbench/{session_id}/generate-profiles",
        follow_redirects=False,
    )
    assert generate_profiles_response.status_code == 303
    generated_profiles_page = client.get(generate_profiles_response.headers["location"])
    assert generated_profiles_page.status_code == 200
    assert "已生成角色配置" in generated_profiles_page.text
    assert "自动化观察器" in generated_profiles_page.text

    followup_response = client.post(
        f"/ui/workbench/{session_id}/followup",
        data={
            "instruction": "Prepare the approval checkpoint after the implementation run completes.",
            "intent": "review_gate",
            "blocking": "true",
            "run_id": run_id,
        },
        follow_redirects=False,
    )

    assert followup_response.status_code == 303
    followup_location = followup_response.headers["location"]
    followup_query = parse_qs(urlparse(followup_location).query)
    assert urlparse(followup_location).path == "/ui/workbench"
    assert followup_query["session_id"] == [session_id]
    assert followup_query["notice"] == ["后续事项已加入队列"]

    followup_page_response = client.get(followup_location)
    assert followup_page_response.status_code == 200
    assert "后续事项队列" in followup_page_response.text
    assert "当前运行检查点" in followup_page_response.text
    assert "已生成角色配置" in followup_page_response.text
    assert "自动化观察器" in followup_page_response.text
    assert "review_gate" in followup_page_response.text
    assert run_id in followup_page_response.text


def test_local_game_templates_do_not_use_inner_html() -> None:
    source = Path("packages/contributions/games/local_game_artifacts.py").read_text(encoding="utf-8")
    assert ".innerHTML" not in source
