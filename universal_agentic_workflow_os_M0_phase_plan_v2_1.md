# Universal Agentic Workflow OS v2.1 — M0 Phase 总览与索引

**模式：Local-first, Cloud-ready**

**文档定位：** 本文不再承载每个 phase 的完整细节，而作为 M0 阶段的总览、导航和执行入口页。每个 phase 的详细开发方案已拆分为独立文档，便于分阶段推进、评审和后续持续维护。

---

# 1. 本文怎么使用

如果要回答“**M0 一共分几段、顺序是什么、何时能进入 M1**”，看本文。

如果要回答“**某个 phase 具体怎么做、先做什么、验什么、有哪些风险**”，看对应 phase 子文档。

建议使用方式：

1. 先阅读本文，确认整体节奏和关键路径
2. 再进入当前正在执行的 phase 子文档
3. phase 结束后回到本文，执行阶段 gate 和整体准入检查

M0 文档职责同时固定如下：

- 总说明文档：保留长期语义与演进方向
- `universal_agentic_workflow_os_M0_task_breakdown_v2_1.md`：作为 M0 字段、任务与验收口径的主文档
- `m0_phase_docs/`：只承载执行化方案，不重复发明协议字段

---

# 2. M0 Phase 总览

| Phase | 建议时长 | 目标 | 对应详细文档 | 结束 gate |
| --- | --- | --- | --- | --- |
| Phase 0 | 2~3 天 | 冻结范围、对象职责和关键架构决策 | `m0_phase_docs/phase_0_scope_and_governance.md` | M0 边界冻结 |
| Phase 1 | 2~3 天 | 完成 Wave 1 schema 与 Preset 冷启动基线 | `m0_phase_docs/phase_1_contracts_and_preset_baseline.md` | contracts / preset baseline 冻结 |
| Phase 2 | 2~3 天 | 建立 SQLite、仓储层和 timeline 底座 | `m0_phase_docs/phase_2_persistence_and_timeline_foundation.md` | 持久化底座可用 |
| Phase 3 | 2~3 天 | 建立 Orchestrator skeleton、runtime 边界与 thin compile 占位 | `m0_phase_docs/phase_3_orchestrator_and_runtime_boundary.md` | 主控制环入口成立 |
| Phase 4 | 2 天 | 打通 ShellAdapter → Evidence → Auto-Review 闭环 | `m0_phase_docs/phase_4_execution_evidence_review_loop.md` | 最小执行闭环成立 |
| Phase 5 | 2~3 天 | 建立 CLI / DX / smoke，并完成 freeze review | `m0_phase_docs/phase_5_cli_dx_smoke_and_freeze_review.md` | M0 go / no-go 决策 |

**建议总周期：** 14~18 个工作日，约 2~3 周。

---

# 3. 各 Phase 文档导航

## Phase 0

文档：`m0_phase_docs/phase_0_scope_and_governance.md`

适合在以下场景阅读：

- 团队正在定义 M0 做与不做
- Wave 1 / Wave 2 / Wave 3 对象边界仍有争议
- 需要回到 ADR 澄清架构取舍

## Phase 1

文档：`m0_phase_docs/phase_1_contracts_and_preset_baseline.md`

适合在以下场景阅读：

- 正在设计 contracts v1
- 正在落 bootstrap presets
- 需要锁死 `manual preset only`

## Phase 2

文档：`m0_phase_docs/phase_2_persistence_and_timeline_foundation.md`

适合在以下场景阅读：

- 正在设计 SQLite 表结构
- 正在实现 repository
- 正在补 run events / timeline

## Phase 3

文档：`m0_phase_docs/phase_3_orchestrator_and_runtime_boundary.md`

适合在以下场景阅读：

- 正在搭 API skeleton
- 正在处理 LangGraph 防腐层
- 正在确定 thin compile 的输入输出

## Phase 4

文档：`m0_phase_docs/phase_4_execution_evidence_review_loop.md`

适合在以下场景阅读：

- 正在实现 ShellAdapter
- 正在设计 Evidence builder
- 正在落最小 Auto-Review

## Phase 5

文档：`m0_phase_docs/phase_5_cli_dx_smoke_and_freeze_review.md`

适合在以下场景阅读：

- 正在做 operator CLI
- 正在整理 DX 命令和 smoke
- 正在准备 M0 freeze review

---

