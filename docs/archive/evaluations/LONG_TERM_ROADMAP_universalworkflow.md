# UniversalWorkflow 长期路线与架构收口方案

> 建议文件位置：仓库根目录  
> 建议文件名：`LONG_TERM_ROADMAP.md`  
> 适用对象：项目负责人、Codex、Claude Code、OpenCode、后续所有 coding agent  
> 当前阶段建议：M67-M72

---

## 0. 文档目的

本文档用于重新校准 UniversalWorkflow 项目的长期路线。

项目早期目标是：

```text
尽可能组合利用已有 AI / agent / MCP / CLI / 多模态 / 工程工具，
减少自研基础设施，
把项目做成一个可长期运行、可审计、可恢复、可自我迭代的 AI workflow 控制塔。
```

但在实际 AI 辅助开发过程中，项目逐渐出现了“自研平台化”趋势：

```text
原始目标：组合已有能力，少写代码
实际演化：每个缺口 AI 都顺手补一点
最终风险：adapter 变厚，control plane 变 runtime，runtime 变 framework
```

本文档的目标是：

1. 明确项目长期定位；
2. 明确哪些大板块应该引入成熟方案；
3. 明确哪些能力必须自研；
4. 明确 LangGraph、MCP、CLI Agent 生态在项目中的位置；
5. 明确 M67-M72 的长期开发路线；
6. 建立 Build-vs-Buy 纪律，避免继续无意识重复造轮子；
7. 给 Codex 等 coding agent 一个清晰、可执行、可验收的开发方向。

---

## 1. 项目长期定位

### 1.1 推荐定位

UniversalWorkflow 应定位为：

```text
Local-first AI Workflow Control Tower
本地优先的长程 AI 工作流控制塔
```

它不是：

```text
通用 agent framework
通用 coding agent
通用 workflow engine
通用 MCP 平台
通用 SaaS connector 平台
通用 observability 平台
通用 CI/CD 平台
```

它应该是：

```text
多个成熟 AI / CLI / MCP / runtime / 多模态工具之上的控制层、治理层、证据层和业务流程层。
```

### 1.2 一句话定义

```text
成熟工具负责“干活”；
UniversalWorkflow 负责“让谁在什么时候、以什么权限、用什么上下文、按什么验收标准干活”。
```

### 1.3 项目真正价值

UniversalWorkflow 的核心价值不在于重新实现成熟底层工具，而在于：

```text
1. 长程任务管理
2. 多 AI / 多 CLI / 多 MCP / 多工具调度
3. 上下文控制
4. 权限与自动化授权
5. 高风险动作确认
6. 能力投射与能力治理
7. 证据链
8. 自动审查与人工接管
9. 自我升级边界
10. 面向互动内容 / 游戏 / 多模态生产的业务流水线
```

---

## 2. 总体架构分工

长期架构应收敛为：

```text
+----------------------------------------------------------+
|                    Operator / Human                      |
+----------------------------------------------------------+
                            |
                            v
+----------------------------------------------------------+
|              UniversalWorkflow Control Tower             |
|----------------------------------------------------------|
| PolicyEngine | AutomationLease | Capability Registry     |
| MCP Broker   | CLI Adapter     | Evidence / Audit        |
| ReviewPolicy | OperatorPacket  | Business Workflow       |
+----------------------------------------------------------+
                            |
                            v
+----------------------------------------------------------+
|                    Runtime Substrate                     |
|----------------------------------------------------------|
| LangGraph Runtime Adapter                                |
| - graph execution                                        |
| - checkpoint                                             |
| - resume                                                 |
| - interrupt                                              |
| - conditional edge                                       |
| - subgraph                                               |
| - streaming runtime state                                |
+----------------------------------------------------------+
                            |
                            v
+----------------------------------------------------------+
|                    Capability Providers                  |
|----------------------------------------------------------|
| Codex CLI | Claude Code | Gemini CLI | OpenCode          |
| MCP Tools | Browser | Search | Figma/Canva | Media APIs  |
+----------------------------------------------------------+
                            |
                            v
+----------------------------------------------------------+
|                  Artifacts / Code / Reports              |
+----------------------------------------------------------+
```

