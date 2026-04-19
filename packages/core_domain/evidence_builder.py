from __future__ import annotations

import hashlib
from pathlib import Path

from packages.contracts import ArtifactRef, CheckResult, Evidence
from packages.worker_adapters.base import ExecutionResult


class EvidenceBuilder:
    def build(self, run_id: str, runtime_task_id: str, result: ExecutionResult) -> Evidence:
        artifact_refs = [self._artifact_ref_for(path) for path in result.artifact_paths]
        known_gaps: list[str] = []
        for artifact in artifact_refs:
            if artifact.mtime > result.finished_at.timestamp():
                known_gaps.append(
                    f"possible out-of-band change detected for {artifact.path}; review not blocked in M0"
                )

        checks = [
            CheckResult(
                name="return_code_zero",
                status="pass" if result.return_code == 0 else "fail",
                detail=f"return_code={result.return_code}",
            ),
            CheckResult(
                name="stderr_empty",
                status="pass" if not result.stderr.strip() else "warn",
                detail="stderr empty" if not result.stderr.strip() else "stderr contains output",
            ),
        ]
        summary = (
            "Execution completed successfully."
            if result.return_code == 0
            else "Execution completed with failures."
        )
        return Evidence(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            summary=summary,
            changed_files=[artifact.path for artifact in artifact_refs],
            checks=checks,
            known_gaps=known_gaps,
            artifact_refs=artifact_refs,
            return_code=result.return_code,
            raw_execution={
                "adapter_name": result.adapter_name,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "started_at": result.started_at.isoformat(),
                "finished_at": result.finished_at.isoformat(),
                "duration_ms": result.duration_ms,
                "artifact_paths": result.artifact_paths,
                "metadata": result.metadata,
            },
        )

    def _artifact_ref_for(self, artifact_path: str) -> ArtifactRef:
        path = Path(artifact_path)
        return ArtifactRef(
            path=path.resolve().as_posix(),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            mtime=path.stat().st_mtime,
            size_bytes=path.stat().st_size,
        )
