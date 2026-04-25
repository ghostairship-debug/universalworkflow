# M43-1A：商业化 block puzzle vertical slice

## 目标

基于 PDF 策划案，把当前 `local_game_artifacts.py` 中的 block puzzle 原型升级为可实际操作的商业化 vertical slice。

## 交付

- `index.html` 包含真实桌面拖拽和触控拖动。
- 棋盘支持可放/不可放预览。
- 候选块拖动时显示上移 ghost，避免手指遮挡。
- 道具系统包含刷新方块、横竖排消除、打乱重排。
- 商业化入口包含广告复活、结算插屏点位、皮肤/背景/棋盘装饰、拼图作品。
- README 和 design trace 明确来自 PDF，不再写“拖拽后续扩展”。

## 验收

- `tests/test_execution_loop.py::test_compile_run_can_materialize_block_puzzle_vertical_slice`
- 新增 M43 定点测试。
- 生成示例 artifact 后可用浏览器打开。
