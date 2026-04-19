# M10-1B - Lifecycle Projection And Surface Integration

- Task ID: `M10-1B`
- Phase: `M10 Phase 1 - Ownership Topology And Claim Domain Freeze`
- Status: `completed`
- Depends On: `M10-1A`

## Goal

- Populate the new ownership topology in runtime lifecycle flows.
- Expose it through projection, replay, CLI, and API surfaces.

## Out Of Scope

- barrier/join execution
- batch parallel scheduling
- debt retirement wording

## Read Set

- `packages/core_domain/services.py`
- `packages/core_domain/service_lifecycle.py`
- `packages/core_domain/service_projection.py`
- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`
- `tests/test_execution_loop.py`
- `tests/test_cli.py`
- `tests/test_api.py`

## Write Set

- Allowed:
  - service, lifecycle, projection, CLI/API files above
  - focused tests
  - active phase docs

## Invariants

- keep current single-run lifecycle green
- make attempt linkage explicit where the runtime already knows it
- do not broaden into phase-2 concurrency behavior

## Test Plan

- `python -m pytest tests/test_execution_loop.py tests/test_cli.py tests/test_api.py -q -k "claim or lease or ownership or topology or replay"`

## Completion Evidence

- Actual modified files:
  - `packages/core_domain/services.py`
  - `packages/core_domain/service_lifecycle.py`
  - `packages/core_domain/service_projection.py`
  - `apps/operator_cli/main.py`
  - `tests/test_execution_loop.py`
  - `tests/test_cli.py`
  - `tests/test_api.py`
- Validation result:
  - `python -m pytest tests/test_execution_loop.py tests/test_cli.py tests/test_api.py -q -k "claim or lease or ownership or projection"` -> `33 passed, 152 deselected`
