# Universal Agentic Workflow OS — 深度评估报告与开发建议

> **评估时间**: 2026-04-21  
> **评估基线**: M30 Operator Control Freeze  
> **上一次评估基线**: M20 Freeze Review (`v1 core complete`)  
> **评估模型**: Claude Opus 4.6 (Thinking)  
> **测试结果**: 273 passed / 0 failed (pytest -q, 361.56s)

---

## 一、项目总览

Universal Agentic Workflow OS 是一个 **本地优先（local-first）** 的智能体工作流运行时系统。它以 SQLite 为唯一持久化层，通过严格的生命周期状态机驱动 `create → compile → resume → review → terminal` 执行流程，支持多适配器路由、多控制面调度权威、以及完整的治理/审计/仿真体系。

自上次 M20 评估以来，项目完成了 **M21 至 M30 共 10 个里程碑**，重点从"v1 core complete"基线向操作员控制收敛和自然语言规划能力推进。

### 核心定位

| 维度 | 描述 |
|------|------|
| **架构范式** | 本地优先 + SQLite 单数据库 + 确定性运行时图（RuntimeGraph） |
| **执行模型** | shell / opencode / opencode_session / noop / agent（opt-in）五适配器路由 |
| **治理模型** | 5 种审查策略 × 量化治理指标 × 自动化告警 × 发布就绪门控 × 能力策略预览 |
| **调度模型** | 多数仲裁调度器权威对等 + 跨控制面租约提交 + 围栏令牌回调验证 |
| **协作模型** | CLI + API + TUI + Web UI 四入口 + 远程 HTTP Worker 池 |
| **规划模型** | 自然语言目标 → preset 建议 → plan graph → policy preview → goal packet → launch |

### 代码规模

| 指标 | M20 基线 | M30 当前 | 变化 |
|------|---------|---------|------|
| Python 源文件（packages + apps） | ~50 | 51 | +1 |
| 源代码总量 | ~800 KB | ~826 KB | +26 KB |
| 测试文件 | 12 | 12 | — |
| 测试代码总量 | ~290 KB | ~335 KB | +45 KB |
| 测试用例 | 264 | 273 | +9 |
| Git 提交 | 11 | 12 | +1 |
| 里程碑 | M0 → M20 | M0 → M30 | +10 |
| 契约类型 | 40+ | 50+ | +10 |
| 增量迁移文件 | 14 | 14 | — |
| 冻结评审 | 1 | 4 | +3 |

### M21-M30 里程碑摘要

| 里程碑 | 主题 | 关键产出 |
|--------|------|----------|
| M21 | 重基线与扩张冻结 | `workflowctl db migrate` / `migration-status`、`ResultEnvelope v1`、compile/recompile 去重 |
| M22 | 能力描述符 | `CapabilityDescriptor` / `CapabilityHealth` 读模型、CLI/API 表面 |
| M23 | 会话式外部代理通道 | `opencode_session` 适配器、session refs 投影 |
| M24 | 编排计划图 | `OrchestrationPlanGraph` / `OrchestrationGraphNode` 契约、编译时图规划 |
| M25 | 自然语言启动 | `launch` / `plan-graph` CLI/API 表面、单目标入口 |
| M26 | 能力策略预览 | policy preview 操作员表面、适配器覆盖修复 |
| M27 | 操作员包标准化 | `get_run_operator_packet()` 紧凑读模型 |
| M28 | 目标包与受控启动预览 | `preview_goal_packet()`、goal packet CLI/API |
| M29 | 仪表盘操作员收敛 | dashboard snapshot 嵌入 focus_operator_packet |
| M30 | 操作员控制冻结 | 冻结评审、活文档更新至 M30 基线 |

---

## 二、架构评估

### 2.1 分层结构

