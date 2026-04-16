from __future__ import annotations

from packages.contracts import Evidence, ReviewDecision, ReviewVerdict


class AutoReviewV0:
    def review(self, evidence: Evidence) -> ReviewVerdict:
        stderr = str(evidence.raw_execution.get("stderr", "")).strip()
        decision = ReviewDecision.pass_ if evidence.return_code == 0 and not stderr else ReviewDecision.fail
        rationale = (
            "Return code is zero and stderr is empty."
            if decision == ReviewDecision.pass_
            else "Return code is non-zero or stderr contains output."
        )
        return ReviewVerdict(
            run_id=evidence.run_id,
            evidence_id=evidence.evidence_id,
            decision=decision,
            rationale=rationale,
        )
