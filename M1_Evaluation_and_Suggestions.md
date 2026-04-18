# Universal Agentic Workflow OS (v2.1) - M1 阶段实现评估报告 (Implementation Review)

**评估人：** Gemini (Antigravity) 
**评估日期：** 2026-04-19
**评估基准：** M1 Phase 实际代码落地 (packages/, apps/, infra/)
**评估结论：** **M1 Phase 实现完美闭环，符合 Local-First 且高度解耦的架构初衷，建议重构部分巨型类后稳步推进 M1.5/M2。**

---

## 1. 总体实现情况摘要 (Current Implementation Status)

经过对代码库和测试结果的深度扫描，M1 阶段的实现在架构纪律和业务完整度上达到了极高水准。当前的测试覆盖率极佳（`pytest` 208项全数通过），且脱机验证（Offline Validation）也已闭环。

**已落地的核心高价值特性：**
* **工作流显式化：** 成功将内部状态升级为显式的 `compile / recompile / resume` 暴露接口。
* **防腐层与隔离墙：** `langgraph` 被极其严格地限制在了 `packages/runtime_langgraph/gateway.py` 中，`core_domain` 和 `contracts` 完美保持了纯 Python/SQLite 的无状态特性。
* **审查策略引擎：** 实现了四种 Review Policy (`auto_only`, `recommended`, `human_required`, `mandatory`)，并能正确触发状态机的转换。
* **持久化能力增强：** `HandoffLite` 已经成功落表，且 Operator TUI 提供了极佳的只读监控体验。
* **技术债偿还：** 成功偿还了 M0 遗留的 TD-002 (`PresetResolver.suggest`)、TD-003 (`HandoffLite` 作用域) 和 TD-004 (Thin compile 占位)。

---

## 2. 存在的风险隐患 (Identified Risks)

尽管系统跑通了，但从代码组织和演进角度来看，存在以下几个不容忽视的风险：

1. **“上帝类”的出现 (God Object Anti-Pattern)：**
   `packages/core_domain/services.py` 中的 `OrchestratorService` 代码量已经超过 3600 行（165KB），承担了状态流转、凭证校验、资源回收、预算审计等几乎所有业务。这是一个非常危险的维护瓶颈，容易导致后续开发出现隐式耦合和合并冲突。
2. **并发控制仍处于“纸面防御”阶段：**
   技术债注册表显示，虽然引入了 `Claim` 和 `Worker-Lease` 的数据结构，但 M1 依然没有强制的并发拦截器（TD-001, TD-009）。如果后续存在多个调度器或终端同时操作同一个 Run，极易引发状态撕裂。
3. **测试过度依赖 Shell 集成：**
   目前的 E2E 验证大量依赖于 `make smoke` 和 `infra.scripts.offline_validation` 脚本。这种重量级的全链路测试在引入真正的 LLM Gateway 时，可能会面临极高的 Flaky（不稳定）风险。

---

## 3. 需要修改的建议 (Refactoring & Modification Suggestions)

在全面进入 M2 前，建议插入一个极短的技术债清理阶段（Refactoring Phase）：

* **重构拆分 OrchestratorService（最高优先级）：**
  必须将 `OrchestratorService` 拆分为职责单一的多个 Service。例如：
  * `RunLifecycleService`: 负责 create, compile, status transition
  * `ReviewGovernanceService`: 负责 evidence, review, policy check
  * `ResourceLeaseService`: 负责 claim 和 worker_lease
  * `TelemetryDiagnosticService`: 负责 event, snapshot, inspection
* **策略硬编码的抽离：**
  目前 Review 策略（如 `recommended` 退化为 `human_required`）的部分逻辑写死在主流程中。建议通过策略模式（Strategy Pattern）将不同 Policy 的处理引擎拆分，以便未来扩展（TD-006）。
* **自动化恢复机制：**
  当前的 `reconcile` 偏向于将异常状态呈现给 Operator，建议针对常见的网络闪断导致的 Lease 过期，提供自动 Retry 和 Repair 的内置 Handler。

---

## 4. 下一步开发方案 (Next Steps: M1.5 & M2)

结合当前的技术债列表，后续路线应当如此规划：

### M1.5：执行器路由完善 (Executor Routing)
* 重点偿还 **TD-005**。
* 让 `OpenCodeAdapter` 与 `ShellAdapter` 并行工作，跑通真正的 `WorkerRouter` 动态分发。这是引入复杂多模态 Agent 的基础。

### M2：并发控制与断点恢复 (Concurrency & Resumability)
* 重点偿还 **TD-001, TD-008, TD-009**。
* 强制执行 `Claim / Lease / Barrier`。确保同一个 RuntimeTask 在同一个时间分片内只有唯一的 Executor 在跑。
* 实现完整的 `interrupt / resume / checkpoint merge` 闭环。

### M3：深度观测与控制台 (Observability & UI)
* 偿还 **TD-007, TD-010**。
* 丰富 Event 的 Payload，提供完整的 Trace ID 与 Metrics。
* 开发可视化的 Web Dashboard 取代当前的 Terminal TUI。

---

## 5. 其他没想到的点 (Other Insights & Blind Spots)

1. **上下文爆炸与修剪 (Context Pruning Strategy)：**
   随着 `memory_items` 和长生命周期 Run 的增加，在恢复（Resume）时发送给 LLM Gateway 的状态上下文（Payload/Prompt）会迅速膨胀并触及 Token 限制。目前系统里缺乏明确的 **“记忆遗忘/修剪策略”**（Memory Summarization/Eviction），建议在 M2 加入相关能力。
2. **Schema 迁移的脆弱性：**
   随着状态表越来越复杂，如果 SQLite 的 Migration 依然靠纯手工编写 SQL，极易出现 Schema Drift。建议考虑引入轻量级的 ORM 迁移工具（如 Alembic，虽然保持模型轻量，但 Schema 管理可以工具化）以提升容错率。
3. **离线与在线状态的平滑降级：**
   目前的网络感知大多停留在离线探针（Offline Probe）。如果 LLM 请求在中途挂起超过 5 分钟，系统的断网降级体验还比较生硬。建议引入一个全局的 `Circuit Breaker`（熔断器），在 Gateway 连续超时后主动挂起任务，避免耗尽重试预算（Budget Ledger）。
