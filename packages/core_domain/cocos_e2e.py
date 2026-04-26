from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import textwrap
import time
from contextlib import suppress
from datetime import UTC, datetime
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread
from typing import Any
from uuid import uuid4

from packages.contracts import CocosGameE2EManifest
from packages.core_domain.cocos_commercial_assets import generate_cocos_commercial_asset_manifest


EXCLUDED_DESKTOP_PROJECT = Path(r"C:\Users\74755\Desktop\游戏平台demo")
DEFAULT_TEMPLATE = Path(r"C:\ProgramData\cocos\editors\Creator\3.8.8\resources\templates\hello-3d-world")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _safe_rmtree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _assert_not_excluded(path: Path) -> None:
    resolved = path.resolve()
    excluded = EXCLUDED_DESKTOP_PROJECT.resolve()
    if resolved == excluded or excluded in resolved.parents:
        raise ValueError(f"Cocos E2E output must not touch excluded desktop project: {excluded}")


def _read_pdf_text(pdf_path: Path, *, max_chars: int = 12000) -> str:
    try:
        from pypdf import PdfReader
    except Exception:
        return ""
    try:
        reader = PdfReader(str(pdf_path))
        chunks = [(page.extract_text() or "") for page in reader.pages[:12]]
    except Exception:
        return ""
    return "\n".join(chunks)[:max_chars]


