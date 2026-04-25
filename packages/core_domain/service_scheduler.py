from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from packages.contracts import (
    ControlPlaneHandoffEnvelope,
    Run,
    RuntimeStateRef,
    RuntimeTask,
    SchedulerCommittedLease,
    SchedulerConsensusTerm,
    SchedulerLeaseDecision,
    SchedulerLeaseProposal,
    SchedulerPeerHeartbeat,
    SchedulerVoteRecord,
)
from packages.core_domain.db import unit_of_work
from packages.core_domain.errors import EntityNotFoundError, SchedulerArbitrationError, WorkflowError

if TYPE_CHECKING:
    from packages.core_domain.services import OrchestratorService


class SchedulerServiceMixin:
    """Scheduler lease and arbitration facade methods."""

    def _scheduler_authority_payload(self: "OrchestratorService", state_ref: RuntimeStateRef | None) -> dict[str, Any]:
        return self.scheduler_authority_support.authority_payload(state_ref)

    def _scheduler_decision_history(
        self: "OrchestratorService",
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self.scheduler_authority_support.decision_history(payload)

    def _scheduler_conflicts(
        self: "OrchestratorService",
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self.scheduler_authority_support.conflicts(payload)

    def _scheduler_handoff_history(
        self: "OrchestratorService",
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self.scheduler_authority_support.handoff_history(payload)

    def _cluster_summary_payload(
        self: "OrchestratorService",
        *,
        cluster: dict[str, Any] | None = None,
        term: SchedulerConsensusTerm | dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return self.scheduler_authority_support.cluster_summary_payload(cluster=cluster, term=term)

    def _scheduler_context_for_dispatch(
        self: "OrchestratorService",
        committed_lease: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return self.scheduler_authority_support.scheduler_context_for_dispatch(committed_lease)

    def _scheduler_committed_lease_payload(
        self: "OrchestratorService",
        committed_lease: SchedulerCommittedLease | dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return self.scheduler_authority_support.committed_lease_payload(committed_lease)

    def _scheduler_handoff_envelope_payload(
        self: "OrchestratorService",
        handoff_envelope: ControlPlaneHandoffEnvelope | dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return self.scheduler_authority_support.handoff_envelope_payload(handoff_envelope)

    def _scheduler_arbitration_updates(
        self: "OrchestratorService",
        state_ref: RuntimeStateRef | None,
        *,
        control_plane_id: str,
        proposal: SchedulerLeaseProposal | None = None,
        decision: SchedulerLeaseDecision | None = None,
        committed_lease: SchedulerCommittedLease | dict[str, Any] | None = None,
        term: SchedulerConsensusTerm | dict[str, Any] | None = None,
        votes: list[SchedulerVoteRecord | dict[str, Any]] | None = None,
        handoff_envelope: ControlPlaneHandoffEnvelope | dict[str, Any] | None = None,
        heartbeat: SchedulerPeerHeartbeat | None = None,
        cluster: dict[str, Any] | None = None,
        conflict: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.scheduler_authority_support.arbitration_updates(
            state_ref,
            control_plane_id=control_plane_id,
            proposal=proposal,
            decision=decision,
            committed_lease=committed_lease,
            term=term,
            votes=votes,
            handoff_envelope=handoff_envelope,
            heartbeat=heartbeat,
            cluster=cluster,
            conflict=conflict,
        )

    def _create_control_plane_handoff_envelope(
        self: "OrchestratorService",
        *,
        run_id: str,
        runtime_task_id: str,
        from_control_plane_id: str,
        to_control_plane_id: str,
        committed_lease: SchedulerCommittedLease,
        connection=None,
    ) -> ControlPlaneHandoffEnvelope:
        snapshots = self.snapshot_repo.list_for_run(run_id)
        latest_snapshot = snapshots[-1] if snapshots else None
        latest_review_verdict = self.review_repo.latest_for_run(run_id)
        state_ref = self.runtime_state_repo.get_by_task(runtime_task_id, connection=connection)
        replay_excerpt = {}
        try:
            replay = self.get_run_replay_packet(run_id)
            replay_excerpt = {
                "headline": replay["summary"]["headline"],
                "next_action": replay["summary"]["next_action"],
                "failure_taxonomy": replay["summary"]["failure_taxonomy"],
            }
        except WorkflowError:
            replay_excerpt = {}
        envelope = self.scheduler_authority_cluster.create_handoff_envelope(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            from_control_plane_id=from_control_plane_id,
            to_control_plane_id=to_control_plane_id,
            committed_lease_id=committed_lease.committed_lease_id,
            term_no=committed_lease.term_no,
            commit_index=committed_lease.commit_index,
            snapshot_payload=latest_snapshot.snapshot_payload if latest_snapshot is not None else {},
            review_state=(
                latest_review_verdict.model_dump(mode="json")
                if latest_review_verdict is not None
                else {"effective_review_state": "not_requested"}
            ),
            durable_refs=self._durable_refs_for_state(state_ref),
            replay_excerpt=replay_excerpt,
            connection=connection,
        )
        return envelope

    def _ensure_committed_scheduler_lease(
        self: "OrchestratorService",
        *,
        run: Run,
        runtime_task: RuntimeTask,
        connection=None,
    ) -> tuple[dict[str, Any], ControlPlaneHandoffEnvelope | None]:
        result = self.scheduler_authority_cluster.submit_proposal(
            control_plane_id=self.control_plane_identity.control_plane_id,
            run_id=run.run_id,
            runtime_task_id=runtime_task.runtime_task_id,
            domain_kind="runtime_task",
            domain_key=runtime_task.runtime_task_id,
            connection=connection,
        )
        if not result.get("granted"):
            raise SchedulerArbitrationError(
                "control plane does not own a committed scheduler lease for the runtime task",
                {
                    "run_id": run.run_id,
                    "runtime_task_id": runtime_task.runtime_task_id,
                    "result": result,
                },
            )
        previous = result.get("previous_committed_lease")
        current = result.get("committed_lease")
        handoff_envelope = None
        if (
            isinstance(previous, dict)
            and isinstance(current, dict)
            and previous.get("control_plane_id") is not None
            and previous.get("control_plane_id") != current.get("control_plane_id")
        ):
            handoff_envelope = self._create_control_plane_handoff_envelope(
                run_id=run.run_id,
                runtime_task_id=runtime_task.runtime_task_id,
                from_control_plane_id=str(previous["control_plane_id"]),
                to_control_plane_id=str(current["control_plane_id"]),
                committed_lease=SchedulerCommittedLease.model_validate(current),
                connection=connection,
            )
            result["handoff_envelope"] = self._scheduler_handoff_envelope_payload(handoff_envelope)
        return result, handoff_envelope

    def _validate_callback_scheduler_context(
        self: "OrchestratorService",
        *,
        runtime_task_id: str,
        execution_target: dict[str, Any] | None,
        connection=None,
    ) -> SchedulerCommittedLease:
        current_committed = self.scheduler_authority_cluster.get_active_committed_lease_for_domain(
            domain_kind="runtime_task",
            domain_key=runtime_task_id,
            connection=connection,
        )
        if current_committed is None:
            raise SchedulerArbitrationError(
                "worker callback arrived without an active committed scheduler lease",
                {"runtime_task_id": runtime_task_id},
            )
        if current_committed.control_plane_id != self.control_plane_identity.control_plane_id:
            raise SchedulerArbitrationError(
                "worker callback was received by a stale control plane",
                {
                    "runtime_task_id": runtime_task_id,
                    "active_control_plane_id": current_committed.control_plane_id,
                    "local_control_plane_id": self.control_plane_identity.control_plane_id,
                },
            )
        target = execution_target or {}
        if (
            target.get("committed_lease_id")
            and str(target.get("committed_lease_id")) != current_committed.committed_lease_id
        ):
            raise SchedulerArbitrationError(
                "worker callback committed lease does not match the active committed lease",
                {
                    "runtime_task_id": runtime_task_id,
                    "callback_committed_lease_id": target.get("committed_lease_id"),
                    "active_committed_lease_id": current_committed.committed_lease_id,
                },
            )
        if target.get("fencing_token") and str(target.get("fencing_token")) != current_committed.fencing_token:
            raise SchedulerArbitrationError(
                "worker callback fencing token does not match the active committed lease",
                {
                    "runtime_task_id": runtime_task_id,
                    "callback_fencing_token": target.get("fencing_token"),
                    "active_fencing_token": current_committed.fencing_token,
                },
            )
        return current_committed

    def submit_scheduler_proposal(
        self: "OrchestratorService",
        *,
        control_plane_id: str,
        run_id: str,
        runtime_task_id: str,
        domain_kind: str = "runtime_task",
        domain_key: str,
        requested_lease_seconds: int = 300,
        requested_epoch: int = 1,
    ) -> dict[str, Any]:
        self.get_run(run_id)
        with unit_of_work(self.db_path) as connection:
            state_ref = self.runtime_state_repo.get_by_task(runtime_task_id, connection=connection)
            result = self.scheduler_authority_cluster.submit_proposal(
                control_plane_id=control_plane_id,
                run_id=run_id,
                runtime_task_id=runtime_task_id,
                domain_kind=domain_kind,
                domain_key=domain_key,
                requested_lease_seconds=requested_lease_seconds,
                requested_epoch=requested_epoch,
                connection=connection,
            )
            proposal = (
                SchedulerLeaseProposal.model_validate(result["proposal"])
                if isinstance(result.get("proposal"), dict)
                else None
            )
            decision = (
                SchedulerLeaseDecision.model_validate(result["decision"])
                if isinstance(result.get("decision"), dict)
                else None
            )
            committed_lease = (
                SchedulerCommittedLease.model_validate(result["committed_lease"])
                if isinstance(result.get("committed_lease"), dict)
                else None
            )
            term = (
                SchedulerConsensusTerm.model_validate(result["term"])
                if isinstance(result.get("term"), dict)
                else None
            )
            votes = [
                SchedulerVoteRecord.model_validate(item)
                for item in result.get("votes", [])
                if isinstance(item, dict)
            ]
            handoff_envelope_payload = result.get("handoff_envelope") if isinstance(result.get("handoff_envelope"), dict) else None
            handoff_envelope = (
                ControlPlaneHandoffEnvelope.model_validate(result["handoff_envelope"])
                if isinstance(result.get("handoff_envelope"), dict)
                else None
            )
            if state_ref is not None:
                updates = self._scheduler_arbitration_updates(
                    state_ref,
                    control_plane_id=control_plane_id,
                    proposal=proposal,
                    decision=decision,
                    committed_lease=committed_lease,
                    term=term,
                    votes=votes,
                    handoff_envelope=handoff_envelope_payload or handoff_envelope,
                    cluster=result.get("cluster"),
                    conflict=result.get("conflict"),
                )
                self.runtime_state_repo.upsert(
                    self._state_ref_with_payload_updates(state_ref, updates),
                    connection=connection,
                )
            return result

    def record_scheduler_peer_heartbeat(
        self: "OrchestratorService",
        *,
        control_plane_id: str,
        status: str = "active",
        lease_count: int = 0,
        observed_at: str | None = None,
    ) -> dict[str, Any]:
        heartbeat = self.scheduler_peer_heartbeat_repo.create(
            SchedulerPeerHeartbeat(
                control_plane_id=control_plane_id,
                status=status,
                lease_count=lease_count,
                observed_at=datetime.fromisoformat(observed_at) if observed_at is not None else self._utc_now(),
            )
        )
        cluster = self.scheduler_authority_cluster.heartbeat_node(
            node_id=control_plane_id,
            bind_url=f"internal://{control_plane_id}",
            status=status,
            role="control_plane",
            observed_at=heartbeat.observed_at.isoformat(),
        )
        return {
            "heartbeat": heartbeat.model_dump(mode="json"),
            "cluster": cluster["cluster"],
        }

    def release_scheduler_lease(
        self: "OrchestratorService",
        lease_id: str,
        *,
        release_reason: str = "control_plane_release",
    ) -> dict[str, Any]:
        with unit_of_work(self.db_path) as connection:
            released = self.scheduler_authority_cluster.release_lease(
                lease_id,
                release_reason=release_reason,
                connection=connection,
            )
            decision = (
                SchedulerLeaseDecision.model_validate(released["decision"])
                if isinstance(released.get("decision"), dict)
                else None
            )
            if decision is None:
                raise EntityNotFoundError("scheduler_lease", lease_id)
            state_ref = self.runtime_state_repo.get_by_task(decision.runtime_task_id, connection=connection)
            if state_ref is not None:
                updates = self._scheduler_arbitration_updates(
                    state_ref,
                    control_plane_id=decision.control_plane_id,
                    decision=decision,
                    committed_lease=released.get("committed_lease"),
                    cluster=released.get("cluster"),
                )
                self.runtime_state_repo.upsert(
                    self._state_ref_with_payload_updates(state_ref, updates),
                    connection=connection,
                )
            latest_heartbeat = self.scheduler_peer_heartbeat_repo.latest_for_control_plane(
                decision.control_plane_id,
                connection=connection,
            )
            return {
                "decision": decision.model_dump(mode="json"),
                "committed_lease": released.get("committed_lease"),
                "cluster": released.get("cluster"),
                "latest_peer_heartbeat": (
                    latest_heartbeat.model_dump(mode="json") if latest_heartbeat is not None else None
                ),
            }

    def get_scheduler_lease(self: "OrchestratorService", lease_id: str) -> dict[str, Any]:
        payload = self.scheduler_authority_cluster.get_lease(lease_id)
        decision = (
            SchedulerLeaseDecision.model_validate(payload["decision"])
            if isinstance(payload.get("decision"), dict)
            else None
        )
        latest_heartbeat = (
            self.scheduler_peer_heartbeat_repo.latest_for_control_plane(decision.control_plane_id)
            if decision is not None
            else None
        )
        return {
            **payload,
            "latest_peer_heartbeat": (
                latest_heartbeat.model_dump(mode="json") if latest_heartbeat is not None else None
            ),
        }
