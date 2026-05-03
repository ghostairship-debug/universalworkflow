from __future__ import annotations

import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app
import apps.operator_cli.game_commands as game_commands
import packages.contributions.games.cocos.e2e as cocos_e2e_module
from packages.contributions.asset_factory.asset_generation import (
    AssetGenerationRequest,
    AssetGenerationResult,
    generate_procedural_sfx,
)
from packages.contributions.games.cocos.commercial_assets import (
    generate_cocos_commercial_asset_manifest,
    generate_cocos_local_stable_asset_manifest,
)
from packages.contributions.games.cocos.ecosystem_bridge import collect_cocos_ecosystem_bridge_evidence
import packages.contributions.games.cocos.ecosystem_bridge as ecosystem_bridge_module
from packages.contributions.games.cocos.e2e import run_cocos_game_e2e
from packages.contributions.games.cocos.graph_bridge import build_cocos_graph_evidence_bridge
from packages.contributions.games.cocos.inspector import describe_cocos_delivery_modes, inspect_cocos_project_v2
from packages.contributions.games.cocos.player_validation import validate_cocos_player_visible_evidence
from packages.contributions.games.cocos.sample_closeout import run_cocos_small_goal_sample_closeout
from infra.scripts.validate_cocos_browser_runtime_hook import validate_cocos_browser_runtime_hook
from infra.scripts.validate_cocos_start_scene import validate_cocos_start_scene


def _fake_asset_generator(request: AssetGenerationRequest) -> AssetGenerationResult:
    output = Path(request.output_dir) / request.filename
    output.parent.mkdir(parents=True, exist_ok=True)
    if request.modality == "vision_review":
        output.write_text('{"review_text":"commercial polish looks coherent"}', encoding="utf-8")
        mime_type = "application/json"
    else:
        output.write_bytes(f"{request.modality}-asset".encode("utf-8"))
        mime_type = request.mime_type or "application/octet-stream"
    return AssetGenerationResult(
        provider=request.provider,
        modality=request.modality,
        status="completed",
        artifact_paths=[output.as_posix()],
        mime_type=mime_type,
    )


def test_discover_cocos_creator_exe_prefers_existing_explicit_path(tmp_path: Path) -> None:
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")

    assert cocos_e2e_module.discover_cocos_creator_exe(creator) == creator.resolve()


def test_discover_cocos_creator_exe_scans_versioned_creator_roots(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("WORKFLOW_COCOS_CREATOR_EXE", raising=False)
    monkeypatch.delenv("COCOS_CREATOR_EXE", raising=False)
    monkeypatch.delenv("COCOS_CREATOR_PATH", raising=False)
    monkeypatch.setattr(cocos_e2e_module, "DEFAULT_CREATOR_EXE", tmp_path / "missing" / "CocosCreator.exe")
    older = tmp_path / "3.8.1" / "CocosCreator.exe"
    newer = tmp_path / "3.8.8" / "CocosCreator.exe"
    older.parent.mkdir(parents=True)
    newer.parent.mkdir(parents=True)
    older.write_text("", encoding="utf-8")
    newer.write_text("", encoding="utf-8")

    assert cocos_e2e_module.discover_cocos_creator_exe(search_roots=[tmp_path]) == newer.resolve()


def test_cocos_safe_rmtree_renames_locked_output_dir(tmp_path: Path, monkeypatch) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "cocos_build_stdout.log").write_text("locked", encoding="utf-8")
    original_rmtree = cocos_e2e_module.shutil.rmtree
    calls: list[str] = []

    def _flaky_rmtree(path: Path) -> None:
        name = Path(path).name
        calls.append(name)
        if name == "output":
            raise PermissionError("simulated Windows log lock")
        original_rmtree(path)

    monkeypatch.setattr(cocos_e2e_module.shutil, "rmtree", _flaky_rmtree)

    cocos_e2e_module._safe_rmtree(output_dir)

    assert not output_dir.exists()
    assert any(name.startswith("output.stale-") for name in calls)


def test_cocos_e2e_generates_real_creator_project_without_build(tmp_path: Path) -> None:
    pdf_path = tmp_path / "design.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% fake unit-test placeholder\n")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    output_dir = tmp_path / "cocos_project"

    payload = run_cocos_game_e2e(
        pdf_path=pdf_path,
        output_dir=output_dir,
        creator_exe=creator,
        require_build=False,
    )

    assert payload["manifest"]["go_no_go"] == "GO"
    assert payload["runtime_config"]["go_no_go"] == "GO"
    assert Path(payload["runtime_config_path"]).exists()
    assert payload["technical_smoke_go"] is True
    assert payload["production_scaffold_go"] is False
    assert (output_dir / "assets" / "scripts" / "BlockPuzzleGame.ts").exists()
    assert (output_dir / "assets" / "scene" / "main.scene").exists()
    assert (output_dir / "design_mapping.json").exists()
    assert not (output_dir / "assets" / "model" / "helloWorld").exists()
    assert (output_dir / "commercial_editor_structure_manifest.json").exists()
    assert (output_dir / "commercial_component_manifest.json").exists()
    assert (output_dir / "commercial_prefab_manifest.json").exists()
    assert (output_dir / "gameplay_interaction_contract.json").exists()
    script = (output_dir / "assets" / "scripts" / "BlockPuzzleGame.ts").read_text(encoding="utf-8")
    assert "__COCOS_BLOCK_PUZZLE_E2E__" in script
    assert "bootBlockPuzzleStandalone()" in script
    assert "campaignFirstSevenLevels" in script
    assert "Math.floor(this.score / 10 + offset)" in script
    assert "fillRoundedPanel" in script
    assert "drawOpenPanels" in script
    assert "1010 方块消除" in script
    assert "经典模式 + 7 关挑战" in script
    assert "商业化功能面板" in script
    assert "皮肤商店" in script
    assert "pause: '暂停'" in script
    assert "广告位：激励复活 + 过关插屏" in script
    assert "Live commercial panels" not in script
    assert "Classic + Campaign 1-7" not in script
    assert "Revive Ad" not in script
    assert "Ad slots: revive reward + interstitial after level clear" not in script
    scene_text = (output_dir / "assets" / "scene" / "main.scene").read_text(encoding="utf-8")
    assert "CommercialCanvas" in scene_text
    assert "BoardRoot" in scene_text
    assert "SkinShopPanel" in scene_text
    scene_data = json.loads(scene_text)
    globals_ref = scene_data[1]["_globals"]["__id__"]
    globals_data = scene_data[globals_ref]
    assert globals_data["__type__"] == "cc.SceneGlobals"
    assert "_skybox" in globals_data


def test_validate_cocos_start_scene_requires_scene_meta_settings_and_nodes(tmp_path: Path) -> None:
    project = tmp_path / "cocos_project"
    (project / "assets" / "scene").mkdir(parents=True)
    (project / "settings" / "v2" / "packages").mkdir(parents=True)
    (project / "assets" / "scene" / "main.scene").write_text(
        json.dumps([{"__type__": "cc.SceneAsset"}, {"__type__": "cc.Scene", "_id": "scene-a"}]),
        encoding="utf-8",
    )
    (project / "assets" / "scene" / "main.scene.meta").write_text(
        json.dumps({"uuid": "scene-a"}),
        encoding="utf-8",
    )
    (project / "settings" / "v2" / "packages" / "scene.json").write_text(
        json.dumps({"__version__": "1.0.0", "current-scene": "scene-b"}),
        encoding="utf-8",
    )

    payload = validate_cocos_start_scene(project)

    assert payload["status"] == "failed"
    assert "scene_settings_uuid_mismatch" in payload["issues"]
    assert "required_scene_nodes_missing" in payload["issues"]
    assert "scene_globals_missing" in payload["issues"]
    assert "scene_globals_reference_missing" in payload["issues"]


