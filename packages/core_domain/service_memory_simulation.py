from __future__ import annotations

from typing import Any

from packages.contracts import (
    DomainPackDefinition,
    MemoryCandidate,
    MemoryItem,
    MemoryNamespace,
    MemoryRetrievalPreview,
    RunEvent,
    RunEventType,
    RunStatus,
    SimulationPolicyDefinition,
    SimulationRecord,
    SimulationRecordSource,
    SimulationReport,
    TaskKind,
)
from packages.core_domain.db import unit_of_work
from packages.core_domain.errors import EntityNotFoundError, PresetNotFoundError
from packages.core_domain.memory import load_seed_memory_namespaces


class MemorySimulationServiceMixin:
    def list_domain_packs(self) -> list[DomainPackDefinition]:
        return self.domain_pack_registry.list()

    def list_memory_namespaces(self) -> list[MemoryNamespace]:
        return load_seed_memory_namespaces()

    def list_memory_items(
        self,
        *,
        run_id: str | None = None,
        namespace_id: str | None = None,
    ) -> list[MemoryItem]:
        return self.memory_item_repo.list(run_id=run_id, namespace_id=namespace_id)

    def _memory_candidate_id(self, run_id: str, namespace_id: str) -> str:
        return f"memcand_{run_id}_{namespace_id}"

    def preview_domain_pack_resolution(
        self,
        preset_id: str,
        task_kind: TaskKind | str | None = None,
        adapter_name: str | None = None,
    ) -> dict[str, Any]:
        preset = self.preset_repo.get(preset_id)
        if preset is None:
            raise PresetNotFoundError(f"preset not found: {preset_id}")
        resolved_task_kind = self._resolve_task_kind(preset, task_kind)
        domain_pack = self._resolve_domain_pack(preset, resolved_task_kind)
        selected_adapter = adapter_name or (
            domain_pack.capability_exposure.preferred_adapter_name if domain_pack is not None else None
        )
        capability_route = self._resolve_capability_route(resolved_task_kind, requested_adapter=selected_adapter)
        return {
            "preset": preset.model_dump(mode="json"),
            "task_kind": str(resolved_task_kind),
            "domain_pack": domain_pack.model_dump(mode="json") if domain_pack is not None else None,
            "capability_resolution": capability_route.model_dump(mode="json") if capability_route is not None else None,
            "resolved": domain_pack is not None,
        }

    def validate_domain_pack_catalog(self) -> dict[str, Any]:
        return self.domain_pack_registry.validate_catalog(self.list_presets(), self.list_capability_routes())

    def list_capability_routes(self) -> list[dict[str, str]]:
        return self.worker_router.routes()

    def runtime_gateway_status(self) -> dict[str, Any]:
        return self.runtime_gateway.describe()

    def list_simulation_policies(self) -> list[SimulationPolicyDefinition]:
        return self.simulation_policy_registry.list()

    def get_run_memory_candidates(self, run_id: str) -> list[MemoryCandidate]:
        detail = self.get_status_detail(run_id)
        summary = self.get_run_summary(run_id)
        inspection = self.inspect_run_state(run_id)
        audit_report = self.get_run_audit_report(run_id)
        timeline = self.get_timeline(run_id)
        runtime_task_ids = detail.get("runtime_task_ids", [])
        latest_review = detail.get("latest_review_verdict")
        domain_pack = detail.get("domain_pack")
        namespaces = {item.namespace_id: item for item in self.list_memory_namespaces()}

        candidates: list[MemoryCandidate] = []
        if "repo" in namespaces:
            candidates.append(
                MemoryCandidate(
                    candidate_id=self._memory_candidate_id(run_id, "repo"),
                    run_id=run_id,
                    namespace_id="repo",
                    title=f"Run summary for {detail['run']['preset_id']}",
                    summary=summary["headline"],
                    tags=[
                        detail["run"]["status"],
                        detail["review_policy"],
                        domain_pack["domain_pack_id"] if domain_pack is not None else "no_domain_pack",
                    ],
                    source_refs=[
                        f"run:{run_id}",
                        *[f"task:{task_id}" for task_id in runtime_task_ids],
                    ],
                )
            )
        if "policy" in namespaces:
            candidates.append(
                MemoryCandidate(
                    candidate_id=self._memory_candidate_id(run_id, "policy"),
                    run_id=run_id,
                    namespace_id="policy",
                    title=f"Review policy outcome for {run_id}",
                    summary=(
                        f"Policy `{detail['review_policy']}` ended in "
                        f"`{detail['effective_review_state']}` with next action `{detail['next_action']}`."
                    ),
                    tags=[detail["review_policy"], detail["effective_review_state"]],
                    source_refs=[
                        f"run:{run_id}",
                        *( [f"verdict:{latest_review['verdict_id']}"] if latest_review is not None else [] ),
                    ],
                )
            )
        failure_category = summary["failure_taxonomy"]["category"]
        if failure_category != "success" and "failure" in namespaces:
            candidates.append(
                MemoryCandidate(
                    candidate_id=self._memory_candidate_id(run_id, "failure"),
                    run_id=run_id,
                    namespace_id="failure",
                    title=f"Failure memory candidate for {run_id}",
                    summary=(
                        f"Failure category `{failure_category}` with closure state "
                        f"`{audit_report['review_packet']['closure_summary']['state']}`."
                    ),
                    tags=[
                        failure_category,
                        detail["run"]["status"],
                        detail["failure_reason"] or "no_failure_reason",
                    ],
                    source_refs=[f"run:{run_id}", "audit:run_audit_report"],
                )
            )
        if detail["run"]["status"] == RunStatus.completed and "release" in namespaces:
            candidates.append(
                MemoryCandidate(
                    candidate_id=self._memory_candidate_id(run_id, "release"),
                    run_id=run_id,
                    namespace_id="release",
                    title=f"Release-ready candidate for {run_id}",
                    summary=(
                        f"Completed run with review state `{detail['effective_review_state']}` and "
                        f"{inspection['problem_count']} inspection problems."
                    ),
                    tags=[
                        "completed",
                        detail["effective_review_state"],
                        domain_pack["domain_pack_id"] if domain_pack is not None else "generic",
                    ],
                    source_refs=[
                        f"run:{run_id}",
                        *( [f"event:{event.event_id}" for event in timeline[-3:]] ),
                    ],
                )
            )
        return candidates

    def materialize_run_memory_candidate(self, run_id: str, candidate_id: str) -> MemoryItem:
        candidates = self.get_run_memory_candidates(run_id)
        selected_candidate = next((item for item in candidates if item.candidate_id == candidate_id), None)
        if selected_candidate is None:
            raise EntityNotFoundError("memory_candidate", candidate_id)

        existing_item = self.memory_item_repo.get_by_source_candidate(candidate_id)
        if existing_item is not None:
            return existing_item

        with unit_of_work(self.db_path) as connection:
            memory_item = MemoryItem(
                run_id=run_id,
                namespace_id=selected_candidate.namespace_id,
                source_candidate_id=selected_candidate.candidate_id,
                title=selected_candidate.title,
                summary=selected_candidate.summary,
                tags=selected_candidate.tags,
                source_refs=selected_candidate.source_refs,
            )
            self.memory_item_repo.create(memory_item, connection=connection)
            self.event_repo.append(
                RunEvent(
                    run_id=run_id,
                    event_type=RunEventType.memory_item_materialized,
                    object_type="memory_item",
                    object_id=memory_item.memory_item_id,
                    summary=f"Memory item materialized in namespace `{memory_item.namespace_id}`",
                    payload_json={
                        "run_id": run_id,
                        "memory_item_id": memory_item.memory_item_id,
                        "namespace_id": memory_item.namespace_id,
                        "source_candidate_id": memory_item.source_candidate_id,
                    },
                ),
                connection=connection,
            )
        return memory_item

    def preview_memory_retrieval(
        self,
        *,
        preset_id: str | None = None,
        run_id: str | None = None,
        namespace_id: str | None = None,
        memory_item_ids: list[str] | None = None,
        limit: int = 5,
    ) -> MemoryRetrievalPreview:
        if run_id is not None:
            self.get_run(run_id)
        if preset_id is not None and self.preset_repo.get(preset_id) is None:
            raise PresetNotFoundError(f"preset not found: {preset_id}")

        items = self.list_memory_items(run_id=run_id, namespace_id=namespace_id)

        if preset_id is not None:
            items = [
                item
                for item in items
                if (origin_run := self.run_repo.get(item.run_id)) is not None and origin_run.preset_id == preset_id
            ]

        items = sorted(items, key=lambda item: (item.created_at, item.memory_item_id), reverse=True)

        if memory_item_ids:
            item_by_id = {item.memory_item_id: item for item in items}
            missing_item_ids = [item_id for item_id in memory_item_ids if item_id not in item_by_id]
            if missing_item_ids:
                raise EntityNotFoundError("memory_item", ",".join(missing_item_ids))
            selected_items = [item_by_id[item_id] for item_id in memory_item_ids]
        else:
            selected_items = items[:limit]

        namespace_ids = list(dict.fromkeys(item.namespace_id for item in selected_items))
        source_run_ids = list(dict.fromkeys(item.run_id for item in selected_items))
        brief_lines = [f"[{item.namespace_id}] {item.title}: {item.summary}" for item in selected_items]

        return MemoryRetrievalPreview(
            run_id=run_id,
            preset_id=preset_id,
            namespace_ids=namespace_ids,
            selected_memory_item_ids=[item.memory_item_id for item in selected_items],
            source_run_ids=source_run_ids,
            item_count=len(selected_items),
            brief_lines=brief_lines,
            items=selected_items,
        )

    def get_run_simulation(self, run_id: str) -> SimulationReport:
        detail = self.get_status_detail(run_id)
        inspection = self.inspect_run_state(run_id)
        return self._simulation_report_for(detail, inspection)

    def _persist_simulation_record(
        self,
        run_id: str,
        report: SimulationReport,
        *,
        recorded_from: SimulationRecordSource,
        connection,
    ) -> SimulationRecord:
        record = SimulationRecord(
            run_id=run_id,
            policy_id=report.policy_id,
            status=report.status,
            triggered=report.triggered,
            summary=report.summary,
            recorded_from=recorded_from,
            report=report,
        )
        self.simulation_record_repo.create(record, connection=connection)
        self.event_repo.append(
            RunEvent(
                run_id=run_id,
                event_type=RunEventType.simulation_recorded,
                object_type="simulation_record",
                object_id=record.record_id,
                summary=f"Simulation record persisted ({record.recorded_from})",
                payload_json={
                    "run_id": run_id,
                    "record_id": record.record_id,
                    "policy_id": record.policy_id,
                    "status": record.status,
                    "triggered": record.triggered,
                    "recorded_from": record.recorded_from,
                },
            ),
            connection=connection,
        )
        return record

    def _record_lifecycle_simulation_if_triggered(
        self,
        run_id: str,
        recorded_from: SimulationRecordSource,
    ) -> SimulationRecord | None:
        self.get_run(run_id)
        report = self.get_run_simulation(run_id)
        if not report.triggered:
            return None
        with unit_of_work(self.db_path) as connection:
            return self._persist_simulation_record(
                run_id,
                report,
                recorded_from=recorded_from,
                connection=connection,
            )

    def record_run_simulation(
        self,
        run_id: str,
        recorded_from: SimulationRecordSource = SimulationRecordSource.manual_request,
    ) -> SimulationRecord:
        self.get_run(run_id)
        report = self.get_run_simulation(run_id)
        with unit_of_work(self.db_path) as connection:
            return self._persist_simulation_record(
                run_id,
                report,
                recorded_from=recorded_from,
                connection=connection,
            )

    def list_simulation_records(self, run_id: str) -> list[SimulationRecord]:
        self.get_run(run_id)
        return self.simulation_record_repo.list_for_run(run_id)
