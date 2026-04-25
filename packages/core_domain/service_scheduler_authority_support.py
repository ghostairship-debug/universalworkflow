from __future__ import annotations

from packages.core_domain.service_scheduler_lease_projection import SchedulerLeaseProjectionService


class SchedulerAuthoritySupportService(SchedulerLeaseProjectionService):
    """Compatibility alias for legacy scheduler-authority support imports."""


__all__ = ["SchedulerAuthoritySupportService", "SchedulerLeaseProjectionService"]
