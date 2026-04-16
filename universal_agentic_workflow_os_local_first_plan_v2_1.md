# Universal Agentic Workflow OS v2.1

**模式：Local-first, Cloud-ready**

**文档目标：** 定义一套可在个人 PC 上落地、但能够平滑升级到云端与高并发场景的通用 Agentic Workflow 操作系统方案。该系统面向软件工程、多模态内容生产、交互式产品构建、仿真验证等复杂任务，不依赖单一 CLI、单一模型、单一协议或单一供应商。

---

# 1. 项目定义

## 1.1 项目定位

本项目不是一个“更强的命令行助手”，也不是一个“超级 Prompt 指挥官”。

本项目的目标，是构建一个 **Universal Agentic Workflow OS**：

- 面向目标，而不是面向脚本。
- 具备稳定的控制面，而不是把所有决策都交给临时 Prompt。
- 可以动态生成和修订任务图，但任何变化都要经过编译、校验、审计和预算约束。
- 能够统一调度多种执行运行时，包括代码 CLI、多模态 CLI、本地脚本、MCP 工具、隔离沙盒，以及未来的云端 Worker。
- 能够处理多任务串并行、冲突控制、失败恢复、人工门禁、证据归档和长期记忆。

系统最终应支持：

- 软件工程工作流
- 多模态内容生成工作流
- 移动端/交互式体验构建与验证工作流
- 可插拔的领域扩展（Domain Packs）

## 1.2 当前现实约束

当前阶段的现实约束如下：

- 默认运行环境是个人 PC。
- 短期不以高成本云服务为前提。
- 系统必须支持本地开发、调试、演示和小规模多 Worker 协同。
- 架构不能因为本地优先而退化成不可扩展的玩具系统。
- 未来必须支持平滑升级到云端、多机和更高并发版本。

因此，本方案采用：

**工业级抽象 + 本地级实现**。

具体含义：

- **协议、边界、对象模型、调度语义、恢复语义** 按长期演进要求设计。
- **数据库、运行器、执行器、观测方式** 以本地可用、低成本、低运维复杂度为优先。
- 未来升级时替换实现层，不推翻协议层和领域模型。

## 1.3 核心成功标准

系统阶段性成功至少应满足以下标准：

1. 在本地 PC 上能完整跑通一条工作流主链：
   - 创建 Run
   - 选择 Preset
   - 形成计划
   - 编译任务图
   - 调度执行
   - 回收 Evidence
   - 做 Review
   - 触发 Recover / Retry / Rollback
   - 完成 Phase Closure 与 Final Acceptance

2. 上下文不再依赖“大而全总提示词”，而是以：
   - Task Card
   - Task Packet
   - Task Context 拉取
   - Evidence
   - Review Verdict
   - Query Service
   为主。

3. 至少两类执行器可被统一调度，且控制面不绑定某一 CLI。

4. 系统具备基本并发安全性：
   - 写任务需要 Claim
   - 未知写范围默认串行
   - 高风险改动进入 Barrier
   - Worker 卡死可被检测与回收

5. 系统具备恢复能力：
   - Retry
   - Fallback
   - Replan
   - Rollback
   - Human Gate

6. 未来升级到云端时：
   - 不需要推翻核心对象语义
   - 不需要推翻控制环
   - 不需要推翻 Worker Adapter 协议
   - 只替换数据库、执行器宿主、重型持久化运行时等实现层组件

7. 对于 M0 冷启动阶段：
   - 最小执行闭环必须可在断网环境下运行
   - 不依赖任何 LLM API Key
   - `make smoke` 必须能验证纯本地控制流与证据闭环

---

# 2. 设计原则

## 2.1 Local-first, Cloud-ready

- 本地开发、调试、演示与单机协作必须成立。
- 云端升级必须是替换实现，不是重写架构。
- 本地实现默认选择简单、稳定、便于调试的技术方案。
- 云端升级需要的接口、对象、抽象层必须从一开始就预留。

## 2.2 固定控制环 + 动态任务图

系统采用：

- **固定的宏观控制环**
- **受约束的动态微观任务图**

宏观控制环稳定，负责把系统行为锁定在可恢复、可审计、可预算、可干预的框架内。

微观任务图可以动态生成和修订，但必须通过 Compiler 和 Admission 才能进入执行。

## 2.3 协议优先，而不是 Prompt 优先

系统中的关键协作对象必须结构化：

- TaskCard
- RuntimeTask
- TaskPacket
- Evidence
- ReviewVerdict
- Claim
- BudgetLedger
- RecoveryAction

Prompt 只承担理解与生成作用，不承担主状态机职责。

## 2.4 证据优先，而不是摘要优先

系统默认以 **Machine-readable Evidence** 为真相源。

Summary 只保留为：

- 人类快速理解
- Operator 处理异常
- 生成说明性解释

机器协作、审计、恢复、质量回放、失败记忆写入都应基于结构化 Evidence。

## 2.5 控制面与执行面分离

控制面负责：

- 接受目标
- 计划编译
- 调度与准入
- 并发控制
- 预算与熔断
- 审批与恢复
- 证据与审计

执行面负责：

- 代码修改
- 文件读写
- 多模态生成
- 构建、测试、模拟器驱动
- 外部 CLI / MCP / API 调用

CLI 只是工人，不是系统本体。

## 2.6 通用内核 + Domain Pack

通用内核负责：

- 控制环
- 核心对象
- 编译、调度、恢复
- 证据、预算、观测、记忆

具体领域能力通过 Domain Pack 注入，例如：

- 软件工程 Domain Pack
- 多模态内容 Domain Pack
- 移动仿真 Domain Pack
- 可玩内容构建 Domain Pack

## 2.7 多模态能力商品化，系统重心转向控制层

