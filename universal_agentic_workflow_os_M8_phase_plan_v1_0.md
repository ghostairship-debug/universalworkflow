# Universal Agentic Workflow OS - M8 开发方案

**方案版本：** `v1.1 Freeze Draft`  
**方案日期：** 2026-04-19  
**仓库基线：** `M7 complete` + `Pre-M8 complete`  
**方案状态：** 当前唯一有效的 M8 总规划基线

---

## 1. M8 的唯一目标

M8 的目标不是把仓库做成一套平行于官方生态的通用 agent 平台。

M8 的目标是把当前仓库稳定收敛为：

**一个建立在成熟 agent/runtime/tooling 生态之上的、但仍由仓库自己掌握本地控制权的 workflow control plane。**

M8 完成后，系统应同时满足三件事：

1. **该借的已经借到位**
   - 标准 agent loop
   - 低层 persistence / checkpoint / interrupt
   - 通用 server / IDE / tracing substrate
   - 可复用 skills 格式语义

2. **该保留的仍然牢牢在仓库内**
   - run lifecycle
   - review / governance / budget / admission
   - domain packs
   - simulation
   - operator projections
   - release gates

3. **本地基线不被破坏**
   - 默认安装
   - 默认测试
   - 默认离线验证
   - 默认 operator surface
   - 在不接外部平台时仍可运行

---

## 2. 输入文档

本方案综合以下文档形成。

### 当前仓库与 freeze 基线

- [README.md](./README.md)
- [docs/current_development_workflow.md](./docs/current_development_workflow.md)
- [docs/reviews/pre-m8-freeze-review.md](./docs/reviews/pre-m8-freeze-review.md)

### 既有 M8 评估与方案

- [docs/reviews/m8-ecosystem-reuse-and-wheel-reinvention-assessment.md](./docs/reviews/m8-ecosystem-reuse-and-wheel-reinvention-assessment.md)
- [docs/reviews/m8-external-tool-integration-and-self-build-plan.md](./docs/reviews/m8-external-tool-integration-and-self-build-plan.md)
- [docs/reviews/m8-pre-entry-extra-optimization-assessment.md](./docs/reviews/m8-pre-entry-extra-optimization-assessment.md)

### 根目录新增评估

- [M8_Strategic_Evaluation_Report.md](./M8_Strategic_Evaluation_Report.md)
- [M8_Strategic_Evaluation_Claude_Opus.md](./M8_Strategic_Evaluation_Claude_Opus.md)
- [M8_Readiness_Deep_Evaluation.md](./M8_Readiness_Deep_Evaluation.md)
- [Pre_M8_Evaluation_Report.md](./Pre_M8_Evaluation_Report.md)

### 本轮复审

- [docs/reviews/m8-gpt-pro-reassessment-and-plan-update.md](./docs/reviews/m8-gpt-pro-reassessment-and-plan-update.md)

---

## 3. M8 的生态边界

这部分不是愿景，而是必须承认的现实边界。

### 3.1 LangGraph 的位置

LangGraph 当前更适合作为：

- **低层 orchestration/runtime**
- durable execution / memory / HITL / streaming substrate

而不是本仓库默认的高层 agent loop。

如果需要更高层 agent 抽象，应优先借：

- **LangChain `create_agent + middleware`**

### 3.2 LangChain agents 的位置

`create_agent` 应被视为 `M8` 的标准 agent lane 候选。

它适合承接：

- 标准 tool-calling loop
- middleware 驱动的动态工具选择
- fallback / retries / guardrails / HITL hooks

### 3.3 LangGraph API 的位置

若进入 durable runtime pilot：

- **Functional API** 作为首选接法
  - 适合最小改动接 persistence / memory / HITL / streaming
- **Graph API** 只用于复杂 graph-native 场景
  - shared state
  - complex branching
  - parallel merge
  - subgraphs
  - graph visualization

### 3.4 Agent Server / Studio 的位置

它们属于：

- server / IDE / debug tooling layer
- 可借用能力

不是：

- 本仓库在 M8 要去平行重造的平台层

