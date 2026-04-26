# Universal Agentic Workflow OS 深度评估报告（Opus）

- 日期：2026-04-25
- 当前基线：已接受 `M66`（包版本 `0.66.0`）
- 评估前提：个人自用 / 本地 operator runtime
- 评估方式：本地工作树静态分析 + 实测命令（`workflowctl test matrix`、`workflowctl capability probe`、`workflowctl doctor --strict`、`check_doc_links`）
- 评估者：Claude Opus 4.7
- 与既有评估的关系：本文是 [PROJECT_DEEP_EVALUATION_M47_OPUS.md](docs/archive/evaluations/PROJECT_DEEP_EVALUATION_M47_OPUS.md) 的后续。M48-M66 之间一次性跨 19 个里程碑，必须重新校核

## 0. 一句话总评

> **M48-M66 真的把 [M48_M51_RECOVERY_PLAN.md](docs/archive/evaluations/M48_M51_RECOVERY_PLAN.md) 中我提的大部分 P0/P1 都做了**——这是 dogfood 从声称变成事实的关键一跳。但 **"zero-open-debt"是范围限定的修辞**，至少 5 处仍有可证实的结构残留；**`OperatorActionReceipt` 缺 `scope_hash`** 这一关键字段；**1 个 git commit 压缩 19 个 M** 让 phase 级审计无法用 `git log` 校核；**整个项目代码体量在拆分中反而继续膨胀**。

## 1. 评分（M47 → M66）

| 维度 | M47 | M66 | 变化原因 |
| --- | ---: | ---: | --- |
| 项目设想合理性 | 8.5 | 8.5 | 个人自用 + local-first 不变 |
| 架构基础 | 7.0 | **7.5** | OrchestratorService 真瘦了 1218 行；mixin 增至 9 个；scheduler 真 lazy import |
| 实现纪律 | 7.5 | **8.0** | M48-M66 真的执行了 RECOVERY_PLAN；ratchet 测试到位；live probe 真做 |
| 个人自用成熟度 | 7.5 | **8.0** | `test matrix` / `doctor --strict` / `capability probe` 都是真实可用的入口 |
| 测试可复现性 | 5.5 | **8.0** | 唯一 basetemp + 测试矩阵分层落地 |
| 长期可维护性 | 4.5 | **6.0** | services.py 瘦了，但 repositories.py 没动、scheduler 双重存在、chat helper 还是 re-export 私有 API |
| 真实安全边界 | — | **6.5** | receipt + workspace_root 落地；但 receipt 缺 scope_hash 是关键空洞 |

**核心趋势**：M47→M66 净结果是 **拆分纪律真的形成了，但代码总量在拆分中继续膨胀；安全协议落地了但留了一个关键洞**。

## 2. 真做对的事（必须公正承认）

这一轮评估和 M47 不同——大量东西**真的被做了**。下面是实测证据：

### 2.1 OrchestratorService 真瘦了

| 指标 | M47 | M66 | 实测命令 |
| --- | ---: | ---: | --- |
| `services.py` 行数 | 3552 | **2334** | `wc -l packages/core_domain/services.py` |
| OrchestratorService 直接方法数 | 158 | **99** | `grep -c '^    def ' packages/core_domain/services.py` |
| Mixin 数 | 4 | **9** | 类签名 |
| `__init__` ↔ 第一个公共方法跨度 | 229-489 | 244-1941（仍偏大） | 静态分析 |

新增的 5 个 Mixin：`CoreHelperServiceMixin`、`RepairServiceMixin`、`SchedulerServiceMixin`、`WorkerCallbackServiceMixin`、`OperatorActionServiceMixin`——配套 5 个新文件（`service_core_helpers.py`、`service_repair.py`、`service_scheduler.py`、`service_worker_callbacks.py`、`service_operator_action.py`）。

### 2.2 拆分硬约束（ratchet）真落地

[`tests/test_service_decomposition.py`](tests/test_service_decomposition.py) 实施了**比我建议的更严格**的 ratchet：

```python
assert len(direct_methods) <= 120
assert services_py_lines <= 2600
assert chat_facade_lines <= 120
assert cli_main_lines <= 500
assert web_ui_lines <= 700
assert "innerHTML" not in (web_ui + components)  # XSS regression
```

