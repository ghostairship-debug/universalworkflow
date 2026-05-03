# Post-M109 Long-Running Development Plan

> Source basis: archived inputs `docs/archive/root_legacy_2026_05_03/codex_guidance_universalworkflow_refactor.md` and `docs/archive/root_legacy_2026_05_03/universalworkflow_deep_evaluation_report.md`.
> Current baseline: M109 accepted; the latest user review rejected the launched commercial build as not playable, so a commercial playability repair loop is active.
> Scope: repair the workflow truth chain, commercial-game final gate, same-project task-card execution, and product-body evidence path without auto-creating M110 task cards.

## Current Truth

2026-05-03 update: the user launched the current build and returned a real product-level `NO-GO` ("not playable"). A second review of the first repair slice also returned `NO-GO` with concrete defects: missing BGM, incomplete functions, missing Chinese UI, drag stutter, and drag coordinate mismatch. These reviews supersede the prior optimistic machine-ready handoff for product acceptance. The current repair loop may produce agent QA and browser evidence, but it must not convert unattended validation into human acceptance.

- `agent_playtest_after_repair_go=true` for the current browser automation pass only
- `commercial_game_development_readiness_go=true` for development-start control-plane readiness only
- `human_player_review_go=false`
- `commercial_playable_go=false`
- The latest human/user review status is `NO-GO`; the only valid next acceptance state is a new explicit human acceptance after repair.
- The launched build path was correct; the failure was product-level. The current repair slices replace the proof-like browser bridge with a player-visible 10x10 runtime, Chinese UI, procedural BGM/SFX, aligned drag preview, and player-visible function panels, but this remains below final commercial playable acceptance until explicitly accepted by a human reviewer.
- Runtime hooks, canvas presence, feature flags, browser events, screenshots, scaffold/build evidence, and Cocos bridge evidence cannot prove commercial playable completion.
- The current success criterion is an honest repair-and-review loop: playable runtime evidence, adversarial visual QA, and then explicit human acceptance.

## Development Discipline

- Workflow remains the control plane: receipt, lease, write_set, provider live proof, evidence, operator packet, and task-card DB authority remain mandatory.
- Codex/local patches are allowed for complex workflow/control-plane hardening, safety protocols, tests, and documentation wiring.
- The plan/milestone/phase/task-card hierarchy remains intact. This document stops at milestone and phase level.
- Future phases must create DB-backed task cards only after a phase is active; this document does not export future task cards.
- If a phase has only one card later, it must explicitly mark `single_card_exception`.
- Any workflow bug blocks business work until repaired with regression tests.
- Deprecated `commercial_cocos_game` fixed-template delivery remains blocked by `legacy_cocos_template_removed`.

## Next Development Plan

Current completed slices have hardened the false-positive gates, created a baseline-only Cocos product-body shell, added an independent `commercial_game_development_readiness_v1` evidence口径, completed real product-body/runtime, product-depth, machine-evidence, asset, browser, and audio-runtime proof phases, and preserved `commercial_playable_go=false`. The latest active phase `Commercial Asset And Browser Runtime Proof Implementation` materialized exactly three current-phase DB task cards under run `commercial_asset_browser_runtime_20260503`; all three completed through `human_visible_cli_enforced` execution, and the final commercial gate now stops at `AWAITING_HUMAN_REVIEW`.

Phase sequence:

0. Commercial playability repair loop.
   - Treat the user rejection of the launched build as a real `NO-GO`.
   - Replace proof-only browser/runtime surfaces with a player-visible 10x10 block puzzle runtime that can be inspected and played through boot, placement, line clear, candidate refresh, game-over/revive, props, shop, gallery, level, pause, and audio controls.
   - Repair the second-review defects explicitly: BGM must start from real browser audio after user gesture, first-screen and panels must be Chinese, drag preview must follow the pointer without stutter, and board coordinate targeting must align with the visual piece.
   - Use Playwright screenshots and interaction scripts as agent QA evidence only; they cannot set `human_player_review_go=true`.
   - Continue repair until the game is actually usable and visually acceptable, then request/record explicit human acceptance instead of self-approving.

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

6. Asset and browser runtime proof completion.
   - `Commercial Asset And Browser Runtime Proof Implementation` is complete for the current unattended machine-evidence loop.
   - It generated only current-phase DB task cards for non-placeholder asset proof, browser playtest interaction proof, and browser audio/BGM/SFX/volume proof.
   - Machine evidence now passes; the phase is blocked only by the required human review handoff.

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
- Asset graph evidence proves non-placeholder commercial assets.
- Browser playtest evidence proves player-visible interaction and runtime audio controls in the built Cocos output.
- Commercial final gate has reached `AWAITING_HUMAN_REVIEW` after all machine contracts passed, and `commercial_playable_go` stays false until real human acceptance.

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

