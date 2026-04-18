# Universal Agentic Workflow OS — M7 全盘深度评估报告

**评估人：** Claude Opus 4.6 (Thinking)  
**评估日期：** 2026-04-19  
**评估范围：** M0–M7 全量代码、文档、测试、基础设施、架构演进  
**评估结论：** 见第 8 节

---

## 1. 里程碑演进全景 (Milestone Evolution Overview)

项目从 M0 到 M7 共经历了 **8 个正式里程碑**，每个里程碑都严格遵循了 "Phase 0 冻结 → Task Card 驱动开发 → Phase Gate Review → Freeze Review" 的纪律循环。以下是各阶段的核心交付物：

| 里程碑 | 核心主题 | Phases | 关键交付物 |
|--------|---------|--------|-----------|
| **M0** | Bootstrap Spine | 6 phases | SQLite 持久化、CLI、API、ShellAdapter、auto_review、offline validation |
| **M1** | Resumable Main Chain | 6 phases | `compile/recompile/resume` 显式生命周期、`HandoffLite` 持久化、`PresetResolver.suggest()`、`human_required` 闭环、UoW 事务 |
| **M2** | Concurrency Primitives | 6 phases | `RuntimeClaim`、`RunSnapshot`、`BudgetLedger`、`WorkerLease`、`RuntimeAttempt` 生命周期、`reconcile` 修复 |
| **M3** | Observability & Governance | 5 phases | Failure Taxonomy、Event Inspection、Closure Audit、`run audit-report`、`tech-debt` / `review-policy` / `release-readiness` 治理报告 |
| **M4** | Review Policy Runtime & Domain Packs | 4 phases | `recommended` / `mandatory` run-level runtime 语义、`CapabilityRegistry`、`software_delivery_pack`、Golden Demo、Release Readiness |
| **M5** | Live LLM Gateway & Operator TUI | 3 phases (scoped) | `OpenAIRuntimeGateway`、`runtime_brief`、`NullRuntimeGateway` 降级、Operator TUI、CLI-first 架构修正（含 `OpenCodeAdapter`） |
| **M6** | Domain Pack Platformization & Memory | 7 phases | Domain Pack 平台化四段（match/capability/compile/runtime）、Memory Namespace Catalog、`MemoryCandidate` / `MemoryItem` 持久化、`retrieval-preview`、compile-time memory brief injection |
| **M7** | Simulation Lifecycle Baseline | 4 phases | `SimulationPolicyRegistry`、`LocalDeterministicSimulationRunner`、`SimulationRecord` 持久化、lifecycle hook 自动记录 |

**总 Task Card 文件数：** 43 个 task card markdown + 33 个独立 task 子目录  
**总 Phase Review 文件数：** 25 份 freeze review / phase review  
**总 Migration 数：** 9 个 SQL migration 文件 (001–009)  
**总 Seed 文件数：** 4 (presets, domain_packs, memory_namespaces, simulation_policies)

---

## 2. 代码库结构与规模 (Codebase Structure & Scale)

### 2.1 目录结构

