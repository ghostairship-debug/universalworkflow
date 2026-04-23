# Current Development Workflow

This document is the canonical living guide for what the repository should do next and how work should be executed.

## 1. Authoritative Current-State Sources

Use these in priority order when deciding what is current:

1. [docs/reviews/m36-workbench-ia-capability-slot-freeze-review.md](reviews/m36-workbench-ia-capability-slot-freeze-review.md)
2. [docs/tech-debt-registry.md](tech-debt-registry.md)
3. [README.md](../README.md)
4. [m36_phase_docs/phase_0_workbench_ia_and_capability_slot_freeze.md](../m36_phase_docs/phase_0_workbench_ia_and_capability_slot_freeze.md)
5. [docs/task_cards/m36_phase_0_task_cards.md](task_cards/m36_phase_0_task_cards.md)
6. [docs/reviews/m35-role-execution-productization-freeze-review.md](reviews/m35-role-execution-productization-freeze-review.md)
7. [docs/reviews/m34-facade-reduction-and-authority-interior-cleanup-freeze-review.md](reviews/m34-facade-reduction-and-authority-interior-cleanup-freeze-review.md)
8. [docs/reviews/m33-orchestration-service-contraction-freeze-review.md](reviews/m33-orchestration-service-contraction-freeze-review.md)
9. [docs/reviews/m32-interaction-profile-cluster-foundation-freeze-review.md](reviews/m32-interaction-profile-cluster-foundation-freeze-review.md)
10. [docs/reviews/m31-boundary-contraction-freeze-review.md](reviews/m31-boundary-contraction-freeze-review.md)

The repository has accepted `M36 Phase 0` and currently has no open post-`M36 Phase 0` bounded phase.

Archived planning context from the pre-merge backup workspace is summarized in [docs/reviews/m32-archived-planning-inputs.md](reviews/m32-archived-planning-inputs.md). Treat it as reference-only, not as parallel execution truth.

The rebuilt post-`M34` roadmap is summarized in [POST_M34_MULTIPHASE_ROADMAP.md](../POST_M34_MULTIPHASE_ROADMAP.md). Treat it as reference-only until the next bounded phase opens.

## 2. Current Repository Position

The repository has now completed:

- `M8` through `M20`
- `M21` through `M30`
- accepted `M31 Phase 0`
- accepted `M32 Phase 0`
- accepted `M33 Phase 0`
- accepted `M34 Phase 0`
- accepted `M35`
- accepted `M36 Phase 0`
- the runtime, governance, orchestration, Web operator UI, remote worker productization, repo-mutation baseline, single-store quorum-style scheduler-authority closure, interaction/profile/cluster foundation, and the first shared orchestration/service contraction line
- a second bounded scheduler-authority/service honesty cleanup line
- explicit execution-profile contracts, an authoritative execution-resolution line, additive config defaults, and additive read-side explainability for shipped execution choices
- a bounded `M36 Phase 0` workbench IA / capability-slot freeze with additive `codex` routing and bounded MiniMax MCP search/image-understanding pilots
- retirement of `TD-021`

Current status:

- the mainline product is `v1 core complete`
- the latest accepted freeze is `M36 Workbench IA / Capability Slot Freeze`
- there is no currently active bounded phase
- `TD-STRUCT-001` and `TD-STRUCT-003` remain partially repaid carry-forward debt
- `TD-STRUCT-005` remains deferred and is aligned mainly to `M38-M39`
- `TD-STRUCT-006` remains deferred and is aligned mainly to `M39`
- `TD-STRUCT-004` remains repaid in accepted `M33 Phase 0`
- the latest accepted foundation is interaction-first, role-profile-aware, cluster-aware, execution-profile-aware, and capability-slot-aware, with resolved execution projected through the shipped multi-role presets
- the pre-open hardening gate is complete: the governance-report regressions are repaired, the root planning docs are aligned, and the no-behavior-change `APIRouter` split has been absorbed as pre-open work
- automation-plane breadth remains deferred
- the built-in Web UI and TUI remain operator surfaces rather than completed chat-style natural-language workbenches
- natural-language goal planning and launch exist today through CLI/API plus the minimum workbench preview; accepted `M36 Phase 0` froze the workbench IA and future surface map but did not yet ship `M36 Phase 1` conversational flow
- `codex` is now an additive coding adapter option and the capability plane now exposes a bounded MiniMax MCP pilot profile for `web_search` and `understand_image`
- `MMX CLI`, `gcloud` / Vertex AI, and broader capability-ecosystem productization remain deferred
- the rebuilt post-`M34` roadmap restores a meaningful multi-phase shape for later product milestones, and later `M36+` work remains reference-only until the next phase opens

