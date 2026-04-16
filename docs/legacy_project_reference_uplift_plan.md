# 遗产项目参考提升计划

> 对应当前仓库 `M1` 基线的专项落地版，请同时参阅 [docs/m1_legacy_reference_uplift_plan.md](/D:/Universal%20Agentic%20workflow/docs/m1_legacy_reference_uplift_plan.md:1)。本文保留跨 `M1.5 / M2 / M3` 的总览视角；专项执行时以 M1 专项计划为先。

## 1. 文档定位

本文档用于回答两个问题：

1. `D:\AI Agent` 是否对当前仓库仍有参考价值。
2. 如果有，应该以什么方式、在什么阶段、吸收哪些内容。

本文档不是迁移计划，不是模块搬运计划，也不是共享运行时计划。它只定义“如何把遗产项目中仍然有价值的语义、边界条件、测试资产和反模式经验，转化为当前仓库后续阶段的提升输入”。

---

## 2. 评估结论

结论是：**有明确参考价值，但价值主要集中在 `语义规则`、`失败模式`、`回归测试资产` 和 `反模式警示`，而不是可直接复用的实现模块。**

原因如下：

- 当前仓库已经在 `M1` 形成了自己的 `run-centric` 主链：
  - `Run -> compile / recompile / resume -> evidence -> review`
  - `RuntimeGateway`、`RuntimeStateRef`、`status-detail`、`handoffs` 已独立成型
- 遗产仓则是明显更重的 `project / phase / task-card` 内核，带有：
  - project-centric 状态机
  - phase/task-card progression
  - reconcile / repair 引擎
  - review gate 持久化与复杂 phase review 链
  - 历史兼容层与内容子域

因此：

- 可以复用：行为不变量、状态守卫、漂移修复思路、测试场景、失败分类
- 不应该复用：project kernel、phase runtime、facade 聚合结构、内容子域、历史兼容层

---

## 3. 已核验的遗产样本

本次实际抽查并确认有价值的遗产样本如下：

### 3.1 语义与状态机

- `D:\AI Agent\src\agentic_kernel\domain\project.py`
- `D:\AI Agent\src\agentic_kernel\domain\task_state.py`

确认价值：

- 状态集合和合法迁移矩阵定义清楚
- terminal / non-terminal 分层明确
- 对“非法状态跳转”有非常直接的守卫价值

不应直接继承的部分：

- `project` 维度状态名字和路径
- phase 驱动下的 `review_required`、`paused`、`approved` 全套 project 语义

### 3.2 review 与 gate 语义

- `D:\AI Agent\src\agentic_kernel\services\review_service.py`
- `D:\AI Agent\tests\services\test_review_policy_routing.py`

确认价值：

- `latest gate` 语义清楚
- optional / recommended / mandatory 这类 richer review policy 的行为边界值得借鉴
- “是否真的需要 review gate”这类判断逻辑更成熟

不应直接继承的部分：

- plan-task / phase-review 绑定模型
- gate API 形状与 project event schema

### 3.3 reconcile / repair 能力

- `D:\AI Agent\src\agentic_kernel\services\runtime_reconcile_service.py`
- `D:\AI Agent\tests\services\test_phase_task_card_runtime.py`

确认价值：

- 对 drift、泄漏状态、非法活跃任务、提前 review、scope 变更 reopen 的失败模式覆盖很强
- 提供了“诊断 -> dry run -> apply repair”的完整思维框架
- 测试中包含大量真实的坏状态样本，非常适合转译成当前仓库的回归测试

不应直接继承的部分：

- phase/task-card/project 绑定结构
- runtime reconcile 服务的大而全依赖注入界面
- future phase supersede 等 project-kernel 专用语义

### 3.4 反模式与复杂度警示

- `D:\AI Agent\src\agentic_kernel\facade.py`
- `D:\AI Agent\docs\project-deep-dive.zh-CN.md`

确认价值：

- `facade.py` 是非常典型的“统一入口膨胀”为巨型聚合点的反例
- deep dive 文档清楚说明了复杂度是如何逐步堆出来的

不应直接继承的部分：

- façade 风格本身
- doc-driven compile pipeline 作为未来主路径
- `pf_content` 等内容工厂子域

---

## 4. 对当前项目真正有帮助的遗产价值分类

### 4.1 Class A：高价值，应进入后续提升计划

这些内容值得在后续阶段被系统吸收：

