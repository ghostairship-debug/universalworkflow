# PM8-B2 - Subprocess Environment Allowlist

**Phase:** `Pre-M8 Phase B - Runtime Safety And Portability Hardening`  
**Status:** Completed

## Goal

Bound the local subprocess environment so adapters inherit only a minimal trusted local environment plus explicit workflow task values.

## Deliverables

- centralized subprocess env helper
- allowlisted env strategy for shell/CLI-backed adapters
- test coverage proving unrelated parent env values are not passed through

## Verification

- `tests/test_execution_loop.py`

## Outcome

- Subprocess-backed adapters no longer inherit the full parent environment by default.
- Explicit `WORKFLOW_*` packet values still flow through as intended.
