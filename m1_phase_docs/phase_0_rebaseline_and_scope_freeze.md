# M1 Phase 0 — Rebaseline And Scope Freeze

**阶段定位：** M1 的 Phase 0 不是编码阶段，而是把 M1 要实现的协议增量、状态机、运行时边界和事务模型冻结为可编码基线。  
**执行前提：** M0 freeze review 已完成，M1 总计划与执行循环协议已就位。  
**本阶段输出：** 本文、`docs/task_cards/m1_phase_0_task_cards.md` 及 5 张复杂 task 独立 md。

---

# 1. 本阶段目标

本阶段只做一件事：  
把 M1 真正要写进代码的**边界、状态、接口与安全约束**冻结下来，避免 Phase 1 之后继续在实现中临时发明协议。

本阶段完成后，后续 Phase 1~4 必须以这里的冻结决策为准。

---

# 2. 输入基线

本阶段直接基于以下输入：

- `docs/reviews/m0-freeze-review.md`
- `docs/tech-debt-registry.md`
- `universal_agentic_workflow_os_M1_phase_plan_v2_1.md`
- `docs/task_cards/m1_execution_loop_protocol.md`
- `M1_Evaluation_and_Suggestions.md`
- `M0_Evaluation_Claude_Opus.md` 中的 M1 评估章节
- 当前 M0 实现代码：`packages/`、`apps/`、`infra/`、`tests/`

---

# 3. 本阶段冻结结论

## 3.1 M1 继续坚持的边界

- M1 继续保持 local-first、offline-first
- M1 主链不依赖 LLM、联网检索、embedding 或云端服务
- M1 不引入真实 Claim / Lease / Barrier
- M1 不接第二执行器
- M1 不接 Web console
- M1 不要求真实 LangGraph 图集成

## 3.2 Run Status State Machine 冻结

M1 结束时，`RunStatus` 固定为：

- `pending`
- `prepared`
- `running`
- `awaiting_review`
- `completed`
- `failed`
- `cancelled`

**明确不新增：**

- `compiled`
- `resuming`
- `paused`
- `review_requested`

**原因：**

- `prepared` 继续承载“compile 已完成、runtime 已就绪”的语义，避免为 M1 引入额外状态而放大迁移与守卫复杂度
- `review_requested` 作为 event，不作为 run status
- `resume` 是动作，不单独沉淀为状态

### 合法状态转换矩阵

| From | Action | To | 备注 |
| --- | --- | --- | --- |
| `pending` | `compile` | `prepared` | 首次 compile |
| `prepared` | `recompile` | `prepared` | 清理旧 compile snapshot 后重建 |
| `prepared` | `resume` | `running` | 启动或恢复执行 |
| `running` | `auto review pass` | `completed` | 仅 `auto_only` |
| `running` | `auto review fail` | `failed` | 仅 `auto_only` |
| `running` | `review requested` | `awaiting_review` | 仅 `human_required` |
| `awaiting_review` | `approve` | `completed` | 人工通过 |
| `awaiting_review` | `reject` | `failed` | 人工拒绝 |
| `pending` | `cancel` | `cancelled` | 开发态逃生 |
| `prepared` | `cancel` | `cancelled` | 开发态逃生 |
| `awaiting_review` | `cancel` | `cancelled` | 开发态逃生 |

**M1 不承诺：**

- 对 `running` 状态提供抢占式取消
- 对 `completed` / `failed` / `cancelled` 提供 replay / rollback / fork

## 3.3 `suggest(goal_text)` 实现策略冻结

M1 的 `PresetResolver.suggest(goal_text)` 固定采用：

- **离线**
- **确定性**
- **可解释**
- **启发式规则匹配**

M1 不采用：

- LLM 推断
- embedding / 语义向量
- 联网查询

### M1 建议策略

- 基于 `goal_text` 的关键词匹配
- 基于每个 preset 的规则表打分
- 输出按分数排序的候选列表
- 每条建议必须包含 `reason`

### M1 期望行为

- 不自动替用户选择 preset
- 分数相同按稳定规则排序
- 空 goal 或弱匹配时仍返回稳定排序，但明确 reason 为“default fallback”

## 3.4 `human_required` 最小闭环冻结

M1 对 `human_required` 的最小闭环固定如下：

### 触发时机

- runtime task 完成后生成 evidence
- 若 preset 的 review policy 为 `human_required`，则**不执行 auto review**
- run 进入 `awaiting_review`
- timeline 写入 `review_requested`

### 确认动作

- CLI：`workflowctl run approve <run_id>`
- CLI：`workflowctl run reject <run_id>`
- API：`POST /runs/{run_id}/approve`
- API：`POST /runs/{run_id}/reject`

### 状态语义

- `awaiting_review` 表示 evidence 已生成，等待人工决策
- approve 后创建 `ReviewVerdict(reviewer_type=human, decision=pass)` 并转 `completed`
- reject 后创建 `ReviewVerdict(reviewer_type=human, decision=fail)` 并转 `failed`

