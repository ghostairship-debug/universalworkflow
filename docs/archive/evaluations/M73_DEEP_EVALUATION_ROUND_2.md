# M73 深度评估第 2 轮报告

生成日期：2026-04-26

## 评估范围

第 2 轮在第 1 轮修复之后执行，重点确认：

- 根目录是否仍有过期历史报告滞留。
- `self-development-manifest` 是否能同时识别根目录当前报告和归档历史报告。
- 活动文档是否继续出现过期表述，例如 zero open debt、Gemini CLI 已接入、gcloud 是 worker adapter、调度权威被描述为分布式共识等。
- 当前治理、文档和 workflow 基础检查是否仍为绿灯。

已采集证据：

- `state/m73_iterative_deep_evaluation/evidence/r2_plan_graph.json`
- `state/m73_iterative_deep_evaluation/evidence/r2_policy_preview.json`
- `state/m73_iterative_deep_evaluation/evidence/r2_goal_packet.json`
- `state/m73_iterative_deep_evaluation/evidence/r2_manifest.json`
- `state/m73_iterative_deep_evaluation/evidence/r2_doc_links.json`
- `state/m73_iterative_deep_evaluation/evidence/r2_doctor_strict.json`
- `state/m73_iterative_deep_evaluation/evidence/r2_test_matrix_unit.json`

## 总体结论

本轮未发现需要继续修改的当前阶段阻塞项，也没有发现必须在本次评估循环内处理的新增问题。第 1 轮提出的治理/归档不一致已经修复：

- M67-M71 执行报告已归档到 `docs/archive/evaluations/`。
- 根目录仅保留当前 closeout 入口 `M72_EXECUTION_REPORT.md` 以及本轮 M73 评估报告。
- `self-development-manifest` 已能识别归档执行报告，M67-M72 manifest 仍为 `GO`。
- 活动说明文档没有继续声明 zero open debt、Gemini CLI 已接入、gcloud 是 worker adapter 或分布式 scheduler authority。

因此，本次“多轮深度评估 → 修复 → 复评”循环达到停止条件：当前无进一步修改必要。

## 验证结果

- `python -m pytest tests/test_governance.py tests/test_self_development_manifest.py -q --basetemp state/.pytest-tmp-workflow/m73-r2-governance`：16 passed。
- `python -m infra.scripts.check_doc_links`：passed，检查 7 份活动文档，0 issues。
- `workflowctl governance self-development-manifest`：`go_no_go = GO`，`blocking_issue_count = 0`。
- `workflowctl doctor --strict`：`status = ok`，workspace root 显式，optional CLI 中 Codex/OpenCode/Claude/MMX/gcloud 均可发现。
- `workflowctl test matrix --suite unit`：57 passed。

## 复核发现

### 已关闭：历史报告归档与 manifest 查找逻辑不一致

第 1 轮发现的 P1 问题已经关闭。manifest 现在对每个 milestone 暴露 `lookup_paths`，当前报告优先根目录，历史报告可在归档目录被识别。

### 已关闭：M67-M72 默认集合语义不够清楚

CLI help 已明确默认集合是 “M67-M72 closeout set”，不再暗示它是所有未来 milestone 的自动范围。

### 无需本轮修改：热点文件仍偏大

仓库仍存在大文件和大测试文件，但它们当前没有造成治理红灯、文档红灯、doctor 红灯或 manifest 红灯。继续拆分可以作为后续能力开发过程中的局部工程任务处理，不构成本轮评估循环的继续条件。

## 停止判断

本轮报告认为当前阶段无修改必要。后续如果进入 M73/M74 能力层开发，建议继续遵守既有规则：

- 每个 phase 至少多个 task card，单卡必须写 `single_card_exception`。
- 简单 artifact-only / disjoint write_set 任务优先交给 workflow 编排和并发执行。
- 一旦 workflow 自身暴露 bug，先修 workflow bug，再恢复业务开发。
- 能力 readiness 只以 live probe 和 runtime ledger 为准。
