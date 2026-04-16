# M1 执行循环协议（代码级 Task Card 标准）

**文档定位：** 本文定义 M1 阶段的标准执行循环、task 粒度规则、复杂任务拆分标准与安全执行要求。  
**适用范围：** 从 M1 开始，所有 phase 文档、task cards 与复杂 task 独立 md 都应遵循本文。

---

# 1. 为什么需要升级执行循环

M0 阶段的 task card 更偏向“阶段提醒”与“目标概述”，足以支撑 bootstrap 实施，但不适合 M1 这种已经开始涉及：

- contract / migration / repository 协同变更
- compile / resume / handoff / review policy 这类状态语义升级
- API、CLI、runtime、持久化多层联动

从 M1 开始，如果 task card 仍然只写“做什么”，而不写“读什么、改什么、怎么验、哪里危险”，就很容易出现：

- 任务边界漂移
- 中途发明接口字段
- 跨层修改失控
- 测试只覆盖 happy path
- 复杂任务在未冻结中间态前直接开改

因此，M1 必须切换到 **代码级 task card + 复杂任务独立 md** 的执行方式。

---

# 2. 标准执行循环

每个 phase 必须按以下顺序推进：

1. 回读基线  
   读取 M0 freeze review、技术债登记簿、最新评估结论、当前 phase 上游实现结果。

2. 产出 phase 详细文档  
   在 `m1_phase_docs/` 下生成当前 phase 文档，冻结本阶段的目标、边界、依赖、接口变化和 phase gate。

3. 生成 phase 级 task 索引  
   在 `docs/task_cards/` 下生成当前 phase 的 task 索引文档，列出所有 task、依赖关系、预计影响层和验收方式。

4. 识别复杂 task  
   按本文的复杂度判定规则，为高风险 task 创建独立 md 文档。

5. 冻结 task 边界  
   每张 task card 在编码前都要冻结 read set、write set、测试方案、风险点和回滚点。

6. 逐 task 实施  
   一次只推进一个 task，除非两个 task 的 write set 完全不重叠且测试互不依赖。

7. 完成后立即验证  
   每完成一个 task，立即运行该卡定义的测试，并回填 task 文档中的实现偏差、已知问题和完成证据。

8. phase gate review  
   当前 phase 的所有 task 完成后，重新评估是否满足 phase gate。

9. 进入下一 phase 前复评  
   根据当前实现结果重新审视下一 phase 的拆分方式。若实际接口或风险已经变化，必须先更新 phase 文档和 task cards，再进入实施。

---

# 3. 文档产物与目录结构

每个 phase 至少产出以下三层文档：

## 3.1 Phase 详细文档

路径示例：

- `m1_phase_docs/phase_0_rebaseline_and_scope_freeze.md`

作用：

- 冻结当前 phase 的目标、边界、接口变化、风险与 phase gate

## 3.2 Phase Task 索引

路径示例：

- `docs/task_cards/m1_phase_0_task_cards.md`

作用：

- 作为当前 phase 的执行导航页
- 列出所有 task card、依赖顺序、复杂度等级、对应独立 md 链接

## 3.3 Complex Task 独立 md

路径示例：

- `docs/task_cards/m1_phase_0/P0-T02_contract_delta_freeze.md`
- `docs/task_cards/m1_phase_3/P3-T04_resume_transaction_boundary.md`

作用：

- 对高风险任务做代码级拆解
- 作为实际编码时的唯一执行说明

---

# 4. Task 分级规则

M1 的 task 分为两类：

## 4.1 标准 Task

适用于以下任务：

- 改动范围清晰
- write set 小
- 不涉及 schema / migration / state machine / transaction
- 可以在一个连续实现段内完成并验证

标准 task 可以只写在 phase task 索引文档里，但仍必须是代码级描述。

## 4.2 复杂 Task

满足以下任一条件，就必须单独生成 md：

- 涉及 contract、migration、repository、event schema、status 变更
- 涉及 public API / CLI / service 边界调整
- 涉及 runtime、resume、handoff、idempotency、transaction、rollback 语义
- 涉及跨 3 个及以上目录层或 5 个及以上文件
- 需要先落中间态、再继续下一个实现步骤
- 需要多轮测试或需要验证兼容性 / 向后兼容
- 风险判断上“不写细就容易做错”

**默认规则：**  
对复杂性判断拿不准时，按复杂 task 处理，不按标准 task 处理。

---

# 5. Phase 文档必须包含的内容

每个 `m1_phase_docs/phase_x_*.md` 至少包含：

- 本 phase 的目标
- 与 M0 / 上一 phase 的差异
- 本 phase 的 in scope / out of scope
- 依赖的现有模块、文件、接口
- 计划新增 / 修改的 contract、service、API、CLI、migration
- phase task 拆解原则
- phase gate
- 风险与回退策略

如果 phase 本身足够复杂，还应补：

- 关键状态机变化
- 新旧接口兼容策略
- 中间态允许存在多久
- 哪些 task 必须串行执行

---

