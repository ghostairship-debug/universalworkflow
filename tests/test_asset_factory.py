from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import apps.operator_cli.asset_commands as asset_commands
from apps.operator_cli.main import app
from packages.contributions.asset_factory.asset_generation import AssetGenerationRequest, AssetGenerationResult
from packages.contributions.asset_factory.factory import AssetFactoryGenerators, qa_asset_factory_manifest, run_asset_factory


def _fake_asset_generator(request: AssetGenerationRequest) -> AssetGenerationResult:
    output = Path(request.output_dir) / request.filename
    output.parent.mkdir(parents=True, exist_ok=True)
    if request.modality == "vision_review":
        output.write_text('{"status":"reviewed"}', encoding="utf-8")
        mime_type = "application/json"
    else:
        output.write_bytes(f"{request.provider}:{request.modality}:{request.prompt}".encode("utf-8"))
        mime_type = request.mime_type or "application/octet-stream"
    return AssetGenerationResult(
        provider=request.provider,
        modality=request.modality,
        status="completed",
        artifact_paths=[output.as_posix()],
        mime_type=mime_type,
        model=request.model,
    )


def _write_prompt_manifest(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "m81_asset_factory_prompt_manifest_v1",
                "assets": [
                    {
                        "name": "hero_background",
                        "modality": "image",
                        "provider": "mmx_generation_api",
                        "filename": "hero_background.png",
                        "required": True,
                        "prompt": "{style_guide}; readable mobile puzzle background",
                    },
                    {
                        "name": "tap_sfx",
                        "modality": "audio",
                        "provider": "gcp_tts_api",
                        "filename": "tap_sfx.mp3",
                        "required": True,
                        "prompt": "Tap.",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_asset_factory_generates_manifest_with_hash_dedupe_and_provenance(tmp_path: Path) -> None:
    prompt_manifest = tmp_path / "prompt_manifest.json"
    _write_prompt_manifest(prompt_manifest)
    generators = AssetFactoryGenerators(
        image=_fake_asset_generator,
        speech=_fake_asset_generator,
        music=_fake_asset_generator,
        tts=_fake_asset_generator,
        visual_review=_fake_asset_generator,
    )

    first = run_asset_factory(
        style_guide="premium neon",
        manifest_path=prompt_manifest,
        output_dir=tmp_path / "factory",
        generators=generators,
    )
    second = run_asset_factory(
        style_guide="premium neon",
        manifest_path=prompt_manifest,
        output_dir=tmp_path / "factory",
        generators=generators,
    )

    assert first["go_no_go"] == "GO"
    assert Path(first["manifest_path"]).exists()
    assert first["provenance"]["completed_count"] == 2
    assert second["provenance"]["reused_count"] == 2
    assert all(item["provenance"]["output_hashes"] for item in first["results"])


def test_asset_factory_blocks_missing_required_assets(tmp_path: Path) -> None:
    prompt_manifest = tmp_path / "prompt_manifest.json"
    _write_prompt_manifest(prompt_manifest)

    def _blocked_audio(request: AssetGenerationRequest) -> AssetGenerationResult:
        if request.modality == "audio":
            return AssetGenerationResult(
                provider=request.provider,
                modality=request.modality,
                status="blocked",
                failure_class="provider_auth_missing",
            )
        return _fake_asset_generator(request)

    manifest = run_asset_factory(
        style_guide="premium neon",
        manifest_path=prompt_manifest,
        output_dir=tmp_path / "factory",
        generators=AssetFactoryGenerators(
            image=_fake_asset_generator,
            speech=_blocked_audio,
            music=_fake_asset_generator,
            tts=_blocked_audio,
            visual_review=_fake_asset_generator,
        ),
    )

    assert manifest["go_no_go"] == "NO-GO"
    assert "required_asset_tap_sfx_provider_auth_missing" in manifest["blockers"]


def test_asset_factory_qa_reviews_generated_images(tmp_path: Path) -> None:
    prompt_manifest = tmp_path / "prompt_manifest.json"
    _write_prompt_manifest(prompt_manifest)
    manifest = run_asset_factory(
        style_guide="premium neon",
        manifest_path=prompt_manifest,
        output_dir=tmp_path / "factory",
        generators=AssetFactoryGenerators(
            image=_fake_asset_generator,
            speech=_fake_asset_generator,
            music=_fake_asset_generator,
            tts=_fake_asset_generator,
            visual_review=_fake_asset_generator,
        ),
    )

    report = qa_asset_factory_manifest(
        asset_manifest_path=manifest["manifest_path"],
        evidence_dir=tmp_path / "qa",
        visual_review_generator=_fake_asset_generator,
    )

    assert report["go_no_go"] == "GO"
    assert report["visual_review_count"] == 1
    assert Path(report["report_path"]).exists()


def test_cli_asset_factory_run_and_qa_commands(tmp_path: Path, monkeypatch) -> None:
    prompt_manifest = tmp_path / "prompt_manifest.json"
    _write_prompt_manifest(prompt_manifest)

    def _fake_run_asset_factory(**kwargs):
        output = Path(kwargs["output_dir"])
        output.mkdir(parents=True, exist_ok=True)
        manifest_path = output / "asset_factory_manifest.json"
        manifest_path.write_text("{}", encoding="utf-8")
        return {"go_no_go": "GO", "manifest_path": manifest_path.as_posix(), "results": []}

    def _fake_qa_asset_factory_manifest(**kwargs):
        evidence = Path(kwargs["evidence_dir"])
        evidence.mkdir(parents=True, exist_ok=True)
        return {"go_no_go": "GO", "report_path": (evidence / "asset_factory_qa_report.json").as_posix()}

    monkeypatch.setattr(asset_commands, "run_asset_factory", _fake_run_asset_factory)
    monkeypatch.setattr(asset_commands, "qa_asset_factory_manifest", _fake_qa_asset_factory_manifest)

    run_result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "asset",
            "factory",
            "run",
            "--style-guide",
            "premium neon",
            "--manifest",
            str(prompt_manifest),
            "--output-dir",
            str(tmp_path / "factory"),
        ],
    )
    qa_result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "asset",
            "factory",
            "qa",
            "--asset-manifest",
            str(tmp_path / "factory" / "asset_factory_manifest.json"),
            "--evidence-dir",
            str(tmp_path / "qa"),
        ],
    )

    assert run_result.exit_code == 0
    assert qa_result.exit_code == 0
