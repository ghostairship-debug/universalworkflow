# M7 Phase 2 Review - Persistent Simulation Record Baseline

## Scope

`M7 Phase 2` turns the first simulation baseline from an on-demand report into an auditable persisted record surface.

Implemented:

- `SimulationRecord` contract
- `simulation_records` SQLite table and repository
- `simulation_recorded` event lineage
- `run record-simulation` / `run simulations`
- `POST /runs/{id}/simulation-records` / `GET /runs/{id}/simulation-records`
- latest persisted simulation record projection in status/inspection/summary/audit surfaces

Still deferred:

- automatic lifecycle hooks that record simulation without explicit operator/API request
- browser/device simulation
- external simulator integration

## Verification

- `pytest tests/test_contracts.py tests/test_repositories.py tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q`
  - `196 passed`
- `pytest -q`
  - `205 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`

## Result

- Phase gate passed.
- The repository now has persistent simulation history and event lineage, giving later lifecycle-hook phases a stable target object to write into.