### 超时语义

- M1 不实现 review 超时
- `awaiting_review` 可无限挂起
- 超时 / SLA 机制留到 M2+

## 3.5 Runtime “真实主链”冻结

M1 中的 runtime “真实主链”固定采用：

- 纯 Python 控制流
- 持久化 `RuntimeStateRef`
- `RuntimeGateway.start()` / `resume()` 进入真实执行路径

M1 不要求：

- 引入 `langgraph` 运行时依赖
- 引入 checkpointer
- 引入中断回放 / fork / replay

### `RuntimeStateRef` 语义

M1 的 `RuntimeStateRef` 是轻量状态引用，只保存：

- `run_id`
- `runtime_task_id`
- `graph_step`
- `state_payload`
- `is_terminal`
- `updated_at`

它不能保存 contract 实例，也不能承载大对象上下文。

## 3.6 `RuntimeGateway` 归属冻结

M1 固定采用依赖倒置：

- `RuntimeGateway` ABC 移入 `packages/contracts/`
- `RuntimeStateRef` 也作为 contract 输出
- `packages/runtime_langgraph/` 只保留实现，不再承载接口定义

## 3.7 Unit of Work 冻结

M1 默认采用：

- **service method 级事务边界**

即以下方法各自作为事务边界：

- `compile_run()`
- `recompile_run()`
- `resume_run()`
- `approve_run_review()`
- `reject_run_review()`
- `cancel_run()`

### 实现约束

- 使用 `db.unit_of_work()` 风格的 context manager
- repository 接受可注入 connection
- service 内部负责在一个事务内完成多步写入
- 不做跨 service 方法的长事务

## 3.8 M1 数据迁移策略冻结

M1 期间对本地测试环境固定采用：

- **允许破坏性清理本地 SQLite**
- `db reset` 视为标准迁移路径

M1 不承诺：

- 兼容历史临时 M0 测试数据库样本
- 对历史手工污染数据做无损迁移

M1 只要求：

- migration 自身可重复执行
- fresh reset -> migrate -> seed -> smoke 可稳定通过

---

# 4. M1 冻结后的接口增量

## 4.1 CLI 增量

M1 目标 CLI 面固定新增：

- `workflowctl run suggest-presets --goal ...`
- `workflowctl run compile <run_id>`
- `workflowctl run recompile <run_id>`
- `workflowctl run resume <run_id>`
- `workflowctl run status-detail <run_id>`
- `workflowctl run handoffs <run_id>`
- `workflowctl run approve <run_id>`
- `workflowctl run reject <run_id>`

## 4.2 API 增量

M1 目标 API 面固定新增：

- `POST /runs/{run_id}/compile`
- `POST /runs/{run_id}/recompile`
- `POST /runs/{run_id}/resume`
- `POST /runs/{run_id}/approve`
- `POST /runs/{run_id}/reject`
- `GET /runs/{run_id}/status-detail`
- `GET /runs/{run_id}/handoffs`

## 4.3 Event 增量

M1 建议新增 event 类型：

- `run_compiled`
- `runtime_resumed`
- `handoff_created`
- `review_requested`
- `run_cancelled`

保留已有 M0 事件，不破坏原有 timeline 结构。

---

# 5. 本阶段 Task 拆解原则

Phase 0 只做复杂 task，不设“标准 task”。

原因：

- 每一张卡都涉及协议冻结
- 每一张卡都影响后续代码安全
- 每一张卡都必须有独立 read set / write set / 风险说明

因此，本阶段所有 task 均以独立 md 形式存在。

---

# 6. Phase Gate

只有当以下条件满足，Phase 0 才算通过：

- Run Status State Machine 已冻结
- `suggest()` 策略已冻结
- `human_required` 最小闭环已冻结
- runtime “真实主链”边界已冻结
- UoW 粒度与迁移策略已冻结
- task cards 已能直接指导 Phase 1 编码

---

# 7. 风险与回退策略

## 当前最大风险

- 状态机定义过多，导致 Phase 1 迁移复杂度失控
- runtime 边界不够清晰，导致 M1 偷偷引入真实 LangGraph
- `human_required` 设计过重，反向拖累 M1 收口

## 回退策略

- 一旦发现新增状态超过最小闭环，优先删状态，不优先加事件
- 一旦 runtime 方案需要新增 `langgraph` 依赖，则默认退回纯 Python 方案
- 一旦 human review 设计需要超时 / 队列 / 通知，则默认降级为“无限挂起 + approve/reject”

---

# 8. 下一步

Phase 0 通过后，直接进入：

- `docs/task_cards/m1_phase_0_task_cards.md` 的 gate review 回填
- `Phase 1` 的 contracts / persistence delta 详细文档与代码级 task cards
