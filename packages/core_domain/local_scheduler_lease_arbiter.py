from __future__ import annotations

"""Local-only scheduler lease arbiter.

This module intentionally does not import ``packages.core_domain.scheduler_authority``.
It is used when the scheduler-authority cluster flag is off, so the default
single-control-plane path stays independent from the heavier cluster runtime.
"""

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from packages.contracts import (
    AuthorityNodeIdentity,
    ControlPlaneHandoffEnvelope,
    SchedulerCommittedLease,
    SchedulerConsensusTerm,
    SchedulerLeaseDecision,
    SchedulerLeaseProposal,
)
from packages.core_domain.db import unit_of_work
from packages.core_domain.errors import EntityNotFoundError
from packages.core_domain.repositories import SchedulerLeaseDecisionRepository, SchedulerLeaseProposalRepository


def _utc_now() -> datetime:
    return datetime.now(UTC)


class LocalSchedulerLeaseArbiter:
    """Single-control-plane lease arbiter used when cluster authority is disabled."""

    def __init__(
        self,
        db_path: str | Path | None,
        *,
        node_id: str,
        bind_url: str,
        peer_urls: list[str] | None = None,
        quorum_size: int = 1,
        election_timeout_ms: int = 15000,
        heartbeat_interval_ms: int = 3000,
    ) -> None:
        del peer_urls
        self.db_path = Path(db_path) if db_path is not None else None
        self.enabled = False
        self.node_id = node_id
        self.bind_url = bind_url
        self.quorum_size = max(int(quorum_size), 1)
        self.election_timeout_ms = max(int(election_timeout_ms), 1)
        self.heartbeat_interval_ms = max(int(heartbeat_interval_ms), 1)
        self.scheduler_proposal_repo = SchedulerLeaseProposalRepository(self.db_path)
        self.scheduler_decision_repo = SchedulerLeaseDecisionRepository(self.db_path)

    def _row_to_committed_lease(self, row: sqlite3.Row | dict[str, Any]) -> SchedulerCommittedLease:
        return SchedulerCommittedLease.model_validate(dict(row))

    def _row_to_handoff(self, row: sqlite3.Row | dict[str, Any]) -> ControlPlaneHandoffEnvelope:
        data = dict(row)
        data["snapshot_payload"] = json.loads(data.pop("snapshot_payload_json"))
        data["review_state"] = json.loads(data.pop("review_state_json"))
        data["durable_refs"] = json.loads(data.pop("durable_refs_json"))
        data["replay_excerpt"] = json.loads(data.pop("replay_excerpt_json"))
        return ControlPlaneHandoffEnvelope.model_validate(data)

    def _authority_index_fields(
        self,
        *,
        term_no: int | None,
        commit_index: int | None,
    ) -> dict[str, int | None]:
        return {
            "term_no": term_no,
            "authority_term_no": term_no,
            "commit_index": commit_index,
            "decision_index": commit_index,
        }

    def _authority_term_payload(self, term: SchedulerConsensusTerm) -> dict[str, Any]:
        payload = term.model_dump(mode="json")
        payload["authority_node_id"] = payload.get("leader_node_id")
        payload["authority_term_no"] = payload.get("term_no")
        payload["decision_index"] = payload.get("commit_index")
        return payload

    def _committed_lease_payload(self, committed_lease: SchedulerCommittedLease) -> dict[str, Any]:
        payload = committed_lease.model_dump(mode="json")
        payload.update(
            self._authority_index_fields(
                term_no=committed_lease.term_no,
                commit_index=committed_lease.commit_index,
            )
        )
        return payload

    def _latest_local_only_committed_lease(
        self,
        connection: sqlite3.Connection,
    ) -> SchedulerCommittedLease | None:
        row = connection.execute(
            """
            SELECT * FROM scheduler_committed_leases
             ORDER BY commit_index DESC, created_at DESC
             LIMIT 1
            """
        ).fetchone()
        return self._row_to_committed_lease(row) if row is not None else None

    def _latest_committed_lease_for_domain(
        self,
        connection: sqlite3.Connection,
        *,
        domain_kind: str,
        domain_key: str,
    ) -> SchedulerCommittedLease | None:
        row = connection.execute(
            """
            SELECT * FROM scheduler_committed_leases
             WHERE domain_kind = ? AND domain_key = ?
             ORDER BY commit_index DESC, created_at DESC
             LIMIT 1
            """,
            (domain_kind, domain_key),
        ).fetchone()
        return self._row_to_committed_lease(row) if row is not None else None

    def _active_committed_lease_for_domain(
        self,
        connection: sqlite3.Connection,
        *,
        domain_kind: str,
        domain_key: str,
        now: datetime,
    ) -> SchedulerCommittedLease | None:
        row = connection.execute(
            """
            SELECT * FROM scheduler_committed_leases
             WHERE domain_kind = ? AND domain_key = ? AND status = 'active'
               AND released_at IS NULL AND lease_expires_at > ?
             ORDER BY commit_index DESC
             LIMIT 1
            """,
            (domain_kind, domain_key, now.isoformat()),
        ).fetchone()
        return self._row_to_committed_lease(row) if row is not None else None

    def _get_committed_lease_by_lease_id(
        self,
        connection: sqlite3.Connection,
        lease_id: str,
    ) -> SchedulerCommittedLease | None:
        row = connection.execute(
            "SELECT * FROM scheduler_committed_leases WHERE lease_id = ?",
            (lease_id,),
        ).fetchone()
        return self._row_to_committed_lease(row) if row is not None else None

    def _release_committed_lease(
        self,
        connection: sqlite3.Connection,
        committed_lease: SchedulerCommittedLease,
        *,
        release_reason: str,
    ) -> SchedulerCommittedLease:
        released_at = _utc_now()
        connection.execute(
            """
            UPDATE scheduler_committed_leases
               SET status = 'released', released_at = ?, release_reason = ?
             WHERE committed_lease_id = ?
            """,
            (released_at.isoformat(), release_reason, committed_lease.committed_lease_id),
        )
        return SchedulerCommittedLease.model_validate(
            {
                **committed_lease.model_dump(mode="json"),
                "status": "released",
                "released_at": released_at,
                "release_reason": release_reason,
            }
        )

    def _next_commit_index(self, connection: sqlite3.Connection) -> int:
        row = connection.execute(
            "SELECT COALESCE(MAX(commit_index), 0) AS max_commit_index FROM scheduler_committed_leases"
        ).fetchone()
        return int((row["max_commit_index"] if row is not None else 0) or 0) + 1

    def _synthetic_local_only_term(
        self,
        connection: sqlite3.Connection,
        *,
        now: datetime | None = None,
        latest_committed: SchedulerCommittedLease | None = None,
        commit_index: int | None = None,
    ) -> SchedulerConsensusTerm:
        observed_at = now or _utc_now()
        current = latest_committed or self._latest_local_only_committed_lease(connection)
        resolved_term_no = current.term_no if current is not None else 1
        resolved_commit_index = commit_index if commit_index is not None else (current.commit_index if current is not None else 0)
        started_at = current.created_at if current is not None else observed_at
        return SchedulerConsensusTerm(
            term_no=max(int(resolved_term_no), 1),
            leader_node_id=self.node_id,
            quorum_size=1,
            commit_index=max(int(resolved_commit_index), 0),
            status="active",
            started_at=started_at,
            last_heartbeat_at=observed_at,
        )

    def _local_node_payload(self, observed_at: datetime) -> dict[str, Any]:
        payload = AuthorityNodeIdentity(
            node_id=self.node_id,
            bind_url=self.bind_url,
            status="active",
            role="control_plane",
            last_heartbeat_at=observed_at,
        ).model_dump(mode="json")
        payload["active"] = True
        return payload

    def _cluster_snapshot(
        self,
        connection: sqlite3.Connection,
        *,
        current_term: SchedulerConsensusTerm | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        observed_at = now or _utc_now()
        term = current_term or self._synthetic_local_only_term(connection, now=observed_at)
        return {
            "enabled": False,
            "mode": "local_only",
            "authority_mode": "single_control_plane_local_only",
            "node_count": 1,
            "active_node_count": 1,
            "quorum_size": 1,
            "leader_node_id": self.node_id,
            "authority_node_id": self.node_id,
            "term_no": term.term_no,
            "authority_term_no": term.term_no,
            "commit_index": term.commit_index,
            "decision_index": term.commit_index,
            "nodes": [self._local_node_payload(observed_at)],
        }

    def cluster_snapshot(self, *, connection: sqlite3.Connection | None = None) -> dict[str, Any]:
        if connection is not None:
            return self._cluster_snapshot(connection)
        with unit_of_work(self.db_path) as owned:
            return self._cluster_snapshot(owned)

    def heartbeat_node(
        self,
        *,
        node_id: str | None = None,
        bind_url: str | None = None,
        status: str = "active",
        role: str = "peer",
        observed_at: str | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> dict[str, Any]:
        if connection is not None:
            return self._heartbeat_node(
                connection,
                node_id=node_id,
                bind_url=bind_url,
                status=status,
                role=role,
                observed_at=observed_at,
            )
        with unit_of_work(self.db_path) as owned:
            return self._heartbeat_node(
                owned,
                node_id=node_id,
                bind_url=bind_url,
                status=status,
                role=role,
                observed_at=observed_at,
            )

    def _heartbeat_node(
        self,
        connection: sqlite3.Connection,
        *,
        node_id: str | None = None,
        bind_url: str | None = None,
        status: str = "active",
        role: str = "peer",
        observed_at: str | None = None,
    ) -> dict[str, Any]:
        del node_id
        del bind_url
        del status
        del role
        heartbeat_at = datetime.fromisoformat(observed_at) if observed_at is not None else _utc_now()
        term = self._synthetic_local_only_term(connection, now=heartbeat_at)
        return {
            "node": self._local_node_payload(heartbeat_at),
            "cluster": self._cluster_snapshot(connection, current_term=term, now=heartbeat_at),
        }

    def _disabled_remote_proposal(
        self,
        connection: sqlite3.Connection,
        *,
        control_plane_id: str,
    ) -> dict[str, Any]:
        term = self._synthetic_local_only_term(connection)
        return {
            "enabled": False,
            "proposal": None,
            "decision": None,
            "committed_lease": None,
            "duplicate": False,
            "granted": False,
            "votes": [],
            "term": self._authority_term_payload(term),
            "cluster": self._cluster_snapshot(connection, current_term=term),
            "reason": "scheduler_authority_cluster_disabled_local_only",
            "requested_control_plane_id": control_plane_id,
            "local_control_plane_id": self.node_id,
        }

    def _create_local_only_committed_lease(
        self,
        connection: sqlite3.Connection,
        *,
        proposal: SchedulerLeaseProposal,
        decision: SchedulerLeaseDecision,
        commit_index: int,
        lease_epoch: int,
        term_no: int,
    ) -> SchedulerCommittedLease:
        committed = SchedulerCommittedLease(
            lease_id=decision.lease_id,
            proposal_id=proposal.proposal_id,
            decision_id=decision.decision_id,
            control_plane_id=decision.control_plane_id,
            run_id=decision.run_id,
            runtime_task_id=decision.runtime_task_id,
            domain_kind=decision.domain_kind,
            domain_key=decision.domain_key,
            term_no=term_no,
            commit_index=commit_index,
            lease_epoch=lease_epoch,
            lease_expires_at=decision.lease_expires_at,
        )
        connection.execute(
            """
            INSERT INTO scheduler_committed_leases (
              committed_lease_id, lease_id, proposal_id, decision_id, control_plane_id, run_id, runtime_task_id,
              domain_kind, domain_key, term_no, commit_index, lease_epoch, fencing_token, status, lease_expires_at,
              released_at, release_reason, schema_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                committed.committed_lease_id,
                committed.lease_id,
                committed.proposal_id,
                committed.decision_id,
                committed.control_plane_id,
                committed.run_id,
                committed.runtime_task_id,
                committed.domain_kind,
                committed.domain_key,
                committed.term_no,
                committed.commit_index,
                committed.lease_epoch,
                committed.fencing_token,
                committed.status,
                committed.lease_expires_at.isoformat(),
                None,
                None,
                committed.schema_version,
                committed.created_at.isoformat(),
            ),
        )
        return committed

    def submit_proposal(
        self,
        *,
        control_plane_id: str,
        run_id: str,
        runtime_task_id: str,
        domain_kind: str = "runtime_task",
        domain_key: str,
        requested_lease_seconds: int = 300,
        requested_epoch: int = 1,
        authority_node_id: str | None = None,
        authority_bind_url: str | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> dict[str, Any]:
        if connection is not None:
            return self._submit_proposal(
                connection,
                control_plane_id=control_plane_id,
                run_id=run_id,
                runtime_task_id=runtime_task_id,
                domain_kind=domain_kind,
                domain_key=domain_key,
                requested_lease_seconds=requested_lease_seconds,
                requested_epoch=requested_epoch,
                authority_node_id=authority_node_id,
                authority_bind_url=authority_bind_url,
            )
        with unit_of_work(self.db_path) as owned:
            return self._submit_proposal(
                owned,
                control_plane_id=control_plane_id,
                run_id=run_id,
                runtime_task_id=runtime_task_id,
                domain_kind=domain_kind,
                domain_key=domain_key,
                requested_lease_seconds=requested_lease_seconds,
                requested_epoch=requested_epoch,
                authority_node_id=authority_node_id,
                authority_bind_url=authority_bind_url,
            )

    def _submit_proposal(
        self,
        connection: sqlite3.Connection,
        *,
        control_plane_id: str,
        run_id: str,
        runtime_task_id: str,
        domain_kind: str,
        domain_key: str,
        requested_lease_seconds: int,
        requested_epoch: int,
        authority_node_id: str | None,
        authority_bind_url: str | None,
    ) -> dict[str, Any]:
        del authority_node_id
        del authority_bind_url
        now = _utc_now()
        if control_plane_id != self.node_id:
            return self._disabled_remote_proposal(connection, control_plane_id=control_plane_id)

        proposal = self.scheduler_proposal_repo.create(
            SchedulerLeaseProposal(
                control_plane_id=control_plane_id,
                run_id=run_id,
                runtime_task_id=runtime_task_id,
                domain_kind=domain_kind,
                domain_key=domain_key,
                requested_lease_seconds=requested_lease_seconds,
                requested_epoch=requested_epoch,
            ),
            connection=connection,
        )
        active_committed = self._active_committed_lease_for_domain(
            connection,
            domain_kind=domain_kind,
            domain_key=domain_key,
            now=now,
        )
        latest_committed = self._latest_committed_lease_for_domain(
            connection,
            domain_kind=domain_kind,
            domain_key=domain_key,
        )
        term = self._synthetic_local_only_term(connection, now=now, latest_committed=latest_committed)

        if active_committed is not None:
            latest_decision = self.scheduler_decision_repo.get(active_committed.lease_id, connection=connection)
            if active_committed.control_plane_id == control_plane_id:
                proposal = self.scheduler_proposal_repo.update_status(
                    proposal.proposal_id,
                    "accepted_existing",
                    connection=connection,
                ) or proposal
                term = self._synthetic_local_only_term(connection, now=now, latest_committed=active_committed)
                return {
                    "proposal": proposal.model_dump(mode="json"),
                    "decision": latest_decision.model_dump(mode="json") if latest_decision is not None else None,
                    "committed_lease": self._committed_lease_payload(active_committed),
                    "duplicate": True,
                    "granted": True,
                    "votes": [],
                    "term": self._authority_term_payload(term),
                    "cluster": self._cluster_snapshot(connection, current_term=term, now=now),
                    "previous_committed_lease": (
                        self._committed_lease_payload(latest_committed) if latest_committed is not None else None
                    ),
                }

            conflict = {
                "problem": "active_committed_conflict",
                "control_plane_id": control_plane_id,
                "active_control_plane_id": active_committed.control_plane_id,
                "committed_lease_id": active_committed.committed_lease_id,
                "lease_id": active_committed.lease_id,
                "fencing_token": active_committed.fencing_token,
                "term_no": active_committed.term_no,
                "authority_term_no": active_committed.term_no,
                "commit_index": active_committed.commit_index,
                "decision_index": active_committed.commit_index,
                "lease_epoch": active_committed.lease_epoch,
                "lease_expires_at": active_committed.lease_expires_at.isoformat(),
            }
            decision = self.scheduler_decision_repo.create(
                SchedulerLeaseDecision(
                    proposal_id=proposal.proposal_id,
                    control_plane_id=control_plane_id,
                    run_id=run_id,
                    runtime_task_id=runtime_task_id,
                    domain_kind=domain_kind,
                    domain_key=domain_key,
                    lease_epoch=active_committed.lease_epoch,
                    decision="rejected",
                    reason="conflict_active_committed_lease_owned_by_other_control_plane",
                    lease_expires_at=active_committed.lease_expires_at,
                ),
                connection=connection,
            )
            proposal = self.scheduler_proposal_repo.update_status(proposal.proposal_id, "rejected", connection=connection) or proposal
            return {
                "proposal": proposal.model_dump(mode="json"),
                "decision": decision.model_dump(mode="json"),
                "committed_lease": None,
                "duplicate": False,
                "granted": False,
                "conflict": conflict,
                "votes": [],
                "term": self._authority_term_payload(term),
                "cluster": self._cluster_snapshot(connection, current_term=term, now=now),
                "previous_committed_lease": (
                    self._committed_lease_payload(latest_committed) if latest_committed is not None else None
                ),
            }

        if latest_committed is not None and latest_committed.released_at is None and latest_committed.lease_expires_at <= now:
            latest_committed = self._release_committed_lease(
                connection,
                latest_committed,
                release_reason="expired_before_regrant",
            )
            latest_decision = self.scheduler_decision_repo.get(latest_committed.lease_id, connection=connection)
            if latest_decision is not None:
                self.scheduler_decision_repo.release(
                    latest_decision.lease_id,
                    released_at=now.isoformat(),
                    release_reason="expired_before_regrant",
                    connection=connection,
                )

        lease_epoch = max(requested_epoch, (latest_committed.lease_epoch + 1) if latest_committed is not None else 1)
        decision = self.scheduler_decision_repo.create(
            SchedulerLeaseDecision(
                proposal_id=proposal.proposal_id,
                control_plane_id=control_plane_id,
                run_id=run_id,
                runtime_task_id=runtime_task_id,
                domain_kind=domain_kind,
                domain_key=domain_key,
                lease_epoch=lease_epoch,
                decision="granted",
                reason="local_control_plane_committed",
                lease_expires_at=now + timedelta(seconds=requested_lease_seconds),
            ),
            connection=connection,
        )
        commit_index = self._next_commit_index(connection)
        term = self._synthetic_local_only_term(
            connection,
            now=now,
            latest_committed=latest_committed,
            commit_index=commit_index,
        )
        committed_lease = self._create_local_only_committed_lease(
            connection,
            proposal=proposal,
            decision=decision,
            commit_index=commit_index,
            lease_epoch=lease_epoch,
            term_no=term.term_no,
        )
        proposal = self.scheduler_proposal_repo.update_status(proposal.proposal_id, "granted", connection=connection) or proposal
        return {
            "proposal": proposal.model_dump(mode="json"),
            "decision": decision.model_dump(mode="json"),
            "committed_lease": self._committed_lease_payload(committed_lease),
            "duplicate": False,
            "granted": True,
            "votes": [],
            "term": self._authority_term_payload(term),
            "cluster": self._cluster_snapshot(connection, current_term=term, now=now),
            "previous_committed_lease": (
                self._committed_lease_payload(latest_committed) if latest_committed is not None else None
            ),
        }

    def release_lease(
        self,
        lease_id: str,
        *,
        release_reason: str = "control_plane_release",
        connection: sqlite3.Connection | None = None,
    ) -> dict[str, Any]:
        if connection is not None:
            return self._release_lease(connection, lease_id=lease_id, release_reason=release_reason)
        with unit_of_work(self.db_path) as owned:
            return self._release_lease(owned, lease_id=lease_id, release_reason=release_reason)

    def _release_lease(
        self,
        connection: sqlite3.Connection,
        *,
        lease_id: str,
        release_reason: str,
    ) -> dict[str, Any]:
        committed_lease = self._get_committed_lease_by_lease_id(connection, lease_id)
        if committed_lease is None:
            raise EntityNotFoundError("scheduler_committed_lease", lease_id)
        committed_lease = self._release_committed_lease(connection, committed_lease, release_reason=release_reason)
        decision = self.scheduler_decision_repo.release(
            lease_id,
            released_at=_utc_now().isoformat(),
            release_reason=release_reason,
            connection=connection,
        )
        return {
            "committed_lease": self._committed_lease_payload(committed_lease),
            "decision": decision.model_dump(mode="json") if decision is not None else None,
            "cluster": self._cluster_snapshot(connection),
        }

    def get_lease(
        self,
        lease_id: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> dict[str, Any]:
        if connection is not None:
            return self._get_lease(connection, lease_id=lease_id)
        with unit_of_work(self.db_path) as owned:
            return self._get_lease(owned, lease_id=lease_id)

    def _get_lease(
        self,
        connection: sqlite3.Connection,
        *,
        lease_id: str,
    ) -> dict[str, Any]:
        committed_lease = self._get_committed_lease_by_lease_id(connection, lease_id)
        if committed_lease is None:
            raise EntityNotFoundError("scheduler_committed_lease", lease_id)
        proposal = self.scheduler_proposal_repo.get(committed_lease.proposal_id, connection=connection)
        decision = self.scheduler_decision_repo.get(lease_id, connection=connection)
        now = _utc_now()
        return {
            "lease_id": lease_id,
            "proposal": proposal.model_dump(mode="json") if proposal is not None else None,
            "decision": decision.model_dump(mode="json") if decision is not None else None,
            "committed_lease": self._committed_lease_payload(committed_lease),
            "votes": [],
            "cluster": self._cluster_snapshot(connection),
            "active": committed_lease.status == "active" and committed_lease.released_at is None and committed_lease.lease_expires_at > now,
            "expired": committed_lease.lease_expires_at <= now,
        }

    def get_active_committed_lease_for_domain(
        self,
        *,
        domain_kind: str,
        domain_key: str,
        connection: sqlite3.Connection | None = None,
    ) -> SchedulerCommittedLease | None:
        if connection is not None:
            return self._active_committed_lease_for_domain(connection, domain_kind=domain_kind, domain_key=domain_key, now=_utc_now())
        with unit_of_work(self.db_path) as owned:
            return self._active_committed_lease_for_domain(owned, domain_kind=domain_kind, domain_key=domain_key, now=_utc_now())

    def create_handoff_envelope(
        self,
        *,
        run_id: str,
        runtime_task_id: str,
        from_control_plane_id: str,
        to_control_plane_id: str,
        committed_lease_id: str,
        term_no: int,
        commit_index: int,
        snapshot_payload: dict[str, Any],
        review_state: dict[str, Any],
        durable_refs: dict[str, Any],
        replay_excerpt: dict[str, Any],
        connection: sqlite3.Connection | None = None,
    ) -> ControlPlaneHandoffEnvelope:
        if connection is not None:
            return self._create_handoff_envelope(
                connection,
                run_id=run_id,
                runtime_task_id=runtime_task_id,
                from_control_plane_id=from_control_plane_id,
                to_control_plane_id=to_control_plane_id,
                committed_lease_id=committed_lease_id,
                term_no=term_no,
                commit_index=commit_index,
                snapshot_payload=snapshot_payload,
                review_state=review_state,
                durable_refs=durable_refs,
                replay_excerpt=replay_excerpt,
            )
        with unit_of_work(self.db_path) as owned:
            return self._create_handoff_envelope(
                owned,
                run_id=run_id,
                runtime_task_id=runtime_task_id,
                from_control_plane_id=from_control_plane_id,
                to_control_plane_id=to_control_plane_id,
                committed_lease_id=committed_lease_id,
                term_no=term_no,
                commit_index=commit_index,
                snapshot_payload=snapshot_payload,
                review_state=review_state,
                durable_refs=durable_refs,
                replay_excerpt=replay_excerpt,
            )

    def _create_handoff_envelope(
        self,
        connection: sqlite3.Connection,
        *,
        run_id: str,
        runtime_task_id: str,
        from_control_plane_id: str,
        to_control_plane_id: str,
        committed_lease_id: str,
        term_no: int,
        commit_index: int,
        snapshot_payload: dict[str, Any],
        review_state: dict[str, Any],
        durable_refs: dict[str, Any],
        replay_excerpt: dict[str, Any],
    ) -> ControlPlaneHandoffEnvelope:
        envelope = ControlPlaneHandoffEnvelope(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            from_control_plane_id=from_control_plane_id,
            to_control_plane_id=to_control_plane_id,
            committed_lease_id=committed_lease_id,
            term_no=term_no,
            commit_index=commit_index,
            snapshot_payload=snapshot_payload,
            review_state=review_state,
            durable_refs=durable_refs,
            replay_excerpt=replay_excerpt,
        )
        connection.execute(
            """
            INSERT INTO control_plane_handoff_envelopes (
              envelope_id, run_id, runtime_task_id, from_control_plane_id, to_control_plane_id, committed_lease_id,
              term_no, commit_index, snapshot_payload_json, review_state_json, durable_refs_json, replay_excerpt_json,
              schema_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                envelope.envelope_id,
                envelope.run_id,
                envelope.runtime_task_id,
                envelope.from_control_plane_id,
                envelope.to_control_plane_id,
                envelope.committed_lease_id,
                envelope.term_no,
                envelope.commit_index,
                json.dumps(envelope.snapshot_payload, ensure_ascii=False),
                json.dumps(envelope.review_state, ensure_ascii=False),
                json.dumps(envelope.durable_refs, ensure_ascii=False),
                json.dumps(envelope.replay_excerpt, ensure_ascii=False),
                envelope.schema_version,
                envelope.created_at.isoformat(),
            ),
        )
        return envelope

    def list_handoff_envelopes_for_run(
        self,
        run_id: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> list[ControlPlaneHandoffEnvelope]:
        if connection is not None:
            return self._list_handoff_envelopes_for_run(connection, run_id=run_id)
        with unit_of_work(self.db_path) as owned:
            return self._list_handoff_envelopes_for_run(owned, run_id=run_id)

    def _list_handoff_envelopes_for_run(
        self,
        connection: sqlite3.Connection,
        *,
        run_id: str,
    ) -> list[ControlPlaneHandoffEnvelope]:
        rows = connection.execute(
            """
            SELECT * FROM control_plane_handoff_envelopes
             WHERE run_id = ?
             ORDER BY created_at, envelope_id
            """,
            (run_id,),
        ).fetchall()
        return [self._row_to_handoff(row) for row in rows]
