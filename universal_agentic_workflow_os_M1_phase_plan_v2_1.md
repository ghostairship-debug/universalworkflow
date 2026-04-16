# Universal Agentic Workflow OS v2.1 — M1 Phase 总览与执行计划

**模式：Local-first, Cloud-ready**

**文档定位：** 本文用于定义基于当前已落地 M0 基线的 **M1 实际推进顺序、阶段边界、关键 gate 与验收口径**。它不替代总说明，也不替代后续每个 phase 的详细开发文档；在进入某个 M1 phase 之前，仍必须先产出该 phase 的详细方案和 task cards。

---

# 1. 本文怎么使用

如果要回答“**M1 现在应该做什么、按什么顺序做、做到什么程度就该收口**”，看本文。

如果要回答“**当前正在执行的 phase 具体拆成哪些 task card、每张卡怎么验收**”，则在进入该 phase 前，基于本文再生成：

- `m1_phase_docs/phase_x_*.md`
- `docs/task_cards/m1_phase_x_task_cards.md`
- `docs/task_cards/m1_execution_loop_protocol.md`

建议固定采用以下推进循环：

1. 回读 M0 freeze review、技术债登记簿、当前评估结论
2. 进入当前 M1 phase 前，先补一份 phase 详细开发文档，明确代码边界、接口变化、测试范围与风险
3. 将该 phase 拆成**代码级 task cards**，而不是只写任务目标
4. 对复杂 task 强制生成独立 md 文档，再冻结 write set、接口影响、测试方案与回滚点
5. 按 task 逐个实现，每完成一个 task 就做对应测试与文档回填
6. 当前 phase 完成后做一次 gate review，并根据真实实现结果重排下一 phase 的 task cards
7. 只有当当前 phase 的 gate 通过，才允许进入下一 phase

---

# 2. 为什么 M1 需要重新定基线

原始总方案中，M1 被定义为“最窄 Vertical Spine”。但当前仓库已经在 M0 阶段提前完成了以下能力：

- `POST /runs` + preset 记录
- `prepare_run()` + thin compile 占位
- `execute_run()` + ShellAdapter
- Evidence / Auto-Review / timeline
- Operator CLI 与离线 smoke / offline validation

因此，**M1 不再重复建设“第一条最窄 spine”本身，而是把这条 spine 从 bootstrap 版本升级为：**

- 可建议但不自动生效的 preset 选择
- 可显式触发的 compile / recompile / resume 工作流
- 持久化的 `HandoffLite`
- 更可信的 runtime 边界与 resumable control loop
- 更完整但仍保持轻量的 review policy 与 operator surface

M1 仍然明确 **不是** M2：

- 不做真实 Claim / Lease / Barrier
- 不做安全并发执行
- 不接第二执行器
- 不引入必须依赖网络或 LLM 的主路径

---

# 3. M1 目标

M1 结束时，系统应从“能跑通 bootstrap 闭环”升级为“能跑通最小可恢复、可交接、可重编译的单机主链”。

M1 的目标建议固定为：

- `PresetResolver` 从 `manual_select` 升级为 `manual_select + suggest`
- `suggest(goal_text)` 只输出排序建议，不自动替用户选择 preset
- `HandoffLite` 进入持久化与查询范围，成为 phase 间交接的正式对象
- thin compile 从内部占位能力升级为显式工作流步骤
- runtime 边界从 placeholder 升级为最小可恢复主图，但仍保持防腐层极薄
- `execute_run()`、`cancel_run()`、`resume_run()` 的状态转换具备明确守卫和幂等约束
- `human_required` review policy 至少具备最小闭环，不再只是 seed 中的静态字段
- M1 smoke 继续要求在断网且无 LLM API Key 环境中可通过

---

# 4. 已吸收的评估结论

Gemini 与 Claude Opus 的新增评估中，建议纳入 M1 的项建议固定如下：

## 4.1 直接纳入 M1

