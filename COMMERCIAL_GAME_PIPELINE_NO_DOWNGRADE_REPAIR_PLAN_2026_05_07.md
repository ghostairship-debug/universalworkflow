# Commercial Game Pipeline No-Downgrade Repair Plan

Date: 2026-05-07

This plan supersedes any optimistic interpretation of the latest PDF-only regeneration. The latest run proved that the control plane has several useful contracts, but the actual commercial game production path still downgraded core design, Cocos integration, and QA responsibilities. The next repair phase must fix the pipeline before another commercial game run can be treated as meaningful evidence.

## Current Truth

- Latest reviewed run: `pdf_only_commercial_game_20260507`.
- Source of truth used by that run: `C:\Users\74755\Desktop\俄罗斯方块消除策划文档4.2.pdf`.
- Generated project: `D:\PDF_Game_Workflow_Run_20260507_0832\cocos_project`.
- Pipeline result: `failed`, `stop_reason=commercial_game_no_degradation_failed`.
- Human/user review result: `NO-GO`; visual quality is worse than the previous manually repaired version.
- `commercial_playable_go=false` remains mandatory.
- `commercial_passed=true` from browser playtest is not accepted as commercial evidence for this run because it was event/feature-coverage driven and contradicted by screenshots.

## Implementation Progress

2026-05-08 diagnostic/repair-loop closure adds the missing same-project repair controls discovered after repeated failed reruns:

- Root cause confirmed: `repair_loop=true` produced supervisor repair packets, but final gate and artifact-contract failures were not sufficient by themselves to force same-project product repair. Repeated fresh `D:\WorkflowCommercialGameFresh_*` directories masked the broken feedback loop instead of repairing the current project.
- Prior `completed` task-card ledger entries are no longer trusted blindly. Before a completed same-project card can be reused, the worker now revalidates its current expected artifacts, referenced scene files, launch-scene binding, and runtime component binding contract. If the artifact contract is no longer valid, the prior entry is marked invalid and the same task card is rerun in the same project with fresh receipt/visible CLI evidence.
- Cocos same-project reuse now has a source guard. `workflow_project_source.json` records `source_sha256`; an existing project directory can only be reused for the same source identity. A non-empty unmanaged output directory blocks as `same_project_unmanaged_project_dir`, and a managed directory from another source blocks as `same_project_source_mismatch`.
- This does not claim the game is now commercially complete. It repairs the control-plane reason the previous loop could run many times without converging: stale evidence and cross-run directory contamination are now blocked before more product work is attempted.

Round 1-3 of this repair plan are now implemented at the control-plane and regression-test layer:

- `GameDesignSpec` can now be built directly from the M109 unified brief requirement matrix while preserving original `req_id` values, raw source hashes, source counts, `QualityRubric`, and `TestOracleSpec`.
- `commercial_game_production` now builds and validates the commercial `GameDesignSpec` before asset-provider execution when a source file is present, and again before the task-card worker mutates a Cocos project.
- Commercial same-project business task cards must now carry `task_card_generation_source=active_phase_execution_blueprint`, `PhaseExecutionBlueprint` schema metadata, `TaskCardCompileReport` metadata, non-empty `covered_requirement_ids`, no missing requirement IDs, and a successful compile report.
- Commercial final validation now treats live role proof and Cocos ecosystem proof as mandatory for `commercial_game_production` completion, without silently forcing remote role-model calls when `--live-agent-roles` was not explicitly requested.
- Browser playtest and evidence contracts now block static canvas hashes, desktop Cocos splash-only evidence, missing desktop runtime start, and `report_only` Cocos bridge evidence without fresh runner metadata.
- Cocos browser playtest defaults are now universal commercial defaults; block-puzzle-specific features such as `10x10`, `threeCandidates`, and `antiStall` remain legacy constants only and are no longer the default oracle for arbitrary game briefs.
- Role-derived `GameDesignSpec` now uses the unified requirement matrix builder instead of re-generating and then patching requirement IDs, so role outputs preserve source hashes and receipt semantics.
- Explicit live-role execution is now timeout-bounded via `WORKFLOW_LIVE_ROLE_TIMEOUT_SECONDS`; a stuck provider call blocks as `live_llm_call_timeout` instead of silently hanging the commercial design path.
- Active phase task-card persistence now writes reviewable `PhaseExecutionBlueprint` and `TaskCardCompileReport` artifacts and links their paths back into each DB task card metadata entry.
- AI surrogate quality now requires visual review evidence with screenshot review and `visual_quality_score>=85`, plus audio review evidence for BGM, SFX, and mix. High area scores alone can no longer pass the AI production vertical-slice gate.
- Verification passed: targeted commercial/game/AI suite `191 passed`, active truth `GO`, document links `passed`, and `workflowctl test matrix --suite full` completed with `192 passed, 137 skipped`.

