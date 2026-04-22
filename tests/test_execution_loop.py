from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from packages.contracts import (
    MutationMode,
    RunEventType,
    RunSnapshotStage,
    SimulationRecordSource,
    RuntimeAttemptStatus,
    RuntimeClaim,
    RuntimeClaimStatus,
    RuntimeGraphStep,
    RuntimeStateRef,
    TaskKind,
    TaskPacket,
    WorkerLease,
    WorkerLeaseStatus,
)
from packages.core_domain.auto_review import AutoReviewV0
from packages.core_domain.capability_plane import CapabilityPlane
from packages.core_domain.db import migrate, unit_of_work
from packages.core_domain.domain_packs import DomainPackRegistry, load_seed_domain_packs
from packages.core_domain.errors import (
    BudgetExhaustedError,
    CapabilityAdapterNotFoundError,
    InvalidStateTransitionError,
    RepoMutationScopeError,
    RepairActionNotAvailableError,
    RuntimeClaimConflictError,
    WorkflowError,
)
from packages.core_domain.evidence_builder import EvidenceBuilder
from packages.core_domain.observability import InMemoryTraceExporter, TraceExporter, TraceRecord
from packages.core_domain.repositories import PresetRepository
from packages.core_domain.services import OrchestratorService
from packages.runtime_langgraph.durable_pilot import DurableRuntimePilot, LangGraphDurableRuntimePilot
from packages.runtime_langgraph.gateway import OpenAIRuntimeGateway
from packages.worker_adapters.base import ExecutionResult, resolve_artifact_paths, utc_now
from packages.worker_adapters.langchain_agent_adapter import AgentExecutionResponse, LangChainAgentAdapter
from packages.worker_adapters.noop_adapter import NoopAdapter
from packages.worker_adapters.opencode_adapter import OpenCodeAdapter
from packages.worker_adapters.opencode_session_adapter import OpenCodeSessionAdapter
from packages.worker_adapters.router import WorkerRouter
from packages.worker_adapters.shell_adapter import ShellAdapter


class _FakeGatewayResponse:
    id = "resp_gateway"
    output_text = "Outcome: produce a feature artifact Risk: shell command may drift Check: inspect generated markdown"


class _FakeGatewayResponses:
    def __init__(self):
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeGatewayResponse()


class _FakeGatewayClient:
    def __init__(self):
        self.responses = _FakeGatewayResponses()


def _fake_opencode_runner(command, cwd, env, capture_output, text, check, timeout):
    prompt = command[2]
    content_match = re.search(r"<<<WORKFLOW_FILE>>>\n(.*?)<<<END_WORKFLOW_FILE>>>", prompt, re.DOTALL)
    assert content_match is not None
    assert timeout == 180
    return subprocess.CompletedProcess(
        command,
        0,
        stdout=json.dumps({"type": "text", "part": {"text": content_match.group(1)}}),
        stderr="",
    )


def _fake_patch_runner(command, cwd, env, capture_output, text, check, timeout):
    write_set = json.loads(env.get("WORKFLOW_MUTATION_WRITE_SET", "[]"))
    assert write_set
    target = write_set[0].replace("\\", "/")
    patch_text = (
        f"--- {target}\n"
        f"+++ {target}\n"
        "@@ -1 +1 @@\n"
        "-before\n"
        "+after\n"
    )
    return subprocess.CompletedProcess(
        command,
        0,
        stdout=json.dumps({"type": "text", "part": {"text": patch_text}}),
        stderr="",
    )


def _fake_timeout_runner(command, cwd, env, capture_output, text, check, timeout):
    raise subprocess.TimeoutExpired(command, timeout, output="partial stdout", stderr="partial stderr")


def _fake_session_runner(command, cwd, env, capture_output, text, check, timeout):
    if len(command) >= 2 and command[1] == "export":
        return subprocess.CompletedProcess(command, 0, stdout='{"session_id":"sess_exec_123"}', stderr="")
    content = "# Sessionful external lane\n\nshared session artifact\n"
    stdout = "\n".join(
        [
            json.dumps({"type": "session", "session_id": "sess_exec_123", "share_url": "https://example.com/session/exec-123"}),
            json.dumps({"type": "trace", "trace_id": "trace_exec_123"}),
            json.dumps({"type": "text", "part": {"text": content}}),
        ]
    )
    return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")


def _fake_agent_runner(packet: TaskPacket, manifest) -> AgentExecutionResponse:
    projected = [item.tool_name for item in manifest.tools] if manifest is not None else []
    content = (
        "# Research Spike\n\n"
        f"goal: {packet.env.get('WORKFLOW_RUN_GOAL')}\n"
        f"execution_lane: {packet.env.get('WORKFLOW_EXECUTION_LANE')}\n"
        f"projected_tools: {', '.join(projected)}\n"
    )
    return AgentExecutionResponse(
        content=content,
        tool_call_ids=["toolcall_fake_agent"],
        metadata={"agent_runner": "fake"},
    )


class _RecordingDurablePilot(DurableRuntimePilot):
    def __init__(self) -> None:
        self.start_calls: list[tuple[str, str]] = []
        self.checkpoint_calls: list[tuple[dict[str, str], str]] = []
        self.review_calls: list[tuple[dict[str, str], str]] = []

    def describe(self) -> dict[str, object]:
        return {"provider": "recording", "enabled": True, "mode": "test"}

    def start(self, run_id: str, runtime_task_id: str) -> dict[str, str]:
        self.start_calls.append((run_id, runtime_task_id))
        return {
            "thread_id": f"thread_{run_id[-6:]}",
            "checkpoint_id": f"checkpoint_{runtime_task_id[-6:]}",
            "assistant_id": f"assistant_{run_id[-6:]}",
        }

    def checkpoint(self, refs: dict[str, str], *, reason: str) -> dict[str, str]:
        self.checkpoint_calls.append((dict(refs), reason))
        return {**refs, "checkpoint_id": f"checkpoint_{reason}"}

    def review_decision(self, refs: dict[str, str], *, decision: str) -> dict[str, str]:
        self.review_calls.append((dict(refs), decision))
        return {**refs, "checkpoint_id": f"checkpoint_review_{decision}"}


class _ExplodingTraceExporter(TraceExporter):
    def describe(self) -> dict[str, object]:
        return {"provider": "exploding", "enabled": True}

    def export(self, record: TraceRecord) -> str | None:
        raise RuntimeError(f"boom:{record.name}")


class _DelayedShellAdapter(ShellAdapter):
    def __init__(self, delay_seconds: float = 0.2):
        super().__init__()
        self.delay_seconds = delay_seconds
        self.started_packets: list[tuple[str, datetime]] = []

    def launch(self, packet: TaskPacket) -> ExecutionResult:
        started_at = utc_now()
        self.started_packets.append((packet.runtime_task_id, started_at))
        time.sleep(self.delay_seconds)
        artifact_paths = resolve_artifact_paths(
            packet,
            create_missing=True,
            placeholder=f"parallel batch artifact for {packet.runtime_task_id}\n",
        )
        finished_at = utc_now()
        return ExecutionResult(
            runtime_task_id=packet.runtime_task_id,
            return_code=0,
            stdout="parallel batch ok",
            stderr="",
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=max(int((finished_at - started_at).total_seconds() * 1000), 0),
            artifact_paths=artifact_paths,
            adapter_name=self.normalized_name(),
        )