```
packages/
├── contracts/          # 纯 Pydantic 契约层（models, events, runtime ABC）
│   ├── __init__.py     (123 行, 2.8KB — 统一 re-export)
│   ├── models.py       (423 行, 12.8KB — 28 个契约对象)
│   ├── events.py       (274 行, 7.3KB — 27 种事件类型 + payload 校验)
│   └── runtime.py      (224 行, 7.5KB — RuntimeGateway ABC, Claim, Lease, Attempt, Snapshot)
├── core_domain/        # 业务逻辑层
│   ├── services.py     (3624 行, 165KB — OrchestratorService ⚠️)
│   ├── repositories.py (1200 行, 51.6KB — 16 个 Repository)
│   ├── governance.py   (418 行, 17.5KB — tech-debt / review-policy / release-readiness)
│   ├── compile.py      (219 行, 9.2KB — CompileSnapshot builder)
│   ├── simulation.py   (184 行, 8.4KB — SimulationPolicyRegistry + runner)
│   ├── domain_packs.py (7.9KB)
│   ├── errors.py       (156 行 — 12 种结构化错误)
│   └── ...
├── runtime_langgraph/  # LLM Gateway 防腐层
│   └── gateway.py      (204 行 — NullRuntimeGateway + OpenAIRuntimeGateway)
└── worker_adapters/    # 执行器适配层
    ├── router.py       (64 行 — WorkerRouter)
    ├── capability_registry.py
    ├── shell_adapter.py
    ├── opencode_adapter.py
    └── noop_adapter.py

apps/
├── operator_cli/main.py    (23.3KB — 完整 CLI 入口)
├── orchestrator_api/main.py (13.2KB — FastAPI 路由)
└── operator_tui/dashboard.py (4.8KB — Rich 终端仪表盘)

infra/
├── migrations/ (9 个 SQL 文件)
├── seeds/      (4 个 JSON 种子文件)
└── scripts/    (manage.py 17.6KB, offline_validation.py 86.3KB)

tests/ (8 个测试文件, 208 个测试用例)
```

### 2.2 关键数字

| 指标 | 数值 |
|------|------|
| 契约对象（Pydantic models） | 28 |
| 事件类型（RunEventType） | 27 |
| Repository 类 | 16 |
| SQL Migration 文件 | 9 |
| 错误类型 | 12 |
| CLI 命令数 | ~40 |
| API 路由数 | 36 |
| pytest 通过数 | **208** |
| Offline Validation | **overall_passed=true** |
| Seed Presets | 4 (feature_delivery, research_spike, advisory_delivery, guarded_delivery) |
| Review Policies (runtime) | 4 (auto_only, recommended, human_required, mandatory) |
| Worker Adapters | 3 (ShellAdapter, OpenCodeAdapter, NoopAdapter) |
| Domain Packs | 1 (software_delivery_pack) |

---

## 3. 架构优势评估 (Architectural Strengths)

### 3.1 防腐层纪律（Anti-Corruption Layer Discipline）— 极优

这是整个项目最值得称道的设计决策。经过代码级验证：

- `packages/contracts/` 和 `packages/core_domain/` **零 langgraph import**
- `RuntimeGateway` 作为纯 Python ABC 定义在 `contracts/runtime.py` 中
- 唯一的 LangGraph/OpenAI 依赖被限制在 `runtime_langgraph/gateway.py`（204 行）
- `build_runtime_gateway_from_env()` 的 fallback 默认是 `NullRuntimeGateway`，确保全链路在无 LLM 环境下可通过
- Smoke 测试主动清除 LLM API Key 环境变量后再执行

**结论：这是极少见的在 Agent 系统中能做到如此干净的 LLM 隔离的项目。**

### 3.2 状态机形式化 — 优秀

`RUN_STATUS_TRANSITIONS` 以 `frozenset` 字典的形式硬编码了合法状态转换：

```
pending → {prepared, cancelled}
prepared → {prepared, running, cancelled}
running → {awaiting_review, completed, failed}
awaiting_review → {completed, failed, cancelled}
completed → {completed}  (幂等)
failed → {failed}         (幂等)
cancelled → {cancelled}   (幂等)
```

所有状态转换都通过 `_transition_run_status()` 统一守卫，非法转换抛出 `InvalidStateTransitionError(409)`。

### 3.3 契约层设计 — 优秀

- 使用 `PersistedContractModel` 统一 `schema_version` 和 `created_at`
- 所有 ID 采用 `{prefix}_{uuid_hex[:12]}` 格式，可读且可 grep
- `model_validator` 用于强制生命周期不变量（如 active claim 不可有 released_at）
- Event Payload 采用 `extra="forbid"` 严格模式校验

### 3.4 Unit of Work 事务保护 — 良好

`db.py` 中的 `unit_of_work` context manager 正确实现了 `commit/rollback` 语义。Repository 层支持注入 `connection` 参数，允许在同一个事务中执行多步写入。

