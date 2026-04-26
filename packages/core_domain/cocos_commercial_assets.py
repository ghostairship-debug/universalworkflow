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
from packages.core_domain.asset_factory import (
    AssetFactoryGenerators,
    qa_asset_factory_manifest,
    run_asset_factory,
)

AssetGenerator = Callable[[AssetGenerationRequest], AssetGenerationResult]
REQUIRED_COMMERCIAL_ASSET_NAMES = {
    "background",
    "block_skin_neon",
    "particle_clear",
    "sfx_place",
    "sfx_clear",
    "bgm_loop",
    "voice_reward",
}


def _result_payload(name: str, result: AssetGenerationResult) -> dict[str, Any]:
    return {"asset_name": name, **result.to_dict()}


def _coverage(results: list[dict[str, Any]]) -> dict[str, bool]:
    completed = [item for item in results if item.get("status") == "completed"]
    completed_names = {
        str(item.get("asset_name") or "")
        for item in completed
        if item.get("artifact_paths")
    }
    return {
        "generated_art_assets": {"background", "block_skin_neon", "particle_clear"} <= completed_names,
        "generated_audio_assets": {"sfx_place", "sfx_clear", "bgm_loop", "voice_reward"} <= completed_names,
        "skin_switching_visual_assets": any("skin" in name for name in completed_names),
        "particle_effects": any("particle" in name for name in completed_names),
        "commercial_polish_pass": REQUIRED_COMMERCIAL_ASSET_NAMES <= completed_names,
    }


def _blocked_required_assets(results: list[dict[str, Any]]) -> list[str]:
    completed_names = {
        str(item.get("asset_name") or "")
        for item in results
        if item.get("status") == "completed" and item.get("artifact_paths")
    }
    blockers = [f"required_asset_{name}_not_completed" for name in sorted(REQUIRED_COMMERCIAL_ASSET_NAMES - completed_names)]
    for item in results:
        name = str(item.get("asset_name") or "")
        if name in REQUIRED_COMMERCIAL_ASSET_NAMES and item.get("status") != "completed":
            failure = item.get("failure_class") or "blocked"
            blocker = f"required_asset_{name}_{failure}"
            if blocker not in blockers:
                blockers.append(blocker)
    return blockers


def _generate_with_retries(
    generator: AssetGenerator,
    request: AssetGenerationRequest,
    *,
    attempts: int = 2,
) -> AssetGenerationResult:
    last_result: AssetGenerationResult | None = None
    for attempt in range(1, attempts + 1):
        result = generator(request)
        metadata = dict(result.metadata or {})
        metadata["attempt"] = attempt
        metadata["max_attempts"] = attempts
        result.metadata = metadata
        if result.status == "completed" and result.artifact_paths:
            return result
        last_result = result
    if last_result is None:
        return generator(request)
    return last_result


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
    root.mkdir(parents=True, exist_ok=True)
    prompt_manifest_path = root / "commercial_asset_prompt_manifest.json"
    prompt_manifest_path.write_text(
        json.dumps(_cocos_asset_factory_prompt_manifest(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    factory_manifest = run_asset_factory(
        style_guide=style_prompt,
        manifest_path=prompt_manifest_path,
        output_dir=root / "commercial_asset_factory",
        generators=AssetFactoryGenerators(
            image=image_generator,
            speech=speech_generator,
            music=music_generator,
            tts=tts_generator,
            visual_review=visual_review_generator,
        ),
        max_attempts=2,
    )
    results: list[dict[str, Any]] = list(factory_manifest["results"])
    qa_report: dict[str, Any] | None = None
    if include_vertex_review:
        qa_report = qa_asset_factory_manifest(
            asset_manifest_path=factory_manifest["manifest_path"],
            evidence_dir=root / "commercial_asset_factory" / "qa",
            visual_review_generator=visual_review_generator,
        )
        for review in qa_report["visual_reviews"]:
            results.append({**review, "asset_name": f"{review['asset_name']}_visual_review"})

    coverage = _coverage(results)
    blockers = _blocked_required_assets(results)
    manifest = {
        "schema_version": "m77_cocos_commercial_assets_v1",
        "created_at": datetime.now(UTC).isoformat(),
        "style_prompt": style_prompt,
        "asset_root": factory_manifest["asset_root"],
        "results": results,
        "feature_coverage": coverage,
        "blockers": blockers,
        "go_no_go": "GO" if all(coverage.values()) and not blockers else "NO-GO",
        "asset_factory_manifest": factory_manifest,
        "asset_factory_qa": qa_report,
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


def _cocos_asset_factory_prompt_manifest() -> dict[str, Any]:
    return {
        "schema_version": "m81_asset_factory_prompt_manifest_v1",
        "assets": [
            {
                "name": "background",
                "modality": "image",
                "provider": "mmx_generation_api",
                "filename": "background.png",
                "required": True,
                "prompt": "{style_guide}; vertical 390x844 mobile game background, clean playfield safe area, no text",
            },
            {
                "name": "block_skin_neon",
                "modality": "image",
                "provider": "mmx_generation_api",
                "filename": "block_skin_neon.png",
                "required": True,
                "prompt": "{style_guide}; glossy square block tile skin sprite sheet, no text, crisp edges",
            },
            {
                "name": "particle_clear",
                "modality": "image",
                "provider": "mmx_generation_api",
                "filename": "particle_clear.png",
                "required": True,
                "prompt": "{style_guide}; transparent-feeling sparkle particle burst for line clear, no text",
            },
            {
                "name": "sfx_place",
                "modality": "audio",
                "provider": "mmx_generation_api",
                "filename": "sfx_place.mp3",
                "required": True,
                "prompt": "short polished mobile puzzle block placement sound",
            },
            {
                "name": "sfx_clear",
                "modality": "audio",
                "provider": "mmx_generation_api",
                "filename": "sfx_clear.mp3",
                "required": True,
                "prompt": "short bright line clear reward sound for casual mobile puzzle game",
            },
            {
                "name": "bgm_loop",
                "modality": "music",
                "provider": "mmx_generation_api",
                "filename": "bgm_loop.mp3",
                "required": True,
                "prompt": "short seamless upbeat premium casual puzzle game background loop, no vocals",
            },
            {
                "name": "voice_reward",
                "modality": "audio",
                "provider": "gcp_tts_api",
                "filename": "voice_reward.mp3",
                "required": True,
                "prompt": "Great clear. Keep going.",
            },
        ],
    }
