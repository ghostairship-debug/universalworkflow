# Commercial Game Pipeline Evaluation - 2026-04-28

## Scope

This report closes the 2026-04-28 unattended commercial-game pipeline repair and evaluation window. It covers workflow bug-first repairs, `commercial_game_production` pipeline evaluation, hygiene cleanup, and the final real-game pipeline attempt.

It does not claim a shipped commercial playable game. The final gate remains `commercial_playable_go=false` until real build, browser playtest, screenshots, player-visible QA, and asset evidence all pass.

## Bug-First Repairs

| Area | Result | Evidence |
| --- | --- | --- |
| Default repo-mutation route | `from-task-card` patch apply now defaults to Codex CLI enforcement, not OpenCode. OpenCode stays a simple-lane adapter. | `tests/test_cli.py::test_cli_from_task_card_defaults_patch_apply_to_codex`, `tests/test_execution_loop.py::test_compile_run_defaults_patch_apply_to_codex_adapter` |
| Receipt gate and propagation | Missing or mismatched receipts fail fast before repo mutation; parent receipt ids propagate into orchestration child runs. | `tests/test_execution_loop.py` patch-apply receipt regression set |
| Adapter watchdog evidence | Codex/OpenCode timeout and nonzero exits record timeout type, `failure_class`, stream counts, last-output age, stdout/stderr previews, mutation-result context, and recovery guidance. | `tests/test_m41_capabilities.py` |
| Repo mutation evidence | Patch proposals receive bounded read-set excerpts, inaccurate hunk locations can be recovered safely, and failed apply restore preserves LF newlines. | `tests/test_m77_provider_access.py`, `tests/test_repo_mutation_atomicity.py` |
| Worker heartbeat and scheduler release | Local worker execution renews heartbeat state, terminal/human-review runs release scheduler leases, stale leases are repairable, and old expired-authority findings were reconciled. | `tests/test_execution_loop.py`, `state/long_runs/scheduler_lease_fix_cli_probe_20260428`, `state/long_runs/scheduler_lease_repair_existing_runs_20260428` |
| Pipeline heartbeat | Pipeline runs write heartbeat JSONL evidence and terminal heartbeat records. | `state/long_runs/commercial_pipeline_eval_20260428_053221/evidence/pipeline_c0eefb308826.heartbeat.jsonl` |
| Remote callback idempotency | Duplicate remote completion callbacks remain accepted after terminal scheduler release. | `tests/test_remote_worker_api.py::test_remote_worker_completion_callback_is_idempotent` |
| Adapter/stage failure capture | Agent/capability/validation executor exceptions become structured stage-failure evidence. | `tests/test_pipeline_and_automation_cli.py` |
| MiniMax prompt budget | Commercial asset prompts are capped below provider prompt limits while preserving asset-specific instructions. | `tests/test_asset_factory.py` |
| SFX modality and QA | Short game SFX is split from speech/TTS; `procedural_sfx_local` WAV assets carry sha256, duration, RMS/peak, non-silent, clipping, provenance, and QA-gate metadata. | `run_288e9dc2562b`, `run_3776bc6a71f5`, `tests/test_asset_factory.py` |
| Cocos audio binding | Commercial Cocos manifests and runtime bindings preserve `sfx`, `voice`, and `music` modalities through resource binding and audio hooks. | `run_c064ab735768`, `run_8ed8421da0f4`, `tests/test_cocos_e2e.py` |
| Asset failure classification | Provider quota/usage, provider response, missing output, missing source, and missing Cocos Creator are classified into recoverable or operator-input blockers. | `tests/test_cocos_e2e.py`, `tests/test_m109_unified_brief.py` |
| Legacy guard | `commercial_cocos_game` blocks with `legacy_cocos_template_removed`. | `state/long_runs/legacy_cocos_block_after_repairs` |

## Workflow Runs

