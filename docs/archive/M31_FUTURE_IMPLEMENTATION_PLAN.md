# M31+ 未来实现方案（覆盖更新版）

日期：2026-04-21  
状态：未来实现蓝图 / 覆盖更新版  
目标：基于第二轮评估与当前阶段问题解决方案，给出面向 M32~M36 的系统实现方案，覆盖多 agent 协同、固定角色、即时角色生成、自动化编排、外部能力接入、自然语言交互、通用能力接入、自我迭代升级、任意工程开发、易用性设计等核心关注点。

---

## 0. 未来目标：这个系统最终应该长成什么

这个项目未来不应该只是：

- 一个 workflow runner
- 一个多 agent demo
- 一个 CLI 包着几个 adapter
- 一个只能给 operator 用的本地工具

它更合理的最终定位是：

> **一个本地优先的 agentic engineering / operations platform**  
> **一个以控制平面为内核、以工作台为交互层、以能力运行时为执行层的平台系统。**

未来成熟形态必须同时服务三类主体：

### 1）人
- 操作员
- 开发者
- 产品经理
- 审核者
- 终端用户

### 2）agent
- planner
- architect
- researcher
- coder
- tester
- reviewer
- monitor
- release manager
- 临时生成的专业角色

### 3）外部系统
- worker pool
- MCP servers
- IDE / CI / repo connector
- scheduling / automation backends
- future hosted execution surfaces

---

## 1. 总体设计原则

未来方案必须长期坚持下面几条原则。

## 1.1 外层控制权归代码，局部认知权归模型

这意味着：

- lifecycle transition 归代码
- review / budget / mutation / trust boundary 归代码
- graph compile / schedule 归代码
- model 可以参与：
  - 计划生成
  - 角色推断
  - 子任务执行
  - 局部决策
- 但 model 不应无边界接管整个系统

## 1.2 状态必须显式，不能重新退回“全靠 prompt 上下文”

当前仓库最大的优势之一就是显式状态和显式证据。  
未来必须继续保留：

- state refs
- attempts
- claims / leases
- snapshots
- evidence
- review history
- simulation / eval / repair lineage

## 1.3 多 agent 协同应由“拓扑”定义，而不是由 prompt 临时发挥

也就是：

- 平台决定拓扑
- 模型在拓扑内工作
- agent 是角色，不是随意漂移的人格

## 1.4 capability 接入必须统一契约

任何工具、任何 worker、任何 sessionful runtime、任何 hosted backend，都必须进入同一 capability runtime family。

## 1.5 自主升级必须是受控闭环，而不是开放式自修改

当前 inspection / repair / replay 很强，但未来自迭代必须通过：

- eval
- canary
- upgrade proposal
- human or policy gate
- promotion decision

形成受控闭环。

---

## 2. 未来参考架构

建议未来平台分成七个平面：

```text
+------------------------------------------------------------+
| Interaction Plane                                          |
| chat / workbench / guided launch / operator UI / SDK       |
+------------------------------------------------------------+
| Planning & Orchestration Plane                             |
| intent -> plan -> graph compile -> schedule -> supervise   |
+------------------------------------------------------------+
| Role System Plane                                          |
| fixed roles / generated roles / role registry / runtime    |
+------------------------------------------------------------+
| Capability Runtime Plane                                   |
| adapters / MCP / worker pools / sessions / hosted runtime  |
+------------------------------------------------------------+
| Memory & Knowledge Plane                                   |
| session / run / artifact / skill / policy memory           |
+------------------------------------------------------------+
| Governance & Evolution Plane                               |
| policy / audit / replay / eval / repair / promotion        |
+------------------------------------------------------------+
| Kernel / Control Plane                                     |
| lifecycle / snapshots / claims / leases / scheduler truth  |
+------------------------------------------------------------+
```

### 这七层之间的关系