### 3.5 MCP 的位置

MCP 是：

- 工具/资源协议
- 不是 trust policy
- 不是最小授权系统
- 不是 tool subset projection 机制

因此：

- trust tier
- allowlist
- schema budget
- tool subset
- token/context 控制

必须由本仓库 control plane 自己定义。

### 3.6 Observability 的位置

M8 不应在 `Phase 0` 就把自己绑定死到单一后端。

正确方向应是：

- **OTel-first**
- **sink-agnostic**

然后：

- 首个 sink 先实现 `Langfuse`
- `LangSmith` 作为后续可选 sink / tooling route

### 3.7 Skills 的位置

Skills 值得做兼容，但其定位更像：

- packaging / portability / interop 层

而不是：

- 当前 runtime 的核心主线

---

## 4. 核心原则：Borrow / Wrap / Own

## 4.1 Borrow：直接借，不重造

- 标准 agent loop：`create_agent + middleware`
- 低层 persistence / checkpoint / thread / interrupt
- low-level HITL pause/resume primitive
- server / IDE / graph debug tooling
- 通用 trace/eval substrate
- Skills 的开放格式语义

## 4.2 Wrap：薄封装，不做平替

- `RuntimeGateway`
- `CapabilitySource`
- `CapabilityRegistry`
- `ToolProjectionManifest`
- tool exposure policy
- trace export abstraction
- skill export/import adapter
- repository state ↔ external runtime state 映射层

## 4.3 Own：长期拥有，不能丢

- run lifecycle
- `compile / recompile / resume / cancel / approve / reject / reconcile / repair`
- review policy
- governance / release readiness / debt / audit
- budget / admission policy
- domain pack / preset / workflow catalog
- deterministic simulation
- local-first fallback discipline
- operator-facing projections：
  - `status-detail`
  - `inspection`
  - `summary`
  - `event-inspection`
  - `audit-report`
  - `release-readiness`

---

## 5. 绝对约束

1. **所有外部能力默认关闭**
2. **默认路径不得依赖云服务**
3. **public product state 继续以 repository / SQLite canonical state 为准**
4. **`TaskKind` 保持小而稳定**
   - 能力差异发生在 capability projection
   - 不发生在枚举爆炸
5. **M8 不动主稳定链**
   - `feature_delivery` 全周期固定在 native deterministic lane
6. **M8 首个试验 run class 锁定在低风险路径**
   - 推荐：`research_spike`
   - durable pilot 推荐：`research_spike_reviewable` 这类 review-heavy 变体
7. **所有外部集成必须是 `opt-in enhancement`**
8. **任何外部失败都必须可回退到本地默认路径**

---

## 6. 目标架构

## 6.1 Control Plane（Own）

负责：

- run lifecycle
- review / governance / budget / admission
- domain pack resolution
- simulation
- operator projections
- release gates

## 6.2 Capability Plane（Wrap）

负责：

- `CapabilitySource`
- `CapabilityRegistry`
- `ToolProjectionManifest`
- trust boundary
- 从 `preset / task_kind / domain_pack / review policy` 映射到 tool subset

## 6.3 Execution Plane（Borrow + Wrap）

分四条 lane：

### Lane A — Native deterministic lane

保留现有：

- native / shell / noop

这是 M8 期间的默认稳定路径。

### Lane B — Standard agent lane

默认候选实现：

- `create_agent + middleware`

用途：

- 标准工具调用型 agent loop

### Lane C — Durable incremental lane

默认候选实现：

- LangGraph Functional API

用途：

- 最小侵入接 pause/resume / checkpoint / thread persistence

### Lane D — Graph-native complex lane

只在以下场景启用：

- shared state
- complex branching
- parallel merge
- subgraphs
- graph visualization 真实需要时

## 6.4 Observability Plane（Wrap）

- 本地 operator projections 继续保留
- 新增 OTel-first export abstraction
- 首个 sink 使用 `Langfuse`
- `LangSmith` 保留为后续 sink / dev tooling route

## 6.5 Packaging / Interop Plane（Wrap）

