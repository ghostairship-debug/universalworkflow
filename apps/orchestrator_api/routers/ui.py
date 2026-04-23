from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from apps.orchestrator_api.routers.governance import build_governance_reports
from apps.orchestrator_api.web_ui import (
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

    def _redirect_with_notice(path: str, notice: str) -> RedirectResponse:
        separator = "&" if "?" in path else "?"
        return RedirectResponse(url=f"{path}{separator}{urlencode({'notice': notice})}", status_code=status.HTTP_303_SEE_OTHER)

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
            return _redirect_with_notice("/ui/workbench", "preview skipped: goal is required")
        preset_id = str(form.get("preset_id") or "").strip() or None
        cluster_template_id = str(form.get("cluster_template_id") or "").strip()
        payload = service.create_intent_session(
            goal=goal,
            preferred_preset_id=preset_id,
            preferred_cluster_template_ids=[cluster_template_id] if cluster_template_id else None,
        )
        return _redirect_with_notice(
            f"/ui/workbench?session_id={payload['session']['session_id']}",
            "workbench preview refreshed",
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
        return _redirect_with_notice(f"/ui/workbench?session_id={session_id}", "clarifications updated")

    @router.post("/ui/workbench/{session_id}/launch")
    async def web_workbench_launch(session_id: str, request: Request) -> RedirectResponse:
        form = await request.form()
        execute = str(form.get("execute") or "").lower() in {"1", "true", "on", "yes"}
        payload = service.launch_intent_session(session_id, execute=execute)
        run_id = payload["launch_payload"]["run"]["run_id"]
        return _redirect_with_notice(
            f"/ui/runs/{run_id}",
            f"launch completed: preset={payload['launch_payload']['selected_preset_id']}",
        )

    @router.post("/ui/actions/{run_id}/resume")
    def web_resume_run(run_id: str) -> RedirectResponse:
        bundle = service.resume_run(run_id)
        return _redirect_with_notice(
            f"/ui/runs/{run_id}",
            f"resume completed: status={bundle.run.status} evidence={bundle.evidence.evidence_id}",
        )

    @router.post("/ui/actions/{run_id}/approve")
    def web_approve_run(run_id: str) -> RedirectResponse:
        bundle = service.approve_run_review(run_id)
        return _redirect_with_notice(
            f"/ui/runs/{run_id}",
            f"approve completed: review={bundle.review_verdict.decision} status={bundle.run.status}",
        )

    @router.post("/ui/actions/{run_id}/reject")
    def web_reject_run(run_id: str) -> RedirectResponse:
        bundle = service.reject_run_review(run_id)
        return _redirect_with_notice(
            f"/ui/runs/{run_id}",
            f"reject completed: review={bundle.review_verdict.decision} status={bundle.run.status}",
        )

    @router.post("/ui/actions/{run_id}/reconcile")
    def web_reconcile_run(run_id: str) -> RedirectResponse:
        result = service.reconcile_run(run_id)
        return _redirect_with_notice(
            f"/ui/runs/{run_id}",
            f"reconcile inspected: passed={result['passed']} problems={result['problem_count']}",
        )

    @router.post("/ui/actions/{run_id}/cancel")
    def web_cancel_run(run_id: str) -> RedirectResponse:
        run = service.cancel_run(run_id)
        return _redirect_with_notice(f"/ui/runs/{run_id}", f"cancel completed: status={run.status}")

    @router.post("/ui/actions/batch-resume")
    async def web_batch_resume_runs(request: Request) -> RedirectResponse:
        form = await request.form()
        run_ids = [str(item) for item in form.getlist("run_id") if str(item).strip()]
        if not run_ids:
            return _redirect_with_notice("/ui/reviews", "batch-resume skipped: no runs selected")
        result = service.resume_runs_parallel(run_ids, max_workers=min(len(run_ids), 4))
        return _redirect_with_notice(
            "/ui/reviews",
            f"batch-resume completed: requested={len(run_ids)} results={len(result['results'])}",
        )

    return router
