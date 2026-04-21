# M31 当前阶段问题解决方案（覆盖更新版）

日期：2026-04-21  
状态：建议执行  
目标：在进入接下来的产品化、生态扩张、自主升级与更广泛多 agent 平台建设之前，先修掉当前阶段最关键的结构问题。

---

## 0. 本文的核心目标

本方案不是“补几个功能”。  
它解决的是一个更本质的问题：

> 当前仓库已经具备了很多平台语义，但这些语义还没有全部收束成一个**可诚实表述、可稳定扩展、可产品化演进**的平台架构。

因此，本方案的目标是：

1. 修正当前最危险的结构和语义问题  
2. 在不推倒内核的前提下，让系统具备进入下一阶段的资格  
3. 把后续 M32~M36 的广度扩张建立在一个更稳的基座之上

---

## 1. 先明确：当前最需要修的不是“功能缺口”，而是“平台收口”

当前项目最值钱的东西已经存在：

- 本地优先生命周期内核
- 审计、回放、inspection、repair
- review policy
- mutation contract
- capability plane 雏形
- orchestration baseline
- worker/lease/scheduler authority 模型
- operator projections
- 广泛测试

所以此阶段不应该把精力浪费在：

- 再堆更多 provider
- 再堆更多 UI
- 再堆更多 demo orchestration
- 再堆更多 flags 下的 feature breadth

而应该先完成四件事：

1. **平台边界收口**
2. **语义诚实性修正**
3. **通用 orchestration / capability / interaction / automation 抽象**
4. **为未来 M32~M36 建立可扩展的正式对象模型**

---

## 2. 当前阶段的阻塞级问题（P0）

## P0-1. `OrchestratorService` 仍然过重

### 问题本质
当前项目虽然已经拆出 mixin 和 supporting module，但真正的业务中枢仍然过于集中在 `OrchestratorService`。

### 风险
如果继续这样扩展，未来所有这些东西都会继续向它聚拢：

- workbench
- role runtime
- automation controller
- capability runtime
- eval/upgrade loop
- distributed execution logic

结果会是：

- 边界越来越模糊
- 修改风险越来越大
- 新表面继续直接依赖一个大 façade
- 后续平台化改造成本暴涨

### 解决方案
把 `OrchestratorService` 退化为兼容 façade / coordinator，不再作为真实平台中枢。

### 建议拆出的服务边界
- `RunKernelService`
- `LifecycleKernelService`
- `ReviewPolicyService`
- `OwnershipLeaseService`
- `SnapshotLineageService`
- `MutationExecutionService`
- `CapabilitySelectionService`
- `AuditReplayService`
- `RepairReconciliationService`

### 验收标准
- 新增平台能力不再直接往 `OrchestratorService` 里塞主逻辑
- CLI/API/Web/TUI 可以继续使用 façade，但内部必须是明确 delegation
- 单个服务文件不再同时承担生命周期、编排、capability、repair、projection 多重职责

---

## P0-2. scheduler authority 语义需要收紧并诚实化

### 问题本质
当前实现已经建模了：

- proposals
- decisions
- votes
- committed leases
- fencing
- handoff lineage

这很好。  
但从核心代码看，当前“多数派”更多依赖同一存储上下文中的节点列表和投票记录，而不是一个真正独立 peer 间复制/提交协议。

### 风险
如果这一点不先修，后续会出现两个严重问题：

1. **技术风险**：后面真要走 hosted/multi-node/product path 时，底层语义不够硬
2. **产品/叙事风险**：对外表述容易超过代码当前可证明的范围

### 解决方案
这里有两个可行路线，但必须二选一并显式化。

#### 路线 A：短期诚实收口（推荐先做）
把当前 shipped path 明确定义为：

> **single-store authority cluster / quorum-style ownership model**

即：
- 保留 term/decision/lease/fencing/handoff 的全部价值
- 但不再把它直接表述成“真正的 peer-to-peer distributed consensus”

#### 路线 B：中期补齐真实 distributed path
如果真的要继续宣称“多数派对等体共识”，则必须新增：

- peer-to-peer proposal RPC
- vote collection protocol
- explicit leader/follower replication
- commit acknowledgement
- term divergence handling
- split-brain / partition test
- peer failure and rejoin semantics

### 当前阶段建议
M31 先做路线 A，再把路线 B 放到后续里程碑，而不是现在继续模糊。