def test_execute_run_success_path(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Build one artifact", "feature_delivery")
    service.prepare_run(run.run_id)
    bundle = service.execute_run(run.run_id)

    assert bundle.run.status == "completed"
    assert bundle.execution_result.return_code == 0
    assert bundle.evidence.artifact_refs
    artifact_ref = bundle.evidence.artifact_refs[0]
    assert artifact_ref.sha256
    assert artifact_ref.mtime > 0
    assert artifact_ref.size_bytes > 0
    assert bundle.review_verdict.decision == "pass"


def test_openai_runtime_gateway_projects_brief_into_artifact_and_status(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    fake_client = _FakeGatewayClient()
    service = OrchestratorService(
        db_path,
        runtime_gateway=OpenAIRuntimeGateway(client=fake_client, model="gpt-5.4-mini"),
    )

    run = service.create_run("Build one artifact with a brief", "feature_delivery")
    service.compile_run(run.run_id)
    bundle = service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)
    timeline = service.get_timeline(run.run_id)
    artifact_text = Path(bundle.evidence.artifact_refs[0].path).read_text(encoding="utf-8")

    assert detail["runtime_gateway"]["provider"] == "openai"
    assert detail["last_runtime_state"]["state_payload"]["runtime_brief"].startswith("Outcome:")
    assert detail["context_budget"]["status"] == "ok"
    assert detail["trace_context"]["run_id"] == run.run_id
    assert detail["trace_context"]["verdict_id"] == bundle.review_verdict.verdict_id
    assert "runtime_gateway: openai" in artifact_text
    assert "runtime_model: gpt-5.4-mini" in artifact_text
    assert "runtime_brief: Outcome:" in artifact_text
    assert timeline[-1].payload_json["trace_context"]["run_id"] == run.run_id
    assert timeline[-1].payload_json["trace_context"]["event_id"] == timeline[-1].event_id
    assert fake_client.responses.calls[0]["model"] == "gpt-5.4-mini"


def test_dashboard_snapshot_projects_recent_runs_and_focus_detail(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    first_run = service.create_run("First dashboard run", "feature_delivery")
    second_run = service.create_run("Second dashboard run", "research_spike")
    service.compile_run(first_run.run_id)

    snapshot = service.get_dashboard_snapshot(focus_run_id=first_run.run_id, limit=2)

    assert snapshot["runtime_gateway"]["provider"] == "null"
    assert snapshot["run_count"] == 2
    assert snapshot["selected_run_id"] == first_run.run_id
    assert snapshot["focus_detail"]["run"]["run_id"] == first_run.run_id
    assert snapshot["focus_operator_packet"]["run"]["run_id"] == first_run.run_id
    assert snapshot["runs"][0]["run_id"] == first_run.run_id
    assert snapshot["runs"][1]["run_id"] == second_run.run_id


def test_compile_run_creates_handoff_and_runtime_state(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Prepare compile snapshot", "feature_delivery")
    prepared = service.compile_run(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert prepared.run.status == "prepared"
    assert detail["handoffs"]
    assert detail["runtime_state_refs"]
    assert detail["next_action"] == "resume"
    assert detail["current_runtime_attempt"]["trigger"] == "compile"
    assert detail["runtime_attempt_projection"]["attempt_count"] == 1
    assert detail["runtime_attempt_projection"]["current_trigger"] == "compile"


def test_resume_run_updates_terminal_runtime_state(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Resume through prepared state", "feature_delivery")
    service.compile_run(run.run_id)
    bundle = service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert bundle.run.status == "completed"
    assert detail["runtime_state_refs"][0]["is_terminal"] is True
    assert detail["runtime_state_refs"][0]["graph_step"] == "completed"
    assert detail["current_runtime_attempt"] is None
    assert detail["latest_runtime_attempt"]["status"] == "completed"
    assert detail["latest_runtime_attempt"]["trigger"] == "resume"
    assert detail["runtime_attempt_projection"]["attempt_count"] == 2
    assert len(detail["runtime_attempt_projection"]["superseded_attempt_ids"]) == 1


def test_human_required_path_waits_for_manual_review(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Research runtime choices", "research_spike")
    service.compile_run(run.run_id)
    bundle = service.resume_run(run.run_id)
    waiting_detail = service.get_status_detail(run.run_id)

    assert bundle.run.status == "awaiting_review"
    assert bundle.review_verdict is None
    assert waiting_detail["effective_review_state"] == "human_pending"
    assert waiting_detail["latest_review_verdict"] is None
    assert waiting_detail["current_runtime_attempt"]["trigger"] == "resume"
    assert waiting_detail["current_runtime_attempt"]["status"] == "current"

    approved = service.approve_run_review(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert approved.run.status == "completed"
    assert detail["runtime_state_refs"][0]["is_terminal"] is True
    assert detail["runtime_state_refs"][0]["graph_step"] == "completed"
    assert detail["effective_review_state"] == "human_approved"
    assert detail["latest_review_verdict"]["reviewer_type"] == "human"
    assert detail["current_runtime_attempt"] is None
    assert detail["latest_runtime_attempt"]["status"] == "completed"


def test_recommended_policy_passes_without_human_gate(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Advisory delivery passes", "advisory_delivery")
    service.compile_run(run.run_id)
    bundle = service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert bundle.run.status == "completed"
    assert bundle.review_verdict is not None
    assert bundle.review_verdict.decision == "pass"
    assert detail["review_policy"] == "recommended"
    assert detail["effective_review_state"] == "auto_passed"
    assert detail["latest_review_verdict"]["reviewer_type"] == "auto"


def test_optional_policy_completes_with_advisory_review_state(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Optional delivery passes", "optional_delivery")
    service.compile_run(run.run_id)
    bundle = service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert bundle.run.status == "completed"
    assert bundle.review_verdict is not None
    assert bundle.review_verdict.decision == "pass"
    assert detail["review_policy"] == "optional"
    assert detail["effective_review_state"] == "advisory_passed"
    assert detail["failure_reason"] is None


def test_optional_policy_failure_stays_runtime_terminal_and_advisory(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Optional delivery fails", "optional_delivery")
    prepared = service.compile_run(run.run_id)
    with unit_of_work(db_path) as connection:
        connection.execute(
            "UPDATE task_packets SET command_json = ? WHERE runtime_task_id = ?",
            ('["python", "-c", "import sys; sys.exit(2)"]', prepared.task_packet.runtime_task_id),
        )

    bundle = service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert bundle.run.status == "failed"
    assert bundle.review_verdict is not None
    assert bundle.review_verdict.decision == "fail"
    assert detail["review_policy"] == "optional"
    assert detail["effective_review_state"] == "advisory_failed"
    assert detail["failure_reason"] == "runtime_return_code_non_zero"
    assert detail["latest_runtime_attempt"]["status"] == "failed"


def test_resume_run_auto_terminal_records_simulation_hook(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Auto terminal simulation hook", "feature_delivery")
    service.compile_run(run.run_id)
    bundle = service.resume_run(run.run_id)
    records = service.list_simulation_records(run.run_id)
    detail = service.get_status_detail(run.run_id)
    timeline = service.get_timeline(run.run_id)

    assert bundle.run.status == "completed"
    assert [record.recorded_from for record in records] == [SimulationRecordSource.lifecycle_terminal]
    assert detail["latest_simulation_record"]["recorded_from"] == "lifecycle_terminal"
    assert "simulation_recorded" in [event.event_type for event in timeline]


def test_recommended_policy_auto_fail_escalates_to_human_review(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Advisory delivery escalates", "advisory_delivery")
    prepared = service.compile_run(run.run_id)
    with unit_of_work(db_path) as connection:
        connection.execute(
            "UPDATE task_packets SET command_json = ? WHERE runtime_task_id = ?",
            ('["python", "-c", "import sys; sys.exit(2)"]', prepared.task_packet.runtime_task_id),
        )

    bundle = service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert bundle.run.status == "awaiting_review"
    assert bundle.review_verdict is not None
    assert bundle.review_verdict.decision == "fail"
    assert detail["review_policy"] == "recommended"
    assert detail["effective_review_state"] == "human_pending"
    assert detail["latest_review_verdict"]["reviewer_type"] == "auto"
    assert detail["latest_review_verdict"]["decision"] == "fail"
    assert detail["waiting_reason"] == "awaiting_human_review"
    assert detail["last_runtime_state"]["graph_step"] == "awaiting_review"


def test_mandatory_policy_always_waits_for_human_signoff(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Guarded delivery", "guarded_delivery")
    service.compile_run(run.run_id)
    bundle = service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert bundle.run.status == "awaiting_review"
    assert bundle.review_verdict is not None
    assert bundle.review_verdict.decision == "pass"
    assert detail["review_policy"] == "mandatory"
    assert detail["effective_review_state"] == "human_pending"
    assert detail["latest_review_verdict"]["reviewer_type"] == "auto"
    assert detail["latest_review_verdict"]["decision"] == "pass"
    assert detail["current_runtime_attempt"]["status"] == "current"

    records = service.list_simulation_records(run.run_id)
    assert [record.recorded_from for record in records] == [SimulationRecordSource.lifecycle_awaiting_review]

    reviewed = service.approve_run_review(run.run_id)
    records_after_approval = service.list_simulation_records(run.run_id)

    assert reviewed.run.status == "completed"
    assert [record.recorded_from for record in records_after_approval] == [
        SimulationRecordSource.lifecycle_awaiting_review,
        SimulationRecordSource.lifecycle_terminal,
    ]


def test_execute_run_rejects_invalid_transition_after_completion(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Complete then retry", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)

    with pytest.raises(InvalidStateTransitionError):
        service.resume_run(run.run_id)


def test_human_review_rejects_invalid_transition_before_review_state(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Approve too early", "feature_delivery")
    service.compile_run(run.run_id)

    with pytest.raises(InvalidStateTransitionError):
        service.approve_run_review(run.run_id)


def test_auto_review_fails_for_non_zero_return_code(tmp_path: Path) -> None:
    task_packet = TaskPacket(
        runtime_task_id="task_fail",
        run_id="run_fail",
        task_kind=TaskKind.shell_exec,
        command=["python", "-c", "import sys; sys.exit(2)"],
        working_directory=str(tmp_path),
    )
    result = ShellAdapter().launch(task_packet)
    evidence = EvidenceBuilder().build("run_fail", "task_fail", result)
    verdict = AutoReviewV0().review(evidence)

    assert result.return_code == 2
    assert evidence.result_envelope is not None
    assert evidence.result_envelope.verification.return_code == 2
    assert verdict.decision == "fail"


def test_shell_adapter_enforces_timeout_and_returns_stable_failure_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command, cwd, env, capture_output, text, check, timeout):
        assert timeout == 120
        raise subprocess.TimeoutExpired(command, timeout, output="partial stdout", stderr="partial stderr")

    monkeypatch.setattr(subprocess, "run", fake_run)
    task_packet = TaskPacket(
        runtime_task_id="task_timeout",
        run_id="run_timeout",
        task_kind=TaskKind.shell_exec,
        command=["python", "-c", "print('slow')"],
        working_directory=str(tmp_path),
    )

    result = ShellAdapter().launch(task_packet)

    assert result.return_code == 124
    assert "partial stdout" in result.stdout
    assert "partial stderr" in result.stderr
    assert "timed out after 120s" in result.stderr


def test_shell_adapter_uses_allowlisted_environment_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured_env: dict[str, str] = {}

    def fake_run(command, cwd, env, capture_output, text, check, timeout):
        captured_env.update(env)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setenv("SECRET_SHOULD_NOT_PASS", "nope")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    task_packet = TaskPacket(
        runtime_task_id="task_env",
        run_id="run_env",
        task_kind=TaskKind.shell_exec,
        command=["python", "-c", "print('env')"],
        working_directory=str(tmp_path),
        env={"WORKFLOW_EXPLICIT_VALUE": "yes"},
    )

    ShellAdapter().launch(task_packet)

    assert captured_env["WORKFLOW_EXPLICIT_VALUE"] == "yes"
    assert captured_env["OPENAI_API_KEY"] == "test-key"
    assert "SECRET_SHOULD_NOT_PASS" not in captured_env


def test_compile_run_uses_current_interpreter_for_generated_command(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Portable compile command", "feature_delivery")
    prepared = service.compile_run(run.run_id)

    assert prepared.task_packet.command[0] == sys.executable


def test_worker_router_uses_noop_adapter_for_noop_task(tmp_path: Path) -> None:
    packet = TaskPacket(
        runtime_task_id="task_noop",
        run_id="run_noop",
        task_kind=TaskKind.noop,
        command=[],
        working_directory=str(tmp_path),
        expected_artifacts=["state/artifacts/noop.md"],
    )
    router = WorkerRouter([ShellAdapter(), NoopAdapter()])

    adapter = router.route(packet)
    result = adapter.launch(packet)

    assert adapter.__class__.__name__ == "NoopAdapter"
    assert result.adapter_name == "noop"
    assert result.return_code == 0
    assert result.artifact_paths


def test_worker_router_exposes_capability_registry_routes() -> None:
    router = WorkerRouter()

    routes = router.routes()

    assert routes == [
        {"capability": "noop", "adapter_name": "noop", "adapter_class": "NoopAdapter"},
        {"capability": "shell_exec", "adapter_name": "shell", "adapter_class": "ShellAdapter"},
        {"capability": "shell_exec", "adapter_name": "opencode", "adapter_class": "OpenCodeAdapter"},
    ]


def test_compile_run_rejects_unknown_adapter_for_capability(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Compile with invalid adapter", "feature_delivery")

    with pytest.raises(CapabilityAdapterNotFoundError):
        service.compile_run(run.run_id, adapter_name="missing_adapter")


def test_service_can_execute_noop_task_kind_for_allowed_preset(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Noop service execution", "research_spike")
    prepared = service.compile_run(run.run_id, task_kind="noop")
    bundle = service.resume_run(run.run_id)
    evidence = service.get_task_evidence(prepared.task_packet.runtime_task_id)

    assert prepared.task_packet.task_kind == "noop"
    assert prepared.task_packet.command == []
    assert bundle.run.status == "awaiting_review"
    assert evidence.raw_execution["adapter_name"] == "noop"
    assert evidence.artifact_refs


def test_compile_run_projects_domain_pack_and_capability_resolution(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Compile with software delivery domain pack", "feature_delivery")
    prepared = service.compile_run(run.run_id)
    detail = service.get_status_detail(run.run_id)
    timeline_types = [event.event_type for event in service.get_timeline(run.run_id)]

    assert prepared.domain_pack is not None
    assert prepared.domain_pack.domain_pack_id == "software_delivery_pack"
    assert prepared.domain_pack.matched_preset_id == "feature_delivery"
    assert prepared.domain_pack.compile_projection.artifact_label == "software_delivery"
    assert prepared.domain_pack.runtime_projection.operator_label == "software-delivery"
    assert prepared.capability_route is not None
    assert prepared.capability_route.adapter_name == "shell"
    assert prepared.task_packet.env["WORKFLOW_DOMAIN_PACK_ID"] == "software_delivery_pack"
    assert "WORKFLOW_DOMAIN_PACK_RESOLUTION" in prepared.task_packet.env
    assert prepared.task_packet.env["WORKFLOW_CAPABILITY_ADAPTER"] == "shell"
    assert detail["domain_pack"]["domain_pack_id"] == "software_delivery_pack"
    assert detail["domain_pack"]["matched_preset_id"] == "feature_delivery"
    assert detail["domain_pack"]["runtime_projection"]["operator_label"] == "software-delivery"
    assert detail["capability_resolution"]["adapter_name"] == "shell"
    assert "domain_pack_selected" in timeline_types


def test_compile_run_can_pin_opencode_adapter(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Compile through opencode", "feature_delivery")
    prepared = service.compile_run(run.run_id, adapter_name="opencode")
    detail = service.get_status_detail(run.run_id)

    assert prepared.capability_route is not None
    assert prepared.capability_route.adapter_name == "opencode"
    assert prepared.task_packet.env["WORKFLOW_CAPABILITY_ADAPTER"] == "opencode"
    assert detail["capability_resolution"]["adapter_name"] == "opencode"


def test_opencode_adapter_enforces_timeout_budget(tmp_path: Path) -> None:
    packet = TaskPacket(
        runtime_task_id="task_opencode_timeout",
        run_id="run_opencode_timeout",
        task_kind=TaskKind.shell_exec,
        command=[],
        working_directory=str(tmp_path),
        expected_artifacts=["state/artifacts/opencode.md"],
        env={"WORKFLOW_PRESET_ID": "feature_delivery", "WORKFLOW_RUN_GOAL": "timeout"},
    )

    adapter = OpenCodeAdapter(runner=_fake_timeout_runner, executable="python")
    result = adapter.launch(packet)

    assert result.return_code == 124
    assert "timed out after 180s" in result.stderr


def test_domain_pack_artifact_is_used_in_auto_path(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Run through domain pack", "feature_delivery")
    prepared = service.compile_run(run.run_id)
    bundle = service.resume_run(run.run_id)
    artifact_path = Path(prepared.task_packet.expected_artifacts[0])
    if not artifact_path.is_absolute():
        artifact_path = Path(prepared.task_packet.working_directory) / artifact_path

    content = artifact_path.read_text(encoding="utf-8")

    assert bundle.run.status == "completed"
    assert "domain_pack: software_delivery_pack" in content
    assert "domain_pack_operator_label: software-delivery" in content
    assert "domain_pack_capability_tags: artifact_generation,software_delivery" in content
    assert "domain_pack_evidence_expectations: artifact exists,artifact includes runtime brief when available" in content
    assert "domain_context: software_delivery" in content
    assert "adapter: shell" in content
    assert "goal: [software-delivery]" in content


def test_status_detail_uses_stored_domain_pack_resolution_when_registry_changes(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    seeded_domain_packs = load_seed_domain_packs(Path("infra/seeds/domain_packs.json"))
    compile_service = OrchestratorService(db_path, domain_pack_registry=DomainPackRegistry(seeded_domain_packs))

    run = compile_service.create_run("Compile with stored domain pack resolution", "feature_delivery")
    compile_service.compile_run(run.run_id)

    read_service = OrchestratorService(db_path, domain_pack_registry=DomainPackRegistry([]))
    detail = read_service.get_status_detail(run.run_id)

    assert detail["domain_pack"]["domain_pack_id"] == "software_delivery_pack"
    assert detail["domain_pack"]["matched_preset_id"] == "feature_delivery"
    assert detail["domain_pack"]["compile_projection"]["artifact_label"] == "software_delivery"


def test_service_can_preview_domain_pack_resolution_before_compile(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    preview = service.preview_domain_pack_resolution("feature_delivery", task_kind="shell_exec")

    assert preview["resolved"] is True
    assert preview["domain_pack"]["domain_pack_id"] == "software_delivery_pack"
    assert preview["capability_resolution"]["adapter_name"] == "shell"


def test_service_validates_domain_pack_catalog(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    report = service.validate_domain_pack_catalog()

    assert report["passed"] is True
    assert report["issue_count"] == 0
    assert report["claimed_pairs"] == [
        {
            "preset_id": "advisory_delivery",
            "task_kind": "shell_exec",
            "domain_pack_id": "software_delivery_pack",
        },
        {
            "preset_id": "feature_delivery",
            "task_kind": "shell_exec",
            "domain_pack_id": "software_delivery_pack",
        },
        {
            "preset_id": "guarded_delivery",
            "task_kind": "shell_exec",
            "domain_pack_id": "software_delivery_pack",
        },
        {
            "preset_id": "optional_delivery",
            "task_kind": "shell_exec",
            "domain_pack_id": "software_delivery_pack",
        },
    ]


def test_run_memory_candidates_project_namespace_scoped_candidates(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Memory candidate baseline", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)

    namespaces = service.list_memory_namespaces()
    candidates = service.get_run_memory_candidates(run.run_id)
    second_candidates = service.get_run_memory_candidates(run.run_id)

    assert [namespace.namespace_id for namespace in namespaces] == ["repo", "failure", "policy", "release"]
    assert {candidate.namespace_id for candidate in candidates} == {"repo", "policy", "release"}
    assert any(candidate.namespace_id == "release" for candidate in candidates)
    assert [candidate.candidate_id for candidate in candidates] == [candidate.candidate_id for candidate in second_candidates]
    assert {candidate.candidate_id for candidate in candidates} == {
        f"memcand_{run.run_id}_repo",
        f"memcand_{run.run_id}_policy",
        f"memcand_{run.run_id}_release",
    }


def test_run_memory_candidate_materialization_persists_memory_item(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Persist one memory item", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)

    candidates = service.get_run_memory_candidates(run.run_id)
    selected_candidate = next(candidate for candidate in candidates if candidate.namespace_id == "policy")

    memory_item = service.materialize_run_memory_candidate(run.run_id, selected_candidate.candidate_id)
    duplicate = service.materialize_run_memory_candidate(run.run_id, selected_candidate.candidate_id)
    stored_items = service.list_memory_items(run_id=run.run_id)
    timeline = service.get_timeline(run.run_id)

    assert memory_item.namespace_id == "policy"
    assert memory_item.source_candidate_id == selected_candidate.candidate_id
    assert duplicate.memory_item_id == memory_item.memory_item_id
    assert [item.memory_item_id for item in stored_items] == [memory_item.memory_item_id]
    assert "memory_item_materialized" in [event.event_type for event in timeline]


def test_memory_retrieval_preview_supports_preset_namespace_and_explicit_selection(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    first_run = service.create_run("First memory retrieval source", "feature_delivery")
    service.compile_run(first_run.run_id)
    service.resume_run(first_run.run_id)
    first_candidates = service.get_run_memory_candidates(first_run.run_id)
    first_policy_item = service.materialize_run_memory_candidate(
        first_run.run_id,
        next(candidate.candidate_id for candidate in first_candidates if candidate.namespace_id == "policy"),
    )

    second_run = service.create_run("Second memory retrieval source", "feature_delivery")
    service.compile_run(second_run.run_id)
    service.resume_run(second_run.run_id)
    second_candidates = service.get_run_memory_candidates(second_run.run_id)
    second_policy_item = service.materialize_run_memory_candidate(
        second_run.run_id,
        next(candidate.candidate_id for candidate in second_candidates if candidate.namespace_id == "policy"),
    )

    preview = service.preview_memory_retrieval(preset_id="feature_delivery", namespace_id="policy", limit=5)
    explicit_preview = service.preview_memory_retrieval(
        preset_id="feature_delivery",
        namespace_id="policy",
        memory_item_ids=[first_policy_item.memory_item_id],
    )

    assert preview.item_count == 2
    assert preview.namespace_ids == ["policy"]
    assert set(preview.source_run_ids) == {first_run.run_id, second_run.run_id}
    assert preview.selected_memory_item_ids == [second_policy_item.memory_item_id, first_policy_item.memory_item_id]
    assert all(line.startswith("[policy]") for line in preview.brief_lines)

    assert explicit_preview.item_count == 1
    assert explicit_preview.selected_memory_item_ids == [first_policy_item.memory_item_id]
    assert explicit_preview.source_run_ids == [first_run.run_id]


def test_run_simulation_passes_for_feature_delivery_completion(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Simulation pass path", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)

    report = service.get_run_simulation(run.run_id)
    summary = service.get_run_summary(run.run_id)
    audit_report = service.get_run_audit_report(run.run_id)

    assert report.policy_id == "delivery_consistency_simulation"
    assert report.triggered is True
    assert report.status == "passed"
    assert summary["simulation_summary"]["status"] == "passed"
    assert summary["execution_profile"]["simulation_policy"]["policy_id"] == "delivery_consistency_simulation"
    assert audit_report["simulation_report"]["status"] == "passed"


def test_run_simulation_is_skipped_when_policy_disabled(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Research run without simulation", "research_spike")

    report = service.get_run_simulation(run.run_id)

    assert report.policy_id == "research_no_simulation"
    assert report.trigger_policy == "disabled"
    assert report.triggered is False
    assert report.status == "skipped"
    assert report.reason == "disabled_by_policy"


def test_failure_only_simulation_triggers_for_inconsistent_advisory_run(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Advisory simulation on failure", "advisory_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)

    with unit_of_work(db_path) as connection:
        row = connection.execute(
            """
            SELECT state_ref_id
            FROM runtime_state_refs
            WHERE run_id = ?
            ORDER BY updated_at DESC, created_at DESC, state_ref_id DESC
            LIMIT 1
            """,
            (run.run_id,),
        ).fetchone()
        connection.execute(
            """
            UPDATE runtime_state_refs
            SET graph_step = ?, is_terminal = ?, updated_at = CURRENT_TIMESTAMP
            WHERE state_ref_id = ?
            """,
            ("compiled", 0, row["state_ref_id"]),
        )

    report = service.get_run_simulation(run.run_id)

    assert report.policy_id == "advisory_failure_simulation"
    assert report.trigger_policy == "failure_only"
    assert report.triggered is True
    assert report.status == "failed"
    assert "inspection_consistency" in report.finding_codes


def test_record_run_simulation_persists_history_and_projects_latest_record(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Persist simulation record", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)

    record = service.record_run_simulation(run.run_id)
    records = service.list_simulation_records(run.run_id)
    detail = service.get_status_detail(run.run_id)
    inspection = service.inspect_run_state(run.run_id)
    summary = service.get_run_summary(run.run_id)
    timeline = service.get_timeline(run.run_id)

    assert record.policy_id == "delivery_consistency_simulation"
    assert record.status == "passed"
    assert [item.recorded_from for item in records] == [
        SimulationRecordSource.lifecycle_terminal,
        SimulationRecordSource.manual_request,
    ]
    assert detail["latest_simulation_record"]["record_id"] == record.record_id
    assert inspection["latest_simulation_record"]["record_id"] == record.record_id
    assert summary["simulation_summary"]["latest_record_id"] == record.record_id
    assert "simulation_recorded" in [event.event_type for event in timeline]


def test_cancel_run_records_simulation_hook_when_policy_triggers(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Cancel with simulation hook", "feature_delivery")
    service.compile_run(run.run_id)

    cancelled = service.cancel_run(run.run_id)
    records = service.list_simulation_records(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert cancelled.status == "cancelled"
    assert [record.recorded_from for record in records] == [SimulationRecordSource.lifecycle_cancelled]
    assert detail["latest_simulation_record"]["recorded_from"] == "lifecycle_cancelled"


def test_manual_record_simulation_appends_after_lifecycle_hook(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Manual simulation after hook", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)

    manual_record = service.record_run_simulation(run.run_id)
    records = service.list_simulation_records(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert [record.recorded_from for record in records] == [
        SimulationRecordSource.lifecycle_terminal,
        SimulationRecordSource.manual_request,
    ]
    assert manual_record.recorded_from == "manual_request"
    assert detail["latest_simulation_record"]["record_id"] == manual_record.record_id


def test_compile_can_inject_explicit_memory_brief_into_task_packet_and_artifact(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    source_run = service.create_run("Source memory item", "feature_delivery")
    service.compile_run(source_run.run_id)
    service.resume_run(source_run.run_id)
    source_candidates = service.get_run_memory_candidates(source_run.run_id)
    policy_item = service.materialize_run_memory_candidate(
        source_run.run_id,
        next(candidate.candidate_id for candidate in source_candidates if candidate.namespace_id == "policy"),
    )

    target_run = service.create_run("Target memory-aware compile", "feature_delivery")
    prepared = service.compile_run(target_run.run_id, memory_item_ids=[policy_item.memory_item_id])
    detail = service.get_status_detail(target_run.run_id)
    task_packet = service.task_repo.get_task_packet(prepared.task_packet.runtime_task_id)
    service.resume_run(target_run.run_id)

    artifact_path = Path(prepared.task_packet.expected_artifacts[0])
    if not artifact_path.is_absolute():
        artifact_path = Path(prepared.task_packet.working_directory) / artifact_path
    artifact_content = artifact_path.read_text(encoding="utf-8")

    assert prepared.memory_preview is not None
    assert prepared.memory_preview.selected_memory_item_ids == [policy_item.memory_item_id]
    assert detail["memory_retrieval_preview"]["selected_memory_item_ids"] == [policy_item.memory_item_id]
    assert task_packet is not None
    assert task_packet.env["WORKFLOW_MEMORY_RETRIEVAL_PREVIEW"]
    assert "memory_item_ids:" in artifact_content
    assert policy_item.memory_item_id in artifact_content
    assert "memory_brief:" in artifact_content


def test_service_can_execute_opencode_adapter_with_fake_runner(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    router = WorkerRouter([ShellAdapter(), OpenCodeAdapter(runner=_fake_opencode_runner), NoopAdapter()])
    service = OrchestratorService(db_path, worker_router=router)

    run = service.create_run("Run through opencode adapter", "feature_delivery")
    prepared = service.compile_run(run.run_id, adapter_name="opencode")
    bundle = service.resume_run(run.run_id)
    evidence = service.get_task_evidence(prepared.task_packet.runtime_task_id)
    artifact_path = Path(prepared.task_packet.expected_artifacts[0])
    if not artifact_path.is_absolute():
        artifact_path = Path(prepared.task_packet.working_directory) / artifact_path
    content = artifact_path.read_text(encoding="utf-8")

    assert bundle.run.status == "completed"
    assert evidence.raw_execution["adapter_name"] == "opencode"
    assert "adapter: opencode" in content


def test_preview_tool_projection_includes_mcp_subset_for_reviewable_pilot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UAWO_ENABLE_AGENT_LANE", "1")
    monkeypatch.setenv("UAWO_ENABLE_MCP_SOURCE", "1")
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path, capability_plane=CapabilityPlane())

    sources = service.list_capability_sources()
    preview = service.preview_tool_projection(preset_id="research_spike_reviewable")

    assert any(item["source_type"] == "built_in" for item in sources)
    assert any(item["source_type"] == "mcp_stdio" for item in sources)
    assert preview["execution_lane"] == "standard_agent"
    assert preview["capability_resolution"]["adapter_name"] == "agent"
    tool_names = [item["tool_name"] for item in preview["tool_projection_manifest"]["tools"]]
    assert "list_workspace_files" in tool_names
    assert "mcp_list_workspace_files" in tool_names
    assert preview["mcp_server_profiles"][0]["profile_id"] == "local_workspace_readonly"


def test_research_spike_reviewable_runs_agent_lane_and_exports_trace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UAWO_ENABLE_AGENT_LANE", "1")
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    trace_exporter = InMemoryTraceExporter()
    router = WorkerRouter(
        [
            ShellAdapter(),
            OpenCodeAdapter(runner=_fake_opencode_runner),
            NoopAdapter(),
            LangChainAgentAdapter(runner=_fake_agent_runner),
        ]
    )
    service = OrchestratorService(
        db_path,
        worker_router=router,
        trace_exporter=trace_exporter,
    )

    run = service.create_run("Research borrowed agent lane", "research_spike_reviewable")
    prepared = service.compile_run(run.run_id)
    bundle = service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)
    artifact_text = Path(bundle.evidence.artifact_refs[0].path).read_text(encoding="utf-8")

    assert str(prepared.execution_lane) == "standard_agent"
    assert prepared.capability_route is not None
    assert prepared.capability_route.adapter_name == "agent"
    assert bundle.run.status == "awaiting_review"
    assert detail["execution_lane"] == "standard_agent"
    assert detail["trace_exporter"]["provider"] == "memory"
    assert detail["last_runtime_state"]["state_payload"]["execution_lane"] == "standard_agent"
    assert len(trace_exporter.records) >= 2
    assert trace_exporter.records[-1].lane_type == "standard_agent"
    assert "execution_lane: standard_agent" in artifact_text
    assert "projected_tools:" in artifact_text


def test_feature_delivery_can_dispatch_through_external_worker_pool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UAWO_ENABLE_EXTERNAL_WORKER_POOLS", "1")
    monkeypatch.setenv("WORKFLOW_WORKER_POOL_ID", "mock_remote_shell")
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("External worker pool dispatch", "feature_delivery")
    service.compile_run(run.run_id)
    bundle = service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert bundle.run.status == "completed"
    assert detail["execution_target"]["worker_pool_id"] == "mock_remote_shell"
    assert detail["execution_target"]["target_kind"] == "external_worker_pool"
    assert detail["lease_renewals"][0]["status"] == "renewed"
    assert detail["execution_target"]["authority_term_no"] == detail["execution_target"]["term_no"]
    assert detail["execution_target"]["decision_index"] == detail["execution_target"]["commit_index"]
    assert detail["lease_renewals"][0]["authority_term_no"] == detail["lease_renewals"][0]["term_no"]
    assert detail["lease_renewals"][0]["decision_index"] == detail["lease_renewals"][0]["commit_index"]


def test_durable_pilot_refs_stay_in_diagnostics_and_can_resume_review(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UAWO_ENABLE_AGENT_LANE", "1")
    monkeypatch.setenv("UAWO_ENABLE_DURABLE_PILOT", "1")
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    durable = _RecordingDurablePilot()
    router = WorkerRouter(
        [
            ShellAdapter(),
            OpenCodeAdapter(runner=_fake_opencode_runner),
            NoopAdapter(),
            LangChainAgentAdapter(runner=_fake_agent_runner),
        ]
    )
    service = OrchestratorService(
        db_path,
        worker_router=router,
        durable_runtime_pilot=durable,
        trace_exporter=InMemoryTraceExporter(),
    )

    run = service.create_run("Research durable pilot", "research_spike_reviewable")
    prepared = service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    awaiting_detail = service.get_status_detail(run.run_id)

    assert str(prepared.execution_lane) == "durable_incremental"
    assert durable.start_calls == [(run.run_id, prepared.task_packet.runtime_task_id)]
    assert awaiting_detail["durable_runtime_pilot"]["provider"] == "recording"
    assert awaiting_detail["execution_lane"] == "durable_incremental"
    assert "thread_id" not in awaiting_detail["run"]
    assert awaiting_detail["last_runtime_state"]["state_payload"]["thread_id"].startswith("thread_")
    assert awaiting_detail["trace_context"]["thread_id"].startswith("thread_")
    assert awaiting_detail["durable_lineage"]["transition_count"] >= 2
    assert [item["reason"] for item in awaiting_detail["durable_lineage"]["history"]] == ["start", "resume", "awaiting_review"]

    approved = service.approve_run_review(run.run_id)
    approved_detail = service.get_status_detail(run.run_id)

    assert approved.run.status == "completed"
    assert durable.review_calls
    assert approved_detail["run"]["status"] == "completed"
    assert "thread_id" not in approved_detail["run"]
    assert approved_detail["last_runtime_state"]["state_payload"]["checkpoint_id"].startswith("checkpoint_")
    assert approved_detail["durable_lineage"]["transition_count"] == 4


def test_langgraph_durable_pilot_writes_checkpoint_snapshots(tmp_path: Path) -> None:
    state_dir = tmp_path / "durable"
    pilot = LangGraphDurableRuntimePilot(state_dir=state_dir)

    refs = pilot.start("run_alpha", "task_alpha")
    updated = pilot.checkpoint(refs, reason="resume")

    snapshot_path = state_dir / f"{refs['thread_id']}.json"
    assert snapshot_path.exists()
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert payload["latest_checkpoint_id"] == updated["checkpoint_id"]
    assert len(payload["checkpoints"]) == 2
    assert pilot.describe()["state_dir"] == state_dir.resolve().as_posix()


def test_trace_export_failures_do_not_block_agent_lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UAWO_ENABLE_AGENT_LANE", "1")
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    router = WorkerRouter(
        [
            ShellAdapter(),
            OpenCodeAdapter(runner=_fake_opencode_runner),
            NoopAdapter(),
            LangChainAgentAdapter(runner=_fake_agent_runner),
        ]
    )
    service = OrchestratorService(
        db_path,
        worker_router=router,
        trace_exporter=_ExplodingTraceExporter(),
    )

    run = service.create_run("Research trace isolation", "research_spike_reviewable")
    service.compile_run(run.run_id)
    bundle = service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert bundle.run.status == "awaiting_review"
    assert detail["trace_exporter"]["provider"] == "exploding"
    assert detail["trace_context"]["external_trace_id"] is None


def test_research_spike_reviewable_can_run_through_sessionful_external_agent_lane(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    router = WorkerRouter(
        [
            ShellAdapter(),
            OpenCodeAdapter(runner=_fake_opencode_runner),
            OpenCodeSessionAdapter(runner=_fake_session_runner),
            NoopAdapter(),
        ]
    )
    service = OrchestratorService(db_path, worker_router=router)

    run = service.create_run("Collaborative sessionful research", "research_spike_reviewable")
    prepared = service.compile_run(run.run_id, adapter_name="opencode_session")
    assert prepared.execution_lane == "sessionful_external_agent"

    bundle = service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)
    if detail["run"]["status"] == "awaiting_review":
        service.approve_run_review(run.run_id)
        detail = service.get_status_detail(run.run_id)

    assert bundle.evidence.result_envelope is not None
    assert bundle.evidence.result_envelope.session_ref is not None
    assert bundle.evidence.result_envelope.session_ref.external_session_id == "sess_exec_123"
    assert detail["trace_context"]["external_session_id"] == "sess_exec_123"
    assert detail["trace_context"]["external_session_url"] == "https://example.com/session/exec-123"
    assert detail["trace_context"]["session_export_ref"].endswith(".json")


def test_operator_projections_include_policy_preview_and_session_refs(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    router = WorkerRouter(
        [
            ShellAdapter(),
            OpenCodeAdapter(runner=_fake_opencode_runner),
            OpenCodeSessionAdapter(runner=_fake_session_runner),
            NoopAdapter(),
        ]
    )
    service = OrchestratorService(db_path, worker_router=router)

    run = service.create_run("Collaborative sessionful research", "research_spike_reviewable")
    service.compile_run(run.run_id, adapter_name="opencode_session")
    service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)
    if detail["run"]["status"] == "awaiting_review":
        service.approve_run_review(run.run_id)
        detail = service.get_status_detail(run.run_id)

    inspection = service.inspect_run_state(run.run_id)
    audit = service.get_run_audit_report(run.run_id)
    replay = service.get_run_replay_packet(run.run_id)
    operator_packet = service.get_run_operator_packet(run.run_id)
    operator_view = service.get_operator_view(run.run_id)

    assert detail["capability_policy_preview"]["enabled"] is True
    assert detail["capability_policy_preview"]["policy_preview"]["sessionful_node_count"] == 1
    assert detail["operator_projection"]["recommended_operator_mode"] == "human_visible"
    assert detail["operator_projection"]["session_ref"]["external_session_id"] == "sess_exec_123"
    assert inspection["operator_projection"]["capability_health_summary"]["descriptor_count"] >= 1
    assert audit["operator_projection"]["session_ref"]["external_session_id"] == "sess_exec_123"
    assert replay["capability_policy_preview"]["policy_preview"]["sessionful_node_count"] == 1
    assert operator_packet["operator_projection"]["session_ref"]["external_session_id"] == "sess_exec_123"
    assert operator_view["operator_projection"]["recommended_operator_mode"] == "human_visible"


def test_project_delivery_runs_multi_role_orchestration(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Ship a coordinated project slice", "project_delivery")
    service.compile_run(run.run_id)
    detail = service.get_status_detail(run.run_id)
    replay = service.get_run_replay_packet(run.run_id)
    operator_packet = service.get_run_operator_packet(run.run_id)

    assert detail["run"]["status"] == "prepared"
    assert detail["orchestration"]["cluster_template_ids"] == ["dev_cluster"]
    assert detail["selected_clusters"][0]["template_id"] == "dev_cluster"
    assert detail["cluster_graph"]["cluster_template_ids"] == ["dev_cluster"]
    assert detail["cluster_policy_preview"]["selected_cluster_template_ids"] == ["dev_cluster"]
    assert detail["cluster_packets"][0]["cluster_template_id"] == "dev_cluster"
    assert replay["selected_clusters"][0]["template_id"] == "dev_cluster"
    assert replay["cluster_execution_lineage"]["selected_cluster_template_ids"] == ["dev_cluster"]
    assert replay["cluster_packets"][0]["handoff_packets"][0]["cluster_template_id"] == "dev_cluster"
    assert operator_packet["selected_clusters"][0]["template_id"] == "dev_cluster"
    assert operator_packet["cluster_policy_preview"]["selected_cluster_template_ids"] == ["dev_cluster"]


def test_compile_run_accepts_repo_mutation_contract_and_projects_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTHONPATH", repo_root.as_posix())
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    router = WorkerRouter([ShellAdapter(), OpenCodeAdapter(runner=_fake_patch_runner), NoopAdapter()])
    service = OrchestratorService(db_path, worker_router=router)

    target_file = tmp_path / "mutated.txt"
    target_file.write_text("before\n", encoding="utf-8")
    task_card = tmp_path / "task_card.md"
    task_card.write_text("# M16\n\nImplement one bounded mutation.\n", encoding="utf-8")
    verifier = tmp_path / "verify_mutated.py"
    verifier.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "sys.exit(0 if Path('mutated.txt').read_text(encoding='utf-8') == 'after\\n' else 1)\n",
        encoding="utf-8",
    )
    test_command = f"{sys.executable} {verifier.name}"

    run = service.create_run("Bounded repo mutation", "feature_delivery")
    prepared = service.compile_run(
        run.run_id,
        adapter_name="opencode",
        task_card_ref="M16-1A",
        task_card_path=task_card.as_posix(),
        write_set=["mutated.txt"],
        read_set=["task_card.md"],
        test_commands=[test_command],
        mutation_mode=MutationMode.patch_apply,
    )
    detail = service.get_status_detail(run.run_id)

    assert prepared.execution_lane == "repo_change_controlled"
    assert prepared.task_packet.mutation_contract is not None
    assert prepared.task_packet.mutation_contract.write_set == ["mutated.txt"]
    assert detail["mutation_contract"]["task_card_ref"] == "M16-1A"
    assert detail["execution_lane"] == "repo_change_controlled"

    bundle = service.resume_run(run.run_id)
    mutation_report = service.get_run_mutation_report(run.run_id)
    detail_after = service.get_status_detail(run.run_id)

    assert bundle.run.status == "completed"
    assert target_file.read_text(encoding="utf-8") == "after\n"
    assert mutation_report["mutation_result"]["final_test_status"] == "passed"
    assert mutation_report["mutation_result"]["changed_files"] == ["mutated.txt"]
    assert detail_after["mutation_result"]["fix_iteration_count"] == 0
    assert detail_after["mutation_result"]["test_attempts"][0]["passed"] is True


def test_repo_mutation_rejects_out_of_scope_patch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTHONPATH", repo_root.as_posix())
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()

    def _rejecting_runner(command, cwd, env, capture_output, text, check, timeout):
        patch_text = (
            "--- rogue.txt\n"
            "+++ rogue.txt\n"
            "@@ -0,0 +1 @@\n"
            "+outside\n"
        )
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"type": "text", "part": {"text": patch_text}}),
            stderr="",
        )

    router = WorkerRouter([ShellAdapter(), OpenCodeAdapter(runner=_rejecting_runner), NoopAdapter()])
    service = OrchestratorService(db_path, worker_router=router)

    target_file = tmp_path / "allowed.txt"
    target_file.write_text("before\n", encoding="utf-8")
    run = service.create_run("Reject out of scope mutation", "feature_delivery")
    service.compile_run(
        run.run_id,
        adapter_name="opencode",
        write_set=["allowed.txt"],
        mutation_mode=MutationMode.patch_apply,
    )

    with pytest.raises(RepoMutationScopeError):
        service.resume_run(run.run_id)

    assert target_file.read_text(encoding="utf-8") == "before\n"
    assert not (tmp_path / "rogue.txt").exists()


def test_repo_mutation_retries_with_bounded_fix_iterations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTHONPATH", repo_root.as_posix())
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()

    def _iterating_runner(command, cwd, env, capture_output, text, check, timeout):
        target = json.loads(env["WORKFLOW_MUTATION_WRITE_SET"])[0].replace("\\", "/")
        attempt_index = int(env.get("WORKFLOW_MUTATION_ATTEMPT_INDEX", "0"))
        next_value = "broken" if attempt_index == 0 else "after"
        patch_text = (
            f"--- {target}\n"
            f"+++ {target}\n"
            "@@ -1 +1 @@\n"
            "-before\n"
            f"+{next_value}\n"
        )
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"type": "text", "part": {"text": patch_text}}),
            stderr="",
        )

    router = WorkerRouter([ShellAdapter(), OpenCodeAdapter(runner=_iterating_runner), NoopAdapter()])
    service = OrchestratorService(db_path, worker_router=router)

    target_file = tmp_path / "iterated.txt"
    target_file.write_text("before\n", encoding="utf-8")
    verifier = tmp_path / "verify_iterated.py"
    verifier.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "sys.exit(0 if Path('iterated.txt').read_text(encoding='utf-8') == 'after\\n' else 1)\n",
        encoding="utf-8",
    )
    test_command = f"{sys.executable} {verifier.name}"

    run = service.create_run("Bounded fix loop", "feature_delivery")
    service.compile_run(
        run.run_id,
        adapter_name="opencode",
        write_set=["iterated.txt"],
        test_commands=[test_command],
        max_fix_iterations=1,
        mutation_mode=MutationMode.patch_apply,
    )
    service.resume_run(run.run_id)
    mutation_report = service.get_run_mutation_report(run.run_id)

    assert target_file.read_text(encoding="utf-8") == "after\n"
    assert mutation_report["mutation_result"]["fix_iteration_count"] == 1
    assert [item["iteration"] for item in mutation_report["mutation_result"]["test_attempts"]] == [0, 1]
    assert mutation_report["mutation_result"]["final_test_status"] == "passed"


def test_project_delivery_coder_uses_repo_mutation_when_parent_contract_is_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTHONPATH", repo_root.as_posix())
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    router = WorkerRouter([ShellAdapter(), OpenCodeAdapter(runner=_fake_patch_runner), NoopAdapter()])
    service = OrchestratorService(db_path, worker_router=router)

    target_file = tmp_path / "project_slice.txt"
    target_file.write_text("before\n", encoding="utf-8")
    task_card = tmp_path / "project_task_card.md"
    task_card.write_text("# Project Slice\n\nImplement the bounded coder change.\n", encoding="utf-8")
    verifier = tmp_path / "verify_project_slice.py"
    verifier.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "sys.exit(0 if Path('project_slice.txt').read_text(encoding='utf-8') == 'after\\n' else 1)\n",
        encoding="utf-8",
    )
    test_command = f"{sys.executable} {verifier.name}"

    run = service.create_run("Dogfood project delivery mutation", "project_delivery")
    service.compile_run(
        run.run_id,
        task_card_ref="M17-3A",
        task_card_path=task_card.as_posix(),
        write_set=["project_slice.txt"],
        test_commands=[test_command],
        mutation_mode=MutationMode.patch_apply,
    )
    service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert detail["orchestration"]["role_progress"]["coder"]["mutation_report"]["mutation_result"]["final_test_status"] == "passed"
    assert target_file.read_text(encoding="utf-8") == "after\n"


def test_domain_pack_skill_export_requires_flag_then_exports_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    with pytest.raises(WorkflowError):
        service.export_domain_pack_skill("software_delivery_pack", output_root=tmp_path / "skills")

    monkeypatch.setenv("UAWO_ENABLE_SKILL_EXPORT", "1")
    enabled_service = OrchestratorService(db_path)
    payload = enabled_service.export_domain_pack_skill("software_delivery_pack", output_root=tmp_path / "skills")

    bundle_dir = Path(payload["bundle_path"])
    assert payload["exported"] is True
    assert (bundle_dir / "README.md").exists()
    assert (bundle_dir / "skill.json").exists()


def test_status_detail_projects_auto_review_state(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Auto review projection", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert detail["effective_review_state"] == "auto_passed"
    assert detail["latest_review_verdict"]["reviewer_type"] == "auto"
    assert detail["latest_review_verdict"]["decision"] == "pass"


def test_status_detail_projects_human_reject_state(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Human reject projection", "research_spike")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    service.reject_run_review(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert detail["effective_review_state"] == "human_rejected"
    assert detail["latest_review_verdict"]["reviewer_type"] == "human"
    assert detail["latest_review_verdict"]["decision"] == "fail"


def test_status_detail_exposes_operator_diagnostics(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    prepared_run = service.create_run("Prepared diagnostics", "feature_delivery")
    service.compile_run(prepared_run.run_id)
    prepared_detail = service.get_status_detail(prepared_run.run_id)

    assert prepared_detail["failure_reason"] is None
    assert prepared_detail["waiting_reason"] == "awaiting_runtime_resume"
    assert prepared_detail["last_runtime_state"]["graph_step"] == "compiled"
    assert prepared_detail["last_review_verdict"] is None
    assert prepared_detail["recoverability_hint"] == "resume_run"

    failed_run = service.create_run("Rejected diagnostics", "research_spike")
    service.compile_run(failed_run.run_id)
    service.resume_run(failed_run.run_id)
    service.reject_run_review(failed_run.run_id)
    failed_detail = service.get_status_detail(failed_run.run_id)

    assert failed_detail["failure_reason"] == "human_review_rejected"
    assert failed_detail["waiting_reason"] is None
    assert failed_detail["last_runtime_state"]["graph_step"] == "failed"
    assert failed_detail["recoverability_hint"] == "inspect_evidence_then_recompile"


def test_run_summary_projects_success_taxonomy(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Summary success path", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    summary = service.get_run_summary(run.run_id)

    assert summary["failure_taxonomy"]["category"] == "success"
    assert summary["inspection_summary"]["passed"] is True
    assert summary["timeline_summary"]["terminal_event_type"] == "run_completed"
    assert summary["ownership_summary"]["runtime_attempt_projection"]["attempt_count"] == 2


def test_run_summary_projects_review_pending_taxonomy(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Summary awaiting review", "research_spike")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    summary = service.get_run_summary(run.run_id)

    assert summary["failure_taxonomy"]["category"] == "review_pending"
    assert summary["review_summary"]["effective_review_state"] == "human_pending"
    assert summary["timeline_summary"]["terminal_event_type"] is None
    assert summary["next_action"] == "human_review"


def test_run_summary_projects_cancelled_taxonomy(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Summary cancelled path", "feature_delivery")
    service.compile_run(run.run_id)
    service.cancel_run(run.run_id)
    summary = service.get_run_summary(run.run_id)

    assert summary["failure_taxonomy"]["category"] == "operator_cancelled"
    assert summary["failure_taxonomy"]["is_failure"] is True
    assert summary["timeline_summary"]["terminal_event_type"] == "run_cancelled"


def test_event_inspection_projects_closed_auto_path(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Event inspection auto", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    event_inspection = service.get_event_inspection(run.run_id)
    summary = service.get_run_summary(run.run_id)

    assert event_inspection["closure_audit"]["passed"] is True
    assert event_inspection["closure_audit"]["state"] == "closed"
    assert event_inspection["closure_audit"]["required_event_type"] == "run_completed"
    assert event_inspection["review_digest"]["review_submitted_count"] == 1
    assert event_inspection["event_digest"]["terminal_event_type"] == "run_completed"
    assert event_inspection["event_digest"]["recent_event_types"][-1] == "simulation_recorded"
    assert summary["closure_summary"]["state"] == "closed"
    assert summary["review_summary"]["latest_review_decision"] == "pass"


def test_event_inspection_projects_awaiting_review_path(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Event inspection review wait", "research_spike")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    event_inspection = service.get_event_inspection(run.run_id)
    summary = service.get_run_summary(run.run_id)

    assert event_inspection["closure_audit"]["passed"] is True
    assert event_inspection["closure_audit"]["state"] == "awaiting_review"
    assert event_inspection["closure_audit"]["required_event_type"] == "review_requested"
    assert event_inspection["review_digest"]["review_requested_count"] == 1
    assert event_inspection["review_digest"]["review_submitted_count"] == 0
    assert event_inspection["event_digest"]["terminal_event_type"] is None
    assert summary["closure_summary"]["state"] == "awaiting_review"
    assert summary["review_summary"]["pending_human_review"] is True


def test_event_inspection_flags_missing_terminal_event(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Event inspection missing closure", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    with unit_of_work(db_path) as connection:
        connection.execute(
            "DELETE FROM run_events WHERE run_id = ? AND event_type = ?",
            (run.run_id, str(RunEventType.run_completed)),
        )

    event_inspection = service.get_event_inspection(run.run_id)
    summary = service.get_run_summary(run.run_id)

    assert event_inspection["closure_audit"]["passed"] is False
    assert event_inspection["closure_audit"]["state"] == "closure_gap_detected"
    assert "missing_event:run_completed" in event_inspection["closure_audit"]["missing_requirements"]
    assert "missing_terminal_event:run_completed" in event_inspection["closure_audit"]["missing_requirements"]
    assert event_inspection["closure_audit"]["recommended_action"] == "inspect_timeline_and_reconcile"
    assert summary["closure_summary"]["passed"] is False


def test_run_audit_report_projects_closed_auto_path(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Audit report auto", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    report = service.get_run_audit_report(run.run_id)

    assert report["audit_version"] == "m3_phase_3_v1"
    assert report["summary"]["failure_taxonomy"]["category"] == "success"
    assert report["review_packet"]["closure_summary"]["state"] == "closed"
    assert report["event_inspection"]["closure_audit"]["passed"] is True
    assert report["timeline_overview"]["event_count"] >= len(report["timeline_tail"])
    assert report["timeline_tail"][-1]["event_type"] == "simulation_recorded"


def test_run_audit_report_projects_human_review_wait_path(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Audit report human wait", "research_spike")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    report = service.get_run_audit_report(run.run_id)

    assert report["summary"]["failure_taxonomy"]["category"] == "review_pending"
    assert report["review_packet"]["effective_review_state"] == "human_pending"
    assert report["review_packet"]["closure_summary"]["state"] == "awaiting_review"
    assert report["event_inspection"]["review_digest"]["pending_human_review"] is True


def test_run_replay_packet_projects_metrics_and_lineage(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Replay packet auto", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    packet = service.get_run_replay_packet(run.run_id)

    assert packet["packet_version"] == "m9_phase_1_v1"
    assert packet["metrics"]["counts"]["events"] >= 1
    assert packet["metrics"]["counts"]["runtime_attempts"] >= 2
    assert packet["state_lineage"]["runtime_state_refs"][0]["graph_step"] == "completed"
    assert packet["review_lineage"]["effective_review_state"] == "auto_passed"
    assert len(packet["task_packets"]) == 1
    assert any(item["event_type"] == "run_completed" for item in packet["timeline"])


def test_inspection_reports_completed_runtime_non_terminal(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Completed but runtime live", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    state_ref = service.runtime_state_repo.list_for_run(run.run_id)[0]
    service.runtime_state_repo.upsert(
        RuntimeStateRef(
            state_ref_id=state_ref.state_ref_id,
            run_id=state_ref.run_id,
            runtime_task_id=state_ref.runtime_task_id,
            graph_step=RuntimeGraphStep.awaiting_review,
            state_payload={**state_ref.state_payload, "corrupted": True},
            is_terminal=False,
            created_at=state_ref.created_at,
        )
    )

    inspection = service.inspect_run_state(run.run_id)

    assert inspection["passed"] is False
    assert inspection["problem_count"] == 1
    assert inspection["repairable_problem_count"] == 1
    assert inspection["apply_supported"] is True
    assert inspection["problems"][0]["problem"] == "completed_runtime_non_terminal"
    assert inspection["problems"][0]["repairable"] is True
    assert inspection["problems"][0]["repair_action"] == "align_completed_runtime_state"
    assert inspection["recommended_action"] == "reconcile_runtime_state_ref"


def test_inspection_reports_awaiting_review_missing_evidence(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Awaiting review missing evidence", "research_spike")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    with unit_of_work(db_path) as connection:
        connection.execute("DELETE FROM evidence WHERE run_id = ?", (run.run_id,))

    inspection = service.inspect_run_state(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert inspection["passed"] is False
    assert inspection["repairable_problem_count"] == 0
    assert inspection["apply_supported"] is False
    assert inspection["problems"][0]["problem"] == "awaiting_review_missing_evidence"
    assert inspection["problems"][0]["repairable"] is False
    assert inspection["problems"][0]["repair_action"] is None
    assert inspection["recommended_action"] == "rebuild_or_replay_evidence"
    assert detail["waiting_reason"] == "awaiting_human_review_missing_evidence"


def test_inspection_reports_cancelled_with_live_runtime(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Cancelled but runtime live", "feature_delivery")
    service.compile_run(run.run_id)
    cancelled = service.cancel_run(run.run_id)
    assert cancelled.status == "cancelled"

    state_ref = service.runtime_state_repo.list_for_run(run.run_id)[0]
    service.runtime_state_repo.upsert(
        RuntimeStateRef(
            state_ref_id=state_ref.state_ref_id,
            run_id=state_ref.run_id,
            runtime_task_id=state_ref.runtime_task_id,
            graph_step=RuntimeGraphStep.compiled,
            state_payload={**state_ref.state_payload, "corrupted": True},
            is_terminal=False,
            created_at=state_ref.created_at,
        )
    )

    inspection = service.inspect_run_state(run.run_id)

    assert inspection["passed"] is False
    assert inspection["problems"][0]["problem"] == "cancelled_with_live_runtime"
    assert inspection["problems"][0]["repairable"] is True
    assert inspection["problems"][0]["repair_action"] == "align_cancelled_runtime_state"
    assert inspection["recommended_action"] == "terminate_or_reconcile_runtime"


def test_inspection_reports_prepared_compile_snapshot_incomplete_without_side_effects(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Prepared but incomplete snapshot", "feature_delivery")
    prepared = service.compile_run(run.run_id)
    timeline_before = service.get_timeline(run.run_id)
    with unit_of_work(db_path) as connection:
        connection.execute("DELETE FROM task_packets WHERE run_id = ?", (run.run_id,))

    inspection = service.inspect_run_state(run.run_id)
    timeline_after = service.get_timeline(run.run_id)

    assert inspection["passed"] is False
    assert inspection["problems"][0]["problem"] == "prepared_compile_snapshot_incomplete"
    assert inspection["problems"][0]["repairable"] is True
    assert inspection["problems"][0]["repair_action"] == "recompile_prepared_run"
    assert inspection["problems"][0]["details"]["missing_components"] == [f"task_packet:{prepared.task_packet.runtime_task_id}"]
    assert inspection["recommended_action"] == "recompile_run"
    assert service.get_run(run.run_id).status == "prepared"
    assert service.task_repo.get_task_packet(prepared.task_packet.runtime_task_id) is None
    assert [event.event_id for event in timeline_after] == [event.event_id for event in timeline_before]


def test_apply_run_repair_aligns_completed_runtime_state(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Completed but runtime live repair", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    state_ref = service.runtime_state_repo.list_for_run(run.run_id)[0]
    service.runtime_state_repo.upsert(
        RuntimeStateRef(
            state_ref_id=state_ref.state_ref_id,
            run_id=state_ref.run_id,
            runtime_task_id=state_ref.runtime_task_id,
            graph_step=RuntimeGraphStep.awaiting_review,
            state_payload={**state_ref.state_payload, "corrupted": True},
            is_terminal=False,
            created_at=state_ref.created_at,
        )
    )

    repair = service.apply_run_repair(run.run_id)
    inspection = service.inspect_run_state(run.run_id)
    timeline = service.get_timeline(run.run_id)

    assert repair["action"] == "align_completed_runtime_state"
    assert repair["problem"] == "completed_runtime_non_terminal"
    assert inspection["passed"] is True
    assert inspection["problem_count"] == 0
    assert service.runtime_state_repo.list_for_run(run.run_id)[0].graph_step == "completed"
    assert service.runtime_state_repo.list_for_run(run.run_id)[0].is_terminal is True
    assert "repair_applied" in [event.event_type for event in timeline]


def test_apply_run_repair_aligns_cancelled_runtime_state(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Cancelled but runtime live repair", "feature_delivery")
    service.compile_run(run.run_id)
    service.cancel_run(run.run_id)
    state_ref = service.runtime_state_repo.list_for_run(run.run_id)[0]
    service.runtime_state_repo.upsert(
        RuntimeStateRef(
            state_ref_id=state_ref.state_ref_id,
            run_id=state_ref.run_id,
            runtime_task_id=state_ref.runtime_task_id,
            graph_step=RuntimeGraphStep.compiled,
            state_payload={**state_ref.state_payload, "corrupted": True},
            is_terminal=False,
            created_at=state_ref.created_at,
        )
    )

    repair = service.apply_run_repair(run.run_id, action="align_cancelled_runtime_state")
    inspection = service.inspect_run_state(run.run_id)

    assert repair["action"] == "align_cancelled_runtime_state"
    assert repair["problem"] == "cancelled_with_live_runtime"
    assert inspection["passed"] is True
    assert service.runtime_state_repo.list_for_run(run.run_id)[0].graph_step == "cancelled"
    assert service.runtime_state_repo.list_for_run(run.run_id)[0].is_terminal is True


def test_apply_run_repair_recompiles_prepared_snapshot_and_preserves_task_kind(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Recompile prepared repair", "research_spike")
    prepared = service.compile_run(run.run_id, task_kind="noop")
    with unit_of_work(db_path) as connection:
        connection.execute("DELETE FROM task_packets WHERE run_id = ?", (run.run_id,))

    repair = service.apply_run_repair(run.run_id)
    inspection = service.inspect_run_state(run.run_id)
    repaired_runtime_task_id = repair["repaired_runtime_task_ids"][0]
    repaired_packet = service.task_repo.get_task_packet(repaired_runtime_task_id)

    assert repair["action"] == "recompile_prepared_run"
    assert repair["problem"] == "prepared_compile_snapshot_incomplete"
    assert inspection["passed"] is True
    assert repaired_packet is not None
    assert repaired_packet.task_kind == "noop"


def test_apply_run_repair_rejects_manual_only_problem(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Awaiting review without evidence repair", "research_spike")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    with unit_of_work(db_path) as connection:
        connection.execute("DELETE FROM evidence WHERE run_id = ?", (run.run_id,))

    with pytest.raises(RepairActionNotAvailableError):
        service.apply_run_repair(run.run_id)


def test_out_of_band_change_is_recorded_as_known_gap(tmp_path: Path) -> None:
    artifact_path = tmp_path / "artifact.md"
    artifact_path.write_text("initial", encoding="utf-8")
    finished_at = utc_now()
    os.utime(artifact_path, (finished_at.timestamp() + 5, finished_at.timestamp() + 5))

    result = ExecutionResult(
        runtime_task_id="task_oob",
        return_code=0,
        stdout="ok",
        stderr="",
        started_at=finished_at,
        finished_at=finished_at,
        duration_ms=1,
        artifact_paths=[artifact_path.as_posix()],
        adapter_name="shell",
    )
    evidence = EvidenceBuilder().build("run_oob", "task_oob", result)

    assert evidence.known_gaps
    assert "out-of-band change" in evidence.known_gaps[0]


def test_resume_run_releases_claim_after_auto_terminal(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Auto claim lifecycle", "feature_delivery")
    service.compile_run(run.run_id)
    bundle = service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)
    claims = service.list_claims(run.run_id)
    timeline_types = [event.event_type for event in service.get_timeline(run.run_id)]

    assert bundle.run.status == "completed"
    assert len(claims) == 1
    assert claims[0].status == "released"
    assert claims[0].release_reason == "run_terminal"
    assert detail["active_claims"] == []
    assert detail["latest_claim"]["status"] == "released"
    assert "claim_acquired" in timeline_types
    assert "claim_released" in timeline_types


def test_resume_run_releases_claim_before_human_review_wait(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Human review claim lifecycle", "research_spike")
    service.compile_run(run.run_id)
    bundle = service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)
    claims = service.list_claims(run.run_id)

    assert bundle.run.status == "awaiting_review"
    assert len(claims) == 1
    assert claims[0].status == "released"
    assert claims[0].release_reason == "awaiting_human_review"
    assert detail["active_claims"] == []
    assert detail["latest_claim"]["status"] == "released"


def test_resume_run_releases_worker_lease_after_auto_terminal(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Auto worker lease lifecycle", "feature_delivery")
    service.compile_run(run.run_id)
    bundle = service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)
    claims = service.list_claims(run.run_id)
    leases = service.list_worker_leases(run.run_id)
    timeline_types = [event.event_type for event in service.get_timeline(run.run_id)]

    assert bundle.run.status == "completed"
    assert len(leases) == 1
    assert leases[0].status == "released"
    assert leases[0].release_reason == "run_terminal"
    assert leases[0].adapter_name == "shell"
    assert leases[0].worker_kind == "worker"
    assert leases[0].worker_id == "worker_shell_local"
    assert leases[0].claim_id == claims[0].claim_id
    assert leases[0].attempt_id == detail["latest_runtime_attempt"]["attempt_id"]
    assert detail["active_worker_leases"] == []
    assert detail["latest_worker_lease"]["status"] == "released"
    assert detail["worker_lease_projection"]["active_lease_count"] == 0
    assert detail["worker_lease_projection"]["latest_adapter_name"] == "shell"
    assert detail["ownership_topology"]["claim"]["owner_kind"] == "control_plane"
    assert detail["ownership_topology"]["claim"]["domain_kind"] == "runtime_task"
    assert detail["ownership_topology"]["worker_lease"]["worker_kind"] == "worker"
    assert detail["ownership_topology"]["worker_lease"]["claim_id"] == claims[0].claim_id
    assert detail["ownership_topology"]["topology_aligned"] is True
    assert "worker_lease_acquired" in timeline_types
    assert "worker_lease_released" in timeline_types


def test_resume_runs_parallel_records_batch_barrier_and_starts_runs_together(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    delayed_adapter = _DelayedShellAdapter(delay_seconds=0.2)
    service = OrchestratorService(
        db_path,
        worker_router=WorkerRouter([delayed_adapter]),
    )

    first_run = service.create_run("Parallel batch first", "feature_delivery")
    second_run = service.create_run("Parallel batch second", "feature_delivery")
    service.compile_run(first_run.run_id)
    service.compile_run(second_run.run_id)

    batch = service.resume_runs_parallel([first_run.run_id, second_run.run_id], max_workers=2)
    first_detail = service.get_status_detail(first_run.run_id)
    second_detail = service.get_status_detail(second_run.run_id)
    first_timeline_types = [event.event_type for event in service.get_timeline(first_run.run_id)]

    assert batch["status"] == "completed"
    assert batch["member_count"] == 2
    assert batch["errors"] == []
    assert len(batch["results"]) == 2
    assert first_detail["parallel_batch"]["barrier_id"] == batch["barrier_id"]
    assert second_detail["parallel_batch"]["barrier_id"] == batch["barrier_id"]
    assert first_detail["parallel_batch"]["state"] == "released"
    assert second_detail["parallel_batch"]["state"] == "released"
    assert len(delayed_adapter.started_packets) == 2
    start_delta_ms = abs(
        int(
            (
                delayed_adapter.started_packets[0][1] - delayed_adapter.started_packets[1][1]
            ).total_seconds()
            * 1000
        )
    )
    assert start_delta_ms < 150
    assert first_detail["ownership_topology"]["topology_aligned"] is True
    assert second_detail["ownership_topology"]["topology_aligned"] is True
    assert RunEventType.batch_barrier_waiting in first_timeline_types
    assert RunEventType.batch_barrier_released in first_timeline_types


def test_resume_run_releases_worker_lease_before_human_review_wait(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Human review worker lease lifecycle", "research_spike")
    service.compile_run(run.run_id)
    bundle = service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)
    leases = service.list_worker_leases(run.run_id)

    assert bundle.run.status == "awaiting_review"
    assert len(leases) == 1
    assert leases[0].status == "released"
    assert leases[0].release_reason == "awaiting_human_review"
    assert detail["active_worker_leases"] == []
    assert detail["latest_worker_lease"]["status"] == "released"


def test_resume_run_rejects_when_active_claim_already_exists(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Claim conflict", "feature_delivery")
    prepared = service.compile_run(run.run_id)
    service.runtime_claim_repo.create(
        RuntimeClaim(
            run_id=run.run_id,
            runtime_task_id=prepared.task_packet.runtime_task_id,
            lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
    )

    with pytest.raises(RuntimeClaimConflictError):
        service.resume_run(run.run_id)

    assert service.get_run(run.run_id).status == "prepared"


def test_cancel_run_releases_active_claims(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Cancel active claim", "feature_delivery")
    prepared = service.compile_run(run.run_id)
    service.runtime_claim_repo.create(
        RuntimeClaim(
            run_id=run.run_id,
            runtime_task_id=prepared.task_packet.runtime_task_id,
            lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
    )

    cancelled = service.cancel_run(run.run_id)
    claims = service.list_claims(run.run_id)

    assert cancelled.status == "cancelled"
    assert claims[0].status == "released"
    assert claims[0].release_reason == "run_cancelled"
    assert service.get_status_detail(run.run_id)["active_claims"] == []


def test_cancel_run_releases_active_worker_leases(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Cancel active worker lease", "feature_delivery")
    prepared = service.compile_run(run.run_id)
    service.worker_lease_repo.create(
        WorkerLease(
            run_id=run.run_id,
            runtime_task_id=prepared.task_packet.runtime_task_id,
            adapter_name="shell",
            lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
    )

    cancelled = service.cancel_run(run.run_id)
    leases = service.list_worker_leases(run.run_id)

    assert cancelled.status == "cancelled"
    assert leases[0].status == "released"
    assert leases[0].release_reason == "run_cancelled"
    assert service.get_status_detail(run.run_id)["active_worker_leases"] == []


def test_inspection_can_release_non_running_active_claim(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Prepared active claim repair", "feature_delivery")
    prepared = service.compile_run(run.run_id)
    service.runtime_claim_repo.create(
        RuntimeClaim(
            run_id=run.run_id,
            runtime_task_id=prepared.task_packet.runtime_task_id,
            lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
    )

    inspection = service.inspect_run_state(run.run_id)
    repair = service.apply_run_repair(run.run_id, action="release_runtime_claim")
    claims = service.list_claims(run.run_id)

    assert inspection["passed"] is False
    assert inspection["problems"][0]["problem"] == "non_running_run_has_active_claim"
    assert inspection["problems"][0]["repair_action"] == "release_runtime_claim"
    assert repair["action"] == "release_runtime_claim"
    assert claims[0].status == "released"
    assert claims[0].release_reason == "reconciled_non_running_active_claim"
    assert service.inspect_run_state(run.run_id)["passed"] is True


def test_inspection_can_expire_stale_runtime_claim(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Prepared expired claim repair", "feature_delivery")
    prepared = service.compile_run(run.run_id)
    service.runtime_claim_repo.create(
        RuntimeClaim(
            run_id=run.run_id,
            runtime_task_id=prepared.task_packet.runtime_task_id,
            lease_expires_at=datetime.now(UTC) - timedelta(minutes=5),
        )
    )

    inspection = service.inspect_run_state(run.run_id)
    repair = service.apply_run_repair(run.run_id, action="expire_runtime_claim")
    claims = service.list_claims(run.run_id)

    assert inspection["passed"] is False
    assert {problem["problem"] for problem in inspection["problems"]} >= {
        "runtime_claim_expired",
        "non_running_run_has_active_claim",
    }
    assert repair["action"] == "expire_runtime_claim"
    assert claims[0].status == RuntimeClaimStatus.expired
    assert claims[0].release_reason == "reconciled_expired_claim"
    assert service.inspect_run_state(run.run_id)["passed"] is True


def test_inspection_can_release_non_running_active_worker_lease(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Prepared active worker lease repair", "feature_delivery")
    prepared = service.compile_run(run.run_id)
    service.worker_lease_repo.create(
        WorkerLease(
            run_id=run.run_id,
            runtime_task_id=prepared.task_packet.runtime_task_id,
            adapter_name="shell",
            lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
    )

    inspection = service.inspect_run_state(run.run_id)
    repair = service.apply_run_repair(run.run_id, action="release_worker_lease")
    leases = service.list_worker_leases(run.run_id)

    assert inspection["passed"] is False
    assert {problem["problem"] for problem in inspection["problems"]} >= {"non_running_run_has_active_worker_lease"}
    assert repair["action"] == "release_worker_lease"
    assert leases[0].status == "released"
    assert leases[0].release_reason == "reconciled_non_running_active_worker_lease"
    assert service.inspect_run_state(run.run_id)["passed"] is True


def test_inspection_can_expire_stale_worker_lease(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Prepared expired worker lease repair", "feature_delivery")
    prepared = service.compile_run(run.run_id)
    service.worker_lease_repo.create(
        WorkerLease(
            run_id=run.run_id,
            runtime_task_id=prepared.task_packet.runtime_task_id,
            adapter_name="shell",
            lease_expires_at=datetime.now(UTC) - timedelta(minutes=5),
        )
    )

    inspection = service.inspect_run_state(run.run_id)
    repair = service.apply_run_repair(run.run_id, action="expire_worker_lease")
    leases = service.list_worker_leases(run.run_id)

    assert inspection["passed"] is False
    assert {problem["problem"] for problem in inspection["problems"]} >= {
        "worker_lease_expired",
        "non_running_run_has_active_worker_lease",
    }
    assert repair["action"] == "expire_worker_lease"
    assert leases[0].status == WorkerLeaseStatus.expired
    assert leases[0].release_reason == "reconciled_expired_worker_lease"
    assert service.inspect_run_state(run.run_id)["passed"] is True


def test_recompile_supersedes_previous_current_attempt(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Recompile with attempt lineage", "feature_delivery")
    first_prepare = service.compile_run(run.run_id)
    second_prepare = service.recompile_run(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert first_prepare.task_packet.runtime_task_id != second_prepare.task_packet.runtime_task_id
    assert detail["current_runtime_attempt"]["trigger"] == "recompile"
    assert detail["current_runtime_attempt"]["runtime_task_id"] == second_prepare.task_packet.runtime_task_id
    assert detail["runtime_attempt_projection"]["attempt_count"] == 2
    assert len(detail["runtime_attempt_projection"]["superseded_attempt_ids"]) == 1


def test_inspection_can_create_repair_runtime_attempt(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Repair missing current attempt", "feature_delivery")
    prepared = service.compile_run(run.run_id)

    current_attempt = service.runtime_attempt_repo.current_for_run(run.run_id)
    assert current_attempt is not None
    service.runtime_attempt_repo.close(
        current_attempt.attempt_id,
        status=RuntimeAttemptStatus.interrupted,
        closed_at=prepared.run.updated_at.isoformat(),
        close_reason="test_missing_current_attempt",
    )

    inspection = service.inspect_run_state(run.run_id)
    assert inspection["passed"] is False
    assert {problem["problem"] for problem in inspection["problems"]} >= {"missing_current_runtime_attempt"}

    repair = service.apply_run_repair(run.run_id, action="create_repair_runtime_attempt")
    repaired_detail = service.get_status_detail(run.run_id)

    assert repair["applied"] is True
    assert repaired_detail["current_runtime_attempt"]["trigger"] == "repair"
    assert repaired_detail["current_runtime_attempt"]["runtime_task_id"] == prepared.task_packet.runtime_task_id


def test_inspection_can_interrupt_current_attempt_when_runtime_task_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Interrupt stale current attempt", "feature_delivery")
    service.compile_run(run.run_id)
    current_attempt = service.runtime_attempt_repo.current_for_run(run.run_id)
    assert current_attempt is not None

    with unit_of_work(db_path) as connection:
        service.task_repo.clear_for_run(run.run_id, connection=connection)

    inspection = service.inspect_run_state(run.run_id)
    assert inspection["passed"] is False
    assert {problem["problem"] for problem in inspection["problems"]} >= {"current_runtime_attempt_task_missing"}

    repair = service.apply_run_repair(run.run_id, action="interrupt_current_runtime_attempt")
    repaired_detail = service.get_status_detail(run.run_id)

    assert repair["applied"] is True
    assert repaired_detail["current_runtime_attempt"] is None
    assert repaired_detail["latest_runtime_attempt"]["status"] == "interrupted"


def test_compile_run_captures_compiled_snapshot(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Compile snapshot capture", "feature_delivery")
    prepared = service.compile_run(run.run_id)
    detail = service.get_status_detail(run.run_id)
    snapshots = service.list_snapshots(run.run_id)

    assert prepared.run.status == "prepared"
    assert len(snapshots) == 1
    assert snapshots[0].stage == RunSnapshotStage.compiled
    assert detail["snapshot_count"] == 1
    assert detail["latest_snapshot"]["stage"] == "compiled"
    assert detail["latest_snapshot"]["runtime_task_id"] == prepared.task_packet.runtime_task_id


def test_resume_run_captures_terminal_snapshot_for_auto_path(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Auto snapshot capture", "feature_delivery")
    service.compile_run(run.run_id)
    bundle = service.resume_run(run.run_id)
    snapshots = service.list_snapshots(run.run_id)
    inspection = service.inspect_run_state(run.run_id)

    assert bundle.run.status == "completed"
    assert [snapshot.stage for snapshot in snapshots] == [RunSnapshotStage.compiled, RunSnapshotStage.completed]
    assert inspection["latest_snapshot"]["stage"] == "completed"


def test_human_review_path_captures_wait_and_terminal_snapshots(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Human snapshot capture", "research_spike")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    waiting_detail = service.get_status_detail(run.run_id)
    service.approve_run_review(run.run_id)
    snapshots = service.list_snapshots(run.run_id)

    assert waiting_detail["latest_snapshot"]["stage"] == "awaiting_review"
    assert [snapshot.stage for snapshot in snapshots] == [
        RunSnapshotStage.compiled,
        RunSnapshotStage.awaiting_review,
        RunSnapshotStage.completed,
    ]


def test_cancel_and_repair_capture_snapshots(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    cancel_run = service.create_run("Cancel snapshot capture", "feature_delivery")
    service.compile_run(cancel_run.run_id)
    service.cancel_run(cancel_run.run_id)
    cancel_snapshots = service.list_snapshots(cancel_run.run_id)
    assert cancel_snapshots[-1].stage == RunSnapshotStage.cancelled

    repair_run = service.create_run("Repair snapshot capture", "feature_delivery")
    service.compile_run(repair_run.run_id)
    service.resume_run(repair_run.run_id)
    state_ref = service.runtime_state_repo.list_for_run(repair_run.run_id)[0]
    service.runtime_state_repo.upsert(
        RuntimeStateRef(
            state_ref_id=state_ref.state_ref_id,
            run_id=state_ref.run_id,
            runtime_task_id=state_ref.runtime_task_id,
            graph_step=RuntimeGraphStep.awaiting_review,
            state_payload={**state_ref.state_payload, "corrupted": True},
            is_terminal=False,
            created_at=state_ref.created_at,
        )
    )
    repair = service.apply_run_repair(repair_run.run_id)
    repair_snapshots = service.list_snapshots(repair_run.run_id)

    assert repair["action"] == "align_completed_runtime_state"
    assert repair_snapshots[-1].stage == RunSnapshotStage.repaired
    assert repair_snapshots[-1].snapshot_payload["repair_action"] == "align_completed_runtime_state"


def test_compile_run_creates_budget_ledger_projection(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Budget projection compile", "feature_delivery")
    service.compile_run(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert detail["budget_ledger"] is not None
    assert detail["budget_projection"]["max_retries"] == 1
    assert detail["budget_projection"]["remaining_retries"] == 1
    assert detail["budget_projection"]["compile_count"] == 1
    assert detail["budget_projection"]["execution_count"] == 0


def test_resume_run_records_budget_consumption(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Budget projection execute", "feature_delivery")
    service.compile_run(run.run_id)
    service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert detail["budget_projection"]["execution_count"] == 1
    assert detail["budget_projection"]["total_runtime_ms"] >= 0
    assert detail["budget_projection"]["last_return_code"] == 0


def test_recompile_run_enforces_retry_budget(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Budget exhausted recompile", "feature_delivery")
    service.compile_run(run.run_id)
    service.recompile_run(run.run_id)
    detail = service.get_status_detail(run.run_id)

    assert detail["budget_projection"]["remaining_retries"] == 0
    assert detail["budget_projection"]["recompile_count"] == 1

    with pytest.raises(BudgetExhaustedError):
        service.recompile_run(run.run_id)


def test_compile_and_resume_project_capability_envelope_and_receipt(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    run = service.create_run("Project capability contract projection", "feature_delivery")
    service.compile_run(run.run_id)
    compiled_detail = service.get_status_detail(run.run_id)

    assert compiled_detail["capability_invocation_envelope"] is not None
    assert compiled_detail["capability_invocation_envelope"]["authority_mode"] == "single_store_quorum"
    assert compiled_detail["capability_invocation_envelope"]["descriptor"]["provider_kind"] == "adapter_route"

    service.resume_run(run.run_id)
    detail = service.get_status_detail(run.run_id)
    audit_report = service.get_run_audit_report(run.run_id)

    assert detail["capability_execution_receipt"] is not None
    assert detail["capability_execution_receipt"]["status"] == "completed"
    assert detail["capability_execution_receipt"]["return_code"] == 0
    assert audit_report["capability_execution_receipt"]["envelope"]["authority_mode"] == "single_store_quorum"


def test_guarded_project_delivery_uses_shared_graph_substrate(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    preview = service.preview_orchestration_plan_graph(
        goal="Coordinate a guarded project delivery slice",
        preset_id="guarded_project_delivery",
    )
    launch = service.launch_goal(
        goal="Coordinate a guarded project delivery slice",
        preset_id="guarded_project_delivery",
        execute=False,
    )
    detail = service.get_status_detail(launch["run"]["run_id"])

    assert preview["selected_preset_id"] == "guarded_project_delivery"
    assert preview["plan_graph"]["execution_mode"] == "planner_generated_graph_with_parallel_children"
    assert len(preview["plan_graph"]["nodes"]) == 4
    assert len(preview["plan_graph"]["edges"]) >= 1
    assert len(preview["plan_graph"]["barriers"]) == 1
    assert len(preview["plan_graph"]["retry_policies"]) == 1
    assert detail["orchestration_plan_graph"]["preset_id"] == "guarded_project_delivery"
    assert detail["capability_invocation_envelope"]["authority_mode"] == "single_store_quorum"


def test_guarded_project_delivery_uses_shared_orchestration_plan_defaults(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()
    service = OrchestratorService(db_path)

    plan = service._default_orchestration_plan_for_preset("guarded_project_delivery", "preview_run")

    assert plan is not None
    assert plan.cluster_template_ids == ["dev_cluster"]
    assert str(plan.review_policy) == "mandatory"
    assert [step.role_label for step in plan.steps] == [
        "architect",
        "implementer",
        "risk_mapper",
        "quality_gate",
    ]
    assert "launch_guard" in [role.role_label for role in plan.roles]
    assert "launch_guard" not in [step.role_label for step in plan.steps]
    reviewer_step = next(step for step in plan.steps if step.role_label == "quality_gate")
    assert reviewer_step.preset_id == "guarded_delivery"
