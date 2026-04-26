from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from apps.operator_cli.main import app
from apps.orchestrator_api.main import create_app
from packages.core_domain import capability_probe
from packages.core_domain.capability_probe import probe_provider, run_capability_probes
from packages.core_domain.db import migrate
from packages.core_domain.repositories import CapabilityProbeResultRepository
from packages.core_domain.services import OrchestratorService
from packages.contracts import CapabilityInvocationRecord, CapabilityProbeResult
from packages.worker_adapters.base import ExecutionResult, utc_now


class _ProbeTimeoutAdapter:
    timeout_seconds = 180

    def __init__(self) -> None:
        self.observed_timeout_seconds: int | None = None

    def normalized_name(self) -> str:
        return "probe_timeout_adapter"

    def launch(self, packet):
        self.observed_timeout_seconds = self.timeout_seconds
        now = utc_now()
        return ExecutionResult(
            runtime_task_id=packet.runtime_task_id,
            return_code=0,
            stdout="workflow-shell-probe",
            stderr="",
            started_at=now,
            finished_at=now,
            duration_ms=0,
            artifact_paths=[],
            adapter_name=self.normalized_name(),
        )


class _GenericArtifactAdapter:
    timeout_seconds = 180

    def normalized_name(self) -> str:
        return "opencode"

    def launch(self, packet):
        artifact_path = Path(packet.expected_artifacts[0])
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text("How can I help you with your workflow today?\n", encoding="utf-8")
        now = utc_now()
        return ExecutionResult(
            runtime_task_id=packet.runtime_task_id,
            return_code=0,
            stdout="How can I help you with your workflow today?\n",
            stderr="",
            started_at=now,
            finished_at=now,
            duration_ms=0,
            artifact_paths=[artifact_path.as_posix()],
            adapter_name=self.normalized_name(),
        )


class _LiveProofArtifactAdapter:
    timeout_seconds = 180

    def __init__(self, adapter_name: str = "opencode") -> None:
        self.adapter_name = adapter_name

    def normalized_name(self) -> str:
        return self.adapter_name

    def launch(self, packet):
        artifact_path = Path(packet.expected_artifacts[0])
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            json.dumps(
                {
                    "status": "ok",
                    "probe": "executed",
                    "adapter": self.normalized_name(),
                    "live_backend": True,
                    "no_fallback": True,
                }
            ),
            encoding="utf-8",
        )
        now = utc_now()
        return ExecutionResult(
            runtime_task_id=packet.runtime_task_id,
            return_code=0,
            stdout=json.dumps({"status": "ok", "probe": "executed", "adapter": self.normalized_name()}),
            stderr="",
            started_at=now,
            finished_at=now,
            duration_ms=0,
            artifact_paths=[artifact_path.as_posix()],
            adapter_name=self.normalized_name(),
        )


class _MinimalLiveProofArtifactAdapter:
    timeout_seconds = 180

    def normalized_name(self) -> str:
        return "opencode"

    def launch(self, packet):
        artifact_path = Path(packet.expected_artifacts[0])
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text("ok\n", encoding="utf-8")
        now = utc_now()
        return ExecutionResult(
            runtime_task_id=packet.runtime_task_id,
            return_code=0,
            stdout='{"type":"text","text":"ok"}',
            stderr="",
            started_at=now,
            finished_at=now,
            duration_ms=0,
            artifact_paths=[artifact_path.as_posix()],
            adapter_name=self.normalized_name(),
        )


class _TemplateOnlyArtifactAdapter:
    timeout_seconds = 180

    def normalized_name(self) -> str:
        return "opencode"

    def launch(self, packet):
        artifact_path = Path(packet.expected_artifacts[0])
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text("preset: capability_probe\nadapter: opencode\n", encoding="utf-8")
        now = utc_now()
        return ExecutionResult(
            runtime_task_id=packet.runtime_task_id,
            return_code=0,
            stdout="",
            stderr="",
            started_at=now,
            finished_at=now,
            duration_ms=0,
            artifact_paths=[artifact_path.as_posix()],
            adapter_name=self.normalized_name(),
        )


