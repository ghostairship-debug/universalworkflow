# Universal Agentic Workflow OS v2.1 — M0 任务拆解版

**模式：Local-first, Cloud-ready**

**文档定位：** 本文将 v2.1 中的 **M0（Contract Freeze + Bootstrap）** 里程碑拆解为可执行任务集合，用于在本地个人 PC 环境下推进第一阶段开发。

**适用范围：** 仅覆盖 M0，不覆盖 M1 之后的第二执行器、复杂 Scheduler、完整质量平面、Domain Pack、Web 控制台与云端部署。

---

# 1. M0 的定义

## 1.1 M0 的核心目标

M0 的目标不是“做出一个功能很多的系统”，而是先建立这套系统最关键的**骨架与协议底座**，让后续 M1 的第一条 Vertical Spine 能在不返工核心语义的前提下跑通。

M0 必须完成的事情只有六类：

1. 冻结 **Wave 1 核心对象** 的语义与最小 schema。
2. 完成 **最小 Preset Bootstrap**，并固定 `manual` 选择模式。
3. 建立 **SQLite + 迁移体系 + 最小持久化层**。
4. 建立 **最小 Orchestrator Skeleton** 与主控制环入口。
5. 建立 **CLI-first 的 operator surface**，不做 Web 控制台。
6. 跑通 **M0 Smoke**，证明系统已具备进入 M1 的基础。

## 1.2 M0 的非目标

M0 明确**不做**以下内容：

- 不做 Web 控制台。
- 不做自动 Preset 分类。
- 不做复杂 LangGraph subgraph。
- 不做第二执行器（只保留 ShellAdapter）。
- 不做完整 Scheduler / Claim / Lease / BudgetLedger。
- 不做完整 Memory / Retrieval。
- 不做 Domain Pack。
- 不做重型仿真与多模态执行链。
- 不做云端部署与多机并发。

## 1.3 M0 成功标准

M0 完成后，至少应满足：

1. `contracts` 中已有 Wave 1 对象的 v1 定义。
2. `PresetDefinition` 已可 seed，且系统只能手动选 Preset。
3. SQLite 可迁移、可初始化、可 reset。
4. 可通过 API 创建 `Run`。
5. 可通过 CLI 查看 `Run` 的基础状态与 timeline。
6. `HandoffLite` 已有最小协议定义。
7. 已写完 M0 必需 ADR。
8. `make smoke` 可在 5 分钟内完成并通过。
9. M0 的 smoke 能在断网且未配置任何 LLM API Key 的环境中通过。

---

# 2. M0 工作原则

## 2.1 先冻结语义，再扩大功能

M0 的第一优先级是**对象语义和边界**，不是功能数量。任何会导致对象边界模糊的快速开发，都不应在 M0 接受。

## 2.2 先 CLI，后 UI

M0 只允许：

- HTTP API
- CLI 命令
- JSON 输出
- 可选的极简文本查看器

M0 不允许把 Web 页面开发当成主任务。

## 2.3 先 ShellAdapter，后其他 Worker

M0 只需要一个最简单、最可控的执行器：`ShellAdapter`。它的作用不是提供最终执行能力，而是验证控制流和 Evidence 闭环。

## 2.4 先手动 Preset，后智能路由

M0 不引入任何自动 Preset 分类逻辑。Preset 选择必须由人类显式指定。

## 2.5 先最小完整链，后横向扩展

M0 要做的是：

- 一个完整但很窄的骨架

而不是：

- 多条不完整的半成品路径

## 2.6 文档与契约的唯一口径

M0 阶段文档职责必须固定如下：

- `universal_agentic_workflow_os_local_first_plan_v2_1.md`：保留长期语义与演进方向
- `universal_agentic_workflow_os_M0_task_breakdown_v2_1.md`：作为 M0 字段、任务与验收口径的主文档
- `m0_phase_docs/`：只承载执行化方案，不重复发明字段与协议

如果三者出现冲突，以本任务拆解文档作为 M0 落地口径。

---

# 3. M0 范围冻结

## 3.1 M0 必须冻结的对象（Wave 1）

