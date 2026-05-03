# 当前开发工作流

## 2026-05-03 Closeout: Commercial Machine Evidence And Player Visible Completion

`Commercial Machine Evidence And Player Visible Completion` 已按 active-phase-only 原则执行到诚实 NO-GO；本阶段没有进入 M110，没有生成未来 phase task cards，也没有把机器证据或无人值守结果转换为商业可玩 GO。

- DB task-card run id: `commercial_machine_evidence_20260503`
- Cocos project: `state/pipeline_runs/commercial_game_core_content_20260503/cocos_project`
- Pipeline evidence: `state/commercial_machine_evidence_20260503/pipeline_evidence/`
- 当前 phase 只生成 3 张 DB-backed task cards：`commercial_machine_evidence_20260503_product_depth_chinese_ui`、`commercial_machine_evidence_20260503_build_browser_machine_evidence`、`commercial_machine_evidence_20260503_human_review_packet_gate`。
- 三张卡均通过 `human_visible_cli_enforced` 执行链完成；visible CLI session metadata、mirrored `stdout.log` / `stderr.log` / `stream.jsonl`、fresh receipt、child run/attempt、changed files 和测试通过是完成条件。
- 已修复控制面问题：`Commercial Machine Evidence And Player Visible Completion` 现在只 materialize 当前 phase 的三张卡；product-depth 证据会合并 `chinese_ui_panels_evidence.json`；Cocos browser playtest 会识别默认 `#GameCanvas`，不再误把 Cocos 默认 canvas 当成缺失。
- 当前证据结论：`commercial_game_development_readiness_go=true`，`product_body_evidence.go=true`，`gameplay_semantic_evidence.go=true`，`product_depth_evidence.go=true`，`build_ledger.go=true`。
- 当前商业终态仍为：`machine_evidence_go=false`，`human_player_review_go=false`，`commercial_playable_go=false`。
- 剩余 blocker 已收窄为：`placeholder_assets_only`、`browser_playtest_no_go`、`audio_runtime_not_verified`、`bgm_runtime_not_verified`、`sfx_runtime_not_verified`、`volume_toggle_missing`。
- 下一 active phase：`Commercial Asset And Browser Runtime Proof Implementation`。只允许为该 phase 生成当前 DB task cards，目标是补齐非 placeholder 资产证明、浏览器可交互运行证明、真实音频/BGM/SFX/音量控件运行证明，并在机器证据全过后停在 `AWAITING_HUMAN_REVIEW`。

## 2026-05-02 Human Review NO-GO: Trusted Cocos Build Browser Audio Runtime Evidence

`Trusted Cocos Build Browser Audio Runtime Evidence` 原先按 machine-evidence closeout 收口；真实人工评审后已被复判为 `NO-GO`。本阶段仍未进入 M110，未生成未来 phase task cards，未自动 commit/push/PR，未声明商业可玩 GO。

- DB task-card run id: `trusted_cocos_build_browser_audio_runtime_20260502`
- Task-card snapshot: `state/trusted_cocos_build_browser_audio_runtime_20260502/task_cards.md`
- Phase evidence: `state/trusted_cocos_build_browser_audio_runtime_20260502/`
- Phase preflight previews: `state/trusted_cocos_build_browser_audio_runtime_20260502/plan_graph.json`, `state/trusted_cocos_build_browser_audio_runtime_20260502/policy_preview.json`, `state/trusted_cocos_build_browser_audio_runtime_20260502/goal_packet.json`
- 被人工复判否定的机器判断：真实 Cocos Creator 3.8.8 Web Mobile build ledger、HTTP/browser playtest ledger、screenshots、console/page error capture、BGM/SFX/volume runtime proof、drag/place/button panel events 和 feature coverage 曾被机器 gate 接受，但这些证据不足以证明商业游戏本体完成。
- 核对结论：拉起的 URL 指向当前 pipeline 的 `build/web-mobile`，不是路径错误；问题是该 build 本身不是合格游戏本体，而是 runtime hook / canvas / event coverage 被机器 gate 误收。
- 人审结论：`human_review_result.json` 记录真实人工评审 `NO-GO`，原因是 `product_body_not_valid`、`machine_gate_false_positive`、`event_and_canvas_runtime_hook_not_sufficient_for_game_body`。
- 最终严格管线：`pipeline_ecf26665254e`，evidence 位于 `state/trusted_cocos_build_browser_audio_runtime_20260502/final_pipeline_run_validation_after_overlay_mobile_top_repair/`。
- Phase closeout: `state/trusted_cocos_build_browser_audio_runtime_20260502/phase_closeout.json`
- Operator packet: `state/trusted_cocos_build_browser_audio_runtime_20260502/operator_packet.json`
- Runtime gate: `state/trusted_cocos_build_browser_audio_runtime_20260502/runtime_gate.json`
- 当前终态：`machine_evidence_go=false`，`commercial_final_gate_evidence.go_no_go=NO-GO`，`human_player_review_go=false`，`commercial_playable_go=false`。
- 当前 blocker：`human_player_review_failed`、`product_body_not_valid`、`machine_gate_false_positive`。下一步必须新开 active phase 同时修复商业游戏本体与 final gate，不能继续用 event-only/canvas runtime hook 证明产品完成。
- 根目录长程修复计划：[POST_M109_LONG_RUNNING_DEVELOPMENT_PLAN_2026_05_02.md](POST_M109_LONG_RUNNING_DEVELOPMENT_PLAN_2026_05_02.md)。该文档只写到 milestone/phase，不创建 M110 或未来 phase task card；当前实现切片已覆盖 DB lifecycle、fresh execution、evidence reuse、gameplay semantic、product body gate 假阳性、source requirement matrix / task-card req_id coverage gate，以及非商业成品的 Cocos product-body baseline bootstrap。

## 2026-05-02 Closeout: Audio Animation Runtime Hooks Same-Project Repair

`Audio Animation Runtime Hooks Same-Project Repair` 已按 active-phase-only 原则收口。本阶段原始 5 张 DB-backed task cards 之外，因 workflow bug-first 修复补充了 4 张当前 phase 修复/确认卡；未进入 M110，未生成未来 phase task cards，未推进 Cocos build/browser playtest/human-review，未声明商业可玩 GO。

- DB task-card run id: `audio_animation_runtime_hooks_same_project_repair_20260502`
- Task-card snapshot: `state/audio_animation_runtime_hooks_same_project_repair_20260502/task_cards.md`
- Phase evidence: `state/audio_animation_runtime_hooks_same_project_repair_20260502/`
- 已完成：`audio_runtime_hooks_micro_patch` 通过 OpenCode same-project task-card execution 写入 `AudioRuntimeState.ts` 与 `audio_manifest.json`；`animation_feedback_hooks_micro_patch` 写入 `FeedbackAnimationState.ts` 与 `feedback_animation_manifest.json`。
- 已修复 workflow bug：`/dev/null` new-file patch 覆盖已有文件会污染内容的问题已在 repo mutation 层拒绝；unsafe `python -c` task-card test 改为 `infra.scripts.validate_animation_artifact_integrity`；OpenCode adapter 内层 180s timeout 已对齐到 task-card adaptive timeout env。
- 已完成确认：`animation_feedback_hooks_integrity_confirmation_after_timeout_repair` 使用 fresh OpenCode receipt `opreceipt_d66da1444cfa` / child run `run_cd54cbc8a9e1` 完成，写入 `workflow_animation_artifact_integrity_evidence.json`，safe validator 通过。
- 保持未声明：`audioPlaybackVerified`、`bgmStarted`、`sfxPlaybackVerified`、`volumeToggleUsable`、`animationFeedbackVerified`、browser playtest、human review 和 `commercial_playable_go` 仍未声明。
- Operator packet: `state/audio_animation_runtime_hooks_same_project_repair_20260502/operator_packet.json`
- Normalized repair packet: `state/audio_animation_runtime_hooks_same_project_repair_20260502/normalized_repair_packet.json`
- Phase gate: `state/audio_animation_runtime_hooks_same_project_repair_20260502/audio_animation_hooks_gate.json`
- Phase closeout: `state/audio_animation_runtime_hooks_same_project_repair_20260502/phase_closeout.json`
- 下一步 opening phase：`Trusted Cocos Build Browser Audio Runtime Evidence`。只为该阶段生成当前 phase task cards，先 build，再在 build GO 后 playtest/runtime gate；不得提前声明 commercial GO。