- internal domain pack / preset 继续是 canonical packaging
- 后置增加 Agent Skills exporter/importer
- 目标是 portability，不是让 Skills 成为 runtime 主语义

---

## 7. Canonical State 与 ID 模型

这一节必须在 `Phase 0` 冻结，不允许边做边改。

## 7.1 Canonical IDs

系统内至少要明确：

- `run_id`
- `review_id`
- `runtime_attempt_id`
- `simulation_id`
- `projection_id`
- `tool_call_id`
- `external_trace_id`
- `thread_id`
- `checkpoint_id`
- `assistant_id`
  - 仅当引入 Agent Server 时
- `external_session_id`
  - 仅对 MCP HTTP transport 需要

## 7.2 真相层规则

- **product truth**
  - `run_status / review_state / budget / audit / governance`
  - 一律在 repository state
- **runtime truth**
  - `thread_id / checkpoint_id / interrupt payload / graph state / task future`
  - 一律视为 implementation substrate
- **diagnostic visibility**
  - runtime refs 可以出现在 `status-detail`
  - 但只能放 diagnostics 区
  - 不能成为公共业务契约字段
- **双写规则**
  - 外部 runtime 状态写入不得绕过 repository transition
- **回退规则**
  - 任一 lane promotion 都必须允许清空 external refs 后退回 native lane

---

## 8. Phase 0 必须冻结的 ADR

`Phase 0` 不是走流程，而是 M8 成败前提。

至少冻结以下 ADR：

1. `Borrow / Wrap / Own Matrix`
2. `Execution Lane Strategy`
3. `Canonical IDs & State Mapping`
4. `TaskKind & Capability Projection Policy`
5. `MCP Trust Model & Server Profiles`
6. `Fallback / Degradation Policy`
7. `Observability Export Abstraction`
8. `Durable Runtime Pilot Contract`
9. `Feature Flags & Promotion Rules`

同时新增 feature flags：

- `UAWO_ENABLE_AGENT_LANE`
- `UAWO_ENABLE_MCP_SOURCE`
- `UAWO_ENABLE_EXTERNAL_TRACE_EXPORT`
- `UAWO_ENABLE_DURABLE_PILOT`
- `UAWO_ENABLE_SKILL_EXPORT`

---

## 9. Phase 总排布

新的 M8 顺序固定为：

1. `Phase 0 - Rebaseline and Scope Freeze`
2. `Phase 1 - Borrowed Agent Foundation`
3. `Phase 2 - MCP Capability Pilot`
4. `Phase 3 - Observability`
5. `Phase 4 - Durable Runtime Pilot`
6. `Phase 5 - Skills Alignment`
7. `Phase 6 - Confidence Pack`
8. `Phase 7 - Freeze Review`

这个顺序的原则是：

- 前半段先解决**运行模型与能力投影**
- 后半段再解决**观测、耐久化、包装互通和收尾**

---

## 10. 详细 Phase 计划

## Phase 0 — Rebaseline and Scope Freeze

### 目标

一次性冻结：

- 借用边界
- 状态映射
- fallback 规则
- 试点 run class
- feature flags

### 交付物

- Git checkpoint
- 9 份 ADR
- M8 task-card index
- `Borrow / Wrap / Own` 矩阵
- pilot run-class freeze
- 更新后的 dev workflow 文档

### 实施清单

1. 对当前基线做一次干净 checkpoint
2. 冻结试点 run class：
   - `feature_delivery`：M8 全程固定 native lane
   - `research_spike`：Phase 1 标准 agent lane pilot
   - `research_spike_reviewable`：Phase 4 durable pilot
3. 冻结 `TaskKind` 策略：
   - **不扩枚举**
   - 所有 MCP/tool 差异进入 `ToolProjectionManifest`
4. 冻结 trust tiers：
   - `T0` built-in local capability
   - `T1` local stdio MCP
   - `T2` internal managed HTTP MCP
   - `T3` third-party remote HTTP MCP
   - M8 默认只批准 `T0/T1`
5. 冻结 observability 策略：
   - OTel-first
   - 首个 sink 使用 Langfuse
   - abstraction 不绑定单一 vendor
