# Universal Game Production And AI Playtest Upgrade Plan

> Date: 2026-05-03
> Scope: redesign `commercial_game_production` so arbitrary game design briefs can reach a high implementation baseline through workflow execution and high-intensity AI surrogate playtesting.
> Non-goal: do not optimize only for the current 10x10 block-puzzle sample. That sample is a failed pilot and a regression fixture, not the target product category.

## Current Diagnosis

The latest block-puzzle repair improved the visible result, but it proved the wrong thing:

- The final repair was mainly a Codex/local emergency patch, not a workflow-generated product slice.
- The result is still a playable prototype/vertical-slice fragment, not a commercial-grade game.
- The workflow currently proves too many proxy facts: feature flags, events, screenshots, canvas presence, and runtime hooks.
- It does not yet prove that it can repeatedly turn an arbitrary design brief into a polished game across different genres.
- The previous minimum bar was too low. "10x10, 3 candidates, placement, clear, refresh, failure, revive" is only a design-specific checklist for one puzzle test case, not a universal game-production baseline.

The next design goal is therefore:

> For any supported game design brief, workflow must preserve the full source requirements, derive an engine-native implementation plan, produce a playable build through task-card workers, and run high-intensity AI surrogate playtests until the AI quality gate passes.

## New Quality Target

The minimum implementation baseline must be much higher than the current repaired sample. A future workflow-generated game cannot pass by being merely "playable." It must pass a `production_vertical_slice_floor`:

- Core loop is fully playable from boot to failure/retry/progression.
- All design-specific player verbs are implemented, not stubbed.
- The first-session experience is coherent: start, onboarding, first objective, success, failure, reward, next action.
- UI is localized according to the brief and visually organized for the target platform.
- Art direction is consistent: no raw placeholder look, no unstyled panels, no generic debug UI.
- Audio includes BGM/SFX/feedback rules with runtime playback and volume state.
- Input feels correct for target device: pointer/touch/gamepad/keyboard mapping, cancellation, invalid action feedback, and latency budget.
- Progression, economy, unlocks, levels, inventory, narrative, or other genre-relevant systems are functional when required by the brief.
- Save/load and session continuity work for all persistent systems.
- Build launches through the target delivery path and records reproducible evidence.
- AI surrogate playtest score reaches the configured threshold with no blocking P0/P1 findings.

This floor is genre-agnostic. For a platformer it means movement, collision, camera, checkpoints, enemies, fail/retry, and feel. For a card game it means rules, deck state, turn flow, opponent behavior, UI readability, and pacing. For a narrative game it means dialogue state, choice consequences, scene transitions, save/load, and content coverage.

## Architecture Direction

### 1. Game-Agnostic Design IR

Add a normalized game design intermediate representation before task-card generation:

- `GameDesignSpec`: raw source preservation, source hashes, sections, requirement ids.
- `GenreModel`: genre, camera/view, target platform, session length, input model, engine constraints.
- `MechanicGraph`: verbs, rules, resources, win/fail states, progression dependencies.
- `StateModelContract`: authoritative runtime state, transitions, invariants, save/load fields.
- `InteractionMap`: input gestures, hit targets, cancellation, invalid feedback, accessibility actions.
- `UIFlowGraph`: screens, HUD, menus, modals, empty/error/loading states, localization.
- `ContentMatrix`: levels, stages, enemies, cards, items, quests, dialogue, rewards, tuning rows.
- `AssetStyleBible`: visual direction, palette, typography, effects, animation tone, asset list.
- `AudioDesignSheet`: BGM loops, SFX events, mix rules, mute/volume, failure and reward cues.
- `QualityRubric`: genre-specific and universal scoring rubric used by AI playtest agents.
- `TestOracleSpec`: scripted scenarios, state assertions, screenshot expectations, performance budgets.

The IR must be lossless with respect to source requirements. Derived requirements are allowed only as explicitly marked engineering additions.

### 2. Workflow-Generated Product, Not Codex Rescue

The next pipeline must prove that workflow can reproduce and exceed the Codex rescue level:

