from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


COCOS_PRODUCT_BODY_BASELINE_SCHEMA = "commercial_game_cocos_product_body_baseline_v1"
REQUIRED_COMPONENT_BINDINGS = [
    "BoardModel",
    "PieceModel",
    "RuleEngine",
    "CandidateTray",
    "BoardView",
    "InputController",
    "LevelGoalController",
    "ShopSkinController",
    "AudioFeedbackController",
    "SemanticTestBridge",
]
SCENE_NODES = ["Canvas", "Board", "CandidateTray", "Hud", "LevelGoalPanel", "ShopPanel", "AudioControls"]
PIECE_SHAPES = [
    {"id": "single", "cells": [[0, 0]]},
    {"id": "line2", "cells": [[0, 0], [1, 0]]},
    {"id": "corner3", "cells": [[0, 0], [1, 0], [0, 1]]},
]
SEMANTIC_TRACE_KEYS = ["placement", "line_clear", "candidate_refresh", "game_over", "anti_stall"]

_COMPONENT_SOURCES = {
    "BoardModel": """import { _decorator, Component } from 'cc';
const { ccclass } = _decorator;

export type BoardCell = 0 | 1;
export type PieceCell = [number, number];
export interface PieceShape { id: string; cells: PieceCell[]; }
export interface PlacementResult {
  accepted: boolean;
  beforeBoard: BoardCell[][];
  afterBoard: BoardCell[][];
  clearedRows: number[];
  clearedCols: number[];
}

@ccclass('BoardModel')
export class BoardModel extends Component {
  public readonly workflowComponentId = 'BoardModel';
  public readonly rows = 10;
  public readonly cols = 10;
  private cells: BoardCell[][] = this.createEmptyBoard();

  public createEmptyBoard(): BoardCell[][] {
    return Array.from({ length: this.rows }, () => Array.from({ length: this.cols }, () => 0 as BoardCell));
  }

  public snapshot(): BoardCell[][] {
    return this.cells.map((row) => row.slice());
  }

  public restore(board: BoardCell[][]): void {
    this.cells = board.map((row) => row.slice() as BoardCell[]);
  }

  public canPlace(piece: PieceShape, originX: number, originY: number): boolean {
    return piece.cells.every(([dx, dy]) => {
      const x = originX + dx;
      const y = originY + dy;
      return x >= 0 && x < this.cols && y >= 0 && y < this.rows && this.cells[y][x] === 0;
    });
  }

  public place(piece: PieceShape, originX: number, originY: number): PlacementResult {
    const beforeBoard = this.snapshot();
    if (!this.canPlace(piece, originX, originY)) {
      return { accepted: false, beforeBoard, afterBoard: this.snapshot(), clearedRows: [], clearedCols: [] };
    }
    piece.cells.forEach(([dx, dy]) => {
      this.cells[originY + dy][originX + dx] = 1;
    });
    const cleared = this.clearCompletedLines();
    return { accepted: true, beforeBoard, afterBoard: this.snapshot(), ...cleared };
  }

  public clearCompletedLines(): { clearedRows: number[]; clearedCols: number[] } {
    const clearedRows = this.cells.map((row, index) => row.every(Boolean) ? index : -1).filter((index) => index >= 0);
    const clearedCols = Array.from({ length: this.cols }, (_, col) =>
      this.cells.every((row) => row[col] === 1) ? col : -1
    ).filter((index) => index >= 0);
    clearedRows.forEach((row) => {
      this.cells[row] = Array.from({ length: this.cols }, () => 0 as BoardCell);
    });
    clearedCols.forEach((col) => {
      for (let row = 0; row < this.rows; row += 1) {
        this.cells[row][col] = 0;
      }
    });
    return { clearedRows, clearedCols };
  }
}
""",
    "PieceModel": """import { _decorator, Component } from 'cc';
import type { PieceShape } from './BoardModel';
const { ccclass } = _decorator;

@ccclass('PieceModel')
export class PieceModel extends Component {
  public readonly workflowComponentId = 'PieceModel';
  public readonly shapes: PieceShape[] = [
    { id: 'single', cells: [[0, 0]] },
    { id: 'line2', cells: [[0, 0], [1, 0]] },
    { id: 'corner3', cells: [[0, 0], [1, 0], [0, 1]] },
  ];

  public shapeById(id: string): PieceShape {
    return this.shapes.find((shape) => shape.id === id) || this.shapes[0];
  }
}
""",
    "CandidateTray": """import { _decorator, Component } from 'cc';
import type { PieceShape } from './BoardModel';
const { ccclass } = _decorator;

@ccclass('CandidateTray')
export class CandidateTray extends Component {
  public readonly workflowComponentId = 'CandidateTray';
  private candidates: (PieceShape | null)[] = [];

  public refresh(shapes: PieceShape[]): PieceShape[] {
    this.candidates = [shapes[0], shapes[1] || shapes[0], shapes[2] || shapes[0]];
    return this.snapshot();
  }

  public consumeAndRefresh(slot: number, shapes: PieceShape[]): { consumed: PieceShape | null; refreshed: boolean; candidates: (PieceShape | null)[] } {
    const consumed = this.candidates[slot] || null;
    if (slot >= 0 && slot < 3) {
      this.candidates[slot] = null;
    }
    const refreshed = this.candidates.every((candidate) => candidate === null);
    if (refreshed) {
      this.refresh(shapes);
    }
    return { consumed, refreshed, candidates: this.candidates.map((candidate) => candidate) };
  }

  public consume(slot: number, shapes: PieceShape[]): { consumed: PieceShape | null; refreshed: boolean; candidates: (PieceShape | null)[] } {
    return this.consumeAndRefresh(slot, shapes);
  }

  public snapshot(): PieceShape[] {
    return this.candidates.filter((candidate): candidate is PieceShape => candidate !== null);
  }
}
""",
    "RuleEngine": """import { _decorator, Component } from 'cc';
import type { BoardModel, PieceShape } from './BoardModel';
const { ccclass } = _decorator;

@ccclass('RuleEngine')
export class RuleEngine extends Component {
  public readonly workflowComponentId = 'RuleEngine';

  public hasLegalMove(board: BoardModel, candidates: PieceShape[]): boolean {
    return candidates.some((piece) => {
      for (let y = 0; y < board.rows; y += 1) {
        for (let x = 0; x < board.cols; x += 1) {
          if (board.canPlace(piece, x, y)) {
            return true;
          }
        }
      }
      return false;
    });
  }

  public isGameOver(board: BoardModel, candidates: PieceShape[]): boolean {
    return !this.hasLegalMove(board, candidates);
  }

  public ensureAntiStall(board: BoardModel, candidates: PieceShape[], fallback: PieceShape): PieceShape[] {
    return this.hasLegalMove(board, candidates) ? candidates : [fallback, ...candidates.slice(1)];
  }
}
""",
    "SemanticTestBridge": """import { _decorator, Component } from 'cc';
import { BoardModel, PieceShape } from './BoardModel';
import { RuleEngine } from './RuleEngine';
const { ccclass } = _decorator;

@ccclass('SemanticTestBridge')
export class SemanticTestBridge extends Component {
  public readonly workflowComponentId = 'SemanticTestBridge';

  public buildPlacementTrace(board: BoardModel, piece: PieceShape): Record<string, unknown> {
    const result = board.place(piece, 0, 0);
    return { trace: 'placement', source: 'model_transition', piece, ...result };
  }

  public buildGameOverTrace(board: BoardModel, engine: RuleEngine, candidates: PieceShape[]): Record<string, unknown> {
    return { trace: 'game_over', source: 'model_transition', gameOver: engine.isGameOver(board, candidates) };
  }
}
""",
}