**关键意义**：以后任何"再加一个方法到 facade"的 PR 都会被这个测试红掉。这是 M47 评估中我说"如果不加 ratchet，瘦身会回滚"——这一点真做了。

### 2.3 service_interaction.py 极致拆分

```
M47 时：service_interaction.py 2315 行
M66 时：service_interaction.py 14 行 thin facade
       ├─ service_interaction_chat.py     1285 行
       ├─ service_interaction_cluster.py   608 行
       └─ service_interaction_session.py   612 行
```

这是真实的物理拆分，不是"挂个新 mixin"。

### 2.4 chat_runtime 包目录化

```
M47 时：chat_runtime.py 738 行单文件，MiniMax 错误继承 DeepSeek
M66 时：runtime_langgraph/chat_runtime/ 8 个文件
       ├─ base.py
       ├─ openai_compatible.py    ← MiniMax 和 DeepSeek 共同父类（修复了 M47 评估指出的继承错位）
       ├─ openai_runtime.py
       ├─ fallback.py
       ├─ actions.py
       ├─ reasoning_filter.py
       ├─ response_utils.py
       └─ builder.py
```

### 2.5 CLI 拆 sub-app

```
M47 时：apps/operator_cli/main.py 1535 行，60+ 命令挂在一个 Typer
M66 时：apps/operator_cli/main.py    96 行（只剩 wiring + doctor + tui）
       ├─ run_commands.py        638
       ├─ interaction_commands.py 229
       ├─ catalog_commands.py    215
       ├─ admin_commands.py      174
       ├─ scheduler_commands.py   42
       ├─ test_commands.py        28
       ├─ doctor_payload.py
       └─ shared.py
```

### 2.6 Web UI 拆分 + 安全收紧

```
M47 时：web_ui.py 1398 行 + innerHTML 拼 SSE payload
M66 时：web_ui.py 602 行 + web_ui_components.py 875 行 + ratchet 禁用 innerHTML
```

### 2.7 OperatorActionReceipt 协议真上线

实测 `grep` 结果：

- `apps/orchestrator_api/routers/runs.py` 中 **8 个高风险 endpoint** 都加了 `Header(default=None, alias="X-Operator-Action-Receipt")` dependency
- `apps/orchestrator_api/routers/interaction.py` chat 确认动作也加了
- `apps/orchestrator_api/routers/ui.py` Workbench 确认卡走 receipt 流
- `OperatorActionGuard.consume_receipt` 实施：
  - ✅ TTL（`expires_at <= now` 拒绝）
  - ✅ Single-use（`status != "issued"` 拒绝、`mark_consumed` 写入）
  - ✅ workspace_root 一致性校验
  - ✅ action_type 一致性校验

### 2.8 真 live capability probe

实测：

```bash
$ workflowctl --db-path state/workflow.db --workspace-root "D:/Universal Agentic workflow" \
    capability probe --provider shell --require-live --evidence-dir state/m67_eval_probe_shell
{
  "provider": "shell", "status": "verified_ready", "live_probe": true,
  "auth_source": "local_python", "latency_ms": 46, "return_code": 0,
  "stdout_preview": "workflow-shell-probe\r\n"
}
```

[`packages/core_domain/capability_probe.py`](packages/core_domain/capability_probe.py) 真的对 7 个 provider（shell/codex/opencode/mmx/vertex/claude/langchain）跑真子进程，校核 auth_source（OPENAI_API_KEY / MINIMAX_API_KEY / ANTHROPIC_API_KEY / GOOGLE_APPLICATION_CREDENTIALS / `*_login`）。

### 2.9 测试矩阵分层 + 唯一 basetemp

实测：

```
$ workflowctl test matrix --suite unit  → 52 passed in 16.26s
$ workflowctl test matrix --suite core  → 87 passed in 79.11s
```

basetemp 自动到 `state/.pytest-tmp-m61m66/matrix-x0_c5f_r/`（命名问题见 §4.7）。

### 2.10 scheduler 真 lazy import + 重命名

[`services.py:357-372`](packages/core_domain/services.py)：

