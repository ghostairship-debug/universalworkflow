from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from packages.contracts import (
    Evidence,
    ExecutionTargetRef,
    LeaseRenewalRecord,
    ReviewDecision,
    ReviewerType,
    RunEvent,
    RunEventType,
    RunSnapshotStage,
    RunStatus,
    RuntimeAttempt,
    RuntimeAttemptStatus,
    RuntimeStateRef,
    SimulationPolicyDefinition,
    SimulationReport,
    SimulationTriggerPolicy,
    WorkerLease,
)
from packages.core_domain.service_types import RunDiagnosticContext


class ProjectionServiceMixin:
    def _result_envelope_for(self, last_evidence: Evidence | None) -> dict[str, Any] | None:
        if last_evidence is None or last_evidence.result_envelope is None:
            return None
        return last_evidence.result_envelope.model_dump(mode="json")

    def _execution_target_for(
        self,
        last_runtime_state: RuntimeStateRef | None,
        last_evidence: Evidence | None,
    ) -> dict[str, Any] | None:
        if last_runtime_state is not None and isinstance(last_runtime_state.state_payload.get("execution_target"), dict):
            return dict(last_runtime_state.state_payload["execution_target"])
        if last_evidence is not None:
            target = last_evidence.raw_execution.get("metadata", {}).get("execution_target")
            if isinstance(target, dict):
                return dict(target)
        return None

    def _lease_renewals_for(
        self,
        last_runtime_state: RuntimeStateRef | None,
        last_evidence: Evidence | None,
    ) -> list[dict[str, Any]]:
        if last_runtime_state is not None and isinstance(last_runtime_state.state_payload.get("lease_renewals"), list):
            return [dict(item) for item in last_runtime_state.state_payload["lease_renewals"] if isinstance(item, dict)]
        if last_evidence is not None:
            renewals = last_evidence.raw_execution.get("metadata", {}).get("lease_renewals")
            if isinstance(renewals, list):
                return [dict(item) for item in renewals if isinstance(item, dict)]
        return []

    def _mutation_contract_for(
        self,
        context: RunDiagnosticContext,
        last_runtime_state: RuntimeStateRef | None,
    ) -> dict[str, Any] | None:
        runtime_task = self._runtime_task_for_context(context)
        if runtime_task is not None:
            task_packet = self.task_repo.get_task_packet(runtime_task.runtime_task_id)
            if task_packet is not None and task_packet.mutation_contract is not None:
                return task_packet.mutation_contract.model_dump(mode="json")
        if last_runtime_state is not None and isinstance(last_runtime_state.state_payload.get("mutation_contract"), dict):
            return dict(last_runtime_state.state_payload["mutation_contract"])
        return None

    def _mutation_result_for(
        self,
        last_runtime_state: RuntimeStateRef | None,
        last_evidence: Evidence | None,
    ) -> dict[str, Any] | None:
        if last_runtime_state is not None and isinstance(last_runtime_state.state_payload.get("mutation_result"), dict):
            return dict(last_runtime_state.state_payload["mutation_result"])
        if last_evidence is not None:
            mutation_result = last_evidence.raw_execution.get("metadata", {}).get("mutation_result")
            if isinstance(mutation_result, dict):
                return dict(mutation_result)
        return None

    def _scheduler_authority_for(
        self,
        context: RunDiagnosticContext,
        last_runtime_state: RuntimeStateRef | None,
    ) -> dict[str, Any] | None:
        payload = (
            dict(last_runtime_state.state_payload.get("scheduler_authority"))
            if last_runtime_state is not None
            and isinstance(last_runtime_state.state_payload.get("scheduler_authority"), dict)
            else {}
        )
        runtime_task = self._runtime_task_for_context(context)
        live_cluster = self.scheduler_authority_cluster.cluster_snapshot()
        payload["cluster_summary"] = live_cluster
        payload["local_control_plane_id"] = self.control_plane_identity.control_plane_id
        if runtime_task is not None:
            active_committed = self.scheduler_authority_cluster.get_active_committed_lease_for_domain(
                domain_kind="runtime_task",
                domain_key=runtime_task.runtime_task_id,
            )
            if active_committed is not None:
                payload["active_committed_lease"] = active_committed.model_dump(mode="json")
        handoff_history = payload.get("handoff_history")
        handoff_items = [dict(item) for item in handoff_history if isinstance(item, dict)] if isinstance(handoff_history, list) else []
        for handoff in context.handoffs:
            serialized = handoff.model_dump(mode="json")
            if not any(item.get("envelope_id") == serialized["envelope_id"] for item in handoff_items):
                handoff_items.append(serialized)
        if handoff_items:
            payload["handoff_history"] = handoff_items[-20:]
        active_committed_payload = payload.get("active_committed_lease")
        active_owner = (
            str(active_committed_payload.get("control_plane_id"))
            if isinstance(active_committed_payload, dict) and active_committed_payload.get("control_plane_id") is not None
            else None
        )
        payload["stale_plane_detected"] = bool(
            active_owner is not None and active_owner != self.control_plane_identity.control_plane_id
        )
        payload["takeover_state"] = {
            "local_control_plane_id": self.control_plane_identity.control_plane_id,
            "active_control_plane_id": active_owner,
            "active_owner_is_local": active_owner == self.control_plane_identity.control_plane_id if active_owner is not None else None,
            "handoff_count": len(handoff_items),
        }
        return payload or None

    def _parse_iso_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _duration_ms_between(self, start: datetime | None, end: datetime | None) -> int | None:
        if start is None or end is None:
            return None
        return max(int((end - start).total_seconds() * 1000), 0)

    def _worker_lease_projection(
        self,
        context: RunDiagnosticContext,
        latest_worker_lease: WorkerLease | None,
        active_worker_leases: list[WorkerLease],
        expired_active_worker_leases: list[WorkerLease],
    ) -> dict[str, Any]:
        return {
            "lease_count": len(context.worker_leases),
            "active_lease_count": len(active_worker_leases),
            "expired_active_lease_count": len(expired_active_worker_leases),
            "latest_lease_id": latest_worker_lease.lease_id if latest_worker_lease is not None else None,
            "latest_status": str(latest_worker_lease.status) if latest_worker_lease is not None else None,
            "latest_worker_name": latest_worker_lease.worker_name if latest_worker_lease is not None else None,
            "latest_adapter_name": latest_worker_lease.adapter_name if latest_worker_lease is not None else None,
            "latest_heartbeat_at": (
                latest_worker_lease.heartbeat_at.isoformat() if latest_worker_lease is not None else None
            ),
            "latest_lease_expires_at": (
                latest_worker_lease.lease_expires_at.isoformat() if latest_worker_lease is not None else None
            ),
            "active_lease_ids": [lease.lease_id for lease in active_worker_leases],
            "expired_active_lease_ids": [lease.lease_id for lease in expired_active_worker_leases],
        }

    def _attempt_projection(
        self,
        context: RunDiagnosticContext,
        latest_attempt: RuntimeAttempt | None,
        current_attempt: RuntimeAttempt | None,
    ) -> dict[str, Any]:
        superseded_attempts = self._superseded_attempts(context)
        interrupted_attempts = [
            attempt for attempt in context.runtime_attempts if str(attempt.status) == RuntimeAttemptStatus.interrupted
        ]
        terminal_attempts = [
            attempt
            for attempt in context.runtime_attempts
            if str(attempt.status)
            in {
                RuntimeAttemptStatus.completed,
                RuntimeAttemptStatus.failed,
                RuntimeAttemptStatus.cancelled,
                RuntimeAttemptStatus.interrupted,
            }
        ]
        return {
            "attempt_count": len(context.runtime_attempts),
            "current_attempt_id": current_attempt.attempt_id if current_attempt is not None else None,
            "current_runtime_task_id": current_attempt.runtime_task_id if current_attempt is not None else None,
            "current_trigger": str(current_attempt.trigger) if current_attempt is not None else None,
            "latest_attempt_id": latest_attempt.attempt_id if latest_attempt is not None else None,
            "latest_sequence_no": latest_attempt.sequence_no if latest_attempt is not None else None,
            "latest_status": str(latest_attempt.status) if latest_attempt is not None else None,
            "latest_runtime_task_id": latest_attempt.runtime_task_id if latest_attempt is not None else None,
            "superseded_attempt_ids": [attempt.attempt_id for attempt in superseded_attempts],
            "interrupted_attempt_ids": [attempt.attempt_id for attempt in interrupted_attempts],
            "terminal_attempt_count": len(terminal_attempts),
        }

    def _failure_reason_for(
        self,
        context: RunDiagnosticContext,
        last_runtime_state: RuntimeStateRef | None,
    ) -> str | None:
        if str(context.run.status) != RunStatus.failed:
            return None
        review_policy = self._review_policy_for_context(context, last_runtime_state=last_runtime_state)
        if context.latest_review_verdict is not None and str(context.latest_review_verdict.decision) == ReviewDecision.fail:
            if review_policy == "optional" and last_runtime_state is not None and last_runtime_state.state_payload.get("return_code") not in (None, 0):
                return "runtime_return_code_non_zero"
            if str(context.latest_review_verdict.reviewer_type) == ReviewerType.human:
                return "human_review_rejected"
            return "auto_review_failed"
        if last_runtime_state is not None and last_runtime_state.state_payload.get("return_code") not in (None, 0):
            return "runtime_return_code_non_zero"
        return "run_failed"

    def _waiting_reason_for(self, context: RunDiagnosticContext, last_evidence: Evidence | None) -> str | None:
        status = str(context.run.status)
        if status == RunStatus.pending:
            return "awaiting_compile"
        if status == RunStatus.prepared:
            return "awaiting_runtime_resume"
        if status == RunStatus.running:
            return "runtime_execution_in_progress"
        if status == RunStatus.awaiting_review:
            return "awaiting_human_review" if last_evidence is not None else "awaiting_human_review_missing_evidence"
        return None

    def _default_simulation_policy(self, preset_id: str | None) -> SimulationPolicyDefinition:
        matched_preset_ids = [preset_id] if preset_id is not None else []
        return SimulationPolicyDefinition(
            policy_id="simulation_disabled_unmatched",
            name="Disabled Simulation",
            description="Fallback simulation policy used when no explicit preset match exists.",
            preset_ids=matched_preset_ids,
            trigger_policy=SimulationTriggerPolicy.disabled,
            check_ids=[],
        )

    def _simulation_policy_for_context(self, context: RunDiagnosticContext) -> SimulationPolicyDefinition:
        preset_id = context.preset.preset_id if context.preset is not None else None
        if preset_id is None:
            return self._default_simulation_policy(None)
        return self.simulation_policy_registry.match(preset_id) or self._default_simulation_policy(preset_id)

    def _simulation_report_for(
        self,
        detail: dict[str, Any],
        inspection: dict[str, Any],
    ) -> SimulationReport:
        policy_payload = detail.get("simulation_policy")
        policy = (
            SimulationPolicyDefinition.model_validate(policy_payload)
            if policy_payload is not None
            else self._default_simulation_policy(detail["run"].get("preset_id"))
        )
        return self.simulation_runner.run(policy, detail, inspection)

    def _event_digest_for(self, timeline: list[RunEvent]) -> dict[str, Any]:
        event_type_counts = Counter(str(event.event_type) for event in timeline)
        latest_event = timeline[-1] if timeline else None
        terminal_event = next(
            (
                event
                for event in reversed(timeline)
                if str(event.event_type) in {RunEventType.run_completed, RunEventType.run_failed, RunEventType.run_cancelled}
            ),
            None,
        )
        recent_events = timeline[-5:]
        return {
            "event_count": len(timeline),
            "distinct_event_type_count": len(event_type_counts),
            "event_type_counts": dict(event_type_counts),
            "latest_event_type": str(latest_event.event_type) if latest_event is not None else None,
            "latest_event_at": latest_event.created_at.isoformat() if latest_event is not None else None,
            "terminal_event_type": str(terminal_event.event_type) if terminal_event is not None else None,
            "terminal_event_at": terminal_event.created_at.isoformat() if terminal_event is not None else None,
            "review_requested_count": event_type_counts.get(str(RunEventType.review_requested), 0),
            "review_submitted_count": event_type_counts.get(str(RunEventType.review_submitted), 0),
            "snapshot_event_count": event_type_counts.get(str(RunEventType.run_snapshot_created), 0),
            "repair_event_count": event_type_counts.get(str(RunEventType.repair_applied), 0),
            "recent_event_types": [str(event.event_type) for event in recent_events],
        }

    def _timeline_summary_for(self, timeline: list[RunEvent]) -> dict[str, Any]:
        digest = self._event_digest_for(timeline)
        return {
            "event_count": digest["event_count"],
            "event_type_counts": digest["event_type_counts"],
            "latest_event_type": digest["latest_event_type"],
            "latest_event_at": digest["latest_event_at"],
            "terminal_event_type": digest["terminal_event_type"],
            "repair_event_count": digest["repair_event_count"],
            "recent_event_types": digest["recent_event_types"],
        }

    def _summary_headline_for(
        self,
        detail: dict[str, Any],
        inspection: dict[str, Any],
        failure_taxonomy: dict[str, Any],
    ) -> str:
        run_status = str(detail["run"]["status"])
        if failure_taxonomy["category"] == "inconsistent_state":
            return f"Run {run_status} with {inspection['problem_count']} inspection issue(s)"
        if failure_taxonomy["category"] == "success":
            return "Run completed cleanly"
        if failure_taxonomy["category"] == "review_pending":
            return "Run is waiting for human review"
        if failure_taxonomy["category"] == "operator_cancelled":
            return "Run was cancelled by operator"
        if failure_taxonomy["category"] == "review_failure":
            return f"Run failed during review: {failure_taxonomy['primary_reason']}"
        if failure_taxonomy["category"] == "runtime_failure":
            return f"Run failed during execution: {failure_taxonomy['primary_reason']}"
        return f"Run is {run_status}"

    def _summary_lines_for(
        self,
        detail: dict[str, Any],
        inspection: dict[str, Any],
        failure_taxonomy: dict[str, Any],
        timeline_summary: dict[str, Any],
        simulation_report: SimulationReport,
    ) -> list[str]:
        return [
            (
                f"status={detail['run']['status']} review={detail['effective_review_state']} "
                f"taxonomy={failure_taxonomy['category']}"
            ),
            (
                f"attempts={detail['runtime_attempt_projection']['attempt_count']} "
                f"active_claims={len(detail['active_claims'])} "
                f"active_worker_leases={detail['worker_lease_projection']['active_lease_count']}"
            ),
            (
                f"inspection_problems={inspection['problem_count']} "
                f"latest_event={timeline_summary['latest_event_type']} "
                f"recommended_action={inspection['recommended_action']}"
            ),
            (
                f"simulation={simulation_report.status} "
                f"triggered={simulation_report.triggered} "
                f"policy={simulation_report.trigger_policy}"
            ),
            (
                f"execution_target={detail['execution_target']['target_kind'] if detail.get('execution_target') else 'local'} "
                f"orchestration={'enabled' if detail.get('orchestration') else 'disabled'} "
                f"lease_renewals={len(detail.get('lease_renewals', []))}"
            ),
        ]

    def _timeline_highlights_for(self, timeline: list[RunEvent]) -> list[dict[str, Any]]:
        return [
            {
                "event_id": event.event_id,
                "event_type": str(event.event_type),
                "summary": event.summary,
                "object_type": event.object_type,
                "object_id": event.object_id,
                "created_at": event.created_at.isoformat(),
            }
            for event in timeline[-5:]
        ]

    def _review_digest_for(self, detail: dict[str, Any], timeline: list[RunEvent]) -> dict[str, Any]:
        review_requested_events = [
            event for event in timeline if str(event.event_type) == str(RunEventType.review_requested)
        ]
        review_submitted_events = [
            event for event in timeline if str(event.event_type) == str(RunEventType.review_submitted)
        ]
        latest_requested = review_requested_events[-1] if review_requested_events else None
        latest_submitted = review_submitted_events[-1] if review_submitted_events else None
        latest_review_verdict = detail["latest_review_verdict"]
        return {
            "effective_review_state": detail["effective_review_state"],
            "latest_review_verdict": latest_review_verdict,
            "review_requested_count": len(review_requested_events),
            "review_submitted_count": len(review_submitted_events),
            "latest_review_requested_at": latest_requested.created_at.isoformat() if latest_requested is not None else None,
            "latest_review_submitted_at": latest_submitted.created_at.isoformat() if latest_submitted is not None else None,
            "latest_review_decision": (
                latest_review_verdict["decision"] if latest_review_verdict is not None else None
            ),
            "latest_reviewer_type": (
                latest_review_verdict["reviewer_type"] if latest_review_verdict is not None else None
            ),
            "pending_human_review": detail["effective_review_state"] == "human_pending",
        }

    def _run_metrics_for_context(
        self,
        context: RunDiagnosticContext,
        timeline: list[RunEvent],
        *,
        budget_ledger,
        last_runtime_state: RuntimeStateRef | None,
        last_evidence: Evidence | None,
        latest_snapshot,
    ) -> dict[str, Any]:
        run_id = context.run.run_id
        review_history = self.review_repo.list_for_run(run_id)
        simulation_records = self.simulation_record_repo.list_for_run(run_id)
        memory_items = self.memory_item_repo.list_for_run(run_id)
        durable_lineage = self._durable_lineage_for_state(last_runtime_state)
        review_requested_events = [
            event for event in timeline if str(event.event_type) == str(RunEventType.review_requested)
        ]
        review_submitted_events = [
            event for event in timeline if str(event.event_type) == str(RunEventType.review_submitted)
        ]
        latest_runtime_completed_event = next(
            (event for event in reversed(timeline) if str(event.event_type) == str(RunEventType.runtime_task_completed)),
            None,
        )
        terminal_event = next(
            (
                event
                for event in reversed(timeline)
                if str(event.event_type) in {RunEventType.run_completed, RunEventType.run_failed, RunEventType.run_cancelled}
            ),
            None,
        )
        latest_execution_duration_ms = (
            latest_runtime_completed_event.payload_json.get("duration_ms")
            if latest_runtime_completed_event is not None
            else (last_evidence.raw_execution.get("duration_ms") if last_evidence is not None else None)
        )
        terminal_at = terminal_event.created_at if terminal_event is not None else None
        if terminal_at is None and latest_snapshot is not None and str(context.run.status) in {
            RunStatus.completed,
            RunStatus.failed,
            RunStatus.cancelled,
        }:
            terminal_at = latest_snapshot.created_at
        latest_review_requested_at = review_requested_events[-1].created_at if review_requested_events else None
        latest_review_submitted_at = review_submitted_events[-1].created_at if review_submitted_events else None
        return {
            "counts": {
                "events": len(timeline),
                "snapshots": len(context.snapshots),
                "runtime_tasks": len(context.runtime_tasks),
                "runtime_attempts": len(context.runtime_attempts),
                "claims": len(context.claims),
                "active_claims": len(self._active_claims_for(context)),
                "worker_leases": len(context.worker_leases),
                "active_worker_leases": len(self._active_worker_leases_for(context)),
                "evidence": sum(1 for evidence in context.evidence_by_task.values() if evidence is not None),
                "review_verdicts": len(review_history),
                "review_requested_events": len(review_requested_events),
                "review_submitted_events": len(review_submitted_events),
                "simulation_records": len(simulation_records),
                "memory_items": len(memory_items),
                "durable_transitions": durable_lineage["transition_count"] if durable_lineage is not None else 0,
                "durable_checkpoints": durable_lineage["checkpoint_count"] if durable_lineage is not None else 0,
            },
            "timings_ms": {
                "runtime_total": budget_ledger.total_runtime_ms if budget_ledger is not None else None,
                "latest_execution": latest_execution_duration_ms,
                "time_to_first_evidence": (
                    self._duration_ms_between(context.run.created_at, last_evidence.created_at)
                    if last_evidence is not None
                    else None
                ),
                "time_to_latest_review": (
                    self._duration_ms_between(context.run.created_at, review_history[-1].reviewed_at)
                    if review_history
                    else None
                ),
                "time_to_terminal": self._duration_ms_between(context.run.created_at, terminal_at),
                "human_review_wait": (
                    self._duration_ms_between(
                        latest_review_requested_at,
                        self._utc_now() if str(context.run.status) == RunStatus.awaiting_review else latest_review_submitted_at,
                    )
                    if latest_review_requested_at is not None
                    else None
                ),
            },
            "coverage": {
                "has_external_trace_id": bool(
                    last_runtime_state is not None and last_runtime_state.state_payload.get("external_trace_id")
                ),
                "has_durable_refs": bool(self._durable_refs_for_state(last_runtime_state)),
                "has_durable_lineage": durable_lineage is not None,
                "has_memory_items": bool(memory_items),
                "has_simulation_records": bool(simulation_records),
            },
            "latest_ids": {
                "state_ref_id": last_runtime_state.state_ref_id if last_runtime_state is not None else None,
                "snapshot_id": latest_snapshot.snapshot_id if latest_snapshot is not None else None,
                "evidence_id": last_evidence.evidence_id if last_evidence is not None else None,
                "review_verdict_id": review_history[-1].verdict_id if review_history else None,
                "terminal_event_id": terminal_event.event_id if terminal_event is not None else None,
            },
        }

    def _closure_expectation_for(self, run_status: str) -> dict[str, Any]:
        if run_status == RunStatus.prepared:
            return {
                "required_event_type": str(RunEventType.run_compiled),
                "required_snapshot_stage": str(RunSnapshotStage.compiled),
                "terminal": False,
            }
        if run_status == RunStatus.awaiting_review:
            return {
                "required_event_type": str(RunEventType.review_requested),
                "required_snapshot_stage": str(RunSnapshotStage.awaiting_review),
                "terminal": False,
            }
        if run_status == RunStatus.completed:
            return {
                "required_event_type": str(RunEventType.run_completed),
                "required_snapshot_stage": str(RunSnapshotStage.completed),
                "terminal": True,
            }
        if run_status == RunStatus.failed:
            return {
                "required_event_type": str(RunEventType.run_failed),
                "required_snapshot_stage": str(RunSnapshotStage.failed),
                "terminal": True,
            }
        if run_status == RunStatus.cancelled:
            return {
                "required_event_type": str(RunEventType.run_cancelled),
                "required_snapshot_stage": str(RunSnapshotStage.cancelled),
                "terminal": True,
            }
        return {
            "required_event_type": None,
            "required_snapshot_stage": None,
            "terminal": False,
        }

    def _closure_audit_for(
        self,
        detail: dict[str, Any],
        inspection: dict[str, Any],
        event_digest: dict[str, Any],
        review_digest: dict[str, Any],
    ) -> dict[str, Any]:
        run_status = str(detail["run"]["status"])
        latest_snapshot = detail["latest_snapshot"]
        expectation = self._closure_expectation_for(run_status)
        required_event_type = expectation["required_event_type"]
        required_snapshot_stage = expectation["required_snapshot_stage"]
        missing_requirements: list[str] = []
        notes: list[str] = []

        if required_event_type is not None and event_digest["event_type_counts"].get(required_event_type, 0) == 0:
            missing_requirements.append(f"missing_event:{required_event_type}")

        if expectation["terminal"]:
            if event_digest["terminal_event_type"] != required_event_type:
                missing_requirements.append(f"missing_terminal_event:{required_event_type}")
            if latest_snapshot is None or latest_snapshot["stage"] != required_snapshot_stage:
                missing_requirements.append(f"missing_terminal_snapshot:{required_snapshot_stage}")
            if detail["current_runtime_attempt"] is not None:
                missing_requirements.append("terminal_run_has_live_attempt")
            if detail["active_claims"]:
                missing_requirements.append("terminal_run_has_active_claims")
            if detail["active_worker_leases"]:
                missing_requirements.append("terminal_run_has_active_worker_leases")
            if review_digest["effective_review_state"] == "human_pending":
                missing_requirements.append("terminal_run_still_review_pending")
        else:
            if required_snapshot_stage is not None and (
                latest_snapshot is None or latest_snapshot["stage"] != required_snapshot_stage
            ):
                missing_requirements.append(f"missing_snapshot:{required_snapshot_stage}")
            if run_status == RunStatus.awaiting_review and event_digest["terminal_event_type"] is not None:
                missing_requirements.append("awaiting_review_has_terminal_event")

        if review_digest["effective_review_state"] in {
            "auto_passed",
            "auto_failed",
            "advisory_passed",
            "advisory_failed",
            "human_approved",
            "human_rejected",
        } and review_digest["review_submitted_count"] == 0:
            missing_requirements.append("missing_review_submission_event")

        if run_status == RunStatus.awaiting_review and review_digest["review_requested_count"] == 0:
            missing_requirements.append("missing_review_request_event")

        if inspection["problem_count"] > 0:
            notes.append(f"state inspection reports {inspection['problem_count']} issue(s)")

        passed = not missing_requirements and inspection["problem_count"] == 0
        if missing_requirements:
            state = "closure_gap_detected"
        elif inspection["problem_count"] > 0:
            state = "closed_with_state_issues" if expectation["terminal"] else "open_with_state_issues"
        elif expectation["terminal"]:
            state = "closed"
        elif run_status == RunStatus.awaiting_review:
            state = "awaiting_review"
        elif run_status == RunStatus.prepared:
            state = "prepared"
        else:
            state = "open"

        if missing_requirements:
            if any(item.startswith("missing_terminal_") for item in missing_requirements):
                recommended_action = "inspect_timeline_and_reconcile"
            elif any("review" in item for item in missing_requirements):
                recommended_action = "inspect_review_closure"
            else:
                recommended_action = detail["recoverability_hint"]
        elif inspection["problem_count"] > 0:
            recommended_action = inspection["recommended_action"]
        else:
            recommended_action = detail["next_action"] if not expectation["terminal"] else "none"

        return {
            "passed": passed,
            "state": state,
            "required_event_type": required_event_type,
            "required_snapshot_stage": required_snapshot_stage,
            "has_terminal_event": event_digest["terminal_event_type"] == required_event_type if expectation["terminal"] else False,
            "has_required_snapshot": (
                latest_snapshot is not None and latest_snapshot["stage"] == required_snapshot_stage
                if required_snapshot_stage is not None
                else False
            ),
            "missing_requirements": missing_requirements,
            "notes": notes,
            "recommended_action": recommended_action,
        }

    def _build_event_inspection(
        self,
        detail: dict[str, Any],
        inspection: dict[str, Any],
        timeline: list[RunEvent],
    ) -> dict[str, Any]:
        event_digest = self._event_digest_for(timeline)
        review_digest = self._review_digest_for(detail, timeline)
        closure_audit = self._closure_audit_for(detail, inspection, event_digest, review_digest)
        return {
            "run": detail["run"],
            "event_digest": event_digest,
            "review_digest": review_digest,
            "closure_audit": closure_audit,
            "timeline_highlights": self._timeline_highlights_for(timeline),
            "operator_projection": {
                "status": detail["run"]["status"],
                "next_action": detail["next_action"],
                "recoverability_hint": detail["recoverability_hint"],
                "inspection_problem_count": inspection["problem_count"],
            },
            "trace_context": detail["trace_context"],
        }

    def get_run_summary(self, run_id: str) -> dict[str, Any]:
        detail = self.get_status_detail(run_id)
        inspection = self.inspect_run_state(run_id)
        timeline = self.get_timeline(run_id)
        failure_taxonomy = self._failure_taxonomy_for(detail, inspection)
        timeline_summary = self._timeline_summary_for(timeline)
        event_inspection = self._build_event_inspection(detail, inspection, timeline)
        simulation_report = self._simulation_report_for(detail, inspection)
        headline = self._summary_headline_for(detail, inspection, failure_taxonomy)
        return {
            "run": detail["run"],
            "headline": headline,
            "summary_lines": self._summary_lines_for(
                detail,
                inspection,
                failure_taxonomy,
                timeline_summary,
                simulation_report,
            ),
            "run_metrics": detail["run_metrics"],
            "execution_profile": {
                "review_policy": detail["review_policy"],
                "execution_lane": detail["execution_lane"],
                "domain_pack": detail["domain_pack"],
                "capability_resolution": detail["capability_resolution"],
                "tool_projection_manifest": detail["tool_projection_manifest"],
                "mutation_contract": detail["mutation_contract"],
                "mutation_result": detail["mutation_result"],
                "scheduler_authority": detail["scheduler_authority"],
                "simulation_policy": detail["simulation_policy"],
            },
            "failure_taxonomy": failure_taxonomy,
            "simulation_summary": {
                "policy_id": simulation_report.policy_id,
                "trigger_policy": simulation_report.trigger_policy,
                "triggered": simulation_report.triggered,
                "status": simulation_report.status,
                "finding_codes": simulation_report.finding_codes,
                "recommended_action": simulation_report.recommended_action,
                "latest_record_id": (
                    detail["latest_simulation_record"]["record_id"]
                    if detail.get("latest_simulation_record") is not None
                    else None
                ),
            },
            "review_summary": event_inspection["review_digest"],
            "inspection_summary": {
                "passed": inspection["passed"],
                "problem_count": inspection["problem_count"],
                "repairable_problem_count": inspection["repairable_problem_count"],
                "recommended_action": inspection["recommended_action"],
                "problem_codes": [str(problem["problem"]) for problem in inspection["problems"]],
            },
            "timeline_summary": timeline_summary,
            "closure_summary": event_inspection["closure_audit"],
            "ownership_summary": {
                "runtime_attempt_projection": detail["runtime_attempt_projection"],
                "latest_claim": detail["latest_claim"],
                "worker_lease_projection": detail["worker_lease_projection"],
                "ownership_topology": detail["ownership_topology"],
            },
            "execution_target": detail["execution_target"],
            "lease_renewals": detail["lease_renewals"],
            "mutation_contract": detail["mutation_contract"],
            "mutation_result": detail["mutation_result"],
            "scheduler_authority": detail["scheduler_authority"],
            "orchestration": detail["orchestration"],
            "parallel_batch": detail["parallel_batch"],
            "context_budget": detail["context_budget"],
            "trace_context": detail["trace_context"],
            "next_action": detail["next_action"],
            "recoverability_hint": detail["recoverability_hint"],
        }

    def get_event_inspection(self, run_id: str) -> dict[str, Any]:
        detail = self.get_status_detail(run_id)
        inspection = self.inspect_run_state(run_id)
        timeline = self.get_timeline(run_id)
        return self._build_event_inspection(detail, inspection, timeline)

    def get_run_audit_report(self, run_id: str) -> dict[str, Any]:
        detail = self.get_status_detail(run_id)
        summary = self.get_run_summary(run_id)
        inspection = self.inspect_run_state(run_id)
        simulation_report = self._simulation_report_for(detail, inspection)
        event_inspection = self.get_event_inspection(run_id)
        timeline = self.get_timeline(run_id)
        timeline_tail = [event.model_dump(mode="json") for event in timeline[-10:]]
        return {
            "audit_version": "m3_phase_3_v1",
            "report_generated_at": self._utc_now().isoformat(),
            "run": detail["run"],
            "summary": summary,
            "event_inspection": event_inspection,
            "state_inspection": inspection,
            "simulation_report": simulation_report.model_dump(mode="json"),
            "latest_simulation_record": detail["latest_simulation_record"],
            "context_budget": detail["context_budget"],
            "run_metrics": detail["run_metrics"],
            "trace_context": detail["trace_context"],
            "result_envelope": detail["result_envelope"],
            "trace_exporter": detail["trace_exporter"],
            "orchestration_plan_graph": detail["orchestration_plan_graph"],
            "mutation_packet": {
                "contract": detail["mutation_contract"],
                "result": detail["mutation_result"],
            },
            "scheduler_packet": detail["scheduler_authority"],
            "review_packet": {
                "effective_review_state": summary["review_summary"]["effective_review_state"],
                "latest_review_verdict": summary["review_summary"]["latest_review_verdict"],
                "closure_summary": summary["closure_summary"],
                "next_action": summary["next_action"],
                "recoverability_hint": summary["recoverability_hint"],
            },
            "timeline_tail": timeline_tail,
            "timeline_overview": {
                "event_count": summary["timeline_summary"]["event_count"],
                "latest_event_type": summary["timeline_summary"]["latest_event_type"],
                "recent_event_types": summary["timeline_summary"]["recent_event_types"],
            },
        }

    def get_run_replay_packet(self, run_id: str) -> dict[str, Any]:
        context = self._load_run_context(run_id)
        detail = self.get_status_detail(run_id)
        inspection = self.inspect_run_state(run_id)
        summary = self.get_run_summary(run_id)
        event_inspection = self.get_event_inspection(run_id)
        simulation_report = self._simulation_report_for(detail, inspection)
        timeline = self.get_timeline(run_id)
        evidence = [item.model_dump(mode="json") for item in context.evidence_by_task.values() if item is not None]
        review_history = [item.model_dump(mode="json") for item in self.review_repo.list_for_run(run_id)]
        task_packets: list[dict[str, Any]] = []
        for runtime_task in context.runtime_tasks:
            task_packet = self.task_repo.get_task_packet(runtime_task.runtime_task_id)
            if task_packet is not None:
                task_packets.append(task_packet.model_dump(mode="json"))
        return {
            "packet_version": "m9_phase_1_v1",
            "generated_at": self._utc_now().isoformat(),
            "run": detail["run"],
            "execution_profile": summary["execution_profile"],
            "metrics": detail["run_metrics"],
            "trace_context": detail["trace_context"],
            "execution_target": detail["execution_target"],
            "lease_renewals": detail["lease_renewals"],
            "mutation_contract": detail["mutation_contract"],
            "mutation_result": detail["mutation_result"],
            "scheduler_authority": detail["scheduler_authority"],
            "orchestration": detail["orchestration"],
            "orchestration_plan_graph": detail["orchestration_plan_graph"],
            "parallel_batch": detail["parallel_batch"],
            "summary": {
                "headline": summary["headline"],
                "next_action": summary["next_action"],
                "recoverability_hint": summary["recoverability_hint"],
                "failure_taxonomy": summary["failure_taxonomy"],
            },
            "state_lineage": {
                "runtime_state_refs": detail["runtime_state_refs"],
                "latest_snapshot": detail["latest_snapshot"],
                "snapshots": [snapshot.model_dump(mode="json") for snapshot in context.snapshots],
                "durable_lineage": detail["durable_lineage"],
            },
            "ownership_lineage": {
                "runtime_attempts": detail["runtime_attempts"],
                "claims": detail["claims"],
                "worker_leases": detail["worker_leases"],
                "ownership_topology": detail["ownership_topology"],
            },
            "review_lineage": {
                "review_policy": detail["review_policy"],
                "effective_review_state": detail["effective_review_state"],
                "evidence": evidence,
                "review_history": review_history,
                "latest_review_verdict": detail["latest_review_verdict"],
            },
            "task_packets": task_packets,
            "timeline": [event.model_dump(mode="json") for event in timeline],
            "event_inspection": event_inspection,
            "state_inspection": inspection,
            "simulation_report": simulation_report.model_dump(mode="json"),
        }

    def get_status_detail(self, run_id: str) -> dict[str, Any]:
        context = self._load_run_context(run_id)
        runtime_task = self._runtime_task_for_context(context)
        domain_pack = self._domain_pack_for_context(context)
        memory_preview = self._memory_preview_for_context(context)
        simulation_policy = self._simulation_policy_for_context(context)
        capability_route = self._capability_route_for_runtime_task(runtime_task)
        tool_projection_manifest = self._tool_projection_manifest_for_context(context)
        execution_lane = self._execution_lane_for_context(context)
        mcp_profiles = self._mcp_profiles_for_context(context)
        last_runtime_state = self._last_runtime_state(context)
        last_evidence = self._last_evidence(context)
        latest_attempt = self._last_attempt(context)
        current_attempt = self._current_attempt(context)
        latest_claim = self._last_claim(context)
        latest_worker_lease = self._last_worker_lease(context)
        latest_snapshot = self._last_snapshot(context)
        latest_simulation_record = self.simulation_record_repo.latest_for_run(run_id)
        budget_ledger = self.budget_repo.get_by_run(run_id)
        active_claims = self._active_claims_for(context)
        active_worker_leases = self._active_worker_leases_for(context)
        expired_active_worker_leases = self._expired_active_worker_leases(context)
        inspection_problems = self._inspect_context(context)
        context_budget = self._context_budget_from_state_ref(last_runtime_state)
        parallel_batch = self._parallel_batch_from_state_ref(last_runtime_state)
        execution_target = self._execution_target_for(last_runtime_state, last_evidence)
        lease_renewals = self._lease_renewals_for(last_runtime_state, last_evidence)
        mutation_contract = self._mutation_contract_for(context, last_runtime_state)
        mutation_result = self._mutation_result_for(last_runtime_state, last_evidence)
        scheduler_authority = self._scheduler_authority_for(context, last_runtime_state)
        orchestration = self._orchestration_from_context(context)
        orchestration_plan_graph = self._orchestration_plan_graph_from_context(context)
        timeline = self.get_timeline(run_id)
        review_policy = self._review_policy_for_context(context, last_runtime_state=last_runtime_state)
        trace_context = self._trace_context_for_context(
            context,
            last_runtime_state=last_runtime_state,
            latest_attempt=latest_attempt,
            latest_evidence=last_evidence,
        )
        result_envelope = self._result_envelope_for(last_evidence)
        run_metrics = self._run_metrics_for_context(
            context,
            timeline,
            budget_ledger=budget_ledger,
            last_runtime_state=last_runtime_state,
            last_evidence=last_evidence,
            latest_snapshot=latest_snapshot,
        )
        return {
            "run": context.run.model_dump(mode="json"),
            "runtime_gateway": self.runtime_gateway.describe(),
            "trace_exporter": self.trace_exporter.describe(),
            "durable_runtime_pilot": self.durable_runtime_pilot.describe(),
            "feature_flags": self._feature_flags(),
            "execution_lane": execution_lane,
            "tool_projection_manifest": (
                tool_projection_manifest.model_dump(mode="json") if tool_projection_manifest is not None else None
            ),
            "mcp_server_profiles": mcp_profiles,
            "review_policy": review_policy,
            "domain_pack": domain_pack.model_dump(mode="json") if domain_pack is not None else None,
            "memory_retrieval_preview": memory_preview.model_dump(mode="json") if memory_preview is not None else None,
            "context_budget": context_budget,
            "parallel_batch": parallel_batch,
            "execution_target": execution_target,
            "lease_renewals": lease_renewals,
            "mutation_contract": mutation_contract,
            "mutation_result": mutation_result,
            "scheduler_authority": scheduler_authority,
            "orchestration": orchestration,
            "orchestration_plan_graph": orchestration_plan_graph,
            "trace_context": trace_context,
            "result_envelope": result_envelope,
            "durable_lineage": self._durable_lineage_for_state(last_runtime_state),
            "run_metrics": run_metrics,
            "simulation_policy": simulation_policy.model_dump(mode="json"),
            "capability_resolution": capability_route.model_dump(mode="json") if capability_route is not None else None,
            "runtime_tasks": [task.model_dump(mode="json") for task in context.runtime_tasks],
            "runtime_task_ids": [task.runtime_task_id for task in context.runtime_tasks],
            "handoffs": [handoff.model_dump(mode="json") for handoff in context.handoffs],
            "runtime_state_refs": [state_ref.model_dump(mode="json") for state_ref in context.runtime_state_refs],
            "snapshot_count": len(context.snapshots),
            "latest_snapshot": self._serialize_snapshot(latest_snapshot),
            "latest_simulation_record": self._serialize_contract(latest_simulation_record),
            "budget_ledger": budget_ledger.model_dump(mode="json") if budget_ledger is not None else None,
            "budget_projection": self._budget_projection(budget_ledger),
            "runtime_attempts": [attempt.model_dump(mode="json") for attempt in context.runtime_attempts],
            "latest_runtime_attempt": self._serialize_attempt(latest_attempt),
            "current_runtime_attempt": self._serialize_attempt(current_attempt),
            "runtime_attempt_projection": self._attempt_projection(context, latest_attempt, current_attempt),
            "claims": [claim.model_dump(mode="json") for claim in context.claims],
            "active_claims": [claim.model_dump(mode="json") for claim in active_claims],
            "latest_claim": self._serialize_claim(latest_claim),
            "worker_leases": [lease.model_dump(mode="json") for lease in context.worker_leases],
            "active_worker_leases": [lease.model_dump(mode="json") for lease in active_worker_leases],
            "latest_worker_lease": self._serialize_worker_lease(latest_worker_lease),
            "ownership_topology": self._ownership_topology_projection(
                latest_claim,
                latest_worker_lease,
                current_attempt,
            ),
            "worker_lease_projection": self._worker_lease_projection(
                context,
                latest_worker_lease,
                active_worker_leases,
                expired_active_worker_leases,
            ),
            "latest_review_verdict": self._serialize_contract(context.latest_review_verdict),
            "last_review_verdict": self._serialize_contract(context.latest_review_verdict),
            "effective_review_state": self._effective_review_state(
                context.run,
                context.latest_review_verdict,
                review_policy,
            ),
            "next_action": self._next_action_for(str(context.run.status)),
            "failure_reason": self._failure_reason_for(context, last_runtime_state),
            "waiting_reason": self._waiting_reason_for(context, last_evidence),
            "last_runtime_state": self._serialize_contract(last_runtime_state),
            "recoverability_hint": self._recoverability_hint_for(context, inspection_problems),
        }

    def inspect_run_state(self, run_id: str) -> dict[str, Any]:
        context = self._load_run_context(run_id)
        runtime_task = self._runtime_task_for_context(context)
        domain_pack = self._domain_pack_for_context(context)
        memory_preview = self._memory_preview_for_context(context)
        simulation_policy = self._simulation_policy_for_context(context)
        capability_route = self._capability_route_for_runtime_task(runtime_task)
        tool_projection_manifest = self._tool_projection_manifest_for_context(context)
        execution_lane = self._execution_lane_for_context(context)
        mcp_profiles = self._mcp_profiles_for_context(context)
        problems = self._inspect_context(context)
        last_runtime_state = self._last_runtime_state(context)
        latest_attempt = self._last_attempt(context)
        current_attempt = self._current_attempt(context)
        latest_snapshot = self._last_snapshot(context)
        latest_simulation_record = self.simulation_record_repo.latest_for_run(run_id)
        latest_claim = self._last_claim(context)
        latest_worker_lease = self._last_worker_lease(context)
        budget_ledger = self.budget_repo.get_by_run(run_id)
        active_claims = self._active_claims_for(context)
        active_worker_leases = self._active_worker_leases_for(context)
        expired_active_worker_leases = self._expired_active_worker_leases(context)
        repairable_problem_count = sum(1 for problem in problems if problem["repairable"])
        context_budget = self._context_budget_from_state_ref(last_runtime_state)
        parallel_batch = self._parallel_batch_from_state_ref(last_runtime_state)
        execution_target = self._execution_target_for(last_runtime_state, self._last_evidence(context))
        lease_renewals = self._lease_renewals_for(last_runtime_state, self._last_evidence(context))
        mutation_contract = self._mutation_contract_for(context, last_runtime_state)
        mutation_result = self._mutation_result_for(last_runtime_state, self._last_evidence(context))
        scheduler_authority = self._scheduler_authority_for(context, last_runtime_state)
        orchestration = self._orchestration_from_context(context)
        orchestration_plan_graph = self._orchestration_plan_graph_from_context(context)
        timeline = self.get_timeline(run_id)
        review_policy = self._review_policy_for_context(context, last_runtime_state=last_runtime_state)
        trace_context = self._trace_context_for_context(
            context,
            last_runtime_state=last_runtime_state,
            latest_attempt=latest_attempt,
        )
        run_metrics = self._run_metrics_for_context(
            context,
            timeline,
            budget_ledger=budget_ledger,
            last_runtime_state=last_runtime_state,
            last_evidence=self._last_evidence(context),
            latest_snapshot=latest_snapshot,
        )
        return {
            "run": context.run.model_dump(mode="json"),
            "runtime_gateway": self.runtime_gateway.describe(),
            "trace_exporter": self.trace_exporter.describe(),
            "durable_runtime_pilot": self.durable_runtime_pilot.describe(),
            "feature_flags": self._feature_flags(),
            "execution_lane": execution_lane,
            "tool_projection_manifest": (
                tool_projection_manifest.model_dump(mode="json") if tool_projection_manifest is not None else None
            ),
            "mcp_server_profiles": mcp_profiles,
            "review_policy": review_policy,
            "domain_pack": domain_pack.model_dump(mode="json") if domain_pack is not None else None,
            "memory_retrieval_preview": memory_preview.model_dump(mode="json") if memory_preview is not None else None,
            "context_budget": context_budget,
            "parallel_batch": parallel_batch,
            "execution_target": execution_target,
            "lease_renewals": lease_renewals,
            "mutation_contract": mutation_contract,
            "mutation_result": mutation_result,
            "scheduler_authority": scheduler_authority,
            "orchestration": orchestration,
            "orchestration_plan_graph": orchestration_plan_graph,
            "trace_context": trace_context,
            "durable_lineage": self._durable_lineage_for_state(last_runtime_state),
            "run_metrics": run_metrics,
            "simulation_policy": simulation_policy.model_dump(mode="json"),
            "capability_resolution": capability_route.model_dump(mode="json") if capability_route is not None else None,
            "effective_review_state": self._effective_review_state(
                context.run,
                context.latest_review_verdict,
                review_policy,
            ),
            "last_runtime_state": self._serialize_contract(last_runtime_state),
            "latest_snapshot": self._serialize_snapshot(latest_snapshot),
            "latest_simulation_record": self._serialize_contract(latest_simulation_record),
            "runtime_attempts": [attempt.model_dump(mode="json") for attempt in context.runtime_attempts],
            "latest_runtime_attempt": self._serialize_attempt(latest_attempt),
            "current_runtime_attempt": self._serialize_attempt(current_attempt),
            "runtime_attempt_projection": self._attempt_projection(context, latest_attempt, current_attempt),
            "budget_projection": self._budget_projection(budget_ledger),
            "active_claims": [claim.model_dump(mode="json") for claim in active_claims],
            "active_worker_leases": [lease.model_dump(mode="json") for lease in active_worker_leases],
            "latest_claim": self._serialize_claim(latest_claim),
            "latest_worker_lease": self._serialize_worker_lease(latest_worker_lease),
            "ownership_topology": self._ownership_topology_projection(
                latest_claim,
                latest_worker_lease,
                current_attempt,
            ),
            "worker_lease_projection": self._worker_lease_projection(
                context,
                latest_worker_lease,
                active_worker_leases,
                expired_active_worker_leases,
            ),
            "passed": not problems,
            "problem_count": len(problems),
            "repairable_problem_count": repairable_problem_count,
            "apply_supported": repairable_problem_count > 0,
            "problems": problems,
            "recommended_action": problems[0]["next_action"] if problems else "none",
        }

    def reconcile_run(self, run_id: str) -> dict[str, Any]:
        return self.inspect_run_state(run_id)

    def _run_operator_row(self, run_id: str) -> dict[str, Any]:
        detail = self.get_status_detail(run_id)
        summary = self.get_run_summary(run_id)
        inspection = self.inspect_run_state(run_id)
        latest_review_verdict = summary["review_summary"]["latest_review_verdict"]
        return {
            "run": detail["run"],
            "headline": summary["headline"],
            "effective_review_state": detail["effective_review_state"],
            "next_action": detail["next_action"],
            "recoverability_hint": detail["recoverability_hint"],
            "failure_reason": detail["failure_reason"],
            "waiting_reason": detail["waiting_reason"],
            "review_policy": detail["review_policy"],
            "execution_lane": detail["execution_lane"],
            "domain_pack": detail["domain_pack"],
            "capability_resolution": detail["capability_resolution"],
            "execution_target": detail["execution_target"],
            "scheduler_authority": detail["scheduler_authority"],
            "orchestration": detail["orchestration"],
            "parallel_batch": detail["parallel_batch"],
            "latest_review_verdict": latest_review_verdict,
            "review_recommended_action": (
                detail["recoverability_hint"]
                if detail["effective_review_state"] == "human_pending"
                else detail["next_action"]
            ),
            "inspection_problem_count": inspection["problem_count"],
            "inspection_recommended_action": inspection["recommended_action"],
            "worker_lease_projection": detail["worker_lease_projection"],
            "runtime_attempt_projection": detail["runtime_attempt_projection"],
            "trace_context": detail["trace_context"],
            "run_metrics": detail["run_metrics"],
            "budget_projection": detail["budget_projection"],
            "latest_snapshot": detail["latest_snapshot"],
        }

    def list_run_operator_rows(
        self,
        *,
        limit: int = 10,
        status: str | None = None,
        preset_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            self._run_operator_row(run.run_id)
            for run in self.list_runs(limit=limit, status=status, preset_id=preset_id)
        ]

    def list_pending_review_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.list_run_operator_rows(limit=limit, status=str(RunStatus.awaiting_review))
        return [
            {
                **row,
                "latest_auto_review_verdict": (
                    row["latest_review_verdict"]
                    if row["latest_review_verdict"] is not None
                    and row["latest_review_verdict"].get("reviewer_type") == str(ReviewerType.auto)
                    else None
                ),
            }
            for row in rows
        ]

    def get_operator_view(self, run_id: str) -> dict[str, Any]:
        detail = self.get_status_detail(run_id)
        summary = self.get_run_summary(run_id)
        inspection = self.inspect_run_state(run_id)
        timeline = [event.model_dump(mode="json") for event in self.get_timeline(run_id)]
        replay_packet = self.get_run_replay_packet(run_id)
        return {
            "run": detail["run"],
            "summary": summary,
            "status_detail": detail,
            "inspection": inspection,
            "timeline": timeline,
            "replay_packet_excerpt": {
                "headline": replay_packet["summary"]["headline"],
                "next_action": replay_packet["summary"]["next_action"],
                "recoverability_hint": replay_packet["summary"]["recoverability_hint"],
                "failure_taxonomy": replay_packet["summary"]["failure_taxonomy"],
                "execution_profile": replay_packet["execution_profile"],
            },
            "orchestration": detail["orchestration"],
            "mutation_report": self.get_run_mutation_report(run_id),
            "scheduler_authority": detail["scheduler_authority"],
            "cluster_overview": (
                detail["scheduler_authority"]["cluster_summary"]
                if detail.get("scheduler_authority") is not None
                else self.scheduler_authority_cluster.cluster_snapshot()
            ),
            "handoffs": detail["handoffs"],
        }

    def get_run_mutation_report(self, run_id: str) -> dict[str, Any]:
        detail = self.get_status_detail(run_id)
        inspection = self.inspect_run_state(run_id)
        return {
            "run": detail["run"],
            "execution_lane": detail["execution_lane"],
            "mutation_contract": detail["mutation_contract"],
            "mutation_result": detail["mutation_result"],
            "result_envelope": detail["result_envelope"],
            "inspection_problem_count": inspection["problem_count"],
            "recommended_action": inspection["recommended_action"],
        }

    def get_dashboard_snapshot(self, *, focus_run_id: str | None = None, limit: int = 8) -> dict[str, Any]:
        runs = self.list_runs(limit=limit)
        run_rows: list[dict[str, Any]] = []
        for run in runs:
            detail = self.get_status_detail(run.run_id)
            run_rows.append(
                {
                    "run_id": run.run_id,
                    "goal": run.goal,
                    "preset_id": run.preset_id,
                    "status": run.status,
                    "updated_at": run.updated_at.isoformat(),
                    "effective_review_state": detail["effective_review_state"],
                    "next_action": detail["next_action"],
                    "failure_reason": detail["failure_reason"],
                    "waiting_reason": detail["waiting_reason"],
                    "domain_pack_id": (
                        detail["domain_pack"]["domain_pack_id"] if detail["domain_pack"] is not None else None
                    ),
                    "capability_adapter": (
                        detail["capability_resolution"]["adapter_name"]
                        if detail["capability_resolution"] is not None
                        else None
                    ),
                }
            )

        selected_run_id = focus_run_id or (run_rows[0]["run_id"] if run_rows else None)
        focus_detail = self.get_status_detail(selected_run_id) if selected_run_id is not None else None
        focus_summary = self.get_run_summary(selected_run_id) if selected_run_id is not None else None
        timeline_tail = (
            [event.model_dump(mode="json") for event in self.get_timeline(selected_run_id)[-8:]]
            if selected_run_id is not None
            else []
        )
        return {
            "runtime_gateway": self.runtime_gateway.describe(),
            "trace_exporter": self.trace_exporter.describe(),
            "durable_runtime_pilot": self.durable_runtime_pilot.describe(),
            "feature_flags": self._feature_flags(),
            "cluster_overview": self.scheduler_authority_cluster.cluster_snapshot(),
            "run_count": len(run_rows),
            "selected_run_id": selected_run_id,
            "runs": run_rows,
            "focus_detail": focus_detail,
            "focus_summary": focus_summary,
            "timeline_tail": timeline_tail,
        }