- run / runtime 状态迁移矩阵补强
- review policy 丰富化前的语义与测试样例
- `latest review verdict` / `effective review state` 的查询语义
- drift / desync / stale / leaked-state 的失败模式目录
- dry-run repair 与 operator diagnostics 思路
- 大量面向坏状态的回归测试样本

### 4.2 Class B：中价值，只适合作为参考

- operator status surface 的可读性设计
- runtime summary / review summary 的最小结构约束
- richer inspection payload 的组织方式

### 4.3 Class C：明确不吸收

- `facade.py` 式统一巨型入口
- project-centric kernel
- phase/task-card runtime 作为当前仓库主执行模型
- doc-driven compile pipeline 作为标准路径
- `pf_content` / media factory 子域
- 历史兼容层和旧迁移假设

---

## 5. 参考提升总原则

后续吸收遗产内容时，统一遵守以下原则：

1. **先从当前仓库的问题出发，不从遗产目录出发。**
2. **先抽语义，再写当前仓库版本，不复制实现。**
3. **优先吸收测试与守卫，不优先吸收服务结构。**
4. **任何吸收都必须保持当前仓库的 run-centric 边界。**
5. **一旦遗产内容要求引入 phase/task-card/project-kernel 假设，立即降级为 reference-only。**

---

## 6. 分阶段提升计划

## 6.1 M1.5：Hardening 阶段

### 目标

在不改变当前主架构的前提下，吸收遗产仓里最值得借鉴的“状态守卫 + review 细化 + operator 诊断”能力。

### 推荐吸收项

#### A. 状态机补强

参考来源：

- `domain/project.py`
- `domain/task_state.py`

当前映射：

- `packages/contracts/models.py`
- `packages/contracts/runtime.py`
- `packages/core_domain/services.py`

建议动作：

- 为 `RunStatus` 制定显式迁移矩阵，而不只依赖 service 层分散判断
- 为 `RuntimeStateRef.graph_step` 定义更明确的 lifecycle 分类
- 增加 terminal / non-terminal 一致性测试
- 明确 `cancelled / failed / awaiting_review / prepared` 之间的非法跳转

建议产出：

- `ADR`：M1.5 run/runtime state transition policy
- contract tests：状态迁移表驱动测试
- service tests：非法跳转 409 测试补全

#### B. Review Policy 丰富化准备

参考来源：

- `review_service.py`
- `test_review_policy_routing.py`

当前映射：

- `packages/contracts/models.py`
- `packages/core_domain/services.py`
- `tests/test_api.py`
- `tests/test_cli.py`
- `tests/test_execution_loop.py`

建议动作：

- 先不直接扩枚举，而是先把 richer review policy 的测试矩阵引入当前仓库
- 把 `auto_only / human_required` 升级为“可扩展的 review gate 评估框架”
- 为未来的 `recommended / mandatory / optional` 设计兼容测试，而不是马上扩实现

建议产出：

- review policy decision table
- review semantics tests
- `status-detail` 中补 `effective_review_state` / `latest_review_verdict`

#### C. Operator Diagnostics 补强

参考来源：

- `project-deep-dive.zh-CN.md`
- `test_phase_task_card_runtime.py` 中的状态与恢复可观察性断言

当前映射：

