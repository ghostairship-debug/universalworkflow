from __future__ import annotations

from fastapi import APIRouter, Header, Query, status

from apps.orchestrator_api.request_models import (
    BatchResumeRequest,
    CreateRunRequest,
    GoalPlanRequest,
    LaunchGoalRequest,
    MaterializeMemoryItemRequest,
    OperatorActionReceiptRequest,
    ReconcileRunRequest,
    TaskKindOverrideRequest,
)
from packages.core_domain.services import OrchestratorService


def _serialize_task_bundle(bundle) -> dict:
    return {
        "run": bundle.run.model_dump(mode="json"),
        "runtime_task_id": bundle.task_packet.runtime_task_id,
        "handoff_id": bundle.handoff.handoff_id,
        "state_ref_id": bundle.state_ref.state_ref_id,
        "domain_pack_id": bundle.domain_pack.domain_pack_id if bundle.domain_pack is not None else None,
        "capability_adapter": bundle.capability_route.adapter_name if bundle.capability_route is not None else None,
        "execution_lane": str(bundle.execution_lane),
        "resolved_execution": bundle.resolved_execution.model_dump(mode="json"),
        "mutation_contract": (
            bundle.task_packet.mutation_contract.model_dump(mode="json")
            if bundle.task_packet.mutation_contract is not None
            else None
        ),
        "tool_projection_manifest": (
            bundle.tool_projection_manifest.model_dump(mode="json")
            if bundle.tool_projection_manifest is not None
            else None
        ),
        "mcp_server_profiles": [profile.model_dump(mode="json") for profile in bundle.mcp_server_profiles],
        "memory_preview": bundle.memory_preview.model_dump(mode="json") if bundle.memory_preview is not None else None,
    }


