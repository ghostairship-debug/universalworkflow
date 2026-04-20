from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from packages.contracts import ExecutionTargetKind, ExecutionTargetRef, LeaseRenewalRecord, TaskPacket, WorkerPoolProfile
from packages.core_domain.config import build_effective_config
from packages.core_domain.m8_flags import is_external_worker_pools_enabled
from packages.worker_adapters.base import ExecutionResult


DEFAULT_WORKER_POOL_SEED_PATH = Path("infra/seeds/worker_pool_profiles.json")
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def load_worker_pool_profiles(seed_path: str | Path | None = None) -> list[WorkerPoolProfile]:
    configured_seed_path = seed_path
    if configured_seed_path is None:
        configured_seed_path = build_effective_config()["worker_pools"]["seed_path"]
    path = Path(str(configured_seed_path))
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [WorkerPoolProfile.model_validate(item) for item in payload]


def resolve_worker_pool_profile(
    profiles: list[WorkerPoolProfile],
    worker_pool_id: str | None,
) -> WorkerPoolProfile | None:
    if not worker_pool_id:
        return None
    for profile in profiles:
        if profile.worker_pool_id == worker_pool_id:
            return profile
    return None


@dataclass(slots=True)
class ExternalDispatchResult:
    execution_result: ExecutionResult
    execution_target: ExecutionTargetRef
    lease_renewals: list[LeaseRenewalRecord] = field(default_factory=list)


