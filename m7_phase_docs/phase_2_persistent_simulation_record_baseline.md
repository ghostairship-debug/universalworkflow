# M7 Phase 2 - Persistent Simulation Record Baseline

**Phase status:** Completed  
**Phase position:** This phase starts after `M7 Phase 1` proves that simulation policy resolution and deterministic local reports are already useful through existing operator surfaces.

**Entry condition:** Simulation reports can be generated on demand, but there is still no persisted simulation history, no simulation audit lineage, and no stable record surface for later lifecycle hooks.

---

## 1. Reassessment

Current simulation status:

- policies exist
- deterministic reports exist
- CLI/API/operator summary surfaces exist
- all reports are still recomputed on demand

Decision:

- persist simulation records before adding automatic lifecycle hooks
- keep persistence lightweight and local-first
- record reports on explicit operator/API request, not on every lifecycle transition

Why this is the safer next step:

- it creates an auditable history before hook proliferation
- it avoids making runtime behavior more implicit too early
- it gives later hook phases a stable target object to write into

---

## 2. In Scope

- add a persisted `SimulationRecord` contract
- add one SQLite table and repository for simulation records
- add explicit `record simulation` surfaces through CLI/API
- expose latest persisted simulation record through operator surfaces

---

## 3. Out Of Scope

- automatic compile/resume/review simulation hooks
- browser/device simulation
- replay engines
- simulation scheduling queues
- external simulation services

---

## 4. Target Baseline

- operators can explicitly persist the current simulation report for a run
- persisted simulation records are queryable per run
- timeline/audit surfaces can point to the latest persisted simulation record
- summary still keeps the live deterministic simulation view

---

## 5. Phase Task Breakdown Principle

This phase is split into:

1. `SimulationRecord` contract + persistence + event lineage
2. CLI/API/operator surfaces for recording and listing simulation records
3. Docs/validation/closeout

---

## 6. Outcome

- Added a persisted `SimulationRecord` contract.
- Added SQLite persistence through `009_m7_simulation_records.sql`.
- Added explicit recording/listing surfaces:
  - `run record-simulation <run_id>`
  - `run simulations <run_id>`
  - `POST /runs/{run_id}/simulation-records`
  - `GET /runs/{run_id}/simulation-records`
- Added `simulation_recorded` event lineage.
- Projected the latest persisted simulation record into:
  - `status-detail`
  - `inspection`
  - `summary`
  - `audit-report`

Verification:

- `pytest tests/test_contracts.py tests/test_repositories.py tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q`
  - `196 passed`
- `pytest -q`
  - `205 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`

Result:

- Phase gate passed.
- `Simulation` now has both a live report path and a persisted record path, which is the right base for later lifecycle-hook work.

---

## 7. Next Reassessment

The next simulation reassessment should decide whether to:

- add lifecycle hooks that automatically record simulation at selected control points
- add simulation-specific failure taxonomy extensions
- or begin a heavier external simulation substrate