| Purpose | Run id | Status | Notes |
| --- | --- | --- | --- |
| Scope-bound receipt negative check | `run_2532485a894b` receipt path | Failed fast | Scope mismatch was rejected before mutation. Evidence: `state/long_runs/workflow_task_card_completion_20260428_052105`. |
| Workflow-controlled task-card patch attempt | `run_e20a3b0a2511` | Failed honestly | Route used `patch_apply_enforcement -> codex`, no OpenCode default. Codex timed out after 180s with `provider_timeout`, no patch, and structured mutation evidence. Evidence: `state/long_runs/workflow_task_card_completion_20260428_052140`. |
| Procedural SFX QA metadata | `run_288e9dc2562b` | Passed | Workflow-controlled patch updated asset generation metadata. Evidence `evidence_7b7aa7ba02e8`; patch `state/artifacts/run_288e9dc2562b_feature_delivery_mutation.patch`. |
| Asset factory SFX tests | `run_3776bc6a71f5` | Passed | Workflow-controlled patch added SFX QA contract tests. Evidence `evidence_751d2f33d7ae`; patch `state/artifacts/run_3776bc6a71f5_feature_delivery_mutation.patch`. |
| Cocos SFX manifest | `run_c064ab735768` | Passed | Workflow-controlled patch moved `sfx_place` and `sfx_clear` to `procedural_sfx_local` WAV SFX. Evidence `evidence_3fa7ae0adca5`; patch `state/artifacts/run_c064ab735768_feature_delivery_mutation.patch`. |
| Cocos audio modality bindings | `run_8ed8421da0f4` | Passed | Workflow-controlled patch preserved `sfx`, `voice`, and `music` in runtime resource/audio hooks. Evidence `evidence_b561edb66c59`; patch `state/artifacts/run_8ed8421da0f4_feature_delivery_mutation.patch`. |
| Scheduler lease CLI probe | `run_b26fbae993f0` | Passed | Terminal run inspection reported no scheduler-authority problems after release fix. Evidence `evidence_c7fb692d55f4`; path `state/long_runs/scheduler_lease_fix_cli_probe_20260428`. |
| Legacy template guard | `pipeline_f5d904a87f0d` | Blocked | `commercial_cocos_game` stopped with `legacy_cocos_template_removed`. Evidence: `state/long_runs/legacy_cocos_block_after_repairs`. |

## Pipeline Evaluation

| Pipeline id | Path | Result |
| --- | --- | --- |
| `pipeline_a4f77ed8ffd7` | `state/long_runs/commercial_pipeline_eval_20260428_052709` | Failed at final gate. Found MiniMax image prompt length provider error. |
| `pipeline_c0eefb308826` | `state/long_runs/commercial_pipeline_eval_20260428_053221` | Failed at final gate. Image assets, BGM, and GCP TTS voice succeeded; SFX blocked by provider usage limit and is now classified as operator/provider recovery. |
| `pipeline_d7ca062da293` | `state/long_runs/commercial_pipeline_precondition_20260428_054020` | Failed at final gate without wasting provider calls. Missing source input was classified as `operator_input`. |
| `pipeline_061e3703e442` | `state/long_runs/commercial_game_attempt_20260428_054050` | Final real commercial-game attempt. Failed with `cocos_creator_exe_missing`; later correction showed this was a pipeline autodiscovery bug, not proof that Cocos Creator was uninstalled. |
| `pipeline_a41e231c69a4` | `state/long_runs/commercial_game_real_run_after_repair_20260428_1606` | Gate v1 run preserved as automated scaffold/build/playtest evidence. Superseded by no-degradation gate v2; do not cite as final commercial playable proof. |
| `zero_degradation_rerun_20260428_evidencefix` | `state/long_runs/zero_degradation_rerun_20260428_evidencefix` | Strict no-degradation rerun. Failed honestly with `commercial_game_no_degradation_failed`; live role provider proof passed, while Cocos ecosystem, same-project patch proof, product-depth features, audio runtime, build-exit strictness, and human review remained blockers. |

## Game Attempt Result

The real game attempt used `commercial_game_production` with a Chinese source brief at `state/commercial_game_inputs/zen_garden_blocks_zh_brief.md` and required real assets, build, and commercial readiness.

Result for the old attempt: `NO-GO`.

Reasons:

- At the time of the run, the pipeline CLI did not autodiscover the existing Cocos Creator installation when `--creator-exe` was omitted.
- The installed executable was later verified at `C:\ProgramData\cocos\editors\Creator\3.8.8\CocosCreator.exe`.
- The blocker classification was useful as a hard stop, but the operator guidance was too narrow: the correct fix was pipeline autodiscovery plus explicit `--creator-exe` support, not claiming Cocos Creator was absent.
- Because `--require-build` was set and the pipeline received no creator path, the asset stage precondition guard skipped provider calls instead of producing partial assets that could not be validated end to end.

