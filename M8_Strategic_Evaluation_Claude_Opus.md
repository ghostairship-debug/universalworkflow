# M8 战略规划文档深度独立评估

**评估人：** Claude Opus 4.6 (Thinking)  
**评估日期：** 2026-04-19  
**评估对象：**  
1. `m8-ecosystem-reuse-and-wheel-reinvention-assessment.md` (670行, 24KB)  
2. `m8-external-tool-integration-and-self-build-plan.md` (680行, 17KB)  
3. `m8-pre-entry-extra-optimization-assessment.md` (192行, 5.8KB)  
4. `m7-gemini-opus-pre-m8-synthesis.md` (389行, 14KB) — 作为上述三者的源头文件一并审阅  
**评估方法：** 逐文档代码级交叉验证 + 架构可行性判定

---

## 1. 总体评判 (Executive Judgment)

> **这三份文档代表了本项目自 M0 以来最重要的一次战略方向调整。** 它们的核心论断——"停止在基础设施层重新发明轮子，专注于控制面差异化"——是 **完全正确的**。但在执行层面，部分集成方案低估了与现有代码结构的摩擦力，需要在 M8 Phase 0 中做更审慎的范围切割。

---

## 2. 逐文档深度评估

### 2.1 生态重用评估 (Ecosystem Reuse Assessment) — ⭐⭐⭐⭐⭐ 极优

**这是三份文档中质量最高的。** 它做了一件此前 M0–M7 八个里程碑都没有做过的事：**正视项目与外部生态的重叠度**。

#### 做得极好的部分

1. **重叠度量化分层。** 将重叠区域分为"高重叠（durable orchestration, tracing, tool registry）"、"中重叠（memory, HITL）"、"低重叠（domain packs, simulation, governance）"，每一层都有清晰的判据。这不是泛泛而谈的"我们应该用开源"，而是精确到了哪些 **具体的内部抽象** 与生态工具重合。

2. **"Keep vs. Stop vs. Integrate" 三级判定。** 第 10 节的三列分类极其清晰：
   - **Keep custom：** run contracts, governance, simulation, domain packs — 这些确实是项目的护城河
   - **Stop self-building：** tracing platform, connector registry, skill packaging — 这些确实是生态已经商品化的领域
   - **Start integrating：** MCP, external tracing, Agent Skills, durable runtime pilot — 这些是正确的着力点

3. **生态扫描的广度。** 覆盖了 LangGraph / LangSmith / OpenAI Agents SDK / Pydantic AI / AutoGen / CrewAI / Mastra / Temporal / Prefect / Dagster / n8n / Flowise / Dify / Smithery / Arcade / Langfuse / Phoenix 等 17+ 个生态系统，并且每一个都给出了"fit"或"non-fit"的理由。这不是一份"技术选型清单"，而是一份真正的 **生态位分析**。

#### 需要注意的微瑕

- **重用比例估算过于自信。** 文档称"70%–85% 的未来基础设施工作可以重用"。这个数字在方向上正确，但在没有实际 POC 的情况下，可能会给团队错误的期望。实际集成工作的 adapter 编写、状态映射、测试适配等摩擦成本通常会吃掉 30%–50% 的"理论节省"。

---

### 2.2 外部工具集成计划 (Integration Plan) — ⭐⭐⭐⭐☆ 优秀，但有实施风险

#### 最有价值的设计决策

1. **"Router-first MCP"（第 6 节）。** 这是整份文档中最关键的架构决策。原文明确了六条 MCP Token 策略规则：
   - 投影优先于暴露
   - 活跃工具集限制在 1–5 个
   - Schema 最小化
   - 资源获取不等于 Prompt 填充
   - 稳定的 Manifest 缓存
   - Policy-bound 的暴露过滤

   **评价：** 这六条规则如果严格执行，可以完全避免 MCP 的"工具爆炸"问题。这是我见过的对 MCP 集成最有纪律的设计方案之一。

2. **不替换核心的原则。** 第 8 节的六条"不要做"清单（不要重写到 Dify/Flowise 上、不要暴露全部 MCP 工具、不要用外部 Dashboard 替换本地治理报表...）准确地划出了保护线。

#### 代码级可行性分析

我逐一交叉验证了集成方案与当前代码的实际接口：

**MCP-First 工具平面：**
```python
# 当前的 CapabilityRegistry (60 行) 设计极简：
# __init__(adapters: list[WorkerAdapter])
# capabilities() -> list[str]
# adapter_for(capability, adapter_name) -> WorkerAdapter | None
```
要引入 MCP，需要做的是在 `WorkerRouter.__init__` 中除了硬编码的 `[ShellAdapter(), OpenCodeAdapter(), NoopAdapter()]` 之外，增加一个 `MCPCapabilitySource` 来动态发现工具。**这与现有架构完全兼容。** `WorkerAdapter` ABC 的接口（`get_capabilities / estimate_cost / launch / collect_artifacts`）可以被 MCP 工具映射为一个泛化的 `MCPToolAdapter`。