- All product implementation must go through DB task cards unless the task is explicitly workflow/control-plane repair.
- Task cards must cite `req_id`s from `GameDesignSpec` and downstream `TestOracleSpec`.
- High-risk implementation cards still require `human_visible_cli_enforced` or an equivalent visible execution contract.
- Codex/local patches may repair workflow bugs, tests, docs, and emergency diagnostics, but cannot count as the main product-generation proof.
- The final evidence must distinguish `workflow_generated_product_go` from `codex_local_patch_repair_go`.

### 3. Engine-Native Runtime Contract

For Cocos and any future engine adapter, commercial product evidence must come from engine-native code and assets:

- Gameplay model lives in project runtime code, not browser overlay patches.
- View/controller/audio/shop/level/UI components are scene/prefab/component bound.
- Semantic traces come from runtime model transitions.
- Browser bridge evidence is allowed as inspection support only, not as the product body.
- Engine adapter contracts must expose build, launch, screenshot, input, performance, asset graph, and component binding evidence.

### 4. AI Surrogate Playtest Lab

Create a high-intensity AI testing layer that substitutes for much of manual QA while keeping the distinction between AI acceptance and human acceptance clear.

AI playtest modes:

- `scripted_bot`: deterministic scenario scripts generated from `TestOracleSpec`.
- `exploratory_bot`: random and goal-directed input exploration with replay capture.
- `persona_agent`: novice, expert, impatient player, completionist, monetization-sensitive player, accessibility-sensitive player.
- `vision_reviewer`: screenshot/video review for visual polish, overlap, readability, art coherence, and UI hierarchy.
- `design_red_team`: checks whether the implemented experience matches the brief, not only whether it runs.
- `performance_agent`: frame pacing, input latency, load time, memory, long-session soak.
- `device_matrix_agent`: desktop, mobile portrait/landscape, touch, mouse, scaled viewports, low-performance mode, and connected real devices when available.
- `regression_agent`: replays prior bug paths and ensures repaired defects stay fixed.

AI can set `ai_surrogate_playtest_go=true` only when the AI gate passes. It must not silently set `human_player_review_go=true` unless the project explicitly changes governance to accept AI as a delegated reviewer. For current governance, AI pass means "ready for human review or next production phase," not "commercial playable accepted."

### 5. Product Quality Scorecard

Replace binary feature coverage with a weighted quality report:

| Area | Minimum |
| --- | --- |
| Requirement fidelity | All must requirements preserved and implemented or explicitly blocked |
| Core gameplay correctness | Rules, state transitions, fail/retry, progression, and edge cases pass |
| Player experience | First-session flow, feedback, clarity, pacing, and learnability pass |
| UI/UX polish | Layout, hierarchy, localization, readability, mobile/desktop adaptation pass |
| Art direction | Coherent style, non-placeholder assets, animations/effects pass |
| Audio | BGM/SFX runtime, mix, trigger timing, volume/mute pass |
| Input feel | Latency, hit targets, cancellation, invalid feedback, device mapping pass |
| Content depth | Genre-specific content matrix has meaningful playable coverage |
| Performance | Build, load, frame pacing, memory, and error logs pass |
| Robustness | Save/load, restart, long-session, fuzz, and regression tests pass |

Suggested gate:

- `ai_quality_score >= 85`
- No P0/P1 findings
- No unresolved must-requirement omissions
- No placeholder-only art/audio/content for required production surfaces
- No runtime-hook/canvas-overlay product-body substitute
- No build/playtest evidence reuse from old runs

### 6. Defect-To-Repair Loop

AI testing must create actionable repair input instead of only pass/fail summaries:

1. Capture replay, screenshot, video, console/page errors, state snapshot, and requirement ids.
2. Classify finding: correctness, UX, visual, audio, performance, content, economy, localization, device, accessibility.
3. Assign severity and owner role.
4. Generate minimal DB task card with write_set/read_set/test/evidence.
5. Execute through workflow worker.
6. Re-run only affected scenario first, then full AI gate.
7. Preserve regression replay for future phases.

## Next Active Phase Proposal

Phase name:

`Universal Game Production Quality And AI Playtest Architecture`

Goal:

