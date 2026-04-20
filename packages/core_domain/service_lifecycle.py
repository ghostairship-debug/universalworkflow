from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Barrier, BrokenBarrierError
from typing import Any

from packages.contracts import (
    BudgetLedger,
    MutationContract,
    MutationMode,
    ReviewDecision,
    ReviewPolicy,
    ReviewerType,
    ReviewVerdict,
    Run,
    RunEvent,
    RunEventType,
    SchedulerLeaseDecision,
    SchedulerLeaseProposal,
    RunSnapshotStage,
    RunStatus,
    RuntimeAttemptStatus,
    RuntimeAttemptTrigger,
    RuntimeClaimStatus,
    RuntimeGraphStep,
    RuntimeStateRef,
    SimulationRecordSource,
    TaskKind,
    TaskPacket,
    TaskStatus,
    WorkerLeaseStatus,
)
from packages.contracts.models import new_id
from packages.core_domain.compile import CompileSnapshot, compile_run as build_compile_snapshot
from packages.core_domain.db import unit_of_work
from packages.core_domain.errors import (
    BudgetExhaustedError,
    EntityNotFoundError,
    MutationContractError,
    ParallelBarrierBrokenError,
    PresetNotFoundError,
    WorkflowError,
)
from packages.core_domain.service_types import ExecutedRunBundle, PreparedRunBundle, ReviewedRunBundle