6. 冻结 durable runtime promotion 条件

### Exit Gate

- worktree clean
- 默认 flags 全关时：
  - 当前本地测试通过
  - offline validation 通过
- 9 份 ADR 全批准
- 没有公共 CLI/API 契约漂移

### 回退规则

`Phase 0` 没 freeze 完，不允许进入任何代码实现 phase。

---

## Phase 1 — Borrowed Agent Foundation

### 目标

先建立 **LangChain 标准 agent lane**，证明标准 tool-calling / middleware loop 不该继续自己写。

### 交付物

- `AgentExecutionLane`
- `ToolProjectionManifest`
- middleware-based dynamic tool filtering
- `research_spike` 标准 agent lane pilot
- 第一批 built-in read-only tools 包装

### 实施清单

1. 新增 `AgentExecutionLane` 抽象，位于 `RuntimeGateway` 之上
2. 用 `create_agent` 建一条标准 agent lane
3. 第一批只接 **built-in read-only tools**
4. 用 middleware 实现动态工具暴露：
   - `preset`
   - `task_kind`
   - `domain_pack`
   - review policy
   - trust tier
5. 为 `research_spike` 建一个最小 pilot：
   - 读型能力
   - 无副作用
   - 输出结构化结果
   - 保留现有 review path
6. 允许 checkpointer 接入，但此时不要求 durable pilot

### Exit Gate

- `research_spike` 至少一条路径在 agent lane 跑通
- 动态工具过滤有效
- 现有 native lane 无回归
- `feature_delivery` 完全不受影响

### 回退规则

agent lane 必须整体由 feature flag 包裹，异常时可切回 native lane。

---

## Phase 2 — MCP-First Capability Plane Pilot

### 目标

把 capability plane 从“内建 adapter 清单”升级成“router-first projection plane”，但首轮只做 **local stdio MCP**。

### 交付物

- `CapabilitySource`
- `BuiltInCapabilitySource`
- `MCPCapabilitySource`
- `MCPServerProfile`
- `ToolProjectionManifest`
- fake MCP server test harness

### 实施清单

1. 新增 `CapabilitySource`
2. 把现有 built-in capabilities 迁入 `BuiltInCapabilitySource`
3. 新增 `MCPCapabilitySource`
4. 首个 pilot 只支持 **local stdio server**
5. 冻结 `MCPServerProfile` 字段：
   - `transport`
   - `startup_command`
   - `auth_mode`
   - `allowed_tools`
   - `max_tools`
   - `max_schema_bytes`
   - `startup_timeout_ms`
   - `call_timeout_ms`
   - `retry_policy`
   - `manifest_ttl`
6. `ToolProjectionManifest` 至少包含：
   - `capability_id`
   - `source_type`
   - `trust_tier`
   - `review_requirement`
   - `timeout_budget`
   - `schema_hash`
   - `enabled_for_preset`
   - `redaction_rules`
7. 第一个 MCP pilot 必须满足：
   - 工具数量少
   - schema 小
   - 只读
   - 无外部写副作用

### Exit Gate

- 至少一个 local stdio MCP server 被投影进 agent lane
- 模型看见的是 subset，不是全量 inventory
- MCP 故障不会影响 built-in capability path
- `TaskKind` 没有扩张

### 回退规则

`MCPCapabilitySource` 故障时自动降级为 built-in only。

---

## Phase 3 — Observability Abstraction and First Sink

### 目标

把通用 trace/eval 信号导出到外部，但**不改变本地 operator projections 的权威地位**。

### 交付物

- OTel-first export abstraction
- correlation model
- Langfuse sink
- optional LangSmith sink stub
- trace export failure isolation

### 实施清单

1. 定义统一 trace model：
   - root = `run_id`
   - child spans = `compile / execute / review / repair / capability projection / MCP call / simulation reference`
2. 规定最小 correlation 字段：
   - `run_id`
   - `review_id`
   - `runtime_attempt_id`
   - `tool_call_id`
   - `thread_id`
   - `checkpoint_id`
   - `domain_pack`
   - `preset`
   - `lane_type`
