# M38 修复与开发计划

日期：2026-04-24  
状态：M38 已完成，本文保留为完成记录  
产品前提：个人自用 / 本地 operator runtime

说明：本文记录 M38 打开时的判断和最终完成结果。阶段划分章节保留历史执行计划，不再表示当前仍有未完成任务。

## 1. 参考输入

本计划综合以下信息：

- [GPTPRO_EVALUATION.md](GPTPRO_EVALUATION.md)
- [PROJECT_DEEP_EVALUATION_M37.md](PROJECT_DEEP_EVALUATION_M37.md)
- [README.md](README.md)
- [docs/current_development_workflow.md](docs/current_development_workflow.md)
- [docs/tech-debt-registry.md](docs/tech-debt-registry.md)
- [docs/milestone_history.md](docs/milestone_history.md)

GPTPRO 的外部评估有一处需要校正：它基于压缩包和独立环境判断“测试没有全绿”，但当前工作树在 2026-04-24 已验证 `pytest -q` 为 `299 passed`，`offline_validation` 和文档链接检查也通过。因此，本计划不把“当前主线红灯”当作事实，而是把它转化为“测试可复现性、可选 adapter 环境漂移、慢测试分层”风险。

GPTPRO 评估中应采纳的核心判断是：

- `repo_mutation.run_test_commands()` 当前安全边界偏弱，属于 P0。
- MCP tool projection 缺少 canonical identity，后续会遇到工具名冲突和语义漂移。
- optional adapter 不应让普通测试和普通工作流依赖本机是否安装 `opencode` / `codex`。
- 下一阶段要收缩，不要继续横向扩展 Universal OS。
- 最有价值的闭环是本地任务卡 / issue → bounded patch → safe tests → review → PR-ready summary。

## 2. 总体决策

M38 的主题确定为：

> 个人自用硬化、安全执行边界、运行证据、`OrchestratorService` 收缩。

M38 不做：

- 公开产品化。
- 外部用户 onboarding。
- 插件市场。
- 企业权限。
- 新的大型分布式调度能力。
- 大规模包结构重构。
- 默认 GitHub 写入或自动创建 PR。

GitHub 相关能力只作为后续可选方向。M38 最多做到本地 `PR-ready summary`，真正 push / create PR 必须人工确认，并且应在安全测试 runner 和 mutation 闭环稳定后再打开。

## 3. 当前基线

当前已经成立：

- `pytest -q` 通过，`299 passed`。
- `python -m infra.scripts.offline_validation --skip-offline-probe` 通过。
- `python -m infra.scripts.check_doc_links` 通过。
- 测试已分层：日常 `pytest -q` 跑快速核心回归，CLI/API/Web 改动跑定点 slow 用例，完整端到端 `pytest -q --run-slow` 只在每个 M 收口时跑一次；覆盖率使用显式 coverage 命令。
- Phase 2 已完成：tool projection 有 canonical identity，`workflowctl doctor` 提供只读本地诊断。
- Phase 3 已完成：`OrchestratorService` 第一轮收缩，`services.py` 从 3833 行减少到 3520 行。
- Phase 4 已完成：本地 task card 到 bounded patch、safe tests、review、PR-ready summary 的个人闭环。
- 活跃文档已收束为中文最小真相集。
- scheduler-authority 默认 local-only，flag on 才启用 quorum-style 路径。
- generated profiles 和 watchdog automation 已存在，但高风险动作仍需 review gate。

M38 打开时最重要的问题：

- `packages/core_domain/repo_mutation.py` 中 `run_test_commands()` 使用 `shell=True`，继承完整 `os.environ`，且没有 timeout / 输出上限 / 风险分级。
- `ToolProjectionEntry` 当前只有 `tool_name`，没有稳定表达 `canonical_tool_id / raw_tool_name / display_name` 的三层身份。
- adapter 可用性、依赖版本、可选工具缺失缺少统一 `doctor` 诊断。
- `OrchestratorService` 仍是巨型 facade，后续新功能容易继续堆进去。
- Web workbench 和 operator packet 对“为什么这样执行、是否安全继续、失败后怎么办”的解释还不够集中。

## 4. M38 阶段划分

### M38 Phase 0：打开前确认与任务卡

目标：

- 正式写 `M38 Phase 0` phase doc。
- 写当前 phase task-card index 和 detailed task cards。
- 把本计划转化为可执行任务，不再生成长期并行计划。
- 确认不打开公开产品化或新生态扩展。

验收：

- phase doc 和 task cards 只覆盖当前 phase。
- `docs/current_development_workflow.md` 仍是最高优先级操作说明。
- `python -m infra.scripts.check_doc_links` 通过。

### M38 Phase 1：安全 test runner

这是第一优先级。

目标：

- 替换 `run_test_commands()` 的默认 `shell=True`。
- 引入兼容旧 `list[str]` 命令的解析层，但内部执行必须走 argv。
- 默认 timeout。
- stdout / stderr size cap。
- scoped env，默认不传模型 key 和 worker secret。
- secret redaction。
- 高风险命令检测和 review-required 标记。
- 将 test command attempt 写入更明确的结果结构。

建议实现边界：