---

## 3. Build-vs-Buy 总原则

### 3.1 不再默认自研

以后新增大能力前，必须先判断：

```text
这是项目核心差异化吗？
是否已有成熟方案覆盖一个完整板块？
是否只是几个小功能？
引入外部方案是否会侵蚀项目领域模型？
是否可以通过薄 adapter 隔离？
```

### 3.2 覆盖度规则

```text
外部成熟方案覆盖一个板块 ≥ 70%：
    优先引入 / 包装，不自研核心。

外部方案覆盖 40%-70%：
    做 spike 验证，比较维护成本、复杂度、适配成本。

外部方案覆盖 < 40%：
    可以考虑自研。

只是一个小功能：
    默认自研，不要为一个小功能引入大依赖。

项目核心差异化：
    必须自研。
```

### 3.3 大板块优先，小功能谨慎

正确策略不是：

```text
到处接成熟方案
```

也不是：

```text
什么都自己造
```

而是：

```text
成熟方案能承担一个清晰大板块时，引入；
成熟方案只能提供几个零碎小功能时，谨慎；
项目控制层、治理层、业务语义，自研。
```

---

## 4. 应该自研的核心能力

以下是 UniversalWorkflow 的核心差异化，应该长期自研：

```text
1. PolicyEngine
2. AutomationLease
3. OperatorActionReceipt
4. MutationContract
5. ReviewPolicy
6. Capability Registry
7. Capability Projection
8. MCP Broker
9. CLI Adapter Contract
10. Evidence / Audit
11. Operator Packet
12. PR-ready Summary
13. Local-first Operator Console
14. 多模型 / 多 agent 调度策略
15. 成本 / 失败 / 结果记录
16. 互动内容 / 游戏 / 多模态生产流水线
17. 风格一致性验收
18. 商业质量验收
19. 资产库 / 风格库 / 经验库领域模型
20. workflow 自我升级安全边界
```

这些能力不是 LangGraph、MCP、Codex CLI、Claude Code、Gemini CLI 可以直接替代的。

---

## 5. 不应继续自研的基础设施

以下方向不应作为 UniversalWorkflow 的长期自研主线：

```text
1. 通用图执行引擎
2. 通用 checkpoint / resume runtime
3. 通用 coding agent
4. 通用 SaaS connector 平台
5. 通用 browser automation engine
6. 通用 observability / tracing 平台
7. 通用 CI/CD pipeline engine
8. 通用 multi-agent framework
9. 通用 MCP client 之外的散装工具接入
10. 通用 docs RAG 系统
```

如果确有需求，应优先：

```text
使用成熟方案；
通过 adapter / broker 包装；
只保留 UniversalWorkflow 的控制语义。
```

---

## 6. LangGraph 的长期位置

### 6.1 结论

LangGraph 不应接管整个 UniversalWorkflow。

LangGraph 应作为：

```text
runtime execution substrate
运行时执行底座
```

### 6.2 LangGraph 应负责

```text
1. graph execution
2. checkpoint
3. resume
4. interrupt
5. human-in-the-loop pause
6. conditional edge
7. subgraph
8. streaming runtime state
9. failure recovery
10. runtime-level retry
```

### 6.3 LangGraph 不应负责

```text
1. OperatorActionReceipt
2. MutationContract
3. ReviewPolicy
4. PolicyEngine
5. AutomationLease
6. WorkerRouter
7. Capability Registry
8. MCP Broker
9. CLI Adapter Contract
10. Evidence / Audit
11. Operator Packet
12. PR-ready Summary
13. Business Pipeline
14. Local-first UX
```

### 6.4 正确引入方式

不要做：

```text
给现有代码零碎加几个 LangGraph node。
```

应该做：

