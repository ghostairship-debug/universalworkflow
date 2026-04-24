from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contracts import (
    AutomationWatchdog,
    BudgetLedger,
    ChatMessage,
    ChatMessageStatus,
    ChatStreamEvent,
    ControlPlaneIdentity,
    Evidence,
    FollowupRequest,
    GeneratedAgentProfile,
    HandoffLite,
    IntentSession,
    MemoryItem,
    Phase,
    PresetDefinition,
    ReviewVerdict,
    Run,
    RunEvent,
    SchedulerLeaseDecision,
    SchedulerLeaseProposal,
    SchedulerPeerHeartbeat,
    SimulationRecord,
    RuntimeAttempt,
    RunSnapshot,
    RuntimeClaim,
    RuntimeStateRef,
    RuntimeTask,
    WorkerLease,
    TaskCard,
    TaskPacket,
    TaskStatus,
    validate_event_payload,
)
from packages.core_domain.db import DEFAULT_DB_PATH, get_connection
from packages.core_domain.presets import load_seed_presets


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_load(value: str) -> Any:
    return json.loads(value)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class RepositoryBase:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH

    @contextmanager
    def _connection(self, connection: sqlite3.Connection | None = None, commit: bool = False):
        if connection is not None:
            yield connection
            return
        with get_connection(self.db_path) as managed:
            try:
                yield managed
                if commit:
                    managed.commit()
            except Exception:
                if commit:
                    managed.rollback()
                raise


class RunRepository(RepositoryBase):
    def create(self, run: Run, connection: sqlite3.Connection | None = None) -> Run:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO runs (run_id, goal, preset_id, status, schema_version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.goal,
                    run.preset_id,
                    run.status,
                    run.schema_version,
                    run.created_at.isoformat(),
                    run.updated_at.isoformat(),
                ),
            )
        return run

    def get(self, run_id: str, connection: sqlite3.Connection | None = None) -> Run | None:
        with self._connection(connection) as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return Run.model_validate(dict(row)) if row else None

    def list(
        self,
        limit: int | None = None,
        *,
        status: str | None = None,
        preset_id: str | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> list[Run]:
        query = "SELECT * FROM runs"
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if preset_id is not None:
            clauses.append("preset_id = ?")
            params.append(preset_id)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY updated_at DESC, created_at DESC, run_id DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        with self._connection(connection) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [Run.model_validate(dict(row)) for row in rows]

    def update_status(self, run_id: str, status: str, connection: sqlite3.Connection | None = None) -> Run | None:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                "UPDATE runs SET status = ?, updated_at = ? WHERE run_id = ?",
                (status, _utc_now_iso(), run_id),
            )
        return self.get(run_id, connection=connection)


