# M82 执行报告：Workflow Self-Development Loop

## 结论

M82 已完成并进入 GO 状态。新增 `workflowctl governance active-truth-check`，用于检查活跃说明文档、里程碑历史和技术债登记是否与当前 evidence / commit 状态矛盾；同时补齐了本轮 workflow 自开发证据链。

## 实现内容

- 新增 `packages/core_domain/active_truth.py`，检查 stale M79 计划/当前态表达、M78 baseline 滞后、技术债重复登记和 open item 中误标 repaid。
- CLI 新增 `workflowctl governance active-truth-check --strict --output-path ...`。
- 新增 `tests/test_active_truth_check.py`，覆盖 stale truth、当前文档 GO、技术债重复/误标路径。
- 修复 DeepSeek direct coding proposal 的路由模型名兼容问题：`deepseek/deepseek-v4-flash` 在 direct DeepSeek API 调用前会归一化为 `deepseek-v4-flash`。
- 修复 self-development manifest 的 evidence metadata 读取问题：PowerShell `Tee-Object` 产生的 UTF-16 JSON evidence 现在可被 manifest 正常读取。

## Workflow Dogfood Evidence

证据目录：`state/m82_self_development/`

- Task cards：`state/m82_self_development/task_cards/`，包含 implementation、verification、workflow dogfood 三张卡。
- Route previews：`M82-plan-graph.json`、`M82-policy-preview.json`、`M82-goal-packet.json`。
- Simple lane：OpenCode + MiniMax artifact-only run `run_8b90b200d3e4` 真实执行，但自动 review 为 `fail`，已保留为 evidence，不伪装通过。
- Medium lane：DeepSeek proposal 首次因 provider-style 模型名被 DeepSeek API 拒绝；M82 按 bug-first 修复模型名归一化后，重跑成功并保存 proposal evidence。
- Complex lane：Codex artifact-only run `run_9bd0c010da2f` 通过，operator packet 已保存。
- Concurrency：`run batch-resume run_04c9032536ff run_30ad14a0ef57 --max-workers 2` 完成，execution_mode 为 `parallel`，无 write_set conflict。
- Self-development manifest：`state/m82_self_development/evidence/M82-self-development-manifest.json` 为 GO，task card、evidence、operator packet 链路完整。

## 验证

- `python -m pytest tests/test_active_truth_check.py tests/test_governance.py -q`
- `python -m pytest tests/test_m77_provider_access.py::test_generate_coding_proposal_normalizes_router_style_deepseek_model tests/test_m77_provider_access.py::test_generate_coding_proposal_uses_direct_api_without_mutation -q`
- `python -m pytest tests/test_self_development_manifest.py -q`
- `workflowctl governance active-truth-check --strict --output-path state/m82_self_development/evidence/M82-active-truth-check.json`

最终 closeout 仍需在 M82 commit 前运行 doc links、doctor strict、test matrix unit/core/integration 和 full pytest。
