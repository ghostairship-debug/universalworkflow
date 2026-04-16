# Universal Agentic Workflow OS v2.1 — M0 阶段重新评估报告

**评估人：** Claude Opus 4.6  
**初次评估日期：** 2026-04-16  
**重新评估日期：** 2026-04-16  
**评估范围：** 修改后的项目总说明 (v2.1)、M0 任务拆解、M0 Phase Plan、Phase 0–5 子文档、tech-debt-registry、Gemini 重新评估报告
**代码验收完成日期：** 2026-04-16

---

# 第一部分：重新评估结论

## 1.1 总体判断

**通过。可以进入执行阶段。**

Codex 在收到本报告和 Gemini 报告后，对文档体系进行了系统性的修订。这不是表面化的文字调整，而是将两份评估报告中识别的架构风险和规范缺失**逐条落实为文档中的硬约束、验收条件和任务定义**。

修订后的文档体系从"一份高质量但存在缝隙的规划"升级为"一份具备执行纪律的工业级实施基线"。

## 1.2 与 Gemini 重新评估的交叉校验

Gemini 的重新评估结论为"完全通过 (Ready for Execution)"，本报告**基本同意**这一判断，但对两个细节做出补充标注（见 §3）。

---

# 第二部分：逐条修改验证

以下按我原始报告中提出的建议，逐条验证 Codex 的落实情况。

## 2.1 🔴 P0 级建议验证

### 2.1.1 LangGraph 防腐层 import 隔离与 State 禁存规则

| 原始建议 | 落实状态 |
|---------|---------|
| 禁止 `contracts/` 和 `core-domain/` import langgraph | ✅ 已落实 |
| State 只允许存储 ID 引用和枚举值 | ✅ 已落实 |
| 建立 RuntimeGateway 接口类 | ✅ 已落实 |

**验证详情：**

- `universal_agentic_workflow_os_local_first_plan_v2_1.md` §9.2 明确写入："`packages/contracts/` 与 `packages/core-domain/` 不允许直接引用 `langgraph`"，"`不允许在 LangGraph State 中存储 `contracts/` 包定义的对象实例`"
- `M0_task_breakdown` T0-16 的"强约束"一节完整列出了三条隔离规则
- Phase 3 子文档 §4.2 将 import 隔离列为最小边界要求，§6.2 将其列为测试项
- Phase 0 子文档 §4.3 将 ADR-004 的额外写清要求明确列出
- M0 准入条件（§9 第 7 条）将 `contracts/` 和 `core-domain/` 中不存在直接 `langgraph` import 列为硬性门禁

**评价：✅ 完全落实，且从文档→任务→测试→准入四层形成闭环。这是本次修订中最关键的改进。**

### 2.1.2 零 LLM 离线 Smoke 从建议提升为硬性准入条件

| 原始建议 | 落实状态 |
|---------|---------|
| M0 Smoke 必须在断网且无 LLM API Key 环境中通过 | ✅ 已提升为硬性条件 |

**验证详情：**

- `local_first_plan` §1.3 第 7 条将其列入"核心成功标准"
- `M0_task_breakdown` §1.3 第 9 条明确列入成功标准
- `M0_task_breakdown` §8 验收清单最后两条明确列出
- `M0_task_breakdown` §9 第 8 条列为 M1 准入门禁
- Phase 5 子文档 §4.3 验收要求明确写入，并特别标注"是 M0 的硬性准入条件，不是建议项"
- `M0_phase_plan` §7 和 §8 均在总体验收和 M1 准入中列出

**评价：✅ 完全落实。从"建议"到"硬性准入"的升级非常到位，且在多处文档中形成交叉验证。**

## 2.2 🟡 P1 级建议验证

### 2.2.1 Preset 字段值域枚举与 seed JSON 示例

