# Universal Agentic Workflow OS (v2.1) - M7 阶段全盘评估报告 (Implementation Review)

**评估人：** Gemini (Antigravity)
**评估日期：** 2026-04-19
**评估基准：** M7 阶段全景代码落地 (涵盖 `core_domain`, `contracts`, `simulation`, `memory` 等核心子域)
**评估结论：** **项目已成功完成 M7 (Simulation Lifecycle Hook Baseline) 闭环。从 M0 到 M7 的高速演进中，架构始终坚守了 Local-First 与高度防腐的纪律，展现了卓越的工程控制力。然而，业务体量的极速膨胀也使得核心 Service 成为巨大的维护瓶颈，建议在下一阶段（M8）强制安排架构重构。**

---

## 1. 目前的实现情况 (Current Implementation Status)

系统已经远超早期（M1）的简单运行主链，真正演化成了一个功能完备的 Agentic OS 基座。
`pytest` 208项测试全量通过，且 Offline Validation（脱机验证）完美闭环，这在如此复杂的系统迭代中非常难得。

**已落地的核心高价值特性 (跨越 M1-M7)：**
1. **严格的架构防腐：** `langgraph` 被极严格地隔离在 `runtime_langgraph/gateway.py`，核心域（`core_domain`）与契约层（`contracts`）保持了绝对的 Python/SQLite 纯净度。
2. **运行时与执行策略成熟：** 具备完整的 `Compile / Recompile / Resume` 状态机，以及多重审查策略 (`auto_only`, `recommended`, `human_required`, `mandatory`)。
3. **能力与领域路由 (Domain & Capability)：** 实现了基于 `ShellAdapter`, `OpenCodeAdapter`, `NoopAdapter` 的能力路由分发，以及平台化的 Domain Packs。
4. **记忆与上下文管理 (Memory)：** M5/M6 阶段引入的 `memory_candidates`, `memory_items` 以及 `retrieval-preview` 构建了完整的长效上下文召回体系。
5. **本地确定性模拟 (Simulation - M7 新增)：** 刚刚完成的 M7 阶段，成功落地了 Simulation Policy Catalog、本地确定性沙盒报告、持久化的 Simulation History 以及生命周期钩子的自动记录。
6. **治理与修复 (Governance)：** `tech-debt`, `release-readiness`, `reconcile` 等接口为 Operator 提供了极强的白盒诊断和运维手段。

---

## 2. 存在的风险隐患 (Identified Risks)

尽管业务逻辑跑通，但由于 M1 到 M7 的极速狂奔，系统在代码组织和技术债管理上积压了严重风险：

1. **“上帝类”的绝对瓶颈 (God Object Anti-Pattern)：**
   `packages/core_domain/services.py` 中的 `OrchestratorService` 已经膨胀到 **3600 余行 (165KB)**！它现在同时负责执行流转、审查治理、预算管理、领域包解析、记忆管理、模拟运行（Simulation）等所有业务逻辑。这种极度中心化的代码组织是当前项目**最大的定时炸弹**，合并冲突和隐式逻辑耦合的风险极高。
2. **技术债登记簿的停滞 (Registry Stagnation)：**
   `docs/tech-debt-registry.md` 依然停留在早期的 `# M1 技术债登记簿` 语境下。M2-M7 引入的新债（如 Memory 和 Simulation 的边缘 Case）并未被系统化登记，且许多遗留债（TD-006, TD-007, TD-008 等）长期处于“部分偿还”的含糊状态。
3. **大规模上下文爆炸的隐患 (Context Window Overflow)：**
   当前的 Memory 和 Simulation 逻辑在本地跑得非常完美，但当真正接入云端大模型（如 OpenAI Gateway）并面临海量长周期运行任务时，`MemoryRetrievalPreview` 极易导致 Token 触顶。系统目前缺乏硬性的 **上下文修剪与遗忘机制 (Context Pruning/Eviction Engine)**。
4. **并发防御依然脆弱：**
   `Claim` 和 `Worker-Lease` 已存在，但真正的分布式安全并发与隔离依然是基于单机 SQLite 的轻量守卫，还未接受过高并发请求的实战检验。

---

## 3. 需要修改的建议 (Refactoring & Modification Suggestions)

在开启任何新的业务线（M8/M9）之前，**必须**执行一次专注的 Refactoring 阶段：

1. **肢解 `OrchestratorService` (最高优先级)：**
   依照领域驱动设计 (DDD)，将 3600 行的服务按领域拆分：
   - `ExecutionService`: 专职 run, compile, resume, claim
   - `MemoryGovernanceService`: 专职 memory items, namespaces, retrieval
   - `SimulationAuditService`: 专职 simulation policy, reports, records
   - `ReviewAndPolicyService`: 专职 review verdicts, handoffs, auto_review
2. **重塑技术债管理闭环：**
   将 `tech-debt-registry.md` 升级为无版本绑定的全局《架构治理登记簿》。清退已完成的历史条目，并将长期“部分偿还”的条目（如深度的 Trace/Metrics）拆分为可执行的具体卡片。
3. **引入 Token Budget Manager：**
   在生成 Execution Brief 前，增加一个轻量的拦截器，用于计算即将发给 LLM Gateway 的 Payload Token 预估值，如果超载则强制截断或要求 Operator 确认。

---

## 4. 下一步开发方案 (Next Steps: M8 & Beyond)

结合 M7 阶段刚刚闭环的 `Simulation Lifecycle Hooks`，未来的方向应该从“功能堆叠”转向“深度观测与扩展”：

### M8：架构瘦身与深度可观测性 (Refactoring & Observability)
* 强制落地 `OrchestratorService` 拆分。
* 正式偿还 **TD-007**：引入详尽的 Trace ID 体系和 Metrics 采集，让 `run_events` 不仅是文字记录，而是能导入到 Jaeger/Prometheus 或结构化日志系统中的诊断数据。

### M9：Web 控制台与分布式进阶 (Dashboard & Scale)
* 偿还 **TD-010**：开发可视化的 Web Dashboard（如基于 React/Vue + FastAPI），取代当前的 Terminal TUI，彻底释放审查和监控的用户体验。
* 进一步硬化并发逻辑（Barrier），从 SQLite 本地防守过渡到可支持外部 Worker 节点池的调度模型。

### M10：高级模拟扩展 (Advanced Simulation)
* 将 M7 规划中被 explicitly deferred 的项目（Browser/Mobile Agent 外部模拟回放、队列调度机制等）提上日程，将 Agent OS 从内部工作流彻底推向外部环境互动。

---

**最终建议：** 团队目前的研发纪律极强（Task Card 驱动），请将“拆分 Service”和“重整技术债”直接写成具体的 Task Cards，作为开启 M8 的第一个强制性 Gate。
