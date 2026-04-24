# 当前开发工作流

本文档是后续开发的最高优先级操作说明。当前项目是个人自用的本地 operator runtime，所有计划、文档和验证都应服务“未来的我能不能稳定继续使用”，而不是服务外部用户、公开 SaaS、开源 onboarding 或第三方生态。

## 1. 活跃真相源

判断当前状态时，只看以下文件：

1. [README.md](../README.md)
2. [docs/current_development_workflow.md](current_development_workflow.md)
3. [docs/tech-debt-registry.md](tech-debt-registry.md)
4. [docs/milestone_history.md](milestone_history.md)
5. [PROJECT_DEEP_EVALUATION_M37.md](../PROJECT_DEEP_EVALUATION_M37.md)
6. [docs/governance/tech_debt_registry.json](governance/tech_debt_registry.json)

旧 phase docs、task cards、freeze reviews、archive、M2M 交接计划和重复根目录计划不再是活跃真相源。需要历史细节时从 git 历史查看，不再恢复到工作树。

## 2. 当前仓库状态

- 已完成：`M8-M30`、`M31 Phase 0`、`M32 Phase 0`、`M33 Phase 0`、`M34 Phase 0`、`M35`、`M36`、`M37`。
- 当前没有打开 post-`M37` bounded phase。
- 当前主线可称为 `v1 core complete` personal-runtime baseline。
- Web UI 已有可用的 natural-language workbench v1。
- generated profiles 已作为受治理的 generated-profile family 落地。
- bounded automation watchdog 已落地，高风险动作仍必须 review-gated。
- scheduler-authority 默认 local-only，只有设置 `UAWO_ENABLE_SCHEDULER_AUTHORITY_CLUSTER=1` 时才走 quorum-style 路径。
- `TD-STRUCT-001`、`TD-STRUCT-003`、`TD-STRUCT-005`、`TD-STRUCT-006` 仍是后续主要结构债。

## 3. 下一步

下一步只应打开 `M38 Phase 0`，并且必须先写 phase doc 和 task cards。建议主题：

> M38：个人自用硬化、`OrchestratorService` 收缩、运行证据增强。

M38 Phase 0 应先做：

1. 固化个人自用边界，避免旧的外部产品化叙事回流。
2. 写一份短的个人日常操作剧本。
3. 验证当前 resume、reconcile、cancel、review、state recovery 路径。
4. 明确 `OrchestratorService` 收缩的第一批切口。
5. 确认运行证据、capability health、成本/失败原因展示的最小目标。

## 4. 明确不做

除非拥有者明确改目标，否则后续阶段不做：

- 外部用户 onboarding。
- 公开 SaaS / 多租户 / 企业权限。
- 第三方插件市场。
- 社区贡献路径。
- 为陌生用户解释而牺牲个人自用效率的文档工程。
- 无运行证据支撑的新 capability 广覆盖。

## 5. 任务卡协议

每个新 active phase 仍按 task-card 协议推进：

1. 先写当前 phase doc。
2. 再写当前 phase task-card index。
3. 再写 detailed task cards。
4. 执行时同步记录实际结果。
5. 完成后用验证结果和 living-doc 更新收尾。

规则：

- 只为当前 active phase 生成任务卡。
- 不提前生成未来 phase 的任务卡包。
- 已关闭阶段的任务卡不要长期保留在工作树；结论吸收到本文件、历史摘要或技术债登记表后即可清理。
- 每个 mutating workflow run 必须有写集、测试和审查边界。

## 6. 文档治理规则

工作树应保持小而清楚。

- 根目录只保留真正需要直接看到的入口文档。
- 历史里程碑只保留中文摘要，不保留分散 phase/task-card/review 材料。
- 技术债以 `docs/governance/tech_debt_registry.json` 为结构化真相，`docs/tech-debt-registry.md` 只做人类可读摘要。
- 文档内容优先中文；如代码、命令、环境变量或公共类型必须保留英文原文，则只保留必要英文。
- 旧计划不得与当前工作流并列成为“第二真相源”。

## 7. 验证规则

文档或代码变更后至少运行：

```powershell
python -m infra.scripts.check_doc_links
```

涉及运行路径、验证脚本或 active truth set 时再运行：

```powershell
python -m infra.scripts.offline_validation --skip-offline-probe
pytest -q
```

M38 打开前，任何清理都不能删除真实 pytest 测试、迁移、seed、运行时配置或治理 JSON。

## 8. 一句话指令

把已接受的 `M37` 当作最新完成基线；保持 post-`M37` phase 关闭；下一次只通过 `M38 Phase 0` 文档和任务卡打开个人自用硬化工作。