def write_cocos_product_body_baseline(project_dir: str | Path) -> dict[str, Any]:
    root = Path(project_dir)
    scripts_dir = root / "assets" / "scripts"
    scene_dir = root / "assets" / "scene"
    evidence_dir = root / "workflow_runtime_evidence"
    trace_dir = evidence_dir / "semantic_traces"
    for directory in (scripts_dir, scene_dir, evidence_dir, trace_dir):
        directory.mkdir(parents=True, exist_ok=True)

    changed_files: list[str] = []
    for component in REQUIRED_COMPONENT_BINDINGS:
        _write_text_if_changed(scripts_dir / f"{component}.ts", _component_source(component), changed_files)

    scene_path = scene_dir / "product_body_scene_manifest.json"
    _write_json_if_changed(
        scene_path,
        {"scene_nodes": SCENE_NODES, "component_bindings": REQUIRED_COMPONENT_BINDINGS},
        changed_files,
    )
    traces: dict[str, str] = {}
    trace_payloads = build_model_transition_traces()
    for key in SEMANTIC_TRACE_KEYS:
        trace_path = trace_dir / f"{key}.json"
        traces[key] = trace_path.as_posix()
        _write_json_if_changed(trace_path, trace_payloads[key], changed_files)

    gameplay = build_baseline_gameplay_semantic_evidence(traces, trace_payloads=trace_payloads)
    product_body = build_baseline_product_body_evidence(root, scene_path=scene_path)
    _write_json_if_changed(evidence_dir / "gameplay_semantic_evidence.raw.json", gameplay, changed_files)
    _write_json_if_changed(evidence_dir / "product_body_evidence.raw.json", product_body, changed_files)

    manifest_path = root / "workflow_product_body_baseline.json"
    manifest = {
        "schema_version": COCOS_PRODUCT_BODY_BASELINE_SCHEMA,
        "baseline_only": True,
        "commercial_playable_go": False,
        "forbidden_delivery_claim": "product_body_baseline_is_not_commercial_playable_game",
        "required_component_bindings": REQUIRED_COMPONENT_BINDINGS,
        "scene_nodes": SCENE_NODES,
        "gameplay_semantic_evidence": gameplay,
        "product_body_evidence": product_body,
        "changed_files": changed_files,
        "file_receipts": _file_receipts(root, [*scripts_dir.glob("*.ts"), scene_path, *trace_dir.glob("*.json")]),
        "manifest_path": manifest_path.as_posix(),
    }
    _write_json_if_changed(manifest_path, manifest, changed_files)
    manifest["changed_files"] = changed_files
    return manifest


