# 技术债登记表

结构化真相源是 [docs/governance/tech_debt_registry.json](governance/tech_debt_registry.json)。本文档只提供人类可读摘要；治理 API/CLI 默认读取 JSON。

## 登记规则

- 只登记已经明确接受或在仓库中清晰观察到的债务。
- 不把未分析想法塞进登记表。
- 每条债务必须说明引入位置、计划偿还阶段、当前状态和阻塞影响。
- 历史债务可以汇总，但不能在没有证据的情况下静默删除。
- 不再使用“项目零债”的表达；只说明 blocking debt 是否清零，以及 carry-forward debt 是否阻塞下一阶段。

## 当前结论

- M73-M76 已落地 workflow dogfood、capability control、MCP broker、AutomationLease、Pipeline 最小入口、Cocos E2E 生成与验证路径的骨架，但最近评估确认存在实现降级项。
- M77 是当前活跃修复入口：已修复 OpenAI API/Codex CLI 边界、MiniMax/DeepSeek direct coding API 与受控 patch apply 入口、LangChain 默认路由降级和 Pipeline 假完成风险；MMX/GCP TTS live proof 已跑通，Vertex Imagen/Gemini image 与 Cocos 商业化产物不足仍需继续修。
- 当前不能再宣称所有能力 closeout 硬闸门已完整通过；M77 完成前，能力层开发应以 provider truth、asset generation live proof、pipeline real execution 和 workflow dogfood 可信性为前置。
- 留存策略本轮暂不处理；大型清理仍会持续发生。

## 已偿还债务摘要

| ID | 描述 | 偿还阶段 | 结果 |
| --- | --- | --- | --- |
| TD-STRUCT-001 | Orchestrator/CLI/Web/chat surface 过大 | M62/M63 | facade ratchet、interaction split、chat runtime package、CLI command family、Web UI split 已落地 |
| TD-STRUCT-003 | scheduler-authority 命名可能高估 consensus 语义 | M65/M66 | 已收敛为 `LocalSchedulerLeaseArbiter` local-first 语义，旧名称仅兼容 |
| TD-STRUCT-005 | capability health 缺少 runtime probe 支撑 | M64 | 已加入 `CapabilityProbeResult` ledger，并完成 all-provider require-live probe |
| M67-SEC-001 | `OperatorActionReceipt` 缺少 request scope 绑定 | M67 P2 | 已加入 `scope_hash` / `scope_payload` 并覆盖 tamper / legacy receipt 拒绝 |
| M67-PROBE-001 | capability probe 可能误收 simulated/dry-run/fallback evidence | M67 P3 | 已加入 provider-specific live-proof contract |
| M67-VAL-001 | offline validation 缺少 shard/freshness/timeout 失败报告 | M67 P4 | 已加入 quick/full/shard、timeout trace、last-command 报告 |
| M67-WEB-001 | Web UI 仍依赖 inline CSP 例外和 `innerHTML` 路径 | M67 P5 | 已静态化 operator CSS/JS、移除 CSP `unsafe-inline`、替换 `.innerHTML` 清空路径 |
| M67-SCHED-001 | scheduler 默认文档和 flag-off boot path 未完全 local lease 化 | M67 P6 | 已改为 local scheduler lease arbiter 默认语义，并验证 flag-off 不进入 legacy cluster runtime |
| M67-WF-001 | workflow 自身参与开发缺少完整 proof | M67 P8 | 已用 workflow 跑 simple/medium/complex 任务并生成 manifest/operator packet |
| M73-CAP-001 | capability policy/live proof/write_set/receipt 缺少统一强制入口 | M73 | 已加入 capability enforcement pilot 和 `CapabilityInvocation` contract |
| M73-MCP-001 | MCP include_mcp 可能暴露全部 profile | M73 | 已加入 canonical tool id、selector、collision guard，未显式 selector 时不暴露全部 MCP |
| M73-AUTO-001 | 无人值守 resume/batch/test/artifact 写入缺少有界授权 | M73 | 已加入 file-backed `AutomationLease` |
| M74-PIPE-001 | Pipeline 概念缺少正式 contract | M74 | 已加入 `WorkflowPipeline` / `PipelineStage` contract 与 preview |
| M75-PIPE-EXEC-001 | Pipeline 缺少最小执行入口 | M75 | 已加入串行 `workflowctl pipeline run` |
| M76-COCOS-001 | H5 游戏 pipeline 缺少真实 Cocos E2E evidence | M76 | 已加入 `workflowctl game cocos-e2e`，生成 Cocos Creator 项目、构建 Web Mobile、浏览器 playtest |