```python
if self.scheduler_authority_cluster_enabled:
    from packages.core_domain.scheduler_authority import SchedulerAuthorityClusterService
    scheduler_authority_cluster_cls = SchedulerAuthorityClusterService
else:
    scheduler_authority_cluster_cls = LocalSchedulerLeaseArbiter
```

flag off 时**不**进入 scheduler_authority 模块。`tests/test_scheduler_flag_off_isolation.py` 验证 sys.modules 不含。`local_scheduler_lease_arbiter.py` 809 行作为新默认实现。

### 2.11 其他完成的小事（M47 提过的）

| 项目 | M47 状态 | M66 状态 |
| --- | --- | --- |
| `local_game_artifacts.py` 在 core_domain | 1206 行污染 | **移到 `packages/contributions/games/`**（但仍是 1206 行单文件，见 §4.5） |
| `cluster_router` 关键词字面量硬编码 | 无 telemetry | 已提到 [`infra/seeds/cluster_route_markers.json`](infra/seeds/cluster_route_markers.json)，且新增 `ClusterRouteDecisionRepository` 写入 SQLite ledger |
| `examples/local_task_cards/` 只 1 个示例 | 1 | **5**（safe_doc_patch / test_runner_guard / cli_projection / review_required / failure_recovery） |
| README ↔ 代码漂移（doctor 命令位置等） | 多处 | 已修，`check_doc_links` 0 issue |
| 历史评估归档 | 根目录混 | 全部移到 [`docs/archive/evaluations/`](docs/archive/evaluations/) |
| CI 缺失 | — | `.github/workflows/ci.yml` 已有（未实测 PR 触发，仅文件存在） |
| API import-time 副作用 | `app = create_app()` 立即 migrate | M52-M60 报告说"lazy ASGI app wrappers"已加 |

## 3. P0 仍存在的问题

### 3.1 OperatorActionReceipt 缺 `scope_hash`（关键空洞）

GPT Pro 在 [archive/GPTPRO_EVALUATION.md:67-95](docs/archive/evaluations/GPTPRO_EVALUATION.md) 中提议的 receipt 协议**有 7 项校验**：

| 校验项 | M66 实施情况 |
| --- | :---: |
| receipt 存在 | ✅ |
| action_type 匹配 | ✅ |
| run_id/session_id 匹配 | ❌ |
| **request body 关键字段 hash 匹配（scope_hash）** | ❌ |
| 未过期 | ✅ |
| 未被消费（single-use） | ✅ |
| consume 后不可重放 | ✅ |
| workspace_root 匹配 | ✅（额外加的，好事） |

实测 `grep "scope_hash" packages/core_domain/service_operator_action_guard.py` 0 命中。`OperatorActionReceipt` model（[`models.py:585-597`](packages/contracts/models.py)）有 `requested_write_set: list[str]` 字段被存储，**但 `consume_receipt` 不验证它**和实际 request body 一致。

**真实风险**：浏览器中如果有恶意 JS 拿到 receipt（同源情况下完全可能），它可以：

1. 抢先调用 `POST /operator-action-receipts {"action_type": "resume_run"}` 拿 receipt
2. 改 body 把 `write_set` 从 `["README.md"]` 改成 `[".env", "secrets/*"]`
3. 用同一个 receipt POST `/runs/{id}/resume`——会通过！

虽然个人自用 + loopback 风险有限，但既然已经做了 receipt 协议，**漏掉 scope_hash 等于做了 80% 的工作但留了关键洞**。

**修复路径**（M67 候选）：

```python
# issue 时
scope_hash = sha256(canonical_json({
    "write_set": sorted(request.write_set),
    "test_commands": list(request.test_commands),
    "mutation_mode": request.mutation_mode,
    "task_card_ref": request.task_card_ref,
    "execute": request.execute,
})).hexdigest()
receipt.scope_hash = scope_hash

# consume 时
if compute_scope_hash(request_body) != receipt.scope_hash:
    raise OperatorActionReceiptError("scope_hash mismatch")
```

### 3.2 scheduler flag off 仍构造 5 个 scheduler repository

实测 [`services.py:280-282`](packages/core_domain/services.py)：

