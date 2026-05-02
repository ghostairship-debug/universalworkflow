# Task Card CLI Observability And Direct Execution Repair 2026-04-30

## Summary

本计划只修 workflow 执行控制面和诊断证据，不继续推进 Cocos 产品实现卡，不进入 build/playtest/audio/human-review，不声明 `commercial_playable_go` 为 true。

当前 `chinese_ui_panels_and_feedback` 三次失败不能简单归因为“Codex provider 8 分钟无输出”。已确认更具体的问题是：`commercial_game_task_worker_cli` 用 `--preset project_delivery` 调用 `workflowctl run from-task-card`，触发了默认 project delivery orchestration；外层 watchdog 只看到 `from-task-card` 的 `workflow_progress` 控制心跳；真实 Codex CLI 输出被内层 `CodexAdapter` 以 `capture_output=True` 捕获，未实时桥接到外层 stdout 或 DB provider stream evidence。因此当前 `provider_output_event_count=0` 只能证明外层未观测到 provider 输出，不能证明 provider 自身没有任何动作。

下一步目标是建立可诊断、可恢复、无降级的单 task-card 执行路径：

- `from-task-card` patch apply 必须默认直接执行单张 task card 的 coder/patch worker，不得隐式展开 planner/coder/research orchestration。
- provider 输出监控必须基于 adapter-level stream evidence 或 DB runtime events，而不是只看外层 wrapper stdout/stderr。
- child run 被 watchdog 终止时，run / runtime task / attempt / worker lease 必须一起闭合，不能留下 `runtime_tasks.status=running`。
- 三次重试策略保留，但必须基于正确的 failure source 和 fresh receipt，不把观测盲点伪装成 provider 真实沉默。

## Confirmed Diagnosis

### Root Cause A: Task Card Worker Entered Orchestration

`run_task_card_patch_via_workflowctl` 对 `issue-receipt` 和 `from-task-card` 都传入 `--preset project_delivery`。`resume_run()` 对 `project_delivery` 会优先执行默认 orchestration plan，于是单张 task card 被展开为 planner / coder / research 子 run。

结果：

- `chinese_ui_panels_and_feedback` 的每次 attempt 都产生了 parent `project_delivery` run。
- 每个 parent run 又产生 optional planner、feature coder、optional research 子 run。
- 这解释了上游失败后出现“额外产出”的现象：它们不是产品下游 phase，而是被误触发的 orchestration child runs。

### Root Cause B: Outer Watchdog Watches The Wrong Stream

`from-task-card` 执行期间只每 30 秒向 stderr 输出 `workflow_progress`。这些是 control heartbeat，不是 provider output。

`CodexAdapter.launch()` 启动 `codex exec --json --output-last-message ...`，但使用 `capture_output=True`。真实 Codex stdout/stderr 只在 adapter 完成后进入 `ExecutionResult`，没有实时转发给 parent `from-task-card` 进程，也没有写入 DB provider stream event。

结果：

- 外层 task-card wrapper 的 `provider_output_event_count=0` 是“外层未收到 provider stream”的事实。
- 它不能区分 `codex exec` 真无输出、Codex 正在长时间工作、Codex JSONL 被内层捕获但未转发、或 orchestration 子 run 正在阻塞。

### Root Cause C: Closure Evidence Is Incomplete

外层 watchdog 终止 child workflow 后，会更新 `runs`、`runtime_attempts` 和 `worker_leases`，但历史证据显示对应 `runtime_tasks.status` 仍可能保持 `running`，且没有 `runtime_task_completed` / evidence。

结果：

- DB 里可以看到 run failed、attempt closed、lease released。
- 但 runtime task 仍像悬挂任务，后续诊断容易误判。

## Development Principles

- Bug-first：本阶段只修 workflow / receipt / evidence / route / repo mutation / test matrix，不继续业务产品卡。
- No degradation：不得用 shell/noop/dry-run、filesystem-only、event-only、fallback-only 伪装 task-card implementation 成功。
- DB-first：task card 权威来源仍是 SQLite `task_cards` 表；本计划文档不生成 task cards。
- Active phase only：实施时只打开一个 active phase，不生成未来 phase 的 DB task cards。
- Same project：后续恢复产品卡时仍必须在同一个 Cocos project 内续跑，不重新生成固定模板工程。
- Fresh receipt：任何重试都必须 fresh receipt，不复用 consumed receipt。
- Upstream short-circuit：单卡 implementation 未完成前，下游 build/playtest/audio/product-depth/human-review 只允许 blocked/skipped。
- No commercial GO：无人值守和机器证据不能替代真实人审，不得声明 `commercial_playable_go` 为 true。

## Milestone 1: Reproducible Diagnosis And Evidence Baseline