随着越来越多 CLI 和运行时原生支持文本、图片、视频、音乐、语音、视觉理解与搜索能力，系统不应继续把“多模态模型接入”当作主研发重点。

系统应将多模态能力视为：

**执行器暴露的一组能力（Capabilities）**。

真正长期值钱的层是：

- 任务编译
- 执行器选择
- 冲突控制
- 证据归一化
- 质量验证
- 预算与恢复

---

# 3. 总体架构

本系统采用 10 个逻辑平面。部分平面在实现上可以合并，但语义边界应当明确。

## 3.1 Plane A：Experience & Control Tower

职责：

- 创建、恢复、暂停、回滚、重放、分叉 Run
- 展示 DAG、Phase、Task、Budget、Claims、Artifacts、Evidence、Review Verdict
- 展示关键路径与异常
- 执行人工 Gate 决策

本地实现：

- **M0 禁止以 Web 控制台为主任务**
- 默认采用 CLI + HTTP API + JSON 输出
- 如确实需要查看器，优先极简 TUI / timeline viewer，而不是完整前端
- Web 控制台最早在 M1.5 以后再进入主计划

云端升级：

- 多用户控制台
- 更强的权限控制
- 多项目与批次管理

## 3.2 Plane B：Governance & Core Contracts

职责：

- 定义顶层对象语义
- 维护 TaskCard、Preset、Approval、Review 规则
- 维护工作规范、ADR、Smoke Tests 规范
- 管理 schema 版本演进

本地实现：

- Markdown + JSON schema + contracts package
- 版本化 schema

云端升级：

- schema registry
- 多版本协议兼容

## 3.3 Plane C：Planning Compiler & Preset Engine

职责：

- 接目标与上下文
- 选择 Preset
- 输出 PlanIR / PlanPatch
- 将计划编译为 RuntimeTask 集合
- 对任务图做校验与约束收紧

冷启动规则（M0-M1）：

- **M0 默认只允许用户显式指定 Preset**
- 系统只做 Preset 合法性检查，不做自动分类
- M1 可增加 `preset_suggester`，但只能给建议，不能自动生效
- 只有在 Preset 库、错误分类与评估集稳定后，才允许引入 heuristic / LLM-assisted resolver

必须校验：

- DAG 无环
- 依赖完整
- 任务可验证
- 写范围已声明
- 预算满足要求
- 高风险任务需要审批策略

## 3.4 Plane D：Economic & Admission Plane

职责：

- 预算分配
- 准入判断
- 资源熔断
- 重试上限控制
- 人工审核容量控制

资源维度：

- token
- 美元成本
- GPU/设备分钟
- provider quota
- worker 并发槽位
- retry 次数
- human review 次数

## 3.5 Plane E：Durable State & Memory Plane

职责：

- 持久化 Run / Phase / Task / Evidence / Claim / Budget 等业务真相
- 提供读写分离的查询视图
- 提供记忆与检索接口
- 写入失败记忆、设计记忆、资产记忆等

本地实现：

- SQLite 为默认数据库
- 仓储接口与迁移体系按未来 PostgreSQL 兼容设计

云端升级：

- PostgreSQL
- 更强索引、读副本、异步写入

## 3.6 Plane F：Orchestration & Cognitive Fabric

职责：

- 驱动宏观控制环
- 维护细粒度控制状态
- 管理子图、暂停恢复、中断、审批等待
- 执行 Recover / Replan 控制逻辑

当前建议：

- 使用 LangGraph 作为当前主 runtime
- 通过 Anti-Corruption Layer 隔离 LangGraph API 变动

关键规则：

- Orchestration 调用 Scheduler
- 不允许 Scheduler 直接回调修改图状态
- LangGraph State 只保存轻量句柄与引用，不保存业务真相

## 3.7 Plane G：Conflict-aware Scheduler

职责：

- Claim 分配与释放
- Barrier 管理
- Lease 与 Heartbeat
- 并发准入
- 死锁检测与回收
- Speculative Parallel 许可

这是系统正确性的核心层，不可弱化为简单队列。

## 3.8 Plane H：Worker Fabric & Capability Registry

职责：

- 暴露统一的 WorkerAdapter 协议
- 注册执行器能力
- 路由任务到合适执行器
- 收集生成文件和结构化结果

执行器可以是：

- 本地 shell / Python / Node worker
- OpenCode adapter
- Codex CLI adapter
- 原生多模态 CLI adapter
- MCP adapter
- 隔离沙盒 worker

## 3.9 Plane I：Quality, Review & Simulation

职责：

- Review（对不对）
- Critic（好不好）
- 验证 hooks
- Golden set 检查
- 失败记忆写入
- 仿真与体验验证

说明：

- 这是一个概念上的独立平面。
- 在实现上，它会以 hooks、review services、simulation services 的形式横切嵌入多个控制节点。
- 不应演变成“什么都往里塞”的杂层。

## 3.10 Plane J：Thin Integration Bus

职责：

- 对接 MCP
- 对接外部 API
- 对接本地/远程工具
- 对接未来外部调用方

说明：

- MCP 是标准化接入总线，不是主状态机。
- 有原生 CLI 的能力优先走 CLI adapter。
- 没有 CLI 但有成熟 MCP 的能力走 MCP adapter。
- 两者都没有时再直连 API。

---

# 4. 宏观控制环

在任何 Run 启动前，系统必须先完成一个**运行前 Bootstrap**：

- Seed 至少 1–2 个最简 Preset
- 初始化本地 Preset Registry
- 确认默认 Preset 选择模式为 `manual`
- 确认最小 Smoke Test 可用

Bootstrap 不是单次 Run 的控制环步骤，而是系统能否跑通第一条 spine 的前置条件。

宏观控制环固定为 11 步：