**可行性：🟢 极高。** 预估 200–400 行新增代码即可完成核心路径。

**Durable Runtime 引擎试点：**
```python
# 当前 RuntimeGateway ABC (3 个方法):
# describe() -> dict
# start(run_id, runtime_task_id) -> RuntimeStateRef
# resume(state_ref) -> RuntimeStateRef
```
这个 ABC 极窄 — 只有 `start` 和 `resume` 两个运行时方法。文档建议在这个 ABC 下面挂一个 `LangGraphRuntimeAdapter`。

**问题在于：** 当前的 `RuntimeGateway` 并不控制执行循环。真正的执行循环在 `OrchestratorService._execute_prepared_run()` → `WorkerRouter.route(packet)` → `adapter.launch(packet)` 这条链路上。`RuntimeGateway` 仅仅负责生成 `runtime_brief`（即 LLM 的执行预审文本），它 **不是** 控制执行流转的引擎。

**这意味着：如果要引入 LangGraph 作为 durable runtime，仅仅替换 `RuntimeGateway` 是不够的。** 需要在 `LifecycleServiceMixin` 的 `compile/execute/resume` 主链路中增加一个分流点，允许某些 Run 走 LangGraph 子图而非当前的 `ShellAdapter.launch()` 同步路径。这比文档暗示的"加一个 Gateway 实现"要复杂得多。

**可行性：🟡 中等。** 文档低估了集成深度。需要约 600–1000 行新增代码 + 显著的测试适配。

**外部观测集成：**
当前事件模型（`RunEvent` 27 种类型 + `TraceContext` 12 个关联 ID）已经足够用来构建 OpenTelemetry Span。核心路径是：在 `event_repo.append()` 调用点增加一个异步的 `TraceExporter` 钩子。

**可行性：🟢 高。** 预估 150–300 行新增代码。

---

### 2.3 准入前额外优化评估 (Pre-Entry Optimization) — ⭐⭐⭐⭐⭐ 极优

这份文档解决了一个关键的 **决策困境**：面对两份外部评估报告指出的残留问题，是否应该再开一轮硬化？

**答案是坚定的"不"。** 文档的逻辑链极其严密：

1. Pre-M8 已经通过了自定义的 Gate（`pre_m8_gates overall_passed=true`）
2. 216 个测试全绿
3. 残留问题（services.py 仍然较大、新模块测试偏薄）是"信心改善"而非"基线缺陷"
4. 再开一轮硬化会模糊里程碑边界、削弱纪律

**评价：** 这份文档展示了极其成熟的 **过度工程化抵抗力**。能在"发现问题"和"过度反应"之间精准切割，说明项目的治理纪律已经内化。

---

## 3. 与代码现实的摩擦分析 (Code-Reality Friction Points)

以下是三份文档中 **未充分讨论但会在执行中产生显著摩擦** 的技术点：

### 3.1 🔴 TaskKind 枚举的刚性

当前 `TaskKind` 只有两个值：
```python
class TaskKind(StrEnum):
    shell_exec = "shell_exec"
    noop = "noop"
```

如果引入 MCP 工具作为新的 Capability Source，每一个 MCP 工具 **不是** 一种 `TaskKind`。但当前的 `compile_run()` 和 `_resolve_task_kind()` 都围绕 `preset.allowed_task_kinds` 来路由。这意味着：

- 要么扩展 `TaskKind` 枚举（如 `mcp_tool_call`）
- 要么让 MCP 工具走 `shell_exec` 的隧道（通过环境变量注入 MCP server 地址）
- 要么重构 capability resolution 使其不再依赖 `TaskKind` 枚举

**三份文档都没有讨论这个问题。** 这是 MCP 集成落地时最先碰到的设计抉择。

### 3.2 🟡 SQLite 的 Repository 耦合

集成计划假设可以保持 `SQLite-first` 的本地优先模型。但如果 LangGraph 成为 durable runtime pilot，LangGraph 有自己的 checkpoint store（默认 `MemorySaver`，可接 PostgreSQL 或 Redis）。这意味着 **存在两套持久化系统**：

- 本项目的 SQLite（run / event / task / evidence / claim / lease / attempt / snapshot）
- LangGraph 的 checkpoint store（graph state / thread state）

这两套系统之间的一致性如何保证？谁是 source of truth？文档虽然说了"repository state remains canonical"，但没有给出具体的同步/映射机制。

### 3.3 🟡 NullRuntimeGateway 的测试保护

文档未提及的一个关键约束：**当前 216 个测试中 100% 运行在 `NullRuntimeGateway` 下。** 任何 MCP / LangGraph 集成都必须保证：