以下对象在 M0 必须完成 **语义冻结 + schema v1**：

- `Run`
- `Phase`
- `TaskCard`
- `RuntimeTask`
- `TaskPacket`
- `Evidence`
- `ReviewVerdict`
- `PresetDefinition`
- `HandoffLite`

说明：

- `HandoffLite` 在 M0 必须冻结语义与最小 schema
- `HandoffLite` 不要求进入首批落表范围，也不进入 M0 smoke 主链

## 3.2 M0 只需要“预留语义”的对象

以下对象在 M0 只需要在架构中占位，不要求完整落表：

- `Claim`
- `WorkerLease`
- `BudgetLedger`
- `ApprovalGate`
- `RunSnapshot`
- `ErrorSignature`
- `RecoveryAction`

这些对象的完整冻结留到 M2，但在 M0 应该至少：

- 写入命名与职责说明
- 明确归属平面
- 不允许未来与已有对象职责冲突

---

# 4. M0 产出总表

M0 的最终交付物应至少包含：

## 4.1 文档类

- `docs/architecture/m0-scope.md`
- `docs/contracts/wave1-objects.md`
- `docs/presets/preset-registry-v1.md`
- `docs/adrs/ADR-001.md`
- `docs/adrs/ADR-002.md`
- `docs/adrs/ADR-003.md`
- `docs/adrs/ADR-004.md`
- `docs/adrs/ADR-005.md`
- `docs/smoke/m0-smoke.md`
- `docs/tech-debt-registry.md`

## 4.2 代码类

- `packages/contracts/`
- `packages/core-domain/`
- `packages/runtime-langgraph/`（最小骨架）
- `packages/worker-adapters/`（至少 ShellAdapter）
- `apps/orchestrator-api/`
- `apps/operator-cli/` 或同等 CLI 模块
- `infra/migrations/`
- `infra/scripts/`

## 4.3 运行类

- SQLite schema v1
- 初始 Preset registry seed
- `make dev`
- `make migrate`
- `make reset-db`
- `make smoke`
- `workflowctl run create`
- `workflowctl run cancel`
- `workflowctl run status`
- `workflowctl run timeline`
- `workflowctl db reset`

---

# 5. M0 执行顺序

M0 推荐拆成 5 个工作包（Workstreams）：

1. **WS-A：Contract Freeze**
2. **WS-B：Preset Bootstrap**
3. **WS-C：State & Orchestrator Skeleton**
4. **WS-D：CLI / DX / Smoke**
5. **WS-E：Stabilization & Review**

推荐顺序：

`WS-A → WS-B → WS-C → WS-D → WS-E`

其中可并行的部分：

- 在 `T0-02` 完成后，WS-A 的 ADR 与 WS-B 的 schema 起草可部分并行
- WS-B 的 preset seed 文档与 registry 代码可并行
- WS-C 的 DB migration 与 API skeleton 可并行
- WS-D 的 CLI 命令与 smoke 文档可并行
- `T0-21a` 可在 WS-C 完成后启动，不必等待执行闭环全部完成

---

# 6. M0 详细任务拆解

下面按任务卡格式给出可执行任务。

---

## T0-01｜冻结 M0 范围与不做事项

**目标：** 明确 M0 的边界，防止范围蔓延。  
**依赖：** 无。  
**输出：** `docs/architecture/m0-scope.md`

### 需写清内容

- M0 的目标
- M0 的非目标
- M0 成功标准
- M0 的输入输出
- M0 与 M1 的边界

### 验收标准

- 文档明确列出“做什么 / 不做什么 / 完成算什么”。
- 团队内部对 M0 边界没有歧义。

### 验证

- 人工 review 文档
- ADR / task 卡引用该文档不出现冲突

---

## T0-02｜冻结 Wave 1 对象清单与职责

**目标：** 固定 M0 必须落地的对象边界。  
**依赖：** T0-01。  
**输出：** `docs/contracts/wave1-objects.md`

### 必须覆盖

- `Run`
- `Phase`
- `TaskCard`
- `RuntimeTask`
- `TaskPacket`
- `Evidence`
- `ReviewVerdict`
- `PresetDefinition`
- `HandoffLite`

