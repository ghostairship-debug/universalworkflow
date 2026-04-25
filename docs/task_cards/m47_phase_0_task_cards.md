# M47 Phase 0 任务卡索引

| ID | 状态 | 摘要 |
| --- | --- | --- |
| M47-0A | done | 更新活跃中文文档和技术债 |
| M47-1A | done | 跑 doc links、offline validation、pytest quick |
| M47-2A | done | 跑一次 slow 回归 |
| M47-3A | done | git commit/push 并停止 |

## 验证记录

- `python -m infra.scripts.check_doc_links`：通过。
- `python -m infra.scripts.offline_validation --skip-offline-probe`：通过，`overall_passed=true`。
- `python -m pytest -q`：`242 passed, 134 skipped`。
- `python -m pytest -q --run-slow`：`376 passed`。
