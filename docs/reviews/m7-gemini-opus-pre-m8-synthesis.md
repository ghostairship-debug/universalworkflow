# M7 Gemini/Opus/GPT Pro Synthesis And Pre-M8 Hardening Plan

## Purpose

This document consolidates the latest M7 assessment reports and turns them into one concrete hardening plan that must be completed **before** the repository officially enters `M8`.

Source reports:

- `M7_Evaluation_Gemini.md`
- `M7_Evaluation_Claude.md`
- `M7_Evaluation_GPT pro.md`

Note:
The repository stores the Opus evaluation under `M7_Evaluation_Claude.md`. This plan treats that file as the current Opus report because its contents explicitly identify `Claude Opus 4.6`.

---

## 1. Consolidated Conclusion

All three reports agree on the same top-level reading:

- `M7` is **complete**, and the repository already has a usable local-first version.
- The next priority should **not** be another capability expansion cycle.
- The repository should pass through a **pre-M8 hardening gate** focused on architecture, validation discipline, and governance cleanup.

The shared reasoning is strong:

- the current runtime/control surface is already broad enough for a local usable baseline
- `Domain Pack`, `Memory`, and `Simulation` all now have real baseline implementations
- the largest remaining risks are now **structural**, not missing-user-feature risks

The GPT Pro report adds one important expansion to that conclusion:

- the next gate is not only about maintainability
- it is also about **trustworthiness of delivery artifacts**, **runtime safety**, and **source-of-truth discipline**

So the correct next move is:

1. stop adding major capability breadth
2. harden the core architecture
3. re-enter `M8` only after the hardening gate is closed

---

## 2. Ground Truth Check Against The Current Repository

The reports are directionally correct, but this plan uses the repository as the source of truth for execution details.

Current verified facts:

- `M7` is already formally closed by `docs/reviews/m7-freeze-review.md`
- the current green baseline is still:
  - `pytest -q`
  - `python -m infra.scripts.offline_validation --skip-offline-probe`
- `packages/core_domain/services.py` is still the dominant structural hotspot
  - current measured size: `3426` lines
- `infra/scripts/offline_validation.py` remains oversized
  - current measured size: `1709` lines / `86274` bytes
- `docs/tech-debt-registry.md` has now been renamed and refreshed, but governance still parses Markdown directly instead of consuming a structured canonical source
- `pyproject.toml` still uses tight upper bounds on key runtime dependencies
- subprocess-backed adapters still:
  - inherit broad parent environment state
  - do not enforce declared timeout budgets at launch time
- `packages/core_domain/compile.py` still shells out through `"python"` rather than `sys.executable`
- release-readiness still defaults to `state/offline_validation_report.json`
- canonical repository docs still contain local absolute-path links, which hurts portability outside the current machine/app context
- clean source-package/export flow is still not productized as a first-class repository capability

This means the repository is **functionally ahead** of the trust/governance model that describes and ships it.

---

## 3. What To Adopt From The Reports

### A. Directly adopt

These items should be accepted without change:

- `OrchestratorService` decomposition is the first hard gate before `M8`
- `infra/scripts/offline_validation.py` should be split into smaller validation modules
- subprocess-backed adapters need real timeout enforcement
- subprocess-backed adapters should stop inheriting the full parent environment by default
- governance/report generation should stop depending on free-form Markdown as its primary runtime input
- a clean source-package/export flow should exist before calling the repository ready for the next expansion cycle
- `M8` should **not** reopen large new capability breadth before the hardening gate is closed

### B. Adopt with modification

These items are good, but should land in a narrower form:

- Token/context control
  - adopt as:
    - ADR
    - payload-sizing instrumentation
    - lightweight preflight guard
  - do **not** try to build a full context-eviction engine before `M8`
- dependency-bound relaxation
  - adopt as:
    - targeted compatibility pass
    - selective widening where tests confirm safety
  - do **not** blanket-loosen all upper bounds in one sweep
- observability strengthening
  - adopt as:
    - structured trace/correlation identifiers
    - clearer event linkage across CLI/API/service surfaces
  - do **not** turn pre-M8 into a full Prometheus/Jaeger integration cycle
