from __future__ import annotations

from pydantic import BaseModel, Field


class CreateRunRequest(BaseModel):
    goal: str = Field(min_length=1)
    preset_id: str = Field(min_length=1)


class GoalPlanRequest(BaseModel):
    goal: str = Field(min_length=1)
    preset_id: str | None = None


class LaunchGoalRequest(BaseModel):
    goal: str = Field(min_length=1)
    preset_id: str | None = None
    execute: bool = False


class CreateIntentSessionRequest(BaseModel):
    goal: str = Field(min_length=1)
    preferred_preset_id: str | None = None
    preferred_cluster_template_ids: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    referenced_artifact_paths: list[str] = Field(default_factory=list)
    followup_context: list[str] = Field(default_factory=list)


class ClarificationUpdateRequest(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)
    preferred_preset_id: str | None = None
    preferred_cluster_template_ids: list[str] = Field(default_factory=list)


class IntentPlanDraftRequest(BaseModel):
    preferred_preset_id: str | None = None
    preferred_cluster_template_ids: list[str] = Field(default_factory=list)


class IntentLaunchRequest(BaseModel):
    execute: bool = False
    rationale: str | None = None
    selected_preset_id: str | None = None
    selected_cluster_template_ids: list[str] = Field(default_factory=list)


class FollowupRequestPayload(BaseModel):
    instruction: str = Field(min_length=1)
    intent: str = Field(default="continue", min_length=1)
    blocking: bool = False
    run_id: str | None = None


class ChatMessageRequest(BaseModel):
    content: str = Field(min_length=1)
    session_id: str | None = None
    run_id: str | None = None
    mode: str = Field(default="llm_assisted", min_length=1)
    client_message_id: str | None = None


class ChatActionConfirmRequest(BaseModel):
    rationale: str | None = None


class TaskKindOverrideRequest(BaseModel):
    task_kind: str | None = Field(default=None)
    adapter_name: str | None = Field(default=None)
    agent_model: str | None = Field(default=None)
    codex_model: str | None = Field(default=None)
    opencode_model: str | None = Field(default=None)
    opencode_variant: str | None = Field(default=None)
    runtime_gateway_provider: str | None = Field(default=None)
    runtime_gateway_model: str | None = Field(default=None)
    runtime_reasoning_effort: str | None = Field(default=None)
    worker_pool_id: str | None = Field(default=None)
    memory_item_ids: list[str] = Field(default_factory=list)
    task_card_ref: str | None = Field(default=None)
    task_card_path: str | None = Field(default=None)
    write_set: list[str] = Field(default_factory=list)
    read_set: list[str] = Field(default_factory=list)
    test_commands: list[str] = Field(default_factory=list)
    max_fix_iterations: int = Field(default=0, ge=0)
    mutation_mode: str | None = Field(default=None)


class BatchResumeRequest(BaseModel):
    run_ids: list[str] = Field(min_length=1)
    max_workers: int | None = Field(default=None, ge=1)


class ReconcileRunRequest(BaseModel):
    apply: bool = False
    action: str | None = None


class MaterializeMemoryItemRequest(BaseModel):
    candidate_id: str = Field(min_length=1)


class WorkerHeartbeatCallbackRequest(BaseModel):
    callback_id: str = Field(min_length=1)
    dispatch_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    runtime_task_id: str = Field(min_length=1)
    lease_id: str = Field(min_length=1)
    worker_pool_id: str = Field(min_length=1)
    execution_target: dict | None = None
    heartbeat_at: str = Field(min_length=1)
    lease_expires_at: str = Field(min_length=1)


class WorkerCompletionCallbackRequest(BaseModel):
    callback_id: str = Field(min_length=1)
    dispatch_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    runtime_task_id: str = Field(min_length=1)
    lease_id: str = Field(min_length=1)
    worker_pool_id: str = Field(min_length=1)
    execution_target: dict
    lease_renewals: list[dict] = Field(default_factory=list)
    execution_result: dict | None = None


class SchedulerProposalRequest(BaseModel):
    control_plane_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    runtime_task_id: str = Field(min_length=1)
    domain_kind: str = Field(default="runtime_task", min_length=1)
    domain_key: str = Field(min_length=1)
    requested_lease_seconds: int = Field(default=300, ge=1)
    requested_epoch: int = Field(default=1, ge=1)


class SchedulerHeartbeatRequest(BaseModel):
    control_plane_id: str = Field(min_length=1)
    status: str = Field(default="active", min_length=1)
    lease_count: int = Field(default=0, ge=0)
    observed_at: str | None = None


class SchedulerReleaseRequest(BaseModel):
    release_reason: str = Field(default="control_plane_release", min_length=1)
