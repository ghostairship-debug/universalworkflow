from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _run_scheduler_probe(*, cluster_enabled: bool) -> dict[str, object]:
    script = r"""
import json
import os
import sys
import tempfile
from pathlib import Path

if CLUSTER_ENABLED:
    os.environ["UAWO_ENABLE_SCHEDULER_AUTHORITY_CLUSTER"] = "1"
else:
    os.environ.pop("UAWO_ENABLE_SCHEDULER_AUTHORITY_CLUSTER", None)

from packages.core_domain.db import migrate
from packages.core_domain.services import OrchestratorService

db_path = Path(tempfile.mkdtemp(prefix="scheduler-isolation-")) / "workflow.db"
migrate(db_path)
service = OrchestratorService(db_path)
print(json.dumps({
    "cluster_enabled": service.scheduler_authority_cluster_enabled,
    "cluster_module": service.scheduler_authority_cluster.__class__.__module__,
    "cluster_class": service.scheduler_authority_cluster.__class__.__name__,
    "scheduler_authority_imported": "packages.core_domain.scheduler_authority" in sys.modules,
    "legacy_support_imported": "packages.core_domain.service_scheduler_authority_support" in sys.modules,
}))
"""
    script = script.replace("CLUSTER_ENABLED", "True" if cluster_enabled else "False")
    env = os.environ.copy()
    env.pop("UAWO_ENABLE_SCHEDULER_AUTHORITY_CLUSTER", None)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_scheduler_flag_off_does_not_import_cluster_runtime() -> None:
    payload = _run_scheduler_probe(cluster_enabled=False)

    assert payload == {
        "cluster_enabled": False,
        "cluster_module": "packages.core_domain.local_scheduler_lease_arbiter",
        "cluster_class": "LocalSchedulerLeaseArbiter",
        "scheduler_authority_imported": False,
        "legacy_support_imported": False,
    }


def test_scheduler_flag_on_lazy_imports_cluster_runtime() -> None:
    payload = _run_scheduler_probe(cluster_enabled=True)

    assert payload["cluster_enabled"] is True
    assert payload["cluster_module"] == "packages.core_domain.scheduler_authority"
    assert payload["cluster_class"] == "SchedulerAuthorityClusterService"
    assert payload["scheduler_authority_imported"] is True
    assert payload["legacy_support_imported"] is False
