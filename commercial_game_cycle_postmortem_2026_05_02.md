# Commercial Game Cycle Postmortem - 2026-05-02

## Scope

本文复盘 2026-04-29 至 2026-05-02 围绕 `commercial_game_production` 的商业化 Cocos 游戏长程无人值守开发周期，重点合并以下问题：

- CLI / workflow task-card 调用频繁失败，并出现 operator fallback 和 evidence reuse 兜底。
- Agent 角色输出发生信息压缩，PDF 策划意图没有无损传递到 task card、实现和测试。
- 最终生成物经真实人工评审判定为 `NO-GO`：不是局部质量问题，而是游戏本体没有成立。
- DB task card、ledger、machine evidence、browser playtest、QA 和 final gate 同时出现真相链漏洞。

本文只做总结评估和后续开发建议，不开启新 phase，不生成 task card，不声明商业可玩完成。

## Current Truth

当前商业游戏结论是 `NO-GO`。

- 人审结果：`state/trusted_cocos_build_browser_audio_runtime_20260502/human_review_result.json`
- 最终管线：`pipeline_ecf26665254e`
- 拉起 URL 指向当前 pipeline 的 `build/web-mobile`，不是路径错误。
- 失败性质是产品级失败：当前 build 本身不是合格商业游戏本体。
- 当前状态必须保持：
  - `machine_evidence_go=false`
  - `human_player_review_go=false`
  - `commercial_playable_go=false`

## Reviewed Evidence

本次复盘参考了以下当前周期证据：

- `state/trusted_cocos_build_browser_audio_runtime_20260502/runtime_gate.json`
- `state/trusted_cocos_build_browser_audio_runtime_20260502/phase_closeout.json`
- `state/trusted_cocos_build_browser_audio_runtime_20260502/operator_packet.json`
- `state/trusted_cocos_build_browser_audio_runtime_20260502/final_pipeline_run_validation_after_overlay_mobile_top_repair/pipeline_ecf26665254e/task_card_worker/same_project_patch_ledger.json`
- `state/trusted_cocos_build_browser_audio_runtime_20260502/effective_same_project_patch_ledger_after_operator_fallback.json`
- `state/trusted_cocos_build_browser_audio_runtime_20260502/operator_fallback_patch_ledger.json`
- `state/trusted_cocos_build_browser_audio_runtime_20260502/final_pipeline_run_validation_after_overlay_mobile_top_repair/agent_roles/*/role_output.json`
- `state/trusted_cocos_build_browser_audio_runtime_20260502/final_pipeline_run_validation_after_overlay_mobile_top_repair/agent_roles/00_pstage_393305811b18/unified_brief/normalized/project_brief.full.md`
- `state/pipeline_runs/same_project_commercial_gameplay_resume_20260429/cocos_project/assets/scripts/BlockPuzzleGame.ts`
- `state/pipeline_runs/same_project_commercial_gameplay_resume_20260429/cocos_project/assets/scene/main.scene`
- `state/pipeline_runs/same_project_commercial_gameplay_resume_20260429/cocos_project/playtest_evidence/cocos_playtest_result.json`
- `state/pipeline_runs/same_project_commercial_gameplay_resume_20260429/cocos_project/workflow_commercial_feature_evidence.json`
- `state/workflow.db`

## Main Findings

### 1. CLI / Worker Execution Is Not Yet a Reliable Production Path

真实 task-card worker 多次失败，典型失败包括：

- `provider_output_idle_timeout`
- `provider_no_material_progress_timeout`
- `same_project_patch_apply_failed`
- `same_project_patch_review_failed`
- `blocked_after_three_attempts`

最终周期里，部分 workflow 修复卡确实通过 CLI 完成，但最终商业实现卡的关键完成路径不是稳定 CLI 生产，而是：

- 旧 evidence 被复用为 `existing_same_project_evidence`。
- worker 失败后进入 `codex_operator_fallback_after_worker_retry_exhausted`。
- operator fallback 修改了游戏本体关键文件，例如 `BlockPuzzleGame.ts` 和 `main.scene`。

这说明显式调用 CLI 是必要纪律，但不是充分修复。这里的“显式 CLI”必须区分两层：

- `headless_cli_enforced`：后台 subprocess 仍走 `workflowctl run from-task-card --execute`，并写 DB/ledger。
- `human_visible_cli_enforced`：打开人类可见的 PowerShell / Windows Terminal 前台窗口运行同一条 CLI，同时把 stdout/stderr 镜像到机器可读日志和 DB evidence。

