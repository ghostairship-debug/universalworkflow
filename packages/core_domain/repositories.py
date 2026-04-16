from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.contracts import (
    Evidence,
    Phase,
    PresetDefinition,
    ReviewVerdict,
    Run,
    RunEvent,
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


class RunRepository(RepositoryBase):
    def create(self, run: Run) -> Run:
        with get_connection(self.db_path) as connection:
            connection.execute(
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
            connection.commit()
        return run

    def get(self, run_id: str) -> Run | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return Run.model_validate(dict(row)) if row else None

    def update_status(self, run_id: str, status: str) -> Run | None:
        with get_connection(self.db_path) as connection:
            connection.execute("UPDATE runs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE run_id = ?", (status, run_id))
            connection.commit()
        return self.get(run_id)


class PresetRepository(RepositoryBase):
    def upsert(self, preset: PresetDefinition) -> PresetDefinition:
        with get_connection(self.db_path) as connection:
            connection.execute(
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
            connection.commit()
        return preset

    def seed_defaults(self) -> list[PresetDefinition]:
        presets = load_seed_presets()
        for preset in presets:
            self.upsert(preset)
        return presets

    def get(self, preset_id: str) -> PresetDefinition | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM preset_definitions WHERE preset_id = ?",
                (preset_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_model(row)

    def list(self) -> list[PresetDefinition]:
        with get_connection(self.db_path) as connection:
            rows = connection.execute("SELECT * FROM preset_definitions ORDER BY preset_id").fetchall()
        return [self._row_to_model(row) for row in rows]

    def _row_to_model(self, row: Any) -> PresetDefinition:
        data = dict(row)
        data["allowed_task_kinds"] = _json_load(data.pop("allowed_task_kinds_json"))
        data["default_budget_policy"] = _json_load(data.pop("default_budget_policy_json"))
        data["requires_manual_approval"] = bool(data["requires_manual_approval"])
        return PresetDefinition.model_validate(data)


class TaskRepository(RepositoryBase):
    def create_phase(self, phase: Phase) -> Phase:
        with get_connection(self.db_path) as connection:
            connection.execute(
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
            connection.commit()
        return phase

    def create_task_card(self, task_card: TaskCard) -> TaskCard:
        with get_connection(self.db_path) as connection:
            connection.execute(
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
            connection.commit()
        return task_card

    def create_runtime_task(self, runtime_task: RuntimeTask) -> RuntimeTask:
        with get_connection(self.db_path) as connection:
            connection.execute(
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
            connection.commit()
        return runtime_task

    def create_task_packet(self, task_packet: TaskPacket) -> TaskPacket:
        with get_connection(self.db_path) as connection:
            connection.execute(
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
            connection.commit()
        return task_packet

    def update_runtime_task_status(self, runtime_task_id: str, status: TaskStatus | str) -> RuntimeTask | None:
        with get_connection(self.db_path) as connection:
            connection.execute(
                "UPDATE runtime_tasks SET status = ? WHERE runtime_task_id = ?",
                (str(status), runtime_task_id),
            )
            connection.commit()
        return self.get_runtime_task(runtime_task_id)

    def get_runtime_task(self, runtime_task_id: str) -> RuntimeTask | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM runtime_tasks WHERE runtime_task_id = ?",
                (runtime_task_id,),
            ).fetchone()
        return RuntimeTask.model_validate(dict(row)) if row else None

    def get_task_packet(self, runtime_task_id: str) -> TaskPacket | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM task_packets WHERE runtime_task_id = ?",
                (runtime_task_id,),
            ).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["command"] = _json_load(data.pop("command_json"))
        data["env"] = _json_load(data.pop("env_json"))
        data["expected_artifacts"] = _json_load(data.pop("expected_artifacts_json"))
        return TaskPacket.model_validate(data)

    def list_runtime_tasks_for_run(self, run_id: str) -> list[RuntimeTask]:
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM runtime_tasks WHERE run_id = ? ORDER BY created_at, runtime_task_id",
                (run_id,),
            ).fetchall()
        return [RuntimeTask.model_validate(dict(row)) for row in rows]


class EvidenceRepository(RepositoryBase):
    def create(self, evidence: Evidence) -> Evidence:
        with get_connection(self.db_path) as connection:
            connection.execute(
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
            connection.commit()
        return evidence

    def get_by_task(self, runtime_task_id: str) -> Evidence | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM evidence WHERE runtime_task_id = ?",
                (runtime_task_id,),
            ).fetchone()
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
    def create(self, verdict: ReviewVerdict) -> ReviewVerdict:
        with get_connection(self.db_path) as connection:
            connection.execute(
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
            connection.commit()
        return verdict

    def get_by_evidence(self, evidence_id: str) -> ReviewVerdict | None:
        with get_connection(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM review_verdicts WHERE evidence_id = ?",
                (evidence_id,),
            ).fetchone()
        return ReviewVerdict.model_validate(dict(row)) if row else None


class EventRepository(RepositoryBase):
    def append(self, event: RunEvent) -> RunEvent:
        payload = validate_event_payload(event.event_type, event.payload_json)
        with get_connection(self.db_path) as connection:
            connection.execute(
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
            connection.commit()
        return RunEvent.model_validate({**event.model_dump(mode="json"), "payload_json": payload})

    def list_for_run(self, run_id: str) -> list[RunEvent]:
        with get_connection(self.db_path) as connection:
            rows = connection.execute(
                "SELECT * FROM run_events WHERE run_id = ? ORDER BY created_at, event_id",
                (run_id,),
            ).fetchall()
        events: list[RunEvent] = []
        for row in rows:
            data = dict(row)
            data["payload_json"] = _json_load(data["payload_json"])
            events.append(RunEvent.model_validate(data))
        return events