## 2026-05-02 Closeout: Revive Feedback Feature Coverage Completion

`Revive Feedback Feature Coverage Completion` 已按 active-phase-only 原则收口。本阶段只生成当前 phase 的 4 张 DB-backed task cards；未进入 M110，未生成未来 phase task cards，未推进 audio/build/playtest/human-review，未声明商业可玩 GO。

- DB task-card run id: `revive_feedback_feature_coverage_completion_20260502`
- Task-card snapshot: `state/revive_feedback_feature_coverage_completion_20260502/task_cards.md`
- Phase evidence: `state/revive_feedback_feature_coverage_completion_20260502/`
- Automation lease: `autolease_revive_feedback_coverage_20260502`
- 已完成：`failure_revive_feedback_coverage_micro_patch` 先按 Codex 执行 3 次 fresh receipt，child runs `run_c172afc9ad59`、`run_679dff055f5e`、`run_17730df81964` 均已闭合并最终 `blocked_after_three_attempts`；随后使用当前 phase OpenCode live proof 作为真实 fallback，在 `run_abb467c626b5` 完成同一 DB task card。
- 产品结果：`workflow_commercial_feature_evidence.json` 已写入 `commercial_feature_coverage.failureReviveFeedback=true` 与 `player_visible_checks.failureReviveFeedback=true`，`current_task_card_id=failure_revive_feedback_coverage_completion`，`covered_task_cards` 已包含该卡。
- 保持未声明：`audioPlaybackVerified`、`bgmStarted`、`sfxPlaybackVerified`、`volumeToggleUsable`、`animationFeedbackVerified`、human review 和 `commercial_playable_go` 仍未声明。
- Operator packet: `state/revive_feedback_feature_coverage_completion_20260502/operator_packet.json`
- Normalized repair packet: `state/revive_feedback_feature_coverage_completion_20260502/normalized_repair_packet.json`
- Phase closeout: `state/revive_feedback_feature_coverage_completion_20260502/phase_closeout.json`
- 下一步 opening phase：`Audio Animation Runtime Hooks Same-Project Repair`。只为该阶段生成当前 phase task cards，先完成 audio/animation hooks 后才允许考虑 build/playtest/runtime evidence phase。

## 2026-05-02 Closeout: Patch Generation No-Patch Diagnostic Repair

`Patch Generation No-Patch Diagnostic Repair` 已按 active-phase-only 原则收口。本阶段只生成当前 phase 的 5 张 DB-backed task cards；未进入 M110，未生成未来 phase task cards，未推进 audio/build/playtest/product-depth/human-review，未声明商业可玩 GO。

- DB task-card run id: `patch_generation_no_patch_diagnostic_repair_20260502`
- Task-card snapshot: `state/patch_generation_no_patch_diagnostic_repair_20260502/task_cards.md`
- Phase evidence: `state/patch_generation_no_patch_diagnostic_repair_20260502/`
- Automation lease: `autolease_patch_generation_no_patch_diagnostic_20260502`
- 已完成 workflow bug-first 修复：同项目 task-card wrapper 的内层 `WORKFLOW_CODEX_IDLE_TIMEOUT_SECONDS` / `WORKFLOW_PROVIDER_IDLE_TIMEOUT_SECONDS` 已对齐到 provider-output idle budget 480 秒，避免内层 Codex 在外层 provider-output watchdog 生效前切断 patch_apply turn。
- 已完成 provider live proof：OpenCode live probe 为 `verified_ready` 且 `live_probe=true`，auth source 为 `MINIMAX_API_KEY`；该证据只允许作为真实 fallback 资格，不代表 shell/noop/dry-run 可满足实现 gate。
- 产品恢复结果：`feature_evidence_resume_gate_after_budget_fix` 使用 Codex fresh receipt 在 `run_f41c5b586681` 完成，`workflow_commercial_feature_evidence.json` 已写入 `revive_prompt_evidence`，测试 2/2 通过。
- 剩余 blocker：`failureReviveFeedback` 尚未显式写入 `commercial_feature_coverage` / `player_visible_checks`，所以 product-depth 仍不能通过，audio/build/playtest/human-review 继续 blocked/skipped。
- Operator packet: `state/patch_generation_no_patch_diagnostic_repair_20260502/operator_packet.json`
- Normalized repair packet: `state/patch_generation_no_patch_diagnostic_repair_20260502/normalized_repair_packet.json`
- Phase closeout: `state/patch_generation_no_patch_diagnostic_repair_20260502/phase_closeout.json`
- 下一步 opening phase：`Revive Feedback Feature Coverage Completion`。只为该阶段生成当前 phase task cards，补齐 `failureReviveFeedback` coverage 后才允许考虑 audio/animation hook phase。

## 2026-05-02 Closeout: Revive Prompt Layout Evidence Ultra-Split Repair

`Revive Prompt Layout Evidence Ultra-Split Repair` 已按 active-phase-only 原则收口。本阶段只生成当前 phase 的 5 张 DB-backed task cards；未进入 M110，未生成未来 phase task cards，未推进 audio/build/playtest/product-depth/human-review，未声明商业可玩 GO。

- DB task-card run id: `revive_prompt_layout_evidence_ultra_split_20260502`
- Task-card snapshot: `state/revive_prompt_layout_evidence_ultra_split_20260502/task_cards.md`
- Phase evidence: `state/revive_prompt_layout_evidence_ultra_split_20260502/`
- Automation lease: `autolease_revive_layout_evidence_ultra_split_20260502`
- 本阶段有效进展：`revive_prompt_layout_only_micro_patch` 通过 workflow task-card execution 完成，写入 `failure_overlay_layout.json` 的复活提示布局证据。
- 已完成前置：上一阶段 `FailureOverlayState.ts` 已通过 workflow task-card execution 写入 `watch_reward_revive`、复活奖励提示、每局 1 次限制和 snapshot 输出。
- 本阶段阻塞：`revive_prompt_feature_evidence_only_micro_patch` 三次 fresh receipt 后仍无 accepted patch，child runs 为 `run_c7f0c7428018`、`run_1a1c91b09a70`、`run_112296b408d0`，最终 `blocked_after_three_attempts`，`final_failure_class=provider_execution_failed`。
- 当前根因：三次 raw evidence 都显示 Codex patch_apply 只到 `thread.started` / `turn.started`，未产出 unified diff；内层 `WORKFLOW_CODEX_IDLE_TIMEOUT_SECONDS=240` 早于外层 provider-output idle 480 秒切断 provider turn。下一步必须先修 patch generation idle budget，不得第四次直接重跑 feature-evidence 卡。
- 上游短路继续生效：当前 `same_project_worker_patch_go=false`，所以 `audio_animation_runtime_hooks`、Cocos build/browser playtest/audio runtime/product-depth/human-review 仍只能保持 blocked/skipped，不得下推执行。
- Operator packet: `state/revive_prompt_layout_evidence_ultra_split_20260502/operator_packet.json`
- Normalized repair packet: `state/revive_prompt_layout_evidence_ultra_split_20260502/normalized_repair_packet.json`
- Phase closeout: `state/revive_prompt_layout_evidence_ultra_split_20260502/phase_closeout.json`
- 下一步 opening phase：`Patch Generation No-Patch Diagnostic Repair`。只为该阶段生成当前 phase task cards，先修控制面 idle budget，再由 gate 决定是否 fresh receipt 恢复 feature-evidence 卡；不得进入 build/playtest/audio/human-review。

## 2026-05-02 Closeout: Revive Prompt Micro-Split Exact Context Repair

`Revive Prompt Micro-Split Exact Context Repair` 已按 active-phase-only 原则收口。本阶段只生成当前 phase 的 5 张 DB-backed task cards；未进入 M110，未生成未来 phase task cards，未推进 audio/build/playtest/product-depth/human-review，未声明商业可玩 GO。