### 验收标准
- README、governance、release-readiness、评估文档、operator surface 中的集群叙述与代码真实能力一致
- cluster mode 明确区分 “single-store modeled quorum” 与未来 “replicated authority”
- 新增测试专门验证这一语义边界

---

## P0-3. orchestration 必须从 baseline flow 升级成正式 graph engine

### 问题本质
`project_delivery` 已经证明编排方向正确，但还不是通用 orchestration substrate。

### 风险
如果不抽象，未来固定角色、多角色图、动态角色注入、review quorum、watchdog、fallback 都会继续写成特例逻辑。

### 解决方案
建立真正的一等公民编排对象：

- `ExecutionGraph`
- `NodeSpec`
- `EdgeSpec`
- `RoleSpec`
- `BarrierSpec`
- `ReducerSpec`
- `ApprovalGateSpec`
- `RetryPolicy`
- `WatchdogPolicy`

### 最低动作
1. 把 `project_delivery` 迁移成 graph definition，而不是 service 内部特例
2. 增加 graph validate / graph preview / graph persistence
3. 支持最少一条新图，不修改核心 lifecycle 逻辑即可接入

### 验收标准
- 至少两个 orchestration preset 可以基于同一 graph engine 工作
- orchestration 不再依赖硬编码角色顺序
- barrier / reducer / gate 成为正式抽象而不是隐藏状态拼接

---

## P0-4. capability plane 必须统一成真正 capability runtime contract

### 问题本质
当前 capability 相关能力已经不少，但还没彻底形成统一调用契约。

当前实际存在的东西包括：

- adapters
- MCP profiles
- tool projection
- worker pools
- runtime gateway
- sessionful external lane
- capability descriptors / health

这些东西彼此有关联，但平台眼里还不够“同一种东西”。

### 风险
后续如果直接扩展：

- provider
- role pack
- hosted tool
- external runtime
- IDE / CI connector

会造成运行契约越来越乱。

### 解决方案
建立统一的 capability runtime contract：

- `CapabilityDescriptor`
- `CapabilitySelection`
- `CapabilityInvocationEnvelope`
- `CapabilityExecutionReceipt`
- `CapabilityTrustPolicy`
- `SandboxProfile`
- `CapabilityHealthProbe`

### 必须补上的一项
health 要从“声明式健康”升级到“运行时健康”：

- last success / failure
- latency bucket
- recent probe result
- auth failure / transport failure / timeout bucket
- degraded / ready / unavailable

### 验收标准
- 不同 capability backend 的调用在平台侧长成统一 envelope
- policy、audit、trace、operator projection 可以跨 backend 复用
- capability health 不再只是 enabled/disabled 目录信息

---

## P0-5. 需要建立 interaction plane，而不是继续只靠 operator surface

### 问题本质
当前自然语言入口只到达“goal launch / preview”这一级，尚未形成完整交互层。

### 风险
如果现在直接做更漂亮的前端，会把 operator internal projection 直接暴露给用户，导致：

- 交互模型混乱
- session / run 混淆
- follow-up 处理很难标准化
- 后续 workbench 设计被 operator model 绑死

### 解决方案
建立 interaction plane 正式对象：

- `IntentSession`
- `IntentPacket`
- `ClarificationState`
- `PlanDraft`
- `LaunchDecision`
- `ConversationTurn`
- `RunFollowupRequest`

### 必须坚持的原则
- conversation state ≠ execution state
- 交互层只引用运行态，不直接等于运行态
- UI/workbench 建在 interaction API 上，而不是直接绑 operator packet

### 验收标准
- 用户可以经过“目标 -> 澄清 -> 计划预览 -> 批准 -> 启动”流程进入执行
- follow-up 请求可以映射到结构化控制动作
- workbench 和 operator console 成为两个层级，而不是一个东西两种皮肤

---

## P0-6. 需要真正的 automation plane

### 问题本质
当前系统的 lifecycle 很明确，但推进方式仍然主要依赖前台显式调用。

### 风险
没有 automation plane，系统就很难进入：

- 长任务
- 计划中的自动推进
- 超时处理
- stale-run 清理
- background repair
- 事件驱动扩展

### 解决方案
建立 `AutomationController` 和 background supervisor：

