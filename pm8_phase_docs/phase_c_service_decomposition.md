# Pre-M8 Phase C - Service Decomposition

**Phase status:** Completed  
**Phase position:** This phase begins after `PM8-B` closes the highest-value runtime-safety and portability gaps.

**Entry condition:** The repository now has an explicit pre-`M8` hardening boundary plus safer subprocess execution, but `packages/core_domain/services.py` remains the dominant structural hotspot and still concentrates too much business logic in one file.

---

## 1. Reassessment

Current implementation status:

- `PM8-A` and `PM8-B` are complete.
- `packages/core_domain/services.py` is still the largest structural bottleneck in the repository.
- The repository already has stable CLI/API coverage for the current runtime baseline, so this phase can prioritize move-only extraction over behavior change.
- The safest extraction targets are the logic groups that already behave like bounded subsystems:
  - projection/reporting
  - memory/simulation
  - runtime lifecycle and review entry points

Decision:

- keep `OrchestratorService` as the compatibility facade for CLI/API callers
- move bounded method groups into dedicated service modules first
- preserve all public method names and contracts
- defer deeper semantic redesign; this phase is decomposition, not a runtime rewrite

---

## 2. In Scope

- extract service dataclasses/types out of `services.py`
- extract projection/reporting logic into a dedicated module
- extract memory and simulation logic into a dedicated module
- extract lifecycle/review entry points into a dedicated module
- reduce `OrchestratorService` into a thinner orchestration/compatibility facade
- update living docs and phase review with the new service-map

---

## 3. Out Of Scope

- new workflow features
- CLI/API behavior changes
- runtime semantics redesign
- review-policy expansion
- offline-validation decomposition
- governance contract restructuring

---

## 4. Target Baseline

- `services.py` is no longer the single dominant business-logic container
- `OrchestratorService` remains the public entry point
- extracted modules own bounded responsibility areas
- public CLI/API behavior remains stable
- current tests remain green

---

## 5. Phase Task Breakdown Principle

This phase is split into:

1. service boundary map and shared service types
2. projection/reporting extraction
3. memory/simulation extraction
4. lifecycle/review extraction and facade closeout

---

## 6. Outcome

- Added bounded service modules:
  - `packages/core_domain/service_types.py`
  - `packages/core_domain/service_projection.py`
  - `packages/core_domain/service_memory_simulation.py`
  - `packages/core_domain/service_lifecycle.py`
- Kept `OrchestratorService` as the public compatibility facade used by CLI/API/TUI.
- Moved:
  - projection/reporting/status/audit/dashboard logic into `ProjectionServiceMixin`
  - memory/simulation/domain-pack operator logic into `MemorySimulationServiceMixin`
  - compile/recompile/review/resume/cancel lifecycle entry points into `LifecycleServiceMixin`
- Reduced `packages/core_domain/services.py` from the previous `3400+` line hotspot to a thinner facade/helper container of roughly `1690` lines.
- Preserved current CLI/API behavior while redistributing the main service logic across bounded modules.

Verification:

- `pytest tests/test_execution_loop.py tests/test_cli.py tests/test_api.py tests/test_governance.py -q`
  - `174 passed`

Result:

- Phase gate passed.
- `OrchestratorService` is no longer the dominant single business-logic container, and the repository can proceed to validation/governance hardening.

---

## 7. Next Reassessment

The next approved phase after this one is:

- `Pre-M8 Phase D - Validation, Governance Contract, And Context Hardening`

That phase should only begin after service extraction is stable and the repository has revalidated the shared runtime surfaces against the decomposed service map.