Remaining repair work before a fresh commercial re-run can be trusted:

- No further code-level repair item is currently known from this plan after the 2026-05-08 same-project repair-loop closure. The next meaningful validation is a fresh `commercial_game_production` run from a real source brief/PDF into one explicitly chosen project directory, followed by same-project repair cards if any gate fails. It must not restart by creating a sequence of new output directories.

## Root Cause Summary

The problem is not one bad game build. The problem is that the new universal game pipeline architecture was only partially connected to the real production path.

| Planned contract | Actual evidence from the latest run | Downgrade |
| --- | --- | --- |
| Strong product/design agents produce gameplay, UI, asset, QA, and supervisor judgment | All role outputs used `deterministic_offline_role_builder`; `llm_call_status=not_called_by_default`; `derived_requirements=[]` | Product design was rules-only, not strong-agent driven |
| `GameDesignSpec` is the mandatory product semantic source | Pipeline still primarily consumed unified brief / requirement matrix and fixed commercial cards | Game-specific semantic IR was not the enforced production source |
| Agent-generated `ProductPhaseCandidate` and active `PhaseExecutionBlueprint` drive task cards | Real run used fixed commercial cards such as gameplay levels, shop/skin, audio runtime, scene prefab UI | Blueprint layer existed as code but did not govern the run |
| Cocos scene/prefab/component evidence is required | Ecosystem bridge lacked AssetDB import/query, scene save, node component binding, and prefab instantiate evidence | Engine-native product work fell back to script-drawn runtime UI |
| Generated assets are art-directed and integrated into UX | MMX assets were generated, then needed manual runtime binding; final image composition was poor | Asset generation was artifact-level, not art-direction-to-gameplay integration |
| AI surrogate playtest replaces shallow machine checks | Browser playtest accepted feature flags/events; desktop screenshot stayed on Cocos splash; screenshots were visually poor | QA was event coverage, not player-quality evaluation |
| QA and supervisor red-team failures produce repair loops | QA/supervisor were deterministic outputs and did not catch visual or usability failure before handoff | Red-team layer was effectively inactive |

## Non-Negotiable Repair Principles

1. No commercial implementation card may complete from event-only, canvas-only, feature-flag-only, screenshot-file-only, or script-only evidence.
2. A commercial run must fail fast if the strong planning/design/QA agent path is unavailable. It may not silently fall back to deterministic role output for high-risk commercial work.
3. `GameDesignSpec`, `QualityRubric`, and `TestOracleSpec` must be generated, persisted, and consumed by downstream task-card compilation.
4. Only the active phase may materialize DB task cards; those cards must be compiled from the active `PhaseExecutionBlueprint`.
5. Cocos product work must prove Editor/AssetDB/Scene/Prefab/Component operations when the run claims engine-native commercial output.
6. AI surrogate playtest must inspect player-visible output, including screenshots/video/audio/runtime state, and must be allowed to issue NO-GO even when scripted events pass.
7. Machine evidence may only reach `AWAITING_HUMAN_REVIEW`; unattended workflow must never set `commercial_playable_go=true`.

## Repair Milestones

### Milestone 1: Truth Reset And Documentation Ratchet

Goal: prevent the latest weak run from being interpreted as a successful commercial pipeline proof.

Required changes:

- Record `pdf_only_commercial_game_20260507` as a product-quality NO-GO.
- Mark `commercial_passed=true` from that run as a false positive when used for commercial readiness.
- Update active-truth docs so they distinguish:
  - control-plane interface implemented,
  - production path actually enforced,
  - current game quality accepted by human review.
- Add a regression note that desktop Cocos splash screenshots and identical canvas hashes cannot pass commercial playtest.

Exit criteria:

- README and current workflow docs no longer imply the 2026-05-07 rerun is machine-commercial-ready.
- Active truth names this plan as the next repair sequence.

### Milestone 2: Mandatory GameDesignSpec Production Path

Goal: make `GameDesignSpec` the enforced semantic source for real game production.

Required changes:

- `commercial_game_production` must call the universal design IR path for any source input before task-card generation.
- Persist these artifacts under the run evidence root:
  - raw source receipt and hash,
  - `GameDesignSpec`,
  - `QualityRubric`,
  - `TestOracleSpec`,
  - source requirement matrix,
  - spec validation report.
