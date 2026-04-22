from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packages.core_domain.services import OrchestratorService


class ReviewPolicyService:
    """Explicit review-policy delegation seam for the OrchestratorService facade."""

    def __init__(self, facade: "OrchestratorService") -> None:
        self._facade = facade

    def approve_run_review(self, run_id: str):
        return self._facade.approve_run_review(run_id)

    def reject_run_review(self, run_id: str, rationale: str):
        return self._facade.reject_run_review(run_id, rationale)