- DB task-card run id: `revive_prompt_micro_split_exact_context_20260502`
- Task-card snapshot: `state/revive_prompt_micro_split_exact_context_20260502/task_cards.md`
- Phase evidence: `state/revive_prompt_micro_split_exact_context_20260502/`
- Automation lease: `autolease_revive_prompt_micro_split_20260502`
- 本阶段有效进展：`revive_prompt_state_script_micro_patch` 通过 workflow task-card execution 在第二个 fresh receipt 完成，`FailureOverlayState.ts` 已写入复活奖励提示状态、中文文案、每局 1 次限制、按钮节点和 snapshot 输出。
- 本阶段阻塞：`revive_prompt_layout_evidence_micro_patch` 三次 fresh receipt 后仍无 accepted patch，最终 `blocked_after_three_attempts`，`final_failure_class=provider_execution_failed`。
- 当前根因：script-only 微卡可行，合并的 layout/evidence JSON 卡仍过宽或 evidence JSON 上下文过大。下一步不能第四次重跑该合并卡，必须拆成 layout-only 和 feature-evidence-only 两张更小卡。
- 上游短路继续生效：当前 `same_project_worker_patch_go=false`，所以 `audio_animation_runtime_hooks`、Cocos build/browser playtest/audio runtime/product-depth/human-review 仍只能保持 blocked/skipped，不得下推执行。
- Operator packet: `state/revive_prompt_micro_split_exact_context_20260502/operator_packet.json`
- Normalized repair packet: `state/revive_prompt_micro_split_exact_context_20260502/normalized_repair_packet.json`
- Phase closeout: `state/revive_prompt_micro_split_exact_context_20260502/phase_closeout.json`
- 下一步建议 opening phase：`Revive Prompt Layout Evidence Ultra-Split Repair`。只为该阶段生成当前 phase task cards，先 layout-only，再 feature-evidence-only；不得进入 build/playtest/audio/human-review。

## 2026-05-02 Closeout: Patch Worker Strategy Repair For Codex Turn-Start Stalls

`Patch Worker Strategy Repair For Codex Turn-Start Stalls` 已按 active-phase-only 原则收口。本阶段只生成当前 phase 的 5 张 DB-backed task cards；未进入 M110，未生成未来 phase task cards，未推进 audio/build/playtest/product-depth/human-review，未声明商业可玩 GO。

- DB task-card run id: `patch_worker_strategy_turn_stall_repair_20260502`
- Task-card snapshot: `state/patch_worker_strategy_turn_stall_repair_20260502/task_cards.md`
- Phase evidence: `state/patch_worker_strategy_turn_stall_repair_20260502/`
- 已完成 workflow bug-first 修复：Codex patch_apply 的 diff 生成现在进入 prompt-only broker workspace，不再把真实 repo/Cocos project 作为 `--cd`；同时加上 `--ignore-rules`，并在 metadata 中记录 `prompt_transport`、`prompt_workspace`、`project_working_directory` 和 `project_rules_ignored`。
- 诊断证据：最小 stdin diff 诊断可以在 broker workspace 中快速产出可解析 unified diff；repo 内 prompt-argument 诊断会触发 Codex 工具/PowerShell 读取和策略拒绝，证明原先的 repo/project-rule 上下文会污染 patch proposal。
- 产品恢复结果：`revive_prompt_resume_after_worker_strategy_repair` 在修复后执行 3 次 fresh receipt，child runs 为 `run_0b75311d15cc`、`run_3da7ca8bb0d8`、`run_70357dea69e5`，均已闭合；同项目未变，但仍无 changed files / accepted patch / passing tests，最终 `blocked_after_three_attempts`。
- 当前根因：worker prompt transport 已修，但 `revive_prompt` 产品卡仍过宽或上下文不够“直接可出 diff”；下一步不能第四次重跑同一张卡，必须拆成更小的 exact-context micro-card。
- 上游短路：当前 `same_project_worker_patch_go=false`，所以 `audio_animation_runtime_hooks`、Cocos build/browser playtest/audio runtime/product-depth/human-review 仍只能保持 blocked/skipped，不得下推执行。
- Operator packet: `state/patch_worker_strategy_turn_stall_repair_20260502/operator_packet.json`
- Normalized repair packet: `state/patch_worker_strategy_turn_stall_repair_20260502/normalized_repair_packet.json`
- Phase closeout: `state/patch_worker_strategy_turn_stall_repair_20260502/phase_closeout.json`
- 下一步建议 opening phase：`Revive Prompt Micro-Split Exact Context Repair`。只为该阶段生成当前 phase task cards，把 revive prompt 拆成 script/evidence exact-context 小卡后再 workflow-first 续跑。

## 2026-05-02 Closeout: Provider Command Policy And Patch Generation Prompt Repair

`Provider Command Policy And Patch Generation Prompt Repair` 已按 active-phase-only 原则收口。本阶段只生成当前 phase 的 DB-backed task cards；未进入 M110，未生成未来 phase task cards，未推进 audio/build/playtest/product-depth/human-review，未声明商业可玩 GO。

- DB task-card run id: `provider_command_policy_patch_generation_repair_20260502`
- Task-card snapshot: `state/provider_command_policy_patch_generation_repair_20260502/task_cards.md`
- Phase evidence: `state/provider_command_policy_patch_generation_repair_20260502/`
- 已完成 workflow bug-first 修复：`patch_only_prompt_and_command_policy_guard` 让 Codex/OpenCode patch_apply 提示明确禁止 provider 侧 shell/PowerShell/cmd/Python/Node/npm/package-manager/file-inspection/tool 命令，只返回单个 bounded unified diff；`service_repo_mutation` 注入 `WORKFLOW_MUTATION_PROVIDER_COMMAND_POLICY=patch_only_no_shell` 和 bounded read-set context。
- 已完成 transport 修复：`codex_patch_apply_transport_isolation_guard` 让 Codex patch_apply 只在 mutation 模式使用 `--ignore-user-config` 并禁用 apps/plugins/memories/tool-search/browser/computer/image/workspace features。隔离 smoke 输出 `ok`，说明认证仍可用；stderr 中的 analytics/Cloudflare 噪声未阻止该 smoke 完成。
- 产品恢复结果：`revive_prompt_resume_after_provider_policy_repair` 三次 fresh receipt 后仍失败，暴露 user config/MCP/apps transport 噪声；完成 transport isolation 后，`revive_prompt_resume_after_codex_transport_isolation` 再次三次 fresh receipt，同项目未变、child runs `run_6b6a3475d876`、`run_f91c4e136f05`、`run_9fbd6add32ae` 均闭合，但仍无 changed files / passing tests / accepted patch，最终 `blocked_after_three_attempts`。
- 当前根因：旧的 provider 命令策略和 Codex user-config transport 噪声已偿还；剩余 blocker 是 isolated Codex patch_apply 到达 `turn.started`/provider stream 后没有在 idle 窗口内返回可接受 unified diff，归一为 `codex_patch_apply_turn_started_no_diff_idle_timeout_after_transport_isolation`。
- 上游短路：当前 `same_project_worker_patch_go=false`，所以 `audio_animation_runtime_hooks`、Cocos build/browser playtest/audio runtime/product-depth/human-review 仍只能保持 blocked/skipped，不得下推执行。
- Operator packet: `state/provider_command_policy_patch_generation_repair_20260502/operator_packet.json`
- Normalized repair packet: `state/provider_command_policy_patch_generation_repair_20260502/normalized_repair_packet.json`
- Phase closeout: `state/provider_command_policy_patch_generation_repair_20260502/phase_closeout.json`
- 下一步建议 opening phase：`Patch Worker Strategy Repair For Codex Turn-Start Stalls`。先修 patch worker strategy，再恢复 `revive_prompt_resume_after_codex_transport_isolation`；不得用 shell/noop/dry-run/fallback-only 满足 implementation gate。

## 2026-05-01 Closeout: Split Chinese UI Panels And Failure Feedback Same-Project Resume

`Split Chinese UI Panels And Failure Feedback Same-Project Resume` 已按 active-phase-only 原则收口。本阶段只生成当前 phase 的 DB-backed task cards，业务实现继续走 workflow task-card execution；Codex 只用于 workflow bug-first 修复、closeout 和验证，未推进 audio/build/playtest/product-depth/human-review，未声明商业可玩 GO。

