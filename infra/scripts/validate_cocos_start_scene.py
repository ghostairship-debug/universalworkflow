from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from packages.contributions.games.cocos.e2e import PRODUCTION_SCENE_NODE_NAMES


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        return {"__invalid_json__": str(exc)}


def _referenced_object(data: list[Any], owner: dict[str, Any], field: str) -> dict[str, Any] | None:
    ref = owner.get(field)
    ref_id = ref.get("__id__") if isinstance(ref, dict) else None
    if not isinstance(ref_id, int) or ref_id < 0 or ref_id >= len(data):
        return None
    candidate = data[ref_id]
    return candidate if isinstance(candidate, dict) else None


def validate_cocos_start_scene(project_dir: str | Path) -> dict[str, Any]:
    project = Path(project_dir).resolve()
    scene_path = project / "assets" / "scene" / "main.scene"
    scene_meta_path = project / "assets" / "scene" / "main.scene.meta"
    scene_settings_path = project / "settings" / "v2" / "packages" / "scene.json"
    scene_data = _read_json(scene_path)
    scene_meta = _read_json(scene_meta_path)
    scene_settings = _read_json(scene_settings_path)
    issues: list[str] = []

    if not project.exists():
        issues.append("project_dir_missing")
    if not isinstance(scene_data, list):
        issues.append("main_scene_missing_or_invalid")
        scene_data = []
    if not isinstance(scene_meta, dict):
        issues.append("main_scene_meta_missing_or_invalid")
        scene_meta = {}
    if not isinstance(scene_settings, dict):
        issues.append("scene_settings_missing_or_invalid")
        scene_settings = {}

    scene_asset = next((item for item in scene_data if isinstance(item, dict) and item.get("__type__") == "cc.SceneAsset"), None)
    scene = next((item for item in scene_data if isinstance(item, dict) and item.get("__type__") == "cc.Scene"), None)
    scene_globals_refs = [
        index
        for index, item in enumerate(scene_data)
        if isinstance(item, dict) and item.get("__type__") == "cc.SceneGlobals"
    ]
    if scene_asset is None:
        issues.append("scene_asset_missing")
    if scene is None:
        issues.append("scene_object_missing")
    if not scene_globals_refs:
        issues.append("scene_globals_missing")

    scene_globals: dict[str, Any] | None = None
    if isinstance(scene, dict):
        globals_ref = scene.get("_globals")
        globals_id = globals_ref.get("__id__") if isinstance(globals_ref, dict) else None
        if globals_id is None:
            issues.append("scene_globals_reference_missing")
        elif not isinstance(globals_id, int) or globals_id < 0 or globals_id >= len(scene_data):
            issues.append("scene_globals_reference_invalid")
        else:
            candidate = scene_data[globals_id]
            if isinstance(candidate, dict) and candidate.get("__type__") == "cc.SceneGlobals":
                scene_globals = candidate
            else:
                issues.append("scene_globals_reference_invalid")
    if scene_globals is not None and "_skybox" not in scene_globals:
        issues.append("scene_globals_skybox_missing")
    if scene_globals is not None:
        required_global_refs = {
            "ambient": "cc.AmbientInfo",
            "shadows": "cc.ShadowsInfo",
            "_skybox": "cc.SkyboxInfo",
            "fog": "cc.FogInfo",
            "octree": "cc.OctreeInfo",
            "skin": "cc.SkinInfo",
        }
        for field, expected_type in required_global_refs.items():
            target = _referenced_object(scene_data, scene_globals, field)
            if target is None or target.get("__type__") != expected_type:
                issues.append(f"scene_globals_{field.strip('_')}_reference_invalid")
        for field in ["shadows", "_skybox", "fog", "octree", "skin"]:
            target = _referenced_object(scene_data, scene_globals, field)
            if isinstance(target, dict) and "_enabled" not in target:
                issues.append(f"scene_globals_{field.strip('_')}_enabled_missing")

    meta_uuid = str(scene_meta.get("uuid") or "")
    settings_uuid = str(scene_settings.get("current-scene") or "")
    scene_uuid = str(scene.get("_id") or "") if isinstance(scene, dict) else ""
    if not meta_uuid:
        issues.append("scene_meta_uuid_missing")
    if not settings_uuid:
        issues.append("scene_settings_current_scene_missing")
    if meta_uuid and settings_uuid and meta_uuid != settings_uuid:
        issues.append("scene_settings_uuid_mismatch")
    if scene_uuid and meta_uuid and scene_uuid != meta_uuid:
        issues.append("scene_object_uuid_mismatch")

    node_names = [
        str(item.get("_name"))
        for item in scene_data
        if isinstance(item, dict) and item.get("__type__") == "cc.Node"
    ]
    missing_nodes = [name for name in PRODUCTION_SCENE_NODE_NAMES if name not in node_names]
    if missing_nodes:
        issues.append("required_scene_nodes_missing")

    status = "passed" if not issues else "failed"
    return {
        "schema_version": "cocos_start_scene_validation_v1",
        "status": status,
        "project_dir": project.as_posix(),
        "scene_path": scene_path.as_posix(),
        "scene_meta_path": scene_meta_path.as_posix(),
        "scene_settings_path": scene_settings_path.as_posix(),
        "scene_uuid": scene_uuid or None,
        "meta_uuid": meta_uuid or None,
        "settings_current_scene": settings_uuid or None,
        "scene_node_count": len(node_names),
        "scene_globals_ref_count": len(scene_globals_refs),
        "missing_required_nodes": missing_nodes,
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Cocos Creator start scene wiring for commercial game builds.")
    parser.add_argument("--project-dir", required=True)
    args = parser.parse_args(argv)
    payload = validate_cocos_start_scene(args.project_dir)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
