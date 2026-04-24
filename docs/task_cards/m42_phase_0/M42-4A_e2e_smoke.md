# M42-4A：M42 新集群 E2E Smoke

## 写入范围

- `m42_phase_docs/phase_0_agent_cluster_completion.md`
- `docs/task_cards/m42_phase_0_task_cards.md`
- 如发现阻塞 bug，补最小代码和测试。

## 目标

选择至少一个 M42 新集群跑真实 workflow smoke，验证 launch、child roles、fallback、artifact 和 review gate。

## 结果

- 已选择 `management_cluster` 做真实 smoke。
- 长 timeout smoke：`state/m42_management_cluster_smoke/summary.json`。
- 修复 Windows Codex CLI 进程树 timeout 后，重新跑 tree-timeout smoke：`state/m42_management_cluster_tree_timeout_smoke/summary.json`。
- 收口 run：`run_665006c2016d`。
- 根 run completed；Codex 子 run 在约 8 秒硬超时后被标记 failed，再由 shell fallback 完成。
- 复查无残留 `codex.exe`。

## 验收

- 父 run 进入 completed。
- 子 role 的 adapter/fallback 证据可查看。
- 失败 Codex child 不会被静默 approve。
- timeout 后无残留 native Codex 进程。
