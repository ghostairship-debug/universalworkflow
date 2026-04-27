from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable


HttpPost = Callable[[str, dict[str, str], dict[str, Any], int], dict[str, Any]]
HttpGetBytes = Callable[[str, int], bytes]


@dataclass(slots=True)
class AssetGenerationRequest:
    provider: str
    modality: str
    prompt: str
    output_dir: str | Path
    filename: str
    model: str | None = None
    mime_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AssetGenerationResult:
    provider: str
    modality: str
    status: str
    artifact_paths: list[str] = field(default_factory=list)
    mime_type: str | None = None
    model: str | None = None
    failure_class: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {error_body[:1000]}") from exc


def _get_bytes(url: str, timeout_seconds: int) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
        return response.read()


def _write_bytes(path: Path, data: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
    }


def _minimax_api_key() -> tuple[str | None, str]:
    if os.getenv("MINIMAX_API_KEY"):
        return os.getenv("MINIMAX_API_KEY"), "MINIMAX_API_KEY"
    return os.getenv("MINIMAX_TOKEN"), "MINIMAX_TOKEN"


def _minimax_base_url() -> str:
    base_url = os.getenv("MINIMAX_BASE_URL") or os.getenv("MINIMAX_API_HOST") or "https://api.minimax.io/v1"
    base_url = base_url.rstrip("/")
    return base_url if base_url.endswith("/v1") else f"{base_url}/v1"


