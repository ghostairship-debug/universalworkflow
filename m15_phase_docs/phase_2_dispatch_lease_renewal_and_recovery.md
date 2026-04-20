# M15 Phase 2 - Dispatch, Lease Renewal, And Recovery

Status: complete

## Goal

Record remote dispatch, heartbeat renewal, and completion callbacks in repository truth while preserving the existing lifecycle model.

## Completed Outputs

- `ExternalWorkerGateway` remote HTTP path
- control-plane callback endpoints for heartbeat and completion
- callback idempotency and lease touch support
- transaction-boundary hardening for SQLite callback re-entry

## Verification

- `tests/test_remote_worker_api.py`
- `tests/test_api.py`
