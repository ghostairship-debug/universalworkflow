from __future__ import annotations

import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app
import apps.operator_cli.game_commands as game_commands
import packages.contributions.games.cocos.e2e as cocos_e2e_module
from packages.contributions.asset_factory.asset_generation import AssetGenerationRequest, AssetGenerationResult
from packages.contributions.games.cocos.commercial_assets import (
    generate_cocos_commercial_asset_manifest,
    generate_cocos_local_stable_asset_manifest,
)
from packages.contributions.games.cocos.e2e import run_cocos_game_e2e
from packages.contributions.games.cocos.graph_bridge import build_cocos_graph_evidence_bridge
from packages.contributions.games.cocos.inspector import describe_cocos_delivery_modes, inspect_cocos_project_v2
from packages.contributions.games.cocos.player_validation import validate_cocos_player_visible_evidence
from packages.contributions.games.cocos.sample_closeout import run_cocos_small_goal_sample_closeout


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
    assert payload["commercial_go_no_go"] == "GO"
    assert payload["commercial_playable_go"] is False
    assert payload["manifest"]["go_no_go"] == "NO-GO"


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
