# P2-T02 - Simulation Record Surfaces

## Goal

Expose simulation record creation and listing through service, CLI, API, and operator projections.

## Scope

- `run record-simulation`
- `run simulations`
- `POST /runs/{run_id}/simulation-records`
- `GET /runs/{run_id}/simulation-records`

## Done When

- operators can persist a run's current simulation report
- operator surfaces can see the latest persisted simulation record
