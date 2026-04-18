# M3 Phase 4 - Review Policy Governance And Expansion Baseline

**Phase status:** Completed
**Phase position:** This phase starts after `M3 Phase 3` establishes a run-audit report baseline. It focuses on the remaining M3 governance gap around richer review-policy semantics and policy visibility.

**Entry condition:** `TD-006` is still only partially repaid: the runtime supports `auto_only` and `human_required`, but richer review-policy governance is still missing.

---

## 1. Reassessment

Current implementation status:

- Operators can now inspect summary, event inspection, state inspection, governance debt visibility, and run audit reports.
- The remaining M3 governance gap is no longer packaging or visibility.
- It is the lack of a stronger policy-facing model for review semantics and future policy expansion.

Legacy references worth absorbing now:

- richer review policy routing cases
- policy decision-table style validation
- governance-facing review semantics, not legacy phase/task-card review chains

---

## 2. In Scope

- define a policy-facing review semantics report for current presets and current runtime behavior
- make future richer policy expansion explicit without forcing immediate runtime support for every legacy policy
- expose the report through governance-facing surfaces

---

## 3. Out Of Scope

- introducing full optional / recommended / mandatory execution semantics in one step
- adding new review persistence tables
- reintroducing legacy phase review chains

---

## 4. Phase Task Breakdown Principle

This phase is expected to split into:

1. Review policy catalog and semantics report baseline
2. CLI/API governance surfaces plus regression tests
3. Docs / decision-table / validation closeout

---

## 5. Phase Gate

The phase passes only if all of the following are true:

- a structured review-policy governance report exists
- CLI and API expose the report cleanly
- future richer policies are explicit as reference-only candidates rather than pretending to be implemented
- docs and offline validation cover the report
- full verification remains green

---

## 6. Outcome

- Added a structured review-policy governance report over the current preset catalog and operator state matrix.
- Exposed the report through `workflowctl governance review-policy` and `GET /governance/review-policy`.
- Updated README, the decision table, the debt registry, and offline validation, then verified with `pytest -q` (`146 passed`) and `python -m infra.scripts.offline_validation --skip-offline-probe` (`overall_passed=true`).

---

## 7. Next Reassessment

- The next phase should decide whether to continue inside `M3` with broader governance rollups, or pivot into the next milestone with `M3` governance sufficiently established.
- The remaining gap is no longer policy visibility; it is deciding how much actual runtime policy expansion is worth taking on next.