1. Intake
2. Preset Selection
3. Planning
4. Compile
5. Admission
6. Dispatch
7. Execute
8. Review
9. Recover / Replan
10. Phase Closure
11. Final Acceptance

## 4.1 各步骤职责

### Intake
接收目标、约束、输入资料、用户偏好、预算上限。

### Preset Selection
为目标选择执行骨架。Preset 不等于完整工作流，而是执行策略模板。

### Planning
基于 Preset 和上下文生成 PlanIR。

### Compile
将 PlanIR 编译为 RuntimeTask 集合，并绑定约束。

### Admission
基于预算、并发、能力可用性、风控策略决定是否放行。

### Dispatch
把可运行任务交给 Scheduler，再由 Scheduler 执行 Claim 检查（M0 阶段默认 no-op pass）并选择 Worker。

### Execute
Worker 执行任务并持续上报 Heartbeat 与中间状态。

### Review
依据 Evidence 进行 Review 与 Critic。

### Recover / Replan
对失败、阻塞、超支、低质量或条件变化做纠正。

### Phase Closure
完成当前 Phase 的阶段性关闭与范围验证。

### Final Acceptance
完成整个 Run 的最终验收、归档、沉淀与结束。

## 4.2 Preset 机制

Preset 是“执行骨架模板”，用于限制系统自由度。它不是完整任务图，也不是 prompt 人设，而是对规划、编译、审查、预算与准入策略的模板约束。

### PresetDefinition 建议字段

- `preset_id`
- `name`
- `intent_class`
- `allowed_task_kinds`
- `default_parallelism_policy`
- `default_review_policy`
- `default_budget_policy`
- `required_gates`
- `required_evals`
- `fallback_policy`
- `notes`

### M0 值域约束（用于 contracts v1 与 seed presets）

- `allowed_task_kinds`：M0 至少支持 `shell_exec`、`noop`
- `default_review_policy`：M0 至少支持 `auto_only`、`human_required`
- `default_budget_policy`：M0 使用最小结构 `{"max_retries": int, "timeout_seconds": int}`

### 冷启动策略

M0 阶段 Preset 机制必须保守：

- 只允许**用户显式指定 Preset**
- 不允许 LLM 直接替用户决定 Preset
- 不允许“无 Preset 直接进 Planner”
- 所有 Preset 选择都要写入 run 事件日志

这样做的原因是：在冷启动阶段，Preset 选择错误会把整条 spine 带偏，而这个错误比单个任务失败更难定位。

### Bootstrap Presets（M0 必须 seed）

M0 至少写入以下 2 个最简 Preset：

- `feature_delivery`
- `research_spike`

可选第三个：

- `bugfix_repair`

这 2–3 个 Preset 应当足以支撑第一条 Vertical Spine。

### 扩展 Preset Registry（后续逐步加入）

- `bugfix_incident`
- `refactor`
- `migration`
- `multimodal_asset_batch`
- `interactive_prototype`

### PresetResolver 发展顺序

- **M0：** `manual_select(preset_id)`
- **M1：** `suggest(goal_text) -> ranked presets`（只建议）
- **M2+：** 可引入 `heuristic` 或 `llm_assisted` 模式，但必须保留人工覆盖权

## 4.3 Phase Closure 与 Final Acceptance 的区别

- **Phase Closure**：只验证当前阶段目标及其组合效果。
- **Final Acceptance**：验证整个 Run 的全局一致性、完整性和发布/归档条件。

### 单 Phase 退化规则

当 Run 只有一个 Phase 时：

- 仍保留两个步骤
- 但 Phase Closure 可以作为 Final Acceptance 的前置子集
- Final Acceptance 仍负责全局归档、记忆写入、发布/关闭动作

---

# 5. 核心对象模型

对象语义必须明确，但强 schema 冻结采用分波次策略。

## 5.1 Wave 1（M0 必须冻结）

这些对象是首条 spine 必须用到的：

- `Run`
- `Phase`
- `TaskCard`
- `RuntimeTask`
- `TaskPacket`
- `Evidence`
- `ReviewVerdict`
- `PresetDefinition`
- `HandoffLite`

## 5.2 Wave 2（M2 冻结）

这些对象在并发、安全和恢复引入时冻结：

- `Claim`
- `WorkerLease`
- `BudgetLedger`
- `ApprovalGate`
- `RunSnapshot`
- `ErrorSignature`
- `RecoveryAction`

## 5.3 Wave 3（M4 冻结）

这些对象在增强编译、跨任务交接、记忆与扩展域时冻结：

- `PlanIR`
- `PlanPatch`
- `Artifact`
- `MemoryNamespace`
- `HandoffPacket`
- `DomainPackDefinition`

## 5.4 对象定义

### Run
一次完整工作流会话。

建议字段：

- `run_id`
- `goal`
- `preset_id`
- `status`
- `current_phase_id`
- `created_at`
- `updated_at`
- `owner`
- `budget_policy_ref`
- `summary_ref`

### Phase
Run 中的一组阶段性任务集合。

建议字段：

- `phase_id`
- `run_id`
- `name`
- `objective`
- `status`
- `created_at`
- `entry_criteria`
- `exit_criteria`
- `order_index`

### TaskCard
对人类与 Planner 可读的任务描述对象。

最小字段：

- `id`
- `name`
- `created_at`
- `status`
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

设计/多模态任务可再扩展：

- `design_inputs`
- `asset_constraints`
- `visual_targets`
- `eval_hooks`

### RuntimeTask
经过编译后可调度的任务对象。

建议字段：

- `runtime_task_id`
- `run_id`
- `phase_id`
- `task_card_id`
- `task_kind`
- `status`
- `created_at`
- `dependency_ids`
- `required_capabilities`
- `write_scope`
- `review_policy`
- `budget_slice`
- `retry_policy`
- `admission_policy`