```
┌──────────────────────────────────────────────────────────┐
│                        apps/                              │
│   operator_cli (37 KB)  │  orchestrator_api (32 KB)       │
│   operator_tui (5 KB)   │  web_ui (23 KB)                 │
│   remote_worker_api     │  scheduler_authority_api         │
├──────────────────────────────────────────────────────────┤
│                    packages/core_domain/                   │
│   OrchestratorService (Facade, 166 KB)                    │
│     ├── LifecycleServiceMixin      (70 KB)                │
│     ├── ProjectionServiceMixin     (70 KB)                │
│     ├── MemorySimulationServiceMixin (33 KB)              │
│   repositories.py (64 KB)  │  scheduler_authority.py (45 KB)│
│   governance.py (35 KB)    │  capability_plane.py (21 KB)  │
│   config.py (21 KB)        │  compile.py (12 KB)           │
├──────────────────────────────────────────────────────────┤
│               packages/contracts/                         │
│   models.py (28 KB)  │  events.py (9 KB)  │  runtime.py (8 KB) │
├──────────────────────────────────────────────────────────┤
│        packages/worker_adapters/  │ packages/runtime_langgraph/ │
│   ShellAdapter  OpenCodeAdapter   │   DurablePilot  Gateway    │
│   NoopAdapter   LangChainAgent    │                            │
│   OpenCodeSessionAdapter          │                            │
├──────────────────────────────────────────────────────────┤
│                     infra/                                 │
│   seeds/  │  migrations/ (14)  │  scripts/  │  validation/ │
├──────────────────────────────────────────────────────────┤
│                     state/                                 │
│   workflow.db  │  artifacts/  │  durable/                  │
└──────────────────────────────────────────────────────────┘
```

### 2.2 架构优势

1. **严格的契约边界**：`packages/contracts/` 现在定义了 50+ 契约类型（较 M20 的 40+ 增长 25%），新增 `CapabilityDescriptor`、`CapabilityHealth`、`OrchestrationPlanGraph`、`OrchestrationGraphNode`、`ResultEnvelope`、`ExternalSessionRef` 等，每一个新领域概念都走了正式契约化路线。

2. **确定性状态机**：`RUN_STATUS_TRANSITIONS` 未变，核心状态机保持稳定，这是架构纪律的体现。

3. **本地优先设计一致性**：SQLite 仍为唯一真相源，`unit_of_work()` 事务隔离不变。M21 新增的 `migrate()` / `get_migration_status()` 使增量迁移从"目录存在但无入口"变为产品化操作。

4. **治理自动化进一步深化**：M26 新增的 capability policy preview 使操作员在执行前即可预览能力选择、策略模式、副作用等级。这是从"事后审计"向"事前审查"的重要演进。

5. **自然语言规划链路初步成型**：`suggest-presets → plan-graph → policy-preview → goal-packet → launch` 形成了从自然语言目标到受控执行的完整后端入口链路，虽然前端交互面尚未跟进。

6. **操作员读模型收敛**：M27-M29 通过 operator packet 和 goal packet 标准化，将原先分散在多个 ad hoc 载荷中的操作员状态收口为统一紧凑的读模型，减少了消费端的组装负担。

### 2.3 架构风险

> [!WARNING]
> **services.py 继续膨胀（3,533 行 → 3,751 行 / 163 KB → 166 KB）**

services.py 在 M21-M30 中继续增长了 ~218 行 / ~3 KB。增量主要来自 operator packet、goal packet、policy preview、plan graph 等新投影方法。虽然每个方法本身是合理的，但持续向同一个文件追加的模式没有改变。

**风险等级**: 中高。services.py 现在的方法数已经远超 Mixin 拆分前的水平，新增方法继续走 Mixin → services.py 的路径只是把膨胀分散在了几个文件里，但 OrchestratorService 作为组合入口的负担持续加重。

> [!WARNING]
> **MCP 导入期耦合未解决**

