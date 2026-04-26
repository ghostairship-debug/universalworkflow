from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app
from packages.core_domain.cocos_e2e import run_cocos_game_e2e


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
    script = (output_dir / "assets" / "scripts" / "BlockPuzzleGame.ts").read_text(encoding="utf-8")
    assert "__COCOS_BLOCK_PUZZLE_E2E__" in script
    assert "bootBlockPuzzleStandalone()" in script
    assert "campaignFirstSevenLevels" in script
    assert "Math.floor(this.score / 10 + offset)" in script


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
