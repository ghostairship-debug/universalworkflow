# M1 Phase 1 — Contracts And Persistence Delta

**阶段定位：** 在 Phase 0 已冻结的状态机、runtime 边界和 UoW 策略基础上，完成 M1 所需的 contracts、migration 与 repository 底座扩展。  
**阶段属性：** 代码实现阶段。  
**进入条件：** Phase 0 gate 已通过。

---

# 1. 本阶段目标

把以下能力先做成稳定底座：

- `RunStatus.awaiting_review`
- `PresetSuggestion`
- `RuntimeStateRef`
- `RuntimeGateway` 的 contracts 归属调整
- `HandoffLite` 的真实持久化
- `run_events` 的 M1 新事件类型
- repository 的 connection 注入能力，为后续 UoW 铺路

本阶段不写 compile / resume / approve / reject 的完整业务行为，但要把这些行为依赖的数据结构准备好。

---

# 2. 当前基线与差距

当前 M0 代码中：

- `RuntimeGateway` 和 `RuntimeStateRef` 仍定义在 `packages/runtime_langgraph/gateway.py`
- `HandoffLite` 只有 contract，没有数据库表和 repository
- 没有 `runtime_state_refs` 持久化
- repository 写操作默认独立建连 / commit
- `RunStatus` 还没有 `awaiting_review`
- event schema 还没有 `run_compiled`、`runtime_resumed`、`handoff_created`、`review_requested`、`run_cancelled`

因此，Phase 1 的任务非常明确：**先把 M1 需要的数据与边界层打平。**

---

# 3. In Scope

- contracts 增量
- migration `002_*`
- repository 增量
- db connection 注入能力
- round-trip 测试
- runtime boundary 测试更新

---

# 4. Out Of Scope

- `PresetResolver.suggest()` 的行为实现
- compile / recompile service 实现
- resume service 实现
- human review API / CLI
- M1 smoke 改造

---

# 5. Phase 1 拆解策略

本阶段按 4 张复杂卡执行：

1. contracts / runtime interface delta
2. migration delta
3. repository + db 注入能力
4. tests / boundary gate

每张卡都必须在实现前冻结 `read set / write set / test plan`。

---

# 6. Phase Gate

只有满足以下条件，才允许进入 Phase 2：

- `awaiting_review`、`PresetSuggestion`、`RuntimeStateRef` 已进入 contracts
- `RuntimeGateway` ABC 已移至 contracts 层
- `HandoffLite` 和 `RuntimeStateRef` 已可持久化 round-trip
- `002_*` migration 可重复执行
- repository 已支持外部 connection 注入
- runtime boundary 测试仍保证 `contracts/`、`core_domain/` 无 `langgraph` import

---

# 7. 风险与控制

## 风险

- 一边改 contracts 一边直接改 service，导致 Phase 1 / Phase 2 混在一起
- 迁移和 repository 绑定过深，导致后续 UoW 不好接
- runtime interface 迁移不彻底，仍残留旧依赖方向

## 控制策略

- 本阶段只收口“数据与边界”
- service 行为改动严格延后到 Phase 2 / Phase 3
- 任一 contract 漂移都必须先回写 task card，再继续改码
