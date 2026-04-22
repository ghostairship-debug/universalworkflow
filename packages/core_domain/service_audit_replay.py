from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packages.core_domain.services import OrchestratorService


class AuditReplayService:
    """Explicit audit/replay/projection delegation seam for the OrchestratorService facade."""

    def __init__(self, facade: "OrchestratorService") -> None:
        self._facade = facade

    def get_run_summary(self, run_id: str):
        return self._facade.get_run_summary(run_id)

    def get_event_inspection(self, run_id: str):
        return self._facade.get_event_inspection(run_id)

    def get_run_audit_report(self, run_id: str):
        return self._facade.get_run_audit_report(run_id)

    def get_run_replay_packet(self, run_id: str):
        return self._facade.get_run_replay_packet(run_id)

    def get_status_detail(self, run_id: str):
        return self._facade.get_status_detail(run_id)

    def inspect_run_state(self, run_id: str):
        return self._facade.inspect_run_state(run_id)

    def reconcile_run(self, run_id: str, *, apply_repairs: bool = False):
        return self._facade.reconcile_run(run_id, apply_repairs=apply_repairs)

    def get_run_orchestration(self, run_id: str):
        return self._facade.get_run_orchestration(run_id)

    def get_run_orchestration_plan_graph(self, run_id: str):
        return self._facade.get_run_orchestration_plan_graph(run_id)

    def get_run_operator_packet(self, run_id: str):
        return self._facade.get_run_operator_packet(run_id)

    def get_operator_view(self, run_id: str):
        return self._facade.get_operator_view(run_id)

    def get_dashboard_snapshot(self):
        return self._facade.get_dashboard_snapshot()

    def get_run_mutation_report(self, run_id: str):
        return self._facade.get_run_mutation_report(run_id)
