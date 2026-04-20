# M8 Phase Plan v1.1 独立评估报告

**评估人：** Claude Opus 4.6 (Thinking)  
**评估日期：** 2026-04-19 (v2 — 针对 v1.1 Freeze Draft 更新)  
**评估对象：** `universal_agentic_workflow_os_M8_phase_plan_v1_0.md` (v1.1, 865行, 22KB)  
**新增输入：** `docs/reviews/m8-gpt-pro-reassessment-and-plan-update.md` (306行, 8KB)  
**测试基线确认：** `pytest tests/ -q` → **216 passed** (82.47s) ✅  
**Git 状态：** ✅ 已提交 (`03db8b9 Checkpoint Pre-M8 hardening and M8 planning baseline`)

---

## 1. 总体评判 (Executive Verdict)

> **v1.1 较 v1.0 发生了质的飞跃。** 这不再仅仅是一份"接入外部生态的计划"，而是一份具备工程实操级别精度的**架构转型蓝图**。新增的四条执行通道 (Lane Model)、Borrow/Wrap/Own 三层分类、9 份 ADR 门禁、Trust Tier 体系和 Feature Flag 制度，将此前所有评估中的"软性建议"转化为了可强制执行的工程约束。

> **结论：这是本项目 M0–M7 全周期中最好的一份里程碑规划。可以作为 M8 的正式执行基线 (APPROVED FOR M8 EXECUTION)。**

---

## 2. v1.0 → v1.1 的关键变化 (Delta Analysis)

| 维度 | v1.0 | v1.1 | 变化性质 |
|------|------|------|---------|
| Phase 数量 | 7 (Phase 0–6) | **8 (Phase 0–7)** | 新增 Phase 1 "Borrowed Agent Foundation" |
| 核心框架 | "Reuse substrate / Keep model" | **Borrow / Wrap / Own 三层分类** | 从二元分类升级为三层精确分类 |
| 执行模型 | 单一路径 | **四条 Lane (Native/Agent/Durable/Graph)** | 最重要的架构创新 |
| ADR 门禁 | 5 份 | **9 份** | 新增 Lane Strategy / Trust Model / Feature Flags / Durable Contract |
| Observability | Langfuse 优先 | **OTel-first, sink-agnostic** | 从绑定单一后端到协议优先 |
| Agent 抽象 | 未明确 | **LangChain `create_agent + middleware`** | 新增标准 agent lane |
| Trust 模型 | 未定义 | **T0–T3 四级信任层** | 全新 |
| Feature Flags | 未提及 | **5 个显式 flag** | 全新 |
| Run Class 分配 | 未明确 | **feature_delivery=native, research_spike=agent, research_spike_reviewable=durable** | 精确到 preset 级别的路径分配 |
| Canonical IDs | 未定义 | **11 个 canonical ID 类型** | 全新 |
| Kill Criteria | 未提及 | **Phase 4 有 4 条 kill criteria** | 全新 |
| 工程纪律 | 未提及 | **PR纪律 / 测试纪律 / Promotion纪律** | 全新 |
| Git 状态 | ⚠️ 68 文件未提交 | ✅ **已提交** | **此前的唯一硬阻塞已解除** |

---

## 3. 重大架构创新评估

### 3.1 四条 Lane 模型 — ⭐⭐⭐⭐⭐ 本次更新最大的亮点

```
Lane A — Native deterministic (ShellAdapter/NoopAdapter, 当前默认)
Lane B — Standard agent (LangChain create_agent + middleware)
Lane C — Durable incremental (LangGraph Functional API)
Lane D — Graph-native complex (LangGraph Graph API, 仅复杂场景)
```

**为什么这是最关键的设计决策：**

1. **解决了此前评估中的最大悬疑。** v1.0 说"引入 LangGraph 试点"，但没有说清楚 LangGraph 与现有执行主链的关系。Lane 模型精确回答了这个问题：LangGraph 只用于 Lane C/D，当前主链 (Lane A) 完全不受影响。

2. **渐进式风险控制。** 四条 Lane 形成了一个清晰的风险梯度：A（零风险）→ B（低风险）→ C（中风险）→ D（高风险）。每条 Lane 都可以独立开关，不存在"要么全上要么全不上"的 all-or-nothing 困境。

3. **与现有代码结构完美对齐。** Lane A 对应当前的 `ShellAdapter.launch()` 路径；Lane B 可以挂在 `RuntimeGateway.resume()` 之上；Lane C/D 则需要一个新的 `LangGraphRuntimePilot` 适配器。**三者互不干扰。**

### 3.2 Borrow / Wrap / Own 框架 — ⭐⭐⭐⭐⭐

v1.0 的"Keep custom vs. Stop self-building vs. Integrate"是正确的方向，但 v1.1 的 Borrow/Wrap/Own 更加精确：

- **Borrow**（直接借用，不封装）：标准 agent loop、persistence、server/IDE
- **Wrap**（薄封装，保持控制）：RuntimeGateway、CapabilitySource、trace export
- **Own**（长期拥有）：run lifecycle、governance、simulation、projections

这个分类的最大价值是给了 **每个技术决策一个明确的"应该做到什么程度"的标尺**。

### 3.3 Trust Tier 体系 — ⭐⭐⭐⭐⭐

```
T0 — built-in local capability (ShellAdapter, NoopAdapter)
T1 — local stdio MCP
T2 — internal managed HTTP MCP
T3 — third-party remote HTTP MCP
M8 默认只批准 T0/T1
```