def test_capability_probe_records_live_shell_result(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)

    payload = run_capability_probes(
        provider="shell",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "evidence",
        require_live=True,
        db_path=db_path,
    )

    assert payload["overall_status"] == "passed"
    latest = CapabilityProbeResultRepository(db_path).latest_by_provider()
    assert latest["shell"].status == "verified_ready"
    assert latest["shell"].live_probe is True


def test_capability_health_surfaces_probe_evidence(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    run_capability_probes(
        provider="shell",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "evidence",
        require_live=True,
        db_path=db_path,
    )

    health = OrchestratorService(db_path, workspace_root=tmp_path).list_capability_health()
    shell_health = next(item for item in health if item["descriptor"].get("adapter_name") == "shell")

    assert shell_health["probe_evidence"]["status"] == "verified_ready"
    assert shell_health["readiness_state"] == "verified_ready"


def test_capability_health_verified_only_filters_unverified_descriptors(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    run_capability_probes(
        provider="shell",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "evidence",
        require_live=True,
        db_path=db_path,
    )

    service = OrchestratorService(db_path, workspace_root=tmp_path)
    full_health = service.list_capability_health()
    verified_health = service.list_capability_health(verified_only=True)

    assert len(verified_health) < len(full_health)
    assert verified_health
    assert all(
        (
            item.get("probe_evidence", {}).get("status") == "verified_ready"
            and item.get("probe_evidence", {}).get("live_probe") is True
        )
        or (
            item.get("recent_call_summary", {}).get("recent_success_count", 0) > 0
            and item.get("recent_call_summary", {}).get("verified_by_runtime") is True
        )
        for item in verified_health
    )


def test_capability_health_verified_only_ignores_failed_runtime_attempts(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    service = OrchestratorService(db_path, workspace_root=tmp_path)
    target = next(item for item in service.list_capability_descriptors() if item.get("enabled", True))
    service.capability_invocation_repo.create(
        CapabilityInvocationRecord(
            capability_id=target["capability_id"],
            provider_kind=target["provider_kind"],
            status="failed",
            return_code=1,
            adapter_name=target.get("adapter_name"),
            failure_class="execution_failed",
        )
    )

    verified_health = OrchestratorService(db_path, workspace_root=tmp_path).list_capability_health(verified_only=True)

    assert all(item["descriptor"]["capability_id"] != target["capability_id"] for item in verified_health)


def test_capability_health_verified_only_uses_provider_alias_live_proof(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    CapabilityProbeResultRepository(db_path).create(
        CapabilityProbeResult(
            provider="mmx_image",
            adapter_name="mmx_generation_api",
            status="verified_ready",
            live_probe=True,
            auth_source="MINIMAX_API_KEY",
            evidence_path=str(tmp_path / "evidence" / "mmx_image_probe.json"),
            created_at=utc_now(),
        )
    )

    verified_health = OrchestratorService(db_path, workspace_root=tmp_path).list_capability_health(verified_only=True)
    mmx_health = next(item for item in verified_health if item["descriptor"]["capability_id"] == "asset_generator:mmx_generation_api")

    assert mmx_health["readiness_state"] == "verified_ready"
    assert mmx_health["verified_by_live_probe"] is True
    assert "mmx_image" in mmx_health["provider_route_stats"]


def test_capability_route_stats_include_live_probe_ledger(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    run_capability_probes(
        provider="shell",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "evidence",
        require_live=True,
        db_path=db_path,
    )

    stats = OrchestratorService(db_path, workspace_root=tmp_path).get_capability_route_stats(days=30)

    assert stats["schema_version"] == "m80_provider_route_stats_v1"
    assert stats["providers"]["shell"]["verified_ready"] is True
    assert stats["providers"]["shell"]["probe_summary"]["verified_count"] == 1


def test_cli_capability_route_stats_and_verified_only_health(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    probe_result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--workspace-root",
            str(tmp_path),
            "capability",
            "probe",
            "--provider",
            "shell",
            "--require-live",
            "--evidence-dir",
            str(tmp_path / "evidence"),
        ],
    )
    assert probe_result.exit_code == 0

    stats_result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--workspace-root",
            str(tmp_path),
            "capability",
            "routes",
            "stats",
            "--days",
            "30",
        ],
    )
    health_result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(db_path),
            "--workspace-root",
            str(tmp_path),
            "capability",
            "health",
            "--verified-only",
        ],
    )

    assert stats_result.exit_code == 0
    assert health_result.exit_code == 0
    assert json.loads(stats_result.stdout)["providers"]["shell"]["verified_ready"] is True
    health_payload = json.loads(health_result.stdout)
    assert health_payload
    assert all(item["readiness_state"] in {"verified_ready", "recently_successful"} for item in health_payload)