3. 首个 sink 用 Langfuse
4. 预留 LangSmith sink 接口，M8 不要求双写
5. 本地 `audit-report / status-detail / summary` 不依赖外部 sink

### Exit Gate

- 至少一条 agent lane / MCP lane 轨迹可在外部后端查看
- sink down 不影响本地报告
- 没有为 trace backend 改坏 public API contract

### 回退规则

export failure 只能记本地 warning，不得影响 run outcome。

---

## Phase 4 — Durable Runtime Pilot

### 目标

验证“把窄范围 workflow 跑进 LangGraph durable runtime”是否真的带来 pause/resume/HITL 收益，同时不丢掉 repository canonical state。

### 交付物

- `LangGraphRuntimePilot`
- `run_id ↔ thread_id/checkpoint_id` 映射
- review interrupt mapping
- rollback flag
- diagnostics exposure only

### 实施清单

1. **默认先用 Functional API**
2. 选定 pilot run class：`research_spike_reviewable`
3. 实现 interrupt-based review pause/resume：
   - 动作到 review request
   - review decision 到 resume / reject / edit
4. 所有 external runtime refs 只以 diagnostics 形式进入 operator surface
5. `run_status / review_state / budget / audit` 仍由 repository state 决定
6. 只有当 pilot 真需要 shared state / complex branching / subgraphs 时，才允许局部 Graph API 化
7. Agent Server / Studio 只允许作为**开发与调试工具**接入，不允许成为默认控制面

### Exit Gate

- 一条真实 pilot path 可 pause/resume 成功
- repository state 仍是 canonical
- external runtime state 未泄漏到公共业务契约
- native lane 仍是默认路径

### Kill Criteria

出现以下任一情况，则 durable runtime 不晋升：

- 必须改公共业务契约才能接入
- 双重持久化无法收敛到清晰映射
- review/governance 语义必须让位给 framework 内部状态
- fallback 不能一键关停

### 回退规则

`UAWO_ENABLE_DURABLE_PILOT=false` 后，系统必须回到 native / standard agent lanes。

---

## Phase 5 — Agent Skills Alignment

### 目标

在 runtime / capability 路径稳定后，再把 reusable capability packaging 对齐到 Agent Skills 兼容格式。

### 交付物

- internal skill manifest
- exporter
- one domain pack -> skill bundle example
- validation rules

### 实施清单

1. 不改变 canonical 的 domain pack / preset 体系
2. 新增 exporter，把一个选定 domain pack 打包成 Skill-compatible 目录结构
3. 规范最小字段：
   - `name`
   - `description`
   - `version`
   - `compatibility`
   - `resources`
4. 支持 progressive disclosure 风格资源组织
5. M8 内不要求 vendor-specific upload / deployment

### Exit Gate

- 至少一个 domain pack 成功导出为兼容 skill bundle
- 本地原有 domain pack resolution 不受影响

### 回退规则

skill export 完全独立于主执行路径，不得影响现有包装方式。

---

## Phase 6 — Confidence Pack and Targeted Cleanup

### 目标

补掉高价值置信缺口，但不重新打开大规模 hardening 周期。

### 交付物

- test pack
- fallback tests
- context/tool/schema budget enforcement（opt-in）
- targeted refactor patches

### 实施清单

1. 给以下内容补直接测试：
   - capability projection invariants
   - MCP fake server integration
   - agent lane fallback
   - trace export failure isolation
   - runtime ID mapping
   - review interrupt -> repository state transition
   - context budget guard
2. 如果 `Phase 4` 暴露 `services.py` 仍有单点过热，只允许做小而明确的 extraction
3. 把 context/tool/schema budget 从诊断升级为某些路径的 opt-in enforcement
4. 对所有 feature flags 做 disable-path tests

### Exit Gate

- default local baseline 仍稳定
- external lanes 都有 smoke coverage
- fallback paths 全可测

### 回退规则

不允许因为收尾阶段测试和 refactor 重新打开“大 hardening 里程碑”。

