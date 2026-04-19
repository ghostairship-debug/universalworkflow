# PM8-C3 - Memory And Simulation Extraction

## Goal

Move memory and simulation service logic into a dedicated bounded module without changing existing operator/runtime behavior.

## Write Set

- `packages/core_domain/service_memory_simulation.py`
- `packages/core_domain/services.py`
- `tests/test_execution_loop.py`
- `tests/test_cli.py`
- `tests/test_api.py`

## Verification

- execution-loop tests
- CLI/API tests for memory candidates, retrieval preview, simulation report/records, dashboard

## Done When

- memory and simulation service logic no longer lives directly in `services.py`
- persistence/reporting behavior stays stable
- current CLI/API routes continue to work without contract changes
