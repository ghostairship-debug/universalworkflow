# M0 Phase 0 — 范围冻结与治理基线详细开发方案

**Phase 目标：** 在进入任何实现工作前，先冻结 M0 的边界、对象职责和关键架构决策，确保后续实现不会因为语义漂移而返工。

**覆盖任务：** T0-01、T0-02、T0-04、T0-05、T0-06、T0-07、T0-08、T0-09

---

# 1. 本阶段要解决什么

Phase 0 不是“写文档补格式”，而是给整个 M0 建立唯一可信的上游约束。它需要一次性回答清楚以下问题：

- M0 到底做什么，明确不做什么
- Wave 1 对象分别承担什么职责，不承担什么职责
- Wave 2/3 为什么暂不落地，延后边界是什么
- 为什么控制环固定
- 为什么 Evidence 是机器真相源
- 为什么当前阶段坚持 SQLite、本地优先和保守并发

如果这些问题在 Phase 0 没有讲清，后面的 schema、DB、API、CLI 都会变成移动靶。

---

# 2. 输入与前置条件

## 2.1 输入材料

- `universal_agentic_workflow_os_local_first_plan_v2_1.md`
- `universal_agentic_workflow_os_M0_task_breakdown_v2_1.md`
- 当前团队对 M0 周期、人员和交付方式的共识

## 2.2 文档职责

- 总说明文档：保留长期语义
- M0 任务拆解文档：作为 M0 字段、任务、验收的主口径
- phase 子文档：只负责执行化方案，不重复发明字段

## 2.3 Entry Criteria

- 团队已确认 M0 是当前唯一主目标
- 当前不并行启动 M1 设计和 M0 实现
- 接受“先冻结、后实现”的推进方式

---

# 3. 核心交付物

本阶段必须产出以下文档，并把它们视为后续所有实现工作的强约束：

- `docs/architecture/m0-scope.md`
- `docs/contracts/wave1-objects.md`
- `docs/contracts/future-objects-outline.md`
- `docs/adrs/ADR-001.md`
- `docs/adrs/ADR-002.md`
- `docs/adrs/ADR-003.md`
- `docs/adrs/ADR-004.md`
- `docs/adrs/ADR-005.md`

如果仓库尚未建立 `docs/` 目录，本阶段就要把这些路径先作为目标落位定义下来。

---

# 4. 详细工作流

## 4.1 工作流 A：冻结 M0 范围

对应任务：T0-01

### 开发步骤

1. 从总说明文档提取 M0 的核心目标、非目标和成功标准。
2. 把所有“看起来很重要但不属于 M0”的内容显式列入非目标。
3. 明确 M0 与 M1 的边界，尤其是：
   - M0 不跑完整 spine
   - M0 不做 Web 控制台
   - M0 不做第二执行器
   - M0 不做完整 Scheduler / Claim / Lease
4. 明确 M0 的输入和输出，不允许使用“基础能力完善”等模糊措辞。

### 文档必须写清

- 做什么
- 不做什么
- 完成算什么
- 哪些项做不到时，M0 不能宣告结束

### Review 重点

- 是否有边界模糊措辞
- 是否把 M1 内容偷偷前置到 M0
- 是否存在“以后再说”的未决关键点

## 4.2 工作流 B：冻结 Wave 1 对象职责

对应任务：T0-02、T0-04

### 开发步骤

1. 为每个 Wave 1 对象补一句话职责定义。
2. 为每个对象补“服务谁 / 用来干什么 / 不该干什么”。
3. 画出对象间关系链，至少覆盖：
   - Run → Phase
   - TaskCard → RuntimeTask → TaskPacket
   - RuntimeTask → Evidence → ReviewVerdict
   - Run / Task → HandoffLite
4. 为 Wave 2/3 对象写“暂不实现原因”和“未来解决的问题”。
5. 明确 `HandoffLite` 在 M0 只冻结语义，不进入首批落表和 smoke 主链。

### 对象职责冻结时的判断标准

- 若一个对象既承载控制状态，又承载执行结果，要拆开
- 若一个对象既给人看，又作为机器真相源，要拆开
- 若一个对象只是“暂时放点信息”，不能通过评审