### 验收标准

- 每个对象有一句话职责定义
- 每个对象有“服务谁 / 用来干什么 / 不该干什么”
- 对象之间关系图清晰

### 验证

- Review A：检查对象职责是否重叠
- Review B：检查是否遗漏关键对象

---

## T0-03｜定义 Wave 1 对象 schema v1

**目标：** 为 Wave 1 对象提供最小 schema。  
**依赖：** T0-02。  
**输出：** `packages/contracts/` 中的 schema 与模型定义

### 默认策略

- 所有 M0 contract 默认带 `schema_version`
- Pydantic / schema 校验侧默认允许 `extra=allow`
- 所有持久化的 Wave 1 对象必须带 `created_at`
- `HandoffLite` 在 M0 只冻结语义，不进入首批落表范围

### 至少包含字段

#### Run
- `run_id`
- `goal`
- `preset_id`
- `status`
- `created_at`
- `updated_at`

#### Phase
- `phase_id`
- `run_id`
- `name`
- `created_at`
- `status`
- `order_index`

#### TaskCard
- `task_card_id`
- `name`
- `created_at`
- `depends_on`
- `read_docs`
- `read_code`
- `output_files`
- `may_modify`
- `do_not_modify`
- `acceptance`
- `verify`
- `max_retries`
- `on_failure`

#### RuntimeTask
- `runtime_task_id`
- `run_id`
- `phase_id`
- `task_card_id`
- `task_kind`
- `created_at`
- `status`

#### TaskPacket
- `packet_id`
- `runtime_task_id`
- `created_at`
- `objective`
- `background_brief`
- `read_set`
- `write_scope`
- `expected_outputs`
- `validation_hooks`
- `review_policy`

#### Evidence
- `evidence_id`
- `runtime_task_id`
- `created_at`
- `summary`
- `changed_files`
- `checks`
- `known_gaps`
- `artifact_refs`

#### ReviewVerdict
- `verdict_id`
- `evidence_id`
- `created_at`
- `reviewed_at`
- `reviewer_type`
- `decision`
- `blocking_findings`
- `non_blocking_findings`
- `recommended_actions`

#### PresetDefinition
- `preset_id`
- `name`
- `created_at`
- `intent_class`
- `allowed_task_kinds`
- `default_review_policy`
- `default_budget_policy`
- `required_gates`

#### HandoffLite
- `handoff_id`
- `from_task_id`
- `to_phase_id` 或 `to_task_id`
- `upstream_summary`
- `changed_files`
- `checks`
- `blocking_risks`
- `evidence_ref`

### 验收标准

- 所有 schema 都可被序列化/反序列化
- 字段命名风格统一
- 无明显职责冲突

### 验证

- schema 单元测试
- JSON round-trip 测试

---

## T0-03.5｜建立 contracts 测试基础设施

**目标：** 给 Wave 1 contracts 提供稳定的回归保护。  
**依赖：** T0-03。  
**输出：** contracts 测试目录、基础 fixtures、快照与 round-trip 测试基线

### 至少覆盖

- Wave 1 对象 round-trip 测试
- `created_at` / `schema_version` 必填校验
- `ReviewVerdict.reviewer_type=auto` 默认值校验
- `PresetDefinition` 值域校验入口

### 验收标准

- 后续字段漂移会被测试第一时间发现
- 不依赖手工 eyeballing 判断 contracts 是否变形

### 验证

- contracts test suite 可独立执行

---

## T0-04｜定义 Wave 2/3 占位对象的职责说明

**目标：** 防止 M0 过度冻结，同时避免未来语义漂移。  
**依赖：** T0-02。  
**输出：** `docs/contracts/future-objects-outline.md`

### 必须包含

- `Claim`
- `WorkerLease`
- `BudgetLedger`
- `ApprovalGate`
- `RunSnapshot`
- `ErrorSignature`
- `RecoveryAction`
- `PlanIR`
- `PlanPatch`
- `Artifact`
- `MemoryNamespace`

### 验收标准

- 每个对象明确写出：为什么现在不实现、将来解决什么问题

### 验证

- 架构 review

---