- If `GameDesignSpec` validation fails, block the pipeline before asset generation or Cocos bootstrap.
- Downstream cards must cite `design_spec_id`, `covered_requirement_ids`, and oracle/rubric references.

Exit criteria:

- A commercial run without a valid `GameDesignSpec` cannot create implementation task cards.
- Tests prove missing or invalid spec blocks the run.

### Milestone 3: No-Downgrade Strong Agent Planning

Goal: stop high-risk commercial work from falling back to deterministic role output.

Required changes:

- Add `commercial_high_risk_requires_live_design=true` or equivalent policy for commercial game runs.
- Keep deterministic role output only for lossless preservation and raw requirement indexing.
- Require strong agent output for:
  - product design review,
  - UI/UX art direction,
  - active phase architecture,
  - QA red-team,
  - supervisor decision.
- Preserve the single-agent no-delete/no-merge/no-rename contract:
  - live agents may add `derived_requirements` and `derived_review_notes`,
  - live agents may not replace or shrink preserved requirements.
- If live/strong agent configuration is missing, the run must block with a clear failure class instead of continuing.

Exit criteria:

- A run with `live_agent_roles=false` cannot be used for commercial production completion.
- Role evidence records provider, model, visible CLI/session evidence, and derived-only contract.

### Milestone 4: Active Phase Blueprint As The Only Task-Card Compiler Input

Goal: eliminate fixed commercial repair-card templates from the main production path.

Required changes:

- Generate `ProductPhaseCandidate` from `GameDesignSpec`.
- Let workflow rules compile phase order/dependencies into the plan graph.
- Activate exactly one phase.
- Generate a `PhaseExecutionBlueprint` for that active phase with:
  - module slices,
  - runtime model boundaries,
  - scene/prefab/component binding plan,
  - asset and audio integration plan,
  - test commands,
  - evidence requirements,
  - risk and blocking conditions.
- Compile DB task cards only from that blueprint.
- Record `TaskCardCompileReport` and block on uncovered implementation requirements, missing tests, missing write/read sets, or generic cards.

Exit criteria:

- Fixed cards such as `commercial_scene_prefab_ui` are not used unless they are generated from the active blueprint with spec references.
- Compile/recompile still cannot overwrite active commercial cards.

### Milestone 5: Engine-Native Cocos Product Body

Goal: require real Cocos production evidence instead of script-only rendering.

Required changes:

- Cocos bootstrap may create only an empty shell and generic runtime slots.
- Product implementation must create or modify Cocos assets through the verified engine path:
  - AssetDB import/query,
  - scene create/save/open,
  - node/component binding,
  - prefab creation/instantiation,
  - build API evidence.
- Runtime evidence must show product model transitions and component bindings, not browser hooks.
- Any `report_only` bridge mode in a commercial completion path must block rather than downgrade.

Exit criteria:

- Missing AssetDB/Scene/Prefab/Component evidence blocks product-body GO.
- Script-only UI can be kept as diagnostic evidence but cannot satisfy commercial product-body completion.

### Milestone 6: Asset Direction And Runtime Integration

Goal: move from "assets exist" to "assets are commercially integrated".

Required changes:

- Generate an `AssetStyleBible` from the source and design spec.
- Generate asset prompts from art direction, not fixed slots.
- Require QA on generated assets:
  - size,
  - composition,
  - text-free where required,
  - consistency,
  - safe playfield area,
  - no UI obstruction,
  - no unwanted duplicate gameplay boards inside background images.
- Require Cocos integration proof:
  - asset imported through AssetDB,
  - bound to scene/prefab/component,
  - visible in screenshot,
  - before/after visual comparison,
  - no layout degradation.

Exit criteria:

- `generatedArtAssets=true` is set only after visual integration passes.
- Loading an asset at runtime is not enough to satisfy asset quality.

### Milestone 7: AI Surrogate Playtest And Visual Red-Team Gate

Goal: replace false-positive event checks with high-intensity player-quality evaluation.

Required checks:

- Mobile and desktop screenshots must show the game, not Cocos splash.
- Initial and after-action screenshots/canvas hashes must demonstrate real state change.
- OCR/vision checks must flag tiny text, overlap, unreadable Chinese UI, excessive empty space, and controls outside comfortable touch zones.
- Drag/gesture checks must measure pointer offset and frame-to-frame follow latency.
- Audio checks must verify BGM/SFX/voice playback where required.
- Commercial visual score must evaluate:
  - composition,
  - art/UI consistency,
  - polish,
  - readability,
  - playfield clarity,
  - player feedback.