def test_api_capability_health_and_route_stats_support_m80_fields(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    run_capability_probes(
        provider="shell",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "evidence",
        require_live=True,
        db_path=db_path,
    )
    client = TestClient(create_app(db_path=db_path, workspace_root=tmp_path))

    health_response = client.get("/capability-health?verified_only=true")
    stats_response = client.get("/capability-routes/stats?days=30")

    assert health_response.status_code == 200
    assert stats_response.status_code == 200
    assert health_response.json()
    assert stats_response.json()["providers"]["shell"]["verified_ready"] is True


def test_cli_capability_probe_blocks_when_required_provider_is_unavailable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("WORKFLOW_VERTEX_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCLOUD_PROJECT", raising=False)
    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "capability",
            "probe",
            "--provider",
            "vertex",
            "--require-live",
            "--evidence-dir",
            str(tmp_path / "evidence"),
        ],
    )

    payload = json.loads(result.stdout)
    assert result.exit_code == 1
    assert payload["overall_status"] == "blocked"
    assert payload["results"][0]["status"] == "blocked"


def test_cli_capability_control_plane_reports_write_set_and_live_gate(tmp_path: Path) -> None:
    allowed = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "capability",
            "control-plane",
            "--provider",
            "shell",
            "--mutation-mode",
            "artifact_only",
            "--no-require-live",
        ],
    )
    assert allowed.exit_code == 0
    allowed_payload = json.loads(allowed.stdout)
    assert allowed_payload["decision"] == "allowed"
    assert allowed_payload["provider_key"] == "shell"
    assert allowed_payload["operator_receipt_status"] == "not_required"

    blocked = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "capability",
            "control-plane",
            "--provider",
            "shell",
            "--mutation-mode",
            "patch_apply",
            "--no-require-live",
        ],
    )
    assert blocked.exit_code == 1
    blocked_payload = json.loads(blocked.stdout)
    assert blocked_payload["decision"] == "blocked"
    assert "patch_apply_requires_write_set" in blocked_payload["reasons"]


