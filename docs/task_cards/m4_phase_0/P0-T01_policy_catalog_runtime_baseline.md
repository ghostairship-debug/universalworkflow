# P0-T01 - Policy Catalog Runtime Baseline

**Phase:** `M4 Phase 0`
**Status:** Completed

## Goal

Turn `recommended` and `mandatory` from governance-only labels into real contract-level options, while keeping `optional` explicitly non-executable.

## Scope

- extend `ReviewPolicy`
- add seed presets for the new executable policies
- update resolver suggestion hints
- expand the review semantics decision table
- update governance reporting to separate implemented vs reference-only policy candidates

## Acceptance

- `ReviewPolicy` supports `recommended` and `mandatory`
- the seed preset catalog includes at least one preset for each new executable policy
- governance report marks `optional` as the only remaining reference-only candidate
- tests cover the expanded catalog

## Result

- Added `recommended` and `mandatory` to `ReviewPolicy`.
- Added `advisory_delivery` and `guarded_delivery` seed presets plus deterministic resolver coverage.
- Expanded the decision table and governance report, then verified with `pytest tests/test_contracts.py tests/test_repositories.py tests/test_governance.py -q` (`27 passed`).