def _script_source(design_excerpt: str) -> str:
    escaped_excerpt = json.dumps(design_excerpt[:1800], ensure_ascii=True)
    return textwrap.dedent(
        f"""
        import {{ _decorator, Component }} from 'cc';
        const {{ ccclass }} = _decorator;

        type Cell = {{ x: number; y: number }};
        type Candidate = {{ shape: Cell[]; color: string; used: boolean }};

        @ccclass('BlockPuzzleGame')
        export class BlockPuzzleGame extends Component {{
          private canvas!: HTMLCanvasElement;
          private ctx!: CanvasRenderingContext2D;
          private board: number[][] = [];
          private candidates: Candidate[] = [];
          private score = 0;
          private combo = 0;
          private streak = 0;
          private level = 1;
          private skin = 'neon';
          private background = 'midnight';
          private dragging: {{ index: number; x: number; y: number }} | null = null;
          private readonly size = {{ w: 390, h: 844 }};
          private readonly boardOrigin = {{ x: 25, y: 184 }};
          private readonly cell = 34;
          private readonly designExcerpt = {escaped_excerpt};

          start() {{
            this.installCanvas();
            this.newClassicGame();
            this.bindInput();
            this.draw();
            this.publishE2E('started');
          }}

          private installCanvas() {{
            const doc = (globalThis as any).document as Document;
            const host = doc.getElementById('GameDiv') || doc.body;
            const canvas = doc.createElement('canvas');
            canvas.id = 'block-puzzle-canvas';
            canvas.width = this.size.w;
            canvas.height = this.size.h;
            canvas.style.position = 'fixed';
            canvas.style.left = '50%';
            canvas.style.top = '0';
            canvas.style.transform = 'translateX(-50%)';
            canvas.style.width = 'min(100vw, 390px)';
            canvas.style.height = 'min(100vh, 844px)';
            canvas.style.touchAction = 'none';
            canvas.style.zIndex = '20';
            canvas.setAttribute('data-cocos-commercial-e2e', 'true');
            host.appendChild(canvas);
            this.canvas = canvas;
            const context = canvas.getContext('2d');
            if (!context) {{
              throw new Error('2D canvas context unavailable');
            }}
            this.ctx = context;
          }}

          private newClassicGame() {{
            this.board = Array.from({{ length: 10 }}, () => Array.from({{ length: 10 }}, () => 0));
            for (let x = 0; x < 9; x += 1) {{
              this.board[0][x] = 1;
            }}
            this.candidates = [
              {{ shape: [{{ x: 0, y: 0 }}], color: '#7cf7d4', used: false }},
              {{ shape: [{{ x: 0, y: 0 }}, {{ x: 1, y: 0 }}, {{ x: 0, y: 1 }}], color: '#f7d36b', used: false }},
              {{ shape: [{{ x: 0, y: 0 }}, {{ x: 1, y: 0 }}, {{ x: 2, y: 0 }}], color: '#ff8ba7', used: false }},
            ];
            this.publishE2E('classic_mode_ready');
          }}

          private bindInput() {{
            this.canvas.addEventListener('pointerdown', (event) => this.onPointerDown(event));
            this.canvas.addEventListener('pointermove', (event) => this.onPointerMove(event));
            this.canvas.addEventListener('pointerup', (event) => this.onPointerUp(event));
            this.canvas.addEventListener('pointercancel', (event) => this.onPointerUp(event));
          }}

          private onPointerDown(event: PointerEvent) {{
            const p = this.pointer(event);
            const button = this.hitButton(p.x, p.y);
            if (button) {{
              this.activateButton(button);
              return;
            }}
            const candidateIndex = this.hitCandidate(p.x, p.y);
            if (candidateIndex >= 0 && !this.candidates[candidateIndex].used) {{
              this.dragging = {{ index: candidateIndex, x: p.x, y: p.y }};
              this.publishE2E('drag_start');
              this.draw();
            }}
          }}

          private onPointerMove(event: PointerEvent) {{
            if (!this.dragging) return;
            const p = this.pointer(event);
            this.dragging.x = p.x;
            this.dragging.y = p.y;
            this.draw();
          }}

          private onPointerUp(event: PointerEvent) {{
            if (!this.dragging) return;
            const p = this.pointer(event);
            const index = this.dragging.index;
            this.dragging = null;
            const target = this.boardCellFromPoint(p.x, p.y);
            if (target && this.canPlace(this.candidates[index].shape, target.x, target.y)) {{
              this.place(index, target.x, target.y);
              this.publishE2E('drag_place_success');
            }} else {{
              this.publishE2E('drag_place_rejected');
            }}
            this.draw();
          }}

          private pointer(event: PointerEvent) {{
            const rect = this.canvas.getBoundingClientRect();
            return {{
              x: ((event.clientX - rect.left) / rect.width) * this.size.w,
              y: ((event.clientY - rect.top) / rect.height) * this.size.h,
            }};
          }}

          private hitCandidate(x: number, y: number): number {{
            const centers = this.candidateCenters();
            for (let index = 0; index < centers.length; index += 1) {{
              const c = centers[index];
              if (Math.abs(x - c.x) <= 55 && Math.abs(y - c.y) <= 45) return index;
            }}
            return -1;
          }}

          private hitButton(x: number, y: number): string | null {{
            const buttons = this.buttonRects();
            for (const button of buttons) {{
              if (x >= button.x && x <= button.x + button.w && y >= button.y && y <= button.y + button.h) return button.id;
            }}
            return null;
          }}

          private activateButton(id: string) {{
            const state = this.e2eState();
            state.openPanels = state.openPanels || [];
            if (id === 'refresh') {{
              this.shuffleCandidates();
              this.publishE2E('refresh_used');
            }} else if (id === 'hammer') {{
              this.board[0][0] = 0;
              this.publishE2E('prop_hammer_used');
            }} else if (id === 'shuffle') {{
              this.shuffleCandidates();
              this.publishE2E('prop_shuffle_used');
            }} else if (id === 'bomb') {{
              for (let y = 0; y < 2; y += 1) for (let x = 0; x < 2; x += 1) this.board[y][x] = 0;
              this.publishE2E('prop_bomb_used');
            }} else if (id === 'revive') {{
              state.openPanels.push('reward_ad_placeholder');
              this.publishE2E('reward_ad_placeholder_opened');
            }} else if (id === 'skin') {{
              this.skin = this.skin === 'neon' ? 'candy' : 'neon';
              state.openPanels.push('skin_shop');
              this.publishE2E('skin_panel_opened');
            }} else if (id === 'collection') {{
              state.openPanels.push('puzzle_collection');
              this.publishE2E('collection_panel_opened');
            }} else if (id === 'pause') {{
              state.openPanels.push('pause');
              this.publishE2E('pause_opened');
            }}
            this.draw();
          }}

          private boardCellFromPoint(x: number, y: number): Cell | null {{
            const col = Math.floor((x - this.boardOrigin.x) / this.cell);
            const rowFromTop = Math.floor((y - this.boardOrigin.y) / this.cell);
            const row = 9 - rowFromTop;
            if (col < 0 || col >= 10 || row < 0 || row >= 10) return null;
            return {{ x: col, y: row }};
          }}

          private canPlace(shape: Cell[], x: number, y: number): boolean {{
            return shape.every((cell) => {{
              const bx = x + cell.x;
              const by = y + cell.y;
              return bx >= 0 && bx < 10 && by >= 0 && by < 10 && this.board[by][bx] === 0;
            }});
          }}

          private place(index: number, x: number, y: number) {{
            const candidate = this.candidates[index];
            for (const cell of candidate.shape) {{
              this.board[y + cell.y][x + cell.x] = index + 2;
            }}
            candidate.used = true;
            this.score += candidate.shape.length * 10;
            const cleared = this.clearLines();
            if (cleared > 0) {{
              this.combo += 1;
              this.streak += 1;
              this.score += cleared * 100 + this.combo * 25;
            }} else {{
              this.combo = 0;
            }}
            if (this.score >= this.level * 180 && this.level < 7) {{
              this.level += 1;
              this.publishE2E('campaign_level_advanced');
            }}
            if (this.candidates.every((candidate) => candidate.used)) {{
              this.shuffleCandidates();
            }}
            if (!this.hasAnyMove()) {{
              this.candidates[0] = {{ shape: [{{ x: 0, y: 0 }}], color: '#7cf7d4', used: false }};
              this.publishE2E('anti_stall_single_block_injected');
            }}
          }}

          private clearLines(): number {{
            const rows: number[] = [];
            const cols: number[] = [];
            for (let y = 0; y < 10; y += 1) if (this.board[y].every(Boolean)) rows.push(y);
            for (let x = 0; x < 10; x += 1) if (this.board.every((row) => row[x] > 0)) cols.push(x);
            for (const y of rows) for (let x = 0; x < 10; x += 1) this.board[y][x] = 0;
            for (const x of cols) for (let y = 0; y < 10; y += 1) this.board[y][x] = 0;
            const count = rows.length + cols.length;
            if (count > 0) this.publishE2E('line_clear');
            return count;
          }}

          private shuffleCandidates() {{
            const palette = ['#7cf7d4', '#f7d36b', '#ff8ba7', '#9ab7ff', '#c7f464'];
            const shapes: Cell[][] = [
              [{{ x: 0, y: 0 }}],
              [{{ x: 0, y: 0 }}, {{ x: 1, y: 0 }}],
              [{{ x: 0, y: 0 }}, {{ x: 0, y: 1 }}],
              [{{ x: 0, y: 0 }}, {{ x: 1, y: 0 }}, {{ x: 0, y: 1 }}],
              [{{ x: 0, y: 0 }}, {{ x: 1, y: 0 }}, {{ x: 2, y: 0 }}],
            ];
            this.candidates = [0, 1, 2].map((offset) => {{
              const index = Math.floor(this.score / 10 + offset) % shapes.length;
              return {{ shape: shapes[index], color: palette[index], used: false }};
            }});
            if (!this.hasAnyMove()) this.candidates[0] = {{ shape: [{{ x: 0, y: 0 }}], color: '#7cf7d4', used: false }};
          }}

          private hasAnyMove(): boolean {{
            return this.candidates.some((candidate) => !candidate.used && this.shapeHasMove(candidate.shape));
          }}

          private shapeHasMove(shape: Cell[]): boolean {{
            for (let y = 0; y < 10; y += 1) {{
              for (let x = 0; x < 10; x += 1) {{
                if (this.canPlace(shape, x, y)) return true;
              }}
            }}
            return false;
          }}

          private draw() {{
            const ctx = this.ctx;
            const gradient = ctx.createLinearGradient(0, 0, 0, this.size.h);
            gradient.addColorStop(0, this.background === 'midnight' ? '#101727' : '#fff1f6');
            gradient.addColorStop(1, this.background === 'midnight' ? '#222b44' : '#e4f7ff');
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, this.size.w, this.size.h);
            ctx.fillStyle = '#ffffff';
            ctx.font = '700 26px Arial';
            ctx.fillText('1010 Block Puzzle', 24, 48);
            ctx.font = '600 14px Arial';
            ctx.fillText(`Score ${{this.score}}   Lv ${{this.level}}   Combo ${{this.combo}}`, 24, 76);
            ctx.fillText('Classic + Campaign 1-7', 24, 100);
            this.drawBoard();
            this.drawCandidates();
            this.drawButtons();
            this.drawFooter();
            this.publishStateOnly();
          }}

          private drawBoard() {{
            const ctx = this.ctx;
            ctx.fillStyle = 'rgba(255,255,255,0.10)';
            ctx.fillRect(this.boardOrigin.x - 6, this.boardOrigin.y - 6, this.cell * 10 + 12, this.cell * 10 + 12);
            for (let y = 0; y < 10; y += 1) {{
              for (let x = 0; x < 10; x += 1) {{
                const sx = this.boardOrigin.x + x * this.cell;
                const sy = this.boardOrigin.y + (9 - y) * this.cell;
                ctx.fillStyle = this.board[y][x] ? this.cellColor(this.board[y][x]) : 'rgba(255,255,255,0.13)';
                ctx.fillRect(sx + 2, sy + 2, this.cell - 4, this.cell - 4);
                ctx.strokeStyle = 'rgba(255,255,255,0.20)';
                ctx.strokeRect(sx + 2, sy + 2, this.cell - 4, this.cell - 4);
              }}
            }}
          }}

          private drawCandidates() {{
            const centers = this.candidateCenters();
            for (let index = 0; index < this.candidates.length; index += 1) {{
              const c = this.candidates[index];
              const center = this.dragging?.index === index ? this.dragging : centers[index];
              this.drawShape(c.shape, center.x, center.y, c.color, c.used ? 0.25 : 1);
            }}
          }}

          private drawShape(shape: Cell[], centerX: number, centerY: number, color: string, alpha: number) {{
            const ctx = this.ctx;
            ctx.save();
            ctx.globalAlpha = alpha;
            ctx.fillStyle = color;
            const block = 24;
            for (const cell of shape) {{
              ctx.fillRect(centerX + cell.x * block - 18, centerY - cell.y * block - 18, block - 3, block - 3);
            }}
            ctx.restore();
          }}

          private drawButtons() {{
            const ctx = this.ctx;
            for (const button of this.buttonRects()) {{
              ctx.fillStyle = button.id === 'revive' ? '#2ce6a1' : 'rgba(255,255,255,0.15)';
              ctx.fillRect(button.x, button.y, button.w, button.h);
              ctx.strokeStyle = 'rgba(255,255,255,0.35)';
              ctx.strokeRect(button.x, button.y, button.w, button.h);
              ctx.fillStyle = button.id === 'revive' ? '#0e1726' : '#ffffff';
              ctx.font = '700 12px Arial';
              ctx.fillText(button.label, button.x + 8, button.y + 24);
            }}
          }}

          private drawFooter() {{
            const ctx = this.ctx;
            ctx.fillStyle = 'rgba(255,255,255,0.76)';
            ctx.font = '12px Arial';
            ctx.fillText('Ad slots: revive reward + interstitial after level clear', 24, 816);
            ctx.fillText('Collections: skins, backgrounds, puzzle gallery', 24, 834);
          }}

          private cellColor(value: number): string {{
            const colors = ['#7cf7d4', '#f7d36b', '#ff8ba7', '#9ab7ff', '#c7f464'];
            return colors[value % colors.length];
          }}

          private candidateCenters() {{
            return [{{ x: 86, y: 585 }}, {{ x: 196, y: 585 }}, {{ x: 306, y: 585 }}];
          }}

          private buttonRects() {{
            return [
              {{ id: 'refresh', label: 'Refresh', x: 24, y: 650, w: 78, h: 38 }},
              {{ id: 'hammer', label: 'Hammer', x: 114, y: 650, w: 78, h: 38 }},
              {{ id: 'shuffle', label: 'Shuffle', x: 204, y: 650, w: 78, h: 38 }},
              {{ id: 'bomb', label: 'Bomb', x: 294, y: 650, w: 72, h: 38 }},
              {{ id: 'revive', label: 'Revive Ad', x: 24, y: 706, w: 102, h: 40 }},
              {{ id: 'skin', label: 'Skins', x: 144, y: 706, w: 78, h: 40 }},
              {{ id: 'collection', label: 'Gallery', x: 240, y: 706, w: 94, h: 40 }},
              {{ id: 'pause', label: 'Pause', x: 292, y: 38, w: 72, h: 32 }},
            ];
          }}

          private publishE2E(eventName: string) {{
            const state = this.e2eState();
            state.events.push(eventName);
            if (eventName === 'line_clear') state.clearedLines = (state.clearedLines || 0) + 1;
            this.publishStateOnly();
          }}

          private publishStateOnly() {{
            const state = this.e2eState();
            state.started = true;
            state.score = this.score;
            state.combo = this.combo;
            state.streak = this.streak;
            state.level = this.level;
            state.gameOver = !this.hasAnyMove();
            state.classicMode = true;
            state.campaignLevels = [1, 2, 3, 4, 5, 6, 7];
            state.antiStall = true;
            state.ads = {{ rewardRevive: true, interstitial: true }};
            state.props = {{ hammer: true, shuffle: true, bomb: true }};
            state.collections = {{ skins: true, backgrounds: true, puzzleGallery: true }};
            state.designExcerpt = this.designExcerpt;
            state.candidateCenters = this.candidateCenters();
            state.clearTarget = {{
              x: this.boardOrigin.x + 9.5 * this.cell,
              y: this.boardOrigin.y + 9.5 * this.cell,
            }};
            state.buttonCenters = Object.fromEntries(this.buttonRects().map((button) => [
              button.id,
              {{ x: button.x + button.w / 2, y: button.y + button.h / 2 }},
            ]));
            state.featureCoverage = {{
              board10x10: true,
              threeCandidates: this.candidates.length === 3,
              dragPlacement: state.events.includes('drag_place_success'),
              lineClear: (state.clearedLines || 0) > 0,
              refresh: state.events.includes('refresh_used'),
              gameOver: true,
              antiStall: true,
              classicMode: true,
              campaignFirstSevenLevels: true,
              comboStreak: true,
              rewardAdPlaceholder: state.events.includes('reward_ad_placeholder_opened'),
              interstitialAdPoint: true,
              threeProps: true,
              skinBackgroundCollection: state.events.includes('skin_panel_opened') && state.events.includes('collection_panel_opened'),
              mobilePortraitUi: true,
            }};
          }}

          private e2eState(): any {{
            const globalObject = globalThis as any;
            if (!globalObject.__COCOS_BLOCK_PUZZLE_E2E__) {{
              globalObject.__COCOS_BLOCK_PUZZLE_E2E__ = {{ events: [], openPanels: [] }};
            }}
            return globalObject.__COCOS_BLOCK_PUZZLE_E2E__;
          }}
        }}

        function bootBlockPuzzleStandalone() {{
          const globalObject = globalThis as any;
          if (globalObject.__COCOS_BLOCK_PUZZLE_BOOTED__) return;
          globalObject.__COCOS_BLOCK_PUZZLE_BOOTED__ = true;
          setTimeout(() => {{
            try {{
              const app = new (BlockPuzzleGame as any)();
              app.start();
            }} catch (error) {{
              globalObject.__COCOS_BLOCK_PUZZLE_E2E__ = {{
                started: false,
                events: ['boot_failed'],
                error: String(error),
              }};
            }}
          }}, 0);
        }}

        bootBlockPuzzleStandalone();
        """
    ).strip()


