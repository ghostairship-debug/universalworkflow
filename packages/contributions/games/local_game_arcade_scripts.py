from __future__ import annotations


def _block_puzzle_html_suffix() -> str:
    return """  </div>

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
    let boosters = { refresh: 1, line: 1, shuffle: 1 };
    let dragIndex = null;
    let previewCells = [];
    let lastHoverKey = '';
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
    function haptic(pattern) {
      if (navigator.vibrate) navigator.vibrate(pattern);
    }
    function showCombo(text) {
      const banner = $('comboBanner');
      banner.textContent = text;
      banner.classList.remove('show');
      void banner.offsetWidth;
      banner.classList.add('show');
    }
    function clearPreview() {
      previewCells.forEach(cell => cell.classList.remove('preview-ok', 'preview-bad'));
      previewCells = [];
      lastHoverKey = '';
      $('board').classList.remove('drag-active');
    }
    function pieceForDrag() {
      const index = dragIndex !== null ? dragIndex : selected;
      return index !== null && pieces[index] ? pieces[index] : null;
    }
    function paintPreview(row, col) {
      const piece = pieceForDrag();
      clearPreview();
      if (!piece) return;
      $('board').classList.add('drag-active');
      const ok = canPlace(piece, row, col);
      const cells = cellsOf(piece, row, col).filter(([r, c]) => r >= 0 && c >= 0 && r < SIZE && c < SIZE);
      const paintTargets = cells.length ? cells : [[row, col]];
      paintTargets.forEach(([r, c]) => {
        const cell = document.querySelector('[data-row="' + r + '"][data-col="' + c + '"]');
        if (!cell) return;
        cell.classList.add(ok ? 'preview-ok' : 'preview-bad');
        previewCells.push(cell);
      });
      const hoverKey = row + '-' + col + '-' + ok;
      if (hoverKey !== lastHoverKey) {
        haptic(ok ? 8 : 18);
        lastHoverKey = hoverKey;
      }
    }
    function cellFromPoint(clientX, clientY) {
      const node = document.elementFromPoint(clientX, clientY);
      const cell = node ? node.closest('.cell') : null;
      if (!cell) return null;
      return { row: Number(cell.dataset.row), col: Number(cell.dataset.col) };
    }
    function renderMiniPiece(piece, target, cellSize = 20) {
      target.replaceChildren();
      const grid = document.createElement('div');
      grid.className = 'mini-grid';
      grid.style.gridTemplateColumns = 'repeat(' + piece.shape[0].length + ', ' + cellSize + 'px)';
      const tone = colors[piece.color];
      piece.shape.forEach(row => row.forEach(on => {
        const dot = document.createElement('span');
        dot.className = 'mini-cell' + (on ? ' on' : '');
        dot.style.width = cellSize + 'px';
        dot.style.height = cellSize + 'px';
        dot.style.setProperty('--tone-a', tone[0]);
        dot.style.setProperty('--tone-b', tone[1]);
        grid.appendChild(dot);
      }));
      target.appendChild(grid);
    }
    function moveGhost(clientX, clientY) {
      const ghost = $('dragGhost');
      ghost.style.transform = 'translate(' + (clientX - 40) + 'px, ' + (clientY - 126) + 'px)';
    }
    function startDrag(index, clientX, clientY) {
      if (!pieces[index]) return;
      selected = index;
      dragIndex = index;
      const ghost = $('dragGhost');
      renderMiniPiece(pieces[index], ghost, 22);
      ghost.classList.add('active');
      moveGhost(clientX, clientY);
      $('board').classList.add('drag-active');
      log('开始拖拽候选方块 ' + (index + 1));
    }
    function finishDrag(clientX, clientY) {
      const target = cellFromPoint(clientX, clientY);
      const activeIndex = dragIndex;
      $('dragGhost').classList.remove('active');
      dragIndex = null;
      clearPreview();
      if (target && activeIndex !== null) {
        selected = activeIndex;
        placeSelected(target.row, target.col);
      } else {
        render();
      }
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
        const feedback = (count > 1 ? 'Combo x' + count + ' · ' : '') + (streak >= 3 ? 'Streak x' + streak : '消除成功');
        toast(feedback);
        showCombo(feedback);
        haptic([30, 30, 60]);
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
        haptic(25);
        return;
      }
      clearPreview();
      const cells = cellsOf(piece, row, col);
      cells.forEach(([r, c]) => board[r][c] = { color: piece.color });
      score += cells.length;
      pieces[selected] = null;
      selected = null;
      haptic(10);
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
    function clearMostCrowdedLine() {
      const rows = board.map((row, r) => ({ kind: 'row', index: r, density: row.filter(Boolean).length }));
      const cols = Array.from({ length: SIZE }, (_, c) => ({ kind: 'col', index: c, density: board.filter(row => row[c]).length }));
      const target = rows.concat(cols).sort((a, b) => b.density - a.density)[0];
      if (!target || target.density <= 0) return false;
      if (target.kind === 'row') {
        for (let c = 0; c < SIZE; c++) board[target.index][c] = null;
      } else {
        for (let r = 0; r < SIZE; r++) board[r][target.index] = null;
      }
      return true;
    }
    function revive() {
      if (revives <= 0) return;
      revives--;
      for (let i = 0; i < 3; i++) clearMostCrowdedLine();
      closeModal('gameOverModal');
      toast('广告复活成功');
      log('模拟激励视频复活，清理最拥挤 3 行/列');
      render();
    }
    function useRefreshBooster() {
      if (boosters.refresh <= 0) return;
      const targetIndex = selected !== null && pieces[selected] ? selected : pieces.findIndex(Boolean);
      if (targetIndex < 0) return;
      pieces[targetIndex] = randomPiece();
      boosters.refresh--;
      toast('刷新方块已使用');
      log('道具：刷新候选方块 ' + (targetIndex + 1));
      render();
    }
    function useLineBooster() {
      if (boosters.line <= 0) return;
      if (!clearMostCrowdedLine()) {
        toast('棋盘还很干净，暂时不用清理');
        return;
      }
      boosters.line--;
      score += 25;
      toast('横竖消除已触发');
      log('道具：清理最拥挤的一行或一列');
      render();
      checkGameOver();
    }
    function useShuffleBooster() {
      if (boosters.shuffle <= 0) return;
      const occupied = [];
      board.forEach(row => row.forEach(cell => { if (cell) occupied.push(cell); }));
      if (!occupied.length) {
        toast('棋盘为空，无需打乱');
        return;
      }
      newBoard();
      occupied.sort(() => Math.random() - .5).forEach(cell => {
        let placed = false;
        for (let attempts = 0; attempts < 80 && !placed; attempts++) {
          const r = Math.floor(Math.random() * SIZE);
          const c = Math.floor(Math.random() * SIZE);
          if (!board[r][c]) {
            board[r][c] = cell;
            placed = true;
          }
        }
      });
      boosters.shuffle--;
      toast('打乱重排完成');
      log('道具：打乱重排棋盘');
      render();
      checkGameOver();
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
      $('board').replaceChildren();
      for (let r = 0; r < SIZE; r++) {
        for (let c = 0; c < SIZE; c++) {
          const cell = document.createElement('button');
          cell.className = 'cell' + (board[r][c] ? ' filled' : '');
          cell.type = 'button';
          cell.dataset.testid = 'cell-' + r + '-' + c;
          cell.dataset.row = String(r);
          cell.dataset.col = String(c);
          cell.setAttribute('aria-label', '格子 ' + r + '-' + c);
          if (board[r][c]) {
            const tone = colors[board[r][c].color];
            cell.style.setProperty('--tone-a', tone[0]);
            cell.style.setProperty('--tone-b', tone[1]);
          }
          cell.addEventListener('click', () => placeSelected(r, c));
          cell.addEventListener('dragover', event => {
            event.preventDefault();
            paintPreview(r, c);
          });
          cell.addEventListener('drop', event => {
            event.preventDefault();
            const dropped = Number(event.dataTransfer.getData('text/plain'));
            if (!Number.isNaN(dropped)) selected = dropped;
            dragIndex = null;
            placeSelected(r, c);
          });
          $('board').appendChild(cell);
        }
      }
    }
    function renderPieces() {
      $('tray').replaceChildren();
      pieces.forEach((piece, index) => {
        const shell = document.createElement('button');
        shell.type = 'button';
        shell.className = 'piece' + (selected === index ? ' selected' : '');
        shell.dataset.testid = 'piece-' + index;
        shell.dataset.pieceIndex = String(index);
        shell.setAttribute('aria-label', piece ? '候选方块 ' + (index + 1) : '空候选槽 ' + (index + 1));
        if (!piece) {
          shell.textContent = '已放置';
        } else {
          shell.draggable = true;
          renderMiniPiece(piece, shell, 18);
          shell.addEventListener('click', () => { selected = index; render(); toast('已选择候选方块 ' + (index + 1)); });
          shell.addEventListener('dragstart', event => {
            selected = index;
            dragIndex = index;
            shell.classList.add('dragging');
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', String(index));
            log('桌面拖拽候选方块 ' + (index + 1));
          });
          shell.addEventListener('dragend', () => {
            shell.classList.remove('dragging');
            dragIndex = null;
            clearPreview();
            render();
          });
          shell.addEventListener('pointerdown', event => {
            if (event.pointerType === 'mouse') return;
            event.preventDefault();
            shell.classList.add('dragging');
            startDrag(index, event.clientX, event.clientY);
          });
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
      $('jigsaw').replaceChildren();
      for (let i = 1; i <= 7; i++) {
        const piece = document.createElement('span');
        piece.className = i <= jigsaw ? 'unlocked' : '';
        piece.textContent = i;
        $('jigsaw').appendChild(piece);
      }
    }
    function renderBoosters() {
      $('boostRefreshCount').textContent = boosters.refresh;
      $('boostLineCount').textContent = boosters.line;
      $('boostShuffleCount').textContent = boosters.shuffle;
      $('boosterRefresh').disabled = boosters.refresh <= 0;
      $('boosterLine').disabled = boosters.line <= 0;
      $('boosterShuffle').disabled = boosters.shuffle <= 0;
    }
    function render() {
      renderBoard();
      renderPieces();
      renderStats();
      renderBoosters();
    }
    function start(nextMode) {
      mode = nextMode;
      score = 0;
      revives = mode === 'classic' ? 3 : 1;
      streak = 0;
      collected = [0,0,0,0,0];
      boosters = { refresh: 1, line: 1, shuffle: 1 };
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
    $('boosterRefresh').addEventListener('click', useRefreshBooster);
    $('boosterLine').addEventListener('click', useLineBooster);
    $('boosterShuffle').addEventListener('click', useShuffleBooster);
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
    $('board').addEventListener('dragleave', event => {
      if (!$('board').contains(event.relatedTarget)) clearPreview();
    });
    document.addEventListener('pointermove', event => {
      if (dragIndex === null) return;
      moveGhost(event.clientX, event.clientY);
      const target = cellFromPoint(event.clientX, event.clientY);
      if (target) paintPreview(target.row, target.col);
      else clearPreview();
    });
    document.addEventListener('pointerup', event => {
      if (dragIndex === null) return;
      finishDrag(event.clientX, event.clientY);
    });
    start('classic');
  </script>
</body>
</html>
"""