- 新增 `TestCommandSpec` 或等价内部模型。
- 旧的 string command 可以先通过 `shlex.split(..., posix=False)` 或平台安全解析转换，无法安全解析则拒绝。
- 默认禁止管道、重定向、命令替换、`curl`、`wget`、`ssh`、`scp`、`nc`、删除类危险命令，除非显式 review-gated。
- 不在本阶段重做整个 repo mutation 系统。

验收：

- 新增单元测试覆盖 timeout、env scope、危险命令拦截、输出截断、失败短路。
- 原有 repo mutation 测试继续通过。
- `pytest -q` 通过。
- `offline_validation` 通过。

### M38 Phase 2：MCP / capability identity 与 adapter doctor

目标：

- 为 tool projection 增加稳定 canonical identity。
- 区分 `canonical_tool_id`、`raw_tool_name`、`display_name`。
- 保持现有 `tool_name` 向后兼容。
- 防止 built-in tool 和 MCP tool 同名时语义冲突。
- 增加 `workflowctl doctor`，显示本地依赖、可选 adapter、MCP、模型 key、pytest/dev 版本和 state 路径状态。

建议实现边界：

- 对 `ToolProjectionEntry` 做 additive 字段，不重命名公共类型。
- canonical 示例：`mcp:local_workspace_readonly:mcp_list_workspace_files`。
- built-in 示例：`builtin:standard_agent:list_workspace_files`。
- `doctor` 默认只读、redacted，不泄露 secret 值。
- optional adapter 缺失时输出 degraded，不让普通路径崩溃。

验收：

- API / CLI / offline validation 断言 canonical identity。
- 无 `opencode` / `codex` 时普通测试仍可稳定通过。
- `workflowctl doctor` 有 CLI 测试。
- `pytest -q` 通过。

### M38 Phase 3：`OrchestratorService` 第一轮收缩

目标：

- 不改公共 API。
- 不改核心行为。
- 禁止以大重构名义重排整个 `core_domain`。
- 先抽最直接、最有收益的 coordinator / projector / resolver。

建议第一批切口：

- repo mutation test/fix loop coordinator。
- capability projection builder/use-case。
- generated profile / watchdog surface projection glue。
- execution resolution trace helper。

验收：

- `services.py` 行数实质下降，目标至少净减少 300 行。
- 新模块有对应单元测试或沿用既有回归测试覆盖。
- `pytest -q`、offline validation、doc links 全绿。
- README 和 workflow guide 不新增并行计划。

### M38 Phase 4：个人自用闭环与运行证据

目标：

- 打穿本地任务卡 / issue-like 输入 → bounded patch → safe tests → review → PR-ready summary。
- 强化 operator packet / Web workbench 中的执行解释。
- 展示 adapter、capability、policy、test evidence、失败原因和下一步动作。
- 增加个人日常操作剧本。

建议实现边界：

- 先做本地 `PR-ready summary`，不自动 push，不自动 create PR。
- 先支持本地 markdown / yaml task card，不急着接 GitHub API。
- 所有 repo mutation 必须保留 write-set。

验收：

- 至少 5 个本地任务卡样例。
- 成功路径和失败路径都有 evidence。
- review-required 路径能清楚提示下一步。
- Web / CLI / API 至少两个入口可查看 summary。

## 5. 优先级表

| 优先级 | 工作 | 原因 | 进入条件 |
| --- | --- | --- | --- |
| P0 | 安全 test runner | 当前 `shell=True` 和完整 env 继承是最硬的安全风险 | 立即进入 M38 Phase 1 |
| P0 | M38 task cards | 当前仍是 pre-open，不能直接开写代码 | Phase 0 |
| P1 | MCP canonical identity | 防止工具名漂移和未来冲突 | Phase 2 |
| P1 | `workflowctl doctor` | 解决环境漂移、可选 adapter 和依赖诊断 | Phase 2 |
| P1 | `OrchestratorService` 收缩 | 长期维护最大结构债 | Phase 3 |
| P2 | 本地 PR-ready summary 闭环 | 形成个人自用的尖锐价值闭环 | Phase 4 |
| P3 | GitHub issue / draft PR 集成 | 有价值但必须在安全 runner 后面 | M39 或 M38 后段再决定 |
| P3 | evals 目录和 golden tasks | 应做，但不抢 P0 安全和结构债 | M39 |

## 6. 风险与取舍

当前不用追求：

- 让陌生用户顺利安装。
- 把 GitHub 集成做成自动化发布流水线。
- 把所有 adapter 都做成稳定生产级。
- 把 remote worker / scheduler authority 继续做大。
- 一次性拆分 `packages/core_domain`。

当前必须坚持：

- 本地优先。
- 默认安全。
- 高风险动作 review-gated。
- 写集受控。
- 验证可复现。
- 文档真相源少而清楚。

## 7. M38 启动门槛

正式打开 `M38 Phase 0` 前必须满足：

```powershell
python -m infra.scripts.check_doc_links
python -m infra.scripts.offline_validation --skip-offline-probe
pytest -q
```

当前基线已经满足，但打开 phase 时仍需重新记录当时结果。

## 8. 完成结论

M38 已完成，不再保留详细 phase/task cards。后续开发应先打开新的 M 级计划，再创建当前 active phase 的 phase doc 和任务卡。