class PresetRepository(RepositoryBase):
    def upsert(self, preset: PresetDefinition, connection: sqlite3.Connection | None = None) -> PresetDefinition:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO preset_definitions (
                  preset_id, name, description, allowed_task_kinds_json, default_review_policy,
                  default_budget_policy_json, requires_manual_approval, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    preset.preset_id,
                    preset.name,
                    preset.description,
                    _json_dump(preset.allowed_task_kinds),
                    preset.default_review_policy,
                    _json_dump(preset.default_budget_policy.model_dump(mode="json")),
                    1 if preset.requires_manual_approval else 0,
                    preset.schema_version,
                    preset.created_at.isoformat(),
                ),
            )
        return preset

    def seed_defaults(self, connection: sqlite3.Connection | None = None) -> list[PresetDefinition]:
        presets = load_seed_presets()
        for preset in presets:
            self.upsert(preset, connection=connection)
        return presets

    def get(self, preset_id: str, connection: sqlite3.Connection | None = None) -> PresetDefinition | None:
        with self._connection(connection) as conn:
            row = conn.execute("SELECT * FROM preset_definitions WHERE preset_id = ?", (preset_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_model(row)

    def list(self, connection: sqlite3.Connection | None = None) -> list[PresetDefinition]:
        with self._connection(connection) as conn:
            rows = conn.execute("SELECT * FROM preset_definitions ORDER BY preset_id").fetchall()
        return [self._row_to_model(row) for row in rows]

    def _row_to_model(self, row: Any) -> PresetDefinition:
        data = dict(row)
        data["allowed_task_kinds"] = _json_load(data.pop("allowed_task_kinds_json"))
        data["default_budget_policy"] = _json_load(data.pop("default_budget_policy_json"))
        data["requires_manual_approval"] = bool(data["requires_manual_approval"])
        seed_defaults = {preset.preset_id: preset for preset in load_seed_presets()}
        seeded = seed_defaults.get(data["preset_id"])
        if seeded is not None and seeded.execution_profile is not None:
            data["execution_profile"] = seeded.execution_profile.model_dump(mode="json")
        return PresetDefinition.model_validate(data)


class IntentSessionRepository(RepositoryBase):
    def upsert(self, session: IntentSession, connection: sqlite3.Connection | None = None) -> IntentSession:
        payload = session.model_dump(mode="json")
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO intent_sessions (
                  session_id, goal, status, active_run_id, payload_json, schema_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.intent_packet.goal,
                    str(session.status),
                    session.active_run_id,
                    _json_dump(payload),
                    session.schema_version,
                    session.created_at.isoformat(),
                    _utc_now_iso(),
                ),
            )
        return session

    def get(self, session_id: str, connection: sqlite3.Connection | None = None) -> IntentSession | None:
        with self._connection(connection) as conn:
            row = conn.execute("SELECT payload_json FROM intent_sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        return IntentSession.model_validate(_json_load(row["payload_json"]))

    def list(
        self,
        *,
        limit: int | None = None,
        status: str | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> list[IntentSession]:
        query = "SELECT payload_json FROM intent_sessions"
        params: list[Any] = []
        if status is not None:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC, session_id DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        with self._connection(connection) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [IntentSession.model_validate(_json_load(row["payload_json"])) for row in rows]


class FollowupRequestRepository(RepositoryBase):
    def create(
        self,
        request: FollowupRequest,
        connection: sqlite3.Connection | None = None,
    ) -> FollowupRequest:
        payload = request.model_dump(mode="json")
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO followup_requests (
                  request_id, session_id, run_id, intent, blocking, status, instruction, payload_json,
                  schema_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request.request_id,
                    request.session_id,
                    request.run_id,
                    request.intent,
                    1 if request.blocking else 0,
                    request.status,
                    request.instruction,
                    _json_dump(payload),
                    request.schema_version,
                    request.created_at.isoformat(),
                    _utc_now_iso(),
                ),
            )
        return request

    def list_for_session(
        self,
        session_id: str,
        *,
        limit: int | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> list[FollowupRequest]:
        query = "SELECT payload_json FROM followup_requests WHERE session_id = ? ORDER BY created_at DESC, request_id DESC"
        params: list[Any] = [session_id]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        with self._connection(connection) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [FollowupRequest.model_validate(_json_load(row["payload_json"])) for row in rows]

    def list_for_run(
        self,
        run_id: str,
        *,
        limit: int | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> list[FollowupRequest]:
        query = "SELECT payload_json FROM followup_requests WHERE run_id = ? ORDER BY created_at DESC, request_id DESC"
        params: list[Any] = [run_id]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        with self._connection(connection) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [FollowupRequest.model_validate(_json_load(row["payload_json"])) for row in rows]


class ChatMessageRepository(RepositoryBase):
    def create(
        self,
        message: ChatMessage,
        connection: sqlite3.Connection | None = None,
    ) -> ChatMessage:
        payload = message.model_dump(mode="json")
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO chat_messages (
                  message_id, session_id, run_id, role, content, message_type, action_type, status, payload_json,
                  schema_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.message_id,
                    message.session_id,
                    message.run_id,
                    str(message.role),
                    message.content,
                    str(message.message_type),
                    message.action_type,
                    str(message.status),
                    _json_dump(payload),
                    message.schema_version,
                    message.created_at.isoformat(),
                    _utc_now_iso(),
                ),
            )
        return message

    def get(self, message_id: str, connection: sqlite3.Connection | None = None) -> ChatMessage | None:
        with self._connection(connection) as conn:
            row = conn.execute("SELECT payload_json FROM chat_messages WHERE message_id = ?", (message_id,)).fetchone()
        if row is None:
            return None
        return ChatMessage.model_validate(_json_load(row["payload_json"]))

    def list_for_session(
        self,
        session_id: str,
        *,
        limit: int | None = None,
        after_message_id: str | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> list[ChatMessage]:
        query = "SELECT payload_json FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC, message_id ASC"
        params: list[Any] = [session_id]
        if limit is not None and after_message_id is None:
            query += " LIMIT ?"
            params.append(limit)
        with self._connection(connection) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        messages = [ChatMessage.model_validate(_json_load(row["payload_json"])) for row in rows]
        if after_message_id is not None:
            for index, message in enumerate(messages):
                if message.message_id == after_message_id:
                    messages = messages[index + 1 :]
                    break
        if limit is not None and after_message_id is not None:
            return messages[:limit]
        return messages

    def list_for_run(
        self,
        run_id: str,
        *,
        limit: int | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> list[ChatMessage]:
        query = "SELECT payload_json FROM chat_messages WHERE run_id = ? ORDER BY created_at ASC, message_id ASC"
        params: list[Any] = [run_id]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        with self._connection(connection) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [ChatMessage.model_validate(_json_load(row["payload_json"])) for row in rows]

    def update_status(
        self,
        message_id: str,
        status: ChatMessageStatus | str,
        *,
        payload_json: dict[str, Any] | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> ChatMessage | None:
        message = self.get(message_id, connection=connection)
        if message is None:
            return None
        message.status = ChatMessageStatus(status)
        if payload_json is not None:
            message.payload_json = payload_json
        payload = message.model_dump(mode="json")
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                UPDATE chat_messages
                SET status = ?, payload_json = ?, updated_at = ?
                WHERE message_id = ?
                """,
                (
                    str(message.status),
                    _json_dump(payload),
                    _utc_now_iso(),
                    message_id,
                ),
            )
        return message


class ChatStreamEventRepository(RepositoryBase):
    def create(
        self,
        event: ChatStreamEvent,
        connection: sqlite3.Connection | None = None,
    ) -> ChatStreamEvent:
        if event.sequence_no == 0:
            event.sequence_no = self.next_sequence_no(event.session_id, connection=connection)
        payload = event.model_dump(mode="json")
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO chat_stream_events (
                  event_id, session_id, run_id, message_id, event_type, sequence_no,
                  payload_json, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.session_id,
                    event.run_id,
                    event.message_id,
                    str(event.event_type),
                    event.sequence_no,
                    _json_dump(payload),
                    event.schema_version,
                    event.created_at.isoformat(),
                ),
            )
        return event

    def next_sequence_no(self, session_id: str, connection: sqlite3.Connection | None = None) -> int:
        with self._connection(connection) as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(sequence_no), 0) AS max_sequence_no FROM chat_stream_events WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return int(row["max_sequence_no"]) + 1 if row is not None else 1

    def list_for_session(
        self,
        session_id: str,
        *,
        limit: int | None = None,
        after_event_id: str | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> list[ChatStreamEvent]:
        query = "SELECT payload_json FROM chat_stream_events WHERE session_id = ? ORDER BY sequence_no ASC, event_id ASC"
        params: list[Any] = [session_id]
        with self._connection(connection) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        events = [ChatStreamEvent.model_validate(_json_load(row["payload_json"])) for row in rows]
        if after_event_id is not None:
            found_event_id = False
            for index, event in enumerate(events):
                if event.event_id == after_event_id:
                    found_event_id = True
                    events = events[index + 1 :]
                    break
            if not found_event_id:
                events = []
        if limit is not None:
            return events[:limit]
        return events


class GeneratedAgentProfileRepository(RepositoryBase):
    def create(
        self,
        profile: GeneratedAgentProfile,
        connection: sqlite3.Connection | None = None,
    ) -> GeneratedAgentProfile:
        payload = profile.model_dump(mode="json")
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO generated_agent_profiles (
                  generated_profile_id, base_profile_id, source_type, public_role, role_label, session_id, run_id,
                  cluster_template_id, payload_json, schema_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.generated_profile_id,
                    profile.base_profile_id,
                    profile.source_type,
                    profile.public_role,
                    profile.role_label,
                    profile.session_id,
                    profile.run_id,
                    profile.cluster_template_id,
                    _json_dump(payload),
                    profile.schema_version,
                    profile.created_at.isoformat(),
                    _utc_now_iso(),
                ),
            )
        return profile

    def list(
        self,
        *,
        session_id: str | None = None,
        run_id: str | None = None,
        limit: int | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> list[GeneratedAgentProfile]:
        query = "SELECT payload_json FROM generated_agent_profiles"
        clauses: list[str] = []
        params: list[Any] = []
        if session_id is not None:
            clauses.append("session_id = ?")
            params.append(session_id)
        if run_id is not None:
            clauses.append("run_id = ?")
            params.append(run_id)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC, generated_profile_id DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        with self._connection(connection) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [GeneratedAgentProfile.model_validate(_json_load(row["payload_json"])) for row in rows]


class AutomationWatchdogRepository(RepositoryBase):
    def upsert(
        self,
        watchdog: AutomationWatchdog,
        connection: sqlite3.Connection | None = None,
    ) -> AutomationWatchdog:
        payload = watchdog.model_dump(mode="json")
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO automation_watchdogs (
                  watchdog_id, session_id, run_id, trigger, status, objective, auto_action_enabled, payload_json,
                  schema_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(watchdog_id) DO UPDATE SET
                  session_id = excluded.session_id,
                  run_id = excluded.run_id,
                  trigger = excluded.trigger,
                  status = excluded.status,
                  objective = excluded.objective,
                  auto_action_enabled = excluded.auto_action_enabled,
                  payload_json = excluded.payload_json,
                  schema_version = excluded.schema_version,
                  updated_at = excluded.updated_at
                """,
                (
                    watchdog.watchdog_id,
                    watchdog.session_id,
                    watchdog.run_id,
                    watchdog.trigger,
                    watchdog.status,
                    watchdog.objective,
                    1 if watchdog.auto_action_enabled else 0,
                    _json_dump(payload),
                    watchdog.schema_version,
                    watchdog.created_at.isoformat(),
                    _utc_now_iso(),
                ),
            )
        return watchdog

    def list(
        self,
        *,
        session_id: str | None = None,
        run_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> list[AutomationWatchdog]:
        query = "SELECT payload_json FROM automation_watchdogs"
        clauses: list[str] = []
        params: list[Any] = []
        if session_id is not None:
            clauses.append("session_id = ?")
            params.append(session_id)
        if run_id is not None:
            clauses.append("run_id = ?")
            params.append(run_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC, watchdog_id DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        with self._connection(connection) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [AutomationWatchdog.model_validate(_json_load(row["payload_json"])) for row in rows]

    def find_active(
        self,
        *,
        session_id: str | None = None,
        run_id: str | None = None,
        trigger: str,
        connection: sqlite3.Connection | None = None,
    ) -> AutomationWatchdog | None:
        results = self.list(
            session_id=session_id,
            run_id=run_id,
            status="active",
            limit=20,
            connection=connection,
        )
        return next((item for item in results if item.trigger == trigger), None)


class TaskRepository(RepositoryBase):
    def create_phase(self, phase: Phase, connection: sqlite3.Connection | None = None) -> Phase:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO phases (phase_id, run_id, name, order_index, status, schema_version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    phase.phase_id,
                    phase.run_id,
                    phase.name,
                    phase.order_index,
                    phase.status,
                    phase.schema_version,
                    phase.created_at.isoformat(),
                ),
            )
        return phase

    def list_phases_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[Phase]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                "SELECT * FROM phases WHERE run_id = ? ORDER BY order_index, phase_id",
                (run_id,),
            ).fetchall()
        return [Phase.model_validate(dict(row)) for row in rows]

    def create_task_card(self, task_card: TaskCard, connection: sqlite3.Connection | None = None) -> TaskCard:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO task_cards (task_card_id, run_id, title, description, acceptance_criteria_json, schema_version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_card.task_card_id,
                    task_card.run_id,
                    task_card.title,
                    task_card.description,
                    _json_dump(task_card.acceptance_criteria),
                    task_card.schema_version,
                    task_card.created_at.isoformat(),
                ),
            )
        return task_card

    def list_task_cards_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[TaskCard]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                "SELECT * FROM task_cards WHERE run_id = ? ORDER BY created_at, task_card_id",
                (run_id,),
            ).fetchall()
        task_cards: list[TaskCard] = []
        for row in rows:
            data = dict(row)
            data["acceptance_criteria"] = _json_load(data.pop("acceptance_criteria_json"))
            task_cards.append(TaskCard.model_validate(data))
        return task_cards

    def create_runtime_task(self, runtime_task: RuntimeTask, connection: sqlite3.Connection | None = None) -> RuntimeTask:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO runtime_tasks (
                  runtime_task_id, run_id, phase_id, task_card_id, task_kind, status, summary, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    runtime_task.runtime_task_id,
                    runtime_task.run_id,
                    runtime_task.phase_id,
                    runtime_task.task_card_id,
                    runtime_task.task_kind,
                    runtime_task.status,
                    runtime_task.summary,
                    runtime_task.schema_version,
                    runtime_task.created_at.isoformat(),
                ),
            )
        return runtime_task

    def create_task_packet(self, task_packet: TaskPacket, connection: sqlite3.Connection | None = None) -> TaskPacket:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO task_packets (
                  task_packet_id, runtime_task_id, run_id, task_kind, command_json, working_directory,
                  env_json, expected_artifacts_json, mutation_contract_json, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_packet.task_packet_id,
                    task_packet.runtime_task_id,
                    task_packet.run_id,
                    task_packet.task_kind,
                    _json_dump(task_packet.command),
                    task_packet.working_directory,
                    _json_dump(task_packet.env),
                    _json_dump(task_packet.expected_artifacts),
                    (
                        _json_dump(task_packet.mutation_contract.model_dump(mode="json"))
                        if task_packet.mutation_contract is not None
                        else None
                    ),
                    task_packet.schema_version,
                    task_packet.created_at.isoformat(),
                ),
            )
        return task_packet

    def update_runtime_task_status(
        self,
        runtime_task_id: str,
        status: TaskStatus | str,
        connection: sqlite3.Connection | None = None,
    ) -> RuntimeTask | None:
        with self._connection(connection, commit=True) as conn:
            conn.execute("UPDATE runtime_tasks SET status = ? WHERE runtime_task_id = ?", (str(status), runtime_task_id))
        return self.get_runtime_task(runtime_task_id, connection=connection)

    def get_runtime_task(self, runtime_task_id: str, connection: sqlite3.Connection | None = None) -> RuntimeTask | None:
        with self._connection(connection) as conn:
            row = conn.execute("SELECT * FROM runtime_tasks WHERE runtime_task_id = ?", (runtime_task_id,)).fetchone()
        return RuntimeTask.model_validate(dict(row)) if row else None

    def get_task_packet(self, runtime_task_id: str, connection: sqlite3.Connection | None = None) -> TaskPacket | None:
        with self._connection(connection) as conn:
            row = conn.execute("SELECT * FROM task_packets WHERE runtime_task_id = ?", (runtime_task_id,)).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["command"] = _json_load(data.pop("command_json"))
        data["env"] = _json_load(data.pop("env_json"))
        data["expected_artifacts"] = _json_load(data.pop("expected_artifacts_json"))
        mutation_contract_json = data.pop("mutation_contract_json", None)
        if mutation_contract_json:
            data["mutation_contract"] = _json_load(mutation_contract_json)
        return TaskPacket.model_validate(data)

    def list_runtime_tasks_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[RuntimeTask]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                "SELECT * FROM runtime_tasks WHERE run_id = ? ORDER BY created_at, runtime_task_id",
                (run_id,),
            ).fetchall()
        return [RuntimeTask.model_validate(dict(row)) for row in rows]

    def clear_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> None:
        with self._connection(connection, commit=True) as conn:
            conn.execute("DELETE FROM task_packets WHERE run_id = ?", (run_id,))
            conn.execute("DELETE FROM runtime_tasks WHERE run_id = ?", (run_id,))
            conn.execute("DELETE FROM task_cards WHERE run_id = ?", (run_id,))
            conn.execute("DELETE FROM phases WHERE run_id = ?", (run_id,))


