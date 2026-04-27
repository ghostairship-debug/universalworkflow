# 技术债登记表

结构化真相源是 [docs/governance/tech_debt_registry.json](governance/tech_debt_registry.json)。本文档只提供人类可读摘要；治理 API/CLI 默认读取 JSON。

## 登记规则

- 只登记已经明确接受或在仓库中清晰观察到的债务。
- 不把未分析想法塞进登记表。
- 每条债务必须说明引入位置、计划偿还阶段、当前状态和阻塞影响。
- 历史债务可以汇总，但不能在没有证据的情况下静默删除。
- 不使用“项目零债”的表达；只说明 blocking debt 是否清零，以及 carry-forward debt 是否阻塞下一阶段。

## 当前结论

- M80-M104 的 provider runtime truth、asset factory、active truth check、workflow dogfood proof、`commercial_cocos_game` pipeline template、LangGraph 本地运行时、SQLite checkpoint、interrupt/resume、repair loop、subgraph/supervisor 探针和 Cocos graph pressure test 已落地。
- M84 卫生清理确认：仓库源代码规模可控，膨胀主要来自 `state/` 生成态 evidence、pytest 临时目录和 Cocos 构建产物。
- 商业化游戏方向保留，但 M84 真实试玩反馈证明当前生成物不具备商业化可玩质量。
- 因此 `M77-COCOS-001` 从“已偿还”调整为“部分偿还”：技术链路已通，成品质量门禁未达标。
- M85-M104 已收敛 LangGraph 与 workflow 的主要边界：LangGraph 负责图状态、checkpoint、人审暂停、subgraph 和 repair loop；workflow 继续负责 receipt、lease、write_set、provider live proof、evidence 和 operator packet。
- M105 起优先处理 Cocos 真实工程质量和玩家视角验收。
- 留存策略本轮暂不处理；大型生成态清理仍会持续发生。

## 当前未偿还或部分偿还债务

| ID | 描述 | 当前状态 | 阻塞影响 |
| --- | --- | --- | --- |
| M77-COCOS-001 | Cocos pipeline 能生成、构建和试玩，但 UI、面板、关卡、音频和玩家视角可玩性没有达到商业化成品标准 | partially_repaid | 阻塞把商业化游戏生成声明为正式成品能力；不阻塞继续优化 pipeline |
| M84-GAME-QA-001 | 商业化验收过度依赖内部状态变量和事件覆盖，缺少玩家视角 UI/UX/可玩性断言 | open | 阻塞下一次商业化游戏交付 GO |
| M77-LANGCHAIN-001 | LangChain 保留为实验性 agent adapter，但当前没有主线不可替代价值 | partially_repaid | 非阻塞；继续保持 opt-in |
| M67-CARRY-001 | `repositories.py`、`service_lifecycle.py`、`service_projection.py`、`interaction_catalog.py`、`models.py` 仍偏大 | carry_forward | 非阻塞；后续能力开发触发真实痛点时再拆 |

## 已偿还债务摘要

| ID | 描述 | 偿还阶段 | 结果 |
| --- | --- | --- | --- |
| TD-STRUCT-001 | Orchestrator/CLI/Web/chat surface 过大 | M62/M63 | facade ratchet、interaction split、chat runtime package、CLI command family、Web UI split 已落地 |
| TD-STRUCT-003 | scheduler-authority 命名可能高估 consensus 语义 | M65/M66 | 收敛为 `LocalSchedulerLeaseArbiter` local-first 语义 |
| TD-STRUCT-005 | capability health 缺少 runtime probe 支撑 | M64 | 加入 `CapabilityProbeResult` ledger 和 require-live probe |
| M67-SEC-001 | `OperatorActionReceipt` 缺少 request scope 绑定 | M67 P2 | 加入 `scope_hash` / `scope_payload` |
| M67-PROBE-001 | capability probe 可能误收 simulated/dry-run/fallback evidence | M67 P3 | 加入 provider-specific live-proof contract |
| M67-VAL-001 | offline validation 缺少 shard/freshness/timeout 报告 | M67 P4 | 加入 quick/full/shard、timeout trace、last-command 报告 |
| M67-WEB-001 | Web UI 依赖 inline CSP 例外和 `innerHTML` 路径 | M67 P5 | 静态化 operator CSS/JS，移除 CSP `unsafe-inline`，替换危险路径 |
| M67-SCHED-001 | scheduler 默认语义未完全 local lease 化 | M67 P6 | 改为 local scheduler lease arbiter 默认语义 |
| M73-MCP-001 | MCP include_mcp 可能暴露全部 profile | M73 | 加入 canonical tool id、selector、collision guard |
| M74-PIPE-001 | Pipeline 缺少正式 contract | M74 | 加入 `WorkflowPipeline` / `PipelineStage` |
| M75-PIPE-EXEC-001 | Pipeline 缺少最小执行入口 | M75 | 加入串行 `workflowctl pipeline run` |
| M77-PROVIDER-001 | Provider / Tool / Agent / Asset 边界混乱 | M80 | provider contract、verified-only health、route stats 已拆开 |
| M77-MMX-001 | MMX/MiniMax 缺真实 image/speech/music 资产生成主路径 | M81 | 加入 MiniMax wrappers、binary evidence、asset factory |
| M77-VERTEX-001 | Vertex/gcloud/GCP TTS 边界混乱 | M81 | 拆出 GCP TTS，Vertex Imagen/Gemini review 进入 live proof 和 QA |
| M77-PIPE-001 | Pipeline run 需要证明 stage 真实执行和失败短路 | M83 | `commercial_cocos_game` template 已真实执行 asset factory、Cocos generation/build/playtest 和 readiness gate |
| M82-ACTIVE-TRUTH-001 | 活跃文档可能把已完成工作写成 planned/current/open | M82 | 加入 `workflowctl governance active-truth-check` |
| M84-CORE-PURITY-001 | Cocos/asset/business pipeline code 混入 core_domain | M90 | 垂直 Cocos/asset 实现移到 contributions/runtime_integrations，core_domain 边界恢复 |
| M84-PIPELINE-TRUTH-001 | Pipeline 可能把 placeholder/skipped/validation 失败误写成 completed | M90 | stage truth、安全 command runner、required dependency 和商业化三层 gate 已收敛 |
| M84-RATCHET-001 | 缺少 production/core/file ratchet | M90 | 加入 core purity、production LOC、业务文件大小和架构文档测试 |
| M85-LANGGRAPH-DUP-001 | workflow 编排与 LangGraph primitive 重叠 | M104 | 明确 LangGraph 承接图状态、checkpoint、人审暂停、subgraph 和 repair loop；workflow 保留安全、证据和 provider truth |

## 下一阶段建议

1. 执行 `CURRENT_DEVELOPMENT_WORKFLOW.md` 里的 M105-M108 计划，从 M105.1 的 Cocos command/config truth 开始。
2. 开发计划文档只写到 milestone 和 phase；task card 只在 active phase 生成。
3. 升级商业化游戏验收和 Cocos-native 生产线，但继续区分 technical smoke、production scaffold 和 commercial playable。
4. 保持 `state/` 生成态定期清理，避免 evidence 和构建产物再次膨胀到 GB 级。
