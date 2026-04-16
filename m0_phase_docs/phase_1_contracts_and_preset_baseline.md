# M0 Phase 1 — Contracts 与 Preset 冷启动基线详细开发方案

**Phase 目标：** 将 Phase 0 冻结的语义转成可实现的 Wave 1 schema 与 Preset 冷启动基线，确保数据库、API 和 CLI 都有稳定上游。

**覆盖任务：** T0-03、T0-03.5、T0-10、T0-11

---

# 1. 本阶段要解决什么

Phase 1 的任务不是“把字段列出来”，而是把所有 M0 需要落地的核心对象，收敛成一套足够小、足够稳、足够能支撑实现的 contracts v1。

同时，本阶段还要锁死 Preset 冷启动规则：

- 至少 2 个 bootstrap presets
- `manual only`
- 不允许无 preset 创建 run
- 不允许系统偷偷做自动推断

---

# 2. 输入与前置条件

## 2.1 输入材料

- Phase 0 输出的范围文档
- Wave 1 对象职责文档
- ADR-001 ~ ADR-005

## 2.2 Entry Criteria

- Wave 1 对象职责已冻结
- `manual preset only` 已在治理层确认
- 没有未决的对象命名冲突

本阶段字段与验收的主口径以 `universal_agentic_workflow_os_M0_task_breakdown_v2_1.md` 为准。

---

# 3. 核心交付物

- `packages/contracts/` 下的 schema / model 定义
- `docs/presets/preset-registry-v1.md`
- bootstrap preset seed 数据
- `packages/core-domain/` 中的 `PresetResolver v0`
- contracts 测试基础设施

建议优先定义的模块：

- `run`
- `phase`
- `task_card`
- `runtime_task`
- `task_packet`
- `evidence`
- `review_verdict`
- `preset_definition`
- `handoff_lite`

---

# 4. 详细工作流

## 4.1 工作流 A：Wave 1 schema v1

对应任务：T0-03

### 开发步骤

1. 先统一 schema 设计约束：
   - 命名风格统一
   - 所有对象具备唯一 ID
   - 与 DB 表字段可一一映射
   - 不提前塞入 M2/M4 字段
   - 所有持久化 Wave 1 对象必须带 `created_at`
   - 所有 M0 contract 保留 `schema_version`
   - Pydantic 默认 `extra=allow`
2. 逐个落 Wave 1 对象。
3. 对每个对象补最小 JSON round-trip 验证用例。

### 设计原则

- `TaskCard` 是人类 / planner 可读对象，不是 Worker 执行合同
- `TaskPacket` 是执行合同，不承担长期业务真相
- `Evidence` 是执行结果真相，不负责审核判断
- `ReviewVerdict` 只输出审查结论，不回填执行原始结果
- `Evidence` 统一使用 `artifact_refs`，不再混用 `artifacts`
- `ReviewVerdict` 统一使用 `verdict_id`，并在 M0 默认 `reviewer_type=auto`
- `HandoffLite` 在 M0 只冻结语义与 schema，不要求首批落表

### 最小验证

- schema 可以序列化
- schema 可以反序列化
- 关键枚举 / 必填字段有明确校验错误

## 4.2 工作流 B：Preset Registry v1

对应任务：T0-10

### 开发步骤

1. 定义 `PresetDefinition` 最小字段集。
2. 输出 preset registry 文档，逐个写清 preset 的适用意图。
3. seed 至少两个 presets：
   - `feature_delivery`
   - `research_spike`
4. 可选再加：
   - `bugfix_repair`

### M0 值域必须冻结

- `task_kind`：至少包含 `shell_exec`、`noop`
- `review_policy`：至少包含 `auto_only`、`human_required`
- `budget_policy`：使用最小结构 `{"max_retries": int, "timeout_seconds": int}`

### 每个 preset 至少要写清

- 适用意图
- 允许的 task kinds
- 默认 review policy
- 默认 budget policy
- 是否需要 gates
- 不能用于什么场景

