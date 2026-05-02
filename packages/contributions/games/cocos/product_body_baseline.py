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
    for key in SEMANTIC_TRACE_KEYS:
        trace_path = trace_dir / f"{key}.json"
        traces[key] = trace_path.as_posix()
        _write_json_if_changed(trace_path, {"trace": key, "source": "cocos_product_body_baseline"}, changed_files)

    gameplay = build_baseline_gameplay_semantic_evidence(traces)
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


def build_baseline_gameplay_semantic_evidence(traces: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        "board_state": {"rows": 10, "cols": 10},
        "piece_shapes": PIECE_SHAPES,
        "candidate_tray": [{"slot": index, "state": "available"} for index in range(3)],
        "semantic_traces": dict(traces or {key: f"semantic_traces/{key}.json" for key in SEMANTIC_TRACE_KEYS}),
        "baseline_only": True,
        "runtime_hook": False,
        "canvas_only": False,
    }


def build_baseline_product_body_evidence(project_dir: str | Path, *, scene_path: str | Path) -> dict[str, Any]:
    return {
        "scene_nodes": SCENE_NODES,
        "cocos_component_bindings": REQUIRED_COMPONENT_BINDINGS,
        "scene_path": Path(scene_path).as_posix(),
        "product_body_path": Path(project_dir, "workflow_product_body_baseline.json").as_posix(),
        "baseline_only": True,
        "runtime_hook": False,
        "canvas_only": False,
    }


def _component_source(component: str) -> str:
    return (
        "import { _decorator, Component } from 'cc';\n"
        "const { ccclass } = _decorator;\n\n"
        f"@ccclass('{component}')\n"
        f"export class {component} extends Component {{\n"
        f"  public readonly workflowComponentId = '{component}';\n"
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