- **Kernel** 提供可审计的真相
- **Governance** 约束真相并驱动安全演进
- **Memory** 为角色与交互提供可控上下文
- **Capability Runtime** 提供真正执行能力
- **Role System** 决定谁来做什么
- **Planning & Orchestration** 决定任务如何被拆解和编排
- **Interaction Plane** 决定人如何舒服地使用这一切

---

## 3. 多 agent 协同的总体实现方案

多 agent 协同不应只有一种模式，未来应支持多种协同拓扑，但默认模式必须清楚。

## 3.1 默认拓扑：Manager-as-code

未来最推荐的默认拓扑不是“让最强模型自己拉很多 agent”，而是：

> **graph / scheduler / policy / budgets 由代码控制，agent 在图节点内部作为 bounded specialist 工作。**

适用场景：

- 工程开发
- 受控 repo mutation
- 审核敏感流程
- 企业工作流
- 需要回放、重试、repair、可审计的任务

优点：

- 最稳定
- 最容易加治理
- 最适合与当前仓库的 control-plane 优势结合

## 3.2 交互工作台拓扑：Specialists-as-tools

对于未来的自然语言工作台，默认更适合：

> 一个主对话 agent 作为 manager，其他 specialist 以 tool 形式挂入。

适用场景：

- 用户想持续对话，不想被“切来切去”
- planner / researcher / reviewer 等专业能力需要被调用，但不想直接变成主会话主体

优点：

- UX 更自然
- 角色仍然可控
- 很适合吸收 OpenAI Agents SDK 的 agents-as-tools 模式

## 3.3 深专业协作拓扑：Handoff / Routed Specialist

某些场景需要从一个 agent 真的切到另一个 specialist。  
这时才使用 handoff / routed specialist。

适用场景：

- 深领域专员接管
- 长时间上下文切换
- support/ops 风格的专门协作

原则：

- 这应该是 **opt-in**
- 不应该成为整个系统的默认交互模式

## 3.4 并行协作拓扑：Parallel Map / Reducer

未来系统必须系统化支持：

- 多 researcher 并行
- coder + tester 并行
- reviewer quorum 并行
- 多视角分析并行

输出通过 reducer / evaluator / reviewer 聚合。

这与当前 `project_delivery` 的 barrier 基线高度兼容，应被正式推广。

## 3.5 审核型拓扑：Reviewer Quorum / Debate

对于高风险产物或重要决策，未来应支持：

- 多 reviewer 并行审查
- 大 reviewer / reducer 汇总
- 必要时引入 human gate

这种模式尤其适合：

- release readiness
- architecture decision
- security-sensitive mutation
- 自主升级 proposal 审批

## 3.6 监控型拓扑：Monitor / Watchdog

未来系统必须有“非生产角色”的 agent：

- 不是写代码
- 不是给答案
- 而是监控执行与检测 drift / loop / stall

这一角色负责：

- 发现低进度循环
- 发现角色输出 drift
- 发现预算过快消耗
- 触发 reroute / downgrade / escalate
- 对接 automation controller

---

## 4. 固定 agent 角色设计

未来应形成一套稳定、可复用、可治理的 fixed role registry。

## 4.1 核心固定角色

### Planner
职责：
- 将用户意图转成 plan draft / graph candidate
- 明确目标、范围、约束、风险

### Architect
职责：
- 把 plan 进一步转成技术拆解
- 输出边界、依赖、执行顺序、接口要点

### Researcher
职责：
- 读取仓库、外部资料、历史 evidence、已有 memory
- 给出证据与不确定性说明

### Coder
职责：
- 在 mutation contract 下执行工程实现
- 输出 patch / artifact / code delta

### Tester / Verifier
职责：
- 执行验证、测试、重现实验、lint、环境检查
- 输出可复现证据

### Reviewer
职责：
- 审核需求匹配度、质量、风险、可维护性
- 输出 verdict / issue list / severity

### Policy Guardian
职责：
- 负责 trust / mutation / capability / budget / review policy 约束
- 决定允许 / 拒绝 / 延迟 / 升级