```text
保留 UniversalWorkflow 的领域模型；
新增 LangGraphRuntimeAdapter；
将 OrchestrationPlanGraph 编译成 LangGraph StateGraph；
让 LangGraph 承担执行、checkpoint、interrupt、streaming。
```

### 6.5 推荐结构

```text
packages/runtime_langgraph/
  adapter.py
  plan_adapter.py
  checkpoint.py
  interrupts.py
  state.py
  graph_factory.py
```

接口示例：

```python
class WorkflowRuntime:
    def start(self, run_spec): ...
    def resume(self, run_id, input=None): ...
    def interrupt(self, run_id, reason): ...
    def get_state(self, run_id): ...
    def stream(self, run_id): ...
```

实现：

```text
LegacyWorkflowRuntime
LangGraphWorkflowRuntime
```

---

## 7. MCP 的长期位置

### 7.1 结论

MCP 应作为：

```text
外部工具 / 外部能力接入协议底座
```

但不应该变成：

```text
全部 MCP 工具无脑暴露给 agent。
```

### 7.2 MCP 的正确形态

UniversalWorkflow 应构建：

```text
MCP Broker
```

核心机制：

```text
1. profile allowlist
2. tool allowlist
3. canonical tool id
4. per-task projection
5. risk tier
6. policy / lease binding
7. audit trail
8. schema budget
9. result summary
10. latency / cost record
```

### 7.3 Canonical Tool ID

所有 MCP 工具应使用唯一 ID：

```text
mcp:{profile_id}:{tool_name}
```

避免多个 MCP server 暴露同名工具导致歧义。

### 7.4 按任务最小投射

默认规则：

```text
任何 agent 不应默认看到所有 enabled MCP tools。
```

应根据：

```text
task_kind
preset
cluster
risk_level
automation_lease
policy_decision
context_budget
```

选择本任务真正需要的工具。

### 7.5 风险分级

MCP tool 至少分为：

```text
readonly
local_write
network
external_side_effect
secret_sensitive
```

默认策略：

```text
readonly:
    可在 lease 范围内自动调用

local_write:
    需要 write_set / policy 约束

network:
    需要网络策略允许

external_side_effect:
    默认 require_confirmation

secret_sensitive:
    默认 deny 或 require_confirmation
```

---

## 8. CLI Agent 生态的长期位置

### 8.1 结论

Codex、Claude Code、Gemini CLI、OpenCode 等工具应作为：

```text
执行能力底座
```

UniversalWorkflow 不应自研 coding agent。

### 8.2 UniversalWorkflow 应做什么

UniversalWorkflow 应实现：

```text
CLI Adapter Contract
```

统一管理：

```text
1. input schema
2. output schema
3. workspace policy
4. timeout
5. cost estimate
6. log capture
7. diff capture
8. test command
9. artifact capture
10. failure reason
11. retry policy
12. evidence output
```

### 8.3 推荐 Adapter

```text
CodexCLIAdapter
ClaudeCodeAdapter
GeminiCLIAdapter
OpenCodeAdapter
ShellAdapter
NoopAdapter
```

### 8.4 WorkerRouter 的长期职责

WorkerRouter 不应成为复杂执行引擎。

它应负责：

```text
1. 根据任务类型选择候选 worker
2. 根据模型/CLI能力选择执行器
3. 根据预算和风险过滤执行器
4. 根据失败情况降级或切换执行器
5. 记录调用结果
```

---

## 9. Agent / Cluster 的长期形态

### 9.1 不要过早打磨 prompt

在 runtime、policy、capability 治理层稳定前，不应先深度打磨 agent persona / prompt。

### 9.2 Cluster 应成为职责单元

未来 cluster 应定义为：

```text
输入
输出
可用能力
不可用能力
上下文预算
验收标准
失败回退
handoff packet
```

### 9.3 推荐 Cluster

```text
PlannerCluster
ResearchCluster
ArchitectureCluster
CodeCluster
ReviewCluster
MultimodalCluster
ManagementCluster
```

### 9.4 Cluster 与 LangGraph 的关系