class ExternalWorkerGateway:
    def __init__(
        self,
        *,
        http_post: Callable[[str, dict[str, Any], dict[str, str] | None, int], dict[str, Any]] | None = None,
    ) -> None:
        self._http_post = http_post or self._default_http_post

    def describe(self) -> dict[str, object]:
        return {
            "enabled": is_external_worker_pools_enabled(),
            "supported_dispatch_modes": ["loopback", "remote_http"],
        }

    def _default_http_post(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        request = Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", **(headers or {})},
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"remote worker HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise RuntimeError(f"remote worker request failed: {exc}") from exc

    def _dispatch_loopback(
        self,
        *,
        packet: TaskPacket,
        profile: WorkerPoolProfile,
        lease_id: str,
        launch_local: Callable[[TaskPacket], ExecutionResult],
        scheduler_context: dict[str, Any] | None = None,
    ) -> ExternalDispatchResult:
        started_at = _utc_now()
        execution_result = launch_local(packet)
        renewed_at = _utc_now()
        lease_expires_at = renewed_at + timedelta(seconds=profile.lease_ttl_seconds)
        execution_target = ExecutionTargetRef(
            target_kind=ExecutionTargetKind.external_worker_pool,
            worker_pool_id=profile.worker_pool_id,
            adapter_name=profile.adapter_name,
            dispatch_mode=profile.dispatch_mode,
            worker_name=profile.name,
            worker_id=f"pool_{profile.worker_pool_id}",
            dispatched_at=started_at.isoformat(),
            dispatch_id=f"dispatch_{uuid4().hex[:12]}",
            base_url=profile.base_url,
            callback_base_url=profile.callback_base_url,
            auth_mode=profile.auth_mode,
            last_callback_at=renewed_at.isoformat(),
            control_plane_id=(scheduler_context or {}).get("control_plane_id"),
            committed_lease_id=(scheduler_context or {}).get("committed_lease_id"),
            fencing_token=(scheduler_context or {}).get("fencing_token"),
            term_no=(scheduler_context or {}).get("term_no"),
            commit_index=(scheduler_context or {}).get("commit_index"),
        )
        renewal = LeaseRenewalRecord(
            run_id=packet.run_id,
            runtime_task_id=packet.runtime_task_id,
            worker_pool_id=profile.worker_pool_id,
            lease_id=lease_id,
            status="renewed",
            renewed_at=renewed_at,
            lease_expires_at=lease_expires_at,
            heartbeat_at=renewed_at,
            source="loopback",
            control_plane_id=(scheduler_context or {}).get("control_plane_id"),
            committed_lease_id=(scheduler_context or {}).get("committed_lease_id"),
            fencing_token=(scheduler_context or {}).get("fencing_token"),
            term_no=(scheduler_context or {}).get("term_no"),
            commit_index=(scheduler_context or {}).get("commit_index"),
        )
        return ExternalDispatchResult(
            execution_result=ExecutionResult(
                runtime_task_id=execution_result.runtime_task_id,
                return_code=execution_result.return_code,
                stdout=execution_result.stdout,
                stderr=execution_result.stderr,
                started_at=execution_result.started_at,
                finished_at=execution_result.finished_at,
                duration_ms=execution_result.duration_ms,
                artifact_paths=execution_result.artifact_paths,
                adapter_name=execution_result.adapter_name,
                metadata={
                    **execution_result.metadata,
                    "execution_target": execution_target.model_dump(mode="json"),
                    "lease_renewals": [renewal.model_dump(mode="json")],
                },
            ),
            execution_target=execution_target,
            lease_renewals=[renewal],
        )

    def _dispatch_remote_http(
        self,
        *,
        packet: TaskPacket,
        profile: WorkerPoolProfile,
        lease_id: str,
        timeout_seconds: int,
        scheduler_context: dict[str, Any] | None = None,
    ) -> ExternalDispatchResult:
        if not profile.base_url:
            raise RuntimeError(f"worker pool `{profile.worker_pool_id}` requires base_url for remote_http dispatch")
        callback_base_url = profile.callback_base_url or build_effective_config()["worker_pools"]["callback_base_url"]
        dispatch_id = f"dispatch_{uuid4().hex[:12]}"
        headers: dict[str, str] = {}
        if profile.auth_mode == "shared_secret" and profile.shared_secret_env:
            shared_secret = os.getenv(profile.shared_secret_env)
            if not shared_secret:
                raise RuntimeError(
                    f"worker pool `{profile.worker_pool_id}` requires env `{profile.shared_secret_env}` for shared_secret auth"
                )
            headers["X-Workflow-Shared-Secret"] = shared_secret
        payload = {
            "dispatch_id": dispatch_id,
            "lease_id": lease_id,
            "packet": packet.model_dump(mode="json"),
            "profile": profile.model_dump(mode="json"),
            "callback_base_url": callback_base_url,
            "timeout_seconds": timeout_seconds,
            "scheduler_context": scheduler_context,
        }
        response = self._http_post(
            f"{profile.base_url.rstrip('/')}/dispatches",
            payload,
            headers,
            timeout_seconds,
        )
        execution_target = ExecutionTargetRef.model_validate(response["execution_target"])
        execution_result_payload = dict(response["execution_result"])
        execution_result = ExecutionResult(
            runtime_task_id=execution_result_payload["runtime_task_id"],
            return_code=int(execution_result_payload["return_code"]),
            stdout=execution_result_payload["stdout"],
            stderr=execution_result_payload["stderr"],
            started_at=datetime.fromisoformat(execution_result_payload["started_at"]),
            finished_at=datetime.fromisoformat(execution_result_payload["finished_at"]),
            duration_ms=int(execution_result_payload["duration_ms"]),
            artifact_paths=list(execution_result_payload.get("artifact_paths") or []),
            adapter_name=execution_result_payload["adapter_name"],
            metadata=dict(execution_result_payload.get("metadata") or {}),
        )
        lease_renewals = [LeaseRenewalRecord.model_validate(item) for item in response.get("lease_renewals", [])]
        return ExternalDispatchResult(
            execution_result=execution_result,
            execution_target=execution_target,
            lease_renewals=lease_renewals,
        )

    def dispatch(
        self,
        *,
        packet: TaskPacket,
        profile: WorkerPoolProfile,
        lease_id: str,
        launch_local: Callable[[TaskPacket], ExecutionResult],
        scheduler_context: dict[str, Any] | None = None,
    ) -> ExternalDispatchResult:
        timeout_seconds = build_effective_config()["worker_pools"]["remote_timeout_seconds"]
        if profile.dispatch_mode == "remote_http":
            return self._dispatch_remote_http(
                packet=packet,
                profile=profile,
                lease_id=lease_id,
                timeout_seconds=timeout_seconds,
                scheduler_context=scheduler_context,
            )
        return self._dispatch_loopback(
            packet=packet,
            profile=profile,
            lease_id=lease_id,
            launch_local=launch_local,
            scheduler_context=scheduler_context,
        )
