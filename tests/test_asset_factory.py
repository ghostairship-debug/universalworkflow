from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import apps.operator_cli.asset_commands as asset_commands
from apps.operator_cli.main import app
from packages.contributions.asset_factory.asset_generation import (
    AssetGenerationRequest,
    AssetGenerationResult,
    generate_procedural_sfx,
    generate_minimax_image,
    generate_minimax_speech,
)
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


def test_asset_factory_truncates_long_style_prompt_and_preserves_asset_suffix(tmp_path: Path) -> None:
    prompt_manifest = tmp_path / "prompt_manifest.json"
    _write_prompt_manifest(prompt_manifest)
    seen_prompts: list[str] = []

    def _recording_generator(request: AssetGenerationRequest) -> AssetGenerationResult:
        seen_prompts.append(request.prompt)
        return _fake_asset_generator(request)

    run_asset_factory(
        style_guide="premium neon " * 300,
        manifest_path=prompt_manifest,
        output_dir=tmp_path / "factory",
        generators=AssetFactoryGenerators(
            image=_recording_generator,
            speech=_fake_asset_generator,
            music=_fake_asset_generator,
            tts=_fake_asset_generator,
            visual_review=_fake_asset_generator,
        ),
    )

    image_prompt = seen_prompts[0]
    assert len(image_prompt) <= 1400
    assert image_prompt.endswith("readable mobile puzzle background")


