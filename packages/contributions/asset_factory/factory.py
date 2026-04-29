from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from packages.contributions.asset_factory.asset_generation import (
    AssetGenerationRequest,
    AssetGenerationResult,
    generate_gcp_tts,
    generate_procedural_sfx,
    generate_minimax_image,
    generate_minimax_music,
    generate_minimax_speech,
    generate_vertex_gemini_visual_review,
)

AssetGenerator = Callable[[AssetGenerationRequest], AssetGenerationResult]
MAX_PROVIDER_PROMPT_CHARS = 1400


@dataclass(frozen=True, slots=True)
class AssetFactoryGenerators:
    image: AssetGenerator = generate_minimax_image
    sfx: AssetGenerator = generate_procedural_sfx
    speech: AssetGenerator = generate_minimax_speech
    music: AssetGenerator = generate_minimax_music
    tts: AssetGenerator = generate_gcp_tts
    visual_review: AssetGenerator = generate_vertex_gemini_visual_review


def load_asset_factory_manifest(manifest_path: str | Path) -> dict[str, Any]:
    path = Path(manifest_path)
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    assets = payload.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("asset factory manifest must contain a non-empty assets list")
    return payload


def run_asset_factory(
    *,
    style_guide: str | Path,
    manifest_path: str | Path,
    output_dir: str | Path,
    generators: AssetFactoryGenerators | None = None,
    max_attempts: int = 2,
) -> dict[str, Any]:
    prompt_manifest = load_asset_factory_manifest(manifest_path)
    style_text = _load_style_guide(style_guide)
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    asset_root = root / "assets"
    index_path = root / "asset_hash_index.json"
    hash_index = _read_hash_index(index_path)
    active_generators = generators or AssetFactoryGenerators()
    results: list[dict[str, Any]] = []

    for spec in prompt_manifest["assets"]:
        result = _generate_asset_spec(
            spec,
            style_text=style_text,
            asset_root=asset_root,
            hash_index=hash_index,
            generators=active_generators,
            max_attempts=max_attempts,
        )
        results.append(result)

    index_path.write_text(json.dumps(hash_index, ensure_ascii=False, indent=2), encoding="utf-8")
    blockers = _required_asset_blockers(results)
    manifest = {
        "schema_version": "m81_asset_factory_manifest_v1",
        "created_at": datetime.now(UTC).isoformat(),
        "style_guide": style_text,
        "prompt_manifest_path": Path(manifest_path).resolve().as_posix(),
        "asset_root": asset_root.as_posix(),
        "hash_index_path": index_path.as_posix(),
        "results": results,
        "required_asset_names": [
            str(item.get("name"))
            for item in prompt_manifest["assets"]
            if bool(item.get("required", False))
        ],
        "blockers": blockers,
        "go_no_go": "GO" if not blockers else "NO-GO",
        "provenance": {
            "asset_count": len(results),
            "completed_count": sum(1 for item in results if item.get("status") == "completed"),
            "reused_count": sum(1 for item in results if item.get("provenance", {}).get("reused")),
        },
    }
    manifest_output = root / "asset_factory_manifest.json"
    manifest_output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["manifest_path"] = manifest_output.as_posix()
    return manifest


