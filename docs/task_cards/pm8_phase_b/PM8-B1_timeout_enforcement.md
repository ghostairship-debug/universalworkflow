# PM8-B1 - Timeout Enforcement

**Phase:** `Pre-M8 Phase B - Runtime Safety And Portability Hardening`  
**Status:** Completed

## Goal

Make declared timeout budgets real by enforcing them in subprocess-backed adapters and turning expiry into a stable execution failure result.

## Deliverables

- timeout handling in `CliAdapterBase`
- timeout handling in `ShellAdapter`
- timeout handling in `OpenCodeAdapter`
- test coverage for timeout behavior

## Verification

- `tests/test_execution_loop.py`

## Outcome

- Timeout expiry now returns a stable execution result with return code `124` and a diagnostic stderr message instead of surfacing as an unhandled exception.