### 额外要求

- `feature_delivery` 给出完整 JSON seed 示例
- `research_spike` 给出完整 JSON seed 示例

### 审查重点

- preset 不应过度接近完整工作流
- preset 是执行骨架模板，不是 planner 输出

## 4.3 工作流 C：PresetResolver v0

对应任务：T0-11

### 开发步骤

1. 实现 `manual_select(preset_id)`
2. 校验 preset 是否存在
3. 对非法 preset 返回可解释错误
4. 对缺失 preset 返回明确失败
5. 把 preset 选择写入 run event

### 明确禁止

- 根据 goal 文本猜 preset
- 自动兜底到默认 preset
- 用户没传 preset 时继续执行

### 最小接口语义

- 输入：`preset_id`
- 输出：合法的 `PresetDefinition`
- 失败：明确抛出“preset required”或“preset not found”

---

# 5. 建议实现顺序

1. 先做 `PresetDefinition`，因为它同时影响 contracts 和 resolver
2. 再做 Wave 1 其余 schema
3. 然后写 preset registry 文档与 seed 数据
4. 最后实现 `PresetResolver`

这样可以避免 resolver 先写死逻辑，后续又因为 `PresetDefinition` 调整而返工。

---

# 6. 建议测试设计

## 6.1 Contracts 测试

- 每个对象的最小实例可通过校验
- 缺少关键字段时能报错
- JSON round-trip 不丢字段
- `created_at` / `schema_version` 缺失时能报错
- `ReviewVerdict.reviewer_type=auto` 默认值可验证

## 6.2 Preset 测试

- preset 列表可读取
- `feature_delivery` 与 `research_spike` 可被解析
- 非法 `preset_id` 返回明确错误
- 未传 preset 创建 run 必须失败
- `task_kind` / `review_policy` / `budget_policy` 值域可验证

## 6.3 快照测试

建议为以下对象建立快照：

- `RuntimeTask`
- `TaskPacket`
- `PresetDefinition`

这样后续 Phase 2/3 若误改 contracts，能第一时间发现。

---

# 7. 建议阶段拆分

## Checkpoint 1A：Contracts 草案完成

检查项：

- Wave 1 字段是否足以支持 DB 建表
- 是否提前引入 M2 复杂字段

## Checkpoint 1B：Preset Registry 草案完成

检查项：

- 至少两个 preset 是否已定义清楚
- preset 是否仍保持“骨架模板”定位

## Checkpoint 1C：Resolver 行为锁定

检查项：

- manual only 是否被强制执行
- 是否仍存在隐式默认 preset

---

# 8. 验收与退出标准

## 8.1 Exit Criteria

- Wave 1 schema v1 完成
- 所有对象可序列化 / 反序列化
- 至少 2 个 bootstrap presets 完成 seed
- `PresetResolver = manual only`
- 缺失 preset 时创建 run 明确失败
- 非法 preset_id 时返回可解释错误

## 8.2 Gate 决策问题

1. 数据库表结构是否已经有稳定上游
2. API 层是否可以不再推动 contracts 改名
3. Preset 策略是否已在 M0 内冻结

只要以上任意一项不成立，就不进入 Phase 2。

---

# 9. 风险与缓解

- 风险：schema 定义过厚，未来难收缩
  缓解：只保留 M0 必需字段，剩余能力保持占位

- 风险：preset 定义过薄，后续缺少扩展位
  缓解：至少保留 task kinds、review、budget、gates 四类扩展点

- 风险：resolver 实际行为与文档不一致
  缓解：用测试锁死“无 preset 必失败”的规则

---

# 10. 本阶段完成后的直接产出

Phase 1 完成后，团队应立即拥有以下能力：

- 可以用统一 schema 语言推进数据库和 API
- 可以用 preset seed 和 resolver 跑通最小创建链路
- 可以用 contracts 测试防止上游接口继续漂移

这三件事成立，Phase 1 才算完成。
