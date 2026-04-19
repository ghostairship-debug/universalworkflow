# Pre-M8 Phase D - Validation, Governance Contract, And Context Hardening

## Goal

Make validation, governance reporting, and LLM-bound payload assembly safe to evolve before the repository enters `M8`.

## Status

- Current state: `Completed`
- Previous phase: `Pre-M8 Phase C - Service Decomposition`
- Next reassessment point: `Pre-M8 Phase E - Debt Refresh, Minimal Automation, And Pre-M8 Freeze Review`

## In Scope

- split `infra/scripts/offline_validation.py` into a validation package with a thin script runner
- introduce structured trace / correlation context across service projections and event/report surfaces
- add lightweight runtime-brief/context-budget diagnostics and a preflight guard path
- write an ADR for token-budget and context-pruning strategy
- add structured canonical governance inputs with Markdown compatibility fallback
- make release-readiness validation provenance explicit

## Out Of Scope

- new feature-bearing `M8` breadth
- full observability platform work
- full context-eviction or memory-pruning engine
- new adapters, new UI breadth, or new Domain Pack families

## Dependencies

- `PM8-A` documentation governance and source-package rules
- `PM8-B` runtime safety / trust-boundary baseline
- `PM8-C` service decomposition
- active debts: `TD-007`, `TD-012`, `TD-013`, `TD-015`, `TD-018`

## Target Outputs

- `infra/validation/` package with modular CLI / smoke / API validation flows
- thin `infra/scripts/offline_validation.py` runner
- structured governance sources for tech-debt and review-policy reporting
- updated governance surfaces with explicit evidence provenance
- runtime/context-budget diagnostics visible in state/detail/report surfaces
- ADR for token-budget/context-pruning strategy
- phase review with targeted tests, full `pytest`, and offline validation evidence

## Phase Gate

This phase closes only when:

1. offline validation no longer keeps flow logic in a single oversized script
2. governance reporting prefers structured canonical sources and survives Markdown wording drift
3. runtime brief assembly exposes visible size-aware diagnostics and a guard path
4. release-readiness explicitly identifies the validation evidence it depends on
5. `pytest -q` and `python -m infra.scripts.offline_validation --skip-offline-probe` both pass

## Risks

- validation refactors can silently break the trusted acceptance path
- governance source changes can desynchronize docs and runtime projections if not mirrored carefully
- context-budget diagnostics can over-tighten and accidentally block current green paths if thresholds are too aggressive

## Implementation Notes

- prefer compatibility layers and additive diagnostics over broad contract rewrites
- keep runtime-budget enforcement diagnostics-first with a high threshold
- keep Markdown docs as operator-readable mirrors, but stop using them as the primary runtime contract source

## Outcome

Completed in this phase:

- `infra/scripts/offline_validation.py` was reduced to a thin runner and the validation flows moved under `infra/validation/`
- service and event/report surfaces now expose a structured `trace_context`
- compile/runtime state now carries `context_budget` diagnostics and the OpenAI-backed runtime gateway enforces a conservative hard guard
- canonical structured governance inputs now live under `docs/governance/` with Markdown compatibility fallback retained for overrides/tests
- release-readiness now reports explicit validation evidence provenance
- ADR-006 records the current diagnostics-first budget/pruning strategy

## Verification

- targeted tests:
  - `pytest tests/test_governance.py tests/test_runtime_boundary.py tests/test_execution_loop.py tests/test_cli.py tests/test_api.py -q`
  - `177 passed`
- focused follow-up after new assertions:
  - `pytest tests/test_governance.py tests/test_runtime_boundary.py tests/test_execution_loop.py -q`
  - `89 passed`
- full suite:
  - `pytest -q`
  - `214 passed`
- validation:
  - `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`