def qa_asset_factory_manifest(
    *,
    asset_manifest_path: str | Path,
    evidence_dir: str | Path,
    visual_review_generator: AssetGenerator = generate_vertex_gemini_visual_review,
) -> dict[str, Any]:
    manifest_path = Path(asset_manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    evidence_root = Path(evidence_dir).resolve()
    evidence_root.mkdir(parents=True, exist_ok=True)
    missing_required = _required_asset_blockers(manifest.get("results", []))
    image_results = [
        item
        for item in manifest.get("results", [])
        if item.get("status") == "completed"
        and str(item.get("modality")) == "image"
        and item.get("artifact_paths")
    ]
    sfx_results = [
        item
        for item in manifest.get("results", [])
        if item.get("status") == "completed"
        and str(item.get("modality")) == "sfx"
        and item.get("artifact_paths")
    ]
    sfx_blockers: list[str] = []
    sfx_reviews: list[dict[str, Any]] = []
    for item in sfx_results:
        meta = item.get("metadata") or {}
        checks = {
            "mime_wav": item.get("mime_type") == "audio/wav",
            "sha256": bool(meta.get("sha256")),
            "duration": (meta.get("duration_seconds") or 0) > 0,
            "rms": (meta.get("rms") or 0) > 0,
            "peak": (meta.get("peak") or 0) > 0,
            "non_silent": meta.get("non_silent") is True,
            "not_clipped": meta.get("clipping") is not True,
            "provenance": bool(item.get("provenance")),
            "qa_gate": meta.get("qa_gate_passed") is True,
        }
        failed = [k for k, v in checks.items() if not v]
        passed = all(checks.values())
        sfx_reviews.append({"asset_name": item["asset_name"], "qa_passed": passed, "failed_checks": failed, "checks": checks})
        if not passed:
            sfx_blockers.append(f"sfx_qa_{item['asset_name']}_{failed[0]}")
    reviews: list[dict[str, Any]] = []
    for item in image_results:
        review = visual_review_generator(
            AssetGenerationRequest(
                provider="vertex_generation_api",
                modality="vision_review",
                prompt="Review this generated game asset for commercial readiness, style consistency, and UI safety.",
                output_dir=evidence_root,
                filename=f"{item['asset_name']}_visual_review.json",
                metadata={"image_path": item["artifact_paths"][0]},
            )
        )
        reviews.append({"asset_name": item["asset_name"], **review.to_dict()})
    report = {
        "schema_version": "m81_asset_factory_qa_v1",
        "created_at": datetime.now(UTC).isoformat(),
        "asset_manifest_path": manifest_path.resolve().as_posix(),
        "required_assets_present": not missing_required,
        "missing_required_blockers": missing_required,
        "visual_review_count": len(reviews),
        "visual_reviews": reviews,
        "go_no_go": "GO" if not missing_required and all(item.get("status") == "completed" for item in reviews) else "NO-GO",
        "sfx_review_count": len(sfx_reviews),
        "sfx_reviews": sfx_reviews,
        "sfx_blockers": sfx_blockers,
    }
    if sfx_blockers:
        report["go_no_go"] = "NO-GO"
    elif report["go_no_go"] == "GO" and missing_required:
        report["go_no_go"] = "NO-GO"
    report_path = evidence_root / "asset_factory_qa_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["report_path"] = report_path.as_posix()
    return report


def _generate_asset_spec(
    spec: dict[str, Any],
    *,
    style_text: str,
    asset_root: Path,
    hash_index: dict[str, Any],
    generators: AssetFactoryGenerators,
    max_attempts: int,
) -> dict[str, Any]:
    name = str(spec.get("name") or "").strip()
    if not name:
        raise ValueError("asset spec missing name")
    modality = str(spec.get("modality") or "image")
    provider = str(spec.get("provider") or _default_provider_for_modality(modality))
    filename = str(spec.get("filename") or f"{name}{_default_suffix_for_modality(modality)}")
    prompt = _prompt_for_spec(spec, style_text)
    dedupe_key = _dedupe_key(provider=provider, modality=modality, prompt=prompt, filename=filename)
    indexed = hash_index.get(dedupe_key)
    if indexed and indexed.get("artifact_paths") and all(Path(path).exists() for path in indexed["artifact_paths"]):
        return {
            "asset_name": name,
            "required": bool(spec.get("required", False)),
            "provider": provider,
            "modality": modality,
            "status": "completed",
            "artifact_paths": list(indexed["artifact_paths"]),
            "mime_type": indexed.get("mime_type"),
            "model": indexed.get("model"),
            "failure_class": None,
            "metadata": {"dedupe_reused": True},
            "provenance": {**indexed.get("provenance", {}), "reused": True},
        }

    generator = _generator_for(provider=provider, modality=modality, generators=generators)
    request = AssetGenerationRequest(
        provider=provider,
        modality=modality,
        prompt=prompt,
        output_dir=asset_root / _folder_for_modality(modality),
        filename=filename,
        model=spec.get("model"),
        mime_type=spec.get("mime_type"),
        metadata=dict(spec.get("metadata") or {}),
    )
    result = _generate_with_retries(generator, request, attempts=max_attempts)
    payload = {
        "asset_name": name,
        "required": bool(spec.get("required", False)),
        **result.to_dict(),
        "provenance": {
            "dedupe_key": dedupe_key,
            "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "output_hashes": _hash_files(result.artifact_paths),
            "reused": False,
        },
    }
    if result.status == "completed" and result.artifact_paths:
        hash_index[dedupe_key] = {
            "artifact_paths": list(result.artifact_paths),
            "mime_type": result.mime_type,
            "model": result.model,
            "provenance": payload["provenance"],
        }
    return payload


def _generate_with_retries(
    generator: AssetGenerator,
    request: AssetGenerationRequest,
    *,
    attempts: int,
) -> AssetGenerationResult:
    last_result: AssetGenerationResult | None = None
    for attempt in range(1, max(1, attempts) + 1):
        result = generator(request)
        result.metadata = {**(result.metadata or {}), "attempt": attempt, "max_attempts": attempts}
        if result.status == "completed" and result.artifact_paths:
            return result
        last_result = result
    assert last_result is not None
    return last_result


def _required_asset_blockers(results: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for item in results:
        if not bool(item.get("required", False)):
            continue
        if item.get("status") == "completed" and item.get("artifact_paths"):
            continue
        name = str(item.get("asset_name") or "unknown")
        failure = str(item.get("failure_class") or "not_completed")
        blockers.append(f"required_asset_{name}_{failure}")
    return blockers


def _load_style_guide(style_guide: str | Path) -> str:
    value = str(style_guide)
    path = Path(value)
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return value.strip()


def _read_hash_index(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _prompt_for_spec(spec: dict[str, Any], style_text: str) -> str:
    prompt = str(spec.get("prompt") or "")
    if "{style_guide}" in prompt:
        suffix = prompt.replace("{style_guide}", "").lstrip("; ").strip()
        return _fit_prompt_with_suffix(style_text, suffix)
    return _fit_prompt_with_suffix(style_text, prompt) if style_text else _truncate_prompt(prompt)


def _fit_prompt_with_suffix(style_text: str, suffix: str) -> str:
    style = style_text.strip()
    tail = suffix.strip()
    if not style:
        return _truncate_prompt(tail)
    if not tail:
        return _truncate_prompt(style)
    separator = "; "
    composed = f"{style}{separator}{tail}"
    if len(composed) <= MAX_PROVIDER_PROMPT_CHARS:
        return composed
    style_budget = MAX_PROVIDER_PROMPT_CHARS - len(separator) - len(tail)
    if style_budget > 80:
        return f"{style[:style_budget].rstrip()}{separator}{tail}"
    return _truncate_prompt(composed)


def _truncate_prompt(prompt: str) -> str:
    return prompt.strip()[:MAX_PROVIDER_PROMPT_CHARS].rstrip()


def _generator_for(
    *,
    provider: str,
    modality: str,
    generators: AssetFactoryGenerators,
) -> AssetGenerator:
    if modality == "music":
        return generators.music
    if provider == "procedural_sfx_local":
        return generators.sfx
    if modality == "sfx":
        return generators.sfx
    if modality == "vision_review":
        return generators.visual_review
    if provider == "gcp_tts_api":
        return generators.tts
    if modality == "audio":
        return generators.speech
    return generators.image


def _default_provider_for_modality(modality: str) -> str:
    if modality in {"audio", "voice"}:
        return "mmx_generation_api"
    if modality == "sfx":
        return "procedural_sfx_local"
    if modality == "music":
        return "mmx_generation_api"
    if modality == "vision_review":
        return "vertex_generation_api"
    return "mmx_generation_api"


def _folder_for_modality(modality: str) -> str:
    if modality in {"audio", "music", "voice"}:
        return "audio"
    if modality == "sfx":
        return "audio"
    if modality == "vision_review":
        return "reviews"
    return "images"


def _default_suffix_for_modality(modality: str) -> str:
    if modality in {"audio", "music", "voice"}:
        return ".mp3"
    if modality == "vision_review":
        return ".json"
    if modality == "sfx":
        return ".json"
    return ".png"


def _dedupe_key(*, provider: str, modality: str, prompt: str, filename: str) -> str:
    payload = json.dumps(
        {"provider": provider, "modality": modality, "prompt": prompt, "filename": filename},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _hash_files(paths: list[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for value in paths:
        path = Path(value)
        if path.exists():
            hashes[path.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes
