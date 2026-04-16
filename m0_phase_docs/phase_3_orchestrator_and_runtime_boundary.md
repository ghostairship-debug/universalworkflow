# M0 Phase 3 — Orchestrator 与 Runtime 边界详细开发方案

**Phase 目标：** 建立 Orchestrator API skeleton、LangGraph 防腐层占位和 thin compile 接口，让 M0 形成最小控制环入口。

**覆盖任务：** T0-15、T0-15.5、T0-16、T0-17

---

# 1. 本阶段要解决什么

Phase 3 解决的是“系统如何被启动、如何调用 runtime、如何把 goal 和 preset 变成最小执行对象”的问题。

它不是完整编排实现，而是为后续 spine 提供一个足够薄但不虚假的主入口。

---

# 2. 输入与前置条件

## 2.1 输入材料

- Phase 2 的 SQLite 与 repository
- Phase 1 的 contracts / preset 规则
- ADR-004（LangGraph 防腐层）

## 2.2 Entry Criteria

- run / preset / event 已可持久化
- timeline 可查询
- `PresetResolver = manual only` 已生效

---

# 3. 核心交付物

- `apps/orchestrator-api/`
- `packages/runtime-langgraph/`
- `packages/planner-compiler/` 中的 thin compile 占位
- `RuntimeGateway`
- API 错误响应约定
- 最小控制面 API：
  - `POST /runs`
  - `GET /runs/{id}`
  - `GET /runs/{id}/timeline`
  - `GET /presets`
  - `GET /tasks/{id}/evidence`

---

# 4. 详细工作流

## 4.1 工作流 A：Orchestrator API skeleton

对应任务：T0-15

### 开发步骤

1. 先定义 API 分层：
   - router
   - service
   - repository
   - runtime gateway
2. 明确创建 run 的最小请求和响应结构。
3. 接入 preset 校验与 event 记录。
4. 接入 timeline 和 evidence 查询。

### `POST /runs` 最小行为

- 接收 `goal` 和 `preset_id`
- 校验 `preset_id`
- 创建 run
- 写入 `run_created`
- 写入 `preset_selected`
- 返回 run 基础信息

边界说明：

- `POST /runs` 在 M0 只负责创建 Run 与记录 Preset 选择
- 不通过公共 API 暴露 compile 步骤
- thin compile 保持内部占位能力，不与 run 创建耦合为单一步骤

### 设计原则

- API 层不直接处理 LangGraph 细节
- API 层不直接写 SQL
- 所有关键动作都应落 event

## 4.2 工作流 B：runtime-langgraph 防腐层

对应任务：T0-16

### 开发步骤

1. 建立 runtime gateway 接口。
2. 把 LangGraph 封装在独立模块内。
3. 让上层只看到“启动 / 继续 / 状态回写”的语义接口。
4. 明确 import 隔离与 state 约束。

### 最小边界要求

- 业务层不知道 LangGraph state 长什么样
- contracts 层不引用 LangGraph 类型
- runtime 层只保留 ref / handle / graph_step 等轻量信息
- `contracts/` 与 `core-domain/` 不允许直接 import `langgraph`
- LangGraph State 不允许承载 `contracts` 包定义的对象实例

### M0 只需要做到

- graph wrapper 占位
- 能被 API 调用
- 为 M1 的主控制图预留接入点

## 4.3 工作流 C：Thin Compile v0

对应任务：T0-17

### 开发步骤

1. 定义 compile 输入：
   - `goal`
   - `preset`
2. 定义 compile 输出：
   - 单个 `RuntimeTask`
   - 对应 `TaskPacket`
3. 把 compile 结果落库。
4. 明确 `Dispatch` 包含 claim check placeholder，M0 默认 no-op pass。

### 设计原则

- M0 不做复杂 planner
- M0 不做多任务 DAG
- M0 只钉输入输出接口形状

### 最小语义

- `feature_delivery` / `research_spike` 都可转成一个最小 `RuntimeTask`
- `TaskPacket` 能为 ShellAdapter 提供执行所需上下文

---

# 5. 推荐实现顺序

1. 先立 API skeleton
2. 再立 runtime gateway
3. 最后把 thin compile 接进去

因为 compile 和 runtime 都要挂在 API 主入口之后，顺序反过来容易写成孤立模块。

---

# 6. 建议测试设计

## 6.1 API 测试

- `POST /runs` 成功创建最小 run
- 缺失 preset 时失败
- `GET /presets` 可返回 preset 列表
- `GET /runs/{id}/timeline` 可读
- 错误响应格式稳定且可供 CLI 消费

## 6.2 Runtime 边界测试

- 上层不直接 import LangGraph 类型
- runtime gateway 可以被 mock 替换
- `contracts/` 与 `core-domain/` 无直接 `langgraph` import
- LangGraph State 不承载 contract 实例

## 6.3 Thin Compile 测试

- 同一输入下输出结构稳定
- 生成的 `RuntimeTask` / `TaskPacket` 可落库

---

# 7. 阶段内检查点

## Checkpoint 3A：API 入口成立

检查项：

- run 是否能通过 API 创建
- preset 校验是否已经接入

## Checkpoint 3B：Runtime 边界成立

检查项：

- LangGraph 是否被隔离在 runtime 模块内
- contracts 是否被污染
- 是否已建立 `RuntimeGateway` 作为唯一入口

## Checkpoint 3C：Compile 形状锁定

检查项：

- `goal + preset -> RuntimeTask + TaskPacket` 是否稳定
- 是否仍保持单任务占位，不被提前膨胀

---

# 8. 验收与退出标准

## 8.1 Exit Criteria

- Orchestrator API 可本地启动
- `POST /runs` 可创建 run
- `GET /presets` / `GET /runs/{id}` / `GET /runs/{id}/timeline` 可用
- runtime-langgraph 防腐层已建立
- `RuntimeGateway` 已建立
- thin compile v0 已能生成最小 `RuntimeTask` / `TaskPacket`

## 8.2 Gate 决策问题

1. 主控制环入口是否已经成立
2. runtime 是否已被隔离在可替换边界内
3. compile 是否已经提供稳定输入输出

任意一项不成立，就不进入 Phase 4。

---

# 9. 风险与缓解

- 风险：API 层直接长进编排逻辑
  缓解：保持 router/service/runtime gateway/repository 分层

- 风险：runtime wrapper 只是薄转发，没有真正隔离
  缓解：禁止 contracts 和 service 层引用 LangGraph 细节

- 风险：thin compile 提前变成 planner
  缓解：限定为单任务 compile，占位而非复杂规划

---

# 10. 本阶段完成后的直接产出

Phase 3 完成后，团队应立即拥有以下能力：

- 可以通过 API 创建 run 并拿到基础状态
- 可以通过 runtime gateway 而不是直接依赖 LangGraph
- 可以把最小 goal + preset 编译成执行对象

这三件事成立，Phase 3 才算完成。
