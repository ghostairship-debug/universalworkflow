from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from packages.contracts import ControlPlaneHandoffEnvelope
from packages.core_domain.db import unit_of_work


def _utc_now() -> datetime:
    return datetime.now(UTC)


class LocalSchedulerHandoffMixin:
    def create_handoff_envelope(
        self,
        *,
        run_id: str,
        runtime_task_id: str,
        from_control_plane_id: str,
        to_control_plane_id: str,
        committed_lease_id: str,
        term_no: int,
        commit_index: int,
        snapshot_payload: dict[str, Any],
        review_state: dict[str, Any],
        durable_refs: dict[str, Any],
        replay_excerpt: dict[str, Any],
        connection: sqlite3.Connection | None = None,
    ) -> ControlPlaneHandoffEnvelope:
        if connection is not None:
            return self._create_handoff_envelope(
                connection,
                run_id=run_id,
                runtime_task_id=runtime_task_id,
                from_control_plane_id=from_control_plane_id,
                to_control_plane_id=to_control_plane_id,
                committed_lease_id=committed_lease_id,
                term_no=term_no,
                commit_index=commit_index,
                snapshot_payload=snapshot_payload,
                review_state=review_state,
                durable_refs=durable_refs,
                replay_excerpt=replay_excerpt,
            )
        with unit_of_work(self.db_path) as owned:
            return self._create_handoff_envelope(
                owned,
                run_id=run_id,
                runtime_task_id=runtime_task_id,
                from_control_plane_id=from_control_plane_id,
                to_control_plane_id=to_control_plane_id,
                committed_lease_id=committed_lease_id,
                term_no=term_no,
                commit_index=commit_index,
                snapshot_payload=snapshot_payload,
                review_state=review_state,
                durable_refs=durable_refs,
                replay_excerpt=replay_excerpt,
            )

    def _create_handoff_envelope(
        self,
        connection: sqlite3.Connection,
        *,
        run_id: str,
        runtime_task_id: str,
        from_control_plane_id: str,
        to_control_plane_id: str,
        committed_lease_id: str,
        term_no: int,
        commit_index: int,
        snapshot_payload: dict[str, Any],
        review_state: dict[str, Any],
        durable_refs: dict[str, Any],
        replay_excerpt: dict[str, Any],
    ) -> ControlPlaneHandoffEnvelope:
        envelope = ControlPlaneHandoffEnvelope(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            from_control_plane_id=from_control_plane_id,
            to_control_plane_id=to_control_plane_id,
            committed_lease_id=committed_lease_id,
            term_no=term_no,
            commit_index=commit_index,
            snapshot_payload=snapshot_payload,
            review_state=review_state,
            durable_refs=durable_refs,
            replay_excerpt=replay_excerpt,
        )
        connection.execute(
            """
            INSERT INTO control_plane_handoff_envelopes (
              envelope_id, run_id, runtime_task_id, from_control_plane_id, to_control_plane_id, committed_lease_id,
              term_no, commit_index, snapshot_payload_json, review_state_json, durable_refs_json, replay_excerpt_json,
              schema_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                envelope.envelope_id,
                envelope.run_id,
                envelope.runtime_task_id,
                envelope.from_control_plane_id,
                envelope.to_control_plane_id,
                envelope.committed_lease_id,
                envelope.term_no,
                envelope.commit_index,
                json.dumps(envelope.snapshot_payload, ensure_ascii=False),
                json.dumps(envelope.review_state, ensure_ascii=False),
                json.dumps(envelope.durable_refs, ensure_ascii=False),
                json.dumps(envelope.replay_excerpt, ensure_ascii=False),
                envelope.schema_version,
                envelope.created_at.isoformat(),
            ),
        )
        return envelope

    def list_handoff_envelopes_for_run(
        self,
        run_id: str,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> list[ControlPlaneHandoffEnvelope]:
        if connection is not None:
            return self._list_handoff_envelopes_for_run(connection, run_id=run_id)
        with unit_of_work(self.db_path) as owned:
            return self._list_handoff_envelopes_for_run(owned, run_id=run_id)

    def _list_handoff_envelopes_for_run(
        self,
        connection: sqlite3.Connection,
        *,
        run_id: str,
    ) -> list[ControlPlaneHandoffEnvelope]:
        rows = connection.execute(
            """
            SELECT * FROM control_plane_handoff_envelopes
             WHERE run_id = ?
             ORDER BY created_at, envelope_id
            """,
            (run_id,),
        ).fetchall()
        return [self._row_to_handoff(row) for row in rows]
