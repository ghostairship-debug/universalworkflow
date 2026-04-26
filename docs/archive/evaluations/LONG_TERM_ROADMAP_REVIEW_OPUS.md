# 长期路线图评估（Opus）

- 日期：2026-04-26
- 评估对象：[LONG_TERM_ROADMAP_universalworkflow.md](LONG_TERM_ROADMAP_universalworkflow.md)（1064 行，2026-04-26 01:27）
- 评估者：Claude Opus 4.7
- 评估方式：路线图全文阅读 + 与 [M67_EXECUTION_REPORT.md](M67_EXECUTION_REPORT.md)、[M67_ISSUE_REGISTER.md](M67_ISSUE_REGISTER.md)、[AGENTS.md](AGENTS.md)、[AGENTS_M67_universalworkflow.md](AGENTS_M67_universalworkflow.md) 对账，加 `OrchestrationEngine` / `chat_control_graph` / `durable_pilot` 实测交叉验证
- 与上一份评估的关系：本文不重复 [PROJECT_DEEP_EVALUATION_M66_OPUS.md](PROJECT_DEEP_EVALUATION_M66_OPUS.md) 已经讲过的结论，重点放在 **路线图本身的判断、缺口、与当前 M67 真实状态的对接问题**

## 0. 一句话结论

> **战略立场完全正确，战术执行序列与 M67 真实进度脱节**。control tower + Build-vs-Buy 是项目当下最需要的纪律，但路线图把"M67 收口立规矩"作为下一步——而 M67 实际上 P0/P1/P2/P3 已 completed、P4-P8 仍 pending，路线图描述的 M67 任务（10 项）和 [M67_ISSUE_REGISTER.md](M67_ISSUE_REGISTER.md) 的 7 个 blocking_open **没有对照**。落到执行时会产生"M67 究竟还有多少没做"的混淆。

## 1. 路线图做对的（不要动）

| 做对的判断 | 价值 |
| --- | --- |
| **定位为 control tower 而非 framework** | 解决了项目最大的认知漂移；过去 M40-M47 编号膨胀的根因就是没有这个边界 |
| **Build-vs-Buy 三档覆盖度规则**（≥70% 引入 / 40-70% spike / <40% 自研） | 提供了可操作的判断框架，避免"AI 顺手补一点"导致的无意识自研膨胀 |
| **明确 LangGraph 作为 runtime substrate 而非全部接管** | 与我之前 §3 评估"小聚焦集成"完全一致；保住了 receipt / mutation / review / capability ledger 这 8 个领域协议 |
| **20 项必须自研 + 10 项不应继续自研的双清单** | 消除模糊性；后续 PR 可以直接对照判断 |
| **Build-vs-Buy 模板（§11.3）** | 可以直接挂到 PR template / commit message footer，把纪律变成肌肉记忆 |
| **MCP 5 级风险分级 + per-task projection** | 防止 token 爆炸和默认全量暴露；这是 MCP 接入的正确姿势 |
| **冻结自研 runtime 大功能（§13 第三）** | 这是路线图里最值钱的一句话，应该立刻挂到 AGENTS.md |

## 2. 关键差距（按优先级排）

### P0 — 必须修，否则路线图会执行不动

#### 差距 1：M67 章节与现实脱节

**事实**：路线图 §10 M67 列了 10 项任务（更新 AGENTS.md / 增加 LANGGRAPH_OVERLAP_INVENTORY.md / 增加 EXTERNAL_CAPABILITY_MAP.md / ... / 完成 high-risk action boundary 修复 / 建立 PolicyEngine 最小骨架 / 建立 AutomationLease 最小骨架 / ...）。

**实际**：[M67_EXECUTION_REPORT.md](M67_EXECUTION_REPORT.md) 显示 M67 已经定义了 P0-P8 八个 phase，并且 P0/P1/P2/P3 已 completed：