class EvidenceRepository(RepositoryBase):
    def create(self, evidence: Evidence, connection: sqlite3.Connection | None = None) -> Evidence:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO evidence (
                  evidence_id, run_id, runtime_task_id, summary, changed_files_json, checks_json,
                  known_gaps_json, artifact_refs_json, return_code, raw_execution_json, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence.evidence_id,
                    evidence.run_id,
                    evidence.runtime_task_id,
                    evidence.summary,
                    _json_dump(evidence.changed_files),
                    _json_dump([check.model_dump(mode="json") for check in evidence.checks]),
                    _json_dump(evidence.known_gaps),
                    _json_dump([ref.model_dump(mode="json") for ref in evidence.artifact_refs]),
                    evidence.return_code,
                    _json_dump(evidence.raw_execution),
                    evidence.schema_version,
                    evidence.created_at.isoformat(),
                ),
            )
        return evidence

    def get_by_task(self, runtime_task_id: str, connection: sqlite3.Connection | None = None) -> Evidence | None:
        with self._connection(connection) as conn:
            row = conn.execute("SELECT * FROM evidence WHERE runtime_task_id = ?", (runtime_task_id,)).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["changed_files"] = _json_load(data.pop("changed_files_json"))
        data["checks"] = _json_load(data.pop("checks_json"))
        data["known_gaps"] = _json_load(data.pop("known_gaps_json"))
        data["artifact_refs"] = _json_load(data.pop("artifact_refs_json"))
        data["raw_execution"] = _json_load(data.pop("raw_execution_json"))
        return Evidence.model_validate(data)


