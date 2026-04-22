from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.core_domain.services import OrchestratorService


class RunLifecycleService:
    """Explicit lifecycle delegation seam for the OrchestratorService facade."""

    def __init__(self, facade: "OrchestratorService") -> None:
        self._facade = facade

    def list_presets(self):
        return self._facade.list_presets()

    def list_runs(self):
        return self._facade.list_runs()

    def suggest_presets(self, goal_text: str):
        return self._facade.suggest_presets(goal_text)

    def create_run(self, goal: str, preset_id: str):
        return self._facade.create_run(goal, preset_id)

    def get_run(self, run_id: str):
        return self._facade.get_run(run_id)

    def prepare_run(self, run_id: str, **kwargs: Any):
        return self._facade.prepare_run(run_id, **kwargs)

    def compile_run(self, run_id: str, **kwargs: Any):
        return self._facade.compile_run(run_id, **kwargs)

    def recompile_run(self, run_id: str, **kwargs: Any):
        return self._facade.recompile_run(run_id, **kwargs)

    def resume_run(self, run_id: str):
        return self._facade.resume_run(run_id)

    def execute_run(self, run_id: str):
        return self._facade.execute_run(run_id)

    def resume_runs_parallel(self, run_ids: list[str], *, max_workers: int = 2):
        return self._facade.resume_runs_parallel(run_ids, max_workers=max_workers)

    def cancel_run(self, run_id: str):
        return self._facade.cancel_run(run_id)

    def apply_run_repair(self, run_id: str, action: str):
        return self._facade.apply_run_repair(run_id, action)
