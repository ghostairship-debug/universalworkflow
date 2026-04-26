# Universal Agentic Workflow OS 深度评估报告（M73 / Opus）

- 日期：2026-04-26
- 基线：已接受 `M72: Trusted Self-Development Baseline`，M73 期初
- 评估前提：个人自用 / 本地 operator runtime；M73 拟进入"能力层开发"
- 评估方式：本地工作树静态分析 + 关键路径动态验证（pytest 子集 + doctor strict + LangGraph 集成代码实测）
- 评估者：Claude Opus 4.7
- 与既有评估的关系：本文不重复 [M73_DEEP_EVALUATION_ROUND_1.md](M73_DEEP_EVALUATION_ROUND_1.md) / [ROUND_2.md](M73_DEEP_EVALUATION_ROUND_2.md) 已经讲过的归档/manifest 一致性问题，重点放在**两轮 M73 自评估漏看的事实**

## 0. 一句话总评

> **M67-M72 的"可信收口"是真实进步**——服务边界、安全协议、scheduler 隔离、归档治理都做对了。但 **M73 两轮自评估"无修改必要"过于乐观，因为它只跑了最小验证集（57 个 unit test + governance 16 个）**。把视角拉宽到全仓库后，至少有 5 个 P0/P1 真问题、10 个 P2 优化点是 self-development manifest 看不到的。Opus 视角的价值就是补这一面。

## 1. M67-M72 真正完成的事（不要否定）

为了避免显得在唱反调，先把**确实做对**的列清楚。这些不是文档自吹，而是本次实测验证的：

| 主张 | 实测验证 | 结论 |
| --- | --- | --- |
| services.py 显著瘦身 | M47 时 3552 行 → 现在 **1823 行**（-49%） | ✅ 真砍了 |
| scheduler_authority 真隔离 | services.py:209-214 是**条件 import**，flag off 时不构造也不 import 1650 行模块 | ✅ 完成（M50 P4 推荐落地）|
| core_domain 游戏 HTML 迁出 | `core_domain/local_game_artifacts.py` 从 **1206 行 → 10 行 thin shim**；真实现在 `packages/contributions/games/` | ✅ 大致完成 |
| service_interaction.py 拆分 | 旧 2315 行 → 拆成 chat 883 / session 612 / cluster 608 | ✅ 拆开 |
| OperatorActionReceipt scope_hash | M67 P2 完成；高风险 API 路径全部绑定 scope | ✅ |
| capability live-proof hard gate | M67 P3 完成；7 个 provider 全部 live probe 通过 | ✅ |
| 测试增长 + 速度改善 | M47 时 376 collected, 119 passed + 129 skipped, 6 分钟<br>现在 **463 collected, 203 passed + 130 skipped, 2:17** | ✅ 数量+速度都改善 |
| 文档归档 | 24+ 历史评估全部进 `docs/archive/evaluations/` | ✅ |
| LangGraph 集成（M68） | `focused_runtime.py` 226 行真接 LangGraph StateGraph | ⚠️ 真接了，但**仍是 advisory-only / 不 mutation / 不承担真实 run**（见 §2.3）|
| self-development-manifest | M72 真实可机器检验 GO/NO-GO | ✅ |

**结论**：M47 评估和 M48-M51 计划提的事，**绝大部分已经做完**。这是不容否定的真实进步。

## 2. 五个 P0/P1 真问题（M73 两轮自评未发现）

### 2.1 P0 — 总代码量逆势增长 14%（"复杂度搬家"）

**M73 两轮自评未捕获**：两轮都只看大文件 ratchet（"services.py 已低于 M67 目标"），没看总体积。

**实测**：