class ReviewRepository(RepositoryBase):
    def create(self, verdict: ReviewVerdict, connection: sqlite3.Connection | None = None) -> ReviewVerdict:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO review_verdicts (
                  verdict_id, run_id, evidence_id, decision, rationale, reviewer_type,
                  reviewed_at, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    verdict.verdict_id,
                    verdict.run_id,
                    verdict.evidence_id,
                    verdict.decision,
                    verdict.rationale,
                    verdict.reviewer_type,
                    verdict.reviewed_at.isoformat(),
                    verdict.schema_version,
                    verdict.created_at.isoformat(),
                ),
            )
        return verdict

    def get_by_evidence(self, evidence_id: str, connection: sqlite3.Connection | None = None) -> ReviewVerdict | None:
        with self._connection(connection) as conn:
            row = conn.execute("SELECT * FROM review_verdicts WHERE evidence_id = ?", (evidence_id,)).fetchone()
        return ReviewVerdict.model_validate(dict(row)) if row else None

    def list_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[ReviewVerdict]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                "SELECT * FROM review_verdicts WHERE run_id = ? ORDER BY reviewed_at, verdict_id",
                (run_id,),
            ).fetchall()
        return [ReviewVerdict.model_validate(dict(row)) for row in rows]

    def latest_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> ReviewVerdict | None:
        with self._connection(connection) as conn:
            row = conn.execute(
                """
                SELECT * FROM review_verdicts
                WHERE run_id = ?
                ORDER BY reviewed_at DESC, verdict_id DESC
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
        return ReviewVerdict.model_validate(dict(row)) if row else None


class EventRepository(RepositoryBase):
    def _payload_with_trace_context(self, event: RunEvent) -> dict[str, Any]:
        payload = dict(event.payload_json)
        trace_payload = dict(payload.get("trace_context") or {})
        trace_payload.update(
            {
                "run_id": event.run_id,
                "event_id": event.event_id,
                "runtime_task_id": payload.get("runtime_task_id"),
                "state_ref_id": payload.get("state_ref_id"),
                "attempt_id": payload.get("attempt_id"),
                "evidence_id": payload.get("evidence_id"),
                "verdict_id": payload.get("verdict_id"),
                "claim_id": payload.get("claim_id"),
                "lease_id": payload.get("lease_id"),
                "snapshot_id": payload.get("snapshot_id"),
                "memory_item_id": payload.get("memory_item_id"),
                "simulation_record_id": payload.get("record_id"),
            }
        )
        payload["trace_context"] = {key: value for key, value in trace_payload.items() if value is not None}
        return payload

    def append(self, event: RunEvent, connection: sqlite3.Connection | None = None) -> RunEvent:
        payload = validate_event_payload(event.event_type, self._payload_with_trace_context(event))
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO run_events (
                  event_id, run_id, event_type, object_type, object_id, summary,
                  payload_json, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.run_id,
                    event.event_type,
                    event.object_type,
                    event.object_id,
                    event.summary,
                    _json_dump(payload),
                    event.schema_version,
                    event.created_at.isoformat(),
                ),
            )
        return RunEvent.model_validate({**event.model_dump(mode="json"), "payload_json": payload})

    def list_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[RunEvent]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                "SELECT * FROM run_events WHERE run_id = ? ORDER BY created_at, event_id",
                (run_id,),
            ).fetchall()
        events: list[RunEvent] = []
        for row in rows:
            data = dict(row)
            data["payload_json"] = _json_load(data["payload_json"])
            events.append(RunEvent.model_validate(data))
        return events


class MemoryItemRepository(RepositoryBase):
    def _row_to_model(self, row: Any) -> MemoryItem:
        data = dict(row)
        data["tags"] = _json_load(data.pop("tags_json"))
        data["source_refs"] = _json_load(data.pop("source_refs_json"))
        return MemoryItem.model_validate(data)

    def create(self, memory_item: MemoryItem, connection: sqlite3.Connection | None = None) -> MemoryItem:
        existing = self.get_by_source_candidate(memory_item.source_candidate_id, connection=connection)
        if existing is not None:
            return existing
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO memory_items (
                  memory_item_id, run_id, namespace_id, source_candidate_id, title, summary,
                  tags_json, source_refs_json, materialized_from, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_item.memory_item_id,
                    memory_item.run_id,
                    memory_item.namespace_id,
                    memory_item.source_candidate_id,
                    memory_item.title,
                    memory_item.summary,
                    _json_dump(memory_item.tags),
                    _json_dump(memory_item.source_refs),
                    memory_item.materialized_from,
                    memory_item.schema_version,
                    memory_item.created_at.isoformat(),
                ),
            )
        return memory_item

    def get(self, memory_item_id: str, connection: sqlite3.Connection | None = None) -> MemoryItem | None:
        with self._connection(connection) as conn:
            row = conn.execute("SELECT * FROM memory_items WHERE memory_item_id = ?", (memory_item_id,)).fetchone()
        return self._row_to_model(row) if row is not None else None

    def get_by_source_candidate(
        self,
        source_candidate_id: str,
        connection: sqlite3.Connection | None = None,
    ) -> MemoryItem | None:
        with self._connection(connection) as conn:
            row = conn.execute(
                "SELECT * FROM memory_items WHERE source_candidate_id = ?",
                (source_candidate_id,),
            ).fetchone()
        return self._row_to_model(row) if row is not None else None

    def list(
        self,
        *,
        run_id: str | None = None,
        namespace_id: str | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> list[MemoryItem]:
        query = "SELECT * FROM memory_items"
        predicates: list[str] = []
        params: list[Any] = []
        if run_id is not None:
            predicates.append("run_id = ?")
            params.append(run_id)
        if namespace_id is not None:
            predicates.append("namespace_id = ?")
            params.append(namespace_id)
        if predicates:
            query += " WHERE " + " AND ".join(predicates)
        query += " ORDER BY created_at, memory_item_id"
        with self._connection(connection) as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._row_to_model(row) for row in rows]

    def list_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[MemoryItem]:
        return self.list(run_id=run_id, connection=connection)

    def list_for_namespace(self, namespace_id: str, connection: sqlite3.Connection | None = None) -> list[MemoryItem]:
        return self.list(namespace_id=namespace_id, connection=connection)


class SimulationRecordRepository(RepositoryBase):
    def _row_to_model(self, row: Any) -> SimulationRecord:
        data = dict(row)
        data["triggered"] = bool(data["triggered"])
        data["report"] = _json_load(data.pop("report_json"))
        return SimulationRecord.model_validate(data)

    def create(
        self,
        record: SimulationRecord,
        connection: sqlite3.Connection | None = None,
    ) -> SimulationRecord:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO simulation_records (
                  record_id, run_id, policy_id, status, triggered, summary, recorded_from,
                  report_json, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.record_id,
                    record.run_id,
                    record.policy_id,
                    record.status,
                    1 if record.triggered else 0,
                    record.summary,
                    record.recorded_from,
                    _json_dump(record.report.model_dump(mode="json")),
                    record.schema_version,
                    record.created_at.isoformat(),
                ),
            )
        return record

    def get(self, record_id: str, connection: sqlite3.Connection | None = None) -> SimulationRecord | None:
        with self._connection(connection) as conn:
            row = conn.execute(
                "SELECT * FROM simulation_records WHERE record_id = ?",
                (record_id,),
            ).fetchone()
        return self._row_to_model(row) if row is not None else None

    def list_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[SimulationRecord]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                """
                SELECT * FROM simulation_records
                WHERE run_id = ?
                ORDER BY created_at, record_id
                """,
                (run_id,),
            ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def latest_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> SimulationRecord | None:
        with self._connection(connection) as conn:
            row = conn.execute(
                """
                SELECT * FROM simulation_records
                WHERE run_id = ?
                ORDER BY created_at DESC, record_id DESC
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
        return self._row_to_model(row) if row is not None else None


class HandoffRepository(RepositoryBase):
    def create(self, handoff: HandoffLite, connection: sqlite3.Connection | None = None) -> HandoffLite:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO handoff_lite (
                  handoff_id, run_id, from_phase_id, to_phase_id, summary, blocking_risks_json, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    handoff.handoff_id,
                    handoff.run_id,
                    handoff.from_phase_id,
                    handoff.to_phase_id,
                    handoff.summary,
                    _json_dump(handoff.blocking_risks),
                    handoff.schema_version,
                    handoff.created_at.isoformat(),
                ),
            )
        return handoff

    def list_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[HandoffLite]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                "SELECT * FROM handoff_lite WHERE run_id = ? ORDER BY created_at, handoff_id",
                (run_id,),
            ).fetchall()
        handoffs: list[HandoffLite] = []
        for row in rows:
            data = dict(row)
            data["blocking_risks"] = _json_load(data.pop("blocking_risks_json"))
            handoffs.append(HandoffLite.model_validate(data))
        return handoffs

    def clear_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> None:
        with self._connection(connection, commit=True) as conn:
            conn.execute("DELETE FROM handoff_lite WHERE run_id = ?", (run_id,))


