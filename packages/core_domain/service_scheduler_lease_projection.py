from __future__ import annotations

from typing import TYPE_CHECKING, Any

from packages.contracts import (
    ControlPlaneHandoffEnvelope,
    RuntimeStateRef,
    SchedulerCommittedLease,
    SchedulerConsensusTerm,
    SchedulerLeaseDecision,
    SchedulerLeaseProposal,
    SchedulerPeerHeartbeat,
    SchedulerVoteRecord,
)

if TYPE_CHECKING:
    from packages.core_domain.services import OrchestratorService


class SchedulerLeaseProjectionService:
    """Projection helper for local lease arbiter and legacy scheduler-authority payloads."""

    def __init__(self, facade: "OrchestratorService") -> None:
        self._facade = facade

    def authority_payload(self, state_ref: RuntimeStateRef | None) -> dict[str, Any]:
        payload = (
            dict(state_ref.state_payload.get("scheduler_authority"))
            if state_ref is not None and isinstance(state_ref.state_payload.get("scheduler_authority"), dict)
            else {}
        )
        if state_ref is None:
            return payload
        active_committed_payload = self.committed_lease_payload(payload.get("active_committed_lease"))
        if active_committed_payload is not None:
            payload["active_committed_lease"] = active_committed_payload
        cluster_summary = payload.get("cluster_summary")
        if isinstance(cluster_summary, dict):
            payload["cluster_summary"] = self.cluster_summary_payload(
                cluster=cluster_summary.get("cluster") if isinstance(cluster_summary.get("cluster"), dict) else cluster_summary,
                term=cluster_summary.get("term") if isinstance(cluster_summary.get("term"), dict) else None,
            ) or cluster_summary
        payload["handoff_history"] = [
            self.handoff_envelope_payload(item) or dict(item)
            for item in self.handoff_history(payload)
        ]
        payload["local_control_plane_id"] = self._facade.control_plane_identity.control_plane_id
        active_owner = (
            str(active_committed_payload.get("control_plane_id"))
            if isinstance(active_committed_payload, dict) and active_committed_payload.get("control_plane_id") is not None
            else None
        )
        payload["stale_plane_detected"] = bool(
            active_owner is not None and active_owner != self._facade.control_plane_identity.control_plane_id
        )
        payload["takeover_state"] = {
            "local_control_plane_id": self._facade.control_plane_identity.control_plane_id,
            "active_control_plane_id": active_owner,
            "active_owner_is_local": (
                active_owner == self._facade.control_plane_identity.control_plane_id
                if active_owner is not None
                else None
            ),
            "handoff_count": len(self.handoff_history(payload)),
        }
        return payload

    def decision_history(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        history = payload.get("decision_history")
        return [dict(item) for item in history if isinstance(item, dict)] if isinstance(history, list) else []

    def conflicts(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        conflicts = payload.get("conflicts")
        return [dict(item) for item in conflicts if isinstance(item, dict)] if isinstance(conflicts, list) else []

    def handoff_history(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        handoffs = payload.get("handoff_history")
        return [dict(item) for item in handoffs if isinstance(item, dict)] if isinstance(handoffs, list) else []

    def with_authority_aliases(self, payload: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        aliased = dict(payload)
        if aliased.get("authority_node_id") is None and aliased.get("leader_node_id") is not None:
            aliased["authority_node_id"] = aliased.get("leader_node_id")
        if aliased.get("authority_term_no") is None and aliased.get("term_no") is not None:
            aliased["authority_term_no"] = aliased.get("term_no")
        if aliased.get("decision_index") is None and aliased.get("commit_index") is not None:
            aliased["decision_index"] = aliased.get("commit_index")
        return aliased

    def committed_lease_payload(
        self,
        committed_lease: SchedulerCommittedLease | dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        payload = (
            committed_lease.model_dump(mode="json")
            if isinstance(committed_lease, SchedulerCommittedLease)
            else (dict(committed_lease) if isinstance(committed_lease, dict) else None)
        )
        return self.with_authority_aliases(payload)

    def handoff_envelope_payload(
        self,
        handoff_envelope: ControlPlaneHandoffEnvelope | dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        payload = (
            handoff_envelope.model_dump(mode="json")
            if isinstance(handoff_envelope, ControlPlaneHandoffEnvelope)
            else (dict(handoff_envelope) if isinstance(handoff_envelope, dict) else None)
        )
        return self.with_authority_aliases(payload)

    def cluster_summary_payload(
        self,
        *,
        cluster: dict[str, Any] | None = None,
        term: SchedulerConsensusTerm | dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        def _first_non_none(*values: Any) -> Any:
            for value in values:
                if value is not None:
                    return value
            return None

        if cluster is None and term is None:
            return None
        term_payload = (
            term.model_dump(mode="json")
            if isinstance(term, SchedulerConsensusTerm)
            else (dict(term) if isinstance(term, dict) else None)
        )
        term_payload = self.with_authority_aliases(term_payload)
        cluster_payload = self.with_authority_aliases(dict(cluster) if isinstance(cluster, dict) else {}) or {}
        return {
            "enabled": cluster_payload.get(
                "enabled",
                self._facade.effective_config["scheduler_authority"].get("enabled", True),
            ),
            "mode": cluster_payload.get("mode") or self._facade.effective_config["scheduler_authority"]["mode"],
            "authority_mode": (
                cluster_payload.get("authority_mode")
                or self._facade.effective_config["scheduler_authority"]["authority_mode"]
            ),
            "node_id": self._facade.effective_config["scheduler_authority"]["node_id"],
            "bind_url": self._facade.effective_config["scheduler_authority"]["bind_url"],
            "quorum_size": cluster_payload.get("quorum_size"),
            "leader_node_id": cluster_payload.get("leader_node_id"),
            "authority_node_id": _first_non_none(
                cluster_payload.get("authority_node_id"),
                cluster_payload.get("leader_node_id"),
            ),
            "term_no": _first_non_none(
                cluster_payload.get("term_no"),
                (term_payload or {}).get("term_no"),
            ),
            "authority_term_no": _first_non_none(
                cluster_payload.get("authority_term_no"),
                cluster_payload.get("term_no"),
                (term_payload or {}).get("authority_term_no"),
                (term_payload or {}).get("term_no"),
            ),
            "commit_index": _first_non_none(
                cluster_payload.get("commit_index"),
                (term_payload or {}).get("commit_index"),
            ),
            "decision_index": _first_non_none(
                cluster_payload.get("decision_index"),
                cluster_payload.get("commit_index"),
                (term_payload or {}).get("decision_index"),
                (term_payload or {}).get("commit_index"),
            ),
            "cluster": cluster_payload,
            "term": term_payload,
        }

    def scheduler_context_for_dispatch(self, committed_lease: dict[str, Any] | None) -> dict[str, Any] | None:
        committed_payload = self.committed_lease_payload(committed_lease)
        if committed_payload is None:
            return None
        return {
            "control_plane_id": committed_payload.get("control_plane_id"),
            "committed_lease_id": committed_payload.get("committed_lease_id"),
            "fencing_token": committed_payload.get("fencing_token"),
            "term_no": committed_payload.get("term_no"),
            "authority_term_no": committed_payload.get("authority_term_no"),
            "commit_index": committed_payload.get("commit_index"),
            "decision_index": committed_payload.get("decision_index"),
            "lease_epoch": committed_payload.get("lease_epoch"),
        }

    def arbitration_updates(
        self,
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
        current = self.authority_payload(state_ref)
        history = self.decision_history(current)
        conflicts = self.conflicts(current)
        handoff_history = self.handoff_history(current)
        if decision is not None:
            history.append(decision.model_dump(mode="json"))
        if conflict is not None:
            conflicts.append(conflict)
        if handoff_envelope is not None:
            payload = self.handoff_envelope_payload(handoff_envelope)
            if payload is not None:
                handoff_history.append(payload)
        current_active = current.get("active_decision") if isinstance(current.get("active_decision"), dict) else None
        if decision is not None:
            if decision.decision == "granted" and decision.released_at is None:
                current_active = decision.model_dump(mode="json")
            elif current_active is not None and current_active.get("lease_id") == decision.lease_id:
                current_active = None
        committed_payload = self.committed_lease_payload(committed_lease) or self.with_authority_aliases(
            current.get("active_committed_lease") if isinstance(current.get("active_committed_lease"), dict) else None
        )
        updates: dict[str, Any] = {
            "control_plane_id": control_plane_id,
            "scheduler_authority": {
                "authority_control_plane_id": self._facade.control_plane_identity.control_plane_id,
                "authority_mode": self._facade.effective_config["scheduler_authority"]["authority_mode"],
                "latest_proposal": proposal.model_dump(mode="json") if proposal is not None else current.get("latest_proposal"),
                "latest_decision": decision.model_dump(mode="json") if decision is not None else current.get("latest_decision"),
                "active_decision": current_active,
                "active_committed_lease": committed_payload,
                "cluster_summary": self.cluster_summary_payload(cluster=cluster, term=term) or current.get("cluster_summary"),
                "vote_records": [
                    vote.model_dump(mode="json") if isinstance(vote, SchedulerVoteRecord) else dict(vote)
                    for vote in (votes or [])
                ] or current.get("vote_records"),
                "decision_history": history[-20:],
                "handoff_history": handoff_history[-20:],
                "conflicts": conflicts[-20:],
                "last_peer_heartbeat": (
                    heartbeat.model_dump(mode="json") if heartbeat is not None else current.get("last_peer_heartbeat")
                ),
            },
        }
        if decision is not None:
            updates["lease_epoch"] = decision.lease_epoch
            updates["scheduler_decision_ref"] = decision.decision_id
            updates["scheduler_lease_id"] = decision.lease_id
            updates["arbitration_provenance"] = {
                "decision_id": decision.decision_id,
                "lease_id": decision.lease_id,
                "lease_epoch": decision.lease_epoch,
                "control_plane_id": decision.control_plane_id,
                "authority_control_plane_id": self._facade.control_plane_identity.control_plane_id,
                "decision": decision.decision,
                "reason": decision.reason,
                "lease_expires_at": decision.lease_expires_at.isoformat(),
                "released_at": decision.released_at.isoformat() if decision.released_at is not None else None,
                "release_reason": decision.release_reason,
                "committed_lease_id": committed_payload.get("committed_lease_id") if isinstance(committed_payload, dict) else None,
                "fencing_token": committed_payload.get("fencing_token") if isinstance(committed_payload, dict) else None,
                "term_no": committed_payload.get("term_no") if isinstance(committed_payload, dict) else None,
                "authority_term_no": (
                    committed_payload.get("authority_term_no") if isinstance(committed_payload, dict) else None
                ),
                "commit_index": committed_payload.get("commit_index") if isinstance(committed_payload, dict) else None,
                "decision_index": committed_payload.get("decision_index") if isinstance(committed_payload, dict) else None,
            }
        return updates
