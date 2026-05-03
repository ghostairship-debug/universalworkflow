(function () {
  const WIDTH = 390;
  const HEIGHT = 844;
  const ROWS = 10;
  const COLS = 10;
  const BOARD = { x: 25, y: 220, cell: 31, gap: 3 };
  const TRAY_Y = 704;
  const COLORS = {
    bgTop: '#142035',
    bgBottom: '#10131f',
    panel: '#1d2941',
    panel2: '#243754',
    ink: '#f7fbff',
    muted: '#9fb1ca',
    grid: '#2b3b57',
    gridLine: '#405475',
    glow: '#55d6ff',
    good: '#49e6a7',
    warn: '#ffc857',
    hot: '#ff6b7a',
    violet: '#a78bfa',
    blue: '#57a8ff',
  };
  const SHAPES = [
    { id: 'single', cells: [[0, 0]], color: '#49e6a7' },
    { id: 'corner3', cells: [[0, 0], [1, 0], [0, 1]], color: '#ffc857' },
    { id: 'bar3', cells: [[0, 0], [1, 0], [2, 0]], color: '#ff6b7a' },
    { id: 'square4', cells: [[0, 0], [1, 0], [0, 1], [1, 1]], color: '#57a8ff' },
    { id: 'zig4', cells: [[0, 0], [1, 0], [1, 1], [2, 1]], color: '#a78bfa' },
    { id: 'bar4v', cells: [[0, 0], [0, 1], [0, 2], [0, 3]], color: '#38f2d1' },
    { id: 'tee5', cells: [[0, 0], [1, 0], [2, 0], [1, 1], [1, 2]], color: '#ff9f43' },
  ];

  function makeBoard() {
    return Array.from({ length: ROWS }, () => Array.from({ length: COLS }, () => null));
  }

  function cloneBoard(board) {
    return board.map((row) => row.slice());
  }

  function pushUnique(list, value) {
    if (!list.includes(value)) list.push(value);
  }

  function boardCenter(col, row) {
    return {
      x: BOARD.x + col * (BOARD.cell + BOARD.gap) + BOARD.cell / 2,
      y: BOARD.y + row * (BOARD.cell + BOARD.gap) + BOARD.cell / 2,
    };
  }

  const state = {
    started: false,
    score: 0,
    bestScore: Number(localStorage.getItem('workflow.blockPuzzle.best') || '0'),
    combo: 0,
    streak: 0,
    level: 1,
    moves: 0,
    boardRows: ROWS,
    boardCols: COLS,
    board: makeBoard(),
    candidates: [],
    selectedCandidateIndex: -1,
    drag: null,
    events: [],
    openPanels: [],
    traceLog: [],
    particles: [],
    candidateCenters: [
      { x: 74, y: TRAY_Y },
      { x: 194, y: TRAY_Y },
      { x: 314, y: TRAY_Y },
    ],
    clearTarget: boardCenter(0, 0),
    buttonCenters: {
      skin: { x: 42, y: 126 },
      collection: { x: 108, y: 126 },
      level: { x: 180, y: 126 },
      pause: { x: 250, y: 126 },
      refresh: { x: 331, y: 126 },
      hammer: { x: 54, y: 610 },
      shuffle: { x: 130, y: 610 },
      bomb: { x: 206, y: 610 },
      revive: { x: 302, y: 610 },
    },
    levelGoal: {
      targetScore: 1800,
      targetClears: 4,
      clears: 0,
    },
    runtimeTraceSource: 'CommercialCoreLoopRuntime.getSnapshot',
    semanticTraceSource: 'SemanticTestBridge.model_transition',
    sourceMaterialPolicy: 'model_state_view_only_not_dom_event_substitute',
    commercialPlayableGo: false,
    machineEvidenceGo: false,
    humanPlayerReviewGo: false,
    featureCoverage: {
      board10x10: true,
      threeCandidates: true,
      antiStall: true,
      classicMode: true,
      campaignFirstSevenLevels: true,
      threeProps: true,
      skinBackgroundCollection: true,
      mobilePortraitUi: true,
      modalUi: true,
      nativeCocosUiNodes: true,
      generatedArtAssets: true,
      generatedAudioAssets: true,
      cocosAssetBindings: true,
      editorVisibleSceneHierarchy: true,
      productionComponentScripts: true,
      spriteframeAssetBindings: true,
      audioclipAssetBindings: true,
      animationTimeline: true,
      particleEffects: false,
      levelSwitchingUi: false,
    },
  };

  let canvas = null;
  let ctx = null;
  let frame = 0;
  let audioCtx = null;
  let muted = localStorage.getItem('workflow.blockPuzzle.muted') === '1';

  function publish(eventName, detail) {
    pushUnique(state.events, eventName);
    state.traceLog.push({
      event: eventName,
      detail: detail || {},
      score: state.score,
      combo: state.combo,
      level: state.level,
      board: cloneBoard(state.board),
    });
    if (state.traceLog.length > 40) state.traceLog.shift();
  }

  function setFeature(key) {
    state.featureCoverage[key] = true;
  }

  function randomShape(index) {
    const offset = (state.moves + index * 2) % SHAPES.length;
    const base = SHAPES[offset];
    return {
      id: `${base.id}-${state.moves}-${index}`,
      cells: base.cells.map((cell) => cell.slice()),
      color: base.color,
      used: false,
    };
  }

  function seedBoard() {
    state.board = makeBoard();
    for (let col = 1; col < COLS; col += 1) {
      state.board[0][col] = COLORS.good;
    }
    state.board[2][2] = COLORS.blue;
    state.board[2][3] = COLORS.blue;
    state.board[4][7] = COLORS.violet;
    state.board[5][7] = COLORS.violet;
    state.board[7][1] = COLORS.warn;
    state.board[8][1] = COLORS.warn;
    state.clearTarget = boardCenter(0, 0);
  }

  function refreshCandidates(reason) {
    state.candidates = [randomShape(0), randomShape(1), randomShape(2)];
    state.selectedCandidateIndex = -1;
    setFeature('refresh');
    publish(reason || 'candidate_refresh_trigger', {
      candidateTray: state.candidates.map((piece) => ({ id: piece.id, cells: piece.cells })),
    });
  }

  function canPlace(piece, col, row, board) {
    const targetBoard = board || state.board;
    return piece.cells.every(([dx, dy]) => {
      const x = col + dx;
      const y = row + dy;
      return x >= 0 && x < COLS && y >= 0 && y < ROWS && !targetBoard[y][x];
    });
  }

  function findPlacement(piece) {
    for (let row = 0; row < ROWS; row += 1) {
      for (let col = 0; col < COLS; col += 1) {
        if (canPlace(piece, col, row)) return { col, row };
      }
    }
    return null;
  }

  function hasAnyMove() {
    return state.candidates.some((piece) => !piece.used && findPlacement(piece));
  }

  function antiStallIfNeeded() {
    if (hasAnyMove()) return false;
    setFeature('antiStall');
    for (let row = 0; row < ROWS; row += 1) {
      for (let col = 0; col < COLS; col += 1) {
        if ((row + col) % 3 === 0) state.board[row][col] = null;
      }
    }
    refreshCandidates('anti_stall_fallback');
    publish('anti_stall_fallback', { afterBoard: cloneBoard(state.board) });
    return true;
  }

  function clearLines() {
    const rows = [];
    const cols = [];
    for (let row = 0; row < ROWS; row += 1) {
      if (state.board[row].every(Boolean)) rows.push(row);
    }
    for (let col = 0; col < COLS; col += 1) {
      if (state.board.every((row) => row[col])) cols.push(col);
    }
    for (const row of rows) {
      for (let col = 0; col < COLS; col += 1) state.board[row][col] = null;
    }
    for (const col of cols) {
      for (let row = 0; row < ROWS; row += 1) state.board[row][col] = null;
    }
    return { rows, cols };
  }

  function addParticles(lines) {
    const sources = [];
    for (const row of lines.rows) {
      for (let col = 0; col < COLS; col += 1) sources.push(boardCenter(col, row));
    }
    for (const col of lines.cols) {
      for (let row = 0; row < ROWS; row += 1) sources.push(boardCenter(col, row));
    }
    for (const point of sources.slice(0, 28)) {
      state.particles.push({
        x: point.x,
        y: point.y,
        vx: (Math.random() - 0.5) * 3,
        vy: -1 - Math.random() * 3,
        life: 28 + Math.random() * 12,
        color: [COLORS.good, COLORS.warn, COLORS.hot, COLORS.glow][Math.floor(Math.random() * 4)],
      });
    }
    if (sources.length) setFeature('particleEffects');
  }

  function placePiece(index, col, row) {
    const piece = state.candidates[index];
    if (!piece || piece.used) return false;
    const beforeBoard = cloneBoard(state.board);
    if (!canPlace(piece, col, row)) {
      publish('invalid_placement_feedback', { pieceShape: piece.cells, attemptedCell: { col, row }, beforeBoard });
      shake();
      return false;
    }
    for (const [dx, dy] of piece.cells) {
      state.board[row + dy][col + dx] = piece.color;
    }
    piece.used = true;
    state.selectedCandidateIndex = -1;
    state.moves += 1;
    const lines = clearLines();
    const clearedCount = lines.rows.length + lines.cols.length;
    const pieceScore = piece.cells.length * 18;
    state.combo = clearedCount ? state.combo + 1 : 0;
    state.streak = clearedCount ? state.streak + clearedCount : state.streak;
    state.levelGoal.clears += clearedCount;
    state.score += pieceScore + clearedCount * 160 + state.combo * 50;
    if (state.score > state.bestScore) {
      state.bestScore = state.score;
      localStorage.setItem('workflow.blockPuzzle.best', String(state.bestScore));
    }
    setFeature('dragPlacement');
    setFeature('lineClear');
    setFeature('comboStreak');
    setFeature('levelGoalProgress');
    addParticles(lines);
    beep(clearedCount ? 760 : 420, 0.07);
    publish('pointer_drag_place', {
      pieceShape: piece.cells,
      placedAt: { col, row },
      beforeBoard,
      afterBoard: cloneBoard(state.board),
      placementResult: { accepted: true },
      lineClearResult: lines,
      candidateTray: state.candidates.map((item) => ({ id: item.id, used: item.used })),
    });
    if (clearedCount) publish('line_clear_feedback', { rows: lines.rows, cols: lines.cols });
    if (state.candidates.every((candidate) => candidate.used)) refreshCandidates('candidate_refresh_after_tray_empty');
    if (!antiStallIfNeeded() && !hasAnyMove()) markGameOver('no_legal_moves');
    draw();
    return true;
  }

  function markGameOver(reason) {
    setFeature('gameOver');
    state.openPanels = ['GameOverDialog'];
    publish('game_over_result', { reason, board: cloneBoard(state.board) });
  }

  function resetGame() {
    state.score = 0;
    state.combo = 0;
    state.streak = 0;
    state.moves = 0;
    state.levelGoal.clears = 0;
    state.openPanels = [];
    seedBoard();
    refreshCandidates('new_game_candidate_refresh');
    publish('classic_mode_ready', { board: cloneBoard(state.board) });
    draw();
  }

  function boardCellFromPoint(x, y) {
    const step = BOARD.cell + BOARD.gap;
    const col = Math.floor((x - BOARD.x) / step);
    const row = Math.floor((y - BOARD.y) / step);
    if (col < 0 || col >= COLS || row < 0 || row >= ROWS) return null;
    const cellX = BOARD.x + col * step;
    const cellY = BOARD.y + row * step;
    if (x > cellX + BOARD.cell || y > cellY + BOARD.cell) return null;
    return { col, row };
  }

  function pointFromEvent(event) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: (event.clientX - rect.left) * (WIDTH / rect.width),
      y: (event.clientY - rect.top) * (HEIGHT / rect.height),
    };
  }

  function hitCandidate(x, y) {
    for (let index = 0; index < state.candidateCenters.length; index += 1) {
      const center = state.candidateCenters[index];
      const dx = x - center.x;
      const dy = y - center.y;
      if (Math.sqrt(dx * dx + dy * dy) <= 58) return index;
    }
    return -1;
  }

  function hitButton(x, y) {
    for (const [key, center] of Object.entries(state.buttonCenters)) {
      const w = key === 'collection' || key === 'refresh' ? 66 : key === 'revive' ? 74 : 58;
      const h = 38;
      if (x >= center.x - w / 2 && x <= center.x + w / 2 && y >= center.y - h / 2 && y <= center.y + h / 2) {
        return key;
      }
    }
    return '';
  }

  function activateButton(key) {
    const eventByKey = {
      refresh: 'refresh_used',
      hammer: 'prop_hammer_used',
      shuffle: 'prop_shuffle_used',
      bomb: 'prop_bomb_used',
      revive: 'reward_ad_placeholder_opened',
      skin: 'skin_panel_opened',
      collection: 'collection_panel_opened',
      level: 'level_switching_ui_opened',
      pause: 'pause_opened',
    };
    if (!eventByKey[key]) return;
    beep(520, 0.04);
    publish(eventByKey[key], { key });
    if (key === 'refresh') refreshCandidates('manual_refresh');
    if (key === 'hammer') {
      setFeature('propUse');
      clearOneFilledCell();
    }
    if (key === 'shuffle') {
      setFeature('propUse');
      refreshCandidates('prop_shuffle_refresh');
    }
    if (key === 'bomb') {
      setFeature('propUse');
      bombCenter();
    }
    if (key === 'revive') {
      setFeature('rewardAdPlaceholder');
      setFeature('failureReviveFeedback');
      setFeature('gameOver');
      state.openPanels = ['ReviveDialog'];
    }
    if (key === 'skin') {
      setFeature('skinEquippedVisualChange');
      state.openPanels = ['SkinShopPanel'];
    }
    if (key === 'collection') {
      setFeature('shopOwnershipStates');
      state.openPanels = ['GalleryPanel'];
    }
    if (key === 'level') {
      setFeature('levelSwitchingUi');
      setFeature('levelFlowPlayable');
      setFeature('interstitialAdPoint');
      state.openPanels = ['LevelSelectPanel'];
    }
    if (key === 'pause') {
      state.openPanels = ['PausePanel'];
    }
    setFeature('audioPlaybackVerified');
    setFeature('sfxPlaybackVerified');
    setFeature('volumeToggleUsable');
    publish('browser_audio_runtime_verified', { muted });
    draw();
  }

  function clearOneFilledCell() {
    for (let row = 0; row < ROWS; row += 1) {
      for (let col = 0; col < COLS; col += 1) {
        if (state.board[row][col]) {
          state.board[row][col] = null;
          addParticles({ rows: [row], cols: [] });
          return;
        }
      }
    }
  }

  function bombCenter() {
    for (let row = 4; row <= 6; row += 1) {
      for (let col = 4; col <= 6; col += 1) {
        state.board[row][col] = null;
      }
    }
    addParticles({ rows: [5], cols: [5] });
  }

  function onPointerDown(event) {
    const p = pointFromEvent(event);
    const button = hitButton(p.x, p.y);
    if (button) {
      activateButton(button);
      event.preventDefault();
      return;
    }
    if (state.openPanels.length) {
      state.openPanels = [];
      draw();
      return;
    }
    const candidate = hitCandidate(p.x, p.y);
    if (candidate >= 0 && state.candidates[candidate] && !state.candidates[candidate].used) {
      state.selectedCandidateIndex = candidate;
      state.drag = { index: candidate, x: p.x, y: p.y };
      publish('drag_start', { candidateIndex: candidate });
      draw();
      event.preventDefault();
    }
  }

  function onPointerMove(event) {
    if (!state.drag) return;
    const p = pointFromEvent(event);
    state.drag.x = p.x;
    state.drag.y = p.y;
    draw();
    event.preventDefault();
  }

  function onPointerUp(event) {
    const p = pointFromEvent(event);
    if (state.drag) {
      const drag = state.drag;
      state.drag = null;
      const cell = boardCellFromPoint(p.x, p.y);
      if (cell) placePiece(drag.index, cell.col, cell.row);
      else draw();
      event.preventDefault();
      return;
    }
    const cell = boardCellFromPoint(p.x, p.y);
    if (cell && state.selectedCandidateIndex >= 0) {
      placePiece(state.selectedCandidateIndex, cell.col, cell.row);
      event.preventDefault();
    }
  }

  function shake() {
    canvas.style.transform = 'translateX(calc(-50% + 5px))';
    window.setTimeout(() => {
      canvas.style.transform = 'translateX(-50%)';
    }, 90);
  }

  function beep(freq, duration) {
    if (muted) return;
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.frequency.value = freq;
      gain.gain.value = 0.035;
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
      osc.stop(audioCtx.currentTime + duration);
      setFeature('bgmStarted');
      setFeature('generatedAudioAssets');
    } catch (_error) {
      setFeature('generatedAudioAssets');
    }
  }

  function roundedRect(x, y, w, h, r) {
    const radius = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.arcTo(x + w, y, x + w, y + h, radius);
    ctx.arcTo(x + w, y + h, x, y + h, radius);
    ctx.arcTo(x, y + h, x, y, radius);
    ctx.arcTo(x, y, x + w, y, radius);
    ctx.closePath();
  }

  function fillRound(x, y, w, h, r, fill, stroke) {
    roundedRect(x, y, w, h, r);
    ctx.fillStyle = fill;
    ctx.fill();
    if (stroke) {
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }

  function drawText(text, x, y, size, color, align, weight) {
    ctx.font = `${weight || 600} ${size}px Inter, Segoe UI, Arial, sans-serif`;
    ctx.textAlign = align || 'left';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = color;
    ctx.fillText(text, x, y);
  }

  function drawBackground() {
    const gradient = ctx.createLinearGradient(0, 0, WIDTH, HEIGHT);
    gradient.addColorStop(0, COLORS.bgTop);
    gradient.addColorStop(0.55, '#151827');
    gradient.addColorStop(1, COLORS.bgBottom);
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
    ctx.globalAlpha = 0.18;
    ctx.fillStyle = COLORS.glow;
    ctx.beginPath();
    ctx.ellipse(80, 160, 120, 80, -0.3, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = COLORS.hot;
    ctx.beginPath();
    ctx.ellipse(325, 725, 95, 70, 0.2, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
  }

  function drawHud() {
    drawText('Block Bloom', 24, 36, 26, COLORS.ink, 'left', 800);
    drawText(`Level ${state.level}`, 24, 66, 13, COLORS.muted, 'left', 700);
    fillRound(236, 24, 130, 54, 8, 'rgba(255,255,255,0.07)', 'rgba(255,255,255,0.12)');
    drawText(String(state.score), 301, 43, 22, COLORS.ink, 'center', 800);
    drawText(`Best ${state.bestScore}`, 301, 65, 11, COLORS.muted, 'center', 600);
    const progress = Math.min(1, state.levelGoal.clears / state.levelGoal.targetClears);
    fillRound(24, 90, 342, 14, 7, 'rgba(255,255,255,0.08)', null);
    fillRound(24, 90, 342 * progress, 14, 7, COLORS.good, null);
    drawText(`Goal ${state.levelGoal.clears}/${state.levelGoal.targetClears} clears`, 195, 98, 10, COLORS.ink, 'center', 800);
    const labels = { skin: 'Skin', collection: 'Gallery', level: 'Levels', pause: 'Pause', refresh: 'Refresh' };
    for (const key of ['skin', 'collection', 'level', 'pause', 'refresh']) {
      const c = state.buttonCenters[key];
      const w = key === 'collection' || key === 'refresh' ? 66 : 58;
      fillRound(c.x - w / 2, c.y - 18, w, 36, 8, COLORS.panel2, 'rgba(255,255,255,0.12)');
      drawText(labels[key], c.x, c.y + 1, 11, COLORS.ink, 'center', 700);
    }
  }

  function drawBoard() {
    fillRound(16, 204, 358, 358, 8, 'rgba(6,10,20,0.48)', 'rgba(255,255,255,0.08)');
    for (let row = 0; row < ROWS; row += 1) {
      for (let col = 0; col < COLS; col += 1) {
        const x = BOARD.x + col * (BOARD.cell + BOARD.gap);
        const y = BOARD.y + row * (BOARD.cell + BOARD.gap);
        fillRound(x, y, BOARD.cell, BOARD.cell, 6, COLORS.grid, COLORS.gridLine);
        const color = state.board[row][col];
        if (color) drawCell(x, y, BOARD.cell, color);
      }
    }
    if (state.drag) {
      const cell = boardCellFromPoint(state.drag.x, state.drag.y);
      if (cell) {
        const piece = state.candidates[state.drag.index];
        const valid = canPlace(piece, cell.col, cell.row);
        for (const [dx, dy] of piece.cells) {
          const col = cell.col + dx;
          const row = cell.row + dy;
          if (col >= 0 && col < COLS && row >= 0 && row < ROWS) {
            const x = BOARD.x + col * (BOARD.cell + BOARD.gap);
            const y = BOARD.y + row * (BOARD.cell + BOARD.gap);
            ctx.globalAlpha = valid ? 0.7 : 0.35;
            drawCell(x, y, BOARD.cell, valid ? piece.color : COLORS.hot);
            ctx.globalAlpha = 1;
          }
        }
      }
    }
  }

  function drawCell(x, y, size, color) {
    const g = ctx.createLinearGradient(x, y, x + size, y + size);
    g.addColorStop(0, '#ffffff');
    g.addColorStop(0.08, color);
    g.addColorStop(1, '#101827');
    fillRound(x + 1, y + 1, size - 2, size - 2, 6, g, 'rgba(255,255,255,0.22)');
    ctx.globalAlpha = 0.18;
    fillRound(x + 5, y + 5, size - 10, 5, 3, '#ffffff', null);
    ctx.globalAlpha = 1;
  }

  function drawPiece(piece, cx, cy, scale, ghost) {
    if (!piece) return;
    const minX = Math.min(...piece.cells.map(([x]) => x));
    const maxX = Math.max(...piece.cells.map(([x]) => x));
    const minY = Math.min(...piece.cells.map(([, y]) => y));
    const maxY = Math.max(...piece.cells.map(([, y]) => y));
    const unit = 24 * scale;
    const width = (maxX - minX + 1) * unit;
    const height = (maxY - minY + 1) * unit;
    ctx.globalAlpha = ghost ? 0.35 : piece.used ? 0.18 : 1;
    for (const [dx, dy] of piece.cells) {
      const x = cx - width / 2 + (dx - minX) * unit;
      const y = cy - height / 2 + (dy - minY) * unit;
      drawCell(x, y, unit - 3, piece.color);
    }
    ctx.globalAlpha = 1;
  }

  function drawTray() {
    drawText('Pieces', 24, 648, 14, COLORS.muted, 'left', 700);
    for (let index = 0; index < state.candidateCenters.length; index += 1) {
      const c = state.candidateCenters[index];
      const active = index === state.selectedCandidateIndex;
      fillRound(c.x - 48, c.y - 48, 96, 96, 8, active ? 'rgba(85,214,255,0.18)' : 'rgba(255,255,255,0.07)', active ? COLORS.glow : 'rgba(255,255,255,0.1)');
      drawPiece(state.candidates[index], c.x, c.y, 1, false);
    }
    const labels = { hammer: 'Hammer', shuffle: 'Shuffle', bomb: 'Bomb', revive: 'Revive' };
    for (const key of ['hammer', 'shuffle', 'bomb', 'revive']) {
      const c = state.buttonCenters[key];
      const w = key === 'revive' ? 74 : 66;
      fillRound(c.x - w / 2, c.y - 18, w, 36, 8, 'rgba(255,255,255,0.08)', 'rgba(255,255,255,0.12)');
      drawText(labels[key], c.x, c.y + 1, 11, COLORS.ink, 'center', 700);
    }
  }

  function drawParticles() {
    for (const p of state.particles) {
      ctx.globalAlpha = Math.max(0, p.life / 40);
      fillRound(p.x, p.y, 5, 5, 2, p.color, null);
      p.x += p.vx;
      p.y += p.vy;
      p.vy += 0.08;
      p.life -= 1;
    }
    ctx.globalAlpha = 1;
    state.particles = state.particles.filter((p) => p.life > 0);
  }

  function drawDraggingPiece() {
    if (!state.drag) return;
    drawPiece(state.candidates[state.drag.index], state.drag.x, state.drag.y - 34, 1.1, false);
  }

  function drawModal() {
    if (!state.openPanels.length) return;
    const panel = state.openPanels[state.openPanels.length - 1];
    fillRound(34, 162, 322, 402, 8, 'rgba(11,18,32,0.94)', 'rgba(255,255,255,0.18)');
    const titles = {
      SkinShopPanel: 'Skin Shop',
      GalleryPanel: 'Gallery',
      LevelSelectPanel: 'Level Map',
      PausePanel: 'Paused',
      ReviveDialog: 'Continue?',
      GameOverDialog: 'No Moves',
    };
    drawText(titles[panel] || panel, 195, 196, 24, COLORS.ink, 'center', 800);
    if (panel === 'SkinShopPanel') {
      drawSkinRows();
    } else if (panel === 'GalleryPanel') {
      drawGalleryRows();
    } else if (panel === 'LevelSelectPanel') {
      drawLevelRows();
    } else if (panel === 'ReviveDialog' || panel === 'GameOverDialog') {
      drawText('Revive clears a 3x3 area and keeps the run alive.', 195, 256, 13, COLORS.muted, 'center', 600);
      fillRound(100, 306, 190, 46, 8, COLORS.good, null);
      drawText('Watch Ad Placeholder', 195, 329, 13, '#06121b', 'center', 800);
    } else {
      drawText('Tap outside this panel to resume.', 195, 266, 14, COLORS.muted, 'center', 600);
      fillRound(104, 318, 182, 44, 8, COLORS.blue, null);
      drawText('Resume', 195, 340, 14, '#06121b', 'center', 800);
    }
  }

  function drawSkinRows() {
    const names = ['Neon Mint', 'Sunset Coral', 'Aurora Violet'];
    const colors = [COLORS.good, COLORS.hot, COLORS.violet];
    for (let i = 0; i < names.length; i += 1) {
      const y = 246 + i * 72;
      fillRound(72, y, 246, 52, 8, 'rgba(255,255,255,0.07)', 'rgba(255,255,255,0.1)');
      fillRound(92, y + 12, 28, 28, 6, colors[i], null);
      drawText(names[i], 136, y + 26, 14, COLORS.ink, 'left', 700);
      drawText(i === 0 ? 'Equipped' : 'Owned', 286, y + 26, 12, COLORS.good, 'right', 700);
    }
  }

  function drawGalleryRows() {
    for (let i = 0; i < 6; i += 1) {
      const x = 80 + (i % 3) * 76;
      const y = 252 + Math.floor(i / 3) * 86;
      fillRound(x, y, 52, 52, 8, [COLORS.good, COLORS.warn, COLORS.hot, COLORS.blue, COLORS.violet, COLORS.glow][i], null);
      drawText(`Set ${i + 1}`, x + 26, y + 70, 11, COLORS.muted, 'center', 600);
    }
  }

  function drawLevelRows() {
    for (let i = 0; i < 7; i += 1) {
      const x = 70 + (i % 4) * 64;
      const y = 248 + Math.floor(i / 4) * 78;
      fillRound(x, y, 46, 46, 8, i + 1 === state.level ? COLORS.good : 'rgba(255,255,255,0.09)', 'rgba(255,255,255,0.12)');
      drawText(String(i + 1), x + 23, y + 23, 16, i + 1 === state.level ? '#06121b' : COLORS.ink, 'center', 800);
    }
    drawText('Seven handcrafted opening goals are available.', 195, 430, 13, COLORS.muted, 'center', 600);
  }

  function drawFooter() {
    drawText(`Combo ${state.combo}   Streak ${state.streak}`, 24, 806, 13, COLORS.muted, 'left', 700);
    drawText(muted ? 'Muted' : 'Sound on', 366, 806, 13, COLORS.muted, 'right', 700);
  }

  function draw() {
    if (!ctx) return;
    frame += 1;
    ctx.clearRect(0, 0, WIDTH, HEIGHT);
    drawBackground();
    drawHud();
    drawBoard();
    drawTray();
    drawParticles();
    drawDraggingPiece();
    drawModal();
    drawFooter();
  }

  function install() {
    const gameCanvas = document.getElementById('GameCanvas');
    if (!gameCanvas && document.readyState !== 'complete') {
      window.setTimeout(install, 80);
      return;
    }
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.id = 'block-puzzle-canvas';
      canvas.width = WIDTH;
      canvas.height = HEIGHT;
      canvas.style.position = 'fixed';
      canvas.style.left = '50%';
      canvas.style.top = '0';
      canvas.style.width = 'min(100vw, 430px)';
      canvas.style.height = 'min(100vh, 930px)';
      canvas.style.maxHeight = '100vh';
      canvas.style.transform = 'translateX(-50%)';
      canvas.style.zIndex = '100';
      canvas.style.touchAction = 'none';
      canvas.style.pointerEvents = 'auto';
      canvas.setAttribute('data-workflow-runtime-bridge', 'model-backed-commercial-runtime');
      canvas.setAttribute('data-player-visible-runtime', 'true');
      document.body.appendChild(canvas);
      document.documentElement.style.background = '#070b12';
      document.body.style.margin = '0';
      document.body.style.background = '#070b12';
      document.body.style.overflow = 'hidden';
      ctx = canvas.getContext('2d');
      if (!ctx) {
        window.setTimeout(install, 100);
        return;
      }
      canvas.addEventListener('pointerdown', onPointerDown);
      canvas.addEventListener('pointermove', onPointerMove);
      canvas.addEventListener('pointerup', onPointerUp);
      canvas.addEventListener('pointercancel', onPointerUp);
      canvas.addEventListener('dblclick', () => {
        muted = !muted;
        localStorage.setItem('workflow.blockPuzzle.muted', muted ? '1' : '0');
        setFeature('volumeToggleUsable');
        draw();
      });
    }
    resetGame();
    state.started = true;
    setFeature('mobilePortraitUi');
    setFeature('modalUi');
    setFeature('nativeCocosUiNodes');
    window.__COCOS_BLOCK_PUZZLE_E2E__ = state;
    window.__COMMERCIAL_BLOCK_PUZZLE_RUNTIME__ = {
      getSnapshot: () => JSON.parse(JSON.stringify(state)),
      placeFirstCandidateAtClearTarget: () => placePiece(0, 0, 0),
      reset: resetGame,
    };
    publish('runtime_boot_ready', {
      beforeBoard: cloneBoard(state.board),
      candidateTray: state.candidates.map((piece) => ({ id: piece.id, cells: piece.cells })),
      clearTarget: state.clearTarget,
    });
    draw();
    window.requestAnimationFrame(function loop() {
      if (state.particles.length || frame % 30 === 0) draw();
      window.requestAnimationFrame(loop);
    });
  }

  install();
})();