Correction applied after this report was first written:

- Pipeline CLI and contribution capability execution now autodiscover Cocos Creator for `--require-build` runs when `--creator-exe` is omitted.
- Adapter smoke checks confirmed both OpenCode and Codex can be invoked through their workflow adapters for artifact-only work.

## Gate V1 Run Reclassification

After the workflow-wide repairs, `commercial_game_production` was run again with `--execute-agent-roles`, `--live-agent-roles`, `--execute-capabilities`, `--repair-loop`, `--require-real-assets`, `--require-build`, `--require-playtest`, and `--require-commercial`.

Original gate v1 result: `GO` for this run.

Current gate v2 classification: historical automated scaffold/build/playtest evidence only. It is not sufficient proof of final commercial playable readiness.

Evidence:

- Pipeline id: `pipeline_a41e231c69a4`.
- Evidence root: `state/long_runs/commercial_game_real_run_after_repair_20260428_1606`.
- Output project: `state/pipeline_runs/commercial_game_real_run_after_repair_20260428_1606/cocos_project`.
- Final stage evidence: `state/long_runs/commercial_game_real_run_after_repair_20260428_1606/10_pstage_7deb430995e2/stage_result.json`.
- Player-visible evidence: `state/pipeline_runs/commercial_game_real_run_after_repair_20260428_1606/cocos_project/player_visible_evidence/cocos_player_visible_evidence.json`.
- Screenshots: `cocos_playtest_initial.png`, `cocos_playtest_after_actions.png`, and `cocos_playtest_desktop.png` under the project `playtest_evidence` directory.
- Asset evidence: `background`, `block_skin_neon`, `particle_clear`, `bgm_loop`, `voice_reward`, `sfx_place`, and `sfx_clear` all completed with provider/provenance/hash evidence.

Notes:

- `sfx_place` and `sfx_clear` used `procedural_sfx_local` WAV generation and passed QA metadata.
- Cocos build produced Web Mobile artifacts and copied runtime assets. Cocos returned `creator_exit_code=36`, but gate v1 accepted `artifact_success=true`; gate v2 now treats nonzero Creator exit as a blocker unless explicitly explained by a stricter contract.
- stderr contained `invalid pdf header` / `EOF marker not found` because the markdown brief was supplied via the historical `--pdf-path` option. This workflow source-intake bug is fixed by `--source-path` and markdown source handling.

## No-Degradation Gate V2 Rerun

Strict rerun command required live roles, real assets, build, playtest, Cocos ecosystem evidence, commercial readiness, and human player review.

Result: `NO-GO`.

Evidence:

- Pipeline id: `zero_degradation_rerun_20260428_evidencefix`.
- Evidence root: `state/long_runs/zero_degradation_rerun_20260428_evidencefix`.
- Pipeline evidence: `state/long_runs/zero_degradation_rerun_20260428_evidencefix/zero_degradation_rerun_20260428_evidencefix.json`.
- Heartbeat: `state/long_runs/zero_degradation_rerun_20260428_evidencefix/zero_degradation_rerun_20260428_evidencefix.heartbeat.jsonl`.
- Final stage evidence: `state/long_runs/zero_degradation_rerun_20260428_evidencefix/10_pstage_807796f8c6b2/stage_result.json`.
- Cocos ecosystem evidence: `state/long_runs/zero_degradation_rerun_20260428_evidencefix/zero_degradation_rerun_20260428_evidencefix/cocos_ecosystem/cocos_ecosystem_bridge_evidence.json`.

Gate v2 blockers:

- `editor_bridge_present`, `local_mcp_or_extension_present`, `assetdb_import_query_evidence`, `scene_create_save_evidence`, `prefab_create_instantiate_evidence`, `build_api_evidence`, `license_cost_manifest`.
- `same_project_worker_patch_missing`, `product_feature_depth_missing`, `cocos_build_nonzero_exit`.
- `levels_not_distinct_or_less_than_eight`, `skin_system_not_player_visible`, `shop_ownership_states_missing`.
- `audio_runtime_not_verified`, `bgm_runtime_not_verified`, `volume_toggle_missing`.
- `cocos_ecosystem_bridge_missing`, `awaiting_human_player_review`.