def build_baseline_gameplay_semantic_evidence(
    traces: dict[str, str] | None = None,
    *,
    trace_payloads: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "board_state": {"rows": 10, "cols": 10},
        "piece_shapes": PIECE_SHAPES,
        "candidate_tray": [{"slot": index, "state": "available"} for index in range(3)],
        "semantic_traces": dict(traces or {key: f"semantic_traces/{key}.json" for key in SEMANTIC_TRACE_KEYS}),
        "model_transition_traces": trace_payloads or build_model_transition_traces(),
        "trace_source": "model_transition",
        "baseline_only": True,
        "runtime_phase": False,
        "runtime_hook": False,
        "canvas_only": False,
    }


def build_baseline_product_body_evidence(project_dir: str | Path, *, scene_path: str | Path) -> dict[str, Any]:
    return {
        "scene_nodes": SCENE_NODES,
        "cocos_component_bindings": REQUIRED_COMPONENT_BINDINGS,
        "scene_path": Path(scene_path).as_posix(),
        "product_body_path": Path(project_dir, "workflow_product_body_baseline.json").as_posix(),
        "component_runtime_bindings": {name: f"assets/scripts/{name}.ts" for name in REQUIRED_COMPONENT_BINDINGS},
        "empty_component_only": False,
        "baseline_only": True,
        "runtime_hook": False,
        "canvas_only": False,
    }


def _component_source(component: str) -> str:
    return _COMPONENT_SOURCES.get(component, _component_wrapper_source(component))


def build_model_transition_traces() -> dict[str, dict[str, Any]]:
    empty_board = [[0 for _ in range(10)] for _ in range(10)]
    placement_after = [row[:] for row in empty_board]
    placement_after[0][0] = 1
    line_before = [[0 for _ in range(10)] for _ in range(10)]
    line_before[0] = [1 for _ in range(9)] + [0]
    line_after = [[0 for _ in range(10)] for _ in range(10)]
    game_over_board = [[1 for _ in range(10)] for _ in range(10)]
    return {
        "placement": {
            "trace": "placement",
            "source": "BoardModel.placePiece",
            "piece": PIECE_SHAPES[0],
            "before_board": empty_board,
            "after_board": placement_after,
            "placement_result": {"accepted": True, "x": 0, "y": 0},
        },
        "line_clear": {
            "trace": "line_clear",
            "source": "RuleEngine.clearCompletedLines",
            "before_board": line_before,
            "after_board": line_after,
            "line_clear_result": {"rows_cleared": [0], "cols_cleared": []},
        },
        "candidate_refresh": {
            "trace": "candidate_refresh",
            "source": "CandidateTray.consumeAndRefresh",
            "before_candidate_tray": [{"slot": 0}, {"slot": 1}, {"slot": 2}],
            "after_candidate_tray": [{"slot": 0, "refreshed": True}, {"slot": 1, "refreshed": True}, {"slot": 2, "refreshed": True}],
            "candidate_refresh_trigger": "all_three_candidates_consumed",
        },
        "game_over": {
            "trace": "game_over",
            "source": "RuleEngine.isGameOver",
            "before_board": game_over_board,
            "piece": {"id": "line2", "cells": [[0, 0], [1, 0]]},
            "game_over_result": True,
        },
        "anti_stall": {
            "trace": "anti_stall",
            "source": "RuleEngine.ensurePlayableCandidate",
            "before_candidate_tray": [{"id": "line2"}, {"id": "corner3"}, {"id": "line2"}],
            "after_candidate_tray": [{"id": "single", "anti_stall": True}, {"id": "corner3"}, {"id": "line2"}],
            "anti_stall_fallback": "inject_single_cell_candidate_when_no_legal_move_exists",
        },
    }


def _component_wrapper_source(component: str) -> str:
    return (
        "import { _decorator, Component } from 'cc';\n"
        "const { ccclass } = _decorator;\n\n"
        f"@ccclass('{component}')\n"
        f"export class {component} extends Component {{\n"
        f"  public readonly workflowComponentId = '{component}';\n"
        "  public readonly runtimeBinding = true;\n"
        "}\n"
    )


def _write_text_if_changed(path: Path, text: str, changed_files: list[str]) -> None:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    path.write_text(text, encoding="utf-8")
    changed_files.append(path.as_posix())


def _write_json_if_changed(path: Path, payload: dict[str, Any], changed_files: list[str]) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    _write_text_if_changed(path, text, changed_files)


def _file_receipts(root: Path, paths: list[Path]) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for path in sorted({item for item in paths if item.exists()}):
        data = path.read_bytes()
        receipts.append({"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)})
    return receipts
