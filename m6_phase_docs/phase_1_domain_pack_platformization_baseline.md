# M6 Phase 1 - Domain Pack Platformization Baseline

**Phase status:** Completed  
**Phase position:** This phase starts after `M6 Phase 0` freezes `Domain Pack platformization baseline` as the only approved next-cycle mainline. It turns the current minimal `software_delivery_pack` proof into a reusable platform boundary without reopening full plugin lifecycle or broad kernel work.

**Entry condition:** `M5` is normalized as complete through `Phase 2`, `M6 Phase 0` is written, and the repository still only has a thin proof-style domain-pack implementation rather than a reusable domain-pack platform surface.

---

## 1. Reassessment

Current implementation status:

- the repository already has one enabled minimal pack: `software_delivery_pack`
- current pack matching is still thin and definition-centric
- compile/status/summary surfaces already project the selected pack, but they mostly recompute from the current registry instead of carrying a stable pack-resolution snapshot
- the current definition mixes match rules, capability hints, and compile/runtime behavior into one flat object

What must be improved now:

- the domain-pack contract surface must become reusable instead of demo-shaped
- compile/runtime surfaces must project a stable resolved pack snapshot rather than depending on later registry recomputation
- the pack definition must be split conceptually into:
  - match rules
  - capability exposure
  - compile/runtime projection

What should be preserved:

- one narrow pack family only
- seed-backed local loading
- no new persistence layer for pack lifecycle
- no plugin marketplace or external pack installation flow

Decision:

- keep a single seed-backed pack family
- formalize `DomainPackResolution` as the platform boundary
- store pack resolution at compile time and reuse it across operator surfaces

---

## 2. In Scope

- introduce reusable domain-pack contracts for:
  - matching
  - capability exposure
  - compile projection
  - runtime projection
- convert the current seed and registry to resolve a stable `DomainPackResolution`
- persist that resolution through compile/runtime context so status/summary/inspection remain stable
- update CLI/API/governance/tests/docs to reflect the new platformized domain-pack baseline

---

## 3. Out Of Scope

- multi-pack composition or conflict resolution
- dynamic enable/disable persistence
- external pack loading or plugin lifecycle
- new domain-pack families
- `Memory` or `Simulation`
- TUI mutation workflows
- CLI-first adapter expansion

---

## 4. Target Baseline

- `DomainPackDefinition`
  - no longer acts like a flat demo blob
  - clearly separates match rules, capability exposure, compile projection, and runtime projection
- `DomainPackResolution`
  - is created at compile time
  - is stored with the compiled runtime context
  - is reused by status/detail/summary/inspection instead of late recomputation when possible
- operator surfaces
  - expose richer pack metadata without requiring a second pack family
- governance/readiness
  - can describe the current platformized pack baseline rather than only saying “one pack exists”

---

## 5. Phase Task Breakdown Principle

This phase is expected to split into:

1. Contracts, seed schema, and registry resolution
2. Stable compile/runtime projection and operator-surface reuse
3. Docs, governance, validation, and closeout

---

## 6. Phase Gate

The phase passes only if all of the following are true:

- domain-pack contracts are split into reusable platform-shaped sections
- one stable `DomainPackResolution` is produced at compile time
- status/detail/summary/inspection can reuse the stored resolution
- CLI/API/governance/tests reflect the richer baseline
- full verification remains green

---

## 7. Expected Outputs

This phase should produce:

- reusable domain-pack contracts
- one resolution-aware registry path
- one compile/runtime projection baseline that no longer depends on late recomputation alone
- one updated review/closeout note for the phase

Expected next reassessment after this phase:

- decide whether the next `M6` slice should deepen the platform with bounded pack-lifecycle ergonomics or move to the next second-cycle bridge such as `Memory` preparation hooks

---

## 8. Outcome

- Introduced reusable domain-pack platform contracts:
  - `match`
  - `capability_exposure`
  - `compile_projection`
  - `runtime_projection`
  - `DomainPackResolution`
- Upgraded the seed-backed `software_delivery_pack` into the new platform shape while keeping backward compatibility for flat legacy input.
- Stored domain-pack resolution at compile time and reused it from task-packet/runtime-state context in status, summary, inspection, snapshots, and artifact generation.
- Added richer domain-pack governance visibility through:
  - `governance domain-pack`
  - `GET /governance/domain-packs`
- Updated README, CLI/API surfaces, and validation expectations to describe the platformized baseline rather than only “one pack exists”.

Verification:

- `pytest tests/test_contracts.py tests/test_execution_loop.py tests/test_api.py tests/test_cli.py tests/test_governance.py tests/test_release_closeout.py -q`
  - `168 passed`
- `pytest -q`
  - `183 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`

Result:

- Phase gate passed.
- The repository now has a reusable, stable domain-pack platform baseline rather than only a thin proof.

---

## 9. Next Reassessment

- The next `M6` slice should stay on the domain-pack mainline, but it no longer needs to reshape the core contracts again.
- The most valuable next step is to add pack-resolution preview and catalog-validation surfaces so operators and future pack authors can inspect the selected pack before compile/resume.
