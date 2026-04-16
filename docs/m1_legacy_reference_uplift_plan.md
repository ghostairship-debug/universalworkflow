# M1 遗产参考增强计划

## 0. Implementation Status

Status: `completed`

The first uplift batch defined in this plan has now been implemented without reopening the M1 architecture.

- `Phase A` is complete: explicit run/runtime transition matrix, guard helpers, and invalid-transition tests are in place.
- `Phase B` is complete: legacy-inspired review semantics are translated into the current repository test matrix, and `latest_review_verdict / effective_review_state` are projected through `status-detail`.
- `Phase C` is complete: operator-facing `status-detail` diagnostics and read-only dry-run `inspection` are available through both CLI and API.

Implementation evidence:

- `packages/contracts/models.py`
- `packages/contracts/runtime.py`
- `packages/core_domain/services.py`
- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`
- `infra/scripts/offline_validation.py`
- `tests/test_contracts.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`
- `docs/contracts/m1_run_runtime_transition_matrix.md`
- `docs/reviews/m1_review_semantics_decision_table.md`

Verification evidence:

- `pytest` -> `51 passed`
- `python -m infra.scripts.offline_validation --skip-offline-probe` -> `overall_passed = true`
- manual acceptance passed for both CLI and API on `auto_only` and `human_required` paths

Scope check:

- no legacy `facade.py` pattern import
- no project-centric kernel backport
- no phase/task-card runtime mainline reintroduced
- no doc-driven compile model promoted to the main execution path

## 1. 文档定位

这份文档只做一件事：

**把 `D:\AI Agent` 中仍然有价值的部分，用来做当前仓库的 `M1 hardening`。**

它不是：

- 重开一次 M1 架构设计
- 旧系统迁移计划
- 遗产模块搬运计划
- 共享运行时计划

它是：

- 只吸收那些能增强当前 `M1` **正确性、可观测性、测试覆盖** 的内容
- 不吸收会把当前主线带偏的旧结构

一句话定义：

**“用遗产做 M1 hardening”，而不是重开 M1 架构。**

---

## 2. 当前判断

结论是：**可以，而且值得，而且有一部分是现在就能反哺当前 M1 的。**

但前提是把这件事定义为：

- 提升当前 `M1`
- 补强已有主链
- 只吸收低风险、高收益的守卫与测试资产
- 明确拒绝旧的重内核结构

当前仓库已经有自己的 `run-centric` 主链，`compile / recompile / resume / review / status-detail / CLI / smoke` 都已经成型。  
遗产项目的价值，不在于“现成代码能搬过来”，而在于：

- 更完整的状态机守卫
- 更强的 review 语义边界测试
- 更成熟的坏状态诊断思路
- 更适合 operator 的状态解释方式

---

## 3. 最值得拿来提升当前 M1 的 4 类内容

### 3.1 状态守卫补强

遗产里的状态机定义比当前更完整，适合反哺当前：

- `RunStatus`
- `RuntimeStateRef`

可吸收内容：

- 显式迁移矩阵
- terminal / non-terminal 分类
- 非法跳转测试

参考来源：

- `D:\AI Agent\src\agentic_kernel\domain\project.py`
- `D:\AI Agent\src\agentic_kernel\domain\task_state.py`

映射到当前：

- `packages/contracts/models.py`
- `packages/contracts/runtime.py`
- `packages/core_domain/services.py`

### 3.2 Review 语义与测试矩阵

当前 M1 已有：

- `auto_only`
- `human_required`

的最小闭环，但遗产里对 review policy 的边界测试更强，适合直接翻译成当前仓库测试。

可吸收内容：

- review policy case matrix
- latest verdict / effective review state 语义
- review routing 的边界用例

参考来源：

- `D:\AI Agent\src\agentic_kernel\services\review_service.py`
- `D:\AI Agent\tests\services\test_review_policy_routing.py`

映射到当前：

- `packages/core_domain/services.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`

### 3.3 坏状态诊断与 repair 思路

这是遗产最有价值的部分。

当前 M1 已有可恢复主链，但还没有系统性的：

- dry-run inspector
- reconcile catalog

可吸收内容：

- drift / desync / stale / leaked-state 失败目录
- `inspect -> recommend -> apply` 思路
- 坏状态回归样例

参考来源：

- `D:\AI Agent\src\agentic_kernel\services\runtime_reconcile_service.py`
- `D:\AI Agent\tests\services\test_phase_task_card_runtime.py`

映射到当前：

- `packages/core_domain/services.py`
- `tests/test_execution_loop.py`
- 未来的 inspection / reconcile 入口

### 3.4 Operator Diagnostics 提升

当前 `status-detail` 已有基础，但还能吸收遗产里对：

- 失败原因
- 等待原因
- 下一步建议

的表达方式。

参考来源：

- `D:\AI Agent\docs\project-deep-dive.zh-CN.md`
- `D:\AI Agent\tests\services\test_phase_task_card_runtime.py`

映射到当前：

- `packages/core_domain/services.py`
- `apps/orchestrator_api/main.py`
- `apps/operator_cli/main.py`

---

## 4. 明确不建议拿来提升当前 M1 的内容

这些内容会伤害当前 M1，而不是提升它：

- `facade.py` 巨型统一入口
- project-centric kernel
- phase/task-card runtime 主链
- doc-driven compile 作为标准执行模型
- `pf_content` 子域

参考来源：

- `D:\AI Agent\src\agentic_kernel\facade.py`

这些都必须保持 **reference-only**，不能进入当前仓库实现主线。

---

## 5. 如果只选一批低风险、高收益的 M1 提升项

如果只做一批最值得立刻落地的 uplift，我建议就是这 3 个：

1. 给当前 M1 补一份显式 `run/runtime` 状态迁移矩阵，并补表驱动测试。
2. 把遗产里的 review policy cases 翻译成当前仓库测试，先补测试，不急着扩实现。
3. 新增一版 `status-detail / dry-run inspection`，专门检查几类坏状态：
   - `completed` 但 runtime 非 terminal
   - `awaiting_review` 但缺 evidence
   - `cancelled` 但仍有 live runtime
   - `prepared` 但 compile snapshot 不完整

因此，这份计划的首批执行范围只围绕这 3 个 uplift 展开。

---

## 6. 首批 uplift phase 划分

## 6.1 Uplift Phase A：Run / Runtime 状态守卫硬化

### 目标

给当前 M1 增加一份显式的 `run/runtime` 状态迁移矩阵，并把它落实成表驱动测试与 service guard。

### 输入

- 当前 `M1` 的 contracts / services / tests
- 遗产 `project.py`
- 遗产 `task_state.py`

### 输出

- `RunStatus` / `RuntimeStateRef` 迁移矩阵文档
- 表驱动非法跳转测试
- API / service 层非法跳转错误断言

### 代码落点

- `packages/contracts/models.py`
- `packages/contracts/runtime.py`
- `packages/core_domain/services.py`
- `tests/test_contracts.py`
- `tests/test_api.py`
- `tests/test_execution_loop.py`

### Exit Criteria

- 状态迁移矩阵成文
- 非法跳转测试可回归
- 关键状态错误返回稳定

## 6.2 Uplift Phase B：Review Policy 测试矩阵先行

### 目标

把遗产里最成熟的 review policy case 翻译成当前仓库测试，先提升 review 语义边界，再决定后续是否扩枚举与实现。

### 输入

- 当前 `auto_only / human_required` 主链
- 遗产 `review_service.py`
- 遗产 `test_review_policy_routing.py`

### 输出

- review case matrix
- 当前仓库版本的 review semantics tests
- `latest_review_verdict / effective_review_state` 设计口径

### 代码落点

- `packages/core_domain/services.py`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_cli.py`