def build_runs_router(service: OrchestratorService) -> APIRouter:
    router = APIRouter()

    def _consume_receipt(action_type: str, receipt_id: str | None) -> None:
        service.consume_operator_action_receipt(receipt_id=receipt_id, action_type=action_type)

    @router.post("/operator-action-receipts", status_code=status.HTTP_201_CREATED)
    def create_operator_action_receipt(payload: OperatorActionReceiptRequest) -> dict:
        return service.issue_operator_action_receipt(
            action_type=payload.action_type,
            risk_level=payload.risk_level,
            operator_id=payload.operator_id,
            requested_write_set=payload.requested_write_set,
            ttl_seconds=payload.ttl_seconds,
            metadata=payload.metadata,
        ).model_dump(mode="json")

    @router.get("/runs")
    def list_runs(
        status: str | None = None,
        preset_id: str | None = None,
        limit: int = Query(default=10, ge=1),
    ) -> list[dict]:
        return service.list_run_operator_rows(limit=limit, status=status, preset_id=preset_id)

    @router.get("/reviews/pending")
    def get_pending_reviews(limit: int = Query(default=20, ge=1)) -> list[dict]:
        return service.list_pending_review_runs(limit=limit)

    @router.post("/runs", status_code=status.HTTP_201_CREATED)
    def create_run(payload: CreateRunRequest) -> dict:
        run = service.create_run(goal=payload.goal, preset_id=payload.preset_id)
        return run.model_dump(mode="json")

    @router.post("/runs/plan-graph")
    def preview_goal_plan_graph(payload: GoalPlanRequest) -> dict:
        return service.preview_orchestration_plan_graph(goal=payload.goal, preset_id=payload.preset_id)

    @router.post("/runs/policy-preview")
    def preview_goal_policy(payload: GoalPlanRequest) -> dict:
        return service.preview_capability_policy(goal=payload.goal, preset_id=payload.preset_id)

    @router.post("/runs/goal-packet")
    def preview_goal_packet(payload: GoalPlanRequest) -> dict:
        return service.preview_goal_packet(goal=payload.goal, preset_id=payload.preset_id)

    @router.post("/runs/launch")
    def launch_goal(payload: LaunchGoalRequest) -> dict:
        return service.launch_goal(goal=payload.goal, preset_id=payload.preset_id, execute=payload.execute)

    @router.get("/runs/{run_id}")
    def get_run(run_id: str) -> dict:
        return service.get_run(run_id).model_dump(mode="json")

    @router.post("/runs/{run_id}/compile")
    def compile_run(run_id: str, payload: TaskKindOverrideRequest | None = None) -> dict:
        bundle = service.compile_run(
            run_id,
            task_kind=payload.task_kind if payload is not None else None,
            adapter_name=payload.adapter_name if payload is not None else None,
            agent_model=payload.agent_model if payload is not None else None,
            codex_model=payload.codex_model if payload is not None else None,
            opencode_model=payload.opencode_model if payload is not None else None,
            opencode_variant=payload.opencode_variant if payload is not None else None,
            runtime_gateway_provider=payload.runtime_gateway_provider if payload is not None else None,
            runtime_gateway_model=payload.runtime_gateway_model if payload is not None else None,
            runtime_reasoning_effort=payload.runtime_reasoning_effort if payload is not None else None,
            worker_pool_id=payload.worker_pool_id if payload is not None else None,
            memory_item_ids=payload.memory_item_ids if payload is not None and payload.memory_item_ids else None,
            task_card_ref=payload.task_card_ref if payload is not None else None,
            task_card_path=payload.task_card_path if payload is not None else None,
            write_set=payload.write_set if payload is not None and payload.write_set else None,
            read_set=payload.read_set if payload is not None and payload.read_set else None,
            test_commands=payload.test_commands if payload is not None and payload.test_commands else None,
            max_fix_iterations=payload.max_fix_iterations if payload is not None else 0,
            mutation_mode=payload.mutation_mode if payload is not None else None,
        )
        return _serialize_task_bundle(bundle)

    @router.post("/runs/{run_id}/recompile")
    def recompile_run(run_id: str, payload: TaskKindOverrideRequest | None = None) -> dict:
        bundle = service.recompile_run(
            run_id,
            task_kind=payload.task_kind if payload is not None else None,
            adapter_name=payload.adapter_name if payload is not None else None,
            agent_model=payload.agent_model if payload is not None else None,
            codex_model=payload.codex_model if payload is not None else None,
            opencode_model=payload.opencode_model if payload is not None else None,
            opencode_variant=payload.opencode_variant if payload is not None else None,
            runtime_gateway_provider=payload.runtime_gateway_provider if payload is not None else None,
            runtime_gateway_model=payload.runtime_gateway_model if payload is not None else None,
            runtime_reasoning_effort=payload.runtime_reasoning_effort if payload is not None else None,
            worker_pool_id=payload.worker_pool_id if payload is not None else None,
            memory_item_ids=payload.memory_item_ids if payload is not None and payload.memory_item_ids else None,
            task_card_ref=payload.task_card_ref if payload is not None else None,
            task_card_path=payload.task_card_path if payload is not None else None,
            write_set=payload.write_set if payload is not None and payload.write_set else None,
            read_set=payload.read_set if payload is not None and payload.read_set else None,
            test_commands=payload.test_commands if payload is not None and payload.test_commands else None,
            max_fix_iterations=payload.max_fix_iterations if payload is not None else 0,
            mutation_mode=payload.mutation_mode if payload is not None else None,
        )
        return _serialize_task_bundle(bundle)

    @router.post("/runs/{run_id}/resume")
    def resume_run(
        run_id: str,
        operator_action_receipt: str | None = Header(default=None, alias="X-Operator-Action-Receipt"),
    ) -> dict:
        _consume_receipt("resume_run", operator_action_receipt)
        bundle = service.resume_run(run_id)
        return {
            "run": bundle.run.model_dump(mode="json"),
            "evidence_id": bundle.evidence.evidence_id,
            "review_decision": bundle.review_verdict.decision if bundle.review_verdict is not None else None,
        }

    @router.post("/runs/batch-resume")
    def batch_resume_runs(
        payload: BatchResumeRequest,
        operator_action_receipt: str | None = Header(default=None, alias="X-Operator-Action-Receipt"),
    ) -> dict:
        _consume_receipt("batch_resume_runs", operator_action_receipt)
        return service.resume_runs_parallel(payload.run_ids, max_workers=payload.max_workers)

    @router.post("/runs/{run_id}/approve")
    def approve_run(
        run_id: str,
        operator_action_receipt: str | None = Header(default=None, alias="X-Operator-Action-Receipt"),
    ) -> dict:
        _consume_receipt("approve_run", operator_action_receipt)
        bundle = service.approve_run_review(run_id)
        return {
            "run": bundle.run.model_dump(mode="json"),
            "evidence_id": bundle.evidence.evidence_id,
            "review_decision": bundle.review_verdict.decision,
        }

    @router.post("/runs/{run_id}/reject")
    def reject_run(
        run_id: str,
        operator_action_receipt: str | None = Header(default=None, alias="X-Operator-Action-Receipt"),
    ) -> dict:
        _consume_receipt("reject_run", operator_action_receipt)
        bundle = service.reject_run_review(run_id)
        return {
            "run": bundle.run.model_dump(mode="json"),
            "evidence_id": bundle.evidence.evidence_id,
            "review_decision": bundle.review_verdict.decision,
        }

    @router.get("/runs/{run_id}/timeline")
    def get_run_timeline(run_id: str) -> list[dict]:
        return [event.model_dump(mode="json") for event in service.get_timeline(run_id)]

    @router.get("/runs/{run_id}/replay-packet")
    def get_run_replay_packet(run_id: str) -> dict:
        return service.get_run_replay_packet(run_id)

    @router.get("/runs/{run_id}/orchestration")
    def get_run_orchestration(run_id: str) -> dict:
        return service.get_run_orchestration(run_id)

    @router.get("/runs/{run_id}/plan-graph")
    def get_run_plan_graph(run_id: str) -> dict:
        return service.get_run_orchestration_plan_graph(run_id)

    @router.get("/runs/{run_id}/policy-preview")
    def get_run_policy_preview(run_id: str) -> dict:
        return service.get_run_capability_policy_preview(run_id)

    @router.get("/runs/{run_id}/operator-packet")
    def get_run_operator_packet(run_id: str) -> dict:
        return service.get_run_operator_packet(run_id)

    @router.get("/runs/{run_id}/status-detail")
    def get_run_status_detail(run_id: str) -> dict:
        return service.get_status_detail(run_id)

    @router.get("/runs/{run_id}/summary")
    def get_run_summary(run_id: str) -> dict:
        return service.get_run_summary(run_id)

    @router.get("/runs/{run_id}/pr-ready-summary")
    def get_run_pr_ready_summary(run_id: str) -> dict:
        return service.get_run_pr_ready_summary(run_id)

    @router.get("/runs/{run_id}/simulation")
    def get_run_simulation(run_id: str) -> dict:
        return service.get_run_simulation(run_id).model_dump(mode="json")

    @router.post("/runs/{run_id}/simulation-records", status_code=status.HTTP_201_CREATED)
    def record_run_simulation(run_id: str) -> dict:
        return service.record_run_simulation(run_id).model_dump(mode="json")

    @router.get("/runs/{run_id}/simulation-records")
    def list_run_simulation_records(run_id: str) -> list[dict]:
        return [record.model_dump(mode="json") for record in service.list_simulation_records(run_id)]

    @router.get("/runs/{run_id}/event-inspection")
    def get_run_event_inspection(run_id: str) -> dict:
        return service.get_event_inspection(run_id)

    @router.get("/runs/{run_id}/audit-report")
    def get_run_audit_report(run_id: str) -> dict:
        return service.get_run_audit_report(run_id)

    @router.get("/runs/{run_id}/mutation-report")
    def get_run_mutation_report(run_id: str) -> dict:
        return service.get_run_mutation_report(run_id)

    @router.get("/runs/{run_id}/memory-candidates")
    def get_run_memory_candidates(run_id: str) -> list[dict]:
        return [candidate.model_dump(mode="json") for candidate in service.get_run_memory_candidates(run_id)]

    @router.post("/runs/{run_id}/memory-items", status_code=status.HTTP_201_CREATED)
    def materialize_run_memory_item(run_id: str, payload: MaterializeMemoryItemRequest) -> dict:
        return service.materialize_run_memory_candidate(run_id, payload.candidate_id).model_dump(mode="json")

    @router.get("/runs/{run_id}/memory-items")
    def get_run_memory_items(run_id: str) -> list[dict]:
        return [item.model_dump(mode="json") for item in service.list_memory_items(run_id=run_id)]

    @router.get("/runs/{run_id}/inspection")
    def inspect_run_state(run_id: str) -> dict:
        return service.inspect_run_state(run_id)

    @router.get("/runs/{run_id}/operator-view")
    def get_run_operator_view(run_id: str) -> dict:
        return service.get_operator_view(run_id)

    @router.get("/runs/{run_id}/claims")
    def get_run_claims(run_id: str) -> list[dict]:
        return [claim.model_dump(mode="json") for claim in service.list_claims(run_id)]

    @router.get("/runs/{run_id}/leases")
    def get_run_worker_leases(run_id: str) -> list[dict]:
        return [lease.model_dump(mode="json") for lease in service.list_worker_leases(run_id)]

    @router.get("/runs/{run_id}/attempts")
    def get_run_runtime_attempts(run_id: str) -> list[dict]:
        return [attempt.model_dump(mode="json") for attempt in service.list_runtime_attempts(run_id)]

    @router.get("/runs/{run_id}/snapshots")
    def get_run_snapshots(run_id: str) -> list[dict]:
        return [snapshot.model_dump(mode="json") for snapshot in service.list_snapshots(run_id)]

    @router.get("/runs/{run_id}/budget")
    def get_run_budget(run_id: str) -> dict:
        detail = service.get_status_detail(run_id)
        return {
            "run": detail["run"],
            "budget_ledger": detail["budget_ledger"],
            "budget_projection": detail["budget_projection"],
        }

    @router.post("/runs/{run_id}/reconcile")
    def reconcile_run(
        run_id: str,
        payload: ReconcileRunRequest | None = None,
        operator_action_receipt: str | None = Header(default=None, alias="X-Operator-Action-Receipt"),
    ) -> dict:
        if payload is not None and payload.apply:
            _consume_receipt("reconcile_apply", operator_action_receipt)
            return service.apply_run_repair(run_id, action=payload.action)
        return service.reconcile_run(run_id)

    @router.post("/runs/{run_id}/cancel")
    def cancel_run(
        run_id: str,
        operator_action_receipt: str | None = Header(default=None, alias="X-Operator-Action-Receipt"),
    ) -> dict:
        _consume_receipt("cancel_run", operator_action_receipt)
        return service.cancel_run(run_id).model_dump(mode="json")

    @router.get("/runs/{run_id}/handoffs")
    def get_run_handoffs(run_id: str) -> list[dict]:
        return [handoff.model_dump(mode="json") for handoff in service.list_handoffs(run_id)]

    @router.get("/tasks/{runtime_task_id}/evidence")
    def get_task_evidence(runtime_task_id: str) -> dict:
        return service.get_task_evidence(runtime_task_id).model_dump(mode="json")

    return router
