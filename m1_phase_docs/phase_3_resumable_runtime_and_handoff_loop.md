# M1 Phase 3 — Resumable Runtime And Handoff Loop

**阶段定位：** 在 Phase 2 已提供 compile surface 的基础上，把 runtime 从“prepare 后直接 execute”升级为“通过 persisted state ref 恢复进入执行”的最小可恢复主链。  
**进入条件：** Phase 2 gate 已通过。

---

# 1. 本阶段重评

基于当前实际实现：

- compile / recompile 已经成立
- `RuntimeStateRef` 已落库
- `status-detail` 与 `handoffs` 已可查询
- `unit_of_work()` 已在 compile 路径上线

因此，Phase 3 的重点不是再做 compile，而是：

- `resume_run()` 真正接管执行入口
- runtime state ref 在 resume / terminal 之间真实更新
- `execute_run()` 退化为兼容别名
- `cancel_run()` 进入状态守卫和幂等语义
- UoW 扩展到 resume / execute / cancel

---

# 2. In Scope

- `resume_run()` service
- CLI / API：
  - `run resume`
  - `POST /runs/{run_id}/resume`
- `runtime_resumed` event
- state ref 的 `compiled -> resuming -> terminal` 更新
- `execute_run()` 状态守卫与兼容别名语义
- `cancel_run()` 幂等保护和 `run_cancelled` event
- `status-detail` 的 next action / runtime state 可见性增强

---

# 3. Out Of Scope

- `human_required` 的 approve / reject
- 最终 smoke / offline validation 改造
- M2 并发控制

---

# 4. 关键实现约束

- `resume` 只能从 `prepared` 进入
- `execute_run()` 不再作为新的主入口，只保留兼容语义
- `cancel` 只允许 `pending / prepared / awaiting_review`，对 `cancelled` 必须幂等
- runtime 主链继续保持纯 Python，不引入真实 `langgraph`

---

# 5. Task 拆解原则

本阶段拆为 4 张复杂卡：

1. resume service 与 state ref 更新
2. execute / cancel 状态守卫与 UoW
3. resume API / CLI
4. phase gate tests

---

# 6. Phase Gate

- `resume_run()` 可从 `prepared` 正常推进
- `runtime_resumed` event 已进入 timeline
- terminal 后 state ref 已更新为 terminal
- `cancel_run()` 对重复 cancel 幂等
- targeted tests 通过

---

# 7. 风险与回退

- 风险：为了做 resume，反向把 Phase 4 的 human review 一起卷进来
- 控制：本阶段只保证 auto path 的 resumable runtime；human review 留到 Phase 4 接 final branch
