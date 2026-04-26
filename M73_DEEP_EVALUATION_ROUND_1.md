# M73 深度评估第 1 轮报告

生成日期：2026-04-26

## 评估范围

本轮评估基于当前工作树、M72 自开发 manifest、根目录/归档文档布局、治理文档、测试入口和热点文件体量进行排查。重点检查当前阶段是否已经达到“可以恢复能力层开发”的前置可信状态。

已采集证据：

- `state/m73_iterative_deep_evaluation/evidence/r1_plan_graph.json`
- `state/m73_iterative_deep_evaluation/evidence/r1_policy_preview.json`
- `state/m73_iterative_deep_evaluation/evidence/r1_goal_packet.json`
- `state/m73_iterative_deep_evaluation/evidence/r1_manifest_before.json`

## 总体结论

当前项目主线已经从 M67-M72 的 workflow 可信收口进入 M73 评估/卫生收口阶段，能力层开发可以作为下一阶段目标，但本轮仍发现一个会影响治理可信度的实际问题：历史执行报告的根目录/归档规则与 `self-development-manifest` 的查找逻辑不一致。

因此本轮结论不是“无修改必要”。建议先修复治理 manifest 对归档报告的支持，并把旧执行报告从根目录移入归档；完成后进入第 2 轮复评。

## 发现的问题

### P1：历史执行报告仍滞留根目录，和当前文档定义冲突

现象：

- 当前说明文档已经把“历史评估、长期路线图、旧执行报告”定义为 `docs/archive/evaluations/` 下的归档材料。
- 根目录仍保留 `M67_EXECUTION_REPORT.md` 到 `M71_EXECUTION_REPORT.md`。
- 这些文件暂时不能直接归档，因为 `packages/core_domain/self_development_manifest.py` 只从根目录查找 `{milestone}_EXECUTION_REPORT.md`。

影响：

- 根目录继续膨胀，用户无法一眼分辨“当前入口”和“历史证据”。
- 文档说法与工具行为不一致，治理报告的可信度下降。
- 后续 M73/M74 继续生成报告时，根目录会再次变成历史材料堆场。

建议修复：

- `self-development-manifest` 支持从根目录和 `docs/archive/evaluations/` 两处解析执行报告。
- 当前/latest 报告仍优先根目录；历史报告可被归档后继续被 manifest 识别。
- 将 `M67_EXECUTION_REPORT.md` 至 `M71_EXECUTION_REPORT.md` 移入 `docs/archive/evaluations/`，根目录保留当前 `M72_EXECUTION_REPORT.md` 和本轮 M73 评估报告。
- 增加回归测试覆盖“执行报告在归档目录时 manifest 仍为 GO”。

### P2：`self-development-manifest` 的默认里程碑语义需要更明确

现象：

- `DEFAULT_SELF_DEVELOPMENT_MILESTONES` 固定为 M67-M72。
- CLI help 文案是“default M67-M72 set”，功能上正确，但在进入 M73 后容易被误读为当前活跃开发范围。

影响：

- 这是轻量可读性问题，不影响运行时行为。

建议修复：

- 将 CLI help 调整为 “default M67-M72 closeout set”，明确它是历史 closeout 审计集合，不是自动包含所有未来 milestone。

### P3：热点文件仍然偏大，但本轮不建议立即展开无边界重构

现象：

- `packages/core_domain/repositories.py`、`tests/test_execution_loop.py`、`tests/test_api.py`、`tests/test_cli.py` 等仍是高体量文件。
- `packages/core_domain/services.py` 已低于 M67 目标，但周边 mixin、repository、测试文件仍需要后续结构瘦身。

影响：

- 可维护性和局部修改成本仍偏高。
- 但当前没有证据表明这些热点文件正在造成测试红灯、启动阻塞或安全门禁失效。

建议处理：

- 本轮不做大重构。
- 在下一阶段能力开发前，为每个热点文件建立单独 task card 和 ratchet 目标；拆分必须带兼容测试，避免为“瘦身”引入行为漂移。

## 本轮修复计划

1. 修复 `self-development-manifest` 的执行报告解析逻辑，支持归档路径。
2. 增加 manifest 回归测试，覆盖归档报告路径。
3. 调整 CLI help 文案，避免 M67-M72 默认集合被误解为当前活跃阶段。
4. 归档 M67-M71 执行报告，保留 M72 当前 closeout 报告。
5. 运行 targeted tests、doc links、manifest smoke。

## 下一轮判断标准

完成上述修复后进入第 2 轮复评。如果第 2 轮没有发现新的可证实阻塞项或必须立即修改的问题，则本次长程评估可以停止，并把剩余热点文件瘦身列为非阻塞后续工作。