## T0-05｜编写 ADR-001：固定控制环

**目标：** 固化“固定控制环 + 动态任务图”的根决策。  
**依赖：** T0-01。  
**输出：** `docs/adrs/ADR-001.md`

### 核心内容

- 为什么不用完全自由 agent 图
- 为什么宏观控制环必须固定
- 为什么动态只允许出现在任务图层

### 验收标准

- ADR 包含背景、决策、后果、替代方案

---

## T0-06｜编写 ADR-002：Evidence 优先

**目标：** 固化“证据优先而非 summary 优先”。  
**依赖：** T0-02。  
**输出：** `docs/adrs/ADR-002.md`

### 核心内容

- 为什么 summary 不能作为机器真相源
- Evidence 与 ReviewVerdict 的分工
- 为什么 Handoff 也要结构化

---

## T0-07｜编写 ADR-003：SQLite Local-first

**目标：** 固化本地数据库选择与未来迁移策略。  
**依赖：** T0-01。  
**输出：** `docs/adrs/ADR-003.md`

### 核心内容

- 为什么 M0 先用 SQLite
- 为什么仓储接口要按 PostgreSQL 兼容设计
- 未来迁移边界在哪里

---

## T0-08｜编写 ADR-004：LangGraph 防腐层

**目标：** 固化 LangGraph 的边界使用方式。  
**依赖：** T0-02。  
**输出：** `docs/adrs/ADR-004.md`

### 核心内容

- LangGraph 只做 orchestration runtime
- 业务真相不放进 runtime state
- runtime 只存 ref/handle
- 如何隔离未来 API 变化

---

## T0-09｜编写 ADR-005：Claim 粒度与默认并发策略

**目标：** 尽管 Claim 在 M2 才落地，也要在 M0 固化默认方向。  
**依赖：** T0-04。  
**输出：** `docs/adrs/ADR-005.md`

### 核心内容

- 默认保守并发
- 未知写范围默认串行
- 未来 Claim 的初始粒度建议
- 为什么先不做复杂并发控制

---

## T0-10｜设计 Preset Registry v1

**目标：** 给 M0 的 Preset 冷启动提供最小可用注册表。  
**依赖：** T0-03。  
**输出：** `docs/presets/preset-registry-v1.md` + 对应 seed 数据文件

### 至少 seed 两个 Preset

1. `feature_delivery`
2. `research_spike`

可选第三个：
3. `bugfix_repair`

### M0 必须冻结的值域

- `task_kind`：至少包含 `shell_exec`、`noop`
- `review_policy`：至少包含 `auto_only`、`human_required`
- `budget_policy`：统一为最小结构 `{"max_retries": int, "timeout_seconds": int}`

### 文档必须包含

- `feature_delivery` 的完整 JSON seed 示例
- `research_spike` 的完整 JSON seed 示例
- 每个字段的取值说明与默认值说明

### 验收标准

- 至少有 2 个 preset 可被读取、列出、合法性校验
- 没有自动选择逻辑

### 验证

- `workflowctl preset list`
- `workflowctl run create --preset feature_delivery` 合法

---

## T0-11｜实现 PresetResolver v0（manual only）

**目标：** 固定 Preset 冷启动策略。  
**依赖：** T0-10。  
**输出：** `packages/core-domain/preset_resolver.py` 或同等模块

### 功能范围

- `manual_select(preset_id)`
- 校验 preset 是否存在
- 将 preset 选择写入 run events

### 明确禁止

- LLM 自动分类
- 无 preset 自动兜底
- 基于目标文本的暗中猜测

### 验收标准

- 没传 preset 时，创建 run 失败并返回明确错误
- 非法 preset_id 时返回可解释错误

### 验证

- API 测试
- CLI 测试

---

## T0-12｜搭建 SQLite schema v1 与迁移脚手架

**目标：** 给 M0 提供最小持久化底座。  
**依赖：** T0-03。  
**输出：** `infra/migrations/`、数据库初始化脚本

### 首批表建议

- `runs`
- `phases`
- `task_cards`
- `runtime_tasks`
- `task_packets`
- `evidence`
- `review_verdicts`
- `preset_definitions`
- `run_events`

