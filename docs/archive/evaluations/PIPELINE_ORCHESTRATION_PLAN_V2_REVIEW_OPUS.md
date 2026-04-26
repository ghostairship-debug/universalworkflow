# Pipeline Orchestration Refactor Plan V2 评估报告（Opus）

- 日期：2026-04-26
- 评估对象：[PIPELINE_ORCHESTRATION_REFACTOR_PLAN_V2.md](PIPELINE_ORCHESTRATION_REFACTOR_PLAN_V2.md)（1253 行，今天 14:13）
- 评估者：Claude Opus 4.7
- 评估方式：方案全文阅读 + 与 [M73_PREFLIGHT_AND_CAPABILITY_PLAN.md](M73_PREFLIGHT_AND_CAPABILITY_PLAN.md)、[M73_PREFLIGHT_EXECUTION_REPORT.md](M73_PREFLIGHT_EXECUTION_REPORT.md)、[AGENTS.md](AGENTS.md) 对账，加现有 `OrchestrationPlan` / `OrchestrationEngine` / `cluster_router` 实测交叉验证
- 与既有评估的关系：本文不重复 [PROJECT_DEEP_EVALUATION_M73_OPUS.md](docs/archive/evaluations/PROJECT_DEEP_EVALUATION_M73_OPUS.md) 已经讲过的总 LOC / closeout gate / scheduler 隔离结论，重点放在 **Pipeline V2 方案本身的判断**

## 0. 一句话总评

> **方向对、自我修正健康、但与 M73 已吸收的能力层路线直接冲突，且没回答"WorkflowPipeline 与现有 OrchestrationPlan 是什么关系"这个根问题**。如果照搬实施，会引入第三套图模型（OrchestrationPlanGraph + LangGraph StateGraph + WorkflowPipeline）和两条互不兼容的 M73 路线（Pipeline §11 vs preflight §5）。需要先做 v3 修订再开工。

## 1. V2 方案做对的（不要动）

V1 → V2 的修正非常健康，必须先肯定：

| 修正 | 价值 |
| --- | --- |
| **拒绝 game_* cluster 增殖**（§0.1） | 避免了把单一业务硬编码进 cluster taxonomy；这是项目最大的认知漂移风险 |
| **Pipeline = 多种执行单元的有序编排**（§0.2） | 把 stage_type 从"只能是 cluster"扩展到 7 种，是更准确的产品语义 |
| **支持 manual / ai_generated / hybrid 三种来源**（§0.3） | hybrid 是真实使用模式（AI 起草 + 人工调整 + 确认执行），承认这个比假设全自动更诚实 |
| **明确 LangGraph 不替代产品语义**（§0.4） | 与 [LONG_TERM_ROADMAP_REVIEW_OPUS.md](docs/archive/evaluations/LONG_TERM_ROADMAP_REVIEW_OPUS.md) 已建立的"领域协议自研、基础设施让渡"原则一致 |
| **PipelineAdjustment 作为一等对象**（§4） | 审计 AI 生成 → 人工调整的 diff，是真正用得到的设计 |
| **PipelineHandoff 结构化**（§5） | 避免下一 stage 读杂乱上下文，强制接口约束 |
| **stage 到 LangGraph node 映射表**（§7） | 7 种 stage_type 都有 wrapper 路径，思考完整 |
| **业务差异走 stage_profile / domain_context**（§9.3） | 防止业务方向继续派生 cluster_template，是正确的扩展模式 |

## 2. 关键问题（按优先级排）

### P0 — 必须修，否则方案无法落地

#### 问题 1：Pipeline §11 的 M73A/B/C/D 与 preflight §5 的 M73A/B/C/D/E **直接冲突**

**事实**：
- M73_PREFLIGHT_EXECUTION_REPORT.md（今天 13:45 生成、已经 GO）明确推荐 M73 路线：
  ```
  M73A Capability Enforcement Pilot
  M73B MCP Broker v1
  M73C AutomationLease v0
  M73D LangGraph Real-Runtime Spike
  M73E Manifest V2 Provenance
  ```
- Pipeline 方案 §11 用 **同样的 M73A-M73D 编号** 装了完全不同的内容：
  ```
  M73A 语义和文档收口
  M73B Pipeline contracts
  M73C Pipeline preview
  M73D Pipeline adjustment
  ```

**问题**：
- 同一个 milestone 编号，两个不兼容的内容
- Codex 启动 M73A 时，到底是做 Capability Enforcement 还是 Pipeline 语义？
- preflight 已经声称"GO for capability-layer development"，但 Pipeline 方案要把 M73 改回"语义和文档收口"——**等于撤回 GO**
- AGENTS.md 完全没提 Pipeline 方向

