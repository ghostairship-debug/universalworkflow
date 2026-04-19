# Pre-M8 Phase C Review - Service Decomposition

## Summary

`PM8-C` completed the first structural hard gate before `M8` by decomposing `OrchestratorService` into bounded modules while keeping the existing runtime surfaces stable.

Implemented modules:

- `packages/core_domain/service_types.py`
- `packages/core_domain/service_projection.py`
- `packages/core_domain/service_memory_simulation.py`
- `packages/core_domain/service_lifecycle.py`

Compatibility rule preserved:

- `packages/core_domain/services.py` remains the public facade used by CLI, API, TUI, and tests.

---

## What Moved

### Projection / reporting

- status-detail
- inspection / reconcile read path
- run summary
- event inspection
- audit report
- dashboard projection
- simulation policy/report projection helpers

### Memory / simulation

- domain-pack preview and catalog validation surfaces
- capability route / runtime gateway visibility surfaces
- memory candidate generation and materialization
- memory retrieval preview
- simulation reporting and simulation record persistence

### Lifecycle / review

- snapshot-for-run compile helper
- compile / recompile / prepare
- cancel
- human review finalize
- resume / execute

---

## Structural Result

- `packages/core_domain/services.py` is reduced to a thinner orchestration/compatibility facade plus shared runtime helpers.
- The main service logic is now distributed across bounded service modules instead of accumulating only in one file.
- The most change-prone user-facing service lanes now live outside the previous God Object.

Measured post-phase structure:

- `packages/core_domain/services.py`: ~1693 lines
- `packages/core_domain/service_projection.py`: ~686 lines
- `packages/core_domain/service_memory_simulation.py`: ~337 lines
- `packages/core_domain/service_lifecycle.py`: ~956 lines

---

## Verification

- `pytest tests/test_execution_loop.py tests/test_cli.py tests/test_api.py tests/test_governance.py -q`
  - `174 passed`

Residual note:

- `services.py` still contains shared helper logic for claims, leases, attempts, inspection, repair, and context loading.
- That remaining helper concentration is acceptable for this phase because `PM8-C` was defined as move-first decomposition, not a semantic rewrite.

---

## Gate Decision

`PM8-C` passes.

The next approved phase is:

- `Pre-M8 Phase D - Validation, Governance Contract, And Context Hardening`
