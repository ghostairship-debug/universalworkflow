from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.core_domain.services import OrchestratorService


class OwnershipLeaseService:
    """Explicit ownership/lease/scheduler delegation seam for the OrchestratorService facade."""

    def __init__(self, facade: "OrchestratorService") -> None:
        self._facade = facade

    def list_handoffs(self, run_id: str):
        return self._facade.list_handoffs(run_id)

    def list_claims(self, run_id: str):
        return self._facade.list_claims(run_id)

    def list_worker_leases(self, run_id: str):
        return self._facade.list_worker_leases(run_id)

    def list_runtime_attempts(self, run_id: str):
        return self._facade.list_runtime_attempts(run_id)

    def list_snapshots(self, run_id: str):
        return self._facade.list_snapshots(run_id)

    def get_budget_ledger(self, run_id: str):
        return self._facade.get_budget_ledger(run_id)

    def submit_scheduler_proposal(self, **kwargs: Any):
        return self._facade.submit_scheduler_proposal(**kwargs)

    def record_scheduler_peer_heartbeat(self, **kwargs: Any):
        return self._facade.record_scheduler_peer_heartbeat(**kwargs)

    def release_scheduler_lease(self, lease_id: str, **kwargs: Any):
        return self._facade.release_scheduler_lease(lease_id, **kwargs)

    def get_scheduler_lease(self, lease_id: str):
        return self._facade.get_scheduler_lease(lease_id)

    def record_worker_heartbeat(self, **kwargs: Any):
        return self._facade.record_worker_heartbeat(**kwargs)

    def record_worker_completion(self, **kwargs: Any):
        return self._facade.record_worker_completion(**kwargs)
