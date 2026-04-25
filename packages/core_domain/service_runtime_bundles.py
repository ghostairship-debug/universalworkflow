from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packages.contracts import RuntimeGateway
from packages.core_domain.capability_plane import CapabilityPlane
from packages.core_domain.repositories import (
    AutomationWatchdogRepository,
    BudgetLedgerRepository,
    CapabilityInvocationRepository,
    CapabilityProbeResultRepository,
    ChatMessageRepository,
    ChatStreamEventRepository,
    ClusterRouteDecisionRepository,
    EventRepository,
    EvidenceRepository,
    FollowupRequestRepository,
    GeneratedAgentProfileRepository,
    HandoffRepository,
    IntentSessionRepository,
    MemoryItemRepository,
    OperatorActionReceiptRepository,
    PresetRepository,
    ReviewRepository,
    RunRepository,
    RunSnapshotRepository,
    RuntimeAttemptRepository,
    RuntimeClaimRepository,
    RuntimeStateRepository,
    SchedulerLeaseDecisionRepository,
    SchedulerLeaseProposalRepository,
    SchedulerPeerHeartbeatRepository,
    SimulationRecordRepository,
    TaskRepository,
    WorkerLeaseRepository,
)
from packages.core_domain.m8_flags import is_agent_lane_enabled, is_sessionful_external_agents_enabled
from packages.runtime_langgraph.chat_control_graph import ChatControlGraph
from packages.runtime_langgraph.chat_runtime import ChatLLMRuntime, build_chat_llm_runtime_from_env
from packages.runtime_langgraph.gateway import build_runtime_gateway_from_env
from packages.worker_adapters.base import WorkerAdapter
from packages.worker_adapters.codex_adapter import CodexAdapter
from packages.worker_adapters.external_artifact_adapters import (
    ClaudeArchitectAdapter,
    MMXMultimodalAdapter,
    VertexMultimodalAdapter,
)
from packages.worker_adapters.langchain_agent_adapter import LangChainAgentAdapter
from packages.worker_adapters.noop_adapter import NoopAdapter
from packages.worker_adapters.opencode_adapter import OpenCodeAdapter
from packages.worker_adapters.opencode_session_adapter import OpenCodeSessionAdapter
from packages.worker_adapters.router import WorkerRouter
from packages.worker_adapters.shell_adapter import ShellAdapter


class RepositoryBundle:
    """Owns repository construction so OrchestratorService does not wire them flat."""

    def __init__(self, db_path: str | Path | None) -> None:
        self.run_repo = RunRepository(db_path)
        self.preset_repo = PresetRepository(db_path)
        self.budget_repo = BudgetLedgerRepository(db_path)
        self.task_repo = TaskRepository(db_path)
        self.event_repo = EventRepository(db_path)
        self.evidence_repo = EvidenceRepository(db_path)
        self.review_repo = ReviewRepository(db_path)
        self.handoff_repo = HandoffRepository(db_path)
        self.runtime_state_repo = RuntimeStateRepository(db_path)
        self.runtime_attempt_repo = RuntimeAttemptRepository(db_path)
        self.runtime_claim_repo = RuntimeClaimRepository(db_path)
        self.worker_lease_repo = WorkerLeaseRepository(db_path)
        self.scheduler_proposal_repo = SchedulerLeaseProposalRepository(db_path)
        self.scheduler_decision_repo = SchedulerLeaseDecisionRepository(db_path)
        self.scheduler_peer_heartbeat_repo = SchedulerPeerHeartbeatRepository(db_path)
        self.snapshot_repo = RunSnapshotRepository(db_path)
        self.memory_item_repo = MemoryItemRepository(db_path)
        self.intent_session_repo = IntentSessionRepository(db_path)
        self.followup_request_repo = FollowupRequestRepository(db_path)
        self.chat_message_repo = ChatMessageRepository(db_path)
        self.chat_stream_event_repo = ChatStreamEventRepository(db_path)
        self.cluster_route_decision_repo = ClusterRouteDecisionRepository(db_path)
        self.capability_invocation_repo = CapabilityInvocationRepository(db_path)
        self.capability_probe_result_repo = CapabilityProbeResultRepository(db_path)
        self.operator_action_receipt_repo = OperatorActionReceiptRepository(db_path)
        self.generated_agent_profile_repo = GeneratedAgentProfileRepository(db_path)
        self.automation_watchdog_repo = AutomationWatchdogRepository(db_path)
        self.simulation_record_repo = SimulationRecordRepository(db_path)

    def install_on(self, target: Any) -> None:
        for name, value in vars(self).items():
            setattr(target, name, value)