| 路线图 §10 M67 任务 | M67 真实 phase 对应 | 状态 |
| --- | --- | --- |
| 更新 AGENTS.md | （已存在，仍可补充 control tower 段落） | partial |
| 增加 LANGGRAPH_OVERLAP_INVENTORY.md | 不在 P0-P8 中 | not started |
| 增加 EXTERNAL_CAPABILITY_MAP.md | 不在 P0-P8 中 | not started |
| 明确停止/保留自研清单 | 不在 P0-P8 中 | not started（路线图本身就是这个清单） |
| 完成 high-risk action boundary 修复 | M67 P2 | **completed** |
| 建立 PolicyEngine 最小骨架 | M67-AUTO-001（仍 blocking_open） | partial |
| 建立 AutomationLease 最小骨架 | M67-AUTO-001 | partial |
| capability live-proof | M67 P3 | **completed**（路线图未提，但已做） |
| validation/CI reliability | M67 P4 | pending |
| Web/CSP hardening | M67 P5 | pending |
| scheduler boot path | M67 P6 | pending |
| hot-file slimming | M67 P7 | pending |
| workflow E2E closeout | M67 P8 | pending |

**修复建议**：把路线图 §10 M67 章节改为"M67 已在执行，参见 M67_ISSUE_REGISTER；本路线图的 M67 任务作为 **补充**（以下 4 项）：(1) 把 control tower 定位写入 AGENTS.md §1；(2) 创建 LANGGRAPH_OVERLAP_INVENTORY.md；(3) 创建 EXTERNAL_CAPABILITY_MAP.md；(4) 把 §11.3 Build-vs-Buy 模板挂到 `.github/PULL_REQUEST_TEMPLATE.md`"。剩下 6 项已经在 M67 P0-P8 内或部分完成。

---

#### 差距 2：M68 LangGraph 集成时序过早

**事实**：路线图 §10 把 M68 = LangGraph 真集成放在 M67 收口之后。

**问题**：M67 P7 hot-file slimming（M67-ARCH-001）和 LangGraph 集成有强耦合——`OrchestrationEngine.build_graph_from_plan` 依赖 `OrchestrationPlan` / `OrchestrationStep`，而后者在 `service_orchestration.py` / `services.py` 内。**P7 没做完前做 M68，会把 LangGraph 接到一个还在拆分中的 service 上**，等 P7 拆完所有路径都得改一次。

**修复建议**：把 M68 改为"**M67 P7 收口后、立即开始**"，而不是开新 M。LangGraph 集成本身可以是 M68 P0-P3，但**前置依赖** M67-ARCH-001 已 repaid。在路线图 §10 M68 入口段加一行：`Entry gate: M67-ARCH-001 status=repaid AND M67 P8 GO`。

---

#### 差距 3：M70 接入清单过宽（10 项），违反路线图自己的纪律

**事实**：路线图 §10 M70 列了 10 个外部能力要在一个 milestone 接入：Codex CLI / Claude Code / Gemini CLI / OpenCode / readonly workspace MCP / web search MCP / GitHub MCP / Playwright / Figma/Canva / image-audio-video API。

**问题**：
- 这违反路线图自己的 §3.3"成熟方案能承担一个清晰大板块时引入；提供零碎小功能时谨慎"——10 个能力中 GitHub MCP / Figma / 媒体 API 都是零碎小功能
- 一个 M 接 10 个能力会回到 M40-M47 "广而薄"的老路
- 路线图 §13 第三说"冻结自研 runtime 大功能"，但如果同时接入 10 个外部能力，每个都要写 adapter，**adapter 写多了就是新的"自造 framework"**

**修复建议**：把 M70 拆为两个 milestone：
- **M70 Coding CLI 收敛**：只接 Codex / Claude Code / Gemini CLI / OpenCode 4 个 coding agent，用统一 CLI Adapter Contract（已经在 AGENTS_M67 §3.4 有雏形）。验收：4 个 CLI 能跑同一个 task card
- **M71 受控外部能力（可选）**：readonly workspace MCP + web search + Playwright。Figma / 媒体 API / GitHub MCP **不进 M71**，等到 M72 业务闭环真需要时再按需接入

---

### P1 — 应该修，会显著改善执行体感

#### 差距 4：缺少 M68 失败回滚预案

路线图 §10 M68 只写"不做什么"（不删 contracts、不让 LangGraph 接管 receipt），没说"如果 LangGraph 集成 spike 失败会怎样"。

LangGraph 1.x 还在快速演进（每月小版本），把核心控制流绑到外部库是有版本风险的。

**修复建议**：M68 加一节"Exit Criteria"：
```
M68 失败回滚条件：
- LangGraph spike 在 2 周内未达成"checkpoint resume + interrupt"双向验证 → 回到 M67 状态，本次集成视为"已知不可行"，记入 EXTERNAL_CAPABILITY_MAP.md
- LangGraph 1.x → 2.x breaking change 触发回归 → LangGraphRuntimeAdapter 自动 fall back 到 LegacyWorkflowRuntime
- 任何 receipt / mutation / review 测试在 LangGraph 路径上回归 → P0 立即停止，不进入下一 phase
```