### TaskPacket
发给 Worker 的执行合同。

建议字段：

- `packet_id`
- `run_id`
- `phase_id`
- `runtime_task_id`
- `created_at`
- `task_kind`
- `objective`
- `background_brief`
- `read_set`
- `write_scope`
- `forbidden_scope`
- `dependency_refs`
- `expected_outputs`
- `validation_hooks`
- `review_policy`
- `relevant_memories`
- `known_risks`
- `budget`
- `escalation_rules`
- `schema_version`

### Evidence
任务执行结果的机器真相。

建议字段：

- `evidence_id`
- `run_id`
- `runtime_task_id`
- `created_at`
- `summary`
- `evidence_json`
- `changed_files`
- `checks`
- `self_check`
- `known_gaps`
- `followups`
- `artifact_refs`（M0 最少包含 `path`、`sha256`、`mtime`、`size_bytes`）
- `telemetry_refs`
- `cost_usage`
- `schema_version`

### ReviewVerdict
对任务结果的审核结论。

建议字段：

- `verdict_id`
- `run_id`
- `runtime_task_id`
- `created_at`
- `reviewed_at`
- `reviewer_type`
- `decision`
- `blocking_findings`
- `non_blocking_findings`
- `recommended_actions`
- `retry_hint`
- `risk_level`
- `requires_human_gate`

### Claim
对资源范围的占用声明。

建议字段：

- `claim_id`
- `run_id`
- `runtime_task_id`
- `scope_type`
- `scope_key`
- `mode`
- `ttl`
- `holder`
- `status`

### WorkerLease
Worker 对任务的运行租约。

建议字段：

- `lease_id`
- `runtime_task_id`
- `worker_id`
- `started_at`
- `heartbeat_at`
- `ttl`
- `status`

### BudgetLedger
预算账本对象。

建议字段：

- `ledger_id`
- `run_id`
- `scope`
- `resource_type`
- `allocated`
- `consumed`
- `remaining`
- `thresholds`
- `updated_at`

### ApprovalGate
需要人工或高阶策略审批的门。

建议字段：

- `gate_id`
- `run_id`
- `scope`
- `reason`
- `required_role`
- `status`
- `input_refs`
- `decision_ref`

### RunSnapshot
在 rollback/replay/fork 时冻结的状态快照。

建议字段：

- `snapshot_id`
- `run_id`
- `phase_id`
- `created_at`
- `event_offset`
- `db_state_ref`
- `graph_state_ref`
- `note`

### ErrorSignature
标准化错误签名，用于 watchdog 和 recovery 决策。

建议字段：

- `signature_id`
- `class`
- `subclass`
- `normalized_message`
- `root_hint`
- `scope`
- `fingerprint`

### RecoveryAction
恢复动作记录对象。

建议字段：

- `action_id`
- `run_id`
- `runtime_task_id`
- `action_type`
- `trigger_reason`
- `input_refs`
- `result`
- `created_at`

### Artifact
生成物对象。

建议字段：

- `artifact_id`
- `run_id`
- `type`
- `path`
- `mime_type`
- `size`
- `lineage_ref`
- `checksum`
- `metadata`

### MemoryNamespace
记忆命名空间定义。

建议字段：

- `namespace_id`
- `name`
- `kind`
- `scope`
- `retention_policy`
- `retrieval_policy`

### HandoffLite
Wave 1 即可使用的轻量交接对象，用于 Phase 间、Review 后修复、Retry Lineage 等场景，避免跨步骤上下文断层。

M0 阶段要求冻结其语义与最小 schema，但不要求进入首批落表范围，也不进入 M0 smoke 主链。

建议字段：

- `handoff_lite_id`
- `from_task_id`
- `to_task_id` 或 `to_phase_id`
- `upstream_summary`
- `changed_files`
- `checks`
- `blocking_risks`
- `recommended_next_focus`
- `evidence_ref`

### HandoffPacket
完整的跨任务/跨角色交接包。它是 `HandoffLite` 的增强版，用于跨角色、跨域、跨 Pack 的复杂交接。

建议字段：

- `handoff_id`
- `from_role`
- `to_role`
- `summary`
- `changed_files`
- `checks`
- `open_risks`
- `recommended_focus`
- `artifact_refs`
- `review_context`
- `retry_lineage`
- `relevant_memories`

---

# 6. 错误分类体系（Error Taxonomy）

恢复能力的前提是错误可分类，而不是只做字符串匹配。

## 6.1 一级分类

- `transient`
- `permanent`
- `partial_success`
- `scope_violation`
- `contract_violation`
- `budget_exhausted`
- `provider_failure`
- `environment_missing`
- `simulation_failure`
- `quality_failure`
- `human_gate_required`

## 6.2 二级分类示例

### transient
- 网络抖动
- 供应商临时限流
- 本地子进程偶发失败

### permanent
- 缺失文件且无法生成
- 不支持的操作
- 任务定义不完整

### partial_success
- 部分文件已生成
- 部分验证通过
- 需要后续补齐

### scope_violation
- 修改越界
- 未声明写范围
- 写入受保护区域

### contract_violation
- 输出不符合 schema
- 未产生必需 artifact
- Evidence 缺关键字段

### budget_exhausted
- token 超限
- 美元成本超限
- retry 次数耗尽

### provider_failure
- 供应商返回异常
- 模型不可用
- 配额不可用

### environment_missing
- 缺失依赖
- 缺失 SDK/工具
- 执行环境不满足

### simulation_failure
- 自动仿真未通过
- UI/交互验证失败

### quality_failure
- 功能正确但质量不达标
- 风格不一致
- 设计约束不满足

### human_gate_required
- 需要人工审批
- 风险等级超阈值