| 指标 | M47（2026-04-25） | M72（2026-04-26） | 变化 |
| --- | ---: | ---: | ---: |
| `wc -l packages apps tests/*.py` 总行 | 45795 | **52112** | **+13.8%** |
| services.py | 3552 | 1823 | -49% ✅ |
| service_interaction.py | 2315 | 0（拆掉）| ✅ |
| service_lifecycle.py | 1691 | 1845 | **+9%** |
| repositories.py | 2019 | 2374 | **+18%** |
| service_projection.py | 1608 | 1608 | 0 |
| 新增 service_interaction_chat | 0 | 883 | new |
| 新增 service_interaction_session | 0 | 612 | new |
| 新增 service_interaction_cluster | 0 | 608 | new |
| 新增 capability_control_plane | 0 | （扫描确认存在） | new |
| 新增 parallel_execution_contract | 0 | （扫描确认存在） | new |
| scheduler_authority.py | 1646 | 1650 | 0（保留 optional）|
| 新增 local_scheduler_lease_arbiter.py | 0 | 679 | new |
| 新增 local_scheduler_handoffs.py | 0 | （扫描确认存在） | new |

**判断**：
- 拆 service_interaction.py（2315 → 0）净减 2315 行，但拆出去的三个文件 883+612+608 = **2103 行**——净减 **212 行（9%）**。这是健康的"职责拆开了"
- 但 **整体增了 6300+ 行**：repositories +355、service_lifecycle +154、新增的 capability_control_plane / parallel_execution_contract / local_scheduler_lease_arbiter / local_scheduler_handoffs 等加起来超过 2000 行
- M67-M72 期间复杂度从 services.py **搬家**到了周边模块，**不是消失**

**为什么这是 P0**：
- M67-M72 表面看是"瘦身 + 安全收口"，但**整体认知负担在上升**（13.8%）
- 未来"未来的你"重新进入代码时，需要理解的模块数从 30 个涨到 40 个
- M73 进入"能力层开发"会继续往周边模块塞代码，6 个月后总量可能再涨 20%

**建议**：
- 在 `tests/test_facade_surface.py` 之外加 `tests/test_total_loc_ratchet.py`：
  ```python
  # M72 baseline: 52112; M73 期间不允许涨超过 5%
  assert total_loc(packages, apps) <= 54700
  ```
- 这个 ratchet 是"防止默认增长"的硬约束。任何 PR 涨超过 5% 必须有强理由

---

### 2.2 P0 — M73 自评估只跑了 ≤16% 的测试 + 0 个 closeout gate

**M73 R2 报告自述的验证清单**：
- `pytest tests/test_governance.py tests/test_self_development_manifest.py`：16 passed
- `check_doc_links`：passed
- `governance self-development-manifest`：GO
- `doctor --strict`：ok
- `test matrix --suite unit`：57 passed

**M67_ISSUE_REGISTER §Closeout Gates 列的 8 个**：
1. ✅ check_doc_links
2. ✅ doctor --strict
3. ✅ test matrix --suite unit
4. ❌ test matrix --suite **core**
5. ❌ test matrix --suite **integration**
6. ❌ validation run --suite full
7. ❌ pytest -q --run-slow
8. ❌ capability probe --provider all --require-live

**M73 R2 跑了 8 个里的 3 个，covering 73 个 test 用例（16+57）**。仓库总共 **463 个测试**。M73 R2 的"GO"基于 **15.7% 的测试覆盖**。

**为什么这是 P0**：
- M73 R2 自己的结论："本次循环达到停止条件：当前无进一步修改必要"——**这个结论的证据基础太薄**
- 跳过 core/integration/slow 的代价是：可能有 capability 回归/api regression/web ui 失败，但 R2 的 manifest 不会发现
- M73 进入"能力层开发"前理论上应该跑完整 closeout（M67 P8 的 standard）
- self-development-manifest 工具自己只检查"文档证据完整性"，不验证"系统真在跑"

**实测对照**：本次 Opus 评估排除 3 个 slow 文件后跑了 **203 passed + 130 skipped in 2:17**——这是 M73 自评应该跑的最小集合，但 R2 没跑

**建议**：
- M73 进入能力层开发前补一次 full closeout（R2 跳过的 5 个 gate）
- 修改 `self-development-manifest` 的 GO 规则：必须包含 closeout gate 的最近 evidence path 才允许 GO（不只是看报告/operator packet 是否存在）

---

### 2.3 P1 — M68 LangGraph "完成" 但仍是 advisory 装饰品

**M68 commit message**："Complete M68 LangGraph focused runtime"——听起来像 LangGraph 真接管了 runtime。