**影响**：
- 实施开始第一天就会卡在"先做哪条"
- 如果 Codex 看 Pipeline 方案先开工，preflight 已吸收的 GPT 路线（capability enforcement、MCP broker、automation lease）会被搁置
- 反过来如果先做 preflight 路线，Pipeline 方案要等 M74+

**修复建议**：Pipeline 方案重新编号为 **M74-M76**（或合并进 M73 但与 capability 路线**串行明示**）：
- M73A-M73E：Capability 路线（preflight 已定）
- **M74A** Pipeline 语义和文档收口
- **M74B** Pipeline contracts
- **M74C** Pipeline preview
- **M74D** Pipeline adjustment
- **M75A** LangGraph pipeline execution spike（合并 preflight M73D + Pipeline M74A，这是同一件事）
- **M75B** 最小串行 Pipeline Execution
- **M76** H5 pipeline v1

或者，更激进的方案：**Pipeline 路线优先级 < Capability 路线**，Pipeline 方案推迟到 M74+，本次只接受 §0 的概念修正、§9.3 的"不增殖业务 cluster"原则；M73 仍按 preflight 走。

---

#### 问题 2：WorkflowPipeline vs OrchestrationPlanGraph 关系未定义

**事实**：项目已有完整的图模型：
- `packages/contracts/` 有 `OrchestrationPlan` / `OrchestrationPlanGraph` / `OrchestrationGraphNode` / `EdgeSpec` / `BarrierSpec` / `RetryPolicy`
- `packages/core_domain/orchestration_engine.py` 把 `OrchestrationPlan` 转成 `OrchestrationPlanGraph`
- `packages/core_domain/services.py` 有 `get_run_orchestration_plan_graph` / `preview_orchestration_plan_graph`
- M68 又引入 LangGraph StateGraph（advisory only）

Pipeline 方案 §2.4 提议新增 `WorkflowPipeline` schema，但**完全没回答**：
- WorkflowPipeline 替代 OrchestrationPlanGraph 吗？
- 还是两层并存（pipeline 层 → 编译为 plan graph 层 → 执行为 LangGraph）？
- PipelineStage 等于 OrchestrationGraphNode 吗？还是更高层抽象？
- 现有 evidence / operator_packet / pr_ready_summary 怎么扩展支持 pipeline_id？
- 现有 cluster execution（cluster member_specs）和 Pipeline 的 cluster stage 是什么关系？cluster 内部仍走 OrchestrationPlan，外部走 Pipeline？

**为什么这是 P0**：
- 这正是 GPT Pro 当初批评的"双状态源"反模式的**延伸到三套**：OrchestrationPlanGraph + LangGraph StateGraph + WorkflowPipeline
- 每加一层图模型，evidence / receipt / mutation contract 都要扩展支持
- 不解决这个问题，M74B "Pipeline contracts" 会和现有 contracts 直接撞墙

**修复建议**：在 v3 中加一节 **§14 Pipeline 与 OrchestrationPlan 关系**：

可能的三种方案：
- **方案 A：Pipeline 是更高层抽象**——一个 WorkflowPipeline 编译成多个 OrchestrationPlan（每个 stage 一个 plan）；现有的 single-plan run 是"单 stage pipeline"的特例
- **方案 B：Pipeline 替代 OrchestrationPlan**——彻底迁移，OrchestrationPlan 进入 deprecated；迁移成本最大
- **方案 C：Pipeline 与 OrchestrationPlan 并存但不混用**——pipeline_run 走新模型，run 走旧模型；两套独立 evidence

我倾向 **方案 A**，因为：
- 不破坏现有 run 行为
- WorkflowPipeline 是"plan of plans"，符合 §0.2 的"Pipeline-of-Execution-Units"
- 单 stage pipeline 自动等价于现有 run，零迁移
- 但需要 v3 中明确这点，并说明 evidence / receipt 如何扩展

---

### P1 — 应该修，会显著影响落地体感

#### 问题 3：H5 游戏作为 Pipeline 核心驱动需求过窄

**事实**：
- §8 H5 游戏 pipeline 是 v1→v2 修正的核心展示
- §11 M75 直接做 H5 pipeline v1
- 但 AGENTS.md 明文："本仓库是个人自用 / local-first agentic workflow runtime"
- 用户 user memory：小白 / 个人开发者
- 真实高频使用：workflow 修 workflow（M67-M72 dogfood）、本地 task card、PDF→artifact