### 验收标准

- `make migrate` 成功
- `make reset-db` 成功
- SQLite 文件可在本地重复初始化

### 验证

- 迁移脚本自动化测试

---

## T0-12.5｜配置 SQLite WAL 与连接策略

**目标：** 在不引入额外全局 Mutex 的前提下，明确 M0 的串行执行与 DB 写入策略。  
**依赖：** T0-12。  
**输出：** SQLite WAL 配置约定、连接策略说明、开发环境默认设置

### 必须明确

- M0 采用串行执行语义
- SQLite 使用 WAL 模式
- 连接生命周期与事务边界
- 不额外引入进程级全局 Mutex

### 验收标准

- DB 层并发策略有唯一口径
- 后续 API / repository 层不再各自发明连接策略

### 验证

- DB 初始化检查
- SQLite 配置测试

---

## T0-13｜实现仓储接口 v0

**目标：** 隔离应用逻辑与数据库实现。  
**依赖：** T0-12。  
**输出：** `packages/core-domain/repositories/`

### 至少实现

- `RunRepository`
- `PresetRepository`
- `TaskRepository`
- `EvidenceRepository`
- `ReviewRepository`
- `EventRepository`

### 验收标准

- 上层服务不直接写 SQL
- 仓储接口风格统一

### 验证

- 仓储单测
- SQLite 集成测试

---

## T0-14｜定义最小 run event 模型

**目标：** 为 timeline、调试与后续 observability 打底。  
**依赖：** T0-12。  
**输出：** `run_events` schema + 事件枚举

### 至少包含事件

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

### 必须同时定义

- 每个事件类型的最小 payload schema
- payload 只允许放摘要与必要 ID
- timeline 默认不写入大体积原始 stdout / stderr

### 建议最小 payload

- `run_created`：`{"goal": str, "preset_id": str}`
- `preset_selected`：`{"preset_id": str, "preset_name": str}`
- `runtime_task_completed`：`{"runtime_task_id": str, "return_code": int, "duration_ms": int}`
- `evidence_submitted`：`{"evidence_id": str, "summary": str}`
- `review_submitted`：`{"verdict_id": str, "decision": str}`

### 验收标准

- 所有关键 API 都能写事件
- 事件按时间可查询

### 验证

- timeline API 测试

---

## T0-15｜搭建 Orchestrator API Skeleton

**目标：** 建立本地运行的最小主服务。  
**依赖：** T0-12、T0-13。  
**输出：** `apps/orchestrator-api/`

### 先做的 API

- `POST /runs`
- `GET /runs/{id}`
- `GET /runs/{id}/timeline`
- `GET /presets`
- `GET /tasks/{id}/evidence`

### `POST /runs` 的 M0 语义边界

- 只负责创建 `Run`
- 只负责校验并记录 `preset`
- 只负责写入 `run_created` / `preset_selected`
- 不在 M0 暴露公共 compile API
- thin compile 仅保留内部占位能力

### 明确不做

- 复杂 auth
- 多租户
- WebSocket
- 复杂审批流

### 验收标准

- 服务能本地启动
- API 文档可查看
- 可创建 run 并查回状态

### 验证

- `make dev`
- `curl` / `httpie` 调用接口

---

## T0-15.5｜统一 API 错误响应格式

**目标：** 让 M0 的 API 在 preset 校验、参数错误与资源不存在时返回稳定错误结构。  
**依赖：** T0-15。  
**输出：** M0 API 错误响应约定与基础实现

### 至少覆盖

- preset 缺失
- preset 不存在
- run 不存在
- task 不存在
- 参数校验失败

### 验收标准

- CLI 与 smoke 能依赖统一错误格式做排障
- 错误响应不混用框架默认结构和自定义结构

### 验证

- API 错误路径测试

---

## T0-16｜实现最薄 LangGraph 防腐层与主图占位

**目标：** 不在 M0 做复杂图，但要保留 runtime 接口位置。  
**依赖：** T0-08、T0-15。  
**输出：** `packages/runtime-langgraph/`

### 只需要做

