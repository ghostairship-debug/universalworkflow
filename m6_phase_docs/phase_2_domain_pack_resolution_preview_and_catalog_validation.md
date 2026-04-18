# M6 Phase 2 - Domain Pack Resolution Preview And Catalog Validation

**Phase status:** Completed  
**Phase position:** This phase starts after `M6 Phase 1` establishes a reusable domain-pack platform boundary. It does not reshape the contracts again; it makes the platform inspectable before compile/resume and validates the current catalog against preset and adapter reality.

**Entry condition:** `M6 Phase 1` is complete, `DomainPackResolution` exists, and the main remaining usability gap is that pack selection and pack validity are still mostly inferred indirectly through compile/status surfaces.

---

## 1. Reassessment

Current implementation status:

- domain-pack contracts are now platform-shaped
- compile/runtime surfaces can reuse stored pack resolution
- governance already exposes a higher-level pack-platform view

Current gap:

- operators and future pack authors still cannot ask:
  - which pack would resolve for this preset/task-kind before compile?
  - is the current catalog valid against known presets and adapter routes?
- current validation is mostly implicit through tests, not first-class through CLI/API surfaces

Decision:

- add explicit resolution-preview surfaces
- add explicit catalog-validation surfaces
- keep the current single-pack family and avoid introducing authoring persistence or plugin lifecycle

---

## 2. In Scope

- add service support to preview resolved pack + adapter selection for a preset/task-kind pair
- add catalog validation against:
  - known presets
  - allowed preset/task-kind combinations
  - adapter-route availability for preferred adapters
  - enabled-pack overlap conflicts
- expose these through CLI/API and validation/docs

---

## 3. Out Of Scope

- pack editing or persistence
- pack installation or external loading
- new pack families
- memory or simulation hooks
- TUI mutation workflows

---

## 4. Target Baseline

- `domain-pack resolve`
  - previews the selected pack and capability route before compile
- `domain-pack validate`
  - returns a structured catalog-validation report
- API exposes equivalent read-only surfaces
- offline validation and docs include the new preview/validation path

---

## 5. Phase Task Breakdown Principle

This phase is expected to split into:

1. Resolution-preview service and registry wiring
2. Catalog-validation rules and structured report
3. CLI/API/docs/validation closeout

---

## 6. Outcome

- Added explicit domain-pack resolution preview before compile through:
  - `domain-pack resolve`
  - `GET /domain-packs/resolve`
- Added explicit catalog validation through:
  - `domain-pack validate`
  - `GET /domain-packs/validate`
- Added governance visibility for the platformized catalog through:
  - `governance domain-pack`
  - `GET /governance/domain-packs`
- Extended offline validation so CLI/API acceptance now proves:
  - domain-pack preview works
  - domain-pack validation passes
  - governance sees the catalog as platformized

Verification:

- `pytest tests/test_contracts.py tests/test_execution_loop.py tests/test_api.py tests/test_cli.py tests/test_governance.py -q`
  - `171 passed`
- `pytest -q`
  - `187 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`

Result:

- Phase gate passed.
- The domain-pack platform is now inspectable and mechanically valid before compile/resume.

---

## 7. Next Reassessment

- The current domain-pack mainline now has:
  - platform-shaped contracts
  - stable stored resolution
  - preview/validation/governance surfaces
- The next reasonable second-cycle bridge is no longer more domain-pack plumbing for its own sake.
- The next slice should evaluate a minimal `Memory` preparation hook that reuses current run/audit/evidence outputs without reopening retrieval or long-term storage complexity.
