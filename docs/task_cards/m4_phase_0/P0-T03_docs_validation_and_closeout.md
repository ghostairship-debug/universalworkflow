# P0-T03 - Docs Validation And Closeout

**Phase:** `M4 Phase 0`
**Status:** Completed

## Goal

Close the phase cleanly once runtime semantics are implemented.

## Scope

- update README examples and behavior notes
- extend offline validation to exercise the new policies
- update `TD-006` notes and legacy-reference status
- write the phase review and mark the phase completed

## Acceptance

- operator docs describe `recommended` and `mandatory`
- offline validation verifies the new runtime semantics
- phase review records the verification results

## Result

- Updated README, offline validation, `TD-006`, and legacy-reference status notes.
- Offline validation now exercises both `recommended` fail-escalation and `mandatory` human-signoff flows.
- Final verification passed:
  - `pytest -q` (`153 passed`)
  - `python -m infra.scripts.offline_validation --skip-offline-probe` (`overall_passed=true`)