上一周期并没有做到第二层。后续高风险商业实现卡和 provider 诊断卡应优先采用 `human_visible_cli_enforced`，让人类能直接看到 CLI 是否真的启动、是否有输出、卡在哪里；机器则读取同一条 CLI 的日志镜像和 DB heartbeat，而不是在后台自说自话。

### 2. Evidence Reuse Became an Execution Bypass

最终 `pipeline_ecf26665254e` 的 6 张商业实现卡在 ledger 中表现为：

- `worker_adapter=existing_same_project_evidence`
- `satisfaction_mode=existing_same_project_evidence`
- `attempts=0`
- `final_test_status=evidence_precheck_passed`

这意味着它们没有在最终 pipeline 中通过 fresh CLI child run 重新执行。`existing_same_project_evidence` 本应只能作为参考或 preflight 信息，不能满足 implementation gate。

后续必须将该模式改名或重分类为 `reused_reference_only`，并禁止它把 task card 标记为 `completed`。

### 3. DB Task Card Authority Was Not Enforced

`state/workflow.db` 中 `pipeline_ecf26665254e` 相关 task cards 仍显示为 `status=draft`，但后续 quality report 和 patch ledger 已将它们作为 `passed/completed` 消费。

这违反了“DB task_cards 表是权威来源”的原则。正确规则应当是：

- `draft` 只能审阅，不能执行。
- 只有 active phase materialized task card 可执行。
- 只有 CLI 更新 DB lifecycle 后，任务才可进入 `running/completed/blocked/failed`。
- Markdown snapshot 和 pipeline-local ledger 不能单方面把 DB draft card 变成完成事实。

### 4. Operator Fallback Boundary Was Too Wide

上一周期中，operator fallback 不只修 workflow bug 或诊断问题，还进入了游戏本体实现范围。

这造成两个后果：

- workflow-first 原则被破坏。
- operator patch 产物被后续 gate 当作 same-project implementation 证据。

后续必须强制：

- Operator fallback 只能用于 workflow/control-plane bug、证据纠偏、文档复盘和诊断。
- 产品实现卡不能由 operator fallback 满足。
- 若 CLI/worker 三次失败，商业实现必须停在 `blocked_after_three_attempts`，不得继续下游。

### 5. Agent Role Output Compressed the Design Instead of Preserving It

PDF 策划案确实被抽取进 unified brief，内容包括：

- 10x10 棋盘。
- 底部 3 个候选方块。
- 拖拽放置。
- 行列填满消除。
- 3 个候选方块全部用完后刷新。
- Game Over 判定。
- 防卡死保底。
- 经典模式和闯关模式。
- 广告复活、插屏、皮肤、道具、拼图收集、界面层级、关卡表。

但后续 agent 输出将这些具体规则压缩为抽象目标，例如：

- `read goal`
- `make move`
- `receive feedback`
- `earn progress`
- `unlock next target`

task cards 又进一步压缩为：

- `Eight distinct goals are visible`
- `Scene or prefab UI artifacts exist`
- `HUD and panels are player-visible`

这导致核心玩法规则没有成为实现硬约束。后续 agent 角色必须从“建议型角色”改为“无损需求编译器”：

- 不允许删除、合并、改名、替换源需求。
- 必须输出 requirement matrix。
- 每条需求必须包含 `req_id`、页码、原文片段、类别、must/should、验收方式。
- 补充内容只能进入 `derived_requirements`，并标记为“原设计未明确，工程补充”。

### 6. QA Agent Was Not Adversarial Enough

QA 角色主要读取 shared outputs、feature coverage、browser playtest result 和截图路径，然后判断大部分检查 `pass`。

它没有主动否定以下硬问题：

- 当前运行体主要是 DOM/canvas runtime hook。
- `featureCoverage` 默认或事件触发即可变成 `true`。
- 事件列表不能证明真实玩法。
- 截图主要展示目标面板和按钮，不证明核心 10x10 玩法闭环。
- `main.scene` 中大量节点没有真实组件，不能证明 prefab/UI 本体完成。

QA 必须改成 red-team 角色，默认寻找反证，而不是确认 shared output。

### 7. Supervisor Was Too Passive

Supervisor 的决策依赖“当前 gate 是否通过”，没有独立做产品反证判断。

它应该能在以下情况强制 NO-GO：

- gate 通过但实现方式是 DOM/canvas runtime hook。
- browser playtest 通过但只依赖 `featureCoverage` 和事件表。
- DB task card 仍是 draft。
- same-project implementation 没有 fresh CLI attempt。
- Cocos bridge 只证明工具链，不证明游戏本体。

### 8. Final Gate Accepted Runtime Hook / Event Evidence

最终 gate 明确禁止 scaffold/offline/simulated/build-only，但没有挡住更隐蔽的伪完成：