- DB task-card run id: `split_chinese_ui_feedback_resume_20260501`
- Task-card snapshot: `state/split_chinese_ui_feedback_resume_20260501/task_cards.md`
- Phase evidence: `state/split_chinese_ui_feedback_resume_20260501/`
- 已完成：`chinese_ui_core_panels_visible` 写入中文核心 UI panel 状态与布局；`repair_feature_evidence_json_syntax` 修复同项目 feature evidence JSON；`failure_overlay_copy_layout_only` 写入失败弹窗中文文案和布局引用。
- Bug-first 兜底：`retry_review_failure_classification_repair` 修正了 task-card worker 的失败分类，`patch_generation_failed` 不再误归为评审失败，而归一为 `provider_execution_failed`；`same_project_patch_review_failed` 也进入三次 fresh receipt retry 策略。对应测试已补在 `tests/test_pipeline_and_automation_cli.py`。
- 最终阻塞：`revive_prompt_reward_state_only` 在修复后执行 3 次 fresh receipt 续跑，child runs 为 `run_cd39231e182f`、`run_9dc1cefd8aa7`、`run_751d4f92c3bb`，均有 provider stream/material progress，但都以 `return_code=124`、`mutation_final_test_status=patch_generation_failed` 收口；ledger 标记 `blocked_after_three_attempts`，root failure class 为 `provider_execution_failed`。
- 根因证据：三次失败 stderr 均出现 provider 侧工具策略拒绝、PowerShell profile / ConstrainedLanguage 报错和 240 秒 idle timeout；这不是继续扩大硬时限能解决的产品实现问题，而是 provider 命令策略/补丁生成提示需要先修。
- 上游短路：当前 `same_project_worker_patch_go=false`，因此 `audio_animation_runtime_hooks`、Cocos build/browser playtest/audio runtime/product-depth/human-review 仍只能保持 blocked/skipped，不得下推执行。
- Operator packet: `state/split_chinese_ui_feedback_resume_20260501/operator_packet.json`
- Normalized repair packet: `state/split_chinese_ui_feedback_resume_20260501/normalized_repair_packet.json`
- Phase closeout: `state/split_chinese_ui_feedback_resume_20260501/phase_closeout.json`
- 下一步建议 opening phase：`Provider Command Policy And Patch Generation Prompt Repair`。修 provider 命令策略和 patch-only 提示后，再恢复 `revive_prompt_reward_state_only`，或把它继续拆成 script-only / layout-only / evidence-only 三张当前 phase 卡。

## 2026-05-01 Closeout: Adaptive Wall Timeout For Active Provider Progress Repair

`Adaptive Wall Timeout For Active Provider Progress Repair` 已完成 workflow bug-first 修复。本阶段只修 task-card worker 的硬时限策略，未继续 Cocos 产品实现卡，未推进 audio/build/playtest/human-review，未声明商业可玩 GO。

- DB task-card run id: `adaptive_wall_timeout_repair_20260501`
- Task-card snapshot: `state/adaptive_wall_timeout_repair_20260501/task_cards.md`
- 当前 phase 只生成 4 张 DB-backed task cards：governance/policy contract、subprocess adaptive wall timeout、task-card worker timeout budget wiring、closeout/resume gate。
- 修复结果：`run_subprocess_with_tree_timeout` 支持 bounded adaptive wall timeout。初始 wall timeout 仍为 900 秒；若 child run 仍有 provider output 且最近有 material progress，可延长 900 秒；默认最多延长 1 次，绝对上限 1800 秒。延长证据写入 watchdog metadata：`adaptive_wall_timeout_extension_count`、`adaptive_wall_timeout_effective_seconds`、`adaptive_wall_timeout_absolute_max_seconds`、`adaptive_wall_timeout_exhausted`。
- 任务卡 worker 已把同项目 task-card 执行的外层 watchdog 和内层 Codex timeout 同步到 adaptive 预算：`WORKFLOW_CODEX_TIMEOUT_SECONDS=1800`，同时保留 provider output idle 480 秒和 material progress idle 720 秒。
- 新分类：若已获得 adaptive 延长但仍触发硬墙，failure class 变为 `task_scope_too_large_after_adaptive_wall_timeout`，repair suggestion 是拆分或收窄 task card，而不是继续无界延长。
- 产品恢复边界：后续最多允许用 adaptive timeout 对更小或收窄后的 `chinese_ui_panels_and_feedback` 子卡做验证。若 broad card 再次耗尽 adaptive wall timeout，不得继续第 4 次无脑续跑，必须拆卡。

## 2026-04-30 Closeout: Task Card Direct Execution And Provider Stream Observability Repair

`Task Card Direct Execution And Provider Stream Observability Repair` 是 `chinese_ui_panels_and_feedback` 三次失败后的 workflow bug-first 修复阶段。本阶段只修执行控制面和诊断证据，未继续 Cocos 产品实现卡，未推进 audio/build/playtest/human-review，未声明商业可玩 GO。

- DB task-card run id: `task_card_direct_execution_provider_stream_repair_20260430`
- Task-card snapshot: `state/task_card_direct_execution_provider_stream_repair_20260430/task_cards.md`
- 当前 phase 只生成 4 张 DB-backed task cards：historical forensics、direct task-card execution guard、adapter provider stream observability bridge、watchdog closure integrity/closeout。
- 根因校准：旧 `commercial_game_task_worker_cli` 用 `--preset project_delivery` 调用 `from-task-card`，导致单张产品卡被展开为 planner / coder / research orchestration；外层 watchdog 只能看到 `workflow_progress` control heartbeat，真实 adapter 输出没有桥接为 DB provider stream evidence。因此旧 `provider_output_event_count=0` 只能说明外层未观测到 provider stream，不能单独证明 provider 自身 8 分钟完全无动作。
- 修复结果：task-card patch apply 改为 `feature_delivery` + Codex direct path；lifecycle 层对 task-card patch packet 增加 direct guard；Codex adapter 写入 `provider_stream_observed` metadata，且不记录 raw text 或 chain-of-thought；`from-task-card` runtime state 暴露 provider/material progress 计数；外层 watchdog 可通过 DB activity probe 区分 control heartbeat、provider output idle 和 material progress idle；watchdog closure 会闭合 run、runtime task、attempt、worker lease、claims 和 scheduler leases。
- 产品恢复边界：本阶段完成后只允许从现有 `chinese_ui_panels_and_feedback` 同项目 task card 以 fresh receipt 恢复；不得直接进入 `audio_animation_runtime_hooks`、build/playtest/audio runtime proof 或 human-review。若恢复后仍失败，必须用新的 adapter stream evidence 归因，不能再用旧外层观测盲点作为结论。
- 2026-04-30 post-repair 产品卡恢复结果：`chinese_ui_panels_and_feedback` 已按新 direct/stream/closure 路径执行 3 次 fresh receipt 续跑，全部失败并已闭合现场。新证据证明不再是“无 provider 输出”：三次分别观测到 909、172、1007 条 `provider_stream_observed`，但没有形成可接受的 changed files / tests / evidence；最终状态是 `blocked_after_three_post_repair_attempts`，证据见 `state/task_card_direct_execution_provider_stream_repair_20260430/post_repair_product_resume_ledger.json`。下一步不得继续无脑第 4 次续跑；必须先拆分或收窄中文 UI/失败复活反馈卡，或修 provider 执行预算/任务粒度，再生成新的 active phase/task card。

## 2026-04-30 Closeout: Task Card Three-Attempt Retry And Output Idle Restart Repair

`Task Card Three-Attempt Retry And Output Idle Restart Repair` 已完成 workflow bug-first 修复。本阶段修复同项目 task-card worker 的异常处理，未继续 Cocos build/playtest/audio/human-review，未声明商业可玩 GO。

