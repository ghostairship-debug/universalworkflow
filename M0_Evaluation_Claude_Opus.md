# Universal Agentic Workflow OS v2.1 — M0 阶段重新评估报告

**评估人：** Claude Opus 4.6  
**初次评估日期：** 2026-04-16  
**重新评估日期：** 2026-04-16  
**评估范围：** 修改后的项目总说明 (v2.1)、M0 任务拆解、M0 Phase Plan、Phase 0–5 子文档、tech-debt-registry、Gemini 重新评估报告

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

**验证详情：**

- `M0_task_breakdown` T0-10 "M0 必须冻结的值域"已明确列出三个字段的枚举
- `local_first_plan` §4.2 "M0 值域约束"新增了完整约束定义
- Phase 1 子文档 §4.2 将值域冻结为必做项，并明确要求完整 JSON seed 示例

**评价：✅ 完全落实。Preset 从"骨架化"变成了有血肉的可执行定义。**

### 2.2.2 统一所有 Wave 1 对象的 `created_at` 字段

| 原始建议 | 落实状态 |
|---------|---------|
| 所有 Wave 1 对象必须包含 `created_at` | ✅ 已统一 |

**验证详情：**

- `M0_task_breakdown` T0-03 "默认策略"明确写入"所有持久化的 Wave 1 对象必须带 `created_at`"
- T0-03 中所有 9 个对象的字段列表都包含了 `created_at`
- Phase 1 子文档 §4.1 列为设计约束
- T0-03.5 将 `created_at` 缺失列为必测项

**评价：✅ 完全落实。之前 Phase、Evidence、ReviewVerdict 缺失 `created_at` 的问题已修复。**

### 2.2.3 `ReviewVerdict` 补充 `reviewed_at` 和 `reviewer_type`

| 原始建议 | 落实状态 |
|---------|---------|
| 增加 `reviewed_at` 时间戳 | ✅ 已补充 |
| 增加 `reviewer_type`（auto/human） | ✅ 已补充 |

**验证详情：**

- `M0_task_breakdown` T0-03 ReviewVerdict 字段列表包含 `reviewed_at` 和 `reviewer_type`
- `local_first_plan` §5.4 ReviewVerdict 定义包含 `reviewed_at` 和 `reviewer_type`
- Phase 1 子文档特别标注"M0 默认 `reviewer_type=auto`"

**评价：✅ 完全落实。**

### 2.2.4 run_event payload schema 定义

| 原始建议 | 落实状态 |
|---------|---------|
| 为 10 个事件类型各定义最小 payload schema | ✅ 已在 T0-14 中列出 |

**验证详情：**

- `M0_task_breakdown` T0-14 增加了"必须同时定义"和"建议最小 payload"两个小节
- 5 个示例 payload 已给出具体字段定义
- 明确了"payload 只允许放摘要与必要 ID"的约束
- 验收清单中已列出 "run event payload schema 已定义"

**评价：✅ 完全落实。**

### 2.2.5 Dispatch 步骤预留 Claim 语义占位

| 原始建议 | 落实状态 |
|---------|---------|
| Dispatch 包含 Claim 检查，M0 默认全部通过 | ✅ 已预留 |

**验证详情：**

- `local_first_plan` §4.1 Dispatch 定义已修改为"把可运行任务交给 Scheduler，再由 Scheduler 执行 Claim 检查（M0 阶段默认 no-op pass）并选择 Worker"
- Phase 3 子文档 §4.3 第 4 步明确写入"明确 `Dispatch` 包含 claim check placeholder，M0 默认 no-op pass"

**评价：✅ 完全落实。这确保了 M2 引入 Claim 时是"填充实现"而非"修改协议"。**

### 2.2.6 `POST /runs` 与 thin compile 调用边界

| 原始建议 | 落实状态 |
|---------|---------|
| M0 的 `POST /runs` 只负责创建 Run + 记录 Preset 选择 | ✅ 已明确 |
| Compile 作为独立步骤，不在 `POST /runs` 中同步触发 | ✅ 已明确 |

**验证详情：**

- `M0_task_breakdown` T0-15 新增"`POST /runs` 的 M0 语义边界"小节，逐条列出职责
- 明确"不在 M0 暴露公共 compile API"
- Phase 3 子文档 §4.1 "边界说明"重复确认了这一切割

**评价：✅ 完全落实。这是 Phase 3 原始报告中识别的最大缺口，现已完全修补。**

### 2.2.7 `workflowctl run cancel` 命令

| 原始建议 | 落实状态 |
|---------|---------|
| 增加 `cancel` 而非 `force-fail` | ✅ 已采用 `cancel` |

**验证详情：**

- `M0_task_breakdown` T0-21a 命令列表包含 `workflowctl run cancel <run_id>`
- Phase 5 子文档 §4.1 和 §6.1 均列出 cancel 命令
- `M0_task_breakdown` §4.3 运行类产出包含 cancel

**评价：✅ 完全落实。命名从 `force-fail` 修正为 `cancel`，保持了协议层语义一致性。**

## 2.3 🟢 P2 级建议验证

