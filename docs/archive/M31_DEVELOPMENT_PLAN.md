# M31 具体开发方案

> **生成日期**: 2026-04-21
> **依据文档**: `EVALUATION_REPORT.md`（含第二轮重评）、`M31_ARCHITECTURE_EVALUATION.md`（第二轮重评）、`M31_CURRENT_STAGE_REMEDIATION_PLAN.md`（覆盖更新版）、`M31_FUTURE_IMPLEMENTATION_PLAN.md`（覆盖更新版）、`AI_AGENT_LEGACY_WHITELIST.md`、`README.md`、`NEXT_DEVELOPMENT_PLAN.md`
> **现实校验**: `pytest -q` → `273 passed`、代码结构审计完成

---

## 0. 本方案的定位

本方案是**可直接执行的开发计划**，不是愿景文档，不是架构蓝图。

它综合了以下输入：

- `EVALUATION_REPORT.md` 的代码度量与风险矩阵
- `M31_ARCHITECTURE_EVALUATION.md` 的语义诚实性诊断与 13 维度 readiness 判断
- `M31_CURRENT_STAGE_REMEDIATION_PLAN.md` 的 P0/P1 分级与 Phase 路线
- `M31_FUTURE_IMPLEMENTATION_PLAN.md` 的七层架构愿景与 M32~M36 里程碑建议
- `NEXT_DEVELOPMENT_PLAN.md` 的短中长期分层思路
- `AI_AGENT_LEGACY_WHITELIST.md` 的遗产参考边界

**核心原则**：先收口再扩张，先语义诚实再产品化，先拆边界再加 surface。

---

## 1. M31 总体目标

> **平台边界收口 + 语义诚实性修正 + 工程卫生补齐**

M31 不追求新功能广度，而是解决三份评估文档共同识别的核心问题：

1. `OrchestratorService` 过重导致平台边界模糊
2. scheduler authority 语义表述超过代码实际能力
3. MCP 导入期硬耦合 + 缺少覆盖率工具
4. 技术债务注册表缺少"过渡期结构债"

---

## 2. 执行分期

### Phase M31-0：工程卫生（1 sprint）

**目标**: 修复最紧迫的工程卫生问题，为后续重构建立安全网。

#### 任务 0.1：MCP 导入降级

- **问题**: `capability_plane.py` 顶层硬导入 `mcp`，导致不安装 mcp 包则整个 core_domain 导入失败
- **动作**:
  - 将 `from mcp.client.session import ClientSession` 等改为 lazy import
  - `pyproject.toml` 中 `mcp` 从主依赖移入 `[project.optional-dependencies]` 的 `mcp` 组
  - 确保 `pytest -q` 在不安装 mcp 时仍可收集并运行非 MCP 测试
- **验收**: `pip install -e .`（不含 mcp extra）后，`pytest -q` 不因导入失败而报错
- **涉及文件**: `packages/core_domain/capability_plane.py`, `pyproject.toml`

#### 任务 0.2：覆盖率基线

- **动作**:
  - `pyproject.toml` 添加 `pytest-cov` 到 dev 依赖
  - `addopts` 添加 `--cov=packages --cov=apps --cov-report=term-missing --cov-fail-under=70`
  - 运行一次完整覆盖率报告，记录当前基线
- **验收**: `pytest -q` 输出中包含覆盖率报告，且通过最低阈值
- **涉及文件**: `pyproject.toml`

#### 任务 0.3：技术债务注册表更新

- **动作**: 在 `docs/tech-debt-registry.md` 的 Open Debt 表中新增以下过渡期结构债：
  - TD-STRUCT-001: OrchestratorService façade 过重
  - TD-STRUCT-002: scheduler authority 语义超卖
  - TD-STRUCT-003: orchestration 缺少通用 graph engine
  - TD-STRUCT-004: capability health 仅声明式
  - TD-STRUCT-005: interaction plane 缺位
  - TD-STRUCT-006: automation plane 缺位
- **验收**: 债务注册表不再为空，每条债务有 ID、描述、严重度、关联 P0 编号
- **涉及文件**: `docs/tech-debt-registry.md`

#### 任务 0.4：services.py 方法审计

- **动作**:
  - 统计 `OrchestratorService` 当前方法数、按职责域分类
  - 输出方法清单与拆分候选分析（作为 Phase M31-1 的输入）
  - 结果记录为 `docs/reviews/m31-services-audit.md`
- **验收**: 审计文档产出，包含方法清单、职责域分类、建议拆分边界
- **涉及文件**: 新建 `docs/reviews/m31-services-audit.md`

**Phase M31-0 Exit Gate**: MCP lazy import 完成 + pytest-cov 配置 + 债务注册表更新 + 方法审计完成

