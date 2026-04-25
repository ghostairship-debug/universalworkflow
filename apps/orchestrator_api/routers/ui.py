from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from apps.orchestrator_api.routers.governance import build_governance_reports
from apps.orchestrator_api.web_ui import (
    render_action_confirmation as render_action_confirmation_page,
    render_config as render_config_page,
    render_dashboard as render_dashboard_page,
    render_governance as render_governance_page,
    render_reviews as render_reviews_page,
    render_run_focus as render_run_focus_page,
    render_runs as render_runs_page,
    render_workbench as render_workbench_page,
)
from packages.core_domain.services import OrchestratorService


def build_ui_router(
    service: OrchestratorService,
    effective_config: dict[str, Any],
    resolved_db_path: Path,
) -> APIRouter:
    router = APIRouter()

    def _split_lines(value: Any) -> list[str]:
        return [
            line.strip()
            for line in str(value or "").splitlines()
            if line and line.strip()
        ]

    def _redirect_with_notice(path: str, notice: str) -> RedirectResponse:
        separator = "&" if "?" in path else "?"
        return RedirectResponse(url=f"{path}{separator}{urlencode({'notice': notice})}", status_code=status.HTTP_303_SEE_OTHER)

    def _issue_local_ui_receipt(action_type: str, *, run_id: str | None = None) -> str:
        receipt = service.issue_operator_action_receipt(
            action_type=action_type,
            risk_level="high",
            scope_payload={"run_id": run_id},
            metadata={"source": "web_ui_form", "run_id": run_id},
        )
        return receipt.receipt_id

    def _redirect_to_confirmation(receipt_id: str) -> RedirectResponse:
        query = urlencode({"receipt_id": receipt_id})
        return RedirectResponse(f"/ui/actions/confirm?{query}", status_code=status.HTTP_303_SEE_OTHER)

    def _execute_receipted_action(receipt_id: str) -> tuple[str, str]:
        receipt = service.operator_action_receipt_repo.get(receipt_id)
        if receipt is None:
            return "/ui", "Receipt 不存在或已过期"
        action_type = receipt.action_type
        metadata = receipt.metadata or {}
        run_id = str(metadata.get("run_id") or "")
        if action_type == "batch_resume_runs":
            run_ids = [str(item) for item in metadata.get("run_ids", []) if str(item).strip()]
            service.consume_operator_action_receipt(
                receipt_id=receipt_id,
                action_type=action_type,
                scope_payload={"run_ids": run_ids, "requested_write_set": run_ids},
            )
            result = service.resume_runs_parallel(run_ids, max_workers=min(len(run_ids), 4) if run_ids else None)
            return "/ui/reviews", f"批量继续完成：请求 {len(run_ids)} 结果={len(result['results'])}"
        if not run_id:
            return "/ui", "Receipt 缺少 run_id"
        service.consume_operator_action_receipt(
            receipt_id=receipt_id,
            action_type=action_type,
            scope_payload={"run_id": run_id},
        )
        if action_type == "resume_run":
            bundle = service.resume_run(run_id)
            return f"/ui/runs/{run_id}", f"继续执行完成：状态 {bundle.run.status} 证据={bundle.evidence.evidence_id}"
        if action_type == "approve_run":
            bundle = service.approve_run_review(run_id)
            return f"/ui/runs/{run_id}", f"通过审查完成：审查 {bundle.review_verdict.decision} 状态 {bundle.run.status}"
        if action_type == "reject_run":
            bundle = service.reject_run_review(run_id)
            return f"/ui/runs/{run_id}", f"拒绝审查完成：审查 {bundle.review_verdict.decision} 状态 {bundle.run.status}"
        if action_type == "cancel_run":
            run = service.cancel_run(run_id)
            return f"/ui/runs/{run_id}", f"取消完成：状态 {run.status}"
        return f"/ui/runs/{run_id}", f"Receipt 动作不支持：{action_type}"

    @router.get("/ui", response_class=HTMLResponse)
    def web_dashboard(notice: str | None = None) -> HTMLResponse:
        snapshot = service.get_dashboard_snapshot(limit=8)
        html = render_dashboard_page(
            snapshot=snapshot,
            pending_reviews=service.list_pending_review_runs(limit=8),
            governance=build_governance_reports(resolved_db_path),
            effective_config=effective_config,
            cluster_overview=snapshot.get("cluster_overview"),
            notice=notice,
        )
        return HTMLResponse(html)

    @router.get("/ui/runs", response_class=HTMLResponse)
    def web_runs(
        status: str | None = None,
        preset_id: str | None = None,
        limit: int = Query(default=20, ge=1),
        notice: str | None = None,
    ) -> HTMLResponse:
        html = render_runs_page(
            rows=service.list_run_operator_rows(limit=limit, status=status, preset_id=preset_id),
            status_filter=status,
            preset_filter=preset_id,
            limit=limit,
            notice=notice,
        )
        return HTMLResponse(html)

    @router.get("/ui/runs/{run_id}", response_class=HTMLResponse)
    def web_run_focus(run_id: str, notice: str | None = None) -> HTMLResponse:
        return HTMLResponse(render_run_focus_page(operator_view=service.get_operator_view(run_id), notice=notice))

    @router.get("/ui/reviews", response_class=HTMLResponse)
    def web_reviews(notice: str | None = None) -> HTMLResponse:
        return HTMLResponse(render_reviews_page(rows=service.list_pending_review_runs(limit=20), notice=notice))

    @router.get("/ui/governance", response_class=HTMLResponse)
    def web_governance(notice: str | None = None) -> HTMLResponse:
        return HTMLResponse(
            render_governance_page(
                reports=build_governance_reports(resolved_db_path),
                cluster_overview=service.scheduler_authority_cluster.cluster_snapshot(),
                notice=notice,
            )
        )

    @router.get("/ui/workbench", response_class=HTMLResponse)
    def web_workbench(session_id: str | None = None, notice: str | None = None) -> HTMLResponse:
        session_payload = service.get_intent_session_payload(session_id) if session_id else None
        return HTMLResponse(
            render_workbench_page(
                session_payload=session_payload,
                presets=[preset.model_dump(mode="json") for preset in service.list_presets()],
                cluster_templates=[template.model_dump(mode="json") for template in service.list_cluster_templates()],
                recent_sessions=[session.model_dump(mode="json") for session in service.list_intent_sessions(limit=8)],
                effective_config=effective_config,
                notice=notice,
            )
        )

    @router.get("/ui/config", response_class=HTMLResponse)
    def web_config(notice: str | None = None) -> HTMLResponse:
        return HTMLResponse(render_config_page(effective_config=effective_config, notice=notice))

    @router.post("/ui/workbench/preview")
    async def web_workbench_preview(request: Request) -> RedirectResponse:
        form = await request.form()
        goal = str(form.get("goal") or "").strip()
        if not goal:
            return _redirect_with_notice("/ui/workbench", "预览已跳过：目标不能为空")
        preset_id = str(form.get("preset_id") or "").strip() or None
        cluster_template_id = str(form.get("cluster_template_id") or "").strip()
        payload = service.create_intent_session(
            goal=goal,
            preferred_preset_id=preset_id,
            preferred_cluster_template_ids=[cluster_template_id] if cluster_template_id else None,
            constraints=_split_lines(form.get("constraints")),
            assumptions=_split_lines(form.get("assumptions")),
            referenced_artifact_paths=_split_lines(form.get("referenced_artifact_paths")),
            followup_context=_split_lines(form.get("followup_context")),
        )
        return _redirect_with_notice(
            f"/ui/workbench?session_id={payload['session']['session_id']}",
            "工作台预览已刷新",
        )

    @router.post("/ui/workbench/chat")
    async def web_workbench_chat(request: Request) -> RedirectResponse:
        form = await request.form()
        message = str(form.get("message") or "").strip()
        session_id = str(form.get("session_id") or "").strip() or None
        run_id = str(form.get("run_id") or "").strip() or None
        if not message:
            target = f"/ui/workbench?session_id={session_id}" if session_id else "/ui/workbench"
            return _redirect_with_notice(target, "聊天已跳过：消息不能为空")
        payload = service.post_chat_message(session_id=session_id, run_id=run_id, content=message)
        target_session_id = payload["session"]["session_id"]
        return _redirect_with_notice(
            f"/ui/workbench?session_id={target_session_id}",
            "聊天消息已处理",
        )

    @router.post("/ui/workbench/chat/actions/{action_id}/confirm")
    async def web_workbench_chat_confirm(action_id: str, request: Request) -> RedirectResponse:
        form = await request.form()
        rationale = str(form.get("rationale") or "").strip() or None
        payload = service.confirm_chat_action(action_id, rationale=rationale)
        session_id = payload["session"]["session_id"]
        return _redirect_with_notice(
            f"/ui/workbench?session_id={session_id}",
            "聊天动作已确认",
        )

    @router.post("/ui/workbench/{session_id}/clarify")
    async def web_workbench_clarify(session_id: str, request: Request) -> RedirectResponse:
        form = await request.form()
        answers = {
            str(key).removeprefix("answer_"): str(value).strip()
            for key, value in form.multi_items()
            if str(key).startswith("answer_") and str(value).strip()
        }
        preset_id = str(form.get("preset_id") or "").strip() or None
        cluster_template_id = str(form.get("cluster_template_id") or "").strip()
        service.continue_intent_session(
            session_id,
            answers=answers,
            preferred_preset_id=preset_id,
            preferred_cluster_template_ids=[cluster_template_id] if cluster_template_id else None,
        )
        return _redirect_with_notice(f"/ui/workbench?session_id={session_id}", "澄清信息已更新")

    @router.post("/ui/workbench/{session_id}/launch")
    async def web_workbench_launch(session_id: str, request: Request) -> RedirectResponse:
        form = await request.form()
        execute = str(form.get("execute") or "").lower() in {"1", "true", "on", "yes"}
        payload = service.launch_intent_session(session_id, execute=execute)
        run_id = payload["launch_payload"]["run"]["run_id"]
        return _redirect_with_notice(
            f"/ui/runs/{run_id}",
            f"启动完成：预设={payload['launch_payload']['selected_preset_id']}",
        )

    @router.post("/ui/workbench/{session_id}/generate-profiles")
    def web_workbench_generate_profiles(session_id: str) -> RedirectResponse:
        service.generate_session_profiles(session_id)
        return _redirect_with_notice(f"/ui/workbench?session_id={session_id}", "会话角色配置已刷新")

    @router.post("/ui/workbench/{session_id}/followup")
    async def web_workbench_followup(session_id: str, request: Request) -> RedirectResponse:
        form = await request.form()
        instruction = str(form.get("instruction") or "").strip()
        if not instruction:
            return _redirect_with_notice(
                f"/ui/workbench?session_id={session_id}",
                "后续事项已跳过：指令不能为空",
            )
        intent = str(form.get("intent") or "continue").strip() or "continue"
        blocking = str(form.get("blocking") or "").lower() in {"1", "true", "on", "yes"}
        run_id = str(form.get("run_id") or "").strip() or None
        service.create_followup_request(
            session_id,
            instruction=instruction,
            intent=intent,
            blocking=blocking,
            run_id=run_id,
        )
        return _redirect_with_notice(f"/ui/workbench?session_id={session_id}", "后续事项已加入队列")


    @router.get("/ui/actions/confirm", response_class=HTMLResponse)
    def web_action_confirmation(receipt_id: str = Query(...)) -> HTMLResponse:
        receipt = service.operator_action_receipt_repo.get(receipt_id)
        if receipt is None:
            return HTMLResponse(
                render_action_confirmation_page(
                    receipt={"receipt_id": receipt_id, "action_type": "missing", "status": "missing"},
                    notice="Receipt ???????",
                ),
                status_code=404,
            )
        return HTMLResponse(render_action_confirmation_page(receipt=receipt.model_dump(mode="json")))

    @router.post("/ui/actions/confirm")
    async def web_action_confirm_execute(request: Request) -> RedirectResponse:
        form = await request.form()
        receipt_id = str(form.get("receipt_id") or "").strip()
        path, notice = _execute_receipted_action(receipt_id)
        return _redirect_with_notice(path, notice)

    @router.post("/ui/actions/{run_id}/resume")
    def web_resume_run(run_id: str) -> RedirectResponse:
        return _redirect_to_confirmation(_issue_local_ui_receipt("resume_run", run_id=run_id))

    @router.post("/ui/actions/{run_id}/approve")
    def web_approve_run(run_id: str) -> RedirectResponse:
        return _redirect_to_confirmation(_issue_local_ui_receipt("approve_run", run_id=run_id))

    @router.post("/ui/actions/{run_id}/reject")
    def web_reject_run(run_id: str) -> RedirectResponse:
        return _redirect_to_confirmation(_issue_local_ui_receipt("reject_run", run_id=run_id))

    @router.post("/ui/actions/{run_id}/reconcile")
    def web_reconcile_run(run_id: str) -> RedirectResponse:
        result = service.reconcile_run(run_id)
        return _redirect_with_notice(
            f"/ui/runs/{run_id}",
            f"?????????={result['passed']} ??={result['problem_count']}",
        )

    @router.post("/ui/actions/{run_id}/cancel")
    def web_cancel_run(run_id: str) -> RedirectResponse:
        return _redirect_to_confirmation(_issue_local_ui_receipt("cancel_run", run_id=run_id))

    @router.post("/ui/actions/batch-resume")
    async def web_batch_resume_runs(request: Request) -> RedirectResponse:
        form = await request.form()
        run_ids = [str(item) for item in form.getlist("run_id") if str(item).strip()]
        if not run_ids:
            return _redirect_with_notice("/ui/reviews", "??????????????")
        receipt = service.issue_operator_action_receipt(
            action_type="batch_resume_runs",
            risk_level="high",
            requested_write_set=run_ids,
            scope_payload={"run_ids": run_ids},
            metadata={"source": "web_ui_form", "run_ids": run_ids},
        )
        return _redirect_to_confirmation(receipt.receipt_id)
    return router
