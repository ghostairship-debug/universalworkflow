from __future__ import annotations

from typing import Any


READY_STATUSES = {"passed"}
NO_TEST_STATUSES = {"not_requested", None}


def _compact_attempt(attempt: dict[str, Any]) -> dict[str, Any]:
    return {
        "iteration": attempt.get("iteration"),
        "command": attempt.get("command"),
        "argv": attempt.get("argv"),
        "status": attempt.get("status"),
        "passed": bool(attempt.get("passed")),
        "return_code": attempt.get("return_code"),
        "review_required": bool(attempt.get("review_required")),
        "stdout_truncated": bool(attempt.get("stdout_truncated")),
        "stderr_truncated": bool(attempt.get("stderr_truncated")),
    }


def _test_summary(mutation_result: dict[str, Any] | None) -> dict[str, Any]:
    attempts = list(mutation_result.get("test_attempts", [])) if isinstance(mutation_result, dict) else []
    compact_attempts = [_compact_attempt(attempt) for attempt in attempts if isinstance(attempt, dict)]
    passed_count = len([attempt for attempt in compact_attempts if attempt["passed"]])
    review_required_count = len([attempt for attempt in compact_attempts if attempt["review_required"]])
    failed_count = len(compact_attempts) - passed_count
    final_status = mutation_result.get("final_test_status") if isinstance(mutation_result, dict) else None
    if final_status is None:
        final_status = "not_requested"
    return {
        "status": final_status,
        "attempt_count": len(compact_attempts),
        "passed_count": passed_count,
        "failed_count": failed_count,
        "review_required_count": review_required_count,
        "attempts": compact_attempts,
    }


def _risk_notes(
    *,
    mutation_contract: dict[str, Any] | None,
    mutation_result: dict[str, Any] | None,
    tests: dict[str, Any],
    review: dict[str, Any],
) -> list[str]:
    notes: list[str] = []
    if not isinstance(mutation_contract, dict):
        notes.append("no_mutation_contract")
    elif mutation_contract.get("mutation_mode") != "patch_apply":
        notes.append("not_a_bounded_patch_apply_run")
    if isinstance(mutation_contract, dict) and not mutation_contract.get("write_set"):
        notes.append("missing_write_set")
    if tests["status"] in NO_TEST_STATUSES:
        notes.append("tests_not_requested")
    if tests["failed_count"] > 0:
        notes.append("test_failure_present")
    if tests["review_required_count"] > 0:
        notes.append("test_attempt_requires_review")
    if isinstance(mutation_result, dict) and mutation_result.get("out_of_scope_rejections"):
        notes.append("out_of_scope_patch_rejected")
    if review.get("pending_human_review"):
        notes.append("human_review_pending")
    if review.get("latest_review_decision") == "fail":
        notes.append("latest_review_failed")
    return notes


def _readiness_for(
    *,
    run_status: str,
    failure_taxonomy: dict[str, Any],
    closure_summary: dict[str, Any],
    mutation_result: dict[str, Any] | None,
    tests: dict[str, Any],
    review: dict[str, Any],
    risk_notes: list[str],
) -> str:
    if run_status != "completed":
        if review.get("pending_human_review") or "test_attempt_requires_review" in risk_notes:
            return "review_required"
        if failure_taxonomy.get("is_failure") or run_status in {"failed", "cancelled"}:
            return "blocked"
        return "not_ready"
    if not isinstance(mutation_result, dict):
        return "not_ready"
    if review.get("pending_human_review") or "test_attempt_requires_review" in risk_notes:
        return "review_required"
    if failure_taxonomy.get("is_failure") or closure_summary.get("state") not in {"closed", None}:
        return "blocked"
    if isinstance(mutation_result, dict):
        final_status = mutation_result.get("final_test_status")
        if final_status not in READY_STATUSES:
            return "review_required" if final_status in NO_TEST_STATUSES else "blocked"
    if tests["failed_count"] > 0:
        return "blocked"
    return "ready"


