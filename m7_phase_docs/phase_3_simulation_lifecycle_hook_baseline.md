# M7 Phase 3 - Simulation Lifecycle Hook Baseline

**Phase status:** Completed  
**Phase position:** This phase starts after `M7 Phase 2` proves that simulation reports can already persist as explicit records.

**Entry condition:** The repository can already compute and persist simulation reports on demand, but operators still need to remember to record them manually and there is no lifecycle-shaped simulation lineage yet.

---

## 1. Reassessment

Current simulation status:

- seed-backed simulation policies exist
- deterministic local reports exist
- persisted `SimulationRecord` history exists
- operator/API surfaces can record and list simulation explicitly

Remaining gap:

- selected runtime lifecycle transitions still produce no automatic simulation lineage

Decision:

- add automatic recording only at a few stable control points
- keep the hook policy-gated
- distinguish manual recording from lifecycle recording explicitly
- do not spread hooks across every runtime step

---

## 2. In Scope

- add explicit `recorded_from` lifecycle sources for simulation records
- auto-record simulation at selected control points:
  - `cancelled`
  - `awaiting_review`
  - terminal completion/failure
- expose the hook-generated record source through existing record surfaces

---

## 3. Out Of Scope

- compile-time simulation hooks
- per-step simulation hooks
- browser/device/external simulation
- simulation scheduling queues
- richer simulation-specific failure taxonomy expansion

---

## 4. Target Baseline

- lifecycle transitions can emit simulation history without manual operator action
- the history stays policy-gated
- manual `record-simulation` remains available and appends new history cleanly
- operators can tell whether a simulation record came from a lifecycle hook or an explicit request

---

## 5. Phase Task Breakdown Principle

This phase is split into:

1. Explicit lifecycle source modeling for simulation records
2. Service hook integration at selected control points
3. Docs/validation/closeout

---

## 6. Outcome

- Added explicit `SimulationRecordSource` values:
  - `manual_request`
  - `lifecycle_awaiting_review`
  - `lifecycle_terminal`
  - `lifecycle_cancelled`
- Added automatic simulation recording at selected lifecycle control points:
  - `cancel_run`
  - `resume_run` branches that end in `awaiting_review`
  - terminal auto-review branches
  - terminal human-review branches
- Added `recorded_from` into `simulation_recorded` event payloads.
- Updated CLI `run status` so it also projects `latest_simulation_record`.
- Kept the lifecycle hook policy-gated:
  - hook recording runs only when the resolved simulation policy actually triggers
  - manual recording still persists skipped reports when explicitly requested

Verification:

- `pytest tests/test_contracts.py tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q`
  - `185 passed`
- `pytest -q`
  - `208 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`

Result:

- Phase gate passed.
- `Simulation` now has both explicit operator recording and selected automatic lifecycle lineage, which is sufficient for `M7` closeout without opening heavier simulation scope.

---

## 7. Next Reassessment

The next step should **not** deepen simulation behavior immediately.  
The correct follow-up is a freeze/closure review that decides which simulation ideas move to the next cycle.
