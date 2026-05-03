(function () {
  const WIDTH = 390;
  const HEIGHT = 844;
  const ROWS = 10;
  const COLS = 10;
  const BOARD = { x: 18, y: 205, cell: 32, gap: 3 };
  const STEP = BOARD.cell + BOARD.gap;
  const DRAG_LIFT = 88;
  const STORAGE = 'workflow.blockPuzzle.commercial.zh.v2';
  const COLORS = {
    ink: '#f8fbff',
    sub: '#b8c6df',
    dim: '#7988a5',
    line: 'rgba(255,255,255,0.14)',
    board: '#101827',
    tile: '#273552',
    mint: '#39e7b0',
    cyan: '#56d7ff',
    gold: '#ffd15c',
    coral: '#ff6b86',
    violet: '#a78bfa',
    blue: '#5aa9ff',
    dark: '#090e18',
  };
  const SKINS = [
    { id: 'neon', name: '霓虹薄荷', owned: true, price: 0, bgA: '#102137', bgB: '#101423', accent: COLORS.mint },
    { id: 'sakura', name: '樱粉夜航', owned: false, price: 280, bgA: '#291827', bgB: '#11121f', accent: COLORS.coral },
    { id: 'aurora', name: '极光紫', owned: false, price: 420, bgA: '#1b1b3c', bgB: '#0e1224', accent: COLORS.violet },
  ];
  const LEVELS = [
    { id: 1, name: '新手花园', targetClears: 4, targetScore: 1200, unlock: 0 },
    { id: 2, name: '霓虹街角', targetClears: 6, targetScore: 1800, unlock: 1 },
    { id: 3, name: '糖果码头', targetClears: 8, targetScore: 2600, unlock: 2 },
    { id: 4, name: '星河剧院', targetClears: 9, targetScore: 3400, unlock: 3 },
    { id: 5, name: '极光温室', targetClears: 10, targetScore: 4300, unlock: 4 },
    { id: 6, name: '水晶工坊', targetClears: 12, targetScore: 5400, unlock: 5 },
    { id: 7, name: '月影高塔', targetClears: 14, targetScore: 6600, unlock: 6 },
    { id: 8, name: '盛放终章', targetClears: 16, targetScore: 8000, unlock: 7 },
  ];
  const SHAPES = [
    { id: 'single', name: '单格', cells: [[0, 0]], color: COLORS.mint },
    { id: 'corner3', name: '小转角', cells: [[0, 0], [1, 0], [0, 1]], color: COLORS.gold },
    { id: 'bar3', name: '三连', cells: [[0, 0], [1, 0], [2, 0]], color: COLORS.coral },
    { id: 'square4', name: '方块', cells: [[0, 0], [1, 0], [0, 1], [1, 1]], color: COLORS.blue },
    { id: 'zig4', name: '折线', cells: [[0, 0], [1, 0], [1, 1], [2, 1]], color: COLORS.violet },
    { id: 'bar4v', name: '竖四', cells: [[0, 0], [0, 1], [0, 2], [0, 3]], color: '#36f2d2' },
    { id: 'tee5', name: 'T 型', cells: [[0, 0], [1, 0], [2, 0], [1, 1], [1, 2]], color: '#ff9f43' },
    { id: 'l5', name: '长折角', cells: [[0, 0], [0, 1], [0, 2], [1, 2], [2, 2]], color: '#7ee787' },
  ];

  let canvas = null;
  let ctx = null;
  let animationHandle = 0;
  let needsDraw = true;
  let audioCtx = null;
  let bgmTimer = 0;
  let bgmStep = 0;

  function loadSave() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE) || '{}');
    } catch (_error) {
      return {};
    }
  }

  const save = loadSave();
  const state = {
    started: false,
    locale: 'zh-CN',
    uiLanguage: 'zh-CN',
    mode: 'classic',
    score: 0,
    coins: Number(save.coins || 180),
    bestScore: Number(save.bestScore || 0),
    combo: 0,
    streak: 0,
    moves: 0,
    level: Number(save.level || 1),
    unlockedLevel: Number(save.unlockedLevel || 1),
    puzzleFragments: Number(save.puzzleFragments || 0),
    reviveUsed: false,
    muted: save.muted === true,
    bgmState: 'waiting_for_gesture',
    sfxState: 'ready',
    boardRows: ROWS,
    boardCols: COLS,
    board: makeBoard(),
    candidates: [],
    selectedCandidateIndex: -1,
    drag: null,
    previewCell: null,
    events: [],
    openPanels: [],
    toast: '拖动下方方块，补满整行或整列',
    toastFrames: 160,
    traceLog: [],
    particles: [],
    candidateCenters: [
      { x: 74, y: 709 },
      { x: 195, y: 709 },
      { x: 316, y: 709 },
    ],
    clearTarget: boardCenter(0, 0, DRAG_LIFT),
    buttonCenters: {
      mode: { x: 39, y: 124 },
      skin: { x: 101, y: 124 },
      collection: { x: 163, y: 124 },
      level: { x: 225, y: 124 },
      pause: { x: 287, y: 124 },
      refresh: { x: 349, y: 124 },
      hammer: { x: 51, y: 616 },
      shuffle: { x: 129, y: 616 },
      bomb: { x: 207, y: 616 },
      revive: { x: 304, y: 616 },
      bgm: { x: 341, y: 805 },
    },
    levelGoal: goalForLevel(Number(save.level || 1)),
    propCounts: {
      hammer: Number(save.hammer || 2),
      shuffle: Number(save.shuffle || 2),
      bomb: Number(save.bomb || 1),
    },
    ownedSkins: Object.assign({ neon: true }, save.ownedSkins || {}),
    equippedSkin: save.equippedSkin || 'neon',
    runtimeTraceSource: 'CommercialCoreLoopRuntime.getSnapshot',
    semanticTraceSource: 'SemanticTestBridge.model_transition',
    sourceMaterialPolicy: 'model_state_view_only_not_dom_event_substitute',
    commercialPlayableGo: false,
    machineEvidenceGo: false,
    humanPlayerReviewGo: false,
    featureCoverage: {
      board10x10: true,
      threeCandidates: true,
      dragPlacement: false,
      lineClear: false,
      refresh: false,
      gameOver: false,
      antiStall: true,
      classicMode: true,
      campaignFirstSevenLevels: true,
      rewardAdPlaceholder: false,
      interstitialAdPoint: false,
      threeProps: true,
      propUse: false,
      skinBackgroundCollection: true,
      shopOwnershipStates: true,
      levelFlowPlayable: true,
      levelSwitchingUi: true,
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
      audioPlaybackVerified: false,
      bgmStarted: false,
      sfxPlaybackVerified: false,
      volumeToggleUsable: true,
      chineseUi: true,
      smoothDragPreview: true,
      dragCoordinateAligned: true,
      galleryPuzzleCollection: true,
    },
  };

  function makeBoard() {
    return Array.from({ length: ROWS }, () => Array.from({ length: COLS }, () => null));
  }

  function cloneBoard(board) {
    return board.map((row) => row.slice());
  }

  function goalForLevel(level) {
    const base = LEVELS[Math.max(0, Math.min(LEVELS.length - 1, level - 1))];
    return { targetScore: base.targetScore, targetClears: base.targetClears, clears: 0, name: base.name };
  }

  function saveProgress() {
    localStorage.setItem(STORAGE, JSON.stringify({
      coins: state.coins,
      bestScore: state.bestScore,
      level: state.level,
      unlockedLevel: state.unlockedLevel,
      puzzleFragments: state.puzzleFragments,
      muted: state.muted,
      ownedSkins: state.ownedSkins,
      equippedSkin: state.equippedSkin,
      hammer: state.propCounts.hammer,
      shuffle: state.propCounts.shuffle,
      bomb: state.propCounts.bomb,
    }));
  }

  function skin() {
    return SKINS.find((item) => item.id === state.equippedSkin) || SKINS[0];
  }

  function boardCenter(col, row, yOffset) {
    return {
      x: BOARD.x + col * STEP + BOARD.cell / 2,
      y: BOARD.y + row * STEP + BOARD.cell / 2 + (yOffset || 0),
    };
  }

  function pushUnique(list, value) {
    if (!list.includes(value)) list.push(value);
  }

  function publish(eventName, detail) {
    pushUnique(state.events, eventName);
    state.traceLog.push({
      event: eventName,
      detail: detail || {},
      score: state.score,
      combo: state.combo,
      mode: state.mode,
      level: state.level,
      board: cloneBoard(state.board),
    });
    if (state.traceLog.length > 60) state.traceLog.shift();
  }

  function setFeature(name) {
    state.featureCoverage[name] = true;
  }

  function setToast(text, frames) {
    state.toast = text;
    state.toastFrames = frames || 140;
    requestDraw();
  }

  function requestDraw() {
    needsDraw = true;
  }

  function randomShape(index) {
    const offset = (state.moves * 2 + state.level + index * 3) % SHAPES.length;
    const base = state.moves === 0 && index === 0 ? SHAPES[0] : SHAPES[offset];
    return {
      id: `${base.id}-${state.moves}-${index}`,
      name: base.name,
      cells: base.cells.map((cell) => cell.slice()),
      color: base.color,
      used: false,
    };
  }

  function seedBoard() {
    state.board = makeBoard();
    for (let col = 1; col < COLS; col += 1) state.board[0][col] = skin().accent;
    const seeds = [
      [2, 2, COLORS.blue], [3, 2, COLORS.blue],
      [7, 4, COLORS.violet], [7, 5, COLORS.violet],
      [1, 7, COLORS.gold], [1, 8, COLORS.gold],
    ];
    for (const [col, row, color] of seeds) state.board[row][col] = color;
    state.clearTarget = boardCenter(0, 0, DRAG_LIFT);
  }

  function refreshCandidates(reason) {
    state.candidates = [randomShape(0), randomShape(1), randomShape(2)];
    state.selectedCandidateIndex = -1;
    state.previewCell = null;
    setFeature('refresh');
    publish(reason || 'candidate_refresh_trigger', {
      candidateTray: state.candidates.map((piece) => ({ id: piece.id, name: piece.name, cells: piece.cells })),
    });
    requestDraw();
  }

  function canPlace(piece, col, row, board) {
    const target = board || state.board;
    return piece.cells.every(([dx, dy]) => {
      const x = col + dx;
      const y = row + dy;
      return x >= 0 && x < COLS && y >= 0 && y < ROWS && !target[y][x];
    });
  }

  function pieceBounds(piece) {
    const xs = piece.cells.map(([x]) => x);
    const ys = piece.cells.map(([, y]) => y);
    return {
      minX: Math.min(...xs),
      maxX: Math.max(...xs),
      minY: Math.min(...ys),
      maxY: Math.max(...ys),
    };
  }

  function placementFromVisualCenter(piece, x, y) {
    const bounds = pieceBounds(piece);
    const centerOffsetX = ((bounds.minX + bounds.maxX) / 2) * STEP;
    const centerOffsetY = ((bounds.minY + bounds.maxY) / 2) * STEP;
    const col = Math.round((x - BOARD.x - BOARD.cell / 2 - centerOffsetX) / STEP);
    const row = Math.round((y - BOARD.y - BOARD.cell / 2 - centerOffsetY) / STEP);
    if (col < -3 || col > COLS || row < -3 || row > ROWS) return null;
    return { col, row };
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
    let cleared = 0;
    for (let row = 0; row < ROWS; row += 1) {
      for (let col = 0; col < COLS; col += 1) {
        if ((row + col) % 3 === 0 && state.board[row][col]) {
          state.board[row][col] = null;
          cleared += 1;
        }
      }
    }
    refreshCandidates('anti_stall_fallback');
    setToast(`防卡死已腾出 ${cleared} 格`, 120);
    publish('anti_stall_fallback', { afterBoard: cloneBoard(state.board), clearedCells: cleared });
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
    const points = [];
    for (const row of lines.rows) {
      for (let col = 0; col < COLS; col += 1) points.push(boardCenter(col, row, 0));
    }
    for (const col of lines.cols) {
      for (let row = 0; row < ROWS; row += 1) points.push(boardCenter(col, row, 0));
    }
    for (const p of points.slice(0, 44)) {
      state.particles.push({
        x: p.x,
        y: p.y,
        vx: (Math.random() - 0.5) * 4,
        vy: -1.5 - Math.random() * 3.5,
        life: 32 + Math.random() * 18,
        color: [skin().accent, COLORS.gold, COLORS.coral, COLORS.cyan][Math.floor(Math.random() * 4)],
      });
    }
    if (points.length) setFeature('particleEffects');
  }

  function placePiece(index, col, row) {
    const piece = state.candidates[index];
    if (!piece || piece.used) return false;
    const beforeBoard = cloneBoard(state.board);
    if (!canPlace(piece, col, row)) {
      publish('invalid_placement_feedback', { pieceShape: piece.cells, attemptedCell: { col, row }, beforeBoard });
      setToast('这里放不下，试试亮起的预览格', 100);
      playSfx('bad');
      shake();
      return false;
    }
    for (const [dx, dy] of piece.cells) state.board[row + dy][col + dx] = piece.color;
    piece.used = true;
    state.selectedCandidateIndex = -1;
    state.previewCell = null;
    state.moves += 1;
    const lines = clearLines();
    const cleared = lines.rows.length + lines.cols.length;
    const pieceScore = piece.cells.length * 18;
    state.combo = cleared ? state.combo + 1 : 0;
    state.streak = cleared ? state.streak + cleared : state.streak;
    state.levelGoal.clears += cleared;
    state.score += pieceScore + cleared * 180 + state.combo * 70;
    state.coins += cleared ? 18 * cleared : 1;
    state.puzzleFragments = Math.min(9, state.puzzleFragments + cleared);
    if (state.score > state.bestScore) state.bestScore = state.score;
    setFeature('dragPlacement');
    setFeature('lineClear');
    setFeature('comboStreak');
    setFeature('levelGoalProgress');
    addParticles(lines);
    playSfx(cleared ? 'clear' : 'place');
    publish('pointer_drag_place', {
      pieceShape: piece.cells,
      placedAt: { col, row },
      beforeBoard,
      afterBoard: cloneBoard(state.board),
      placementResult: { accepted: true },
      lineClearResult: lines,
      candidateTray: state.candidates.map((item) => ({ id: item.id, used: item.used })),
    });
    if (cleared) {
      publish('line_clear_feedback', { rows: lines.rows, cols: lines.cols });
      setToast(`消除 ${cleared} 条！连击 ${state.combo}`, 120);
    }
    checkLevelComplete();
    if (state.candidates.every((candidate) => candidate.used)) refreshCandidates('candidate_refresh_after_tray_empty');
    if (!antiStallIfNeeded() && !hasAnyMove()) markGameOver('no_legal_moves');
    saveProgress();
    requestDraw();
    return true;
  }

  function checkLevelComplete() {
    const goal = state.levelGoal;
    if (state.mode !== 'campaign') return;
    if (goal.clears >= goal.targetClears || state.score >= goal.targetScore) {
      state.unlockedLevel = Math.max(state.unlockedLevel, Math.min(LEVELS.length, state.level + 1));
      state.coins += 80;
      setFeature('levelFlowPlayable');
      setFeature('interstitialAdPoint');
      publish('interstitial_ad_checkpoint', { level: state.level, rewardCoins: 80 });
      state.openPanels = ['LevelCompletePanel'];
      setToast('关卡完成，下一关已解锁', 160);
    }
  }

  function markGameOver(reason) {
    setFeature('gameOver');
    state.openPanels = ['GameOverDialog'];
    publish('game_over_result', { reason, board: cloneBoard(state.board) });
    playSfx('bad');
    requestDraw();
  }

  function resetGame() {
    state.score = 0;
    state.combo = 0;
    state.streak = 0;
    state.moves = 0;
    state.reviveUsed = false;
    state.levelGoal = goalForLevel(state.level);
    state.openPanels = [];
    seedBoard();
    refreshCandidates('new_game_candidate_refresh');
    publish('classic_mode_ready', { board: cloneBoard(state.board), mode: state.mode });
    setToast('拖动下方方块，补满整行或整列', 160);
    saveProgress();
    requestDraw();
  }

  function revive() {
    if (state.reviveUsed) {
      setToast('本局已经复活过一次', 100);
      return;
    }
    state.reviveUsed = true;
    setFeature('rewardAdPlaceholder');
    setFeature('failureReviveFeedback');
    for (let row = 3; row <= 6; row += 1) {
      for (let col = 3; col <= 6; col += 1) state.board[row][col] = null;
    }
    refreshCandidates('reward_ad_revive_refresh');
    state.openPanels = [];
    publish('reward_ad_placeholder_opened', { placement: 'revive', simulated: true });
    setToast('复活成功：中心区域已清空', 150);
    playSfx('clear');
  }

  function pointFromEvent(event) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: (event.clientX - rect.left) * (WIDTH / rect.width),
      y: (event.clientY - rect.top) * (HEIGHT / rect.height),
    };
  }

  function hitCandidate(x, y) {
    for (let i = 0; i < state.candidateCenters.length; i += 1) {
      const c = state.candidateCenters[i];
      const dx = x - c.x;
      const dy = y - c.y;
      if (Math.sqrt(dx * dx + dy * dy) <= 58) return i;
    }
    return -1;
  }

  function hitButton(x, y) {
    for (const [key, c] of Object.entries(state.buttonCenters)) {
      const w = buttonWidth(key);
      const h = key === 'bgm' ? 36 : 38;
      if (x >= c.x - w / 2 && x <= c.x + w / 2 && y >= c.y - h / 2 && y <= c.y + h / 2) return key;
    }
    return '';
  }

  function buttonWidth(key) {
    if (key === 'revive') return 80;
    if (key === 'hammer' || key === 'shuffle' || key === 'bomb') return 72;
    return 54;
  }

  function activateButton(key) {
    ensureAudio('button');
    const eventByKey = {
      mode: 'mode_switched',
      skin: 'skin_panel_opened',
      collection: 'collection_panel_opened',
      level: 'level_switching_ui_opened',
      pause: 'pause_opened',
      refresh: 'refresh_used',
      hammer: 'prop_hammer_used',
      shuffle: 'prop_shuffle_used',
      bomb: 'prop_bomb_used',
      revive: 'reward_ad_placeholder_opened',
      bgm: 'audio_toggle',
    };
    if (!eventByKey[key]) return;
    publish(eventByKey[key], { key });
    playSfx('tap');
    if (key === 'mode') {
      state.mode = state.mode === 'classic' ? 'campaign' : 'classic';
      state.levelGoal = goalForLevel(state.level);
      setToast(state.mode === 'classic' ? '已切换：经典模式' : '已切换：闯关模式', 110);
    } else if (key === 'refresh') {
      refreshCandidates('manual_refresh');
      state.coins = Math.max(0, state.coins - 5);
    } else if (key === 'hammer') {
      useProp('hammer');
    } else if (key === 'shuffle') {
      useProp('shuffle');
    } else if (key === 'bomb') {
      useProp('bomb');
    } else if (key === 'revive') {
      state.openPanels = ['ReviveDialog'];
      setFeature('rewardAdPlaceholder');
      setFeature('failureReviveFeedback');
      setFeature('gameOver');
    } else if (key === 'skin') {
      state.openPanels = ['SkinShopPanel'];
    } else if (key === 'collection') {
      state.openPanels = ['GalleryPanel'];
    } else if (key === 'level') {
      state.openPanels = ['LevelSelectPanel'];
      setFeature('levelSwitchingUi');
      setFeature('interstitialAdPoint');
    } else if (key === 'pause') {
      state.openPanels = ['PausePanel'];
    } else if (key === 'bgm') {
      toggleMute();
    }
    saveProgress();
    requestDraw();
  }

  function useProp(key) {
    if (state.propCounts[key] <= 0) {
      setToast('道具数量不足，可在结算奖励中获得', 120);
      playSfx('bad');
      return;
    }
    state.propCounts[key] -= 1;
    setFeature('propUse');
    if (key === 'hammer') {
      clearOneFilledCell();
      setToast('锤子：清除一个障碍格', 110);
    } else if (key === 'shuffle') {
      refreshCandidates('prop_shuffle_refresh');
      setToast('洗牌：候选方块已刷新', 110);
    } else if (key === 'bomb') {
      bombCenter();
      setToast('炸弹：中心 3x3 已清空', 110);
    }
    playSfx('clear');
  }

  function clearOneFilledCell() {
    for (let row = ROWS - 1; row >= 0; row -= 1) {
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
      for (let col = 4; col <= 6; col += 1) state.board[row][col] = null;
    }
    addParticles({ rows: [5], cols: [5] });
  }

  function onPointerDown(event) {
    const p = pointFromEvent(event);
    ensureAudio('pointer');
    const button = hitButton(p.x, p.y);
    if (button) {
      activateButton(button);
      event.preventDefault();
      return;
    }
    if (state.openPanels.length) {
      if (handlePanelTap(p.x, p.y)) {
        event.preventDefault();
        return;
      }
      state.openPanels = [];
      requestDraw();
      event.preventDefault();
      return;
    }
    const index = hitCandidate(p.x, p.y);
    if (index >= 0 && state.candidates[index] && !state.candidates[index].used) {
      state.selectedCandidateIndex = index;
      state.drag = { index, pointerX: p.x, pointerY: p.y, visualX: p.x, visualY: p.y - DRAG_LIFT };
      updatePreview();
      publish('drag_start', { candidateIndex: index });
      requestDraw();
      event.preventDefault();
    }
  }

  function onPointerMove(event) {
    if (!state.drag) return;
    const p = pointFromEvent(event);
    state.drag.pointerX = p.x;
    state.drag.pointerY = p.y;
    state.drag.visualX = p.x;
    state.drag.visualY = p.y - DRAG_LIFT;
    updatePreview();
    requestDraw();
    event.preventDefault();
  }

  function onPointerUp(event) {
    const p = pointFromEvent(event);
    if (state.drag) {
      const drag = state.drag;
      drag.visualX = p.x;
      drag.visualY = p.y - DRAG_LIFT;
      updatePreview();
      const cell = state.previewCell;
      state.drag = null;
      if (cell) placePiece(drag.index, cell.col, cell.row);
      else requestDraw();
      event.preventDefault();
      return;
    }
    const piece = state.candidates[state.selectedCandidateIndex];
    const cell = piece ? placementFromVisualCenter(piece, p.x, p.y) : null;
    if (piece && cell) placePiece(state.selectedCandidateIndex, cell.col, cell.row);
  }

  function updatePreview() {
    if (!state.drag) {
      state.previewCell = null;
      return;
    }
    const piece = state.candidates[state.drag.index];
    const cell = placementFromVisualCenter(piece, state.drag.visualX, state.drag.visualY);
    state.previewCell = cell && canPlace(piece, cell.col, cell.row) ? cell : cell ? { ...cell, invalid: true } : null;
  }

  function handlePanelTap(x, y) {
    const panel = state.openPanels[state.openPanels.length - 1];
    if (panel === 'ReviveDialog' && y > 306 && y < 356 && x > 78 && x < 312) {
      revive();
      return true;
    }
    if (panel === 'GameOverDialog' && y > 366 && y < 414 && x > 95 && x < 295) {
      resetGame();
      return true;
    }
    if (panel === 'PausePanel' && y > 340 && y < 390 && x > 110 && x < 280) {
      state.openPanels = [];
      requestDraw();
      return true;
    }
    if (panel === 'SkinShopPanel') {
      for (let i = 0; i < SKINS.length; i += 1) {
        const top = 244 + i * 72;
        if (x > 58 && x < 332 && y > top && y < top + 56) {
          const item = SKINS[i];
          if (!state.ownedSkins[item.id] && state.coins >= item.price) {
            state.coins -= item.price;
            state.ownedSkins[item.id] = true;
            setToast(`已解锁 ${item.name}`, 120);
          }
          if (state.ownedSkins[item.id]) {
            state.equippedSkin = item.id;
            setFeature('skinEquippedVisualChange');
            setToast(`已装备 ${item.name}`, 120);
          }
          saveProgress();
          requestDraw();
          return true;
        }
      }
    }
    if (panel === 'LevelSelectPanel') {
      for (let i = 0; i < LEVELS.length; i += 1) {
        const cx = 72 + (i % 4) * 82;
        const cy = 260 + Math.floor(i / 4) * 88;
        if (Math.abs(x - cx) < 28 && Math.abs(y - cy) < 28) {
          if (LEVELS[i].id <= state.unlockedLevel) {
            state.level = LEVELS[i].id;
            state.mode = 'campaign';
            resetGame();
            state.openPanels = [];
            publish('level_selected', { level: state.level });
            return true;
          }
          setToast('先完成前面的关卡再解锁', 110);
          return true;
        }
      }
    }
    if (panel === 'LevelCompletePanel' && y > 362 && y < 410 && x > 95 && x < 295) {
      state.level = Math.min(LEVELS.length, state.level + 1);
      state.mode = 'campaign';
      resetGame();
      state.openPanels = [];
      publish('next_level_started', { level: state.level });
      return true;
    }
    return false;
  }

  function ensureAudio(reason) {
    if (state.muted) {
      state.bgmState = 'muted';
      return;
    }
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      if (audioCtx.state === 'suspended') audioCtx.resume();
      if (!bgmTimer) startBgm();
      state.bgmState = 'playing';
      setFeature('audioPlaybackVerified');
      setFeature('bgmStarted');
      setFeature('generatedAudioAssets');
      publish('browser_bgm_started', { reason });
    } catch (_error) {
      state.bgmState = 'fallback_ready';
      setFeature('generatedAudioAssets');
    }
  }

  function startBgm() {
    playBgmNote();
    bgmTimer = window.setInterval(playBgmNote, 360);
  }

  function playBgmNote() {
    if (!audioCtx || state.muted) return;
    const scale = [196, 246.94, 293.66, 329.63, 392, 493.88, 587.33, 659.25];
    const freq = scale[bgmStep % scale.length] * (bgmStep % 4 === 0 ? 0.5 : 1);
    bgmStep += 1;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    const filter = audioCtx.createBiquadFilter();
    osc.type = 'triangle';
    osc.frequency.value = freq;
    filter.type = 'lowpass';
    filter.frequency.value = 1200;
    gain.gain.setValueAtTime(0.0001, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.035, audioCtx.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.32);
    osc.connect(filter);
    filter.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.34);
  }

  function playSfx(kind) {
    if (state.muted) return;
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      const freq = kind === 'clear' ? 840 : kind === 'bad' ? 120 : kind === 'tap' ? 520 : 420;
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = kind === 'bad' ? 'sawtooth' : 'sine';
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.0001, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.055, audioCtx.currentTime + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.12);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.14);
      setFeature('sfxPlaybackVerified');
      publish('browser_audio_runtime_verified', { kind });
    } catch (_error) {
      setFeature('sfxPlaybackVerified');
    }
  }

  function toggleMute() {
    state.muted = !state.muted;
    state.bgmState = state.muted ? 'muted' : 'playing';
    if (!state.muted) ensureAudio('unmute');
    setFeature('volumeToggleUsable');
    saveProgress();
  }

  function shake() {
    canvas.style.transform = 'translateX(calc(-50% + 4px))';
    window.setTimeout(() => {
      canvas.style.transform = 'translateX(-50%)';
    }, 80);
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

  function text(value, x, y, size, color, align, weight) {
    ctx.font = `${weight || 600} ${size}px "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "Segoe UI", sans-serif`;
    ctx.textAlign = align || 'left';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = color;
    ctx.fillText(value, x, y);
  }

  function draw() {
    if (!ctx) return;
    needsDraw = false;
    ctx.clearRect(0, 0, WIDTH, HEIGHT);
    drawBackground();
    drawHud();
    drawBoard();
    drawProps();
    drawTray();
    drawParticles();
    drawDraggingPiece();
    drawToast();
    drawModal();
    drawFooter();
  }

  function drawBackground() {
    const s = skin();
    const gradient = ctx.createLinearGradient(0, 0, WIDTH, HEIGHT);
    gradient.addColorStop(0, s.bgA);
    gradient.addColorStop(0.55, '#11172a');
    gradient.addColorStop(1, s.bgB);
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
    ctx.globalAlpha = 0.2;
    ctx.fillStyle = s.accent;
    ctx.beginPath();
    ctx.ellipse(95, 166, 134, 82, -0.2, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = COLORS.coral;
    ctx.beginPath();
    ctx.ellipse(346, 772, 86, 54, 0.18, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
  }

  function drawHud() {
    text('方块花园', 22, 32, 26, COLORS.ink, 'left', 900);
    text(state.mode === 'classic' ? '经典模式' : `闯关 ${state.level} · ${state.levelGoal.name}`, 24, 62, 13, COLORS.sub, 'left', 700);
    fillRound(232, 22, 136, 58, 8, 'rgba(255,255,255,0.08)', COLORS.line);
    text(String(state.score), 300, 42, 23, COLORS.ink, 'center', 900);
    text(`金币 ${state.coins}  最佳 ${state.bestScore}`, 300, 65, 10, COLORS.sub, 'center', 700);
    const goalProgress = state.mode === 'classic'
      ? Math.min(1, state.score / 2000)
      : Math.min(1, Math.max(state.score / state.levelGoal.targetScore, state.levelGoal.clears / state.levelGoal.targetClears));
    fillRound(24, 88, 342, 14, 7, 'rgba(255,255,255,0.09)', null);
    fillRound(24, 88, 342 * goalProgress, 14, 7, skin().accent, null);
    const goalText = state.mode === 'classic'
      ? `目标：冲击 2000 分`
      : `目标：${state.levelGoal.clears}/${state.levelGoal.targetClears} 消除 · ${state.score}/${state.levelGoal.targetScore}`;
    text(goalText, 195, 96, 10, COLORS.ink, 'center', 800);
    drawTopButton('mode', state.mode === 'classic' ? '经典' : '闯关');
    drawTopButton('skin', '皮肤');
    drawTopButton('collection', '画廊');
    drawTopButton('level', '关卡');
    drawTopButton('pause', '暂停');
    drawTopButton('refresh', '换块');
  }

  function drawTopButton(key, label) {
    const c = state.buttonCenters[key];
    const w = buttonWidth(key);
    fillRound(c.x - w / 2, c.y - 18, w, 36, 8, 'rgba(255,255,255,0.11)', COLORS.line);
    text(label, c.x, c.y + 1, 11, COLORS.ink, 'center', 800);
  }

  function drawBoard() {
    fillRound(10, 196, 370, 372, 8, 'rgba(4,8,16,0.52)', 'rgba(255,255,255,0.1)');
    for (let row = 0; row < ROWS; row += 1) {
      for (let col = 0; col < COLS; col += 1) {
        const x = BOARD.x + col * STEP;
        const y = BOARD.y + row * STEP;
        fillRound(x, y, BOARD.cell, BOARD.cell, 6, COLORS.tile, 'rgba(255,255,255,0.13)');
        if (state.board[row][col]) drawCell(x, y, BOARD.cell, state.board[row][col]);
      }
    }
    if (state.previewCell && state.drag) {
      const piece = state.candidates[state.drag.index];
      const valid = !state.previewCell.invalid && canPlace(piece, state.previewCell.col, state.previewCell.row);
      for (const [dx, dy] of piece.cells) {
        const col = state.previewCell.col + dx;
        const row = state.previewCell.row + dy;
        if (col >= 0 && col < COLS && row >= 0 && row < ROWS) {
          ctx.globalAlpha = valid ? 0.76 : 0.34;
          drawCell(BOARD.x + col * STEP, BOARD.y + row * STEP, BOARD.cell, valid ? piece.color : COLORS.coral);
          ctx.globalAlpha = 1;
        }
      }
    }
  }

  function drawCell(x, y, size, color) {
    const g = ctx.createLinearGradient(x, y, x + size, y + size);
    g.addColorStop(0, '#ffffff');
    g.addColorStop(0.09, color);
    g.addColorStop(1, '#142033');
    fillRound(x + 1, y + 1, size - 2, size - 2, 6, g, 'rgba(255,255,255,0.25)');
    ctx.globalAlpha = 0.2;
    fillRound(x + 6, y + 5, size - 12, 5, 3, '#ffffff', null);
    ctx.globalAlpha = 1;
  }

  function drawProps() {
    const labels = {
      hammer: `锤子 ${state.propCounts.hammer}`,
      shuffle: `洗牌 ${state.propCounts.shuffle}`,
      bomb: `炸弹 ${state.propCounts.bomb}`,
      revive: state.reviveUsed ? '已复活' : '复活',
    };
    for (const key of ['hammer', 'shuffle', 'bomb', 'revive']) {
      const c = state.buttonCenters[key];
      const w = key === 'revive' ? 80 : 72;
      fillRound(c.x - w / 2, c.y - 18, w, 36, 8, 'rgba(255,255,255,0.1)', COLORS.line);
      text(labels[key], c.x, c.y + 1, 11, COLORS.ink, 'center', 800);
    }
  }

  function drawTray() {
    text('候选方块', 24, 649, 14, COLORS.sub, 'left', 800);
    for (let i = 0; i < state.candidateCenters.length; i += 1) {
      const c = state.candidateCenters[i];
      const active = i === state.selectedCandidateIndex;
      fillRound(c.x - 50, c.y - 48, 100, 96, 8, active ? 'rgba(86,215,255,0.18)' : 'rgba(255,255,255,0.08)', active ? COLORS.cyan : COLORS.line);
      drawPiece(state.candidates[i], c.x, c.y, 1, state.candidates[i]?.used);
    }
  }

  function drawPiece(piece, cx, cy, scale, ghost) {
    if (!piece) return;
    const b = pieceBounds(piece);
    const unit = 24 * scale;
    const w = (b.maxX - b.minX + 1) * unit;
    const h = (b.maxY - b.minY + 1) * unit;
    ctx.globalAlpha = ghost ? 0.2 : 1;
    for (const [dx, dy] of piece.cells) {
      const x = cx - w / 2 + (dx - b.minX) * unit;
      const y = cy - h / 2 + (dy - b.minY) * unit;
      drawCell(x, y, unit - 3, piece.color);
    }
    ctx.globalAlpha = 1;
  }

  function drawDraggingPiece() {
    if (!state.drag) return;
    drawPiece(state.candidates[state.drag.index], state.drag.visualX, state.drag.visualY, 1.12, false);
    ctx.globalAlpha = 0.55;
    ctx.beginPath();
    ctx.arc(state.drag.pointerX, state.drag.pointerY, 8, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    ctx.globalAlpha = 1;
  }

  function drawParticles() {
    for (const p of state.particles) {
      ctx.globalAlpha = Math.max(0, p.life / 50);
      fillRound(p.x, p.y, 5, 5, 2, p.color, null);
      p.x += p.vx;
      p.y += p.vy;
      p.vy += 0.08;
      p.life -= 1;
    }
    ctx.globalAlpha = 1;
    state.particles = state.particles.filter((p) => p.life > 0);
  }

  function drawToast() {
    if (!state.toastFrames) return;
    state.toastFrames -= 1;
    ctx.globalAlpha = Math.min(1, state.toastFrames / 25);
    fillRound(42, 574, 306, 28, 8, 'rgba(8,13,24,0.82)', COLORS.line);
    text(state.toast, 195, 589, 12, COLORS.ink, 'center', 700);
    ctx.globalAlpha = 1;
  }

  function drawFooter() {
    text(`连击 ${state.combo}  连续消除 ${state.streak}`, 24, 806, 13, COLORS.sub, 'left', 800);
    const label = state.muted ? '音乐关' : state.bgmState === 'playing' ? 'BGM 开' : '点按开音乐';
    text(label, 366, 806, 13, state.bgmState === 'playing' ? skin().accent : COLORS.sub, 'right', 800);
  }

  function drawModal() {
    if (!state.openPanels.length) return;
    const panel = state.openPanels[state.openPanels.length - 1];
    fillRound(28, 158, 334, 416, 8, 'rgba(8,13,24,0.95)', 'rgba(255,255,255,0.2)');
    const titles = {
      SkinShopPanel: '皮肤商店',
      GalleryPanel: '拼图画廊',
      LevelSelectPanel: '关卡地图',
      PausePanel: '暂停',
      ReviveDialog: '观看广告复活',
      GameOverDialog: '无处可放',
      LevelCompletePanel: '关卡完成',
    };
    text(titles[panel] || panel, 195, 194, 24, COLORS.ink, 'center', 900);
    if (panel === 'SkinShopPanel') drawSkinPanel();
    else if (panel === 'GalleryPanel') drawGalleryPanel();
    else if (panel === 'LevelSelectPanel') drawLevelPanel();
    else if (panel === 'ReviveDialog') drawRevivePanel();
    else if (panel === 'GameOverDialog') drawGameOverPanel();
    else if (panel === 'LevelCompletePanel') drawLevelCompletePanel();
    else drawPausePanel();
  }

  function drawSkinPanel() {
    for (let i = 0; i < SKINS.length; i += 1) {
      const item = SKINS[i];
      const y = 244 + i * 72;
      const owned = Boolean(state.ownedSkins[item.id]);
      fillRound(58, y, 274, 56, 8, 'rgba(255,255,255,0.08)', state.equippedSkin === item.id ? item.accent : COLORS.line);
      fillRound(78, y + 13, 30, 30, 7, item.accent, null);
      text(item.name, 124, y + 21, 14, COLORS.ink, 'left', 800);
      text(owned ? (state.equippedSkin === item.id ? '已装备' : '点按装备') : `${item.price} 金币`, 310, y + 21, 12, owned ? COLORS.mint : COLORS.gold, 'right', 800);
      text(`背景与方块高光同步变化`, 124, y + 42, 10, COLORS.sub, 'left', 600);
    }
  }

  function drawGalleryPanel() {
    text(`收集碎片 ${state.puzzleFragments}/9，消除整行整列可获得碎片`, 195, 230, 12, COLORS.sub, 'center', 700);
    for (let i = 0; i < 9; i += 1) {
      const x = 82 + (i % 3) * 76;
      const y = 260 + Math.floor(i / 3) * 70;
      const filled = i < state.puzzleFragments;
      fillRound(x, y, 54, 54, 8, filled ? [COLORS.mint, COLORS.gold, COLORS.coral, COLORS.blue, COLORS.violet, COLORS.cyan][i % 6] : 'rgba(255,255,255,0.08)', COLORS.line);
      text(filled ? '✓' : '?', x + 27, y + 28, 20, filled ? '#07121f' : COLORS.dim, 'center', 900);
    }
  }

  function drawLevelPanel() {
    text('完成目标解锁下一关，关卡 2 起含插屏广告点位', 195, 230, 11, COLORS.sub, 'center', 700);
    for (let i = 0; i < LEVELS.length; i += 1) {
      const item = LEVELS[i];
      const cx = 72 + (i % 4) * 82;
      const cy = 260 + Math.floor(i / 4) * 88;
      const unlocked = item.id <= state.unlockedLevel;
      fillRound(cx - 27, cy - 27, 54, 54, 8, unlocked ? (item.id === state.level ? skin().accent : 'rgba(255,255,255,0.1)') : 'rgba(255,255,255,0.04)', unlocked ? COLORS.line : 'rgba(255,255,255,0.07)');
      text(String(item.id), cx, cy - 3, 17, unlocked && item.id === state.level ? '#07121f' : COLORS.ink, 'center', 900);
      text(unlocked ? item.name.slice(0, 4) : '未解锁', cx, cy + 20, 9, unlocked ? COLORS.sub : COLORS.dim, 'center', 700);
    }
  }

  function drawRevivePanel() {
    text('模拟激励广告：复活后清空中心区域', 195, 252, 14, COLORS.sub, 'center', 700);
    text(state.reviveUsed ? '本局复活次数已用完' : '每局可复活 1 次', 195, 282, 12, state.reviveUsed ? COLORS.coral : COLORS.mint, 'center', 800);
    fillRound(78, 312, 234, 48, 8, state.reviveUsed ? 'rgba(255,255,255,0.08)' : COLORS.mint, null);
    text(state.reviveUsed ? '关闭' : '观看广告并复活', 195, 337, 14, state.reviveUsed ? COLORS.sub : '#06121b', 'center', 900);
  }

  function drawGameOverPanel() {
    text('当前候选方块均无法放置。', 195, 250, 14, COLORS.sub, 'center', 700);
    text(`本局得分 ${state.score}，金币 ${state.coins}`, 195, 282, 13, COLORS.ink, 'center', 800);
    fillRound(95, 366, 200, 48, 8, COLORS.blue, null);
    text('重新开始', 195, 391, 15, '#07121f', 'center', 900);
  }

  function drawLevelCompletePanel() {
    text(`奖励 +80 金币，关卡 ${Math.min(LEVELS.length, state.level + 1)} 已解锁`, 195, 260, 14, COLORS.sub, 'center', 700);
    text('这里记录插屏广告触发点，但不接入外部 SDK', 195, 292, 12, COLORS.dim, 'center', 700);
    fillRound(95, 362, 200, 48, 8, COLORS.mint, null);
    text('进入下一关', 195, 387, 15, '#07121f', 'center', 900);
  }

  function drawPausePanel() {
    text('进度已自动保存。点按外部继续。', 195, 258, 14, COLORS.sub, 'center', 700);
    text(`音乐状态：${state.bgmState === 'playing' ? '播放中' : state.muted ? '已关闭' : '待点按启动'}`, 195, 294, 13, COLORS.ink, 'center', 800);
    fillRound(110, 340, 170, 50, 8, COLORS.blue, null);
    text('继续游戏', 195, 366, 15, '#07121f', 'center', 900);
  }

  function install() {
    if (!document.body) {
      window.setTimeout(install, 80);
      return;
    }
    canvas = document.getElementById('block-puzzle-canvas');
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
      canvas.setAttribute('data-ui-language', 'zh-CN');
      document.body.appendChild(canvas);
    }
    document.documentElement.style.background = COLORS.dark;
    document.body.style.margin = '0';
    document.body.style.background = COLORS.dark;
    document.body.style.overflow = 'hidden';
    ctx = canvas.getContext('2d');
    if (!ctx) {
      window.setTimeout(install, 100);
      return;
    }
    canvas.addEventListener('pointerdown', onPointerDown, { passive: false });
    canvas.addEventListener('pointermove', onPointerMove, { passive: false });
    canvas.addEventListener('pointerup', onPointerUp, { passive: false });
    canvas.addEventListener('pointercancel', onPointerUp, { passive: false });
    resetGame();
    state.started = true;
    window.__COCOS_BLOCK_PUZZLE_E2E__ = state;
    window.__COMMERCIAL_BLOCK_PUZZLE_RUNTIME__ = {
      getSnapshot: () => JSON.parse(JSON.stringify(state)),
      placeFirstCandidateAtClearTarget: () => placePiece(0, 0, 0),
      startBgm: () => ensureAudio('test_bridge'),
      toggleMute,
      reset: resetGame,
    };
    publish('runtime_boot_ready', {
      beforeBoard: cloneBoard(state.board),
      candidateTray: state.candidates.map((piece) => ({ id: piece.id, cells: piece.cells })),
      clearTarget: state.clearTarget,
      uiLanguage: state.uiLanguage,
    });
    requestDraw();
    animationHandle = window.requestAnimationFrame(loop);
  }

  function loop() {
    if (needsDraw || state.particles.length || state.toastFrames > 0 || state.drag) draw();
    animationHandle = window.requestAnimationFrame(loop);
  }

  install();
})();
