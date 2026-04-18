# M3 Phase 2 - Governance Projection And Tech-Debt Visibility Baseline

**Phase status:** Completed
**Phase position:** This phase starts after `M3 Phase 1` establishes richer event inspection and closure discipline. It turns the existing technical-debt registry into a structured governance surface so later phase reassessment no longer depends only on manually reading markdown tables.

**Entry condition:** `TD-010` remains only partially repaid because governance visibility still depends on manual review of `docs/tech-debt-registry.md`.

---

## 1. Reassessment

Current implementation status:

- Runtime/operator surfaces are now strong enough to explain failure, review state, closure state, and event lineage.
- Governance visibility is still weak because debt tracking remains markdown-only.
- `TD-010` therefore remains open even after stronger summary / event-inspection work.

Legacy references worth absorbing now:

- governance-oriented reporting patterns
- tech-debt dashboard thinking, but not dashboard implementation
- review / closure material as structured governance input

This phase stays intentionally lightweight:

- no dashboard UI
- no background governance daemon
- no issue tracker sync
- no new persistence model for debt data

---

## 2. In Scope

- parse the technical-debt registry into a structured governance report
- expose the governance report through CLI and API
- include governance visibility in offline validation and review materials

---

## 3. Out Of Scope

- dashboard frontend
- persistent metrics store for debt history
- automated debt ticket creation
- changing the debt registry authoring format beyond current markdown tables

---

## 4. Key Constraints

- governance output must stay derivative of the current registry document
- report structure must help phase reassessment without becoming a second source of truth
- the registry document remains the canonical editable artifact

---

## 5. Phase Task Breakdown Principle

This phase is split into three tasks:

1. Tech-debt report parser and governance projection baseline
2. CLI/API governance surfaces and regression tests
3. Docs / validation / review closeout

Each task must pass tests before the next task is considered complete.

---

## 6. Phase Gate

The phase passes only if all of the following are true:

- the tech-debt registry can be projected into a stable structured report
- CLI and API expose the governance report cleanly
- offline validation touches governance visibility
- docs and review materials explain the new governance baseline
- full verification remains green

---

## 7. Outcome

- Added a structured governance report parser for `docs/tech-debt-registry.md`.
- Exposed the report through `workflowctl governance tech-debt` and `GET /governance/tech-debt`.
- Extended offline validation to verify governance visibility alongside runtime/operator acceptance.
- Updated README and review materials, then verified with `pytest -q` (`139 passed`) and `python -m infra.scripts.offline_validation --skip-offline-probe` (`overall_passed=true`).

---

## 8. Next Reassessment

- The next phase should decide whether `M3` continues with richer review-policy governance or whether the remaining roadmap should pivot into the next milestone.
- The immediate governance gap is no longer “can we see the debt registry at all”, but “how far do we want to automate debt / review governance beyond the current markdown-derived report”.
