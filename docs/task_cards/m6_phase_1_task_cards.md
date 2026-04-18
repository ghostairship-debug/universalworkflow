# M6 Phase 1 Task Cards

**Phase:** `M6 Phase 1 - Domain Pack Platformization Baseline`  
**Goal:** Turn the current minimal `software_delivery_pack` proof into a reusable platform boundary without reopening plugin lifecycle or broad runtime expansion.

## Task Cards

| Task | Size | Goal | Depends On | Primary Files | Verification | Done When |
| --- | --- | --- | --- | --- | --- | --- |
| `P1-T01` | `complex` | Introduce reusable domain-pack contracts, seed schema, and registry-backed stable resolution | `Phase 1 entry` | `packages/contracts/*`, `packages/core_domain/domain_packs.py`, `infra/seeds/domain_packs.json`, `tests/test_contracts.py` | contract tests | current pack definition is platform-shaped and registry can emit `DomainPackResolution` |
| `P1-T02` | `complex` | Carry the resolved pack snapshot through compile/runtime context and reuse it in operator surfaces | `P1-T01` | `packages/core_domain/compile.py`, `packages/core_domain/services.py`, `tests/test_execution_loop.py`, `tests/test_api.py`, `tests/test_cli.py` | execution + CLI/API tests | compile/status/summary/inspection use stable pack resolution |
| `P1-T03` | `medium` | Update governance, README, and phase review to describe the platformized baseline | `P1-T01`, `P1-T02` | `packages/core_domain/governance.py`, `README.md`, `docs/reviews/*`, `tests/test_governance.py`, `tests/test_release_closeout.py` | governance tests + docs check | docs and readiness surfaces describe more than “one pack exists” |

## Sequencing Notes

- `P1-T01` defines the new contract surface and seed shape.
- `P1-T02` must use the resolution emitted by `P1-T01`; it should not invent a second projection format.
- `P1-T03` should describe the actual shipped platform boundary, not a future plugin system.

## Closeout

- `P1-T01` completed: platform-shaped contracts, seed schema, and `DomainPackResolution` landed.
- `P1-T02` completed: compile/runtime/operator surfaces now store and reuse stable pack resolution.
- `P1-T03` completed: governance, README, and release/readiness surfaces now describe the platformized baseline.
