from __future__ import annotations

from dataclasses import dataclass

from packages.contracts import (
    CapabilityRoute,
    ExecutionLaneType,
    DomainPackResolution,
    Evidence,
    HandoffLite,
    MemoryRetrievalPreview,
    MCPServerProfile,
    Phase,
    PresetDefinition,
    ReviewVerdict,
    ResolvedExecutionProfile,
    Run,
    RunSnapshot,
    RuntimeAttempt,
    RuntimeClaim,
    RuntimeStateRef,
    RuntimeTask,
    TaskCard,
    TaskPacket,
    ToolProjectionManifest,
    WorkerLease,
)
from packages.worker_adapters.base import ExecutionResult


@dataclass(slots=True)
class PreparedRunBundle:
    run: Run
    preset: PresetDefinition
    task_packet: TaskPacket
    state_ref: RuntimeStateRef
    handoff: HandoffLite
    domain_pack: DomainPackResolution | None
    capability_route: CapabilityRoute | None
    memory_preview: MemoryRetrievalPreview | None
    execution_lane: ExecutionLaneType
    resolved_execution: ResolvedExecutionProfile
    tool_projection_manifest: ToolProjectionManifest | None
    mcp_server_profiles: list[MCPServerProfile]


@dataclass(slots=True)
class ExecutedRunBundle:
    run: Run
    execution_result: ExecutionResult
    evidence: Evidence
    review_verdict: ReviewVerdict | None


@dataclass(slots=True)
class ReviewedRunBundle:
    run: Run
    evidence: Evidence
    review_verdict: ReviewVerdict


@dataclass(slots=True)
class RunDiagnosticContext:
    run: Run
    preset: PresetDefinition | None
    phases: list[Phase]
    task_cards: list[TaskCard]
    runtime_tasks: list[RuntimeTask]
    handoffs: list[HandoffLite]
    runtime_state_refs: list[RuntimeStateRef]
    snapshots: list[RunSnapshot]
    runtime_attempts: list[RuntimeAttempt]
    claims: list[RuntimeClaim]
    worker_leases: list[WorkerLease]
    evidence_by_task: dict[str, Evidence | None]
    latest_review_verdict: ReviewVerdict | None