## 6.3 默认恢复阶梯

1. `local_retry`
2. `tool_or_model_fallback`
3. `bounded_replan`
4. `rollback_to_snapshot`
5. `human_escalation`

错误分类与恢复动作必须显式记录在 `RecoveryAction` 中。

---

# 7. Capability-driven 执行层简化方案

## 7.1 基本思想

系统不再把“图片生成服务”“视频生成服务”“语音生成服务”分别建成厚重内部子系统。

系统把这类能力统一看作：

**Worker 通过 Adapter 暴露出来的 Capabilities。**

因此，执行层的主抽象不再是“按模态分服务”，而是：

- Capability Registry
- Worker Adapter
- Artifact Normalizer
- Provider Policy

## 7.2 Capability Registry

建议能力命名示例：

- `text.chat`
- `text.reason`
- `code.edit`
- `code.review`
- `file.read`
- `file.write`
- `shell.exec`
- `image.generate`
- `image.edit`
- `video.generate`
- `music.generate`
- `speech.synthesize`
- `vision.understand`
- `web.search`
- `simulator.run`
- `appium.test`

Registry 记录：

- 哪个 Worker 支持哪些能力
- 该能力的成本估计方式
- 该能力的副作用等级
- 该能力是否需要隔离执行
- 该能力是否需要人工 Gate

## 7.3 WorkerAdapter 协议

```python
class WorkerAdapter(Protocol):
    def get_id(self) -> str: ...
    def get_capabilities(self) -> dict: ...
    def can_handle(self, packet: dict) -> bool: ...
    def estimate_cost(self, packet: dict) -> dict: ...
    def launch(self, packet: dict) -> dict: ...
    def heartbeat(self, lease_id: str) -> dict: ...
    def collect_artifacts(self, lease_id: str) -> list[dict]: ...
    def normalize_evidence(self, lease_id: str) -> dict: ...
    def cancel(self, lease_id: str) -> dict: ...
```

## 7.4 当前阶段推荐的执行器

首阶段只需要：

- `ShellAdapter`
- `OpenCodeAdapter`
- `GenericCliAdapter`（可封装未来的多模态 CLI）

MCP、隔离沙盒、模拟器可在第二阶段逐步接入。

## 7.5 为什么这样能简化系统

这样设计后：

- 不需要先搭很多按模态拆分的内部服务
- 不需要把 MCP 当默认唯一接入方式
- 不需要为每种模态都先做常驻 specialist
- 多模态执行能力可以直接作为 commodity worker 使用
- 核心研发重心转向控制、调度、证据、预算和质量

---

# 8. 并发、调度与安全模型

## 8.1 调用方向

必须固定为：

**Orchestration → Scheduler → WorkerAdapter**

- Orchestration 决定当前控制环位置与候选任务
- Scheduler 决定是否可运行、如何排队、如何分配 Claim
- WorkerAdapter 执行具体动作

不允许双向回调造成边界污染。

## 8.2 Claim 粒度

支持多粒度 Claim：

- 文件级 Claim
- 目录级 Claim
- 模块级 Claim
- 接口级 Claim
- 资产级 Claim
- 风格/设计 Freeze Claim

默认策略：

- 写任务必须显式声明范围
- 未声明写范围默认串行
- 公共接口、schema、核心模块默认进入 Barrier

## 8.3 Barrier

Barrier 触发条件示例：

- 修改公共 API
- 修改数据库 schema
- 修改共享样式系统
- 修改关键设计规则
- 发布前最后组装阶段

Barrier 期间：

- 限制并发
- 强化 Review
- 必要时触发 ApprovalGate

## 8.4 Worker Lease 与 Heartbeat

每个运行中的任务必须有 Lease：

- 启动时创建
- Worker 周期性上报 Heartbeat
- 超时视为失联
- Scheduler 可 reclaim 并转入 retry/reassign/escalation

## 8.5 死锁控制

需要至少实现：

- Claim acquisition 超时
- 持锁时间上限
- 环等待检测
- 强制释放或升级人工处理

## 8.6 Speculative Parallel

只允许在以下条件同时成立时启用：

- 低风险任务
- 可回滚
- 无共享写域
- 能产生清晰 Evidence
- 预算允许

## 8.7 Admission 规则

Admission 需要综合：

- 预算剩余
- Worker 能力可用性
- 并发槽位
- Claim 冲突情况
- 风险等级
- 是否需要审批

---

# 9. 运行时设计（LangGraph + 防腐层）

## 9.1 使用原则

LangGraph 在本方案中的定位是：

- 当前主 orchestration runtime
- 控制环执行器
- 子图协调器
- 暂停恢复承载器

它不是：

- 核心协议定义者
- 业务真相源
- 唯一不可替代的底层

## 9.2 Anti-Corruption Layer

必须单独建立 `runtime-langgraph` 防腐层。

职责：

- 封装 LangGraph API
- 隔离版本变化
- 将核心对象映射到 LangGraph state/ref
- 将运行时输出回写到业务层
- 通过统一的 `RuntimeGateway` 暴露给 Orchestrator，而不是让 service 层直连 LangGraph

约束：

- `packages/contracts/` 与 `packages/core-domain/` 不允许直接引用 `langgraph`
- LangGraph 相关 import 只能出现在 `runtime-langgraph` 或其适配边界中

## 9.3 LangGraph State 最小化

State 只保存轻量信息，例如：

- `run_id`
- `phase_id`
- `active_task_ids`
- `pending_approval_ids`
- `current_graph_step`
- `budget_snapshot_ref`
- `last_patch_ref`
- `last_error_signature`

强约束：

- 不允许在 LangGraph State 中存储 `contracts/` 包定义的对象实例
- State 只保存 ID、枚举值、引用和轻量快照句柄

