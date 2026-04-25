from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.operator_cli.main import app
from packages.core_domain import capability_probe
from packages.core_domain.capability_probe import probe_provider, run_capability_probes
from packages.core_domain.db import migrate
from packages.core_domain.repositories import CapabilityProbeResultRepository
from packages.core_domain.services import OrchestratorService
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
            stdout="probe-ok",
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

    def normalized_name(self) -> str:
        return "opencode"

    def launch(self, packet):
        artifact_path = Path(packet.expected_artifacts[0])
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            json.dumps({"status": "ok", "probe": "executed", "adapter": "opencode"}),
            encoding="utf-8",
        )
        now = utc_now()
        return ExecutionResult(
            runtime_task_id=packet.runtime_task_id,
            return_code=0,
            stdout='{"status":"ok","probe":"executed","adapter":"opencode"}',
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
    assert result.failure_class == "probe_failed"


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


def test_capability_probe_accepts_minimal_live_proof_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(capability_probe, "_adapter_for_provider", lambda provider: _MinimalLiveProofArtifactAdapter())

    result = probe_provider(
        provider="opencode",
        workspace_root=tmp_path,
        evidence_dir=tmp_path / "evidence",
        require_live=True,
    )

    assert result.status == "verified_ready"
    assert result.failure_class is None
