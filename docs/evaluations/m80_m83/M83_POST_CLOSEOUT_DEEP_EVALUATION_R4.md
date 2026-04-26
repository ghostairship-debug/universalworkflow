# M83 后深度评估 R4

生成时间：2026-04-27

## 结论

最终 all-provider live probe 发现 1 个 P2 workflow 可靠性问题，已完成修复并通过回归与 live probe 复测。由于本轮含 P2，本轮不计入“连续无 P0-P2 建议”。

## P2 已修复项

| ID | 领域 | 问题 | 修复 | 验证 |
| --- | --- | --- | --- | --- |
| M83-R4-PROBE-TIMEOUT | provider 真实性 / workflow probe | `mmx_music` 是真实音乐生成 provider，最近 live probe 正常耗时约 60-106 秒；all-provider gate 的外层 subprocess watchdog 固定 120 秒，偶发撞线会把真实可用 provider 标成 `probe_timeout`。 | 为 `mmx_music` 增加 provider-specific 外层 watchdog：默认 180 秒；显式 `WORKFLOW_CAPABILITY_PROBE_TIMEOUT_SECONDS` 仍优先。 | `tests/test_capability_probe.py::test_capability_probe_uses_provider_specific_timeout_for_slow_music_probe` 通过；`workflowctl capability probe --provider mmx_music --require-live` 通过；`workflowctl capability probe --provider all --require-live` 通过。 |

## 覆盖面检查

- 架构设计：provider-specific timeout 没有改变能力路由语义，只补强了慢速真实资产生成 provider 的 watchdog。
- 功能实现：MMX music 继续是真实 API 资产生成，不降级、不 fallback。
- 安全边界：显式 env timeout 仍优先，外部 provider 失败仍会返回 blocker，不会伪装成功。
- workflow dogfood：发现 gate 红灯后暂停收口，先修 workflow probe 并补测试，符合 bug-first。
- provider 真实性：all-provider require-live 最终通过，`blocked_count=0`。
- 测试可靠性：新增回归覆盖 timeout policy。
- Cocos/game pipeline：M83 pipeline 依赖 asset factory；音乐生成 timeout 修复降低了后续商业化资产 gate 的误报率。
- 治理文档：R3 停止结论已修正为“被 R4 覆盖”。
- 项目体积与卫生：新增 evidence 仅在 state 下，不进入 git。

## 本轮状态

本轮含 P2 修复；连续无 P0-P2 计数重置为 0/2。
