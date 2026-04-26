# M73-M76 无人值守全量收口执行报告

生成日期：2026-04-26

## 结论

状态：`completed`

M73-M76 已完成可信控制面、Pipeline 最小产品层、workflow dogfood evidence、provider live proof、验证收口和 Cocos H5 E2E 入口建设。收口过程中发现 1 个 workflow 自身 bug：CLI capability projection 在未显式传 selector 时没有继承 `WORKFLOW_MCP_BROKER_PROFILE_IDS`，导致 slow suite 失败。该问题已按 bug-first 修复，并通过 targeted test 与完整 slow suite 复跑。

当前 GO/NO-GO：`GO`。

## 完成内容

### M73 Capability Control Layer

- 新增 `CapabilityInvocation` contract，并在高风险 `patch_apply` 路径引入 capability enforcement pilot。
- `resume_run` / `batch_resume` 可以携带 `operator_receipt_id`，用于把 receipt 纳入执行 envelope。
- MCP Broker v1 支持 canonical tool id、同名工具 collision guard、profile/tool selector；`include_mcp=True` 不再自动暴露全部 MCP profile。
- 新增 `AutomationLease`，支持无人值守 resume/batch/test/artifact 写入授权，同时继续禁止 secrets、workspace root 扩大、未授权 publish/push/PR。
- Manifest V2 provenance 增加 task card、evidence、operator packet trace link 和 commit sha 字段。

### M74-M75 Pipeline Layer

- 新增 `WorkflowPipeline` / `PipelineStage` contract。
- `workflowctl pipeline preview/run` 支持最小 plan-of-plans 预览和串行执行。
- 内置 `workflow_self_development_pipeline` 与 `h5_game_commercialization_pipeline` v0。
- Pipeline preview 不直接 mutation；复杂写入仍走既有 workflow run/control-plane。

### M76 Cocos H5 E2E

- 新增 `workflowctl game cocos-e2e`。
- 从 PDF `C:\Users\74755\Desktop\俄罗斯方块消除策划文档4.2.pdf` 提取策划文本，生成 Cocos Creator 3.8 项目。
- 使用 `C:\ProgramData\cocos\editors\Creator\3.8.8\CocosCreator.exe` 构建 Web Mobile。
- 浏览器自动测试覆盖非空 canvas、像素变化、拖拽成功、分数变化、至少一次消除、暂停/复活/皮肤/作品界面和 390x844 移动端布局。
- 明确排除 `C:\Users\74755\Desktop\游戏平台demo`，未读写该目录。

## Workflow Dogfood Evidence

- Phase task cards：`state/m73_m76_autopilot/task_cards/`
- Route/evidence：`state/m73_m76_autopilot/evidence/`
- Operator packet：`state/m73_m76_autopilot/operator_packets/m73_m76_operator_packet.json`
- 并发 evidence：`state/m73_m76_autopilot/evidence/M73_artifact_parallel_batch_resume.json`
- Cocos pre-push evidence：`state/m73_m76_autopilot/cocos_e2e/1010_block_puzzle_cocos_prepush3/cocos_game_e2e_manifest.json`

## Bug-First 修复

发现：`pytest --run-slow` 首轮结果为 `475 passed, 1 failed`，失败测试为 `tests/test_cli.py::test_cli_can_preview_m8_capability_projection`。

根因：CLI projection 命令在没有显式 `--mcp-profile-id` 时传入空列表，屏蔽了环境变量 `WORKFLOW_MCP_BROKER_PROFILE_IDS`，与 service 层“`None` 表示继承环境 selector”的契约不一致。

修复：

- `apps/operator_cli/catalog_commands.py`：未传 selector 时传 `None`，让 service 继承环境变量。
- `apps/orchestrator_api/routers/catalog.py`：API query selector 改为可选，保持同一契约。

验证：

- `python -m pytest tests/test_cli.py::test_cli_can_preview_m8_capability_projection tests/test_api.py::test_api_exposes_m8_capability_sources_and_projection_preview -q --run-slow`
- `python -m pytest -q --run-slow --basetemp state/.pytest-tmp-workflow/m73m76-slow-closeout-rerun`

## Closeout Gates

| Gate | 结果 |
| --- | --- |
| `python -m infra.scripts.check_doc_links` | passed，10 docs checked |
| `workflowctl doctor --strict` | passed，status ok |
| `workflowctl test matrix --suite unit` | passed，57 tests |
| `workflowctl test matrix --suite core` | passed，93 tests |
| `workflowctl test matrix --suite integration` | passed，7 passed / 134 skipped |
| `workflowctl validation run --suite full --skip-offline-probe` | passed |
| `workflowctl capability probe --provider all --require-live` | passed，blocked_count 0 |
| `python -m pytest -q --run-slow` | passed，476 tests |

Provider live proof 结果：

- shell：`verified_ready`
- Codex：`verified_ready`
- OpenCode：`verified_ready`
- MMX：`verified_ready`
- Vertex：`verified_ready`
- Claude：`verified_ready`
- LangChain：`verified_ready`

## 剩余边界

- `repositories.py` 等历史大文件仍是非阻塞维护债，后续在真实能力开发中遇到痛点时继续拆。
- Dynamic/adaptive routing 仍为 opt-in；是否 default-on 必须基于后续 telemetry 决策。
- Cocos Creator 命令行在本机可能返回非零原始码但已生成 build artifact；当前 E2E 以 Web Mobile artifact 和浏览器 playtest 作为最终 GO/NO-GO 证据，原始码会写入 manifest 供审计。

## Go / No-Go

M73-M76 收口结论为 `GO`。项目可以恢复能力层开发，但下一阶段仍必须保持：

- workflow 共同开发
- phase 多 task card
- route/evidence/operator packet
- scoped receipt / AutomationLease
- provider require-live proof
- bug-first 修复纪律
