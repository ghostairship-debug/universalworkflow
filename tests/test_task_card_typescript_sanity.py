from __future__ import annotations

from pathlib import Path

from packages.contributions.pipelines.commercial_game_task_worker_cli import (
    _compress_cocos_uuid,
    _deterministic_typescript_static_sanity_repair,
    _typescript_duplicate_declaration_check,
)


def test_typescript_sanity_rejects_duplicate_exported_class(tmp_path: Path) -> None:
    path = tmp_path / "WorkflowCocosClassRegistry.ts"
    path.write_text(
        "\n".join(
            [
                "import { _decorator, Component } from 'cc';",
                "const { ccclass } = _decorator;",
                "@ccclass('WorkflowCocosClassRegistry')",
                "export class WorkflowCocosClassRegistry extends Component {}",
                "@ccclass('WorkflowCocosClassRegistry')",
                "export class WorkflowCocosClassRegistry extends Component {}",
            ]
        ),
        encoding="utf-8",
    )

    result = _typescript_duplicate_declaration_check([path.as_posix()])

    assert result["go"] is False
    assert result["blockers"] == ["typescript_duplicate_declaration"]
    assert result["findings"][0]["name"] == "WorkflowCocosClassRegistry"


def test_typescript_sanity_accepts_single_class(tmp_path: Path) -> None:
    path = tmp_path / "WorkflowCocosClassRegistry.ts"
    path.write_text(
        "\n".join(
            [
                "import { _decorator, Component } from 'cc';",
                "const { ccclass } = _decorator;",
                "@ccclass('WorkflowCocosClassRegistry')",
                "export class WorkflowCocosClassRegistry extends Component {}",
            ]
        ),
        encoding="utf-8",
    )

    result = _typescript_duplicate_declaration_check([path.as_posix()])

    assert result["go"] is True
    assert result["findings"] == []


def test_typescript_sanity_rejects_missing_relative_named_export(tmp_path: Path) -> None:
    registry = tmp_path / "WorkflowCocosClassRegistry.ts"
    bindings = tmp_path / "WorkflowCocosMachineGateRepairBindings.ts"
    registry.write_text(
        "\n".join(
            [
                "import { WorkflowCocosMachineGateRepairBindings } from './WorkflowCocosMachineGateRepairBindings';",
                "export const WORKFLOW_COCOS_COMPONENT_REGISTRY = { WorkflowCocosMachineGateRepairBindings };",
            ]
        ),
        encoding="utf-8",
    )
    bindings.write_text(
        "\n".join(
            [
                "export const TASK_CARD_ID = 'machine_gate_repair';",
                "export function publishMachineGateRepairPacket() {}",
            ]
        ),
        encoding="utf-8",
    )

    result = _typescript_duplicate_declaration_check([registry.as_posix(), bindings.as_posix()])

    assert result["go"] is False
    assert result["blockers"] == ["typescript_missing_named_export"]
    assert result["findings"][0]["name"] == "WorkflowCocosMachineGateRepairBindings"


def test_static_sanity_rejects_cocos_scene_custom_type_class_name(tmp_path: Path) -> None:
    scene = tmp_path / "block_puzzle_player_visible.scene"
    scene.write_text(
        "\n".join(
            [
                "[",
                '  {"__type__": "cc.Node", "_name": "Canvas"},',
                '  {"__type__": "WorkflowBlockPuzzleSceneRuntime", "_enabled": true}',
                "]",
            ]
        ),
        encoding="utf-8",
    )

    result = _typescript_duplicate_declaration_check([scene.as_posix()])

    assert result["go"] is False
    assert result["blockers"] == ["cocos_serialized_custom_type_uses_class_name"]
    assert result["findings"][0]["name"] == "WorkflowBlockPuzzleSceneRuntime"


def test_cocos_uuid_compression_matches_creator_rf_id() -> None:
    assert _compress_cocos_uuid("2e8a68e7-7d83-4fd6-ae8a-f2b39390a3a1") == "2e8a6jnfYNP1q6K8rOTkKOh"
    assert _compress_cocos_uuid("1fc4dd32-d0cf-4d99-94fa-733ecc949c9e") == "1fc4d0y0M9NmZT6cz7MlJye"