`capability_plane.py` 在模块顶层直接 `from mcp.client.session import ClientSession`，这意味着即使用户不需要 MCP 功能，`mcp` 包也必须安装且在导入时加载。GPT Pro 评估中提到的"可选能力耦合风险"在 M21-M30 中未被处理。

---

## 三、各模块深度评估

### 3.1 契约层 (packages/contracts/)

| 评估项 | 评分 | 说明 |
|--------|------|------|
| 类型完备性 | ⭐⭐⭐⭐⭐ | 50+ 契约类型，M21-M30 新增 `CapabilityDescriptor`、`CapabilityHealth`、`OrchestrationPlanGraph`、`OrchestrationGraphNode`、`ResultEnvelope`、`ExternalSessionRef` 等 |
| 向后兼容 | ⭐⭐⭐⭐ | `DomainPackDefinition._upgrade_flat_shape` 模式保持，新契约均 additive |
| 类型安全 | ⭐⭐⭐⭐ | Pydantic v2 + `model_validator`，`ResultEnvelope` 内置 `sync_result_envelope` 双向同步 |
| 文档覆盖 | ⭐⭐⭐ | 模型自文档化，但仍缺少显式 docstring |

**M20→M30 变化**: `models.py` 从 24 KB 增长至 28 KB，新增 `OrchestrationPlanGraph`（计划图）和 `ResultEnvelope`（统一结果对象）是最重要的契约演进。

### 3.2 核心领域 (packages/core_domain/)

| 模块 | 体量 | M20→M30 变化 | 评估 |
|------|------|-------------|------|
| `services.py` | 166 KB / 3,751 行 | +3 KB / +218 行 | Facade 持续膨胀，新增 operator packet / goal packet / policy preview 方法 |
| `service_lifecycle.py` | 70 KB | 基本稳定 | compile/recompile 已去重，prepared-run 持久化路径合并 |
| `service_projection.py` | 70 KB | +8 KB | 增长最显著，新增 plan graph、operator packet、goal packet、dashboard convergence 投影 |
| `service_memory_simulation.py` | 33 KB | 稳定 | 记忆与仿真逻辑独立 |
| `repositories.py` | 64 KB | 稳定 | 16 个仓储类保持不变 |
| `scheduler_authority.py` | 45 KB | 稳定 | 共识协议无重大改动 |
| `governance.py` | 35 KB | 稳定 | 治理报告生成健壮 |
| `capability_plane.py` | 21 KB | **新增**（M22） | 形式化 CapabilityDescriptor/Health，统一能力源发现 |
| `config.py` | 21 KB | 稳定 | TOML + env + 显式覆盖 |
| `db.py` | 6.5 KB | **重要增强** | 新增 `migrate()` / `get_migration_status()`，增量迁移产品化 |

### 3.3 适配器层 (packages/worker_adapters/)

| 适配器 | 状态 | M20→M30 变化 |
|--------|------|-------------|
| `ShellAdapter` | 生产就绪 | 无变化 |
| `OpenCodeAdapter` | 生产就绪 | 无变化 |
| `NoopAdapter` | 生产就绪 | 无变化 |
| `OpenCodeSessionAdapter` | **新增**（M23） | 会话式外部代理通道，支持 session refs 投影 |
| `LangChainAgentAdapter` | 实验性 opt-in | 无变化 |
| `WorkerRouter` | 生产就绪 | 自动注册 `OpenCodeSessionAdapter` |

### 3.4 应用层 (apps/)

| 应用 | 体量 | M20→M30 变化 | 评估 |
|------|------|-------------|------|
| `operator_cli` | 37 KB | +3 KB | 新增 `plan-graph`、`policy-preview`、`goal-packet`、`launch`、`operator-packet` 命令 |
| `orchestrator_api` | 32 KB | +1 KB | 新增对应 API 端点 |
| `web_ui.py` | 23 KB | 无变化 | 内嵌 HTML 模板不变，仍为 operator console |
| `operator_tui` | 5 KB | 稳定 | Rich-based 仪表盘，read-mostly |
| `remote_worker_api` | — | 无变化 | HTTP 远程 Worker 池 |
| `scheduler_authority_api` | — | 无变化 | 调度器权威对等节点 |