```text
cluster 内部可以是 LangGraph subgraph；
cluster 外部由 UniversalWorkflow 统一调度、授权、审计。
```

---

## 10. 长期开发路线图

## M67：收口与立规矩

### 目标

```text
防止项目继续无意识自研膨胀。
```

### 主要任务

```text
1. 更新 AGENTS.md
2. 增加 Build-vs-Buy 规则
3. 增加 LANGGRAPH_OVERLAP_INVENTORY.md
4. 增加 EXTERNAL_CAPABILITY_MAP.md
5. 明确停止自研清单
6. 明确保留自研清单
7. 完成 high-risk action boundary 修复
8. 建立 PolicyEngine 最小骨架
9. 建立 AutomationLease 最小骨架
10. 避免继续新增自研 runtime 大功能
```

### 不做

```text
1. 不大规模迁移 LangGraph
2. 不疯狂接新 MCP
3. 不深度打磨 agent roles
4. 不引入 Temporal / Prefect / CrewAI / AutoGen 等新底座
5. 不做大规模 UI 重构
```

### 验收标准

```text
1. AGENTS.md 明确项目是 control plane，不是 full-stack agent framework。
2. 新增 runtime / connector / eval / browser / pipeline 能力前必须做 Build-vs-Buy。
3. 明确哪些 runtime 功能应迁给 LangGraph。
4. 明确哪些领域能力必须保留自研。
5. 高风险动作不再因为入口不同而规则不同。
6. dev_autopilot / lease 方向明确。
```

---

## M68：LangGraph 小聚焦真集成

### 目标

```text
让 LangGraph 真正承担 runtime execution 板块，而不是装饰性接入。
```

### 主要任务

```text
1. 保留 OrchestrationPlanGraph 作为领域/审计模型
2. 新增 LangGraphRuntimeAdapter
3. 将 OrchestrationPlanGraph 编译为 LangGraph StateGraph
4. Durable pilot 从 InMemorySaver 升级为 SQLite checkpointer 或独立 checkpoint DB
5. ChatControlGraph 从 noop graph 改为真实 conditional edges
6. confirmation_gate 接 interrupt / resume
7. cluster execution 小范围 graph 化
```

### 不做

```text
1. 不删现有 contracts
2. 不让 LangGraph 接管 receipt / mutation / review / audit
3. 不全量迁移所有 run lifecycle
4. 不让业务逻辑到处直接 import LangGraph
```

### 推荐实现

```text
packages/runtime_langgraph/
  adapter.py
  plan_adapter.py
  checkpoint.py
  chat_graph.py
  interrupts.py
```

### 验收标准

```text
1. LangGraph 不再只是 noop graph。
2. 至少一个真实流程通过 LangGraph 执行。
3. 支持 checkpoint / resume。
4. 支持 confirmation interrupt。
5. OrchestrationPlanGraph 仍作为领域审计模型保留。
6. workflow.db 仍是领域真相源。
7. LangGraph checkpoint 不制造不可控双状态源。
```

---

## M69：Capability Control Plane

### 目标

```text
把能力接入治理层做扎实。
```

### 主要任务

```text
1. Capability Registry
2. Capability Projection
3. MCP Broker
4. CLI Adapter Contract
5. PolicyEngine 完整化
6. AutomationLease 完整化
7. Capability Invocation Audit
8. Per-task Tool Projection
9. 成本 / 延迟 / 失败 / 结果记录
10. 能力风险分级
```

### 不做

```text
1. 不优先接很多新 MCP
2. 不深接 SaaS 集成平台
3. 不接 Temporal
4. 不做完整观测平台
```

### 验收标准

```text
1. 每个 task 只获得必要能力。
2. 每个 capability 调用有 audit。
3. 每个 CLI adapter 有统一输入输出。
4. MCP 工具不会全量暴露。
5. dev_autopilot 只能使用 lease 允许的能力。
6. 外部副作用能力默认 require_confirmation。
```

---

## M70：接入关键外部执行能力

### 目标

```text
接成熟执行器，而不是继续自研执行器。
```

