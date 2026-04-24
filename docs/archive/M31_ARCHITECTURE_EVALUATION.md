# M31 架构评估（第二轮重评）

日期：2026-04-21  
状态：第二轮重评 / 覆盖更新版  
范围：对 `ghostairship-debug/universalworkflow` 当前主干的代码、测试、根目录既有评估文档、冻结评审文档，以及外部相关框架/协议进行重新评估。

---

## 0. 本轮重评的核心结论

第一轮评估把项目定义为“本地优先的 agentic workflow 内核 / 控制平面”，这个方向判断仍然成立。  
但第二轮重评要把一个更关键的事实说得更直白：

> 当前仓库最大的风险已经不是“能力不够”，而是“代码中已经存在大量平台语义，但其中一部分仍然是**建模完成**，尚未等于**真正的平台化完成**”。

换句话说：

- **生命周期、审计、治理、运行所有权、回放、修复**：已经明显超过原型阶段。
- **多角色协同、能力平面、外部执行、控制面集群、产品工作台**：已经有很强的方向性与大量代码，但并非都已经达到“可以安全支撑下一轮产品化与生态扩张”的程度。
- **最需要做的不是继续加广度，而是先把平台边界、语义诚实性、交互面、自动化面彻底收束。**

本轮重评因此把项目当前状态定义为：

> **一个很强的本地优先控制平面内核 + 一个尚未完全收口的平台化外层。**

这与仓库当前自述的 `v1 core complete` 不矛盾；真正的问题是：  
**“core complete”不等于“可以直接进入大规模产品化和生态扩张”。**

---

## 1. 评估依据

本轮重评综合使用以下信息：

### 1.1 仓库内已读材料

重点复核了以下部分：

- `README.md`
- `pyproject.toml`
- `docs/current_development_workflow.md`
- `docs/reviews/m20-freeze-review.md`
- `docs/reviews/m30-operator-control-freeze-review.md`
- `docs/tech-debt-registry.md`
- 根目录既有三份 M31 文档
- `apps/operator_cli/main.py`
- `apps/orchestrator_api/main.py`
- `apps/orchestrator_api/web_ui.py`
- `apps/operator_tui/dashboard.py`
- `packages/core_domain/services.py`
- `packages/core_domain/service_lifecycle.py`
- `packages/core_domain/service_projection.py`
- `packages/core_domain/capability_plane.py`
- `packages/core_domain/external_workers.py`
- `packages/core_domain/scheduler_authority.py`
- `packages/core_domain/config.py`
- `packages/runtime_langgraph/gateway.py`
- `packages/runtime_langgraph/durable_pilot.py`
- `packages/worker_adapters/router.py`
- `infra/scripts/manage.py`
- `infra/seeds/domain_packs.json`
- `infra/seeds/worker_pool_profiles.json`
- `infra/seeds/mcp_server_profiles.json`
- `tests/test_execution_loop.py`
- `tests/test_api.py`
- `tests/test_web_ui.py`

### 1.2 外部对照对象

本轮外部对照重点参考了以下方向：

- OpenAI Agents SDK：tools、agents-as-tools、handoffs、guardrails、tracing、hosted MCP、受控沙箱
- LangGraph：durable execution、persistence、interrupt / human-in-the-loop、workflow/agent patterns
- AutoGen：group chat / team / message-protocol 驱动的多 agent 协作
- CrewAI：crews 与 flows 分层、事件驱动流程与状态管理
- MCP：tools / resources / prompts 三种原语、结构化输出、审批与授权扩展
- Temporal / Prefect / Trigger.dev：durable workflow、background jobs、automations、work pools / queues、长任务控制与可观测性

这些外部材料不是为了“找一个框架替代本项目”，而是为了判断：

> 这个仓库下一步应该吸收哪些模式，避免哪些误区。

---

## 2. 仓库当前“真正已完成”的部分

## 2.1 生命周期内核已经明显超过原型阶段

从 CLI/API/Service 层代码看，这个项目已经不是“一次请求 -> 一次产物”的薄壳。

它已经形成了明确的运行状态机和持久化内核：

- `create`
- `compile / recompile`
- `resume`
- `awaiting_review`
- `completed / failed / cancelled`
- `inspect / reconcile / repair`

并且这些动作不是 README 里的概念，而是进入了：

- `Run`
- `RuntimeStateRef`
- `RuntimeAttempt`
- `RuntimeClaim`
- `WorkerLease`
- `RunSnapshot`
- `ReviewVerdict`
- `Evidence`
- `SimulationRecord`

