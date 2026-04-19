# M8 GPT Pro 外部评估复审与方案修正

**评估日期：** 2026-04-19  
**输入来源：**

- 用户提供的 `GPT Pro` 外部评估与替代版 `M8` 总计划
- 现有仓库基线：`M7 complete` + `Pre-M8 complete`
- 当前 `M8` 方案与相关评估文档

---

## 1. 复审结论

这份 `GPT Pro` 外部评估的方向判断是**总体正确且有较高价值**的。

它最重要的贡献，不是重新定义了 `M8` 的目标，而是对现有 `M8` 方案做了四个关键纠偏：

1. 把 **LangChain `create_agent + middleware`** 提前为 `M8` 的标准 agent lane
2. 把 observability 从“单一具体后端优先”调整为 **OTel-first、sink-agnostic**
3. 把 **durable runtime pilot** 前移到 Skills 之前
4. 把 **Agent Server / Studio** 明确定位为“可借用的 server / IDE 层”，而不是本仓库要平行重造的平台层

经与官方文档复核，这些修正大体成立，应吸收进当前 `M8` 方案。

---

## 2. 与官方文档对照后的判断

以下判断已与官方文档交叉核对。

### A. LangGraph 是低层 orchestration/runtime

官方明确把 LangGraph 定位为：

- low-level orchestration framework and runtime
- 强项是 durable execution、streaming、human-in-the-loop、memory
- 如果需要更高层 agent abstraction，建议优先用 LangChain agents  

因此，把 LangGraph 视为底层 runtime substrate，而不是直接当默认高层 agent loop，是正确的。

### B. LangChain agents / `create_agent` 应作为标准 agent lane 候选

官方当前文档明确表明：

- LangChain 的 agent abstraction 建立在 LangGraph 之上
- `create_agent` 是高层 agent loop 的标准入口
- middleware 覆盖动态模型选择、工具控制、guardrails、HITL 等扩展点

因此，在 `M8` 中先建立一条 **标准 agent lane**，再做更重的 durable runtime pilot，是合理的顺序。

### C. Functional API 与 Graph API 应分层使用

LangGraph 官方文档明确说明：

- Functional API 适合最小改动接入 persistence / memory / HITL / streaming
- Graph API 适合显式 shared state、复杂 branching、parallel merge、subgraph、可视化 graph 结构

因此，`M8` 中如果进行 LangGraph pilot，应默认先走 Functional API，再在确有复杂 workflow 需要时使用 Graph API。

### D. Agent Server / Studio 可借用，但不应成为本项目重造目标

LangChain 生态已经提供：

- Agent Server
- Studio
- LangGraph CLI / server-side MCP 能力

因此，本项目不应在 `M8` 平行重造一个同类平台层，而应将这些能力视为：

- server / IDE / debug tooling layer
- 可借用、可对接、可复用
- 但不是仓库自己的主控制面

### E. OTel-first 是更稳的 observability 路径

Langfuse 明确支持：

- OTLP/HTTP ingestion
- `/api/public/otel`
- OTel exporter 直连

因此，比起在 `M8 Phase 0` 就绑定某单一后端，先冻结：

- `OTel-first export abstraction`
- `sink-agnostic design`

更稳妥。

### F. MCP 不会自动帮本项目解决 trust / projection / token 问题

MCP 官方规范确认：

- stdio 与 Streamable HTTP 是不同 transport
- HTTP transport 存在 session / auth / security 规范
- stdio transport 通常从环境中获取凭据

因此：

- MCP 只是协议
- trust tier
- tool subset
- schema budget
- projection / policy

仍然必须由本仓库控制面自己定义

---

## 3. 采纳的修正

以下内容正式采纳进 `M8` 新版方案。

## 3.1 Phase 顺序修正

旧方案方向：

- `MCP-first capability plane`
- `Skills`
- `trace/eval`
- `durable runtime pilot`

修正后顺序：

1. `Phase 0 - Rebaseline and Scope Freeze`
2. `Phase 1 - Borrowed Agent Foundation`
3. `Phase 2 - MCP Capability Pilot`
4. `Phase 3 - Observability`
5. `Phase 4 - Durable Runtime Pilot`
6. `Phase 5 - Skills Alignment`
7. `Phase 6 - Confidence Pack`
8. `Phase 7 - Freeze Review`

理由：