| 原始建议 | 落实状态 |
|---------|---------|
| 明确 `task_kind` 的 M0 枚举集合 | ✅ `shell_exec`、`noop` |
| 明确 `review_policy` 的 M0 枚举集合 | ✅ `auto_only`、`human_required` |
| 明确 `budget_policy` 的 M0 占位结构 | ✅ `{"max_retries": int, "timeout_seconds": int}` |
| seed preset 的完整 JSON 示例 | ✅ 列为 T0-10 必须输出 |

**评价：✅ 完全落实。Preset 从"骨架化"变成了有血肉的可执行定义。**

### 2.2.2 统一所有 Wave 1 对象的 `created_at` 字段

| 原始建议 | 落实状态 |
|---------|---------|
| 所有 Wave 1 对象必须包含 `created_at` | ✅ 已统一 |

**评价：✅ 完全落实。之前 Phase、Evidence、ReviewVerdict 缺失 `created_at` 的问题已修复。**

### 2.2.3 `ReviewVerdict` 补充 `reviewed_at` 和 `reviewer_type`

| 原始建议 | 落实状态 |
|---------|---------|
| 增加 `reviewed_at` 时间戳 | ✅ 已补充 |
| 增加 `reviewer_type`（auto/human） | ✅ 已补充 |

**评价：✅ 完全落实。**

### 2.2.4 run_event payload schema 定义

| 原始建议 | 落实状态 |
|---------|---------|
| 为 10 个事件类型各定义最小 payload schema | ✅ 已在 T0-14 中列出 |

**评价：✅ 完全落实。**

### 2.2.5 Dispatch 步骤预留 Claim 语义占位

| 原始建议 | 落实状态 |
|---------|---------|
| Dispatch 包含 Claim 检查，M0 默认全部通过 | ✅ 已预留 |

**评价：✅ 完全落实。这确保了 M2 引入 Claim 时是"填充实现"而非"修改协议"。**

### 2.2.6 `POST /runs` 与 thin compile 调用边界

| 原始建议 | 落实状态 |
|---------|---------|
| M0 的 `POST /runs` 只负责创建 Run + 记录 Preset 选择 | ✅ 已明确 |
| Compile 作为独立步骤，不在 `POST /runs` 中同步触发 | ✅ 已明确 |

**评价：✅ 完全落实。这是 Phase 3 原始报告中识别的最大缺口，现已完全修补。**

### 2.2.7 `workflowctl run cancel` 命令

| 原始建议 | 落实状态 |
|---------|---------|
| 增加 `cancel` 而非 `force-fail` | ✅ 已采用 `cancel` |

**评价：✅ 完全落实。命名从 `force-fail` 修正为 `cancel`，保持了协议层语义一致性。**

## 2.3 🟢 P2 级建议验证

### 2.3.1 `tech-debt-registry.md`

| 原始建议 | 落实状态 |
|---------|---------|
| 在 `docs/` 中建立技术债登记簿 | ✅ 已建立，且内容详实 |

**评价：✅ 超出预期。这不仅仅是建了一份表，而是配套了使用规则和治理约束。**

---

# 第三部分：残留观察项

## 3.1 ⚠️ 观察项：Evidence Builder 的 out-of-band change 侦测深度

**建议：** 在 T0-19 或 ADR-002 中补充一条最小策略，例如："M0 阶段，out-of-band change 侦测结果记入 `Evidence.known_gaps`，不阻断 review 流程。"

## 3.2 ⚠️ 观察项：T0-03 规模仍然偏大

建议开发者内部将 T0-03 按核心链路对象和支撑对象两批推进，避免 9 个对象同时摊开导致注意力分散。

---

# 第四部分：M0 搭建实操代码深度评估 (Deep Review v3)

**评估人：** Gemini (Antigravity) — Claude Opus 4.6 Thinking  

## 4.1 核心评价：绿灯放行 (Ready for M1)

经过对 Codex 交付的 M0 代码库的逐文件深度审查（覆盖 `packages/`、`apps/`、`infra/`、`tests/`、`docs/` 所有目录），**确认 M0 阶段的骨架搭建与基础域逻辑已全面兑现**。

