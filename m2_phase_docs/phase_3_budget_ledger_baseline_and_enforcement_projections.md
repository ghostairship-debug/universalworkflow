# M2 Phase 3 - Budget Ledger Baseline And Enforcement Projections

**Phase status:** Completed
**Verification summary:** `pytest` passed with `102 passed`; `python -m infra.scripts.offline_validation --skip-offline-probe` returned `overall_passed=true` and now covers budget-aware CLI, smoke, and API flows.

**Phase position:** This phase starts after `M2 Phase 2` establishes replay-friendly run snapshots. It turns preset budget policy from a schema shape into a persisted, operator-visible ledger baseline.

**Entry condition:** `M2 Phase 2` is complete, snapshot capture is stable, and operator surfaces already expose claim and snapshot diagnostics.

---

## 1. Reassessment

Current implementation status:

- Presets already carry `max_retries` and `timeout_seconds`, but they are still only configuration shapes.
- The repository has no persisted budget ledger, no consumption reporting, and no stable projection of remaining retry headroom.
- The next highest-value step is therefore explicit budget accounting and operator projections, not deeper worker-lease semantics yet.

Legacy references worth absorbing now:

- budget / retry accounting patterns
- operator-visible enforcement projections instead of hidden side effects

This phase keeps the current run-centric architecture intact:

- no distributed quota service
- no cost-based scheduler
- no LLM token accounting

---

## 2. In Scope

- add a persisted `BudgetLedger` contract and repository baseline
- create a ledger per run from preset budget policy
- record compile / recompile / execution consumption into the ledger
- project remaining retry and timeout budget through operator surfaces
- add tests for ledger creation, update, projection, and bounded enforcement

---

## 3. Out Of Scope

- cross-run portfolio budgeting
- distributed quota coordination
- token or billing integration
- automatic retry loops
- adaptive scheduling based on budget

---

## 4. Key Constraints

- budget semantics must stay local and deterministic
- ledger updates must be auditable and lightweight
- enforcement must stay explicit and operator-visible
- this phase may block over-budget operations, but must not invent hidden retry automation
- projections must align with current run-centric flow

---

## 5. Phase Task Breakdown Principle

This phase is split into three complex tasks:

1. Budget ledger contract, migration, repository, and query surfaces
2. Service accounting hooks plus enforcement / projection integration
3. CLI/API/docs/verification closeout

Each task must ship with tests before the next task is considered complete.

---

## 6. Phase Gate

The phase passes only if all of the following are true:

- budget ledgers are persisted and queryable
- compile / recompile / execution paths update the ledger consistently
- status / inspection surfaces expose budget projections clearly
- at least one bounded enforcement rule is applied with a stable error
- CLI and API expose budget visibility
- full `pytest` passes

Gate outcome:

- Passed: budget ledgers are now persisted, queryable, and created from preset budget policy
- Passed: compile, recompile, and execution paths update the ledger consistently
- Passed: status / inspection now expose budget ledger state and remaining retry / timeout headroom
- Passed: retry-budget exhaustion is enforced with the stable `budget_exhausted` error while repair-driven recompile stays explicitly exempt
- Passed: CLI and API both expose budget visibility
- Passed: full `pytest` and offline validation succeeded

---

## 7. Risks And Rollback

- Risk: budget rules look stronger than they really are
  Control: document them as local run-budget projections only
- Risk: ledger updates drift from actual execution events
  Control: hook updates to explicit lifecycle boundaries and test each path
- Risk: enforcement becomes surprising to operators
  Control: return structured errors and expose remaining headroom in status surfaces

## 8. Outcome

- The repository now has an explicit `BudgetLedger` baseline instead of treating budget policy as preset-only metadata.
- Current M2 work now covers claim lifecycle, replay-friendly snapshots, and operator-visible budget accounting without importing a legacy kernel.
- The next recommended phase is `M2 Phase 4 - Worker Lease Heartbeat And Interrupt Safety`, because long-running ownership and heartbeat semantics still remain future-object gaps.
