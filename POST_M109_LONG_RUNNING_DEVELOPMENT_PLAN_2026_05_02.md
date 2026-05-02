# Post-M109 Long-Running Development Plan

> Source basis: `codex_guidance_universalworkflow_refactor.md` and `universalworkflow_deep_evaluation_report.md`.
> Current baseline: M109 accepted; latest strict commercial build remains `NO-GO`.
> Scope: repair the workflow truth chain, commercial-game final gate, same-project task-card execution, and product-body evidence path without auto-creating M110 task cards.

## Current Truth

- `machine_evidence_go=false`
- `commercial_game_development_readiness_go=true` for development-start control-plane readiness only
- `human_player_review_go=false`
- `commercial_playable_go=false`
- The latest reviewed build path was correct; the failure is product-level.
- Runtime hooks, canvas presence, feature flags, browser events, screenshots, scaffold/build evidence, and Cocos bridge evidence cannot prove commercial playable completion.
- The next success criterion is honest failure and false-positive prevention, not commercial GO.

## Development Discipline

- Workflow remains the control plane: receipt, lease, write_set, provider live proof, evidence, operator packet, and task-card DB authority remain mandatory.
- Codex/local patches are allowed for complex workflow/control-plane hardening, safety protocols, tests, and documentation wiring.
- The plan/milestone/phase/task-card hierarchy remains intact. This document stops at milestone and phase level.
- Future phases must create DB-backed task cards only after a phase is active; this document does not export future task cards.
- If a phase has only one card later, it must explicitly mark `single_card_exception`.
- Any workflow bug blocks business work until repaired with regression tests.
- Deprecated `commercial_cocos_game` fixed-template delivery remains blocked by `legacy_cocos_template_removed`.

## Next Development Plan

Current completed slices have hardened the false-positive gates, created a baseline-only Cocos product-body shell, and added an independent `commercial_game_development_readiness_v1` evidence口径. The active phase `Product Body Runtime And Semantic Trace Implementation` has been materialized in the DB as run `product_body_runtime_semantic_trace_20260502` with exactly three current-phase task cards; the quality report is `GO`, lifecycle is `active`, and requirement coverage is passed.

Phase sequence:

1. Active phase preflight and task-card materialization.
   - Run `plan-graph`, `policy-preview`, and `goal-packet` for the new phase.
   - Generate only current-phase DB task cards.
   - Require lifecycle status `active` or `approved`, task-card quality pass, and complete `req_id` coverage before execution.

2. Runtime model implementation.
   - Turn the baseline `BoardModel`, `PieceModel`, `RuleEngine`, `CandidateTray`, and `SemanticTestBridge` into real same-project runtime code.
   - Implement 10x10 board state, piece placement, line clear, candidate refresh, game-over, and anti-stall behavior from the model, not browser events.
   - Export semantic traces from the model/runtime and feed them into `gameplay_semantic_evidence`.

3. Player-visible product body binding.
   - Bind `BoardView`, `InputController`, `LevelGoalController`, `ShopSkinController`, `AudioFeedbackController`, HUD, level-goal panel, shop/skin panel, gallery/collection surface, and audio controls into scene/prefab evidence.
   - Keep `baseline_only=true` from satisfying commercial readiness; only real runtime/component evidence can pass product-body contracts.

4. Requirement coverage and product-depth alignment.
   - Map source `req_id`s to gameplay loop, level goals, shop/skin ownership, gallery/collection, audio, feedback, revive/failure behavior, and UI readability.
   - Produce evidence that proves the implemented behavior, not only feature flags or event markers.

5. Build, playtest, and human-review handoff.
   - Run Cocos build and browser playtest only after same-project worker, gameplay semantic, product body, and product depth contracts pass.
   - Machine pass without human acceptance must stop at `AWAITING_HUMAN_REVIEW`.
   - Human `NO-GO` creates the next repair phase; it must not be converted into a commercial-ready claim.

Blocking conditions:

- Any workflow/receipt/lease/repo-mutation/task-card bug pauses product work until repaired.
- Any task card without lifecycle eligibility, quality pass, fresh receipt execution, changed files, passing tests, and requirement coverage remains non-executable.
- Any runtime-hook, canvas-only, event-only, feature-flag-only, baseline-only, scaffold-only, or build-only evidence remains insufficient for commercial GO.

Development-readiness distinction:

- `commercial_game_development_readiness_go=true` means the workflow can safely start real commercial game content task cards with lifecycle, quality, same-project worker, semantic/product-body starting-point, and req_id coverage gates in place.
- It is not a commercial delivery claim. `commercial_playable_go=true` remains forbidden until machine contracts, build/playtest, player-visible evidence, and explicit human acceptance all pass.
- `baseline_only=true` may support development-start readiness, but final commercial gate now blocks it with `baseline_only_cannot_pass_commercial_final_gate`.

Exit criteria:

- `gameplay_semantic_evidence.go=true` from real runtime/model traces.
- `product_body_evidence.go=true` from Cocos component/scene bindings.
- Product-depth evidence is aligned to source requirements and player-visible behavior.
- Commercial final gate can reach `AWAITING_HUMAN_REVIEW` only after all machine contracts pass, and `commercial_playable_go` stays false until real human acceptance.

## Milestone A: Execution Truth Hardening

Goal: prevent task-card and worker lifecycle false positives before new product work.

Phases:

1. DB task-card lifecycle gate.
   - Split quality status from lifecycle status.
   - Treat `draft`, `archived`, `blocked`, `failed`, `running`, and `completed` as not eligible for new execution.
   - Only `active` and `approved` cards can be execution-eligible when quality passes.

2. Same-project worker fresh execution gate.
   - Reject ineligible DB lifecycle states before worker execution.
   - Do not let prior ledger entries or historical feature evidence complete implementation.
   - Require fresh receipt, child run, child attempt, changed files, and passing tests for completed implementation entries.

3. Upstream short-circuit integrity.
   - If same-project implementation fails, build, browser playtest, gameplay semantic, product body, product depth, and human review remain blocked/skipped.
   - Failure reports should preserve root cause instead of adding noisy downstream product blockers.

Exit criteria:

- Draft cards cannot execute even if quality passes.
- Attempts-zero evidence cannot complete an implementation card.
- Historical evidence is reference-only.
- Same-project worker failure blocks downstream stages.

## Milestone B: Commercial Evidence Contract Hardening

Goal: make the final gate reject machine-friendly but player-invalid evidence.

Phases:

1. Gameplay semantic contract.
   - Require 10x10 board state, piece model, exactly three candidates, placement trace, line-clear trace, candidate refresh trace, game-over trace, and anti-stall trace.
   - Reject event-only, feature-flag-only, screenshot-only, and canvas-only gameplay claims.

2. Product body contract.
   - Require real Cocos scene nodes and component bindings.
   - Reject runtime hook, DOM canvas, feature flag, and event marker substitution as product-body proof.

3. Final gate integration.
   - Final commercial gate must require asset graph, Cocos bridge when requested, same-project fresh patch, build, browser playtest, gameplay semantic, product body, product depth, and human review.

Exit criteria:

- `machine_evidence_go` cannot be true without gameplay semantic and product body contracts.
- `AWAITING_HUMAN_REVIEW` is possible only after all machine contracts pass.
- Human review failure keeps `commercial_playable_go=false`.

## Milestone C: Lossless Requirement Compiler

Goal: prevent source brief/PDF requirements from being compressed into advisory summaries.

Phases:

1. Requirement matrix schema.
   - Add stable `req_id`, source path/page, original quote, normalized requirement, category, priority, downstream owner, and acceptance method.

2. Role-output preservation.
   - Role outputs must preserve source requirement IDs and may add derived requirements only as derived records.

3. Task-card coverage gate.
   - Product implementation cards cannot execute unless they cite required source requirement coverage.

Exit criteria:

- Core gameplay, levels, shop, skins, props, gallery, UI, audio, feedback, and config requirements remain traceable from source to task card and evidence.

## Milestone D: Cocos Product Body Baseline

Goal: create a non-fixed-template but real Cocos component baseline for future commercial implementation.

Phases:

1. Product-body model baseline.
   - Define board model, piece model, rule engine, candidate tray, semantic harness, and product-body contract generator outside `packages/core_domain`.

2. Cocos component bindings.
   - Generate or validate `BoardModel`, `PieceModel`, `RuleEngine`, `CandidateTray`, `BoardView`, `InputController`, `LevelGoalController`, `ShopSkinController`, `AudioFeedbackController`, and `SemanticTestBridge`.

3. Runtime semantic trace export.
   - Export semantic traces from the real runtime/model, not DOM hooks.

Exit criteria:

- Product body gate can distinguish real Cocos component/model evidence from scaffold/browser-hook evidence.

## Milestone E: Red-Team QA And Supervisor

Goal: make QA and supervisor default to disproof rather than confirmation.

Phases:

1. Red-team QA packet.
   - QA records attempted disproofs, accepted proofs, blockers, and evidence links.