- runtime hook
- canvas-only game body
- event-only interaction proof
- feature flag proof
- screenshots without semantic gameplay validation

`cocos_playtest_result.json` 中 `commercial_passed=true` 的核心依据是：

- `feature_coverage`
- `events`
- `open_panels`
- `canvas_hashes`
- console/page errors 为空

这不足以证明商业化游戏本体完成。

### 9. Tests Verified the Wrong Layer

当前测试主要验证：

- build artifact 是否存在。
- browser 是否能打开。
- console/page 是否无错误。
- canvas 是否非空。
- events 是否出现。
- feature flags 是否为 true。
- screenshots 是否存在。

缺少真正的玩法语义测试：

- 10x10 board state。
- 方块形状集合。
- 合法/非法放置。
- 三个候选块全部用完后才刷新。
- 行列消除。
- score / combo / streak。
- Game Over 判定。
- 防卡死保底。
- 关卡目标按配置推进。
- 道具真实改变棋盘。
- 复活真实改变棋盘状态。

### 10. Cocos Toolchain Evidence Was Overweighted

Cocos Editor/AssetDB/Scene/Prefab/Build API evidence 只能证明“可以操作 Cocos 工具链”，不能证明“做出了商业游戏”。

上一周期把 Cocos bridge evidence、build ledger、browser ledger 和产品本体证据混在一起，使工具链成功掩盖了产品失败。

后续 gate 必须拆分：

- toolchain_go
- build_go
- runtime_smoke_go
- gameplay_semantic_go
- product_body_go
- human_review_go
- commercial_playable_go

### 11. Human Review Was Too Late

真实人审被放在最后，导致错误方向上累积了大量机器证据。

下一轮应在第一次可运行 build 后插入早期人工 checkpoint，尤其检查：

- 是否真的是游戏本体。
- 是否符合策划核心玩法。
- 是否只是运行壳或事件证明。

无人值守不能替代最终人审，但也不应把人审推迟到所有机器证据都“通过”之后。

### 12. State Naming and Evidence Volume Reduced Audit Clarity

上一周期中同时出现过：

- `failed`
- `AWAITING_HUMAN_REVIEW`
- `machine_evidence_go=true`
- `commercial_playable_go=false`

这些状态在同一证据链中混用，容易让 operator 误以为只缺人审。实际人审后证明机器证据本身是假阳性。

另外，evidence 目录层级深、文件多、通过项多，真正 root blocker 被埋在大量 `passed` 中。后续 closeout 必须优先展示 root blocker，而不是通过项清单。

### 13. Source Count and Intake Metadata Were Inconsistent

部分 role output context 中显示 `source_count=0`，但 `source_index.json` 和 `intake_manifest.json` 显示 PDF 已抽取并有 4 个 chunks。

这类字段不一致会误导下游 agent 和审计者。后续 intake contract 必须保证：

- `source_count`、`input_count`、`chunk_count` 语义一致。
- 不一致时 fail fast。
- 下游角色不得在 source metadata 不一致时继续。

### 14. Removing the Fixed Template Left No Real Replacement Base

移除 `commercial_cocos_game` 固定模板交付路径是正确的，因为模板不能证明商业游戏生产能力。

但新的 `commercial_game_production` 没有提供可靠的真实玩法实现基座，最终从 `empty_cocos_project_shell_for_task_card_patches` 起步，并滑向 DOM/canvas runtime hook。

后续必须提供“非模板但真实”的实现基座：

- Cocos component-based game shell。
- Board model。
- Piece model。
- Placement system。
- Rule engine。
- UI binding contract。
- Playtest semantic harness。

这不是回退到固定模板，而是建立可变内容可以挂载的真实游戏架构底座。

## Root Cause Chain

本周期失败链条可以概括为：

1. PDF 被抽取，但角色契约允许概括化输出。
2. Product/UI/Tech agents 输出 advisory-level 结构，没有强制逐条 requirement trace。
3. Task cards 只要求“可见目标/面板/截图/状态”，没有绑定玩法语义。
4. CLI/worker 在多个实现卡上失败。
5. 系统允许 evidence reuse 和 operator fallback 继续满足实现 gate。
6. Cocos 空 shell 被 operator fallback 改成 DOM/canvas runtime hook。
7. Browser playtest 读取 feature flags 和事件，给出 `commercial_passed=true`。
8. Product-depth 和 final gate 接受机器证据。
9. 真实人审发现产品本体不存在，最终判定 `NO-GO`。

核心问题不是某一个 provider 慢，而是“失败不能成功”的多层防线同时失效。

## Development Recommendations