1. 所有现有测试仍然在 `NullRuntimeGateway` + 无 MCP Server 的环境下通过
2. 新增的 MCP / LangGraph 测试有独立的 fixture，不污染现有测试环境

这个"测试隔离性"约束在三份文档中完全没有被提及，但它是保护现有基线的生命线。

---

## 4. M8 Phase 分期建议的评估 (Phase Sequence Assessment)

集成计划提出了 7 个 Phase 的执行序列。以下是我的评判：

| Phase | 内容 | 文档建议顺序 | 我的建议顺序 | 调整理由 |
|-------|------|-------------|-------------|---------|
| Phase 0 | Scope Freeze + ADR | 1st | **1st** | ✅ 无争议 |
| Phase 1 | MCP-First Capability | 2nd | **2nd** | ✅ ROI 最高，与现有架构摩擦最小 |
| Phase 2 | Agent Skills 标准化 | 3rd | **4th** | ⬇️ 优先级过高。目前只有 1 个 Domain Pack，标准化的紧迫性不如观测集成 |
| Phase 3 | Trace/Eval 后端 | 4th | **3rd** | ⬆️ 这能直接偿还 TD-007 并提供立即可见的价值 |
| Phase 4 | Durable Runtime Pilot | 5th | **5th** | ✅ 风险最高，放在最后是正确的 |
| Phase 5 | Companion Workflow | 6th | **6th 或删除** | 当前阶段不需要 |
| Freeze Review | Go/No-Go | 7th | **6th** | ✅ 无争议 |

**核心调整：** 将 Trace/Eval 集成提前到 Agent Skills 之前。理由：
1. 外部观测是全团队立即受益的基础设施
2. Agent Skills 标准化在只有 1 个 Domain Pack 的现阶段，价值有限
3. 先有可观测性，后做更复杂的 MCP/Skills 集成时才能有效 debug

---

## 5. 战略级盲点 (Strategic Blind Spots)

### 5.1 缺失的回退策略 (Missing Rollback Plan)

三份文档都是"前进计划"，但没有讨论：**如果 MCP 集成或 LangGraph 试点失败，回退路径是什么？**

当前项目最大的优势之一就是 **完全自主的本地运行能力**（216 测试全部离线通过）。M8 的任何集成都不应该损害这个能力。文档应该明确声明：

> **M8 的所有外部集成必须是 opt-in 的增强层，不是 opt-out 的依赖层。** 如果所有外部服务不可用（无 MCP Server、无 Langfuse、无 LangGraph），系统必须回退到当前的 `NullRuntimeGateway` + `ShellAdapter` 路径并保持完整功能。

### 5.2 缺失的 API 稳定性声明

引入 MCP 和外部观测后，API 路由 `/runs/{run_id}/status-detail` 等的返回结构可能需要扩展（如增加 `mcp_tools_projected`、`trace_external_id` 等字段）。文档没有讨论 API 的向后兼容策略。

### 5.3 OpenAI Responses API 的依赖脆弱性

M7 评估中已经指出：`gateway.py` 使用的是 OpenAI 的 `responses.create()` API（而非标准的 `chat.completions.create()`）。如果 M8 同时引入 LangGraph（内部使用 LangChain/LangSmith 的 LLM 调用路径），就会存在 **两种不同的 OpenAI SDK 调用方式**。这需要在 ADR 中明确统一。

---

## 6. 最终评分与总结

| 维度 | 评分 | 说明 |
|------|------|------|
| 战略方向正确性 | ⭐⭐⭐⭐⭐ | "Reuse substrate, Keep operating model" 是完全正确的方向 |
| 生态分析深度 | ⭐⭐⭐⭐⭐ | 17+ 生态系统的对比分析是极罕见的高质量工作 |
| 架构保护线设计 | ⭐⭐⭐⭐⭐ | Router-first MCP + 六条 Token 策略 + 六条"不要做"清单 |
| 与现有代码的对齐度 | ⭐⭐⭐☆☆ | TaskKind 刚性、双重持久化、测试隔离性均未充分讨论 |
| 执行可行性 | ⭐⭐⭐⭐☆ | MCP 和观测集成可行性高，LangGraph 试点风险被低估 |
| 回退/容错策略 | ⭐⭐☆☆☆ | 完全缺失。这是最需要补充的部分 |

### 一句话总结

> 这三份文档 **精准地定义了项目从"自建一切"到"差异化控制面"的战略转型方向**，其生态分析和架构保护线设计堪称教科书级别。最大的短板不在战略层，而在 **执行层的摩擦预判**：`TaskKind` 枚举的刚性、双重持久化的一致性、测试隔离性的保护、以及最关键的——**缺失的回退策略**。建议在 M8 Phase 0 的 Scope Freeze 中补充一份 "Degradation Policy ADR"，明确声明所有外部集成必须是 opt-in 增强而非 opt-out 依赖。