```python
self.scheduler_proposal_repo = SchedulerLeaseProposalRepository(self.db_path)
self.scheduler_decision_repo = SchedulerLeaseDecisionRepository(self.db_path)
self.scheduler_peer_heartbeat_repo = SchedulerPeerHeartbeatRepository(self.db_path)
```

这 3 个 repo（加上行 263-265 的另外 2 个 scheduler 相关 repo）**无条件构造**——和 M47 评估时一模一样。`scheduler_authority_cluster_enabled` flag 只控制了 `Cluster` 服务的 lazy import，**没有**控制底层 Repository 的构造。

[`services.py:375`](packages/core_domain/services.py) 这一行更典型：

```python
self.scheduler_authority_support = SchedulerAuthoritySupportService(self)
```

这个 `SchedulerAuthoritySupportService` 来自 `packages.core_domain.service_scheduler_authority_support`——**flag off 时仍然 import 并实例化**。

**结论**：M52 报告说"OrchestratorService 不再 import scheduler_authority"是真的（cluster runtime），但**周边的 support service 和 5 个 repository 仍在 boot path 上**。`tests/test_scheduler_flag_off_isolation.py` 只测了 cluster runtime 不在 sys.modules，**没**测 repo / support service 的隔离。

### 3.3 1 个 git commit 关掉 19 个 M（审计黑盒）

```
$ git log --oneline | head -3
11be07b Close M66 cleanup and archive stale docs
a27af04 chore: clean generated planning artifacts
a654031 Complete M43-M47 multimodal game loop and adaptive routing
```

M48-M66 全部塞进 `11be07b` 一个 commit。这意味着：

- **无法**用 `git log --oneline -- packages/core_domain/services.py` 看到"哪个 phase 真的瘦了 services.py"
- **无法**用 `git blame` 找到"`OperatorActionReceipt` 是哪一天加的"
- M48-M51 / M52-M60 / M61-M66 报告里写的具体能力，**只能信报告，不能信 git**
- 新人（未来的你 / 协作者）想审计 phase 完成度时，得读 5 份执行报告 + 实测代码，没有逐 commit 历史可走

**为什么这是 P0**：在 RECOVERY_PLAN 里我把"用 workflow 自己跑 task card → 每 phase 1 个 PR"作为核心机制。**实际执行 squashed 成 1 个 commit** 等于丢了 RECOVERY_PLAN 第 §3.4 节"evidence 落地约定"中"逐 phase 留 evidence"的可审计性。

**修复路径**：M67+ 必须恢复"1 phase 1 commit"或至少"1 M 1 commit"纪律。这件事不需要技术，纯纪律。

### 3.4 repositories.py 2359 行未拆，已比 services.py 还大

```
$ wc -l packages/core_domain/repositories.py packages/core_domain/services.py
2359 packages/core_domain/repositories.py
2334 packages/core_domain/services.py
```

M48-M51 RECOVERY_PLAN §M50 Phase 3（services 收缩 v2）我建议：

> 把 27 个 repository 实例分成 6-8 个 Repository Bundle（RunBundle / TaskBundle / SchedulerBundle / RuntimeBundle / MemoryBundle / ChatBundle / GovernanceBundle）

实测 `services.py:268-295` 仍是 **27 个 `self.*_repo = XxxRepository(self.db_path)` 平铺**。一个都没拆 bundle。

[M61-M66 EXECUTION REPORT](M61_M66_EXECUTION_REPORT.md) 自己承认：

> "deeper repository bundle cleanup can continue as non-blocking M67 debt"

但 [M61-M66 ISSUE REGISTER](M61_M66_ISSUE_REGISTER.md) 里 **没有这一条 carry-forward 项**。这是文档不一致：报告说"留作 M67 debt"，登记表说"zero open"。

### 3.5 service_lifecycle.py 1693 + service_projection.py 1608 完全未动

```
M47 时：service_lifecycle 1691 / service_projection 1608
M66 时：service_lifecycle 1693 / service_projection 1608
```

两个文件 19 个 milestone 后变化 ≤ 2 行。M47 评估时它们就被点名"职责混杂"，M66 仍是巨型 Mixin。这两个 mixin 的方法仍**全部直接挂在 OrchestratorService 上**，是 99 个直接方法中的相当一部分。

