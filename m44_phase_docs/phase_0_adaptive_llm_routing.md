# M44 Phase 0：自适应 LLM 路由

日期：2026-04-25

## 目标

M44 将 MiniMax / DeepSeek / OpenCode 免费或低成本模型作为可选主路径。默认不开启，避免打断 M41/M42 的强 dogfood 稳定策略；打开 `WORKFLOW_ADAPTIVE_LLM_ROUTING_ENABLED=1` 后，系统会按角色复杂度选择模型 lane。

## 路由规则

- `complex`：coder、implementer、patch、mutation、dev 等写代码角色，默认走 `opencode` + `minimax/MiniMax-M2.7`。
- `medium`：planner、reviewer、quality/test sentinel、design critic 等中等判断角色，默认走 `agent` + `deepseek/deepseek-v4-flash`。
- `simple`：research/search/doc/launch/design summarizer 等轻量角色，默认走 `agent` + `minimax/MiniMax-M2.7`。
- 如果强 dogfood 开启，`dogfood_strong_codex_cli` 仍优先，防止核心自开发链路被低成本路由抢走。

## 新增配置

```powershell
$env:WORKFLOW_ADAPTIVE_LLM_ROUTING_ENABLED="1"
$env:WORKFLOW_ADAPTIVE_SIMPLE_MODEL="minimax/MiniMax-M2.7"
$env:WORKFLOW_ADAPTIVE_MEDIUM_MODEL="deepseek/deepseek-v4-flash"
$env:WORKFLOW_ADAPTIVE_COMPLEX_MODEL="minimax/MiniMax-M2.7"
$env:WORKFLOW_ADAPTIVE_CODING_ADAPTER="opencode"
```

## 验证

- `tests/test_m44_adaptive_routing.py`
- `workflowctl doctor` 会显示 `adaptive_llm_routing` 状态和模型配置。
