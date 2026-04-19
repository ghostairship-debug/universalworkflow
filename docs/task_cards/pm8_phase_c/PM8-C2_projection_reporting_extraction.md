# PM8-C2 - Projection And Reporting Extraction

## Goal

Extract projection/reporting logic out of `packages/core_domain/services.py` into a dedicated bounded module while keeping public status/summary/audit behavior stable.

## Write Set

- `packages/core_domain/service_projection.py`
- `packages/core_domain/services.py`
- `tests/test_execution_loop.py`
- `tests/test_cli.py`
- `tests/test_api.py`

## Verification

- execution-loop tests
- CLI/API tests for status-detail, inspection, summary, audit-report, dashboard

## Done When

- projection/reporting helpers and public reporting methods no longer live directly in `services.py`
- `OrchestratorService` still exposes the same public methods
- operator-facing outputs remain stable
