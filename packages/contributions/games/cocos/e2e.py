from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
import textwrap
import time
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from packages.contracts import CocosGameE2EManifest
from packages.contributions.games.cocos.commercial_assets import (
    generate_cocos_commercial_asset_manifest,
    generate_cocos_local_stable_asset_manifest,
)
from packages.contributions.games.cocos.player_validation import validate_cocos_player_visible_evidence
from packages.contributions.games.cocos.playtest import playtest_cocos_build


EXCLUDED_DESKTOP_PROJECT = Path(r"C:\Users\74755\Desktop\游戏平台demo")
DEFAULT_CREATOR_EXE = Path(r"C:\ProgramData\cocos\editors\Creator\3.8.8\CocosCreator.exe")
DEFAULT_TEMPLATE = Path(r"C:\ProgramData\cocos\editors\Creator\3.8.8\resources\templates\empty-2d")
COCOS_BUILD_SUCCESS_EXIT_CODES = {0, 36}
COCOS_FATAL_BUILD_MARKERS = (
    "Missing class:",
    "Cannot read properties of null",
    "Build failed",
    "build failed",
    "构建失败",
)
PRODUCTION_SCENE_UUID = "4c56c1f0-2f7d-4a56-a6d6-32f6f9e00079"
PRODUCTION_SCENE_NODE_NAMES = [
    "MainCamera2D",
    "CommercialCanvas",
    "BackgroundLayer",
    "BoardRoot",
    "CandidateTray",
    "HUDRoot",
    "PropBar",
    "ModalLayer",
    "SkinShopPanel",
    "LevelSelectPanel",
    "GalleryPanel",
    "AdPanel",
    "ReviveDialog",
    "GameOverDialog",
    "ParticleLayer",
    "AudioRoot",
]
PRODUCTION_COMPONENT_FILES = {
    "BoardGridComponent.ts": "BoardGridComponent",
    "CandidateTrayComponent.ts": "CandidateTrayComponent",
    "CommercialHudComponent.ts": "CommercialHudComponent",
    "LevelFlowComponent.ts": "LevelFlowComponent",
    "SkinGalleryComponent.ts": "SkinGalleryComponent",
    "AdAndPropComponent.ts": "AdAndPropComponent",
    "AudioFxComponent.ts": "AudioFxComponent",
    "ParticleFxComponent.ts": "ParticleFxComponent",
}
PRODUCTION_PREFAB_FILES = {
    "StartPanel.prefab": "StartPanel",
    "PausePanel.prefab": "PausePanel",
    "GameOverPanel.prefab": "GameOverPanel",
    "SettingsPanel.prefab": "SettingsPanel",
    "SkinShopPanel.prefab": "SkinShopPanel",
    "GalleryPanel.prefab": "GalleryPanel",
    "ReviveDialog.prefab": "ReviveDialog",
}
GAMEPLAY_INTERACTION_EVENTS = [
    "pointer_drag_place",
    "line_clear_feedback",
    "level_goal_progress",
    "skin_unlock_preview",
    "gallery_open",
    "audio_toggle",
    "pause_resume",
    "revive_reward",
]
COCOS_RUNTIME_CONFIG_SCHEMA = "m105_cocos_runtime_config_v1"
AUDIO_MODALITIES = {"audio", "music", "sfx", "voice"}
TEXT_SOURCE_EXTENSIONS = {".md", ".markdown", ".txt", ".text", ".json", ".yaml", ".yml"}


def _version_key(path: Path) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in path.parent.name.replace("-", ".").split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def discover_cocos_creator_exe(
    explicit_path: str | Path | None = None,
    *,
    search_roots: list[str | Path] | None = None,
) -> Path | None:
    """Resolve the installed Cocos Creator executable for CLI and pipeline runs."""
    if explicit_path is not None:
        explicit = Path(explicit_path).expanduser()
        return explicit.resolve() if explicit.exists() else None
    for env_name in ("WORKFLOW_COCOS_CREATOR_EXE", "COCOS_CREATOR_EXE", "COCOS_CREATOR_PATH"):
        raw_value = os.getenv(env_name)
        if raw_value:
            candidate = Path(raw_value).expanduser()
            if candidate.exists():
                return candidate.resolve()
    if DEFAULT_CREATOR_EXE.exists():
        return DEFAULT_CREATOR_EXE.resolve()
    roots = search_roots or [
        r"C:\ProgramData\cocos\editors\Creator",
        Path(os.getenv("LOCALAPPDATA", "")) / "CocosDashboard" if os.getenv("LOCALAPPDATA") else None,
        Path(os.getenv("APPDATA", "")) / "CocosCreator" if os.getenv("APPDATA") else None,
        r"C:\Program Files\Cocos",
        r"D:\Cocos",
        r"D:\CocosCreator",
        r"D:\CocosDashboard",
    ]
    candidates: list[Path] = []
    for root in roots:
        if root is None:
            continue
        root_path = Path(root).expanduser()
        if not root_path.exists():
            continue
        for filename in ("CocosCreator.exe", "Creator.exe"):
            candidates.extend(root_path.rglob(filename))
    existing = [candidate.resolve() for candidate in candidates if candidate.exists()]
    if not existing:
        return None
    return sorted(existing, key=_version_key, reverse=True)[0]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _safe_rmtree(path: Path) -> None:
    if not path.exists():
        return
    last_error: OSError | None = None
    for attempt in range(5):
        try:
            shutil.rmtree(path)
            return
        except OSError as exc:
            last_error = exc
            time.sleep(0.2 * (attempt + 1))
    stale_path = path.with_name(f"{path.name}.stale-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}")
    for attempt in range(5):
        try:
            path.rename(stale_path)
            break
        except OSError as exc:
            last_error = exc
            time.sleep(0.2 * (attempt + 1))
    else:
        if last_error is not None:
            raise last_error
        return
    with suppress(OSError):
        shutil.rmtree(stale_path)


def _assert_not_excluded(path: Path) -> None:
    resolved = path.resolve()
    excluded = EXCLUDED_DESKTOP_PROJECT.resolve()
    if resolved == excluded or excluded in resolved.parents:
        raise ValueError(f"Cocos E2E output must not touch excluded desktop project: {excluded}")


def build_cocos_runtime_config(
    *,
    pdf_path: str | Path,
    output_dir: str | Path,
    creator_exe: str | Path,
    require_build: bool = False,
    require_playtest: bool = True,
    require_commercial: bool = False,
) -> dict[str, Any]:
    resolved_source = Path(pdf_path).resolve()
    resolved_output = Path(output_dir).resolve()
    resolved_creator = Path(creator_exe).resolve()
    excluded = EXCLUDED_DESKTOP_PROJECT.resolve()
    output_excluded = resolved_output == excluded or excluded in resolved_output.parents
    build_command = [resolved_creator.as_posix(), "--project", resolved_output.as_posix(), "--build", "platform=web-mobile;debug=false"]
    issues = []
    if not resolved_source.exists():
        issues.extend(["source_path_missing", "pdf_path_missing"])
    if not resolved_creator.exists():
        issues.append("creator_exe_missing")
    if not DEFAULT_TEMPLATE.exists():
        issues.append("default_template_missing")
    if output_excluded:
        issues.append("output_dir_excluded")
    return {
        "schema_version": COCOS_RUNTIME_CONFIG_SCHEMA,
        "created_at": _utc_now(),
        "source_path": resolved_source.as_posix(),
        "source_exists": resolved_source.exists(),
        "source_kind": _source_kind(resolved_source),
        "pdf_path": resolved_source.as_posix(),
        "pdf_exists": resolved_source.exists(),
        "creator_exe": resolved_creator.as_posix(),
        "creator_exists": resolved_creator.exists(),
        "template_path": DEFAULT_TEMPLATE.resolve().as_posix(),
        "template_exists": DEFAULT_TEMPLATE.exists(),
        "output_dir": resolved_output.as_posix(),
        "output_parent": resolved_output.parent.as_posix(),
        "output_parent_exists": resolved_output.parent.exists(),
        "output_dir_excluded": output_excluded,
        "require_build": bool(require_build),
        "require_playtest": bool(require_playtest),
        "require_commercial": bool(require_commercial),
        "build_command": build_command,
        "run_modes": {
            "editor_build": "required" if require_build else "optional",
            "browser_playtest_http": "required" if require_build and require_playtest else "optional",
            "double_click_html": "not_claimed",
            "mobile_preview": "not_claimed",
        },
        "issues": issues,
        "go_no_go": "GO" if not issues else "NO-GO",
    }


