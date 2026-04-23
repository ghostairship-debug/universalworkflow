# M36 Phase 0 Task Cards

Phase doc: [m36_phase_docs/phase_0_workbench_ia_and_capability_slot_freeze.md](../../m36_phase_docs/phase_0_workbench_ia_and_capability_slot_freeze.md)

Status: completed
Updated: 2026-04-24

## Cards

| Card | Status | Summary |
| --- | --- | --- |
| [M36-0A](m36_phase_0/M36-0A_phase_opening_and_truth_alignment.md) | completed | Open `M36 Phase 0` formally and align repository truth to the new bounded phase |
| [M36-0B](m36_phase_0/M36-0B_workbench_ia_and_surface_freeze.md) | completed | Freeze the workbench IA and surface map without prematurely shipping `M36 Phase 1` breadth |
| [M36-0C](m36_phase_0/M36-0C_external_capability_slot_freeze_and_bounded_pilots.md) | completed | Freeze external capability slots and land bounded `Codex CLI` plus MiniMax MCP pilots |
| [M36-0D](m36_phase_0/M36-0D_validation_closeout_and_carry_forward.md) | completed | Validate the phase, close it honestly, and record carry-forward judgment |

## Notes

- `M36 Phase 0` starts from the accepted `M35` freeze baseline.
- The additive execution-profile and execution-resolution truth from `M35` remains intact through this phase.
- The active phase should use a workspace-scoped DB label such as `m36_phase0`.
- The default implementation path uses `project_delivery` with `dev_cluster`.
- Design, risk, and evidence tasks may use `research_spike_reviewable` with `research_cluster`.
- Every detailed task card maps to exactly one workflow run with explicit review gates and recorded evidence.
- `Codex CLI` is introduced as an additive coding adapter, not as a replacement runtime stack.
- MiniMax MCP is introduced only through bounded `web_search` and `understand_image` profiles on the existing capability plane.
- `MMX CLI`, `gcloud` / Vertex AI, automation breadth, and broader capability-ecosystem productization remain deferred.
- Closeout is recorded in [docs/reviews/m36-workbench-ia-capability-slot-freeze-review.md](../reviews/m36-workbench-ia-capability-slot-freeze-review.md).
- `M36 Phase 0` is now closed.
