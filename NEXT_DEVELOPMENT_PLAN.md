# Next Development Plan

Status: reference-only pointer
Date: 2026-04-24
Baseline: no active post-`M36 Phase 0` phase
Latest accepted freeze: `M36 Phase 0`
Latest absorbed planning input: root-level `GPT_PRO_ROADMAP .md`

## 1. Purpose

This file is the short root-level planning pointer for the repository after accepted `M36 Phase 0`.

It is also the place where external roadmap proposals should be reduced into one repository-aligned next-step summary instead of remaining as competing truth.

It does **not** open the next phase by itself. Current execution truth now comes from:

1. [docs/current_development_workflow.md](docs/current_development_workflow.md)
2. [docs/reviews/m36-workbench-ia-capability-slot-freeze-review.md](docs/reviews/m36-workbench-ia-capability-slot-freeze-review.md)
3. [docs/tech-debt-registry.md](docs/tech-debt-registry.md)
4. [m36_phase_docs/phase_0_workbench_ia_and_capability_slot_freeze.md](m36_phase_docs/phase_0_workbench_ia_and_capability_slot_freeze.md)
5. [docs/task_cards/m36_phase_0_task_cards.md](docs/task_cards/m36_phase_0_task_cards.md)

## 2. Current Honest Position

The repository has accepted:

- `M31 Phase 0`
- `M32 Phase 0`
- `M33 Phase 0`
- `M34 Phase 0`
- `M35`
- `M36 Phase 0`

That means the repository now has:

- interaction / profile / cluster foundation
- shared orchestration/service contraction for the shipped multi-role presets
- a second scheduler-authority honesty cleanup line
- a minimum workbench preview
- explicit execution-profile contracts, an authoritative execution-resolution line, additive config defaults, and additive read-side explainability for shipped execution choices
- a frozen workbench IA / surface map and bounded external capability-slot strategy with additive `codex` routing plus bounded MiniMax MCP search/image-understanding pilots

It does **not** mean that later `M36+` breadth has already been opened.

## 3. External Roadmap Assessment

The root-level external `GPT_PRO_ROADMAP .md` is directionally aligned with current repository truth and should be treated as an input to absorb, not as a second active plan.

The assessment result is:

- adopt the remaining `M36-M39` platform productization line and the optional `M40` design / visual-verification follow-on
- adopt the hard constraints around SQLite single-store honesty, LangGraph staying behind the runtime boundary, and bounded automation guarded by review/audit
- keep the judgment that the governance tech-debt report regression was the real pre-open gate before `M35`
- keep the idea that the later workbench should grow from the existing interaction-session APIs rather than from a parallel back-end stack
- keep `NEXT_DEVELOPMENT_PLAN.md` itself; it already serves the current workflow rule of one root planning pointer
- keep `TD-STRUCT-005` primarily aligned to `M38-M39`
- keep `TD-STRUCT-006` primarily aligned to `M39`

## 4. Rebuilt Post-M34 Roadmap

The detailed rebuilt roadmap lives in:

- [POST_M34_MULTIPHASE_ROADMAP.md](POST_M34_MULTIPHASE_ROADMAP.md)

That roadmap now remains reference-only beyond the accepted `M36 Phase 0` baseline.

Its main conclusions are:

- the old one-milestone-one-`Phase 0` drift should stop for the productization line
- post-`M34` milestones should return to meaningful multi-phase progression
- the earlier platform product target now honestly requires the remainder of `M36` plus `M37-M39`
- if the target also includes domain-grade design and multimodal visual verification, `M40` is likely needed

## 5. Immediate Next Step

Accepted `M36 Phase 0` is now complete.

The current execution order is:

1. treat [docs/reviews/m35-role-execution-productization-freeze-review.md](docs/reviews/m35-role-execution-productization-freeze-review.md) as the latest completed milestone closeout
2. treat [docs/reviews/m36-workbench-ia-capability-slot-freeze-review.md](docs/reviews/m36-workbench-ia-capability-slot-freeze-review.md) as the latest accepted bounded freeze and keep the retained `M36 Phase 0` materials as closeout evidence rather than active execution truth
3. if `M36` continues, open `M36 Phase 1` with a real phase doc and task-card pack before implementation
4. preserve the bounded `codex` and MiniMax MCP pilots while continuing to defer `MMX CLI`, `gcloud` / Vertex AI, automation-plane breadth, plus broad `TD-STRUCT-005` / `TD-STRUCT-006` expansion until a later bounded phase says otherwise

## 6. Planning Boundary

This planning update is a pointer only.

- no post-`M36 Phase 0` phase is opened here
- later `M36+` implementation is not claimed here
- any future code or contract changes required by the roadmap still belong in the next active phase docs and task cards