- `PresetResolver.suggest(goal_text) -> ranked presets`
- `HandoffLite` 落表并进入查询 / timeline / handoff 视图
- public compile / recompile / resume 工作流
- Run status state machine 的 M1 增量冻结
- `suggest()` 的离线确定性实现策略冻结
- `human_required` 最小闭环语义冻结
- runtime “真实主链”范围冻结
- `execute_run()` 入口状态守卫
- 事务性写入 / Unit of Work
- `cancel` 幂等保护
- `RuntimeGateway` 契约归属梳理
- `Auto-Review v0` 向 policy-aware 版本小步升级

## 4.2 继续延后，不纳入 M1

- 真实 Claim / Lease / Barrier
- 多运行单元安全并发
- 第二执行器与能力路由
- Web 控制台
- LLM 必需型 preset 推断
- 深度 trace / metrics / replay

## 4.3 本轮评估已吸收的补充约束

基于最新 Gemini / Claude Opus 评估，M1 追加吸收以下执行约束：

- `Phase 0` 必须输出一份 **Run Status State Machine** 文字矩阵或图，作为后续 migration、状态守卫和 review 闭环的编码依据
- `suggest(goal_text)` 在 M1 明确采用**离线、可重复、可解释的确定性启发式策略**，不依赖 LLM、embedding 或联网检索
- `human_required` 在 M1 必须冻结最小闭环：触发时机、确认动作、挂起状态以及是否超时
- M1 的 runtime “真实主链”默认采用**纯 Python + 持久化 `RuntimeStateRef`** 的最小恢复语义，不把真实 LangGraph 集成作为 M1 必须项
- `RuntimeGateway` 的抽象归属需要在 `Phase 0 / Phase 1` 明确落到更稳定的位置，优先采用依赖倒置方案
- Unit of Work 需要单独 ADR，且 M1 默认以 **service method 级事务边界** 为基线
- M1 开发期间默认允许对本地 M0 临时测试数据库做**破坏性清理**；M1 不承诺兼容历史临时 DB 样本，标准路径为 `db reset`

---

# 5. M1 Source Of Truth

M1 阶段建议固定以下文档职责：

- 总说明文档：保留长期架构语义和阶段演进方向
- `docs/tech-debt-registry.md`：作为 M0 延后项与 M1 偿债范围的主登记簿
- 本文：作为 M1 的阶段顺序、边界和 gate 主文档
- `m1_phase_docs/`：只承载当前 phase 的详细开发方案
- `docs/task_cards/`：承载 phase 级 task 索引、复杂 task 独立 md 与执行协议
- `docs/task_cards/m1_execution_loop_protocol.md`：作为 task 粒度、复杂度分级与安全执行的硬标准

**执行原则：**

- 本文决定“先做哪一段”
- phase 子文档决定“这一段具体怎么做”
- task cards 决定“今天先做哪张卡、改哪些文件、验哪些测试”

---

# 6. Task Card 粒度与执行标准

M1 的 task card 不再接受“只有一句 goal + 一句 done when”的轻量写法。

从 M1 开始，task card 默认必须写成**代码级执行卡**，至少包含：

- 背景与本卡目标
- 本卡只解决的代码问题与明确非目标
- read set：实现前必须先读的文件 / 模块
- write set：允许改动的文件 / 模块
- 受影响的 contract / API / CLI / migration / event / status
- 需要保持不变的系统约束与兼容性要求
- 分步骤实施方案，颗粒度至少到函数、类、路由、表、测试文件层面
- 测试方案：单测、集成、smoke、手动验证各做什么
- 风险点、回滚点和完成证据

若一个 task 满足以下任一条件，则必须再生成**单独 md 文档**，不能只留在 phase 汇总卡片中：

- 涉及 migration、schema、repository、持久化协议变更
- 涉及 public API、CLI 命令、event schema、status machine 变化
- 涉及跨 3 个及以上模块或跨 `apps/`、`packages/`、`infra/` 的联动修改
- 涉及事务性写入、幂等、恢复、handoff、runtime state 等高风险语义
- 预期需要分多步提交或中间态必须可验证
- 任何“如果描述不够细就容易误改”的任务

建议目录结构固定为：

- `m1_phase_docs/phase_x_*.md`
- `docs/task_cards/m1_phase_x_task_cards.md`
- `docs/task_cards/m1_phase_x/` 下存放复杂 task 的独立 md