Build the workflow control-plane and evidence contracts that make arbitrary game production measurable above the current block-puzzle repair level.

Phase boundaries:

- Do not create M110.
- Do not generate future phase task cards.
- Do not start a new commercial game content implementation until the generic game-quality architecture is in place.
- Treat the current block-puzzle repair as a regression fixture and minimum failure example, not as the universal target.

### Phase 1: Universal Game Design IR

Deliverables:

- Schema for `GameDesignSpec`, `MechanicGraph`, `UIFlowGraph`, `ContentMatrix`, `AssetStyleBible`, `AudioDesignSheet`, `QualityRubric`, and `TestOracleSpec`.
- Lossless intake tests: source requirements cannot be deleted, merged, renamed, or rewritten.
- Genre-neutral requirement categories and acceptance methods.
- Sample conversion from the current block-puzzle source into the generic IR to prove it no longer hardcodes 10x10 assumptions.

Exit criteria:

- Any game brief can be converted into a requirement-preserving IR.
- Design-specific items such as "10x10 board" remain requirements only for that brief.

### Phase 2: Quality Floor And Gate Contract

Deliverables:

- `production_vertical_slice_floor_v1` quality contract.
- `ai_surrogate_playtest_go` evidence schema.
- Weighted `ai_quality_score` report.
- Gate negatives for low-quality but feature-complete builds.
- Regression fixture proving the old proof-like runtime/canvas/event-only pattern fails.

Exit criteria:

- A build with only feature flags and screenshots cannot pass.
- A build below the current v3 repair quality cannot pass.
- A build at current v3 quality can pass only as `prototype_floor_go`, not `production_vertical_slice_go`.

### Phase 3: AI Playtest Lab MVP

Deliverables:

- Scenario runner for scripted playtests generated from `TestOracleSpec`.
- Screenshot/video capture for key states.
- Vision-review packet for layout, visual polish, text fit, and obstruction checks.
- Input-latency and drag/control-feel measurement hooks.
- Persona-agent review packet with structured findings.
- Replay artifact format for reproducible bug paths.

Exit criteria:

- AI playtest can produce blocking findings with evidence, not only a pass list.
- Findings can be converted into DB task cards.

### Phase 4: Workflow Product Worker Proof

Deliverables:

- DB task-card generation from `GameDesignSpec` and `TestOracleSpec`.
- Current-phase-only task cards for one small game slice.
- Worker execution with fresh receipt, visible CLI, changed files, tests, screenshots, and replay evidence.
- Explicit distinction between workflow-generated product changes and Codex/local fallback changes.

Exit criteria:

- Workflow, not Codex rescue, produces a playable slice that meets at least the current v3 floor.
- Evidence proves source requirement coverage, implementation, AI playtest, and repair loop.

### Phase 5: Generality Pilot

Deliverables:

- Run the upgraded workflow on two different sample briefs:
  - the current block puzzle as a regression fixture.
  - a non-puzzle design such as a small platformer, card battler, runner, narrative choice scene, or arcade action prototype.
- Compare both against the same generic quality floor plus genre-specific rubrics.

Exit criteria:

- The workflow does not hardcode block-puzzle assumptions.
- Both pilots produce AI playtest reports, defect loops, and measurable quality scores.

### Round 6: Pre-Commercial Gate Hardening

Implemented hardening before new commercial content work:

- `commercial_fast` and `full` test matrix suites now include the universal game IR, engine-native product-body, AI playtest quality, execution packet, repair loop, task-card generation, CLI, and generality pilot tests.
- `commercial_game_production` now treats AI surrogate playtest evidence as a default commercial machine gate when upstream implementation evidence is otherwise complete. Missing or failing AI surrogate evidence blocks machine readiness instead of allowing a proof-only handoff.
- AI execution reports can be converted directly into repair task cards through `workflowctl game ai-repair-loop`. The command extracts validation blockers, AI quality blockers, and P0/P1 findings, writes DB task cards, materializes per-card worker Markdown, and emits `workflowctl run from-task-card ... --execute` worker loop entries with `human_visible_cli_enforced` for P0/P1 repairs.

### Round 7: Runner And Task-Card Granularity Hardening

