# M18 Freeze Review

## Result

`M18` is complete.

## Completed Scope

- introduced a centralized scheduler-authority first slice for multi-control-plane identity, proposal, lease decision, release, and peer-heartbeat records
- added `/scheduler/proposals`, `/scheduler/heartbeats`, `/scheduler/releases/{lease_id}`, and `/scheduler/leases/{lease_id}` authority APIs
- projected scheduler arbitration provenance into runtime-state-backed status, inspection, replay, and operator views
- added conflict and stale-authority diagnostics without falsely claiming full distributed consensus
- kept repository truth inside the control plane while narrowing `TD-021` to the remaining multi-authority consensus work

## Validation Evidence

- `tests/test_contracts.py`
- `tests/test_repositories.py`
- `tests/test_execution_loop.py`
- `tests/test_cli.py`
- `tests/test_api.py`
- `tests/test_governance.py`
- `python -m pytest -q`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
- `python -m infra.scripts.check_doc_links`

## Notes

- `M18` ships a real first slice, not a marketing rename of deferred work.
- The repository can now explain control-plane identity, lease proposals, lease epochs, arbitration conflicts, and authority-backed regrant behavior.
- True distributed consensus, multi-authority failover, and final cross-control-plane lease ownership remain open in `TD-021`.

## Next Approved Work

- `M19 Phase 0 - Post-M18 Rebaseline And Scope Freeze`