**问题**：把 H5 游戏作为 Pipeline 的核心驱动，可能让 Pipeline 设计**过度适配单一场景**。M75 直接做 H5 v1 而不是先做"workflow 自开发 pipeline"是错过更高价值的应用——后者每天都用，前者偶尔演示用。

**修复建议**：在 v3 §8 之前加一节"先做 workflow_self_development_pipeline"：
```
Stage 1: capability live probe
Stage 2: closeout gate runner
Stage 3: code change（codex / opencode）
Stage 4: targeted test
Stage 5: full validation
Stage 6: evidence + manifest update
Stage 7: operator approval
```

把这个作为 M75A，H5 pipeline 推到 M75B 或 M76。"自己用得到"先于"对外演示"。

---

#### 问题 4：三种来源（manual/ai_generated/hybrid）实施顺序未明确

**事实**：
- §3 列了三种来源很好，但 §11 的 M73C "Pipeline preview" 写："manual draft preview / template draft preview / ai-generated draft preview / hybrid adjusted preview"
- 等于 M73C 一个 phase 同时实现 4 种生成路径

**问题**：四种 draft 生成路径的实现复杂度差距很大：
- manual：最简单，CLI 输入 stages 即可
- template：次简单，载入预定义 yaml/json
- ai_generated：中等，需要 chat workbench 接 LLM 生成 draft
- hybrid：最复杂，需要 ai_generated 先做完 + adjustment 协议

一个 phase 同时做 4 个等于"什么都做不深"。

**修复建议**：在 v3 §11 把 Pipeline preview 拆成 4 个独立 phase：
- M74C-1 manual preview（最先）
- M74C-2 template preview
- M74C-3 ai_generated preview
- M74C-4 hybrid preview（依赖 -3 + adjustment）

或者承认"先只做 manual + template"，ai_generated/hybrid 推到下一个 M。

---

#### 问题 5：execution_mode 路由（§10）和现有 cluster_router 的关系未说

**事实**：
- §10 提议 routing：`single_agent / single_cluster / pipeline_template / ai_generated_pipeline / manual_pipeline / hybrid_pipeline`
- 当前 `cluster_router.py` 178 行是 marker keyword → cluster 路由
- 当前已有 dynamic cluster routing（M45/M46）能 route 多 cluster

**问题未答**：
- "execution_mode" 是新顶层概念吗？还是 cluster_router 升级？
- 谁决定 single_agent vs single_cluster？是新 router 模块还是 cluster_router 扩展？
- 现有的 dynamic multi-cluster routing 算 single_cluster 还是 pipeline？
- 用户输入 "实现一个受控能力切片" 应该 route 到哪个 execution_mode？

**修复建议**：在 v3 §10 加 sub-section "10.x Migration from cluster_router"，明示：
- cluster_router → workflow_router（升级）
- 旧的 marker → cluster 仍保留，作为 single_cluster 路径
- 新增 execution_mode 决策放在 cluster 选择**之前**
- workflow_router 输出 execution_mode + 对应的 plan/pipeline reference

---

#### 问题 6：PipelineAdjustment 审计模型对个人自用过重

**事实**：§4 PipelineAdjustment 字段：
```python
adjustment_id, operation, target_stage_id, before, after, rationale, operator_id, created_at
```

**问题**：
- `operator_id` 假设多用户（项目明确单租户）
- `rationale` 强制要求会成为摩擦点（个人改自己 pipeline 每次写理由很烦）
- `before` / `after` 完整 diff 对小调整过重

**修复建议**：v3 把这些字段标 optional：
```python
class PipelineAdjustment:
    adjustment_id: str
    operation: ...
    target_stage_id: str | None
    diff_summary: str  # 简化的 "changed adapter from codex to opencode"
    before: dict | None  # optional, only when policy preview detects high-risk
    after: dict | None
    rationale: str | None  # optional, required only for high-risk operations via receipt
    operator_id: str | None  # default "local_operator"
    created_at: datetime
```

只在 high-risk operation（如改 write_set 范围、跨过 receipt scope）时强制 rationale。

---

#### 问题 7：M74A LangGraph spike 与 preflight M73D 完全重复

**事实**：
- Pipeline 方案 §11 M74A："non-mutating LangGraph checkpoint/interrupt/resume spike"
- preflight §5 M73D："LangGraph Real-Runtime Spike, non-mutating, Plan -> Review interrupt -> Resume -> Evidence"

这是同一件事。如果两条路线都执行，会做两遍。

