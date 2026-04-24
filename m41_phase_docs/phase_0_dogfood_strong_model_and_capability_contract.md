# M41 Phase 0：强模型 Dogfood 与能力层合同冻结

## 目标

M41 开始“用 workflow 开发 workflow”，但先把稳定性和准确率放在成本之前。Phase 0 只冻结合同和协作边界，并落地最小可见性代码，不直接把 workflow 放到无人值守自开发状态。

## 冻结规则

- 主进程仍是最终技术负责人，负责核心 contracts、execution resolution、cluster orchestration、confirmation gate、冲突处理和最终验收。
- Dogfood 核心角色统一使用 `gpt-5.5 / xhigh`，由 `WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED=1` 打开。
- 低成本模型暂不参与 planner、researcher、coder、reviewer、test sentinel、doc curator 等核心角色。
- Claude Code 只作为一次性架构门，固定在 `research -> planner_design -> claude_architect_gate -> planner_phase_breakdown` 中间，默认 read-only / artifact-only。
- MMX 是默认多模态入口，Vertex 是复杂多模态或长上下文 fallback；M41 先支持路径/引用输入生成 evidence artifact，不做完整上传 UI。
- 分布式 `scheduler_authority` 继续默认关闭；M41 启用的是角色集群，不是多节点控制面。

## 新增接口

- `WORKFLOW_DOGFOOD_STRONG_MODEL_ENABLED`
- `WORKFLOW_DOGFOOD_MODEL`
- `WORKFLOW_DOGFOOD_REASONING_EFFORT`
- `WORKFLOW_CLAUDE_CLI`
- `WORKFLOW_CLAUDE_ARCHITECT_ENABLED`
- `WORKFLOW_CLAUDE_ARCHITECT_MAX_CALLS_PER_SESSION`
- `WORKFLOW_MMX_CLI`
- `WORKFLOW_VERTEX_CLI`
- `WORKFLOW_MULTIMODAL_PRIMARY`
- `WORKFLOW_MULTIMODAL_FALLBACK`

## 投影字段

- `model_selection_source`
- `model_selection_reason`
- `dogfood_strong_model_enabled`
- `claude_architect_call_count`
- `multimodal_evidence_refs`

## Phase 0 验收

- `workflowctl doctor` 能显示 `codex/opencode/claude/mmx/gcloud`，且不泄露 secret。
- capability routes 能看到 `claude_architect`、`mmx_multimodal`、`vertex_multimodal`。
- `architecture_delivery_cluster` 能被 M41 / dogfood / 架构 / 多模态目标命中。
- 强模型开关打开时，核心 agent 的 resolved execution 投影为 `gpt-5.5 / xhigh`，并说明选择来源。
- Claude gate 有一次性调用保护；Vertex 在未配置命令模板时明确 degraded，而不是假装可用。
