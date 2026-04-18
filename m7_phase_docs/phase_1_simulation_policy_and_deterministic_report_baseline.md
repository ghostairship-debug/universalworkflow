# M7 Phase 1 - Simulation Policy And Deterministic Report Baseline

**Phase status:** Completed  
**Phase position:** This phase begins after `M7 Phase 0` freezes `Simulation` as the next second-cycle mainline.

**Entry condition:** The repository has no executable simulation baseline yet, but it does already have strong status-detail, inspection, summary, audit, domain-pack, and memory surfaces that a first simulation slice can reuse.

---

## 1. Reassessment

Current implementation status:

- `Simulation` exists only as roadmap language
- there is no simulation policy catalog
- there is no simulation report surface
- summary/audit do not yet expose any simulation view

Decision:

- add a seed-backed simulation policy registry
- add one deterministic local simulation runner
- keep the first baseline read-mostly and on-demand
- avoid persistence tables in the first slice

---

## 2. In Scope

- define a simulation policy contract and seed file
- define a deterministic simulation report contract
- implement one local simulation runner that evaluates current run consistency/closure readiness
- expose the report through CLI/API and existing summary/audit surfaces

---

## 3. Out Of Scope

- browser or device simulation
- persistent simulation records
- automatic simulation execution during every runtime step
- advanced scenario replay
- large external simulator integrations

---

## 4. Target Baseline

- each preset can resolve to one simulation policy definition
- operators can ask for a structured simulation report for any run
- summary and audit-report include the simulation result
- the report stays deterministic and local-first

---

## 5. Phase Task Breakdown Principle

This phase is split into:

1. Simulation policy contract + deterministic local report engine
2. CLI/API/status surfaces for report access
3. Docs/offline validation/closeout

---

## 6. Outcome

- Added a seed-backed simulation policy registry with three initial policies:
  - `delivery_consistency_simulation`
  - `advisory_failure_simulation`
  - `research_no_simulation`
- Added a deterministic local simulation runner that evaluates:
  - inspection consistency
  - terminal runtime alignment
  - review-state alignment
- Exposed simulation through:
  - `simulation policy list`
  - `run simulation <run_id>`
  - `GET /simulation/policies`
  - `GET /runs/{run_id}/simulation`
- Projected simulation policy/report back into:
  - `status-detail`
  - `inspection`
  - `summary`
  - `audit-report`

Verification:

- `pytest tests/test_contracts.py tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q`
  - `180 passed`
- `pytest -q`
  - `202 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`

Result:

- Phase gate passed.
- `Simulation` is no longer just a roadmap line; it now has one policy-gated deterministic baseline that fits the existing operator surfaces.

---

## 7. Next Reassessment

The next simulation reassessment should decide whether to:

- add persisted simulation records
- add runtime hooks that invoke simulation automatically at selected lifecycle points
- or keep simulation on-demand and move to a heavier external simulation substrate
