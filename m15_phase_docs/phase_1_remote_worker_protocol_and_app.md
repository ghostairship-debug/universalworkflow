# M15 Phase 1 - Remote Worker Protocol And App

Status: complete

## Goal

Add the real remote worker app and freeze the HTTP protocol between control plane and worker.

## Completed Outputs

- `apps/remote_worker_api/main.py`
- `POST /dispatches`
- shared-secret auth support
- remote execution target metadata and renewal payloads

## Verification

- `tests/test_remote_worker_api.py`