### Monitor / Operator Agent
职责：
- 监控运行健康度
- 发现 stall / loop / drift
- 触发 automation / escalation

### Release Manager
职责：
- 收口成果
- 生成发布/关闭/交付 packet
- 做 ship/no-ship 准备

## 4.2 领域角色

未来 domain pack 可以引入领域角色，例如：

- Security Reviewer
- Infra Operator
- Product Spec Writer
- Data Migration Specialist
- Performance Analyst
- Localization Specialist
- Narrative / Content Specialist

原则：

- 领域角色必须仍然服从统一 `RoleSpec`
- 不允许每个 pack 自造运行语义

---

## 5. 即时 agent 角色生成方案

这是未来方案中最关键的增量能力之一。

## 5.1 总原则

即时生成角色必须满足五个条件：

1. **临时性**：默认只服务于当前 session / plan / graph  
2. **结构化**：生成结果必须落成 `RoleSpec`，而不是只是一段 prompt  
3. **边界化**：必须带 capability、memory、repo scope、budget、termination rule  
4. **可审计**：operator 与 audit packet 中必须可见  
5. **可淘汰/可晋升**：好角色可以晋升为模板，差角色必须被回收

## 5.2 角色工厂（Role Factory）

建议实现 `RoleFactory`，输入包括：

- objective gap
- deliverable type
- domain
- risk tier
- required capabilities
- preferred collaboration mode
- autonomy level
- review requirement
- budget envelope

输出 `RoleSpec`，至少包含：

- `role_id`
- `role_kind`（fixed / generated / promoted_template）
- `name`
- `objective`
- `success_criteria`
- `allowed_capabilities`
- `allowed_memory_namespaces`
- `allowed_repo_scope`
- `review_requirement`
- `max_iterations`
- `termination_conditions`
- `escalation_target`
- `preferred_models`
- `visibility_level`

## 5.3 生成角色的运行生命周期

建议统一生命周期：

1. proposed
2. accepted_into_graph
3. executing
4. evaluated
5. archived
6. optionally_promoted

## 5.4 角色晋升规则

生成角色只有在满足以下条件时才允许晋升为模板：

- 多次表现稳定
- capability 使用边界清晰
- 失败模式可解释
- audit / replay / eval 证据充分
- 与现有 fixed roles 不重复或明显更优

---

## 6. 自动化流程编排方案

## 6.1 通用 graph engine

未来编排必须建立在正式的 graph engine 上，而不是继续扩特例 flow。

建议正式对象：

- `ExecutionGraph`
- `NodeSpec`
- `EdgeSpec`
- `BarrierSpec`
- `ReducerSpec`
- `ApprovalGateSpec`
- `RetryPolicy`
- `WatchdogPolicy`

## 6.2 必备 node type

至少应支持：

- `AgentNode`
- `ToolNode`
- `CapabilityNode`
- `HumanGateNode`
- `ApprovalGateNode`
- `ParallelMapNode`
- `ReducerNode`
- `EvalNode`
- `RepairNode`
- `PublishNode`
- `WaitEventNode`
- `ScheduleNode`
- `BranchDecisionNode`

## 6.3 graph 来源

未来 graph 应支持三种来源：

### 固定模板 graph
适用于：
- feature delivery
- guarded delivery
- release prep
- incident investigation

### planner 推导 graph
planner 输出 plan draft，compiler 变成 graph

### hybrid graph
从固定模板出发，运行中注入 generated role / dynamic branch

## 6.4 graph 运行时控制

编排引擎要显式区分：

- graph compile
- graph validate
- graph persist
- graph schedule
- node execute
- graph supervision
- graph repair

这样后续加：

- queue
- schedule
- remote worker
- human gate
- automation controller

不会再导致 graph 模型反复变形。

---

## 7. 通用外部能力接入方案

## 7.1 未来 capability runtime 应统一覆盖的能力类型

