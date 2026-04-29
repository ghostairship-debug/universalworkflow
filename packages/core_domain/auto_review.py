from __future__ import annotations

from typing import Any

from packages.contracts import Evidence, ReviewDecision, ReviewVerdict


class AutoReviewV0:
    def review(self, evidence: Evidence) -> ReviewVerdict:
        mutation_result = _mutation_result_from_evidence(evidence)
        mutation_test_status = (
            mutation_result.get("final_test_status") if isinstance(mutation_result, dict) else None
        )
        mutation_tests_ok = mutation_test_status in {None, "passed", "not_requested"}
        decision = ReviewDecision.pass_ if evidence.return_code == 0 and mutation_tests_ok else ReviewDecision.fail
        rationale = (
            "Return code is zero and required mutation tests passed."
            if decision == ReviewDecision.pass_
            else "Return code is non-zero or required mutation tests failed."
        )
        return ReviewVerdict(
            run_id=evidence.run_id,
            evidence_id=evidence.evidence_id,
            decision=decision,
            rationale=rationale,
        )


def _mutation_result_from_evidence(evidence: Evidence) -> dict[str, Any] | None:
    metadata = evidence.raw_execution.get("metadata")
    if isinstance(metadata, dict) and isinstance(metadata.get("mutation_result"), dict):
        return metadata["mutation_result"]
    if evidence.result_envelope is not None and evidence.result_envelope.mutations is not None:
        return evidence.result_envelope.mutations
    return None
