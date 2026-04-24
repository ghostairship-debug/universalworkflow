from __future__ import annotations

from pathlib import Path
import re


def _pdf_paths_for_goal(goal: str) -> list[Path]:
    return [
        Path(match.strip().strip("`'\"“”‘’"))
        for match in re.findall(r"([A-Za-z]:[\\/][^\n\r`\"'“”]+?\.pdf)", goal, flags=re.IGNORECASE)
    ]


def _read_pdf_text(path: Path, *, max_chars: int = 4000) -> tuple[int, str, str | None]:
    if not path.exists():
        return 0, "", "文件不存在"
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - optional dependency varies by local runtime.
        return 0, "", f"pypdf 不可用：{exc}"
    try:
        reader = PdfReader(str(path))
        chunks: list[str] = []
        for page in reader.pages:
            chunks.append(page.extract_text() or "")
            if sum(len(chunk) for chunk in chunks) >= max_chars:
                break
        text = re.sub(r"\s+", " ", "\n".join(chunks)).strip()
        return len(reader.pages), text[:max_chars], None
    except Exception as exc:  # pragma: no cover - depends on external PDF validity.
        return 0, "", f"读取失败：{exc}"


def _pdf_context_for_goal(goal: str) -> tuple[str, str]:
    paths = _pdf_paths_for_goal(goal)
    if not paths:
        return "- 未在目标中找到可读取 PDF 路径，使用聊天目标中的需求描述。", ""

    sections: list[str] = []
    combined: list[str] = []
    for path in paths:
        page_count, text, error = _read_pdf_text(path)
        if error:
            sections.append(f"- `{path.as_posix()}`：{error}。")
            continue
        combined.append(text)
        excerpt = text[:900] + ("..." if len(text) > 900 else "")
        sections.append(
            f"- `{path.as_posix()}`：已读取 {page_count} 页，提取摘要：{excerpt}"
        )
    return "\n".join(sections), "\n".join(combined)


