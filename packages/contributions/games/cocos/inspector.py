from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contributions.games.cocos.capabilities import REQUIRED_PLAYER_VISIBLE_CHECKS
from packages.contributions.games.cocos.e2e import (
    GAMEPLAY_INTERACTION_EVENTS,
    PRODUCTION_COMPONENT_FILES,
    PRODUCTION_PREFAB_FILES,
    PRODUCTION_SCENE_NODE_NAMES,
)


COCOS_PROJECT_INSPECTOR_V2_SCHEMA = "m105_cocos_project_inspector_v2"
COCOS_DELIVERY_MODES_SCHEMA = "m105_cocos_delivery_modes_v1"
REQUIRED_PANEL_NODES = [
    "SkinShopPanel",
    "LevelSelectPanel",
    "GalleryPanel",
    "AdPanel",
    "ReviveDialog",
    "GameOverDialog",
]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _scene_node_names(scene_path: Path) -> list[str]:
    data = _read_json(scene_path)
    if not isinstance(data, list):
        return []
    return [str(item.get("_name")) for item in data if isinstance(item, dict) and item.get("__type__") == "cc.Node"]


def inspect_cocos_project_v2(
    project_path: str | Path,
    *,
    evidence_dir: str | Path | None = None,
) -> dict[str, Any]:
    project = Path(project_path).resolve()
    scene_path = project / "assets" / "scene" / "main.scene"
    script_path = project / "assets" / "scripts" / "BlockPuzzleGame.ts"
    package_json_path = project / "package.json"
    runtime_config_path = project / "cocos_runtime_config.json"
    component_manifest_path = project / "commercial_component_manifest.json"
    asset_binding_manifest_path = project / "assets" / "resources" / "commercial_assets" / "commercial_asset_bindings.json"
    editor_structure_manifest_path = project / "commercial_editor_structure_manifest.json"
    body_manifest_path = project / "commercial_game_body_manifest.json"
    e2e_manifest_path = project / "cocos_game_e2e_manifest.json"
    prefab_manifest_path = project / "commercial_prefab_manifest.json"
    interaction_contract_path = project / "gameplay_interaction_contract.json"
    prefab_dir = project / "assets" / "prefab"

    scene_nodes = _scene_node_names(scene_path)
    missing_nodes = [name for name in PRODUCTION_SCENE_NODE_NAMES if name not in scene_nodes]
    missing_panels = [name for name in REQUIRED_PANEL_NODES if name not in scene_nodes]
    component_manifest = _read_json(component_manifest_path)
    component_paths = [
        Path(str(item.get("path")))
        for item in (component_manifest or {}).get("components", [])
        if isinstance(item, dict)
    ] if isinstance(component_manifest, dict) else []
    asset_binding_manifest = _read_json(asset_binding_manifest_path)
    bindings = list((asset_binding_manifest or {}).get("bindings", [])) if isinstance(asset_binding_manifest, dict) else []
    image_bindings = [item for item in bindings if item.get("binding_type") == "SpriteFrame"]
    audio_bindings = [item for item in bindings if item.get("binding_type") == "AudioClip"]
    prefab_files = sorted(path.as_posix() for path in prefab_dir.rglob("*.prefab")) if prefab_dir.exists() else []
    prefab_manifest = _read_json(prefab_manifest_path)
    prefab_names = [
        str(item.get("name"))
        for item in (prefab_manifest or {}).get("prefabs", [])
        if isinstance(item, dict)
    ] if isinstance(prefab_manifest, dict) else []
    interaction_contract = _read_json(interaction_contract_path)
    interaction_events = list((interaction_contract or {}).get("events", [])) if isinstance(interaction_contract, dict) else []
    e2e_manifest = _read_json(e2e_manifest_path)
    metadata = dict((e2e_manifest or {}).get("metadata") or {}) if isinstance(e2e_manifest, dict) else {}

    facts = {
        "package_json": package_json_path.exists(),
        "assets_dir": (project / "assets").exists(),
        "scene_main": scene_path.exists(),
        "block_puzzle_script": script_path.exists(),
        "runtime_config": runtime_config_path.exists(),
        "component_manifest": component_manifest_path.exists(),
        "component_scripts_complete": len(component_paths) == len(PRODUCTION_COMPONENT_FILES)
        and all(path.exists() for path in component_paths),
        "asset_binding_manifest": asset_binding_manifest_path.exists(),
        "spriteframe_bindings": bool(image_bindings)
        and all(Path(str(item.get("cocos_resource_path"))).exists() for item in image_bindings),
        "audioclip_bindings": bool(audio_bindings)
        and all(Path(str(item.get("cocos_resource_path"))).exists() for item in audio_bindings),
        "editor_structure_manifest": editor_structure_manifest_path.exists(),
        "commercial_body_manifest": body_manifest_path.exists(),
        "prefab_manifest": prefab_manifest_path.exists(),
        "required_prefabs": set(PRODUCTION_PREFAB_FILES.values()) <= set(prefab_names),
        "gameplay_interaction_contract": interaction_contract_path.exists(),
        "required_interaction_events": set(GAMEPLAY_INTERACTION_EVENTS) <= set(interaction_events),
        "e2e_manifest": e2e_manifest_path.exists(),
        "required_scene_nodes": not missing_nodes,
        "required_panel_nodes": not missing_panels,
        "prefab_files_present": bool(prefab_files),
        "no_hello_template_artifacts": not (project / "assets" / "model" / "helloWorld").exists()
        and not (project / "assets" / "skybox").exists(),
    }
    technical_keys = ["package_json", "assets_dir", "scene_main", "block_puzzle_script", "runtime_config"]
    scaffold_keys = [
        "component_manifest",
        "component_scripts_complete",
        "asset_binding_manifest",
        "spriteframe_bindings",
        "audioclip_bindings",
        "editor_structure_manifest",
        "commercial_body_manifest",
        "prefab_manifest",
        "required_prefabs",
        "gameplay_interaction_contract",
        "required_interaction_events",
        "required_scene_nodes",
        "required_panel_nodes",
        "no_hello_template_artifacts",
    ]
    technical_blockers = [key for key in technical_keys if not facts[key]]
    scaffold_blockers = [key for key in scaffold_keys if not facts[key]]
    player_visible_checks = dict(metadata.get("player_visible_checks") or {})
    missing_player_checks = [key for key in REQUIRED_PLAYER_VISIBLE_CHECKS if key not in player_visible_checks]
    payload = {
        "schema_version": COCOS_PROJECT_INSPECTOR_V2_SCHEMA,
        "created_at": _utc_now(),
        "project_path": project.as_posix(),
        "paths": {
            "scene_path": scene_path.as_posix(),
            "script_path": script_path.as_posix(),
            "runtime_config_path": runtime_config_path.as_posix() if runtime_config_path.exists() else None,
            "component_manifest_path": component_manifest_path.as_posix() if component_manifest_path.exists() else None,
            "asset_binding_manifest_path": asset_binding_manifest_path.as_posix() if asset_binding_manifest_path.exists() else None,
            "body_manifest_path": body_manifest_path.as_posix() if body_manifest_path.exists() else None,
            "prefab_manifest_path": prefab_manifest_path.as_posix() if prefab_manifest_path.exists() else None,
            "interaction_contract_path": interaction_contract_path.as_posix() if interaction_contract_path.exists() else None,
            "e2e_manifest_path": e2e_manifest_path.as_posix() if e2e_manifest_path.exists() else None,
        },
        "scene": {
            "node_count": len(scene_nodes),
            "node_names": scene_nodes,
            "missing_required_nodes": missing_nodes,
            "missing_panel_nodes": missing_panels,
        },
        "prefabs": {"prefab_dir": prefab_dir.as_posix(), "prefab_files": prefab_files, "prefab_names": prefab_names},
        "interactions": {"events": interaction_events},
        "facts": facts,
        "technical_smoke_go": not technical_blockers,
        "production_scaffold_go": not scaffold_blockers,
        "commercial_playable_go": bool(metadata.get("commercial_playable_go")),
        "technical_blockers": technical_blockers,
        "production_scaffold_blockers": scaffold_blockers,
        "missing_player_visible_checks": missing_player_checks,
        "go_no_go": "GO" if not technical_blockers and not scaffold_blockers and not missing_player_checks else "NO-GO",
    }
    if evidence_dir is not None:
        evidence = Path(evidence_dir).resolve()
        evidence.mkdir(parents=True, exist_ok=True)
        output = evidence / "cocos_project_inspector_v2.json"
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["evidence_path"] = output.as_posix()
    return payload