Additional pre-commercial optimization:

- Adds `workflowctl game ai-playtest-run`, a browser-backed AI playtest runner entry that can serve a static build or hit a target URL, collect fresh screenshots/replays/state snapshots, and produce an execution packet plus quality report. The runner remains conservative: browser smoke evidence alone cannot set core-loop, polish, or requirement-fidelity GO without explicit AI/reviewer quality judgments.
- Adds `commercial_full` and `commercial_full_with_browser` matrix suites. `commercial_full` combines commercial fast contracts, pipeline/automation integration, and provider contract tests without the slow Cocos browser target; `commercial_full_with_browser` also includes the slow browser/Cocos suite.
- Splits universal game-production task cards by source requirement category. High-risk runtime, UI, art, audio, progression/economy/content, and performance/device/input cards are generated only when the brief requires them, each with requirement ids, visible CLI, tests, evidence, and blockers. This avoids collapsing arbitrary game work into one broad "UI/art/audio/content" card.

### Round 8: Derived-Only Semantic Enrichment

Additional source-preservation hardening:

- Adds derived-only GameDesignSpec enrichment. AI/LLM stages may add `derived_requirements`, genre-specific rubric checks, test oracle scenarios, state assertions, screenshot expectations, performance budgets, device entries, input models, target platforms, or engine constraints.
- Enrichment cannot replace `requirements`, cannot change `input_requirement_ids`, cannot change `preserved_requirement_ids`, and cannot add `omitted_requirement_ids`.
- Adds `workflowctl game design-ir-enrich` so semantic enrichment is a workflow-visible command rather than a chat-only convention.

## Required Tests

Minimum targeted tests for the next phase:

- `tests/test_m109_unified_brief.py`: lossless source preservation remains enforced.
- `tests/test_task_card_store.py`: implementation cards require req coverage and quality fields.
- `tests/test_pipeline_and_automation_cli.py`: active phase cannot be polluted by compile/recompile.
- New tests:
  - `tests/test_game_design_ir.py`
  - `tests/test_ai_playtest_quality_gate.py`
  - `tests/test_game_quality_scorecard.py`
  - `tests/test_game_repair_loop_from_ai_findings.py`
  - `tests/test_engine_native_product_body_contract.py`
  - `tests/test_ai_playtest_execution_packet.py`
  - `tests/test_game_task_card_generation.py`
  - `tests/test_universal_game_cli.py`
  - `tests/test_universal_game_generality_pilot.py`
  - `tests/test_test_matrix.py`

Required gates:

- `python -m compileall -q` for changed Python files.
- `python -m infra.scripts.check_doc_links`.
- `workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" governance active-truth-check --strict --output-path state/governance/active_truth_check.json`.
- `workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite full`.
- `git diff --check`.

## Success Definition

The upgraded workflow is not successful when it produces another block-puzzle prototype. It is successful when:

- It accepts arbitrary game briefs.
- It preserves all source requirements.
- It derives genre-specific implementation and test oracles.
- It generates DB task cards with source coverage.
- It implements through workflow workers.
- It runs high-intensity AI surrogate playtests across scenarios and devices.
- It creates repair cards from AI findings.
- It iterates until `ai_surrogate_playtest_go=true`.
- It keeps `commercial_playable_go=false` unless the governance layer receives explicit accepted human review or an explicit policy change that delegates final acceptance to AI.

## Implementation Progress

### 2026-05-03 Round 1: Contract Layer

Status: completed.

Implemented:

- `packages/contributions/games/game_design_ir.py`
  - Adds `GameDesignSpec`, `MechanicGraph`, `StateModelContract`, `InteractionMap`, `UIFlowGraph`, `ContentMatrix`, `AssetStyleBible`, `AudioDesignSheet`, `QualityRubric`, and `TestOracleSpec`.
  - Enforces `source_material_policy=no_delete_no_merge_no_rename_only_augment`.
  - Preserves every input requirement id and blocks omitted requirements.
  - Keeps design-specific requirements such as "10x10 board" inside that brief's requirement list instead of promoting them to the universal genre baseline.

