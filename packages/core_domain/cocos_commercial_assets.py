from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from packages.core_domain.asset_generation import (
    AssetGenerationRequest,
    AssetGenerationResult,
    generate_gcp_tts,
    generate_minimax_image,
    generate_minimax_music,
    generate_minimax_speech,
    generate_vertex_gemini_visual_review,
    write_asset_manifest,
)

AssetGenerator = Callable[[AssetGenerationRequest], AssetGenerationResult]


def _result_payload(name: str, result: AssetGenerationResult) -> dict[str, Any]:
    return {"asset_name": name, **result.to_dict()}


def _coverage(results: list[dict[str, Any]]) -> dict[str, bool]:
    completed = [item for item in results if item.get("status") == "completed"]
    completed_names = {str(item.get("asset_name") or "") for item in completed}
    completed_modalities = {str(item.get("modality") or "") for item in completed}
    return {
        "generated_art_assets": "image" in completed_modalities,
        "generated_audio_assets": bool({"audio", "music"} & completed_modalities),
        "skin_switching_visual_assets": any("skin" in name for name in completed_names),
        "particle_effects": any("particle" in name for name in completed_names),
        "commercial_polish_pass": len(completed) >= 4,
    }


def generate_cocos_commercial_asset_manifest(
    *,
    output_dir: str | Path,
    style_prompt: str = "premium neon 1010 block puzzle mobile game, polished casual commercial art",
    include_vertex_review: bool = True,
    image_generator: AssetGenerator = generate_minimax_image,
    speech_generator: AssetGenerator = generate_minimax_speech,
    music_generator: AssetGenerator = generate_minimax_music,
    tts_generator: AssetGenerator = generate_gcp_tts,
    visual_review_generator: AssetGenerator = generate_vertex_gemini_visual_review,
) -> dict[str, Any]:
    root = Path(output_dir).resolve()
    asset_dir = root / "commercial_assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    image_specs = [
        (
            "background",
            "background.png",
            f"{style_prompt}; vertical 390x844 mobile game background, clean playfield safe area, no text",
        ),
        (
            "block_skin_neon",
            "block_skin_neon.png",
            f"{style_prompt}; glossy square block tile skin sprite sheet, no text, crisp edges",
        ),
        (
            "particle_clear",
            "particle_clear.png",
            f"{style_prompt}; transparent-feeling sparkle particle burst for line clear, no text",
        ),
    ]
    for name, filename, prompt in image_specs:
        result = image_generator(
            AssetGenerationRequest(
                provider="mmx_generation_api",
                modality="image",
                prompt=prompt,
                output_dir=asset_dir / "images",
                filename=filename,
            )
        )
        results.append(_result_payload(name, result))

    audio_specs = [
        ("sfx_place", "sfx_place.mp3", "short polished mobile puzzle block placement sound"),
        ("sfx_clear", "sfx_clear.mp3", "short bright line clear reward sound for casual mobile puzzle game"),
    ]
    for name, filename, prompt in audio_specs:
        result = speech_generator(
            AssetGenerationRequest(
                provider="mmx_generation_api",
                modality="audio",
                prompt=prompt,
                output_dir=asset_dir / "audio",
                filename=filename,
            )
        )
        results.append(_result_payload(name, result))

    music_result = music_generator(
        AssetGenerationRequest(
            provider="mmx_generation_api",
            modality="music",
            prompt="short seamless upbeat premium casual puzzle game background loop, no vocals",
            output_dir=asset_dir / "audio",
            filename="bgm_loop.mp3",
        )
    )
    results.append(_result_payload("bgm_loop", music_result))

    voice_result = tts_generator(
        AssetGenerationRequest(
            provider="gcp_tts_api",
            modality="audio",
            prompt="Great clear. Keep going.",
            output_dir=asset_dir / "audio",
            filename="voice_reward.mp3",
        )
    )
    results.append(_result_payload("voice_reward", voice_result))

    review_result_payload: dict[str, Any] | None = None
    if include_vertex_review:
        first_image = next(
            (
                item
                for item in results
                if item.get("status") == "completed"
                and item.get("modality") == "image"
                and item.get("artifact_paths")
            ),
            None,
        )
        if first_image:
            review_result = visual_review_generator(
                AssetGenerationRequest(
                    provider="vertex_generation_api",
                    modality="vision_review",
                    prompt=(
                        "Review this mobile game asset for commercial readiness. "
                        "Return concise JSON-like notes covering polish, readability, and game fit."
                    ),
                    output_dir=asset_dir / "reviews",
                    filename="vertex_visual_review.json",
                    metadata={"image_path": first_image["artifact_paths"][0]},
                )
            )
            review_result_payload = _result_payload("vertex_visual_review", review_result)
            results.append(review_result_payload)

    coverage = _coverage(results)
    manifest = {
        "schema_version": "m77_cocos_commercial_assets_v1",
        "created_at": datetime.now(UTC).isoformat(),
        "style_prompt": style_prompt,
        "asset_root": asset_dir.as_posix(),
        "results": results,
        "feature_coverage": coverage,
        "go_no_go": "GO" if all(coverage.values()) else "NO-GO",
    }
    manifest_path = root / "commercial_asset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_asset_manifest(
        AssetGenerationResult(
            provider="cocos_commercial_asset_pipeline",
            modality="manifest",
            status="completed",
            artifact_paths=[manifest_path.as_posix()],
            mime_type="application/json",
            metadata={"asset_count": len(results), "go_no_go": manifest["go_no_go"]},
        ),
        root / "commercial_asset_manifest_summary.json",
    )
    manifest["manifest_path"] = manifest_path.as_posix()
    return manifest
