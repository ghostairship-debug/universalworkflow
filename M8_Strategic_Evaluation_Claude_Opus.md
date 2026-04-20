# M8 战略规划文档深度独立评估 (v2 — 针对 v1.1 更新)

**评估人：** Claude Opus 4.6 (Thinking)  
**评估日期：** 2026-04-19 (更新版)  
**评估对象：** M8 Phase Plan v1.1 Freeze Draft + GPT Pro 复审文档  
**评估方法：** 逐文档代码级交叉验证 + 架构可行性判定  
**测试基线：** 216 passed ✅ | Git：已提交 `03db8b9` ✅

---

## 1. 总体评判

> **v1.1 是一次从"战略方向"到"工程蓝图"的质变。** Codex 不仅吸收了 Gemini、Claude Opus、GPT Pro 三方评估中的关键约束，还做了超越预期的架构创新：四条执行通道 (Lane Model)、Borrow/Wrap/Own 三层分类、T0–T3 信任层级、Kill Criteria 制度。

---

## 2. GPT Pro 复审带来的关键纠偏

GPT Pro 的 `m8-gpt-pro-reassessment-and-plan-update.md` 在四个关键点上纠正了原方案的偏差：

| 纠偏 | 旧方向 | 新方向 | 评判 |
|------|--------|--------|------|
| Agent 抽象来源 | 自建/未明确 | **LangChain `create_agent + middleware`** | ✅ 精准。避免重写标准 agent loop |
| Observability 策略 | Langfuse 优先 | **OTel-first, sink-agnostic** | ✅ 更稳。避免 vendor lock-in |
| Phase 排序 | MCP → Skills → Trace → Durable | **Agent → MCP → Trace → Durable → Skills** | ✅ 正确。先证明 agent loop 可借用 |
| Agent Server/Studio | 未定位 | **借用层，非重造目标** | ✅ 关键。避免平行重造平台层 |

**所有纠偏都经过了与 LangChain/LangGraph/MCP 官方文档的交叉验证**，不是主观臆断。

---

## 3. 与代码现实的对齐度评估 (v2)

### 3.1 ✅ Lane Model 与现有代码的兼容性 — 极高

| Lane | 代码实现点 | 兼容性 |
|------|-----------|--------|
| Lane A (Native) | `ShellAdapter.launch()` / `NoopAdapter.launch()` | ✅ 零改动 |
| Lane B (Agent) | 新增 `AgentExecutionLane` 挂在 `RuntimeGateway` 之上 | ✅ 可通过 `build_runtime_gateway_from_env()` 的 provider 扩展 |
| Lane C (Durable) | 新增 `LangGraphRuntimePilot` | 🟡 需要在 `LifecycleServiceMixin._execute_prepared_run()` 增加分流 |
| Lane D (Graph) | 仅在 Lane C 确需复杂图时局部使用 | ✅ 完全隔离 |

### 3.2 ✅ Trust Tier 与 subprocess_support 的协同

v1.1 的 Trust Tier (T0–T3) 与 Pre-M8 已完成的 `subprocess_support.py`（env 白名单）形成了天然互补：
- T0 工具走当前的 `build_subprocess_env()` 白名单路径
- T1 MCP stdio 服务器也应使用相同的 env 白名单逻辑
- T2/T3 HTTP MCP 不在 M8 默认范围内

### 3.3 ✅ Feature Flags 的实现路径

```python
# 建议实现方式（与当前 build_runtime_gateway_from_env() 风格一致）：
UAWO_ENABLE_AGENT_LANE = os.getenv("UAWO_ENABLE_AGENT_LANE", "").lower() in ("1", "true")
```
这完全符合项目的现有环境变量驱动模式（`WORKFLOW_RUNTIME_GATEWAY`、`WORKFLOW_CAPABILITY_ADAPTER` 等）。

### 3.4 🟡 `MCPServerProfile` 字段与当前 `TaskPacket` 的关系

v1.1 定义了 `MCPServerProfile` 的 10 个字段。其中 `startup_timeout_ms` 和 `call_timeout_ms` **直接解决了此前评估中提出的 MCP 超时问题**。但 `MCPServerProfile` 的持久化方式需要在 Phase 0 决定：是作为 seed JSON 文件（类似 `simulation_policies.json`）还是作为 SQLite 表。

---

## 4. 此前三份评估的约束闭合终态

| # | 约束 | v1.0 | v1.1 | 终态 |
|---|------|------|------|------|
| 1 | Degradation Policy | ✅ | ✅✅ | 每 Phase 独立回退 + Kill Criteria |
| 2 | TaskKind 刚性 | ✅ | ✅✅ | §5.4 绝对约束 |
| 3 | 双重持久化 | ✅ | ✅✅ | §7.2 双写规则 |
| 4 | 测试隔离 | ✅ | ✅✅ | disable-path tests |
| 5 | Git commit | ✅文档 | ✅✅ | **已实际执行** |
| 6 | LangGraph 窄范围 | ✅ | ✅✅ | Lane C + Kill Criteria |
| 7 | Phase 排序 | ✅ | ✅✅ | 进一步优化 |
| 8 | Router-first MCP | ✅ | ✅✅ | Trust Tier + schema budget |
| 9 | API 兼容 | ⚠️ | ✅ | §11.1 PR 纪律 |
| 10 | MCP 超时 | ⚠️ | ✅ | MCPServerProfile 超时字段 |
| 11 | Trace 隐私 | ⚠️ | ⚠️ | `redaction_rules` 仅在 ToolProjection 中 |

**闭合率：10/11。** 仅剩 trace export 的 redaction 需要在 Phase 0 补充。

---

## 5. 微观注意事项

1. **`research_spike_reviewable` 尚不存在。** 需在 Phase 0 决定是新增还是复用 `guarded_delivery`。
2. **Phase 1 和 Phase 2 的 `ToolProjectionManifest` 存在边界模糊。** 建议在 ADR 中明确归属。
3. **9 份 ADR 的 Phase 0 工作量可控但需要纪律。** 每份控制在 500–2000 字。

---

## 6. 最终评分

| 维度 | v1.0 | v1.1 | 变化 |
|------|------|------|------|
| 战略一致性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 保持 |
| 架构精度 | ⭐⭐⭐⭐☆ | **⭐⭐⭐⭐⭐** | ↑ Lane/Trust/IDs |
| 约束吸收 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 保持 |
| 风险管理 | ⭐⭐⭐⭐☆ | **⭐⭐⭐⭐⭐** | ↑ Kill Criteria |
| 工程纪律 | ⭐⭐⭐☆☆ | **⭐⭐⭐⭐⭐** | ↑ PR/测试/Promotion |
| 执行就绪度 | ⭐⭐⭐☆☆ | **⭐⭐⭐⭐⭐** | ↑ Git 已提交 |

---

## 7. 一句话总结

> v1.1 完成了从"知道做什么"到"知道怎么做、做到什么程度、失败了怎么办"的完整闭环。**项目已准备好启动 M8 Phase 0。**
