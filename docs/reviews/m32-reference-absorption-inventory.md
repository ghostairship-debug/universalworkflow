# M32 Reference Absorption Inventory

Captured: 2026-04-22  
Reference workspace: `D:\Universal Agentic workflow`  
Integration workspace: `D:\uawo-m32-integration`

## Purpose

The primary workspace currently carries uncommitted reference deltas that are relevant to the accepted `M31` baseline and the `M32` opening. This inventory classifies those deltas so `integration` can absorb them intentionally instead of treating the dirty primary workspace as execution truth.

## Direct-Absorb Candidates

These deltas align with accepted `M31` truth or active `M32-0` governance and should be absorbed into the bounded worktree with minimal reshaping:

- `README.md`
  - updates milestone truth from `M30` to accepted `M31 Phase 0`
  - corrects scheduler wording and orchestration baseline wording
- `docs/current_development_workflow.md`
  - promotes accepted `M31` to the controlling baseline and keeps bug-first explicit
- `docs/tech-debt-registry.md`
  - adds `TD-STRUCT-001..006`
  - corrects `TD-021` wording to single-store quorum-style semantics
- `docs/governance/tech_debt_registry.json`
  - structured mirror of the same `TD-STRUCT-*` carry-forward set
- `packages/core_domain/config.py`
  - `authority_mode` support required by the accepted scheduler-honesty line
- `packages/core_domain/capability_plane.py`
  - optional MCP boundary and degradation path
- `packages/contracts/models.py`
  - additive capability invocation/receipt and graph edge/barrier/retry contracts
- `packages/contracts/__init__.py`
  - corresponding export surface updates
- `infra/seeds/presets.json`
  - `guarded_project_delivery` seed coverage
- `packages/core_domain/resolver.py`
  - preset resolution support for `guarded_project_delivery`
- `packages/core_domain/service_lifecycle.py`
- `packages/core_domain/service_memory_simulation.py`
- `packages/core_domain/service_projection.py`
- `packages/core_domain/services.py`
  - shared orchestration substrate, capability projection flow, and M31 carry-forward wiring
- `packages/core_domain/scheduler_authority.py`
- `packages/core_domain/governance.py`
- `pyproject.toml`
  - dev coverage floor and optional dependency boundary support
- targeted tests under `tests/`
  - additive contract, CLI/API, execution-loop, governance, and scheduler-honesty coverage

## Absorb-With-Reshaping Candidates

These deltas are directionally correct but should be rewritten or merged into active `M32` materials rather than copied wholesale:

- `NEXT_DEVELOPMENT_PLAN.md`
  - the reference workspace version should replace the stale root plan in `integration`, but the active phase doc/task-card pack remains higher priority truth
- `docs/reviews/m20-freeze-review.md`
  - only absorb wording updates if they are required for semantic honesty; do not re-open historical scope unnecessarily
- `apps/scheduler_authority_api/main.py`
  - absorb only the semantic-honesty/API projection delta that matches the scheduler wording correction

## Do-Not-Absorb-As-Active-Truth

These items remain archival or reference-only and should not become active execution truth for `M32 Phase 0`:

- old root-level evaluation bundles that are superseded by active `M32` materials
- future-platform vision material that has not yet been promoted through `TD-STRUCT-006`
- any dirty-workspace implementation delta that would introduce a new `*_delivery` service special path instead of the cluster-template route

## Operational Rule

During `M32 Phase 0`:

- the dirty primary workspace remains reference-only
- every absorbed delta must land through the `integration` worktree
- if an absorbed delta exposes a regression, bug-first applies immediately