# 4. 跨阶段关键路径

M0 的关键路径建议固定为：

`Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 5`

说明：

- Phase 4 会阻塞 M1 的最窄 spine，但不会早于 Phase 3 阻塞主入口建立
- Phase 5 是从“能开发”切换到“能交付”的收口阶段

映射到任务层面的关键路径为：

`T0-01 → T0-02 → T0-03 → T0-03.5 → T0-10 → T0-11 → T0-12 → T0-12.5 → T0-15 → T0-15.5 → T0-21a → T0-23 → T0-24 → T0-27`

任何偏离这条路径的工作，都需要回答：

**它是在缩短 M0 完成时间，还是在制造非关键分支？**

---

# 5. 并行推进建议

若团队资源允许，建议按四个编组并行：

- 编组 A：语义与治理
  负责 Phase 0
- 编组 B：Contracts 与 Preset
  负责 Phase 1
- 编组 C：持久化与 API 骨架
  负责 Phase 2 ~ Phase 3
- 编组 D：执行闭环与操作面
  负责 Phase 4 ~ Phase 5

并行约束：

- B 依赖 A 的冻结结果
- C 依赖 B 的 contracts 结果
- D 依赖 C 的 API / event / persistence 结果

补充并行规则：

- `T0-05 ~ T0-09` 可在 `T0-02` 完成后与 `T0-03` / `T0-03.5` 并行推进
- `T0-21a` 可在 Phase 3 后启动，不必等待 Phase 4
- `T0-21b` 依赖 Phase 4 的执行闭环

---

# 6. 每个 Phase 的统一评审问题

每个 phase 结束时，建议都回答以下 6 个问题：

1. 本阶段原定输出是否全部完成
2. 哪些项已完成但质量不足
3. 哪些项明确延后，为什么
4. 是否出现术语、对象或边界漂移
5. 是否允许进入下一阶段
6. 当前最大的 1~3 个风险是什么

如果无法明确回答第 5 问，则默认不进入下一阶段。

---

# 7. M0 总体验收口径

M0 结束时，不要求第一条完整 spine 跑通，但必须满足以下条件：

- Wave 1 对象已冻结并具备 schema v1
- Preset 冷启动已成立，且只允许 manual 模式
- SQLite + migration + repository 已成立
- run events timeline 已成立
- Orchestrator API skeleton 已成立
- ShellAdapter / Evidence / Auto-Review 的最小闭环已成立
- Operator CLI 与 `make smoke` 已成立
- M0 smoke 可在断网且无任何 LLM API Key 的环境中通过
- `docs/tech-debt-registry.md` 已建立并纳入 Freeze Review
- Freeze review 已完成并给出明确结论

---

# 8. 进入 M1 的准入 Gate

只有满足以下条件，才允许进入 M1：

- `workflowctl run create --goal ... --preset ...` 已稳定可用
- `PresetResolver = manual` 已被强制执行
- timeline 中稳定出现 `run_created` 与 `preset_selected`
- 不存在“无 preset 也能创建 run”的后门
- LangGraph 细节未泄漏到 contracts 层
- `contracts/` 与 `core-domain/` 中不存在直接 `langgraph` import
- `make smoke` 可在 5 分钟内跑通
- `make smoke` 可在断网且无任何 LLM API Key 的环境中跑通
- freeze review 明确给出 `go`

若以上任一项不满足，则继续留在 M0 修复，不启动 M1。

---

# 9. 本次拆分后的文档结构

```text
/
  universal_agentic_workflow_os_local_first_plan_v2_1.md
  universal_agentic_workflow_os_M0_task_breakdown_v2_1.md
  universal_agentic_workflow_os_M0_phase_plan_v2_1.md
  /docs
    tech-debt-registry.md
  /m0_phase_docs
    phase_0_scope_and_governance.md
    phase_1_contracts_and_preset_baseline.md
    phase_2_persistence_and_timeline_foundation.md
    phase_3_orchestrator_and_runtime_boundary.md
    phase_4_execution_evidence_review_loop.md
    phase_5_cli_dx_smoke_and_freeze_review.md
```

---

# 10. 一句话使用建议

本文负责总览和 gate，子文档负责执行细节。

推进 M0 时，建议始终保持一个原则：

**总览文档只回答“现在该进入哪个阶段”，phase 子文档只回答“这个阶段该怎么做”。**