Positive evidence:

- `live_role_provider_proof_go=true`.
- The markdown source brief was consumed as `source_kind=text`, without the prior PDF parser warning.
- Pipeline heartbeat reached terminal `failed`, and the persisted pipeline JSON now contains its own `evidence_path`.

## 2026-04-29 Zero-Degradation Cocos/Worker Rerun

This checkpoint implemented the Cocos ecosystem evidence collector and same-project task-card worker repairs, then reran the strict commercial pipeline. This is a superseding strict truth for the Cocos/worker repair slice, not a commercial GO.

Result: `NO-GO`.

Evidence:

- Pipeline id: `zero_degradation_cocos_worker_rerun4_20260429`.
- Evidence root: `state/long_runs/zero_degradation_cocos_worker_rerun4_20260429`.
- Pipeline evidence: `state/long_runs/zero_degradation_cocos_worker_rerun4_20260429/zero_degradation_cocos_worker_rerun4_20260429.json`.
- Heartbeat: `state/long_runs/zero_degradation_cocos_worker_rerun4_20260429/zero_degradation_cocos_worker_rerun4_20260429.heartbeat.jsonl`.
- Same-project ledger: `state/long_runs/zero_degradation_cocos_worker_rerun4_20260429/zero_degradation_cocos_worker_rerun4_20260429/task_card_worker/same_project_patch_ledger.json`.
- Cocos ecosystem evidence: `state/long_runs/zero_degradation_cocos_worker_rerun4_20260429/zero_degradation_cocos_worker_rerun4_20260429/cocos_ecosystem/cocos_ecosystem_bridge_evidence.json`.

Positive evidence:

- Real asset stage passed: `commercial_assets_go=true`, `placeholder_only=false`, with 7 provider evidence entries.
- Live role provider proof passed: `live_role_provider_proof_go=true`.
- `commercial_game_task_card_worker` no longer calls the deterministic Cocos E2E generator for DB task-card implementation. It created one project shell and attempted `workflowctl run from-task-card --execute` with a scope-bound receipt.
- Task-card child execution now records progress-aware watchdog metadata. The first same-project business card failed as `provider_idle_timeout`, with stderr preview `command timed out after 240s (idle_timeout)` and recovery suggestion `retry_with_higher_idle_timeout_or_split_task`.
- Cocos ecosystem collector now creates a project-local Editor extension package manifest, a trusted bridge-report contract, a license/cost manifest, and rejects filesystem-only bridge reports.

Strict blockers:

- `same_project_worker_patch_go=false`; first task-card patch did not complete, so no business implementation was accepted.
- `ecosystem_integration_go=false`; the project-local extension package exists, but no trusted real Editor/API report proved AssetDB, Scene, Prefab, node/component binding, or Build API operations.
- Product-depth checks remain absent: 8 distinct level goals, visible shop/skin ownership state, runtime audio/BGM, volume toggle, build/playtest, and human player review.
- Final gate failed with `commercial_game_no_degradation_failed`; this must not be reported as `commercial_playable_go=true`.

Earlier strict run `zero_degradation_cocos_worker_rerun3_20260429` was stopped by bug-first rule and preserved as failure evidence because the initial worker child runner used raw subprocess waiting without progress-aware child evidence. The repair added `run_subprocess_with_tree_timeout` to the task-card worker CLI and regression test coverage.

## Validation

The following checks passed during this window:

```powershell
python -m pytest tests/test_capability_control_plane.py tests/test_cli.py::test_cli_resume_rejects_unissued_patch_receipt_before_adapter_launch tests/test_cli.py::test_cli_from_task_card_defaults_patch_apply_to_codex tests/test_execution_loop.py::test_compile_run_defaults_patch_apply_to_codex_adapter -q
python -m pytest tests/test_m41_capabilities.py::test_codex_adapter_timeout_records_failure_class_and_stream_previews tests/test_execution_loop.py::test_local_worker_execution_records_heartbeat_renewals tests/test_execution_loop.py::test_local_worker_heartbeat_is_visible_during_execution -q
python -m pytest tests/test_pipeline_and_automation_cli.py tests/test_m109_unified_brief.py -q
python -m pytest tests/test_chat_llm_runtime.py tests/test_m109_unified_brief.py -q
python -m pytest tests/test_asset_factory.py tests/test_cocos_e2e.py -q
python -m pytest tests/test_cli.py tests/test_pipeline_and_automation_cli.py -q
python -m pytest tests/test_langgraph_focused_runtime.py tests/test_langgraph_multi_agent.py -q
python -m pytest tests/test_cocos_e2e.py tests/test_m109_unified_brief.py -q
python -m py_compile packages/core_domain/pipeline.py packages/worker_adapters/codex_adapter.py packages/contributions/asset_factory/factory.py packages/contributions/games/cocos/commercial_assets.py packages/contributions/pipelines/commercial_game_production.py packages/contributions/pipelines/registry.py
python -m pytest tests/test_execution_loop.py -q
python -m pytest tests/test_remote_worker_api.py::test_remote_worker_completion_callback_is_idempotent tests/test_remote_worker_api.py::test_remote_worker_dispatch_and_callbacks_roundtrip -q
python -m pytest tests/test_asset_factory.py tests/test_cocos_e2e.py -q
python -m pytest tests/test_m41_capabilities.py tests/test_m77_provider_access.py tests/test_repo_mutation_atomicity.py tests/test_offline_validation_runner.py -q
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite core
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite integration
python -m infra.scripts.check_doc_links
python -m apps.operator_cli.main --db-path state\workflow.db --workspace-root . validation run --suite full --skip-offline-probe --report-path state\long_runs\codex_validation_full_20260428_after_scheduler_receipt_docs\report.json
python -m apps.operator_cli.main --db-path state\workflow.db --workspace-root . pipeline truth-report --template commercial_game_production
python -m apps.operator_cli.main --db-path state\workflow.db --workspace-root . pipeline preview --template commercial_game_production
python -m pytest tests/test_pipeline_and_automation_cli.py::test_pipeline_preview_blocks_removed_commercial_cocos_game_template tests/test_pipeline_and_automation_cli.py::test_removed_commercial_cocos_template_blocks_before_old_generators tests/test_m109_unified_brief.py::test_cli_pipeline_truth_report_blocks_removed_commercial_cocos_template -q
python -m pytest tests/test_pipeline_and_automation_cli.py::test_commercial_gate_v2_rejects_event_only_scaffold_go tests/test_pipeline_and_automation_cli.py::test_commercial_gate_v2_can_stop_at_human_review_only tests/test_pipeline_and_automation_cli.py::test_pipeline_run_passes_zero_degradation_options_and_source_path -q
python -m pytest tests/test_cocos_e2e.py::test_cocos_ecosystem_bridge_records_missing_editor_contract_without_diagnostic_blocking tests/test_cocos_e2e.py::test_cocos_ecosystem_bridge_blocks_when_required tests/test_cocos_e2e.py::test_cocos_e2e_accepts_markdown_source_without_pdf_parser -q
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite unit
```

## Hygiene

Removed local scratch artifacts from this window while preserving audit evidence:

- Current pytest temporary child directories under `state/.pytest-tmp-workflow`.
- Earlier obsolete scratch long-run directories from the first repair pass: `env_test`, `env_test2`, `commercial_pipeline_completion*`, and `pipeline_eval_20260428_050533`.

Preserved evidence directories listed above because they are needed for audit and handoff.

## Remaining Risks

- Cocos Creator is installed locally, and the pipeline now autodiscovers the default installation. Future real commercial-game runs should still record the resolved executable path in evidence and allow explicit `--creator-exe` overrides.
- Local `procedural_sfx_local` is accepted for micro game SFX only when QA passes. It does not remove the need for provider/live-proof evidence for images, BGM, voice, visual QA, build, browser playtest, screenshots, and commercial final gate.
- The monolithic task-card completion patch was too large for the 180s Codex adapter timeout. Future business pipeline mutation should split the active phase into smaller scope-bound task cards instead of forcing one large repo mutation.
- Cocos build should distinguish successful artifact output from nonzero Creator process exit codes more explicitly; gate v2 currently blocks `creator_exit_code=36`.
- Cocos Editor bridge, local MCP server, AssetDB, Scene/Prefab APIs, ecosystem assets, licenses, costs, and commercial-use boundaries remain planned capability work, not completed integration.
- Business gameplay depth remains open: 8 real level goals, visible shop/skin ownership, collection/economy, audio runtime verification, and human player review are not complete.