### 2.3.1 `tech-debt-registry.md`

| 原始建议 | 落实状态 |
|---------|---------|
| 在 `docs/` 中建立技术债登记簿 | ✅ 已建立，且内容详实 |

**验证详情：**

- `docs/tech-debt-registry.md` 已创建，包含 10 条登记项
- 每条含 ID、描述、引入阶段、计划偿还阶段、阻塞影响
- 文档明确了登记规则、Freeze Review 必查问题和更新约束
- 最后一条（TD-010）甚至对"技术债管理本身的技术债"做了自引用登记

**评价：✅ 超出预期。这不仅仅是建了一份表，而是配套了使用规则和治理约束。**

### 2.3.2 `HandoffLite` 降级为仅冻结语义

| 原始建议 | 落实状态 |
|---------|---------|
| M0 只冻结 HandoffLite 语义定义，不要求落表 | ✅ 已调整 |

**验证详情：**

- `M0_task_breakdown` §3.1 说明"HandoffLite 在 M0 必须冻结语义与最小 schema""不要求进入首批落表范围，也不进入 M0 smoke 主链"
- T0-03 默认策略中明确写入
- `local_first_plan` §5.4 HandoffLite 定义中加入"M0 阶段要求冻结其语义与最小 schema，但不要求进入首批落表范围"
- TD-003 在技术债登记簿中记录

**评价：✅ 完全落实。**

### 2.3.3 拆分 T0-21 为 T0-21a / T0-21b

| 原始建议 | 落实状态 |
|---------|---------|
| T0-21a（依赖 Phase 3）：基础命令 | ✅ 已拆分 |
| T0-21b（依赖 Phase 4）：evidence 命令 | ✅ 已拆分 |

**验证详情：**

- `M0_task_breakdown` 已将 T0-21 拆为 T0-21a 和 T0-21b 两个独立任务卡
- T0-21a 依赖 T0-15，T0-21b 依赖 T0-19 / T0-20 / T0-21a
- 关键路径中使用 T0-21a 而非 T0-21
- 并行建议中明确 T0-21a 可在 Phase 3 后启动

**评价：✅ 完全落实。释放了约 2 天并行空间。**

### 2.3.4 补充缺失任务 T0-03.5 / T0-12.5 / T0-15.5 / T0-22.5

| 缺失任务 | 落实状态 |
|---------|---------|
| T0-03.5：contracts 包测试基础设施 | ✅ 已增加，含具体测试项 |
| T0-12.5：SQLite WAL 模式与连接策略 | ✅ 已增加，不引入额外 Mutex |
| T0-15.5：API 错误响应格式统一 | ✅ 已增加，含具体错误类型 |
| T0-22.5：Python 项目依赖管理 | ✅ 已增加 |

**评价：✅ 四项全部落实，且各自有验收标准。**

## 2.4 其他关键改进

### 2.4.1 总周期调整

原始建议将 M0 总周期从"12–16 工作日"调整为"14–18 工作日"。`M0_phase_plan` 已将建议总周期改为"14~18 个工作日，约 2~3 周"。✅

### 2.4.2 文档职责口径统一

新增了三层文档的职责定义：总说明保留长期语义、任务拆解作为 M0 主口径、phase 子文档只承载执行化方案不重复发明字段。✅

### 2.4.3 `artifact_refs` 中 Hash 确权职责明确

原始报告建议明确 `artifact_refs` 的 hash/mtime 生成是 Evidence Builder 而非 ShellAdapter 的职责。T0-19 新增"职责边界"小节明确了这一分工；Phase 4 子文档 §4.1 和 §4.2 也分别标注。✅

---

# 第三部分：残留观察项

## 3.1 ⚠️ 观察项：Evidence Builder 的 out-of-band change 侦测深度

T0-19 新增了"必须具备最小的 out-of-band change 侦测能力"，Phase 4 §6.2 也将"hash 校验失败可识别为 out-of-band change"列为测试项。这很好。

但当前文档没有说明**侦测到 out-of-band change 后应采取什么动作**——是在 Evidence 中标记 warning？是阻断 review？还是只打日志？

**建议：** 在 T0-19 或 ADR-002 中补充一条最小策略，例如："M0 阶段，out-of-band change 侦测结果记入 `Evidence.known_gaps`，不阻断 review 流程。"这样既不增加实现负担，又固定了行为语义。

**严重度：低。不阻塞启动。可在 Phase 1 schema 设计时顺带明确。**

## 3.2 ⚠️ 观察项：T0-03 规模仍然偏大

原始报告建议将 T0-03 拆为 T0-03a（核心 5 对象）和 T0-03b（辅助 4 对象）。当前版本没有采纳这一拆分，T0-03 仍然是一个覆盖 9 个对象的单一任务卡。

这不是错误——保持为一个任务也可以工作。但在实际执行中，建议开发者内部将 T0-03 按 Run/Phase/RuntimeTask/Evidence/ReviewVerdict（核心链路）与 TaskCard/TaskPacket/PresetDefinition/HandoffLite（支撑对象）两批推进，避免 9 个对象同时摊开导致注意力分散。

