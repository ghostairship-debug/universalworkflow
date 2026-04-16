# M0 Phase 5 — CLI、DX、Smoke 与 Freeze Review 详细开发方案

**Phase 目标：** 让 M0 成为一个可操作、可启动、可复现验收、可正式关门的阶段，而不是停留在开发者内部状态。

**覆盖任务：** T0-21a、T0-21b、T0-22、T0-22.5、T0-23、T0-24、T0-25、T0-26、T0-27

---

# 1. 本阶段要解决什么

Phase 5 是 M0 的交付收口阶段，解决以下问题：

- operator 如何不依赖 Web 页面使用系统
- 新人如何冷启动
- 团队如何在 5 分钟内完成最小验收
- M0 如何被结构化地宣告完成或未完成

---

# 2. 输入与前置条件

## 2.1 输入材料

- Phase 2 的 timeline 能力
- Phase 3 的 Orchestrator API
- Phase 4 的执行闭环

## 2.2 Entry Criteria

- run 可通过 API 创建
- timeline 已有真实事件
- Evidence / ReviewVerdict 已能回查

---

# 3. 核心交付物

- `apps/operator-cli/` 或等价 CLI 模块
- `Makefile` / `scripts/`
- `pyproject.toml` 或等价依赖清单
- `docs/smoke/m0-smoke.md`
- `docs/tech-debt-registry.md`
- `README.md` 或 `docs/getting-started-m0.md`
- `docs/reviews/m0-freeze-review.md`

---

# 4. 详细工作流

## 4.1 工作流 A：Operator CLI v0

对应任务：T0-21a、T0-21b、T0-25

### 必须支持的命令

- `workflowctl run create --goal ... --preset ...`
- `workflowctl run cancel <run_id>`
- `workflowctl run status <run_id>`
- `workflowctl run timeline <run_id>`
- `workflowctl task evidence <task_id>`
- `workflowctl preset list`
- `workflowctl db reset`

### 开发步骤

1. 定义 CLI 命令结构。
2. 对接 Orchestrator API。
3. 统一输出格式，确保 operator 可直接阅读。
4. 为 timeline 输出提供摘要展示，而不是原始 JSON 堆叠。

### 设计重点

- 命令命名与 API 语义保持一致
- 输出以“可排障”为目标
- 错误提示要能指向下一步动作

## 4.2 工作流 B：DX 脚本与冷启动入口

对应任务：T0-22

### 必须提供

- `make dev`
- `make migrate`
- `make reset-db`
- `make smoke`
- `make logs-tail`

并要求：

- 依赖入口单一
- 本地解释器与依赖安装口径固定

### 开发步骤

1. 统一本地启动顺序。
2. 把常用操作收敛成少量命令。
3. 保证失败时输出可定位。

### 设计重点

- 命令要适合新人直接复制执行
- reset-db 和 migrate 必须是可重复的
- smoke 要依赖统一入口，而不是人工拼流程

## 4.3 工作流 C：Smoke 文档与自动化

对应任务：T0-23、T0-24

### M0 Smoke 建议流程

1. `reset-db`
2. `migrate`
3. 清理或显式覆盖 LLM API Key
4. seed presets
5. 创建 run
6. 查询 run
7. 查询 timeline
8. 断言关键事件存在

### 开发步骤

1. 先写手工 smoke 文档。
2. 再将其脚本化成 `make smoke`。
3. 再为失败输出补清晰提示。

### 验收要求

- 5 分钟内完成
- 全流程可重复
- 失败时能快速定位在 DB / API / preset / timeline 哪一层
- 断网环境可通过
- 无任何 LLM API Key 可通过

说明：

- “断网 + 无 LLM API Key” 是 M0 的硬性准入条件，不是建议项

## 4.4 工作流 D：README 与 Freeze Review

对应任务：T0-26、T0-27

### README 必须覆盖

- 环境要求
- 启动命令
- 常用命令
- smoke 执行方式
- 常见错误与排查方法

### Freeze Review 必须回答

- M0 非目标是否被遵守
- Wave 1 是否已冻结
- smoke 是否稳定
- `docs/tech-debt-registry.md` 是否完整登记了延后项
- 哪些内容延后到 M1 / M2
- 是否允许进入 M1

### Freeze Review 输出要求

- 必须给出明确 `go / no-go`
- 必须列出遗留问题
- 必须标明哪些遗留属于非阻塞

---

# 5. 建议实现顺序

1. 先补 `timeline` 查询与 CLI 命令
2. 在 Phase 3 完成后先推进 `T0-21a`
3. 再做 DX 脚本与依赖管理
4. 再写 smoke 文档并自动化
5. 在执行闭环完成后补 `T0-21b`
6. 最后写 README 和 freeze review

因为 freeze review 必须建立在 smoke 稳定可复现的前提上。

---

# 6. 建议测试设计

## 6.1 CLI 测试

- `preset list` 可返回 bootstrap presets
- `run create` 成功
- `run cancel` 可取消开发态脏 run
- `run timeline` 可查看关键事件
- `task evidence` 可返回对应证据
- `db reset` 仅用于开发态并能恢复干净状态

## 6.2 DX 测试

- `make migrate` 可执行
- `make reset-db` 可执行
- `make smoke` 可执行
- 依赖安装入口唯一且可复现

## 6.3 冷启动测试

建议由不参与实现的人按 README 完成一次冷启动，验证：

- 是否需要额外口头说明
- 是否存在遗漏命令
- 是否能独立跑通 smoke
- 是否能在无 API Key 的情况下完成 smoke

---

# 7. 阶段内检查点

## Checkpoint 5A：CLI 可操作

检查项：

- 不开 Web 页面是否仍能完成最小操作
- CLI 输出是否适合排障

## Checkpoint 5B：Smoke 可复现

检查项：

- 手工 smoke 与自动化 smoke 是否一致
- 是否控制在 5 分钟内

## Checkpoint 5C：Freeze Review 可落结论

检查项：

- 是否已有足够证据给出 go / no-go
- 是否清楚列出遗留问题与归属阶段

---

# 8. 验收与退出标准

## 8.1 Exit Criteria

- `workflowctl` 最小命令集可用
- `make dev / migrate / reset-db / smoke / logs-tail` 可用
- M0 Smoke 可在 5 分钟内跑通
- M0 Smoke 可在断网且无任何 LLM API Key 的环境中跑通
- README 足够支持新人冷启动
- Freeze Review 已输出明确结论

## 8.2 Gate 决策问题

1. operator 是否已能独立操作系统
2. 团队是否已能稳定复现 M0 验收
3. M0 是否已具备进入 M1 的正式依据

任意一项不成立，则 M0 不能关门。

---

# 9. 风险与缓解

- 风险：CLI 只是 API 包装层，没有运维价值
  缓解：输出必须围绕状态、timeline、evidence 三类排障信息设计

- 风险：smoke 脚本与文档不一致
  缓解：先写手工文档，再将文档逐步脚本化

- 风险：freeze review 流于会议结论，没有证据支撑
  缓解：要求 review 文档绑定 smoke 结果、遗留项和 go / no-go

---

# 10. 本阶段完成后的直接产出

Phase 5 完成后，团队应立即拥有以下能力：

- 可以不用 Web 控制台完成 M0 最小操作
- 可以通过统一命令完成启动、迁移、重置和验收
- 可以基于 freeze review 正式判断是否进入 M1

这三件事成立，Phase 5 才算完成。