### graph_step 建议枚举

- `intake`
- `preset_selected`
- `planned`
- `compiled`
- `admitted`
- `dispatching`
- `executing`
- `reviewing`
- `recovering`
- `phase_closing`
- `final_accepting`
- `done`
- `blocked`

### budget_snapshot_ref 刷新频率

建议：

- 每次 Admission 前刷新
- 每次 Recovery 前刷新
- 高成本任务执行后刷新

## 9.4 子图建议

- `MainControlGraph`
- `PlanningGraph`
- `DispatchGraph`
- `ReviewGraph`
- `RecoveryGraph`
- `PhaseCloseGraph`
- `FinalAcceptanceGraph`

M1 阶段不要求全量子图，仅需最小主控制图。

---

# 10. 存储、记忆与查询

## 10.1 Local-first 存储策略

当前阶段采用：

- SQLite：默认业务数据库
- 本地文件系统：Artifacts 与调试日志
- JSON 事件日志：可选导出

未来升级：

- PostgreSQL
- 对象存储
- 分层缓存

## 10.2 关键数据表

建议至少包含：

- `projects`
- `workflow_runs`
- `workflow_phases`
- `task_cards`
- `runtime_tasks`
- `task_packets`
- `task_evidence`
- `review_verdicts`
- `claims`
- `worker_leases`
- `approval_gates`
- `budget_ledgers`
- `run_snapshots`
- `error_signatures`
- `recovery_actions`
- `artifacts`
- `memory_namespaces`
- `memory_items`
- `run_events`

## 10.3 Query Service

建议提供：

- `progress`
- `status_brief`
- `status_detail`
- `timeline`
- `phase_snapshot`
- `operator_brief`
- `task_context`

## 10.4 Memory Namespace

建议预定义：

- `repo`
- `design`
- `asset`
- `failure`
- `profile`
- `policy`
- `release`

## 10.5 DB-first 到检索增强的演进

### 当前阶段

- SQL
- JSON 字段
- 全文检索
- 规则化 ContextPack 组装

### 后续阶段

- 语义检索
- failure memory 强化
- design/asset retrieval
- retrieval brief 注入 TaskPacket

---

# 11. Evidence、Review、Critic 与仿真

## 11.1 Evidence 双轨输出

所有任务完成后都应输出：

- `summary`
- `evidence_json`

其中：

- `summary` 给人看
- `evidence_json` 给机器处理

## 11.2 Review 与 Critic 分工

### Review
关注：

- 是否正确
- 是否越界
- 是否违反契约
- 是否缺少必要验证

### Critic
关注：

- 是否足够好
- 是否满足风格/设计目标
- 是否需要更高质量的生成或修正

## 11.3 Operator Brief

人类不是每一步都读 Summary。系统需要自动生成 `OperatorBrief`，只突出：

- 当前卡点
- 关键风险
- 预算异常
- 需要批准的动作
- 关键证据链接

## 11.4 Simulation

Simulation 按 policy 触发，而不是默认对所有任务启用。

触发场景：

- UI/交互类任务
- 移动端模拟
- 高风险体验变更
- 发布前验证

仿真输出也必须转成结构化 Evidence / Artifact。

## 11.5 Golden Sets 与 Failure Memory

需要长期维护：

- Golden workflow cases
- Golden review cases
- Golden failure cases
- Golden artifacts
- FailureMemory

---

# 12. 可观测性（Observability）

这是正式能力，不是附属优化。

## 12.1 目标

可观测性必须回答：

- 当前 Run 卡在哪
- 哪一步最耗时
- 哪一步最耗预算
- 为什么进入 Recovery
- 哪个 Worker 不稳定
- 哪个 Preset 最容易失败

## 12.2 四种观测信号

### 结构化日志

- run_id
- phase_id
- task_id
- worker_id
- event_type
- status
- duration
- cost
- error_signature

### 事件流

- `run_started`
- `phase_started`
- `task_admitted`
- `task_dispatched`
- `lease_heartbeat`
- `evidence_collected`
- `review_failed`
- `recovery_triggered`
- `approval_requested`
- `run_closed`

### 指标

- run 数量
- 任务成功率
- 平均执行耗时
- 平均重试次数
- 预算消耗速率
- claim 冲突率
- 串行化比例
- watchdog 触发频率

### Timeline / Trace

按 Run 生成完整时间线，用于 Debug 和 Replay。

## 12.3 当前阶段实现建议

- 结构化 JSON logs
- SQLite 中的 run_events
- 本地 timeline 页面或命令
- `make logs-tail`

---

# 13. 配置、密钥、幂等与版本演进

## 13.1 配置与密钥管理

当前阶段：

- `.env.local`
- 本地 config 文件
- provider 配置集中管理

未来升级：

- secret manager
- 分环境配置
- 远程注入

## 13.2 幂等性要求

所有带副作用任务必须有幂等策略：

- 文件写入使用 staging + atomic move
- 外部 API 调用带 request key / dedupe key
- 重试前检查已有 artifact 或标记
- RecoveryAction 必须可追踪

## 13.3 Schema 演进策略

所有关键对象必须带：

- `schema_version`
- 向后兼容策略
- 数据迁移脚本
- 兼容窗口

---

# 14. Domain Pack 体系

## 14.1 定义

Domain Pack 是对通用内核的受控扩展。

可扩展内容：

- 对象模型补充字段
- TaskKind
- Specialist catalog
- Review/Critic policy
- Eval hooks
- Simulation hooks
- Artifact 类型
- Release policy

## 14.2 生命周期

Domain Pack 状态：

- `registered`
- `enabled`
- `disabled`
- `deprecated`

规则：