class RuntimeStateRepository(RepositoryBase):
    def _row_to_model(self, row: Any) -> RuntimeStateRef:
        data = dict(row)
        data["state_payload"] = _json_load(data.pop("state_payload_json"))
        data["is_terminal"] = bool(data["is_terminal"])
        return RuntimeStateRef.model_validate(data)

    def upsert(self, state_ref: RuntimeStateRef, connection: sqlite3.Connection | None = None) -> RuntimeStateRef:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO runtime_state_refs (
                  state_ref_id, run_id, runtime_task_id, graph_step, state_payload_json,
                  is_terminal, updated_at, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(runtime_task_id) DO UPDATE SET
                  state_ref_id = excluded.state_ref_id,
                  graph_step = excluded.graph_step,
                  state_payload_json = excluded.state_payload_json,
                  is_terminal = excluded.is_terminal,
                  updated_at = excluded.updated_at,
                  schema_version = excluded.schema_version
                """,
                (
                    state_ref.state_ref_id,
                    state_ref.run_id,
                    state_ref.runtime_task_id,
                    state_ref.graph_step,
                    _json_dump(state_ref.state_payload),
                    1 if state_ref.is_terminal else 0,
                    state_ref.updated_at.isoformat(),
                    state_ref.schema_version,
                    state_ref.created_at.isoformat(),
                ),
            )
        stored = self.get_by_task(state_ref.runtime_task_id, connection=connection)
        assert stored is not None
        return stored

    def get_by_task(self, runtime_task_id: str, connection: sqlite3.Connection | None = None) -> RuntimeStateRef | None:
        with self._connection(connection) as conn:
            row = conn.execute(
                "SELECT * FROM runtime_state_refs WHERE runtime_task_id = ?",
                (runtime_task_id,),
            ).fetchone()
        return self._row_to_model(row) if row is not None else None

    def latest_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> RuntimeStateRef | None:
        with self._connection(connection) as conn:
            row = conn.execute(
                """
                SELECT * FROM runtime_state_refs
                WHERE run_id = ?
                ORDER BY updated_at DESC, created_at DESC, state_ref_id DESC
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
        return self._row_to_model(row) if row is not None else None

    def list_live_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[RuntimeStateRef]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                """
                SELECT * FROM runtime_state_refs
                WHERE run_id = ? AND is_terminal = 0
                ORDER BY updated_at, state_ref_id
                """,
                (run_id,),
            ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def list_terminal_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[RuntimeStateRef]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                """
                SELECT * FROM runtime_state_refs
                WHERE run_id = ? AND is_terminal = 1
                ORDER BY updated_at, state_ref_id
                """,
                (run_id,),
            ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def list_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[RuntimeStateRef]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                "SELECT * FROM runtime_state_refs WHERE run_id = ? ORDER BY updated_at, state_ref_id",
                (run_id,),
            ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def clear_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> None:
        with self._connection(connection, commit=True) as conn:
            conn.execute("DELETE FROM runtime_state_refs WHERE run_id = ?", (run_id,))


class RuntimeClaimRepository(RepositoryBase):
    def _row_to_model(self, row: Any) -> RuntimeClaim:
        return RuntimeClaim.model_validate(dict(row))

    def create(self, claim: RuntimeClaim, connection: sqlite3.Connection | None = None) -> RuntimeClaim:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO runtime_claims (
                  claim_id, run_id, runtime_task_id, owner, owner_kind, owner_id,
                  domain_kind, domain_key, attempt_id, status, lease_expires_at,
                  released_at, release_reason, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    claim.claim_id,
                    claim.run_id,
                    claim.runtime_task_id,
                    claim.owner,
                    claim.owner_kind,
                    claim.owner_id,
                    claim.domain_kind,
                    claim.domain_key,
                    claim.attempt_id,
                    claim.status,
                    claim.lease_expires_at.isoformat(),
                    claim.released_at.isoformat() if claim.released_at is not None else None,
                    claim.release_reason,
                    claim.schema_version,
                    claim.created_at.isoformat(),
                ),
            )
        return claim

    def get(self, claim_id: str, connection: sqlite3.Connection | None = None) -> RuntimeClaim | None:
        with self._connection(connection) as conn:
            row = conn.execute("SELECT * FROM runtime_claims WHERE claim_id = ?", (claim_id,)).fetchone()
        return self._row_to_model(row) if row is not None else None

    def get_active_for_task(self, runtime_task_id: str, connection: sqlite3.Connection | None = None) -> RuntimeClaim | None:
        with self._connection(connection) as conn:
            row = conn.execute(
                """
                SELECT * FROM runtime_claims
                WHERE runtime_task_id = ? AND status = 'active'
                ORDER BY created_at DESC, claim_id DESC
                LIMIT 1
                """,
                (runtime_task_id,),
            ).fetchone()
        return self._row_to_model(row) if row is not None else None

    def list_active_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[RuntimeClaim]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                """
                SELECT * FROM runtime_claims
                WHERE run_id = ? AND status = 'active'
                ORDER BY created_at, claim_id
                """,
                (run_id,),
            ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def list_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[RuntimeClaim]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                "SELECT * FROM runtime_claims WHERE run_id = ? ORDER BY created_at, claim_id",
                (run_id,),
            ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def latest_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> RuntimeClaim | None:
        with self._connection(connection) as conn:
            row = conn.execute(
                """
                SELECT * FROM runtime_claims
                WHERE run_id = ?
                ORDER BY created_at DESC, claim_id DESC
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
        return self._row_to_model(row) if row is not None else None

    def release(
        self,
        claim_id: str,
        *,
        released_at: str,
        release_reason: str,
        status: str = "released",
        connection: sqlite3.Connection | None = None,
    ) -> RuntimeClaim | None:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                UPDATE runtime_claims
                SET status = ?, released_at = ?, release_reason = ?
                WHERE claim_id = ?
                """,
                (status, released_at, release_reason, claim_id),
            )
        return self.get(claim_id, connection=connection)