---

### Phase M31-1：边界收口 + 语义诚实性（2 sprints）

**目标**: 拆分 OrchestratorService façade，修正 scheduler authority 语义。

#### 任务 1.1：OrchestratorService 初步拆分

- **策略**: 不一次拆成 9 个服务，而是先拆出 4 个独立服务边界
- **拆分方案**:

```
OrchestratorService (façade / coordinator)
  ├── 委托 → RunLifecycleService
  │     (create, compile, recompile, resume, cancel, terminal transitions)
  ├── 委托 → ReviewPolicyService
  │     (approve, reject, review state, effective_review_state)
  ├── 委托 → AuditReplayService
  │     (audit-report, replay-packet, event-inspection, simulation)
  └── 委托 → OwnershipLeaseService
        (claims, leases, attempts, snapshots, reconcile, repair)
```

- **约束**:
  - CLI/API/Web/TUI 公开签名不变，仍通过 `OrchestratorService` façade 调用
  - 内部实现改为 façade → 独立 service 的显式委托
  - 每个独立 service 有自己的文件
  - Mixin 逐步退役，逻辑迁入对应独立 service
- **验收**: 
  - `pytest -q` 全部通过（273+）
  - 新功能开发不再需要往 `services.py` 添加方法
  - 每个独立 service 文件职责单一
- **涉及文件**: 
  - 新建 `packages/core_domain/service_run_lifecycle.py`
  - 新建 `packages/core_domain/service_review_policy.py`
  - 新建 `packages/core_domain/service_audit_replay.py`
  - 新建 `packages/core_domain/service_ownership_lease.py`
  - 修改 `packages/core_domain/services.py`（退化为委托 façade）

#### 任务 1.2：scheduler authority 语义诚实化（路线 A）

- **策略**: 不重写实现，而是修正叙述与文档
- **动作**:
  - README.md 中 scheduler authority 相关描述改为 "single-store quorum-style authority model"
  - `docs/reviews/m30-operator-control-freeze-review.md` 中如有过度表述则添加澄清注释
  - `scheduler_authority.py` 模块 docstring 添加显式声明：当前实现是 single-store modeled quorum，不是 peer-to-peer replicated consensus
  - 新增测试 `test_scheduler_authority_semantic_boundary.py`，验证：
    - leader 选举基于本地排序而非 RPC
    - vote 收集在同一存储上下文
    - 明确标注这是 modeled quorum 而非分布式共识
  - 在 `config.py` 或 capability plane 中新增 `authority_mode` 字段区分 `single_store_quorum` 与未来 `replicated_authority`
- **验收**: 
  - 对外文档不再出现"distributed consensus"或等价表述
  - `authority_mode` 字段存在且默认为 `single_store_quorum`
  - 新增语义边界测试通过
- **涉及文件**:
  - `README.md`
  - `packages/core_domain/scheduler_authority.py`
  - 新建 `tests/test_scheduler_authority_semantic_boundary.py`
  - `packages/core_domain/config.py`

#### 任务 1.3：projection 面评估与初步拆分

- **问题**: `service_projection.py` 已达 72 KB，与 `service_lifecycle.py` 体量持平
- **动作**:
  - 评估按投影域拆分：operator projections / governance projections / plan projections
  - 如评估后决定拆分，至少拆出一个独立投影 service
- **验收**: 评估文档产出；如拆分则 `pytest -q` 全通过
- **涉及文件**: `packages/core_domain/service_projection.py`

**Phase M31-1 Exit Gate**: OrchestratorService 退位为 façade + scheduler authority 语义诚实化完成 + 所有测试通过

---

### Phase M31-2：通用编排基础（2 sprints）

**目标**: 从 `project_delivery` baseline 提取通用 orchestration substrate。

#### 任务 2.1：编排契约正式化

- **动作**:
  - 在 `packages/contracts/models.py` 中，将现有 `OrchestrationPlanGraph` / `OrchestrationGraphNode` 演进为更通用的编排契约
  - 新增（或演进现有）：
    - `EdgeSpec`（节点间依赖关系）
    - `BarrierSpec`（并行同步点）
    - `RetryPolicy`（重试策略）
  - 不新建独立的 `ExecutionGraph` 类，而是扩展 `OrchestrationPlanGraph` 使其成为通用 graph 载体
- **验收**: 新契约在 `packages/contracts/` 中定义，与现有契约无命名冲突
- **涉及文件**: `packages/contracts/models.py`

#### 任务 2.2：graph engine 最小实现

- **动作**:
  - 新建 `packages/core_domain/orchestration_engine.py`
  - 实现 graph validate / graph compile / graph persist 最小功能
  - 将 `project_delivery` 迁移为 graph definition 驱动
  - 新增第二个 orchestration preset（如 `guarded_project_delivery` 或 `research_project`）