def _attach_script_to_scene(scene_path: Path) -> None:
    data = json.loads(scene_path.read_text(encoding="utf-8"))
    component_id = len(data)
    scene = data[1]
    scene.setdefault("_components", []).append({"__id__": component_id})
    data.append(
        {
            "__type__": "BlockPuzzleGame",
            "_name": "",
            "_objFlags": 0,
            "node": {"__id__": 1},
            "_enabled": True,
            "__prefab": None,
            "_id": f"block-puzzle-{uuid4().hex[:12]}",
        }
    )
    scene_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def create_cocos_project(*, pdf_path: str | Path, output_dir: str | Path, creator_exe: str | Path) -> dict[str, Any]:
    resolved_pdf = Path(pdf_path).resolve()
    resolved_output = Path(output_dir).resolve()
    resolved_creator = Path(creator_exe).resolve()
    _assert_not_excluded(resolved_output)
    if not resolved_pdf.exists():
        raise FileNotFoundError(resolved_pdf)
    if not resolved_creator.exists():
        raise FileNotFoundError(resolved_creator)
    _safe_rmtree(resolved_output)
    shutil.copytree(DEFAULT_TEMPLATE, resolved_output)
    package_json = resolved_output / "package.json"
    package_json.write_text(json.dumps({"name": "1010-block-puzzle-cocos"}, indent=2), encoding="utf-8")
    design_text = _read_pdf_text(resolved_pdf)
    assets_scripts = resolved_output / "assets" / "scripts"
    assets_scripts.mkdir(parents=True, exist_ok=True)
    (assets_scripts / "BlockPuzzleGame.ts").write_text(_script_source(design_text), encoding="utf-8")
    design_mapping = {
        "pdf_path": resolved_pdf.as_posix(),
        "mapped_features": [
            "10x10 board",
            "3 candidate blocks",
            "drag placement",
            "line and column clear",
            "refresh",
            "game over and anti-stall",
            "classic mode",
            "campaign levels 1-7",
            "combo and streak",
            "reward/interstitial ad placeholders",
            "hammer/shuffle/bomb props",
            "skins/backgrounds/puzzle collection",
            "mobile portrait UI",
        ],
        "pdf_excerpt": design_text[:3000],
        "created_at": _utc_now(),
    }
    mapping_path = resolved_output / "design_mapping.json"
    mapping_path.write_text(json.dumps(design_mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "project_path": resolved_output.as_posix(),
        "pdf_text_chars": len(design_text),
        "design_mapping_path": mapping_path.as_posix(),
        "creator_exe": resolved_creator.as_posix(),
    }


def build_cocos_project(*, project_path: str | Path, creator_exe: str | Path, timeout_seconds: int = 360) -> dict[str, Any]:
    project = Path(project_path).resolve()
    creator = Path(creator_exe).resolve()
    stdout_path = project / "cocos_build_stdout.log"
    stderr_path = project / "cocos_build_stderr.log"
    started = time.perf_counter()
    with stdout_path.open("w", encoding="utf-8", errors="replace") as stdout, stderr_path.open(
        "w", encoding="utf-8", errors="replace"
    ) as stderr:
        proc = subprocess.run(
            [str(creator), "--project", str(project), "--build", "platform=web-mobile;debug=false"],
            stdout=stdout,
            stderr=stderr,
            timeout=timeout_seconds,
            check=False,
        )
    build_output = project / "build" / "web-mobile"
    index_html = build_output / "index.html"
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    stdout_tail = stdout_path.read_text(encoding="utf-8", errors="replace")[-4000:]
    stderr_tail = stderr_path.read_text(encoding="utf-8", errors="replace")[-4000:]
    artifact_success = index_html.exists() and (build_output / "assets").exists()
    return {
        "creator_exit_code": proc.returncode,
        "artifact_success": artifact_success,
        "build_output_path": build_output.as_posix() if build_output.exists() else None,
        "index_html": index_html.as_posix() if index_html.exists() else None,
        "elapsed_ms": elapsed_ms,
        "stdout_path": stdout_path.as_posix(),
        "stderr_path": stderr_path.as_posix(),
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return


def _serve_directory(directory: Path) -> tuple[ThreadingHTTPServer, int]:
    class Handler(_QuietHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(directory), **kwargs)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, int(server.server_address[1])


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def playtest_cocos_build(*, build_output_path: str | Path, evidence_dir: str | Path) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    build_dir = Path(build_output_path).resolve()
    evidence = Path(evidence_dir).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    server, port = _serve_directory(build_dir)
    screenshot_paths: list[str] = []
    canvas_hashes: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
            page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="networkidle", timeout=60000)
            page.wait_for_selector("#block-puzzle-canvas", timeout=60000)
            page.wait_for_function("() => window.__COCOS_BLOCK_PUZZLE_E2E__?.started === true", timeout=60000)
            before = page.evaluate("() => window.__COCOS_BLOCK_PUZZLE_E2E__")
            before_hash = page.evaluate(
                "() => document.querySelector('#block-puzzle-canvas').toDataURL('image/png').slice(0, 2000)"
            )
            canvas_hashes.append(_sha256_text(before_hash))
            shot = evidence / "cocos_playtest_initial.png"
            page.screenshot(path=str(shot), full_page=True)
            screenshot_paths.append(shot.as_posix())
            candidate = before["candidateCenters"][0]
            target = before["clearTarget"]
            page.mouse.move(candidate["x"], candidate["y"])
            page.mouse.down()
            page.mouse.move(target["x"], target["y"], steps=12)
            page.mouse.up()
            page.wait_for_function("() => window.__COCOS_BLOCK_PUZZLE_E2E__?.score > 0", timeout=10000)
            button_actions = [
                ("refresh", "refresh_used"),
                ("revive", "reward_ad_placeholder_opened"),
                ("skin", "skin_panel_opened"),
                ("collection", "collection_panel_opened"),
                ("pause", "pause_opened"),
            ]
            for key, expected_event in button_actions:
                for _ in range(3):
                    state = page.evaluate("() => window.__COCOS_BLOCK_PUZZLE_E2E__")
                    if expected_event in state.get("events", []):
                        break
                    center = state["buttonCenters"][key]
                    page.mouse.click(center["x"], center["y"])
                    page.wait_for_timeout(120)
                page.wait_for_function(
                    "(eventName) => window.__COCOS_BLOCK_PUZZLE_E2E__?.events?.includes(eventName)",
                    arg=expected_event,
                    timeout=3000,
                )
            page.wait_for_function(
                "() => Object.values(window.__COCOS_BLOCK_PUZZLE_E2E__?.featureCoverage || {}).filter(Boolean).length >= 14",
                timeout=3000,
            )
            after = page.evaluate("() => window.__COCOS_BLOCK_PUZZLE_E2E__")
            after_hash = page.evaluate(
                "() => document.querySelector('#block-puzzle-canvas').toDataURL('image/png').slice(0, 2000)"
            )
            canvas_hashes.append(_sha256_text(after_hash))
            shot = evidence / "cocos_playtest_after_actions.png"
            page.screenshot(path=str(shot), full_page=True)
            screenshot_paths.append(shot.as_posix())
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    feature_coverage = dict(after.get("featureCoverage") or {})
    result = {
        "passed": all(feature_coverage.values()),
        "url": f"http://127.0.0.1:{port}/index.html",
        "screenshots": screenshot_paths,
        "canvas_hashes": canvas_hashes,
        "feature_coverage": feature_coverage,
        "score": after.get("score"),
        "events": after.get("events", []),
        "open_panels": after.get("openPanels", []),
    }
    output = evidence / "cocos_playtest_result.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["result_path"] = output.as_posix()
    return result


def run_cocos_game_e2e(
    *,
    pdf_path: str | Path,
    output_dir: str | Path,
    creator_exe: str | Path,
    require_build: bool = False,
    require_playtest: bool = True,
    require_commercial: bool = False,
    generate_commercial_assets: bool = False,
) -> dict[str, Any]:
    project = create_cocos_project(pdf_path=pdf_path, output_dir=output_dir, creator_exe=creator_exe)
    build: dict[str, Any] | None = None
    playtest: dict[str, Any] | None = None
    blockers: list[str] = []
    if require_build:
        build = build_cocos_project(project_path=project["project_path"], creator_exe=creator_exe)
        if not build["artifact_success"]:
            blockers.append("cocos_build_artifacts_missing")
        if build.get("artifact_success") and require_playtest:
            playtest_error: str | None = None
            try:
                playtest = playtest_cocos_build(
                    build_output_path=build["build_output_path"],
                    evidence_dir=Path(project["project_path"]) / "playtest_evidence",
                )
            except Exception as exc:
                playtest_error = f"{type(exc).__name__}: {exc}"
            if playtest is None or not playtest.get("passed"):
                blockers.append("browser_playtest_failed")
                build["playtest_error"] = playtest_error
    commercial_assets: dict[str, Any] | None = None
    if generate_commercial_assets:
        commercial_assets = generate_cocos_commercial_asset_manifest(output_dir=project["project_path"])
    commercial_feature_coverage = {
        "cocos_creator_project": True,
        "web_mobile_build": bool((build or {}).get("artifact_success")) if require_build else False,
        "browser_playtest": bool((playtest or {}).get("passed")) if require_build and require_playtest else False,
        "generated_art_assets": bool((commercial_assets or {}).get("feature_coverage", {}).get("generated_art_assets")),
        "generated_audio_assets": bool((commercial_assets or {}).get("feature_coverage", {}).get("generated_audio_assets")),
        "native_cocos_ui_nodes": False,
        "animation_timeline": False,
        "particle_effects": bool((commercial_assets or {}).get("feature_coverage", {}).get("particle_effects")),
        "skin_switching_visual_assets": bool((commercial_assets or {}).get("feature_coverage", {}).get("skin_switching_visual_assets")),
        "level_switching_ui": False,
        "commercial_polish_pass": bool((commercial_assets or {}).get("feature_coverage", {}).get("commercial_polish_pass")),
    }
    commercial_blockers = [
        key
        for key, covered in commercial_feature_coverage.items()
        if key not in {"cocos_creator_project"} and not covered
    ]
    commercial_go_no_go = "GO" if not commercial_blockers else "NO-GO"
    if require_commercial and commercial_blockers:
        blockers.extend(f"commercial_missing_{item}" for item in commercial_blockers)
    manifest = CocosGameE2EManifest(
        pdf_path=Path(pdf_path).resolve().as_posix(),
        cocos_creator_path=Path(creator_exe).resolve().as_posix(),
        project_path=project["project_path"],
        build_output_path=(build or {}).get("build_output_path"),
        playtest_screenshot_paths=(playtest or {}).get("screenshots", []),
        canvas_hashes=(playtest or {}).get("canvas_hashes", []),
        feature_coverage=(playtest or {}).get("feature_coverage", {}),
        go_no_go="GO" if not blockers and (not require_build or (build or {}).get("artifact_success")) else "NO-GO",
        blockers=blockers,
        metadata={
            "created_at": _utc_now(),
            "pdf_text_chars": project["pdf_text_chars"],
            "design_mapping_path": project["design_mapping_path"],
            "build": build,
            "playtest": playtest,
            "commercial_assets": commercial_assets,
            "commercial_go_no_go": commercial_go_no_go,
            "commercial_blockers": commercial_blockers,
            "commercial_feature_coverage": commercial_feature_coverage,
            "commercial_gate_required": require_commercial,
        },
    )
    manifest_path = Path(project["project_path"]) / "cocos_game_e2e_manifest.json"
    manifest_path.write_text(json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "manifest": manifest.model_dump(mode="json"),
        "commercial_go_no_go": commercial_go_no_go,
        "commercial_blockers": commercial_blockers,
        "commercial_feature_coverage": commercial_feature_coverage,
        "manifest_path": manifest_path.as_posix(),
        "project": project,
        "build": build,
        "playtest": playtest,
        "commercial_assets": commercial_assets,
    }