- Anti-Corruption Layer
- `RuntimeGateway` 接口
- 一个最薄 graph wrapper
- 可从 API 层被调用的入口函数

### 明确不做

- 复杂 subgraph
- 中断恢复复杂逻辑
- 多节点协作图

### 强约束

- `packages/contracts/` 与 `packages/core-domain/` 不允许直接 import `langgraph`
- LangGraph State 不允许存储 `contracts` 包定义的对象实例
- State 只保存 ID、枚举与轻量 ref

### 验收标准

- 上层代码不直接依赖 LangGraph 细节
- runtime 可替换

### 验证

- 单元测试
- API 集成测试

---

## T0-17｜实现 Thin Compile v0

**目标：** 为 M1 的最窄 spine 提前打底。  
**依赖：** T0-03、T0-10、T0-15。  
**输出：** `packages/planner-compiler/thin_compile.py` 或同等模块

### M0 只要求

- 接受 goal + manual preset
- 生成最简单的单 `RuntimeTask`
- 生成对应 `TaskPacket`
- 不通过公共 API 暴露 compile 流程

### 说明

虽然真正的 Vertical Spine 在 M1 跑，但 M0 应先把薄 compile 的接口钉住。

### 验收标准

- 输入一个简单 goal 和 preset，可得到一个最小 RuntimeTask
- 输出结构稳定、可落库

### 验证

- 单元测试
- 固定输入输出快照测试

---

## T0-18｜实现 ShellAdapter v0

**目标：** 提供最小执行器。  
**依赖：** T0-03。  
**输出：** `packages/worker-adapters/shell_adapter.py`

### 最小接口

- `get_capabilities()`
- `estimate_cost(packet)`
- `launch(packet)`
- `collect_artifacts(task_id)`

### M0 的执行范围

- 支持执行简单 shell 命令
- 支持返回 stdout/stderr
- 支持输出最简单 artifact 信息

### 验收标准

- 能执行 `echo` 类命令
- 能收集结果并转成 Evidence 所需输入

### 验证

- 适配器单测
- 本地 shell 集成测试

---

## T0-19｜实现 Evidence 归一化 v0

**目标：** 建立“执行输出 → Evidence”转换器。  
**依赖：** T0-03、T0-18。  
**输出：** `packages/core-domain/evidence_builder.py`

### 最小能力

- 从 shell 执行结果生成 Evidence
- 提供 summary + structured fields
- 生成 `artifact_refs[*].path / sha256 / mtime / size_bytes`
- 落库

### 职责边界

- `artifact_refs` 的 hash / mtime 由 Evidence Builder 负责生成
- `ShellAdapter` 只负责执行与采集原始输出，不负责 artifact 完整性确权
- 必须具备最小的 out-of-band change 侦测能力

### 验收标准

- 任意 shell echo 任务可形成有效 Evidence

### 验证

- 单测
- 与 ShellAdapter 集成测试

---

## T0-20｜实现 Auto-Review v0

**目标：** 给最窄 spine 提供自动闭环的最小审查。  
**依赖：** T0-03、T0-19。  
**输出：** `packages/quality/auto_review_v0.py` 或同等模块

### M0 的最小规则

- 如果 shell 任务返回码为 0 且无明确错误输出，则 `decision=pass`
- 否则 `decision=fail`

### 说明

M0 的 Auto-Review 不是为了质量高，而是为了证明 ReviewVerdict 能进入主链。

### 验收标准

- shell 成功任务有 `pass` verdict
- shell 失败任务有 `fail` verdict

### 验证

- 成功/失败双样例 smoke

---

## T0-21a｜实现 Operator CLI v0（基础命令）

**目标：** 建立 M0 唯一允许的 operator surface。  
**依赖：** T0-15。  
**输出：** `apps/operator-cli/` 或等价模块

### 必须支持的命令

- `workflowctl run create --goal ... --preset ...`
- `workflowctl run cancel <run_id>`
- `workflowctl run status <run_id>`
- `workflowctl run timeline <run_id>`
- `workflowctl preset list`
- `workflowctl db reset`

### 验收标准

- 不依赖 Web 页面即可完成最小操作
- 输出可读、可复制