**修复建议**：v3 §11 M74A **删除**，注明"已合并进 preflight M73D"。Pipeline 方案 M74B "最小串行 Pipeline Execution" 直接用 M73D 已经验证的 LangGraph spike 做 plumbing。

---

### P2 — 可以修，让方案更耐用

| # | 问题 | 修复 |
| --- | --- | --- |
| 8 | §1.2 把 dev/design/multimodal 等 cluster 描述为"主要适合 workflow 自开发"——但它们本来就是 M42 引入的业务集群 | 删除"主要适合"二分法，只描述客观能力 |
| 9 | §2.4 WorkflowPipeline schema 缺 `run_id` / `parent_pipeline_id` / `schema_version` 等关联字段 | v3 加上 |
| 10 | §7 stage→LangGraph node 映射的 `human_checkpoint = interrupt()` 没核实 LangGraph 1.x 真实 API | v3 给出具体调用：`langgraph.checkpoint.interrupt` 还是 `interrupt_after` 配置 |
| 11 | §7 `validation_gate` / `external_worker` 是异步操作，但 LangGraph node 默认同步 | v3 说明：是 wrap 成 sync wait？还是用 LangGraph async node？|
| 12 | §12 Codex 提示词没说"如何处理已有 OrchestrationPlanGraph" | v3 加一句"do not modify existing OrchestrationPlan; treat WorkflowPipeline as higher-level abstraction" |
| 13 | §9 cluster 二分法（Internal vs Support）过于简化 | v3 改为列每个 cluster 的"主要 use case + 兼容 use case"，避免误读 |
| 14 | 没有"Pipeline 失败回滚"章节 | v3 加 §x：stage failure 时如何 rollback 之前已完成 stage 的 mutation；如何 restore_workspace_snapshot |
| 15 | 没有 Pipeline 与现有 receipt 协议的对接 | v3 加 §x：launch_pipeline 是否需要 receipt？哪些 stage 内部动作触发 receipt？|

## 3. 与 M73 PREFLIGHT 路线的合并建议

**当前状态**：
- preflight 已 GO，路线为 M73A-M73E（Capability Enforcement / MCP Broker / AutomationLease / LangGraph spike / Manifest V2）
- Pipeline 方案要重新装 M73A-M73D（语义 / contracts / preview / adjustment）

**合并建议**：

```
M73 (preflight 路线，不动)
  M73A Capability Enforcement Pilot
  M73B MCP Broker v1
  M73C AutomationLease v0
  M73D LangGraph Real-Runtime Spike  ←  Pipeline 方案 §11 M74A 合并到这里
  M73E Manifest V2 Provenance

M74 (Pipeline 方案路线，重新编号)
  M74A Pipeline 语义和文档收口  ← 原 Pipeline §11 M73A
  M74B Pipeline contracts        ← 原 Pipeline §11 M73B
  M74C Pipeline preview (manual + template only)  ← 原 Pipeline §11 M73C 拆一半
  M74D Pipeline adjustment       ← 原 Pipeline §11 M73D
  M74E Pipeline preview (ai_generated + hybrid)  ← 原 Pipeline §11 M73C 另一半

M75 (Pipeline 执行)
  M75A workflow_self_development_pipeline v0  ← 新增，本评估推荐
  M75B 最小串行 Pipeline Execution            ← 原 Pipeline §11 M74B
  M75C h5_game_commercialization_pipeline v0  ← 原 Pipeline §11 M75，推到这里
```

**关键纪律**：
- M74 不能开始，直到 M73 全部 GO
- M75 不能开始，直到 M74A-M74D 全部 GO
- M75A 优先于 M75C（自己用得到先于演示用）

## 4. v3 修订建议（diff 形式）

下面只列与 V2 的差异；其他内容保留。

```
PIPELINE_ORCHESTRATION_REFACTOR_PLAN_V3.md

§0 修正点
  + §0.5 与 M73 preflight 路线的关系（不替代 capability 路线，串行执行）

§2 重新定义核心概念
  + §2.5 WorkflowPipeline 与 OrchestrationPlan 的关系（方案 A：Pipeline 是 plan of plans）

§3 Pipeline 编排模式
  ! 明示实施顺序：先 manual → template → ai_generated → hybrid

§4 PipelineAdjustment
  ! 字段标 optional：rationale / operator_id / before / after 默认可空

§7 Pipeline stage 到 LangGraph node 的映射
  + 给出 LangGraph 1.x 的具体 API 名称
  + 说明 async stage（validation_gate / external_worker）如何 wrap

§8 H5 游戏 pipeline
  ! 改为"业务示例之一"，不是 M75 主线

§10 Pipeline routing
  + §10.x Migration from cluster_router

§11 分阶段实施路线
  ! 重新编号为 M74-M76（避开与 preflight 已吸收的 M73A-M73E 冲突）
  + M75A workflow_self_development_pipeline（新增，优先于 H5）
  ! M75 H5 pipeline 推到 M75C

§12 Codex 实施提示词
  + 加 "do not modify existing OrchestrationPlan; treat WorkflowPipeline as higher abstraction"
  + 加 "respect M73 preflight route; this plan starts no earlier than M74"

§14 Pipeline 失败回滚（新增）

§15 Pipeline 与 OperatorActionReceipt 协议对接（新增）
```

