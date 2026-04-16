# M1 Phase 2 — Preset Suggestion And Compile Surface

**阶段定位：** 在 Phase 1 已稳定的数据与边界底座上，建立 M1 的 deterministic suggestion 与 public compile / recompile surface。  
**进入条件：** Phase 1 gate 已通过。

---

# 1. 本阶段重评

基于 Phase 1 的实际完成情况：

- `RuntimeStateRef`、`HandoffLite`、`RuntimeGateway` 归属、`awaiting_review` 已准备好
- repository 已具备 connection 注入能力
- runtime 与 review 的完整行为尚未开始

因此，Phase 2 不需要再讨论 schema，而应专注完成：

- `PresetResolver.suggest(goal_text)`
- `compile_run()` / `recompile_run()`
- compile 相关 CLI / API
- `status-detail` 与 `handoffs` 查询面

---

# 2. In Scope

- deterministic heuristic suggestion
- compile snapshot 生成与持久化
- recompile 语义
- CLI：
  - `run suggest-presets`
  - `run compile`
  - `run recompile`
  - `run status-detail`
  - `run handoffs`
- API：
  - `POST /runs/{run_id}/compile`
  - `POST /runs/{run_id}/recompile`
  - `GET /runs/{run_id}/status-detail`
  - `GET /runs/{run_id}/handoffs`

---

# 3. Out Of Scope

- resume 的真实执行逻辑
- human review approve / reject
- UoW 的完整 service-method 接线
- M1 smoke 最终版

---

# 4. 关键实现约束

- compile 完成后 run 必须进入 `prepared`
- `recompile` 只允许在 `prepared` 下使用
- `POST /runs` 仍只负责创建 run，不隐式 compile
- `suggest()` 只给建议，不自动选 preset
- compile snapshot 必须能产出 handoff 与 state ref

---

# 5. Task 拆解原则

本阶段拆为 4 张复杂卡：

1. deterministic suggestion
2. compile snapshot / service
3. API / CLI surface
4. tests / gate

---

# 6. Phase Gate

- `suggest()` 稳定可用且有 reason
- compile / recompile 可通过 CLI / API 显式触发
- compile 完成后 `status=prepared`
- status-detail / handoffs 可查询
- Phase 2 tests 通过

---

# 7. 风险与回退

- 风险：把 `recompile` 做成会破坏已执行证据的行为
- 控制：M1 只允许 `prepared` 下 recompile，不允许对已执行 run 重编译