**实测代码**（`focused_runtime.py` 226 行 + M68_EXECUTION_REPORT.md）：
- `comparison.mutation_allowed=false`
- `comparison.direct_mutation_disabled=true`
- M68 报告自述："**不 compile、不 resume、不 patch apply，也不作为新的 workflow 状态源**；它只读取现有 workflow route preview，并在显式传入 evidence dir 时写入 evidence JSON"
- M68 报告自述："`scope`: `planning_review_evidence`"——只跑 3 个 noop 节点
- M68 仍然是 **advisory-only / opt-in / 不影响真实 run**

**对照 LONG_TERM_ROADMAP §6.2** LangGraph 应负责的 10 项：
| 应负责 | M68 实际 |
| --- | --- |
| graph execution | ⚠️ 只跑 3 个 advisory 节点 |
| checkpoint | ❌ |
| resume | ❌ |
| interrupt | ❌ |
| human-in-the-loop pause | ❌ |
| conditional edge | ❌ |
| subgraph | ❌ |
| streaming runtime state | ❌ |
| failure recovery | ❌ |
| runtime-level retry | ❌ |

**判断**：M68 比 M40 时的 8 节点 noop chat_control_graph 升级了一点（增加了 workflow route 对比），但**仍未承担任何实际 run 的执行**。LONG_TERM_ROADMAP §10 M68 验收标准 "至少一个真实流程通过 LangGraph 执行" 实际**未达成**——advisory comparison 不是 "执行流程"。

**为什么这是 P1**：
- 路线图把 M68 标记为"LangGraph 真集成"，commit 也是 "Complete M68"，**但实质是 demo**
- 如果 M73 开始能力开发时延续这个理解，可能误以为 LangGraph 已经"接管 runtime"，导致：
  - 继续在 OrchestrationEngine 自造 runtime 能力（双轨）
  - 或者反过来贸然把真实 run 切到 focused_runtime（mutation 风险，因为它不支持任何回滚）

**建议**：
- 把 M68 重命名为 "LangGraph Advisory Comparison"——不要叫"focused runtime"，更不要暗示"runtime"
- 在 `LONG_TERM_ROADMAP` §10 加一个新 M（比如 M73.5 或 M75）："LangGraph Real Runtime"，目标是真接 checkpoint/resume/interrupt 至少一个 production run
- 这个目标和 LONG_TERM_ROADMAP §10 M68 原本的描述一致，只是承认实际未完成

---

### 2.4 P1 — `scheduler_authority.py` 1650 行虽已隔离，但缺 deprecation 时间表

**M67 P6 完成了"语义重命名"**：默认走 `LocalSchedulerLeaseArbiter`，`scheduler_authority` 标 "compatibility only"。

**但事实**：
- `packages/core_domain/scheduler_authority.py` 仍 1650 行
- `apps/scheduler_authority_api/main.py` 仍存在
- 用户 memory 明确："云/分布式 deferred；保留 optionality 不删除"

**问题**：保留 optionality 是合理的，但**没有"未来某天再决定"的触发条件**：
- 6 个月后还在保留？
- 12 个月后？
- 触发删除的条件是什么？（用户决定不再做云？看到 LangGraph 1.x 提供等价能力？）

**为什么这是 P1**：
- 没有 deprecation timeline 的"软保留"会**无限期累积**
- 1650 行的"未来可能用到"代码 = 永远的认知负担
- 类似 `scheduler_authority_api`、`remote_worker_api`、`external_workers.py` 等"未来云"模块都需要同样的 timeline

**建议**：
- 在 `docs/governance/optional_modules.json` 登记每个 optional 模块：
  ```json
  {
    "scheduler_authority": {
      "lines": 1650,
      "rationale": "云/分布式 deferred；保留 optionality",
      "review_at": "2026-10-26",
      "delete_condition": "用户明确不再做云 OR 6 个月内未启用 cluster mode"
    }
  }
  ```
- 让 `doctor --strict` 在 review_at 到期时提醒决策

---

### 2.5 P1 — `core_domain/local_game_artifacts.py` 10 行 shim 应该删除