### 优先接入

```text
1. Codex CLI Adapter
2. Claude Code Adapter
3. Gemini CLI Adapter
4. OpenCode Adapter
5. readonly workspace MCP
6. web search / browser MCP
7. GitHub read-only MCP
8. Playwright browser automation
9. Figma / Canva / asset tools
10. image / audio / video generation APIs
```

### 每个能力必须具备

```text
1. input schema
2. output schema
3. permission policy
4. audit record
5. failure handling
6. timeout
7. evidence capture
8. acceptance criteria
```

### 验收标准

```text
1. 至少 2 个 coding CLI agent 可通过统一 adapter 调用。
2. 至少 2 个 MCP profile 可按任务投射。
3. Browser / search 能力可作为受控 capability 使用。
4. 调用结果可进入 evidence。
5. 失败可被 review / retry / fallback 处理。
```

---

## M71：Agent / Cluster 角色收敛

### 目标

```text
把 agent roles 从 prompt 角色升级为标准职责单元。
```

### 主要任务

```text
1. 定义 cluster contract
2. 定义 input / output schema
3. 定义 allowed capabilities
4. 定义 context budget
5. 定义 handoff packet
6. 定义 acceptance criteria
7. 定义 fallback policy
8. 逐步将 cluster 内部 subgraph 化
```

### 推荐 Cluster

```text
PlannerCluster
ResearchCluster
ArchitectureCluster
CodeCluster
ReviewCluster
MultimodalCluster
ManagementCluster
```

### 验收标准

```text
1. 每个 cluster 不再只是 prompt。
2. 每个 cluster 有明确输入输出。
3. 每个 cluster 有能力边界。
4. 每个 cluster 有验收标准。
5. cluster 之间通过 HandoffPacket 交接。
```

---

## M72：业务闭环打穿

### 目标

```text
回到 UniversalWorkflow 的真实业务价值：
互动内容 / H5 小游戏 / 多模态内容生产。
```

### 建议打穿第一个闭环

```text
输入一个 H5 小游戏
→ 玩法分析
→ 代码理解
→ 美术风格升级
→ 音效/音乐生成
→ 自动修改代码
→ 自动测试
→ Playwright 截图/试玩
→ 多模态视觉评审
→ 代码质量评审
→ 商业化质量报告
→ 打包产物
```

### 关键验收

```text
1. 可输入真实 H5 小游戏项目。
2. 可自动分析玩法和代码结构。
3. 可生成美术 / 音效升级方案。
4. 可调用 coding CLI 修改代码。
5. 可运行自动测试。
6. 可用浏览器自动试玩 / 截图。
7. 可用视觉模型评审美术一致性。
8. 可生成商业质量报告。
9. 可输出可复盘 evidence。
10. 人类可在关键节点接管。
```

---

## 11. 对 Codex 的长期开发规则

### 11.1 总规则

Codex 必须遵守：

```text
UniversalWorkflow is a control plane, not a full-stack agent framework.
Prefer mature infrastructure for substrate-level capabilities.
Do not introduce large dependencies for tiny utility functions.
Do not reimplement runtime/checkpoint/subgraph features if LangGraph can own them.
Do not reimplement coding agents; use CLI adapters.
Do not expose all MCP tools; use MCP Broker and per-task projection.
```

### 11.2 新增功能前必须判断

新增以下能力前，必须先做 Build-vs-Buy：

```text
runtime
orchestration
checkpoint
resume
interrupt
memory
streaming
subgraph
multi-agent framework
connector
browser automation
pipeline engine
observability
eval platform
coding agent
```

### 11.3 Build-vs-Buy 模板

```md
# Build vs Buy Decision

## Feature

要做什么？

## Existing Solutions

- LangGraph:
- MCP:
- Codex / Claude / Gemini / OpenCode:
- Playwright:
- Dagger / Prefect:
- Phoenix / OTel:
- Other:

## Coverage

外部方案覆盖多少？

- <40%
- 40%-70%
- >70%

## Differentiation

自研的差异化是什么？

## Adapter Plan

是否可以通过 adapter 接入？

## Risks

引入外部方案的风险是什么？
自研的风险是什么？

## Decision

- Build
- Wrap
- Use External
- Spike First
- Defer

## Exit Criteria

什么时候认为该决策成功？
什么时候回滚？
```

