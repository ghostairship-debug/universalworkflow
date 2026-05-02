# Commercial Game Production Next Development Sequence - 2026-04-29

本文档吸收根目录 `universalworkflow_deep_evaluation_report.md` 和 2026-04-29 复核结论，给出下一轮开发顺序。它是 milestone / phase 级开发方案，不是 task-card 导出，不自动开启 M110，也不生成 M110 task cards。

实际执行前必须先打开新的 active phase，并按现有 workflow 规则运行 `plan-graph`、`policy-preview`、`goal-packet`，然后只为 active phase 生成 DB-backed task cards。

## Current Truth

- 最新接受实现基线仍按活跃文档记录为 `M109` pipeline / technical-smoke baseline。
- `commercial_game_production` 是真实商业小游戏生产入口；旧 `commercial_cocos_game` 固定模板入口必须保持 `legacy_cocos_template_removed`。
- Cocos bridge 本地 smoke 已证明 Editor / AssetDB / Scene / Prefab / Build API report 能回传；这只证明本地 Cocos Editor bridge，不证明商业游戏本体完成。
- `commercial_playable_go` 仍为 false。当前阻塞是 same-project task-card patch 稳定性、产品深度、音频/runtime/build/playtest 证据和人工玩家评审。
- 现有 `active-truth-check` 能发现部分过期真相，但还需要扩展，尤其要拦住 README 当前状态标题与 accepted baseline 的口径不一致。

## Operating Rules

- 不把 scaffold、canvas 非空、事件覆盖、HTML/APK 打包成功或 feature flag 写成商业可玩完成。
- 业务 pipeline 补全必须回到 DB task cards、receipt、lease、write_set、provider live proof、evidence、operator packet。
- Codex 直接补丁只用于 workflow bug-first 修复、文档、评估和兜底；商业游戏内容实现默认走 `workflowctl run from-task-card ... --execute`。
- 每个 phase closeout 必须说明 workflow 执行范围、Codex 兜底范围、测试命令、evidence 路径、operator packet 和剩余 blocker。
- 任何 LangGraph-backed execution 都不得绕过 workflow receipt、lease、workspace root、write_set、provider live proof 和 evidence 规则。
- 上游硬失败不得继续推进依赖它的下游阶段。若 same-project worker、provider receipt、真实实现 patch、required build 任一依赖硬失败，下游 build / browser playtest / audio runtime / product-depth / human-review packet 只能标记为 `blocked_by_upstream` 或 `skipped_due_to_upstream_failure`，不得继续尝试证明商业成品，也不得制造一串派生 blocker 冒充独立问题。
- provider timeout 修复必须优先修执行外壳和证据闭环，而不是简单放大 timeout。stdout/stderr 静默但 DB worker heartbeat 正常时，不得直接标记 `provider_idle_timeout`；必须区分 `child_stdout_silent`、`workflow_child_stalled`、`provider_timeout` 和 `provider_execution_failed`。

## Recommended Plan

### Milestone 1: Truth And Gate Calibration

目标：先防误判，再继续生产能力开发。

#### Phase 1.1: Active Truth Check Expansion

目标：扩展 `active-truth-check`，让活跃真相检查覆盖当前复核发现的差距。

范围：

- README current-state title 与 `docs/milestone_history.md` accepted baseline 的一致性。
- `commercial_game_production` / `commercial_cocos_game` truth report 与 README、当前工作流、技术债登记的一致性。
- 根目录评估或设计文档不得宣称 `commercial_playable_go=true`，除非 final gate 和人工评审证据齐全。
- active docs 不得把已落地能力继续写成“待新增”，也不得把 open blockers 写成 repaid。

验收：

- `workflowctl governance active-truth-check --strict` 能拦截上述不一致。
- strict check 输出包含可定位的 file、issue code、detail 和 suggested fix。
- 文档修正后 strict check 通过。

#### Phase 1.2: Legacy Route And Scaffold Guard Ratchet

目标：保持旧模板和 scaffold 诊断路径不可误用。

范围：

- `commercial_cocos_game` 必须继续 hard fail 为 `legacy_cocos_template_removed`。
- `cocos_creator_cli` 作为 production worker 时必须阻断。
- final gate 必须继续拒绝 event-only、filesystem-only、scaffold-only、build-only 证据。

验收：

- 旧模板 truth report 为 `NO-GO`。
- commercial gate negative tests 覆盖 scaffold、filesystem-only bridge、缺人工评审、缺 same-project patch。
- `commercial_game_production` truth report 只说明 stage 可执行性，不被解释为商业可玩完成。

### Milestone 2: V2 Contract Minimal Implementation

目标：把 V2 设计中最能防误判的合同先落成代码和测试。

#### Phase 2.1: Contract Inventory And Schema Boundary

目标：统一合同对象边界，避免每个 capability 自己发明 evidence 字段。

