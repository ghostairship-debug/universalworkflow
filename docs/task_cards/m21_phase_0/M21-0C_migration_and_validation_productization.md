# M21-0C Migration And Validation Productization

Status: completed

## Goal

Turn existing incremental SQLite migrations into an explicit operator capability instead of leaving them as startup-only behavior.

## Acceptance Criteria

- `workflowctl db migrate` exists
- `workflowctl db migration-status` exists
- migration state reports applied, pending, and up-to-date status
- regression coverage proves empty-db and already-migrated behavior

## Evidence

- CLI commands added in `apps/operator_cli/main.py`
- status helper added in `packages/core_domain/db.py`
- regression coverage added in `tests/test_cli.py`

## Result

- completed in the first `M21 Phase 0` implementation slice