- DB task-card run id: `task_card_three_attempt_retry_output_idle_20260430`
- Task-card snapshot: `state/task_card_three_attempt_retry_output_idle_20260430/task_cards.md`
- 当前 phase 只生成 4 张 DB-backed task cards：governance alignment、provider output/material watchdog、same-project three-attempt ledger、repair packet/closeout。
- 三次重试规则：硬前置缺失直接 fail-fast；运行中异常必须先关闭 child run / attempt / worker lease，记录 failure class、attempt、receipt、child run、stdout/stderr tail 和 watchdog state，再用 fresh receipt 续跑同一 task card。连续 3 次运行中失败后才标记 `blocked_after_three_attempts`。
- 输出 idle 规则：`workflow_progress` 只算 control heartbeat，不算 provider output；`last_provider_output_at` 超阈值触发 `provider_output_idle_timeout`；provider 有输出但无 changed files / evidence / tests / artifact 进展超阈值触发 `provider_no_material_progress_timeout`。
- 上游短路规则继续有效：`same_project_worker_patch_go=false` 时，下游 build/playtest/audio/product-depth/human-review 只能写 `blocked_by_same_project_worker` 或 `skipped_due_to_upstream_failure`。
- 本 phase 完成后已回到 `chinese_ui_panels_and_feedback` 同项目产品卡续跑；三次 fresh receipt 尝试均因 `provider_output_idle_timeout` 失败，最终标记 `blocked_after_three_attempts`。后续 direct/stream 修复完成后又进行了三次 post-repair fresh receipt 续跑，最终标记 `blocked_after_three_post_repair_attempts`。继续尝试前必须先做 operator/provider repair、提高/验证执行预算或重新拆卡，不能无脑第四次续跑。

## 2026-04-28 新窗口交接

当前商业小游戏 pipeline 补全任务必须从交接文档继续：

- [Commercial Game Pipeline Handoff](docs/development/commercial_game_pipeline_handoff_2026_04_28.md)
- [Commercial Game Workflow Next Development](docs/development/commercial_game_workflow_next_development_2026_04_28.md)
- [Commercial Game Pipeline Evaluation 2026-04-28](docs/evaluations/commercial_game_pipeline_evaluation_2026_04_28.md)
- [Commercial Game Production Next Development Sequence 2026-04-29](docs/development/commercial_game_production_next_sequence_2026_04_29.md)

2026-04-28 closeout notes:

- Bug-first workflow repairs are complete for route/evidence, progress-aware watchdogs, scheduler lease terminal release, stale scheduler lease repair, parent receipt propagation into orchestration children, and duplicate remote worker callback idempotency.
- OpenCode is not the default repo-mutation route for `from-task-card` patch apply; Codex/OpenCode adapter timeouts now produce structured timeout type, `failure_class`, stream previews, last-output context, mutation result, and recovery guidance instead of an opaque no-patch timeout.
- Unattended execution now has heartbeat evidence for local worker lease renewals and pipeline runs; scheduler-authority leases are released on terminal or human-review states instead of leaving false expired-authority findings.
- Asset modality repair split `voice` / `music` / `sfx`. Commercial Cocos `sfx_place` and `sfx_clear` now use local procedural SFX WAV generation with QA metadata; `voice_reward` remains voice/TTS, and Cocos runtime bindings preserve SFX/voice/music modalities.
- `commercial_game_production` evaluation reached honest final-gate failures with repair packets. Correction: Cocos Creator is installed locally at `C:\ProgramData\cocos\editors\Creator\3.8.8\CocosCreator.exe`; the previous `cocos_creator_exe_missing` result was a pipeline autodiscovery bug when `--creator-exe` was omitted, and that bug is now fixed.
- The older real game attempt `pipeline_061e3703e442` remains `NO-GO`.
- Superseding no-degradation gate v2 review reclassified `pipeline_a41e231c69a4` as historical automated scaffold/build/playtest evidence, not final commercial readiness proof.
- Strict rerun `zero_degradation_rerun_20260428_evidencefix` wrote evidence at `state/long_runs/zero_degradation_rerun_20260428_evidencefix/zero_degradation_rerun_20260428_evidencefix.json` and failed honestly with `commercial_game_no_degradation_failed`. Live LLM role proof passed; missing Cocos ecosystem bridge, same-project worker patch proof, 8 real level goals, visible shop/skin state, audio runtime verification, strict build-exit acceptance, and human player review remain blockers.
- 2026-04-29 zero-degradation Cocos/worker repair: `collect_cocos_ecosystem_bridge_evidence` now produces a project-local Cocos Editor bridge package, trusted bridge-report contract, license/cost manifest, and filesystem-only rejection evidence. Follow-up Cocos ecosystem repair added an unattended bridge runner and verified local Cocos Creator 3.8.8 Editor/AssetDB/Scene/Prefab/Build API evidence in `cocos_bridge_smoke_20260429_145028`; `ecosystem_integration_go` can now pass for the local Editor bridge. `commercial_game_production` task-card worker now uses one persistent Cocos project shell and calls `workflowctl run from-task-card --execute` with receipt-bound Codex patch apply, writing `same_project_patch_ledger.json`; it no longer hands DB task cards to the deterministic Cocos E2E generator. Strict rerun `zero_degradation_cocos_worker_rerun4_20260429` remained `NO-GO`: real assets and live role proof passed, first same-project patch failed with `provider_idle_timeout`, product-depth gates and human player review were absent.
- 2026-04-29 follow-up diagnosis: the latest same-project worker timeout exposed a control-plane repair phase, not a product-content phase. `Provider Watchdog And Upstream Short-Circuit Repair` completed the DB-heartbeat-aware watchdog, child run closure/fresh receipt continuation, fallback-only rejection, and upstream-failure downstream short-circuit. The product resume phase `Same-Project Commercial Gameplay Implementation Resume` is paused again until the 2026-04-30 three-attempt retry control-plane repair is closed.

核心规则：workflow 自己出 bug 时，Codex 可以先做 bug-first 兜底修复；业务 pipeline 补全必须回到 `workflowctl run from-task-card ...` 执行，Codex 只做审阅、兜底和验收。

## 2026-04-28 收束：删除旧 Cocos 模板交付路径

- `commercial_cocos_game` 固定模板流水线不再作为可执行交付入口；调用它只能得到 `legacy_cocos_template_removed` 阻塞结果。
- 后续商业化小游戏必须走 `commercial_game_production` 真实生产管线：统一资料包、单 agent 角色输出、数据库 task card、真实资产生成、task-card worker 实现、玩家 QA、supervisor 和最终商业化验收。
- Cocos empty project 或 E2E scaffold 只能作为底层诊断/启动壳，不能作为商业游戏内容模板，也不能单独证明 `commercial_playable_go`。
- 修复循环必须围绕同一个目标工程做定点修复；不得每次重新生成模板工程来掩盖问题。

## 当前版本说明

