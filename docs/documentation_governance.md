# Documentation Governance

## Purpose

This document defines how repository documents should be interpreted, linked, and updated so current-state claims stay trustworthy.

## 1. Document Taxonomy

Use the following categories.

### A. Living current-state docs

These documents define the current approved repository truth.

- `README.md`
- `docs/current_development_workflow.md`
- latest active synthesis/reassessment doc
- `docs/tech-debt-registry.md`

Rules:

- keep them aligned with actual repository behavior and approved next-step decisions
- update them when user-visible behavior, governance meaning, or approved next work changes
- do not let them silently overclaim relative to the last validated baseline

### B. Active phase execution docs

These documents govern work currently being executed.

- `pm8_phase_docs/*`
- active phase task-card index
- active complex task cards

Rules:

- they may be updated during the phase
- they should reflect actual implementation reality, not just original intent
- they should state the next reassessment point explicitly

### C. Historical review records

These documents preserve milestone and phase history.

- freeze reviews
- closed phase reviews
- closed milestone task-card indexes

Rules:

- keep them historically accurate
- do not rewrite them as if they were the latest state docs
- if reinterpretation is needed, write a new living doc instead of mutating history

### D. Reference / legacy docs

These documents are consulted selectively but do not define current roadmap truth.

- `docs/legacy_ai_agent_reference_plan.md`
- `docs/legacy_project_reference_uplift_plan.md`
- `docs/m1_legacy_reference_uplift_plan.md`

Rules:

- use them for semantics, tests, invariants, and anti-patterns
- do not import their architecture or naming wholesale

## 2. Portable-Link Policy

For repository documents:

- prefer portable repo-local Markdown links for newly written or newly updated living docs
- avoid machine-local absolute paths in repository docs unless there is no practical portable alternative
- do not bulk-rewrite historical docs only for link-style normalization

This means:

- new living docs should prefer links such as `docs/current_development_workflow.md`
- assistant responses may still use absolute local paths for the desktop app UX
- historical docs may keep older link forms until they are substantively revised

## 3. Current-Status Language Rules

When a living doc says the repository is green, complete, or current, it must make clear which of these it means:

- last validated baseline
- currently approved next work
- active worktree state

Required rule of thumb:

- use phrases such as `validated baseline`, `latest completed milestone`, and `next approved phase`
- do not imply that an in-progress dirty worktree is identical to the last validated freeze snapshot

## 4. Canonical Current-State Source Map

When documents disagree, interpret current truth in this order:

1. latest active synthesis/reassessment doc
2. `docs/current_development_workflow.md`
3. `README.md`
4. latest freeze review
5. `docs/tech-debt-registry.md`
6. historical records

## 5. Update Rule

When touching a living doc in future phases, also check whether one of these must be updated:

- `README.md`
- `docs/current_development_workflow.md`
- active phase doc
- active task-card index
- relevant review document
- `docs/tech-debt-registry.md`

If a change introduces a new trust or portability rule, update this document too.