---

# 7. M1 非目标

为了避免 M1 再次膨胀，建议明确以下非目标：

- 不在 M1 引入真实并发调度
- 不在 M1 接第二执行器
- 不在 M1 做 Web UI / Dashboard
- 不在 M1 引入必须依赖云端模型的主路径
- 不在 M1 追求完整中断恢复、回滚、回放、分叉全家桶
- 不在 M1 重做 M0 已稳定成立的 CLI / smoke / offline validation 基线

---

# 8. M1 Phase 总览

| Phase | 建议时长 | 目标 | 主要偿还项 | 结束 gate |
| --- | --- | --- | --- | --- |
| Phase 0 | 1~2 天 | 重定 M1 边界，冻结 contract / API / status delta | TD-002/003/004/006/008 的范围确认 | M1 delta 冻结 |
| Phase 1 | 2~3 天 | 完成 contracts / migration / repository 的 M1 扩展 | `HandoffLite` 持久化、runtime state ref、必要状态字段 | M1 数据模型可落库 |
| Phase 2 | 2~3 天 | 建立 preset suggestion 与 public compile surface | `suggest`、`compile`、`recompile` | compile 主入口成立 |
| Phase 3 | 3~4 天 | 建立 resumable runtime 主链与 handoff 闭环 | `resume`、状态守卫、UoW、幂等 cancel | 最小可恢复控制环成立 |
| Phase 4 | 2~3 天 | 补齐 review policy / operator DX / smoke / freeze review | `human_required` 最小闭环、M1 验收与收口 | M1 go / no-go |

**建议总周期：** 10~15 个工作日，约 2~3 周。

---

# 9. 各 Phase 详细说明

## Phase 0：M1 Rebaseline 与范围冻结

**目标：** 先把“这次 M1 到底做哪些增量、不做哪些增量”冻结清楚，避免后续边写边改协议。

**本阶段需要冻结的关键决定：**

- `PresetResolver` 的建议接口与排序输出结构
- `suggest(goal_text)` 的实现策略与排序规则，默认采用确定性启发式匹配
- compile / recompile / resume 的公共边界
- `HandoffLite` 的落表范围、查询方式和与 phase 的绑定关系
- `RuntimeGateway` / `RuntimeStateRef` 的契约归属
- runtime “真实主链”在 M1 的落地方式，默认冻结为纯 Python 可恢复主链，而非真实 LangGraph 集成
- Run Status State Machine 的 M1 增量矩阵
- 是否新增 `awaiting_review` / `review_requested` 一类状态与事件
- `human_required` 的触发、确认、挂起与超时语义
- `cancel` 的幂等语义
- UoW 的事务边界与实现方式，默认以 service method 为粒度
- M1 是否允许破坏性清理本地 M0 测试数据库

**建议输出：**

- M1 scope & ADR 补充说明
- M1 contract delta 清单
- M1 API / CLI delta 清单
- Run Status State Machine 矩阵
- `suggest()` 策略 ADR
- UoW 粒度 ADR
- M1 测试清单与 smoke 草案

**结束 gate：**

- 所有新增对象、状态、事件、接口的命名已冻结
- `suggest()` 的实现策略已冻结为离线确定性方案
- `human_required` 最小闭环已冻结为可编码语义
- runtime 真实主链的实现边界已冻结
- Run Status State Machine 已产出
- 明确哪些项推迟到 M1.5 / M2
- 当前阶段结束后，不再在实现中临时发明协议字段

## Phase 1：Contracts / Persistence Delta

**目标：** 先把 M1 要新增的 schema、表结构、repository 能力稳定下来，再扩应用层。

**建议范围：**

- 为 `HandoffLite` 增加首批持久化能力
- 如有需要，新增 `runtime_state_refs` 或等价轻量状态持久化表
- 评估并落地 `RunStatus` / `RunEventType` 的最小增量
- 将 `RuntimeGateway` 契约移动到更稳定的位置，优先落到 `packages/contracts/` 一侧，避免 `core_domain -> runtime` 包级倒挂
- 为 compile / recompile / resume 所需对象补充 contract
- 补 migration `002_*`
- repository 层补齐 handoff / compile / resume 所需读写能力
- 明确 M1 对本地临时 DB 的迁移策略，默认允许 `db reset` 式破坏性清理，不承诺兼容 M0 临时样本