- documentation/current-state cleanup
  - adopt as:
    - current-status alignment
    - portable link policy for canonical repo docs
    - explicit canonical/current vs historical review split
  - do **not** turn pre-M8 into a full docs-site migration
- release-readiness/report provenance hardening
  - adopt as:
    - make validation-report dependency explicit
    - define canonical status generation rules
  - do **not** turn pre-M8 into a full release platform rebuild
- CI/locking hygiene
  - adopt as:
    - minimal automated gates
    - explicit lockfile strategy decision
  - do **not** turn pre-M8 into an infrastructure program larger than the hardening gate itself

### C. Explicitly defer

These should stay out of the pre-M8 hardening window:

- new `Domain Pack` families
- richer `Simulation` backend families
- Web dashboard work
- distributed concurrency or external worker pools
- new worker adapters
- broader review-policy expansion such as `optional`

---

## 4. Pre-M8 Hardening Goal

The goal is **not** to redesign the product.

The goal is to make the current baseline safer to extend by:

- shrinking the main structural bottleneck
- aligning governance documents with actual repository reality
- making validation and runtime-brief assembly easier to evolve
- restoring trust in what the repository claims versus what it actually ships
- hardening subprocess execution and delivery hygiene before the next expansion cycle
- preserving the existing green baseline throughout the work

This should be treated as:

- a hardening program
- a refactoring gate
- a scope freeze before the next feature-bearing milestone

It should **not** be treated as:

- a new capability milestone
- a hidden `M8` implementation phase
- a reopening of the long-term roadmap breadth

---

## 5. Pre-M8 Phases

### Phase A - Trust Recovery And Scope Freeze

Goal:
Restore trust in the repository snapshot before deeper refactoring begins.

In scope:

- capture the current hardening boundary
- record baseline metrics and trust assumptions
- align README/current-state language with actual repository reality
- define portable-link and canonical-doc rules for living docs
- define clean worktree and clean source-export expectations

Out of scope:

- functional feature expansion
- public API changes
- new adapters or UI work

Suggested task cards:

- `PM8-A1`
  - write the hardening boundary and current baseline inventory
- `PM8-A2`
  - define canonical current-status/reporting rules and remove misleading status claims
- `PM8-A3`
  - define portable-link policy plus current/review/archive doc taxonomy
- `PM8-A4`
  - specify the clean source-package/export flow and worktree hygiene gate

Exit criteria:

- the hardening boundary is explicit
- current-status language is trustworthy
- canonical-doc and source-package rules exist
- no new breadth work is mixed into the branch

### Phase B - Runtime Safety And Portability Hardening

Goal:
Fix the highest-value runtime-safety and portability gaps before structural refactoring expands.

In scope:

- adapter timeout enforcement
- subprocess environment allowlist strategy
- `sys.executable` portability fix for compile-generated commands
- explicit local-trust boundary documentation where the API/CLI execute external tools

Suggested task cards:

- `PM8-B1`
  - enforce timeout budgets in `ShellAdapter` and `CliAdapterBase`
- `PM8-B2`
  - replace broad environment inheritance with an explicit subprocess allowlist strategy
- `PM8-B3`
  - replace hard-coded `"python"` invocation with `sys.executable` in compile-generated commands
- `PM8-B4`
  - document and test the local-trusted execution boundary

Exit criteria:

- declared timeout budgets are actually enforced
- subprocess execution no longer inherits the full parent environment by default
- compile-generated subprocesses are interpreter-portable
- the local-trust boundary is explicit in operator-facing docs

### Phase C - Service Decomposition

Goal:
Reduce `packages/core_domain/services.py` from a God Object into bounded service modules while keeping behavior stable.

Suggested split targets:

- `RunLifecycleService`
- `ReviewPolicyService`
- `InspectionRepairService`
- `ProjectionService`
- `MemoryService`
- `SimulationService`
- `ResourceLeaseService`

Implementation rule:

- prefer move-only extraction first
- keep current method behavior and contracts stable
- allow a thin orchestration facade if needed

Suggested task cards:

- `PM8-C1`
  - extract projection and reporting logic
- `PM8-C2`
  - extract memory and simulation logic
- `PM8-C3`
  - extract lifecycle/review/resource logic