### 3.5 研发纪律与文档治理 — 极优

- **25 份 Phase Review** 文件形成了完整的决策审计链
- **M5 Closeout** 文档展示了极其成熟的范围漂移自检能力（主动识别 Phase 3 超出冻结范围并回拉）
- Task Card 粒度下探到了函数/路由/表/测试文件级别
- 每个里程碑都有独立的 freeze review 给出明确 go/no-go 结论

---

## 4. 风险与问题识别 (Risks & Issues)

### 4.1 🔴 P0 — OrchestratorService 膨胀（God Object）

`services.py` 达到 **3624 行 / 165KB**，是整个项目单文件最大的代码。它同时承载了：

- 运行生命周期管理（create, compile, recompile, resume, cancel, approve, reject）
- 资源管理（claim 获取/释放、worker lease 获取/释放）
- 运行时尝试管理（runtime attempt 创建/超越/关闭）
- 诊断检查（inspection 问题检测 + 11 种 repair action）
- 失败分类（failure taxonomy）
- 模拟运行（simulation report / record / lifecycle hook）
- 记忆管理（memory candidates / materialization / retrieval preview）
- 状态投影（status-detail, summary, event-inspection, audit-report）
- 预算管理（budget ledger）
- 快照管理（run snapshots）
- TUI 仪表盘数据组装

**影响：**
- 极高的认知负荷：新开发者理解单个方法需要先理解整个 3600 行文件的上下文
- 合并冲突风险：任何两个并行的 feature 改动几乎必然冲突
- 测试脆弱性：测试覆盖了 208 个用例，但全部打在同一个类上，任何 internal 重构都会引发大面积回归

### 4.2 🟡 P1 — 技术债登记簿过时

`docs/tech-debt-registry.md` 标题仍为 "M1 技术债登记簿"，内容停留在 M1 视角：
- 已偿还的 TD-002/003/004 仍在文件中（正确，作为历史记录）
- 但 M2–M7 期间引入的新债（如 Simulation 边界 case、Memory 上下文膨胀、Domain Pack 仅一个 family）**完全没有登记**
- TD-005 标注为 "已偿还"，但 "计划偿还阶段" 写的是 M1.5，实际 `OpenCodeAdapter` 是在 M5 Phase 3 引入的

### 4.3 🟡 P1 — Offline Validation 脚本体量过大

`infra/scripts/offline_validation.py` 达到 **86.3KB**，是整个项目第二大的单文件。作为脚本而非业务逻辑，这个体量表明验证逻辑可能存在大量重复或者应该被拆分为模块化的 test fixtures。

### 4.4 🟡 P1 — 依赖版本锁定过窄

`pyproject.toml` 中的依赖锁定：
```
fastapi>=0.135.2,<0.136.0
pydantic>=2.12.5,<2.13.0
typer>=0.9.0,<0.10.0
uvicorn>=0.34.0,<0.35.0
```
次版本号锁死意味着任何安全更新都需要手动调整上限。对于一个尚在快速迭代的项目，这过于保守。

### 4.5 🟢 P2 — 仅有一个 Domain Pack Family

当前仅有 `software_delivery_pack`。虽然 M6 已经做了平台化四段拆分（match / capability / compile / runtime），但生态丰富度不足。不过这是有意为之的范围控制，不算真正的缺陷。

### 4.6 🟢 P2 — 并发仅为本地守卫

`Claim` 和 `WorkerLease` 语义为单机 SQLite 级别，不支持跨进程或分布式场景。README 中已明确声明这一限制，技术债登记簿也有记录。

---

## 5. 测试与验证评估 (Testing & Validation)

### 5.1 测试覆盖