- `packages/contributions/games/engine_native_contract.py`
  - Adds an engine-native product-body contract.
  - Rejects `browser_bridge`, `browser_overlay`, `canvas_overlay`, `runtime_hook`, `event_only`, `feature_flag_only`, and `screenshot_only` as product-body substitutes.

- `packages/contributions/games/ai_playtest_quality.py`
  - Adds `production_vertical_slice_floor_v1`.
  - Adds weighted `ai_quality_score`.
  - Requires all AI playtest modes, no P0/P1 findings, replay artifacts, screenshots, requirement fidelity, workflow-generated product proof, and engine-native product body.
  - Keeps AI pass separate from `human_player_review_go` and `commercial_playable_go`.

- `packages/contributions/games/ai_repair_loop.py`
  - Converts AI surrogate findings into DB-compatible repair task cards with write_set/read_set/test/evidence, severity-based risk, requirement coverage, and visible-CLI requirement for P0/P1 defects.

- `packages/contributions/pipelines/commercial_game_evidence_contracts.py`
  - Adds optional `require_ai_surrogate_playtest` final-gate integration.
  - Existing commercial gates remain backward compatible, but next phases can require AI surrogate playtest before human review.

Evaluation:

- Targeted tests passed: `tests/test_game_design_ir.py`, `tests/test_engine_native_product_body_contract.py`, `tests/test_ai_playtest_quality_gate.py`, `tests/test_game_quality_scorecard.py`, `tests/test_game_repair_loop_from_ai_findings.py`, and `tests/test_commercial_game_evidence_contracts.py`.
- The current block-puzzle repair remains a regression fixture and does not become the universal game target.

### 2026-05-03 Round 2: AI Playtest Lab And Workflow Task Cards

Status: completed.

Implemented:

- `packages/contributions/games/ai_playtest_lab.py`
  - Generates AI playtest plans from `TestOracleSpec`.
  - Includes scripted, exploratory, persona, vision, design red-team, performance, device matrix, and regression modes.
  - Requires replay, screenshots, state snapshots, console/page logs, AI findings, and quality scorecards.

- `packages/contributions/games/game_task_card_generation.py`
  - Generates current-phase product task cards from `GameDesignSpec`.
  - Produces cards for engine-native runtime/core loop, player-visible UI/art/audio/content, and AI surrogate playtest/repair.
  - Requires workflow-generated product proof and forbids Codex/local emergency patches from satisfying product proof.
  - Carries source requirement coverage into task-card metadata.

Evaluation:

- Targeted tests passed: `tests/test_ai_playtest_lab.py`, `tests/test_game_task_card_generation.py`, `tests/test_universal_game_generality_pilot.py`, `tests/test_game_design_ir.py`, `tests/test_game_repair_loop_from_ai_findings.py`, and `tests/test_task_card_store.py`.
- Generality pilot test covers both the current block-puzzle fixture and a non-puzzle platformer fixture, proving the contract is no longer hardcoded to 10x10 gameplay.

### 2026-05-03 Round 3: Workflow-Callable CLI Surface

Status: completed.

Implemented:

- `apps/operator_cli/game_commands.py`
  - Adds `workflowctl game universal-design-ir` to convert brief files or inline requirements into `GameDesignSpec` JSON.
  - Adds `workflowctl game ai-playtest-plan` to generate an AI surrogate playtest plan from the design spec.
  - Adds `workflowctl game production-task-cards` to generate current-phase DB-compatible product task cards from `GameDesignSpec`, optionally persist them to `task_cards`, and export a Markdown review snapshot.
  - Adds `workflowctl game ai-quality-gate` to evaluate AI surrogate playtest evidence and block non-passing quality reports.
  - Adds `workflowctl game ai-repair-cards` to convert AI findings into DB-compatible repair task cards, including visible-CLI requirements for P0/P1 defects.

Evaluation:

- Targeted CLI tests passed in `tests/test_universal_game_cli.py`.
- The universal game-production path is now workflow-callable: arbitrary brief input can produce lossless IR, AI test plan, active-phase task cards, AI quality gate output, and repair cards without Codex hand-editing those artifacts.