### 验证

- CLI e2e 测试

---

## T0-21b｜实现 Operator CLI v0（Evidence 命令）

**目标：** 在执行闭环落地后补齐证据查询命令。  
**依赖：** T0-19、T0-20、T0-21a。  
**输出：** `workflowctl task evidence <task_id>`

### 必须支持的命令

- `workflowctl task evidence <task_id>`

### 验收标准

- operator 可通过 CLI 查看结构化 Evidence
- 输出适合定位 artifact、checks 与 known gaps

### 验证

- CLI e2e 测试

---

## T0-22｜实现 DX 脚本与本地启动入口

**目标：** 降低 M0 的本地开发摩擦。  
**依赖：** T0-12、T0-15、T0-21a。  
**输出：** `Makefile` / `scripts/`

### 至少包含

- `make dev`
- `make migrate`
- `make reset-db`
- `make smoke`
- `make logs-tail`

### 验收标准

- 一个新人可按 README 在本地跑起系统

### 验证

- 按 README 冷启动测试

---

## T0-22.5｜建立依赖管理基线

**目标：** 固化 M0 的 Python 项目依赖与安装入口，避免环境口径分裂。  
**依赖：** T0-22。  
**输出：** `pyproject.toml` 或等价依赖清单、安装说明

### 至少包含

- 运行依赖清单
- 测试依赖清单
- 本地安装方式
- `make` / CLI 所依赖的解释器口径

### 验收标准

- 新成员能按单一依赖入口完成冷启动
- smoke 与测试不依赖隐式全局环境

---

## T0-23｜编写 M0 Smoke 文档

**目标：** 让 M0 有可重复、可定时的验收流程。  
**依赖：** T0-15、T0-21a。  
**输出：** `docs/smoke/m0-smoke.md`

### Smoke 目标

- migrate 成功
- 读取 Preset 列表成功
- 创建 Run 成功
- timeline 中能看到 `run_created` 与 `preset_selected`
- 在断网环境中通过
- 在未配置任何 LLM API Key 的情况下通过

### 验收标准

- 全流程 <= 5 分钟
- 全流程可脚本化

---

## T0-24｜实现 `make smoke`

**目标：** 把 M0 的最小验收自动化。  
**依赖：** T0-23。  
**输出：** 自动化 smoke 脚本

### 建议流程

1. reset-db
2. migrate
3. seed presets
4. 清理或显式覆盖 LLM API Key
5. create run
6. query run
7. query timeline
8. assert 关键事件存在

### 验收标准

- 在本地 5 分钟内跑完
- 失败输出可定位问题

---

## T0-25｜实现最小 timeline 查询能力

**目标：** 让 operator 能看到系统不是“黑盒”。  
**依赖：** T0-14、T0-15。  
**输出：** `GET /runs/{id}/timeline`

### 最小输出

- 时间戳
- 事件名
- 关键对象 ID
- 简短 payload 摘要

### 验收标准

- 一个 run 的关键事件按顺序可读

### 验证

- API 集成测试
- CLI timeline 测试

---

## T0-26｜编写 M0 README 与快速启动说明

**目标：** 固化本地使用方式。  
**依赖：** T0-22、T0-24。  
**输出：** `README.md` 或 `docs/getting-started-m0.md`

### 必须写清

- 环境要求
- 启动命令
- 常用命令
- smoke 运行方式
- 常见错误

### 验收标准

- 不依赖口头解释即可上手

---

## T0-27｜M0 评审与冻结会议输出

**目标：** 用一次结构化 review 宣告 M0 结束。  
**依赖：** T0-01 ~ T0-26。  
**输出：** `docs/reviews/m0-freeze-review.md`

### 必须回答的问题

- M0 的非目标是否被遵守
- Wave 1 是否已冻结
- Smoke 是否稳定
- `docs/tech-debt-registry.md` 是否完整登记延后项
- 哪些内容明确延迟到 M1/M2
- 是否允许进入 M1

### 验收标准

- 有明确 go / no-go 结论

---

# 7. M0 并行建议

## 7.1 可并行的任务簇

