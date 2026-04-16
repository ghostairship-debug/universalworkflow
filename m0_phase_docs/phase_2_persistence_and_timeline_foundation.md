# M0 Phase 2 — 持久化与 Timeline 底座详细开发方案

**Phase 目标：** 建立 SQLite、迁移、仓储接口和 run events timeline 底座，让 M0 不再停留在内存态原型。

**覆盖任务：** T0-12、T0-12.5、T0-13、T0-14

---

# 1. 本阶段要解决什么

Phase 2 解决的是“系统真相存在哪里、怎么读写、怎么追踪”的问题。M0 之后所有 API、CLI、执行闭环都必须依赖这一层。

本阶段必须回答：

- 哪些数据进 SQLite
- 如何初始化和重建数据库
- 业务层如何隔离 SQL
- timeline 如何成为 operator 的第一调试入口

---

# 2. 输入与前置条件

## 2.1 输入材料

- Phase 1 的 Wave 1 schema v1
- preset seed 设计
- Phase 0 的 SQLite 和 Evidence 相关 ADR

## 2.2 Entry Criteria

- contracts v1 已冻结
- `manual preset only` 已生效
- 没有未决的对象主键 / 命名争议

---

# 3. 核心交付物

- `infra/migrations/`
- SQLite schema v1
- SQLite WAL 与连接策略
- `packages/core-domain/repositories/`
- `run_events` 数据模型与查询接口

建议最小落表：

- `runs`
- `phases`
- `task_cards`
- `runtime_tasks`
- `task_packets`
- `evidence`
- `review_verdicts`
- `preset_definitions`
- `run_events`

说明：

- `HandoffLite` 在 M0 只冻结语义，不进入首批落表范围

---

# 4. 详细工作流

## 4.1 工作流 A：SQLite schema v1 与迁移框架

对应任务：T0-12

### 开发步骤

1. 先确定 DB 初始化方式和文件落位策略。
2. 设计首批表结构和主键、外键关系。
3. 配置 SQLite WAL 模式与连接策略。
4. 建立初始 migration。
5. 建立 reset-db 方式，支持本地重复初始化。

### 设计原则

- 表结构尽量与 contracts 一一对应
- 不在 DB 层提前引入 M2 表
- 外键关系以 M0 最小主链为核心
- 尽量不依赖 SQLite 专有行为
- M0 保持串行执行语义，不额外引入进程级全局 Mutex

### 实现重点

- `runs` 和 `preset_definitions` 必须最先落地
- `run_events` 必须可单独查询
- 时间字段统一格式

## 4.2 工作流 B：Repository v0

对应任务：T0-13

### 开发步骤

1. 为每类核心对象建立 repository 接口。
2. 将 CRUD 能力按“业务动作”而不是“纯表操作”命名。
3. 确保上层服务不直接写 SQL。

### 最小 repository 集

- `RunRepository`
- `PresetRepository`
- `TaskRepository`
- `EvidenceRepository`
- `ReviewRepository`
- `EventRepository`

### 设计原则

- 接口命名要表达业务语义
- repository 返回的对象类型要尽量稳定
- 不让 API 层知道底层 SQL 细节

## 4.3 工作流 C：run events 与 timeline

对应任务：T0-14

### 开发步骤

1. 定义最小事件枚举。
2. 设计事件 payload 的最小摘要格式。
3. 设计 timeline 查询接口的排序和返回结构。
4. 明确哪些业务动作必须写 event。

### M0 必须覆盖的事件

- `run_created`
- `preset_selected`
- `phase_created`
- `runtime_task_created`
- `runtime_task_started`
- `runtime_task_completed`
- `evidence_submitted`
- `review_submitted`
- `run_completed`
- `run_failed`

### payload 约束

- 每个事件类型定义最小 payload schema
- `payload_json` 只存摘要、关键 ID 和有限状态字段
- timeline 默认不存储完整 stdout / stderr 原文

### payload 建议字段

- `event_id`
- `run_id`
- `event_type`
- `created_at`
- `object_type`
- `object_id`
- `summary`
- `payload_json`

### 建议最小 payload 示例

- `run_created`：`{"goal": str, "preset_id": str}`
- `preset_selected`：`{"preset_id": str, "preset_name": str}`
- `runtime_task_completed`：`{"runtime_task_id": str, "return_code": int, "duration_ms": int}`
- `evidence_submitted`：`{"evidence_id": str, "summary": str}`
- `review_submitted`：`{"verdict_id": str, "decision": str}`

---

# 5. 建议实现顺序

1. 先建表和 migration
2. 再写 repository 接口与实现
3. 最后接入 run events

原因是 timeline 的价值建立在稳定持久化之上，而不是反过来。

---

# 6. 建议测试设计

## 6.1 Migration 测试

- 空库初始化成功
- 重复执行不会破坏状态
- reset 后可重新 migrate
- WAL 模式与连接策略可被确认

## 6.2 Repository 测试

- Run 可以创建和查询
- Preset 可以 seed 和读取
- Event 可以追加和按时间查询

## 6.3 Timeline 测试

- 相同 run 的事件能按顺序返回
- 可至少读到 `run_created` 与 `preset_selected`
- payload 摘要可读，不只是原始 JSON
- 不会泄露大体积 stdout / stderr 原文

---

# 7. 阶段内检查点

## Checkpoint 2A：数据库表结构锁定

检查项：

- 表结构是否足够支撑 Phase 3 的 API
- 是否提前引入 M2/M3 表

## Checkpoint 2B：Repository 隔离完成

检查项：

- 上层逻辑是否仍在直接写 SQL
- repository 是否已经覆盖关键对象

## Checkpoint 2C：Timeline 可读

检查项：

- timeline 是否适合调试使用
- event payload 是否有摘要语义

---

# 8. 验收与退出标准

## 8.1 Exit Criteria

- `make migrate` 可成功执行
- `make reset-db` 可成功执行
- 核心表可正常读写
- repository v0 可供服务层使用
- `run_events` 可按时间顺序查询

## 8.2 Gate 决策问题

1. 系统关键数据是否已经脱离内存态单点
2. timeline 是否已经能支撑调试
3. API 层是否可以基于 repository 开发

任意一项不成立，则 Phase 2 未完成。

---

# 9. 风险与缓解

- 风险：把 SQLite 当最终形态设计
  缓解：接口层按未来 PostgreSQL 兼容思路设计

- 风险：repository 只是薄 SQL 包装，没有业务语义
  缓解：接口命名围绕 run / preset / evidence / review 业务动作

- 风险：timeline 过粗导致后续难排障
  缓解：至少覆盖 run、preset、task、evidence、review 主节点

---

# 10. 本阶段完成后的直接产出

Phase 2 完成后，团队应立即拥有以下能力：

- 可以初始化并重建本地数据库
- 可以通过仓储接口访问核心业务真相
- 可以从 timeline 还原一个 run 的最小演进过程

这三件事成立，Phase 2 才算完成。