1. built-in tools  
2. MCP tools / resources / prompts  
3. local process adapters  
4. external worker pools  
5. sessionful external runtimes  
6. hosted model/provider runtimes  
7. IDE / repo / browser / CI connectors  
8. long-running background job backends  

## 7.2 统一 capability contract

所有外部能力都应投影到同一套结构：

- identity
- provider kind
- transport
- auth mode
- trust tier
- side-effect level
- allowed task kinds
- timeout budget
- review requirement
- evidence schema
- sandbox profile
- runtime health state
- tracing hooks

## 7.3 MCP 的定位

MCP 非常重要，但不能误用。

未来应把 MCP 看成：

- 一个非常强的标准化 capability boundary
- 特别适合 tools / resources / prompts 统一暴露

但不应该把整个系统都“缩成 MCP”。

MCP 是能力接入协议之一，  
不是 lifecycle、governance、automation、orchestration 的全部替代物。

## 7.4 capability SDK

建议未来提供正式注册入口：

- `register_tool_capability()`
- `register_worker_pool()`
- `register_session_runtime()`
- `register_mcp_profile()`
- `register_role_pack_capabilities()`

这样后续生态扩展才不会变成直接改核心代码。

---

## 8. 自然语言人机交互方案

## 8.1 interaction plane 目标

未来系统真正面向人的主入口，应是一套有状态工作台，而不是只靠 operator console + launch endpoint。

建议核心对象：

- `IntentSession`
- `IntentPacket`
- `ClarificationState`
- `PlanDraft`
- `LaunchDecision`
- `ConversationTurn`
- `RunFollowupRequest`

## 8.2 标准交互流程

未来标准流应是：

1. 用户提出目标  
2. 系统识别歧义并做澄清  
3. 系统输出 plan / graph / risk / capability preview  
4. 用户批准 / 修改 / 缩小范围  
5. 系统执行  
6. 系统流式回传状态 / 证据 / 问题  
7. 用户追加 follow-up  
8. 系统把 follow-up 映射到 graph change / reroute / branch / review request  

## 8.3 conversation state 与 execution state 分离

必须坚持：

- conversation state 用于交互连续性
- execution state 用于 run truth / replay / audit
- 二者可以关联，但不能混在一起

这是未来 workbench 成功与否的关键。

## 8.4 三层易用性模式

### 模式 A：Simple Goal
面向普通用户：
- 目标输入
- 默认安全配置
- 简单进度反馈

### 模式 B：Guided Project
面向 builder：
- plan graph
- role breakdown
- capability preview
- explicit review gate

### 模式 C：Operator Mode
面向高级用户：
- claims / leases / attempts / snapshots
- repair / reconcile
- cluster / scheduler / replay / audit

---

## 9. 通用记忆与知识方案

## 9.1 记忆分层

### Session Memory
面向对话连续性与用户偏好

### Run Memory
面向某次执行过程中的事实、决策、失败与证据

### Artifact Memory
面向产物、实现模式、输出模板

### Skill Memory
面向流程 know-how、角色模板、策略经验

### Policy / Failure Memory
面向历史风险、升级记录、回归签名、典型故障

## 9.2 记忆访问策略

访问必须受以下因素约束：

- role
- trust tier
- task risk
- repo / project scope
- user/session boundary
- review requirement

否则 memory 会很快从“优势”变成“污染上下文”。

---

## 10. 自我迭代升级方案

## 10.1 目标
让系统具备**受控演进能力**，而不是“无限自我修改”。

## 10.2 升级闭环

建议统一对象：

- `EvalScenario`
- `EvalReport`
- `RepairPlan`
- `UpgradeProposal`
- `CanaryPolicy`
- `PromotionDecision`

统一流程：

1. 发现 friction / regression / repeated manual intervention
2. 生成 `UpgradeProposal`
3. 编译 bounded change plan
4. 在隔离 workspace / branch / sandbox 中执行
5. 运行 eval / benchmark / regression
6. 生成 diff + report + risk summary
7. human 或 policy gate 决定是否推进
8. promote / reject / rerun