# 6. Phase Task 索引必须包含的内容

每个 `docs/task_cards/m1_phase_x_task_cards.md` 至少包含：

- 当前 phase 的 reassessment
- 当前 phase 的 task 列表与依赖顺序
- 每张 task 的复杂度等级：`standard` 或 `complex`
- 每张 task 的目标与受影响层
- 每张 task 的预期输出
- 每张 task 的测试方式
- 若为 complex，必须给出独立 md 路径

建议使用如下字段：

- `Task ID`
- `Type`
- `Summary`
- `Depends On`
- `Read Set`
- `Write Set`
- `Tests`
- `Output`
- `Doc Link`

---

# 7. Complex Task 独立 md 的强制字段

每个复杂 task 的独立 md 至少包含以下字段：

## 7.1 基本信息

- Task ID
- 所属 phase
- 当前状态：`draft / ready / in_progress / blocked / done / verified`
- 上游依赖

## 7.2 任务目标

- 本卡要解决的精确代码问题
- 本卡明确不解决什么

## 7.3 Read Set

- 实现前必须先读的文件列表
- 需要重点理解的类、函数、表或测试

## 7.4 Write Set

- 允许改动的文件
- 原则上不应改动的文件

## 7.5 接口与数据变化

- 受影响的 contract / API / CLI / migration / event / status
- 新增字段、状态、事件、路由或命令
- 兼容性约束

## 7.6 不变量

- 本卡实现时不得破坏的系统约束
- 必须保持成立的旧行为

## 7.7 实施步骤

步骤必须写到代码级，至少覆盖：

- 先改哪一层
- 改哪些类 / 函数 / 路由 / SQL
- 哪一步完成后先跑什么测试
- 哪些步骤之间不能交叉

## 7.8 测试计划

- 必跑单测
- 必跑集成测试
- 是否需要 smoke / 手动验证
- 回归关注点

## 7.9 风险与回滚点

- 最可能引入的回归
- 若中间态失败，应该回退到哪个边界
- 哪些文件改动必须一起提交

## 7.10 完成证据

- 实际修改文件清单
- 实际测试结果
- 与原计划不一致的地方
- 留给下一张卡的注意事项

---

# 8. 代码级 Task Card 的写法要求

不合格示例：

- “增加 resume 能力”
- “让 compile 可用”
- “完善 review”

合格示例应写成这类粒度：

- “在 `packages/contracts/models.py` 中补 `RuntimeStateRef` 持久化 contract，在 `infra/migrations/002_runtime_state_refs.sql` 中新增表，并为 `packages/core_domain/repositories.py` 增加对应 repository round-trip 测试”
- “在 `packages/core_domain/services.py` 中新增 `resume_run()`，只允许 `prepared` 或 `paused` 进入 `running`，对非法状态抛 `WorkflowError`，并在 `tests/test_execution_loop.py` 增加非法状态转换测试”
- “在 `apps/orchestrator_api/main.py` 中新增 `POST /runs/{run_id}/compile` 与 `POST /runs/{run_id}/resume`，同时补 `tests/test_api.py` 对错误响应与 happy path 的覆盖”

---

# 9. 安全执行规则

为了避免“边写边漂移”，执行时必须遵守以下规则：

- 编码前先冻结 write set；如需扩大 write set，必须先更新 task 文档
- 涉及 migration、contract、event、status 的 task 不得跳过独立 md
- 一个 complex task 未验证通过前，不得直接开始其下游 task
- 若真实实现发现任务拆分错误，应暂停编码，先回写文档，再继续
- 任何新增 public 接口都必须同步定义测试入口
- 任何状态转换都必须有正向测试和非法状态测试
- 任何事务性改动都必须明确原子边界
- 任何幂等接口都必须至少验证重复调用一次

---

# 10. Phase Gate 前的必查项

进入下一 phase 前，当前 phase 至少要确认：

- 所有 task 文档状态已更新
- 所有 complex task 都有完成证据
- 计划中的测试都已运行或明确说明未运行原因
- 当前 phase 是否引入了新的技术债
- 下一 phase 的依赖是否仍然成立
- 是否需要重排下一 phase 的 task 顺序

只要上述任一项回答不清楚，就不进入下一 phase。

---

# 11. 推荐文件命名

建议采用统一命名，避免后续难检索：

- phase 文档：`phase_<n>_<short_name>.md`
- phase task 索引：`m1_phase_<n>_task_cards.md`
- complex task：`P<n>-T<nn>_<short_name>.md`

例如：

- `m1_phase_docs/phase_2_preset_suggestion_and_compile_surface.md`
- `docs/task_cards/m1_phase_2_task_cards.md`
- `docs/task_cards/m1_phase_2/P2-T03_compile_api_and_cli_surface.md`

---

# 12. 一句话原则

从 M1 开始，task card 不只是“任务提醒”，而是**安全编码说明书**。  
如果一张卡在编码前还不能回答“改什么、为什么、怎么验、哪里容易错”，那它就还不能进入执行。