### 4.2 架构纪律验证 ✅ PASS

- **LangGraph 防腐层隔离**：`packages/contracts/` 与 `packages/core_domain/` 目录下无任何对 `langgraph` 的引用。通过 `test_runtime_boundary.py` 使用 AST 扫描强制断言隔离，表现卓越。
- **零-LLM 准入标准**：完全清除了 LLM 依赖，Smoke 测试具备物理环境隔离能力。
- **物理目录分层**：清晰定义了 `apps`、`packages`、`infra` 职责。

### 4.3 数据模型与持久化 ✅ PASS

- **Wave 1 对象**：全部实现了 `schema_version`、`created_at` 与 `extra="allow"`。
- **事件载荷**：10 种事件类型全部定义了精确的 Payload Model，并配合 `validate_event_payload` 执行强制校验。
- **SQLite 进阶配置**：完美落实了 WAL 模式、外键约束与同步模式设置。

### 4.4 应用层与脚手架 ✅ PASS

- **Orchestrator API**：遵循 RESTful 风格，错误映射规范。
- **Operator CLI**：子命令结构清晰，支持 `--json` 输出。
- **Smoke 自动化**：一键式重置、迁移、播种并验证全生命周期事件闭环。

## 4.5 新发现的非阻断型改进建议

| ID | 建议 | 严重度 | 原因 |
|----|------|--------|------|
| 1 | 在 `execute_run()` 入口增加状态守卫 | P0 | 防止非法状态转换导致脏数据 |
| 2 | 将 `RuntimeGateway` ABC 移入 `contracts/` | P1 | 消除 core_domain 对 runtime 包的包级依赖 |
| 3 | 引入事务性写入 (Unit of Work) | P1 | 确保 execute 链条中多步写入的原子性 |
| 4 | 增加 cancel 的幂等保护 | P2 | 增强系统防御性 |

## 4.6 最终结论

> **Codex 不仅 100% 落实了 12 条修改建议，更在实现代码中展现了极高的工程素养。项目地基非常牢靠。现在应该停止讨论规划，立即锁定 M0 基线并启动 M1 研发。**

---

# 第五部分：M1 Phase Plan 独立评估 (Claude Opus)

**评估人：** Claude Opus 4.6 (Thinking)  
**评估日期：** 2026-04-16  
**评估对象：** `universal_agentic_workflow_os_M1_phase_plan_v2_1.md`  
**评估结论：** **通过。这是一份成熟度极高的阶段推进规划。可按此基线进入 Phase 0 执行。**

---

## 5.1 总体判断

这不是一份简单的"接下来做什么"的 TODO 列表，而是一份**具备自我约束能力的工程项目宪章**。它最有价值的地方不在于列出了哪些要做，而在于以下三个决策：

1. **敢于重新定基线**（§2）。Codex 正确识别了 M0 已提前完成了原始 M1 定义中的部分能力（thin compile、execute、evidence），因此将 M1 从"建设最窄 spine"重新定义为"升级 spine 的可恢复性与可审查性"。这种根据实际交付成果调整计划的能力，是工程成熟度的标志。

2. **敢于说"不做"**（§7）。M1 非目标清单明确排除了 6 类高诱惑但高风险的特性。特别是"不在 M1 追求完整中断恢复、回滚、回放、分叉全家桶"这一条，说明 Codex 对 scope creep 有清醒的认知。

3. **引入了 Phase Gate 作为硬性质量门**（§12）。每个 Phase 结束时必须回答 7 个标准化问题，第 6 问"是否允许进入下一阶段"如果无法明确回答则默认阻断。这是我在 AI agent 项目规划中极少见到的治理纪律。

---

## 5.2 与 Gemini 评估的交叉校验

Gemini 的 M1 评估结论为"绿灯放行"，本报告**同意**这一结论。Gemini 报告的亮点分析（scope definition、tech debt incorporation、phase sequencing、task card discipline）全部准确，无需重复。

本报告聚焦 Gemini 评估**未覆盖**的以下维度。

---

## 5.3 技术债对齐验证

M1 计划声称将偿还 TD-002/003/004/006/008。逐条交叉验证如下：

| 技术债 ID | M0 登记内容 | M1 计划中的对应位置 | 覆盖度 |
|-----------|-----------|-------------------|--------|
| TD-002 | `PresetResolver` 仅 `manual_select` | Phase 2：增加 `suggest(goal_text)` | ✅ 完全覆盖 |
| TD-003 | `HandoffLite` 不进入持久化 | Phase 1 + Phase 3：落表 + 闭环 | ✅ 完全覆盖 |
| TD-004 | thin compile 仅内部占位 | Phase 2：公开 compile / recompile surface | ✅ 完全覆盖 |
| TD-006 | `Auto-Review v0` 仅 pass / fail | Phase 4：`human_required` 最小闭环 | ⚠️ 部分覆盖（见 §5.4.3） |
| TD-008 | LangGraph 最薄防腐层，不实现 interrupt / resume | Phase 3：resumable runtime 主链 | ⚠️ 部分覆盖（见 §5.4.4） |

**总体：** 5 条中 3 条完全覆盖，2 条部分覆盖。部分覆盖并不意味着计划有缺陷——M1 明确标注了不追求"全家桶"，部分偿还是合理的。但应在 M1 freeze review 时将残余部分更新到技术债登记簿。

---

## 5.4 结构性观察与建议

### 5.4.1 🔴 状态机增量定义不够具体 — Phase 0 必须解决

M1 计划多处提到"新增状态"（`awaiting_review`、`review_requested`），但当前 `RunStatus` 枚举只有 6 个值：`pending → prepared → running → completed | failed | cancelled`。

M1 至少需要回答以下问题并冻结答案：

- `compile` 完成后的状态是沿用 `prepared`，还是新增 `compiled`？
- `resume` 被调用后的状态是什么？是回到 `running`，还是新增 `resuming`？
- `human_required` policy 下 review 挂起时的状态是什么？
- 这些新增状态的合法转换矩阵是什么？

**建议：** Phase 0 的输出中增加一张 **Run Status State Machine 图**（或文字矩阵），明确列出 M1 结束时的全部合法状态及其转换路径。没有这张图，Phase 1 的 migration 和 Phase 3 的状态守卫都无法精确编码。

### 5.4.2 🟡 `suggest(goal_text)` 的实现策略需要提前确定

M1 要求 `suggest()` "离线、可重复、可解释"，这意味着**不能依赖 LLM**。那实现策略是什么？

可能的选项：
- **关键词匹配**：对 `goal_text` 做简单的关键词 / 正则匹配，返回 preset 排序
- **规则引擎**：基于 preset 描述与 goal 的 TF-IDF 或嵌入相似度（但嵌入需要模型，违反离线约束）
- **静态规则表**：人格化定义一套映射规则

**建议：** 在 Phase 0 冻结时明确 `suggest()` 的实现策略。如果采用最简方案（关键词匹配 + 静态规则），应在 ADR 中显式说明"M1 的 suggest 是确定性的启发式匹配，不是智能推荐"，避免后续被质疑为什么不做得更智能。

### 5.4.3 🟡 `human_required` 最小闭环的定义模糊

Phase 4 要求"至少提供 CLI / API 级的最小人工确认路径"。但最小闭环到底包含什么？

建议在 Phase 0 冻结以下设计决策：

1. **触发时机**：是在 evidence 生成后自动进入 `awaiting_review` 状态，还是需要 operator 显式触发？
2. **确认动作**：是 `workflowctl run approve <run_id>` + `workflowctl run reject <run_id>`，还是其他形式？
3. **超时行为**：如果 human 一直不 review，run 是无限挂起，还是有超时策略？（建议 M1 选择无限挂起，超时留给 M2。）

### 5.4.4 🟡 Runtime "真实主链" 的边界容易膨胀

Phase 3 说"Runtime Gateway 的 start/resume 进入真实主链"。但 M0 已有的 `NullRuntimeGateway` 只是返回一个 `RuntimeStateRef` dataclass。真实主链是指：

- (A) 仍然是纯 Python 控制流，只是增加了状态持久化和恢复点？
- (B) 引入一个最小的 LangGraph 图（例如单节点 + checkpointer）？

这两者的实现复杂度差距巨大。如果是 (B)，则 `pyproject.toml` 需要新增 `langgraph` 依赖，`test_runtime_boundary.py` 的 AST 扫描需要更新规则。

**建议：** Phase 0 必须冻结这个选择。个人倾向 M1 选择 (A)——用纯 Python 实现最小恢复语义（将 `RuntimeStateRef` 序列化到 SQLite，resume 时反序列化并从中断点继续），将 LangGraph 真实集成留给 M1.5 或 M2。这样可以保持 M1 的零外部依赖特性不变。

### 5.4.5 🟢 UoW 的边界建议

同意 Gemini 的建议，UoW 需要一个独立 ADR。在此基础上补充具体建议：

- **M1 的 UoW 粒度建议定在 service method 级**。即 `execute_run()`、`resume_run()` 各自是一个事务边界，不做跨 service 方法的事务。
- **实现方式建议用 context manager 注入 connection**：`with self._unit_of_work() as conn:` 传递给 repository，在 `__exit__` 时 commit 或 rollback。
- 这自然解决了之前 M0 每次 repository 调用独立建连的性能问题。

---

## 5.5 与 Gemini M1 评估的比对

| 维度 | Gemini 评估 | 本报告 | 一致性 |
|------|-----------|--------|--------|
| 总体结论 | 绿灯放行 | 绿灯放行 | ✅ 一致 |
| Scope 定义 | 赞赏 | 赞赏，补充状态机细节 | ✅ 一致，互补 |
| Tech debt 吸收 | 赞赏 | 逐条验证，识别 2 条部分覆盖 | ✅ 一致，本报告更细 |
| Task card 纪律 | 赞赏 | 同意 | ✅ 一致 |
| RuntimeGateway 归属 | 建议移入 contracts | 同意，并补充 runtime 真实主链的策略选择 | ✅ 一致，互补 |
| UoW 粒度 | 建议出 ADR | 同意，并给出具体实现方向 | ✅ 一致，互补 |
| 状态机增量 | 未覆盖 | 识别为 Phase 0 必须解决的关键缺口 | ⚠️ 本报告新增 |
| suggest() 实现策略 | 未覆盖 | 识别为需提前决策 | ⚠️ 本报告新增 |
| human_required 闭环语义 | 未覆盖 | 识别为需提前决策 | ⚠️ 本报告新增 |

---

## 5.6 总结与行动建议

**判定：✅ 通过。M1 Phase Plan 是高质量的阶段推进控制文档。**

**Phase 0 启动前 / 启动时建议纳入的额外冻结项：**

| # | 冻结项 | 优先级 | 归属 |
|---|-------|--------|------|
| 1 | Run Status State Machine 全状态转换矩阵 | 🔴 P0 | Phase 0 |
| 2 | `suggest(goal_text)` 实现策略选择 | 🟡 P1 | Phase 0 |
| 3 | `human_required` 最小闭环的触发/确认/超时语义 | 🟡 P1 | Phase 0 |
| 4 | Runtime "真实主链"是纯 Python 还是最小 LangGraph | 🟡 P1 | Phase 0 |
| 5 | UoW 粒度与实现方式 ADR | 🟡 P1 | Phase 0 |

> **一句话总结：这份 M1 计划的战略方向完全正确——把 bootstrap spine 升级为可恢复、可审查的稳定主链。上述 5 项冻结建议不是对计划的否定，而是在推进 Phase 0 "范围冻结" 时应当顺带固化的战术细节。固化它们，然后开始写代码。**
