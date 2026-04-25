from __future__ import annotations

from packages.contributions.games.local_game_arcade_scripts import _block_puzzle_html_suffix


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
    return _block_puzzle_html_prefix() + _block_puzzle_html_suffix()


def _block_puzzle_html_prefix() -> str:
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
      touch-action: none;
      position: relative;
      isolation: isolate;
    }
    .board.drag-active {
      box-shadow: inset 0 0 0 2px rgba(255, 225, 148, .36), 0 24px 62px rgba(0,0,0,.3);
    }
    .cell {
      aspect-ratio: 1;
      border-radius: 10px;
      background: var(--cell);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,.1);
      transition: transform .12s ease, background .12s ease;
      position: relative;
      overflow: hidden;
    }
    .cell::after {
      content: "";
      position: absolute;
      inset: 12%;
      border-radius: 8px;
      opacity: 0;
      transform: scale(.7);
      transition: opacity .12s ease, transform .12s ease;
    }
    .cell.filled {
      background: linear-gradient(135deg, var(--tone-a), var(--tone-b));
      box-shadow: inset 0 2px 5px rgba(255,255,255,.35), 0 6px 12px rgba(0,0,0,.16);
    }
    .cell.preview-ok { background: rgba(78,168,123,.34); transform: scale(.96); }
    .cell.preview-ok::after { opacity: 1; transform: scale(1); background: rgba(126, 226, 162, .72); }
    .cell.preview-bad { background: rgba(233,107,75,.42); transform: scale(.92); }
    .cell.preview-bad::after { opacity: 1; transform: scale(1); background: rgba(255, 113, 88, .72); }
    .cell.clear-flash { animation: clearFlash .34s ease; }
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
      cursor: grab;
      touch-action: none;
      position: relative;
      box-shadow: inset 0 0 0 1px rgba(255,255,255,.52), 0 14px 30px rgba(71,42,16,.12);
    }
    .piece:active { cursor: grabbing; }
    .piece.selected { border-color: var(--gold); box-shadow: 0 0 0 5px rgba(214,168,79,.18); }
    .piece.dragging { opacity: .55; transform: scale(.97); border-color: var(--jade); }
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
    .drag-ghost {
      position: fixed;
      left: 0;
      top: 0;
      z-index: 30;
      pointer-events: none;
      padding: 12px;
      border-radius: 22px;
      background: rgba(255, 250, 237, .86);
      border: 1px solid rgba(255,255,255,.7);
      box-shadow: 0 22px 70px rgba(44, 23, 10, .38);
      transform: translate(-999px, -999px);
      opacity: 0;
      transition: opacity .08s ease;
    }
    .drag-ghost.active { opacity: 1; }
    .drag-ghost .mini-cell { width: 22px; height: 22px; }
    .combo-banner {
      position: fixed;
      left: 50%;
      top: 16%;
      z-index: 22;
      transform: translate(-50%, 12px) scale(.88);
      opacity: 0;
      padding: 14px 22px;
      border-radius: 999px;
      background: linear-gradient(135deg, #fff1a6, #f06f4d);
      color: #4a240e;
      font-weight: 1000;
      letter-spacing: .03em;
      box-shadow: 0 24px 80px rgba(84, 38, 10, .28);
      pointer-events: none;
    }
    .combo-banner.show { animation: comboPop .9s ease; }
    .power-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin-top: 12px;
    }
    .power-card {
      border-radius: 18px;
      padding: 12px;
      background: rgba(255,255,255,.54);
      border: 1px solid rgba(120,77,32,.12);
      text-align: left;
      color: #4d3320;
      min-height: 82px;
    }
    .power-card strong { display: block; font-size: 14px; }
    .power-card span { display: block; margin-top: 4px; color: var(--muted); font-size: 12px; line-height: 1.35; }
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
    body.skin-night {
      --panel: rgba(232, 244, 255, .86);
      --ink: #15202b;
      --muted: #566675;
      background:
        radial-gradient(circle at 16% 14%, rgba(109, 211, 255, .28), transparent 28%),
        radial-gradient(circle at 86% 24%, rgba(255, 211, 110, .22), transparent 24%),
        linear-gradient(135deg, #121c2e 0%, #28435e 48%, #76a8c7 100%);
    }
    @keyframes comboPop {
      0% { opacity: 0; transform: translate(-50%, 18px) scale(.82); }
      22% { opacity: 1; transform: translate(-50%, 0) scale(1.08); }
      72% { opacity: 1; transform: translate(-50%, -8px) scale(1); }
      100% { opacity: 0; transform: translate(-50%, -24px) scale(.96); }
    }
    @keyframes clearFlash {
      0% { filter: brightness(1); transform: scale(1); }
      45% { filter: brightness(1.8); transform: scale(1.08); }
      100% { filter: brightness(1); transform: scale(1); }
    }
    @media (max-width: 920px) {
      .hero { grid-template-columns: 1fr; }
      .stats { grid-template-columns: repeat(2, 1fr); }
      .power-row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="toast" id="toast">提示</div>
  <div class="combo-banner" data-testid="combo-banner" id="comboBanner">Combo!</div>
  <div class="drag-ghost" data-testid="drag-ghost" id="dragGhost" aria-hidden="true"></div>
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
        <p class="subtitle" style="font-size:13px;margin:10px 0 12px;">拖拽底部方块到棋盘，绿色为可放，红色为不可放；手机上会显示上移 ghost，避免手指遮挡。</p>
        <div class="tray" data-testid="piece-tray" id="tray"></div>
        <div class="power-row" data-testid="booster-row">
          <button class="power-card" data-testid="booster-refresh" id="boosterRefresh"><strong>刷新方块 <b id="boostRefreshCount">1</b></strong><span>替换一个候选块，模拟激励广告道具。</span></button>
          <button class="power-card" data-testid="booster-line" id="boosterLine"><strong>横竖消除 <b id="boostLineCount">1</b></strong><span>清理最拥挤的一行或一列。</span></button>
          <button class="power-card" data-testid="booster-shuffle" id="boosterShuffle"><strong>打乱重排 <b id="boostShuffleCount">1</b></strong><span>重排棋盘占用格，给残局续命。</span></button>
        </div>
      </div>
    </section>
    <section class="hero" style="margin-top:18px;">
      <div class="card panel">
        <h2>策划映射</h2>
        <div class="quest" id="designTrace">已实现：10x10 网格、3 候选块、真实拖拽/触控拖动、上移 ghost、防遮挡、绿色/红色放置预览、行列消除、失败检测、防卡死刷新、Combo/Streak、广告复活、插屏点位、道具、皮肤/背景/棋盘装饰与拼图外围。</div>
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
        <button data-skin="skin-night">夜空棋盘</button>
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
"""
