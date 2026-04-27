from __future__ import annotations

import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app
import apps.operator_cli.game_commands as game_commands
import packages.contributions.games.cocos.e2e as cocos_e2e_module
from packages.contributions.asset_factory.asset_generation import AssetGenerationRequest, AssetGenerationResult
from packages.contributions.games.cocos.commercial_assets import generate_cocos_commercial_asset_manifest
from packages.contributions.games.cocos.e2e import run_cocos_game_e2e


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
    assert (output_dir / "assets" / "scripts" / "BlockPuzzleGame.ts").exists()
    assert (output_dir / "assets" / "scene" / "main.scene").exists()
    assert (output_dir / "design_mapping.json").exists()
    assert not (output_dir / "assets" / "model" / "helloWorld").exists()
    assert (output_dir / "commercial_editor_structure_manifest.json").exists()
    assert (output_dir / "commercial_component_manifest.json").exists()
    script = (output_dir / "assets" / "scripts" / "BlockPuzzleGame.ts").read_text(encoding="utf-8")
    assert "__COCOS_BLOCK_PUZZLE_E2E__" in script
    assert "bootBlockPuzzleStandalone()" in script
    assert "campaignFirstSevenLevels" in script
    assert "Math.floor(this.score / 10 + offset)" in script
    assert "fillRoundedPanel" in script
    assert "drawOpenPanels" in script
    assert "Live commercial panels" in script
    scene_text = (output_dir / "assets" / "scene" / "main.scene").read_text(encoding="utf-8")
    assert "CommercialCanvas" in scene_text
    assert "BoardRoot" in scene_text
    assert "SkinShopPanel" in scene_text
    scene_data = json.loads(scene_text)
    globals_ref = scene_data[1]["_globals"]["__id__"]
    globals_data = scene_data[globals_ref]
    assert globals_data["__type__"] == "cc.SceneGlobals"
    assert "_skybox" in globals_data


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
    assert "required_asset_bgm_loop_not_completed" in manifest["blockers"]
    assert "required_asset_bgm_loop_TimeoutError" in manifest["blockers"]


def test_cocos_e2e_generated_assets_clear_asset_specific_blockers(tmp_path: Path, monkeypatch) -> None:
    pdf_path = tmp_path / "design.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% fake unit-test placeholder\n")
    creator = tmp_path / "CocosCreator.exe"
    creator.write_text("", encoding="utf-8")

    def _fake_manifest(*, output_dir, **_kwargs):
        output_root = Path(output_dir)
        image_path = output_root / "commercial_assets" / "images" / "background.png"
        audio_path = output_root / "commercial_assets" / "audio" / "sfx_place.mp3"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(b"image")
        audio_path.write_bytes(b"audio")
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
                    "modality": "audio",
                    "status": "completed",
                    "artifact_paths": [audio_path.as_posix()],
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
    assert payload["commercial_feature_coverage"]["native_cocos_ui_nodes"] is True
    assert payload["commercial_feature_coverage"]["animation_timeline"] is True
    assert payload["commercial_feature_coverage"]["level_switching_ui"] is True
    assert payload["commercial_feature_coverage"]["editor_visible_scene_hierarchy"] is True
    assert payload["commercial_feature_coverage"]["production_component_scripts"] is True
    assert payload["commercial_feature_coverage"]["spriteframe_asset_bindings"] is True
    assert payload["commercial_feature_coverage"]["audioclip_asset_bindings"] is True
    assert payload["commercial_feature_coverage"]["no_hello_3d_template"] is True
    assert payload["commercial_project_inspection"]["go_no_go"] == "GO"
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
