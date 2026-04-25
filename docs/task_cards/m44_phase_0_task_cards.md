# M44 Phase 0 任务卡索引

| ID | 状态 | 摘要 |
| --- | --- | --- |
| M44-0A | done | 冻结 MiniMax/DeepSeek/OpenCode 免费模型优先策略 |
| M44-1A | done | 新增 adaptive routing 配置和投影字段 |
| M44-2A | done | execution resolution 按角色复杂度选择模型 lane |
| M44-3A | done | doctor/status 可见性和定点测试 |

## 收口结论

自适应路由已可用但默认关闭。当前它是“可解释选择器”，不是完全自治的成本优化器；复杂 repo mutation 仍应由主进程或强 dogfood gate 控制。