### 3.5 基础设施 (infra/)

| 模块 | M20→M30 变化 |
|------|-------------|
| 迁移 (migrations/) | 14 个 SQL 迁移文件不变，但 `db.py` 新增了 `migrate()` / `get_migration_status()` 入口 |
| 脚本 (scripts/) | 新增 `m21_rebaseline_report.py` (5 KB) |
| 验证 (validation/) | 无变化 |
| 种子 (seeds/) | 无变化 |
| 冻结评审 | 新增 `m25-beta-freeze-review.md`、`m26-policy-control-freeze-review.md`、`m30-operator-control-freeze-review.md` |
| 任务卡 | M21-M30 各 phase 均有完整 task-card pack |

### 3.6 测试覆盖

| 测试文件 | 体量 | M20→M30 变化 |
|----------|------|-------------|
| `test_execution_loop.py` | 109 KB | +6 KB，新增 plan graph / policy preview / goal packet / operator packet 覆盖 |
| `test_api.py` | 74 KB | +1 KB，新增对应 API 端点测试 |
| `test_cli.py` | 68 KB | +1 KB，新增 CLI 命令测试 |
| `test_repositories.py` | 27 KB | +0.4 KB |
| `test_contracts.py` | 23 KB | 稳定 |
| `test_governance.py` | 12 KB | 稳定 |
| `test_remote_worker_api.py` | 9.5 KB | 稳定 |
| `test_web_ui.py` | 3.7 KB | 稳定 |
| `test_runtime_boundary.py` | 3.9 KB | 稳定 |
| `test_scheduler_authority_api.py` | 3 KB | 稳定 |
| `test_release_closeout.py` | 2.6 KB | 稳定 |
| `test_pre_m8_hardening.py` | 1.6 KB | 稳定 |

**测试质量评价**: ⭐⭐⭐⭐ — 273 个测试全部通过（较 M20 增加 9 个），覆盖面广。仍缺少 `pytest-cov` 配置（`pyproject.toml` 中 `addopts` 仍仅包含 `--basetemp`）。

---

## 四、技术债务状态

### 4.1 已偿还债务

| 债务 ID 范围 | 数量 | 涵盖领域 |
|-------------|------|----------|
| TD-001 ~ TD-021 | **21 项全部偿还** | 从基础预设解析器到分布式调度器共识 |

### 4.2 当前开放债务

**无**。技术债务注册表的 "Open Debt" 表仍为空。但需要注意的是，M21-M30 引入的新能力（capability plane、plan graph、operator packet 等）虽然没有产生正式登记的债务，但存在若干 **隐性结构性问题**（见第五节）。

---

## 五、关键发现与评价

### 5.1 突出优势

1. **工程纪律持续高水准**
   - M21-M30 共 10 个里程碑，每个都有完整的 phase doc、task cards、freeze review
   - 3 个新增冻结评审（M25 beta、M26 policy control、M30 operator control）
   - 文档治理原则实际贯彻（`current_development_workflow.md` 已更新至 M30 基线）
   - 活文档指向最新控制基线，历史文档通过 git history 追溯

2. **增量迁移产品化**（M20 评估建议 → M21 落实）
   - `db.py` 新增 `migrate()` / `get_migration_status()`
   - CLI 入口 `workflowctl db migrate` / `workflowctl db migration-status`
   - 解决了 M20 评估中指出的"依赖 reset-db 重建"问题

3. **ResultEnvelope v1 落地**（GPT Pro 评估建议 → M21 落实）
   - 统一结果对象包含 `summary`、`raw_ref`、`artifacts`、`verification`、`provenance`、`mutations`、`usage`、`confidence`
   - 投影到 evidence、audit report、mutation report
   - 回应了 GPT Pro 评估中"把 artifact 升级成统一结果对象"的建议

