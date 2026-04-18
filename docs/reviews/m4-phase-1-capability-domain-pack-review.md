# M4 Phase 1 Review - Capability Registry And Minimal Domain Pack Baseline

## Scope

`M4 Phase 1` closes the next concrete `M4` milestone gap after review-policy runtime expansion:

- second executor selection is now backed by a visible `CapabilityRegistry`
- one enabled minimal `Domain Pack` now exists and is exercised end-to-end

Implemented:

- `CapabilityRegistry` extracted from hardcoded router capability mapping
- `software_delivery_pack` as the first enabled minimal domain pack
- compile/status/inspection/summary/smoke projection of selected domain pack and adapter route
- CLI/API list surfaces for domain packs and capability routes

Still deferred:

- `optional` review policy remains reference-only
- there is still no full domain-pack platform or dynamic pack lifecycle

## Legacy References Used

- plan-level `Domain Pack` scope constraints from `universal_agentic_workflow_os_local_first_plan_v2_1.md`
- existing in-repo `M1.5` routing boundary as the anti-corruption baseline for second executor work

Absorbed value:

- thin registry-backed routing instead of hardcoded selection
- thin domain-pack projection instead of deep kernel expansion

Explicitly not adopted:

- full plugin or marketplace lifecycle
- heavy new persistence for domain-pack state
- facade-style orchestration expansion

## Verification

- `pytest tests/test_contracts.py tests/test_execution_loop.py tests/test_api.py tests/test_cli.py -q`
  - `143 passed`
- `pytest -q`
  - `158 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe`
  - `overall_passed=true`

## Result

- Phase gate passed.
- `M4 Smoke` now has explicit proof for both:
  - second executor selection via `CapabilityRegistry`
  - one enabled domain pack running a minimal task
- The next reassessment should decide whether to close the remaining `optional` policy gap or move to the remaining `M4` demo/operator-delivery surface.