def test_minimax_image_records_provider_response_error_metadata(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")

    def _fake_post(*_args, **_kwargs):
        return {
            "base_resp": {"status_code": 2056, "status_msg": "usage limit exceeded"},
            "metadata": {"failed_count": "1", "success_count": "0"},
        }

    result = generate_minimax_image(
        AssetGenerationRequest(
            provider="mmx_generation_api",
            modality="image",
            prompt="background",
            output_dir=tmp_path,
            filename="background.png",
        ),
        http_post=_fake_post,
    )

    assert result.status == "blocked"
    assert result.failure_class == "provider_usage_limit_exceeded"
    assert result.metadata["base_resp"]["status_code"] == 2056
    assert result.metadata["response_keys"] == ["base_resp", "metadata"]


def test_minimax_speech_records_usage_limit_failure_class(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")

    def _fake_post(*_args, **_kwargs):
        return {"base_resp": {"status_code": 2056, "status_msg": "usage limit exceeded"}}

    result = generate_minimax_speech(
        AssetGenerationRequest(
            provider="mmx_generation_api",
            modality="audio",
            prompt="tap",
            output_dir=tmp_path,
            filename="tap.mp3",
        ),
        http_post=_fake_post,
    )

    assert result.status == "blocked"
    assert result.failure_class == "provider_usage_limit_exceeded"


def test_minimax_image_records_missing_output_shape(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")

    def _fake_post(*_args, **_kwargs):
        return {
            "id": "trace-id",
            "data": {},
            "metadata": {"failed_count": "1", "success_count": "0"},
            "base_resp": {"status_code": 0, "status_msg": "success"},
        }

    result = generate_minimax_image(
        AssetGenerationRequest(
            provider="mmx_generation_api",
            modality="image",
            prompt="background",
            output_dir=tmp_path,
            filename="background.png",
        ),
        http_post=_fake_post,
    )

    assert result.status == "blocked"
    assert result.failure_class == "provider_output_missing"
    assert result.metadata["data_keys"] == []
    assert result.metadata["provider_metadata"] == {"failed_count": "1", "success_count": "0"}


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


def test_generate_procedural_sfx_records_qa_metadata(tmp_path: Path) -> None:
    result = generate_procedural_sfx(
        AssetGenerationRequest(
            provider="procedural_sfx_local",
            modality="sfx",
            prompt="Bright arcade coin pickup with a short click tail.",
            output_dir=tmp_path,
            filename="coin_pickup.wav",
        )
    )

    assert result.status == "completed"
    assert result.mime_type == "audio/wav"
    assert len(result.artifact_paths) == 1
    assert Path(result.artifact_paths[0]).exists()

    metadata = result.metadata
    assert {
        "sha256",
        "duration_seconds",
        "rms",
        "peak",
        "non_silent",
        "clipping",
        "provenance",
        "qa_gate_passed",
    } <= metadata.keys()
    assert metadata["duration_seconds"] > 0
    assert metadata["rms"] > 0
    assert metadata["peak"] > 0
    assert metadata["non_silent"] is True
    assert metadata["clipping"] is False
    assert metadata["provenance"] == "procedural_sfx_local"
    assert metadata["qa_gate"] is True
    assert metadata["qa_gate_passed"] is True


def test_asset_factory_qa_accepts_valid_procedural_sfx(tmp_path: Path) -> None:
    prompt_manifest = tmp_path / "prompt_manifest.json"
    prompt_manifest.write_text(
        json.dumps(
            {
                "schema_version": "m81_asset_factory_prompt_manifest_v1",
                "assets": [
                    {
                        "name": "tap_sfx",
                        "modality": "sfx",
                        "provider": "procedural_sfx_local",
                        "filename": "tap_sfx.wav",
                        "required": True,
                        "prompt": "Short premium puzzle tap with light sparkle.",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manifest = run_asset_factory(
        style_guide="premium neon",
        manifest_path=prompt_manifest,
        output_dir=tmp_path / "factory",
        generators=AssetFactoryGenerators(
            image=_fake_asset_generator,
            sfx=generate_procedural_sfx,
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

    assert manifest["go_no_go"] == "GO"
    assert manifest["results"][0]["metadata"]["qa_gate_passed"] is True
    assert report["go_no_go"] == "GO"
    assert report["visual_review_count"] == 0
    assert report["sfx_review_count"] == 1
    assert report["sfx_blockers"] == []
    assert report["sfx_reviews"][0]["asset_name"] == "tap_sfx"
    assert report["sfx_reviews"][0]["qa_passed"] is True
    assert report["sfx_reviews"][0]["failed_checks"] == []
    assert Path(report["report_path"]).exists()


def test_asset_factory_qa_blocks_incomplete_or_silent_sfx_metadata(tmp_path: Path) -> None:
    missing_sha_path = tmp_path / "missing_sha.wav"
    missing_sha_path.write_bytes(b"placeholder-wav")
    silent_style_path = tmp_path / "silent_style.wav"
    silent_style_path.write_bytes(b"placeholder-wav")
    manifest_path = tmp_path / "asset_factory_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "asset_name": "missing_sha_sfx",
                        "required": True,
                        "provider": "procedural_sfx_local",
                        "modality": "sfx",
                        "status": "completed",
                        "artifact_paths": [missing_sha_path.as_posix()],
                        "mime_type": "audio/wav",
                        "metadata": {
                            "duration_seconds": 0.75,
                            "rms": 0.21,
                            "peak": 0.42,
                            "non_silent": True,
                            "clipping": False,
                            "provenance": "procedural_sfx_local",
                            "qa_gate": False,
                        },
                        "provenance": {"reused": False},
                    },
                    {
                        "asset_name": "silent_style_sfx",
                        "required": True,
                        "provider": "procedural_sfx_local",
                        "modality": "sfx",
                        "status": "completed",
                        "artifact_paths": [silent_style_path.as_posix()],
                        "mime_type": "audio/wav",
                        "metadata": {
                            "sha256": "0" * 64,
                            "duration_seconds": 0.75,
                            "rms": 0.21,
                            "peak": 0.42,
                            "non_silent": False,
                            "clipping": False,
                            "provenance": "procedural_sfx_local",
                            "qa_gate": False,
                            "qa_gate_passed": False,
                        },
                        "provenance": {"reused": False},
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = qa_asset_factory_manifest(
        asset_manifest_path=manifest_path,
        evidence_dir=tmp_path / "qa",
        visual_review_generator=_fake_asset_generator,
    )

    reviews = {item["asset_name"]: item for item in report["sfx_reviews"]}

    assert report["go_no_go"] == "NO-GO"
    assert report["sfx_blockers"] == [
        "sfx_qa_missing_sha_sfx_sha256",
        "sfx_qa_silent_style_sfx_non_silent",
    ]
    assert reviews["missing_sha_sfx"]["qa_passed"] is False
    assert reviews["missing_sha_sfx"]["failed_checks"][0] == "sha256"
    assert reviews["silent_style_sfx"]["qa_passed"] is False
    assert reviews["silent_style_sfx"]["failed_checks"][0] == "non_silent"
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
