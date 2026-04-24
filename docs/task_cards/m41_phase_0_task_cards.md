# M41 Phase 0 任务卡索引

当前阶段只做合同冻结、可见性和最小能力骨架，不让 workflow 自动接管 repo mutation。

| 任务 | 状态 | 目标 |
| --- | --- | --- |
| M41-0A | done | 冻结强模型 dogfood 策略和执行画像字段 |
| M41-0B | done | 扩展 doctor，诊断 Claude/MMX/Vertex，保持 redaction |
| M41-0C | done | 接入 artifact-only Claude/MMX/Vertex adapter 骨架 |
| M41-0D | done | 新增 architecture delivery cluster |
| M41-0E | done | 增加定向测试，避免外部能力破坏基础路径 |
| M41-0F | done | 已进行一次受控 dogfood 演练，并确认强模型认证与 cluster runtime 仍是后续前置条件 |

## 阶段边界

- 不自动 commit、push 或创建 GitHub PR。
- 不启用低成本自适应模型路由。
- 不让 Claude 写 repo。
- 不把 Vertex 伪装成 ready；没有本地命令模板时必须 degraded。