### Exit Criteria

- 最小 review matrix 已落仓
- review 状态投影可被测试验证
- 未来 richer policy 扩展已具备测试骨架

## 6.3 Uplift Phase C：Status Detail / Dry-Run Inspection

### 目标

新增一版更面向 operator 的 `status-detail` 和一组不修改真实状态的 dry-run inspection。

### 输入

- 当前 `status-detail`
- 当前 `offline_validation`
- 遗产 `runtime_reconcile_service.py`
- 遗产 `test_phase_task_card_runtime.py`

### 输出

- 增强版 `status-detail`
- 4 类坏状态的 dry-run inspection
- 对应 CLI / API / validation 测试

### 重点检查状态

- `completed` 但 runtime 非 terminal
- `awaiting_review` 但缺 evidence
- `cancelled` 但仍有 live runtime
- `prepared` 但 compile snapshot 不完整

### 代码落点

- `packages/core_domain/services.py`
- `apps/orchestrator_api/main.py`
- `apps/operator_cli/main.py`
- `infra/scripts/offline_validation.py`
- `tests/test_api.py`
- `tests/test_cli.py`
- `tests/test_execution_loop.py`

### Exit Criteria

- `status-detail` 中已能解释失败 / 等待 / 下一步
- dry-run inspection 只诊断不修改状态
- 4 类坏状态至少全部可识别

---

## 7. 代码级 task card 索引

这 3 个 uplift phase 的代码级 task cards 见：

- [docs/task_cards/m1_legacy_reference_uplift_task_cards.md](/D:/Universal%20Agentic%20workflow/docs/task_cards/m1_legacy_reference_uplift_task_cards.md:1)

---

## 8. 执行顺序

推荐顺序如下：

1. `Phase A：状态守卫硬化`
2. `Phase B：Review Policy 测试矩阵`
3. `Phase C：Status Detail / Dry-Run Inspection`

原因：

- 状态守卫是最基础的正确性边界
- review matrix 建立在更稳定的状态语义之上
- diagnostics / inspection 只有建立在前两者之上才不会输出漂移信息

---

## 9. 验收标准

这份计划只有在以下条件同时成立时，才算真正完成：

1. 已经把“总览遗产参考计划”和“M1 专项增强计划”分开。
2. 已经把首批 uplift 收敛到 3 个低风险、高收益方向。
3. 每个 uplift 都已经明确到 phase 和代码级 task card。
4. 后续若要进入实现，不需要再重新做一次“吸收哪些遗产内容”的讨论。

---

## 10. 最终结论

最终判断如下：

- 可以做，而且值得做。
- 但目标必须是：**补强当前 M1**，不是搬回遗产结构。
- 当前最应该吸收的是：
  - 状态守卫补强
  - review 语义与测试矩阵
  - 坏状态诊断 / dry-run inspection
  - operator diagnostics 提升
- 当前最应该拒绝的是：
  - giant facade
  - project-centric kernel
  - phase/task-card runtime 回流
  - doc-driven compile 主路径
  - `pf_content` 子域

一句话收口：

**M1 遗产参考增强，不是把旧系统搬回来，而是把旧系统里踩过的坑，转成当前 M1 的守卫、测试和诊断能力。**