def test_validate_cocos_start_scene_accepts_generated_production_scene(tmp_path: Path) -> None:
    project = tmp_path / "cocos_project"
    cocos_e2e_module._write_production_scene(project)

    payload = validate_cocos_start_scene(project)

    assert payload["status"] == "passed"
    assert payload["issues"] == []


def test_validate_cocos_start_scene_rejects_non_cocos_globals_classes(tmp_path: Path) -> None:
    project = tmp_path / "cocos_project"
    cocos_e2e_module._write_production_scene(project)
    scene_path = project / "assets" / "scene" / "main.scene"
    scene_data = json.loads(scene_path.read_text(encoding="utf-8"))
    globals_ref = scene_data[1]["_globals"]["__id__"]
    scene_data[globals_ref]["shadows"] = {"__type__": "ShadowsInfo", "_type": 0}
    scene_data[globals_ref]["_skybox"] = {"__type__": "SkyboxInfo"}
    scene_path.write_text(json.dumps(scene_data), encoding="utf-8")

    payload = validate_cocos_start_scene(project)

    assert payload["status"] == "failed"
    assert "scene_globals_shadows_reference_invalid" in payload["issues"]
    assert "scene_globals_skybox_reference_invalid" in payload["issues"]


def test_validate_cocos_browser_runtime_hook_requires_script_meta_and_scene_component(tmp_path: Path) -> None:
    project = tmp_path / "cocos_project"
    (project / "assets" / "scripts").mkdir(parents=True)
    (project / "assets" / "scene").mkdir(parents=True)
    (project / "assets" / "scene" / "main.scene").write_text(
        json.dumps([{"__type__": "cc.SceneAsset"}, {"__type__": "cc.Scene", "_components": []}]),
        encoding="utf-8",
    )

    payload = validate_cocos_browser_runtime_hook(project)

    assert payload["status"] == "failed"
    assert "block_puzzle_runtime_script_missing" in payload["issues"]
    assert "block_puzzle_runtime_script_meta_missing" in payload["issues"]
    assert "block_puzzle_scene_component_missing" in payload["issues"]


def test_validate_cocos_browser_runtime_hook_accepts_runtime_contract(tmp_path: Path) -> None:
    project = tmp_path / "cocos_project"
    (project / "assets" / "scripts").mkdir(parents=True)
    (project / "assets" / "scene").mkdir(parents=True)
    (project / "assets" / "scripts" / "BlockPuzzleGame.ts").write_text(
        "\n".join(
            [
                "import { _decorator, Component } from 'cc';",
                "const { ccclass } = _decorator;",
                "@ccclass('BlockPuzzleGame')",
                "export class BlockPuzzleGame extends Component {",
                "  start() {",
                "    const canvasId = 'block-puzzle-canvas';",
                "    (globalThis as any).__COCOS_BLOCK_PUZZLE_E2E__ = {",
                "      candidateCenters: [],",
                "      clearTarget: { x: 0, y: 0 },",
                "      buttonCenters: {},",
                "      featureCoverage: {",
                "        audioPlaybackVerified: true,",
                "        bgmStarted: true,",
                "        sfxPlaybackVerified: true,",
                "        volumeToggleUsable: true,",
                "      },",
                "      canvasId,",
                "    };",
                "  }",
                "}",
            ]
        ),
        encoding="utf-8",
    )
    (project / "assets" / "scripts" / "BlockPuzzleGame.ts.meta").write_text(
        json.dumps({"importer": "typescript", "uuid": "block-puzzle-script"}),
        encoding="utf-8",
    )
    (project / "assets" / "scene" / "main.scene").write_text(
        json.dumps(
            [
                {"__type__": "cc.SceneAsset"},
                {"__type__": "cc.Scene", "_components": [{"__id__": 2}]},
                {"__type__": "BlockPuzzleGame", "_enabled": True, "node": {"__id__": 1}},
            ]
        ),
        encoding="utf-8",
    )

    payload = validate_cocos_browser_runtime_hook(project)

    assert payload["status"] == "passed"
    assert payload["issues"] == []


def test_validate_cocos_browser_runtime_hook_rejects_missing_audio_runtime_marker(tmp_path: Path) -> None:
    project = tmp_path / "cocos_project"
    (project / "assets" / "scripts").mkdir(parents=True)
    (project / "assets" / "scene").mkdir(parents=True)
    script = "\n".join(
        [
            "import { _decorator, Component } from 'cc';",
            "const { ccclass } = _decorator;",
            "@ccclass('BlockPuzzleGame')",
            "export class BlockPuzzleGame extends Component {",
            "  start() {",
            "    (globalThis as any).__COCOS_BLOCK_PUZZLE_E2E__ = {",
            "      candidateCenters: [], clearTarget: {}, buttonCenters: {},",
            "      featureCoverage: { audioPlaybackVerified: true, bgmStarted: true, sfxPlaybackVerified: true },",
            "    };",
            "  }",
            "}",
        ]
    )
    (project / "assets" / "scripts" / "BlockPuzzleGame.ts").write_text(script, encoding="utf-8")
    (project / "assets" / "scripts" / "BlockPuzzleGame.ts.meta").write_text(
        json.dumps({"importer": "typescript", "uuid": "block-puzzle-script"}),
        encoding="utf-8",
    )
    (project / "assets" / "scene" / "main.scene").write_text(
        json.dumps(
            [
                {"__type__": "cc.SceneAsset"},
                {"__type__": "cc.Scene", "_components": [{"__id__": 2}]},
                {"__type__": "BlockPuzzleGame", "_enabled": True, "node": {"__id__": 1}},
            ]
        ),
        encoding="utf-8",
    )

    payload = validate_cocos_browser_runtime_hook(project)

    assert payload["status"] == "failed"
    assert "block_puzzle_runtime_markers_missing" in payload["issues"]
    assert "volumeToggleUsable" in payload["missing_script_markers"]