- 先证明高层 agent loop 不该继续自写
- 再证明 capability plane 如何外部化
- 再接 observability
- 再做最重的 durable pilot
- Skills 作为 portability 层后置

## 3.2 标准 agent lane 前移

`M8` 新版方案正式增加：

- **Standard agent lane**
- 默认以 `LangChain create_agent + middleware` 作为候选实现

同时保留：

- Native deterministic lane 作为默认稳定路径

## 3.3 Observability 调整为 OTel-first

从：

- “优先某个具体后端”

调整为：

- **OTel-first**
- **sink-agnostic**
- `Langfuse` 作为首个 sink 实现
- `LangSmith` 保留为后续可选 sink / dev tooling route

## 3.4 Durable pilot 放到 Skills 之前

这项修正采纳。

理由：

- durable runtime 是运行模型问题
- Skills 更偏 packaging / portability
- 运行模型优先级高于包装互通层

## 3.5 Agent Server / Studio 定位修正

采纳：

- 作为可借用的 server / IDE / debug tooling layer
- 不作为本项目要平行重造的平台层

## 3.6 新增 Borrow / Wrap / Own 框架

采纳三层划分：

- **Borrow**
- **Wrap**
- **Own**

这比单纯“外部化 / 自研”更适合当前仓库的架构判断。

## 3.7 新增多 lane 执行模型

采纳四条 lane 的思路：

- Lane A — Native deterministic lane
- Lane B — Standard agent lane
- Lane C — Durable incremental lane
- Lane D — Graph-native complex lane

## 3.8 新增 Canonical IDs & State Mapping 约束

采纳：

- `run_id`
- `review_id`
- `runtime_attempt_id`
- `tool_call_id`
- `thread_id`
- `checkpoint_id`
- `external_trace_id`

等 ID 分类思路，并要求在 `Phase 0` 明确冻结状态映射规则。

## 3.9 新增 trust tier / feature flag 体系

采纳：

- trust tier
- feature flags
- promotion rules

这些会显著提升 `M8` 外部能力接入时的控制力。

---

## 4. 保留审慎、未直接全量照搬的部分

并不是 `GPT Pro` 评估中的每一句都要直接转成硬约束。

以下内容保留审慎处理：

## 4.1 `research_spike_reviewable` 视为推荐试点类，而不是现成事实

这类命名和试点切片方向是好的，但是否直接落为：

- preset
- run class
- profile

应在 `M8 Phase 0` 冻结，而不是在计划文档中假定它已经存在。

## 4.2 LangGraph pilot 仍保持高风险标记

虽然新版方案同意把 durable pilot 前移到 Skills 前面，
但这不意味着降低它的风险等级。

当前仓库仍存在：

- repository state 与 external runtime state 的映射难点
- `TaskKind` / capability projection 与 pilot lane 的耦合问题
- 默认本地基线保护问题

所以 durable pilot 前移的是**阶段顺序**，不是**风险判断**。

## 4.3 Agent lane 仍必须是 opt-in enhancement

即便引入 `create_agent + middleware`，
也不能让它变成默认主链。

默认稳定链仍然是：

- `feature_delivery`
- native deterministic lane

---

## 5. 对现有 M8 方案的最终修正意见

基于这轮复审，现有 `M8` 方案应做如下修正：

1. 把 `LangChain create_agent + middleware` 升格为 `M8` 的标准 agent lane 入口
2. 把 observability 改写为 `OTel-first / sink-agnostic`
3. 把 durable runtime pilot 前移到 Skills 之前
4. 把 Agent Server / Studio 明确写成“借用层”，不是“目标平台层”
5. 增加：
   - Borrow / Wrap / Own
   - lane model
   - canonical IDs
   - trust tiers
   - feature flags
6. 保持原有强约束不变：
   - local-first control plane
   - opt-in enhancement
   - repository canonical state
   - `TaskKind` 保持小而稳定
   - fallback / degradation policy 必须存在

---

## 6. 结论

`GPT Pro` 的这轮外部评估**不是在推翻现有 M8 方案**，
而是在以下几个关键点上把它变得更成熟：

- 更贴近官方生态边界
- 更符合真实接入顺序
- 更能避免把 Skills 或 LangGraph 放到错误位置
- 更好地保护本地控制面与默认基线

因此，建议：

- **保留现有 M8 主旨**
- **吸收本次复审中列出的修正**
- **将根目录 M8 总方案升级为 v1.1**