## 4. P1 问题

### 4.1 "zero-open-debt" 是范围限定的修辞

实测 [`docs/tech-debt-registry.md`](docs/tech-debt-registry.md) 第 46 行原文：

> "M61-M66 范围内可证实的阻塞性 open debt 已清零"

注意三层限定：

1. **范围限定**："M61-M66 范围内"——M67+ 的范围当然没债（还没开始）
2. **可证实限定**："可证实的"——不可证实的不算
3. **阻塞性限定**："阻塞性"——非阻塞的不算

而 [README.md](README.md) 第 7 行简化成：

> "M61-M66 blocking open debt is zero"

加上 [tech_debt_registry.json](docs/governance/tech_debt_registry.json) `open_items` 实际只有 1 条 `{"无": ...}` 占位——容易被读成 "整个项目零债"。

**实测可证实的非零债**：

- 3.4 repositories.py 2359 行未拆
- 3.5 service_lifecycle / service_projection 巨型 Mixin
- 4.2 local_game_artifacts.py 仍是单文件
- 4.3 scheduler_authority.py 1650 行 + LocalSchedulerLeaseArbiter 809 行 = 2459 行调度代码并存
- 4.4 interaction_catalog.py 1266 行未动
- 4.6 chat_runtime facade re-export 私有 helper

这些**都满足"可证实"**，只是**不被视为"阻塞性"**。修辞要诚实：应改成"M61-M66 范围内**计划中**要清的债已清零；非计划债务仍以 carry-forward 形式留待治理"。

### 4.2 local_game_artifacts.py 只是搬家，没拆文件

```
$ ls packages/contributions/games/
__init__.py  local_game_artifacts.py
$ wc -l packages/contributions/games/local_game_artifacts.py
1206
```

M47 评估指出"贪吃蛇 HTML / 1010 方块 HTML 都硬编码在 Python 字符串字面量里"。M48-M51 RECOVERY_PLAN 我建议拆成 `block_puzzle.py` / `snake.py` 两个文件。

实际：搬到 `packages/contributions/games/`，文件名一样，**还是 1206 行单文件**。这等于把垃圾从客厅搬到杂物间——不是清理。

### 4.3 scheduler 双重存在（2459 行调度代码并存）

```
$ wc -l packages/core_domain/scheduler_authority.py packages/core_domain/local_scheduler_lease_arbiter.py
1650 packages/core_domain/scheduler_authority.py
 809 packages/core_domain/local_scheduler_lease_arbiter.py
2459 total
```

M65 声称"Public docs use `LocalSchedulerLeaseArbiter`; legacy scheduler-authority names are compatibility only"。代码事实：**两套实现并存**，flag on 时走老的、flag off 时走新的。

这不是错——保留兼容是合理的。**问题是文档没说清楚**：是新的取代了老的？还是两套各自独立服务不同模式？M67 应该明确：

- 老的 1650 行将在何时被删？还是永久共存？
- 如果永久共存，[ADR](docs/) 应明确两套各自的责任边界
- 如果迁移完成，**剪掉**旧文件而不是留着

### 4.4 interaction_catalog.py 1266 行 + models.py 持续涨

```
M47 时：interaction_catalog 1266 / models 1377
M66 时：interaction_catalog 1266 / models 1440
```

`models.py` 涨了 63 行（OperatorActionReceipt + CapabilityProbeResult + ClusterRouteDecision），但**没有 ratchet**。`interaction_catalog.py` 19 个 M 没动——它装的是 7 个 cluster template 的所有 `AgentProfileDefinition`（M41-M42 加的），这种"配置即代码"应迁到 `infra/seeds/agent_profiles.json` 之类（参考 cluster_route_markers 的迁移路径）。

### 4.5 整体代码体量在拆分中**继续膨胀**

```
M47 packages + apps + tests 总行数：约 45795 行
M66 packages + apps 总行数：37260 行（不含 tests）
```

直接对比不公平（tests 数量没算），但有一个观察：