## 3. What Must Happen Next

The next step is to open the next bounded phase honestly only after its phase doc and task-card pack exist. The likely next slice is `M36 Phase 1`, but it is not active yet.

The repository should proceed by:

1. treating accepted [docs/reviews/m36-workbench-ia-capability-slot-freeze-review.md](reviews/m36-workbench-ia-capability-slot-freeze-review.md) as the latest completed bounded baseline
2. keeping the retained `M36 Phase 0` materials as closeout evidence rather than active execution truth
3. opening `M36 Phase 1` only after writing its phase doc, task-card index, and detailed cards
4. executing bug-first: repair real workflow/runtime regressions before continuing new scope
5. preserving the additive `execution_profile` family, execution-resolution trace, and bounded capability-slot rules shipped through accepted `M35` plus `M36 Phase 0`
6. using `interaction` sessions to kick off the next phase, with `project_delivery` + `dev_cluster` or `research_spike_reviewable` + `research_cluster` chosen by task type
7. mapping each detailed task card to exactly one workflow run, with explicit mutation contracts when repo edits are allowed
8. using `run approve` / `run reject` or `/ui/reviews` as the review gate, and using `interaction followup` rather than free-form replacement runs when work is rejected
9. keeping `MMX CLI`, `gcloud` / Vertex AI, automation-plane breadth, plus `TD-STRUCT-005` / `TD-STRUCT-006` expansion deferred until a later bounded follow-on says otherwise

## 4. Task-Card Protocol

The repository continues to use the task-card protocol for every new active phase:

1. write the current phase doc first
2. write the current phase task-card index
3. write the current phase detailed task cards
4. execute only after the detailed cards exist
5. update cards with actual results while implementing
6. close the phase with tests, review, and living-doc updates

Rules:

- generate task cards only for the current active phase
- do not pre-generate future phase task-card packs
- closed task-card packs are not retained by default; once their conclusions are absorbed into freeze reviews and integrated roadmaps, prefer pruning them
- complex phases require standalone detailed cards for every task
- post-`M34` product milestones should normally use meaningful multi-phase progression; a single `Phase 0` is only the default when the milestone is intentionally debt-bounded
- every detailed card should declare the intended workflow path, including its default preset/cluster pairing when that choice matters
- every mutating workflow run should carry `task_card_ref`, `task_card_path`, bounded `write_set`, bounded `read_set`, explicit `test_command` values, bounded `max_fix_iterations`, and `mutation_mode` only when mutation is intended
- every completed card should record real workflow evidence back into the card, including at least a summary/report view and the validation commands actually run

## 5. Collaboration Mode

Default collaboration remains:

- architecture, high-risk semantics, and final release decisions are human-led
- workflow is used as the bounded execution engine, validation surface, and audit/replay control plane
- bug-first always applies: if workflow self-dogfood exposes a real bug, repair it before continuing feature scope

## 6. Minimal Documentation Rule

Keep the working tree small.

- prefer keeping only the latest accepted freeze review, current README, current workflow guide, living debt registry, and any currently active phase materials as the active truth set
- if useful long-horizon planning rationale must be retained, collapse it into one clearly non-authoritative root roadmap or archive note instead of restoring multiple competing plans
- treat other plans, phase docs, task-card packs, and historical review bundles as disposable once their conclusions are absorbed
- if historical detail is needed later, use git history instead of restoring large doc packs by default

## 7. What Counts As Done

### Task done

- code or documentation delta is implemented
- declared tests pass
- task-card status is updated
- any promised evidence is recorded

### Phase done

- every task card in the active phase is complete
- phase-level verification passes
- phase review or equivalent closeout is written

### Milestone done

- freeze review exists
- living docs are updated
- debt implications are recorded
- the repository can state what is complete and what remains deferred

## 8. Current One-Line Instruction

Treat accepted `M36 Phase 0` as the latest completed bounded freeze baseline, keep no post-`M36 Phase 0` phase active until the next phase doc and task-card pack exist, and do not open later `M36+` breadth except through the task-card protocol.