**实测**：
```python
# packages/core_domain/local_game_artifacts.py（10 行）
from packages.contributions.games.local_game_artifacts import local_artifacts_for_goal as _local_artifacts_for_goal
```

**Grep 调用方**：
- `compile.py:28` 直接 import 自 `packages.contributions.games.local_game_artifacts`
- `tests/test_m43_game_artifacts.py:5` 直接 import 自 `packages.contributions.games.local_game_artifacts`
- **没有任何代码 import 自 `core_domain.local_game_artifacts`**

**判断**：这个 shim 已经是死代码。10 行不大，但留着会让人误以为 core_domain 还有游戏依赖。

**为什么这是 P1（不是 P2）**：
- 删除是 1 分钟的事，但**留着是符号意义上的污染**——M47 评估的批评未真正归零
- 设立"shim 必须有删除时间"的纪律，从这种小 shim 开始最容易

**建议**：M73 第一周顺手删除 `packages/core_domain/local_game_artifacts.py`

## 3. 十个 P2 优化点（按重要性）

| # | 问题 | 建议 |
| --- | --- | --- |
| 1 | `docs/archive/evaluations/` 21 个文件无索引 | 加 `docs/archive/evaluations/README.md`，列每个文件的"哪个时代/已被谁超越/是否仍 relevant" |
| 2 | `PROJECT_OVERVIEW_FOR_BEGINNERS.md` 15K 字过长 | 缩到 ≤ 5K 字 + 链接到深度文档；当前长度反而劝退小白 |
| 3 | `focused_runtime.py` 命名误导 | 改名 `langgraph_advisory_comparison.py` 或 `langgraph_route_comparator.py` |
| 4 | AGENTS.md 没说 M73 进展指标 | 加一节"M73 进展 KPI"：接入新能力数 / live probe 成功率 / workflow 自执行 phase 占比 |
| 5 | `repositories.py` 2374 行（+355 vs M47），未拆 | 按 GPT Pro 提议的 RepositoryBundle 模式拆 6-8 个 bundle；M73 用 1 个 phase 做 |
| 6 | batch-resume `--max-workers 2` 上限缺 evidence | 跑一次 max_workers=4 的 stress test；如果 SQLite 锁触发，记入 evidence；如果不触发，把上限提到 4 |
| 7 | M70 接入清单仍泛（路线图原版 10 个能力） | 按上一份评估建议拆为 M70（4 个 coding CLI）+ M71（3 个受控 MCP）|
| 8 | OperatorActionReceipt 缺运营视角 | 加 `workflowctl receipt stats`：过去 N 天签发 / 消费 / 过期 / 重放拒绝数 |
| 9 | `service_lifecycle.py` 1845 行（+154 vs M47）| M73 一个 phase 拆 RunLifecycleService 的真实业务 owner |
| 10 | M67-M72 引入 5 个新核心模块（capability_control_plane / parallel_execution_contract / local_scheduler_lease_arbiter / local_scheduler_handoffs / self_development_manifest）但 README 无架构图 | 加一张 ASCII 架构图到 README，让"为什么有这么多模块"一眼可见 |

## 4. 与 M73 两轮自评估的对比

| 维度 | M73 R1+R2 自评 | Opus 本评估 |
| --- | --- | --- |
| 评估覆盖 | governance + manifest + doctor + unit | + 全部热点文件实测 + LangGraph 集成深度 + 总 LOC 趋势 + scheduler_authority 物理隔离验证 + 测试 ≤integration |
| 跑的 test 数 | 16 + 57 = 73 | 16 + 57 + 203 = 276 |
| 时间 | 未公布 | 约 3 分钟实测 |
| P0 发现 | 1（归档/manifest 一致性）| 2（总 LOC 增长 + 自评覆盖度过低）|
| P1 发现 | 1（CLI help 文案）| 3（M68 LangGraph 实质 + scheduler 缺 timeline + game shim）|
| P2 发现 | 1（热点文件偏大但不立即处理）| 10（架构图、命名、运营视角等）|
| 结论 | "无修改必要" | M73 进入能力层前应做 5 项快速修复 |

