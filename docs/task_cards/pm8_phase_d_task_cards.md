# PM8 Phase D Task Cards

## Phase Intent

`PM8-D` turns three structural hotspots into safer extension points:

- offline validation becomes a modular package instead of one large script
- governance reports stop relying on Markdown prose as their primary runtime contract
- live runtime brief assembly exposes explicit correlation and context-budget diagnostics

## Task Order

| Task | Status | Complexity | Objective | Depends On | Primary Write Set | Verification |
| --- | --- | --- | --- | --- | --- | --- |
| `PM8-D1` | `completed` | `complex` | Split offline validation into modular flows and a thin runner | `PM8-C complete` | `infra/validation/`, `infra/scripts/offline_validation.py`, `tests/` | targeted validation tests + `offline_validation` |
| `PM8-D2` | `completed` | `medium` | Add trace/correlation context across service projections and event/report surfaces | `PM8-D1` | `packages/contracts/`, `packages/core_domain/`, `tests/` | execution + CLI/API tests |
| `PM8-D3` | `completed` | `medium` | Add runtime-brief/context-budget diagnostics and a preflight guard path | `PM8-D2` | `packages/core_domain/`, `packages/runtime_langgraph/gateway.py`, `tests/` | runtime boundary + execution tests |
| `PM8-D4` | `completed` | `small` | Write the token-budget/context-pruning ADR and update operator docs | `PM8-D3` | `docs/adrs/`, `README.md`, `docs/current_development_workflow.md` | docs review |
| `PM8-D5` | `completed` | `complex` | Introduce structured canonical governance sources with Markdown compatibility fallback | `PM8-D1` | `docs/governance/`, `packages/core_domain/governance.py`, `tests/test_governance.py` | governance tests |
| `PM8-D6` | `completed` | `medium` | Make release-readiness/report provenance explicit and close the phase | `PM8-D2`, `PM8-D3`, `PM8-D5` | `packages/core_domain/governance.py`, `README.md`, `docs/reviews/` | targeted tests + full `pytest` + offline validation |

## Closeout Requirements

- all six tasks updated to completed with implemented write sets
- `README.md` and `docs/current_development_workflow.md` reflect `PM8-D` completion and point to `PM8-E`
- new governance sources and ADR are documented in living docs
- `docs/reviews/pm8-phase-d-validation-governance-context-review.md` captures test evidence and remaining gaps

## Closeout

- `PM8-D1` completed: validation runner logic moved into `infra/validation/` and `infra/scripts/offline_validation.py` is now only an entry wrapper.
- `PM8-D2` completed: event payloads, status/detail, inspection, summary, and audit/report surfaces now expose a stable `trace_context`.
- `PM8-D3` completed: compile/runtime state and the OpenAI-backed gateway now expose `context_budget` diagnostics with a conservative hard guard.
- `PM8-D4` completed: `docs/adrs/ADR-006.md` records the diagnostics-first budget/pruning strategy.
- `PM8-D5` completed: governance now prefers `docs/governance/*.json` and keeps Markdown compatibility for overrides/tests.
- `PM8-D6` completed: release-readiness now declares explicit validation evidence provenance; targeted tests, full `pytest`, and offline validation all passed.