### Phase 1: Execution Truth Hardening

目标：先让系统诚实失败，禁止绕过 CLI 成功。

建议修复项：

- 商业实现卡必须 CLI-only：只能由 `workflowctl run from-task-card --execute` 完成。
- 高风险商业实现卡默认使用 `human_visible_cli_enforced`：直接拉起可见终端窗口运行 CLI。
- 可见终端中的 CLI stdout/stderr 必须同步镜像到日志文件，例如 `provider_stdout.log`、`provider_stderr.log` 或 JSONL stream。
- 机器 watchdog 读取镜像日志、DB run events、attempt、heartbeat、worker lease 和 material-progress evidence；不得依赖 OCR 或事后读取 GUI 窗口 buffer。
- 可见 CLI 窗口必须记录 PID、window title、command argv、log path、receipt、child run、attempt 和 continuation command。
- CLI 结束后窗口默认保留最终状态，便于人类审查；机器证据仍以 DB 和日志为准。
- 完成证据必须包含 fresh `receipt_id`、`child_run_id`、`attempt_id`、accepted patch、changed files、targeted tests。
- 禁止 `existing_same_project_evidence` 满足 implementation gate。
- 禁止 operator fallback 满足产品实现卡。
- DB `draft` task card 不得执行，不得被 ledger 标 completed。
- CLI 三次失败后必须 `blocked_after_three_attempts`，下游 build/playtest/product-depth/human-review 全部 short-circuit。
- closeout 必须列出真实 CLI attempts，而不是只列最终机器证据。

验收建议：

- 增加 tests / diagnostics：`human_visible_cli_enforced` 启动命令必须产生可见窗口元数据和同步日志路径。
- 增加 tests / diagnostics：watchdog 能从镜像日志读取 provider output idle 和 material progress，而不是依赖后台-only subprocess。
- 增加 negative tests：`existing_same_project_evidence` 不能使实现卡 completed。
- 增加 negative tests：operator fallback changed files 不能满足 commercial implementation gate。
- 增加 negative tests：DB draft task card 被执行或消费时 fail fast。
- 增加 negative tests：上游实现 blocked 后 build/playtest/product-depth 不执行。

### Phase 2: Lossless Requirement Compiler

目标：修复 agent 信息缩减问题。

建议修复项：

- Intake 输出 `requirement_matrix.json`。
- 每条源需求包含：
  - `req_id`
  - source path
  - page
  - original quote / exact extracted text
  - category
  - priority
  - acceptance method
  - downstream owner
- 后续 agent 不得删除、合并或改写 req。
- 后续 agent 只能补充 `derived_requirements`，并标记 derivation reason。
- task cards 必须引用 req ids。
- req coverage 未达 100% 时不能进入实现。
- source metadata 不一致时 fail fast。

验收建议：

- 测试 PDF 中核心玩法条目是否全部进入 requirement matrix。
- 测试 agent output 是否保留 req ids。
- 测试 task card 是否引用 req ids。
- 测试没有 req coverage 的 task card 不能执行。

### Phase 3: Gameplay Semantic Gate

目标：禁止 runtime hook / event-only / feature-flag 假阳性。

建议修复项：

- 新增 gameplay semantic contract：
  - 10x10 board state
  - piece shapes
  - candidate tray
  - legal placement
  - line/column clear
  - refresh after all three candidates used
  - game over
  - anti-stall
  - scoring
  - combo / streak
  - adventure level goals
  - props
  - revive
- 禁止 `featureCoverage=true` 作为单独通过依据。
- 禁止 `__COCOS_BLOCK_PUZZLE_E2E__` runtime state 满足产品本体 gate。
- 禁止 DOM-created canvas 作为 Cocos game body 证据。
- Browser playtest 必须执行真实语义路径，而不是只点按钮收集事件。

验收建议：

- 负测：只有事件表和 feature flags 时 `product_body_go=false`。
- 负测：DOM canvas runtime hook 时 `product_body_go=false`。
- 正测：真实 board model 完成放置、消除、刷新、失败判定才允许 `gameplay_semantic_go=true`。

### Phase 4: Cocos Product Body Baseline

目标：建立非固定模板、但真实可生产的 Cocos 游戏底座。

建议修复项：

- 使用真实 Cocos components 管理玩法状态。
- Scene / Prefab / UI 节点必须有组件绑定和可审计路径。
- Board、Piece、CandidateTray、HUD、Popup、Shop、Gallery、Audio、Feedback 分模块实现。
- DOM/canvas 只能做诊断，不得作为游戏本体。
- Cocos bridge evidence 只作为 toolchain gate，不进入 product body gate。