| 测试文件 | 大小 | 关注领域 |
|----------|------|---------|
| test_execution_loop.py | 76KB | 核心执行主链、编译、恢复、审查策略、Domain Pack、Memory、Simulation、Reconcile、Claim/Lease |
| test_cli.py | 50.8KB | CLI 全命令覆盖 |
| test_api.py | 49.2KB | API 全路由覆盖 |
| test_repositories.py | 22KB | Repository round-trip、Migration、Reset |
| test_contracts.py | 20.1KB | 契约对象序列化、状态机、事件 payload 校验 |
| test_governance.py | 6.9KB | 治理报告生成 |
| test_runtime_boundary.py | 2.8KB | 防腐层 import 隔离守卫 |
| test_release_closeout.py | 1.6KB | 黄金 Demo 包验证 |

**亮点：**
- `test_runtime_boundary.py` 中有一个 `test_contracts_and_core_domain_do_not_import_langgraph` 测试，用 AST 解析强制保证防腐层不被打破 — 这是极其优秀的架构守卫测试
- 208 个测试全部在 ~76 秒内完成
- Offline Validation 包含 CLI/API 双路径、多 Review Policy 路径的全链路验证

**不足：**
- 没有性能 / 压力测试（不阻塞当前阶段，但分布式前需要）
- 没有 property-based testing（如 Hypothesis），对状态机的边界组合覆盖依赖手写用例

### 5.2 验证链完整性

```
pytest -q → 208 passed
offline_validation --skip-offline-probe → overall_passed=true
manage demo → status=completed
tui --once → renders successfully
```

四层验证形成了从单元到系统的完整链条。

---

## 6. 需要修改的建议 (Modification Suggestions)

按优先级排列：

### 6.1 🔴 拆分 OrchestratorService

这是 **M8 的第一优先级**。建议拆分方案：

| 新 Service | 职责 | 预估行数 |
|-----------|------|---------|
| `RunLifecycleService` | create, compile, recompile, resume, cancel, approve, reject, status transitions | ~800 |
| `InspectionRepairService` | inspection problem detection, reconcile, 11 种 repair actions | ~400 |
| `ProjectionService` | status-detail, summary, event-inspection, audit-report, timeline | ~600 |
| `SimulationService` | simulation report, record, lifecycle hook | ~300 |
| `MemoryService` | memory candidates, materialization, retrieval preview, compile-time injection | ~300 |
| `ResourceLeaseService` | claim, worker lease, budget ledger 的获取/释放/过期处理 | ~400 |

拆分原则：
- 所有 Service 共享相同的 Repository 实例集合（通过组合注入）
- 拆分是 **纯移动性的**（move-only），不改变任何行为
- 拆分后每个 Service 的公共方法名保持不变，API/CLI 层的调用点从 `svc.xxx()` 变为 `svc.run_lifecycle.xxx()` 或类似
- 拆分必须在 **零测试失败** 的约束下完成

### 6.2 🟡 刷新技术债登记簿

将标题从 "M1 技术债登记簿" 改为 "技术债登记簿"，并补充 M2–M7 引入的实际债务：

- M5: `OpenCodeAdapter` 缺少真实 CLI 工具集成测试
- M6: Memory Retrieval 缺乏上下文修剪策略
- M6: Domain Pack 仅一个 family，平台化模式验证不充分
- M7: Simulation 仅覆盖本地确定性检查，不支持外部模拟后端
- 跨里程碑：OrchestratorService 膨胀（新增 TD-011）

### 6.3 🟡 放宽依赖版本约束

将 `pyproject.toml` 中的次版本上限放宽为主版本约束：

```diff
-  "fastapi>=0.135.2,<0.136.0",
+  "fastapi>=0.135.2,<1.0.0",
-  "pydantic>=2.12.5,<2.13.0",
+  "pydantic>=2.12.5,<3.0.0",
```

### 6.4 🟢 拆分 offline_validation.py

将 86KB 的验证脚本按路径类型拆分为模块：
- `validation/cli_flows.py`
- `validation/api_flows.py`
- `validation/smoke_flows.py`
- `validation/runner.py`

---

## 7. 下一步开发方案 (Next Steps)

### M8（建议主题：Architecture Refactoring & Debt Clearance）

