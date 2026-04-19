# Pre-M8 Hardening Boundary

## Purpose

This document records the exact boundary of the pre-`M8` hardening gate so the repository can improve trust, safety, and maintainability without accidentally reopening roadmap breadth.

## Baseline Evidence Sources

The current validated baseline should be read from these sources in order:

1. `README.md`
2. `docs/reviews/m7-freeze-review.md`
3. `docs/reviews/m7-gemini-opus-pre-m8-synthesis.md`
4. `docs/current_development_workflow.md`
5. `docs/tech-debt-registry.md`

These sources together define:

- what shipped through `M7`
- what remains deferred
- what the current approved next work is
- what debts block safe entry into `M8`

## Current Baseline Inventory

At the start of pre-`M8` hardening, the repository already ships:

- local-first CLI/API runtime baseline
- `shell`, `opencode`, and `noop` execution lanes
- one platformized domain-pack baseline
- persisted memory baseline with retrieval preview and compile-time injection
- deterministic local simulation baseline with persisted records and selected lifecycle hooks
- release-readiness, audit, inspection, and review-policy governance surfaces

The repository does **not** yet claim:

- `M8` feature expansion
- distributed worker ownership
- full optional review-policy runtime breadth
- fully portable repository docs
- fully productized source-package/export workflow

## Trust Assumptions

- Current shipped-status claims refer to the most recent validated closeout, not to every transient local worktree state.
- Active development can temporarily produce a dirty worktree.
- A future freeze or handoff may only claim a clean package when the source-package/export policy is satisfied.

## In Scope For Pre-M8 Hardening

- current-status trust recovery
- portable living-doc rules
- clean source-package/export policy
- runtime safety and portability hardening
- service decomposition
- validation and governance contract hardening
- debt refresh and pre-`M8` freeze review

## Out Of Scope For Pre-M8 Hardening

- new feature-bearing `M8` work
- new domain-pack family expansion
- broader simulation backend work
- web dashboard expansion
- distributed concurrency semantics
- optional review-policy implementation

## Phase-A-Specific Deliverable

`Pre-M8 Phase A` exists to convert this boundary from implicit roadmap language into explicit repository guidance. Later pre-`M8` phases should treat this document as the architectural edge of the hardening window unless a new reassessment explicitly updates it.
