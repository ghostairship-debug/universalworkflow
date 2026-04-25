from __future__ import annotations

from typing import Any

from packages.contracts import ExecutionLaneType, RunStatus
from packages.core_domain.service_types import RunDiagnosticContext


class InspectionServiceMixin:
    def _inspection_problem(
        self,
        problem: str,
        reason: str,
        next_action: str,
        *,
        severity: str = "error",
        details: dict[str, Any] | None = None,
        repairable: bool = False,
        repair_action: str | None = None,
    ) -> dict[str, Any]:
        return {
            "problem": problem,
            "severity": severity,
            "reason": reason,
            "next_action": next_action,
            "repairable": repairable,
            "repair_action": repair_action,
            "details": details or {},
        }

    def _inspect_context(self, context: RunDiagnosticContext) -> list[dict[str, Any]]:
        problems: list[dict[str, Any]] = []
        non_terminal_states = self.runtime_state_repo.list_live_for_run(context.run.run_id)
        latest_attempt = self._last_attempt(context)
        current_attempt = self._current_attempt(context)
        last_runtime_state = self._last_runtime_state(context)
        current_runtime_task_ids = {task.runtime_task_id for task in context.runtime_tasks}
        active_claims = self._active_claims_for(context)
        expired_active_claims = self._expired_active_claims(context)
        active_worker_leases = self._active_worker_leases_for(context)
        expired_active_worker_leases = self._expired_active_worker_leases(context)
        scheduler_authority = self._scheduler_authority_payload(last_runtime_state)

        if (
            str(context.run.status) in {RunStatus.prepared, RunStatus.running, RunStatus.awaiting_review}
            and current_runtime_task_ids
            and current_attempt is None
        ):
            problems.append(
                self._inspection_problem(
                    "missing_current_runtime_attempt",
                    "run has active runtime task metadata but no current runtime attempt is recorded",
                    "create_repair_runtime_attempt",
                    repairable=True,
                    repair_action="create_repair_runtime_attempt",
                    details={
                        "run_status": str(context.run.status),
                        "runtime_task_ids": sorted(current_runtime_task_ids),
                        "latest_attempt_id": latest_attempt.attempt_id if latest_attempt is not None else None,
                    },
                )
            )

        if current_attempt is not None and current_attempt.runtime_task_id not in current_runtime_task_ids:
            problems.append(
                self._inspection_problem(
                    "current_runtime_attempt_task_missing",
                    "current runtime attempt points to a runtime task that is no longer present in the live run context",
                    "interrupt_current_runtime_attempt",
                    repairable=True,
                    repair_action="interrupt_current_runtime_attempt",
                    details={
                        "attempt_id": current_attempt.attempt_id,
                        "runtime_task_id": current_attempt.runtime_task_id,
                        "run_runtime_task_ids": sorted(current_runtime_task_ids),
                    },
                )
            )

        if str(context.run.status) == RunStatus.completed and non_terminal_states:
            state_ref = non_terminal_states[0]
            problems.append(
                self._inspection_problem(
                    "completed_runtime_non_terminal",
                    "run is marked completed but runtime state is still non-terminal",
                    "reconcile_runtime_state_ref",
                    repairable=True,
                    repair_action="align_completed_runtime_state",
                    details={
                        "runtime_task_id": state_ref.runtime_task_id,
                        "graph_step": state_ref.graph_step,
                        "state_ref_id": state_ref.state_ref_id,
                    },
                )
            )

        if (
            str(context.run.status) in {RunStatus.completed, RunStatus.failed, RunStatus.cancelled}
            and current_attempt is not None
        ):
            problems.append(
                self._inspection_problem(
                    "terminal_run_has_current_runtime_attempt",
                    "run is terminal but runtime attempt lineage still records a current attempt",
                    "close_current_runtime_attempt_terminal",
                    repairable=True,
                    repair_action="close_current_runtime_attempt_terminal",
                    details={
                        "attempt_id": current_attempt.attempt_id,
                        "run_status": str(context.run.status),
                        "runtime_task_id": current_attempt.runtime_task_id,
                    },
                )
            )

        if str(context.run.status) == RunStatus.awaiting_review:
            has_evidence = any(evidence is not None for evidence in context.evidence_by_task.values())
            if not has_evidence:
                problems.append(
                self._inspection_problem(
                    "awaiting_review_missing_evidence",
                    "run is awaiting human review but no evidence exists for its runtime task",
                    "rebuild_or_replay_evidence",
                    repairable=False,
                    repair_action=None,
                    details={"runtime_task_ids": [task.runtime_task_id for task in context.runtime_tasks]},
                )
            )

        if current_attempt is not None and (expired_active_claims or expired_active_worker_leases):
            problems.append(
                self._inspection_problem(
                    "current_runtime_attempt_interrupted",
                    "current runtime attempt still exists while its claim or worker lease has already expired",
                    "interrupt_current_runtime_attempt",
                    repairable=True,
                    repair_action="interrupt_current_runtime_attempt",
                    details={
                        "attempt_id": current_attempt.attempt_id,
                        "expired_claim_ids": [claim.claim_id for claim in expired_active_claims],
                        "expired_worker_lease_ids": [lease.lease_id for lease in expired_active_worker_leases],
                    },
                )
            )

        if str(context.run.status) == RunStatus.cancelled and non_terminal_states:
            state_ref = non_terminal_states[0]
            problems.append(
                self._inspection_problem(
                    "cancelled_with_live_runtime",
                    "run is cancelled but at least one runtime state is still live",
                    "terminate_or_reconcile_runtime",
                    repairable=True,
                    repair_action="align_cancelled_runtime_state",
                    details={
                        "runtime_task_id": state_ref.runtime_task_id,
                        "graph_step": state_ref.graph_step,
                        "state_ref_id": state_ref.state_ref_id,
                    },
                )
            )

        if expired_active_claims:
            problems.append(
                self._inspection_problem(
                    "runtime_claim_expired",
                    "run still has active claims whose lease has already expired",
                    "expire_runtime_claim",
                    repairable=True,
                    repair_action="expire_runtime_claim",
                    details={
                        "claim_ids": [claim.claim_id for claim in expired_active_claims],
                        "runtime_task_ids": [claim.runtime_task_id for claim in expired_active_claims],
                    },
                )
            )

        if str(context.run.status) != RunStatus.running and active_claims:
            problems.append(
                self._inspection_problem(
                    "non_running_run_has_active_claim",
                    "run is not running but still has one or more active runtime claims",
                    "release_runtime_claim",
                    repairable=True,
                    repair_action="release_runtime_claim",
                    details={
                        "run_status": str(context.run.status),
                        "claim_ids": [claim.claim_id for claim in active_claims],
                        "runtime_task_ids": [claim.runtime_task_id for claim in active_claims],
                    },
                )
            )

        if expired_active_worker_leases:
            problems.append(
                self._inspection_problem(
                    "worker_lease_expired",
                    "run still has active worker leases whose heartbeat lease has already expired",
                    "expire_worker_lease",
                    repairable=True,
                    repair_action="expire_worker_lease",
                    details={
                        "lease_ids": [lease.lease_id for lease in expired_active_worker_leases],
                        "runtime_task_ids": [lease.runtime_task_id for lease in expired_active_worker_leases],
                        "adapter_names": [lease.adapter_name for lease in expired_active_worker_leases],
                    },
                )
            )

        if str(context.run.status) != RunStatus.running and active_worker_leases:
            problems.append(
                self._inspection_problem(
                    "non_running_run_has_active_worker_lease",
                    "run is not running but still has one or more active worker leases",
                    "release_worker_lease",
                    repairable=True,
                    repair_action="release_worker_lease",
                    details={
                        "run_status": str(context.run.status),
                        "lease_ids": [lease.lease_id for lease in active_worker_leases],
                        "runtime_task_ids": [lease.runtime_task_id for lease in active_worker_leases],
                        "adapter_names": [lease.adapter_name for lease in active_worker_leases],
                    },
                )
            )

        active_decision = (
            scheduler_authority.get("active_decision") if isinstance(scheduler_authority.get("active_decision"), dict) else None
        )
        if active_decision is not None:
            lease_expires_at = self._parse_iso_datetime(active_decision.get("lease_expires_at"))
            released_at = self._parse_iso_datetime(active_decision.get("released_at"))
            if released_at is None and lease_expires_at is not None and lease_expires_at <= self._utc_now():
                problems.append(
                    self._inspection_problem(
                        "scheduler_authority_lease_expired",
                        "scheduler authority still projects an active lease decision whose lease has already expired",
                        "submit_scheduler_proposal_or_release_scheduler_lease",
                        repairable=False,
                        details={
                            "decision_id": active_decision.get("decision_id"),
                            "lease_id": active_decision.get("lease_id"),
                            "control_plane_id": active_decision.get("control_plane_id"),
                            "lease_epoch": active_decision.get("lease_epoch"),
                            "lease_expires_at": active_decision.get("lease_expires_at"),
                        },
                    )
                )

        conflicts = scheduler_authority.get("conflicts")
        if isinstance(conflicts, list) and conflicts:
            latest_conflict = next((item for item in reversed(conflicts) if isinstance(item, dict)), None)
            problems.append(
                self._inspection_problem(
                    "scheduler_authority_conflict",
                    "scheduler authority recorded at least one cross-control-plane lease conflict for this runtime task",
                    "inspect_scheduler_authority_conflicts",
                    severity="warning",
                    repairable=False,
                    details=latest_conflict or {"conflict_count": len(conflicts)},
                )
            )

        active_committed = (
            scheduler_authority.get("active_committed_lease")
            if isinstance(scheduler_authority.get("active_committed_lease"), dict)
            else None
        )
        if scheduler_authority.get("stale_plane_detected") and active_committed is not None:
            problems.append(
                self._inspection_problem(
                    "scheduler_authority_stale_control_plane",
                    "the local control plane is stale and no longer owns the active committed scheduler lease",
                    "inspect_scheduler_authority_takeover",
                    severity="warning",
                    repairable=False,
                    details={
                        "local_control_plane_id": scheduler_authority.get("local_control_plane_id"),
                        "active_control_plane_id": active_committed.get("control_plane_id"),
                        "committed_lease_id": active_committed.get("committed_lease_id"),
                        "fencing_token": active_committed.get("fencing_token"),
                        "term_no": active_committed.get("term_no"),
                        "authority_term_no": active_committed.get("authority_term_no")
                        or active_committed.get("term_no"),
                        "commit_index": active_committed.get("commit_index"),
                        "decision_index": active_committed.get("decision_index")
                        or active_committed.get("commit_index"),
                    },
                )
            )

        if str(context.run.status) == RunStatus.prepared:
            missing_components: list[str] = []
            if len(context.phases) < 2:
                missing_components.append("phases")
            if not context.task_cards:
                missing_components.append("task_cards")
            if not context.runtime_tasks:
                missing_components.append("runtime_tasks")
            if not context.handoffs:
                missing_components.append("handoffs")
            if not context.runtime_state_refs:
                missing_components.append("runtime_state_refs")
            for task in context.runtime_tasks:
                if self.task_repo.get_task_packet(task.runtime_task_id) is None:
                    missing_components.append(f"task_packet:{task.runtime_task_id}")
            if missing_components:
                problems.append(
                    self._inspection_problem(
                        "prepared_compile_snapshot_incomplete",
                        "run is prepared but compile snapshot persistence is incomplete",
                        "recompile_run",
                        repairable=True,
                        repair_action="recompile_prepared_run",
                        details={"missing_components": missing_components},
                    )
                )
        if self._execution_lane_for_context(context) == str(ExecutionLaneType.durable_incremental):
            durable_refs = self._durable_refs_for_state(last_runtime_state)
            durable_lineage = self._durable_lineage_for_state(last_runtime_state)
            if last_runtime_state is None:
                problems.append(
                    self._inspection_problem(
                        "durable_runtime_state_missing",
                        "durable lane is selected but no runtime state ref exists to anchor durable lineage",
                        "recompile_run",
                        repairable=True,
                        repair_action="recompile_prepared_run",
                    )
                )
            elif not durable_refs:
                problems.append(
                    self._inspection_problem(
                        "durable_refs_missing",
                        "durable lane runtime state does not expose thread/checkpoint/assistant refs",
                        "inspect_durable_lineage",
                        repairable=False,
                        details={"state_ref_id": last_runtime_state.state_ref_id},
                    )
                )
            elif durable_lineage is None:
                problems.append(
                    self._inspection_problem(
                        "durable_lineage_missing",
                        "durable lane runtime state exposes refs but does not persist structured durable lineage",
                        "inspect_durable_lineage",
                        repairable=False,
                        details={
                            "state_ref_id": last_runtime_state.state_ref_id,
                            "durable_refs": durable_refs,
                        },
                    )
                )
            else:
                top_level_refs = {
                    key: value
                    for key, value in {
                        "thread_id": last_runtime_state.state_payload.get("thread_id"),
                        "checkpoint_id": last_runtime_state.state_payload.get("checkpoint_id"),
                        "assistant_id": last_runtime_state.state_payload.get("assistant_id"),
                    }.items()
                    if value
                }
                if durable_lineage["current_refs"] != top_level_refs:
                    problems.append(
                        self._inspection_problem(
                            "durable_lineage_refs_mismatch",
                            "durable lineage current refs diverge from the top-level runtime state durable refs",
                            "inspect_durable_lineage",
                            repairable=False,
                            details={
                                "state_ref_id": last_runtime_state.state_ref_id,
                                "current_refs": durable_lineage["current_refs"],
                                "top_level_refs": top_level_refs,
                            },
                        )
                    )
                if not durable_lineage["history"]:
                    problems.append(
                        self._inspection_problem(
                            "durable_lineage_history_empty",
                            "durable lane runtime state is missing transition history",
                            "inspect_durable_lineage",
                            repairable=False,
                            details={"state_ref_id": last_runtime_state.state_ref_id},
                        )
                    )
        return problems