等对象与仓储逻辑中。

这说明项目已经具备了**显式状态、显式证据、显式治理**的基础，这是一条非常正确的主线。

## 2.2 operator-facing 投影层已经非常强

`status-detail`、`summary`、`inspection`、`audit-report`、`replay-packet`、`operator-packet`、`operator-view`、dashboard snapshot 等一整套 operator-facing read model 已经形成。

这意味着系统不是只会“执行”，而是已经会：

- 解释当前状态
- 解释失败原因
- 给出下一步建议
- 输出审计包
- 输出回放包
- 暴露 claims / leases / attempts / snapshots / orchestration / review state

这一点在同类项目里是明显领先的。  
很多 agent 项目能跑，但不能解释自己；这个仓库已经开始能解释自己。

## 2.3 review policy 与治理语义是真正进入系统的

当前支持的运行级 review policy：

- `auto_only`
- `optional`
- `recommended`
- `human_required`
- `mandatory`

已经进入：

- compile / resume / terminal 语义
- `effective_review_state`
- `latest_review_verdict`
- `summary`
- `inspection`
- `audit-report`
- `governance` 报告

这说明治理不是附加层，而是内核特征。

## 2.4 repo mutation 路线是真实价值点

当前仓库不是只会“分析”和“生成文档”，已经进入受控工程修改能力：

- mutation contract
- read set / write set
- patch apply
- bounded fix loop
- test commands
- mutation report
- orchestration 中 coder 角色可继承父级 mutation contract

这条线非常重要，因为它证明项目的长期方向不只是“workflow for prompts”，而是**workflow for real engineering work**。

## 2.5 测试覆盖广而且触及关键语义

测试不仅覆盖 happy path，还覆盖：

- review policy 分支
- simulation 持久化与 policy trigger
- memory candidate / materialization / retrieval preview
- capability projection / MCP preview
- external worker dispatch
- durable pilot
- sessionful external agent lane
- `project_delivery`
- repo mutation 与 bounded fix loop
- claim / lease / attempt / snapshot / budget
- reconcile / repair
- scheduler authority 冲突 / regrant / projection
- API 与 Web UI surface

这说明仓库对“语义完整性”的重视高于很多同类项目。

---

## 3. 仓库当前最强的结构优势

## 3.1 本地优先的控制平面视角是对的

当前项目最有价值的差异点之一不是“用了什么模型”，而是：

> 它把 agentic execution 当成一个需要被治理、观察、回放、修复的控制平面问题。

这比“做一个多 agent demo”高一个层级。

## 3.2 显式所有权模型是正确方向

claims、worker leases、runtime attempts、snapshots、scheduler authority 这些对象，虽然还需要进一步收口，但方向是对的：

- 执行不是匿名的
- 所有权不是隐式的
- 运行与恢复不是黑盒的
- 审计不是事后拼凑的

## 3.3 多执行通道边界已经形成

当前已经形成多执行通道边界：

- shell
- opencode
- noop
- sessionful external agent
- feature-flagged agent lane
- external worker pool dispatch
- optional runtime gateway

这对后续平台化非常重要，因为说明执行层已经不再被单一路径绑死。

## 3.4 capability plane 已经有真正平台雏形

当前 capability plane 已具备：

- descriptor
- health view
- trust tier
- projection manifest
- MCP profile
- worker pool profile
- runtime gateway projection

这意味着未来做统一 capability runtime 是顺水推舟，而不是从零开始。

---

## 4. 第二轮重评发现的关键问题

下面这些问题里，有些在第一轮已经指出；有些是第二轮深入看代码后需要更明确提出的。

## 4.1 关键问题一：`OrchestratorService` 仍然是过重的真实中心

虽然仓库已经拆出了 mixin 与多个 supporting service module，但从实际调用与行为分布看：

- 生命周期控制
- 编排逻辑
- claims / leases
- scheduler authority 绑定
- mutation 执行
- tool projection
- operator projection
- audit / replay
- repair

仍然高度通过 `OrchestratorService` 汇聚。

这会导致几个后果：

1. 新能力最自然的落点仍是一个巨型 façade  
2. 新的前端 / workbench / SDK 很容易继续直接绑这个 façade  
3. 平台内部边界会继续模糊，后续改造成本持续上升

这不是“代码风格问题”，而是**平台边界问题**。

## 4.2 关键问题二：当前 scheduler authority 更像“单存储上的多数派语义建模”，不是真正独立对等体共识

这是本轮重评最重要的新判断之一。