---

## 12. 风险矩阵

| 风险 | 等级 | 说明 | 应对 |
|---|---:|---|---|
| 继续自研 runtime | 高 | 会继续重复 LangGraph 能力 | M67 后冻结新增 runtime 大功能 |
| LangGraph 大迁移 | 高 | 会破坏现有领域能力和测试 | 只做小聚焦真集成 |
| MCP 工具全量暴露 | 高 | token 爆炸、误调用、安全边界混乱 | MCP Broker + per-task projection |
| CLI agent 接入无统一 contract | 高 | 每个 agent 一套逻辑，后续难维护 | 先定义 CLI Adapter Contract |
| Agent roles 先于能力治理深度打磨 | 中高 | prompt 越来越复杂但不可控 | M71 再系统收敛 roles |
| 外部方案零碎引入 | 中高 | 依赖多，收益小 | 只引入大板块 |
| 全部自研 | 高 | 项目变重，维护困难 | Build-vs-Buy 规则 |
| 过早接 Temporal / CrewAI 等 | 中 | 多套 runtime 语义冲突 | 暂缓 |
| 业务闭环迟迟不验证 | 高 | 架构很好但不知道是否创造价值 | M72 打穿 H5 游戏闭环 |

---

## 13. 当前最应该做的三件事

### 第一：更新 AGENTS.md

加入：

```text
UniversalWorkflow is a local-first AI workflow control tower.
It must not evolve into a full-stack self-built agent framework.
Runtime substrate features should prefer LangGraph if a full board-level fit exists.
Tiny utility functions should not justify large external dependencies.
MCP tools must be exposed through MCP Broker and per-task projection.
CLI agents must be accessed through CLI Adapter Contract.
New runtime/connector/eval/browser/pipeline capabilities require Build-vs-Buy review.
```

### 第二：生成 LANGGRAPH_OVERLAP_INVENTORY.md

要求分类：

```text
A. Keep custom
B. Wrap LangGraph
C. Replace execution layer with LangGraph
D. Defer
```

重点盘点：

```text
OrchestrationEngine
OrchestrationPlanGraph
DurableRuntimePilot
ChatControlGraph
ClusterRouter
Run lifecycle
Review pause
Checkpoint / resume
Streaming runtime state
```

### 第三：停止继续新增自研 runtime 大功能

冻结：

```text
自研 checkpoint
自研 graph executor
自研 durable runtime
自研 cluster executor
自研 interrupt/resume engine
```

除非只是修 bug 或兼容旧系统。

---

## 14. 最终长期路线一句话版

```text
M67：收口立规矩，防止继续自研漂移
M68：LangGraph 小聚焦真集成，瘦 runtime
M69：Capability Control Plane，做 MCP Broker / CLI Adapter / Policy / Lease
M70：接关键外部执行能力
M71：规范 agent / cluster
M72：打穿 H5 游戏 / 多模态生产业务闭环
```

最终目标：

```text
UniversalWorkflow 不再是一个越写越重的自研 agent framework；
而是一个组合成熟 AI/工程能力的 local-first workflow control tower。
```

---

## 15. 最终判断

当前项目不是方向错误，而是需要一次战略收口。

正确方向不是：

```text
继续自研所有基础设施
```

也不是：

```text
到处零碎引入外部方案
```

而是：

```text
底座级成熟方案承担大板块；
UniversalWorkflow 自研控制层、治理层、证据层和业务流程层。
```

长期最优形态：

```text
LangGraph 负责 runtime execution；
MCP 负责工具协议；
CLI agents 负责执行能力；
UniversalWorkflow 负责策略、授权、调度、证据、验收和业务闭环。
```
