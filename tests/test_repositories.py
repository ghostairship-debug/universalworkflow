from __future__ import annotations

from pathlib import Path

import pytest

from packages.contracts import (
    BudgetLedger,
    ChatMessage,
    ChatMessageRole,
    ChatMessageStatus,
    ChatStreamEvent,
    ChatStreamEventType,
    ChatMessageType,
    SchedulerLeaseDecision,
    SchedulerLeaseProposal,
    SchedulerPeerHeartbeat,
    HandoffLite,
    MemoryItem,
    MutationContract,
    MutationMode,
    Phase,
    Run,
    RunEvent,
    RunEventType,
    RunSnapshot,
    RunSnapshotStage,
    RuntimeAttempt,
    RuntimeAttemptStatus,
    RuntimeAttemptTrigger,
    RuntimeClaim,
    RuntimeStateRef,
    RuntimeTask,
    SimulationRecord,
    SimulationReport,
    SimulationTriggerPolicy,
    TaskCard,
    TaskKind,
    TaskPacket,
    WorkerLease,
)
from packages.core_domain.db import get_journal_mode, migrate, reset_db
from packages.core_domain.errors import DatabaseBusyError
from packages.core_domain.repositories import (
    BudgetLedgerRepository,
    ChatMessageRepository,
    ChatStreamEventRepository,
    EventRepository,
    HandoffRepository,
    MemoryItemRepository,
    PresetRepository,
    RuntimeAttemptRepository,
    RunSnapshotRepository,
    RuntimeClaimRepository,
    RunRepository,
    SchedulerLeaseDecisionRepository,
    SchedulerLeaseProposalRepository,
    SchedulerPeerHeartbeatRepository,
    SimulationRecordRepository,
    RuntimeStateRepository,
    TaskRepository,
    WorkerLeaseRepository,
)
from packages.core_domain.task_card_store import TaskCardStore, task_card_quality_report