def test_cocos_e2e_accepts_markdown_source_without_pdf_parser(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "design.md"
    source_path.write_text("# 禅境方块\n\n至少 8 个中文目标关卡，商店、皮肤、音频都必须可见。\n", encoding="utf-8")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")

    def _should_not_read_pdf(*_args, **_kwargs):
        raise AssertionError("markdown source must not be sent through PDF parser")

    monkeypatch.setattr(cocos_e2e_module, "_read_pdf_text", _should_not_read_pdf)

    payload = run_cocos_game_e2e(
        pdf_path=source_path,
        output_dir=tmp_path / "cocos_project",
        creator_exe=creator,
        require_build=False,
    )

    mapping = json.loads(Path(payload["project"]["design_mapping_path"]).read_text(encoding="utf-8"))
    assert payload["runtime_config"]["source_kind"] == "text"
    assert payload["runtime_config"]["source_path"] == source_path.resolve().as_posix()
    assert mapping["source_kind"] == "text"
    assert "至少 8 个中文目标关卡" in mapping["pdf_excerpt"]
    assert payload["project"]["source_text_chars"] > 0


def test_cocos_build_accepts_creator_success_exit_code_36(tmp_path: Path, monkeypatch) -> None:
    build_output = tmp_path / "build" / "web-mobile"
    (build_output / "assets").mkdir(parents=True)
    (build_output / "index.html").write_text("<canvas></canvas>", encoding="utf-8")

    def _fake_run(command, *, stdout, stderr, timeout, check):
        stdout.write("build Task (web-mobile) Finished")
        stderr.write("构建参数 debug 校验失败, 将会使用默认值 false")
        return subprocess.CompletedProcess(command, 36)

    monkeypatch.setattr(cocos_e2e_module.subprocess, "run", _fake_run)

    build = cocos_e2e_module.build_cocos_project(
        project_path=tmp_path,
        creator_exe=tmp_path / "CocosCreator.exe",
    )

    assert build["creator_exit_code"] == 36
    assert build["artifact_success"] is True
    assert build["fatal_marker_detected"] is False


def test_cocos_build_copies_commercial_runtime_assets_for_web_playtest(tmp_path: Path, monkeypatch) -> None:
    build_output = tmp_path / "build" / "web-mobile"
    (build_output / "assets").mkdir(parents=True)
    (build_output / "index.html").write_text("<canvas></canvas>", encoding="utf-8")
    source_assets = tmp_path / "assets" / "resources" / "commercial_assets"
    (source_assets / "images").mkdir(parents=True)
    (source_assets / "audio").mkdir(parents=True)
    (source_assets / "images" / "background.png").write_bytes(b"png")
    (source_assets / "audio" / "sfx_clear.mp3").write_bytes(b"mp3")

    def _fake_run(command, *, stdout, stderr, timeout, check):
        stdout.write("build Task (web-mobile) Finished")
        return subprocess.CompletedProcess(command, 36)

    monkeypatch.setattr(cocos_e2e_module.subprocess, "run", _fake_run)

    build = cocos_e2e_module.build_cocos_project(
        project_path=tmp_path,
        creator_exe=tmp_path / "CocosCreator.exe",
    )

    copied_root = build_output / "assets" / "resources" / "commercial_assets"
    assert build["artifact_success"] is True
    assert build["runtime_asset_copy"]["copied"] is True
    assert build["runtime_asset_copy"]["asset_count"] == 2
    assert (copied_root / "images" / "background.png").read_bytes() == b"png"
    assert (copied_root / "audio" / "sfx_clear.mp3").read_bytes() == b"mp3"


def test_cocos_build_installs_model_backed_browser_runtime_bridge(tmp_path: Path, monkeypatch) -> None:
    build_output = tmp_path / "build" / "web-mobile"
    (build_output / "assets").mkdir(parents=True)
    (build_output / "index.html").write_text("<body><canvas id=\"GameCanvas\"></canvas></body>", encoding="utf-8")
    runtime_sources = [
        tmp_path / "assets" / "scripts" / "gameplay" / "CommercialCoreLoopRuntime.ts",
        tmp_path / "assets" / "scripts" / "gameplay" / "CommercialGameplaySemanticBridge.ts",
        tmp_path / "assets" / "scripts" / "AudioFeedbackController.ts",
    ]
    for source in runtime_sources:
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("export const runtimeSource = true;\n", encoding="utf-8")

    def _fake_run(command, *, stdout, stderr, timeout, check):
        stdout.write("build Task (web-mobile) Finished")
        return subprocess.CompletedProcess(command, 36)

    monkeypatch.setattr(cocos_e2e_module.subprocess, "run", _fake_run)

    build = cocos_e2e_module.build_cocos_project(
        project_path=tmp_path,
        creator_exe=tmp_path / "CocosCreator.exe",
    )

    bridge = build["browser_runtime_bridge"]
    assert bridge["installed"] is True
    assert bridge["runtime_source_count"] == 3
    index_html = (build_output / "index.html").read_text(encoding="utf-8")
    bridge_script = (build_output / "workflow-e2e-runtime-bridge.js").read_text(encoding="utf-8")
    evidence = json.loads((tmp_path / "workflow_runtime_evidence" / "browser_runtime_bridge_injection.json").read_text(encoding="utf-8"))
    assert "workflow-e2e-runtime-bridge.js" in index_html
    assert "__COCOS_BLOCK_PUZZLE_E2E__" in bridge_script
    assert "CommercialCoreLoopRuntime.getSnapshot" in bridge_script
    assert "commercialPlayableGo: false" in bridge_script
    assert evidence["runtime_source_policy"] == "model_state_view_only_not_dom_event_substitute"


def test_cocos_build_stops_new_creator_child_processes(tmp_path: Path, monkeypatch) -> None:
    build_output = tmp_path / "build" / "web-mobile"
    (build_output / "assets").mkdir(parents=True)
    (build_output / "index.html").write_text("<canvas></canvas>", encoding="utf-8")
    pid_snapshots = iter([{11}, {11, 22, 33}])
    stopped: list[set[int]] = []

    def _fake_run(command, *, stdout, stderr, timeout, check):
        stdout.write("build Task (web-mobile) Finished")
        return subprocess.CompletedProcess(command, 36)

    monkeypatch.setattr(cocos_e2e_module, "_cocos_creator_pids", lambda: next(pid_snapshots))
    monkeypatch.setattr(cocos_e2e_module, "_stop_cocos_creator_pids", lambda pids: stopped.append(pids))
    monkeypatch.setattr(cocos_e2e_module.subprocess, "run", _fake_run)

    build = cocos_e2e_module.build_cocos_project(
        project_path=tmp_path,
        creator_exe=tmp_path / "CocosCreator.exe",
    )

    assert build["artifact_success"] is True
    assert stopped == [{22, 33}]


def test_cocos_build_rejects_success_code_with_fatal_runtime_marker(tmp_path: Path, monkeypatch) -> None:
    build_output = tmp_path / "build" / "web-mobile"
    (build_output / "assets").mkdir(parents=True)
    (build_output / "index.html").write_text("<canvas></canvas>", encoding="utf-8")

    def _fake_run(command, *, stdout, stderr, timeout, check):
        stdout.write("build Task (web-mobile) Finished")
        stderr.write("Missing class: BlockPuzzleGame")
        return subprocess.CompletedProcess(command, 36)

    monkeypatch.setattr(cocos_e2e_module.subprocess, "run", _fake_run)

    build = cocos_e2e_module.build_cocos_project(
        project_path=tmp_path,
        creator_exe=tmp_path / "CocosCreator.exe",
    )

    assert build["creator_exit_code"] == 36
    assert build["artifact_success"] is False
    assert build["fatal_marker_detected"] is True


def test_cocos_build_timeout_returns_failed_build_evidence(tmp_path: Path, monkeypatch) -> None:
    stopped: list[set[int]] = []

    def _timeout_run(command, *, stdout, stderr, timeout, check):
        stdout.write("build started")
        raise subprocess.TimeoutExpired(command, timeout)

    monkeypatch.setattr(cocos_e2e_module, "_cocos_creator_pids", lambda: {101})
    monkeypatch.setattr(cocos_e2e_module, "_stop_cocos_creator_pids", lambda pids: stopped.append(pids))
    monkeypatch.setattr(cocos_e2e_module.subprocess, "run", _timeout_run)

    build = cocos_e2e_module.build_cocos_project(
        project_path=tmp_path,
        creator_exe=tmp_path / "CocosCreator.exe",
        timeout_seconds=7,
    )

    assert build["creator_exit_code"] == 124
    assert build["timeout"] is True
    assert build["timeout_seconds"] == 7
    assert build["artifact_success"] is False
    assert "timed out after 7s" in build["stderr_tail"]
    assert stopped == [set()]


def test_cocos_ecosystem_bridge_records_missing_editor_contract_without_diagnostic_blocking(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")

    payload = collect_cocos_ecosystem_bridge_evidence(
        project_path=project,
        creator_exe=creator,
        evidence_dir=tmp_path / "ecosystem_evidence",
        require_bridge=False,
    )

    assert payload["strict_required"] is False
    assert payload["ecosystem_integration_go"] is False
    assert payload["blockers"] == []
    assert payload["failure_class"] is None
    assert "assetdb_import_query_evidence" in payload["missing_operations"]
    assert "license_cost_manifest" not in payload["missing_operations"]
    assert payload["checks"]["local_mcp_or_extension_present"] is True
    assert "filesystem_project_generation_only" in payload["bridge_contract"]["forbidden_substitutes"]
    assert Path(payload["evidence_path"]).exists()
    persisted = json.loads(Path(payload["evidence_path"]).read_text(encoding="utf-8"))
    assert persisted["evidence_path"] == payload["evidence_path"]


def test_cocos_ecosystem_bridge_blocks_when_required(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")

    payload = collect_cocos_ecosystem_bridge_evidence(
        project_path=project,
        creator_exe=creator,
        evidence_dir=tmp_path / "ecosystem_evidence",
        require_bridge=True,
        bridge_mode="report_only",
    )

    assert payload["strict_required"] is True
    assert payload["ecosystem_integration_go"] is False
    assert payload["failure_class"] == "cocos_ecosystem_bridge_missing"
    assert "editor_bridge_present" in payload["blockers"]
    assert "assetdb_import_query_evidence" in payload["blockers"]
    assert "scene_create_save_evidence" in payload["blockers"]
    assert "prefab_create_instantiate_evidence" in payload["blockers"]
    assert "license_cost_manifest" not in payload["blockers"]
    assert payload["checks"]["local_mcp_or_extension_present"] is True


def test_cocos_ecosystem_bridge_accepts_trusted_editor_report(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    report = tmp_path / "bridge_report.json"
    report.write_text(
        json.dumps(
            {
                "schema_version": "cocos_editor_bridge_report_v1",
                "tool_kind": "cocos_editor_extension",
                "editor_api_used": True,
                "project_path": project.as_posix(),
                "operations": {
                    "editor_status_version": {"status": "completed", "version": "3.8.8"},
                    "project_open": {"status": "completed"},
                    "assetdb_import_query": {"status": "completed", "asset_count": 1},
                    "scene_create_save": {"status": "completed"},
                    "node_component_binding": {"status": "completed"},
                    "prefab_create_instantiate": {"status": "completed"},
                    "build_api_trigger": {"status": "completed"},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    payload = collect_cocos_ecosystem_bridge_evidence(
        project_path=project,
        creator_exe=creator,
        evidence_dir=tmp_path / "ecosystem_evidence",
        require_bridge=True,
        bridge_report_path=report,
        bridge_mode="report_only",
    )

    assert payload["ecosystem_integration_go"] is True
    assert payload["blockers"] == []
    assert payload["failure_class"] is None
    assert payload["checks"]["assetdb_import_query_evidence"] is True
    assert payload["checks"]["node_component_binding_evidence"] is True
    assert payload["bridge_report_validation"]["tool_kind"] == "cocos_editor_extension"


def test_cocos_ecosystem_bridge_rejects_filesystem_only_report(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    report = tmp_path / "bridge_report.json"
    report.write_text(
        json.dumps(
            {
                "tool_kind": "filesystem_project_generation_only",
                "editor_api_used": False,
                "project_path": project.as_posix(),
                "operations": {
                    "editor_status_version": True,
                    "assetdb_import_query": True,
                    "scene_create_save": True,
                    "node_component_binding": True,
                    "prefab_create_instantiate": True,
                    "build_api_trigger": True,
                },
            }
        ),
        encoding="utf-8",
    )

    payload = collect_cocos_ecosystem_bridge_evidence(
        project_path=project,
        creator_exe=creator,
        evidence_dir=tmp_path / "ecosystem_evidence",
        require_bridge=True,
        bridge_report_path=report,
        bridge_mode="report_only",
    )

    assert payload["ecosystem_integration_go"] is False
    assert payload["failure_class"] == "cocos_ecosystem_bridge_missing"
    assert "untrusted_cocos_bridge_tool_kind" in payload["blockers"]
    assert "cocos_editor_api_not_used" in payload["blockers"]
    assert payload["checks"]["assetdb_import_query_evidence"] is False


def test_cocos_ecosystem_bridge_runner_blocks_existing_process_without_launch(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    project.mkdir()
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        ecosystem_bridge_module,
        "_cocos_creator_processes",
        lambda: [{"pid": 1234, "command_line": "CocosCreator.exe --project locked"}],
    )

    def _should_not_launch(*_args, **_kwargs):
        raise AssertionError("runner must not launch Cocos when user-owned process exists")

    monkeypatch.setattr(ecosystem_bridge_module.subprocess, "Popen", _should_not_launch)

    payload = collect_cocos_ecosystem_bridge_evidence(
        project_path=project,
        creator_exe=creator,
        evidence_dir=tmp_path / "ecosystem_evidence",
        require_bridge=True,
        bridge_mode="auto",
    )

    assert payload["ecosystem_integration_go"] is False
    assert payload["operator_action_required"] is True
    assert payload["failure_class"] == "cocos_editor_operator_action_required"
    assert "existing_cocos_creator_process_requires_operator_action" in payload["blockers"]
    assert payload["bridge_runner_evidence"]["status"] == "AWAITING_OPERATOR_ACTION"
    assert Path(payload["bridge_runner_evidence"]["runner_evidence_path"]).exists()


def test_cocos_ecosystem_bridge_runner_timeout_preserves_evidence(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    project.mkdir()
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")

    class _NeverReportingProcess:
        pid = 4321
        returncode = None
        terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

    monkeypatch.setattr(ecosystem_bridge_module, "_cocos_creator_processes", lambda: [])
    monkeypatch.setattr(
        ecosystem_bridge_module,
        "_terminate_runner_process_tree",
        lambda _pid: {"terminated_child_pids": [9876], "exit_code": 0},
    )
    monkeypatch.setattr(ecosystem_bridge_module.subprocess, "Popen", lambda *_args, **_kwargs: _NeverReportingProcess())

    payload = ecosystem_bridge_module.run_cocos_editor_bridge(
        project_path=project,
        creator_exe=creator,
        evidence_dir=tmp_path / "ecosystem_evidence",
        timeout_seconds=0,
    )

    assert payload["status"] == "AWAITING_OPERATOR_ACTION"
    assert payload["failure_class"] == "cocos_editor_bridge_report_timeout"
    assert "cocos_editor_bridge_report_timeout" in payload["blockers"]
    assert "stdout_preview" in payload
    assert "stderr_preview" in payload
    assert payload["runner_started_process_tree_termination"]["terminated_child_pids"] == [9876]
    assert "recoverable_suggestion" in payload
    assert Path(payload["runner_evidence_path"]).exists()


def test_cocos_ecosystem_bridge_runner_waits_for_complete_report(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    project.mkdir()
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    partial_report = project / "temp" / "workflow_cocos_bridge" / "cocos_editor_bridge_report.json"
    partial_report.parent.mkdir(parents=True, exist_ok=True)
    partial_report.write_text(
        json.dumps(
            {
                "schema_version": "cocos_editor_bridge_report_v1",
                "tool_kind": "cocos_editor_extension",
                "editor_api_used": True,
                "project_path": project.as_posix(),
                "operations": {
                    "editor_status_version": {"status": "completed"},
                    "project_open": {"status": "completed"},
                    "build_api_trigger": {"status": "completed"},
                },
            }
        ),
        encoding="utf-8",
    )

    class _PartialReportProcess:
        pid = 7654
        returncode = None

        def poll(self):
            return None

        def terminate(self):
            return None

    monkeypatch.setattr(ecosystem_bridge_module, "_cocos_creator_processes", lambda: [])
    monkeypatch.setattr(ecosystem_bridge_module, "_terminate_runner_process_tree", lambda _pid: {"terminated_child_pids": []})
    monkeypatch.setattr(ecosystem_bridge_module.subprocess, "Popen", lambda *_args, **_kwargs: _PartialReportProcess())

    payload = ecosystem_bridge_module.run_cocos_editor_bridge(
        project_path=project,
        creator_exe=creator,
        evidence_dir=tmp_path / "ecosystem_evidence",
        timeout_seconds=0,
    )

    assert payload["status"] == "AWAITING_OPERATOR_ACTION"
    assert payload["failure_class"] == "cocos_editor_bridge_report_incomplete_timeout"
    assert "cocos_editor_bridge_report_incomplete_timeout" in payload["blockers"]
    assert payload["bridge_report_operation_names"] == [
        "build_api_trigger",
        "editor_status_version",
        "project_open",
    ]


def test_cocos_ecosystem_bridge_auto_accepts_report_created_by_runner(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")

    def _fake_runner(**kwargs):
        report_path = project / "temp" / "workflow_cocos_bridge" / "cocos_editor_bridge_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    "schema_version": "cocos_editor_bridge_report_v1",
                    "tool_kind": "cocos_editor_extension",
                    "editor_api_used": True,
                    "project_path": project.as_posix(),
                    "operations": {
                        "editor_status_version": {"status": "completed", "version": "3.8.8"},
                        "project_open": {"status": "completed"},
                        "assetdb_import_query": {"status": "completed", "asset_count": 1},
                        "scene_create_save": {"status": "completed"},
                        "node_component_binding": {"status": "completed"},
                        "prefab_create_instantiate": {"status": "completed"},
                        "build_api_trigger": {"status": "completed"},
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return {
            "schema_version": "cocos_editor_bridge_runner_evidence_v1",
            "status": "completed",
            "blockers": [],
            "failure_class": None,
            "bridge_report_path": report_path.as_posix(),
        }

    payload = collect_cocos_ecosystem_bridge_evidence(
        project_path=project,
        creator_exe=creator,
        evidence_dir=tmp_path / "ecosystem_evidence",
        require_bridge=True,
        bridge_mode="auto",
        bridge_runner=_fake_runner,
    )

    assert payload["ecosystem_integration_go"] is True
    assert payload["failure_class"] is None
    assert payload["bridge_runner_evidence"]["status"] == "completed"


def test_cli_game_cocos_e2e_generates_manifest_without_build(tmp_path: Path) -> None:
    pdf_path = tmp_path / "design.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% fake unit-test placeholder\n")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    output_dir = tmp_path / "cli_cocos_project"

    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "cocos-e2e",
            "--pdf-path",
            str(pdf_path),
            "--output-dir",
            str(output_dir),
            "--creator-exe",
            str(creator),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["manifest"]["project_path"] == output_dir.as_posix()
    assert Path(payload["manifest_path"]).exists()
    assert Path(payload["runtime_config_path"]).exists()


def test_cli_game_cocos_config_reports_command_and_paths(tmp_path: Path) -> None:
    pdf_path = tmp_path / "design.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% fake unit-test placeholder\n")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    output_dir = tmp_path / "config_project"

    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "cocos-config",
            "--pdf-path",
            str(pdf_path),
            "--output-dir",
            str(output_dir),
            "--creator-exe",
            str(creator),
            "--require-build",
            "--require-commercial",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "m105_cocos_runtime_config_v1"
    assert payload["build_command"] == [
        creator.resolve().as_posix(),
        "--project",
        output_dir.resolve().as_posix(),
        "--build",
        "platform=web-mobile;debug=false",
    ]
    assert payload["run_modes"]["browser_playtest_http"] == "required"
    assert payload["run_modes"]["double_click_html"] == "not_claimed"


def test_cocos_project_inspector_v2_reports_project_facts(tmp_path: Path) -> None:
    pdf_path = tmp_path / "design.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% fake unit-test placeholder\n")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    output_dir = tmp_path / "inspect_project"
    run_cocos_game_e2e(
        pdf_path=pdf_path,
        output_dir=output_dir,
        creator_exe=creator,
        require_build=False,
    )

    payload = inspect_cocos_project_v2(output_dir, evidence_dir=tmp_path / "inspection")

    assert payload["schema_version"] == "m105_cocos_project_inspector_v2"
    assert payload["technical_smoke_go"] is True
    assert payload["facts"]["scene_main"] is True
    assert payload["facts"]["runtime_config"] is True
    assert payload["facts"]["no_hello_template_artifacts"] is True
    assert payload["facts"]["prefab_manifest"] is True
    assert payload["facts"]["required_prefabs"] is True
    assert payload["facts"]["gameplay_interaction_contract"] is True
    assert payload["facts"]["required_interaction_events"] is True
    assert Path(payload["evidence_path"]).exists()


def test_cocos_project_inspector_v2_requires_passing_player_visible_checks(tmp_path: Path) -> None:
    pdf_path = tmp_path / "design.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% fake unit-test placeholder\n")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    output_dir = tmp_path / "inspect_player_project"
    local_assets = generate_cocos_local_stable_asset_manifest(output_dir=tmp_path / "assets")
    run_cocos_game_e2e(
        pdf_path=pdf_path,
        output_dir=output_dir,
        creator_exe=creator,
        require_build=False,
        require_commercial=True,
        commercial_assets_payload=local_assets,
    )

    payload = inspect_cocos_project_v2(output_dir, evidence_dir=tmp_path / "inspection_player")

    assert payload["technical_smoke_go"] is True
    assert payload["production_scaffold_go"] is True
    assert payload["commercial_playable_go"] is False
    assert payload["missing_player_visible_checks"] == []
    assert payload["failing_player_visible_checks"]
    assert payload["player_visible_gate_passed"] is False
    assert payload["go_no_go"] == "NO-GO"


def test_cli_game_cocos_inspect_writes_evidence(tmp_path: Path) -> None:
    pdf_path = tmp_path / "design.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% fake unit-test placeholder\n")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    output_dir = tmp_path / "cli_inspect_project"
    run_cocos_game_e2e(
        pdf_path=pdf_path,
        output_dir=output_dir,
        creator_exe=creator,
        require_build=False,
    )

    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "cocos-inspect",
            "--project-path",
            str(output_dir),
            "--evidence-dir",
            str(tmp_path / "cli_inspection"),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["technical_smoke_go"] is True
    assert Path(payload["evidence_path"]).exists()


def test_cocos_delivery_modes_do_not_claim_double_click_html(tmp_path: Path) -> None:
    project = tmp_path / "delivery_project"
    build = project / "build" / "web-mobile"
    (build / "assets").mkdir(parents=True)
    (build / "index.html").write_text("<html></html>", encoding="utf-8")

    payload = describe_cocos_delivery_modes(project, evidence_dir=tmp_path / "delivery_evidence")

    assert payload["schema_version"] == "m105_cocos_delivery_modes_v1"
    assert payload["modes"]["web_mobile_http"]["status"] == "available"
    assert payload["modes"]["double_click_html"]["status"] == "not_claimed"
    assert payload["modes"]["native_package"]["status"] == "not_claimed"
    assert Path(payload["evidence_path"]).exists()


def test_cli_game_cocos_delivery_reports_modes(tmp_path: Path) -> None:
    project = tmp_path / "cli_delivery_project"
    build = project / "build" / "web-mobile"
    (build / "assets").mkdir(parents=True)
    (build / "index.html").write_text("<html></html>", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "cocos-delivery",
            "--project-path",
            str(project),
            "--evidence-dir",
            str(tmp_path / "cli_delivery_evidence"),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["modes"]["web_mobile_http"]["status"] == "available"
    assert payload["modes"]["mobile_preview"]["status"] == "manual_device_check_required"


def test_cocos_graph_evidence_bridge_links_graph_and_project_facts(tmp_path: Path) -> None:
    pdf_path = tmp_path / "design.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% fake unit-test placeholder\n")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    output_dir = tmp_path / "bridge_project"
    run_cocos_game_e2e(
        pdf_path=pdf_path,
        output_dir=output_dir,
        creator_exe=creator,
        require_build=False,
    )

    payload = build_cocos_graph_evidence_bridge(
        workspace_root=tmp_path,
        project_path=output_dir,
        evidence_dir=tmp_path / "bridge_evidence",
    )

    assert payload["schema_version"] == "m105_cocos_graph_evidence_bridge_v1"
    assert payload["status"] == "completed"
    assert payload["graph"]["persistent_checkpoint"]["status"] == "completed"
    assert Path(payload["graph"]["evidence_path"]).exists()
    assert Path(payload["inspection"]["evidence_path"]).exists()
    assert Path(payload["delivery"]["evidence_path"]).exists()
    assert Path(payload["evidence_path"]).exists()


def test_cli_game_cocos_graph_evidence_writes_bridge(tmp_path: Path) -> None:
    pdf_path = tmp_path / "design.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% fake unit-test placeholder\n")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    output_dir = tmp_path / "cli_bridge_project"
    run_cocos_game_e2e(
        pdf_path=pdf_path,
        output_dir=output_dir,
        creator_exe=creator,
        require_build=False,
    )

    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "cocos-graph-evidence",
            "--project-path",
            str(output_dir),
            "--evidence-dir",
            str(tmp_path / "cli_bridge_evidence"),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "completed"
    assert payload["graph"]["attempt_id"]


def test_cocos_player_visible_validation_can_pass_with_complete_playtest(tmp_path: Path) -> None:
    shot = tmp_path / "shot.png"
    shot.write_bytes(b"png")
    playtest = {
        "passed": True,
        "commercial_passed": True,
        "screenshots": [shot.as_posix()],
        "canvas_hashes": ["abc"],
        "score": 10,
        "events": ["refresh_used", "pause_opened"],
        "feature_coverage": {
            "mobilePortraitUi": True,
            "dragPlacement": True,
            "campaignFirstSevenLevels": True,
            "levelSwitchingUi": True,
            "propUse": True,
            "generatedAudioAssets": True,
        },
        "console_errors": [],
        "page_errors": [],
    }

    payload = validate_cocos_player_visible_evidence(
        playtest=playtest,
        inspection={"scene": {"node_names": ["CommercialCanvas", "HUDRoot"]}},
        technical_smoke=True,
        production_scaffold=True,
        evidence_dir=tmp_path / "player_validation",
    )

    assert payload["go_no_go"] == "GO"
    assert payload["commercial_playable_go"] is True
    assert all(item["status"] == "pass" for item in payload["player_visible_checks"].values())
    assert Path(payload["evidence_path"]).exists()


def test_cli_game_cocos_player_validate_rejects_missing_playtest(tmp_path: Path) -> None:
    pdf_path = tmp_path / "design.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% fake unit-test placeholder\n")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    output_dir = tmp_path / "player_validate_project"
    run_cocos_game_e2e(
        pdf_path=pdf_path,
        output_dir=output_dir,
        creator_exe=creator,
        require_build=False,
        use_local_stable_assets=True,
        require_commercial=True,
    )

    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "cocos-player-validate",
            "--project-path",
            str(output_dir),
            "--evidence-dir",
            str(tmp_path / "player_validation_evidence"),
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["commercial_playable_go"] is False
    assert Path(payload["evidence_path"]).exists()


def test_cocos_sample_closeout_reports_honest_limits(tmp_path: Path) -> None:
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")

    payload = run_cocos_small_goal_sample_closeout(
        workspace_root=tmp_path,
        output_dir=tmp_path / "sample_project",
        creator_exe=creator,
        evidence_dir=tmp_path / "sample_evidence",
        require_build=False,
    )

    assert payload["schema_version"] == "m108_cocos_sample_closeout_v1"
    assert payload["status"] == "completed"
    assert payload["claims"]["technical_smoke_go"] is True
    assert payload["claims"]["production_scaffold_go"] is True
    assert payload["claims"]["commercial_playable_go"] is False
    assert payload["budget_review"]["auto_continue_to_m109"] is False
    assert payload["honest_limits"]
    assert Path(payload["evidence_path"]).exists()


def test_cli_game_cocos_sample_closeout_writes_report(tmp_path: Path) -> None:
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "cocos-sample-closeout",
            "--output-dir",
            str(tmp_path / "cli_sample_project"),
            "--evidence-dir",
            str(tmp_path / "cli_sample_evidence"),
            "--creator-exe",
            str(creator),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "m108_cocos_sample_closeout_v1"
    assert payload["budget_review"]["requires_review_before_more_cocos_milestones"] is True


def test_cocos_e2e_commercial_gate_rejects_technical_demo(tmp_path: Path) -> None:
    pdf_path = tmp_path / "design.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% fake unit-test placeholder\n")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    output_dir = tmp_path / "commercial_gate_project"

    payload = run_cocos_game_e2e(
        pdf_path=pdf_path,
        output_dir=output_dir,
        creator_exe=creator,
        require_build=False,
        require_commercial=True,
    )

    assert payload["manifest"]["go_no_go"] == "NO-GO"
    assert payload["commercial_go_no_go"] == "NO-GO"
    assert "generated_art_assets" in payload["commercial_blockers"]
    assert "commercial_missing_generated_audio_assets" in payload["manifest"]["blockers"]


def test_cli_game_cocos_e2e_commercial_gate_returns_nonzero(tmp_path: Path) -> None:
    pdf_path = tmp_path / "design.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% fake unit-test placeholder\n")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")
    output_dir = tmp_path / "cli_commercial_project"

    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "cocos-e2e",
            "--pdf-path",
            str(pdf_path),
            "--output-dir",
            str(output_dir),
            "--creator-exe",
            str(creator),
            "--require-commercial",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["commercial_go_no_go"] == "NO-GO"


def test_cocos_commercial_asset_manifest_can_batch_generated_assets(tmp_path: Path) -> None:
    manifest = generate_cocos_commercial_asset_manifest(
        output_dir=tmp_path / "commercial_assets",
        include_vertex_review=True,
        image_generator=_fake_asset_generator,
        speech_generator=_fake_asset_generator,
        music_generator=_fake_asset_generator,
        tts_generator=_fake_asset_generator,
        visual_review_generator=_fake_asset_generator,
    )

    assert manifest["go_no_go"] == "GO"
    assert manifest["feature_coverage"]["generated_art_assets"] is True
    assert manifest["feature_coverage"]["generated_audio_assets"] is True
    assert manifest["feature_coverage"]["skin_switching_visual_assets"] is True
    assert manifest["feature_coverage"]["particle_effects"] is True
    assert manifest["asset_factory_manifest"]["schema_version"] == "m81_asset_factory_manifest_v1"
    assert manifest["asset_factory_qa"]["schema_version"] == "m81_asset_factory_qa_v1"
    assert any(item["asset_name"].endswith("_visual_review") for item in manifest["results"])
    assert Path(manifest["manifest_path"]).exists()


def test_cocos_commercial_asset_manifest_routes_sfx_to_dedicated_generator(tmp_path: Path) -> None:
    sfx_requests: list[AssetGenerationRequest] = []

    def _tracked_sfx_generator(request: AssetGenerationRequest) -> AssetGenerationResult:
        sfx_requests.append(request)
        return generate_procedural_sfx(request)

    def _unexpected_speech_generator(request: AssetGenerationRequest) -> AssetGenerationResult:
        return AssetGenerationResult(
            provider=request.provider,
            modality=request.modality,
            status="blocked",
            failure_class="speech_generator_should_not_run",
        )

    manifest = generate_cocos_commercial_asset_manifest(
        output_dir=tmp_path / "commercial_assets",
        include_vertex_review=True,
        image_generator=_fake_asset_generator,
        sfx_generator=_tracked_sfx_generator,
        speech_generator=_unexpected_speech_generator,
        music_generator=_fake_asset_generator,
        tts_generator=_fake_asset_generator,
        visual_review_generator=_fake_asset_generator,
    )

    assert manifest["go_no_go"] == "GO"
    assert manifest["asset_factory_qa"]["sfx_review_count"] == 2
    assert manifest["asset_factory_qa"]["sfx_blockers"] == []
    assert {request.provider for request in sfx_requests} == {"procedural_sfx_local"}
    assert {request.modality for request in sfx_requests} == {"sfx"}
    assert {request.filename for request in sfx_requests} == {"sfx_place.wav", "sfx_clear.wav"}

    prompt_manifest = json.loads(Path(manifest["asset_factory_manifest"]["prompt_manifest_path"]).read_text(encoding="utf-8"))
    prompt_assets = {item["name"]: item for item in prompt_manifest["assets"]}
    assert prompt_assets["sfx_place"] == {"name": "sfx_place", "modality": "sfx", "provider": "procedural_sfx_local", "filename": "sfx_place.wav", "mime_type": "audio/wav", "required": True, "prompt": "short polished mobile puzzle block placement sound"}
    assert prompt_assets["sfx_clear"] == {"name": "sfx_clear", "modality": "sfx", "provider": "procedural_sfx_local", "filename": "sfx_clear.wav", "mime_type": "audio/wav", "required": True, "prompt": "short bright line clear reward sound for casual mobile puzzle game"}
    assert prompt_assets["voice_reward"] == {"name": "voice_reward", "modality": "voice", "provider": "gcp_tts_api", "filename": "voice_reward.mp3", "mime_type": "audio/mpeg", "required": True, "prompt": "Great clear. Keep going."}

    result_assets = {item["asset_name"]: item for item in manifest["results"] if item["asset_name"] in {"sfx_place", "sfx_clear", "voice_reward"}}
    assert result_assets["sfx_place"]["provider"] == "procedural_sfx_local"
    assert result_assets["sfx_place"]["modality"] == "sfx"
    assert result_assets["sfx_place"]["mime_type"] == "audio/wav"
    assert result_assets["sfx_clear"]["provider"] == "procedural_sfx_local"
    assert result_assets["sfx_clear"]["modality"] == "sfx"
    assert result_assets["sfx_clear"]["mime_type"] == "audio/wav"
    assert result_assets["voice_reward"]["provider"] == "gcp_tts_api"
    assert result_assets["voice_reward"]["modality"] == "voice"
    assert result_assets["voice_reward"]["mime_type"] == "audio/mpeg"


def test_cocos_commercial_asset_manifest_blocks_missing_bgm(tmp_path: Path) -> None:
    def _blocked_music(request: AssetGenerationRequest) -> AssetGenerationResult:
        return AssetGenerationResult(
            provider=request.provider,
            modality=request.modality,
            status="blocked",
            failure_class="TimeoutError",
            metadata={"error": "simulated timeout"},
        )

    manifest = generate_cocos_commercial_asset_manifest(
        output_dir=tmp_path / "commercial_assets",
        include_vertex_review=False,
        image_generator=_fake_asset_generator,
        speech_generator=_fake_asset_generator,
        music_generator=_blocked_music,
        tts_generator=_fake_asset_generator,
    )

    assert manifest["go_no_go"] == "NO-GO"
    assert manifest["feature_coverage"]["generated_audio_assets"] is False
    assert "required_asset_bgm_loop_not_completed" not in manifest["blockers"]
    assert "required_asset_bgm_loop_TimeoutError" in manifest["blockers"]


def test_cocos_local_stable_assets_can_feed_commercial_scaffold(tmp_path: Path) -> None:
    pdf_path = tmp_path / "design.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% fake unit-test placeholder\n")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")

    manifest = generate_cocos_local_stable_asset_manifest(output_dir=tmp_path / "local_assets")
    payload = run_cocos_game_e2e(
        pdf_path=pdf_path,
        output_dir=tmp_path / "local_asset_project",
        creator_exe=creator,
        require_build=False,
        require_commercial=True,
        commercial_assets_payload=manifest,
    )

    assert manifest["go_no_go"] == "GO"
    assert {item["provider"] for item in manifest["results"]} == {"local_stable_asset_pack"}
    assert {item["asset_name"]: item["modality"] for item in manifest["results"]} == {
        "background": "image",
        "block_skin_neon": "image",
        "particle_clear": "image",
        "sfx_place": "sfx",
        "sfx_clear": "sfx",
        "bgm_loop": "music",
        "voice_reward": "voice",
    }
    assert payload["commercial_go_no_go"] == "GO"
    assert payload["commercial_feature_coverage"]["generated_audio_assets"] is True
    assert payload["commercial_playable_go"] is False
    assert payload["manifest"]["go_no_go"] == "NO-GO"
    assert payload["commercial_body"]["feature_coverage"]["audio_runtime_hooks"] is True
    bindings = json.loads(Path(payload["commercial_body"]["asset_binding_manifest_path"]).read_text(encoding="utf-8"))
    binding_map = {item["asset_name"]: item for item in bindings["bindings"]}
    assert binding_map["sfx_place"]["modality"] == "sfx"
    assert binding_map["sfx_clear"]["modality"] == "sfx"
    assert binding_map["bgm_loop"]["modality"] == "music"
    assert binding_map["voice_reward"]["modality"] == "voice"
    assert all(
        binding_map[name]["binding_type"] == "AudioClip"
        for name in ["sfx_place", "sfx_clear", "bgm_loop", "voice_reward"]
    )
    script = (Path(payload["project"]["project_path"]) / "assets" / "scripts" / "BlockPuzzleGame.ts").read_text(encoding="utf-8")
    assert 'new Set<string>(["audio", "music", "sfx", "voice"])' in script
    assert "this.playSound('voice_reward');" in script


def test_cli_game_cocos_local_assets_writes_manifest(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "cocos-local-assets",
            "--output-dir",
            str(tmp_path / "cli_local_assets"),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "m106_cocos_local_stable_assets_v1"
    assert payload["go_no_go"] == "GO"


def test_cocos_e2e_generated_assets_clear_asset_specific_blockers(tmp_path: Path, monkeypatch) -> None:
    pdf_path = tmp_path / "design.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% fake unit-test placeholder\n")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")

    def _fake_manifest(*, output_dir, **_kwargs):
        output_root = Path(output_dir)
        image_path = output_root / "commercial_assets" / "images" / "background.png"
        sfx_path = output_root / "commercial_assets" / "audio" / "sfx_place.mp3"
        voice_path = output_root / "commercial_assets" / "audio" / "voice_reward.mp3"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        sfx_path.parent.mkdir(parents=True, exist_ok=True)
        voice_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(b"image")
        sfx_path.write_bytes(b"audio")
        voice_path.write_bytes(b"voice")
        manifest_path = output_root / "commercial_asset_manifest.json"
        manifest_path.write_text("{}", encoding="utf-8")
        return {
            "manifest_path": manifest_path.as_posix(),
            "go_no_go": "GO",
            "feature_coverage": {
                "generated_art_assets": True,
                "generated_audio_assets": True,
                "skin_switching_visual_assets": True,
                "particle_effects": True,
                "commercial_polish_pass": True,
            },
            "results": [
                {
                    "asset_name": "background",
                    "provider": "mmx_generation_api",
                    "modality": "image",
                    "status": "completed",
                    "artifact_paths": [image_path.as_posix()],
                    "mime_type": "image/png",
                },
                {
                    "asset_name": "sfx_place",
                    "provider": "mmx_generation_api",
                    "modality": "sfx",
                    "status": "completed",
                    "artifact_paths": [sfx_path.as_posix()],
                    "mime_type": "audio/mpeg",
                },
                {
                    "asset_name": "voice_reward",
                    "provider": "gcp_tts_api",
                    "modality": "voice",
                    "status": "completed",
                    "artifact_paths": [voice_path.as_posix()],
                    "mime_type": "audio/mpeg",
                },
            ],
        }

    monkeypatch.setattr(cocos_e2e_module, "generate_cocos_commercial_asset_manifest", _fake_manifest)

    payload = run_cocos_game_e2e(
        pdf_path=pdf_path,
        output_dir=tmp_path / "generated_asset_project",
        creator_exe=creator,
        require_build=False,
        require_commercial=True,
        generate_commercial_assets=True,
    )

    assert payload["commercial_feature_coverage"]["generated_art_assets"] is True
    assert payload["commercial_feature_coverage"]["generated_audio_assets"] is True
    assert payload["commercial_go_no_go"] == "GO"
    assert payload["commercial_playable_go"] is False
    assert payload["manifest"]["go_no_go"] == "NO-GO"
    assert "commercial_playable_no_go" in payload["manifest"]["blockers"]
    assert payload["commercial_feature_coverage"]["native_cocos_ui_nodes"] is True
    assert payload["commercial_feature_coverage"]["animation_timeline"] is True
    assert payload["commercial_feature_coverage"]["level_switching_ui"] is True
    assert payload["commercial_feature_coverage"]["editor_visible_scene_hierarchy"] is True
    assert payload["commercial_feature_coverage"]["production_component_scripts"] is True
    assert payload["commercial_feature_coverage"]["spriteframe_asset_bindings"] is True
    assert payload["commercial_feature_coverage"]["audioclip_asset_bindings"] is True
    assert payload["commercial_feature_coverage"]["no_hello_3d_template"] is True
    assert payload["commercial_project_inspection"]["go_no_go"] == "GO"
    assert payload["commercial_body"]["feature_coverage"]["audio_runtime_hooks"] is True
    bindings = json.loads(Path(payload["commercial_body"]["asset_binding_manifest_path"]).read_text(encoding="utf-8"))
    binding_map = {item["asset_name"]: item for item in bindings["bindings"]}
    assert binding_map["sfx_place"]["modality"] == "sfx"
    assert binding_map["sfx_place"]["binding_type"] == "AudioClip"
    assert binding_map["voice_reward"]["modality"] == "voice"
    assert binding_map["voice_reward"]["binding_type"] == "AudioClip"
    assert "commercial_missing_generated_art_assets" not in payload["manifest"]["blockers"]
    script = (Path(payload["project"]["project_path"]) / "assets" / "scripts" / "BlockPuzzleGame.ts").read_text(
        encoding="utf-8"
    )
    assert "CommercialNativeUIRoot" in script
    assert "animation_timeline_started" in script
    assert "level_switching_ui_opened" in script
    assert "cocos_asset_bindings_loaded" in script
    assert Path(payload["commercial_body"]["manifest_path"]).exists()
    assert Path(payload["commercial_body"]["asset_binding_manifest_path"]).exists()
    assert Path(payload["commercial_body"]["editor_structure_manifest_path"]).exists()
    assert Path(payload["commercial_body"]["component_manifest_path"]).exists()


def test_cli_game_cocos_assets_uses_commercial_manifest(tmp_path: Path, monkeypatch) -> None:
    def _fake_manifest(*, output_dir, **_kwargs):
        manifest_path = Path(output_dir) / "commercial_asset_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text("{}", encoding="utf-8")
        return {"go_no_go": "GO", "manifest_path": manifest_path.as_posix(), "feature_coverage": {}}

    monkeypatch.setattr(game_commands, "generate_cocos_commercial_asset_manifest", _fake_manifest)

    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "game",
            "cocos-assets",
            "--output-dir",
            str(tmp_path / "assets"),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["go_no_go"] == "GO"