目标是先把这次问题变成可重复诊断证据，而不是马上改阈值。

### Phase 1.1: Historical Run Forensics

- 固化 `chinese_ui_panels_and_feedback` 三次失败的 parent run、orchestration child runs、attempt、receipt、lease、runtime task 状态。
- 导出最小诊断包：run timeline、event counts、runtime task terminal state、worker lease state、stdout/stderr tail、ledger attempts。
- 明确哪些 evidence 是真实 provider output，哪些只是 control heartbeat。

验收：

- 诊断包能说明 `provider_output_event_count=0` 的观测边界。
- 诊断包能列出被误触发的 orchestration child runs。
- 诊断包不得把现有三次失败改写成商业实现证据。

### Phase 1.2: Stream Boundary Regression Test Design

- 增加测试覆盖：外层 wrapper control heartbeat 不等于 provider output。
- 增加测试覆盖：内层 adapter capture output 未桥接时，outer provider output idle 不能被解释为 provider 真沉默。
- 增加测试覆盖：task-card patch run 不得产生 planner/research orchestration child runs。

验收：

- 测试先能复现当前观测盲点。
- 失败断言指向具体边界，不依赖长时间 sleep。

## Milestone 2: Direct Task-Card Patch Execution

目标是修掉最根的入口偏差：单 task card patch apply 不应进入 project delivery orchestration。

### Phase 2.1: Direct Execution Contract

- 为 `workflowctl run from-task-card --execute` 明确 direct patch contract。
- 当存在 task-card mutation contract / `task_card_ref` / patch apply write_set 时，必须直接走 repo mutation path。
- `commercial_game_task_worker_cli` 不得再用 `project_delivery` 触发多角色 orchestration；应使用单卡执行 preset 或显式 direct flag。
- 如果确实需要 orchestration，必须由单独命令或显式参数开启，不能是 task-card patch 的默认行为。

验收：

- 单张 task card 执行只创建一个 implementation child run。
- 不生成 planner / research child runs。
- receipt scope、write_set、read_set、test commands 仍被校验。

### Phase 2.2: Orchestration Guard

- 在 lifecycle 层增加 guard：repo mutation + task-card contract 不得隐式进入 default orchestration。
- 如果用户或代码同时请求 task-card patch 和 project orchestration，必须返回明确 blocker，例如 `task_card_patch_orchestration_conflict`。
- 保留 `project_delivery` 的正常多角色编排能力，但它不能吞掉 task-card worker 的最小执行语义。

验收：

- `from-task-card` patch apply 与 `project_delivery` orchestration 的边界可由测试证明。
- 不破坏普通 `pipeline run --template commercial_game_production` 的高层 orchestration 入口。

## Milestone 3: Adapter-Level Provider Stream Evidence

目标是把真实 provider 过程暴露给 DB 和 watchdog，而不是依赖外层 stdout。

### Phase 3.1: Subprocess Stream Callback

- 扩展 `run_subprocess_with_tree_timeout`，支持 `on_output(stream, line, timestamp, classification)` callback。
- callback 必须能区分 control output、provider output、material progress。
- callback 不能记录 chain-of-thought；只记录 CLI JSONL event metadata、stderr/stdout tail、event type、timestamp、byte counts、material tokens。

验收：

- fake subprocess 可实时产生 provider stream event。
- stdout/stderr capture 仍能完整返回最终 `ExecutionResult`。
- 旧 adapter 未接 callback 时行为兼容。

### Phase 3.2: Codex Adapter Stream Bridge

- `CodexAdapter.launch()` 将 `codex exec --json` 的 JSONL/stdout/stderr 行写入 DB runtime events 或 adapter stream ledger。
- 至少记录：provider process started、provider output line count、last provider output timestamp、last provider event type、last material progress timestamp、artifact path。
- 不记录模型思考链，不依赖不可获取的 hidden reasoning。

验收：

- `from-task-card` 进度探针能从 DB 读到 adapter-level `last_provider_output_at`。
- outer wrapper 的 provider idle 判断基于 DB adapter stream，而不是只基于 `workflow_progress`。
- 若 Codex CLI 真实无任何 provider stream，才触发 `provider_output_idle_timeout`。

## Milestone 4: Watchdog Classification And Closure Integrity

目标是让 timeout 分类反映真实来源，并保证被关闭现场可恢复。

### Phase 4.1: Failure Classification Repair

- 保留现有分类，但修正来源：
  - `wrapper_output_idle_timeout`：外层 wrapper 没有输出，不能当作 provider timeout。
  - `provider_output_idle_timeout`：adapter-level provider stream 超阈值无输出。
  - `provider_no_material_progress_timeout`：adapter 有输出但无 changed files / evidence / test / artifact 进展。
  - `workflow_child_stalled`：DB heartbeat / lease / attempt 不再更新。
  - `provider_timeout`：provider adapter 自身返回 timeout。