- 新 Run 只能绑定 `enabled` 的 Pack
- 运行中的 Run 不应被强行切换 Pack 版本
- 如需切换，应通过 `PlanPatch + Approval` 显式升级

## 14.3 首批 Domain Packs

- `se_core`
- `multimodal_content`
- `mobile_simulation`
- `interactive_prototype`

---

# 15. 仓库结构

## 15.1 目标结构（完整视图）

```text
/apps
  /control-tower
  /orchestrator-api
  /worker-gateway
  /simulation-gateway
  /integration-bus

/packages
  /contracts
  /core-domain
  /planner-compiler
  /scheduler
  /runtime-langgraph
  /worker-adapters
  /budget
  /memory
  /quality
  /query-service
  /domain-se
  /domain-multimodal
  /domain-mobile
  /domain-interactive

/infra
  /migrations
  /scripts
  /docker
  /k8s
  /observability

/docs
  /adrs
  /architecture
  /governance
  /presets
  /evals
```

## 15.2 M0-M1 精简结构（实现视图）

```text
/apps
  /orchestrator-api

/packages
  /contracts
  /core-domain
  /planner-compiler
  /scheduler
  /worker-adapters
  /runtime-langgraph

/infra
  /migrations
  /scripts

/docs
  /adrs
```

说明：

- M0 不建立 Web 控制台。
- 早期操作面采用 `workflowctl` CLI + JSON timeline 输出。
- `query-service`、`memory`、`quality`、`budget` 先以内聚模块存在，不急于单独拆包。
- `worker-gateway` 可先合并进 `orchestrator-api`。
- Domain Pack 延后到 M4。

---

# 16. 核心 API 设计

## 16.1 Control APIs

- `POST /runs`
- `POST /runs/{run_id}/resume`
- `POST /runs/{run_id}/pause`
- `POST /runs/{run_id}/cancel`
- `POST /runs/{run_id}/rollback`
- `POST /runs/{run_id}/replay`
- `POST /runs/{run_id}/fork`

## 16.2 Query APIs

- `GET /runs/{run_id}/progress`
- `GET /runs/{run_id}/status-brief`
- `GET /runs/{run_id}/status-detail`
- `GET /runs/{run_id}/timeline`
- `GET /phases/{phase_id}/snapshot`
- `GET /tasks/{task_id}/context`

## 16.3 Runtime Callback APIs

- `POST /tasks/{task_id}/start`
- `POST /tasks/{task_id}/heartbeat`
- `POST /tasks/{task_id}/complete`
- `POST /tasks/{task_id}/fail`
- `POST /reviews`
- `POST /critics`
- `POST /simulations`

## 16.4 Governance APIs

- `POST /approvals`
- `POST /approvals/{gate_id}/decide`
- `POST /claims/acquire`
- `POST /claims/release`
- `POST /budgets/adjust`
- `POST /plans/patch`

## 16.5 Operator CLI（M0 必须具备）

- `workflowctl run create --goal ... --preset ...`
- `workflowctl run status <run_id>`
- `workflowctl run cancel <run_id>`
- `workflowctl run timeline <run_id>`
- `workflowctl task evidence <task_id>`
- `workflowctl db reset`
- `workflowctl approval decide <gate_id> --allow/--deny`

---

# 17. 本地开发框架

## 17.1 技术栈

- Python
- FastAPI
- LangGraph
- SQLite
- SQLAlchemy / Pydantic
- CLI-first operator surface（M0-M1）

## 17.2 DX 目标

本地开发必须具备：

- `make dev`
- `make migrate`
- `make smoke`
- `make logs-tail`
- `make reset-db`
- `workflowctl status`
- `workflowctl timeline`

## 17.3 本地运行方式

最小启动集合：

- Orchestrator API
- SQLite
- CLI operator surface（无 Web 页面）
- 1~2 个 WorkerAdapter

---

# 18. 里程碑计划

本项目采用双轨时间线：

- **12 周基线计划**：现实默认计划
- **8 周冲刺计划**：条件理想时的加速版本

原则：

- 12 周基线是默认承诺，不是假设“拖延时的补救版”
- 8 周冲刺只在集成顺利、需求稳定、AI 辅助质量高时采用
- M0 的实际工作量可能达到 2–3 周，不能低估对象冻结、ADR、冒烟失败和幻觉校正成本

## 18.1 12 周基线计划（默认）

### 周 1-3：M0 — Contract Freeze + Bootstrap

目标：

- 冻结 Wave 1 对象
- 写 ADR-001 ~ ADR-005
- 建 SQLite schema v1
- 建 Orchestrator skeleton
- Seed 最小 Preset Registry
- 明确 `manual` PresetResolver

产出：

- contracts v1
- `PresetDefinition` v1
- `HandoffLite` v1（语义冻结，不要求 M0 首批落表）
- SQLite schema v1
- Orchestrator skeleton
- Smoke test 0

限制：

- 不做 Web 控制台
- 不做复杂 subgraph
- 不做自动 Preset 分类

### 周 4-6：M1 — 最窄 Vertical Spine

目标：跑通最窄 spine。

建议 spine：

`Bootstrap Presets → Goal → Manual Preset Selection → Thin Compile → 1 RuntimeTask → ShellAdapter → Evidence → Auto-Review → Done`

要求：

- 保留最薄 compiler
- 保留最薄 LangGraph 主图
- 只接 ShellAdapter
- CLI 方式查看 run / timeline / evidence

### 周 7-8：M1.5 — 第二执行器 + 轻操作面

目标：

- 接第二类 WorkerAdapter（如 OpenCode 或 Generic CLI）
- 增加极简 operator surface（CLI 为主，可选 TUI）
- 保持主链不被前端开发拖慢

### 周 9-10：M2 — Scheduler + Claim + Lease

目标：引入 Wave 2 对象与基础调度安全。

