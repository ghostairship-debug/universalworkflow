# Pre-M8 Phase B Task Cards

**Phase:** `Pre-M8 Phase B - Runtime Safety And Portability Hardening`  
**Goal:** Enforce adapter runtime-safety assumptions and fix the highest-value portability gaps before service decomposition begins.

## Task Cards

| Task | Size | Goal | Depends On | Primary Files | Verification | Done When |
| --- | --- | --- | --- | --- | --- | --- |
| `PM8-B1` | `complex` | Enforce timeout budgets in subprocess-backed adapters and turn timeout expiry into a stable execution failure result | `PM8-A complete` | `packages/worker_adapters/cli_base.py`, `packages/worker_adapters/shell_adapter.py`, `packages/worker_adapters/opencode_adapter.py`, `packages/worker_adapters/subprocess_support.py`, `tests/test_execution_loop.py` | execution-loop tests | adapters enforce timeout budgets without crashing the workflow |
| `PM8-B2` | `complex` | Replace broad subprocess environment inheritance with an explicit allowlist strategy | `PM8-B1` | `packages/worker_adapters/subprocess_support.py`, `packages/worker_adapters/*`, `tests/test_execution_loop.py` | execution-loop tests | subprocesses inherit only the allowed local environment plus explicit task packet values |
| `PM8-B3` | `medium` | Make compile-generated Python commands interpreter-portable | `PM8-B1` | `packages/core_domain/compile.py`, `tests/test_execution_loop.py` | execution-loop tests | compile-generated commands use `sys.executable` |
| `PM8-B4` | `medium` | Document the local-trusted execution boundary, update debt/reviews, and verify the phase | `PM8-B1`, `PM8-B2`, `PM8-B3` | `README.md`, `docs/architecture/local_execution_trust_boundary.md`, `docs/tech-debt-registry.md`, `docs/reviews/pm8-phase-b-runtime-safety-review.md`, `tests/`, `infra/scripts/offline_validation.py` | targeted + full validation | docs and governance reflect the hardening result and the phase closes cleanly |

## Closeout

- `PM8-B1` completed: timeout budgets are now enforced in subprocess-backed adapters and timeout expiry is normalized into a stable execution failure result.
- `PM8-B2` completed: subprocess-backed adapters now use an explicit allowlist strategy instead of inheriting the full parent environment.
- `PM8-B3` completed: compile-generated Python commands now use `sys.executable`.
- `PM8-B4` completed: the local execution trust boundary is documented, `TD-016` is retired, and targeted/full verification passed.