### 2026-05-03 Round 4: AI Playtest Execution Packet Gate

Status: completed.

Implemented:

- `packages/contributions/games/ai_playtest_execution.py`
  - Adds `universal_ai_playtest_execution_packet_v1`.
  - Validates that all AI playtest modes executed, are fresh, and include replay artifacts, screenshots, state snapshots, console/page error capture, device matrix results, performance metrics, and vision-review output.
  - Validates that `TestOracleSpec`-derived scripted scenarios, state assertions, vision targets, and planned device matrix entries are covered and passing.
  - Can require artifact files to exist on disk, blocking reports that only cite nonexistent screenshots or replays.
  - Converts validated execution packets into `universal_ai_surrogate_playtest_quality_v1` evidence and injects P1 findings when execution evidence is invalid.

- `apps/operator_cli/game_commands.py`
  - Adds `workflowctl game ai-playtest-execution-gate`.
  - The command defaults to artifact-file existence checks and blocks low-fidelity AI evidence before it reaches the production quality gate.

Evaluation:

- Targeted tests passed: `tests/test_ai_playtest_execution_packet.py`, `tests/test_universal_game_cli.py`, and `tests/test_ai_playtest_quality_gate.py`.
- This closes the biggest evidence gap between a hand-written AI quality score and a real AI surrogate playtest packet: replay/screenshot/state/performance/device evidence must now be present and fresh.

### 2026-05-03 Round 5: Commercial Pipeline Materialization Integration

Status: completed.

Implemented:

- `packages/core_domain/role_agent_executor.py`
  - Adds active-phase detection for `Universal Game Production Quality And AI Playtest Architecture`.
  - Materializes only current-phase DB task cards for the universal game-quality phase, split by source requirement category plus AI surrogate playtest quality gate.
  - Builds those cards from a `GameDesignSpec` derived from the source-preserving unified requirement matrix.
  - Preserves source `req_id` coverage, omitted-requirement blocking, visible CLI evidence requirements, and active-phase-only semantics.

Evaluation:

- Targeted tests passed in `tests/test_m109_unified_brief.py` and `tests/test_game_task_card_generation.py`.
- The universal game-quality architecture is no longer only a standalone CLI/library path; it is now reachable from the normal `commercial_game_production` task-card generation agent for the current active phase.

### 2026-05-04 Round 9: PDF-Only Workflow Repair And Gate Ratchet

Status: completed for machine evidence; awaiting explicit human acceptance.

Implemented:

- `commercial_game_pdf_only_20260503`
  - Uses `C:\Users\74755\Desktop\俄罗斯方块消除策划文档4.2.pdf` as the sole product input for the current commercial game repair loop.
  - Executes product repairs through DB task cards and `human_visible_cli_enforced` visible worker sessions.
  - Keeps Codex/local patches scoped to workflow bugs, evidence contracts, tests, hygiene, and documentation.

- `packages/contributions/pipelines/commercial_game_evidence_contracts.py`
  - Browser playtest evidence now blocks when required runtime feature coverage is missing, instead of allowing screenshots/audio to mask absent gameplay hooks.
  - Product-depth evidence now blocks mojibake level-goal labels so Chinese UI readability cannot be silently downgraded.

- Current Cocos evidence under `state/commercial_game_pdf_only_20260503`
  - Latest machine evidence reports `build_ledger.go=true`, `browser_playtest_ledger.go=true`, and `product_depth_evidence.go=true`.
  - Browser playtest feature coverage includes core loop, level flow, shop/skin/gallery, BGM/SFX/volume, Chinese UI, drag preview, coordinate alignment, revive/failure feedback, and panel interactions.
  - Stale legacy evidence from `state/pipeline_runs/commercial_game_core_content_20260503` is no longer treated as the active truth source.

Evaluation:

- The PDF-only workflow run now exceeds the earlier local emergency patch as a machine-evidence artifact because the product repairs came through workflow task cards and the evidence gates were ratcheted during the loop.
- This is still not a final commercial playable acceptance: `human_player_review_go=false` and `commercial_playable_go=false` remain correct until a human reviewer explicitly accepts the launched build.
