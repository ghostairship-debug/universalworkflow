# M3 Phase 3 - Run Audit Report And Review Packet Baseline

**Phase status:** Completed
**Phase position:** This phase starts after `M3 Phase 2` establishes governance visibility for technical debt. It packages the existing run-facing observability surfaces into a single audit bundle for review, handoff, and future dashboard/reporting work.

**Entry condition:** Summary, event inspection, state inspection, and governance visibility are already stable, but operators still need to manually assemble multiple surfaces when preparing a review or handoff packet.

---

## 1. Reassessment

Current implementation status:

- `run summary` explains outcome and closure state.
- `run event-inspection` explains event digest and closure audit.
- `run inspect` explains state inconsistencies and repair recommendations.
- Operators still need to manually combine these surfaces when exporting a single review-ready audit packet.

Legacy references worth absorbing now:

- structured completion / review summary packaging
- governance-oriented reporting patterns
- review / closure discipline expressed as a single audit artifact

This phase stays intentionally lightweight:

- no PDF export
- no dashboard UI
- no separate audit persistence table

---

## 2. In Scope

- define a single run-audit report surface that bundles the existing operator-facing projections
- expose the audit bundle through CLI and API
- add audit-report coverage to docs and offline validation

---

## 3. Out Of Scope

- file export formats such as PDF / DOCX
- long-term report storage
- background audit generation

---

## 4. Key Constraints

- audit output must stay derivative of existing persisted state
- the audit bundle must not become a competing source of truth
- raw surfaces must remain available for deeper debugging

---

## 5. Phase Task Breakdown Principle

This phase is split into three tasks:

1. Service-level run audit report assembly
2. CLI/API audit-report surfaces and regression tests
3. Docs / validation / review closeout

Each task must pass tests before the next task is considered complete.

---

## 6. Phase Gate

The phase passes only if all of the following are true:

- a stable run-audit report surface exists for any run
- CLI and API expose the audit-report surface cleanly
- offline validation exercises the audit bundle
- docs and review materials explain how the audit report fits into operator workflow
- full verification remains green

---

## 7. Outcome

- Added a structured run-audit report that bundles summary, event inspection, state inspection, review packet, and recent timeline context.
- Exposed the bundle through `workflowctl run audit-report` and `GET /runs/{run_id}/audit-report`.
- Updated README, offline validation, and review materials, then verified with `pytest -q` (`143 passed`) and `python -m infra.scripts.offline_validation --skip-offline-probe` (`overall_passed=true`).

---

## 8. Next Reassessment

- The next phase should decide whether to keep expanding `M3` governance/reporting, or whether the remaining roadmap should pivot into the next major milestone.
- The immediate gap is no longer missing audit packaging; it is deciding how far to automate governance, review policy richness, and longer-lived reporting artifacts.