Slice 5 fills the remaining Post-M109 hardening gaps before commercial content work:

- High-risk commercial `same_project_patch` task cards now require `execution_visibility_mode=human_visible_cli_enforced`; completion is blocked without visible CLI session metadata and mirrored `stdout.log`, `stderr.log`, `stream.jsonl`, and `visible_cli_session.json` evidence.
- Single-agent role outputs now use v2 lossless preservation fields: `source_material_policy=no_delete_no_merge_no_rename_only_augment`, `input_requirement_ids`, `preserved_requirement_ids`, `derived_requirements`, `omitted_requirement_ids`, and `preservation_go`. Any omitted requirement blocks task-card quality/execution.
- Unified intake defaults to raw-input preservation with source hash receipts and source/chunk/media count consistency checks.
- Commercial `recompile_run` is guarded against replacing active `commercial_game_production` DB task cards generated by `task_card_generation_agent` with generic ready cards.
- The Cocos product-body baseline now contains runtime model code for `BoardModel`, `PieceModel`, `RuleEngine`, `CandidateTray`, and `SemanticTestBridge`, including 10x10 board placement, line clear, candidate refresh, game-over, and anti-stall model-transition traces. It remains `baseline_only=true` and cannot satisfy commercial final GO.
- QA and supervisor outputs default to red-team blocking findings and forced NO-GO rules for baseline-only, runtime-hook, canvas-only, event-only, feature-flag-only, missing fresh CLI, missing visible CLI, and requirement omission evidence chains.
- `Commercial Game Core Content Implementation` is now defined as the next post-push active phase and materializes exactly three current-phase DB task cards: core loop/levels, shop-skin-gallery, and audio-feedback-polish.

Slice 6 completes the machine-evidence narrowing pass:

- Added active-phase-only task-card materialization for `Commercial Machine Evidence And Player Visible Completion`.
- Generated exactly three DB task cards for run `commercial_machine_evidence_20260503`: product-depth Chinese UI evidence, build/browser machine evidence, and human-review packet gate.
- All three cards completed through visible CLI worker execution with fresh receipts, child runs/attempts, changed files, mirrored logs, and visible session metadata.
- Product-body, gameplay semantic, product-depth, and Cocos build evidence are now GO; `commercial_game_development_readiness_go=true` remains unchanged.
- The final gate honestly remained `NO-GO` after this slice: `machine_evidence_go=false`, `human_player_review_go=false`, and `commercial_playable_go=false`.
- Those blockers were narrowed to `placeholder_assets_only`, `browser_playtest_no_go`, `audio_runtime_not_verified`, `bgm_runtime_not_verified`, `sfx_runtime_not_verified`, and `volume_toggle_missing`.
- The follow-up active phase was `Commercial Asset And Browser Runtime Proof Implementation`; it generated only current-phase DB cards and did not downgrade missing browser/audio evidence into success.

Slice 7 completes the asset/browser/audio machine-evidence loop:

- Added active-phase-only task-card materialization for `Commercial Asset And Browser Runtime Proof Implementation`.
- Generated exactly three DB task cards for run `commercial_asset_browser_runtime_20260503`: non-placeholder asset graph proof, browser interaction runtime proof, and browser audio/BGM/SFX/volume runtime proof.
- All three cards completed through `human_visible_cli_enforced` execution with fresh receipts, child runs/attempts, changed files, mirrored logs, visible session metadata, and passing targeted tests.
- Fixed binary asset snapshot handling in repo mutation so PNG/MP3 assets can be snapshotted/restored without UTF-8 decode failures.
- Real Cocos Web Mobile builds now install a model-backed browser runtime bridge after build; browser playtest verifies HTTP launch, mobile/desktop screenshots, drag placement, button interactions, game-over/revive evidence, generated asset bindings, and audio/BGM/SFX/volume state without console/page errors.
- Fixed commercial final validation so machine-ready unattended output becomes `AWAITING_HUMAN_REVIEW` instead of requiring `commercial_playable_go=true`.
- Current final state is `machine_evidence_go=true`, `human_player_review_go=false`, and `commercial_playable_go=false`; the only remaining blocker is `awaiting_human_player_review`.

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