def test_cli_capability_provider_contracts_explain_vertex_and_gcloud(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "--db-path",
            str(tmp_path / "workflow.db"),
            "--workspace-root",
            str(tmp_path),
            "capability",
            "provider-contracts",
            "--provider",
            "vertex",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["provider"] == "vertex"
    assert payload["adapter_name"] == "vertex_multimodal"
    assert payload["cli_dependency"] == "gcloud"
    assert any("Gemini CLI is not currently an adapter" in note for note in payload["notes"])
    assert any("not an independent worker adapter" in note for note in payload["notes"])


def test_capability_probe_sets_adapter_timeout_below_outer_watchdog(tmp_path: Path, monkeypatch) -> None:
    adapter = _ProbeTimeoutAdapter()
    monkeypatch.setenv("WORKFLOW_CAPABILITY_PROBE_TIMEOUT_SECONDS", "30")
    monkeypatch.setattr(capability_probe, "_adapter_for_provider", lambda provider: adapter)

    result = probe_provider(
        provider="shell",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "evidence",
        require_live=True,
    )

    assert result.status == "verified_ready"
    assert adapter.observed_timeout_seconds == 25


def test_capability_probe_rejects_generic_artifact_false_positive(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(capability_probe, "_adapter_for_provider", lambda provider: _GenericArtifactAdapter())

    result = probe_provider(
        provider="opencode",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "evidence",
        require_live=True,
    )

    assert result.status == "blocked"
    assert result.failure_class == "generic_assistant_evidence"


def test_capability_probe_rejects_simulated_or_dry_run_evidence(tmp_path: Path, monkeypatch) -> None:
    class _SimulatedArtifactAdapter(_GenericArtifactAdapter):
        def launch(self, packet):
            artifact_path = Path(packet.expected_artifacts[0])
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text("Simulated Probe Action: no actual API call was forced.\n", encoding="utf-8")
            now = utc_now()
            return ExecutionResult(
                runtime_task_id=packet.runtime_task_id,
                return_code=0,
                stdout="Simulated Probe Action: no actual API call was forced.\n",
                stderr="",
                started_at=now,
                finished_at=now,
                duration_ms=0,
                artifact_paths=[artifact_path.as_posix()],
                adapter_name=self.normalized_name(),
            )

    monkeypatch.setattr(capability_probe, "_adapter_for_provider", lambda provider: _SimulatedArtifactAdapter())

    result = probe_provider(
        provider="vertex",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "evidence",
        require_live=True,
    )

    assert result.status == "blocked"
    assert result.failure_class == "simulated_or_dry_run_evidence"


def test_capability_probe_accepts_explicit_live_proof_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(capability_probe, "_adapter_for_provider", lambda provider: _LiveProofArtifactAdapter())

    result = probe_provider(
        provider="opencode",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "evidence",
        require_live=True,
    )

    assert result.status == "verified_ready"
    assert result.failure_class is None


def test_capability_probe_accepts_explicit_live_proof_for_non_coding_provider(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(capability_probe, "_adapter_for_provider", lambda provider: _LiveProofArtifactAdapter("vertex_multimodal"))

    result = probe_provider(
        provider="vertex",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "evidence",
        require_live=True,
    )

    assert result.status == "verified_ready"
    assert result.failure_class is None


def test_capability_probe_extracts_live_proof_from_markdown_fence(tmp_path: Path, monkeypatch) -> None:
    class _FencedLiveProofArtifactAdapter(_GenericArtifactAdapter):
        def normalized_name(self) -> str:
            return "mmx_multimodal"

        def launch(self, packet):
            artifact_path = Path(packet.expected_artifacts[0])
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                '```json\n{"status":"ok","probe":"executed","provider":"mmx","live_backend":true,"no_fallback":true}\n```\n',
                encoding="utf-8",
            )
            now = utc_now()
            return ExecutionResult(
                runtime_task_id=packet.runtime_task_id,
                return_code=0,
                stdout="",
                stderr="",
                started_at=now,
                finished_at=now,
                duration_ms=0,
                artifact_paths=[artifact_path.as_posix()],
                adapter_name=self.normalized_name(),
            )

    monkeypatch.setattr(capability_probe, "_adapter_for_provider", lambda provider: _FencedLiveProofArtifactAdapter())

    result = probe_provider(
        provider="mmx",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "evidence",
        require_live=True,
    )

    assert result.status == "verified_ready"
    assert result.failure_class is None


def test_capability_probe_rejects_minimal_ok_as_insufficient_live_proof(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(capability_probe, "_adapter_for_provider", lambda provider: _MinimalLiveProofArtifactAdapter())

    result = probe_provider(
        provider="opencode",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "evidence",
        require_live=True,
    )

    assert result.status == "blocked"
    assert result.failure_class == "missing_live_proof"


def test_capability_probe_rejects_template_only_evidence(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(capability_probe, "_adapter_for_provider", lambda provider: _TemplateOnlyArtifactAdapter())

    result = probe_provider(
        provider="opencode",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "evidence",
        require_live=True,
    )

    assert result.status == "blocked"
    assert result.failure_class == "missing_live_proof"


def test_vertex_review_probe_png_is_valid_enough_for_multimodal_upload() -> None:
    data = capability_probe._tiny_png_bytes()

    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"IHDR" in data
    assert b"IDAT" in data
    assert b"IEND" in data