2. Supervisor override.
   - Supervisor can force `NO-GO` on draft cards, missing fresh execution, attempts zero, operator fallback product writes, runtime hook body, incomplete requirement coverage, missing semantic proof, and failed human review.

3. Human review loop.
   - Machine pass without human review becomes `AWAITING_HUMAN_REVIEW`, not GO.
   - Human failure creates repair phase input, not a commercial claim.

Exit criteria:

- The `pipeline_ecf26665254e` false-positive pattern is rejected by regression tests.

## Milestone F: Architecture And CI Hardening

Goal: reduce long-term control-plane complexity while preserving local-first runtime semantics.

Phases:

1. Service extraction by friction.
   - Extract task-card lifecycle, evidence truth, final gate, gameplay semantic gate, receipt/lease, and repo mutation services only when tests show clear pressure.

2. Layered CI.
   - Keep fast tests for contracts, task cards, receipts, repo mutation, final-gate negatives, active truth, and pipeline preview.
   - Move Cocos/browser/provider live checks to integration/nightly/manual lanes.

3. Active-truth automation.
   - Keep README, current workflow, tech-debt registry, pipeline truth, and DB task-card state aligned.

Exit criteria:

- Active truth drift becomes machine-detectable.
- Control-plane modules shrink only through proven boundaries, not speculative refactors.

## Completed Slices In This Run

Slice 1 implements the first hardening slice from Milestones A and B:

- DB lifecycle-aware task-card quality report v2.
- Same-project worker lifecycle rejection and fresh implementation metadata checks.
- Historical same-project evidence downgraded to reference-only.
- New gameplay semantic and product body evidence contracts.
- Final gate now includes gameplay semantic and product body machine contracts.
- Regression tests added for draft lifecycle blocking, evidence reuse downgrade, semantic/product-body false positives, and upstream short-circuit expansion.

Slice 2 implements the first Lossless Requirement Compiler slice from Milestone C:

- Unified intake now emits `requirement_matrix.json` and `requirement_matrix.md` with stable `req_id`, source path/page/section, original quote, normalized requirement, category, priority, downstream owner, and acceptance method.
- Agent packets now include the requirement matrix path and role-relevant req_id trace.
- Generated same-project implementation task cards carry `required_requirement_ids` and `covered_requirement_ids`.
- Task-card quality/execution eligibility now blocks cards that declare requirement coverage but lack complete req_id coverage.
- Commercial task-card worker preflight now rejects quality-ineligible cards as well as lifecycle-ineligible cards.

Slice 3 starts the Cocos Product Body Baseline from Milestone D:

- Added a compact Cocos contribution module that writes `BoardModel`, `PieceModel`, `RuleEngine`, `CandidateTray`, `BoardView`, `InputController`, `LevelGoalController`, `ShopSkinController`, `AudioFeedbackController`, and `SemanticTestBridge` baseline components into the persistent project shell.
- The baseline emits raw gameplay semantic evidence and product-body evidence with a 10x10 board, three candidates, piece shapes, semantic trace files, scene nodes, and Cocos component bindings.
- The baseline manifest explicitly sets `commercial_playable_go=false` and `baseline_only=true`.
- `bootstrap_cocos_project_shell` now includes the baseline manifest path without writing final commercial feature coverage.
- Production/business ratchets were refreshed with explicit M110 split windows for the accepted post-review hardening files.

Slice 4 completes the development-readiness loop:

- Added `commercial_game_development_readiness_v1` as a separate evidence contract from `commercial_playable_go`.
- Wired production worker payloads to emit `commercial_game_development_readiness_go` while preserving `commercial_playable_go=false` without human acceptance.
- Added active-phase-only product-body runtime task-card generation for `Product Body Runtime And Semantic Trace Implementation`.
- Generated DB task cards for run `product_body_runtime_semantic_trace_20260502`: runtime models, semantic core-loop traces, and scene/prefab component evidence.
- Strengthened final gate so baseline-only semantic/product-body evidence cannot pass commercial final gate.
- Preflight evidence was saved under `state/product_body_runtime_semantic_trace_20260502/`.

## Validation Commands

Targeted:

```powershell
python -m pytest -q tests/test_cocos_product_body_baseline.py tests/test_task_card_store.py tests/test_m109_unified_brief.py tests/test_commercial_game_evidence_contracts.py tests/test_pipeline_and_automation_cli.py
```

Doc gate:

```powershell
python -m infra.scripts.check_doc_links
```

Broader follow-up:

```powershell
python -m pytest -q tests/test_repositories.py
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" governance active-truth-check --strict --output-path state/governance/active_truth_check.json
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite full
git diff --check
```
