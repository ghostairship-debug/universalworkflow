from __future__ import annotations

import base64
import json
from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

import packages.contributions.asset_factory.asset_generation as asset_generation_module
from apps.operator_cli.main import app
from packages.core_domain import capability_probe
from packages.contributions.asset_factory.asset_generation import (
    AssetGenerationRequest,
    generate_gcp_tts,
    generate_minimax_image,
    generate_minimax_music,
    generate_minimax_speech,
    generate_vertex_gemini_visual_review,
    generate_vertex_imagen,
)
from packages.core_domain.automation_lease import create_automation_lease
from packages.core_domain.capability_control_plane import provider_contract_for_key
from packages.core_domain.capability_plane import CapabilityPlane
from packages.core_domain.llm_coding_api import (
    CodingProposalRequest,
    apply_coding_proposal_patch,
    extract_unified_diff_from_proposal,
    generate_coding_proposal,
)
from packages.core_domain.provider_access import provider_access_contract_for_key


class _FakeChatCompletions:
    def create(self, **_kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="## Summary\nProposal only.\n\n## Tests\nRun targeted tests.",
                    )
                )
            ]
        )


class _FakePatchChatCompletions:
    def create(self, **_kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            "## Summary\nApply patch.\n\n```diff\n"
                            "--- a/target.txt\n"
                            "+++ b/target.txt\n"
                            "@@ -1 +1 @@\n"
                            "-old\n"
                            "+new\n"
                            "```\n"
                        )
                    )
                )
            ]
        )


class _FakeClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=_FakeChatCompletions())


class _CapturingChatCompletions:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="## Summary\nProvider-prefixed model normalized.\n\n## Tests\nRun targeted tests.",
                    )
                )
            ]
        )


class _CapturingClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=_CapturingChatCompletions())


class _FakePatchClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=_FakePatchChatCompletions())


def test_provider_access_separates_codex_cli_from_openai_api() -> None:
    codex = provider_access_contract_for_key("codex_cli")
    openai = provider_access_contract_for_key("openai_api")

    assert codex is not None
    assert codex["category"] == "cli_agent"
    assert codex["transport"] == "cli"
    assert "OPENAI_API_KEY" not in codex["auth_sources"]
    assert openai is not None
    assert openai["category"] == "api_model"
    assert openai["default_route"] is False


def test_provider_contracts_include_generation_and_experimental_boundaries() -> None:
    mmx_generation = provider_contract_for_key("mmx_generation_api")
    gcp_tts = provider_contract_for_key("gcp_tts_api")
    langchain = provider_contract_for_key("langchain_agent")

    assert mmx_generation is not None
    assert mmx_generation["category"] == "asset_generator"
    assert "image" in mmx_generation["modalities"]
    assert gcp_tts is not None
    assert gcp_tts["provider"] == "gcp_tts_api"
    assert "not Vertex AI proper" in gcp_tts["route_role"]
    assert langchain is not None
    assert langchain["category"] == "experimental_agent_framework"
    assert "Not part of the default provider route" in " ".join(langchain["notes"])


def test_capability_descriptors_surface_api_and_asset_categories_without_verified_ready() -> None:
    health = CapabilityPlane().list_capability_health(capability_routes=[])

    minimax = next(item for item in health if item.descriptor.capability_id == "api_model:minimax_api")
    mmx_assets = next(item for item in health if item.descriptor.capability_id == "asset_generator:mmx_generation_api")
    gcp_tts = next(item for item in health if item.descriptor.capability_id == "asset_generator:gcp_tts_api")

    assert minimax.readiness_state == "configured"
    assert minimax.runtime_probe_status == "configured"
    assert mmx_assets.readiness_state == "configured"
    assert mmx_assets.descriptor.side_effect_level == "artifact_write"
    assert gcp_tts.readiness_state == "configured"


def test_generate_coding_proposal_uses_direct_api_without_mutation(tmp_path: Path) -> None:
    result = generate_coding_proposal(
        CodingProposalRequest(
            provider="deepseek",
            goal="Review a small patch",
            read_set=["packages/example.py"],
            write_set=["packages/example.py"],
        ),
        evidence_dir=tmp_path,
        client=_FakeClient(),
    )

    assert result.status == "completed"
    assert result.provider == "deepseek_api"
    assert result.metadata["mutation_mode"] == "proposal_only"
    assert result.evidence_path is not None
    payload = json.loads(Path(result.evidence_path).read_text(encoding="utf-8"))
    assert payload["proposal_text"].startswith("## Summary")


