# M7 Phase 0 - Simulation Rebaseline And Scope Freeze

**Phase status:** Completed  
**Phase position:** This phase starts after `M6 Phase 6` closes the first explicit `Domain Pack -> Memory -> compile` bridge. It re-centers the second-cycle roadmap before implementation moves into `Simulation`.

**Entry condition:** `Domain Pack` and `Memory` now both have platform/baseline slices, while `Simulation` is still only a planned line in the master plan.

---

## 1. Reassessment

Current second-cycle status:

- `Domain Pack` is platformized and previewable
- `Memory` has namespaces, persistent items, retrieval preview, and one explicit compile bridge
- `Simulation` still has no executable baseline in the repository

Planning implication:

- continuing to deepen `Memory` first would over-concentrate on one line
- the original roadmap explicitly treats `Simulation` as the third second-cycle pillar
- the next approved mainline should therefore switch from `Memory` deepening to `Simulation` baseline work

Decision:

- freeze `Simulation` as the next approved mainline
- keep the first simulation slice narrow and deterministic
- do not reopen browser/mobile simulation or heavy external runners in the first phase

---

## 2. In Scope

- define the first approved `Simulation` problem slice
- keep the slice policy-gated instead of globally enabled
- require the slice to reuse existing status / inspection / audit surfaces rather than invent a parallel operator plane

---

## 3. Out Of Scope

- browser automation or UI simulation
- mobile simulation
- persistent simulation tables
- distributed simulation workers
- replay engines
- auto-triggering simulation inside every runtime path

---

## 4. Approved First Slice

The first executable `Simulation` slice is:

- seed-backed simulation policy definitions
- deterministic local simulation evaluation
- one structured simulation report per run
- CLI/API/operator visibility through existing summary and audit surfaces

This means the first phase should answer:

- whether a run is covered by simulation policy
- whether the policy actually triggers for the current run state
- what the local deterministic simulation concludes
- how that conclusion feeds operator/audit views

---

## 5. Phase Task Breakdown Principle

The first implementation phase should split into:

1. Simulation policy contract and deterministic runner
2. CLI/API/operator surfaces for simulation report access
3. Docs/validation/closeout

---

## 6. Output

This rebaseline freezes the next approved implementation phase as:

- **`M7 Phase 1 - Simulation Policy And Deterministic Report Baseline`**

Its responsibility is:

- add a seed-backed simulation policy catalog
- add one deterministic local simulation runner
- expose a structured report without adding persistent simulation storage

---

## 7. Result

- `Simulation` is now the approved next mainline.
- The first slice is explicitly bounded to policy, report generation, and operator visibility.
- `Memory` deepening is not the current priority unless a later reassessment reopens it.
