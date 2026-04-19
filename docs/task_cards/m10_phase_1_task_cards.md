# M10 Phase 1 Task Cards

**Phase:** `M10 Phase 1 - Ownership Topology And Claim Domain Freeze`  
**Status:** Complete

This is a complex phase. Every task below has a standalone detailed card.

## Reassessment

- `M10 Phase 0` is complete and froze ownership topology as the first feature-bearing `M10` slice.
- The repository already has local claim, worker-lease, attempt, reconcile, and projection surfaces.
- The current gap is not missing ownership history; it is that ownership topology is still too implicit for later barrier/parallel work.

## Task Cards

| ID | Complexity | Goal | Depends On | Read Scope | Write Scope | Verification | Exit Signal | Doc Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `M10-1A` | `complex` | Add explicit ownership-topology fields to claim and worker-lease contracts, migrations, and repositories | `Phase entry` | `packages/contracts/runtime.py`, `packages/contracts/events.py`, `packages/core_domain/repositories.py`, `infra/migrations/*`, `tests/test_contracts.py`, `tests/test_repositories.py` | contracts, repositories, migration, contract/repository tests, active phase docs | contract + repository tests | persisted ownership topology exists without breaking current claim/lease lifecycle rules | [M10-1A](m10_phase_1/M10-1A_ownership_contract_and_persistence_freeze.md) |
| `M10-1B` | `complex` | Wire ownership topology through lifecycle, status/inspection/replay projections, CLI, and API surfaces | `M10-1A` | `packages/core_domain/services.py`, `packages/core_domain/service_lifecycle.py`, `packages/core_domain/service_projection.py`, `apps/operator_cli/main.py`, `apps/orchestrator_api/main.py`, `tests/test_execution_loop.py`, `tests/test_cli.py`, `tests/test_api.py` | service, lifecycle, projection, CLI/API, focused tests, active phase docs | execution-loop + CLI + API tests | claim/lease topology is visible and coherent across run surfaces | [M10-1B](m10_phase_1/M10-1B_lifecycle_projection_and_surface_integration.md) |
| `M10-1C` | `medium` | Close the phase with updated docs, governance wording as needed, and focused verification evidence | `M10-1B` | `README.md`, `docs/current_development_workflow.md`, `docs/tech-debt-registry.md`, active phase docs, `packages/core_domain/governance.py`, `tests/test_governance.py` | living docs, governance wording if needed, active phase docs, review doc | focused `pytest` + `python -m infra.scripts.check_doc_links` | ownership topology is frozen and the phase is ready to hand off to the next reassessment | [M10-1C](m10_phase_1/M10-1C_docs_governance_and_closeout.md) |

## Completion Notes

### `M10-1A`

- Prefer additive topology fields over disruptive renames.
- Preserve current release/expiry lifecycle validation.
- Keep the new contract grounded in what the current local control plane can actually populate.
- Completed with contract, event-payload, migration, and repository updates for explicit ownership topology.

### `M10-1B`

- Link ownership records to attempts where the runtime flow already proves that relationship.
- Add topology projections without losing the existing simple claim/lease summaries.
- Do not mix barrier or batch-execution logic into this phase.
- Completed with lifecycle wiring plus projection, CLI, and API exposure for `ownership_topology`.

### `M10-1C`

- Keep debt and governance wording honest about what remains deferred.
- Completed by closing the phase, writing the phase review, and handing off to `M10 Phase 2`.