**这直接解决了此前评估中关于 MCP 安全边界的担忧。** M8 阶段只允许 local stdio MCP，远端 HTTP MCP 不在默认范围内。这意味着 MCP 集成的风险被压到了最低。

### 3.4 Canonical IDs & State Mapping (§7) — ⭐⭐⭐⭐⭐

v1.0 没有这个章节。v1.1 明确定义了 11 个 Canonical ID 类型和 5 条"真相层规则"（product truth / runtime truth / diagnostic visibility / 双写规则 / 回退规则）。

**"双写规则"是关键创新：** "外部 runtime 状态写入不得绕过 repository transition"——这一条规则直接杜绝了此前评估中担心的"LangGraph checkpoint 与 SQLite 不一致"问题。

---

## 4. 此前评估中提出的约束闭合矩阵 (v2)

| # | 约束 | 提出方 | v1.0 状态 | v1.1 状态 |
|---|------|-------|----------|----------|
| 1 | Degradation Policy | Opus | ✅ | ✅ 保持 + 每 Phase 都有回退规则 |
| 2 | TaskKind 刚性 | Opus | ✅ | ✅ §5.4 "不扩枚举" |
| 3 | 双重持久化 | Opus | ✅ | ✅✅ §7.2 双写规则 + 回退规则 |
| 4 | 测试隔离 | Opus | ✅ | ✅✅ §11.2 五种测试类型 + disable-path test |
| 5 | Git checkpoint | 双方 | ✅ 文档要求 | ✅✅ **实际已完成** `03db8b9` |
| 6 | LangGraph 窄范围 | 双方 | ✅ | ✅✅ Lane C/D + Kill Criteria |
| 7 | Phase 排序 | Opus | ✅ | ✅✅ 进一步优化：Trace→Agent→MCP→Observe→Durable→Skills |
| 8 | Router-first MCP | 生态评估 | ✅ | ✅✅ Trust Tier + schema budget |
| 9 | API 兼容策略 | Opus | ⚠️ 未闭合 | ✅ §11.1 "public CLI/API 字段变化必须自带 ADR" |
| 10 | MCP discovery 超时 | Opus | ⚠️ 未闭合 | ✅ §10 Phase 2: `startup_timeout_ms / call_timeout_ms` |
| 11 | Trace 数据隐私 | Opus | ⚠️ 未闭合 | ⚠️ 部分闭合 (`redaction_rules` 在 ToolProjection 中出现，但 trace export 的 redaction 未显式定义) |

**闭合率从 v1.0 的 8/11 提升到 v1.1 的 10/11。** 仅剩 trace export 的 redaction 策略需要在 Phase 0 补充。

---

## 5. 仍需注意的微观问题

### 5.1 ⚠️ `research_spike_reviewable` 不是已有 preset

文档多处引用 `research_spike_reviewable` 作为 durable pilot 的 run class。但当前的 seed presets 只有 4 个：`feature_delivery`, `research_spike`, `advisory_delivery`, `guarded_delivery`。`research_spike_reviewable` 是一个**尚不存在的概念**。GPT Pro 的复审文件（§4.1）也指出了这一点。Phase 0 必须明确是新增 preset 还是使用 `guarded_delivery` 替代。

### 5.2 ⚠️ Phase 1 与 Phase 2 的边界模糊

Phase 1（Borrowed Agent Foundation）需要 `ToolProjectionManifest`，Phase 2（MCP Capability）也需要 `ToolProjectionManifest`。它们是否是同一个抽象？如果是，那 Phase 1 就隐含了 Phase 2 的前置依赖。建议在 Phase 0 的 ADR 中明确 `ToolProjectionManifest` 的归属。

### 5.3 ℹ️ 9 份 ADR 的工作量

Phase 0 要求产出 **9 份 ADR**。按照当前项目 ADR-001 到 ADR-006 的密度（500–2700 字/份），这大约等于 9,000–25,000 字的纯设计文档。这在 Phase 0 的时间窗口内是可行的，但必须有意识地控制每份 ADR 的范围，避免 Phase 0 变成一个"无限文档编写周期"。

---

## 6. 最终评分

| 维度 | v1.0 评分 | v1.1 评分 | 说明 |
|------|----------|----------|------|
| 战略一致性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 保持 |
| 架构精度 | ⭐⭐⭐⭐☆ | **⭐⭐⭐⭐⭐** | ↑ Lane Model + Borrow/Wrap/Own + Trust Tier |
| 约束吸收率 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 保持 (10/11) |
| 风险管理 | ⭐⭐⭐⭐☆ | **⭐⭐⭐⭐⭐** | ↑ Kill Criteria + Phase-level 回退规则 |
| 工程纪律 | ⭐⭐⭐☆☆ | **⭐⭐⭐⭐⭐** | ↑ PR/测试/Promotion 三维纪律 |
| 执行就绪度 | ⭐⭐⭐☆☆ | **⭐⭐⭐⭐⭐** | ↑ Git 已提交 + Feature Flags 已定义 |

---

## 7. 一句话总结

> M8 Phase Plan v1.1 完成了从"方向性规划"到"可强制执行的工程蓝图"的跨越。四条 Lane 模型、Borrow/Wrap/Own 三层分类、T0–T3 信任层级、9 份 ADR 门禁和 Kill Criteria 制度，使得这份文档不仅告诉团队"M8 要做什么"，更精确地定义了"M8 不可以做什么"以及"失败时如何回退"。**此前评估中的唯一硬阻塞（Git 未提交）已经解除。项目可以立即启动 M8 Phase 0。**