## 5. 7 天先做什么（如果你接受本评估）

**不要立刻开 Pipeline V2**。先做这 5 件事，预计 7 天：

| 天 | 动作 | 工作量 | 解决 |
| --- | --- | :---: | --- |
| Day 1 | 把 Pipeline V2 的 §0 修正点（拒绝 game_* cluster + Pipeline-of-Execution-Units + 三种来源 + LangGraph 不替代）写入 AGENTS.md，作为**纯文档约束**（不实施代码）| 1 小时 | §1 价值保留 |
| Day 2 | 用本评估生成 Pipeline V3，重新编号 M74-M76 + 加 §14 失败回滚 + §15 receipt 对接 | 半天 | P0 #1 |
| Day 3 | v3 §2.5 决定 WorkflowPipeline vs OrchestrationPlan 关系（方案 A/B/C 选一个，建议 A）| 半天 | P0 #2 |
| Day 4 | 开 M73A Capability Enforcement Pilot（preflight 已定路线，不变） | 1 天 | preflight |
| Day 5-7 | 继续 M73A-M73E 路线 | 3 天 | preflight |

**完成后**：M73 真 GO 之后再开 M74A（Pipeline 语义收口）。**Pipeline 实施不该早于 M74**。

## 6. 与既有评估的对照

| 评估 | 主张 | Pipeline V2 是否吸收 |
| --- | --- | --- |
| Opus M37（M48 推荐） | OrchestratorService 收缩 | 不相关 |
| Opus M47 | core_domain 去污染、测试可复现性 | M73 preflight 已吸收 |
| GPT Pro M47 | OperatorActionReceipt + workspace root | M73 preflight 已吸收 |
| Codex M48 | repo mutation 原子性、Web XSS | M67 已完成 |
| Opus LONG_TERM ROADMAP REVIEW | M72 主线改为 Workflow Self-Development | **Pipeline V2 未继承**（仍把 H5 当 M75 主线）|
| Opus M73 | M68 是 advisory；total LOC ratchet | preflight 部分吸收（M68 口径），LOC ratchet 未吸收 |
| GPT M73 | Capability enforcement 路线 M73A-M73E | preflight 已吸收 |
| **Pipeline V2** | Pipeline 产品层 + WorkflowPipeline 模型 | **新增，但与 preflight 路线冲突** |

**核心冲突**：Pipeline V2 没有承认 M73 preflight 已经 GO，没有继承 LONG_TERM_ROADMAP_REVIEW 的"workflow self-development 优先于 H5"判断。

## 7. 一句话给你

> **Pipeline V2 的方向是对的、自我修正是健康的、四层模型是清楚的，但作为执行计划它有两个根问题——M73 编号冲突和 WorkflowPipeline vs OrchestrationPlan 关系未定义**。先做 V3 修订（重新编号 M74-M76 + 加关系定义 + 加失败回滚），再让 Codex 开工。否则第一周就会撞墙。

## 附录：评估方法

```bash
# 读全文
Read PIPELINE_ORCHESTRATION_REFACTOR_PLAN_V2.md (1253 lines)

# 与现状对账
Read M73_PREFLIGHT_AND_CAPABILITY_PLAN.md
Read M73_PREFLIGHT_EXECUTION_REPORT.md
Read AGENTS.md

# 验证现有 contracts 与 Pipeline 提议的关系
grep "OrchestrationPlan\|OrchestrationGraphNode" packages/contracts/
Read packages/core_domain/orchestration_engine.py
Read packages/core_domain/cluster_router.py
```

未做（不影响结论）：
- 不验证 LangGraph 1.x `interrupt()` 具体 API（属 v3 修订工作）
- 不试跑 Pipeline contract round-trip（V2 还没产出 contract 代码）
- 不评估 WorkflowPipeline schema 的字段完备性（属 v3 工作）