4. **自然语言规划链路从零到一**
   - `suggest-presets → plan-graph → policy-preview → goal-packet → launch` 完整后端链路
   - 操作员可以在执行前预览能力选择、策略模式、计划图、匹配的描述符和健康状态
   - 这是从"命令式操作"向"目标式操作"的重要跃迁

5. **操作员读模型标准化**
   - operator packet 和 goal packet 将分散的 ad hoc 载荷收口为统一读模型
   - dashboard 与 operator view 对齐到同一 packet 族
   - 减少了消费端（CLI/API/TUI/Web UI）的组装负担

6. **CapabilityDescriptor 形式化**
   - 每个外部能力都有结构化的 `capability_id`、`provider_kind`、`transport`、`auth_mode`、`scopes`、`cost_class`、`latency_class`、`side_effect_level`、`evidence_schema`
   - 这为未来接入更多 provider 和外部能力奠定了契约基础
   - 回应了 GPT Pro 评估中"统一走 CapabilityDescriptor"的建议

### 5.2 需要关注的领域

1. **services.py 体量继续增长（163 KB → 166 KB）**
   - M20 评估中的"中"风险等级应上调至"中高"
   - 新功能仍然以 Mixin 方法 → services.py 组合的方式追加
   - service_projection.py 同步增长至 70 KB，与 service_lifecycle.py 体量持平
   - 三个 Mixin + services.py 本身合计 339 KB，是整个 core_domain 包的主导体量

2. **MCP 导入期耦合**（GPT Pro 风险 4 未处理）
   - `capability_plane.py` 顶层 `from mcp.client.session import ClientSession`
   - `from mcp.client.stdio import StdioServerParameters, stdio_client`
   - 这不是 lazy import，不是 extras 保护，不是功能标志降级
   - 影响：不安装 `mcp` 包 → 整个 core_domain 导入失败 → 所有测试无法收集

3. **Web UI 仍然原始**（M20 评估风险 5 未处理）
   - `web_ui.py` 23 KB 内嵌 HTML 字符串模板无变化
   - M30 冻结评审显式列出"front-end natural-language chat/workbench surface"为 deferred
   - 自然语言规划后端已就位但无对应前端交互面

4. **测试增量有限（+9）**
   - M21-M30 引入了大量新 surface（plan graph、policy preview、goal packet、operator packet、launch、capability descriptor、capability health、sessionful agent）
   - 但测试仅增加 9 个，覆盖密度相对新 surface 数量偏低
   - 仍未配置 `pytest-cov`

5. **pyproject.toml 未演进**
   - 无 `pytest-cov` 配置
   - `mcp` 仍在主依赖而非 optional extras
   - 版本策略未变（`fastapi>=0.135.2,<1.0.0` 等）

6. **TaskKind 扩展性未改善**
   - 仍仅有 `shell_exec` 和 `noop` 两种 TaskKind
   - M20 评估中指出的"新增 TaskKind 需同时修改契约、预设、适配器、能力注册表"的问题未见结构性缓解

---

## 六、M31+ 开发建议

> [!IMPORTANT]
> 以下建议遵循项目既定的"不在下一 Phase 明确开启前启动新广度工作"的纪律。M30 冻结评审已明确 deferred 列表。

### 6.1 M31 Phase 0: 结构性健康恢复（建议 P0 范围）

| 任务 | 说明 | 预期产出 |
|------|------|----------|
| **MCP 导入降级** | 将 `capability_plane.py` 中 MCP 导入改为 lazy import，`mcp` 从主依赖移入 optional extras `[mcp]` | `pyproject.toml` 更新 + 导入降级 |
| **覆盖率基线** | 添加 `pytest-cov` 并建立最低覆盖率门控 | `pyproject.toml` 配置 + 覆盖率报告 |
| **Projection 面拆分评估** | `service_projection.py` 已达 70 KB，评估是否按投影域拆分 | 重构决策文档 |
| **services.py 方法审计** | 统计 OrchestratorService 当前方法数，识别可独立服务边界的方法簇 | 方法清单 + 拆分候选分析 |