class RunSnapshotRepository(RepositoryBase):
    def _row_to_model(self, row: Any) -> RunSnapshot:
        data = dict(row)
        data["snapshot_payload"] = _json_load(data.pop("snapshot_payload_json"))
        return RunSnapshot.model_validate(data)

    def create(self, snapshot: RunSnapshot, connection: sqlite3.Connection | None = None) -> RunSnapshot:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO run_snapshots (
                  snapshot_id, run_id, stage, run_status, runtime_task_id, summary,
                  snapshot_payload_json, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.snapshot_id,
                    snapshot.run_id,
                    snapshot.stage,
                    snapshot.run_status,
                    snapshot.runtime_task_id,
                    snapshot.summary,
                    _json_dump(snapshot.snapshot_payload),
                    snapshot.schema_version,
                    snapshot.created_at.isoformat(),
                ),
            )
        return snapshot

    def list_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[RunSnapshot]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                """
                SELECT * FROM run_snapshots
                WHERE run_id = ?
                ORDER BY created_at, snapshot_id
                """,
                (run_id,),
            ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def latest_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> RunSnapshot | None:
        with self._connection(connection) as conn:
            row = conn.execute(
                """
                SELECT * FROM run_snapshots
                WHERE run_id = ?
                ORDER BY created_at DESC, snapshot_id DESC
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
        return self._row_to_model(row) if row is not None else None


class RuntimeAttemptRepository(RepositoryBase):
    def create(self, attempt: RuntimeAttempt, connection: sqlite3.Connection | None = None) -> RuntimeAttempt:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO runtime_attempts (
                  attempt_id, run_id, runtime_task_id, sequence_no, trigger, status,
                  superseded_by_attempt_id, superseded_at, supersede_reason,
                  closed_at, close_reason, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt.attempt_id,
                    attempt.run_id,
                    attempt.runtime_task_id,
                    attempt.sequence_no,
                    attempt.trigger,
                    attempt.status,
                    attempt.superseded_by_attempt_id,
                    attempt.superseded_at.isoformat() if attempt.superseded_at is not None else None,
                    attempt.supersede_reason,
                    attempt.closed_at.isoformat() if attempt.closed_at is not None else None,
                    attempt.close_reason,
                    attempt.schema_version,
                    attempt.created_at.isoformat(),
                ),
            )
        return attempt

    def get(self, attempt_id: str, connection: sqlite3.Connection | None = None) -> RuntimeAttempt | None:
        with self._connection(connection) as conn:
            row = conn.execute("SELECT * FROM runtime_attempts WHERE attempt_id = ?", (attempt_id,)).fetchone()
        return RuntimeAttempt.model_validate(dict(row)) if row is not None else None

    def list_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[RuntimeAttempt]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                """
                SELECT * FROM runtime_attempts
                WHERE run_id = ?
                ORDER BY sequence_no, created_at, attempt_id
                """,
                (run_id,),
            ).fetchall()
        return [RuntimeAttempt.model_validate(dict(row)) for row in rows]

    def list_for_task(self, runtime_task_id: str, connection: sqlite3.Connection | None = None) -> list[RuntimeAttempt]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                """
                SELECT * FROM runtime_attempts
                WHERE runtime_task_id = ?
                ORDER BY sequence_no, created_at, attempt_id
                """,
                (runtime_task_id,),
            ).fetchall()
        return [RuntimeAttempt.model_validate(dict(row)) for row in rows]

    def latest_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> RuntimeAttempt | None:
        with self._connection(connection) as conn:
            row = conn.execute(
                """
                SELECT * FROM runtime_attempts
                WHERE run_id = ?
                ORDER BY sequence_no DESC, created_at DESC, attempt_id DESC
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
        return RuntimeAttempt.model_validate(dict(row)) if row is not None else None

    def current_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> RuntimeAttempt | None:
        with self._connection(connection) as conn:
            row = conn.execute(
                """
                SELECT * FROM runtime_attempts
                WHERE run_id = ? AND status = 'current'
                ORDER BY sequence_no DESC, created_at DESC, attempt_id DESC
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
        return RuntimeAttempt.model_validate(dict(row)) if row is not None else None

    def list_superseded_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[RuntimeAttempt]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                """
                SELECT * FROM runtime_attempts
                WHERE run_id = ? AND status = 'superseded'
                ORDER BY sequence_no, created_at, attempt_id
                """,
                (run_id,),
            ).fetchall()
        return [RuntimeAttempt.model_validate(dict(row)) for row in rows]

    def next_sequence_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> int:
        with self._connection(connection) as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(sequence_no), 0) AS max_sequence_no FROM runtime_attempts WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        max_sequence_no = int(row["max_sequence_no"]) if row is not None else 0
        return max_sequence_no + 1

    def supersede(
        self,
        attempt_id: str,
        *,
        superseded_by_attempt_id: str,
        superseded_at: str,
        supersede_reason: str,
        connection: sqlite3.Connection | None = None,
    ) -> RuntimeAttempt | None:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                UPDATE runtime_attempts
                SET status = 'superseded',
                    superseded_by_attempt_id = ?,
                    superseded_at = ?,
                    supersede_reason = ?,
                    closed_at = NULL,
                    close_reason = NULL
                WHERE attempt_id = ?
                """,
                (superseded_by_attempt_id, superseded_at, supersede_reason, attempt_id),
            )
        return self.get(attempt_id, connection=connection)

    def close(
        self,
        attempt_id: str,
        *,
        status: str,
        closed_at: str,
        close_reason: str,
        connection: sqlite3.Connection | None = None,
    ) -> RuntimeAttempt | None:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                UPDATE runtime_attempts
                SET status = ?,
                    closed_at = ?,
                    close_reason = ?,
                    superseded_by_attempt_id = NULL,
                    superseded_at = NULL,
                    supersede_reason = NULL
                WHERE attempt_id = ?
                """,
                (status, closed_at, close_reason, attempt_id),
            )
        return self.get(attempt_id, connection=connection)


class BudgetLedgerRepository(RepositoryBase):
    def create(self, ledger: BudgetLedger, connection: sqlite3.Connection | None = None) -> BudgetLedger:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO budget_ledgers (
                  ledger_id, run_id, preset_id, max_retries, timeout_seconds,
                  compile_count, recompile_count, execution_count, total_runtime_ms,
                  last_return_code, updated_at, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ledger.ledger_id,
                    ledger.run_id,
                    ledger.preset_id,
                    ledger.max_retries,
                    ledger.timeout_seconds,
                    ledger.compile_count,
                    ledger.recompile_count,
                    ledger.execution_count,
                    ledger.total_runtime_ms,
                    ledger.last_return_code,
                    ledger.updated_at.isoformat(),
                    ledger.schema_version,
                    ledger.created_at.isoformat(),
                ),
            )
        return ledger

    def get_by_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> BudgetLedger | None:
        with self._connection(connection) as conn:
            row = conn.execute("SELECT * FROM budget_ledgers WHERE run_id = ?", (run_id,)).fetchone()
        return BudgetLedger.model_validate(dict(row)) if row is not None else None

    def update(self, ledger: BudgetLedger, connection: sqlite3.Connection | None = None) -> BudgetLedger:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                UPDATE budget_ledgers
                SET preset_id = ?, max_retries = ?, timeout_seconds = ?, compile_count = ?,
                    recompile_count = ?, execution_count = ?, total_runtime_ms = ?,
                    last_return_code = ?, updated_at = ?, schema_version = ?
                WHERE run_id = ?
                """,
                (
                    ledger.preset_id,
                    ledger.max_retries,
                    ledger.timeout_seconds,
                    ledger.compile_count,
                    ledger.recompile_count,
                    ledger.execution_count,
                    ledger.total_runtime_ms,
                    ledger.last_return_code,
                    ledger.updated_at.isoformat(),
                    ledger.schema_version,
                    ledger.run_id,
                ),
            )
        stored = self.get_by_run(ledger.run_id, connection=connection)
        assert stored is not None
        return stored


