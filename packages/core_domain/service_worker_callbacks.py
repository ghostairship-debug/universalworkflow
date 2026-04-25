from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from packages.contracts import LeaseRenewalRecord, RunEvent, RunEventType, RuntimeStateRef
from packages.core_domain.db import unit_of_work
from packages.core_domain.errors import EntityNotFoundError

if TYPE_CHECKING:
    from packages.core_domain.services import OrchestratorService


class WorkerCallbackServiceMixin:
    """Remote worker callback facade methods."""

    def _worker_callback_registry(
        self: "OrchestratorService",
        state_ref: RuntimeStateRef | None,
    ) -> dict[str, list[str]]:
        if state_ref is None:
            return {"heartbeat": [], "completion": []}
        callbacks = state_ref.state_payload.get("worker_callbacks")
        if not isinstance(callbacks, dict):
            return {"heartbeat": [], "completion": []}
        heartbeat = callbacks.get("heartbeat")
        completion = callbacks.get("completion")
        return {
            "heartbeat": [str(item) for item in heartbeat] if isinstance(heartbeat, list) else [],
            "completion": [str(item) for item in completion] if isinstance(completion, list) else [],
        }

    def _append_worker_callback(
        self: "OrchestratorService",
        state_ref: RuntimeStateRef,
        *,
        callback_type: str,
        callback_id: str,
        payload: dict[str, Any],
    ) -> RuntimeStateRef:
        registry = self._worker_callback_registry(state_ref)
        callback_ids = registry.setdefault(callback_type, [])
        if callback_id not in callback_ids:
            callback_ids.append(callback_id)
        callback_history = list(state_ref.state_payload.get("worker_callback_history") or [])
        callback_history.append({"type": callback_type, "callback_id": callback_id, **payload})
        return self._state_ref_with_payload_updates(
            state_ref,
            {
                "worker_callbacks": registry,
                "worker_callback_history": callback_history[-20:],
            },
        )

    def record_worker_heartbeat(
        self: "OrchestratorService",
        *,
        callback_id: str,
        dispatch_id: str,
        run_id: str,
        runtime_task_id: str,
        lease_id: str,
        worker_pool_id: str,
        heartbeat_at: str,
        lease_expires_at: str,
        execution_target: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with unit_of_work(self.db_path) as connection:
            state_ref = self.runtime_state_repo.get_by_task(runtime_task_id, connection=connection)
            if state_ref is None:
                raise EntityNotFoundError("runtime_state_ref", runtime_task_id)
            committed_lease = self._validate_callback_scheduler_context(
                runtime_task_id=runtime_task_id,
                execution_target=execution_target,
                connection=connection,
            )
            registry = self._worker_callback_registry(state_ref)
            if callback_id in registry["heartbeat"]:
                return {"accepted": True, "duplicate": True, "callback_id": callback_id}
            lease = self.worker_lease_repo.touch(
                lease_id,
                heartbeat_at=heartbeat_at,
                lease_expires_at=lease_expires_at,
                connection=connection,
            )
            if lease is None:
                raise EntityNotFoundError("worker_lease", lease_id)
            renewed_at = datetime.fromisoformat(heartbeat_at)
            renewal = LeaseRenewalRecord(
                run_id=run_id,
                runtime_task_id=runtime_task_id,
                worker_pool_id=worker_pool_id,
                lease_id=lease_id,
                status="renewed",
                renewed_at=renewed_at,
                heartbeat_at=renewed_at,
                lease_expires_at=datetime.fromisoformat(lease_expires_at),
                callback_id=callback_id,
                source="worker_callback",
            )
            current_renewals = self._lease_renewals_for(state_ref, None)
            if callback_id not in {item.get("callback_id") for item in current_renewals if isinstance(item, dict)}:
                current_renewals.append(renewal.model_dump(mode="json"))
            payload_updates: dict[str, Any] = {
                "lease_renewals": current_renewals[-20:],
            }
            if execution_target is not None:
                payload_updates["execution_target"] = {
                    **execution_target,
                    "last_callback_at": heartbeat_at,
                }
                payload_updates["committed_scheduler_lease"] = self._scheduler_committed_lease_payload(committed_lease)
            updated_state = self._append_worker_callback(
                self._state_ref_with_payload_updates(state_ref, payload_updates),
                callback_type="heartbeat",
                callback_id=callback_id,
                payload={
                    "dispatch_id": dispatch_id,
                    "lease_id": lease_id,
                    "heartbeat_at": heartbeat_at,
                    "lease_expires_at": lease_expires_at,
                },
            )
            self.runtime_state_repo.upsert(updated_state, connection=connection)
            self.event_repo.append(
                RunEvent(
                    run_id=run_id,
                    event_type=RunEventType.worker_heartbeat_received,
                    object_type="worker_lease",
                    object_id=lease_id,
                    summary="Worker heartbeat received",
                    payload_json={
                        "run_id": run_id,
                        "runtime_task_id": runtime_task_id,
                        "lease_id": lease_id,
                        "worker_pool_id": worker_pool_id,
                        "callback_id": callback_id,
                        "heartbeat_at": heartbeat_at,
                        "lease_expires_at": lease_expires_at,
                    },
                ),
                connection=connection,
            )
        return {"accepted": True, "duplicate": False, "callback_id": callback_id}

    def record_worker_completion(
        self: "OrchestratorService",
        *,
        callback_id: str,
        dispatch_id: str,
        run_id: str,
        runtime_task_id: str,
        lease_id: str,
        worker_pool_id: str,
        execution_target: dict[str, Any],
        lease_renewals: list[dict[str, Any]] | None = None,
        execution_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with unit_of_work(self.db_path) as connection:
            state_ref = self.runtime_state_repo.get_by_task(runtime_task_id, connection=connection)
            if state_ref is None:
                raise EntityNotFoundError("runtime_state_ref", runtime_task_id)
            committed_lease = self._validate_callback_scheduler_context(
                runtime_task_id=runtime_task_id,
                execution_target=execution_target,
                connection=connection,
            )
            registry = self._worker_callback_registry(state_ref)
            if callback_id in registry["completion"]:
                return {"accepted": True, "duplicate": True, "callback_id": callback_id}
            payload_updates: dict[str, Any] = {
                "execution_target": {
                    **execution_target,
                    "last_callback_at": self._utc_now().isoformat(),
                },
                "committed_scheduler_lease": self._scheduler_committed_lease_payload(committed_lease),
            }
            if lease_renewals is not None:
                merged_renewals = self._lease_renewals_for(state_ref, None)
                seen_callback_ids = {
                    item.get("callback_id")
                    for item in merged_renewals
                    if isinstance(item, dict)
                }
                for renewal in lease_renewals:
                    callback_ref = renewal.get("callback_id") if isinstance(renewal, dict) else None
                    if callback_ref and callback_ref in seen_callback_ids:
                        continue
                    if isinstance(renewal, dict):
                        merged_renewals.append(renewal)
                        if callback_ref:
                            seen_callback_ids.add(callback_ref)
                payload_updates["lease_renewals"] = merged_renewals[-20:]
            if execution_result is not None:
                payload_updates["remote_execution_result"] = execution_result
            updated_state = self._append_worker_callback(
                self._state_ref_with_payload_updates(state_ref, payload_updates),
                callback_type="completion",
                callback_id=callback_id,
                payload={
                    "dispatch_id": dispatch_id,
                    "lease_id": lease_id,
                    "return_code": execution_result.get("return_code") if execution_result is not None else None,
                },
            )
            self.runtime_state_repo.upsert(updated_state, connection=connection)
            self.event_repo.append(
                RunEvent(
                    run_id=run_id,
                    event_type=RunEventType.worker_completion_recorded,
                    object_type="runtime_task",
                    object_id=runtime_task_id,
                    summary="Worker completion callback recorded",
                    payload_json={
                        "run_id": run_id,
                        "runtime_task_id": runtime_task_id,
                        "lease_id": lease_id,
                        "worker_pool_id": worker_pool_id,
                        "callback_id": callback_id,
                        "dispatch_id": dispatch_id,
                        "return_code": execution_result.get("return_code") if execution_result is not None else None,
                    },
                ),
                connection=connection,
            )
        return {"accepted": True, "duplicate": False, "callback_id": callback_id}