## 当前未偿还债务

| ID | 描述 | 当前状态 | 阻塞影响 |
| --- | --- | --- | --- |
| M77-PROVIDER-001 | OpenAI API、Codex CLI、MiniMax/DeepSeek API、OpenCode CLI、MMX/GCP/Vertex generation、MCP tool、LangChain experimental 的边界混乱 | partially_repaid | provider access contract、docs、tests 和 direct API controlled patch apply 已落地；后续仍需更多真实 route evidence |
| M77-MMX-001 | MMX/MiniMax 当前主要是 text evidence 通道，未完整接入 image/speech/music 资产生成主路径 | partially_repaid | API wrapper、二进制资产落盘、manifest 和 image/speech/music live proof 已落地；缺 Cocos asset pipeline 批量调用 |
| M77-VERTEX-001 | Vertex 当前主要是文本 evidence，未完整接入 Imagen/Gemini image/GCP TTS/visual review 生成与审查能力 | partially_repaid | Cloud TTS 已拆为 `gcp_tts_api` 并真实 live proof；Vertex Imagen/Gemini image/visual review 仍未完成 |
| M77-LANGCHAIN-001 | LangChain 当前缺少主线不可替代价值，仍可能被误认为默认 provider route | partially_repaid | 已降级为 experimental / opt-in，并保留旧 adapter 兼容 |
| M77-PIPE-001 | Pipeline run 仍偏最小/v0，需证明 stage 真实执行、失败短路和 evidence chain | partially_repaid | 已禁止 capability stage 伪 completed，增加 blocked/failed/skipped 短路和 stage evidence；仍需接全量 workflow run/capability invocation |
| M77-COCOS-001 | Cocos E2E 当前偏技术 demo，缺商业化 UI、美术、音效、动画、粒子、皮肤、关卡闭环 | partially_repaid | 已新增 `--require-commercial` NO-GO 硬门禁，防止半成品冒充商业化完成；真实商业化产物仍未完成 |
| M67-CARRY-001 | `repositories.py`、`service_lifecycle.py`、`service_projection.py`、`interaction_catalog.py`、`models.py` 仍偏大 | carry_forward | 非阻塞维护债；只有在后续能力开发中造成真实痛点时继续拆分 |

## M76 收口说明

- 根目录当前保留 M73-M76 最终方案、执行报告和两轮 M76 后评估。
- capability readiness 不接受 fallback-only、generic greeting、simulated 或 dry-run 作为 `verified_ready`。
- 动态/自适应路由仍为 opt-in；是否 default-on 必须另开 telemetry 决策。
- GitHub/PR 能力边界保持诚实：系统可生成 PR-ready summary，但不会自动 commit/push/PR，除非 operator 明确要求。
## M77 补充记录

- `M77-VERTEX-001` 已从 “仅 GCP TTS 可用” 推进到 Vertex AI REST wrapper，并真实跑通 `vertex_imagen` 与 `vertex_gemini_review` live proof。
- `M77-MMX-001` 已进入并真实跑通 Cocos asset manifest 批处理：`workflowctl game cocos-assets` 会批量生成图像、语音、音乐、TTS 和可选视觉审查 evidence。
- `M77-COCOS-001` 仍未完全偿还：商业化资产门禁可以识别生成物，但原生 Cocos UI、动画时间线、关卡切换 UI 和真正商业级 game body 仍是后续工作。
