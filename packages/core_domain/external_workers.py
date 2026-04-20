from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable

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
    def describe(self) -> dict[str, object]:
        return {
            "enabled": is_external_worker_pools_enabled(),
            "supported_dispatch_modes": ["loopback"],
        }

    def dispatch(
        self,
        *,
        packet: TaskPacket,
        profile: WorkerPoolProfile,
        lease_id: str,
        launch_local: Callable[[TaskPacket], ExecutionResult],
    ) -> ExternalDispatchResult:
        started_at = _utc_now()
        execution_result = launch_local(packet)
        renewed_at = _utc_now()
        lease_expires_at = renewed_at + timedelta(seconds=300)
        execution_target = ExecutionTargetRef(
            target_kind=ExecutionTargetKind.external_worker_pool,
            worker_pool_id=profile.worker_pool_id,
            adapter_name=profile.adapter_name,
            dispatch_mode=profile.dispatch_mode,
            worker_name=profile.name,
            worker_id=f"pool_{profile.worker_pool_id}",
            dispatched_at=started_at.isoformat(),
        )
        renewal = LeaseRenewalRecord(
            run_id=packet.run_id,
            runtime_task_id=packet.runtime_task_id,
            worker_pool_id=profile.worker_pool_id,
            lease_id=lease_id,
            status="renewed",
            renewed_at=renewed_at,
            lease_expires_at=lease_expires_at,
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