- `workflow_progress` 继续只算 control heartbeat。

验收：

- stdout/stderr 静默但 DB adapter stream 正常，不触发 provider timeout。
- DB heartbeat 正常但 adapter stream 长期无 provider output，触发可恢复 provider output idle。
- DB heartbeat 停止，触发 workflow child stalled。

### Phase 4.2: Child Closure Repair

- `_close_child_workflow` 必须闭合 run、runtime task、runtime attempt、worker lease、runtime claim / scheduler lease。
- 写入 closeout event 时包含 child run id、runtime task id、attempt id、lease id、receipt id、failure class、continuation argv。
- 若存在 nested orchestration child runs，也必须按同一规则闭合，但后续 direct task-card path 应避免产生这些 nested runs。

验收：

- 被 watchdog 终止后，DB 中不再出现同一 run 的 `runtime_tasks.status=running`。
- repair packet 能给出 fresh receipt 续跑命令。
- 不删除历史 evidence，不伪造 `runtime_task_completed`。

## Milestone 5: Retry Policy Recalibration And Product Resume Gate

目标是保留三次重试原则，但只在诊断来源可信后恢复产品卡。

### Phase 5.1: Three-Attempt Retry Rebinding

- 三次重试仍以 `task_card_id` 为单位。
- 运行中异常才重试；硬前置缺失继续 fail-fast。
- 每次失败必须 fresh receipt、同项目续跑、保留 adapter stream evidence。
- 未满三次失败不得推进下游；三次失败后才 `blocked_after_three_attempts`。

验收：

- 第 2 次或第 3 次成功时，consecutive failure count 清零并推进下一张卡。
- 三次失败后只阻塞根 task card，并短路下游。
- repair packet 只报告根因和 blocked downstream，不展开派生 blocker 噪音。

### Phase 5.2: Safe Product Resume Decision

- 只有 direct task-card execution、adapter stream evidence、closure integrity、retry tests 全部通过后，才能恢复 `chinese_ui_panels_and_feedback`。
- 恢复时必须继续使用原 same-project Cocos project 和原产品 phase task-card pack。
- 不允许直接进入 audio/build/playtest/human-review。

验收：

- 恢复前 operator packet 明确说明前置修复证据路径。
- 恢复后若 `chinese_ui_panels_and_feedback` 仍失败，只能根据新 stream evidence 归因。

## Required Tests

最低测试集：

```powershell
python -m pytest tests/test_pipeline_and_automation_cli.py -q
python -m pytest tests/test_commercial_game_evidence_contracts.py -q
python -m pytest tests/test_active_truth_check.py -q
python -m infra.scripts.check_doc_links
python -m apps.operator_cli.main governance active-truth-check --strict
python -m apps.operator_cli.main pipeline truth-report --template commercial_game_production
python -m apps.operator_cli.main pipeline truth-report --template commercial_cocos_game
```

新增/更新测试必须覆盖：

- `from-task-card` patch apply 不触发 default project orchestration。
- `project_delivery` 普通 orchestration 入口仍可用。
- control heartbeat 不计入 provider output。
- adapter-level provider stream 正常时，outer wrapper 不触发 provider output idle。
- provider stream 真空闲时，fresh receipt 重试，未满三次不标 blocked。
- 三次连续运行中失败后才 `blocked_after_three_attempts`。
- watchdog closure 后 run / runtime task / attempt / lease 都 terminal。
- shell/noop/dry-run/fallback-only 不能满足 same-project implementation gate。
- 上游 implementation 未完成时 build/playtest/audio/product-depth/human-review 不执行。

## Operator Closeout Requirements

本修复阶段完成时必须产出：

- DB-backed active phase task cards snapshot。
- Historical diagnosis packet。
- Route evidence。
- Adapter stream evidence sample。
- Retry ledger。
- Child closure integrity report。
- Test evidence。
- Operator packet。
- Normalized repair packet。
- Phase closeout。
- 下一步是否恢复 `chinese_ui_panels_and_feedback` 的明确 GO/NO-GO。

## Non-Goals

- 不继续实现 `chinese_ui_panels_and_feedback`。
- 不推进 `audio_animation_runtime_hooks`。
- 不推进 Cocos build/playtest/browser/audio runtime proof。
- 不生成 human player review packet。
- 不生成未来 phase task cards。
- 不自动 commit / push / PR。
- 不把缺真实人审写成商业 GO。

## Next Activation

建议下一次实现时只打开一个 active phase：

`Task Card Direct Execution And Provider Stream Observability Repair`

该 active phase 启动后再生成 DB-backed task cards。计划文档本身不提前生成 task cards。