def test_migrate_and_wal_mode(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    applied = migrate(db_path)
    assert "001_init.sql" in applied
    assert "002_m1_runtime_state_and_handoffs.sql" in applied
    assert "003_m2_runtime_claims.sql" in applied
    assert "004_m2_run_snapshots.sql" in applied
    assert "005_m2_budget_ledgers.sql" in applied
    assert "006_m2_worker_leases.sql" in applied
    assert "007_m2_runtime_attempts.sql" in applied
    assert "008_m6_memory_items.sql" in applied
    assert "009_m7_simulation_records.sql" in applied
    assert "010_m10_ownership_topology.sql" in applied
    assert "011_m16_repo_mutation_contracts.sql" in applied
    assert "012_m18_scheduler_authority.sql" in applied
    assert "026_m108_task_card_store.sql" in applied
    assert get_journal_mode(db_path) == "wal"

    second_apply = migrate(db_path)
    assert second_apply == []


def test_reset_db_reports_busy_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "workflow.db"
    db_path.write_text("busy", encoding="utf-8")

    def _busy_unlink(self, missing_ok: bool = False):  # type: ignore[override]
        raise PermissionError("db is locked")

    monkeypatch.setattr(Path, "unlink", _busy_unlink)

    with pytest.raises(DatabaseBusyError) as exc_info:
        reset_db(db_path)

    assert exc_info.value.code == "database_busy"
    assert exc_info.value.details["operation"] == "reset_db"


def test_memory_item_repository_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()

    run_repo = RunRepository(db_path)
    memory_repo = MemoryItemRepository(db_path)

    run = run_repo.create(Run(goal="Memory item round trip", preset_id="feature_delivery"))
    memory_item = memory_repo.create(
        MemoryItem(
            run_id=run.run_id,
            namespace_id="policy",
            source_candidate_id=f"memcand_{run.run_id}_policy",
            title="Policy memory item",
            summary="Persisted review-policy memory item",
            tags=["policy", "auto_only"],
            source_refs=[f"run:{run.run_id}", "verdict:none"],
        )
    )

    stored = memory_repo.get(memory_item.memory_item_id)
    assert stored is not None
    assert stored.namespace_id == "policy"
    assert stored.tags == ["policy", "auto_only"]

    duplicate = memory_repo.create(
        MemoryItem(
            run_id=run.run_id,
            namespace_id="policy",
            source_candidate_id=memory_item.source_candidate_id,
            title="Should dedupe",
            summary="Should not create a second item",
        )
    )
    assert duplicate.memory_item_id == memory_item.memory_item_id
    assert [item.memory_item_id for item in memory_repo.list_for_run(run.run_id)] == [memory_item.memory_item_id]
    assert [item.memory_item_id for item in memory_repo.list_for_namespace("policy")] == [memory_item.memory_item_id]


def test_chat_message_repository_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    chat_repo = ChatMessageRepository(db_path)

    first = chat_repo.create(
        ChatMessage(
            session_id="intent_session_chat",
            run_id="run_chat",
            role=ChatMessageRole.user,
            content="launch",
        )
    )
    second = chat_repo.create(
        ChatMessage(
            session_id="intent_session_chat",
            run_id="run_chat",
            role=ChatMessageRole.assistant,
            content="Confirm resume?",
            message_type=ChatMessageType.confirmation_required,
            action_type="resume_run",
            status=ChatMessageStatus.pending_confirmation,
            payload_json={"confirmation": {"action_type": "resume_run", "run_id": "run_chat"}},
        )
    )

    stored = chat_repo.get(second.message_id)
    assert stored is not None
    assert stored.action_type == "resume_run"
    assert stored.payload_json["confirmation"]["run_id"] == "run_chat"
    assert [item.message_id for item in chat_repo.list_for_session("intent_session_chat")] == [
        first.message_id,
        second.message_id,
    ]
    assert [item.message_id for item in chat_repo.list_for_session("intent_session_chat", after_message_id=first.message_id)] == [
        second.message_id,
    ]
    assert [item.message_id for item in chat_repo.list_for_run("run_chat")] == [first.message_id, second.message_id]

    updated = chat_repo.update_status(
        second.message_id,
        ChatMessageStatus.confirmed,
        payload_json={"confirmation": {"action_type": "resume_run"}, "result": {"status": "ok"}},
    )
    assert updated is not None
    assert updated.status == "confirmed"
    assert chat_repo.get(second.message_id).payload_json["result"]["status"] == "ok"  # type: ignore[union-attr]

    stream_repo = ChatStreamEventRepository(db_path)
    user_event = stream_repo.create(
        ChatStreamEvent(
            session_id="intent_session_chat",
            run_id="run_chat",
            message_id=first.message_id,
            event_type=ChatStreamEventType.user_message,
            payload_json=first.model_dump(mode="json"),
        )
    )
    delta_event = stream_repo.create(
        ChatStreamEvent(
            session_id="intent_session_chat",
            run_id="run_chat",
            message_id=second.message_id,
            event_type=ChatStreamEventType.assistant_delta,
            payload_json={"message_id": second.message_id, "delta": "Confirm"},
        )
    )

    assert [item.event_id for item in stream_repo.list_for_session("intent_session_chat")] == [
        user_event.event_id,
        delta_event.event_id,
    ]
    assert [item.event_id for item in stream_repo.list_for_session("intent_session_chat", after_event_id=user_event.event_id)] == [
        delta_event.event_id,
    ]
    assert stream_repo.list_for_session("intent_session_chat", after_event_id="heartbeat:intent_session_chat") == []
    assert user_event.sequence_no == 1
    assert delta_event.sequence_no == 2


def test_simulation_record_repository_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()

    run_repo = RunRepository(db_path)
    simulation_repo = SimulationRecordRepository(db_path)

    run = run_repo.create(Run(goal="Simulation record round trip", preset_id="feature_delivery"))
    report = SimulationReport(
        run_id=run.run_id,
        preset_id=run.preset_id,
        policy_id="delivery_consistency_simulation",
        trigger_policy=SimulationTriggerPolicy.always,
        simulator_name="local_consistency_check",
        triggered=True,
        status="passed",
        reason="triggered_by_always_policy",
        summary="Simulation passed.",
        check_results=[],
    )
    record = simulation_repo.create(
        SimulationRecord(
            run_id=run.run_id,
            policy_id=report.policy_id,
            status=report.status,
            triggered=report.triggered,
            summary=report.summary,
            report=report,
        )
    )

    stored = simulation_repo.get(record.record_id)
    assert stored is not None
    assert stored.policy_id == "delivery_consistency_simulation"
    assert stored.report.status == "passed"
    assert [item.record_id for item in simulation_repo.list_for_run(run.run_id)] == [record.record_id]
    assert simulation_repo.latest_for_run(run.run_id).record_id == record.record_id


def test_seed_presets_into_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)

    presets = PresetRepository(db_path).seed_defaults()
    stored = PresetRepository(db_path).list()

    assert len(presets) == 8
    assert [preset.preset_id for preset in stored] == [
        "advisory_delivery",
        "feature_delivery",
        "guarded_delivery",
        "guarded_project_delivery",
        "optional_delivery",
        "project_delivery",
        "research_spike",
        "research_spike_reviewable",
    ]