class LifecycleServiceMixin:
    def _parallel_batch_payload(self, barrier_id: str, member_count: int, state: str) -> dict[str, Any]:
        return {
            "barrier_id": barrier_id,
            "member_count": member_count,
            "state": state,
        }

    def _snapshot_for_run(
        self,
        run: Run,
        preset: PresetDefinition,
        requested_task_kind: TaskKind | str | None = None,
        requested_adapter: str | None = None,
        memory_item_ids: list[str] | None = None,
        task_card_ref: str | None = None,
        task_card_path: str | None = None,
        write_set: list[str] | None = None,
        read_set: list[str] | None = None,
        test_commands: list[str] | None = None,
        max_fix_iterations: int = 0,
        mutation_mode: MutationMode | str | None = None,
    ) -> CompileSnapshot:
        resolved_task_kind = self._resolve_task_kind(preset, requested_task_kind)
        resolved_mutation_mode = MutationMode(mutation_mode) if mutation_mode is not None else MutationMode.artifact_only
        mutation_contract = (
            MutationContract(
                task_card_ref=task_card_ref,
                task_card_path=task_card_path,
                write_set=list(write_set or []),
                read_set=list(read_set or []),
                test_commands=list(test_commands or []),
                max_fix_iterations=max_fix_iterations,
                mutation_mode=resolved_mutation_mode,
            )
            if (
                task_card_ref is not None
                or task_card_path is not None
                or write_set
                or read_set
                or test_commands
                or resolved_mutation_mode != MutationMode.artifact_only
            )
            else None
        )
        domain_pack = self._resolve_domain_pack(preset, resolved_task_kind)
        default_adapter = self._default_adapter_for_preset(
            preset,
            resolved_task_kind,
            domain_pack,
        )
        selected_adapter = requested_adapter or (
            "opencode"
            if mutation_contract is not None and mutation_contract.mutation_mode == MutationMode.patch_apply
            else default_adapter
        )
        if mutation_contract is not None and mutation_contract.mutation_mode == MutationMode.patch_apply and selected_adapter != "opencode":
            raise MutationContractError(
                "patch_apply mutation contracts require the opencode adapter",
                {"adapter_name": selected_adapter},
            )
        capability_route = self._resolve_capability_route(resolved_task_kind, requested_adapter=selected_adapter)
        execution_lane = self._resolve_execution_lane(
            preset=preset,
            task_kind=resolved_task_kind,
            selected_adapter=capability_route.adapter_name if capability_route is not None else selected_adapter,
            mutation_contract=mutation_contract,
        )
        tool_projection_manifest, mcp_server_profiles = self._build_tool_projection_manifest(
            run=run,
            preset=preset,
            task_kind=resolved_task_kind,
            lane_type=execution_lane,
            domain_pack=domain_pack,
        )
        memory_preview = (
            self.preview_memory_retrieval(preset_id=preset.preset_id, memory_item_ids=memory_item_ids)
            if memory_item_ids
            else None
        )
        snapshot = build_compile_snapshot(
            run.goal,
            preset,
            run.run_id,
            task_kind=resolved_task_kind,
            domain_pack=domain_pack,
            capability_route=capability_route,
            memory_preview=memory_preview,
            execution_lane=execution_lane,
            tool_projection_manifest=tool_projection_manifest,
            mcp_server_profiles=mcp_server_profiles,
            mutation_contract=mutation_contract,
        )
        worker_pool_profile = self._selected_worker_pool_profile()
        if worker_pool_profile is not None:
            snapshot.task_packet = TaskPacket.model_validate(
                {
                    **snapshot.task_packet.model_dump(mode="json"),
                    "env": {
                        **snapshot.task_packet.env,
                        "WORKFLOW_EXECUTION_TARGET": "external_worker_pool",
                        "WORKFLOW_WORKER_POOL_ID": worker_pool_profile.worker_pool_id,
                    },
                }
            )
        if preset.preset_id == "project_delivery":
            orchestration_plan = self._default_project_delivery_plan(run.run_id)
            snapshot.task_packet = TaskPacket.model_validate(
                {
                    **snapshot.task_packet.model_dump(mode="json"),
                    "env": {
                        **snapshot.task_packet.env,
                        "WORKFLOW_ORCHESTRATION_PLAN": json.dumps(orchestration_plan.model_dump(mode="json"), ensure_ascii=False),
                    },
                }
            )
        return snapshot

    def compile_run(
        self,
        run_id: str,
        task_kind: TaskKind | str | None = None,
        adapter_name: str | None = None,
        memory_item_ids: list[str] | None = None,
        task_card_ref: str | None = None,
        task_card_path: str | None = None,
        write_set: list[str] | None = None,
        read_set: list[str] | None = None,
        test_commands: list[str] | None = None,
        max_fix_iterations: int = 0,
        mutation_mode: MutationMode | str | None = None,
    ) -> PreparedRunBundle:
        run = self.get_run(run_id)
        self._require_status(run, "compile", [RunStatus.pending])
        preset = self.preset_repo.get(run.preset_id)
        if preset is None:
            raise PresetNotFoundError(f"preset not found: {run.preset_id}")
        snapshot = self._snapshot_for_run(
            run,
            preset,
            task_kind,
            requested_adapter=adapter_name,
            memory_item_ids=memory_item_ids,
            task_card_ref=task_card_ref,
            task_card_path=task_card_path,
            write_set=write_set,
            read_set=read_set,
            test_commands=test_commands,
            max_fix_iterations=max_fix_iterations,
            mutation_mode=mutation_mode,
        )

        with unit_of_work(self.db_path) as connection:
            self._ensure_budget_ledger(run, preset, connection=connection, compile_count=1)
            self.task_repo.create_phase(snapshot.compile_phase, connection=connection)
            self.task_repo.create_phase(snapshot.execution_phase, connection=connection)
            self.task_repo.create_task_card(snapshot.task_card, connection=connection)
            self.task_repo.create_runtime_task(snapshot.runtime_task, connection=connection)
            self.task_repo.create_task_packet(snapshot.task_packet, connection=connection)
            self.handoff_repo.create(snapshot.handoff, connection=connection)
            self._create_runtime_attempt(
                run.run_id,
                snapshot.runtime_task.runtime_task_id,
                trigger=RuntimeAttemptTrigger.compile,
                connection=connection,
            )
            state_ref = self._state_ref_with_compile_context(
                self.runtime_gateway.start(run.run_id, snapshot.runtime_task.runtime_task_id),
                run,
                preset,
                snapshot,
            )
            state_ref = self._state_ref_with_m8_context(state_ref, snapshot)
            trace_id = self._export_trace(
                run_id=run.run_id,
                name="compile",
                lane_type=snapshot.execution_lane,
                status=RunStatus.prepared,
                attributes={
                    "runtime_task_id": snapshot.runtime_task.runtime_task_id,
                    "adapter_name": snapshot.capability_route.adapter_name if snapshot.capability_route is not None else None,
                    "projection_id": (
                        snapshot.tool_projection_manifest.projection_id
                        if snapshot.tool_projection_manifest is not None
                        else None
                    ),
                },
            )
            if trace_id is not None:
                state_ref = self._state_ref_with_payload_updates(state_ref, {"external_trace_id": trace_id})
            stored_state_ref = self.runtime_state_repo.upsert(state_ref, connection=connection)
            updated_run = self._transition_run_status(run, "compile", RunStatus.prepared, connection=connection)
            for phase in (snapshot.compile_phase, snapshot.execution_phase):
                self.event_repo.append(
                    RunEvent(
                        run_id=run.run_id,
                        event_type=RunEventType.phase_created,
                        object_type="phase",
                        object_id=phase.phase_id,
                        summary="Phase created",
                        payload_json={"phase_id": phase.phase_id, "phase_name": phase.name},
                    ),
                    connection=connection,
                )
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.handoff_created,
                    object_type="handoff",
                    object_id=snapshot.handoff.handoff_id,
                    summary="Handoff created",
                    payload_json={
                        "handoff_id": snapshot.handoff.handoff_id,
                        "from_phase_id": snapshot.handoff.from_phase_id,
                        "to_phase_id": snapshot.handoff.to_phase_id,
                    },
                ),
                connection=connection,
            )
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.runtime_task_created,
                    object_type="runtime_task",
                    object_id=snapshot.runtime_task.runtime_task_id,
                    summary="Runtime task created",
                    payload_json={
                        "runtime_task_id": snapshot.runtime_task.runtime_task_id,
                        "task_kind": snapshot.runtime_task.task_kind,
                        "summary": snapshot.runtime_task.summary,
                    },
                ),
                connection=connection,
            )
            if snapshot.domain_pack is not None and snapshot.capability_route is not None:
                self.event_repo.append(
                    RunEvent(
                        run_id=run.run_id,
                        event_type=RunEventType.domain_pack_selected,
                        object_type="domain_pack",
                        object_id=snapshot.domain_pack.domain_pack_id,
                        summary="Domain pack selected",
                        payload_json={
                            "domain_pack_id": snapshot.domain_pack.domain_pack_id,
                            "domain_pack_name": snapshot.domain_pack.name,
                            "matched_preset_id": snapshot.domain_pack.matched_preset_id,
                            "task_kind": snapshot.runtime_task.task_kind,
                            "adapter_name": snapshot.capability_route.adapter_name,
                            "operator_label": snapshot.domain_pack.runtime_projection.operator_label,
                            "capability_tags": snapshot.domain_pack.capability_exposure.capability_tags,
                            "evidence_expectations": snapshot.domain_pack.runtime_projection.evidence_expectations,
                        },
                    ),
                    connection=connection,
                )
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.run_compiled,
                    object_type="run",
                    object_id=run.run_id,
                    summary="Run compiled",
                    payload_json={
                        "run_id": run.run_id,
                        "status": RunStatus.prepared,
                        "runtime_task_id": snapshot.runtime_task.runtime_task_id,
                    },
                ),
                connection=connection,
            )
            self._capture_run_snapshot(
                run.run_id,
                RunSnapshotStage.compiled,
                "Compile snapshot captured",
                runtime_task_id=snapshot.runtime_task.runtime_task_id,
                connection=connection,
                payload_extra={
                    "domain_pack_id": snapshot.domain_pack.domain_pack_id if snapshot.domain_pack is not None else None,
                    "domain_pack_resolution": (
                        snapshot.domain_pack.model_dump(mode="json") if snapshot.domain_pack is not None else None
                    ),
                    "adapter_name": snapshot.capability_route.adapter_name if snapshot.capability_route is not None else None,
                    "memory_retrieval_preview": (
                        snapshot.memory_preview.model_dump(mode="json") if snapshot.memory_preview is not None else None
                    ),
                },
            )
        return PreparedRunBundle(
            run=updated_run,
            preset=preset,
            task_packet=snapshot.task_packet,
            state_ref=stored_state_ref,
            handoff=snapshot.handoff,
            domain_pack=snapshot.domain_pack,
            capability_route=snapshot.capability_route,
            memory_preview=snapshot.memory_preview,
            execution_lane=snapshot.execution_lane,
            tool_projection_manifest=snapshot.tool_projection_manifest,
            mcp_server_profiles=snapshot.mcp_server_profiles,
        )

    def recompile_run(
        self,
        run_id: str,
        task_kind: TaskKind | str | None = None,
        adapter_name: str | None = None,
        memory_item_ids: list[str] | None = None,
        task_card_ref: str | None = None,
        task_card_path: str | None = None,
        write_set: list[str] | None = None,
        read_set: list[str] | None = None,
        test_commands: list[str] | None = None,
        max_fix_iterations: int = 0,
        mutation_mode: MutationMode | str | None = None,
        *,
        ignore_budget: bool = False,
    ) -> PreparedRunBundle:
        run = self.get_run(run_id)
        self._require_status(run, "recompile", [RunStatus.prepared])
        preset = self.preset_repo.get(run.preset_id)
        if preset is None:
            raise PresetNotFoundError(f"preset not found: {run.preset_id}")
        snapshot = self._snapshot_for_run(
            run,
            preset,
            task_kind,
            requested_adapter=adapter_name,
            memory_item_ids=memory_item_ids,
            task_card_ref=task_card_ref,
            task_card_path=task_card_path,
            write_set=write_set,
            read_set=read_set,
            test_commands=test_commands,
            max_fix_iterations=max_fix_iterations,
            mutation_mode=mutation_mode,
        )

        with unit_of_work(self.db_path) as connection:
            ledger = self._ensure_budget_ledger(run, preset, connection=connection, compile_count=1)
            remaining_retries = self._remaining_retries(ledger)
            if not ignore_budget and remaining_retries is not None and remaining_retries <= 0:
                raise BudgetExhaustedError(run.run_id, remaining_retries, ledger.max_retries)
            next_compile_count = ledger.compile_count + 1
            next_recompile_count = ledger.recompile_count if ignore_budget else ledger.recompile_count + 1
            ledger = self.budget_repo.update(
                BudgetLedger.model_validate(
                    {
                        **ledger.model_dump(mode="json"),
                        "compile_count": next_compile_count,
                        "recompile_count": next_recompile_count,
                        "updated_at": self._utc_now().isoformat(),
                    }
                ),
                connection=connection,
            )
            self.runtime_state_repo.clear_for_run(run.run_id, connection=connection)
            self.handoff_repo.clear_for_run(run.run_id, connection=connection)
            self.task_repo.clear_for_run(run.run_id, connection=connection)

            self.task_repo.create_phase(snapshot.compile_phase, connection=connection)
            self.task_repo.create_phase(snapshot.execution_phase, connection=connection)
            self.task_repo.create_task_card(snapshot.task_card, connection=connection)
            self.task_repo.create_runtime_task(snapshot.runtime_task, connection=connection)
            self.task_repo.create_task_packet(snapshot.task_packet, connection=connection)
            self.handoff_repo.create(snapshot.handoff, connection=connection)
            self._ensure_current_runtime_attempt(
                run.run_id,
                snapshot.runtime_task.runtime_task_id,
                trigger=RuntimeAttemptTrigger.recompile,
                connection=connection,
                reason_if_superseded="recompile",
            )
            state_ref = self._state_ref_with_compile_context(
                self.runtime_gateway.start(run.run_id, snapshot.runtime_task.runtime_task_id),
                run,
                preset,
                snapshot,
            )
            state_ref = self._state_ref_with_m8_context(state_ref, snapshot)
            trace_id = self._export_trace(
                run_id=run.run_id,
                name="recompile",
                lane_type=snapshot.execution_lane,
                status=RunStatus.prepared,
                attributes={
                    "runtime_task_id": snapshot.runtime_task.runtime_task_id,
                    "adapter_name": snapshot.capability_route.adapter_name if snapshot.capability_route is not None else None,
                    "projection_id": (
                        snapshot.tool_projection_manifest.projection_id
                        if snapshot.tool_projection_manifest is not None
                        else None
                    ),
                },
            )
            if trace_id is not None:
                state_ref = self._state_ref_with_payload_updates(state_ref, {"external_trace_id": trace_id})
            stored_state_ref = self.runtime_state_repo.upsert(state_ref, connection=connection)
            updated_run = self._transition_run_status(run, "recompile", RunStatus.prepared, connection=connection)
            for phase in (snapshot.compile_phase, snapshot.execution_phase):
                self.event_repo.append(
                    RunEvent(
                        run_id=run.run_id,
                        event_type=RunEventType.phase_created,
                        object_type="phase",
                        object_id=phase.phase_id,
                        summary="Phase created",
                        payload_json={"phase_id": phase.phase_id, "phase_name": phase.name},
                    ),
                    connection=connection,
                )
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.handoff_created,
                    object_type="handoff",
                    object_id=snapshot.handoff.handoff_id,
                    summary="Handoff created",
                    payload_json={
                        "handoff_id": snapshot.handoff.handoff_id,
                        "from_phase_id": snapshot.handoff.from_phase_id,
                        "to_phase_id": snapshot.handoff.to_phase_id,
                    },
                ),
                connection=connection,
            )
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.runtime_task_created,
                    object_type="runtime_task",
                    object_id=snapshot.runtime_task.runtime_task_id,
                    summary="Runtime task created",
                    payload_json={
                        "runtime_task_id": snapshot.runtime_task.runtime_task_id,
                        "task_kind": snapshot.runtime_task.task_kind,
                        "summary": snapshot.runtime_task.summary,
                    },
                ),
                connection=connection,
            )
            if snapshot.domain_pack is not None and snapshot.capability_route is not None:
                self.event_repo.append(
                    RunEvent(
                        run_id=run.run_id,
                        event_type=RunEventType.domain_pack_selected,
                        object_type="domain_pack",
                        object_id=snapshot.domain_pack.domain_pack_id,
                        summary="Domain pack selected",
                        payload_json={
                            "domain_pack_id": snapshot.domain_pack.domain_pack_id,
                            "domain_pack_name": snapshot.domain_pack.name,
                            "matched_preset_id": snapshot.domain_pack.matched_preset_id,
                            "task_kind": snapshot.runtime_task.task_kind,
                            "adapter_name": snapshot.capability_route.adapter_name,
                            "operator_label": snapshot.domain_pack.runtime_projection.operator_label,
                            "capability_tags": snapshot.domain_pack.capability_exposure.capability_tags,
                            "evidence_expectations": snapshot.domain_pack.runtime_projection.evidence_expectations,
                        },
                    ),
                    connection=connection,
                )
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.run_compiled,
                    object_type="run",
                    object_id=run.run_id,
                    summary="Run recompiled",
                    payload_json={
                        "run_id": run.run_id,
                        "status": RunStatus.prepared,
                        "runtime_task_id": snapshot.runtime_task.runtime_task_id,
                    },
                ),
                connection=connection,
            )
            self._capture_run_snapshot(
                run.run_id,
                RunSnapshotStage.compiled,
                "Recompile snapshot captured",
                runtime_task_id=snapshot.runtime_task.runtime_task_id,
                connection=connection,
                payload_extra={
                    "domain_pack_id": snapshot.domain_pack.domain_pack_id if snapshot.domain_pack is not None else None,
                    "domain_pack_resolution": (
                        snapshot.domain_pack.model_dump(mode="json") if snapshot.domain_pack is not None else None
                    ),
                    "adapter_name": snapshot.capability_route.adapter_name if snapshot.capability_route is not None else None,
                    "memory_retrieval_preview": (
                        snapshot.memory_preview.model_dump(mode="json") if snapshot.memory_preview is not None else None
                    ),
                },
            )
        return PreparedRunBundle(
            run=updated_run,
            preset=preset,
            task_packet=snapshot.task_packet,
            state_ref=stored_state_ref,
            handoff=snapshot.handoff,
            domain_pack=snapshot.domain_pack,
            capability_route=snapshot.capability_route,
            memory_preview=snapshot.memory_preview,
            execution_lane=snapshot.execution_lane,
            tool_projection_manifest=snapshot.tool_projection_manifest,
            mcp_server_profiles=snapshot.mcp_server_profiles,
        )

    def prepare_run(
        self,
        run_id: str,
        task_kind: TaskKind | str | None = None,
        adapter_name: str | None = None,
        memory_item_ids: list[str] | None = None,
    ) -> PreparedRunBundle:
        return self.compile_run(
            run_id,
            task_kind=task_kind,
            adapter_name=adapter_name,
            memory_item_ids=memory_item_ids,
        )

    def cancel_run(self, run_id: str) -> Run:
        run = self.get_run(run_id)
        if run.status == RunStatus.cancelled:
            return run
        self._require_status(run, "cancel", [RunStatus.pending, RunStatus.prepared, RunStatus.awaiting_review])
        with unit_of_work(self.db_path) as connection:
            state_refs = self.runtime_state_repo.list_for_run(run.run_id, connection=connection)
            for state_ref in state_refs:
                cancelled_state = RuntimeStateRef(
                    state_ref_id=state_ref.state_ref_id,
                    run_id=state_ref.run_id,
                    runtime_task_id=state_ref.runtime_task_id,
                    graph_step=RuntimeGraphStep.cancelled,
                    state_payload={**state_ref.state_payload, "reason": "cancelled_by_operator"},
                    is_terminal=True,
                    created_at=state_ref.created_at,
                )
                cancelled_state = self._state_ref_with_durable_transition(
                    cancelled_state,
                    reason="cancelled",
                    metadata={"reason": "cancelled_by_operator"},
                )
                self.runtime_state_repo.upsert(cancelled_state, connection=connection)
            current_attempt = self.runtime_attempt_repo.current_for_run(run.run_id, connection=connection)
            if current_attempt is not None:
                self._close_runtime_attempt(
                    current_attempt,
                    status=RuntimeAttemptStatus.cancelled,
                    reason="run_cancelled",
                    connection=connection,
                )
            self._release_active_claims_for_run(
                run.run_id,
                status=RuntimeClaimStatus.released,
                reason="run_cancelled",
                connection=connection,
            )
            self._release_active_worker_leases_for_run(
                run.run_id,
                status=WorkerLeaseStatus.released,
                reason="run_cancelled",
                connection=connection,
            )
            updated_run = self._transition_run_status(run, "cancel", RunStatus.cancelled, connection=connection)
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.run_cancelled,
                    object_type="run",
                    object_id=run.run_id,
                    summary="Run cancelled",
                    payload_json={
                        "run_id": run.run_id,
                        "status": RunStatus.cancelled,
                        "reason": "cancelled_by_operator",
                    },
                ),
                connection=connection,
            )
            self._capture_run_snapshot(
                run.run_id,
                RunSnapshotStage.cancelled,
                "Cancelled snapshot captured",
                connection=connection,
            )
        self._record_lifecycle_simulation_if_triggered(
            run.run_id,
            SimulationRecordSource.lifecycle_cancelled,
        )
        return updated_run

    def approve_run_review(self, run_id: str, rationale: str = "approved by operator") -> ReviewedRunBundle:
        return self._finalize_human_review(run_id, ReviewDecision.pass_, rationale)

    def reject_run_review(self, run_id: str, rationale: str = "rejected by operator") -> ReviewedRunBundle:
        return self._finalize_human_review(run_id, ReviewDecision.fail, rationale)

    def _finalize_human_review(self, run_id: str, decision: ReviewDecision, rationale: str) -> ReviewedRunBundle:
        run = self.get_run(run_id)
        self._require_status(run, "human_review", [RunStatus.awaiting_review])
        runtime_tasks = self.task_repo.list_runtime_tasks_for_run(run.run_id)
        if not runtime_tasks:
            raise EntityNotFoundError("runtime_task", run.run_id)
        runtime_task = runtime_tasks[0]
        evidence = self.evidence_repo.get_by_task(runtime_task.runtime_task_id)
        if evidence is None:
            raise EntityNotFoundError("evidence", runtime_task.runtime_task_id)

        with unit_of_work(self.db_path) as connection:
            verdict = ReviewVerdict(
                run_id=run.run_id,
                evidence_id=evidence.evidence_id,
                decision=decision,
                rationale=rationale,
                reviewer_type=ReviewerType.human,
            )
            self.review_repo.create(verdict, connection=connection)
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.review_submitted,
                    object_type="review_verdict",
                    object_id=verdict.verdict_id,
                    summary=f"Review verdict: {verdict.decision}",
                    payload_json={
                        "verdict_id": verdict.verdict_id,
                        "decision": verdict.decision,
                    },
                ),
                connection=connection,
            )

            state_ref = self.runtime_state_repo.get_by_task(runtime_task.runtime_task_id, connection=connection)
            if state_ref is not None:
                durable_refs = self._durable_refs_for_state(state_ref)
                updated_durable_refs = (
                    self.durable_runtime_pilot.review_decision(durable_refs, decision=str(decision))
                    if durable_refs
                    else {}
                )
                terminal_step = "completed" if decision == ReviewDecision.pass_ else "failed"
                terminal_state = RuntimeStateRef(
                    state_ref_id=state_ref.state_ref_id,
                    run_id=state_ref.run_id,
                    runtime_task_id=state_ref.runtime_task_id,
                    graph_step=RuntimeGraphStep(terminal_step),
                    state_payload={
                        **state_ref.state_payload,
                        "human_review_decision": decision,
                        **updated_durable_refs,
                    },
                    is_terminal=True,
                    created_at=state_ref.created_at,
                )
                trace_id = self._export_trace(
                    run_id=run.run_id,
                    name="human_review_finalize",
                    lane_type=state_ref.state_payload.get("execution_lane", "native_deterministic"),
                    status=terminal_step,
                    attributes={
                        "runtime_task_id": runtime_task.runtime_task_id,
                        "verdict_id": verdict.verdict_id,
                        "decision": str(decision),
                    },
                )
                if trace_id is not None:
                    terminal_state = self._state_ref_with_payload_updates(
                        terminal_state,
                        {"external_trace_id": trace_id},
                    )
                terminal_state = self._state_ref_with_durable_transition(
                    terminal_state,
                    reason="human_review_terminal",
                    refs=updated_durable_refs or durable_refs or None,
                    metadata={
                        "review_decision": str(decision),
                        "verdict_id": verdict.verdict_id,
                        "reviewer_type": str(ReviewerType.human),
                    },
                )
                self.runtime_state_repo.upsert(terminal_state, connection=connection)
            current_attempt = self.runtime_attempt_repo.current_for_run(run.run_id, connection=connection)
            if current_attempt is not None:
                self._close_runtime_attempt(
                    current_attempt,
                    status=RuntimeAttemptStatus.completed if decision == ReviewDecision.pass_ else RuntimeAttemptStatus.failed,
                    reason="human_review_approved" if decision == ReviewDecision.pass_ else "human_review_rejected",
                    connection=connection,
                )

            self._release_active_worker_leases_for_run(
                run.run_id,
                status=WorkerLeaseStatus.released,
                reason="run_terminal",
                connection=connection,
            )

            terminal_status = RunStatus.completed if decision == ReviewDecision.pass_ else RunStatus.failed
            updated_run = self._transition_run_status(run, "human_review", terminal_status, connection=connection)
            terminal_event = RunEvent(
                run_id=run.run_id,
                event_type=RunEventType.run_completed if terminal_status == RunStatus.completed else RunEventType.run_failed,
                object_type="run",
                object_id=run.run_id,
                summary="Run completed" if terminal_status == RunStatus.completed else "Run failed review",
                payload_json={
                    "run_id": run.run_id,
                    "status": terminal_status,
                }
                if terminal_status == RunStatus.completed
                else {
                    "run_id": run.run_id,
                    "status": terminal_status,
                    "reason": "human_review_reject",
                },
            )
            self.event_repo.append(terminal_event, connection=connection)
            self._capture_run_snapshot(
                run.run_id,
                RunSnapshotStage.completed if terminal_status == RunStatus.completed else RunSnapshotStage.failed,
                "Human review terminal snapshot captured",
                runtime_task_id=runtime_task.runtime_task_id,
                connection=connection,
                payload_extra={"decision": str(decision)},
            )
        self._record_lifecycle_simulation_if_triggered(
            run.run_id,
            SimulationRecordSource.lifecycle_terminal,
        )
        return ReviewedRunBundle(run=updated_run, evidence=evidence, review_verdict=verdict)

    def resume_run(
        self,
        run_id: str,
        *,
        _parallel_barrier: Barrier | None = None,
        _barrier_id: str | None = None,
        _barrier_size: int | None = None,
    ) -> ExecutedRunBundle:
        run = self.get_run(run_id)
        self._require_status(run, "resume", [RunStatus.prepared])
        preset = self.preset_repo.get(run.preset_id)
        if preset is None:
            raise PresetNotFoundError(f"preset not found: {run.preset_id}")
        runtime_tasks = self.task_repo.list_runtime_tasks_for_run(run.run_id)
        if not runtime_tasks:
            raise EntityNotFoundError("runtime_task", run.run_id)
        runtime_task = runtime_tasks[0]
        task_packet = self.task_repo.get_task_packet(runtime_task.runtime_task_id)
        if task_packet is None:
            raise EntityNotFoundError("task_packet", runtime_task.runtime_task_id)

        hook_source: SimulationRecordSource | None = None
        bundle: ExecutedRunBundle | None = None
        with unit_of_work(self.db_path) as connection:
            state_ref = self.runtime_state_repo.get_by_task(runtime_task.runtime_task_id, connection=connection)
            if state_ref is None:
                raise EntityNotFoundError("runtime_state_ref", runtime_task.runtime_task_id)
            lane_type = state_ref.state_payload.get("execution_lane", task_packet.env.get("WORKFLOW_EXECUTION_LANE"))
            budget_ledger = self._ensure_budget_ledger(run, preset, connection=connection, compile_count=1)
            current_attempt = self._ensure_current_runtime_attempt(
                run.run_id,
                runtime_task.runtime_task_id,
                trigger=RuntimeAttemptTrigger.resume,
                connection=connection,
                reason_if_superseded="resume",
                force_new=True,
            )
            scheduler_submission, handoff_envelope = self._ensure_committed_scheduler_lease(
                run=run,
                runtime_task=runtime_task,
                connection=connection,
            )
            state_ref = self._state_ref_with_payload_updates(
                state_ref,
                self._scheduler_arbitration_updates(
                    state_ref,
                    control_plane_id=self.control_plane_identity.control_plane_id,
                    proposal=(
                        SchedulerLeaseProposal.model_validate(scheduler_submission["proposal"])
                        if isinstance(scheduler_submission.get("proposal"), dict)
                        else None
                    ),
                    decision=(
                        SchedulerLeaseDecision.model_validate(scheduler_submission["decision"])
                        if isinstance(scheduler_submission.get("decision"), dict)
                        else None
                    ),
                    committed_lease=scheduler_submission.get("committed_lease"),
                    term=scheduler_submission.get("term"),
                    votes=scheduler_submission.get("votes"),
                    handoff_envelope=handoff_envelope,
                    cluster=scheduler_submission.get("cluster"),
                    conflict=scheduler_submission.get("conflict"),
                ),
            )
            owner_kind, owner_id, owner_name = self._control_plane_identity()
            claim = self._acquire_runtime_claim(
                run.run_id,
                runtime_task.runtime_task_id,
                connection=connection,
                owner=owner_name,
                owner_kind=owner_kind,
                owner_id=owner_id,
                attempt_id=current_attempt.attempt_id,
            )
            resumed_state = self.runtime_gateway.resume(state_ref)
            durable_refs = self._durable_refs_for_state(resumed_state)
            if durable_refs:
                durable_refs = self.durable_runtime_pilot.checkpoint(durable_refs, reason="resume")
                resumed_state = self._state_ref_with_payload_updates(resumed_state, durable_refs)
            resumed_state = self._state_ref_with_durable_transition(
                resumed_state,
                reason="resume",
                refs=durable_refs or None,
                metadata={"phase": "resume"},
            )
            self.runtime_state_repo.upsert(resumed_state, connection=connection)
            self._transition_run_status(run, "resume", RunStatus.running, connection=connection)
            self.task_repo.update_runtime_task_status(runtime_task.runtime_task_id, TaskStatus.running, connection=connection)
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.runtime_resumed,
                    object_type="runtime_state_ref",
                    object_id=resumed_state.state_ref_id,
                    summary="Runtime resumed",
                    payload_json={
                        "run_id": run.run_id,
                        "runtime_task_id": runtime_task.runtime_task_id,
                        "graph_step": resumed_state.graph_step,
                    },
                ),
                connection=connection,
            )
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.runtime_task_started,
                    object_type="runtime_task",
                    object_id=runtime_task.runtime_task_id,
                    summary="Runtime task started",
                    payload_json={
                        "runtime_task_id": runtime_task.runtime_task_id,
                        "task_kind": runtime_task.task_kind,
                    },
                ),
                connection=connection,
            )

            brief_env = {
                key: value
                for key, value in {
                    "WORKFLOW_RUNTIME_GATEWAY_PROVIDER": resumed_state.state_payload.get("runtime_gateway_provider"),
                    "WORKFLOW_LLM_MODEL": resumed_state.state_payload.get("llm_model"),
                    "WORKFLOW_RUNTIME_BRIEF": resumed_state.state_payload.get("runtime_brief"),
                }.items()
                if value
            }
            execution_packet = TaskPacket.model_validate(
                {
                    **task_packet.model_dump(mode="json"),
                    "env": {
                        **task_packet.env,
                        **{key: str(value) for key, value in brief_env.items()},
                    },
                }
            )
            scheduler_context = self._scheduler_context_for_dispatch(
                scheduler_submission.get("committed_lease") if isinstance(scheduler_submission, dict) else None
            )

            adapter = self.worker_router.route(execution_packet)
            adapter_name = adapter.__class__.__name__.replace("Adapter", "").lower()
            worker_pool_profile = self._selected_worker_pool_profile()
            worker_name_override = worker_pool_profile.name if worker_pool_profile is not None else None
            worker_id_override = f"pool_{worker_pool_profile.worker_pool_id}" if worker_pool_profile is not None else None
            worker_kind, worker_id, worker_name = self._worker_identity(adapter_name, worker_name=worker_name_override)
            worker_lease = self._acquire_worker_lease(
                run.run_id,
                runtime_task.runtime_task_id,
                adapter_name=adapter_name,
                connection=connection,
                worker_name=worker_name,
                worker_kind=worker_kind,
                worker_id=worker_id_override or worker_id,
                claim_id=claim.claim_id,
                attempt_id=current_attempt.attempt_id,
            )
            if _parallel_barrier is not None and _barrier_id is not None and _barrier_size is not None:
                resumed_state = self._state_ref_with_payload_updates(
                    resumed_state,
                    {"parallel_batch": self._parallel_batch_payload(_barrier_id, _barrier_size, "waiting")},
                )
                self.runtime_state_repo.upsert(resumed_state, connection=connection)
                self.event_repo.append(
                    RunEvent(
                        run_id=run.run_id,
                        event_type=RunEventType.batch_barrier_waiting,
                        object_type="parallel_batch",
                        object_id=_barrier_id,
                        summary="Run is waiting on the batch barrier",
                        payload_json={
                            "run_id": run.run_id,
                            "runtime_task_id": runtime_task.runtime_task_id,
                            "barrier_id": _barrier_id,
                            "member_count": _barrier_size,
                        },
                    ),
                    connection=connection,
                )
                connection.commit()
                try:
                    _parallel_barrier.wait(timeout=30)
                except BrokenBarrierError as exc:
                    raise ParallelBarrierBrokenError(_barrier_id, run.run_id) from exc
                resumed_state = self._state_ref_with_payload_updates(
                    resumed_state,
                    {"parallel_batch": self._parallel_batch_payload(_barrier_id, _barrier_size, "released")},
                )
                self.runtime_state_repo.upsert(resumed_state, connection=connection)
                self.event_repo.append(
                    RunEvent(
                        run_id=run.run_id,
                        event_type=RunEventType.batch_barrier_released,
                        object_type="parallel_batch",
                        object_id=_barrier_id,
                        summary="Run crossed the batch barrier",
                        payload_json={
                            "run_id": run.run_id,
                            "runtime_task_id": runtime_task.runtime_task_id,
                            "barrier_id": _barrier_id,
                            "member_count": _barrier_size,
                        },
                    ),
                    connection=connection,
                )
                connection.commit()
            if preset.preset_id == "project_delivery":
                connection.commit()
                execution_result = self._execute_project_delivery_orchestration(execution_packet)
            elif worker_pool_profile is not None:
                if execution_packet.mutation_contract is not None and execution_packet.mutation_contract.mutation_mode == MutationMode.patch_apply:
                    raise MutationContractError(
                        "repo mutation tasks must run against the local workspace and cannot be dispatched to worker pools",
                        {"worker_pool_id": worker_pool_profile.worker_pool_id},
                    )
                if worker_pool_profile.dispatch_mode == "remote_http":
                    connection.commit()
                dispatch_result = self.external_worker_gateway.dispatch(
                    packet=execution_packet,
                    profile=worker_pool_profile,
                    lease_id=worker_lease.lease_id,
                    launch_local=adapter.launch,
                    scheduler_context=scheduler_context,
                )
                execution_result = dispatch_result.execution_result
                if worker_pool_profile.dispatch_mode == "remote_http":
                    refreshed_state = self.runtime_state_repo.get_by_task(runtime_task.runtime_task_id, connection=connection)
                    if refreshed_state is not None:
                        resumed_state = refreshed_state
                self.event_repo.append(
                    RunEvent(
                        run_id=run.run_id,
                        event_type=RunEventType.worker_dispatch_accepted,
                        object_type="worker_lease",
                        object_id=worker_lease.lease_id,
                        summary="Worker dispatch accepted",
                        payload_json={
                            "run_id": run.run_id,
                            "runtime_task_id": runtime_task.runtime_task_id,
                            "lease_id": worker_lease.lease_id,
                            "worker_pool_id": worker_pool_profile.worker_pool_id,
                            "dispatch_id": dispatch_result.execution_target.dispatch_id,
                        },
                    ),
                    connection=connection,
                )
            else:
                execution_result = self._execute_repo_mutation(adapter, execution_packet)
            if isinstance(execution_result.metadata.get("execution_target"), dict):
                resumed_state = self._state_ref_with_payload_updates(
                    resumed_state,
                    {"execution_target": execution_result.metadata["execution_target"]},
                )
            if isinstance(execution_result.metadata.get("lease_renewals"), list):
                resumed_state = self._state_ref_with_payload_updates(
                    resumed_state,
                    {"lease_renewals": execution_result.metadata["lease_renewals"]},
                )
            if isinstance(execution_result.metadata.get("mutation_result"), dict):
                resumed_state = self._state_ref_with_payload_updates(
                    resumed_state,
                    {
                        "mutation_contract": execution_result.metadata.get("mutation_contract"),
                        "mutation_result": execution_result.metadata["mutation_result"],
                    },
                )
            completed_status = TaskStatus.completed if execution_result.return_code == 0 else TaskStatus.failed
            self.task_repo.update_runtime_task_status(runtime_task.runtime_task_id, completed_status, connection=connection)
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.runtime_task_completed,
                    object_type="runtime_task",
                    object_id=runtime_task.runtime_task_id,
                    summary="Runtime task completed",
                    payload_json={
                        "runtime_task_id": runtime_task.runtime_task_id,
                        "return_code": execution_result.return_code,
                        "duration_ms": execution_result.duration_ms,
                    },
                ),
                connection=connection,
            )

            evidence = self.evidence_builder.build(run.run_id, runtime_task.runtime_task_id, execution_result)
            self.evidence_repo.create(evidence, connection=connection)
            self.budget_repo.update(
                BudgetLedger.model_validate(
                    {
                        **budget_ledger.model_dump(mode="json"),
                        "execution_count": budget_ledger.execution_count + 1,
                        "total_runtime_ms": budget_ledger.total_runtime_ms + execution_result.duration_ms,
                        "last_return_code": execution_result.return_code,
                        "updated_at": self._utc_now().isoformat(),
                    }
                ),
                connection=connection,
            )
            self.event_repo.append(
                RunEvent(
                    run_id=run.run_id,
                    event_type=RunEventType.evidence_submitted,
                    object_type="evidence",
                    object_id=evidence.evidence_id,
                    summary=evidence.summary,
                    payload_json={"evidence_id": evidence.evidence_id, "summary": evidence.summary},
                ),
                connection=connection,
            )

            review_policy = ReviewPolicy(preset.default_review_policy)

            if review_policy == ReviewPolicy.human_required:
                self._release_worker_lease(
                    worker_lease,
                    status=WorkerLeaseStatus.released,
                    reason="awaiting_human_review",
                    connection=connection,
                )
                awaiting_payload = {
                    **resumed_state.state_payload,
                    "review_policy": preset.default_review_policy,
                    "return_code": execution_result.return_code,
                }
                checkpoint_refs = self._durable_refs_for_state(resumed_state)
                if checkpoint_refs:
                    awaiting_payload.update(
                        self.durable_runtime_pilot.checkpoint(checkpoint_refs, reason="awaiting_review")
                    )
                awaiting_state = RuntimeStateRef(
                    state_ref_id=resumed_state.state_ref_id,
                    run_id=run.run_id,
                    runtime_task_id=runtime_task.runtime_task_id,
                    graph_step=RuntimeGraphStep.awaiting_review,
                    state_payload=awaiting_payload,
                    is_terminal=False,
                    created_at=resumed_state.created_at,
                )
                trace_id = self._export_trace(
                    run_id=run.run_id,
                    name="awaiting_review",
                    lane_type=lane_type,
                    status=RunStatus.awaiting_review,
                    attributes={
                        "runtime_task_id": runtime_task.runtime_task_id,
                        "evidence_id": evidence.evidence_id,
                    },
                )
                if trace_id is not None:
                    awaiting_state = self._state_ref_with_payload_updates(
                        awaiting_state,
                        {"external_trace_id": trace_id},
                    )
                awaiting_state = self._state_ref_with_durable_transition(
                    awaiting_state,
                    reason="awaiting_review",
                    refs=self._durable_refs_for_state(awaiting_state),
                    metadata={
                        "review_policy": str(preset.default_review_policy),
                        "awaiting_review_reason": "human_required",
                        "return_code": execution_result.return_code,
                    },
                )
                self.runtime_state_repo.upsert(awaiting_state, connection=connection)
                self._release_active_claims_for_run(
                    run.run_id,
                    status=RuntimeClaimStatus.released,
                    reason="awaiting_human_review",
                    connection=connection,
                )
                updated_run = self._transition_run_status(
                    Run.model_validate({**run.model_dump(mode="json"), "status": RunStatus.running}),
                    "request_human_review",
                    RunStatus.awaiting_review,
                    connection=connection,
                )
                self.event_repo.append(
                    RunEvent(
                        run_id=run.run_id,
                        event_type=RunEventType.review_requested,
                        object_type="run",
                        object_id=run.run_id,
                        summary="Human review requested",
                        payload_json={
                            "run_id": run.run_id,
                            "policy": preset.default_review_policy,
                            "status": RunStatus.awaiting_review,
                        },
                    ),
                    connection=connection,
                )
                self._capture_run_snapshot(
                    run.run_id,
                    RunSnapshotStage.awaiting_review,
                    "Awaiting-review snapshot captured",
                    runtime_task_id=runtime_task.runtime_task_id,
                    connection=connection,
                    payload_extra={"review_policy": str(preset.default_review_policy)},
                )
                hook_source = SimulationRecordSource.lifecycle_awaiting_review
                bundle = ExecutedRunBundle(
                    run=updated_run,
                    execution_result=execution_result,
                    evidence=evidence,
                    review_verdict=None,
                )
            else:
                review_verdict = self.auto_review.review(evidence)
                self.review_repo.create(review_verdict, connection=connection)
                self.event_repo.append(
                    RunEvent(
                        run_id=run.run_id,
                        event_type=RunEventType.review_submitted,
                        object_type="review_verdict",
                        object_id=review_verdict.verdict_id,
                        summary=f"Review verdict: {review_verdict.decision}",
                        payload_json={
                            "verdict_id": review_verdict.verdict_id,
                            "decision": review_verdict.decision,
                        },
                    ),
                    connection=connection,
                )

                if review_policy == ReviewPolicy.mandatory or (
                    review_policy == ReviewPolicy.recommended and review_verdict.decision == ReviewDecision.fail
                ):
                    awaiting_reason = (
                        "mandatory_human_signoff"
                        if review_policy == ReviewPolicy.mandatory
                        else "recommended_auto_review_failed"
                    )
                    self._release_worker_lease(
                        worker_lease,
                        status=WorkerLeaseStatus.released,
                        reason="awaiting_human_review",
                        connection=connection,
                    )
                    awaiting_payload = {
                        **resumed_state.state_payload,
                        "review_policy": preset.default_review_policy,
                        "return_code": execution_result.return_code,
                        "awaiting_review_reason": awaiting_reason,
                        "latest_auto_review_decision": review_verdict.decision,
                    }
                    checkpoint_refs = self._durable_refs_for_state(resumed_state)
                    if checkpoint_refs:
                        awaiting_payload.update(
                            self.durable_runtime_pilot.checkpoint(checkpoint_refs, reason="awaiting_review")
                        )
                    awaiting_state = RuntimeStateRef(
                        state_ref_id=resumed_state.state_ref_id,
                        run_id=run.run_id,
                        runtime_task_id=runtime_task.runtime_task_id,
                        graph_step=RuntimeGraphStep.awaiting_review,
                        state_payload=awaiting_payload,
                        is_terminal=False,
                        created_at=resumed_state.created_at,
                    )
                    trace_id = self._export_trace(
                        run_id=run.run_id,
                        name="awaiting_review",
                        lane_type=lane_type,
                        status=RunStatus.awaiting_review,
                        attributes={
                            "runtime_task_id": runtime_task.runtime_task_id,
                            "evidence_id": evidence.evidence_id,
                            "verdict_id": review_verdict.verdict_id,
                        },
                    )
                    if trace_id is not None:
                        awaiting_state = self._state_ref_with_payload_updates(
                            awaiting_state,
                            {"external_trace_id": trace_id},
                        )
                    awaiting_state = self._state_ref_with_durable_transition(
                        awaiting_state,
                        reason="awaiting_review",
                        refs=self._durable_refs_for_state(awaiting_state),
                        metadata={
                            "review_policy": str(preset.default_review_policy),
                            "awaiting_review_reason": awaiting_reason,
                            "return_code": execution_result.return_code,
                            "review_decision": str(review_verdict.decision),
                            "verdict_id": review_verdict.verdict_id,
                        },
                    )
                    self.runtime_state_repo.upsert(awaiting_state, connection=connection)
                    self._release_active_claims_for_run(
                        run.run_id,
                        status=RuntimeClaimStatus.released,
                        reason="awaiting_human_review",
                        connection=connection,
                    )
                    updated_run = self._transition_run_status(
                        Run.model_validate({**run.model_dump(mode="json"), "status": RunStatus.running}),
                        "request_human_review",
                        RunStatus.awaiting_review,
                        connection=connection,
                    )
                    self.event_repo.append(
                        RunEvent(
                            run_id=run.run_id,
                            event_type=RunEventType.review_requested,
                            object_type="run",
                            object_id=run.run_id,
                            summary="Human review requested",
                            payload_json={
                                "run_id": run.run_id,
                                "policy": preset.default_review_policy,
                                "status": RunStatus.awaiting_review,
                            },
                        ),
                        connection=connection,
                    )
                    self._capture_run_snapshot(
                        run.run_id,
                        RunSnapshotStage.awaiting_review,
                        "Awaiting-review snapshot captured",
                        runtime_task_id=runtime_task.runtime_task_id,
                        connection=connection,
                        payload_extra={
                            "review_policy": str(preset.default_review_policy),
                            "awaiting_review_reason": awaiting_reason,
                            "latest_auto_review_decision": str(review_verdict.decision),
                        },
                    )
                    hook_source = SimulationRecordSource.lifecycle_awaiting_review
                    bundle = ExecutedRunBundle(
                        run=updated_run,
                        execution_result=execution_result,
                        evidence=evidence,
                        review_verdict=review_verdict,
                    )
                else:
                    if review_policy == ReviewPolicy.optional:
                        final_status = RunStatus.completed if execution_result.return_code == 0 else RunStatus.failed
                        if final_status == RunStatus.completed:
                            terminal_event = RunEvent(
                                run_id=run.run_id,
                                event_type=RunEventType.run_completed,
                                object_type="run",
                                object_id=run.run_id,
                                summary="Run completed",
                                payload_json={"run_id": run.run_id, "status": RunStatus.completed},
                            )
                            terminal_graph_step = RuntimeGraphStep.completed
                        else:
                            terminal_event = RunEvent(
                                run_id=run.run_id,
                                event_type=RunEventType.run_failed,
                                object_type="run",
                                object_id=run.run_id,
                                summary="Run failed during execution",
                                payload_json={
                                    "run_id": run.run_id,
                                    "status": RunStatus.failed,
                                    "reason": "runtime_return_code_non_zero",
                                },
                            )
                            terminal_graph_step = RuntimeGraphStep.failed
                    elif review_verdict.decision == ReviewDecision.pass_:
                        final_status = RunStatus.completed
                        terminal_event = RunEvent(
                            run_id=run.run_id,
                            event_type=RunEventType.run_completed,
                            object_type="run",
                            object_id=run.run_id,
                            summary="Run completed",
                            payload_json={"run_id": run.run_id, "status": RunStatus.completed},
                        )
                        terminal_graph_step = RuntimeGraphStep.completed
                    else:
                        final_status = RunStatus.failed
                        terminal_event = RunEvent(
                            run_id=run.run_id,
                            event_type=RunEventType.run_failed,
                            object_type="run",
                            object_id=run.run_id,
                            summary="Run failed review",
                            payload_json={
                                "run_id": run.run_id,
                                "status": RunStatus.failed,
                                "reason": "auto_review_fail",
                            },
                        )
                        terminal_graph_step = RuntimeGraphStep.failed

                    terminal_payload = {
                        **resumed_state.state_payload,
                        "review_policy": preset.default_review_policy,
                        "return_code": execution_result.return_code,
                        "latest_auto_review_decision": str(review_verdict.decision),
                    }
                    if review_policy == ReviewPolicy.optional:
                        terminal_payload["review_effect"] = "advisory_only"
                    checkpoint_refs = self._durable_refs_for_state(resumed_state)
                    if checkpoint_refs:
                        terminal_payload.update(
                            self.durable_runtime_pilot.checkpoint(checkpoint_refs, reason="terminal")
                        )
                    terminal_state = RuntimeStateRef(
                        state_ref_id=resumed_state.state_ref_id,
                        run_id=run.run_id,
                        runtime_task_id=runtime_task.runtime_task_id,
                        graph_step=terminal_graph_step,
                        state_payload=terminal_payload,
                        is_terminal=True,
                        created_at=resumed_state.created_at,
                    )
                    trace_id = self._export_trace(
                        run_id=run.run_id,
                        name="run_terminal",
                        lane_type=lane_type,
                        status=final_status,
                        attributes={
                            "runtime_task_id": runtime_task.runtime_task_id,
                            "evidence_id": evidence.evidence_id,
                            "verdict_id": review_verdict.verdict_id,
                            "adapter_name": adapter.normalized_name(),
                        },
                    )
                    if trace_id is not None:
                        terminal_state = self._state_ref_with_payload_updates(
                            terminal_state,
                            {"external_trace_id": trace_id},
                        )
                    terminal_state = self._state_ref_with_durable_transition(
                        terminal_state,
                        reason="terminal",
                        refs=self._durable_refs_for_state(terminal_state),
                        metadata={
                            "review_policy": str(preset.default_review_policy),
                            "return_code": execution_result.return_code,
                            "review_decision": str(review_verdict.decision),
                            "verdict_id": review_verdict.verdict_id,
                        },
                    )
                    self.runtime_state_repo.upsert(terminal_state, connection=connection)
                    current_attempt = self.runtime_attempt_repo.current_for_run(run.run_id, connection=connection)
                    if current_attempt is not None:
                        close_reason = (
                            "optional_advisory_terminal"
                            if review_policy == ReviewPolicy.optional and final_status == RunStatus.completed
                            else "runtime_return_code_non_zero"
                            if review_policy == ReviewPolicy.optional
                            else "auto_review_passed"
                            if final_status == RunStatus.completed
                            else "auto_review_failed"
                        )
                        self._close_runtime_attempt(
                            current_attempt,
                            status=RuntimeAttemptStatus.completed
                            if final_status == RunStatus.completed
                            else RuntimeAttemptStatus.failed,
                            reason=close_reason,
                            connection=connection,
                        )
                    self._release_worker_lease(
                        worker_lease,
                        status=WorkerLeaseStatus.released,
                        reason="run_terminal",
                        connection=connection,
                    )
                    self._release_active_claims_for_run(
                        run.run_id,
                        status=RuntimeClaimStatus.released,
                        reason="run_terminal",
                        connection=connection,
                    )
                    updated_run = self._transition_run_status(
                        Run.model_validate({**run.model_dump(mode="json"), "status": RunStatus.running}),
                        "auto_review_finalize",
                        final_status,
                        connection=connection,
                    )
                    self.event_repo.append(terminal_event, connection=connection)
                    self._capture_run_snapshot(
                        run.run_id,
                        RunSnapshotStage.completed if final_status == RunStatus.completed else RunSnapshotStage.failed,
                        "Auto terminal snapshot captured",
                        runtime_task_id=runtime_task.runtime_task_id,
                        connection=connection,
                        payload_extra={"decision": str(review_verdict.decision)},
                    )
                    hook_source = SimulationRecordSource.lifecycle_terminal
                    bundle = ExecutedRunBundle(
                        run=updated_run,
                        execution_result=execution_result,
                        evidence=evidence,
                        review_verdict=review_verdict,
                    )
        if hook_source is not None:
            self._record_lifecycle_simulation_if_triggered(run.run_id, hook_source)
        if bundle is None:
            raise RuntimeError(f"resume_run did not produce a terminal or awaiting-review bundle for {run.run_id}")
        return bundle

    def execute_run(self, run_id: str) -> ExecutedRunBundle:
        return self.resume_run(run_id)

    def resume_runs_parallel(self, run_ids: list[str], *, max_workers: int | None = None) -> dict[str, Any]:
        normalized_run_ids: list[str] = []
        seen: set[str] = set()
        for run_id in run_ids:
            if run_id not in seen:
                normalized_run_ids.append(run_id)
                seen.add(run_id)
        barrier_id = new_id("barrier")
        if not normalized_run_ids:
            return {
                "barrier_id": barrier_id,
                "member_count": 0,
                "max_workers": 0,
                "status": "completed",
                "results": [],
                "errors": [],
            }

        worker_count = min(max_workers or len(normalized_run_ids), len(normalized_run_ids))
        sync_barrier = Barrier(len(normalized_run_ids))
        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        def _resume_one(target_run_id: str) -> dict[str, Any]:
            try:
                bundle = self.resume_run(
                    target_run_id,
                    _parallel_barrier=sync_barrier,
                    _barrier_id=barrier_id,
                    _barrier_size=len(normalized_run_ids),
                )
            except Exception:
                try:
                    sync_barrier.abort()
                except Exception:
                    pass
                raise
            return {
                "run": bundle.run.model_dump(mode="json"),
                "evidence_id": bundle.evidence.evidence_id,
                "review_decision": bundle.review_verdict.decision if bundle.review_verdict is not None else None,
            }

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {executor.submit(_resume_one, run_id): run_id for run_id in normalized_run_ids}
            for future in as_completed(future_map):
                run_id = future_map[future]
                try:
                    results.append(future.result())
                except WorkflowError as exc:
                    errors.append(
                        {
                            "run_id": run_id,
                            "code": exc.code,
                            "message": exc.message,
                            "details": exc.details,
                        }
                    )
                except Exception as exc:
                    errors.append(
                        {
                            "run_id": run_id,
                            "code": "unexpected_parallel_batch_error",
                            "message": str(exc),
                            "details": {},
                        }
                    )

        results.sort(key=lambda item: item["run"]["run_id"])
        errors.sort(key=lambda item: item["run_id"])
        return {
            "barrier_id": barrier_id,
            "member_count": len(normalized_run_ids),
            "max_workers": worker_count,
            "status": "completed" if not errors else "failed",
            "results": results,
            "errors": errors,
        }