---

#### 差距 5：M71 Cluster 列表（7 个）与"不自研 multi-agent framework"自相矛盾

**事实**：
- 路线图 §5 第 8 项："不应继续自研 通用 multi-agent framework"
- 路线图 §10 M71 列了 7 个 Cluster：Planner / Research / Architecture / Code / Review / Multimodal / Management

**问题**：cluster 本质就是 multi-agent framework 的一种形态。说"不自研 multi-agent framework"但又"自研 7 个 cluster contract"是矛盾的。

**修复建议**：明确区分两层：
- **Cluster Contract**（输入/输出/能力/验收/handoff packet）= 自研，是项目的领域协议
- **Cluster Execution**（实际跑 cluster 内部的图）= LangGraph subgraph 接管

在路线图 §9.4 已经有"cluster 内部可以是 LangGraph subgraph"，但 §5 / §10 M71 没强调这一点。建议在 M71 加一句："Cluster Contract 自研；Cluster Execution 走 LangGraph subgraph，不自造执行引擎"。

---

#### 差距 6：M72 业务闭环锁定 H5 游戏过窄

**事实**：路线图 §10 M72 列了 11 步全部围绕 H5 小游戏（玩法分析 → 美术升级 → 音效生成 → ... → 商业化质量报告 → 打包产物）。

**问题**：
- 项目的真实使用场景更广：本地 task card → bounded patch、PDF→artifact、operator dogfood、capability live probe、长程开发任务
- 把 M72 锁到 H5 游戏，会让其他真实场景被边缘化
- 而且当前项目的 dogfood 主要是"用 workflow 修 workflow"（M67 AGENTS.md 明文），不是"用 workflow 做游戏"

**修复建议**：M72 改名"**业务闭环打穿（操作者优先）**"，给两条候选闭环：
- **闭环 A：Workflow Self-Development**（首选）：用 workflow 自己执行 M68-M71 的全部 phase；验收 = M68-M71 中至少 50% phase 由 workflow 完成
- **闭环 B：H5 小游戏**（次选 / 演示用）：保留路线图原版 11 步，但作为"对外展示"而非主要交付

把"workflow 修 workflow"放在 M72 主线，能让 M67 AGENTS.md 的 dogfood 承诺从"M67 一次性"变成"M67-M72 持续"。

---

#### 差距 7：覆盖度规则的"≥70% 引入"过于绝对

**事实**：路线图 §3.2 说"外部成熟方案覆盖一个板块 ≥70% → 优先引入/包装"。

**问题**：有些场景外部方案覆盖 80%，但你需要的恰好是不覆盖的 20%。比如 LangGraph 提供 80% 的图执行 + checkpoint，但缺的 20%（OperatorActionReceipt scope_hash 校验、mutation contract 的原子回滚）恰好是项目核心差异化。这种情况引入 LangGraph 反而会被框架的 callback 模型限制。

**修复建议**：在 §3.2 加一条补充规则：
```
即使外部方案覆盖 ≥70%：
- 缺的部分如果属于"必须自研"清单 → 仍然引入，但用 thin adapter 隔离
- 缺的部分需要修改外部方案才能补 → 不引入，自研
- 缺的部分需要 fork → 不引入，自研
```

---

### P2 — 可以修，让路线图更耐用

#### 差距 8：缺少 LangGraph 版本风险

风险矩阵 §12 列了 9 个风险，但**没有列 LangGraph 1.x → 2.x 升级带来的回归**。LangGraph 1.0 才发布几个月，breaking change 概率不低。

**修复建议**：风险矩阵加一行：
```
LangGraph 升级中断 workflow | 中高 | 1.x→2.x 可能 breaking | LangGraphRuntimeAdapter 用 thin wrapper；锁版本到 minor；准备 LegacyWorkflowRuntime 回滚路径
```

---

#### 差距 9：CLI Adapter Contract 缺少"何时用 Codex vs Claude Code"决策模型

路线图 §8.3 列了 6 个 adapter，但没说"什么任务该路由到哪个 CLI"。

当前 dogfood 默认用 Codex，但项目实际还有 Claude Code（用户用我做评估就是例子）、Gemini CLI、OpenCode。M70 接入 4 个 coding CLI 后，如果没有路由策略，会变成"每次手动选 / 全靠 fallback"。