### 6.2 候选广度方向

#### 方向 A：自然语言交互面产品化

| 优先级 | 建议 | 理由 |
|--------|------|------|
| P1 | **Web 聊天式工作台** — chat 输入 + goal packet 预览 + plan graph 可视化 | 后端链路已完整但前端缺失 |
| P1 | **Policy 从预览升级为强制门控** | M30 deferred，是自治度提升前置条件 |
| P2 | **plan graph 从固定模板到目标驱动** | 当前编排计划仍是固定模板 |

#### 方向 B：能力平面深化

| 优先级 | 建议 | 理由 |
|--------|------|------|
| P1 | **MCP 作为一等能力接缝** — lazy import + 启动探测 + 缺失降级 | 当前导入期硬耦合 |
| P1 | **多 Provider Gateway** — 支持 Anthropic / Gemini / 本地模型 | `RuntimeGateway` 仍绑定 OpenAI |
| P2 | **OTel Trace 实际导出** | 抽象已就位，缺少默认非空实现 |

#### 方向 C：工程基础加固

| 优先级 | 建议 | 理由 |
|--------|------|------|
| P1 | **CI Pipeline** — GitHub Actions | 验证完全本地手动 |
| P2 | **golden workflow 回归** — 全链路重放验证 | GPT Pro 建议 |
| P2 | **TaskKind 插件化** — 新增 TaskKind 不必同时修改 N 个文件 | 扩展点过于分散 |

### 6.3 代码级改进建议

#### 建议 1: MCP 导入降级

```python
# 当前：顶层硬导入
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# 建议：lazy import + 降级
def _import_mcp():
    try:
        from mcp.client.session import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client
        return ClientSession, StdioServerParameters, stdio_client
    except ImportError:
        return None, None, None
```

#### 建议 2: pyproject.toml extras 分组

```toml
[project.optional-dependencies]
dev = ["pytest>=8.3.4,<9.0.0", "pytest-cov>=6.0.0,<7.0.0"]
mcp = ["mcp>=1.18.0,<2.0.0"]
```

#### 建议 3: 覆盖率配置

```toml
[tool.pytest.ini_options]
addopts = "--basetemp=state/.pytest-tmp --cov=packages --cov=apps --cov-report=term-missing --cov-fail-under=75"
```

---

## 七、M20 评估建议回顾

| M20 建议项 | M30 状态 | 评价 |
|-----------|---------|------|
| Schema 迁移策略 | ✅ 已落实 | `db.py` 新增 `migrate()` / `get_migration_status()` |
| 覆盖率基线 | ❌ 未落实 | pyproject.toml 无 `pytest-cov` |
| services.py 重构评估 | ⚠️ 部分 | compile/recompile 去重完成，总体体量继续增长 |
| 依赖审计 | ❌ 未落实 | 版本策略无变化 |
| Web UI 现代化 | ❌ 未落实 | 显式 deferred 到 M31+ |
| TaskKind 扩展性 | ❌ 未落实 | 仍仅 2 种 TaskKind |

| GPT Pro 建议项 | M30 状态 | 评价 |
|---------------|---------|------|
| 基线做干净 | ✅ 已落实 | `m21_rebaseline_report.py`、canonical demo matrix |
| 拆 OrchestratorService | ⚠️ 部分 | Mixin 拆分已有，services.py 继续膨胀 |
| ResultEnvelope 统一结果对象 | ✅ 已落实 | 完整契约 + evidence 投影 |
| MCP 真正插件化 | ❌ 未落实 | 导入期硬耦合 |
| project_delivery 图编排 | ⚠️ 部分 | PlanGraph 契约已有，默认编排仍为固定模板 |
| golden workflow 回归 | ❌ 未落实 | 仅单元测试 |

