from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from packages.contracts import (
    Evidence,
    HandoffLite,
    Phase,
    PresetDefinition,
    ReviewVerdict,
    Run,
    RunEvent,
    RuntimeStateRef,
    RuntimeTask,
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

    def update_status(self, run_id: str, status: str, connection: sqlite3.Connection | None = None) -> Run | None:
        with self._connection(connection, commit=True) as conn:
            conn.execute("UPDATE runs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE run_id = ?", (status, run_id))
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
        return PresetDefinition.model_validate(data)


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
                  env_json, expected_artifacts_json, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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


class EventRepository(RepositoryBase):
    def append(self, event: RunEvent, connection: sqlite3.Connection | None = None) -> RunEvent:
        payload = validate_event_payload(event.event_type, event.payload_json)
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
        if row is None:
            return None
        data = dict(row)
        data["state_payload"] = _json_load(data.pop("state_payload_json"))
        data["is_terminal"] = bool(data["is_terminal"])
        return RuntimeStateRef.model_validate(data)

    def list_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> list[RuntimeStateRef]:
        with self._connection(connection) as conn:
            rows = conn.execute(
                "SELECT * FROM runtime_state_refs WHERE run_id = ? ORDER BY updated_at, state_ref_id",
                (run_id,),
            ).fetchall()
        state_refs: list[RuntimeStateRef] = []
        for row in rows:
            data = dict(row)
            data["state_payload"] = _json_load(data.pop("state_payload_json"))
            data["is_terminal"] = bool(data["is_terminal"])
            state_refs.append(RuntimeStateRef.model_validate(data))
        return state_refs

    def clear_for_run(self, run_id: str, connection: sqlite3.Connection | None = None) -> None:
        with self._connection(connection, commit=True) as conn:
            conn.execute("DELETE FROM runtime_state_refs WHERE run_id = ?", (run_id,))