def test_run_task_and_timeline_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()

    run_repo = RunRepository(db_path)
    task_repo = TaskRepository(db_path)
    event_repo = EventRepository(db_path)

    run = run_repo.create(Run(goal="Create one task", preset_id="feature_delivery"))
    phase = task_repo.create_phase(Phase(run_id=run.run_id, name="compile", order_index=0))
    task_card = task_repo.create_task_card(
        TaskCard(
            run_id=run.run_id,
            title="Write one artifact",
            description="Create a single task packet",
            acceptance_criteria=["runtime task exists"],
        )
    )
    runtime_task = task_repo.create_runtime_task(
        RuntimeTask(
            run_id=run.run_id,
            phase_id=phase.phase_id,
            task_card_id=task_card.task_card_id,
            task_kind=TaskKind.shell_exec,
            summary="Compile a single shell task",
        )
    )
    task_repo.create_task_packet(
        TaskPacket(
            runtime_task_id=runtime_task.runtime_task_id,
            run_id=run.run_id,
            task_kind=TaskKind.shell_exec,
            command=["python", "-c", "print('ok')"],
            working_directory=".",
            mutation_contract=MutationContract(
                task_card_ref="M16-1A",
                write_set=["README.md"],
                test_commands=["python -m pytest -q"],
                mutation_mode=MutationMode.patch_apply,
            ),
        )
    )

    event_repo.append(
        RunEvent(
            run_id=run.run_id,
            event_type=RunEventType.run_created,
            object_type="run",
            object_id=run.run_id,
            summary="Run created",
            payload_json={"goal": run.goal, "preset_id": run.preset_id},
        )
    )
    event_repo.append(
        RunEvent(
            run_id=run.run_id,
            event_type=RunEventType.runtime_task_created,
            object_type="runtime_task",
            object_id=runtime_task.runtime_task_id,
            summary="Task created",
            payload_json={
                "runtime_task_id": runtime_task.runtime_task_id,
                "task_kind": runtime_task.task_kind,
                "summary": runtime_task.summary,
            },
        )
    )

    events = event_repo.list_for_run(run.run_id)
    assert [event.event_type for event in events] == [
        RunEventType.run_created,
        RunEventType.runtime_task_created,
    ]
    assert "stdout" not in events[1].payload_json
    stored_packet = task_repo.get_task_packet(runtime_task.runtime_task_id)
    assert stored_packet is not None
    assert stored_packet.mutation_contract is not None
    assert stored_packet.mutation_contract.mutation_mode == "patch_apply"