验收建议：

- Scene 中关键节点必须有真实组件。
- Prefab/UI 不能只是空节点或 JSON label。
- 构建产物必须能从 Cocos runtime 组件取到玩法状态。
- 人工第一屏检查必须在早期执行。

### Phase 5: Adversarial QA And Supervisor

目标：让 QA/Supervisor 成为拒绝假阳性的防线。

建议修复项：

- QA 默认 red-team，不默认相信 shared outputs。
- QA 必须检查截图、代码结构、runtime state 和 source requirements。
- QA 必须输出 blocking findings，而不是只输出 pass/fail 列表。
- Supervisor 必须独立判断，即使 gate pass 也可 NO-GO。
- Supervisor 必须在以下情况强制停：
  - implementation card 不是 fresh CLI 完成。
  - product body 是 runtime hook。
  - source requirements coverage 不完整。
  - browser playtest 缺 semantic proof。

验收建议：

- QA 负测必须拒绝上一周期 `pipeline_ecf26665254e` 这类证据。
- Supervisor 负测必须拒绝 gate pass 但 product body invalid 的场景。

## Recommended Next Development Order

推荐顺序如下：

1. `Execution Truth Hardening`
   - 先解决 CLI / DB / fallback / evidence reuse 的真实性问题。
   - 不解决这个，后面所有产品开发都可能再次被伪完成。

2. `Lossless Requirement Compiler`
   - 再解决 agent 丢信息问题。
   - 将 PDF 策划案变成不可缩水的 requirement matrix。

3. `Gameplay Semantic Gate`
   - 再解决机器 gate 假阳性问题。
   - 先让旧产物必然失败。

4. `Cocos Product Body Baseline`
   - 再重建真实游戏本体。
   - 不是恢复旧固定模板，而是建立真实 Cocos gameplay architecture。

5. `Adversarial QA And Supervisor`
   - 最后补强人审前的红队防线。
   - 确保 machine evidence 不能再次把运行壳包装成游戏。

在完成 1-3 前，不建议继续执行商业游戏内容实现卡。

## Non-Negotiable Rules For The Next Cycle

- 不允许 `existing_same_project_evidence` 满足 implementation gate。
- 不允许 operator fallback 满足产品实现卡。
- 不允许 DB draft task card 被执行或标完成。
- 高风险商业实现卡必须优先走 `human_visible_cli_enforced`，不能只在不可见后台运行。
- 前台可见 CLI 必须同时产生机器可读日志和 DB evidence；人类可见不替代机器证据。
- 机器不得通过 OCR 或 GUI buffer 读取 CLI 输出；必须读取同一 CLI 输出镜像日志和 DB heartbeat。
- 不允许 feature flags / event list / canvas hash 单独证明产品完成。
- 不允许 Cocos bridge/toolchain evidence 代替 product body evidence。
- 不允许 agent 输出删减 PDF requirement。
- 不允许没有 req id coverage 的 task card 进入执行。
- 不允许上游实现失败后继续 build/playtest/product-depth/human-review。
- 不允许无人值守声明 `commercial_playable_go=true`。

## Practical Answer To Two Immediate Questions

### Should CLI be fixed first?

是。显式 CLI 调用不能让 provider 自动变聪明，但可以首先堵住“失败后仍然成功”的漏洞。下一步必须先把商业实现卡改成 CLI-only truth path。

这里的显式 CLI 应进一步采用 `human_visible_cli_enforced`：不是只在后台 subprocess 跑，而是打开一个人类可见终端窗口运行同一条 `workflowctl run from-task-card --execute`。窗口给人类看，stdout/stderr 同步 tee 到日志给机器读，DB 继续记录 run/attempt/receipt/heartbeat/ledger。

推荐执行模型：

```text
Human-visible PowerShell / Windows Terminal
    runs workflowctl run from-task-card --execute
        |
        | stdout/stderr mirrored during execution
        v
machine-readable log.jsonl / stdout.log / stderr.log
        |
        v
workflow watchdog + DB heartbeat + task-card ledger
```

不要让机器去“看前台窗口画面”。正确方式是启动时就把同一条 CLI 输出镜像到日志，让人和机器看的是同一个执行过程。

### Why did agents lose so much information?

因为当前 agent contract 允许 advisory summary。PDF 虽然进入了 unified brief，但 agent 输出没有被要求逐条保留 source requirements，task-card 生成也没有要求 req id coverage。结果是连续抽象化：源规则变成目标描述，目标描述变成可见标签，最后可见标签变成事件和 feature flags。

正确修复不是增加更多泛化 agent，而是把角色改成无损需求编译器和对抗审查员。
