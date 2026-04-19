# Pre-M8 Phase A - Trust Recovery And Scope Freeze

**Phase status:** Completed  
**Phase position:** This phase begins immediately after `M7` closes and the repository approves the pre-`M8` hardening gate.

**Entry condition:** The repository ships a usable local-first runtime through `M7`, but pre-`M8` hardening has not yet been opened as an implemented phase series. Current-state truth is spread across living docs, and trust-sensitive repository practices such as portable links, clean source export, and worktree hygiene are not yet formalized.

---

## 1. Reassessment

Current implementation status:

- `M7` is complete and the current baseline remains usable.
- The next approved work is the pre-`M8` hardening gate rather than feature-bearing `M8`.
- The repository already has a current-state guide, but the pre-`M8` phase series had not yet been opened as first-class phase/task artifacts.
- Living docs still lacked explicit portable-link rules, document taxonomy, and clean source-package/export policy.
- The worktree entering this phase was not clean: it already contained living-doc updates and a root-level evaluation report supplied for the hardening reassessment.

Decision:

- open pre-`M8` execution as a real phase/task series
- define a trustworthy hardening boundary and current baseline inventory
- distinguish validated baseline claims from active in-progress worktree state
- introduce explicit portable-link, doc-taxonomy, and source-package hygiene rules for living docs
- keep this phase documentation- and governance-focused; do not expand runtime behavior yet

---

## 2. In Scope

- define the pre-`M8` hardening boundary and current baseline inventory
- define current-status/reporting rules for living docs
- define portable-link rules and document taxonomy for current vs historical vs reference docs
- define clean source-package/export expectations and worktree hygiene gate
- open the `PM8` phase and task-card series in repository-native form

---

## 3. Out Of Scope

- runtime behavior changes
- new adapters, new UI, or new `M8` feature breadth
- automated export tooling
- full rewrite of historical docs to comply with the new portability rules
- retiring pre-`M8` debts before the later hardening phases execute

---

## 4. Target Outputs

- `pm8_phase_docs/phase_a_trust_recovery_and_scope_freeze.md`
- `docs/task_cards/pm8_phase_a_task_cards.md`
- `docs/task_cards/pm8_phase_a/PM8-A*.md`
- `docs/architecture/pre_m8_hardening_boundary.md`
- `docs/documentation_governance.md`
- `docs/source_package_export_policy.md`
- updated `README.md`
- updated `docs/current_development_workflow.md`
- `docs/reviews/pm8-phase-a-trust-recovery-review.md`

---

## 5. Phase Task Breakdown Principle

This phase is split into:

1. hardening boundary and baseline inventory
2. trustworthy current-status/reporting rules
3. portable-link policy and current/review/archive taxonomy
4. clean source-package/export expectations and worktree hygiene gate

---

## 6. Outcome

- Opened the first implemented pre-`M8` phase series with a dedicated phase doc, task-card index, and task-card set.
- Added `docs/architecture/pre_m8_hardening_boundary.md` to make the hardening boundary, baseline evidence sources, and explicit non-goals visible.
- Added `docs/documentation_governance.md` to define:
  - canonical current-state docs
  - current/review/archive/reference taxonomy
  - portable-link rules for living docs
  - current-status wording rules
- Added `docs/source_package_export_policy.md` to define:
  - clean worktree expectations
  - clean source-package/export contents
  - exclusions for DBs, artifacts, caches, and local noise
  - required manifest/evidence for future handoff-ready bundles
- Updated living docs so the repository now states:
  - the current shipped baseline still refers to the last validated closeout
  - `PM8-A` is complete
  - `PM8-B` is the next approved phase

Verification:

- documentation audit only
- no code/runtime behavior changed in this phase
- no automated test suite was required for the completed scope

Result:

- Phase gate passed.
- Pre-`M8` hardening is now opened as a real implementation series rather than only a synthesis document.

---

## 7. Next Reassessment

The next approved phase is:

- `Pre-M8 Phase B - Runtime Safety And Portability Hardening`

That phase should implement the highest-value runtime-safety fixes that were intentionally left out of this trust-recovery step:

- timeout enforcement
- subprocess environment allowlist strategy
- interpreter-portable compile-generated commands
- explicit local-trust execution boundary documentation in operator surfaces
