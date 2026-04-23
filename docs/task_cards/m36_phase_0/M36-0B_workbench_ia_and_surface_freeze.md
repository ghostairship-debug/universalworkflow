# M36-0B Workbench IA And Surface Freeze

Status: completed

## Goal

Freeze the workbench information architecture and the interaction/workbench surface boundaries so later `M36` work can build on one explicit product path instead of introducing parallel front-end or back-end entry points.

## Acceptance

- make the workbench/operator separation explicit in the active phase docs and root workflow guide
- freeze `M36 Phase 0` as an IA/surface-freeze slice, not the full conversational workbench implementation
- record that the existing workbench remains a minimum preview while the future workbench flow is deferred to `M36 Phase 1`
- keep current CLI/API/operator routes stable and additive
- keep the `execution_profile` and read-side explanation families from `M35` as the execution truth consumed by later workbench flows

## Notes

- this card does not ship the guided goal-input, clarification, follow-up, or review UX from later `M36` phases
- this card is about freezing boundaries and naming the product seams honestly

## Result

- froze the workbench IA around the existing interaction-session and launch surfaces instead of inventing a parallel back-end stack
- made the operator-surface vs product-workbench split explicit in the phase docs and root workflow guide
- recorded that accepted `M36 Phase 0` still leaves the current `/ui/workbench` as a minimum preview rather than a completed conversational shell
- preserved current route families and additive execution/read-model truth from `M35`