**建议同步吸收的评估项：**

- `execute_run()` / `resume_run()` 的状态模型先定义清楚
- `cancel_run()` 的幂等语义先固化到 contract + service 层

**结束 gate：**

- migration 可重复执行
- 新增对象 round-trip 测试通过
- repository 层已经能支撑后续 API / CLI 开发

## Phase 2：Preset Suggestion 与 Compile Surface

**目标：** 把 M0 的“内部 prepare 能力”升级为对 operator 可见的 compile 工作流，并引入建议式 preset 选择。

**建议范围：**

- 为 `PresetResolver` 增加 `suggest(goal_text)`，要求离线、可重复、可解释
- 输出 ranked presets，但最终选择权仍归 operator
- 增加 compile / recompile 的 service 层方法
- 新增对应 API / CLI 入口
- 明确 `POST /runs` 仍只负责创建 run，不隐式 compile / execute
- 为 compile 结果增加可查询视图，如 task packet / handoff / next action 摘要

**建议接口方向：**

- API：`POST /runs/{run_id}/compile`
- API：`POST /runs/{run_id}/recompile`
- API：`GET /runs/{run_id}/status-detail`
- CLI：`workflowctl run suggest-presets`
- CLI：`workflowctl run compile`
- CLI：`workflowctl run recompile`

**结束 gate：**

- 用户可以先创建 run，再显式 compile，而不是只能走内部 prepare
- `suggest()` 稳定可用且不自动落地选择
- compile / recompile 不破坏 M0 既有主链

## Phase 3：Resumable Runtime 与 Handoff 闭环

**目标：** 把 runtime 从“能 start 的 placeholder”升级为“可记录状态、可恢复推进、可沉淀 handoff”的最小主控制图。

**建议范围：**

- `RuntimeGateway.start()` 与 `RuntimeGateway.resume()` 进入真实主链
- 将 `RuntimeStateRef` 持久化为轻量 ref，而不是在 LangGraph State 中堆 contract 对象
- M1 默认以纯 Python 控制流承载恢复语义，不把真实 LangGraph 图接入作为本阶段必须项
- 在 compile -> execute 或 phase -> phase 切换处生成 `HandoffLite`
- 新增 `resume_run()` service 与 API / CLI 入口
- 为 `execute_run()` 增加明确状态守卫
- 引入 Unit of Work / 事务性写入，覆盖 compile / resume / execute 的多步写入链，默认以 service method 为事务边界
- 为 `cancel_run()` 增加幂等保护

**M1 对 runtime 的硬约束：**

- `contracts/` 与 `core_domain/` 仍不得直接引用 `langgraph`
- LangGraph State 中仍只允许 ID、枚举和轻量 ref
- M1 不要求为 runtime 引入真实 `langgraph` 依赖
- 真实 Claim / Lease / Barrier 继续留在 M2

**结束 gate：**

- `compile -> resume -> execute -> review -> done` 主链跑通
- handoff 已落库且可查询
- `resume` 不依赖人工改库即可恢复继续
- 状态转换错误能被 guard 正确阻断

## Phase 4：Review Policy、Operator DX 与 Freeze Review

**目标：** 把 M1 增量收口成可交付基线，而不是停留在“接口已经有了”。

**建议范围：**

- 让 `auto_only` 与 `human_required` 的 policy 差异在流程中真正生效
- 如果保留 `human_required` 预设，则至少提供 CLI / API 级的最小人工确认路径
- 完成 `status-detail`、handoff 查询、review 状态可见性
- 更新 smoke、offline validation、README、freeze review
- 将 M1 未完成但接受延后的项补登技术债

**建议 smoke：**

- `feature_delivery` 路径：`create -> compile -> resume -> execute -> auto review -> completed`
- `research_spike` 路径：`create -> compile -> resume -> evidence -> review requested -> human confirm -> completed`
- 全部在断网且无 LLM API Key 环境中通过