### 簇 A：语义冻结
- T0-01
- T0-02
- T0-04
- T0-05 ~ T0-09

### 簇 B：Preset 冷启动
- T0-10
- T0-11
- T0-03.5

### 簇 C：本地持久化底座
- T0-12
- T0-12.5
- T0-13
- T0-14

### 簇 D：运行骨架
- T0-15
- T0-15.5
- T0-16
- T0-17

### 簇 E：执行闭环
- T0-18
- T0-19
- T0-20

### 簇 F：操作面与 DX
- T0-21a
- T0-21b
- T0-22
- T0-22.5
- T0-23
- T0-24
- T0-25
- T0-26

## 7.2 关键路径

关键路径建议按如下推进：

`T0-01 → T0-02 → T0-03 → T0-03.5 → T0-10 → T0-11 → T0-12 → T0-12.5 → T0-15 → T0-15.5 → T0-21a → T0-23 → T0-24 → T0-27`

补充并行关系：

- `T0-05 ~ T0-09` 可在 `T0-02` 后与 `T0-03` 并行
- `T0-21a` 可在 `T0-15` / `T0-15.5` 后启动
- `T0-21b` 依赖 `T0-19` / `T0-20`

这条路径决定 M0 是否能如期结束。

---

# 8. M0 验收清单

M0 结束前必须逐条打勾：

- [ ] M0 范围文档完成
- [ ] Wave 1 对象清单冻结
- [ ] Wave 1 schema v1 完成
- [ ] contracts 测试基础设施完成
- [ ] Wave 2/3 占位职责文档完成
- [ ] ADR-001 ~ ADR-005 完成
- [ ] 至少 2 个 Bootstrap Preset 已 seed
- [ ] Preset 值域与 seed JSON 示例完成
- [ ] `manual` PresetResolver 生效
- [ ] SQLite schema v1 已迁移
- [ ] SQLite WAL 与连接策略固定
- [ ] 仓储接口可用
- [ ] run events timeline 可查询
- [ ] run event payload schema 已定义
- [ ] Orchestrator API skeleton 可启动
- [ ] API 错误响应格式统一
- [ ] RuntimeGateway 边界成立
- [ ] ShellAdapter v0 可执行简单任务
- [ ] Evidence builder v0 可落库
- [ ] `artifact_refs` 已包含 `sha256 / mtime / size_bytes`
- [ ] Auto-Review v0 可输出 ReviewVerdict
- [ ] Operator CLI 基础命令可用
- [ ] Operator CLI Evidence 命令可用
- [ ] `make dev / migrate / reset-db / smoke` 可用
- [ ] 依赖管理基线完成
- [ ] `docs/tech-debt-registry.md` 已建立
- [ ] M0 Smoke <= 5 分钟
- [ ] M0 Smoke 可在断网且无 LLM API Key 的环境中通过
- [ ] M0 freeze review 已通过

---

# 9. M0 进入 M1 的准入条件

只有满足以下条件，才允许进入 M1：

1. M0 验收清单全绿，或仅剩非阻塞问题。
2. `workflowctl run create --goal ... --preset ...` 已稳定可用。
3. `PresetResolver = manual` 已被强制执行。
4. timeline 中至少能稳定看到：
   - `run_created`
   - `preset_selected`
5. 不存在“没有 preset 也能偷偷创建 run”的后门。
6. Orchestrator 层没有把 LangGraph 细节泄漏到 contracts 层。
7. `contracts/` 与 `core-domain/` 中不存在直接 `langgraph` import。
8. M0 Smoke 可在断网且无 LLM API Key 的环境中通过。
9. README 足够让新成员冷启动。

如果以上任一条不满足，则不进入 M1，而是继续 M0 修复。

---

# 10. 最终建议

M0 的关键不在于写多少代码，而在于：

- 先把语义钉死
- 先把边界讲清
- 先把最窄主链打通
- 先用最小成本建立“系统不是黑盒”的调试能力

因此，M0 的最佳执行策略不是“全面开工”，而是：

**先冻结、后落库；先 CLI、后 UI；先 ShellAdapter、后复杂执行器；先 manual Preset、后智能路由；先 Smoke、后扩展。**
