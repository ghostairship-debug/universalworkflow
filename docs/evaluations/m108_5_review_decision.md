# M108.5 复盘决策报告

## 结论

M109 暂不自动开始。

M105-M108 已经把 Cocos 样机生产线推进到可检查状态，但商业化可玩目标还没有被真实玩家视角证据证明。当前判断是：技术准入基本具备，商业目标可达性还没回答清楚。

因此本轮进入 M108.5 复盘决策点，而不是直接进入 M109。

## 本轮采纳的外部意见

- M105-M108 连续押 Cocos 已经用完当前预算；继续做 M109+ 前必须先复盘。
- 三层 gate 已落地，但玩家视角 gate 不能只看检查项存在，必须看每项是否真的 pass。
- self-development manifest 必须能读到 M105-M108 的真实 evidence，否则机器闸口会误判 NO-GO。
- 过期的 ratchet / shim 例外必须处理，不能把已经过期的治理例外带进下一轮。

## 修复项

1. 自开发证据识别
   - manifest 现在会识别 `state/m105_*` 到 `state/m108_*` 目录下的扁平 evidence 文件。
   - manifest 现在会统计扁平 `task_cards.md` 里的实际卡片标题，不再把 4 张卡误算成 1 个文件。
   - 如果没有单独的 execution report，但存在 `closeout_summary.json`，会把它作为 closeout 类 execution report。
   - 已为 M105-M108 的本地 state 补充复盘重建的 `operator_packet.json`，并明确标注不是新执行。

2. Cocos inspector
   - 玩家视角检查项不再只看“是否存在”。
   - 每项必须 `status=pass`，并带有 `method`、`evidence_path`、hash 和 `validator_version`。
   - 只要玩家视角检查 fail，`go_no_go` 就保持 `NO-GO`。

3. ratchet 例外
   - 已过期的 `remove_after_milestone=M86/M90` 例外不再保留原状态。
   - 本轮只对仍需冻结观察的 Cocos/asset 大文件例外延到 `M110`，并写明 M108.5 review 理由。

4. Task card 形态
   - task card 权威源改为数据库 `task_cards` 表。
   - Markdown 只作为自动导出的人工快照，不再作为机器真相。
   - 新 task card 必须包含 goal、write_set、read_set、test commands、acceptance、evidence requirements、blocking conditions、risk level、model guidance 和 expected artifacts。

## 投入产出复盘

M105-M108 的直接收益：

- Cocos command/config truth 已落地。
- project inspector v2 已落地。
- 本地稳定资产包已落地。
- Prefab/Panel/交互契约已落地。
- 玩家视角 gate 已落地并在本轮加严。
- graph evidence bridge 已落地。
- 小目标样机 closeout 已落地。

仍未达成的目标：

- 没有真实 build/playtest 玩家证据证明商业化可玩。
- UI、音频、关卡流程、皮肤/画廊、移动端体验仍没有达到可宣称成品的证据。
- 当前 closeout 只能证明样机闭环，不证明商业化成品闭环。

## 商业化 gap 初步归因

当前 gap 不是单纯“再多做几个 milestone”就一定能解决。

- 工程能力：已有工程检查、资产绑定、交互契约和 graph evidence，但还缺真实构建试玩证据和更完整的修复闭环。
- 模型能力：商业级 UI、美术风格、音频节奏和玩法润色还没有被现有编码循环稳定证明。
- 资产能力：本地稳定资产能保证样机不断，但不能替代真实美术、音乐、配音和产品级素材。
- 验收标准：`commercial_playable_go` 必须继续保持严格；不能把样机标准降低成商业成品标准。

## 决策

当前决策：`M109_decision = HOLD`。

允许的下一步只有三类：

1. 先做人类试玩或外部评估，再决定是否开 M109。
2. 如果开 M109，必须限定 2-3 个 milestone 内达成 `commercial_playable_go`，否则停止游戏主线。
3. 如果确认主要 gap 是模型或资产能力，而不是工程能力，则暂停游戏主线，先补底座或资产管线。

## M109 准入条件

进入 M109 前必须同时满足：

- self-development manifest 对 M105-M108 返回 GO。
- Cocos inspector 的玩家视角 gate 不再误报 GO。
- 过期治理例外已删除或延期并写明理由。
- 明确选择 M109 的目标：工程补齐、资产补齐、模型补齐，或验收标准重定义。
- 明确预算上限：继续 Cocos 主线最多再投入 2-3 个 milestone。

## 验证记录

- `python -m pytest tests/test_self_development_manifest.py tests/test_cocos_e2e.py::test_cocos_project_inspector_v2_requires_passing_player_visible_checks tests/test_business_file_size_ratchet.py -q`：10 passed。
- `python -m pytest tests/test_cocos_e2e.py tests/test_self_development_manifest.py tests/test_business_file_size_ratchet.py tests/test_core_domain_purity.py tests/test_production_loc_ratchet.py -q`：40 passed。
- `python -m pytest tests/test_repositories.py tests/test_self_development_manifest.py tests/test_cli.py::test_cli_from_task_card_executes_bounded_patch_and_returns_pr_ready_summary tests/test_execution_loop.py::test_pr_ready_summary_projects_successful_bounded_patch tests/test_contracts.py tests/test_production_loc_ratchet.py tests/test_business_file_size_ratchet.py tests/test_core_domain_purity.py -q`：61 passed，1 skipped。
- `python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" db migrate`：applied `026_m108_task_card_store.sql`。
- `python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" governance self-development-manifest --milestone M105 --milestone M106 --milestone M107 --milestone M108 --output-path state/m105_m108_evaluation_repair_loop/self_development_manifest_default_after_m108_5.json`：GO。
- `python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" governance self-development-manifest --milestone M105 --milestone M106 --milestone M107 --milestone M108 --output-path state/m105_m108_evaluation_repair_loop/self_development_manifest_after_task_card_store.json`：GO。
- `python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" governance active-truth-check --strict --output-path state/governance/active_truth_check_m108_5.json`：GO。
- `python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" governance active-truth-check --strict --output-path state/governance/active_truth_check_task_card_store.json`：GO。
- `python -m apps.operator_cli.main --db-path state/workflow.db --workspace-root "D:\Universal Agentic workflow" test matrix --suite core`：96 passed。
- `python -m infra.scripts.check_doc_links`：passed。
- `python -m pytest -q`：464 passed，136 skipped。