产出：

- Claim
- WorkerLease
- BudgetLedger
- ApprovalGate
- RunSnapshot
- ErrorSignature
- RecoveryAction
- Scheduler v1
- Watchdog P0

### 周 11：M3 — Budget + Recovery + Observability

目标：补齐预算、恢复和观测主链。

产出：

- structured logs
- run_events timeline
- recovery ladder
- budget breaker
- watchdog P1
- Error taxonomy wiring

### 周 12：Stabilization + Demo

目标：

- 端到端 Demo
- Golden smoke demo
- 文档整理
- 下阶段 Domain Pack 路线冻结

## 18.2 8 周冲刺计划（Stretch）

仅在以下条件成立时启用：

- M0 在 2 周内完成
- 第一条 spine 在无重大返工情况下跑通
- 第二执行器集成阻力低
- 团队愿意接受更高的节奏风险

### M0（第 1-2 周）

- Wave 1 contracts
- ADR-001 ~ ADR-005
- SQLite schema
- Preset bootstrap
- Smoke test 0

### M1（第 3-4 周）

- 最窄 spine（ShellAdapter only）
- CLI operator surface
- Auto-Review 基线

### M2（第 5-6 周）

- Claim
- Lease
- BudgetLedger
- ErrorSignature
- RecoveryAction

### M3（第 7 周）

- Observability
- Budget breaker
- Watchdog P0/P1

### M4（第 8 周）

- 第二执行器
- 极简 TUI 或延后 Web 规划
- Demo / 稳定化

说明：

- Memory、Domain Pack、Simulation 深化进入第二个 12 周周期。
- 如果第 4 周末 spine 仍不稳定，立即退回 12 周基线，不继续硬压进度。

# 19. Smoke Tests

每个阶段都必须有 <= 5 分钟的 Smoke Test。

## M0 Smoke

- `migrate` 成功
- `POST /runs` 返回 201
- 在断网且未配置任何 LLM API Key 的环境中通过

## M1 Smoke

- Bootstrap 两个 Preset
- 创建 Run
- 手动选择 Preset
- 派发一个 shell echo 任务
- 回收 Evidence
- Auto-Review 通过

## M2 Smoke

- 两个写同一范围的任务被自动串行
- 一个任务 Lease 超时后被 Reclaim

## M3 Smoke

- 人工制造 provider failure
- 系统生成 ErrorSignature
- 触发 RecoveryAction
- BudgetBreaker 生效

## M4 Smoke

- 第二执行器可通过 CapabilityRegistry 被选中
- 一个 Domain Pack 被启用并跑完一个最小任务

---

# 20. 初始 ADR 列表

- `ADR-001`：为什么采用固定控制环而非自由 Agent 图
- `ADR-002`：为什么采用 Evidence 优先而非 Summary 优先
- `ADR-003`：为什么当前阶段采用 SQLite，未来迁移 PostgreSQL
- `ADR-004`：LangGraph 防腐层设计
- `ADR-005`：Claim 粒度与默认并发策略
- `ADR-006`：Capability Registry 与 Worker Adapter 统一抽象
- `ADR-007`：Quality Plane 作为横切能力的实现约束

---

# 21. 风险与缓解

## 21.1 主要风险

### LangGraph API 变动
缓解：防腐层 + 固定版本 + State 最小化

### 对象冻结过多过早
缓解：Wave 1 / 2 / 3 分阶段冻结

### 控制台拖慢主链开发
缓解：M1 只做最小 operator view

### Claim 粒度不当导致频繁串行
缓解：先保守、监控串行率、逐步精细化

### 执行器集成复杂度高于预期
缓解：M1 先用 ShellAdapter 跑通，OpenCode/多模态 CLI 后接

### 本地开发体验太差
缓解：先把 DX 纳入正式目标，提供最小 make 命令与 timeline

---

# 22. 第一条 Vertical Spine 的最终定义

第一条 Spine 必须足够窄，目标是验证控制环的数据是否真的能流通，而不是一次性验证所有能力。

## 22.1 Spine 前置条件

在第一条 Spine 运行前，必须先完成：

- Bootstrap Presets（至少 `feature_delivery`、`research_spike`）
- `PresetResolver = manual`
- SQLite schema 已迁移
- `workflowctl` 可查看 run 状态

## 22.2 Spine 目标

验证以下链路：

`Bootstrap Presets → Goal → Manual Preset Selection → Thin Compile → 1 RuntimeTask → ShellAdapter → Evidence → Auto-Review → Done`

## 22.3 关键约束

- 不接复杂 subgraph
- 不接多执行器路由
- 不做自动 Preset 分类
- 不做 Web 控制台
- 不做完整 Domain Pack

## 22.4 完成标准

- 能成功创建 Run
- 能手动选中 Preset
- 能生成单个 RuntimeTask
- 能通过 ShellAdapter 执行
- 能落库 Evidence 和 ReviewVerdict
- 能通过 CLI 输出 timeline 和结果

# 23. 最终结论

本方案的核心不是“让某个模型更自由”，而是：

- 用固定控制环约束系统漂移
- 用 Compiler 约束动态任务图
- 用 Scheduler 约束并发和副作用
- 用 Evidence 约束执行结果表达
- 用 Recovery / Budget / Watchdog 约束失控成本
- 用 Capability Registry 把执行器能力商品化
- 用 Domain Pack 保持通用内核的长期可扩展性

当前阶段，系统应坚持：

- **Local-first**：在个人 PC 上跑通最小完整链路
- **Cloud-ready**：协议、对象、抽象层一开始就预留升级位
- **控制优先**：把重心放在控制面、证据链、调度器、预算、质量与恢复，而不是反复封装模型接入层

这将是一条既现实可行、又不会在未来被重写推翻的路线。