从当前核心实现看，`packages/core_domain/scheduler_authority.py` 里的 cluster 语义有明显的优点：

- term
- proposal
- decision
- vote
- committed lease
- handoff envelope
- fencing token
- cluster snapshot

这些对象都存在。

但更关键的是实现方式：

- 活跃节点来自本地数据库中的 `authority_node_identities`
- leader 由活跃 node_id 排序后选出
- votes 在同一存储上下文里被创建
- proposal 的“获批”不是通过真实 peer RPC 收集，而是在同一控制逻辑里基于活跃节点列表直接形成
- `peer_urls` 出现在配置中，但在这部分核心算法里并没有形成真正对等体网络协议

这意味着当前实现更接近于：

> **单控制面 / 单存储中的 quorum-style ownership modeling 与 fencing lineage**

而不是严格意义上的：

> **互相独立节点上的复制日志式分布式共识系统**

这并不意味着当前实现没有价值。它仍然对：

- ownership fencing
- replay/audit lineage
- fail-closed callback validation
- takeover lineage presentation

有很高价值。

但问题在于：  
**如果继续向产品化或生态扩张对外表述“已经完成真正的多控制面多数派共识”，就会形成语义超卖。**

本轮重评因此建议：

- 要么明确把当前 shipped shape 定位为 **single-store quorum authority model**
- 要么在下一阶段真正实现 peer-to-peer proposal/vote/commit replication
- 在这之前，不应该模糊这两者之间的界线

这是产品化前必须先修的“语义诚实性问题”。

## 4.3 关键问题三：capability health 当前更多是“声明式健康”，不是“运行时健康”

`packages/core_domain/capability_plane.py` 中的 health 视图是有用的，但目前更多是：

- enabled / disabled
- failure class catalog
- descriptor metadata
- `recent_call_summary` 占位

而不是一个真正持续采样、持续探测、可用于自动调度的 runtime health plane。

问题在于：

- descriptor != availability
- enabled != usable
- route exists != route is healthy
- profile listed != transport can actually perform

这意味着 capability plane 已经有平台雏形，但其 **routing / scheduling / operator health semantics 仍偏静态**。

## 4.4 关键问题四：orchestration baseline 已经存在，但 orchestration engine 还没有真正被抽象出来

`project_delivery` 很重要，因为它证明了系统已经能做：

- planner
- coder / researcher 并行
- reviewer
- barrier
- child run lineage

但它仍然更接近：

> “一个成功实现的 baseline flow”

而不是：

> “所有未来编排都建立其上的通用 graph engine”。

当前还缺少真正的一等公民对象与稳定抽象，例如：

- `ExecutionGraph`
- `NodeSpec`
- `EdgeSpec`
- `BarrierSpec`
- `ReducerSpec`
- `ApprovalGateSpec`
- `WatchdogPolicy`
- `RoleSpec`

没有这些，未来：

- 固定角色体系
- 即时角色生成
- 动态图扩展
- 复杂 fallback / escalation
- 长任务自动化控制

都会继续落回 service 逻辑，难以平台化。

## 4.5 关键问题五：交互层仍然缺位，当前 Web/TUI 仍是 operator console

当前仓库已经有：

- CLI
- API
- TUI
- Web UI

但当前 Web UI 是内联 HTML string 构造的 operator console，定位也明确不是 chat-style workbench。

这本身不是问题，问题在于：

- 当前没有真正的 `IntentSession`
- 没有 plan clarify / revise / approve 的统一对象
- 没有会话态与运行态的正式分离
- 没有事件流式更新面
- 没有把 natural-language goal entry 扩展成真正的 interaction plane

因此当前系统可以说是：

> “后端已具备自然语言入口的部分基础，但产品交互平面还没有真正建立”。

## 4.6 关键问题六：automation plane 尚未形成

README、freeze review 与代码都表明：

- lifecycle 很明确
- repair 也有
- inspection 也有

但当前依然缺一个真正的 background controller / automation plane，去处理：

- stale run watcher
- waiting review timeout
- auto-resume trigger
- event-driven next step
- schedule-driven orchestration
- background reconciliation jobs
- queue / trigger / long job control

这会直接阻碍后续产品化，因为真正的 agent platform 不能长期依赖前台人工按钮推进。

## 4.7 关键问题七：memory plane 还是 kernel primitive，不是产品级记忆系统

当前 memory 设计很清晰，但更多是：

- run-derived candidates
- manual materialization
- retrieval preview
- compile-time injection

这很有价值，但还不是一个完整的产品级记忆体系。  
仍然缺少：