def test_deterministic_static_sanity_repair_rewrites_cocos_class_name_to_rf_id(tmp_path: Path) -> None:
    project = tmp_path / "cocos_project"
    scene = project / "assets" / "scene" / "main.scene"
    script = project / "assets" / "scripts" / "runtime" / "workflow" / "WorkflowBlockPuzzleSceneRuntime.ts"
    scene.parent.mkdir(parents=True)
    script.parent.mkdir(parents=True)
    scene.write_text('{"__type__":"WorkflowBlockPuzzleSceneRuntime"}', encoding="utf-8")
    script.write_text(
        "@ccclass('WorkflowBlockPuzzleSceneRuntime')\nexport class WorkflowBlockPuzzleSceneRuntime {}",
        encoding="utf-8",
    )
    Path(f"{script.as_posix()}.meta").write_text(
        '{"uuid":"2e8a68e7-7d83-4fd6-ae8a-f2b39390a3a1"}',
        encoding="utf-8",
    )
    sanity = _typescript_duplicate_declaration_check([scene.as_posix()])

    repair = _deterministic_typescript_static_sanity_repair(project_dir=project, sanity=sanity)
    repaired = _typescript_duplicate_declaration_check([scene.as_posix()])

    assert repair["go"] is True
    assert repaired["go"] is True
    assert '"__type__":"2e8a6jnfYNP1q6K8rOTkKOh"' in scene.read_text(encoding="utf-8")


def test_static_sanity_rejects_reserved_cc_comp_workflow_component_alias(tmp_path: Path) -> None:
    scene = tmp_path / "block_puzzle_player_visible.scene"
    scene.write_text(
        "\n".join(
            [
                "[",
                '  {"__type__": "cc.Node", "_name": "Canvas"},',
                '  {"__type__": "cc.Comp", "workflowComponentClass": "WorkflowBlockPuzzleBoardBinding"},',
                '  {"__type__": "cc.CompPrefabInfo", "fileId": "safe_prefab_metadata"}',
                "]",
            ]
        ),
        encoding="utf-8",
    )

    result = _typescript_duplicate_declaration_check([scene.as_posix()])

    assert result["go"] is False
    assert result["blockers"] == ["cocos_serialized_custom_type_uses_reserved_cc_comp"]
    assert result["findings"][0]["name"] == "WorkflowBlockPuzzleBoardBinding"
    assert all(item.get("serialized_type") != "cc.CompPrefabInfo" for item in result["findings"])


def test_deterministic_static_sanity_repair_rewrites_reserved_cc_comp_alias_to_rf_id(tmp_path: Path) -> None:
    project = tmp_path / "cocos_project"
    scene = project / "assets" / "scene" / "main.scene"
    script = project / "assets" / "scripts" / "runtime" / "workflow" / "WorkflowBlockPuzzleBoardBinding.ts"
    scene.parent.mkdir(parents=True)
    script.parent.mkdir(parents=True)
    scene.write_text(
        '[{"__type__":"cc.Comp","__scriptAsset":{"__uuid__":"stale"},"workflowComponentClass":"WorkflowBlockPuzzleBoardBinding"}]',
        encoding="utf-8",
    )
    script.write_text(
        "@ccclass('WorkflowBlockPuzzleBoardBinding')\nexport class WorkflowBlockPuzzleBoardBinding {}",
        encoding="utf-8",
    )
    Path(f"{script.as_posix()}.meta").write_text(
        '{"uuid":"1fc4dd32-d0cf-4d99-94fa-733ecc949c9e"}',
        encoding="utf-8",
    )
    sanity = _typescript_duplicate_declaration_check([scene.as_posix()])

    repair = _deterministic_typescript_static_sanity_repair(project_dir=project, sanity=sanity)
    repaired = _typescript_duplicate_declaration_check([scene.as_posix()])
    scene_text = scene.read_text(encoding="utf-8")

    assert repair["go"] is True
    assert repaired["go"] is True
    assert '"__type__": "1fc4d0y0M9NmZT6cz7MlJye"' in scene_text
    assert '"__uuid__": "1fc4dd32-d0cf-4d99-94fa-733ecc949c9e"' in scene_text


def test_deterministic_static_sanity_repair_generates_missing_workflow_component(tmp_path: Path) -> None:
    project = tmp_path / "cocos_project"
    scene = project / "assets" / "prefabs" / "block_candidate_bar.prefab"
    scene.parent.mkdir(parents=True)
    scene.write_text(
        '[{"__type__":"cc.Comp","__scriptAsset":{"__uuid__":"stale"},"workflowComponentClass":"WorkflowCandidateShapeRuntime"}]',
        encoding="utf-8",
    )
    sanity = _typescript_duplicate_declaration_check([scene.as_posix()])

    repair = _deterministic_typescript_static_sanity_repair(project_dir=project, sanity=sanity)
    repaired = _typescript_duplicate_declaration_check([scene.as_posix()])
    script = project / "assets" / "scripts" / "runtime" / "workflow" / "WorkflowCandidateShapeRuntime.ts"

    assert repair["go"] is True
    assert repaired["go"] is True
    assert script.exists()
    assert Path(f"{script.as_posix()}.meta").exists()
    assert '"__type__": "cc.Comp"' not in scene.read_text(encoding="utf-8")
