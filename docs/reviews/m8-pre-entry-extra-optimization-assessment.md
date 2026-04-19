# M8 Pre-Entry Extra Optimization Assessment

**Assessment date:** 2026-04-19  
**Repository baseline:** `M7 complete` + `Pre-M8 complete`  
**External inputs reviewed:**

- `M8_Readiness_Deep_Evaluation.md`
- `Pre_M8_Evaluation_Report.md`

---

## 1. Question

Before opening `M8`, should the repository run **another dedicated optimization/hardening cycle**, or is the current state already sufficient to proceed into `M8 Phase 0`?

---

## 2. Short Answer

**No additional full pre-M8 optimization round is necessary.**

The repository should **not** open a new broad hardening cycle before `M8`.
Instead, it should perform a **small entry-hygiene package** and then proceed directly into:

- `M8 Phase 0 - Feature Rebaseline And Scope Freeze`

---

## 3. Why A Full Extra Round Is Not Necessary

Both newly added root-level evaluations agree on the key point:

- `Pre-M8` achieved its intended gate
- the repository is in **GO** state for entering `M8`
- the next approved step should still be a scope-freeze entry phase, not unconstrained feature work

This matches the canonical repository record:

- [pre-m8-freeze-review.md](./pre-m8-freeze-review.md)
- [current_development_workflow.md](../current_development_workflow.md)

The current baseline already shows:

- `pytest -q`
  - `216 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`
- `python -m infra.scripts.pre_m8_gates`
  - `overall_passed=true`

That means the repository has already crossed the threshold from:

- "needs more hardening before next-cycle planning"

to:

- "ready to rebaseline the next cycle"

Opening another full hardening round before `M8` would blur the existing milestone boundary and weaken the current planning discipline.

---

## 4. What The Two New Evaluations Add

## 4.1 Confirmed strengths

The two evaluations are useful because they reinforce several points already visible in the repository:

- `OrchestratorService` decomposition materially improved maintainability
- subprocess execution hardening was meaningful and correctly scoped
- validation modularization improved structure substantially
- documentation/governance work is now part of the real operating model
- `Pre-M8` solved the most important structural blockers without destabilizing the test baseline

These points are consistent with the current repository evidence.

## 4.2 Useful residual concerns

The two evaluations also point to several residual issues that are real, but mostly **not M8-entry blockers**:

1. `services.py` still remains large  
2. direct unit tests for some newly added support modules are still thinner than ideal  
3. the worktree is still dirty / not checkpointed  
4. some next-cycle debt decisions still need explicit scoping in `M8 Phase 0`

Those are valid concerns.
But they do **not** justify reopening a broad pre-M8 hardening phase.

---

## 5. What Still Deserves Action Before M8

The right response is a **small entry-hygiene package**, not a new milestone.

## 5.1 Required before active M8 feature work

### A. Create a clean checkpoint in Git

This is the only item that should be treated as effectively mandatory before deeper `M8` development.

Reason:

- the current worktree still contains many modified/untracked files
- `Pre-M8` is already logically frozen
- `M8` should not begin on top of an uncheckpointed baseline

Recommendation:

- create a dedicated checkpoint commit for the `Pre-M8` frozen baseline
- then open `M8` work on top of that checkpoint

### B. Keep `M8 Phase 0` as a strict scope-freeze phase

Do not convert root-level evaluation suggestions directly into unapproved milestone work.

Instead:

- re-read the evaluations
- re-read the freeze review
- decide explicitly which residual items belong in `M8`

This is already the canonical rule and should remain so.

## 5.2 Recommended but not blocking

### C. Add a few direct support-module tests early in M8

Recommended targets:

- subprocess timeout/env allowlist helpers
- context-budget helper behavior
- selected service-boundary isolation tests

Why recommended:

- current behavior is already covered indirectly by broader tests
- direct tests would make future refactors safer

Why not blocking:

- the full repository test suite is already green
- these are confidence improvements, not baseline integrity failures

### D. Continue service decomposition only as scoped M8 work

The residual size of `services.py` is a legitimate technical debt concern.
However:

- the largest structural risk has already been reduced materially
- the remaining work is better handled as explicit `M8` scoped follow-up
- it should not reopen `Pre-M8`

---

## 6. What Should Not Happen

Do **not** do any of the following before `M8 Phase 0`:

- open a new generic hardening milestone
- treat every root-level recommendation as an immediate blocker
- add more broad architecture work without a new phase decision
- continue refactoring purely because residual debt still exists

Residual debt is expected.
The important question is whether it blocks re-entry into milestone planning.
At this point, it does not.

---

## 7. Final Recommendation

The correct path is:

1. checkpoint the current `Pre-M8` state in Git  
2. treat the new root-level evaluations as **inputs** to `M8 Phase 0`, not as a reason to reopen `Pre-M8`  
3. optionally schedule direct support-module tests and further service extraction into early `M8`, if approved during scope freeze  
4. proceed into `M8 Phase 0 - Feature Rebaseline And Scope Freeze`

---

## 8. Bottom Line

The new evaluations do **not** justify another full optimization round before `M8`.

They do justify:

- one clean checkpoint
- one disciplined `M8 Phase 0`
- and possibly a small number of early-`M8` cleanup tasks

That is the highest-signal response to the current repository state.
