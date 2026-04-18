# M3 Phase 0 - Failure Taxonomy And Run Summary Baseline

**Phase status:** Completed
**Phase position:** This phase starts after `M2 Phase 5` closes the runtime-attempt baseline. It shifts the roadmap from runtime ownership primitives to observability / governance surfaces that make failures, closure state, and operator summaries easier to audit.

**Entry condition:** `M2` has explicit reconcile, claim, worker-lease, snapshot, budget, and runtime-attempt visibility, but richer failure taxonomy and structured closure summaries are still missing.

---

## 1. Reassessment

Current implementation status:

- Operator surfaces already expose raw details through `status-detail`, `inspection`, timeline, claims, leases, snapshots, budget, and attempts.
- Those surfaces are useful, but they still require operators to mentally compose failure state and closure state from many separate projections.
- `TD-007` and `TD-010` remain open because event inspection and governance summaries are still minimal.

Legacy references worth absorbing now:

- failure taxonomy
- richer run event inspection
- structured completion / review summary discipline
- governance-oriented review wording, not legacy orchestration structure

This phase stays intentionally lightweight:

- no trace ingestion system
- no metrics backend
- no dashboard server
- no legacy facade aggregation

---

## 2. In Scope

- define a stable operator-facing failure taxonomy for current run outcomes
- add a structured run summary surface that condenses closure state, review state, timeline digest, and ownership projections
- expose the summary through CLI and API
- update docs and validation so summary surfaces become part of standard acceptance

---

## 3. Out Of Scope

- full metrics / tracing stack
- distributed observability storage
- alerting or background monitoring daemons
- generalized dashboard UI

---

## 4. Key Constraints

- taxonomy must describe current repo semantics only
- summaries must reuse existing repository state instead of creating a second audit model
- output should improve scanability without hiding the underlying detailed surfaces

---

## 5. Phase Task Breakdown Principle

This phase is split into three tasks:

1. Failure taxonomy and run-summary service baseline
2. CLI/API summary surfaces and regression tests
3. Docs / validation / review closeout

Each task must pass tests before the next task is considered complete.

---

## 6. Phase Gate

The phase passes only if all of the following are true:

- a stable summary surface exists for any run
- failure taxonomy is explicit for completed / failed / cancelled / awaiting_review paths
- CLI and API expose the summary cleanly
- docs and validation mention the summary surface
- full `pytest` passes

---

## 7. Risks And Rollback

- Risk: summary becomes a misleading “single truth” and hides important detail
  Control: keep raw detail surfaces intact and make the summary derivative only
- Risk: taxonomy names overclaim semantics beyond current runtime
  Control: map only from current run / review / inspection state
- Risk: M3 starts drifting into dashboard work too early
  Control: keep this phase CLI/API-first and documentation-backed

---

## 8. Outcome

- Added a structured run-summary surface with explicit failure taxonomy, review summary, timeline digest, and ownership summary.
- Exposed the summary through `workflowctl run summary` and `GET /runs/{run_id}/summary`.
- Added summary coverage to README and offline validation, then verified with `pytest -q` (`131 passed`) and `python -m infra.scripts.offline_validation --skip-offline-probe` (`overall_passed=true`).

## 9. Next Reassessment

- The next phase should decide whether to continue inside `M3` with richer event inspection / review closure discipline, or to prioritize governance automation such as debt reporting and review dashboards.
- The immediate gaps are no longer raw runtime lineage or summary visibility; they are deeper event analysis, richer review policy governance, and debt observability.