**M48-M66 新增的源文件**（粗略统计）：
- `service_repair.py` 714
- `service_scheduler.py` 406
- `service_interaction_chat.py` 1285
- `service_interaction_session.py` 612
- `service_interaction_cluster.py` 608
- `service_operator_action.py` 42
- `service_operator_action_guard.py` 106
- `service_worker_callbacks.py` 226
- `service_core_helpers.py` 383
- `local_scheduler_lease_arbiter.py` 809
- `capability_probe.py` 364
- `web_ui_components.py` 875
- `test_matrix.py` 162（在 core_domain，应在 infra）
- 7 个 CLI command modules 共约 1326

**新增 ≈ 7900+ 行**，而 services.py 只瘦了 1218 行。即使加上 service_interaction.py 减少的 2300 行 + chat_runtime.py 减少的 738 行 ≈ **净瘦 4256 行 / 净增 7900 行**——**整体仍涨 ~3600 行**。

这是经典的"水平拆但不垂直减"：拆分本身正确，但功能没简化、配置没外置，**净代码量增加是真实事实**。

### 4.6 chat_runtime facade re-export 私有 helper

[`packages/runtime_langgraph/chat_runtime/__init__.py:25-47`](packages/runtime_langgraph/chat_runtime/__init__.py) 在 `__all__` 中导出了：

```python
"_coalesce_text_deltas",       # 下划线开头
"_extract_chat_completion_text",
"_extract_response_text",
"_iter_chat_completion_deltas",
"_iter_response_text_deltas",
"_iter_visible_text_deltas",
"_load_json_object",
"_minimax_base_url_from_env",
"_strip_reasoning_markup",
```

下划线前缀 = Python 约定的"内部 API，不要靠它"。`__all__` 把它们 re-export = "我承诺这些是公共的"。**两者矛盾**——这是 backward-compat 强迫症留下的：M47 时这些 helper 被外部引用过，怕拆分破坏调用方，索性全 re-export。

修复（M67 候选）：让真正应是公共的去掉下划线（如 `chunk_text`、`infer_rule_based_chat_action` 已经是无下划线的）；私有的就让调用方一次性改 import 路径。这是 5 分钟的活，但留 19 个里程碑没改。

### 4.7 测试 basetemp 命名残留 `m61m66`

实测 `workflowctl test matrix` 的 basetemp：

```
state/.pytest-tmp-m61m66/matrix-x0_c5f_r
```

M61-M66 闭幕之后还在用 `m61m66` basename。这是 [M48_M51_RECOVERY_PLAN.md §8.2](docs/archive/evaluations/M48_M51_RECOVERY_PLAN.md) "不让 M 编号继续膨胀"对应的"不让 M 命名残留在工具链上"。

修复（M67 候选）：basetemp 用通用名（`state/.pytest-tmp/matrix-{timestamp}-{hash}`）或当前 baseline（`state/.pytest-tmp-current/`）。

## 5. P2 问题（不阻塞，但应记入登记表）

### 5.1 `test_matrix.py` 在 `packages/core_domain/`

```
packages/core_domain/test_matrix.py  162 行
```

`test_matrix` 是 CI/dev 工具，不是领域逻辑。它依赖 subprocess 跑 pytest 命令——典型的 "infrastructure"，不是 "domain"。`apps/operator_cli/test_commands.py` 28 行作为入口已经够，实际逻辑应在 `infra/test_matrix.py`。

### 5.2 examples/local_task_cards/ 已 5 个，但没有 cluster / dogfood / multimodal 的 task card

5 个示例都是 doc / patch / projection / review / recovery 类。RECOVERY_PLAN 中 M48-M51 要求"5-10 个跨场景任务卡，包括 multimodal / failure-recovery"——multimodal 仍缺。

### 5.3 M48-M51 EXECUTION REPORT 极短（27 行），M52-M60 也只 45 行

对比 M61-M66 报告 63 行 + ISSUE REGISTER 25 行，**M48-M60 的执行细节被压缩得太狠**。如果未来要复盘"哪些 P0 真的修了"，27 行给不出可复核的 phase-by-phase 完成度。这和 §3.3 单 commit 一起，构成"半透明"的执行历史。

### 5.4 `LocalSchedulerLeaseArbiter` 与 `scheduler_authority` 文档边界未画