**修复建议**：M70（重新拆分后）加一个 phase："CLI Selection Policy"。基于：
- 任务类型（patch_apply / artifact_only / chat_assist / review）
- 模型成本（Codex gpt-5 vs Claude Sonnet vs Gemini Pro 不同）
- 历史成功率（capability_invocation ledger 的 readiness 分级）
- 上下文窗口（不同 CLI 上下文窗口不同）

输出一张 routing decision table，写入 `infra/seeds/cli_routing.yaml`。

---

#### 差距 10：MCP Broker canonical tool ID 缺迁移路径

路线图 §7.3 提议 `mcp:{profile_id}:{tool_name}`，但没说现有 MCP tool 怎么从旧名字过渡。

**修复建议**：M69 加 sub-phase "MCP Tool ID Migration"：
- 第一阶段：双重 ID（旧名字 + canonical ID 都接受）
- 第二阶段：所有内部代码切到 canonical ID
- 第三阶段：旧名字标 deprecated；6 个月后移除

---

#### 差距 11：Build-vs-Buy 模板缺"已有自造代码的回收路径"

路线图 §11.3 模板只考虑"新增功能"决策，没有"已有自造代码的回收"。比如 `OrchestrationPlanGraph` 已经存在，按新规则应该让 LangGraph 接管，但模板里没有这个分支。

**修复建议**：模板加一节：
```
## Existing Code Path

如果该能力已经有自造代码：
- [ ] 完全替换为外部方案（删除自造代码）
- [ ] thin adapter 包装外部方案，自造代码作为 fallback 保留
- [ ] 自造代码与外部方案并行（两套实现）
- [ ] 不动（自造代码够用，外部方案不引入）
```

---

#### 差距 12：缺数字化进展指标

每个 M 有"验收标准"但都是 yes/no。比如 M68"至少一个真实流程通过 LangGraph 执行"——一个就够了？10% 的流程？

**修复建议**：每个 M 加 1-2 个数字化 KPI。例如：
- M68：≥30% 的 run 通过 LangGraphRuntimeAdapter 执行；≥1 次 checkpoint resume 在生产 run 上验证；LangGraph 调用 latency 中位数 ≤ Legacy 的 1.2 倍
- M69：每个 task 暴露的 MCP tool 数量中位数 ≤ 5（vs 当前全量暴露）
- M70：4 个 coding CLI 的 readiness 都达到 `recently_successful`
- M71：每个 cluster 的 contract 测试覆盖率 ≥ 80%
- M72：闭环 A 中由 workflow 自执行的 phase 占比 ≥ 50%

---

## 3. 与 M67 当前真实状态的接驳建议

路线图描述的"未来"和 M67 已经在做的"现在"之间需要桥。给一个具体接驳清单：

| 路线图主张 | M67 已做 / 未做 | 接驳建议 |
| --- | --- | --- |
| AGENTS.md 加 control tower 定位 | 未明确（AGENTS.md 仍说 "personal / local-first agentic workflow runtime"） | M67 P4 顺手补 |
| LANGGRAPH_OVERLAP_INVENTORY.md | 不存在 | M67 P7 hot-file slimming 期间一并产出 |
| EXTERNAL_CAPABILITY_MAP.md | 不存在 | M68 P0 入口产物 |
| Build-vs-Buy 模板挂 PR template | 不存在 | M67 P4（CI/validation 期间）一并加 |
| PolicyEngine / AutomationLease 骨架 | M67-AUTO-001 仍 blocking_open（P2 只修了硬边界） | M67 P5 / P6 完成；不开新 M |
| 高风险动作硬边界 | M67 P2 已完成 scope_hash | 已完成，无需再做 |
| capability live-proof | M67 P3 已完成 | 已完成，无需再做 |
| LangGraph 真集成 | M68 主题 | M67 P7 + P8 收口后立即开始 |

## 4. 修订版 M67-M72 路线（diff 形式）

下面只列与原路线图 §10 的差异；其他内容保留。

