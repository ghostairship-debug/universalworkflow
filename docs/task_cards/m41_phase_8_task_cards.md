# M41 Phase 8 任务卡索引

| ID | 状态 | 摘要 |
| --- | --- | --- |
| M41-8A | done | 增加 Codex CLI dogfood 后端选择，并让 architecture delivery 的核心 agent 角色默认解析到 Codex artifact-only |
| M41-8B | done | 为 LangChain agent lane 增加 MiniMax -> DeepSeek -> OpenAI 的 provider factory |
| M41-8C | done | 扩展 doctor、run detail 投影和 Codex artifact prompt |

## 收口说明

Phase 8 解除 M41 dogfood 对 `OPENAI_API_KEY` 的默认硬依赖。LangChain lane 仍可显式启用，但默认强 dogfood 主路径改为 Codex CLI。

2026-04-25 追加验证：升级 npm `@openai/codex` 到 `0.125.0` 后，本机 `codex exec --model gpt-5.5` 已可用，Codex CLI dogfood 默认恢复为 `gpt-5.5 xhigh`。已修复 Codex CLI 参数顺序、stdin prompt、UTF-8 解码和 artifact 父目录创建，并用真实 Codex CLI 生成 `state/m41_dogfood_smoke/planner_design.md`。

升级后再次用真实 `CodexAdapter.launch()` 生成 `state/m41_dogfood_smoke/planner_design_gpt55.md`，返回模型为 `gpt-5.5`，说明 workflow adapter 路径也已恢复强模型 dogfood。