### Review 重点

- `Evidence` 与 `ReviewVerdict` 是否混淆
- `TaskCard` 与 `TaskPacket` 是否混淆
- `Run` 与 `Phase` 是否被塞入过多业务细节

## 4.3 工作流 C：冻结 ADR 决策

对应任务：T0-05 ~ T0-09

### 开发步骤

1. 先统一 ADR 模板：
   - 背景
   - 问题
   - 决策
   - 替代方案
   - 后果与代价
2. 再分别起草五份 ADR。
3. 最后做一次横向校对，确保五份 ADR 不互相冲突。

### 每份 ADR 的最小落点

- ADR-001：固定控制环，不允许自由 agent 图主导系统
- ADR-002：Evidence 优先，不允许 summary 充当机器真相源
- ADR-003：SQLite 作为 M0 本地实现，不影响未来 PostgreSQL 迁移
- ADR-004：LangGraph 只作为 runtime，经防腐层接入，并通过 `RuntimeGateway` 暴露给 Orchestrator
- ADR-005：并发先保守，未知写域默认串行，M0 采用串行执行语义且不引入全局 Mutex

### ADR-004 必须额外写清

- `contracts/` 与 `core-domain/` 不允许直接 import `langgraph`
- LangGraph State 不允许存储 `contracts` 包定义的对象实例
- State 只保存 ID、枚举与轻量 ref

### Review 重点

- 是否写清“为什么现在这样做”
- 是否写清“未来什么时候会变”
- 是否写清“不采用其他方案的代价”

---

# 5. 建议并行方式

## 5.1 并行分工

- 线 A：范围文档与对象文档
- 线 B：ADR-001 ~ ADR-005

在 `T0-02` 完成后，线 B 可与 Phase 1 的 schema 起草并行推进。

## 5.2 合流规则

在 Phase 0 结束前，必须做一次统一术语校对，确保：

- `Run / Phase / TaskCard / RuntimeTask / TaskPacket / Evidence / ReviewVerdict / HandoffLite` 的命名一致
- “manual preset only” 在所有文档中口径一致
- “M0 不做什么” 在范围文档和 ADR 中完全一致

---

# 6. 阶段内检查点

## Checkpoint 0A：范围冻结草案

检查项：

- M0 非目标是否足够清晰
- 是否已经明确 M1 的边界

## Checkpoint 0B：对象职责冻结草案

检查项：

- Wave 1 对象是否存在职责重叠
- Wave 2/3 延后原因是否足够具体

## Checkpoint 0C：ADR 横向一致性检查

检查项：

- ADR 之间是否相互支持
- 是否存在一份 ADR 放开了另一份 ADR 的约束

---

# 7. 验收与退出标准

## 7.1 Exit Criteria

- `m0-scope` 文档完成并通过评审
- `wave1-objects` 文档完成并通过评审
- `future-objects-outline` 文档完成并通过评审
- ADR-001 ~ ADR-005 完成并通过评审
- 团队对 M0 的做与不做没有实质分歧

## 7.2 Gate 决策问题

Phase 0 结束时必须明确回答：

1. 是否允许进入 schema 设计
2. 是否还存在会引发大规模返工的对象争议
3. 是否需要缩减 M0 范围

只要任意一问答案不清晰，Phase 0 视为未完成。

---

# 8. 风险与缓解

- 风险：文档看似完整，但未形成强约束
  缓解：每个文档都必须能被后续任务直接引用，不允许抽象空话

- 风险：Wave 2/3 占位对象写得过粗，导致后续语义漂移
  缓解：至少写清“为什么现在不做”和“未来解决什么问题”

- 风险：ADR 只解释选项，不解释代价
  缓解：强制补写替代方案和后果

---

# 9. 本阶段完成后的直接产出

Phase 0 完成后，团队应立即拥有三类能力：

- 能统一口径讨论 M0 边界
- 能用同一套对象语言讨论后续 schema 和实现
- 能在发生设计争议时回到 ADR 定位根因

这三件事成立，才说明 Phase 0 真正完成。