---

## 八、风险矩阵

| 风险 | 影响 | 可能性 | M20→M30 趋势 | 缓解策略 |
|------|------|--------|-------------|----------|
| services.py + Mixin 合计持续膨胀 | 高 | 高 | ↑ 恶化 | M31 Phase 0 拆分评估 |
| MCP 导入期耦合 | 中 | 高 | → 不变 | lazy import + extras |
| 无量化覆盖率 | 中 | 高 | → 不变 | pytest-cov 配置 |
| Web UI 用户体验 | 低 | 高 | → 不变 | 方向 A 优先改进 |
| 单 SQLite 并发瓶颈 | 中 | 低 | → 不变 | 架构决策明确 |
| 外部依赖大版本升级 | 中 | 中 | → 不变 | 定期审计 |
| 自然语言前端缺失 | 中 | 高 | **新增** | Web 聊天工作台 |
| policy preview-only 无强制力 | 中 | 中 | **新增** | enforced gating |

---

## 九、总体评价

| 维度 | M20 评分 | M30 评分 | 说明 |
|------|---------|---------|------|
| **架构设计** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 新增 capability plane、plan graph、operator packet 丰富了架构面，但 services.py 膨胀加重 |
| **代码质量** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ResultEnvelope 提升了结果可信度。MCP 耦合是扣分项 |
| **测试成熟度** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 273 测试全通过，但增量有限且仍无覆盖率工具 |
| **工程纪律** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 10 个里程碑、3 个冻结评审、完整 task card 治理 |
| **可扩展性** | ⭐⭐⭐ | ⭐⭐⭐☆ | CapabilityDescriptor 提升了能力接入结构化程度 |
| **可观测性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 新增 plan graph / policy preview / operator packet / goal packet 投影面 |
| **部署就绪度** | ⭐⭐⭐ | ⭐⭐⭐ | 增量迁移入口到位，但仍无 CI、容器化 |
| **自然语言能力** | — | ⭐⭐⭐ | **新增维度**。后端链路完整，前端交互面缺失 |
| **综合评分** | **4.0 / 5.0** | **4.1 / 5.0** | 在保持工程纪律的同时稳步推进了操作员控制和自然语言规划能力 |

---

## 十、结论

本项目在 M30 基线上完成了从"v1 core complete"到"operator-control baseline"的演进。M21-M30 的 10 个里程碑聚焦在三条主线上：

1. **重基线与信任恢复**（M21）：增量迁移产品化、ResultEnvelope v1、compile/recompile 去重
2. **能力与规划结构化**（M22-M25）：CapabilityDescriptor、OrchestrationPlanGraph、自然语言 launch 链路
3. **操作员控制收敛**（M26-M30）：policy preview、operator packet、goal packet、dashboard 收敛

这条演进路线是审慎且有效的 — 它没有急于铺开多 provider、多模态、自动化循环等广度工作，而是先把操作员面的投影和控制做到一致。

### 下一步应关注的核心问题

1. **结构性健康**：services.py + Mixin 合计 339 KB 的体量需要正式评估拆分方案
2. **可选依赖治理**：MCP 导入期耦合是当前最紧迫的工程卫生问题
3. **量化覆盖率**：273 个测试是充分的数量，但没有覆盖率数据就无法判断盲区
4. **前端交互面**：自然语言后端已就位，缺一个前端 workbench 来释放其价值

> **一句话**：M21-M30 证明了这个项目能够在保持极高工程纪律的同时稳步推进产品能力 — 它现在最需要的不是更多 surface，而是在打开下一轮广度之前解决 MCP 耦合、覆盖率盲区和 services.py 膨胀这三个结构性问题。