@dataclass
class WorkerRuntimeBundle:
    runtime_gateway: RuntimeGateway
    chat_llm_runtime: ChatLLMRuntime
    chat_control_graph: ChatControlGraph
    capability_plane: CapabilityPlane
    worker_router: WorkerRouter

    @classmethod
    def build(
        cls,
        *,
        effective_config: dict[str, Any],
        workspace_root: Path,
        runtime_gateway: RuntimeGateway | None = None,
        chat_llm_runtime: ChatLLMRuntime | None = None,
        chat_control_graph: ChatControlGraph | None = None,
        capability_plane: CapabilityPlane | None = None,
        shell_adapter: ShellAdapter | None = None,
        worker_router: WorkerRouter | None = None,
    ) -> "WorkerRuntimeBundle":
        resolved_gateway = runtime_gateway or build_runtime_gateway_from_env()
        gateway_description = resolved_gateway.describe()
        effective_config["runtime_gateway"]["provider"] = gateway_description.get("provider")
        effective_config["runtime_gateway"]["provider_source"] = (
            "runtime_gateway_argument" if runtime_gateway is not None else effective_config["runtime_gateway"]["provider_source"]
        )
        if gateway_description.get("model") is not None:
            effective_config["runtime_gateway"]["openai_model"] = gateway_description.get("model")
            effective_config["runtime_gateway"]["openai_model_source"] = (
                "runtime_gateway_argument"
                if runtime_gateway is not None
                else effective_config["runtime_gateway"]["openai_model_source"]
            )
        if gateway_description.get("reasoning_effort") is not None:
            effective_config["runtime_gateway"]["openai_reasoning_effort"] = gateway_description.get("reasoning_effort")
            effective_config["runtime_gateway"]["openai_reasoning_effort_source"] = (
                "runtime_gateway_argument"
                if runtime_gateway is not None
                else effective_config["runtime_gateway"]["openai_reasoning_effort_source"]
            )
        resolved_capability_plane = capability_plane or CapabilityPlane(workspace_root=workspace_root)
        adapters: list[WorkerAdapter] = [
            shell_adapter or ShellAdapter(),
            CodexAdapter(),
            OpenCodeAdapter(),
            ClaudeArchitectAdapter(),
            MMXMultimodalAdapter(),
            VertexMultimodalAdapter(),
            NoopAdapter(),
        ]
        if is_sessionful_external_agents_enabled():
            adapters.append(OpenCodeSessionAdapter())
        if is_agent_lane_enabled():
            adapters.append(
                LangChainAgentAdapter(
                    mcp_tool_caller=resolved_capability_plane.mcp_source.call_tool,
                )
            )
        return cls(
            runtime_gateway=resolved_gateway,
            chat_llm_runtime=chat_llm_runtime or build_chat_llm_runtime_from_env(),
            chat_control_graph=chat_control_graph or ChatControlGraph(),
            capability_plane=resolved_capability_plane,
            worker_router=worker_router or WorkerRouter(adapters),
        )

    def install_on(self, target: Any) -> None:
        target.runtime_gateway = self.runtime_gateway
        target.chat_llm_runtime = self.chat_llm_runtime
        target.chat_control_graph = self.chat_control_graph
        target.capability_plane = self.capability_plane
        target.worker_router = self.worker_router
