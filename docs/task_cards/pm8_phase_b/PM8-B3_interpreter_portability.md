# PM8-B3 - Interpreter Portability

**Phase:** `Pre-M8 Phase B - Runtime Safety And Portability Hardening`  
**Status:** Completed

## Goal

Make compile-generated Python commands portable across environments by using the currently running interpreter.

## Deliverables

- `compile.py` updated to use `sys.executable`
- regression coverage for compile-generated command shape

## Verification

- `tests/test_execution_loop.py`

## Outcome

- Compile-generated commands now use `sys.executable`, which avoids relying on a plain `"python"` binary being available on `PATH`.