建议合同：

- `AssetGraph`
- `CocosBridgeEvidence`
- `SameProjectPatchLedger`
- `BuildLedger`
- `BrowserPlaytestLedger`
- `CommercialFinalGateEvidence`

验收：

- 每个合同有 schema version。
- 每个合同能表达 `completed / blocked / failed / skipped / stubbed / simulated`。
- required dependency 不得由 skipped、stubbed、simulated 或 filesystem-only evidence 满足。

#### Phase 2.2: Final Gate Evidence Contract

目标：让 final gate 只消费明确证据合同，而不是松散 shared output。

范围：

- gate 输入显式区分 bridge、patch、build、playtest、asset、product-depth、human-review。
- gate 输出保留 `technical_smoke_go`、`production_scaffold_go`、`commercial_playable_go` 三层结论。
- `commercial_playable_go=true` 必须同时满足机器证据与人工玩家评审。

验收：

- 缺任一硬证据时 final gate 为 `NO-GO` 或 `AWAITING_HUMAN_REVIEW`。
- 所有 blocker 能生成 repair packet 或后续 active phase 输入。

### Milestone 3: Same-Project Worker Reliability

目标：解决当前最直接的执行阻塞：same-project task-card patch 在真实 run 中不稳定。

#### Phase 3.0: Provider Watchdog And Fallback Repair

目标：先修 provider / worker 执行外壳，避免活着的 child run 被 stdout/stderr idle watchdog 误杀，也避免失败后 DB 状态悬挂。

范围：

- `run_task_card_patch_via_workflowctl` 的 watchdog 必须读取 DB run events、worker heartbeat、attempt 状态和 lease 状态；stdout/stderr 静默但 DB heartbeat 正常时只能记录 `child_stdout_silent`，不得直接杀为 `provider_idle_timeout`。
- `workflowctl run from-task-card` 在长任务执行期间必须向 stderr 或事件流输出进度心跳，stdout 继续保留最终 JSON，避免外层 wrapper 误判空闲。
- 外层 watchdog 确认卡死并终止 child run 时，必须关闭 child run / current attempt / worker lease，写入 failure evidence，并把 `child_run_id`、attempt id、failure class 回写 patch ledger。
- 真正的 provider timeout 必须触发同 task card、同 project、同 write_set、fresh receipt 的可恢复续跑；fallback 只能使用有 live proof 的真实 provider，不得把 shell/noop/dry-run 当作商业实现成功。
- fallback 执行后仍必须产出 changed files、tests、evidence；否则保持 blocked，不得进入下游 build/playtest。

验收：

- 模拟 stdout/stderr 静默但 DB heartbeat 正常时，task card 不会被标记为 `provider_idle_timeout`。
- 模拟 DB heartbeat 停止时，child run 被关闭为明确失败，ledger 记录 `workflow_child_stalled`、`child_run_id`、attempt、恢复命令。
- 模拟真实 provider timeout 时，续跑使用 fresh receipt，不复用 consumed receipt。
- fallback-only、noop、shell dry-run 不能满足 same-project implementation gate。
- provider/watchdog 修复完成前，不继续产品深度实现 phase。

#### Phase 3.1: Stage-Internal Phase Graph

目标：把大块 gameplay implementation 拆成小 phase DAG，但只为 active phase 生成 task cards。

建议 phase 类型：

- project shell and manifest check
- level-goal implementation
- UI / panel implementation
- shop / skin ownership implementation
- audio runtime implementation
- build / browser verification
- player QA repair

验收：

- stage 内部 phase 能表达依赖关系。
- disjoint write_set 可并发，write_set 冲突自动串行。
- 仍保持 plan / milestone / phase / task card 四层语义。

#### Phase 3.2: Partial Evidence And Continuation

目标：provider timeout 或 worker 中断后，不丢失已经完成的 evidence。

范围：

- `same_project_patch_ledger.json` 记录每张卡的 receipt、changed_files、test status、watchdog、timeout type、continuation command。
- provider idle timeout 必须转成可恢复 blocker，而不是 opaque failure。
- retry budget 和 repair attempts 必须绑定 task card，而不是整条 pipeline 盲重跑。
- worker 或 provider 在当前 task card 上硬失败时，依赖该实现结果的后续 stage 必须短路，不得继续 build/playtest/product-depth 证明；ledger 需要输出 root blocker、blocked downstream stage 列表和恢复命令。

验收：

- 首张卡 timeout 后能保留 partial evidence。
- 续跑从未完成卡继续，不重新生成固定模板工程。
- worker closeout 能明确哪些卡完成、哪些卡 blocked、下一步如何恢复。
- same-project patch 未完成时，final gate 只报告根因和 `blocked_by_same_project_worker` 下游状态，不能把缺失的 browser/audio/product-depth 证据展开成误导性的独立失败。