## 10.3 自我升级边界

未来任何自我升级都必须遵循：

- 不直接改主线
- 不跳过评估
- 不跳过可追溯性
- 高风险 mutation 必须有人类或强 policy gate
- 每次升级都必须留下 replay-grade lineage

---

## 11. 任意工程开发方案

## 11.1 目标
把“任意工程开发”从当前 repo mutation baseline，升级成正式平台任务族。

## 11.2 工程任务正式对象

建议引入 `EngineeringTaskSpec`，统一表达：

- code changes
- docs changes
- config changes
- tests
- infra changes
- migrations
- repo analysis / remediation
- release prep

## 11.3 工程任务关键字段

- repo / workspace target
- branch / session target
- read set
- write set
- mutation mode
- test plan
- rollback rule
- reviewer requirement
- packaging / PR rule
- acceptance criteria
- security / risk tier

## 11.4 工程执行模式

未来至少支持：

- local shell path
- opencode patch path
- sessionful collaborative path
- external worker path
- research + mutation + verification 混合路径

这条线应成为平台最具差异化的能力之一。

---

## 12. M32~M36 推荐里程碑

## M32：平台契约化与 graph engine 完成
重点：
- graph engine 正式上线
- role registry v1
- capability invocation contract v1
- authority model 语义收口完成

## M33：workbench 与 fixed-role runtime
重点：
- interaction plane v1
- workbench UI v1
- fixed role runtime
- specialists-as-tools / manager-as-code 双拓扑

## M34：generated role + automation plane
重点：
- `RoleFactory`
- generated role lifecycle
- watchdog / monitor
- background `AutomationController`
- schedule / event-driven orchestration

## M35：通用 capability 生态 + 任意工程开发
重点：
- capability SDK
- MCP / worker / session / connector 统一接入
- `EngineeringTaskSpec`
- more serious product-grade engineering workflows

## M36：受控自我升级 + 产品化收口
重点：
- eval / canary / promotion 系统
- upgrade proposal loop
- stable product surfaces
- pack ecosystem 与产品边界收口

---

## 13. 吸收外部框架的原则

未来方案不应整体重写到某个外部框架里，而应“吸收模式、保留内核”。

### OpenAI Agents SDK 值得吸收的部分
- agents-as-tools
- handoffs
- guardrails
- tracing
- hosted MCP
- 受控 sandbox / 长任务工作空间思路

### LangGraph 值得吸收的部分
- durable execution
- persistence / checkpoint
- interrupt / human-in-the-loop
- orchestrator-worker / evaluator-optimizer pattern

### AutoGen 值得吸收的部分
- message-protocol 驱动的多 agent 运行时
- group chat manager
- team runtime / routed collaboration

### CrewAI 值得吸收的部分
- crew / flow 分层
- event-driven flow UX
- 任务编排的可读性表达

### MCP 值得吸收的部分
- tools / resources / prompts 三种标准原语
- 标准化上下文接入边界
- 结构化工具输出与审批能力

### Temporal / Prefect / Trigger.dev 值得吸收的部分
- durable workflow
- background job control
- event / schedule automations
- queue / work pool / retry / monitoring 模型

---

## 14. 最终方案的一句话概括

如果把未来 M36 的理想形态压成一句话：

> **它应该成为一个以控制平面为真相内核、以 graph orchestration 为工作骨架、以角色系统为多 agent 运行时、以 capability runtime 为外部执行统一边界、以 workbench 为人类主入口、以 eval/promotion 为自我演进闭环的本地优先平台。**

---

## 15. 最终建议

未来实现方案不应理解成“继续堆更多功能”，而应理解成：

- 先把平台对象立起来
- 再把协同拓扑立起来
- 再把交互层和自动化层立起来
- 最后才扩生态、扩能力、扩自主性

这样才能同时得到：

- 最优架构
- 最高效率
- 最强可用性与易用性
- 最好稳定性
- 最好可扩展性

这才是从当前仓库走向 M36 的正确路径。
