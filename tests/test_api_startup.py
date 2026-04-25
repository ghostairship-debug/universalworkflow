from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _import_probe(module_name: str, db_path: Path) -> dict[str, object]:
    script = f"""
import json
import os
from pathlib import Path

db_path = Path(os.environ["WORKFLOW_DB_PATH"])
import {module_name} as target
print(json.dumps({{
    "db_exists": db_path.exists(),
    "app_class": target.app.__class__.__name__,
}}))
"""
    env = os.environ.copy()
    env["WORKFLOW_DB_PATH"] = str(db_path)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_orchestrator_api_import_does_not_migrate_default_db(tmp_path: Path) -> None:
    payload = _import_probe("apps.orchestrator_api.main", tmp_path / "workflow.db")

    assert payload == {"db_exists": False, "app_class": "LazyASGIApp"}


def test_scheduler_authority_api_import_does_not_migrate_default_db(tmp_path: Path) -> None:
    payload = _import_probe("apps.scheduler_authority_api.main", tmp_path / "scheduler.db")

    assert payload == {"db_exists": False, "app_class": "LazyASGIApp"}