### Milestone 4: Trusted Cocos Evidence In Production

目标：把已证明的本地 Cocos bridge 能力接入真实 `commercial_game_production` 生产流。

#### Phase 4.1: Bridge Evidence Binding

目标：生产 run 消费可信 Editor bridge report，而不是只看文件系统存在。

范围：

- bridge report 必须证明 Editor API、AssetDB、Scene、Prefab、Build hook。
- license / cost manifest 必须进入 run evidence。
- filesystem-only、CLI-only、playtest-only、feature-flag-only bridge 证据必须阻断 commercial GO。

验收：

- `ecosystem_integration_go` 只代表 bridge 能力 GO。
- final gate 继续要求商业本体证据，不能因 bridge GO 自动 commercial GO。

#### Phase 4.2: Build And Browser Playtest Ledger

目标：把构建和浏览器试玩变成可审计 ledger。

范围：

- Cocos build command、exit code、fatal marker、artifact path。
- HTTP launch、browser console/page errors、screenshot、mobile viewport。
- audio playback、BGM start、SFX trigger、volume toggle runtime proof。

验收：

- build/playtest ledger 可被 final gate 消费。
- 缺 audio 或 browser runtime proof 时 commercial GO 阻断。
- 若上游 same-project implementation 未完成，build/playtest ledger 必须记录 `skipped_due_to_upstream_failure`，不得启动真实构建或试玩来验证一个未完成的商业成品。

### Milestone 5: Product Depth And Player Quality

目标：在控制面和证据面稳定后，再补真实游戏内容深度。

#### Phase 5.1: Product-Depth Feature Gates

目标：把“像商业游戏”拆成可验收产品深度 gate。

范围：

- 8 个 distinct level goals。
- shop / skin ownership state 与装备后视觉变化。
- 可用 UI panel、关卡流程、复活或失败反馈。
- 音频设计、动效反馈、移动端体验。

验收：

- 每项 feature 都有玩家视角 evidence。
- feature coverage 不能只由事件标记满足。
- 自动验证不足时必须进入人工 review packet。

#### Phase 5.2: Human Player Review Loop

目标：把人工玩家评审纳入正式 gate，而不是事后评论。

范围：

- review packet 汇总截图、视频或浏览器证据、音频证据、已知 blocker、repair suggestions。
- 人工评审不通过时生成 repair phase 输入。
- 人工评审通过但机器证据缺失时仍不能 GO。

验收：

- `AWAITING_HUMAN_REVIEW` 与 `NO-GO` 区分清楚。
- final GO 需要 human review evidence 和机器证据同时满足。

### Milestone 6: CI And Retention Hardening

目标：前面证据链稳定后，再把质量保障分层。

#### Phase 6.1: Test Matrix Tiering

建议分层：

- fast core tests：domain、receipt、lease、repo mutation、active truth、pipeline truth。
- integration tests：task-card worker、pipeline run、operator packet、repair loop。
- Cocos tests：bridge、build、browser playtest、runtime media。
- provider contract tests：provider-specific live proof，禁止 simulated / dry-run / fallback-only 误标 ready。

验收：

- fast tests 本地默认可跑。
- Cocos/provider tests 可按环境开关或 nightly 运行。
- CI 文档明确哪些结果能证明什么，哪些不能证明 commercial playable。

#### Phase 6.2: Artifact Retention

目标：避免 `state`、pytest temp、Cocos artifacts 和 evidence 无限膨胀。

范围：

- 成功 run 的保留策略。
- 失败 run 的现场保留策略。
- 大型 Cocos 工程和构建产物的清理规则。
- evidence index 保留必要元信息和恢复指针。

验收：

- 清理不破坏 closeout、operator packet 和 final gate 证据。
- 递归删除必须遵守 workspace 边界检查。

## First Active Phase Recommendation

建议下一次真正进入执行时，先打开一个 active phase：

```text
Provider Watchdog And Upstream Short-Circuit Repair
```

该 phase 只覆盖本次复盘暴露出的两个执行纪律问题：provider/watchdog 误判与上游失败短路。它的目标是修补 task-card worker 的 timeout 判定、child run 失败闭环、fresh receipt 续跑和下游短路 gate，并把这些结果写入 closeout。完成后再恢复产品深度实现或 Cocos build/playtest 证据。

不要一次性为 Milestone 2-6 生成 task cards。Milestone 2-6 只作为后续路线图，等对应 phase active 后再生成 DB-backed task cards。

## Suggested Verification Commands

```powershell
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" governance active-truth-check --strict --output-path state/governance/active_truth_check.json
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" pipeline truth-report --template commercial_game_production
workflowctl --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" pipeline truth-report --template commercial_cocos_game
python -m infra.scripts.check_doc_links
```

Active implementation phases should add targeted pytest commands in their DB task cards. This document intentionally does not prescribe task-card-level write sets for future inactive phases.
