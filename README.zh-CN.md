# Universal Agentic Workflow OS 中文说明

这份文档是当前仓库的中文总览入口，面向中文读者说明：

- 项目现在完成到了什么程度
- Web UI / TUI / 自然语言入口分别做到哪里
- agent 集群与产品化当前处于什么状态
- post-`M34` 之后的路线应该如何理解

如果中文说明与英文最小真相集冲突，请以下列文档为准：

1. [README.md](README.md)
2. [docs/current_development_workflow.md](docs/current_development_workflow.md)
3. [docs/reviews/m34-facade-reduction-and-authority-interior-cleanup-freeze-review.md](docs/reviews/m34-facade-reduction-and-authority-interior-cleanup-freeze-review.md)
4. [docs/tech-debt-registry.md](docs/tech-debt-registry.md)
5. [POST_M34_MULTIPHASE_ROADMAP.md](POST_M34_MULTIPHASE_ROADMAP.md)

## 1. 当前仓库位置

截至当前主线，仓库已经完成：

- `M8` 到 `M30`
- accepted `M31 Phase 0`
- accepted `M32 Phase 0`
- accepted `M33 Phase 0`
- accepted `M34 Phase 0`

这意味着当前主线已经具备：

- 本地优先的 CLI / API / Web operator console / TUI
- interaction / profile / cluster foundation
- `DevCluster` 与 `ResearchCluster` 的基础模板
- 共享 orchestration plan builder 与 `project_delivery` / `guarded_project_delivery` 主线
- scheduler-authority 的 bounded honesty cleanup
- 最小 `/ui/workbench` preview

当前状态的关键结论：

- 主线仍可称为 `v1 core complete`
- 当前没有任何 post-`M34` bounded phase 被正式打开
- `TD-STRUCT-001`、`TD-STRUCT-003` 仍是部分偿还
- `TD-STRUCT-005`、`TD-STRUCT-006` 仍然 deferred

## 2. Web UI、TUI 与自然语言入口

### Web UI

当前 Web UI 的定位仍然是 **operator surface**，而不是完整聊天式工作台。

它已经可以：

- 浏览 runs、reviews、governance、config
- 执行 `resume / approve / reject / reconcile / cancel / batch-resume`
- 查看 packetized operator state

但它还不是：

- 聊天式自然语言 workbench
- 流式对话界面
- 运行中自由 replanning 的产品前端

### TUI

当前 TUI 是 **read-mostly terminal dashboard**，适合：

- 看 recent runs
- 看 focus detail
- 看 runtime gateway 状态
- 看 timeline tail

它不是完整 operator shell，也不是自然语言聊天终端。

### 自然语言入口

自然语言目标入口已经存在，但主要落在 **CLI / API / minimum workbench preview**，而不是完整前端工作台。

当前后端已经支持：

- `run suggest-presets`
- `run plan-graph`
- `run policy-preview`
- `run goal-packet`
- `run launch`
- `run operator-packet`

也就是说：

- 后端已经能从自然语言 goal 推导计划与 launch
- 但用户侧前端产品形态还没有完成

## 3. Agent 集群完成到什么程度

当前 agent 集群不是“没做”，而是已经完成了 **foundation + 第一条 shipped cluster 主线**。

已经完成的部分：

- profile / cluster / packet family 已进入正式对象层
- `DevCluster` 与 `ResearchCluster` 已有默认模板
- cluster-aware goal/operator/replay packet 已存在
- `project_delivery` / `guarded_project_delivery` 已通过共享 orchestration 路径接入 `DevCluster` 主线

尚未完成的部分：

- 还不是任意目标自动生成任意 agent 集群的成熟产品
- `ResearchCluster` 还没有达到 `DevCluster` 同等成熟度
- 角色级 adapter / model / variant / policy 配置还没有产品化
- `DesignCluster` 与多模态视觉验证仍未进入 accepted 主线

## 4. 为什么要重构 post-M34 路线

从 `M21` 到 `M34`，仓库实际上长期采用了“一次 milestone 只做一个 bounded `Phase 0`”的推进方式。

这种方式的优点是：

- 风险低
- freeze / closeout 清楚
- bug-first 容易执行

但它也带来了明显漂移：

- `M` 继续增长，但常常只对应一个很窄的 bounded slice
- `Phase` 不再真正表达同一 milestone 内的多阶段推进
- 更早的产品化目标被反复后推

因此，post-`M34` 的路线需要恢复成真正有意义的 **多 phase milestone**，而不是继续默认“一路只有 `Phase 0`”。

## 5. 原有目标还需要多少个 M

新的重构路线写在根目录：

- [POST_M34_MULTIPHASE_ROADMAP.md](POST_M34_MULTIPHASE_ROADMAP.md)

当前最诚实的判断是：

- 如果目标是完成较早设想中的平台产品化目标，至少还需要 `M35-M39`
- 如果目标还包括更高质量的 `DesignCluster` 与多模态视觉验证，通常还需要 `M40`

也就是说：

- 平台产品化目标：还需要 5 个 M
- 更高质量的设计 / 游戏开发目标：大概率还需要 6 个 M

## 6. 现在离 M35 还差什么

`M35` 还没有正式打开，当前只能把 post-`M34` 路线视为 **reference-only**。

在打开 `M35` 之前，仓库还需要先清掉一个 bug-first 前置门槛：

- 当前 governance tech-debt report 相关还有 2 条 expectation regression 需要先修

这一步属于“开相前清障”，不是 `M35 Phase 0` 本身。

## 7. 一句话总结

当前仓库已经完成了 `M34` 之前的核心 foundation、收缩和诚实化工作，但真正的产品化主线还没有开始。post-`M34` 的正确理解不是“马上进入 M35/M36 并自动完成前端和配置”，而是要先用新的多 phase milestone 结构，逐步完成 `M35-M39` 的平台产品化，并在需要时继续推进到 `M40` 的设计与视觉验证能力。
