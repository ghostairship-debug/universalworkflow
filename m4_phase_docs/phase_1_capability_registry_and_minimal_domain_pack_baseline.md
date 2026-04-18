# M4 Phase 1 - Capability Registry And Minimal Domain Pack Baseline

**Phase status:** Completed  
**Phase position:** This phase starts after `M4 Phase 0` makes richer run-level review policies executable. It shifts `M4` onto the next milestone blocker: proving that the second executor is selected through a real registry and that one minimal `Domain Pack` can be enabled and exercised end-to-end.

**Entry condition:** `M4 Phase 0` is stable, `recommended / mandatory` are executable, `optional` remains reference-only, and the remaining `M4` acceptance gap is no longer review-policy breadth. It is missing `CapabilityRegistry + Domain Pack + M4 smoke` proof.

---

## 1. Reassessment

Current implementation status:

- The runtime already has two adapters: `ShellAdapter` and `NoopAdapter`.
- Routing still lives inside `WorkerRouter` as a hardcoded capability map.
- The repository still has no concrete `Domain Pack` baseline, even though the master plan expects one enabled pack to run a minimal task in `M4 Smoke`.

Legacy references worth absorbing now:

- existing `M1.5` second-executor routing boundaries already shipped in this repository
- plan-level `Domain Pack` scope constraints from `universal_agentic_workflow_os_local_first_plan_v2_1.md`

What is worth reusing:

- keep the current anti-corruption stance: registry-backed routing, not facade expansion
- keep `Domain Pack` as a thin compile-time/runtime projection, not as a new execution kernel
- prove the milestone through smoke and operator surfaces

What must not be reused:

- full plugin/runtime marketplace behavior
- project-kernel or phase-kernel revival
- large new persistence subsystems for domain expansion

---

## 2. In Scope

- extract concrete `CapabilityRegistry` visibility from the router boundary
- add one minimal seed-backed `Domain Pack` definition and registry
- resolve that domain pack for a narrow preset slice
- project selected domain pack and capability route through compile/status/smoke surfaces
- update CLI/API/README/offline validation so `M4 Smoke` has explicit proof points

---

## 3. Out Of Scope

- multi-pack conflict resolution
- dynamic enable/disable persistence
- plugin installation or external pack loading
- full domain-specific execution semantics
- LLM integration
- web frontend or TUI work
- implementing `optional` review policy

---

## 4. Target Baseline

- `CapabilityRegistry`
  - canonical source of adapter capability routes
  - `WorkerRouter` delegates route lookup to the registry
  - CLI/API can list current capability bindings
- minimal `Domain Pack`
  - one seed-backed enabled pack: `software_delivery_pack`
  - applies to `feature_delivery`, `advisory_delivery`, and `guarded_delivery`
  - affects compile output in a visible, testable way:
    - projected in `status-detail` / `inspection` / `summary`
    - injected into compiled artifact content
    - recorded through a lightweight `domain_pack_selected` event
- `M4 Smoke`
  - proves shell path still works under the selected domain pack
  - proves noop path is still selected through `CapabilityRegistry`

---

## 5. Phase Task Breakdown Principle

This phase is expected to split into:

1. Contracts, registries, seeds, and compile-time domain-pack wiring
2. Service / CLI / API projections plus smoke and validation updates
3. Docs, review notes, and phase closeout

---

## 6. Phase Gate

The phase passes only if all of the following are true:

- `CapabilityRegistry` is the concrete source of adapter capability projection
- `domain-pack list` / `GET /domain-packs` work
- `capability list` / `GET /capability-routes` work
- `feature_delivery`-style runs project `software_delivery_pack`
- compiled shell artifacts contain visible domain-pack proof
- smoke and offline validation both prove the registry + domain-pack baseline
- full verification remains green

---

## 7. Outcome

- Extracted concrete `CapabilityRegistry` support from the router boundary and exposed it through CLI/API.
- Added a seed-backed `software_delivery_pack` domain pack plus registry-based preset matching.
- Wired domain-pack and capability resolution into compile, status, inspection, summary, snapshots, timeline, smoke, and offline validation.
- Added `domain_pack_selected` events and visible artifact proof for the shell path.
- Verified with:
  - `pytest tests/test_contracts.py tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q` (`143 passed`)
  - `pytest -q` (`158 passed`)
  - `python -m infra.scripts.offline_validation --skip-offline-probe` (`overall_passed=true`)

---

## 8. Next Reassessment

- `M4` no longer lacks a concrete domain-pack proof baseline.
- The next phase should decide whether to close the last `optional` policy gap, or pivot to the remaining `M4` delivery surface such as minimal operator experience / demo / release-shaped closeout.
