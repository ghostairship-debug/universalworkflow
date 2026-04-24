# M41 Phase 6：受控 Dogfood E2E 记录

日期：2026-04-25

## 目标

用 workflow 自己发起一次 M41 内部开发演练，验证强模型 dogfood、能力层可见性、`architecture_delivery_cluster`、generated profiles、确定性 evidence/review/PR-ready summary，以及人工接管点记录。

## 执行结果

- 数据库：`state/m41_dogfood_e2e_safe_20260425.db`
- 结果 JSON：`state/m41_dogfood_e2e_result.json`
- session：`intent_session_708a7abfb198`
- architecture plan run：`run_ddc43d27c9eb`
- deterministic evidence run：`run_fb56a549b9e2`
- architecture plan run 状态：`prepared`
- evidence run 状态：`completed`
- 选中 cluster：`architecture_delivery_cluster`
- generated profiles：8 个
- evidence artifact：`state/artifacts/run_fb56a549b9e2_feature_delivery_software_delivery.md`

## Cluster 链路

本次 workflow 生成并投影的角色顺序为：

1. `multimodal_evidence`
2. `planner_design`
3. `claude_architect_gate`
4. `phase_designer`
5. `implementer`
6. `quality_gate`
7. `doc_curator`
8. `launch_guard`

## 模型与能力状态

- `planner_design`、`phase_designer`、`implementer`、`quality_gate`、`doc_curator` 均投影为 `gpt-5.5`，`model_selection_source=dogfood_strong_default`。
- `mmx_multimodal` 为 ready，作为多模态主入口。
- `vertex_multimodal` 为 ready，作为 fallback。
- `claude_architect` CLI 可用，但 gate 未启用，因此本次没有消耗 Claude 额度。
- strong dogfood 打开后，doctor 正确显示 `dogfood_strong_model=missing_auth`，因为当前没有 `OPENAI_API_KEY`。

## 暴露的问题

第一次尝试直接 resume `project_delivery` 的 architecture cluster 时，workflow 进入 agent lane 并尝试启动 LangChain/OpenAI `gpt-5.5` agent，但当前环境没有 `OPENAI_API_KEY`，导致执行失败。

这说明 M41 dogfood 的“强模型准确率优先”方向合理，但在真正无人值守前必须满足两个前置条件：

- doctor 必须提前报告 strong model agent 执行认证是否完整。
- cluster member execution 不能把“可投影的角色链路”误认为“已可执行的多 agent runtime”。

## 已做修复

- `workflowctl doctor` 新增 `dogfood_strong_model` 状态；strong dogfood 打开但缺少 `OPENAI_API_KEY` 时报告 `missing_auth`。
- `LangChainAgentAdapter` 初始化 `ChatOpenAI` 失败时，改为抛出带明确原因的 `WorkerAdapterUnavailableError`，不再泄露底层 OpenAI client 错误。

## 人工接管点

- Claude 架构门未启用，本次不调用 Claude，只记录为人工接管点。
- 真实 cluster member execution 仍未完全自动化；本次只完成 cluster 计划、画像生成和确定性 evidence run。
- 主进程负责识别强模型认证缺失并改用 deterministic evidence run 收口。
- 本次没有 commit、push 或创建 PR。

## 验收

- workflow 成功生成 session、plan draft、cluster projection、generated profiles。
- workflow 成功产出 completed evidence run。
- evidence run 产生 result envelope、artifact、auto review 和 PR-ready summary。
- 本次演练暴露的认证前置条件已进入 doctor。