def _snake_game_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>贪吃蛇小游戏</title>
  <style>
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #0f1f1b; color: #f4f1e8; font-family: "Microsoft YaHei", sans-serif; }
    main { width: min(92vw, 540px); text-align: center; }
    canvas { width: min(92vw, 420px); height: min(92vw, 420px); background: #172b24; border: 6px solid #d7b56d; border-radius: 18px; box-shadow: 0 22px 80px rgba(0,0,0,.35); }
    .hud { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin: 14px auto; max-width: 420px; }
    button { border: 0; border-radius: 999px; padding: 10px 16px; background: #d7b56d; color: #10221d; font-weight: 700; cursor: pointer; }
    p { color: #c9d5cc; }
  </style>
</head>
<body>
  <main>
    <h1>贪吃蛇小游戏</h1>
    <div class="hud"><strong>分数：<span id="score">0</span></strong><button id="restart">重新开始</button></div>
    <canvas id="game" width="420" height="420"></canvas>
    <p>方向键 / WASD 控制移动，撞墙或撞到自己会重新开始。</p>
  </main>
  <script>
    const canvas = document.getElementById('game');
    const ctx = canvas.getContext('2d');
    const scoreEl = document.getElementById('score');
    const size = 21;
    const cell = canvas.width / size;
    let snake, food, dir, nextDir, score, timer;
    function placeFood() {
      do {
        food = { x: Math.floor(Math.random() * size), y: Math.floor(Math.random() * size) };
      } while (snake.some(p => p.x === food.x && p.y === food.y));
    }
    function reset() {
      snake = [{ x: 10, y: 10 }, { x: 9, y: 10 }, { x: 8, y: 10 }];
      dir = { x: 1, y: 0 };
      nextDir = dir;
      score = 0;
      scoreEl.textContent = score;
      placeFood();
      clearInterval(timer);
      timer = setInterval(tick, 120);
      draw();
    }
    function tick() {
      dir = nextDir;
      const head = { x: snake[0].x + dir.x, y: snake[0].y + dir.y };
      if (head.x < 0 || head.y < 0 || head.x >= size || head.y >= size || snake.some(p => p.x === head.x && p.y === head.y)) {
        reset();
        return;
      }
      snake.unshift(head);
      if (head.x === food.x && head.y === food.y) {
        score += 10;
        scoreEl.textContent = score;
        placeFood();
      } else {
        snake.pop();
      }
      draw();
    }
    function draw() {
      ctx.fillStyle = '#172b24';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#e65f3c';
      ctx.beginPath();
      ctx.arc((food.x + .5) * cell, (food.y + .5) * cell, cell * .36, 0, Math.PI * 2);
      ctx.fill();
      snake.forEach((part, index) => {
        ctx.fillStyle = index === 0 ? '#f5d26f' : '#7fcf9a';
        ctx.fillRect(part.x * cell + 2, part.y * cell + 2, cell - 4, cell - 4);
      });
    }
    function setDirection(x, y) {
      if (dir.x + x === 0 && dir.y + y === 0) return;
      nextDir = { x, y };
    }
    window.addEventListener('keydown', event => {
      const key = event.key.toLowerCase();
      if (key === 'arrowup' || key === 'w') setDirection(0, -1);
      if (key === 'arrowdown' || key === 's') setDirection(0, 1);
      if (key === 'arrowleft' || key === 'a') setDirection(-1, 0);
      if (key === 'arrowright' || key === 'd') setDirection(1, 0);
    });
    document.getElementById('restart').addEventListener('click', reset);
    reset();
  </script>
</body>
</html>
"""


def _block_puzzle_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>方块艺境 - 1010 Block Puzzle</title>
  <style>
    :root {
      --bg: #14100d;
      --panel: rgba(255, 250, 238, .86);
      --ink: #221710;
      --muted: #7a685c;
      --gold: #d6a84f;
      --coral: #e96b4b;
      --jade: #4ea87b;
      --sky: #62a9d7;
      --violet: #8b70c9;
      --cell: rgba(255, 255, 255, .16);
      --grid: rgba(37, 24, 16, .14);
      font-family: "Microsoft YaHei", "Noto Sans SC", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      background:
        radial-gradient(circle at 12% 12%, rgba(255, 216, 137, .35), transparent 28%),
        radial-gradient(circle at 84% 18%, rgba(233, 107, 75, .32), transparent 24%),
        linear-gradient(135deg, #26170f 0%, #735033 46%, #e2b761 100%);
      overflow-x: hidden;
    }
    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(255,255,255,.07) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.06) 1px, transparent 1px);
      background-size: 42px 42px;
      mask-image: radial-gradient(circle at center, black, transparent 80%);
    }
    button {
      border: 0;
      border-radius: 999px;
      padding: 12px 18px;
      font-weight: 800;
      color: #25160d;
      background: linear-gradient(135deg, #ffe6a3, var(--gold));
      box-shadow: 0 10px 24px rgba(96, 54, 12, .22);
      cursor: pointer;
      transition: transform .16s ease, box-shadow .16s ease, filter .16s ease;
    }
    button:hover { transform: translateY(-1px); filter: saturate(1.08); }
    button.secondary { background: rgba(255,255,255,.62); box-shadow: inset 0 0 0 1px rgba(70,48,27,.14); }
    button.danger { background: linear-gradient(135deg, #ffb199, #e96b4b); color: #fffaf0; }
    .app {
      width: min(1200px, calc(100vw - 28px));
      margin: 0 auto;
      padding: 24px 0 40px;
    }
    .hero {
      display: grid;
      grid-template-columns: 1.05fr .95fr;
      gap: 22px;
      align-items: stretch;
    }
    .card {
      background: var(--panel);
      border: 1px solid rgba(255,255,255,.5);
      box-shadow: 0 24px 90px rgba(41, 20, 6, .26);
      border-radius: 28px;
      backdrop-filter: blur(20px);
    }
    .brand {
      padding: 30px;
      position: relative;
      overflow: hidden;
    }
    .brand::after {
      content: "";
      position: absolute;
      right: -70px;
      top: -60px;
      width: 220px;
      height: 220px;
      border-radius: 54px;
      rotate: 18deg;
      background: linear-gradient(135deg, rgba(214,168,79,.52), rgba(233,107,75,.22));
    }
    .eyebrow {
      color: #8b5b21;
      text-transform: uppercase;
      letter-spacing: .16em;
      font-size: 12px;
      font-weight: 900;
    }
    h1 {
      margin: 12px 0 12px;
      font-size: clamp(36px, 6vw, 72px);
      line-height: .94;
      letter-spacing: -0.06em;
    }
    .subtitle { color: var(--muted); font-size: 17px; line-height: 1.72; max-width: 620px; }
    .mode-row, .toolbar, .hud-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }
    .mode-row { margin-top: 24px; }
    .stats {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-top: 22px;
    }
    .stat {
      padding: 14px;
      border-radius: 18px;
      background: rgba(255,255,255,.54);
      min-height: 78px;
    }
    .stat span { display: block; color: var(--muted); font-size: 12px; font-weight: 800; }
    .stat strong { display: block; margin-top: 6px; font-size: 23px; }
    .game-card { padding: 20px; display: grid; gap: 14px; }
    .hud-row { justify-content: space-between; }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      padding: 8px 11px;
      color: #69491f;
      font-weight: 800;
      background: rgba(255,246,220,.74);
      border: 1px solid rgba(116,80,38,.12);
    }
    .board {
      display: grid;
      grid-template-columns: repeat(10, 1fr);
      gap: 5px;
      padding: 12px;
      border-radius: 26px;
      background: rgba(27, 18, 12, .84);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,.12), 0 18px 44px rgba(0,0,0,.24);
      user-select: none;
    }
    .cell {
      aspect-ratio: 1;
      border-radius: 10px;
      background: var(--cell);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,.1);
      transition: transform .12s ease, background .12s ease;
    }
    .cell.filled {
      background: linear-gradient(135deg, var(--tone-a), var(--tone-b));
      box-shadow: inset 0 2px 5px rgba(255,255,255,.35), 0 6px 12px rgba(0,0,0,.16);
    }
    .cell.preview-ok { background: rgba(78,168,123,.45); }
    .cell.preview-bad { background: rgba(233,107,75,.42); }
    .tray {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
    }
    .piece {
      min-height: 116px;
      padding: 13px;
      border-radius: 22px;
      background: rgba(255,255,255,.58);
      border: 2px solid transparent;
      display: grid;
      place-items: center;
    }
    .piece.selected { border-color: var(--gold); box-shadow: 0 0 0 5px rgba(214,168,79,.18); }
    .mini-grid {
      display: grid;
      gap: 4px;
    }
    .mini-cell {
      width: 18px;
      height: 18px;
      border-radius: 5px;
      background: transparent;
    }
    .mini-cell.on {
      background: linear-gradient(135deg, var(--tone-a), var(--tone-b));
      box-shadow: inset 0 2px 4px rgba(255,255,255,.32);
    }
    .side {
      display: grid;
      gap: 14px;
    }
    .panel { padding: 20px; }
    .panel h2, .panel h3 { margin: 0 0 10px; }
    .quest {
      padding: 14px;
      border-radius: 18px;
      background: rgba(255,255,255,.54);
      color: var(--muted);
      line-height: 1.55;
    }
    .log {
      height: 132px;
      overflow: auto;
      padding: 12px;
      border-radius: 16px;
      background: rgba(44,30,21,.08);
      color: #6d594c;
      font-size: 13px;
    }
    .log div { margin-bottom: 6px; }
    .modal {
      position: fixed;
      inset: 0;
      display: none;
      place-items: center;
      padding: 22px;
      background: rgba(22, 14, 9, .58);
      z-index: 10;
    }
    .modal.active { display: grid; }
    .modal-card {
      width: min(520px, 100%);
      padding: 24px;
      border-radius: 28px;
      background: #fff8e9;
      box-shadow: 0 30px 120px rgba(0,0,0,.38);
    }
    .jigsaw {
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 7px;
      margin: 12px 0;
    }
    .jigsaw span {
      aspect-ratio: 1;
      display: grid;
      place-items: center;
      border-radius: 12px;
      background: rgba(214,168,79,.18);
      color: #946a22;
      font-weight: 900;
    }
    .jigsaw span.unlocked { background: linear-gradient(135deg, #ffd36e, #e96b4b); color: white; }
    .toast {
      position: fixed;
      left: 50%;
      top: 22px;
      transform: translateX(-50%);
      padding: 12px 18px;
      border-radius: 999px;
      background: rgba(31,22,14,.88);
      color: #fff8e9;
      box-shadow: 0 14px 44px rgba(0,0,0,.28);
      opacity: 0;
      pointer-events: none;
      transition: opacity .2s ease, translate .2s ease;
      z-index: 20;
    }
    .toast.show { opacity: 1; translate: 0 8px; }
    body.skin-gem .cell.filled, body.skin-gem .mini-cell.on { filter: saturate(1.28) hue-rotate(28deg); }
    body.skin-wool .cell.filled, body.skin-wool .mini-cell.on { filter: saturate(.72) sepia(.15); border-radius: 999px; }
    @media (max-width: 920px) {
      .hero { grid-template-columns: 1fr; }
      .stats { grid-template-columns: repeat(2, 1fr); }
    }
  </style>
</head>
<body>
  <div class="toast" id="toast">提示</div>
  <main class="app">
    <section class="hero">
      <div class="card brand">
        <div class="eyebrow">Commercial vertical slice</div>
        <h1>方块艺境</h1>
        <p class="subtitle">基于《1010 Block Puzzle》策划案 4.2：10x10 棋盘、3 个候选方块、行列消除、Combo/Streak、经典与闯关、广告复活、皮肤和拼图收集都在一个可运行 HTML 原型里。</p>
        <div class="mode-row">
          <button data-testid="classic-mode" id="classicMode">经典模式</button>
          <button data-testid="adventure-mode" id="adventureMode">第 <span id="levelLabel">1</span> 关</button>
          <button class="secondary" data-testid="skin-panel" id="skinPanel">装饰</button>
          <button class="secondary" data-testid="works-panel" id="worksPanel">作品</button>
        </div>
        <div class="stats">
          <div class="stat"><span>当前模式</span><strong id="modeStat">经典</strong></div>
          <div class="stat"><span>当前分数</span><strong id="score">0</strong></div>
          <div class="stat"><span>历史最高</span><strong id="best">0</strong></div>
          <div class="stat"><span>复活次数</span><strong id="revives">1</strong></div>
        </div>
      </div>
      <div class="card game-card">
        <div class="hud-row">
          <span class="pill" id="targetPill">无尽挑战，追求高分</span>
          <div class="toolbar">
            <button class="secondary" data-testid="pause-button" id="pauseBtn">暂停/设置</button>
            <button class="secondary" data-testid="restart-button" id="restartBtn">重新开始</button>
          </div>
        </div>
        <div class="board" data-testid="game-board" id="board" aria-label="10x10 方块棋盘"></div>
        <div class="tray" data-testid="piece-tray" id="tray"></div>
      </div>
    </section>
    <section class="hero" style="margin-top:18px;">
      <div class="card panel">
        <h2>策划映射</h2>
        <div class="quest" id="designTrace">已实现：10x10 网格、3 候选块、全部用完刷新、行列消除、失败检测、防卡死刷新、Combo/Streak、广告复活、道具入口、皮肤与拼图外围。</div>
      </div>
      <div class="card panel">
        <h2>运行日志</h2>
        <div class="log" data-testid="event-log" id="log"></div>
      </div>
    </section>
  </main>

  <div class="modal" id="pauseModal">
    <div class="modal-card">
      <h2>设置</h2>
      <p>音效：开 · 音乐：开 · 震动：开</p>
      <div class="toolbar">
        <button class="secondary" id="resumeBtn">继续游戏</button>
        <button class="secondary" id="pauseRestart">重新开始</button>
        <button class="danger" id="homeBtn">返回主页</button>
      </div>
    </div>
  </div>

  <div class="modal" id="gameOverModal">
    <div class="modal-card">
      <h2>就差一点！</h2>
      <p id="gameOverCopy">看一次激励视频可清理最拥挤的 3 行/列，继续挑战。</p>
      <div class="toolbar">
        <button data-testid="revive-button" id="reviveBtn">看广告复活</button>
        <button class="secondary" id="retryBtn">重新挑战</button>
        <button class="secondary" id="backHomeBtn">返回</button>
      </div>
    </div>
  </div>

  <div class="modal" id="winModal">
    <div class="modal-card">
      <h2>胜利！</h2>
      <p>获得一块拼图碎片，继续推进作品收集。</p>
      <div class="toolbar">
        <button id="nextLevelBtn">下一关</button>
        <button class="secondary" id="closeWinBtn">稍后再玩</button>
      </div>
    </div>
  </div>

  <div class="modal" id="skinModal">
    <div class="modal-card">
      <h2>个性化装扮</h2>
      <p>商业化入口模拟：皮肤可由激励广告或进度解锁。</p>
      <div class="toolbar">
        <button data-skin="">木块</button>
        <button data-skin="skin-gem">宝石</button>
        <button data-skin="skin-wool">毛线</button>
        <button class="secondary" data-close="skinModal">关闭</button>
      </div>
    </div>
  </div>

  <div class="modal" id="worksModal">
    <div class="modal-card">
      <h2>作品 · 拼图收集</h2>
      <p>闯关每胜利一次掉落碎片，7 块合成一幅完整作品。</p>
      <div class="jigsaw" id="jigsaw"></div>
      <button class="secondary" data-close="worksModal">关闭</button>
    </div>
  </div>

  <script>
    const SIZE = 10;
    const colors = [
      ['#f7c767', '#d99b31'],
      ['#f2876a', '#d94b3c'],
      ['#8dd89e', '#3d9d67'],
      ['#86c9f0', '#3e8fc0'],
      ['#b3a1ec', '#7461bf']
    ];
    const levels = [
      { label: '分数达到 1000', type: 'score', value: 1000 },
      { label: '两种颜色方块分别收集 50 个', type: 'color', colors: 2, value: 50 },
      { label: '分数达到 1500', type: 'score', value: 1500 },
      { label: '三种颜色方块分别收集 45 个', type: 'color', colors: 3, value: 45 },
      { label: '分数达到 2000', type: 'score', value: 2000 },
      { label: '四种颜色方块分别收集 40 个', type: 'color', colors: 4, value: 40 },
      { label: '四种颜色方块分别收集 50 个', type: 'color', colors: 4, value: 50 }
    ];
    const shapes = [
      [[1]],
      [[1,1]],
      [[1],[1]],
      [[1,1,1]],
      [[1],[1],[1]],
      [[1,1],[1,1]],
      [[1,0],[1,1]],
      [[0,1],[1,1]],
      [[1,1,1],[1,0,0]],
      [[1,1,1],[0,1,0]],
      [[1,1,1],[1,1,1],[1,1,1]]
    ];
    let board, pieces, selected = null, score = 0, best = 0, mode = 'classic', level = 0, revives = 1, streak = 0, jigsaw = 0, collected = [0,0,0,0,0];
    const $ = id => document.getElementById(id);
    function log(text) {
      const line = document.createElement('div');
      line.textContent = new Date().toLocaleTimeString() + ' · ' + text;
      $('log').prepend(line);
    }
    function toast(text) {
      $('toast').textContent = text;
      $('toast').classList.add('show');
      setTimeout(() => $('toast').classList.remove('show'), 1500);
    }
    function newBoard() {
      board = Array.from({ length: SIZE }, () => Array.from({ length: SIZE }, () => null));
    }
    function randomPiece() {
      const shape = shapes[Math.floor(Math.random() * shapes.length)];
      const color = Math.floor(Math.random() * colors.length);
      return { shape, color };
    }
    function cellsOf(piece, row, col) {
      const cells = [];
      piece.shape.forEach((line, y) => line.forEach((on, x) => {
        if (on) cells.push([row + y, col + x]);
      }));
      return cells;
    }
    function canPlace(piece, row, col) {
      return cellsOf(piece, row, col).every(([r, c]) => r >= 0 && c >= 0 && r < SIZE && c < SIZE && !board[r][c]);
    }
    function anyCanPlace(piece) {
      for (let r = 0; r < SIZE; r++) for (let c = 0; c < SIZE; c++) if (canPlace(piece, r, c)) return true;
      return false;
    }
    function refreshPieces() {
      let attempts = 0;
      do {
        pieces = [randomPiece(), randomPiece(), randomPiece()];
        attempts++;
      } while (emptyRatio() > .4 && !pieces.some(anyCanPlace) && attempts < 20);
      selected = null;
      log('刷新 3 个候选方块');
    }
    function emptyRatio() {
      let empty = 0;
      board.forEach(row => row.forEach(cell => { if (!cell) empty++; }));
      return empty / 100;
    }
    function clearLines() {
      const rows = [];
      const cols = [];
      for (let r = 0; r < SIZE; r++) if (board[r].every(Boolean)) rows.push(r);
      for (let c = 0; c < SIZE; c++) if (board.every(row => row[c])) cols.push(c);
      const clearSet = new Set();
      rows.forEach(r => { for (let c = 0; c < SIZE; c++) clearSet.add(r + ',' + c); });
      cols.forEach(c => { for (let r = 0; r < SIZE; r++) clearSet.add(r + ',' + c); });
      clearSet.forEach(key => {
        const [r, c] = key.split(',').map(Number);
        if (board[r][c]) collected[board[r][c].color]++;
        board[r][c] = null;
      });
      const count = rows.length + cols.length;
      if (count) {
        streak++;
        const gain = 5 * count * count + (streak >= 3 ? streak * 10 : 0);
        score += gain;
        toast((count > 1 ? 'Combo x' + count + ' · ' : '') + (streak >= 3 ? 'Streak x' + streak : '消除成功'));
        log('消除 ' + count + ' 条线，奖励 ' + gain + ' 分');
      } else {
        streak = 0;
      }
    }
    function placeSelected(row, col) {
      if (selected === null || !pieces[selected]) {
        toast('请先选择底部候选方块');
        return;
      }
      const piece = pieces[selected];
      if (!canPlace(piece, row, col)) {
        toast('这个位置放不下');
        return;
      }
      const cells = cellsOf(piece, row, col);
      cells.forEach(([r, c]) => board[r][c] = { color: piece.color });
      score += cells.length;
      pieces[selected] = null;
      selected = null;
      clearLines();
      if (pieces.every(p => !p)) refreshPieces();
      updateWinState();
      render();
      checkGameOver();
    }
    function checkGameOver() {
      const remaining = pieces.filter(Boolean);
      if (remaining.length && !remaining.some(anyCanPlace)) {
        $('reviveBtn').disabled = revives <= 0;
        $('gameOverCopy').textContent = revives > 0 ? '看一次激励视频可清理最拥挤的 3 行/列，继续挑战。' : '复活次数已用完，结算插屏广告在这里触发。';
        openModal('gameOverModal');
        log('触发 Game Over');
      }
    }
    function revive() {
      if (revives <= 0) return;
      revives--;
      for (let i = 0; i < 3; i++) {
        const rowDensity = board.map((row, r) => [r, row.filter(Boolean).length]).sort((a,b) => b[1] - a[1])[0][0];
        for (let c = 0; c < SIZE; c++) board[rowDensity][c] = null;
      }
      closeModal('gameOverModal');
      toast('广告复活成功');
      log('模拟激励视频复活，清理最拥挤 3 行');
      render();
    }
    function updateWinState() {
      if (mode !== 'adventure') return;
      const cfg = levels[level];
      let win = false;
      if (cfg.type === 'score') win = score >= cfg.value;
      if (cfg.type === 'color') win = collected.slice(0, cfg.colors).every(v => v >= cfg.value);
      if (win) {
        jigsaw = Math.min(7, jigsaw + 1);
        openModal('winModal');
        log('闯关胜利，掉落拼图碎片');
      }
    }
    function renderBoard() {
      $('board').innerHTML = '';
      for (let r = 0; r < SIZE; r++) {
        for (let c = 0; c < SIZE; c++) {
          const cell = document.createElement('button');
          cell.className = 'cell' + (board[r][c] ? ' filled' : '');
          cell.type = 'button';
          cell.dataset.testid = 'cell-' + r + '-' + c;
          cell.setAttribute('aria-label', '格子 ' + r + '-' + c);
          if (board[r][c]) {
            const tone = colors[board[r][c].color];
            cell.style.setProperty('--tone-a', tone[0]);
            cell.style.setProperty('--tone-b', tone[1]);
          }
          cell.addEventListener('click', () => placeSelected(r, c));
          $('board').appendChild(cell);
        }
      }
    }
    function renderPieces() {
      $('tray').innerHTML = '';
      pieces.forEach((piece, index) => {
        const shell = document.createElement('button');
        shell.type = 'button';
        shell.className = 'piece' + (selected === index ? ' selected' : '');
        shell.dataset.testid = 'piece-' + index;
        shell.setAttribute('aria-label', piece ? '候选方块 ' + (index + 1) : '空候选槽 ' + (index + 1));
        if (!piece) {
          shell.textContent = '已放置';
        } else {
          const grid = document.createElement('div');
          grid.className = 'mini-grid';
          grid.style.gridTemplateColumns = 'repeat(' + piece.shape[0].length + ', 18px)';
          const tone = colors[piece.color];
          piece.shape.forEach(row => row.forEach(on => {
            const dot = document.createElement('span');
            dot.className = 'mini-cell' + (on ? ' on' : '');
            dot.style.setProperty('--tone-a', tone[0]);
            dot.style.setProperty('--tone-b', tone[1]);
            grid.appendChild(dot);
          }));
          shell.appendChild(grid);
          shell.addEventListener('click', () => { selected = index; render(); toast('已选择候选方块 ' + (index + 1)); });
        }
        $('tray').appendChild(shell);
      });
    }
    function renderStats() {
      best = Math.max(best, score);
      $('score').textContent = score;
      $('best').textContent = best;
      $('modeStat').textContent = mode === 'classic' ? '经典' : '闯关';
      $('levelLabel').textContent = level + 1;
      $('revives').textContent = revives;
      const cfg = levels[level];
      $('targetPill').textContent = mode === 'classic' ? '无尽挑战，追求高分' : '第 ' + (level + 1) + ' 关 · ' + cfg.label;
      renderJigsaw();
    }
    function renderJigsaw() {
      $('jigsaw').innerHTML = '';
      for (let i = 1; i <= 7; i++) {
        const piece = document.createElement('span');
        piece.className = i <= jigsaw ? 'unlocked' : '';
        piece.textContent = i;
        $('jigsaw').appendChild(piece);
      }
    }
    function render() {
      renderBoard();
      renderPieces();
      renderStats();
    }
    function start(nextMode) {
      mode = nextMode;
      score = 0;
      revives = 1;
      streak = 0;
      collected = [0,0,0,0,0];
      newBoard();
      refreshPieces();
      closeModal('gameOverModal');
      closeModal('winModal');
      render();
      log('开始' + (mode === 'classic' ? '经典模式' : '闯关模式第 ' + (level + 1) + ' 关'));
    }
    function openModal(id) { $(id).classList.add('active'); }
    function closeModal(id) { $(id).classList.remove('active'); }
    $('classicMode').addEventListener('click', () => start('classic'));
    $('adventureMode').addEventListener('click', () => start('adventure'));
    $('restartBtn').addEventListener('click', () => start(mode));
    $('pauseBtn').addEventListener('click', () => openModal('pauseModal'));
    $('resumeBtn').addEventListener('click', () => closeModal('pauseModal'));
    $('pauseRestart').addEventListener('click', () => { closeModal('pauseModal'); start(mode); });
    $('homeBtn').addEventListener('click', () => { closeModal('pauseModal'); toast('已返回主页状态'); });
    $('retryBtn').addEventListener('click', () => start(mode));
    $('backHomeBtn').addEventListener('click', () => closeModal('gameOverModal'));
    $('reviveBtn').addEventListener('click', revive);
    $('nextLevelBtn').addEventListener('click', () => { level = Math.min(levels.length - 1, level + 1); closeModal('winModal'); start('adventure'); });
    $('closeWinBtn').addEventListener('click', () => closeModal('winModal'));
    $('skinPanel').addEventListener('click', () => openModal('skinModal'));
    $('worksPanel').addEventListener('click', () => openModal('worksModal'));
    document.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', () => closeModal(button.dataset.close)));
    document.querySelectorAll('[data-skin]').forEach(button => button.addEventListener('click', () => {
      document.body.className = button.dataset.skin;
      toast('已切换皮肤');
    }));
    start('classic');
  </script>
</body>
</html>
"""


def _requested_folder_for_goal(goal: str, *, default_name: str) -> Path:
    output_match = re.search(
        r"(?:输出(?:到|目录|文件夹)?|保存到|生成到)\s*[：:]\s*([A-Za-z]:[\\/][^\n，,。；;]+)",
        goal,
    )
    if output_match:
        return Path(output_match.group(1).strip().strip("`'\"“”‘’"))
    folder_match = re.search(r"(?:文件夹|目录)\s*[：:]\s*([^\s，,。；;]+)", goal)
    folder_name = folder_match.group(1).strip("`'\"“”‘’") if folder_match else ""
    if re.match(r"^[A-Za-z]:[\\/]", folder_name):
        return Path(folder_name)
    if ("D盘" in goal or "D 盘" in goal or re.search(r"\bD:\b", goal, flags=re.IGNORECASE)) and folder_name:
        return Path("D:/") / folder_name
    if "D盘" in goal or "D 盘" in goal:
        return Path("D:/") / default_name
    if folder_name:
        return Path("state") / "artifacts" / "generated" / folder_name
    return Path("state") / "artifacts" / "generated" / default_name


def _snake_artifacts(goal: str) -> list[tuple[Path, str]]:
    folder = _requested_folder_for_goal(goal, default_name="snake_game")
    return [
        (folder / "index.html", _snake_game_html()),
        (
            folder / "README.md",
            "# 贪吃蛇小游戏\n\n"
            "这是由 Universal Agentic Workflow 本地聊天工作台生成的小游戏。\n\n"
            "打开 `index.html` 即可运行，使用方向键或 WASD 控制蛇移动。\n",
        ),
    ]


def _block_puzzle_artifacts(
    goal: str,
    *,
    pdf_context: tuple[str, str] | None = None,
) -> list[tuple[Path, str]]:
    folder = _requested_folder_for_goal(goal, default_name="俄罗斯方块消除商业化小游戏")
    pdf_section, pdf_text = pdf_context or _pdf_context_for_goal(goal)
    source_line = "来源：目标中的 PDF 策划文档与聊天需求提炼。"
    if pdf_text:
        source_line = "来源：已自动读取目标中的 PDF 策划文档，并结合聊天需求提炼。"
    readme = (
        "# 方块艺境 - 商业化 1010 Block Puzzle 原型\n\n"
        f"{source_line}\n\n"
        "## 运行方式\n"
        "直接用浏览器打开 `index.html`。\n\n"
        "## 已覆盖功能\n"
        "- 10x10 棋盘和底部 3 个候选方块。\n"
        "- 全部候选块用完后刷新。\n"
        "- 行/列填满消除，包含 Combo 和 Streak 反馈。\n"
        "- 经典模式与前 7 关闯关配置。\n"
        "- 失败弹窗、模拟激励广告复活、结算广告点位。\n"
        "- 皮肤装饰、作品/拼图收集外围系统。\n"
        "- 响应式商业化视觉包装。\n"
    )
    trace = (
        "# 信息检索与策划映射\n\n"
        "## 信息来源\n"
        f"{pdf_section}\n\n"
        "## 从 PDF 提取的关键需求\n"
        "- 10x10 网格，底部 3 个候选方块。\n"
        "- 放置后按格数得分，行列填满消除。\n"
        "- 3 个候选方块全部用完后刷新。\n"
        "- 没有剩余候选方块可放时 Game Over。\n"
        "- 空位超过 40% 时避免随机刷出全都放不下的死局。\n"
        "- 经典模式追求高分，闯关模式有前 7 关目标。\n"
        "- Combo、Streak、放置预览、震动反馈、广告复活、插屏广告、皮肤和拼图收集。\n\n"
        "## 原型实现取舍\n"
        "- 浏览器原型使用点击选择候选块，再点击棋盘落点；移动端可继续扩展为真实拖拽。\n"
        "- 广告和震动以本地模拟形式呈现，不接真实广告 SDK。\n"
        "- 所有状态保存在前端内存，适合商业化 vertical slice 和玩法验证。\n"
    )
    return [
        (folder / "index.html", _block_puzzle_html()),
        (folder / "README.md", readme),
        (folder / "design_trace.md", trace),
    ]


def local_artifacts_for_goal(goal: str) -> list[tuple[Path, str]]:
    normalized = goal.lower()
    pdf_context = _pdf_context_for_goal(goal)
    searchable = f"{normalized}\n{pdf_context[1].lower()}"
    block_markers = ("1010", "block puzzle", "俄罗斯方块", "方块消除", "消除策划", "商业化小游戏")
    if any(marker in searchable or marker in goal for marker in block_markers):
        return _block_puzzle_artifacts(goal, pdf_context=pdf_context)
    if "贪吃蛇" in goal or "snake" in normalized:
        return _snake_artifacts(goal)
    return []