- stale run watcher
- waiting review timeout
- schedule trigger
- event trigger
- background reconcile / health scan
- escalation rules
- retry / reroute actions

### 验收标准
- 一部分运行推进不再必须依赖前台按钮
- 背景控制逻辑是显式可配置、可观测、可审计的
- automation 行为能进入 audit / replay / operator projection

---

## 3. 重要但次于 P0 的问题（P1）

## P1-1. memory 需要分层，不应继续只停留在 run-memory primitive
建议正式拆分为：

- session memory
- run memory
- artifact memory
- skill memory
- policy/failure memory

## P1-2. eval / trace / repair 需要形成统一进化闭环
当前 inspection / replay / repair 很强，但还没有正式变成：

- benchmark
- eval report
- canary
- upgrade proposal
- promotion decision

## P1-3. packaging / extension model 需要明确分层
建议区分：

- domain packs
- role packs
- skill packs
- capability packs

## P1-4. operator surface 与 product surface 需要明确双轨
Web/TUI 继续服务 operator；未来 workbench 不应试图取代 operator console。

---

## 4. M31 建议实施路线

## Phase M31-A：边界收口 + 语义诚实性修正

### 目标
- 拆 façade
- 修正 authority cluster 叙述
- 识别当前 shipped semantics 与 future semantics 的边界

### 交付物
- service decomposition
- updated architecture wording
- control-plane mode taxonomy
- debt registry 增加“过渡期结构债”

### Exit gate
- 对外/对内文档不再出现语义超卖
- 新功能不再默认往 `OrchestratorService` 堆

---

## Phase M31-B：通用 orchestration substrate

### 目标
- 形成 graph-based orchestration

### 交付物
- `ExecutionGraph`
- graph validate/preview
- `project_delivery` graph migration
- second orchestration template

### Exit gate
- 新编排能不改核心 lifecycle 逻辑接入

---

## Phase M31-C：capability runtime + health plane

### 目标
- 统一 capability invocation contract
- 引入真正 runtime health

### 交付物
- capability invocation envelope
- trust/sandbox policy
- runtime health probing
- backend-agnostic trace/audit projection

### Exit gate
- capability routing 不再是多个彼此分裂的执行分支

---

## Phase M31-D：interaction plane

### 目标
- 形成 workbench 后端，不再只有 operator entry

### 交付物
- `IntentSession`
- plan clarify/approve flow
- follow-up request mapping
- interaction API

### Exit gate
- 自然语言交互正式进入系统模型

---

## Phase M31-E：automation plane

### 目标
- 后台控制正式建立

### 交付物
- `AutomationController`
- timeout / stale / event / schedule handling
- background reconcile jobs
- automation operator visibility

### Exit gate
- 系统不再是只能靠前台按钮推进的 control plane

---

## 5. 本阶段明确“不做什么”

为了避免再次跑偏，M31 应明确以下非目标：

### 5.1 不做大规模 provider breadth 扩张
先把 capability contract 统一再说。

### 5.2 不把当前 authority model 继续包装成已经完成的 distributed consensus
这是产品和架构上都不该冒的风险。

### 5.3 不先做漂亮前端再补交互内核
顺序必须反过来。

### 5.4 不先开放无约束自我升级
必须先有 eval / canary / promotion 体系。

### 5.5 不围绕单一外部框架重写
吸收模式，不做整体替换。

---

## 6. 成功标准

M31 结束时，应至少达到下面这些标准：

### 架构层
- `OrchestratorService` 退位为 façade/coordinator
- `project_delivery` 不再是唯一编排特例
- capability runtime contract 成型
- authority cluster 叙事与实现一致

### 产品层
- 存在真正的 interaction API
- 用户可以通过“澄清 -> 计划 -> 批准 -> 执行”路径使用系统
- operator UI 与 product workbench 分层清楚

### 自动化层
- stale run / timeout / waiting review 能被后台逻辑显式处理
- automation 进入 audit / replay / operator surfaces

### 平台层
- 新 capability backend、新 orchestration、新 role pack 的接入边际成本显著下降
- debt registry 正式纳入平台过渡期债务

---

## 7. 一句话建议

> 先把当前仓库从“强控制平面内核 + 大量平台语义”收口成“真正边界清楚的平台基座”，再谈产品化、生态扩张和自主升级；否则后面的每一步都会比现在贵得多。
