from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.contracts import (
    Evidence,
    ReviewDecision,
    ReviewPolicy,
    ReviewerType,
    ReviewVerdict,
    Run,
    RunSnapshot,
    RuntimeAttempt,
    RuntimeClaim,
    RuntimeStateRef,
    OwnershipActorKind,
    OwnershipDomainKind,
    RunStatus,
    TaskPacket,
    WorkerLease,
    allowed_run_status_transitions,
    can_transition_run_status,
)
from packages.core_domain.errors import (
    InvalidStateTransitionError,
)
from packages.core_domain.resolver import PresetResolver
from packages.core_domain.service_types import (
    RunDiagnosticContext,
)
from packages.core_domain.external_workers import (
    resolve_worker_pool_profile,
)
from packages.core_domain.m8_flags import (
    active_feature_flags,
    is_external_worker_pools_enabled,
)
from packages.core_domain.provider_access import list_provider_access_contracts
from packages.runtime_langgraph.gateway import resolve_runtime_gateway




class CoreHelperServiceMixin:
    def get_cluster_route_stats(self, *, days: int = 30) -> dict[str, Any]:
        return self.cluster_route_decision_repo.summarize_recent(days=days)

    def get_capability_route_stats(self, *, days: int = 30) -> dict[str, Any]:
        probe_stats = self.capability_probe_result_repo.summarize_recent(days=days)
        invocation_stats = self.capability_invocation_repo.summarize_recent_routes(days=days)
        contracts = {str(item["provider_key"]): item for item in list_provider_access_contracts()}
        providers = sorted(set(contracts) | set(probe_stats["providers"]) | set(invocation_stats["providers"]))
        provider_payloads: dict[str, Any] = {}
        for provider in providers:
            contract = contracts.get(provider, {})
            probe = probe_stats["providers"].get(provider, {})
            invocation = invocation_stats["providers"].get(provider, {})
            verified_count = int(probe.get("verified_count") or 0)
            invocation_success_count = int(invocation.get("success_count") or 0)
            provider_payloads[provider] = {
                "provider": provider,
                "display_name": contract.get("display_name") or provider,
                "category": contract.get("category"),
                "transport": contract.get("transport"),
                "modalities": list(contract.get("modalities") or []),
                "default_model": contract.get("default_model"),
                "auth_sources": list(contract.get("auth_sources") or []),
                "default_route": bool(contract.get("default_route")),
                "cost_hint": self._provider_cost_hint(contract),
                "fallback_policy": self._provider_fallback_policy(provider, contract),
                "verified_ready": verified_count > 0,
                "recently_successful": invocation_success_count > 0,
                "probe_summary": probe,
                "invocation_summary": invocation,
            }
        return {
            "schema_version": "m80_provider_route_stats_v1",
            "days": days,
            "provider_count": len(provider_payloads),
            "providers": provider_payloads,
        }

    def _provider_cost_hint(self, contract: dict[str, Any]) -> str:
        transport = str(contract.get("transport") or "")
        provider_key = str(contract.get("provider_key") or "")
        if provider_key == "shell":
            return "local_free"
        if transport == "cli":
            return "external_cli_account"
        if transport in {"api", "langchain"}:
            return "provider_variable"
        if transport == "mcp":
            return "tool_specific"
        return "unknown"

    def _provider_fallback_policy(self, provider: str, contract: dict[str, Any]) -> str:
        if provider == "deepseek_api":
            return "fallback_to_codex_cli"
        if provider in {"minimax_api", "opencode_cli"}:
            return "fallback_to_deepseek_then_codex"
        if provider in {"mmx_generation_api", "vertex_generation_api", "gcp_tts_api"}:
            return "blocked_if_required_asset_missing"
        if provider == "openai_api":
            return "not_primary_without_openai_api_key"
        if provider == "langchain_agent":
            return "experimental_opt_in_only"
        notes = " ".join(str(item) for item in contract.get("notes") or [])
        return notes[:240] if notes else "none"

    def _resolver(self) -> PresetResolver:
        return PresetResolver(self.preset_repo.list())

    def _require_status(self, run: Run, action: str, allowed_statuses: list[RunStatus | str]) -> None:
        allowed = [str(status) for status in allowed_statuses]
        if str(run.status) not in allowed:
            raise InvalidStateTransitionError(action, str(run.status), allowed)

    def _transition_run_status(
        self,
        run: Run,
        action: str,
        target_status: RunStatus | str,
        *,
        connection=None,
    ) -> Run:
        normalized_target = RunStatus(target_status)
        if not can_transition_run_status(run.status, normalized_target):
            raise InvalidStateTransitionError(
                action,
                str(run.status),
                [str(status) for status in allowed_run_status_transitions(run.status)],
                str(normalized_target),
            )
        updated_run = self.run_repo.update_status(run.run_id, normalized_target, connection=connection)
        assert updated_run is not None
        return updated_run

    def _next_action_for(self, status: str) -> str:
        if status == RunStatus.pending:
            return "compile"
        if status == RunStatus.prepared:
            return "resume"
        if status == RunStatus.awaiting_review:
            return "human_review"
        if status == RunStatus.running:
            return "observe"
        return "none"

    def _review_policy_for_context(
        self,
        context: RunDiagnosticContext,
        *,
        last_runtime_state: RuntimeStateRef | None = None,
    ) -> str:
        if context.preset is not None:
            return str(context.preset.default_review_policy)
        state_ref = last_runtime_state or self._last_runtime_state(context)
        if state_ref is not None and state_ref.state_payload.get("review_policy"):
            return str(state_ref.state_payload["review_policy"])
        return str(ReviewPolicy.auto_only)

    def _effective_review_state(
        self,
        run: Run,
        latest_review_verdict: ReviewVerdict | None,
        review_policy: ReviewPolicy | str | None = None,
    ) -> str:
        normalized_policy = str(review_policy or ReviewPolicy.auto_only)
        if str(run.status) == RunStatus.awaiting_review:
            if latest_review_verdict is None:
                return "human_pending"
            if str(latest_review_verdict.reviewer_type) != ReviewerType.human:
                return "human_pending"
        if latest_review_verdict is None:
            return "not_requested"
        if str(latest_review_verdict.reviewer_type) == ReviewerType.human:
            return "human_approved" if str(latest_review_verdict.decision) == ReviewDecision.pass_ else "human_rejected"
        if normalized_policy == str(ReviewPolicy.optional):
            return "advisory_passed" if str(latest_review_verdict.decision) == ReviewDecision.pass_ else "advisory_failed"
        return "auto_passed" if str(latest_review_verdict.decision) == ReviewDecision.pass_ else "auto_failed"

    def _serialize_contract(self, value: Evidence | ReviewVerdict | RuntimeStateRef | None) -> dict[str, Any] | None:
        return value.model_dump(mode="json") if value is not None else None

    def _serialize_claim(self, value: RuntimeClaim | None) -> dict[str, Any] | None:
        return value.model_dump(mode="json") if value is not None else None

    def _serialize_snapshot(self, value: RunSnapshot | None) -> dict[str, Any] | None:
        return value.model_dump(mode="json") if value is not None else None

    def _serialize_worker_lease(self, value: WorkerLease | None) -> dict[str, Any] | None:
        return value.model_dump(mode="json") if value is not None else None

    def _serialize_attempt(self, value: RuntimeAttempt | None) -> dict[str, Any] | None:
        return value.model_dump(mode="json") if value is not None else None

    def _control_plane_identity(self) -> tuple[str, str, str]:
        return (
            str(OwnershipActorKind.control_plane),
            "control_plane_local",
            "local_orchestrator",
        )

    def _worker_identity(self, adapter_name: str, *, worker_name: str | None = None) -> tuple[str, str, str]:
        normalized_adapter = (adapter_name or "worker").strip().lower().replace(" ", "_")
        return (
            str(OwnershipActorKind.worker),
            f"worker_{normalized_adapter}_local",
            worker_name or "local_worker",
        )

    def _ownership_domain_for(
        self,
        runtime_task_id: str,
        *,
        domain_kind: OwnershipDomainKind | str = OwnershipDomainKind.runtime_task,
        domain_key: str | None = None,
    ) -> tuple[str, str]:
        normalized_kind = str(OwnershipDomainKind(domain_kind))
        return normalized_kind, domain_key or runtime_task_id

    def _utc_now(self) -> datetime:
        return datetime.now(UTC)

    def _parse_iso_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

    def _workspace_root(self) -> Path:
        return Path(str(self.effective_config.get("workspace", {}).get("root") or Path.cwd())).resolve()

    def _feature_flags(self) -> dict[str, bool]:
        return active_feature_flags()

    def get_effective_config(self) -> dict[str, Any]:
        return self.effective_config

    def list_worker_pool_profiles(self) -> list[dict[str, Any]]:
        return [
            {
                **profile.model_dump(mode="json"),
                "feature_flag_enabled": is_external_worker_pools_enabled(),
                "default_selected": profile.worker_pool_id == self.effective_config["worker_pools"]["default_pool_id"],
            }
            for profile in self.worker_pool_profiles
        ]

    def _selected_worker_pool_profile(self, worker_pool_id: str | None = None) -> Any | None:
        if not is_external_worker_pools_enabled():
            return None
        return resolve_worker_pool_profile(
            self.worker_pool_profiles,
            worker_pool_id or self.effective_config["worker_pools"]["default_pool_id"],
        )

    def _runtime_gateway_for_task_packet(self, task_packet: TaskPacket):
        return resolve_runtime_gateway(
            self.runtime_gateway,
            provider=task_packet.env.get("WORKFLOW_RUNTIME_GATEWAY_PROVIDER") or None,
            model=(
                task_packet.env.get("WORKFLOW_RUNTIME_GATEWAY_MODEL")
                or task_packet.env.get("WORKFLOW_LLM_MODEL")
                or None
            ),
            reasoning_effort=task_packet.env.get("WORKFLOW_RUNTIME_REASONING_EFFORT") or None,
        )