- Red-team must output blocking findings first, not pass lists.

Exit criteria:

- A visually poor game cannot report `commercial_passed=true`.
- Desktop splash, identical canvas hash, or screenshot mismatch is a blocking failure.

### Milestone 8: Repair Loop Integration

Goal: make QA findings automatically become scoped repair work.

Required changes:

- AI NO-GO findings create DB repair task cards for the same active phase.
- Repair cards inherit:
  - spec requirement ids,
  - screenshot evidence,
  - failing oracle checks,
  - exact write/read sets,
  - targeted tests.
- The repair loop must rerun Cocos build, browser/device playtest, AI visual review, and final gate.
- Repeated failure should trigger task splitting or pipeline bug-first repair, not infinite same-card retries.

Exit criteria:

- Every AI NO-GO has a repair packet or a recorded workflow blocker.
- No human-review packet is prepared while machine visual QA is still NO-GO.

### Milestone 9: Full Commercial Re-Run

Goal: rerun from the desktop PDF only after the no-downgrade chain is enforced.

Required run shape:

```text
Raw source PDF
  -> lossless intake
  -> GameDesignSpec / QualityRubric / TestOracleSpec
  -> ProductPhaseCandidate
  -> workflow plan-graph / policy-preview / goal-packet
  -> activate current phase
  -> live strong-agent PhaseExecutionBlueprint
  -> workflow TaskCardCompileReport
  -> DB task cards
  -> human_visible_cli_enforced provider execution
  -> Cocos native asset/scene/prefab/component evidence
  -> build/package
  -> AI surrogate playtest and visual red-team
  -> repair loop
  -> AWAITING_HUMAN_REVIEW
```

Exit criteria:

- `machine_evidence_go=true` only if all machine and AI visual gates pass.
- `human_player_review_go=false` until the user explicitly accepts.
- `commercial_playable_go=false` until both machine evidence and explicit human acceptance are true.

## Required Tests

Targeted tests to add or strengthen:

- `tests/test_game_design_ir.py`
  - commercial pipeline cannot continue without valid `GameDesignSpec`.
  - `QualityRubric` and `TestOracleSpec` are present and source-linked.
- `tests/test_game_task_card_generation.py`
  - task cards must come from active `PhaseExecutionBlueprint`.
  - fixed generic commercial cards are rejected unless compiled from blueprint.
- `tests/test_commercial_game_evidence_contracts.py`
  - deterministic-only role output blocks commercial implementation.
  - missing Cocos AssetDB/Scene/Prefab/Component evidence blocks product-body GO.
  - event-only, feature-flag-only, canvas-only, screenshot-file-only evidence blocks commercial pass.
- `tests/test_cocos_e2e.py`
  - desktop splash screenshot blocks playtest.
  - unchanged canvas/screenshot hashes block commercial pass.
  - generated asset visible integration must be proven, not just loaded.
- `tests/test_pipeline_and_automation_cli.py`
  - `commercial_game_production` with high-risk commercial mode blocks if live/strong role proof is missing.
  - `TaskCardCompileReport` is required before worker execution.
- AI/vision regression tests:
  - tiny Chinese UI text,
  - UI overlap,
  - bad mobile touch zones,
  - background obstructing playfield,
  - drag pointer offset,
  - visual quality score below threshold.

Required gates:

```powershell
python -m compileall -q apps packages tests
python -m pytest tests/test_game_design_ir.py tests/test_game_task_card_generation.py tests/test_commercial_game_evidence_contracts.py tests/test_cocos_e2e.py tests/test_pipeline_and_automation_cli.py -q
python -m infra.scripts.check_doc_links
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" governance active-truth-check --strict --output-path state/governance/active_truth_check.json
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite full
git diff --check
```

## Completion Definition

This repair plan is complete only when a fresh commercial game run cannot reproduce the 2026-05-07 downgrade pattern.

Passing control-plane tests is not enough. The repaired pipeline must demonstrate, on a fresh source-driven run, that:

- strong planning/QA agents were actually called or the run blocked,
- `GameDesignSpec` governed task-card generation,
- active `PhaseExecutionBlueprint` governed DB cards,
- Cocos engine-native evidence was present,
- assets were art-directed and visually integrated,
- AI surrogate playtest rejected low-quality output,
- final state stopped at `AWAITING_HUMAN_REVIEW` until human acceptance.