def test_rich_task_card_store_round_trip_and_markdown_export(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    run = RunRepository(db_path).create(Run(goal="Create rich task cards", preset_id="feature_delivery"))
    card = TaskRepository(db_path).create_task_card(
        TaskCard(
            schema_version="m108_task_card_v2",
            run_id=run.run_id,
            title="Tighten task card storage",
            description="Store task cards in the database with enough execution detail for a model to act safely.",
            acceptance_criteria=["database row is complete", "markdown export is generated"],
            milestone="M108.5",
            phase_name="task-card-store",
            goal="Move task cards to the DB as source of truth and export markdown as a human snapshot.",
            write_set=["packages/core_domain/task_card_store.py"],
            read_set=["CURRENT_DEVELOPMENT_WORKFLOW.md"],
            test_commands=["python -m pytest tests/test_repositories.py -q"],
            evidence_requirements=["quality report", "markdown snapshot"],
            blocking_conditions=["DB migration fails"],
            model_guidance=["Use the structured fields before editing files."],
            risk_level="medium",
            provider_lane="codex",
            execution_mode="patch_apply",
            status="ready",
        )
    )

    stored = TaskRepository(db_path).get_task_card(card.task_card_id)
    assert stored is not None
    assert stored.write_set == ["packages/core_domain/task_card_store.py"]
    assert stored.milestone == "M108.5"
    assert task_card_quality_report([stored])["go_no_go"] == "GO"

    export = TaskCardStore(db_path).export_run_markdown(run.run_id, tmp_path / "task_cards.md")
    exported = Path(export["output_path"]).read_text(encoding="utf-8")
    assert "Generated from the workflow task card database" in exported
    assert "Tighten task card storage" in exported


def test_run_repository_lists_recent_runs_in_updated_order(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()

    run_repo = RunRepository(db_path)
    first = run_repo.create(Run(goal="First run", preset_id="feature_delivery"))
    second = run_repo.create(Run(goal="Second run", preset_id="research_spike"))
    run_repo.update_status(first.run_id, "prepared")

    listed = run_repo.list(limit=2)

    assert [run.run_id for run in listed] == [first.run_id, second.run_id]


def test_handoff_and_runtime_state_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()

    run_repo = RunRepository(db_path)
    task_repo = TaskRepository(db_path)
    handoff_repo = HandoffRepository(db_path)
    state_repo = RuntimeStateRepository(db_path)

    run = run_repo.create(Run(goal="Create one task", preset_id="feature_delivery"))
    phase_a = task_repo.create_phase(Phase(run_id=run.run_id, name="compile", order_index=0))
    phase_b = task_repo.create_phase(Phase(run_id=run.run_id, name="execute", order_index=1))
    task_card = task_repo.create_task_card(
        TaskCard(
            run_id=run.run_id,
            title="Execute one shell task",
            description="Create a single runtime task",
            acceptance_criteria=["runtime task exists"],
        )
    )
    runtime_task = task_repo.create_runtime_task(
        RuntimeTask(
            run_id=run.run_id,
            phase_id=phase_b.phase_id,
            task_card_id=task_card.task_card_id,
            task_kind=TaskKind.shell_exec,
            summary="Compile a single shell task",
        )
    )
    runtime_task_terminal = task_repo.create_runtime_task(
        RuntimeTask(
            run_id=run.run_id,
            phase_id=phase_b.phase_id,
            task_card_id=task_card.task_card_id,
            task_kind=TaskKind.noop,
            summary="Record a noop terminal task",
        )
    )
    handoff = handoff_repo.create(
        HandoffLite(
            run_id=run.run_id,
            from_phase_id=phase_a.phase_id,
            to_phase_id=phase_b.phase_id,
            summary="compile to execution handoff",
        )
    )
    state = state_repo.upsert(
        RuntimeStateRef(
            run_id=run.run_id,
            runtime_task_id=runtime_task.runtime_task_id,
            graph_step="compiled",
            state_payload={"entrypoint": "resume"},
        )
    )
    terminal_state = state_repo.upsert(
        RuntimeStateRef(
            run_id=run.run_id,
            runtime_task_id=runtime_task_terminal.runtime_task_id,
            graph_step="completed",
            state_payload={"entrypoint": "noop"},
            is_terminal=True,
        )
    )

    stored_handoffs = handoff_repo.list_for_run(run.run_id)
    stored_states = state_repo.list_for_run(run.run_id)
    latest_state = state_repo.latest_for_run(run.run_id)
    live_states = state_repo.list_live_for_run(run.run_id)
    terminal_states = state_repo.list_terminal_for_run(run.run_id)

    assert stored_handoffs[0].handoff_id == handoff.handoff_id
    assert {item.runtime_task_id for item in stored_states} == {
        runtime_task.runtime_task_id,
        runtime_task_terminal.runtime_task_id,
    }
    assert {item.runtime_task_id for item in live_states} == {runtime_task.runtime_task_id}
    assert {item.runtime_task_id for item in terminal_states} == {runtime_task_terminal.runtime_task_id}
    assert latest_state is not None
    assert latest_state.runtime_task_id == terminal_state.runtime_task_id
    assert latest_state.graph_step == "completed"


def test_repository_methods_support_injected_connection(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    run_repo = RunRepository(db_path)

    from packages.core_domain.db import unit_of_work

    with unit_of_work(db_path) as connection:
        run = run_repo.create(Run(goal="Injected connection", preset_id="feature_delivery"), connection=connection)
        updated = run_repo.update_status(run.run_id, "prepared", connection=connection)
        assert updated is not None
        assert updated.status == "prepared"


def test_runtime_claim_repository_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()

    run_repo = RunRepository(db_path)
    task_repo = TaskRepository(db_path)
    claim_repo = RuntimeClaimRepository(db_path)

    run = run_repo.create(Run(goal="Claim round trip", preset_id="feature_delivery"))
    phase = task_repo.create_phase(Phase(run_id=run.run_id, name="execute", order_index=0))
    task_card = task_repo.create_task_card(
        TaskCard(
            run_id=run.run_id,
            title="Create one claimed task",
            description="Persist one runtime task for claim tests",
            acceptance_criteria=["claim exists"],
        )
    )
    runtime_task = task_repo.create_runtime_task(
        RuntimeTask(
            run_id=run.run_id,
            phase_id=phase.phase_id,
            task_card_id=task_card.task_card_id,
            task_kind=TaskKind.shell_exec,
            summary="Claimed task",
        )
    )
    claim = claim_repo.create(
        RuntimeClaim(
            run_id=run.run_id,
            runtime_task_id=runtime_task.runtime_task_id,
            lease_expires_at=run.created_at,
        )
    )

    active_claim = claim_repo.get_active_for_task(runtime_task.runtime_task_id)
    assert active_claim is not None
    assert active_claim.claim_id == claim.claim_id
    assert active_claim.owner_kind == "control_plane"
    assert active_claim.owner_id == "control_plane_local"
    assert active_claim.domain_kind == "runtime_task"
    assert active_claim.domain_key == runtime_task.runtime_task_id
    assert {item.claim_id for item in claim_repo.list_active_for_run(run.run_id)} == {claim.claim_id}

    released = claim_repo.release(
        claim.claim_id,
        released_at=run.created_at.isoformat(),
        release_reason="completed",
    )
    assert released is not None
    assert released.status == "released"
    assert released.release_reason == "completed"
    assert claim_repo.get_active_for_task(runtime_task.runtime_task_id) is None
    assert len(claim_repo.list_for_run(run.run_id)) == 1


def test_run_snapshot_repository_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()

    run_repo = RunRepository(db_path)
    snapshot_repo = RunSnapshotRepository(db_path)

    run = run_repo.create(Run(goal="Snapshot round trip", preset_id="feature_delivery"))
    compile_snapshot = snapshot_repo.create(
        RunSnapshot(
            run_id=run.run_id,
            stage=RunSnapshotStage.compiled,
            run_status="prepared",
            summary="Compile snapshot",
            snapshot_payload={"next_action": "resume_run"},
        )
    )
    terminal_snapshot = snapshot_repo.create(
        RunSnapshot(
            run_id=run.run_id,
            stage=RunSnapshotStage.completed,
            run_status="completed",
            summary="Terminal snapshot",
            snapshot_payload={"review_state": "auto_passed"},
        )
    )

    stored = snapshot_repo.list_for_run(run.run_id)
    latest = snapshot_repo.latest_for_run(run.run_id)

    assert [item.snapshot_id for item in stored] == [compile_snapshot.snapshot_id, terminal_snapshot.snapshot_id]
    assert latest is not None
    assert latest.snapshot_id == terminal_snapshot.snapshot_id
    assert latest.snapshot_payload["review_state"] == "auto_passed"


def test_budget_ledger_repository_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()

    run_repo = RunRepository(db_path)
    ledger_repo = BudgetLedgerRepository(db_path)

    run = run_repo.create(Run(goal="Budget ledger round trip", preset_id="feature_delivery"))
    ledger = ledger_repo.create(
        BudgetLedger(
            run_id=run.run_id,
            preset_id=run.preset_id,
            max_retries=2,
            timeout_seconds=300,
            compile_count=1,
        )
    )

    stored = ledger_repo.get_by_run(run.run_id)
    assert stored is not None
    assert stored.ledger_id == ledger.ledger_id
    assert stored.recompile_count == 0

    updated = ledger_repo.update(
        BudgetLedger.model_validate(
            {
                **stored.model_dump(mode="json"),
                "compile_count": 2,
                "recompile_count": 1,
                "execution_count": 1,
                "total_runtime_ms": 42,
                "last_return_code": 0,
            }
        )
    )

    assert updated.compile_count == 2
    assert updated.recompile_count == 1
    assert updated.execution_count == 1
    assert updated.total_runtime_ms == 42
    assert updated.last_return_code == 0


def test_worker_lease_repository_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()

    run_repo = RunRepository(db_path)
    task_repo = TaskRepository(db_path)
    lease_repo = WorkerLeaseRepository(db_path)

    run = run_repo.create(Run(goal="Worker lease round trip", preset_id="feature_delivery"))
    phase = task_repo.create_phase(Phase(run_id=run.run_id, name="execute", order_index=0))
    task_card = task_repo.create_task_card(
        TaskCard(
            run_id=run.run_id,
            title="Create one leased task",
            description="Persist one runtime task for worker-lease tests",
            acceptance_criteria=["worker lease exists"],
        )
    )
    runtime_task = task_repo.create_runtime_task(
        RuntimeTask(
            run_id=run.run_id,
            phase_id=phase.phase_id,
            task_card_id=task_card.task_card_id,
            task_kind=TaskKind.shell_exec,
            summary="Leased task",
        )
    )
    lease = lease_repo.create(
        WorkerLease(
            run_id=run.run_id,
            runtime_task_id=runtime_task.runtime_task_id,
            adapter_name="shell",
            lease_expires_at=run.created_at,
        )
    )

    active_lease = lease_repo.get_active_for_task(runtime_task.runtime_task_id)
    assert active_lease is not None
    assert active_lease.lease_id == lease.lease_id
    assert active_lease.worker_kind == "worker"
    assert active_lease.worker_id == "worker_local"
    assert active_lease.domain_kind == "runtime_task"
    assert active_lease.domain_key == runtime_task.runtime_task_id
    assert {item.lease_id for item in lease_repo.list_active_for_run(run.run_id)} == {lease.lease_id}

    released = lease_repo.release(
        lease.lease_id,
        released_at=run.created_at.isoformat(),
        release_reason="completed",
    )
    assert released is not None
    assert released.status == "released"
    assert released.release_reason == "completed"
    assert lease_repo.get_active_for_task(runtime_task.runtime_task_id) is None
    assert len(lease_repo.list_for_run(run.run_id)) == 1


def test_scheduler_authority_repositories_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()

    run_repo = RunRepository(db_path)
    task_repo = TaskRepository(db_path)
    proposal_repo = SchedulerLeaseProposalRepository(db_path)
    decision_repo = SchedulerLeaseDecisionRepository(db_path)
    heartbeat_repo = SchedulerPeerHeartbeatRepository(db_path)

    run = run_repo.create(Run(goal="Scheduler authority round trip", preset_id="feature_delivery"))
    phase = task_repo.create_phase(Phase(run_id=run.run_id, name="authority", order_index=0))
    task_card = task_repo.create_task_card(
        TaskCard(
            run_id=run.run_id,
            title="Persist scheduler authority state",
            description="Create one runtime task and authority lease records",
            acceptance_criteria=["scheduler authority rows exist"],
        )
    )
    runtime_task = task_repo.create_runtime_task(
        RuntimeTask(
            run_id=run.run_id,
            phase_id=phase.phase_id,
            task_card_id=task_card.task_card_id,
            task_kind=TaskKind.shell_exec,
            summary="Authority task",
        )
    )

    proposal = proposal_repo.create(
        SchedulerLeaseProposal(
            control_plane_id="control_plane_alpha",
            run_id=run.run_id,
            runtime_task_id=runtime_task.runtime_task_id,
            domain_key=runtime_task.runtime_task_id,
            requested_lease_seconds=120,
        )
    )
    decision = decision_repo.create(
        SchedulerLeaseDecision(
            proposal_id=proposal.proposal_id,
            control_plane_id="control_plane_alpha",
            run_id=run.run_id,
            runtime_task_id=runtime_task.runtime_task_id,
            domain_key=runtime_task.runtime_task_id,
            lease_epoch=1,
            lease_expires_at=run.created_at,
        )
    )
    heartbeat = heartbeat_repo.create(
        SchedulerPeerHeartbeat(
            control_plane_id="control_plane_alpha",
            lease_count=1,
            observed_at=run.created_at,
        )
    )

    assert proposal_repo.get(proposal.proposal_id) is not None
    active = decision_repo.get_active_for_domain(
        "runtime_task",
        runtime_task.runtime_task_id,
        now_iso=(run.created_at.replace(year=run.created_at.year - 1)).isoformat(),
    )
    assert active is not None
    assert active.lease_id == decision.lease_id
    latest = heartbeat_repo.latest_for_control_plane("control_plane_alpha")
    assert latest is not None
    assert latest.heartbeat_id == heartbeat.heartbeat_id

    released = decision_repo.release(
        decision.lease_id,
        released_at=run.created_at.isoformat(),
        release_reason="test_release",
    )
    assert released is not None
    assert released.release_reason == "test_release"
    assert decision_repo.get(decision.lease_id) is not None


def test_runtime_attempt_repository_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    PresetRepository(db_path).seed_defaults()

    run_repo = RunRepository(db_path)
    task_repo = TaskRepository(db_path)
    attempt_repo = RuntimeAttemptRepository(db_path)

    run = run_repo.create(Run(goal="Runtime attempt round trip", preset_id="feature_delivery"))
    phase = task_repo.create_phase(Phase(run_id=run.run_id, name="execute", order_index=0))
    task_card = task_repo.create_task_card(
        TaskCard(
            run_id=run.run_id,
            title="Create runtime attempts",
            description="Persist runtime attempts for lineage tests",
            acceptance_criteria=["runtime attempts exist"],
        )
    )
    runtime_task_a = task_repo.create_runtime_task(
        RuntimeTask(
            run_id=run.run_id,
            phase_id=phase.phase_id,
            task_card_id=task_card.task_card_id,
            task_kind=TaskKind.shell_exec,
            summary="Attempt A task",
        )
    )
    runtime_task_b = task_repo.create_runtime_task(
        RuntimeTask(
            run_id=run.run_id,
            phase_id=phase.phase_id,
            task_card_id=task_card.task_card_id,
            task_kind=TaskKind.noop,
            summary="Attempt B task",
        )
    )

    attempt_a = attempt_repo.create(
        RuntimeAttempt(
            run_id=run.run_id,
            runtime_task_id=runtime_task_a.runtime_task_id,
            sequence_no=attempt_repo.next_sequence_for_run(run.run_id),
            trigger=RuntimeAttemptTrigger.compile,
        )
    )

    assert attempt_repo.current_for_run(run.run_id) is not None
    assert attempt_repo.current_for_run(run.run_id).attempt_id == attempt_a.attempt_id

    attempt_b = RuntimeAttempt(
        run_id=run.run_id,
        runtime_task_id=runtime_task_b.runtime_task_id,
        sequence_no=attempt_repo.next_sequence_for_run(run.run_id),
        trigger=RuntimeAttemptTrigger.recompile,
    )
    superseded_a = attempt_repo.supersede(
        attempt_a.attempt_id,
        superseded_by_attempt_id=attempt_b.attempt_id,
        superseded_at=run.created_at.isoformat(),
        supersede_reason="recompile",
    )
    attempt_b = attempt_repo.create(attempt_b)

    assert superseded_a is not None
    assert superseded_a.status == "superseded"
    assert superseded_a.superseded_by_attempt_id == attempt_b.attempt_id
    assert attempt_repo.latest_for_run(run.run_id) is not None
    assert attempt_repo.latest_for_run(run.run_id).attempt_id == attempt_b.attempt_id
    assert attempt_repo.current_for_run(run.run_id) is not None
    assert attempt_repo.current_for_run(run.run_id).attempt_id == attempt_b.attempt_id
    assert {item.attempt_id for item in attempt_repo.list_superseded_for_run(run.run_id)} == {attempt_a.attempt_id}

    closed_b = attempt_repo.close(
        attempt_b.attempt_id,
        status=RuntimeAttemptStatus.interrupted,
        closed_at=run.created_at.isoformat(),
        close_reason="worker_lease_expired",
    )

    assert closed_b is not None
    assert closed_b.status == "interrupted"
    assert closed_b.close_reason == "worker_lease_expired"
    assert attempt_repo.current_for_run(run.run_id) is None
    assert [item.sequence_no for item in attempt_repo.list_for_run(run.run_id)] == [1, 2]
    assert [item.attempt_id for item in attempt_repo.list_for_task(runtime_task_a.runtime_task_id)] == [attempt_a.attempt_id]
    assert attempt_repo.next_sequence_for_run(run.run_id) == 3


def test_reset_db_removes_sqlite_file(tmp_path: Path) -> None:
    db_path = tmp_path / "workflow.db"
    migrate(db_path)
    assert db_path.exists()
    reset_db(db_path)
    assert not db_path.exists()
