# M41-0C：外部 Artifact-only Adapter

## 写入范围

- `packages/worker_adapters/external_artifact_adapters.py`
- `packages/core_domain/services.py`
- `apps/remote_worker_api/main.py`
- `packages/worker_adapters/subprocess_support.py`

## 验收

- `claude_architect`、`mmx_multimodal`、`vertex_multimodal` 只支持 `artifact_only`。
- Claude 有每 session/M 阶段一次调用保护的本地 guard。
- MMX 默认作为多模态主入口。
- Vertex 第一版要求显式命令模板，避免误报 ready。
