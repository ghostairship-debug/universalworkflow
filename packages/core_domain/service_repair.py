from __future__ import annotations

from typing import Any

from packages.contracts import (
    Run,
    RunEvent,
    RunEventType,
    RunSnapshot,
    RunSnapshotStage,
    RuntimeAttemptStatus,
    RuntimeAttemptTrigger,
    RuntimeClaimStatus,
    RuntimeGraphStep,
    RuntimeStateRef,
    RunStatus,
    TaskKind,
    TaskStatus,
    WorkerLeaseStatus,
)
from packages.core_domain.db import unit_of_work
from packages.core_domain.errors import (
    RepairActionNotAvailableError,
    UnsupportedRepairActionError,
)
from packages.core_domain.service_types import (
    RunDiagnosticContext,
)




class RepairServiceMixin:
    def _recoverability_hint_for(
        self,
        context: RunDiagnosticContext,
        problems: list[dict[str, Any]] | None = None,
    ) -> str:
        if problems:
            return str(problems[0]["next_action"])
        status = str(context.run.status)
        if status == RunStatus.pending:
            return "compile_run"
        if status == RunStatus.prepared:
            return "resume_run"
        if status == RunStatus.awaiting_review:
            return "approve_or_reject_review"
        if status == RunStatus.failed:
            return "inspect_evidence_then_recompile"
        if status == RunStatus.cancelled:
            return "create_new_run"
        return "none"

    def _available_repair_actions(self, problems: list[dict[str, Any]]) -> list[str]:
        return [
            str(problem["repair_action"])
            for problem in problems
            if problem.get("repairable") and problem.get("repair_action") is not None
        ]

    def _failure_taxonomy_for(self, detail: dict[str, Any], inspection: dict[str, Any]) -> dict[str, Any]:
        run_status = str(detail["run"]["status"])
        failure_reason = detail.get("failure_reason")
        waiting_reason = detail.get("waiting_reason")
        problem_codes = [str(problem["problem"]) for problem in inspection["problems"]]

        if inspection["problem_count"] > 0:
            category = "inconsistent_state"
            primary_reason = problem_codes[0]
            is_failure = True
        elif run_status == RunStatus.completed:
            category = "success"
            primary_reason = "completed"
            is_failure = False
        elif run_status == RunStatus.failed:
            category = "review_failure" if failure_reason in {"human_review_rejected", "auto_review_failed"} else "runtime_failure"
            primary_reason = failure_reason or "run_failed"
            is_failure = True
        elif run_status == RunStatus.cancelled:
            category = "operator_cancelled"
            primary_reason = "cancelled_by_operator"
            is_failure = True
        elif run_status == RunStatus.awaiting_review:
            category = "review_pending"
            primary_reason = waiting_reason or "awaiting_human_review"
            is_failure = False
        else:
            category = "pending_work"
            primary_reason = waiting_reason or detail.get("next_action") or "awaiting_progress"
            is_failure = False

        return {
            "category": category,
            "primary_reason": primary_reason,
            "is_failure": is_failure,
            "is_terminal": run_status in {RunStatus.completed, RunStatus.failed, RunStatus.cancelled},
            "problem_codes": problem_codes,
        }

    def _select_repair_problem(self, run_id: str, problems: list[dict[str, Any]], action: str | None) -> dict[str, Any]:
        available_actions = self._available_repair_actions(problems)
        if action is not None and action not in self.SUPPORTED_REPAIR_ACTIONS:
            raise UnsupportedRepairActionError(action, list(self.SUPPORTED_REPAIR_ACTIONS))
        if not available_actions:
            raise RepairActionNotAvailableError(run_id, action, available_actions)
        selected_action = action or available_actions[0]
        for problem in problems:
            if problem.get("repairable") and problem.get("repair_action") == selected_action:
                return problem
        raise RepairActionNotAvailableError(run_id, selected_action, available_actions)

    def _runtime_terminal_graph_step_for_run_status(self, run_status: RunStatus | str) -> RuntimeGraphStep:
        normalized = RunStatus(run_status)
        mapping = {
            RunStatus.completed: RuntimeGraphStep.completed,
            RunStatus.failed: RuntimeGraphStep.failed,
            RunStatus.cancelled: RuntimeGraphStep.cancelled,
        }
        return mapping[normalized]

    def _task_terminal_status_for_run_status(self, run_status: RunStatus | str) -> TaskStatus:
        normalized = RunStatus(run_status)
        mapping = {
            RunStatus.completed: TaskStatus.completed,
            RunStatus.failed: TaskStatus.failed,
            RunStatus.cancelled: TaskStatus.cancelled,
        }
        return mapping[normalized]

    def _append_repair_event(
        self,
        run_id: str,
        action: str,
        problem: str,
        repaired_runtime_task_ids: list[str],
        *,
        connection=None,
    ) -> None:
        self.event_repo.append(
            RunEvent(
                run_id=run_id,
                event_type=RunEventType.repair_applied,
                object_type="run",
                object_id=run_id,
                summary=f"Repair applied: {action}",
                payload_json={
                    "run_id": run_id,
                    "action": action,
                    "problem": problem,
                    "repaired_runtime_task_ids": repaired_runtime_task_ids,
                },
            ),
            connection=connection,
        )

    def _capture_run_snapshot(
        self,
        run_id: str,
        stage: RunSnapshotStage | str,
        summary: str,
        *,
        runtime_task_id: str | None = None,
        connection=None,
        payload_extra: dict[str, Any] | None = None,
    ) -> RunSnapshot:
        context = self._load_run_context(run_id, connection=connection)
        last_runtime_state = self._last_runtime_state(context)
        last_attempt = self._last_attempt(context)
        current_attempt = self._current_attempt(context)
        last_claim = self._last_claim(context)
        last_worker_lease = self._last_worker_lease(context)
        review_policy = self._review_policy_for_context(context, last_runtime_state=last_runtime_state)
        snapshot = RunSnapshot(
            run_id=run_id,
            stage=RunSnapshotStage(stage),
            run_status=context.run.status,
            runtime_task_id=runtime_task_id or (context.runtime_tasks[0].runtime_task_id if context.runtime_tasks else None),
            summary=summary,
            snapshot_payload={
                "effective_review_state": self._effective_review_state(
                    context.run,
                    context.latest_review_verdict,
                    review_policy,
                ),
                "review_policy": review_policy,
                "runtime_task_ids": [task.runtime_task_id for task in context.runtime_tasks],
                "latest_runtime_graph_step": str(last_runtime_state.graph_step) if last_runtime_state is not None else None,
                "latest_runtime_state_ref_id": last_runtime_state.state_ref_id if last_runtime_state is not None else None,
                "durable_lineage": self._durable_lineage_for_state(last_runtime_state),
                "latest_attempt_id": last_attempt.attempt_id if last_attempt is not None else None,
                "current_attempt_id": current_attempt.attempt_id if current_attempt is not None else None,
                "latest_review_verdict_id": (
                    context.latest_review_verdict.verdict_id if context.latest_review_verdict is not None else None
                ),
                "latest_claim_id": last_claim.claim_id if last_claim is not None else None,
                "active_claim_ids": [claim.claim_id for claim in self._active_claims_for(context)],
                "latest_worker_lease_id": last_worker_lease.lease_id if last_worker_lease is not None else None,
                "active_worker_lease_ids": [lease.lease_id for lease in self._active_worker_leases_for(context)],
                **(payload_extra or {}),
            },
        )
        self.snapshot_repo.create(snapshot, connection=connection)
        self.event_repo.append(
            RunEvent(
                run_id=run_id,
                event_type=RunEventType.run_snapshot_created,
                object_type="run_snapshot",
                object_id=snapshot.snapshot_id,
                summary=summary,
                payload_json={
                    "run_id": run_id,
                    "snapshot_id": snapshot.snapshot_id,
                    "stage": snapshot.stage,
                    "run_status": snapshot.run_status,
                    "runtime_task_id": snapshot.runtime_task_id,
                },
            ),
            connection=connection,
        )
        return snapshot

    def _task_kind_for_recompile(self, run_id: str) -> TaskKind | str | None:
        runtime_tasks = self.task_repo.list_runtime_tasks_for_run(run_id)
        if runtime_tasks:
            return runtime_tasks[0].task_kind
        timeline = self.get_timeline(run_id)
        for event in reversed(timeline):
            if event.event_type == RunEventType.runtime_task_created:
                task_kind = event.payload_json.get("task_kind")
                if task_kind is not None:
                    return task_kind
        return None

    def _apply_align_terminal_runtime_state(self, run: Run, action: str, problem: str) -> list[str]:
        with unit_of_work(self.db_path) as connection:
            live_states = self.runtime_state_repo.list_live_for_run(run.run_id, connection=connection)
            if not live_states:
                raise RepairActionNotAvailableError(run.run_id, action, [action])
            target_graph_step = self._runtime_terminal_graph_step_for_run_status(run.status)
            target_task_status = self._task_terminal_status_for_run_status(run.status)
            repaired_runtime_task_ids: list[str] = []
            for state_ref in live_states:
                repaired_state = RuntimeStateRef(
                    state_ref_id=state_ref.state_ref_id,
                    run_id=state_ref.run_id,
                    runtime_task_id=state_ref.runtime_task_id,
                    graph_step=target_graph_step,
                    state_payload={
                        **state_ref.state_payload,
                        "repaired_action": action,
                        "repaired_problem": problem,
                    },
                    is_terminal=True,
                    created_at=state_ref.created_at,
                )
                self.runtime_state_repo.upsert(repaired_state, connection=connection)
                self.task_repo.update_runtime_task_status(
                    state_ref.runtime_task_id,
                    target_task_status,
                    connection=connection,
                )
                repaired_runtime_task_ids.append(state_ref.runtime_task_id)
            self._append_repair_event(
                run.run_id,
                action,
                problem,
                repaired_runtime_task_ids,
                connection=connection,
            )
        return repaired_runtime_task_ids

    def _apply_recompile_prepared_run(self, run_id: str, action: str, problem: str) -> list[str]:
        task_kind = self._task_kind_for_recompile(run_id)
        prepared = self.recompile_run(run_id, task_kind=task_kind, ignore_budget=True)
        self._append_repair_event(
            run_id,
            action,
            problem,
            [prepared.task_packet.runtime_task_id],
        )
        return [prepared.task_packet.runtime_task_id]

    def _apply_claim_release_repair(
        self,
        run_id: str,
        action: str,
        problem: str,
        *,
        status: RuntimeClaimStatus | str,
        reason: str,
    ) -> list[str]:
        with unit_of_work(self.db_path) as connection:
            active_claims = self.runtime_claim_repo.list_active_for_run(run_id, connection=connection)
            if not active_claims:
                raise RepairActionNotAvailableError(run_id, action, [action])
            repaired_runtime_task_ids: list[str] = []
            for claim in active_claims:
                self._release_runtime_claim(
                    claim,
                    status=status,
                    reason=reason,
                    connection=connection,
                )
                repaired_runtime_task_ids.append(claim.runtime_task_id)
            self._append_repair_event(
                run_id,
                action,
                problem,
                repaired_runtime_task_ids,
                connection=connection,
            )
        return repaired_runtime_task_ids

    def _apply_worker_lease_release_repair(
        self,
        run_id: str,
        action: str,
        problem: str,
        *,
        status: WorkerLeaseStatus | str,
        reason: str,
    ) -> list[str]:
        with unit_of_work(self.db_path) as connection:
            active_leases = self.worker_lease_repo.list_active_for_run(run_id, connection=connection)
            if not active_leases:
                raise RepairActionNotAvailableError(run_id, action, [action])
            repaired_runtime_task_ids: list[str] = []
            for lease in active_leases:
                self._release_worker_lease(
                    lease,
                    status=status,
                    reason=reason,
                    connection=connection,
                )
                repaired_runtime_task_ids.append(lease.runtime_task_id)
            self._append_repair_event(
                run_id,
                action,
                problem,
                repaired_runtime_task_ids,
                connection=connection,
            )
        return repaired_runtime_task_ids

    def _apply_close_current_attempt_terminal(
        self,
        run: Run,
        action: str,
        problem: str,
    ) -> list[str]:
        with unit_of_work(self.db_path) as connection:
            current_attempt = self.runtime_attempt_repo.current_for_run(run.run_id, connection=connection)
            if current_attempt is None:
                raise RepairActionNotAvailableError(run.run_id, action, [action])
            status_mapping = {
                RunStatus.completed: RuntimeAttemptStatus.completed,
                RunStatus.failed: RuntimeAttemptStatus.failed,
                RunStatus.cancelled: RuntimeAttemptStatus.cancelled,
            }
            close_reason_mapping = {
                RunStatus.completed: "reconciled_terminal_run_completed",
                RunStatus.failed: "reconciled_terminal_run_failed",
                RunStatus.cancelled: "reconciled_terminal_run_cancelled",
            }
            attempt_status = status_mapping[RunStatus(run.status)]
            self._close_runtime_attempt(
                current_attempt,
                status=attempt_status,
                reason=close_reason_mapping[RunStatus(run.status)],
                connection=connection,
            )
            repaired_runtime_task_ids = [current_attempt.runtime_task_id]
            self._append_repair_event(
                run.run_id,
                action,
                problem,
                repaired_runtime_task_ids,
                connection=connection,
            )
        return repaired_runtime_task_ids

    def _apply_interrupt_current_attempt(
        self,
        run_id: str,
        action: str,
        problem: str,
    ) -> list[str]:
        with unit_of_work(self.db_path) as connection:
            current_attempt = self.runtime_attempt_repo.current_for_run(run_id, connection=connection)
            if current_attempt is None:
                raise RepairActionNotAvailableError(run_id, action, [action])
            self._close_runtime_attempt(
                current_attempt,
                status=RuntimeAttemptStatus.interrupted,
                reason=f"reconciled_{problem}",
                connection=connection,
            )
            repaired_runtime_task_ids = [current_attempt.runtime_task_id]
            self._append_repair_event(
                run_id,
                action,
                problem,
                repaired_runtime_task_ids,
                connection=connection,
            )
        return repaired_runtime_task_ids

    def _apply_create_repair_attempt(
        self,
        run_id: str,
        action: str,
        problem: str,
    ) -> list[str]:
        with unit_of_work(self.db_path) as connection:
            run_context = self._load_run_context(run_id, connection=connection)
            if self._current_attempt(run_context) is not None or not run_context.runtime_tasks:
                raise RepairActionNotAvailableError(run_id, action, [action])
            runtime_task = run_context.runtime_tasks[0]
            self._ensure_current_runtime_attempt(
                run_id,
                runtime_task.runtime_task_id,
                trigger=RuntimeAttemptTrigger.repair,
                connection=connection,
                reason_if_superseded="repair_recreated_current_attempt",
            )
            repaired_runtime_task_ids = [runtime_task.runtime_task_id]
            self._append_repair_event(
                run_id,
                action,
                problem,
                repaired_runtime_task_ids,
                connection=connection,
            )

    def apply_run_repair(self, run_id: str, action: str | None = None) -> dict[str, Any]:
        run = self.get_run(run_id)
        inspection_before = self.inspect_run_state(run_id)
        selected_problem = self._select_repair_problem(run_id, inspection_before["problems"], action)
        selected_action = str(selected_problem["repair_action"])

        if selected_action == "align_completed_runtime_state":
            repaired_runtime_task_ids = self._apply_align_terminal_runtime_state(
                run,
                selected_action,
                str(selected_problem["problem"]),
            )
        elif selected_action == "align_cancelled_runtime_state":
            repaired_runtime_task_ids = self._apply_align_terminal_runtime_state(
                run,
                selected_action,
                str(selected_problem["problem"]),
            )
        elif selected_action == "close_current_runtime_attempt_terminal":
            repaired_runtime_task_ids = self._apply_close_current_attempt_terminal(
                run,
                selected_action,
                str(selected_problem["problem"]),
            )
        elif selected_action == "create_repair_runtime_attempt":
            repaired_runtime_task_ids = self._apply_create_repair_attempt(
                run_id,
                selected_action,
                str(selected_problem["problem"]),
            )
        elif selected_action == "recompile_prepared_run":
            repaired_runtime_task_ids = self._apply_recompile_prepared_run(
                run_id,
                selected_action,
                str(selected_problem["problem"]),
            )
        elif selected_action == "interrupt_current_runtime_attempt":
            repaired_runtime_task_ids = self._apply_interrupt_current_attempt(
                run_id,
                selected_action,
                str(selected_problem["problem"]),
            )
        elif selected_action == "release_runtime_claim":
            repaired_runtime_task_ids = self._apply_claim_release_repair(
                run_id,
                selected_action,
                str(selected_problem["problem"]),
                status=RuntimeClaimStatus.released,
                reason="reconciled_non_running_active_claim",
            )
        elif selected_action == "expire_runtime_claim":
            repaired_runtime_task_ids = self._apply_claim_release_repair(
                run_id,
                selected_action,
                str(selected_problem["problem"]),
                status=RuntimeClaimStatus.expired,
                reason="reconciled_expired_claim",
            )
        elif selected_action == "release_worker_lease":
            repaired_runtime_task_ids = self._apply_worker_lease_release_repair(
                run_id,
                selected_action,
                str(selected_problem["problem"]),
                status=WorkerLeaseStatus.released,
                reason="reconciled_non_running_active_worker_lease",
            )
        elif selected_action == "expire_worker_lease":
            repaired_runtime_task_ids = self._apply_worker_lease_release_repair(
                run_id,
                selected_action,
                str(selected_problem["problem"]),
                status=WorkerLeaseStatus.expired,
                reason="reconciled_expired_worker_lease",
            )
        else:
            raise UnsupportedRepairActionError(selected_action, list(self.SUPPORTED_REPAIR_ACTIONS))

        self._capture_run_snapshot(
            run_id,
            RunSnapshotStage.repaired,
            f"Repair snapshot captured: {selected_action}",
            payload_extra={"repair_action": selected_action, "problem": str(selected_problem["problem"])},
        )
        inspection_after = self.inspect_run_state(run_id)
        updated_run = self.get_run(run_id)
        return {
            "run": updated_run.model_dump(mode="json"),
            "applied": True,
            "action": selected_action,
            "problem": selected_problem["problem"],
            "repaired_runtime_task_ids": repaired_runtime_task_ids,
            "inspection_before": inspection_before,
            "inspection_after": inspection_after,
        }
