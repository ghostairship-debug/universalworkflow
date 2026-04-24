# M41 Phase 13：Codex CLI 强模型 Dogfood E2E

日期：2026-04-25

## 目标

复测 Phase 6 暴露的问题：在没有 `OPENAI_API_KEY` 的个人本地环境中，`architecture_delivery_cluster` 不应再卡死在 LangChain agent lane。Phase 13 使用升级后的 Codex CLI `0.125.0` 和 `gpt-5.5 xhigh` 路径，验证 workflow 能否产出真实 planner/reviewer/doc artifact、handoff 信息、模型投影和可审计证据。

## 范围

- 使用 `WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED=1`。
- 使用 `WORKFLOW_DOGFOOD_EXECUTION_BACKEND=codex_cli`。
- 使用 `architecture_delivery_cluster`。
- 本阶段允许真实 Codex CLI artifact-only 调用。
- 本阶段不自动 commit、push 或创建 GitHub PR。
- 本阶段不扩大到自适应低成本模型路由。

## 验收点

- `workflowctl doctor` 或等价 CLI payload 显示 dogfood 后端为 `codex_cli` 且 Codex CLI 可用。
- `planner_design`、`phase_designer`、`quality_gate`、`doc_curator` 等核心角色解析为 `codex` + `gpt-5.5 xhigh`。
- 至少一个真实 Codex CLI artifact-only run 成功落盘。
- 记录仍需人工接管或后续实现的 cluster-member runtime 缺口。
- 定点测试、文档链接检查和 offline validation 通过。

## 运行记录

### 环境

- `WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED=1`
- `WORKFLOW_DOGFOOD_EXECUTION_BACKEND=codex_cli`
- `WORKFLOW_DOGFOOD_MODEL=gpt-5.5`
- `WORKFLOW_DOGFOOD_REASONING_EFFORT=xhigh`
- `WORKFLOW_CLAUDE_ARCHITECT_ENABLED=0`
- 最终验证轮额外使用 `WORKFLOW_CODEX_TIMEOUT_SECONDS=75`，用于验证长耗时 Codex 节点能被边界化并 fallback。

### 真实 E2E 结果

- 输出目录：`state/m41_phase13_dogfood_e2e_rerun4/`
- 数据库：`state/m41_phase13_dogfood_e2e_rerun4.db`
- session：`intent_session_557cecbe8fc4`
- parent run：`run_c0cad7dc9f58`
- parent status：`completed`
- parent return code：`0`
- 子角色数量：`7`

子角色实际结果：

| 角色 | 最终 run | 最终 adapter | 模型 | 状态 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `multimodal_evidence` | `run_11f9db3512ba` | `shell` | - | `completed` | 本机 MMX 未形成可用真实输出，原 MMX 失败后 fallback |
| `planner_design` | `run_d5c85aca7d07` | `codex` | `gpt-5.5 / xhigh` | `completed` | 真实 Codex CLI artifact-only 成功 |
| `claude_architect_gate` | `run_9068b4972724` | `shell` | - | `completed` | Claude gate disabled，按预期 fallback |
| `phase_designer` | `run_69ffa1512dd5` | `codex` | `gpt-5.5 / xhigh` | `completed` | 真实 Codex CLI artifact-only 成功 |
| `implementer` | `run_8443982f0cfb` | `shell` | - | `completed` | Codex bounded timeout 后 fallback；本阶段仍不做 repo mutation |
| `quality_gate` | `run_5cfada12e1d7` | `shell` | - | `completed` | Codex bounded timeout 后 fallback |
| `doc_curator` | `run_9d71520ffcd7` | `shell` | - | `completed` | Codex bounded timeout 后 fallback |

关键 artifact：

- `state/artifacts/run_d5c85aca7d07_advisory_delivery_software_delivery.md`
- `state/artifacts/run_69ffa1512dd5_optional_delivery_software_delivery.md`
- `state/artifacts/run_8443982f0cfb_feature_delivery_software_delivery.md`
- `state/artifacts/run_c0cad7dc9f58_project_delivery.md`

### 本阶段修复

1. 修复 `launch_goal()` 只在 preview 保留 `architecture_delivery_cluster`、compile 后退回 `dev_cluster` 的问题。
2. 修复 worker adapter 抛异常后 parent run 卡在 `running`、claim/lease 不释放的问题；现在会转成失败 evidence。
3. 修复 cluster member 继承 parent orchestration plan 后递归展开集群的问题。
4. 修复 orchestration child `return_code != 0` 却被自动 approve 成 `completed` 的语义错误。
5. 修复 human-required child 非零失败后 fallback 成功但原 child 仍停留 `awaiting_review` 的幽灵待审问题。
6. 新增 `WORKFLOW_CODEX_TIMEOUT_SECONDS`，默认不改变现有 `180s`，但个人 dogfood 可临时缩短强模型节点等待时间。

### 仍需后续处理

- MMX/Claude 在本机真实能力层仍处于 degraded/fallback 状态；Phase 13 只证明 workflow 可恢复，不代表多模态和 Claude gate 已完成真实生产接入。
- Codex CLI 在 review/doc 类 artifact-only 角色上仍可能长时间不收敛；M42+ 应考虑 role prompt 收缩、token/timeout 分层或 reviewer/doc curator 的更轻量专用路径。
- 本阶段没有自动 commit、push 或创建 PR。
