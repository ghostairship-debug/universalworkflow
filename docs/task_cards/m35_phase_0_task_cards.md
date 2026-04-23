# M35 Phase 0 Task Cards

Phase doc: [m35_phase_docs/phase_0_role_execution_productization.md](../../m35_phase_docs/phase_0_role_execution_productization.md)

Status: completed
Updated: 2026-04-24

## Cards

| Card | Status | Summary |
| --- | --- | --- |
| [M35-0A](m35_phase_0/M35-0A_phase_opening_and_workflow_orchestration_freeze.md) | completed | Open `M35 Phase 0` formally and freeze the workflow-driven execution model |
| [M35-0B](m35_phase_0/M35-0B_execution_configuration_contract_freeze.md) | completed | Freeze the additive execution-configuration contract across the shipped role/profile/cluster surfaces |
| [M35-0C](m35_phase_0/M35-0C_execution_resolution_precedence_and_seam_freeze.md) | completed | Freeze the execution-resolution precedence line and the future resolver-consumption seams |
| [M35-0D](m35_phase_0/M35-0D_validation_closeout_and_carry_forward.md) | completed | Validate the opening line, close the phase, and record honest carry-forward judgment |

## Notes

- `M35 Phase 0` starts from the accepted `M34 Phase 0` freeze baseline.
- The pre-open hardening gate is already closed and should not be reopened inside `M35`.
- The active phase should use a workspace-scoped DB label such as `m35_phase0`.
- The default implementation path uses `project_delivery` with `dev_cluster`.
- Design, risk, and evidence tasks may use `research_spike_reviewable` with `research_cluster`.
- Every detailed task card maps to exactly one workflow run with explicit review gates and recorded evidence.
- `TD-STRUCT-001` and `TD-STRUCT-003` remain bounded carry-forward debt, not the main `M35` productization theme.
- `TD-STRUCT-005` and `TD-STRUCT-006` remain deferred while `M35 Phase 0` opens and freezes the contract/precedence line.
- Closeout is recorded in [docs/reviews/m35-role-execution-productization-freeze-review.md](../reviews/m35-role-execution-productization-freeze-review.md).
- `M35 Phase 0` is now closed.