def _next_action_for(readiness: str, summary: dict[str, Any]) -> str:
    if readiness == "ready":
        return "prepare_local_commit_or_pr_manually"
    if readiness == "review_required":
        return "complete_human_review_or_adjust_test_contract"
    if readiness == "blocked":
        return summary.get("recoverability_hint") or "inspect_evidence_then_recompile"
    return summary.get("next_action") or "resume_or_inspect_run"


def _markdown_for(payload: dict[str, Any]) -> str:
    changed_files = payload["bounded_patch"]["changed_files"] or ["(none)"]
    test_status = payload["tests"]["status"]
    review = payload["review"]
    lines = [
        f"# PR-ready summary: {payload['goal']}",
        "",
        f"- Readiness: {payload['readiness']}",
        f"- Run: {payload['run_id']} ({payload['run_status']})",
        f"- Task card: {payload['task_card']['ref'] or '-'}",
        f"- Changed files: {', '.join(changed_files)}",
        f"- Tests: {test_status} ({payload['tests']['passed_count']}/{payload['tests']['attempt_count']} passed)",
        f"- Review: {review.get('latest_review_decision') or review.get('effective_review_state')}",
        f"- Next action: {payload['next_action']}",
        "",
        "Manual boundary: no git commit, push, or PR was created by this summary.",
    ]
    if payload["risk_notes"]:
        lines.extend(["", "Risk notes:"])
        lines.extend([f"- {note}" for note in payload["risk_notes"]])
    return "\n".join(lines)


def build_pr_ready_summary(summary: dict[str, Any]) -> dict[str, Any]:
    run = summary["run"]
    mutation_contract = summary.get("mutation_contract")
    mutation_result = summary.get("mutation_result")
    tests = _test_summary(mutation_result)
    review = dict(summary.get("review_summary") or {})
    risk_notes = _risk_notes(
        mutation_contract=mutation_contract if isinstance(mutation_contract, dict) else None,
        mutation_result=mutation_result if isinstance(mutation_result, dict) else None,
        tests=tests,
        review=review,
    )
    readiness = _readiness_for(
        run_status=str(run["status"]),
        failure_taxonomy=summary.get("failure_taxonomy") or {},
        closure_summary=summary.get("closure_summary") or {},
        mutation_result=mutation_result if isinstance(mutation_result, dict) else None,
        tests=tests,
        review=review,
        risk_notes=risk_notes,
    )
    payload = {
        "summary_version": "m38_phase_4_v1",
        "run_id": run["run_id"],
        "goal": run["goal"],
        "run_status": run["status"],
        "readiness": readiness,
        "ready": readiness == "ready",
        "task_card": {
            "ref": mutation_contract.get("task_card_ref") if isinstance(mutation_contract, dict) else None,
            "path": mutation_contract.get("task_card_path") if isinstance(mutation_contract, dict) else None,
        },
        "bounded_patch": {
            "enabled": isinstance(mutation_contract, dict) and mutation_contract.get("mutation_mode") == "patch_apply",
            "mutation_mode": mutation_contract.get("mutation_mode") if isinstance(mutation_contract, dict) else None,
            "write_set": mutation_contract.get("write_set", []) if isinstance(mutation_contract, dict) else [],
            "read_set": mutation_contract.get("read_set", []) if isinstance(mutation_contract, dict) else [],
            "changed_files": mutation_result.get("changed_files", []) if isinstance(mutation_result, dict) else [],
            "applied_patch_hash": (
                mutation_result.get("applied_patch_hash") if isinstance(mutation_result, dict) else None
            ),
            "fix_iteration_count": (
                mutation_result.get("fix_iteration_count") if isinstance(mutation_result, dict) else None
            ),
        },
        "tests": tests,
        "review": {
            "effective_review_state": review.get("effective_review_state"),
            "latest_review_decision": review.get("latest_review_decision"),
            "latest_reviewer_type": review.get("latest_reviewer_type"),
            "pending_human_review": bool(review.get("pending_human_review")),
        },
        "risk_notes": risk_notes,
        "next_action": _next_action_for(readiness, summary),
        "manual_git": {
            "commit": "not_performed",
            "push": "not_performed",
            "create_pr": "not_performed",
        },
    }
    payload["markdown"] = _markdown_for(payload)
    return payload