def describe_cocos_delivery_modes(
    project_path: str | Path,
    *,
    build_output_path: str | Path | None = None,
    evidence_dir: str | Path | None = None,
) -> dict[str, Any]:
    project = Path(project_path).resolve()
    runtime_config = _read_json(project / "cocos_runtime_config.json")
    configured_build = project / "build" / "web-mobile"
    build_dir = Path(build_output_path).resolve() if build_output_path is not None else configured_build
    build_required = build_output_path is not None
    index_html = build_dir / "index.html" if build_dir is not None else None
    assets_dir = build_dir / "assets" if build_dir is not None else None
    http_supported = bool(index_html and index_html.exists() and assets_dir and assets_dir.exists())
    payload = {
        "schema_version": COCOS_DELIVERY_MODES_SCHEMA,
        "created_at": _utc_now(),
        "project_path": project.as_posix(),
        "build_output_path": build_dir.as_posix() if build_dir is not None else None,
        "modes": {
            "source_project": {
                "status": "available" if project.exists() else "missing",
                "entry": project.as_posix(),
            },
            "web_mobile_http": {
                "status": "available" if http_supported else "missing_build_output",
                "entry": index_html.as_posix() if index_html and index_html.exists() else None,
                "requires_local_http_server": True,
            },
            "double_click_html": {
                "status": "not_claimed",
                "entry": index_html.as_posix() if index_html and index_html.exists() else None,
                "reason": "Cocos Web Mobile assets are validated through an HTTP server path; file:// is not a commercial delivery claim.",
            },
            "mobile_preview": {
                "status": "not_claimed" if not http_supported else "manual_device_check_required",
                "reason": "Mobile browser behavior needs an explicit device or emulation evidence pass.",
            },
            "native_package": {
                "status": "not_claimed",
                "reason": "Current scope is Web Mobile project/build evidence, not APK/IPA packaging.",
            },
        },
        "go_no_go": "GO" if project.exists() and (not build_required or http_supported) else "NO-GO",
    }
    if evidence_dir is not None:
        evidence = Path(evidence_dir).resolve()
        evidence.mkdir(parents=True, exist_ok=True)
        output = evidence / "cocos_delivery_modes.json"
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["evidence_path"] = output.as_posix()
    return payload