def test_generate_coding_proposal_normalizes_router_style_deepseek_model() -> None:
    client = _CapturingClient()

    result = generate_coding_proposal(
        CodingProposalRequest(
            provider="deepseek",
            model="deepseek/deepseek-v4-flash",
            goal="Review a small patch",
        ),
        client=client,
    )

    assert result.status == "completed"
    assert result.model == "deepseek-v4-flash"
    assert client.chat.completions.calls[0]["model"] == "deepseek-v4-flash"


def test_generate_coding_proposal_includes_bounded_read_set_file_context(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "packages" / "example.py"
    target.parent.mkdir(parents=True)
    target.write_text("VALUE = 'current implementation'\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    client = _CapturingClient()

    result = generate_coding_proposal(
        CodingProposalRequest(
            provider="deepseek",
            goal="Update exact file",
            read_set=["packages/example.py"],
            write_set=["packages/example.py"],
        ),
        client=client,
    )

    prompt = client.chat.completions.calls[0]["messages"][1]["content"]
    assert result.status == "completed"
    assert "READ_SET_FILE: packages/example.py" in prompt
    assert "VALUE = 'current implementation'" in prompt


def test_extract_unified_diff_from_fenced_proposal() -> None:
    diff = extract_unified_diff_from_proposal(
        "text\n```diff\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n```\n"
    )

    assert diff.startswith("--- a/a.txt")


def test_apply_coding_proposal_patch_requires_automation_lease(tmp_path: Path) -> None:
    (tmp_path / "target.txt").write_text("old\n", encoding="utf-8")

    result = apply_coding_proposal_patch(
        CodingProposalRequest(
            provider="deepseek",
            goal="update file",
            write_set=["target.txt"],
        ),
        workspace_root=tmp_path,
        automation_lease_id=None,
        client=_FakePatchClient(),
    )

    assert result.status == "blocked"
    assert result.failure_class == "automation_lease_required"
    assert (tmp_path / "target.txt").read_text(encoding="utf-8") == "old\n"


def test_apply_coding_proposal_patch_uses_workflow_write_set_and_tests(tmp_path: Path) -> None:
    (tmp_path / "target.txt").write_text("old\n", encoding="utf-8")
    lease = create_automation_lease(
        workspace_root=tmp_path,
        allowed_actions=["coding_patch_apply"],
        write_set_allowlist=["target.txt"],
    )

    result = apply_coding_proposal_patch(
        CodingProposalRequest(
            provider="deepseek",
            goal="update file",
            write_set=["target.txt"],
        ),
        workspace_root=tmp_path,
        automation_lease_id=lease.lease_id,
        evidence_dir=tmp_path / "evidence",
        test_commands=["python --version"],
        client=_FakePatchClient(),
    )

    assert result.status == "completed"
    assert result.changed_files == ["target.txt"]
    assert result.patch_hash
    assert Path(result.evidence_path).exists()
    assert (tmp_path / "target.txt").read_text(encoding="utf-8") == "new\n"


def test_cli_coding_proposal_blocks_without_api_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_TOKEN", raising=False)

    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "capability",
            "coding-proposal",
            "--provider",
            "minimax",
            "--goal",
            "Draft a proposal",
            "--evidence-dir",
            str(tmp_path / "evidence"),
        ],
    )

    payload = json.loads(result.stdout)
    assert result.exit_code == 1
    assert payload["status"] == "blocked"
    assert payload["failure_class"] == "provider_auth_missing"


def test_minimax_image_generation_writes_binary_asset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")

    def _fake_post(_url, _headers, _payload, _timeout):
        return {"data": {"image_base64": base64.b64encode(b"png-bytes").decode("ascii")}}

    result = generate_minimax_image(
        AssetGenerationRequest(
            provider="mmx_generation_api",
            modality="image",
            prompt="tiny icon",
            output_dir=tmp_path,
            filename="icon.png",
        ),
        http_post=_fake_post,
    )

    assert result.status == "completed"
    assert Path(result.artifact_paths[0]).read_bytes() == b"png-bytes"
    assert result.metadata["sha256"]