**严重度：低。属于执行建议，不影响文档正确性。**

## 3.3 对 Gemini 重新评估报告的意见

Gemini 的重新评估报告结构清晰、验证到位，我同意其"绿灯放行"的结论。

对其提出的两个遗留观察项补充意见：

| Gemini 观察项 | 本报告意见 |
|---|---|
| Unknown Fields `extra = "allow"` 落位 | 同意。T0-03 默认策略中已写入 `extra=allow`，但实际编码时需确保 Pydantic 版本兼容性（v1 用 `class Config: extra = "allow"`，v2 用 `model_config`）。建议在 T0-22.5 锁定 Pydantic 版本时一并确认。 |
| SQLite WAL 配置 | 同意。T0-12.5 已覆盖此项。执行时注意 WAL 需在第一次连接时通过 PRAGMA 设置，不能依赖 SQLite 默认行为。 |

---

# 第四部分：修改验证总表

| # | 原始建议 | 优先级 | 落实状态 | 备注 |
|---|---------|--------|---------|------|
| 1 | ADR-004 import 隔离 + State 禁存规则 | 🔴 P0 | ✅ 完全落实 | 四层闭环（文档→任务→测试→准入） |
| 2 | 零 LLM 离线 Smoke 硬性准入 | 🔴 P0 | ✅ 完全落实 | 多处交叉确认 |
| 3 | Preset 字段值域枚举 + seed JSON | 🟡 P1 | ✅ 完全落实 | |
| 4 | 统一 `created_at` | 🟡 P1 | ✅ 完全落实 | 9 个对象全部补齐 |
| 5 | run_event payload schema | 🟡 P1 | ✅ 完全落实 | 5 个示例已给出 |
| 6 | Dispatch Claim 占位 | 🟡 P1 | ✅ 完全落实 | no-op pass 语义清晰 |
| 7 | `POST /runs` 与 compile 边界 | 🟡 P1 | ✅ 完全落实 | Phase 3 最大缺口已修补 |
| 8 | `workflowctl run cancel` | 🟡 P1 | ✅ 完全落实 | |
| 9 | tech-debt-registry.md | 🟢 P2 | ✅ 超出预期 | 含 10 条登记 + 治理规则 |
| 10 | HandoffLite 降级 | 🟢 P2 | ✅ 完全落实 | |
| 11 | 拆分 T0-21 | 🟢 P2 | ✅ 完全落实 | |
| 12 | 补充 T0-03.5 / T0-12.5 / T0-15.5 / T0-22.5 | 🟢 P2 | ✅ 完全落实 | |

**落实率：12/12 = 100%**

---

# 第五部分：与 Gemini 重新评估的交叉验证

| 维度 | Gemini 重新评估 | 本报告重新评估 | 一致性 |
|------|---------------|--------------|--------|
| 总体结论 | 完全通过，绿灯放行 | 通过，可进入执行 | ✅ 一致 |
| P0 修改落实 | 确认落实 | 确认落实（四层闭环） | ✅ 一致 |
| P1 修改落实 | 确认落实 | 确认落实（逐条验证） | ✅ 一致 |
| P2 修改落实 | 确认落实 | 确认落实（tech-debt 超出预期） | ✅ 一致 |
| 残留风险 | Unknown Fields + WAL 配置 | out-of-band change 策略 + T0-03 规模 | ⚠️ 互补（各自识别了不同的低优先级观察项） |
| 下一步建议 | 锁定文档、启动 Phase 0 + Phase 1 | 同意，补充执行细节建议 | ✅ 一致 |

**两份重新评估报告在核心结论上完全一致，在残留观察项上形成互补覆盖。**

---

# 第六部分：最终结论与启动建议

## 6.1 项目就绪度判断

**就绪。** 当前文档体系是我在 AI 项目评估中见过的最系统化的 M0 规划之一。Codex 不仅接受了修改建议，而且在落实过程中展现了工程判断力——例如在 T0-12.5 中明确"不额外引入进程级全局 Mutex"（接受了我对 Gemini 建议的纠偏），在 tech-debt-registry 中做到了自引用登记。

## 6.2 启动建议

1. **立即启动 Phase 0。** 当前文档已足以作为实施基线，不需要再做规划层面的调整。
2. **Phase 0 与 Phase 1 按已有并行方案推进。** ADR 编写与 schema 设计可在 T0-02 完成后并行展开。
3. **在 T0-03 实际执行时，内部按核心链路对象和支撑对象两批推进。**
4. **在 T0-19 的编码过程中，顺带明确 out-of-band change 侦测后的行为策略（建议记入 `known_gaps`，不阻断）。**
5. **在 T0-22.5 锁定 Python 依赖时，确认 Pydantic 版本并对齐 `extra` 配置语法。**

## 6.3 一句话总结

> **从"规划质量极高"到"实施基线就绪"，Codex 完成了最后一步跨越。12 条修改建议 100% 落实，文档体系从四个层面（总说明→任务拆解→phase 子文档→验收清单）形成了无缝闭环。剩余观察项均为低优先级，不阻塞启动。现在应该停止讨论文档，开始写代码。**