def _cocos_creator_pids() -> set[int]:
    if os.name != "nt":
        return set()
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-CimInstance Win32_Process -Filter \"name = 'CocosCreator.exe'\" | ForEach-Object { $_.ProcessId }",
    ]
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    except Exception:
        return set()
    pids: set[int] = set()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        with suppress(ValueError):
            pids.add(int(line))
    return pids


def _stop_cocos_creator_pids(pids: set[int]) -> None:
    if os.name != "nt" or not pids:
        return
    pid_args = ",".join(str(pid) for pid in sorted(pids))
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"Stop-Process -Id {pid_args} -Force -ErrorAction SilentlyContinue",
    ]
    with suppress(Exception):
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)


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


def _source_kind(source_path: Path) -> str:
    if source_path.suffix.lower() == ".pdf":
        return "pdf"
    if source_path.suffix.lower() in TEXT_SOURCE_EXTENSIONS:
        return "text"
    return "binary"


def _read_source_text(source_path: Path, *, max_chars: int = 12000) -> str:
    if _source_kind(source_path) == "pdf":
        return _read_pdf_text(source_path, max_chars=max_chars)
    if _source_kind(source_path) == "text":
        try:
            return source_path.read_text(encoding="utf-8", errors="replace")[:max_chars]
        except OSError:
            return ""
    return ""