def _google_cloud_project() -> str | None:
    for env_name in ("WORKFLOW_GCP_QUOTA_PROJECT", "GOOGLE_CLOUD_QUOTA_PROJECT"):
        value = os.getenv(env_name)
        if value:
            return value
    gcloud = shutil.which("gcloud")
    if gcloud:
        try:
            completed = subprocess.run(
                [gcloud, "config", "get-value", "project"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        except Exception:
            completed = None
        if completed is not None:
            value = completed.stdout.strip()
            if completed.returncode == 0 and value and value != "(unset)":
                return value
    for env_name in ("GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT", "CLOUDSDK_CORE_PROJECT"):
        value = os.getenv(env_name)
        if value:
            return value
    return None


def _vertex_location() -> str:
    return (
        os.getenv("WORKFLOW_VERTEX_LOCATION")
        or os.getenv("GOOGLE_CLOUD_LOCATION")
        or os.getenv("VERTEX_LOCATION")
        or "us-central1"
    )


def _vertex_api_base_url(location: str) -> str:
    normalized = location.strip().lower()
    if normalized == "global":
        return "https://aiplatform.googleapis.com/v1"
    return f"https://{normalized}-aiplatform.googleapis.com/v1"


def _gcp_auth_headers() -> tuple[dict[str, str] | None, dict[str, Any]]:
    token = _gcloud_access_token()
    project = _google_cloud_project()
    if not token:
        return None, {"auth": "gcloud_adc"}
    if not project:
        return None, {"auth": "gcloud_adc", "project": "missing"}
    headers = {"Authorization": f"Bearer {token}", "X-Goog-User-Project": project}
    return headers, {"project": project, "quota_project": project}


def _extract_base64_strings(payload: Any, keys: set[str]) -> list[str]:
    values: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in keys:
                if isinstance(value, str):
                    values.append(value)
                elif isinstance(value, list):
                    values.extend(str(item) for item in value if isinstance(item, str))
            values.extend(_extract_base64_strings(value, keys))
    elif isinstance(payload, list):
        for item in payload:
            values.extend(_extract_base64_strings(item, keys))
    return values


def _extract_strings(payload: Any, keys: set[str]) -> list[str]:
    values: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in keys and isinstance(value, str):
                values.append(value)
            values.extend(_extract_strings(value, keys))
    elif isinstance(payload, list):
        for item in payload:
            values.extend(_extract_strings(item, keys))
    return values


def _decode_base64_or_hex_audio(value: str) -> bytes:
    candidate = value.strip()
    if not candidate:
        raise ValueError("empty audio payload")
    if len(candidate) % 2 == 0 and all(char in "0123456789abcdefABCDEF" for char in candidate):
        return bytes.fromhex(candidate)
    return base64.b64decode(candidate, validate=True)


def _extract_urls(payload: Any) -> list[str]:
    urls: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in {"url", "audio_url", "image_url", "file_url"} and isinstance(value, str) and value.startswith("http"):
                urls.append(value)
            elif key in {"image_urls", "audio_urls"} and isinstance(value, list):
                urls.extend(str(item) for item in value if isinstance(item, str) and str(item).startswith("http"))
            else:
                urls.extend(_extract_urls(value))
    elif isinstance(payload, list):
        for item in payload:
            urls.extend(_extract_urls(item))
    return urls


def _extract_text_parts(payload: Any) -> list[str]:
    values: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "text" and isinstance(value, str):
                values.append(value)
            else:
                values.extend(_extract_text_parts(value))
    elif isinstance(payload, list):
        for item in payload:
            values.extend(_extract_text_parts(item))
    return values


def _mime_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"


def _blocked_result(request: AssetGenerationRequest, failure_class: str, metadata: dict[str, Any]) -> AssetGenerationResult:
    return AssetGenerationResult(
        provider=request.provider,
        modality=request.modality,
        status="blocked",
        model=request.model,
        failure_class=failure_class,
        metadata=metadata,
    )


def _response_error_metadata(payload: dict[str, Any]) -> dict[str, Any] | None:
    base_resp = payload.get("base_resp")
    if isinstance(base_resp, dict) and base_resp.get("status_code") not in {None, 0, "0"}:
        return {
            "base_resp": base_resp,
            "response_keys": sorted(str(key) for key in payload.keys()),
        }
    return None


def generate_minimax_image(
    request: AssetGenerationRequest,
    *,
    http_post: HttpPost | None = None,
    http_get: HttpGetBytes | None = None,
    timeout_seconds: int = 120,
) -> AssetGenerationResult:
    api_key, api_key_env = _minimax_api_key()
    if not api_key:
        return _blocked_result(request, "provider_auth_missing", {"api_key_env": api_key_env})
    model = request.model or "image-01"
    post = http_post or _post_json
    get = http_get or _get_bytes
    try:
        payload = post(
            f"{_minimax_base_url()}/image_generation",
            {"Authorization": f"Bearer {api_key}"},
            {
                "model": model,
                "prompt": request.prompt,
                "aspect_ratio": request.metadata.get("aspect_ratio", "1:1"),
                "response_format": "base64",
            },
            timeout_seconds,
        )
        output = Path(request.output_dir) / request.filename
        base64_values = _extract_base64_strings(payload, {"image_base64", "base64", "b64_json"})
        if base64_values:
            asset_meta = _write_bytes(output, base64.b64decode(base64_values[0]))
        else:
            urls = _extract_urls(payload)
            if not urls:
                raise ValueError("MiniMax image response did not include base64 image or URL")
            asset_meta = _write_bytes(output, get(urls[0], timeout_seconds))
        return AssetGenerationResult(
            provider="mmx_generation_api",
            modality="image",
            status="completed",
            artifact_paths=[output.as_posix()],
            mime_type=request.mime_type or "image/png",
            model=model,
            metadata={"transport": "api", **asset_meta},
        )
    except Exception as exc:
        return _blocked_result(request, exc.__class__.__name__, {"error": str(exc), "model": model})


def generate_minimax_speech(
    request: AssetGenerationRequest,
    *,
    http_post: HttpPost | None = None,
    http_get: HttpGetBytes | None = None,
    timeout_seconds: int = 120,
) -> AssetGenerationResult:
    api_key, api_key_env = _minimax_api_key()
    if not api_key:
        return _blocked_result(request, "provider_auth_missing", {"api_key_env": api_key_env})
    model = request.model or "speech-2.8-hd"
    post = http_post or _post_json
    get = http_get or _get_bytes
    try:
        payload = post(
            f"{_minimax_base_url()}/t2a_v2",
            {"Authorization": f"Bearer {api_key}"},
            {
                "model": model,
                "text": request.prompt,
                "stream": False,
                "language_boost": request.metadata.get("language_boost", "auto"),
                "output_format": request.metadata.get("output_format", "hex"),
                "voice_setting": {
                    "voice_id": request.metadata.get("voice_id", "English_expressive_narrator"),
                    "speed": request.metadata.get("speed", 1),
                    "vol": request.metadata.get("vol", 1),
                    "pitch": request.metadata.get("pitch", 0),
                },
                "audio_setting": {
                    "sample_rate": request.metadata.get("sample_rate", 32000),
                    "bitrate": request.metadata.get("bitrate", 128000),
                    "format": request.metadata.get("format", "mp3"),
                    "channel": request.metadata.get("channel", 1),
                },
            },
            timeout_seconds,
        )
        response_error = _response_error_metadata(payload)
        if response_error:
            raise ValueError(f"MiniMax speech response error: {response_error['base_resp']}")
        output = Path(request.output_dir) / request.filename
        encoded_values = _extract_strings(payload, {"audio_file", "audio_base64", "audio"})
        if encoded_values:
            asset_meta = _write_bytes(output, _decode_base64_or_hex_audio(encoded_values[0]))
        else:
            urls = _extract_urls(payload)
            if not urls:
                raise ValueError("MiniMax speech response did not include hex/base64 audio or URL")
            asset_meta = _write_bytes(output, get(urls[0], timeout_seconds))
        return AssetGenerationResult(
            provider="mmx_generation_api",
            modality="audio",
            status="completed",
            artifact_paths=[output.as_posix()],
            mime_type=request.mime_type or "audio/mpeg",
            model=model,
            metadata={"transport": "api", **asset_meta},
        )
    except Exception as exc:
        return _blocked_result(request, exc.__class__.__name__, {"error": str(exc), "model": model})


def generate_minimax_music(
    request: AssetGenerationRequest,
    *,
    http_post: HttpPost | None = None,
    http_get: HttpGetBytes | None = None,
    timeout_seconds: int = 180,
) -> AssetGenerationResult:
    api_key, api_key_env = _minimax_api_key()
    if not api_key:
        return _blocked_result(request, "provider_auth_missing", {"api_key_env": api_key_env})
    model = request.model or "music-2.6"
    post = http_post or _post_json
    get = http_get or _get_bytes
    try:
        payload = post(
            f"{_minimax_base_url()}/music_generation",
            {"Authorization": f"Bearer {api_key}"},
            {
                "model": model,
                "prompt": request.prompt,
                "lyrics": request.metadata.get("lyrics", ""),
                "stream": False,
                "output_format": request.metadata.get("output_format", "hex"),
                "is_instrumental": request.metadata.get("is_instrumental", not bool(request.metadata.get("lyrics"))),
                "audio_setting": {
                    "sample_rate": request.metadata.get("sample_rate", 44100),
                    "bitrate": request.metadata.get("bitrate", 256000),
                    "format": request.metadata.get("format", "mp3"),
                },
            },
            timeout_seconds,
        )
        response_error = _response_error_metadata(payload)
        if response_error:
            raise ValueError(f"MiniMax music response error: {response_error['base_resp']}")
        output = Path(request.output_dir) / request.filename
        encoded_values = _extract_strings(payload, {"audio_file", "audio_base64", "music_base64", "audio"})
        if encoded_values:
            asset_meta = _write_bytes(output, _decode_base64_or_hex_audio(encoded_values[0]))
        else:
            urls = _extract_urls(payload)
            if not urls:
                raise ValueError("MiniMax music response did not include hex/base64 audio or URL")
            asset_meta = _write_bytes(output, get(urls[0], timeout_seconds))
        return AssetGenerationResult(
            provider="mmx_generation_api",
            modality="music",
            status="completed",
            artifact_paths=[output.as_posix()],
            mime_type=request.mime_type or "audio/mpeg",
            model=model,
            metadata={"transport": "api", **asset_meta},
        )
    except Exception as exc:
        return _blocked_result(request, exc.__class__.__name__, {"error": str(exc), "model": model})


def _gcloud_access_token() -> str | None:
    explicit = os.getenv("GOOGLE_OAUTH_ACCESS_TOKEN")
    if explicit:
        return explicit
    gcloud = shutil.which("gcloud")
    if not gcloud:
        return None
    auth_mode = (os.getenv("WORKFLOW_GCP_AUTH_MODE") or "user").strip().lower()
    user_command = [gcloud, "auth", "print-access-token", "--quiet"]
    adc_command = [gcloud, "auth", "application-default", "print-access-token", "--quiet"]
    commands = [adc_command, user_command] if auth_mode in {"adc", "application_default"} else [user_command, adc_command]
    for command in commands:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        except Exception:
            continue
        token = completed.stdout.strip()
        if completed.returncode == 0 and token:
            return token
    return None


def _classify_gcp_tts_error(exc: Exception) -> tuple[str, dict[str, Any]]:
    message = str(exc)
    metadata: dict[str, Any] = {"error": message}
    if "quota project" in message:
        return "gcp_quota_project_missing", metadata
    if "SERVICE_DISABLED" in message or "has not been used" in message:
        return "gcp_service_disabled", metadata
    if "PERMISSION_DENIED" in message or "403" in message:
        return "gcp_permission_denied", metadata
    return exc.__class__.__name__, metadata


def generate_gcp_tts(
    request: AssetGenerationRequest,
    *,
    http_post: HttpPost | None = None,
    timeout_seconds: int = 120,
) -> AssetGenerationResult:
    token = _gcloud_access_token()
    if not token:
        return _blocked_result(request, "provider_auth_missing", {"auth": "gcloud_adc"})
    post = http_post or _post_json
    quota_project = request.metadata.get("quota_project") or _google_cloud_project()
    headers = {"Authorization": f"Bearer {token}"}
    if quota_project:
        headers["X-Goog-User-Project"] = str(quota_project)
    try:
        payload = post(
            "https://texttospeech.googleapis.com/v1/text:synthesize",
            headers,
            {
                "input": {"text": request.prompt},
                "voice": {
                    "languageCode": request.metadata.get("language_code", "en-US"),
                    "name": request.metadata.get("voice_name", "en-US-Neural2-D"),
                },
                "audioConfig": {"audioEncoding": request.metadata.get("audio_encoding", "MP3")},
            },
            timeout_seconds,
        )
        audio_values = _extract_base64_strings(payload, {"audioContent"})
        if not audio_values:
            raise ValueError("Vertex TTS response did not include audioContent")
        output = Path(request.output_dir) / request.filename
        asset_meta = _write_bytes(output, base64.b64decode(audio_values[0]))
        return AssetGenerationResult(
            provider="gcp_tts_api",
            modality="audio",
            status="completed",
            artifact_paths=[output.as_posix()],
            mime_type=request.mime_type or "audio/mpeg",
            model=request.model or "cloud-tts",
            metadata={"transport": "api", "quota_project": quota_project, **asset_meta},
        )
    except Exception as exc:
        failure_class, metadata = _classify_gcp_tts_error(exc)
        metadata["quota_project"] = quota_project
        return _blocked_result(request, failure_class, metadata)


def generate_vertex_imagen(
    request: AssetGenerationRequest,
    *,
    http_post: HttpPost | None = None,
    timeout_seconds: int = 180,
) -> AssetGenerationResult:
    headers, auth_metadata = _gcp_auth_headers()
    if headers is None:
        return _blocked_result(request, "provider_auth_missing", auth_metadata)
    project = str(auth_metadata["project"])
    requested_location = str(request.metadata.get("location") or _vertex_location())
    # Imagen prediction endpoints are regional. Gemini generateContent can use the
    # global endpoint, but Imagen should fall back to a regional online location.
    location = "us-central1" if requested_location.strip().lower() == "global" else requested_location
    model = request.model or os.getenv("WORKFLOW_VERTEX_IMAGEN_MODEL") or "imagen-4.0-generate-001"
    post = http_post or _post_json
    try:
        payload = post(
            f"{_vertex_api_base_url(location)}/projects/{project}/locations/{location}/publishers/google/models/{model}:predict",
            headers,
            {
                "instances": [{"prompt": request.prompt}],
                "parameters": {
                    "sampleCount": int(request.metadata.get("sample_count", 1)),
                    "aspectRatio": request.metadata.get("aspect_ratio", "1:1"),
                    "addWatermark": bool(request.metadata.get("add_watermark", True)),
                    "enhancePrompt": bool(request.metadata.get("enhance_prompt", True)),
                },
            },
            timeout_seconds,
        )
        output = Path(request.output_dir) / request.filename
        base64_values = _extract_base64_strings(
            payload,
            {"bytesBase64Encoded", "imageBase64", "image_base64", "base64", "b64_json"},
        )
        if not base64_values:
            raise ValueError("Vertex Imagen response did not include base64 image bytes")
        asset_meta = _write_bytes(output, base64.b64decode(base64_values[0]))
        return AssetGenerationResult(
            provider="vertex_generation_api",
            modality="image",
            status="completed",
            artifact_paths=[output.as_posix()],
            mime_type=request.mime_type or "image/png",
            model=model,
            metadata={
                "transport": "api",
                "location": location,
                "requested_location": requested_location,
                **auth_metadata,
                **asset_meta,
            },
        )
    except Exception as exc:
        failure_class, metadata = _classify_gcp_tts_error(exc)
        return _blocked_result(
            request,
            failure_class,
            {"error": str(exc), "model": model, "location": location, "requested_location": requested_location, **metadata},
        )


def generate_vertex_gemini_visual_review(
    request: AssetGenerationRequest,
    *,
    http_post: HttpPost | None = None,
    timeout_seconds: int = 120,
) -> AssetGenerationResult:
    headers, auth_metadata = _gcp_auth_headers()
    if headers is None:
        return _blocked_result(request, "provider_auth_missing", auth_metadata)
    image_path_value = request.metadata.get("image_path")
    if not image_path_value:
        return _blocked_result(request, "image_path_required", {"provider": "vertex_gemini_visual_review"})
    image_path = Path(str(image_path_value)).resolve()
    if not image_path.exists():
        return _blocked_result(request, "image_path_missing", {"image_path": image_path.as_posix()})
    project = str(auth_metadata["project"])
    location = str(request.metadata.get("location") or _vertex_location())
    model = request.model or os.getenv("WORKFLOW_VERTEX_GEMINI_MODEL") or "gemini-2.5-flash"
    mime_type = request.mime_type or str(request.metadata.get("mime_type") or _mime_for_path(image_path))
    post = http_post or _post_json
    try:
        payload = post(
            f"{_vertex_api_base_url(location)}/projects/{project}/locations/{location}/publishers/google/models/{model}:generateContent",
            headers,
            {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": request.prompt},
                            {
                                "inlineData": {
                                    "mimeType": mime_type,
                                    "data": base64.b64encode(image_path.read_bytes()).decode("ascii"),
                                }
                            },
                        ],
                    }
                ]
            },
            timeout_seconds,
        )
        text = "\n".join(part.strip() for part in _extract_text_parts(payload) if part.strip()).strip()
        if not text:
            raise ValueError("Vertex Gemini visual review response did not include text")
        output = Path(request.output_dir) / request.filename
        output.parent.mkdir(parents=True, exist_ok=True)
        review_payload = {
            "provider": "vertex_generation_api",
            "modality": "vision_review",
            "model": model,
            "image_path": image_path.as_posix(),
            "review_text": text,
            "created_at": datetime.now(UTC).isoformat(),
        }
        output.write_text(json.dumps(review_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        encoded = text.encode("utf-8")
        return AssetGenerationResult(
            provider="vertex_generation_api",
            modality="vision_review",
            status="completed",
            artifact_paths=[output.as_posix()],
            mime_type="application/json",
            model=model,
            metadata={
                "transport": "api",
                "location": location,
                "review_sha256": hashlib.sha256(encoded).hexdigest(),
                "size_bytes": len(encoded),
                **auth_metadata,
            },
        )
    except Exception as exc:
        failure_class, metadata = _classify_gcp_tts_error(exc)
        return _blocked_result(request, failure_class, {"error": str(exc), "model": model, "location": location, **metadata})


def generate_vertex_tts(
    request: AssetGenerationRequest,
    *,
    http_post: HttpPost | None = None,
    timeout_seconds: int = 120,
) -> AssetGenerationResult:
    """Compatibility wrapper; Cloud TTS is a GCP service, not Vertex AI proper."""

    return generate_gcp_tts(request, http_post=http_post, timeout_seconds=timeout_seconds)


def write_asset_manifest(result: AssetGenerationResult, manifest_path: str | Path) -> str:
    output = Path(manifest_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                **result.to_dict(),
                "created_at": datetime.now(UTC).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output.as_posix()
