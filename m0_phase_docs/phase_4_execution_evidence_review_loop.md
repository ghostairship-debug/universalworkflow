# M0 Phase 4 — 执行、证据与审查闭环详细开发方案

**Phase 目标：** 打通 ShellAdapter、Evidence builder 和 Auto-Review，让系统从“能建 run”进化到“能解释执行结果”。

**覆盖任务：** T0-18、T0-19、T0-20

---

# 1. 本阶段要解决什么

Phase 4 解决的是最小执行闭环：

- 任务如何被真正执行
- 执行结果如何变成结构化 Evidence
- Evidence 如何进一步形成 ReviewVerdict

没有这个阶段，M0 只能算是控制面骨架，还不能支撑 M1 的最窄 spine。

---

# 2. 输入与前置条件

## 2.1 输入材料

- Phase 3 生成的 `RuntimeTask` / `TaskPacket`
- Phase 2 的持久化和 timeline 能力
- Phase 0 的 Evidence ADR

## 2.2 Entry Criteria

- `RuntimeTask` 和 `TaskPacket` 已可落库
- Orchestrator API 已能创建最小 run
- `Evidence` / `ReviewVerdict` schema 已冻结

---

# 3. 核心交付物

- `packages/worker-adapters/shell_adapter.py`
- `packages/core-domain/evidence_builder.py`
- `packages/quality/auto_review_v0.py`

---

# 4. 详细工作流

## 4.1 工作流 A：ShellAdapter v0

对应任务：T0-18

### 开发步骤

1. 定义 WorkerAdapter 最小协议。
2. 实现 ShellAdapter 的核心方法：
   - `get_capabilities()`
   - `estimate_cost(packet)`
   - `launch(packet)`
   - `collect_artifacts(task_id)`
3. 约定命令执行返回结构：
   - `return_code`
   - `stdout`
   - `stderr`
   - `started_at`
   - `finished_at`

### M0 范围约束

- 只支持简单 shell 命令
- 不处理复杂隔离
- 不处理多 worker 调度
- 不处理 heartbeat / lease

### 设计重点

- 输出结构必须稳定
- 执行结果必须足以支撑 Evidence 构建
- 错误输出不能只靠文本打印，要进入结构化结果
- ShellAdapter 不负责 artifact 的 hash / mtime 确权

## 4.2 工作流 B：Evidence Builder v0

对应任务：T0-19

### 开发步骤

1. 定义执行结果到 Evidence 的映射规则。
2. 抽取最小结构化字段：
   - `summary`
   - `changed_files`
   - `checks`
   - `known_gaps`
   - `artifact_refs`
3. 把原始执行信息收进 machine-readable payload。
4. 将 Evidence 落库并写 event。

### `artifact_refs` 最小要求

- `path`
- `sha256`
- `mtime`
- `size_bytes`

### 设计原则

- `summary` 只服务人类快速理解
- 机器判断依赖结构化字段
- 不能把原始 stdout/stderr 当作完整 Evidence
- `artifact_refs` 的 hash / mtime 由 Evidence Builder 负责生成，不由 ShellAdapter 负责
- 必须具备最小的 out-of-band change 侦测能力

## 4.3 工作流 C：Auto-Review v0

对应任务：T0-20

### 开发步骤

1. 定义最小 pass / fail 规则。
2. 从 Evidence 中读取执行结果关键信号。
3. 生成 `ReviewVerdict` 并落库。

### M0 最小规则

- `return_code == 0` 且无明确错误输出：`decision = pass`
- 否则：`decision = fail`

### 设计原则

- 这不是最终质量系统
- 目标是证明 ReviewVerdict 能进入主链
- 规则必须简单、稳定、可预测

---

# 5. 建议实现顺序

1. 先做 ShellAdapter
2. 再做 Evidence Builder
3. 最后接 Auto-Review

因为 Review 的可信度依赖稳定的 Evidence，而 Evidence 的可信度依赖稳定的执行结果结构。

---

# 6. 建议测试设计

## 6.1 ShellAdapter 测试

- `echo` 命令成功执行
- 非法命令可返回失败结构
- stdout / stderr / return_code 可被完整拿到

## 6.2 Evidence 测试

- 成功任务可生成有效 Evidence
- 失败任务也可生成有效 Evidence
- 结构化字段不为空且语义清楚
- `artifact_refs` 已包含 `sha256 / mtime / size_bytes`
- hash 校验失败可识别为 out-of-band change

## 6.3 Review 测试

- 成功命令得到 `pass`
- 失败命令得到 `fail`
- `ReviewVerdict` 可回查到 `Evidence`

## 6.4 集成测试

建议做一条最小集成流：

`TaskPacket -> ShellAdapter -> Execution Result -> Evidence -> ReviewVerdict`

---

# 7. 阶段内检查点

## Checkpoint 4A：执行结果结构锁定

检查项：

- ShellAdapter 输出结构是否稳定
- 是否足以被 Evidence Builder 消费

## Checkpoint 4B：Evidence 归一化锁定

检查项：

- summary 与结构化字段是否分离清楚
- 是否存在“只存日志不存证据”的问题

## Checkpoint 4C：Review 闭环成立

检查项：

- `pass / fail` 是否可预测
- ReviewVerdict 是否已进入主链

---

# 8. 验收与退出标准

## 8.1 Exit Criteria

- ShellAdapter 能执行最小 shell 命令
- 执行结果可转成有效 Evidence
- ReviewVerdict 能根据结果给出 pass / fail
- 相关数据能被持久化和查询

## 8.2 Gate 决策问题

1. 系统是否已经不仅能建 run，而且能解释执行结果
2. Evidence 是否已成为机器可读真相源
3. ReviewVerdict 是否已成为可回查的审核结论

任意一项不成立，就不进入 Phase 5。

---

# 9. 风险与缓解

- 风险：ShellAdapter 过早追求通用性
  缓解：M0 只覆盖最小命令执行

- 风险：Evidence builder 只是把输出原样打包
  缓解：必须抽取结构化字段，保留人机双轨

- 风险：Auto-Review 被过度设计
  缓解：限制为可预测的 pass / fail 基线

---

# 10. 本阶段完成后的直接产出

Phase 4 完成后，团队应立即拥有以下能力：

- 可以执行一个最小任务
- 可以把执行结果变成结构化 Evidence
- 可以对 Evidence 给出最小审查结论

这三件事成立，Phase 4 才算完成。
