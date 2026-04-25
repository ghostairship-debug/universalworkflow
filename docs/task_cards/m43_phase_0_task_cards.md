# M43 Phase 0 任务卡索引

| ID | 状态 | 摘要 |
| --- | --- | --- |
| M43-0A | done | 读取 PDF，冻结商业化小游戏验收清单 |
| M43-1A | done | 升级本地 block puzzle artifact：真实拖拽、触控、道具、美术和商业化外围 |
| M43-2A | done | 增加定点测试，覆盖拖拽、道具、PDF trace 和输出目录 |
| M43-3A | done | 生成 `examples/block_puzzle_shop/` 并做真实 smoke/playtest |
| M43-4A | done | 记录 M43 evidence 和 closeout，为 M44 自适应路由做输入 |

## Bug-first 规则

- 游戏 artifact 不能生成时先修生成器。
- 前端 HTML 静态检查失败时先修 UI/交互。
- workflow run 无法产物化时先修编排/路径/执行问题。
- 不因为追赶 M44-M47 而跳过 M43 的拖拽和商业化验收。

## 收口证据

- 真实 PDF：`C:\Users\74755\Desktop\俄罗斯方块消除策划文档4.2.pdf`
- 示例 artifact：[examples/block_puzzle_shop/index.html](../../examples/block_puzzle_shop/index.html)
- PDF 映射：[examples/block_puzzle_shop/design_trace.md](../../examples/block_puzzle_shop/design_trace.md)
- 浏览器 smoke 截图：`state/m43_block_puzzle_e2e/block_puzzle_shop_smoke.png`
- 定点验证：`tests/test_m43_game_artifacts.py` 与 `tests/test_execution_loop.py::test_compile_run_can_materialize_block_puzzle_vertical_slice`
