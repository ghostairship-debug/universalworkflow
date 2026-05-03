from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_SCRIPT_MARKERS = [
    "ccclass('BlockPuzzleGame')",
    "class BlockPuzzleGame extends Component",
    "block-puzzle-canvas",
    "__COCOS_BLOCK_PUZZLE_E2E__",
    "candidateCenters",
    "clearTarget",
    "buttonCenters",
    "featureCoverage",
    "audioPlaybackVerified",
    "bgmStarted",
    "sfxPlaybackVerified",
    "volumeToggleUsable",
]


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        return {"__invalid_json__": str(exc)}


def validate_cocos_browser_runtime_hook(project_dir: str | Path) -> dict[str, Any]:
    project = Path(project_dir).resolve()
    script_path = project / "assets" / "scripts" / "BlockPuzzleGame.ts"
    script_meta_path = project / "assets" / "scripts" / "BlockPuzzleGame.ts.meta"
    scene_path = project / "assets" / "scene" / "main.scene"
    runtime_source_sets = [
        [
            project / "assets" / "scripts" / "gameplay" / "CommercialCoreLoopRuntime.ts",
            project / "assets" / "scripts" / "gameplay" / "CommercialGameplaySemanticBridge.ts",
            project / "assets" / "scripts" / "AudioFeedbackController.ts",
        ],
        [
            project / "assets" / "scripts" / "BoardModel.ts",
            project / "assets" / "scripts" / "RuleEngine.ts",
            project / "assets" / "scripts" / "SemanticTestBridge.ts",
            project / "assets" / "scripts" / "AudioFeedbackController.ts",
        ],
    ]
    runtime_sources = next(
        (source_set for source_set in runtime_source_sets if all(path.exists() for path in source_set)),
        [],
    )
    source_backed_bridge = bool(runtime_sources)
    issues: list[str] = []
    script_text = ""

    if not script_path.exists():
        issues.append("block_puzzle_runtime_script_missing")
    else:
        script_text = script_path.read_text(encoding="utf-8", errors="replace")
    if not script_meta_path.exists():
        issues.append("block_puzzle_runtime_script_meta_missing")
    else:
        meta = _read_json(script_meta_path)
        if not isinstance(meta, dict) or meta.get("importer") != "typescript" or not meta.get("uuid"):
            issues.append("block_puzzle_runtime_script_meta_invalid")

    missing_markers = [marker for marker in REQUIRED_SCRIPT_MARKERS if marker not in script_text]
    if missing_markers:
        issues.append("block_puzzle_runtime_markers_missing")

    scene_data = _read_json(scene_path)
    component_refs: list[int] = []
    attached = False
    if not isinstance(scene_data, list):
        issues.append("main_scene_missing_or_invalid")
        scene_data = []
    for index, item in enumerate(scene_data):
        if not isinstance(item, dict):
            continue
        if item.get("__type__") == "BlockPuzzleGame":
            component_refs.append(index)
    for item in scene_data:
        if not isinstance(item, dict):
            continue
        refs = item.get("_components")
        if not isinstance(refs, list):
            continue
        ref_ids = [ref.get("__id__") for ref in refs if isinstance(ref, dict)]
        if any(ref_id in component_refs for ref_id in ref_ids):
            attached = True
            break
    if not component_refs:
        if not source_backed_bridge:
            issues.append("block_puzzle_scene_component_missing")
    if component_refs and not attached:
        issues.append("block_puzzle_scene_component_not_attached")

    status = "passed" if not issues else "failed"
    return {
        "schema_version": "cocos_browser_runtime_hook_validation_v1",
        "status": status,
        "project_dir": project.as_posix(),
        "script_path": script_path.as_posix(),
        "script_meta_path": script_meta_path.as_posix(),
        "scene_path": scene_path.as_posix(),
        "missing_script_markers": missing_markers,
        "component_ref_count": len(component_refs),
        "component_attached": attached,
        "browser_runtime_source_backed": source_backed_bridge,
        "runtime_sources": [path.as_posix() for path in runtime_sources],
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Cocos browser runtime hook coverage for commercial playtest.")
    parser.add_argument("--project-dir", required=True)
    args = parser.parse_args(argv)
    payload = validate_cocos_browser_runtime_hook(args.project_dir)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