```
M67  Workflow-Dogfood 可信收口（保持原版 P0-P8，加 4 项补充）
   + P4 顺手：AGENTS.md 加 control tower 定位段
   + P4 顺手：Build-vs-Buy 模板挂 PR template
   + P7 顺手：产出 LANGGRAPH_OVERLAP_INVENTORY.md
   + 收口前：Go/No-Go 决议必须包含路线图认可

M68  LangGraph 小聚焦真集成
   ! Entry gate: M67-ARCH-001 = repaid AND M67 P8 = GO
   + P0 入口产物：EXTERNAL_CAPABILITY_MAP.md
   + Exit Criteria：spike 失败回滚条件
   + KPI：≥30% run 走 LangGraph；≥1 次生产 checkpoint resume

M69  Capability Control Plane（保持原版）
   + sub-phase：MCP Tool ID Migration（双重 ID 过渡）
   + KPI：per-task MCP tool 数量中位数 ≤ 5

M70  Coding CLI 收敛（原 M70 拆出来）
   - 删除：MCP profiles / Playwright / Figma / 媒体 API
   ! 只接 Codex / Claude Code / Gemini CLI / OpenCode
   + 新增 phase：CLI Selection Policy（routing decision table）
   + KPI：4 个 CLI readiness 都到 recently_successful

M71  受控外部能力（原 M70 后半 + 原 M71 一部分）
   + 接 readonly workspace MCP / web search MCP / Playwright（仅这 3 个）
   + 同时做：Cluster Contract 自研 + Cluster Execution 用 LangGraph subgraph
   + KPI：cluster contract 测试覆盖率 ≥ 80%

M72  业务闭环打穿（操作者优先）
   ! 主线改为：Workflow Self-Development（用 workflow 修 workflow）
   * 演示线保留：H5 小游戏 11 步
   + KPI：M68-M71 中 ≥50% phase 由 workflow 自执行
```

整体节奏：**6 个 M 不变，但每个 M 边界更清晰、KPI 更具体、与现状对接更顺**。

## 5. 7 天行动清单（先做这些，再谈 M68）

如果你看完这份评估同意大方向，**不要立刻开 M68**。先做这 5 件事，预计 7 天：

| 天 | 动作 | 产物 |
| --- | --- | --- |
| Day 1 | 用本评估更新 [LONG_TERM_ROADMAP_universalworkflow.md](LONG_TERM_ROADMAP_universalworkflow.md) §10（合并修订版）；用一个 commit | 更新后的路线图 |
| Day 2 | AGENTS.md §1 加 control tower 定位段；§3.4 加 CLI Adapter Contract 雏形 | AGENTS.md v2 |
| Day 3-4 | 完成 M67 P4（validation/CI reliability，对应 M67-VAL-001） | M67 P4 evidence |
| Day 5 | 完成 M67 P5（Web CSP hardening，对应 M67-WEB-001） | M67 P5 evidence |
| Day 6 | 完成 M67 P6（scheduler boot path，对应 M67-SCHED-001） | M67 P6 evidence |
| Day 7 | 启动 M67 P7（hot-file slimming）；同时产出 LANGGRAPH_OVERLAP_INVENTORY.md（路线图 §13 第二） | LANGGRAPH_OVERLAP_INVENTORY.md 第一版 |

**完成这 7 天后**，再判断要不要进入 M67 P8 收口（workflow E2E）。M68 LangGraph 集成最早等到 M67 真正 GO 之后。

## 6. 一句话给你

> **这份长期路线图的"应该往哪走"是对的，"现在在哪"和"明天该做什么"需要补两个钩子才能接上当前的 M67 进度**。控制塔的隐喻足够清晰、Build-vs-Buy 的纪律足够硬、6 个 M 的方向足够稳——但如果不修复 §2 列的 7 个 P0/P1 差距，路线图会停留在文档层面而不会变成 commits。

## 附录：评估方法

本次评估实际操作：

```bash
# 路线图全文阅读
Read LONG_TERM_ROADMAP_universalworkflow.md (1064 lines)

# 现状对照
Read M67_EXECUTION_REPORT.md
Read M67_ISSUE_REGISTER.md
Read AGENTS.md
Read AGENTS_M67_universalworkflow.md
Read M61_M66_EXECUTION_REPORT.md
Read M61_M66_ISSUE_REGISTER.md

# 关键代码实测交叉验证
grep "from langgraph" packages apps    # 确认 LangGraph 集成范围
Read packages/runtime_langgraph/chat_control_graph.py
Read packages/runtime_langgraph/durable_pilot.py
Read packages/core_domain/orchestration_engine.py
```

未做（不影响结论）：

- pytest 全套
- workflowctl test matrix
- M67 P4-P8 实际状态二次确认（依赖 M67_EXECUTION_REPORT.md 的自述）