- 当前工作状态：`M109` 已作为 pipeline / technical-smoke baseline 接受；2026-04-28 的后续工作是 `commercial_game_production` 与 workflow-wide bug-first 修复，不自动进入 M110 或生成 M110 task card。
- 接受实现基线：M109 已完成统一资料包、单 agent 角色管线、设计/方案输出、多模态路由真相表、DB task-card quality gate、有限 Cocos technical-smoke trial 和 cluster-upgrade review。
- 当前纠偏：Cocos 生产线可生成可检查的本地样机工程，但 `commercial_playable_go` 仍必须依赖真实玩家视角证据；缺少 build/playtest 证据时只能标为样机，不能宣称商业化成品。后续商业小游戏必须走 `commercial_game_production`，并继续保留 workflow receipt、lease、write_set、provider live proof、evidence 和 operator packet 边界。
- 2026-04-29 no-degradation 纠偏结果：`pipeline_a41e231c69a4` 只保留为 gate v1 历史证据；最新严格 run `zero_degradation_cocos_worker_rerun4_20260429` 为 `NO-GO`，不得声明 `commercial_playable_go` 为 true。后续 `cocos_bridge_smoke_20260429_145028` 已补齐真实本地 Editor bridge/API 证据，但商业本体的同项目 task-card patch、产品深度、构建/试玩和人工验收仍未完成。
- 前一产品 active phase：`Same-Project Commercial Gameplay Implementation Resume`。它已完成关卡目标与商店/皮肤两张卡，随后在 `chinese_ui_panels_and_feedback` 上三次 fresh receipt 续跑均因 `provider_output_idle_timeout` 失败；不得提前推进 Cocos build/playtest/human-review phase，也不得声明商业可玩 GO。
- 2026-04-30 本阶段执行进展：`commercial_gameplay_levels` 和 `shop_skin_ownership_visuals` 已通过 DB-backed workflow task-card runs 完成，同项目写入 8 个 distinct level goals、商店/皮肤拥有状态和装备后视觉变化 evidence；`chinese_ui_panels_and_feedback` 在 direct/stream 修复前是 `blocked_after_three_attempts`，修复后三次续跑确认 provider 有大量输出但未产出可接受的补丁/测试/evidence，最终更新为 `blocked_after_three_post_repair_attempts`。按上游短路规则，`audio_animation_runtime_hooks` 和 `feature_evidence_writer_and_phase_closeout` 继续保持 `blocked/skipped_due_to_upstream_failure`，不得继续推进 build/playtest/human-review。
- 商业化生产线 v2 细化设计见根目录 [COMMERCIAL_GAME_PRODUCTION_V2_PIPELINE_DESIGN.md](COMMERCIAL_GAME_PRODUCTION_V2_PIPELINE_DESIGN.md)：它定义 stage 内部 phase graph、资产图、Cocos bridge worker、supervisor repair loop 和 final gate contract；它不是 active task-card 导出，也不自动开启 M110。
- 活跃真相集：`README.md`、`AGENTS.md`、本文件、`docs/milestone_history.md`、`docs/tech-debt-registry.md`、`docs/governance/tech_debt_registry.json`。
- 历史评估、旧路线图、旧计划和生成态 evidence 不保留为活跃工作树文档。需要逐字审计时使用 Git 历史。

本项目仍是个人自用、本地优先的 operator runtime。所有计划、文档和验证都服务于“能否稳定、诚实、可恢复地继续开发”，不服务于公开 SaaS、多租户、公共 onboarding 或第三方托管执行。

## Plan / Milestone / Phase / Task Card

- 一个 plan 应包含多个 milestone。
- 一个 milestone 应包含多个 phase。
- 一个 phase 默认应包含多张 task card。
- task card 是最小可执行单元。
- 开发计划文档只写到 milestone 和 phase，不提前生成 task card。
- 只有 active phase 才生成 task card。
- 单卡 phase 必须显式写入 `single_card_exception` 并说明原因。
- task card 的权威来源是 SQLite `task_cards` 表；Markdown 只作为自动导出的人工快照。
- task card 不得只是任务清单，必须包含 goal、write_set、read_set、test commands、acceptance、evidence requirements、blocking conditions、risk level、model guidance 和 expected artifacts。
- 每个 active phase 默认只导出一份 `state/<milestone_phase>/task_cards.md` 或 `state/task_cards/<run_id>/task_cards.md`；不要生成大量散装 task card 文档。
- 每个 phase 前运行并保存 `plan-graph`、`policy-preview`、`goal-packet`。
- 每个 phase 至少输出 task cards、route evidence、test evidence、operator packet 和 closeout summary。
- 成功 phase 可以 1 phase 1 commit；失败 phase 不提交，只保留 evidence 和恢复指针。

## Bug-First 规则

workflow、dogfood、receipt、probe、evidence、route、repo mutation、test matrix 任一路径出现 bug 时，暂停业务 phase：

1. 生成 workflow bug task card。
2. 修复 workflow bug。
3. 补回归测试。
4. 再恢复原 phase。

## 路由默认值

- OpenAI API 当前不是已配置主路径；OpenAI-family coding 真实入口是 Codex CLI。
- MiniMax / DeepSeek API 可以直接生成 plan、review、patch proposal；需要写仓库时必须通过受控 patch apply。
- simple 杂活：OpenCode + `minimax/MiniMax-M2.7`。
- medium review / validation：DeepSeek V4 Flash，失败直接 fallback Codex。
- complex 架构、安全协议、repo mutation：Codex CLI 或本地补丁兜底。
- MMX/MiniMax 的主要价值是 image / speech / music / future video 资产生成，不是只做文本 evidence。
- Vertex 生成能力走 API/SDK；`gcloud` 只是 Vertex/GCP 认证与环境工具。
- Cloud Text-to-Speech 使用 `gcp_tts_api`；旧 `vertex_tts` 只作为兼容 alias。
- Gemini CLI 暂不接入；Gemini-family 能力短期通过 Vertex/GCP。
- LangChain 是 experimental / opt-in agent framework，不进入默认主路由。

## Capability Truth

- Capability health 必须来自 runtime ledger / live probe，而不是 descriptor 自我声明。
- `verified_ready` 或 `recently_successful` 只能由真实 provider-specific live proof 产生。
- simulated、dry-run、generic greeting、fallback-only、非真实调用不能标记为 ready。
- text evidence、coding proposal、asset generation 必须分开声明。
- 生成类能力必须有真实二进制 artifact、mime、hash 和 evidence。

## 高风险动作边界

以下动作必须使用 scope-bound `OperatorActionReceipt` 或明确的 `AutomationLease`，并在消费时校验实际 request scope：

- `launch_execute`
- `resume_run`
- `approve_run`
- `reject_run`
- `cancel_run`
- `batch_resume_runs`
- repo mutation / patch apply
- watchdog auto-apply
- git commit / push / PR

GET 请求不得触发状态变更。所有文件写入必须解析明确 workspace root。

## Pipeline 规则

- `WorkflowPipeline` 是 `OrchestrationPlan` 之上的 plan-of-plans，不是 cluster 的别名。
- Pipeline preview 不直接 mutation。
- Pipeline run 必须写 stage evidence。
- 未真实执行的 capability stage 必须返回 `blocked`，不得伪装 `completed`。
- 未真实执行的 `agent_role` / `cluster` stage 必须返回 `stubbed` 或 `blocked`，不得伪装 `completed`。
- 后续 `cluster` 不再扩展为独立执行引擎；它只表示角色/能力模板。真正多角色执行应由 LangGraph subgraph 承载，并继续受 workflow 的安全和证据规则约束。
- required dependency 只能由 `completed` 满足；`skipped` 只能满足显式 optional dependency。
- validation command 必须使用 `packages/runtime_security/safe_command_runner.py` 的安全 argv runner，默认 `shell=False`，不得通过 shell metacharacter 绕过审核。
- validation/capability 失败后必须短路后续 stage。
- 复杂写入仍走既有 run/control-plane、receipt/lease、write_set 和 repo mutation 语义。

## Core Domain 边界

- `packages/core_domain` 只应包含 control plane、receipt/lease、workspace/write_set、provider truth、evidence/governance、generic pipeline contract 等通用核心能力。
- Cocos/H5/game executor、commercial asset generator、业务 pipeline template、垂直 QA/playtest runner 不应新增到 `core_domain`。
- 兼容 shim 必须写明 `remove_after_milestone`，默认不晚于 M89，并禁止新代码继续依赖旧路径；延期必须以 shim 命中率或下游迁移 evidence 支撑。
- M105.1 启动前必须先运行 `rg -n "remove_after_milestone" . -g "!state/**"`。如果命中生产 shim，必须先删除，或写明延期 milestone、理由和验证证据；不能把过期 shim 带进新的 Cocos 开发。
- LOC 纪律使用 production/core/file ratchet，不用包含 tests 的总 LOC 作为唯一硬门禁。

## LangGraph 收敛规则

- LangGraph 适合承担状态机、checkpoint/resume、human interrupt、multi-agent/subgraph、repair loop 和 graph observability。
- LangGraph 不得绕过 `OperatorActionReceipt`、`AutomationLease`、workspace root、write_set audit、provider live proof 或 evidence/operator packet。
- M104 后的默认方向是：能用 LangGraph 承载的状态推进、checkpoint、人审暂停、subgraph、repair loop 和 stream evidence，优先用 LangGraph。
- 短期目标不是让 LangGraph 接管全部控制面，而是让 graph-backed executor 服务于 workflow 的安全和证据规则。
- `workflowctl run ...`、`pipeline preview/run`、`capability probe/health`、`test matrix` 必须保持兼容。
- graph-backed phase 仍必须遵守 plan / milestone / phase / task card 四层语义。
- `WorkflowGraphState` 不得成为绕过 workflow 的权威状态源；它必须继续服务于 `OrchestrationPlanGraph`、`WorkflowPipeline` 和 run lifecycle 的关系。
- cluster 与 LangGraph subgraph 的分工是：cluster 定义“需要哪些角色、各自负责什么、何时升级为多人协作”，LangGraph subgraph 定义“这些角色如何执行、交接、审阅和收敛”。旧 cluster runtime 不作为新的主执行路径继续加功能。