class WorkerLeaseRepository(RepositoryBase):
    def create(self, lease: WorkerLease, connection: sqlite3.Connection | None = None) -> WorkerLease:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO worker_leases (
                  lease_id, run_id, runtime_task_id, worker_name, worker_kind, worker_id,
                  domain_kind, domain_key, claim_id, attempt_id, adapter_name, status,
                  heartbeat_at, lease_expires_at, released_at, release_reason, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lease.lease_id,
                    lease.run_id,
                    lease.runtime_task_id,
                    lease.worker_name,
                    lease.worker_kind,
                    lease.worker_id,
                    lease.domain_kind,
                    lease.domain_key,
                    lease.claim_id,
                    lease.attempt_id,
                    lease.adapter_name,
                    lease.status,
                    lease.heartbeat_at.isoformat(),
                    lease.lease_expires_at.isoformat(),
                    lease.released_at.isoformat() if lease.released_at is not None else None,
                    lease.release_reason,
                    lease.schema_version,
                    lease.created_at.isoformat(),
                ),
            )
        return lease

    def get(self, lease_id: str, connection: sqlite3.Connection | None = None) -> WorkerLease | None:
        with self._connection(connection) as conn:
            row = conn.execute("SELECT * FROM worker_leases WHERE lease_id = ?", (lease_id,)).fetchone()
        return WorkerLease.model_validate(dict(row)) if row is not None else None

    def get_active_for_task(self, runtime_task_id: str, connection: sqlite3.Connection | None = None) -> WorkerLease | None:
        with self._connection(connection) as conn:
            row = conn.execute(
                """
                SELECT * FROM worker_leases
                WHERE runtime_task_id = ? AND status = 'active'
                ORDER BY created_at DESC, lease_id DESC
                LIMIT 1
                """,
                (runtime_task_id,),
            ).fetchone()
        return WorkerLease.model_validate(dict(row)) if row is not None else None

    def list_active_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[WorkerLease]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                """
                SELECT * FROM worker_leases
                WHERE run_id = ? AND status = 'active'
                ORDER BY created_at, lease_id
                """,
                (run_id,),
            ).fetchall()
        return [WorkerLease.model_validate(dict(row)) for row in rows]

    def list_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[WorkerLease]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                "SELECT * FROM worker_leases WHERE run_id = ? ORDER BY created_at, lease_id",
                (run_id,),
            ).fetchall()
        return [WorkerLease.model_validate(dict(row)) for row in rows]

    def latest_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> WorkerLease | None:
        with self._connection(connection) as conn:
            row = conn.execute(
                """
                SELECT * FROM worker_leases
                WHERE run_id = ?
                ORDER BY created_at DESC, lease_id DESC
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
        return WorkerLease.model_validate(dict(row)) if row is not None else None

    def release(
        self,
        lease_id: str,
        *,
        released_at: str,
        release_reason: str,
        status: str = "released",
        connection: sqlite3.Connection | None = None,
    ) -> WorkerLease | None:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                UPDATE worker_leases
                SET status = ?, released_at = ?, release_reason = ?
                WHERE lease_id = ?
                """,
                (status, released_at, release_reason, lease_id),
            )
        return self.get(lease_id, connection=connection)

    def touch(
        self,
        lease_id: str,
        *,
        heartbeat_at: str,
        lease_expires_at: str,
        connection: sqlite3.Connection | None = None,
    ) -> WorkerLease | None:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                UPDATE worker_leases
                SET heartbeat_at = ?, lease_expires_at = ?
                WHERE lease_id = ? AND status = 'active'
                """,
                (heartbeat_at, lease_expires_at, lease_id),
            )
        return self.get(lease_id, connection=connection)


class SchedulerLeaseProposalRepository(RepositoryBase):
    def _row_to_model(self, row: Any) -> SchedulerLeaseProposal:
        return SchedulerLeaseProposal.model_validate(dict(row))

    def create(
        self,
        proposal: SchedulerLeaseProposal,
        connection: sqlite3.Connection | None = None,
    ) -> SchedulerLeaseProposal:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO scheduler_lease_proposals (
                  proposal_id, control_plane_id, run_id, runtime_task_id, domain_kind, domain_key,
                  requested_lease_seconds, requested_epoch, status, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.proposal_id,
                    proposal.control_plane_id,
                    proposal.run_id,
                    proposal.runtime_task_id,
                    proposal.domain_kind,
                    proposal.domain_key,
                    proposal.requested_lease_seconds,
                    proposal.requested_epoch,
                    proposal.status,
                    proposal.schema_version,
                    proposal.created_at.isoformat(),
                ),
            )
        return proposal

    def get(
        self,
        proposal_id: str,
        connection: sqlite3.Connection | None = None,
    ) -> SchedulerLeaseProposal | None:
        with self._connection(connection) as conn:
            row = conn.execute(
                "SELECT * FROM scheduler_lease_proposals WHERE proposal_id = ?",
                (proposal_id,),
            ).fetchone()
        return self._row_to_model(row) if row is not None else None

    def update_status(
        self,
        proposal_id: str,
        status: str,
        connection: sqlite3.Connection | None = None,
    ) -> SchedulerLeaseProposal | None:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                "UPDATE scheduler_lease_proposals SET status = ? WHERE proposal_id = ?",
                (status, proposal_id),
            )
        return self.get(proposal_id, connection=connection)

    def list_for_run(
        self,
        run_id: str,
        connection: sqlite3.Connection | None = None,
    ) -> list[SchedulerLeaseProposal]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                """
                SELECT * FROM scheduler_lease_proposals
                WHERE run_id = ?
                ORDER BY created_at, proposal_id
                """,
                (run_id,),
            ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def list_for_task(
        self,
        runtime_task_id: str,
        connection: sqlite3.Connection | None = None,
    ) -> list[SchedulerLeaseProposal]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                """
                SELECT * FROM scheduler_lease_proposals
                WHERE runtime_task_id = ?
                ORDER BY created_at, proposal_id
                """,
                (runtime_task_id,),
            ).fetchall()
        return [self._row_to_model(row) for row in rows]


class SchedulerLeaseDecisionRepository(RepositoryBase):
    def _row_to_model(self, row: Any) -> SchedulerLeaseDecision:
        return SchedulerLeaseDecision.model_validate(dict(row))

    def create(
        self,
        decision: SchedulerLeaseDecision,
        connection: sqlite3.Connection | None = None,
    ) -> SchedulerLeaseDecision:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO scheduler_lease_decisions (
                  decision_id, lease_id, proposal_id, control_plane_id, run_id, runtime_task_id,
                  domain_kind, domain_key, lease_epoch, decision, reason, lease_expires_at,
                  released_at, release_reason, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.decision_id,
                    decision.lease_id,
                    decision.proposal_id,
                    decision.control_plane_id,
                    decision.run_id,
                    decision.runtime_task_id,
                    decision.domain_kind,
                    decision.domain_key,
                    decision.lease_epoch,
                    decision.decision,
                    decision.reason,
                    decision.lease_expires_at.isoformat(),
                    decision.released_at.isoformat() if decision.released_at is not None else None,
                    decision.release_reason,
                    decision.schema_version,
                    decision.created_at.isoformat(),
                ),
            )
        return decision

    def get(
        self,
        lease_id: str,
        connection: sqlite3.Connection | None = None,
    ) -> SchedulerLeaseDecision | None:
        with self._connection(connection) as conn:
            row = conn.execute(
                "SELECT * FROM scheduler_lease_decisions WHERE lease_id = ? ORDER BY created_at DESC, decision_id DESC LIMIT 1",
                (lease_id,),
            ).fetchone()
        return self._row_to_model(row) if row is not None else None

    def get_active_for_domain(
        self,
        domain_kind: str,
        domain_key: str,
        *,
        now_iso: str,
        connection: sqlite3.Connection | None = None,
    ) -> SchedulerLeaseDecision | None:
        with self._connection(connection) as conn:
            row = conn.execute(
                """
                SELECT * FROM scheduler_lease_decisions
                WHERE domain_kind = ?
                  AND domain_key = ?
                  AND decision = 'granted'
                  AND released_at IS NULL
                  AND lease_expires_at > ?
                ORDER BY created_at DESC, decision_id DESC
                LIMIT 1
                """,
                (domain_kind, domain_key, now_iso),
            ).fetchone()
        return self._row_to_model(row) if row is not None else None

    def latest_for_domain(
        self,
        domain_kind: str,
        domain_key: str,
        connection: sqlite3.Connection | None = None,
    ) -> SchedulerLeaseDecision | None:
        with self._connection(connection) as conn:
            row = conn.execute(
                """
                SELECT * FROM scheduler_lease_decisions
                WHERE domain_kind = ? AND domain_key = ?
                ORDER BY created_at DESC, decision_id DESC
                LIMIT 1
                """,
                (domain_kind, domain_key),
            ).fetchone()
        return self._row_to_model(row) if row is not None else None

    def list_for_run(
        self,
        run_id: str,
        connection: sqlite3.Connection | None = None,
    ) -> list[SchedulerLeaseDecision]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                """
                SELECT * FROM scheduler_lease_decisions
                WHERE run_id = ?
                ORDER BY created_at, decision_id
                """,
                (run_id,),
            ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def release(
        self,
        lease_id: str,
        *,
        released_at: str,
        release_reason: str,
        connection: sqlite3.Connection | None = None,
    ) -> SchedulerLeaseDecision | None:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                UPDATE scheduler_lease_decisions
                SET released_at = ?, release_reason = ?
                WHERE lease_id = ? AND released_at IS NULL
                """,
                (released_at, release_reason, lease_id),
            )
        return self.get(lease_id, connection=connection)