def test_minimax_speech_generation_accepts_hex_audio(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")

    def _fake_post(_url, _headers, payload, _timeout):
        assert payload["output_format"] == "hex"
        assert payload["voice_setting"]["voice_id"] == "English_expressive_narrator"
        return {"data": {"audio": b"mp3-bytes".hex(), "status": 2}}

    result = generate_minimax_speech(
        AssetGenerationRequest(
            provider="mmx_generation_api",
            modality="audio",
            prompt="probe",
            output_dir=tmp_path,
            filename="voice.mp3",
        ),
        http_post=_fake_post,
    )

    assert result.status == "completed"
    assert Path(result.artifact_paths[0]).read_bytes() == b"mp3-bytes"


def test_minimax_music_generation_accepts_hex_audio_and_defaults_instrumental(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")

    def _fake_post(_url, _headers, payload, _timeout):
        assert payload["output_format"] == "hex"
        assert payload["is_instrumental"] is True
        return {"data": {"audio": b"music-bytes".hex(), "status": 2}}

    result = generate_minimax_music(
        AssetGenerationRequest(
            provider="mmx_generation_api",
            modality="music",
            prompt="short instrumental reward jingle",
            output_dir=tmp_path,
            filename="jingle.mp3",
        ),
        http_post=_fake_post,
    )

    assert result.status == "completed"
    assert Path(result.artifact_paths[0]).read_bytes() == b"music-bytes"


def test_gcp_tts_generation_writes_binary_asset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_OAUTH_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WORKFLOW_GCP_QUOTA_PROJECT", "test-project")

    def _fake_post(_url, headers, _payload, _timeout):
        assert headers["X-Goog-User-Project"] == "test-project"
        return {"audioContent": base64.b64encode(b"mp3-bytes").decode("ascii")}

    result = generate_gcp_tts(
        AssetGenerationRequest(
            provider="gcp_tts_api",
            modality="audio",
            prompt="probe",
            output_dir=tmp_path,
            filename="voice.mp3",
        ),
        http_post=_fake_post,
    )

    assert result.status == "completed"
    assert result.provider == "gcp_tts_api"
    assert Path(result.artifact_paths[0]).read_bytes() == b"mp3-bytes"


def test_vertex_imagen_generation_writes_binary_asset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_OAUTH_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WORKFLOW_GCP_QUOTA_PROJECT", "test-project")

    def _fake_post(url, headers, payload, _timeout):
        assert "publishers/google/models/imagen-4.0-generate-001:predict" in url
        assert headers["X-Goog-User-Project"] == "test-project"
        assert payload["instances"][0]["prompt"] == "icon"
        return {"predictions": [{"bytesBase64Encoded": base64.b64encode(b"png-bytes").decode("ascii")}]}

    result = generate_vertex_imagen(
        AssetGenerationRequest(
            provider="vertex_generation_api",
            modality="image",
            prompt="icon",
            output_dir=tmp_path,
            filename="vertex.png",
        ),
        http_post=_fake_post,
    )

    assert result.status == "completed"
    assert result.provider == "vertex_generation_api"
    assert Path(result.artifact_paths[0]).read_bytes() == b"png-bytes"


def test_vertex_imagen_converts_global_location_to_regional_endpoint(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_OAUTH_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WORKFLOW_GCP_QUOTA_PROJECT", "test-project")
    monkeypatch.setenv("WORKFLOW_VERTEX_LOCATION", "global")

    def _fake_post(url, _headers, _payload, _timeout):
        assert url.startswith("https://us-central1-aiplatform.googleapis.com/v1/")
        assert "/locations/us-central1/" in url
        return {"predictions": [{"bytesBase64Encoded": base64.b64encode(b"png-bytes").decode("ascii")}]}

    result = generate_vertex_imagen(
        AssetGenerationRequest(
            provider="vertex_generation_api",
            modality="image",
            prompt="icon",
            output_dir=tmp_path,
            filename="vertex.png",
        ),
        http_post=_fake_post,
    )

    assert result.status == "completed"
    assert result.metadata["requested_location"] == "global"
    assert result.metadata["location"] == "us-central1"


def test_vertex_gemini_visual_review_writes_review_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_OAUTH_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WORKFLOW_GCP_QUOTA_PROJECT", "test-project")
    image = tmp_path / "probe.png"
    image.write_bytes(b"png-bytes")

    def _fake_post(url, _headers, payload, _timeout):
        assert "generateContent" in url
        assert payload["contents"][0]["parts"][1]["inlineData"]["mimeType"] == "image/png"
        return {"candidates": [{"content": {"parts": [{"text": "Visual review: polished enough."}]}}]}

    result = generate_vertex_gemini_visual_review(
        AssetGenerationRequest(
            provider="vertex_generation_api",
            modality="vision_review",
            prompt="review",
            output_dir=tmp_path,
            filename="review.json",
            metadata={"image_path": image.as_posix()},
        ),
        http_post=_fake_post,
    )

    assert result.status == "completed"
    payload = json.loads(Path(result.artifact_paths[0]).read_text(encoding="utf-8"))
    assert "Visual review" in payload["review_text"]


def test_vertex_gemini_visual_review_uses_global_endpoint(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_OAUTH_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WORKFLOW_GCP_QUOTA_PROJECT", "test-project")
    monkeypatch.setenv("WORKFLOW_VERTEX_LOCATION", "global")
    image = tmp_path / "probe.png"
    image.write_bytes(b"png-bytes")

    def _fake_post(url, _headers, _payload, _timeout):
        assert url.startswith("https://aiplatform.googleapis.com/v1/projects/")
        assert "/locations/global/" in url
        return {"candidates": [{"content": {"parts": [{"text": "Global visual review ok."}]}}]}

    result = generate_vertex_gemini_visual_review(
        AssetGenerationRequest(
            provider="vertex_generation_api",
            modality="vision_review",
            prompt="review",
            output_dir=tmp_path,
            filename="review.json",
            metadata={"image_path": image.as_posix()},
        ),
        http_post=_fake_post,
    )

    assert result.status == "completed"


def test_gcloud_access_token_resolves_windows_cmd_shim(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_OAUTH_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("WORKFLOW_GCP_AUTH_MODE", raising=False)
    monkeypatch.setattr(asset_generation_module.shutil, "which", lambda name: r"C:\gcloud.CMD" if name == "gcloud" else None)

    def _fake_run(args, **_kwargs):
        assert args[0] == r"C:\gcloud.CMD"
        assert args[1:3] == ["auth", "print-access-token"]
        return SimpleNamespace(returncode=0, stdout="adc-token\n", stderr="")

    monkeypatch.setattr(asset_generation_module.subprocess, "run", _fake_run)

    assert asset_generation_module._gcloud_access_token() == "adc-token"


def test_gcloud_access_token_can_prefer_adc_mode(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_OAUTH_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("WORKFLOW_GCP_AUTH_MODE", "adc")
    monkeypatch.setattr(asset_generation_module.shutil, "which", lambda name: r"C:\gcloud.CMD" if name == "gcloud" else None)

    calls: list[list[str]] = []

    def _fake_run(args, **_kwargs):
        calls.append(list(args))
        return SimpleNamespace(returncode=0, stdout="adc-token\n", stderr="")

    monkeypatch.setattr(asset_generation_module.subprocess, "run", _fake_run)

    assert asset_generation_module._gcloud_access_token() == "adc-token"
    assert calls[0][1:4] == ["auth", "application-default", "print-access-token"]


def test_google_cloud_project_prefers_gcloud_config_over_ambient_project_env(monkeypatch) -> None:
    monkeypatch.delenv("WORKFLOW_GCP_QUOTA_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_QUOTA_PROJECT", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "wrong-env-project")
    monkeypatch.setattr(asset_generation_module.shutil, "which", lambda name: r"C:\gcloud.CMD" if name == "gcloud" else None)

    def _fake_run(args, **_kwargs):
        assert args[:3] == [r"C:\gcloud.CMD", "config", "get-value"]
        return SimpleNamespace(returncode=0, stdout="configured-project\n", stderr="")

    monkeypatch.setattr(asset_generation_module.subprocess, "run", _fake_run)

    assert asset_generation_module._google_cloud_project() == "configured-project"


def test_capability_probe_asset_provider_requires_binary_live_proof(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")

    def _fake_generate(request, **_kwargs):
        from packages.contributions.asset_factory.asset_generation import AssetGenerationResult

        output = Path(request.output_dir) / request.filename
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"asset")
        return AssetGenerationResult(
            provider="mmx_generation_api",
            modality="image",
            status="completed",
            artifact_paths=[output.as_posix()],
            mime_type="image/png",
            model="image-01",
        )

    monkeypatch.setattr(capability_probe, "generate_minimax_image", _fake_generate)

    result = capability_probe.probe_provider(
        provider="mmx_image",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "evidence",
        require_live=True,
    )

    assert result.status == "verified_ready"
    assert result.metadata["proof"]["binary_artifact_required"] is True
    assert Path(result.evidence_path).exists()