README.md / current_development_workflow.md 都没有解答：

- 如果开 `scheduler_authority_cluster_enabled=true`，`LocalSchedulerLeaseArbiter` 还跑不跑？
- 如果两者都跑，谁是真正的 lease 仲裁源？
- `scheduler_authority` 的 5 个 repository 在 flag off 时为什么仍要构造？是为了让"切回 cluster 模式时数据不丢"还是路径漏改？

### 5.5 `SUPPORTED_REPAIR_ACTIONS` 仍硬编码在 services.py 上

[`services.py:231-242`](packages/core_domain/services.py) 11 个 repair 动作仍是类常量。`service_repair.py` 714 行已存在，常量却没跟过去。这是拆分留下的一处"挂科"。

### 5.6 `chat_facade_lines <= 120` ratchet 卡死后续

`chat_runtime/__init__.py` 已 47 行。如果 M67+ 加 1 个 provider（比如 Gemini），facade 至少多 5 行 import + 1 个名字到 `__all__`。当前阈值 120 还有余量，但这种 ratchet 必须有"何时 raise 阈值"的明确规则，否则会变成"加新功能要先解 ratchet"的反向阻力。

## 6. 半真半假的声明（修辞校核）

| 文档原文 | 半真半假在哪 | 修辞建议 |
| --- | --- | --- |
| README "M61-M66 blocking open debt is zero" | 限定 "blocking" + "M61-M66 范围"，但容易误读为整体零债 | 改成 "M61-M66 范围内的计划债已清；3 项 carry-forward 见 §X" |
| M61-M66 ISSUE REGISTER 里 `M61-REL-001` 描述 "slow shard closeout still recommended" 但状态是 `repaid` | "still recommended" 还没做但已 `repaid` | 状态应为 `partially_repaid` 或新增独立条目 |
| M61-M66 EXECUTION REPORT "all-provider live probe passed" | 我只复测了 shell；MMX/Vertex/Claude/Codex/OpenCode/LangChain 6 个未独立验证 | 应附验证日期 + evidence path（probe artifact） |
| README "scheduler-authority names remain only for legacy compatibility" | 但 1650 行实现仍在 import path 上（cluster mode 时） | 应明确 "legacy 实现仍 1650 行；删除计划见 ADR-XXX" |
| M52-M60 EXECUTION REPORT "This pass does not claim the whole M52-M60 plan is fully retired" | 这句话**明确诚实**，但 README/milestone_history 提到 M52-M60 时简化成 "已吸收" | 应在 milestone_history 里保留"部分吸收 + carry-forward"的限定 |

## 7. M67+ 建议（不是新一轮拆，是收尾 + 节制）

> **核心原则**：M48-M66 已经做了大量结构改造。**M67+ 的主题不应是再开新拆分**，而是 **(a) 修补 M48-M66 留下的关键洞 + (b) 进入维护模式 + (c) 重新让真实功能开发主导**。

### M67：M66 收尾（不是新里程碑，是补丁）

**Phase 0**：把本评估的 7 个 P0/P1 修补做完

| Phase | 修复 | 风险 | 预估 |
| --- | --- | --- | --- |
| 0.1 | OperatorActionReceipt 加 `scope_hash`（写入 + 校验） | 极高 | 半天 |
| 0.2 | scheduler 5 个 repo 真正在 flag off 时不构造 + `SchedulerAuthoritySupportService` 也 lazy | 高 | 半天 |
| 0.3 | `local_game_artifacts.py` 真拆成 `block_puzzle.py` + `snake.py` | 低 | 1 小时 |
| 0.4 | chat_runtime facade `__all__` 移除下划线 helper | 低 | 30 分钟 |
| 0.5 | basetemp 改通用命名（去掉 m61m66） | 低 | 30 分钟 |
| 0.6 | tech-debt-registry / README 修辞校核（§6） | 低 | 1 小时 |
| 0.7 | M67 起恢复 1 phase 1 commit 纪律 | 纪律 | 持续 |

**M67 不能跨过**的事：

- 不开新 capability（即使有想法）
- 不开新 cluster
- 不重写 `repositories.py`（留作 M68 再决定，避免"刚拆完又拆"）