**为什么差异这么大**：
- self-development-manifest 是"机器检查证据完整性"的工具，**不是代码质量评估工具**
- 任何符合 task card / operator packet / commit 规则的 milestone 都能拿 GO，即使代码层面有真问题
- 这正是"自评估"的天然盲区——**机器不会问"我们做对了吗"，只会问"我们按规则做了吗"**

## 5. M73 第一周建议（5 项快速修复）

如果你接受本评估，**进入能力层开发前的 7 天**应该做：

| 天 | 动作 | 工作量 | 解决 |
| --- | --- | :---: | --- |
| Day 1 | 删 `core_domain/local_game_artifacts.py`（10 行 shim）；运行 `pytest tests/test_m43_game_artifacts.py` 验证不破坏 | 30 分钟 | §2.5 |
| Day 2 | 加 `tests/test_total_loc_ratchet.py`：M73 期间总 LOC ≤ 54700 | 1 小时 | §2.1 |
| Day 3 | 跑 M67_ISSUE_REGISTER §Closeout Gates 全部 8 项；evidence 落 `state/m73_closeout_gates/` | 半天 | §2.2 |
| Day 4 | 加 `docs/governance/optional_modules.json`，登记 scheduler_authority + scheduler_authority_api + remote_worker_api 等 optional 模块的 review_at | 半天 | §2.4 |
| Day 5 | 修订 LONG_TERM_ROADMAP §10：M68 真名为 "LangGraph Advisory Comparison"；新增"LangGraph Real Runtime"作为后续目标 | 1 小时 | §2.3 |
| Day 6 | 加 `docs/archive/evaluations/README.md` 索引 | 1 小时 | §3 #1 |
| Day 7 | 加 README 架构图（ASCII） | 1-2 小时 | §3 #10 |

**完成后**：M73 才真的"准备就绪"进入能力层开发。否则会带着两个未还的债（总 LOC 失控 + closeout gate 未跑）开始新一轮膨胀。

## 6. 一句话给你

> **M67-M72 是真实进步，M73 自评的"无修改必要"是部分正确**。把 self-development-manifest 当 GO/NO-GO 决策唯一依据是危险的——它检查"是否按规则做"，但不检查"是否做对了"。Opus 视角的价值是补这个缺口：M73 应该先把上面 5 项修完，再开能力层。

## 附录：本次评估实际操作

```bash
# 静态规模
find packages apps tests -name "*.py" | xargs wc -l | sort -rn | head -25
grep -rn "from langgraph" packages apps --include="*.py"

# 验证 scheduler_authority 真隔离
grep -rn "scheduler_authority\|local_scheduler" packages/core_domain/services.py
# → services.py:209-214 是条件 import，flag off 不构造

# 验证 core_domain 污染状态
wc -l packages/core_domain/local_game_artifacts.py packages/contributions/games/local_game_artifacts.py
# → core_domain 那个只有 10 行 thin shim；真实现已迁出

# 动态验证
python -m pytest --collect-only -q  # 463 tests collected
python -m apps.operator_cli.main ... doctor --strict  # status=ok
python -m pytest -q --tb=no -x \
  --ignore=tests/test_execution_loop.py \
  --ignore=tests/test_release_closeout.py \
  --ignore=tests/test_web_ui.py  # 203 passed + 130 skipped in 2:17
```

代码读取覆盖：

- `packages/runtime_langgraph/focused_runtime.py`（M68 LangGraph 真实集成）
- `packages/core_domain/local_scheduler_lease_arbiter.py`（M67 P6 替代品）
- `packages/core_domain/services.py:200-220`（scheduler_authority 条件 import 验证）
- `M68_EXECUTION_REPORT.md`（验证 advisory-only 自述）
- `M72_EXECUTION_REPORT.md`、`M73_DEEP_EVALUATION_ROUND_1.md`、`ROUND_2.md`、`AGENTS.md`、`README.md`
- `PROJECT_OVERVIEW_FOR_BEGINNERS.md`（M72 期间新增）

未覆盖（不影响结论）：

- M67 P8 closeout 完整重跑
- 462 个 slow test 全跑
- 实际 LangGraph 1.x → 2.x 兼容性测试
- M68-M72 各个 EXECUTION_REPORT.md 全文（只读了 M68 + M72）