**范围冻结建议：**
1. OrchestratorService 拆分（上述 6.1 方案）
2. 技术债登记簿全面刷新
3. 引入 Token Budget / Context Pruning 的 ADR（设计文档，不必实现）
4. 补充 M2–M7 期间遗漏的 seed 更新（如新的 simulation policy、memory namespace）

**不纳入 M8：**
- 新的 Domain Pack family
- Web Dashboard
- 分布式并发
- 新的 Worker Adapter

### M9（建议主题：Memory Depth & Context Management）

- Memory Retrieval 引入硬性的 Token 限额与修剪策略
- Memory Namespace 扩展（从 seed 到可配置）
- Compile-time Memory Brief 支持多轮召回

### M10（建议主题：Simulation Expansion & External Integration）

- 非确定性模拟后端（Browser, API call 模拟）
- Compile-time / per-step simulation hooks
- 模拟触发矩阵扩展

---

## 8. 最终评估结论 (Final Verdict)

### 总体评价

| 维度 | 评级 | 说明 |
|------|------|------|
| 架构纪律 | ⭐⭐⭐⭐⭐ | LLM 防腐层、状态机形式化、契约层设计均属业界顶级水准 |
| 研发流程 | ⭐⭐⭐⭐⭐ | Task Card 驱动、Phase Gate Review、Freeze Review、范围漂移自检 — 极其成熟的工程纪律 |
| 功能完备度 | ⭐⭐⭐⭐☆ | 核心主链完整，但 Domain Pack 生态和 Memory 深度仍处于早期 |
| 测试覆盖 | ⭐⭐⭐⭐☆ | 208 个用例 + 四层验证链 + 防腐层 AST 守卫，但缺少性能测试和 property-based testing |
| 代码可维护性 | ⭐⭐⭐☆☆ | **OrchestratorService 的 3624 行是当前最大的结构性风险**，必须在 M8 拆分 |
| 文档治理 | ⭐⭐⭐⭐☆ | 25 份 review + 43 份 task card 是极佳的决策审计链，但技术债登记簿需要刷新 |

### 一句话总结

> 这是一个在架构纪律和研发流程上达到了**极高工程水准**的 Agentic OS 基座，它的最大威胁不是功能缺失，而是核心 Service 的巨型化——修复这一结构性问题应当是下一阶段的首要任务。

---

## 9. 附录：你可能没想到的点 (Blind Spots)

1. **事件回放能力为零。** 当前的 `run_events` 表只记录了 27 种事件的摘要 payload，但没有任何机制可以从事件流重建 Run 状态。如果未来要做审计或 debugging，需要考虑 Event Sourcing 或至少增加 snapshot-at-event 的投影能力。

2. **SQLite WAL 模式下的并发写限制。** 当前的 `PRAGMA journal_mode = WAL` 允许并发读，但写入仍然是序列化的。如果未来引入多 Worker 写同一个 DB 文件的场景，WAL 的写锁会成为瓶颈。这与 TD-001/009 的分布式方向有交叉。

3. **OpenAI Gateway 的 `responses.create` API 用法。** `gateway.py` 使用的是 `self._client.responses.create()`（而非 `chat.completions.create()`），这依赖 OpenAI SDK 的较新 Responses API。如果用户使用旧版 SDK 或兼容 API（如 Azure OpenAI），这个 surface 会直接报错。建议增加 SDK 版本检测或 fallback。

4. **CLI 入口点 `workflowctl` 依赖 `pip install -e .`。** 如果用户通过 `python -m apps.operator_cli.main` 运行但没有安装包，`workflowctl` 命令不可用。这两种入口的行为一致性目前靠文档保证，建议考虑统一。

5. **Artifact 文件路径硬编码。** `compile.py` 中的 `_artifact_path_for()` 硬编码了 `state/artifacts/` 路径前缀。如果有需要部署到非标准目录的场景（如容器化），这会成为阻碍。

6. **没有任何日志框架。** 整个项目不使用 `logging` 模块。所有诊断信息依赖 `print` 或结构化返回值。对于生产环境或长时间运行的场景，缺少可配置的日志级别和输出目标。
