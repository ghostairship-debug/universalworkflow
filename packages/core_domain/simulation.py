from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.contracts import CheckResult, SimulationPolicyDefinition, SimulationReport, SimulationReportStatus, SimulationTriggerPolicy


DEFAULT_SIMULATION_POLICY_SEED_PATH = Path("infra/seeds/simulation_policies.json")
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_seed_simulation_policies(
    seed_path: Path | str = DEFAULT_SIMULATION_POLICY_SEED_PATH,
) -> list[SimulationPolicyDefinition]:
    path = Path(seed_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    data = json.loads(path.read_text(encoding="utf-8"))
    return [SimulationPolicyDefinition.model_validate(item) for item in data]


class SimulationPolicyRegistry:
    def __init__(self, policies: list[SimulationPolicyDefinition] | None = None):
        self._policies = {
            policy.policy_id: policy for policy in (policies or load_seed_simulation_policies())
        }

    def list(self) -> list[SimulationPolicyDefinition]:
        return sorted(self._policies.values(), key=lambda item: item.policy_id)

    def get(self, policy_id: str) -> SimulationPolicyDefinition | None:
        return self._policies.get(policy_id)

    def match(self, preset_id: str) -> SimulationPolicyDefinition | None:
        for policy in self.list():
            if preset_id in policy.preset_ids:
                return policy
        return None


class LocalDeterministicSimulationRunner:
    def run(
        self,
        policy: SimulationPolicyDefinition,
        detail: dict[str, Any],
        inspection: dict[str, Any],
    ) -> SimulationReport:
        run_status = str(detail["run"]["status"])
        failure_like = inspection["problem_count"] > 0 or run_status in {"failed", "cancelled"}

        if policy.trigger_policy == SimulationTriggerPolicy.disabled:
            return SimulationReport(
                run_id=detail["run"]["run_id"],
                preset_id=detail["run"]["preset_id"],
                policy_id=policy.policy_id,
                trigger_policy=policy.trigger_policy,
                simulator_name=policy.simulator_name,
                triggered=False,
                status=SimulationReportStatus.skipped,
                reason="disabled_by_policy",
                summary="Simulation skipped because the preset policy disables it.",
                recommended_action="none",
            )

        if policy.trigger_policy == SimulationTriggerPolicy.failure_only and not failure_like:
            return SimulationReport(
                run_id=detail["run"]["run_id"],
                preset_id=detail["run"]["preset_id"],
                policy_id=policy.policy_id,
                trigger_policy=policy.trigger_policy,
                simulator_name=policy.simulator_name,
                triggered=False,
                status=SimulationReportStatus.skipped,
                reason="policy_not_triggered",
                summary="Simulation skipped because the failure-only policy did not trigger for the current run state.",
                recommended_action="none",
            )

        checks = [
            self._inspection_consistency_check(inspection),
            self._runtime_terminal_alignment_check(detail),
            self._review_state_alignment_check(detail),
        ]
        failed_checks = [check for check in checks if check.status != "pass"]
        status = SimulationReportStatus.failed if failed_checks else SimulationReportStatus.passed
        finding_codes = [check.name for check in failed_checks]
        recommended_action = detail["recoverability_hint"] if failed_checks else "none"
        summary = (
            "Simulation detected follow-up issues in the current run state."
            if failed_checks
            else "Simulation passed with no deterministic consistency findings."
        )
        reason = (
            "triggered_by_failure_only_policy"
            if policy.trigger_policy == SimulationTriggerPolicy.failure_only
            else "triggered_by_always_policy"
        )
        return SimulationReport(
            run_id=detail["run"]["run_id"],
            preset_id=detail["run"]["preset_id"],
            policy_id=policy.policy_id,
            trigger_policy=policy.trigger_policy,
            simulator_name=policy.simulator_name,
            triggered=True,
            status=status,
            reason=reason,
            summary=summary,
            finding_codes=finding_codes,
            recommended_action=recommended_action,
            check_results=checks,
        )

    def _inspection_consistency_check(self, inspection: dict[str, Any]) -> CheckResult:
        problem_count = inspection["problem_count"]
        if problem_count == 0:
            return CheckResult(name="inspection_consistency", status="pass", detail="No inspection problems detected.")
        return CheckResult(
            name="inspection_consistency",
            status="fail",
            detail=f"{problem_count} inspection problem(s) detected.",
        )

    def _runtime_terminal_alignment_check(self, detail: dict[str, Any]) -> CheckResult:
        run_status = str(detail["run"]["status"])
        last_runtime_state = detail.get("last_runtime_state")
        if run_status not in {"completed", "failed", "cancelled"}:
            return CheckResult(
                name="runtime_terminal_alignment",
                status="pass",
                detail="Run is not in a terminal state; terminal runtime alignment is not required.",
            )
        if last_runtime_state is not None and last_runtime_state.get("is_terminal") is True:
            return CheckResult(
                name="runtime_terminal_alignment",
                status="pass",
                detail="Terminal run status aligns with a terminal runtime state.",
            )
        return CheckResult(
            name="runtime_terminal_alignment",
            status="fail",
            detail="Terminal run status does not align with a terminal runtime state.",
        )

    def _review_state_alignment_check(self, detail: dict[str, Any]) -> CheckResult:
        run_status = str(detail["run"]["status"])
        review_policy = detail.get("review_policy")
        review_state = detail.get("effective_review_state")
        if run_status == "awaiting_review":
            passed = review_state == "human_pending"
            detail_text = (
                "Awaiting-review run still correctly projects human_pending."
                if passed
                else f"Awaiting-review run projected unexpected review state `{review_state}`."
            )
            return CheckResult(name="review_state_alignment", status="pass" if passed else "fail", detail=detail_text)
        if run_status == "completed" and review_policy in {"human_required", "mandatory"}:
            passed = review_state == "human_approved"
            detail_text = (
                "Completed run has the required human approval closure."
                if passed
                else f"Completed run with `{review_policy}` projected `{review_state}` instead of `human_approved`."
            )
            return CheckResult(name="review_state_alignment", status="pass" if passed else "fail", detail=detail_text)
        if run_status == "completed" and review_policy in {"auto_only", "recommended"}:
            passed = review_state == "auto_passed"
            detail_text = (
                "Completed auto-reviewed run correctly projects auto_passed."
                if passed
                else f"Completed run with `{review_policy}` projected `{review_state}` instead of `auto_passed`."
            )
            return CheckResult(name="review_state_alignment", status="pass" if passed else "fail", detail=detail_text)
        if run_status == "failed" and detail.get("failure_reason") == "human_review_rejected":
            passed = review_state == "human_rejected"
            detail_text = (
                "Failed run correctly reflects human rejection."
                if passed
                else f"Human-rejected run projected `{review_state}` instead of `human_rejected`."
            )
            return CheckResult(name="review_state_alignment", status="pass" if passed else "fail", detail=detail_text)
        return CheckResult(
            name="review_state_alignment",
            status="pass",
            detail="No stricter review-state alignment rule applied for this run state.",
        )