- `PM8-C4`
  - reduce `OrchestratorService` to an orchestration facade or compatibility shim

Exit criteria:

- all tests remain green
- public CLI/API behavior remains stable
- `services.py` is no longer the dominant business-logic container

### Phase D - Validation, Governance Contract, And Context Hardening

Goal:
Make validation, governance reporting, and LLM-bound payload assembly safe to evolve.

In scope:

- split `offline_validation.py`
- add structured correlation/trace propagation
- add a lightweight context-budget preflight
- document the budget/pruning strategy in ADR form
- stop treating free-form Markdown as the primary governance runtime input
- make release-readiness validation provenance explicit

Suggested task cards:

- `PM8-D1`
  - split offline validation into modular flows and a thin runner
- `PM8-D2`
  - add request/run trace linkage across CLI, API, service, and event surfaces
- `PM8-D3`
  - add runtime-brief payload sizing and preflight budget checks
- `PM8-D4`
  - write ADR for token-budget and context-pruning strategy
- `PM8-D5`
  - introduce a structured canonical source or compatibility layer for governance inputs
- `PM8-D6`
  - make release-readiness/report provenance explicit instead of silently depending on ambient state

Exit criteria:

- offline validation is modularized
- runtime brief assembly exposes size-aware diagnostics
- governance reporting no longer depends on brittle prose-first assumptions
- release-readiness clearly declares its evidence source
- a future-proof ADR exists for deeper context control

### Phase E - Debt Refresh, Minimal Automation, And Pre-M8 Freeze Review

Goal:
Close the hardening gate and prove the repository is ready for `M8`.

In scope:

- reconcile the debt registry with the updated hardening scope
- add minimal automated gates for the canonical pre-M8 checks
- decide and document the dependency lock strategy
- produce the final pre-M8 freeze review

Suggested task cards:

- `PM8-E1`
  - refresh debt items and retire completed entries with explicit evidence
- `PM8-E2`
  - add minimal automated gates for tests, docs links, and source-package hygiene
- `PM8-E3`
  - document the lockfile/versioning strategy
- `PM8-E4`
  - produce a pre-M8 freeze review with hard go/no-go criteria

Exit criteria:

- debt registry reflects the current repository reality from `M0` through `M7`
- minimal automated gates exist for the hardening baseline
- dependency/locking policy is explicit
- hardening outcomes are documented
- explicit `M8` entry criteria are approved

---

## 6. Proposed M8 Entry Gates

`M8` should start only when all of the following are true:

- `M7` remains green after refactoring
- current-status docs no longer overclaim relative to the actual repository snapshot
- a clean source-package/export flow exists and can produce a handoff-ready source bundle
- declared subprocess timeout budgets are actually enforced
- subprocess environment inheritance is intentionally bounded
- compile-generated subprocesses are interpreter-portable
- `OrchestratorService` is decomposed enough that new domain work no longer defaults back into one file
- governance reporting no longer relies on brittle prose-first parsing as its primary contract
- offline validation is modular enough to evolve without becoming another God Object
- runtime-brief assembly has a visible size/budget guard path
- release-readiness clearly identifies the validation evidence it depends on
- the repository has a fresh freeze review that declares the hardening gate complete

---

## 7. What This Plan Protects

This plan protects four things at once:

- the current usable baseline
- the roadmap discipline that was recovered in earlier cycles
- the ability to grow `Memory`, `Domain Pack`, `Simulation`, and future runtime integration without compounding structural fragility
- the trustworthiness of what gets shipped, reviewed, and handed to other people as the repository's true current state

If this hardening window is skipped, the repository will likely keep shipping features, but every later cycle will become more expensive and more conflict-prone.

If this hardening window is completed first, `M8` can restart from a cleaner architectural footing.

---

## 8. Final Recommendation

Treat the three reports as materially aligned.

The repository does **not** need another broad capability cycle before `M8`.
It needs one focused pre-M8 hardening program with five ordered phases:

1. trust recovery and scope freeze
2. runtime safety and portability hardening
3. service decomposition
4. validation, governance contract, and context hardening
5. debt refresh, minimal automation, and freeze review

That is the recommended path into `M8`.