class SchedulerPeerHeartbeatRepository(RepositoryBase):
    def _row_to_model(self, row: Any) -> SchedulerPeerHeartbeat:
        return SchedulerPeerHeartbeat.model_validate(dict(row))

    def create(
        self,
        heartbeat: SchedulerPeerHeartbeat,
        connection: sqlite3.Connection | None = None,
    ) -> SchedulerPeerHeartbeat:
        with self._connection(connection, commit=True) as conn:
            conn.execute(
                """
                INSERT INTO scheduler_peer_heartbeats (
                  heartbeat_id, control_plane_id, status, lease_count, observed_at, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    heartbeat.heartbeat_id,
                    heartbeat.control_plane_id,
                    heartbeat.status,
                    heartbeat.lease_count,
                    heartbeat.observed_at.isoformat(),
                    heartbeat.schema_version,
                    heartbeat.created_at.isoformat(),
                ),
            )
        return heartbeat

    def latest_for_control_plane(
        self,
        control_plane_id: str,
        connection: sqlite3.Connection | None = None,
    ) -> SchedulerPeerHeartbeat | None:
        with self._connection(connection) as conn:
            row = conn.execute(
                """
                SELECT * FROM scheduler_peer_heartbeats
                WHERE control_plane_id = ?
                ORDER BY observed_at DESC, heartbeat_id DESC
                LIMIT 1
                """,
                (control_plane_id,),
            ).fetchone()
        return self._row_to_model(row) if row is not None else None

    def list_recent(
        self,
        *,
        limit: int = 20,
        connection: sqlite3.Connection | None = None,
    ) -> list[SchedulerPeerHeartbeat]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                """
                SELECT * FROM scheduler_peer_heartbeats
                ORDER BY observed_at DESC, heartbeat_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_model(row) for row in rows]