### M68：评估"是否还需要继续做拆分"

读完 M67 后再决定：

- 如果 `repositories.py 2359` 行真的造成开发阻力 → M68 做 Repository Bundle 拆分
- 如果不造成阻力（你和 codex 都不痛）→ **关闭 M 编号机制**，回到 unbounded local dogfood
- 如果中间状态 → 加一个非常薄的 ratchet `repositories.py <= 2400`，让它**只能瘦不能胖**，等真痛了再动

### 关于 milestone 编号节制（重要）

M40-M47 你已经吃过"M 编号膨胀"的亏（M44/M45/M46/M47 每个只是单 feature flag 或 doc 收口）；M48-M66 又一次跨 19 个 M 用一个 commit 关掉。这两次模式都是**M 编号变得很廉价，但单 M 的真实含金量不一致**。

建议从 M67 起：

1. **每个 M 至少 3 个独立 commit**（1 phase 1 commit 是好习惯）
2. **每个 M 必须能用 `git log v0.{N-1}..v0.{N}` 看到 phase-by-phase 变化**
3. **如果一个 M 想做的事 1 天能做完，不开 M，直接做并 squash 到 main 即可**（M 编号不是"今天我要做事的标签"）
4. **包版本号 (`pyproject.toml: version`) 要和 milestone_history 同步前进**——M66 已经 `0.66.0`，但中间没有 0.48.0 / 0.50.0 / 0.60.0 等中间版本。如果 M67 是补丁，应该是 `0.67.0`；如果 M67 是 patch-of-M66，应是 `0.66.1`。

## 8. 评估方法附录

实际跑过的命令：

```bash
# 静态规模
find packages apps -name "*.py" | xargs wc -l | sort -rn | head -30
grep -c '^    def ' packages/core_domain/services.py        # 99
grep -c '^    def ' packages/core_domain/service_interaction.py  # 0（只有 14 行 facade）

# 动态验证
workflowctl test matrix --suite unit                         # 52 passed in 16.26s
workflowctl test matrix --suite core                         # 87 passed in 79.11s
workflowctl capability probe --provider shell --require-live # status=verified_ready
workflowctl --db-path state/workflow.db doctor --strict      # status=ok
python -m infra.scripts.check_doc_links                      # 0 issue, 6 docs

# 关键路径校核
grep -rn "X-Operator-Action-Receipt" apps/orchestrator_api/routers/   # 7 处
grep "scope_hash" packages/core_domain/service_operator_action_guard.py  # 0 命中
git log --oneline | head -5                                  # 11be07b 包了 19 个 M
```

代码读取覆盖：

- `packages/core_domain/{services, service_operator_action, service_operator_action_guard, capability_probe, repositories, models}.py`
- `packages/runtime_langgraph/chat_runtime/{__init__,...}.py`
- `apps/orchestrator_api/{main, routers/runs}.py`
- 全部 5 份历史 EXECUTION/REGISTER 文档
- `tests/test_service_decomposition.py`
- README + milestone_history + tech-debt-registry

未覆盖（不影响结论）：

- `tests/test_operator_action_receipt.py` 内部断言（已知 5.69s 跑过，但具体是不是测了 scope_hash 缺失场景未读）
- 实跑 codex/opencode/mmx/vertex/claude/langchain 6 个 provider 的 live probe（README 声称跑过，evidence 在 `state/m61_m66_execution/capability_probes/` 但未独立复核）
- web_ui_components.py 875 行内部细节
- `.github/workflows/ci.yml` 内部脚本

## 9. 一句话给你

> **M48-M66 你和 codex 真的把绝大部分 P0/P1 修了**——这一轮可以为自己鼓掌一次。但 **`scope_hash` 缺失、scheduler 仍在 boot path 上、1 个 commit 装 19 个 M、整体代码净膨胀 3600 行**——这 4 件事说明结构纪律在拆分本身上做得比拆分背后的"治理"做得好。M67 不该再开新主题，应**用 1-2 周做完§7 的 7 个补丁**，然后 **关掉 M 编号机制**，让项目重新进入"想做新事就做"的轻量节奏。