## 商业化 Cocos 游戏规则

商业化 H5/Cocos 游戏是正式业务需求，应作为 pipeline 场景承载，而不是新增一堆 `game_*_cluster`。

必须区分：

- 技术 smoke：工程能生成、构建能跑。
- E2E scaffold：有 Cocos 工程、资产绑定和自动试玩 evidence。
- 商业化可玩成品：真实 UI、可用面板、玩法闭环、关卡流程、皮肤/画廊、音频设计、动效反馈、移动端体验都达到玩家可接受标准。

当前结论：

- M78/M79/M83 证明了 Cocos 项目生成、asset factory、Web Mobile build、browser playtest 和 pipeline 模板可以跑通。
- M84 真实试玩反馈确认：当前产物仍是样机级，不具备商业化可玩质量。
- `workflowctl game cocos-e2e --require-commercial` 和 `commercial_game_production` final gate 不能继续只看状态变量或事件覆盖。
- 后续 gate 必须输出 `technical_smoke_go`、`production_scaffold_go`、`commercial_playable_go` 三层结论；`--require-commercial` 必须绑定玩家视角的 `commercial_playable_go`，而 `--require-cocos-ecosystem`、`--live-agent-roles`、`--require-human-player-review` 缺证据时只能 blocked/failed。
- Cocos ecosystem bridge 现在已有项目内 Editor extension 包、unattended runner、trusted report contract 和 license/cost manifest；本地 smoke `cocos_bridge_smoke_20260429_145028` 已证明 Editor/AssetDB/Scene/Prefab/Build API report 可回传并满足 `ecosystem_integration_go`。这只代表本地 Cocos Editor 生态桥接完成，不代表商业游戏本体完成。
- 后续修复重点是可玩性与玩家视角质量，而不是再生成更多 manifest。

## 验证规则

文档变更至少运行：

```powershell
python -m infra.scripts.check_doc_links
```