**结束 gate：**

- operator 可以从 CLI/API 看清当前 run 处于 compile、handoff、review、completed 中的哪一段
- 两类 review policy 至少各有一条可验证路径
- M1 smoke 与 offline validation 通过
- M1 freeze review 给出明确 `go / no-go`

---

# 10. 跨阶段关键路径

M1 的关键路径建议固定为：

`Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4`

关键原因如下：

- 没有 Phase 0 的冻结，Phase 1 很容易反复改 schema
- 没有 Phase 1 的 contract / migration 底座，Phase 2 的 compile surface 会很快返工
- 没有 Phase 2 的 compile surface，Phase 3 的 `resume` 会缺少明确入口
- 没有 Phase 3 的 resumable runtime，Phase 4 的 review / operator DX 只能停留在展示层

任何想提前插入 M1.5 或 M2 能力的需求，都需要先回答：

**它是在补齐 M1 的最小闭环，还是在制造新的阶段漂移？**

---

# 11. 并行推进建议

如果团队资源允许，建议按四个编组并行：

- 编组 A：治理与 contracts，负责 Phase 0 与 Phase 1
- 编组 B：compile / preset / operator surface，负责 Phase 2
- 编组 C：runtime / handoff / transaction，负责 Phase 3
- 编组 D：review / smoke / docs / freeze review，负责 Phase 4

并行约束：

- B 依赖 A 冻结的 contract / migration 结果
- C 依赖 B 冻结的 compile / resume 边界
- D 可以在 C 接近完成时提前准备 smoke 和 freeze review 草稿

---

# 12. 每个 Phase 的统一评审问题

每个 M1 phase 结束时，建议都回答以下 7 个问题：

1. 本阶段原定输出是否全部完成
2. 哪些接口已经存在但语义还不稳
3. 哪些项明确延后到下一阶段，为什么
4. 是否引入了新的状态、事件或对象漂移
5. 现有测试是否覆盖了本阶段最容易回归的路径
6. 是否允许进入下一阶段
7. 当前最大的 1~3 个风险是什么

如果第 6 问无法明确回答，则默认不进入下一阶段。

---

# 13. M1 总体验收口径

M1 结束时，建议至少满足以下条件：

- Run Status State Machine 已文档化并与实现一致
- `PresetResolver.suggest()` 已稳定可用，且仅提供建议
- `suggest()` 已被固定为离线确定性启发式方案
- run 可以显式经历 `create -> compile/recompile -> resume`
- `HandoffLite` 已进入持久化与查询范围
- `RuntimeGateway` 不再只是空壳占位，`start/resume` 已进入真实路径
- runtime 主链在 M1 范围内仍保持纯 Python 可恢复语义，不依赖真实 LangGraph 集成
- `execute_run()`、`resume_run()`、`cancel_run()` 具备状态守卫或幂等约束
- compile / resume / execute 的关键多步写入具备事务性保护，且 UoW 边界已文档化
- `human_required` policy 不再只是静态配置，而有最小可执行闭环
- CLI / API 可以查询更清晰的 status detail / handoff / review 状态
- M1 smoke 在断网且无任何 LLM API Key 的环境中通过
- M1 freeze review 已完成并给出明确结论

---

# 14. 进入 M1.5 / M2 的准入 Gate

只有满足以下条件，才建议进入 M1.5 或 M2：

- M1 的 compile / resume / handoff 主链已经稳定
- `PresetResolver` 的建议功能没有绕过人工选择权
- `human_required` 路径已经可验证，不再是死字段
- runtime 防腐层边界仍然成立
- 离线 smoke 与 offline validation 已更新并通过
- 技术债登记簿已更新，明确哪些项留给 M1.5，哪些项留给 M2

若以上任一项不满足，则继续留在 M1 收口，不启动后续阶段。

---

# 15. 一句话使用建议

M1 不要把自己做成“M2 的预演”。  
它的职责很明确：**把 M0 的 bootstrap spine 升级成最小可恢复、可交接、可重编译、可审查的稳定主链。**