- **验收**: 
  - 至少两个 orchestration preset 基于同一 graph engine 工作
  - 新编排不修改核心 lifecycle 逻辑即可接入
  - `pytest -q` 全通过
- **涉及文件**: 
  - 新建 `packages/core_domain/orchestration_engine.py`
  - 修改 `packages/core_domain/service_lifecycle.py`（project_delivery 迁移）

**Phase M31-2 Exit Gate**: graph engine 最小可用 + 两个 preset 运行在同一 engine 上 + 测试通过

---

## 3. M31 明确"不做什么"

以下内容在 M31 范围内**明确排除**：

| 编号 | 不做什么 | 原因 |
|------|----------|------|
| N1 | 不做大规模 provider/adapter 扩张 | 先统一 capability contract |
| N2 | 不把 scheduler authority 包装成 distributed consensus | 语义诚实性原则 |
| N3 | 不先做漂亮前端再补交互内核 | 顺序必须反过来 |
| N4 | 不开放无约束自我升级 | 必须先有 eval/canary/promotion |
| N5 | 不围绕单一外部框架重写 | 吸收模式，不做整体替换 |
| N6 | 不新增 interaction plane / automation plane | 推迟到 M32+ |
| N7 | 不新增动态角色工厂 | 推迟到 M34+ |

---

## 4. M32~M34 路线预览（非承诺）

基于评估文档和愿景文档，后续里程碑的**建议方向**如下：

### M32：capability runtime contract + interaction plane 基础

- capability invocation envelope 统一
- capability health 从声明式升级为运行时探测
- `IntentSession` / interaction API 最小版
- MCP 作为一等 capability seam

### M33：automation plane + workbench 基础

- `AutomationController` 最小实现
- stale run watcher / timeout handling / background reconcile
- Web workbench v1（基于 interaction API，非直接绑 operator packet）
- operator UI 与 product workbench 正式分层

### M34：role system + generated roles

- `RoleSpec` 正式化
- fixed role registry v1
- `RoleFactory` 最小版（ephemeral → typed → bounded）
- specialists-as-tools / manager-as-code 双拓扑支持

---

## 5. 文档治理动作

在 M31 Phase 0 启动时，执行以下文档整理：

| 动作 | 时机 |
|------|------|
| 将 `M31_ARCHITECTURE_EVALUATION.md` 复制到 `docs/reviews/m31-architecture-evaluation-r2.md` | Phase M31-0 启动时 |
| 将 `M31_FUTURE_IMPLEMENTATION_PLAN.md` 移动到 `docs/vision/platform_architecture_blueprint.md` | Phase M31-0 启动时 |
| 保留 `M31_CURRENT_STAGE_REMEDIATION_PLAN.md` 在根目录作为执行参考 | 持续 |
| 保留 `AI_AGENT_LEGACY_WHITELIST.md` 在根目录 | 每次新 phase 复查 |
| `NEXT_DEVELOPMENT_PLAN.md` 标记为被本文档取代 | Phase M31-0 启动时 |

---

## 6. 验证计划

### 自动化验证

```bash
# 全量测试
python -m pytest -q

# 覆盖率（Phase M31-0 后可用）
python -m pytest --cov=packages --cov=apps --cov-report=term-missing

# MCP 降级验证（不安装 mcp 时）
pip install -e . && python -m pytest -q

# 离线验证
powershell -ExecutionPolicy Bypass -File .\infra\scripts\run_offline_validation.ps1
```

### 手动验证

- Phase M31-1 后：确认 CLI/API 公开签名无变化（对比 README 中的 common commands）
- Phase M31-1 后：确认 scheduler authority 相关文档叙述与代码一致
- Phase M31-2 后：运行 `project_delivery` 和新增 preset，验证 graph engine 工作

---

## 7. 成功标准

M31 结束时应达到：

| 维度 | 标准 |
|------|------|
| **工程卫生** | MCP lazy import ✓ / pytest-cov ✓ / 债务注册表更新 ✓ |
| **平台边界** | OrchestratorService 退位为 façade，新功能不再直接堆入 |
| **语义诚实** | scheduler authority 文档与代码一致，不存在语义超卖 |
| **编排抽象** | 至少两个 preset 基于同一 graph engine |
| **测试** | 273+ 测试全通过 + 覆盖率报告可用 |
| **文档** | 三份 M31 文档归档/保留到位 |

---

## 8. 一句话总结

> M31 的核心使命是把当前仓库从"强控制平面内核 + 大量平台语义"收口成"边界清楚、语义诚实、可安全扩展的平台基座"——这是所有后续产品化、生态扩张和自主升级的前提。