涉及运行路径、API、UI、验证脚本或活跃真相源时追加：

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite unit
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite core
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite integration
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" validation run --suite full --skip-offline-probe
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" capability probe --provider all --require-live --evidence-dir state/<milestone>/capability_probes
python -m pytest -q
```

## 卫生清理规则

- `state/` 是生成态目录，默认不进入 Git；工作树只应保留 `.gitkeep`、必要的本地 `workflow.db` 和正在使用的短期 evidence。
- 大型 Cocos 工程、APK/HTML 包、pytest 临时目录、旧 evidence、离线验证 scratch DB 都应按需清理。
- `state/.pytest-tmp-workflow/` 是测试临时工作区；`workflowctl test matrix` 成功后会自动删除本次 pytest 临时目录，不影响 `workflow.db`。
- 测试失败时默认保留本次临时目录，方便排查；下一次测试会按 24 小时 TTL 和 256MB 上限清理旧目录。
- 如需临时保留所有测试产物，设置 `WORKFLOW_KEEP_TEST_TEMP=1`；如需调整阈值，使用 `WORKFLOW_TEST_TEMP_TTL_HOURS` 和 `WORKFLOW_TEST_TEMP_MAX_MB`。
- 清理文件不等于清理功能。商业化游戏 pipeline 代码、测试和说明继续保留。
- 删除递归目录前必须确认目标解析后仍在当前 workspace 或明确目标目录内。

## 下一阶段开发计划

- 当前基线：M109 已接受为 pipeline / technical-smoke baseline；2026-05-02/2026-05-03 post-review hardening 已完成 DB lifecycle/fresh execution gate、reference-only evidence reuse、gameplay semantic/product-body gate、source requirement matrix、task-card req_id coverage gate、visible CLI 强制执行、lossless single-agent v2 preservation，以及非商业成品 Cocos product-body baseline bootstrap。
- 当前新增真相：`commercial_game_development_readiness_go=true` 只表示可以安全开始真实商业游戏内容开发；`machine_evidence_go=false`、`human_player_review_go=false`、`commercial_playable_go=false` 仍保持不变。baseline 组件、Cocos bridge、build、playtest、runtime hooks 或 feature coverage 均不能单独证明商业游戏完成。
- 已完成 active phases：`Product Body Runtime And Semantic Trace Implementation`、`Commercial Game Core Content Implementation`、`Commercial Machine Evidence And Player Visible Completion` 均只生成当前 phase DB cards，并保留 `commercial_playable_go=false`。
- 当前完成证据：runtime model / semantic trace / scene-component binding / product-depth / Cocos build 已达到机器证据 GO；中文 UI panel evidence 已纳入 product-depth；human review packet 文件保持 blocked 而非自批。
- 当前剩余 blocker：非 placeholder 资产证明、浏览器可交互 playtest GO、BGM/SFX/audio playback 与 volume toggle 的真实浏览器运行证明。
- Phase preflight：先运行 `plan-graph`、`policy-preview`、`goal-packet`；task card 必须满足 lifecycle `active/approved`、质量字段完整、fresh execution 约束、write_set/read_set/test/evidence 完整，以及 `covered_requirement_ids` 覆盖所需 source `req_id`。
- Next active phase：`Commercial Asset And Browser Runtime Proof Implementation`。该 phase 只生成当前 task cards，优先补齐 asset graph、browser playtest、audio runtime proof；若运行环境不能提供真实 browser/audio evidence，必须 blocked，不能降级为 headless success。
- 后续 handoff：机器证据全过后只能进入 `AWAITING_HUMAN_REVIEW`；无人值守不得设置 `commercial_playable_go=true`。
- Bug-first：workflow、receipt、lease、repo mutation、task-card worker、evidence contract、active truth 或 test matrix 任一路径出问题，先修 workflow bug 并补测试，再继续产品实现。

### Acceptable Detours

M109 以真实工程管线打磨为主线，但不能冻结 workflow 和 LangGraph 底座。每个 milestone 最多允许 1 个 detour，且只能用于：

- workflow bug、receipt/lease、repo mutation、pipeline truth、active truth、provider live proof、安全 command runner、LangGraph runtime blocker。
- 会阻塞当前 milestone 的测试矩阵、evidence、operator packet 或 repair loop 问题。

detour 必须写明原因、范围、write_set、测试命令和 closeout。detour 不能引入新的业务路线，也不能提前生成非 active phase 的 task card。

### M109：统一资料包 + 单 Agent 角色管线试运行

M109 的目标不是直接继续堆 Cocos 功能，也不是全面重构 cluster，而是先把真实工程链路中缺失的“输入整理、角色思考、任务交付、多模态资产、玩家审阅和停止判断”补成可执行管线。

M109 的默认链路：

```text
杂乱输入
→ 统一项目资料包
→ 单 agent 角色链路
→ 高质量 task card
→ workflow worker / capability executor 执行
→ QA / 玩家视角审阅
→ validator / gate
→ supervisor 判断继续、修复、停止，或是否升级 cluster
```

M109 的边界：

- 原始材料不直接丢给各 agent；各 agent 读取整理后的统一资料包和自己的 agent packet。
- 整合阶段不做降级摘要，只做整理、分节、细化、归类和来源标注。
- cluster 先降格为单 agent；只有试运行证明某个单 agent 反复薄弱，才把该角色升级为 cluster template，并用 LangGraph subgraph 执行，而不是回到旧 cluster runtime。
- 多模态 agent 是角色，不是具体模型；图片、语音、音乐和视觉审查按能力类型走 API 主路由。
- supervisor 只做过程监督和停止/修复/升级判断，不接管 workflow 控制面，不绕过 receipt、lease、write_set、provider live proof、evidence 或 gate。

#### M109.0：Pipeline Truth Calibration

- 盘点当前 pipeline 中哪些 stage 真实执行，哪些 `agent_role` / `cluster` stage 仍是 `stubbed` 或 `blocked`。
- 入口命令：`workflowctl pipeline truth-report --template commercial_game_production`。
- 输出 `pipeline_truth_report` 和 `stubbed_stage_inventory`，明确 M109 的实际改造边界。
- 验证 task card 数据库仍是权威源，Markdown 只作为快照导出。
- closeout 必须说明 Cocos 在 M109 中只是试运行场景，不是自动续期的业务主线。

#### M109.1：Unified Project Brief

- 新增 intake / context packaging 层，把 PDF、MD、TXT、DOCX、XLSX、图片和用户 brief 转成统一项目资料包。
- 入口命令：`workflowctl intake package --input <file-or-dir> --output-dir state/<run>/brief_bundle`。
- 文字材料整合进 `project_brief.full.md`，保留完整内容；不允许只保留摘要或截断后的 `excerpt` 作为工作真相。
- 图片和媒体文件存文件系统并按 hash 去重；数据库只存元信息、OCR/多模态描述、来源关系、agent 分发记录和 hash。
- 统一资料包至少包含 `media_manifest`、`source_index`、`intake_manifest` 和每个角色的 agent packet。
- 原始文件可以作为证据和回查入口，但不能成为后续文本 agent 的唯一输入。

#### M109.2：Single-Agent Role Protocol

- 将原 cluster 能力先降格为单 agent：产品玩法、UI/体验、技术方案、多模态生成、task card 生成、QA/玩家视角和 supervisor。
- 入口开关：`workflowctl pipeline run ... --execute-agent-roles`；默认仍把未显式执行的角色 stage 记为 `stubbed`，避免伪装完成。
- 试运行预览：`workflowctl pipeline preview --template commercial_game_production`，旧 `m109_single_agent_cocos` 只保留为兼容别名。
- 建立角色输入、输出、证据和失败格式；角色输出必须是结构化 artifact，不是纯聊天记录。
- 建立角色默认模型档位：supervisor、技术方案和 task card 生成使用强模型；产品、UI、多模态文本判断和 QA 使用中强模型；执行 worker 按任务难度路由；validator 优先使用规则和测试。
- 用户不需要逐个指定每个 agent 的模型；只需要选择质量/速度/成本偏好，或在必要时显式覆盖某个角色。

#### M109.3：Design And Planning Execution

- 让之前占位的策划、设计和方案 stage 真实执行。
- 产品玩法 agent 输出玩法目标、核心循环、关卡/成长和验收口径。
- UI/体验 agent 输出界面流程、面板、移动端体验、可点击路径和玩家反馈要求。
- 技术方案 agent 输出 Cocos 工程结构、文件边界、实现顺序、风险和测试计划。
- 多模态生成 agent 输出资产清单、风格要求、生成优先级和视觉/音频 QA 要求。

#### M109.4：Multimodal API Lane

- 多模态 agent 负责提出资产需求和验收要求，不直接自由选择 provider。
- 默认主路由：图片/UI视觉/角色道具背景走 MiniMax/MMX Generation API；语音走 MiniMax Speech API，必要时 GCP TTS fallback；音乐/音效走 MiniMax Music API；截图审查和视觉 QA 走 Vertex/Gemini visual review API。
- MMX CLI 只保留为兼容、探测和临时证据通道，不作为商业化资产生成主路由。
- 每个生成物必须记录 `artifact_path`、`provider`、`model`、`mime_type`、`sha256`、`prompt_hash`、失败原因和 evidence。

#### M109.5：Task Card Quality Gate

- task card 仍写入 SQLite 权威表，Markdown 只导出 active phase 快照。
- 每张 task card 必须包含 `goal`、`read_set`、`write_set`、`test commands`、`acceptance`、`evidence requirements`、`blocking conditions`、`risk level`、`model guidance` 和 `expected artifacts`。
- task card 生成 agent 必须引用统一资料包和角色输出，不能只把 phase 拆成任务清单。
- 只有 active phase 生成 task card，不提前生成未来 phase 的 task card。

#### M109.6：Cocos Trial Run

- 用一个小目标 Cocos/H5 游戏跑完整链路，验证统一资料包、单 agent 方案、task card、多模态资产、执行 worker、QA 和 gate 是否能接上。
- 重点不是宣称商业化完成，而是验证管线是否比旧链路更会理解、拆解、执行、审阅和返工。
- 试运行必须诚实输出 `technical_smoke_go`、`production_scaffold_go`、`commercial_playable_go`，缺少真实玩家视角 evidence 时不得声明商业化可玩。

#### M109.7：Cluster Upgrade Review

- 根据试运行结果决定哪些单 agent 需要升级为 cluster template + LangGraph subgraph。
- 如果 UI/体验反复弱，升级 UI/体验 cluster template；如果多模态反复弱，升级多模态 cluster template；如果 QA 反复漏问题，升级玩家视角 QA cluster template；如果技术拆分反复错，升级技术方案 cluster template。
- 未暴露明显问题的角色继续保持单 agent，避免提前复杂化。
- closeout 必须给出 `cluster_upgrade_decision`，并说明继续、暂停、外部评估或进入 M110 的理由；任何升级都必须声明对应 subgraph 执行边界、输入输出和 gate。

M109 验收标准：

- 杂乱输入能变成统一资料包，长文字不会被截断降级为唯一工作真相。
- `agent_role` stage 不再只是 `stubbed`，关键角色能产出真实结构化方案。
- task card 质量提升，且权威来源仍是数据库。
- 多模态资产走 API 生成并保存可验收 evidence。
- workflow worker / capability executor 能消费资料包、角色输出和 task card。
- QA/gate 能诚实判断 GO / NO-GO，supervisor 能判断继续、修复、停止或升级 cluster。
# M109 Status Update (2026-04-27)

- Accepted baseline: `M109`.
- M109 is complete: unified project brief, single-agent roles, design/planning outputs, multimodal route truth table, DB task-card quality gate, bounded Cocos technical-smoke trial, and cluster-upgrade review all have evidence.
- Cocos M109 result: `technical_smoke_go=true`, `production_scaffold_go=true`, `commercial_playable_go=false`.
- Do not describe M109 as a commercial playable game delivery. It is a pipeline and technical-smoke milestone.
- Cluster decision: keep single-agent roles. Upgrade only if later evidence shows a specific role repeatedly fails.
- Next work must start with a new active phase and DB-backed task cards; do not auto-create M110 task cards from this document.

## 2026-05-03 Post-M109 Hardening Update

- Current control-plane readiness remains `commercial_game_development_readiness_go=true`; current commercial delivery truth remains `machine_evidence_go=false`, `human_player_review_go=false`, and `commercial_playable_go=false`.
- High-risk commercial `same_project_patch` DB task cards now require `execution_visibility_mode=human_visible_cli_enforced`. A headless run cannot complete those cards unless it records visible CLI metadata and mirrored machine logs.
- Single-agent role outputs now use lossless v2 preservation: roles may preserve and augment source requirements, but they may not delete, merge, rename, or rewrite input requirements. Any `omitted_requirement_ids` blocks execution.
- Unified intake preserves raw source receipts and hashes by default; source count, chunk count, and media count mismatches fail fast.
- Commercial `recompile_run` cannot replace active `commercial_game_production` DB task cards generated by the task-card generation agent.
- The Cocos product-body baseline now contains actual runtime model code and model-transition traces for 10x10 board state, placement, line clear, candidate refresh, game-over, and anti-stall behavior. It still remains `baseline_only=true` and cannot pass commercial final GO.
- QA and supervisor default to red-team blocking behavior for baseline-only, runtime-hook, canvas-only, event-only, feature-flag-only, missing fresh CLI, missing visible CLI, and requirement-omission evidence chains.
- `Commercial Machine Evidence And Player Visible Completion` completed its three visible-CLI DB cards and honestly stayed NO-GO: product depth/build are GO, but asset graph and browser/audio runtime proof remain blockers.
- Next active phase is `Commercial Asset And Browser Runtime Proof Implementation`; it must not pre-generate future phase cards and must not downgrade missing browser/audio evidence to headless success.