---

## Phase 7 — M8 Freeze Review

### 目标

正式决定 M8 的可宣称成果与 M9 候选项。

### 必答问题

1. 标准 agent lane 是否已经真实存在？
2. MCP-first capability plane 是否真实存在？
3. 外部 observability 是否真实接通？
4. durable runtime pilot 是否真实存在且边界安全？
5. local-first fallback 是否完整保住？
6. 仓库是否确实减少了通用基础设施的重复造轮子？
7. 哪些能力仍然必须留在 native deterministic lane？

### Freeze 产物

- M8 freeze review
- carry-over debt list
- M9 candidate queue
- promotion / no-promotion decisions by lane

---

## 11. 全局工程纪律

## 11.1 PR 纪律

- 一个 PR 只做一个抽象层变化
- 不允许同一 PR 同时改：
  - agent lane
  - MCP plane
  - durable pilot
- public CLI/API 字段变化必须自带 ADR 和 migration note
- 每个 phase 至少保留一个可完全关闭的 feature flag

## 11.2 测试纪律

每个 phase 必须同时具备：

- unit tests
- integration test
- disable-path test
- failure-path test
- operator projection regression test

## 11.3 Promotion 纪律

任何实验路径晋升为默认路径，必须同时满足：

- fallback 已验证
- public contract 无泄漏
- operator projection 可解释
- governance / review / budget 语义不被削弱

---

## 12. 全局安全与退化策略

## 12.1 MCP

- 默认只允许 `T1 local stdio`
- 远端 HTTP MCP 不是 M8 默认路径
- 所有 MCP server 都要：
  - allowlist
  - timeout
  - schema budget
  - tool count limit
- 模型不能直接看到 inventory 全量

## 12.2 Observability

- export 失败只记告警
- 不影响 run outcome
- 本地报告始终先于外部后端

## 12.3 Durable runtime

- 不能替代 repository canonical state
- external runtime refs 只能作为 diagnostics
- 一键关停后必须恢复到 native / standard agent lanes

## 12.4 Secrets

- 外部集成统一走 profile / policy
- 不允许“子进程继承整个宿主环境”式扩张
- stdio MCP 的环境变量注入必须白名单化

---

## 13. M8 默认不纳入范围

M8 默认不做这些事：

- 新的通用 web dashboard 主战线
- 平行于 Agent Server / Studio 的通用 server / IDE 平台
- 大规模新 worker-adapter family 扩张
- connector registry 大扩张
- `TaskKind` 爆炸
- model-first MCP
- 把 LangGraph 直接升格成全局默认 runtime
- 把 Agent Skills 提前成 runtime 主线
- 引入会破坏本地默认可运行性的强云依赖

---

## 14. M8 完成定义

M8 只有在以下条件同时成立时，才算真正完成：

1. `feature_delivery` 仍稳定运行在 native deterministic lane
2. `research_spike` 已有一条可用的 standard agent lane
3. 至少一个 local stdio MCP source 被 router-first 地投影给 agent lane
4. 至少一个外部 trace sink 成功接入，但默认本地路径不依赖它
5. 至少一条 `research_spike_reviewable` durable pilot 路径可 pause/resume
6. 至少一个 domain pack 可导出为 Agent Skill-compatible bundle
7. 没有因为外部化而破坏 local-first baseline
8. 没有为了 pilot 而让 external runtime state 侵入公共业务契约
9. 没有为了“工具更多”而扩张 `TaskKind`
10. operator projections 仍然是系统行为的权威解释面

---

## 15. 现在就该执行的第一组动作

开工顺序只需要记住一条：

**先做 `Phase 0` 的 ADR freeze 和 checkpoint，再做 `Phase 1` 的 borrowed agent lane。**

不要先做 Skills。  
不要先把 LangGraph 当全局替换。  
不要先把 Langfuse 或 LangSmith 绑死成唯一答案。  
不要先去做新 UI。  

M8 的正确打开方式，是先把“哪些能力不该自己写”在代码结构上落实掉，再去引入 MCP、durable runtime 和 portability。