- `packages/core_domain/services.py::get_status_detail`
- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`

建议动作：

- 增强 `status-detail` 的 `next_action` 解释
- 增加失败原因、等待原因、最后 review verdict、最后 runtime state 的聚合摘要
- 为 CLI 增加更可读的 operator diagnostics 输出约定

---

## 6.2 M2：Runtime Recovery / Reconcile 阶段

### 目标

吸收遗产仓中最强的那部分价值：坏状态诊断、repair playbook、runtime drift 防护和恢复策略。

### 推荐吸收项

#### A. Runtime Snapshot Lifecycle 细化

参考来源：

- `domain/task_state.py`
- `storage/task_store.py`（由索引给出）

当前映射：

- `packages/contracts/runtime.py`
- `packages/core_domain/repositories.py`
- `infra/migrations/`

建议动作：

- 扩展 `RuntimeStateRef` 的状态粒度与 attempt 视图
- 增加 `latest / live / terminal` 查询模式
- 明确 `resume`、`retry`、`superseded`、`stale` 的持久化语义

#### B. Drift / Desync Catalog

参考来源：

- `runtime_reconcile_service.py`
- `test_phase_task_card_runtime.py`

当前映射：

- `packages/core_domain/services.py`
- `tests/test_execution_loop.py`
- 未来的 `reconcile` 服务或脚本

建议动作：

- 先建立当前仓库版本的“坏状态目录”，例如：
  - `run.completed` 但 runtime state 非 terminal
  - `run.awaiting_review` 但缺少 evidence
  - `run.cancelled` 但仍存在 live runtime
  - `run.prepared` 但 compile snapshot 不完整
  - `run.completed` 但缺少 review 或 terminal event
- 每类坏状态先做 dry-run inspection，再定义 repair action

#### C. Repair Playbook

参考来源：

- `runtime_reconcile_service.py`

当前映射：

- 未来的 `packages/core_domain/reconcile.py`
- CLI / API 诊断入口

建议动作：

- 引入 `inspect -> recommend -> apply` 三段式修复模式
- repair action 只允许修复当前仓库 own semantics，不允许倒灌遗产 phase 语义
- repair 首先面向：
  - stale runtime
  - cancelled-but-live runtime
  - review-pending mismatch
  - recompile residue

#### D. Regression Case Mining

参考来源：

- `test_phase_task_card_runtime.py`
- `test_quality_loop_runtime.py`（由索引给出）

建议动作：

- 将遗产测试中的坏状态案例翻译为当前仓库版本的集成测试
- 优先保留“失败模式”与“断言形状”，不保留数据模型形状

---

## 6.3 M3：Observability / Governance 阶段

### 目标

把遗产仓中更偏治理和质量基线的能力转化成长期约束，而不是执行链核心逻辑。

### 推荐吸收项

- failure taxonomy
- richer run event inspection
- review / closure discipline
- tech debt dashboard 思路
- structured completion summary / review summary 约束

当前映射：

- `docs/tech-debt-registry.md`
- `packages/contracts/events.py`
- `docs/reviews/`
- `tests/`

---

## 7. 推荐的首批落地工作包

如果在 `M1` 之后立即开始做“遗产参考提升”，建议按下面顺序推进。

### WP-1：状态守卫硬化

范围：

- `RunStatus` 迁移矩阵
- `RuntimeStateRef` terminal 规则
- 非法跳转测试表

预期收益：

- 这是最低风险、最高收益的遗产吸收点
- 不引入遗产架构，只提升当前仓库的正确性

### WP-2：Review Semantics 测试先行

范围：

- 从遗产 `test_review_policy_routing.py` 提炼 case matrix
- 转写当前仓库版本的 review policy tests
- 为 future policy 扩展预埋测试框架

预期收益：

- 可以先提升质量边界，再决定是否扩实现

### WP-3：坏状态目录与 Dry-Run Inspector

范围：

- 建立 run-centric drift catalog
- 设计 inspection payload
- 写 dry-run 诊断测试

预期收益：

- 为 M2 的 repair/reconcile 铺路
- 这是吸收遗产最强价值的正确入口

### WP-4：反模式守卫

范围：

- 在 ADR 或 architecture notes 中明确记录：
  - 禁止 giant facade
  - 禁止 phase/task-card runtime 回流
  - 禁止 doc-compile 成为主路径
  - 禁止内容子域污染主内核

预期收益：

- 避免“借鉴遗产”变成“重复遗产结构债”

---

## 8. 明确禁区

以下内容不得进入当前仓库的吸收计划：

- 直接复制 `src/agentic_kernel/facade.py`
- 引入 project-centric `Project` 状态机作为当前仓库顶层模型
- 把 phase/task-card runtime 搬回当前主链
- 把 doc compiler block 机制变成当前仓库的官方执行入口
- 引入 `pf_content`、media factory 或 OpenCode/OMO 专用角色层
- 为了兼容遗产命名而扭曲当前 contracts

---

## 9. 决策总结

最终判断如下：

- **遗产项目有参考价值。**
- **参考价值是真实的，而且已经被抽查样本验证。**
- **可吸收内容主要在 `状态守卫`、`review 语义`、`坏状态修复思路`、`测试资产` 和 `反模式警示`。**
- **不应把遗产项目当作可迁移代码库，更不应把它作为当前仓库未来架构的模板。**

一句话总结：

**把 `D:\AI Agent` 当作“高质量遗产语义与回归案例库”，而不是“待搬运的旧系统”。**