- session memory
- project memory
- artifact memory
- role-scoped memory policy
- promotion / compaction / TTL / summarization policy

因此 memory 已经起步，但还不能承载未来“对话工作台 + 长任务 + 多角色复用知识”的目标。

## 4.8 关键问题八：当前 open debt 为空，但“过渡期结构债”客观存在

`docs/tech-debt-registry.md` 的 open debt 为空，这在“已清掉既有核心债”的狭义上是合理的。  
但从第二轮重评看，仍然客观存在一类新的债：

- 平台边界债
- 语义诚实性债
- orchestration abstraction debt
- interaction-plane debt
- automation-plane debt
- capability-runtime unification debt

这些不应再被写成“未来想法”，而应进入显式债务/阶段规划。

---

## 5. 当前 readiness 判断（第二轮版）

| 维度 | 评价 | 第二轮判断 |
|---|---|---|
| 生命周期内核 | 强 | 已超过原型，值得保留 |
| 治理/审计/回放 | 强 | 是仓库最大的长期资产之一 |
| operator 可观测性 | 强 | read model 很成熟 |
| repo mutation | 中强 | 方向非常好，但应升格成正式平台任务族 |
| capability plane | 中强 | 已有平台雏形，但健康与统一执行契约不足 |
| orchestration substrate | 中 | baseline 可用，但未抽象为真正 graph engine |
| 多 agent 角色系统 | 中弱 | 有固定 baseline，无正式 role runtime |
| 即时角色生成 | 弱 | 基本还未进入平台层 |
| NL workbench | 弱 | 当前仍是 operator-first，不是 interaction-first |
| automation plane | 弱 | 几乎还未成立为独立层 |
| distributed control plane 真实性 | 中弱 | 当前更像单存储上的 quorum modeling，不应过度表述 |
| 生态/扩展模型 | 中弱 | domain pack / skill export 是起点，不是成熟生态系统 |
| 自我迭代升级 | 弱 | inspection / replay / repair 很好，但升级闭环尚未平台化 |

---

## 6. 对根目录既有三份 M31 文档的回看结论

根目录既有三份 M31 文档的总体方向是对的，尤其是：

- “先平台化整理，再进入产品化/生态扩张”
- “保持本地优先内核”
- “不要被某个外部框架整体替代”
- “要抽出 orchestration / interaction / capability / automation 平面”

这些判断都应保留。

但本轮重评认为需要补强两点：

### 6.1 要把“语义诚实性”提升为显式主题

尤其是 scheduler authority / multi-control-plane 这一块，要更明确区分：

- 已实现的 ownership / fencing / lineage / projection
- 尚未达到的真正对等复制式共识能力

### 6.2 要把“operator-ready ≠ product-ready”写得更重

当前 operator surface 已经很强，这容易造成误判，以为“产品已经很接近完成”。  
实际上：

- operator control 很成熟
- 产品交互面仍未完成
- automation 面仍未完成
- 多角色平台抽象仍未完成

---

## 7. 最终判断

## 7.1 这不是一个需要推倒重写的项目

恰恰相反，这个仓库的长期价值主要来自它已经沉淀出的：

- lifecycle
- review policy
- audit/replay
- ownership model
- mutation control
- operator projection

这些都不应该推倒。

## 7.2 但它也绝对不应该直接跳到“大规模产品化 / 生态扩张 / 自主升级”

如果现在直接进入：

- 大量 provider 扩张
- 大量 domain / role pack 扩张
- workbench 产品化
- 自动化控制 / 自主升级
- 更强的 distributed execution 宣传与承诺

而不先把边界收束，会很容易形成：

- 语义超卖
- 平台耦合
- 交互复杂而难用
- capability/runtime contract 混乱
- 后续演化成本急剧上升

## 7.3 第二轮重评的最终建议

> **M31 仍然应该被视为平台硬化阶段，而且要比第一轮评估写得更收紧。**

推荐的下一阶段定位是：

> **M31：平台边界收口 + 语义诚实性修正 + 通用编排抽象 + 交互面/自动化面建立**

在此之前：

- 不建议广度优先
- 不建议平台宣传超前于实现
- 不建议继续让 `OrchestratorService` 成为唯一真实中心
- 不建议把当前 scheduler authority 直接等同于成熟的分布式共识系统

---

## 8. 一句话结论

如果用一句话概括本轮重评：

> 这个仓库已经拥有一个足够强的控制平面内核，但还没有完成从“强内核”到“强平台”的最后一次关键跃迁；而这次跃迁，必须先于产品化和生态扩张发生。