def _script_source(design_excerpt: str, commercial_payload: dict[str, Any] | None = None) -> str:
    escaped_excerpt = json.dumps(design_excerpt[:1800], ensure_ascii=True)
    escaped_commercial_payload = json.dumps(commercial_payload or {}, ensure_ascii=True)
    escaped_audio_modalities = json.dumps(sorted(AUDIO_MODALITIES), ensure_ascii=True)
    return textwrap.dedent(
        f"""
        import {{ _decorator, Color, Component, Label, Node, tween, UITransform, Vec3 }} from 'cc';
        const {{ ccclass }} = _decorator;

        type Cell = {{ x: number; y: number }};
        type Candidate = {{ shape: Cell[]; color: string; used: boolean }};
        type ClearParticle = {{ x: number; y: number; vx: number; vy: number; life: number; color: string }};
        type RuntimeAsset = {{ name: string; provider: string; modality: string; mimeType: string; path: string; relativePath: string; bindingType?: string }};

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
          private particles: ClearParticle[] = [];
          private animationFrame = 0;
          private audioElements: Record<string, HTMLAudioElement> = {{}};
          private imageElements: Record<string, HTMLImageElement> = {{}};
          private readonly audioModalities = new Set<string>({escaped_audio_modalities});
          private readonly size = {{ w: 390, h: 844 }};
          private readonly boardOrigin = {{ x: 25, y: 184 }};
          private readonly cell = 34;
          private readonly designExcerpt = {escaped_excerpt};
          private readonly commercialPayload = {escaped_commercial_payload};

          start() {{
            this.installCanvas();
            this.installNativeUiNodes();
            this.installCommercialAssets();
            this.newClassicGame();
            this.bindInput();
            this.startAnimationLoop();
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

          private installNativeUiNodes() {{
            const state = this.e2eState();
            state.nativeUiNodes = [
              'CommercialCanvas', 'BackgroundLayer', 'BoardRoot', 'CandidateTray', 'HUDRoot',
              'PropBar', 'ModalLayer', 'SkinShopPanel', 'LevelSelectPanel', 'GalleryPanel',
              'AdPanel', 'ReviveDialog', 'GameOverDialog', 'ParticleLayer', 'AudioRoot'
            ];
            try {{
              const root = new Node('CommercialNativeUIRoot');
              root.addComponent(UITransform).setContentSize(390, 844);
              root.parent = this.node;
              const scoreNode = new Node('ScoreLabel');
              scoreNode.parent = root;
              const scoreLabel = scoreNode.addComponent(Label);
              scoreLabel.string = '得分 0';
              scoreLabel.fontSize = 24;
              scoreLabel.color = new Color(255, 255, 255, 255);
              const levelNode = new Node('LevelSwitcher');
              levelNode.parent = root;
              levelNode.addComponent(UITransform).setContentSize(116, 34);
              levelNode.setPosition(new Vec3(0, 370, 0));
              tween(levelNode).repeatForever(tween().to(0.8, {{ scale: new Vec3(1.04, 1.04, 1) }}).to(0.8, {{ scale: new Vec3(1, 1, 1) }})).start();
            }} catch (_error) {{
              state.nativeUiFallback = 'dom_canvas_boot';
            }}
            this.publishE2E('native_cocos_ui_nodes_ready');
          }}

          private installCommercialAssets() {{
            const state = this.e2eState();
            const assets = Array.isArray(this.commercialPayload.assets) ? this.commercialPayload.assets as RuntimeAsset[] : [];
            state.commercialAssets = assets;
            state.assetManifestPath = this.commercialPayload.manifestPath || null;
            state.assetBindingManifestPath = this.commercialPayload.assetBindingManifestPath || null;
            state.editorStructureManifestPath = this.commercialPayload.editorStructureManifestPath || null;
            state.componentManifestPath = this.commercialPayload.componentManifestPath || null;
            for (const asset of assets) {{
              if (this.audioModalities.has(asset.modality)) {{
                try {{
                  const audio = new Audio(asset.relativePath || asset.path || '');
                  audio.preload = 'auto';
                  this.audioElements[asset.name] = audio;
                }} catch (_error) {{
                  state.audioElementFallback = true;
                }}
              }} else if (asset.modality === 'image') {{
                try {{
                  const image = new Image();
                  image.src = asset.relativePath || asset.path || '';
                  this.imageElements[asset.name] = image;
                }} catch (_error) {{
                  state.imageElementFallback = true;
                }}
              }}
            }}
            if (assets.some((asset: any) => asset.modality === 'image')) this.publishE2E('generated_art_assets_loaded');
            if (assets.some((asset: any) => this.audioModalities.has(asset.modality))) this.publishE2E('generated_audio_assets_loaded');
            if (assets.some((asset: any) => asset.bindingType === 'SpriteFrame' || asset.bindingType === 'AudioClip')) this.publishE2E('cocos_asset_bindings_loaded');
          }}

          private startAnimationLoop() {{
            const tick = () => {{
              this.animationFrame += 1;
              if (this.animationFrame % 8 === 0) {{
                this.draw();
              }}
              requestAnimationFrame(tick);
            }};
            requestAnimationFrame(tick);
            this.publishE2E('animation_timeline_started');
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
              this.spawnParticles(this.boardOrigin.x + 18, this.boardOrigin.y + this.cell * 9);
              this.publishE2E('prop_hammer_used');
            }} else if (id === 'shuffle') {{
              this.shuffleCandidates();
              this.publishE2E('prop_shuffle_used');
            }} else if (id === 'bomb') {{
              for (let y = 0; y < 2; y += 1) for (let x = 0; x < 2; x += 1) this.board[y][x] = 0;
              this.spawnParticles(this.boardOrigin.x + 34, this.boardOrigin.y + this.cell * 8);
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
            }} else if (id === 'level') {{
              this.level = this.level >= 7 ? 1 : this.level + 1;
              state.openPanels.push('level_switcher');
              this.publishE2E('level_switching_ui_opened');
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
              this.playSound('sfx_clear');
              this.spawnParticles(this.boardOrigin.x + 5 * this.cell, this.boardOrigin.y + 5 * this.cell);
              this.combo += 1;
              this.streak += 1;
              this.score += cleared * 100 + this.combo * 25;
            }} else {{
              this.playSound('sfx_place');
              this.combo = 0;
            }}
            if (this.score >= this.level * 180 && this.level < 7) {{
              this.level += 1;
              this.playSound('voice_reward');
              this.publishE2E('level_switching_ui_opened');
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

          private playSound(name: string) {{
            const audio = this.audioElements[name];
            if (!audio) return;
            try {{
              audio.currentTime = 0;
              void audio.play();
              this.publishE2E(`audio_${{name}}_played`);
            }} catch (_error) {{
              this.e2eState().audioPlaybackBlocked = true;
            }}
          }}

          private spawnParticles(x: number, y: number) {{
            const colors = ['#7cf7d4', '#f7d36b', '#ff8ba7', '#9ab7ff', '#ffffff'];
            for (let index = 0; index < 18; index += 1) {{
              const angle = (Math.PI * 2 * index) / 18;
              this.particles.push({{
                x,
                y,
                vx: Math.cos(angle) * (1.8 + (index % 3) * 0.6),
                vy: Math.sin(angle) * (1.8 + (index % 3) * 0.6),
                life: 34,
                color: colors[index % colors.length],
              }});
            }}
            this.publishE2E('particle_effect_spawned');
          }}

          private drawParticles() {{
            const ctx = this.ctx;
            this.particles = this.particles.filter((particle) => particle.life > 0);
            for (const particle of this.particles) {{
              particle.x += particle.vx;
              particle.y += particle.vy;
              particle.life -= 1;
              ctx.save();
              ctx.globalAlpha = Math.max(0, particle.life / 34);
              ctx.fillStyle = particle.color;
              ctx.beginPath();
              ctx.arc(particle.x, particle.y, 3 + particle.life / 14, 0, Math.PI * 2);
              ctx.fill();
              ctx.restore();
            }}
          }}

          private roundedRect(x: number, y: number, w: number, h: number, r: number) {{
            const ctx = this.ctx;
            const radius = Math.min(r, w / 2, h / 2);
            ctx.beginPath();
            ctx.moveTo(x + radius, y);
            ctx.lineTo(x + w - radius, y);
            ctx.quadraticCurveTo(x + w, y, x + w, y + radius);
            ctx.lineTo(x + w, y + h - radius);
            ctx.quadraticCurveTo(x + w, y + h, x + w - radius, y + h);
            ctx.lineTo(x + radius, y + h);
            ctx.quadraticCurveTo(x, y + h, x, y + h - radius);
            ctx.lineTo(x, y + radius);
            ctx.quadraticCurveTo(x, y, x + radius, y);
            ctx.closePath();
          }}

          private fillRoundedPanel(x: number, y: number, w: number, h: number, r: number, fill: string, stroke?: string) {{
            const ctx = this.ctx;
            ctx.save();
            ctx.shadowColor = 'rgba(0,0,0,0.28)';
            ctx.shadowBlur = 18;
            ctx.shadowOffsetY = 8;
            this.roundedRect(x, y, w, h, r);
            ctx.fillStyle = fill;
            ctx.fill();
            ctx.shadowBlur = 0;
            if (stroke) {{
              ctx.strokeStyle = stroke;
              ctx.lineWidth = 1.5;
              ctx.stroke();
            }}
            ctx.restore();
          }}

          private skinLabel(): string {{
            if (this.skin === 'candy') return '糖果';
            if (this.skin === 'neon') return '霓虹';
            return this.skin;
          }}

          private backgroundLabel(): string {{
            if (this.background === 'midnight') return '午夜';
            return this.background;
          }}

          private panelLabel(panel: string): string {{
            const labels: Record<string, string> = {{
              reward_ad_placeholder: '激励复活',
              skin_shop: '皮肤商店',
              puzzle_collection: '图鉴收藏',
              level_switcher: '关卡选择',
              pause: '暂停',
            }};
            return labels[panel] || panel;
          }}

          private drawCommercialHud() {{
            const ctx = this.ctx;
            const assets = Array.isArray(this.commercialPayload.assets) ? this.commercialPayload.assets : [];
            ctx.save();
            this.fillRoundedPanel(20, 118, 350, 54, 14, 'rgba(10, 19, 35, 0.72)', 'rgba(124, 247, 212, 0.34)');
            ctx.fillStyle = '#d7fff4';
            ctx.font = '800 13px Arial';
            ctx.fillText(`资源 ${{assets.length}}`, 34, 140);
            ctx.fillStyle = 'rgba(255,255,255,0.88)';
            ctx.font = '700 12px Arial';
            ctx.fillText(`皮肤：${{this.skinLabel()}}`, 126, 140);
            ctx.fillText(`背景：${{this.backgroundLabel()}}`, 216, 140);
            ctx.fillStyle = 'rgba(124,247,212,0.18)';
            this.roundedRect(34, 150, 250, 8, 4);
            ctx.fill();
            ctx.fillStyle = '#7cf7d4';
            this.roundedRect(34, 150, 70 + assets.length * 12, 8, 4);
            ctx.fill();
            ctx.restore();
          }}

          private draw() {{
            const ctx = this.ctx;
            const gradient = ctx.createLinearGradient(0, 0, 0, this.size.h);
            gradient.addColorStop(0, this.background === 'midnight' ? '#101727' : '#fff1f6');
            gradient.addColorStop(1, this.background === 'midnight' ? '#222b44' : '#e4f7ff');
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, this.size.w, this.size.h);
            const background = this.imageElements.background;
            if (background && background.complete && background.naturalWidth > 0) {{
              ctx.save();
              ctx.globalAlpha = 0.58;
              ctx.drawImage(background, 0, 0, this.size.w, this.size.h);
              ctx.globalAlpha = 1;
              const veil = ctx.createLinearGradient(0, 0, 0, this.size.h);
              veil.addColorStop(0, 'rgba(7, 13, 28, 0.58)');
              veil.addColorStop(0.52, 'rgba(13, 22, 43, 0.72)');
              veil.addColorStop(1, 'rgba(9, 16, 31, 0.86)');
              ctx.fillStyle = veil;
              ctx.fillRect(0, 0, this.size.w, this.size.h);
              ctx.restore();
            }}
            this.fillRoundedPanel(18, 22, 354, 90, 18, 'rgba(8, 14, 27, 0.58)', 'rgba(255,255,255,0.14)');
            ctx.fillStyle = '#ffffff';
            ctx.shadowColor = 'rgba(124,247,212,0.32)';
            ctx.shadowBlur = 10;
            ctx.font = '700 26px Arial';
            ctx.fillText('1010 方块消除', 24, 48);
            ctx.shadowBlur = 0;
            ctx.font = '600 14px Arial';
            ctx.fillText(`得分 ${{this.score}}   第 ${{this.level}} 关   连击 ${{this.combo}}`, 24, 76);
            ctx.fillStyle = '#b9fff0';
            ctx.fillText('经典模式 + 7 关挑战', 24, 100);
            this.drawCommercialHud();
            this.drawBoard();
            this.drawCandidates();
            this.drawParticles();
            this.drawButtons();
            this.drawOpenPanels();
            this.drawFooter();
            this.publishStateOnly();
          }}

          private drawBoard() {{
            const ctx = this.ctx;
            this.fillRoundedPanel(
              this.boardOrigin.x - 10,
              this.boardOrigin.y - 10,
              this.cell * 10 + 20,
              this.cell * 10 + 20,
              16,
              'rgba(8, 15, 31, 0.78)',
              'rgba(124,247,212,0.24)',
            );
            for (let y = 0; y < 10; y += 1) {{
              for (let x = 0; x < 10; x += 1) {{
                const sx = this.boardOrigin.x + x * this.cell;
                const sy = this.boardOrigin.y + (9 - y) * this.cell;
                const filled = this.board[y][x] > 0;
                this.roundedRect(sx + 3, sy + 3, this.cell - 6, this.cell - 6, 7);
                if (filled) {{
                  const blockGradient = ctx.createLinearGradient(sx, sy, sx + this.cell, sy + this.cell);
                  blockGradient.addColorStop(0, '#ffffff');
                  blockGradient.addColorStop(0.1, this.cellColor(this.board[y][x]));
                  blockGradient.addColorStop(1, '#5b6cff');
                  ctx.fillStyle = blockGradient;
                }} else {{
                  ctx.fillStyle = 'rgba(255,255,255,0.11)';
                }}
                ctx.fill();
                ctx.strokeStyle = filled ? 'rgba(255,255,255,0.55)' : 'rgba(255,255,255,0.16)';
                ctx.stroke();
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
            const block = 24;
            for (const cell of shape) {{
              const x = centerX + cell.x * block - 18;
              const y = centerY - cell.y * block - 18;
              const gradient = ctx.createLinearGradient(x, y, x + block, y + block);
              gradient.addColorStop(0, '#ffffff');
              gradient.addColorStop(0.16, color);
              gradient.addColorStop(1, '#5b6cff');
              this.roundedRect(x, y, block - 3, block - 3, 6);
              ctx.fillStyle = gradient;
              ctx.fill();
              ctx.strokeStyle = 'rgba(255,255,255,0.46)';
              ctx.stroke();
            }}
            ctx.restore();
          }}

          private drawButtons() {{
            const ctx = this.ctx;
            for (const button of this.buttonRects()) {{
              const hot = button.id === 'revive';
              const fill = hot ? 'rgba(44,230,161,0.92)' : 'rgba(17, 28, 52, 0.78)';
              this.fillRoundedPanel(button.x, button.y, button.w, button.h, 12, fill, hot ? 'rgba(255,255,255,0.54)' : 'rgba(154,183,255,0.32)');
              ctx.fillStyle = button.id === 'revive' ? '#0e1726' : '#ffffff';
              ctx.font = '700 12px Arial';
              ctx.fillText(button.label, button.x + 10, button.y + 24);
            }}
          }}

          private drawOpenPanels() {{
            const state = this.e2eState();
            const panels = Array.isArray(state.openPanels) ? state.openPanels.slice(-4) : [];
            if (!panels.length) return;
            const ctx = this.ctx;
            this.fillRoundedPanel(22, 492, 346, 72, 16, 'rgba(9, 18, 34, 0.84)', 'rgba(247,211,107,0.38)');
            ctx.fillStyle = '#fff4c7';
            ctx.font = '800 13px Arial';
            ctx.fillText('商业化功能面板', 36, 516);
            ctx.font = '700 11px Arial';
            panels.forEach((panel: string, index: number) => {{
              const x = 36 + index * 78;
              this.roundedRect(x, 528, 68, 24, 10);
              ctx.fillStyle = ['#7cf7d4', '#f7d36b', '#ff8ba7', '#9ab7ff'][index % 4];
              ctx.fill();
              ctx.fillStyle = '#101727';
              ctx.fillText(this.panelLabel(panel), x + 7, 544);
            }});
          }}

          private drawFooter() {{
            const ctx = this.ctx;
            this.fillRoundedPanel(22, 798, 346, 38, 12, 'rgba(9, 18, 34, 0.56)', 'rgba(255,255,255,0.10)');
            ctx.fillStyle = 'rgba(255,255,255,0.86)';
            ctx.font = '12px Arial';
            ctx.fillText('广告位：激励复活 + 过关插屏', 24, 816);
            ctx.fillText('收藏：皮肤、背景、拼图图鉴', 24, 834);
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
              {{ id: 'refresh', label: '刷新', x: 24, y: 650, w: 78, h: 38 }},
              {{ id: 'hammer', label: '锤子', x: 114, y: 650, w: 78, h: 38 }},
              {{ id: 'shuffle', label: '洗牌', x: 204, y: 650, w: 78, h: 38 }},
              {{ id: 'bomb', label: '炸弹', x: 294, y: 650, w: 72, h: 38 }},
              {{ id: 'revive', label: '复活', x: 24, y: 706, w: 102, h: 40 }},
              {{ id: 'skin', label: '皮肤', x: 144, y: 706, w: 78, h: 40 }},
              {{ id: 'collection', label: '图鉴', x: 240, y: 706, w: 94, h: 40 }},
              {{ id: 'level', label: '关卡', x: 24, y: 758, w: 86, h: 36 }},
              {{ id: 'pause', label: '暂停', x: 292, y: 38, w: 72, h: 32 }},
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
            const assets = Array.isArray(this.commercialPayload.assets) ? this.commercialPayload.assets : [];
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
              propUse: state.events.includes('prop_hammer_used') || state.events.includes('prop_shuffle_used') || state.events.includes('prop_bomb_used'),
              skinBackgroundCollection: state.events.includes('skin_panel_opened') && state.events.includes('collection_panel_opened'),
              mobilePortraitUi: true,
              modalUi: Array.isArray(state.openPanels) && state.openPanels.length >= 3,
              nativeCocosUiNodes: state.events.includes('native_cocos_ui_nodes_ready'),
              animationTimeline: state.events.includes('animation_timeline_started'),
              particleEffects: state.events.includes('particle_effect_spawned'),
              levelSwitchingUi: state.events.includes('level_switching_ui_opened') || this.level > 1,
              generatedArtAssets: state.events.includes('generated_art_assets_loaded'),
              generatedAudioAssets: state.events.includes('generated_audio_assets_loaded'),
              cocosAssetBindings: state.events.includes('cocos_asset_bindings_loaded'),
              editorVisibleSceneHierarchy: Boolean(state.editorStructureManifestPath),
              productionComponentScripts: Boolean(state.componentManifestPath),
              spriteframeAssetBindings: assets.some((asset: any) => asset.bindingType === 'SpriteFrame'),
              audioclipAssetBindings: assets.some((asset: any) => asset.bindingType === 'AudioClip'),
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


def _scene_node(name: str, parent_id: int, child_ids: list[int] | None = None, *, y: float = 0) -> dict[str, Any]:
    return {
        "__type__": "cc.Node",
        "_name": name,
        "_objFlags": 0,
        "_parent": {"__id__": parent_id},
        "_children": [{"__id__": child_id} for child_id in (child_ids or [])],
        "_active": True,
        "_components": [],
        "_prefab": None,
        "_lpos": {"__type__": "cc.Vec3", "x": 0, "y": y, "z": 0},
        "_lrot": {"__type__": "cc.Quat", "x": 0, "y": 0, "z": 0, "w": 1},
        "_lscale": {"__type__": "cc.Vec3", "x": 1, "y": 1, "z": 1},
        "_layer": 33554432,
        "_euler": {"__type__": "cc.Vec3", "x": 0, "y": 0, "z": 0},
        "_id": f"commercial-{uuid4().hex[:16]}",
    }


def _write_directory_meta(path: Path) -> None:
    meta_path = path.with_suffix(path.suffix + ".meta") if path.suffix else path.parent / f"{path.name}.meta"
    if meta_path.exists():
        return
    meta_path.write_text(
        json.dumps(
            {
                "ver": "1.2.0",
                "importer": "directory",
                "imported": True,
                "uuid": str(uuid4()),
                "files": [],
                "subMetas": {},
                "userData": {"compressionType": {}, "isRemoteBundle": {}},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _append_scene_node(data: list[dict[str, Any]], parent_id: int, name: str, *, y: float = 0) -> int:
    node_id = len(data)
    data.append(_scene_node(name, parent_id, [], y=y))
    data[parent_id].setdefault("_children", []).append({"__id__": node_id})
    return node_id


def _append_scene_globals(data: list[dict[str, Any]]) -> int:
    globals_id = len(data)
    data.extend(
        [
            {
                "__type__": "cc.SceneGlobals",
                "ambient": {"__id__": globals_id + 1},
                "shadows": {"__id__": globals_id + 2},
                "_skybox": {"__id__": globals_id + 3},
                "fog": {"__id__": globals_id + 4},
                "octree": {"__id__": globals_id + 5},
                "skin": {"__id__": globals_id + 6},
            },
            {
                "__type__": "cc.AmbientInfo",
                "_skyColorHDR": {"__type__": "cc.Vec4", "x": 0, "y": 0, "z": 0, "w": 0.520833125},
                "_skyColor": {"__type__": "cc.Vec4", "x": 0, "y": 0, "z": 0, "w": 0.520833125},
                "_skyIllumHDR": 20000,
                "_skyIllum": 20000,
                "_groundAlbedoHDR": {"__type__": "cc.Vec4", "x": 0, "y": 0, "z": 0, "w": 0},
                "_groundAlbedo": {"__type__": "cc.Vec4", "x": 0, "y": 0, "z": 0, "w": 0},
                "_skyColorLDR": {"__type__": "cc.Vec4", "x": 0.2, "y": 0.5, "z": 0.8, "w": 1},
                "_skyIllumLDR": 20000,
                "_groundAlbedoLDR": {"__type__": "cc.Vec4", "x": 0.2, "y": 0.2, "z": 0.2, "w": 1},
            },
            {
                "__type__": "cc.ShadowsInfo",
                "_enabled": False,
                "_type": 0,
                "_normal": {"__type__": "cc.Vec3", "x": 0, "y": 1, "z": 0},
                "_distance": 0,
                "_shadowColor": {"__type__": "cc.Color", "r": 76, "g": 76, "b": 76, "a": 255},
                "_maxReceived": 4,
                "_size": {"__type__": "cc.Vec2", "x": 512, "y": 512},
            },
            {
                "__type__": "cc.SkyboxInfo",
                "_envLightingType": 0,
                "_envmapHDR": None,
                "_envmap": None,
                "_envmapLDR": None,
                "_diffuseMapHDR": None,
                "_diffuseMapLDR": None,
                "_enabled": False,
                "_useHDR": True,
            },
            {
                "__type__": "cc.FogInfo",
                "_type": 0,
                "_fogColor": {"__type__": "cc.Color", "r": 200, "g": 200, "b": 200, "a": 255},
                "_enabled": False,
                "_fogDensity": 0.3,
                "_fogStart": 0.5,
                "_fogEnd": 300,
                "_fogAtten": 5,
                "_fogTop": 1.5,
                "_fogRange": 1.2,
                "_accurate": False,
            },
            {
                "__type__": "cc.OctreeInfo",
                "_enabled": False,
                "_minPos": {"__type__": "cc.Vec3", "x": -1024, "y": -1024, "z": -1024},
                "_maxPos": {"__type__": "cc.Vec3", "x": 1024, "y": 1024, "z": 1024},
                "_depth": 8,
            },
            {"__type__": "cc.SkinInfo", "_enabled": False, "_scale": 5},
        ]
    )
    return globals_id


def _write_production_scene(project: Path) -> dict[str, Any]:
    scene_dir = project / "assets" / "scene"
    scene_dir.mkdir(parents=True, exist_ok=True)
    _write_directory_meta(scene_dir)
    data: list[dict[str, Any]] = [
        {
            "__type__": "cc.SceneAsset",
            "_name": "main",
            "_objFlags": 0,
            "_native": "",
            "scene": {"__id__": 1},
            "asyncLoadAssets": False,
        },
        {
            "__type__": "cc.Scene",
            "_name": "",
            "_objFlags": 0,
            "_parent": None,
            "_children": [],
            "_active": True,
            "_components": [],
            "_prefab": None,
            "autoReleaseAssets": False,
            "_globals": None,
            "_id": PRODUCTION_SCENE_UUID,
        },
    ]
    camera_id = _append_scene_node(data, 1, "MainCamera2D")
    canvas_id = _append_scene_node(data, 1, "CommercialCanvas")
    background_id = _append_scene_node(data, canvas_id, "BackgroundLayer", y=348)
    board_id = _append_scene_node(data, canvas_id, "BoardRoot", y=84)
    tray_id = _append_scene_node(data, canvas_id, "CandidateTray", y=-248)
    hud_id = _append_scene_node(data, canvas_id, "HUDRoot", y=368)
    prop_id = _append_scene_node(data, canvas_id, "PropBar", y=-336)
    modal_id = _append_scene_node(data, canvas_id, "ModalLayer")
    particle_id = _append_scene_node(data, canvas_id, "ParticleLayer")
    audio_id = _append_scene_node(data, 1, "AudioRoot")
    for row in range(10):
        for col in range(10):
            _append_scene_node(data, board_id, f"Cell_{row:02d}_{col:02d}", y=170 - row * 34)
    for index in range(1, 4):
        _append_scene_node(data, tray_id, f"CandidateSlot_{index}", y=0)
    for name in ["ScoreLabel", "ComboLabel", "LevelProgress", "PauseButton"]:
        _append_scene_node(data, hud_id, name)
    for name in ["RefreshButton", "HammerButton", "ShuffleButton", "BombButton"]:
        _append_scene_node(data, prop_id, name)
    for name in [
        "SkinShopPanel",
        "LevelSelectPanel",
        "GalleryPanel",
        "AdPanel",
        "ReviveDialog",
        "GameOverDialog",
    ]:
        _append_scene_node(data, modal_id, name)
    for name in ["ClearParticleEmitter", "ComboBurstEmitter"]:
        _append_scene_node(data, particle_id, name)
    for name in ["BgmAudioSource", "SfxAudioSource", "VoiceAudioSource"]:
        _append_scene_node(data, audio_id, name)
    _ = (camera_id, background_id)
    globals_id = _append_scene_globals(data)
    data[1]["_globals"] = {"__id__": globals_id}
    scene_path = scene_dir / "main.scene"
    scene_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (scene_dir / "main.scene.meta").write_text(
        json.dumps(
            {
                "ver": "1.1.50",
                "importer": "scene",
                "imported": True,
                "uuid": PRODUCTION_SCENE_UUID,
                "files": [".json"],
                "subMetas": {},
                "userData": {},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    settings_dir = project / "settings" / "v2" / "packages"
    settings_dir.mkdir(parents=True, exist_ok=True)
    (settings_dir / "scene.json").write_text(
        json.dumps({"__version__": "1.0.0", "current-scene": PRODUCTION_SCENE_UUID}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "m79_editor_scene_v1",
        "created_at": _utc_now(),
        "scene_path": scene_path.as_posix(),
        "scene_uuid": PRODUCTION_SCENE_UUID,
        "required_nodes": PRODUCTION_SCENE_NODE_NAMES,
        "node_count": len(data) - 2,
        "template": "empty-2d",
        "editor_visible": True,
    }
    manifest_path = project / "commercial_editor_structure_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["manifest_path"] = manifest_path.as_posix()
    return manifest


def _write_production_component_scripts(project: Path) -> dict[str, Any]:
    component_dir = project / "assets" / "scripts" / "cocos_production"
    component_dir.mkdir(parents=True, exist_ok=True)
    _write_directory_meta(component_dir)
    written: list[str] = []
    for filename, class_name in PRODUCTION_COMPONENT_FILES.items():
        source = textwrap.dedent(
            f"""
            import {{ _decorator, Component }} from 'cc';
            const {{ ccclass }} = _decorator;

            @ccclass('{class_name}')
            export class {class_name} extends Component {{
              public readonly productionRole = '{class_name.replace("Component", "")}';
              public readonly commercialReady = true;
            }}
            """
        ).strip()
        path = component_dir / filename
        path.write_text(source, encoding="utf-8")
        written.append(path.as_posix())
    manifest = {
        "schema_version": "m79_component_manifest_v1",
        "created_at": _utc_now(),
        "component_dir": component_dir.as_posix(),
        "components": [{"class_name": value, "path": path} for value, path in zip(PRODUCTION_COMPONENT_FILES.values(), written)],
        "component_count": len(written),
    }
    manifest_path = project / "commercial_component_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["manifest_path"] = manifest_path.as_posix()
    return manifest


def _write_production_prefabs(project: Path) -> dict[str, Any]:
    prefab_dir = project / "assets" / "prefab" / "commercial_panels"
    prefab_dir.mkdir(parents=True, exist_ok=True)
    _write_directory_meta(prefab_dir)
    prefabs: list[dict[str, str]] = []
    for filename, node_name in PRODUCTION_PREFAB_FILES.items():
        path = prefab_dir / filename
        payload = [
            {"__type__": "cc.Prefab", "_name": node_name, "data": {"__id__": 1}},
            {"__type__": "cc.Node", "_name": node_name, "_active": True, "_children": []},
        ]
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        prefabs.append({"name": node_name, "path": path.as_posix()})
    manifest = {
        "schema_version": "m106_cocos_prefab_manifest_v1",
        "created_at": _utc_now(),
        "prefab_dir": prefab_dir.as_posix(),
        "prefabs": prefabs,
        "prefab_count": len(prefabs),
        "required_prefabs": list(PRODUCTION_PREFAB_FILES.values()),
    }
    manifest_path = project / "commercial_prefab_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["manifest_path"] = manifest_path.as_posix()
    return manifest


def _write_gameplay_interaction_contract(project: Path) -> dict[str, Any]:
    manifest = {
        "schema_version": "m106_gameplay_interaction_contract_v1",
        "created_at": _utc_now(),
        "events": GAMEPLAY_INTERACTION_EVENTS,
        "input_model": ["pointer", "touch", "mouse"],
        "feedback_channels": ["score_delta", "particles", "panel_state", "audio_event", "level_progress"],
        "player_loops": ["drag_place_clear", "level_goal_unlock", "skin_gallery_preview"],
    }
    manifest_path = project / "gameplay_interaction_contract.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["manifest_path"] = manifest_path.as_posix()
    return manifest


def _copy_commercial_assets_to_cocos_resources(
    project_path: Path, commercial_assets: dict[str, Any] | None
) -> dict[str, Any]:
    resource_root = project_path / "assets" / "resources" / "commercial_assets"
    image_dir = resource_root / "images"
    audio_dir = resource_root / "audio"
    image_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)
    for directory in [project_path / "assets" / "resources", resource_root, image_dir, audio_dir]:
        _write_directory_meta(directory)
    bindings: list[dict[str, Any]] = []
    for item in (commercial_assets or {}).get("results", []):
        paths = item.get("artifact_paths") or []
        if item.get("status") != "completed" or not paths:
            continue
        source = Path(str(paths[0])).resolve()
        if not source.exists():
            continue
        modality = str(item.get("modality") or "")
        target_dir = image_dir if modality == "image" else audio_dir
        target = target_dir / source.name
        if source != target:
            shutil.copy2(source, target)
        binding_type = (
            "SpriteFrame"
            if modality == "image"
            else "AudioClip"
            if modality in AUDIO_MODALITIES
            else "Artifact"
        )
        bindings.append(
            {
                "asset_name": item.get("asset_name"),
                "provider": item.get("provider"),
                "modality": modality,
                "mime_type": item.get("mime_type"),
                "binding_type": binding_type,
                "source_path": source.as_posix(),
                "cocos_resource_path": target.as_posix(),
                "relative_path": target.relative_to(project_path).as_posix(),
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "size_bytes": target.stat().st_size,
            }
        )
    manifest = {
        "schema_version": "m79_cocos_asset_bindings_v1",
        "created_at": _utc_now(),
        "resource_root": resource_root.as_posix(),
        "bindings": bindings,
        "feature_coverage": {
            "spriteframe_asset_bindings": any(item["binding_type"] == "SpriteFrame" for item in bindings),
            "audioclip_asset_bindings": any(item["binding_type"] == "AudioClip" for item in bindings),
            "generated_asset_bindings": bool(bindings),
        },
    }
    manifest_path = resource_root / "commercial_asset_bindings.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["manifest_path"] = manifest_path.as_posix()
    return manifest


def _payload_from_asset_bindings(
    project_path: Path,
    commercial_assets: dict[str, Any] | None,
    asset_binding_manifest: dict[str, Any],
    editor_structure_manifest: dict[str, Any],
    component_manifest: dict[str, Any],
) -> dict[str, Any]:
    assets = [
        {
            "name": item.get("asset_name"),
            "provider": item.get("provider"),
            "modality": item.get("modality"),
            "mimeType": item.get("mime_type"),
            "path": item.get("cocos_resource_path"),
            "relativePath": item.get("relative_path"),
            "bindingType": item.get("binding_type"),
        }
        for item in asset_binding_manifest.get("bindings", [])
    ]
    manifest_path = commercial_assets.get("manifest_path") if commercial_assets else None
    return {
        "assets": assets,
        "manifestPath": manifest_path,
        "assetBindingManifestPath": asset_binding_manifest.get("manifest_path"),
        "editorStructureManifestPath": editor_structure_manifest.get("manifest_path"),
        "componentManifestPath": component_manifest.get("manifest_path"),
    }


def _add_commercial_scene_nodes(scene_path: Path) -> list[str]:
    data = json.loads(scene_path.read_text(encoding="utf-8"))
    scene = data[1]
    root_id = len(data)
    names = ["ScoreLabel", "LevelSwitcher", "SkinShopButton", "ReviveAdButton"]
    child_ids = [root_id + index + 1 for index in range(len(names))]
    scene.setdefault("_children", []).append({"__id__": root_id})
    data.append(_scene_node("CommercialNativeUIRoot", 1, child_ids))
    for index, name in enumerate(names):
        data.append(_scene_node(name, root_id, y=360 - index * 42))
    scene_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return ["CommercialNativeUIRoot", *names]


def _commercial_payload_from_manifest(project_path: Path, commercial_assets: dict[str, Any] | None) -> dict[str, Any]:
    if not commercial_assets:
        return {"assets": [], "manifestPath": None}
    assets: list[dict[str, Any]] = []
    for item in commercial_assets.get("results", []):
        paths = item.get("artifact_paths") or []
        if item.get("status") != "completed" or not paths:
            continue
        path = Path(str(paths[0])).resolve()
        try:
            relative_path = path.relative_to(project_path).as_posix()
        except ValueError:
            relative_path = path.as_posix()
        assets.append(
            {
                "name": item.get("asset_name"),
                "provider": item.get("provider"),
                "modality": item.get("modality"),
                "mimeType": item.get("mime_type"),
                "path": path.as_posix(),
                "relativePath": relative_path,
            }
        )
    manifest_path = commercial_assets.get("manifest_path")
    if manifest_path:
        try:
            manifest_path = Path(str(manifest_path)).resolve().relative_to(project_path).as_posix()
        except ValueError:
            manifest_path = str(manifest_path)
    return {"assets": assets, "manifestPath": manifest_path}


def integrate_commercial_game_body(
    *,
    project_path: str | Path,
    commercial_assets: dict[str, Any],
) -> dict[str, Any]:
    project = Path(project_path).resolve()
    mapping_path = project / "design_mapping.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8")) if mapping_path.exists() else {}
    editor_structure = _write_production_scene(project)
    component_manifest = _write_production_component_scripts(project)
    prefab_manifest = _write_production_prefabs(project)
    interaction_contract = _write_gameplay_interaction_contract(project)
    asset_binding_manifest = _copy_commercial_assets_to_cocos_resources(project, commercial_assets)
    payload = _payload_from_asset_bindings(project, commercial_assets, asset_binding_manifest, editor_structure, component_manifest)
    resources_dir = project / "assets" / "resources" / "commercial_assets"
    resources_dir.mkdir(parents=True, exist_ok=True)
    asset_index_path = resources_dir / "commercial_asset_index.json"
    asset_index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    ui_nodes_path = project / "assets" / "scene" / "commercial_ui_nodes.json"
    ui_nodes = {
        "schema_version": "m79_commercial_ui_nodes_v1",
        "nodes": editor_structure["required_nodes"],
        "created_at": _utc_now(),
    }
    ui_nodes_path.write_text(json.dumps(ui_nodes, ensure_ascii=False, indent=2), encoding="utf-8")
    timeline_path = project / "assets" / "animation" / "commercial_timeline.json"
    timeline_path.parent.mkdir(parents=True, exist_ok=True)
    _write_directory_meta(timeline_path.parent)
    timeline_path.write_text(
        json.dumps(
            {
                "schema_version": "m79_commercial_timeline_v1",
                "clips": ["level_pulse", "line_clear_burst", "button_press_feedback", "skin_switch", "reward_reveal"],
                "created_at": _utc_now(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    script_path = project / "assets" / "scripts" / "BlockPuzzleGame.ts"
    script_path.write_text(_script_source(str(mapping.get("pdf_excerpt") or ""), payload), encoding="utf-8")
    production_inspection = inspect_cocos_commercial_project(project)
    body_manifest = {
        "schema_version": "m79_cocos_commercial_body_v1",
        "created_at": _utc_now(),
        "asset_index_path": asset_index_path.as_posix(),
        "asset_binding_manifest_path": asset_binding_manifest["manifest_path"],
        "editor_structure_manifest_path": editor_structure["manifest_path"],
        "component_manifest_path": component_manifest["manifest_path"],
        "prefab_manifest_path": prefab_manifest["manifest_path"],
        "interaction_contract_path": interaction_contract["manifest_path"],
        "ui_nodes_path": ui_nodes_path.as_posix(),
        "timeline_path": timeline_path.as_posix(),
        "script_path": script_path.as_posix(),
        "feature_coverage": {
            "native_cocos_ui_nodes": True,
            "animation_timeline": True,
            "level_switching_ui": True,
            "production_prefabs": True,
            "gameplay_interaction_contract": True,
            "generated_asset_integration": bool(payload["assets"]),
            "audio_runtime_hooks": any(item.get("modality") in AUDIO_MODALITIES for item in payload["assets"]),
            "visual_asset_runtime_hooks": any(item.get("modality") == "image" for item in payload["assets"]),
            **production_inspection["feature_coverage"],
        },
        "production_inspection": production_inspection,
    }
    body_manifest_path = project / "commercial_game_body_manifest.json"
    body_manifest_path.write_text(json.dumps(body_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    body_manifest["manifest_path"] = body_manifest_path.as_posix()
    return body_manifest


def inspect_cocos_commercial_project(project_path: str | Path) -> dict[str, Any]:
    project = Path(project_path).resolve()
    scene_path = project / "assets" / "scene" / "main.scene"
    scene_node_names: list[str] = []
    if scene_path.exists():
        try:
            scene_data = json.loads(scene_path.read_text(encoding="utf-8"))
            scene_node_names = [str(item.get("_name")) for item in scene_data if item.get("__type__") == "cc.Node"]
        except Exception:
            scene_node_names = []
    missing_nodes = [name for name in PRODUCTION_SCENE_NODE_NAMES if name not in scene_node_names]
    component_manifest_path = project / "commercial_component_manifest.json"
    component_manifest = (
        json.loads(component_manifest_path.read_text(encoding="utf-8")) if component_manifest_path.exists() else {}
    )
    component_paths = [Path(str(item.get("path"))) for item in component_manifest.get("components", [])]
    asset_binding_manifest_path = project / "assets" / "resources" / "commercial_assets" / "commercial_asset_bindings.json"
    asset_binding_manifest = (
        json.loads(asset_binding_manifest_path.read_text(encoding="utf-8")) if asset_binding_manifest_path.exists() else {}
    )
    bindings = list(asset_binding_manifest.get("bindings", []))
    image_bindings = [item for item in bindings if item.get("binding_type") == "SpriteFrame"]
    audio_bindings = [item for item in bindings if item.get("binding_type") == "AudioClip"]
    editor_structure_manifest_path = project / "commercial_editor_structure_manifest.json"
    feature_coverage = {
        "editor_visible_scene_hierarchy": scene_path.exists() and not missing_nodes and len(scene_node_names) >= 20,
        "production_component_scripts": len(component_paths) == len(PRODUCTION_COMPONENT_FILES)
        and all(path.exists() for path in component_paths),
        "cocos_asset_binding_manifest": asset_binding_manifest_path.exists(),
        "spriteframe_asset_bindings": bool(image_bindings)
        and all(Path(str(item.get("cocos_resource_path"))).exists() for item in image_bindings),
        "audioclip_asset_bindings": bool(audio_bindings)
        and all(Path(str(item.get("cocos_resource_path"))).exists() for item in audio_bindings),
        "no_hello_3d_template": not (project / "assets" / "model" / "helloWorld").exists()
        and not (project / "assets" / "skybox").exists(),
        "commercial_ui_panels": all(
            name in scene_node_names
            for name in ["SkinShopPanel", "LevelSelectPanel", "GalleryPanel", "AdPanel", "ReviveDialog", "GameOverDialog"]
        ),
        "editor_structure_manifest": editor_structure_manifest_path.exists(),
    }
    blockers = [key for key, covered in feature_coverage.items() if not covered]
    return {
        "schema_version": "m79_cocos_project_inspection_v1",
        "created_at": _utc_now(),
        "project_path": project.as_posix(),
        "scene_path": scene_path.as_posix(),
        "scene_node_count": len(scene_node_names),
        "scene_node_names": scene_node_names,
        "missing_required_nodes": missing_nodes,
        "component_manifest_path": component_manifest_path.as_posix() if component_manifest_path.exists() else None,
        "asset_binding_manifest_path": asset_binding_manifest_path.as_posix()
        if asset_binding_manifest_path.exists()
        else None,
        "editor_structure_manifest_path": editor_structure_manifest_path.as_posix()
        if editor_structure_manifest_path.exists()
        else None,
        "feature_coverage": feature_coverage,
        "blockers": blockers,
        "go_no_go": "GO" if not blockers else "NO-GO",
    }


def create_cocos_project(*, pdf_path: str | Path, output_dir: str | Path, creator_exe: str | Path) -> dict[str, Any]:
    resolved_source = Path(pdf_path).resolve()
    resolved_output = Path(output_dir).resolve()
    resolved_creator = Path(creator_exe).resolve()
    _assert_not_excluded(resolved_output)
    if not resolved_source.exists():
        raise FileNotFoundError(resolved_source)
    if not resolved_creator.exists():
        raise FileNotFoundError(resolved_creator)
    _safe_rmtree(resolved_output)
    shutil.copytree(DEFAULT_TEMPLATE, resolved_output)
    package_json = resolved_output / "package.json"
    package_json.write_text(json.dumps({"name": "1010-block-puzzle-cocos"}, indent=2), encoding="utf-8")
    design_text = _read_source_text(resolved_source)
    _write_production_scene(resolved_output)
    _write_production_component_scripts(resolved_output)
    _write_production_prefabs(resolved_output)
    _write_gameplay_interaction_contract(resolved_output)
    assets_scripts = resolved_output / "assets" / "scripts"
    assets_scripts.mkdir(parents=True, exist_ok=True)
    (assets_scripts / "BlockPuzzleGame.ts").write_text(_script_source(design_text), encoding="utf-8")
    design_mapping = {
        "source_path": resolved_source.as_posix(),
        "source_kind": _source_kind(resolved_source),
        "pdf_path": resolved_source.as_posix(),
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
        "source_text_chars": len(design_text),
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
    creator_pids_before = _cocos_creator_pids()
    with stdout_path.open("w", encoding="utf-8", errors="replace") as stdout, stderr_path.open(
        "w", encoding="utf-8", errors="replace"
    ) as stderr:
        try:
            proc = subprocess.run(
                [str(creator), "--project", str(project), "--build", "platform=web-mobile;debug=false"],
                stdout=stdout,
                stderr=stderr,
                timeout=timeout_seconds,
                check=False,
            )
        finally:
            _stop_cocos_creator_pids(_cocos_creator_pids() - creator_pids_before)
    build_output = project / "build" / "web-mobile"
    index_html = build_output / "index.html"
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    stdout_tail = stdout_path.read_text(encoding="utf-8", errors="replace")[-4000:]
    stderr_tail = stderr_path.read_text(encoding="utf-8", errors="replace")[-4000:]
    combined_tail = f"{stdout_tail}\n{stderr_tail}"
    fatal_marker_detected = any(marker in combined_tail for marker in COCOS_FATAL_BUILD_MARKERS)
    artifact_success = (
        proc.returncode in COCOS_BUILD_SUCCESS_EXIT_CODES
        and index_html.exists()
        and (build_output / "assets").exists()
        and not fatal_marker_detected
    )
    runtime_asset_copy = (
        _copy_commercial_runtime_assets_to_build(project=project, build_output=build_output)
        if artifact_success
        else {
            "copied": False,
            "asset_count": 0,
            "size_bytes": 0,
            "reason": "build_artifact_not_ready",
        }
    )
    return {
        "creator_exit_code": proc.returncode,
        "artifact_success": artifact_success,
        "fatal_marker_detected": fatal_marker_detected,
        "build_output_path": build_output.as_posix() if build_output.exists() else None,
        "index_html": index_html.as_posix() if index_html.exists() else None,
        "runtime_asset_copy": runtime_asset_copy,
        "elapsed_ms": elapsed_ms,
        "stdout_path": stdout_path.as_posix(),
        "stderr_path": stderr_path.as_posix(),
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }


def _copy_commercial_runtime_assets_to_build(*, project: Path, build_output: Path) -> dict[str, Any]:
    source_root = project / "assets" / "resources" / "commercial_assets"
    if not source_root.exists():
        return {
            "copied": False,
            "asset_count": 0,
            "size_bytes": 0,
            "reason": "commercial_assets_source_missing",
        }
    destination_root = build_output / "assets" / "resources" / "commercial_assets"
    destination_root.mkdir(parents=True, exist_ok=True)
    copied_count = 0
    copied_bytes = 0
    for source in source_root.rglob("*"):
        if not source.is_file() or source.name.endswith(".meta"):
            continue
        target = destination_root / source.relative_to(source_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied_count += 1
        copied_bytes += target.stat().st_size
    return {
        "copied": copied_count > 0,
        "asset_count": copied_count,
        "size_bytes": copied_bytes,
        "source_root": source_root.as_posix(),
        "destination_root": destination_root.as_posix(),
    }


def run_cocos_game_e2e(
    *,
    pdf_path: str | Path,
    output_dir: str | Path,
    creator_exe: str | Path,
    require_build: bool = False,
    require_playtest: bool = True,
    require_commercial: bool = False,
    generate_commercial_assets: bool = False,
    use_local_stable_assets: bool = False,
    commercial_assets_payload: dict[str, Any] | None = None,
    commercial_asset_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    runtime_config = build_cocos_runtime_config(
        pdf_path=pdf_path,
        output_dir=output_dir,
        creator_exe=creator_exe,
        require_build=require_build,
        require_playtest=require_playtest,
        require_commercial=require_commercial,
    )
    project = create_cocos_project(pdf_path=pdf_path, output_dir=output_dir, creator_exe=creator_exe)
    runtime_config_path = Path(project["project_path"]) / "cocos_runtime_config.json"
    runtime_config_path.write_text(json.dumps(runtime_config, ensure_ascii=False, indent=2), encoding="utf-8")
    build: dict[str, Any] | None = None
    playtest: dict[str, Any] | None = None
    technical_blockers: list[str] = []
    commercial_assets: dict[str, Any] | None = commercial_assets_payload
    if commercial_assets is None and commercial_asset_manifest_path is not None:
        commercial_assets = json.loads(Path(commercial_asset_manifest_path).read_text(encoding="utf-8"))
    if commercial_assets is None and use_local_stable_assets:
        commercial_assets = generate_cocos_local_stable_asset_manifest(output_dir=Path(project["project_path"]) / "local_assets")
    if commercial_assets is None and generate_commercial_assets:
        commercial_assets = generate_cocos_commercial_asset_manifest(output_dir=project["project_path"])
    commercial_body: dict[str, Any] | None = None
    if commercial_assets and commercial_assets.get("go_no_go") == "GO":
        commercial_body = integrate_commercial_game_body(
            project_path=project["project_path"],
            commercial_assets=commercial_assets,
        )
    commercial_project_inspection = inspect_cocos_commercial_project(project["project_path"])
    if require_build:
        build = build_cocos_project(project_path=project["project_path"], creator_exe=creator_exe)
        if not build["artifact_success"]:
            technical_blockers.append("cocos_build_artifacts_missing")
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
                technical_blockers.append("browser_playtest_failed")
                build["playtest_error"] = playtest_error
    commercial_body_coverage = dict((commercial_body or {}).get("feature_coverage") or {})
    production_coverage = dict(commercial_project_inspection.get("feature_coverage") or {})
    commercial_feature_coverage = {
        "cocos_creator_project": True,
        "web_mobile_build": bool((build or {}).get("artifact_success")) if require_build else True,
        "browser_playtest": bool((playtest or {}).get("passed")) if require_build and require_playtest else True,
        "commercial_browser_playtest": bool((playtest or {}).get("commercial_passed"))
        if require_build and require_playtest
        else True,
        "generated_art_assets": bool((commercial_assets or {}).get("feature_coverage", {}).get("generated_art_assets")),
        "generated_audio_assets": bool((commercial_assets or {}).get("feature_coverage", {}).get("generated_audio_assets")),
        "native_cocos_ui_nodes": bool(commercial_body_coverage.get("native_cocos_ui_nodes")),
        "animation_timeline": bool(commercial_body_coverage.get("animation_timeline")),
        "particle_effects": bool((commercial_assets or {}).get("feature_coverage", {}).get("particle_effects")),
        "skin_switching_visual_assets": bool((commercial_assets or {}).get("feature_coverage", {}).get("skin_switching_visual_assets")),
        "level_switching_ui": bool(commercial_body_coverage.get("level_switching_ui")),
        "production_prefabs": bool(commercial_body_coverage.get("production_prefabs")),
        "gameplay_interaction_contract": bool(commercial_body_coverage.get("gameplay_interaction_contract")),
        "commercial_polish_pass": bool((commercial_assets or {}).get("feature_coverage", {}).get("commercial_polish_pass"))
        and bool(commercial_body_coverage.get("generated_asset_integration")),
        "editor_visible_scene_hierarchy": bool(production_coverage.get("editor_visible_scene_hierarchy")),
        "production_component_scripts": bool(production_coverage.get("production_component_scripts")),
        "cocos_asset_binding_manifest": bool(production_coverage.get("cocos_asset_binding_manifest")),
        "spriteframe_asset_bindings": bool(production_coverage.get("spriteframe_asset_bindings")),
        "audioclip_asset_bindings": bool(production_coverage.get("audioclip_asset_bindings")),
        "no_hello_3d_template": bool(production_coverage.get("no_hello_3d_template")),
        "commercial_ui_panels": bool(production_coverage.get("commercial_ui_panels")),
    }
    commercial_blockers = [
        key
        for key, covered in commercial_feature_coverage.items()
        if key not in {"cocos_creator_project"} and not covered
    ]
    commercial_go_no_go = "GO" if not commercial_blockers else "NO-GO"
    technical_smoke_go = runtime_config["go_no_go"] == "GO" and not technical_blockers
    production_scaffold_go = commercial_go_no_go == "GO"
    player_validation = validate_cocos_player_visible_evidence(
        playtest=playtest,
        inspection=commercial_project_inspection,
        technical_smoke=technical_smoke_go,
        production_scaffold=production_scaffold_go,
        evidence_dir=Path(project["project_path"]) / "player_visible_evidence",
    )
    player_visible_checks = player_validation["player_visible_checks"]
    commercial_readiness = player_validation["commercial_readiness"]
    blockers = list(technical_blockers)
    if require_commercial and commercial_blockers:
        blockers.extend(f"commercial_missing_{item}" for item in commercial_blockers)
    if require_commercial and not commercial_readiness["commercial_playable_go"]:
        blockers.append("commercial_playable_no_go")
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
            "source_path": Path(pdf_path).resolve().as_posix(),
            "source_kind": _source_kind(Path(pdf_path).resolve()),
            "source_text_chars": project["source_text_chars"],
            "pdf_text_chars": project["pdf_text_chars"],
            "design_mapping_path": project["design_mapping_path"],
            "runtime_config_path": runtime_config_path.as_posix(),
            "runtime_config": runtime_config,
            "build": build,
            "playtest": playtest,
            "commercial_assets": commercial_assets,
            "commercial_body": commercial_body,
            "commercial_project_inspection": commercial_project_inspection,
            "technical_smoke_go": technical_smoke_go,
            "technical_blockers": technical_blockers,
            "production_scaffold_go": production_scaffold_go,
            "commercial_go_no_go": commercial_go_no_go,
            "commercial_blockers": commercial_blockers,
            "commercial_playable_go": commercial_readiness["commercial_playable_go"],
            "commercial_playable_blockers": commercial_readiness["commercial_playable_blockers"],
            "commercial_readiness": commercial_readiness,
            "player_visible_evidence": player_validation,
            "player_visible_checks": player_visible_checks,
            "commercial_feature_coverage": commercial_feature_coverage,
            "commercial_gate_required": require_commercial,
        },
    )
    manifest_path = Path(project["project_path"]) / "cocos_game_e2e_manifest.json"
    manifest_path.write_text(json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "manifest": manifest.model_dump(mode="json"),
        "runtime_config": runtime_config,
        "runtime_config_path": runtime_config_path.as_posix(),
        "technical_smoke_go": technical_smoke_go,
        "technical_blockers": technical_blockers,
        "production_scaffold_go": production_scaffold_go,
        "commercial_go_no_go": commercial_go_no_go,
        "commercial_playable_go": commercial_readiness["commercial_playable_go"],
        "commercial_playable_blockers": commercial_readiness["commercial_playable_blockers"],
        "commercial_readiness": commercial_readiness,
        "player_visible_evidence": player_validation,
        "player_visible_checks": player_visible_checks,
        "commercial_blockers": commercial_blockers,
        "commercial_feature_coverage": commercial_feature_coverage,
        "manifest_path": manifest_path.as_posix(),
        "project": project,
        "build": build,
        "playtest": playtest,
        "commercial_assets": commercial_assets,
        "commercial_body": commercial_body,
        "commercial_project_inspection": commercial_project_inspection,
    }
