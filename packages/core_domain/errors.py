class WorkflowError(Exception):
    code = "workflow_error"
    status_code = 400

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class PresetRequiredError(WorkflowError):
    code = "preset_required"


class PresetNotFoundError(WorkflowError):
    code = "preset_not_found"
    status_code = 404


class EntityNotFoundError(WorkflowError):
    code = "entity_not_found"
    status_code = 404

    def __init__(self, entity: str, entity_id: str):
        super().__init__(f"{entity} not found: {entity_id}", {"entity": entity, "entity_id": entity_id})


class InvalidStateTransitionError(WorkflowError):
    code = "invalid_state_transition"
    status_code = 409

    def __init__(self, action: str, current_status: str, allowed_statuses: list[str], target_status: str | None = None):
        super().__init__(
            f"cannot {action} when run status is {current_status}",
            {
                "action": action,
                "current_status": current_status,
                "allowed_statuses": allowed_statuses,
                "target_status": target_status,
            },
        )


class UnsupportedTaskKindError(WorkflowError):
    code = "unsupported_task_kind"
    status_code = 422

    def __init__(self, task_kind: str, available_task_kinds: list[str]):
        super().__init__(
            f"unsupported task kind: {task_kind}",
            {"task_kind": task_kind, "available_task_kinds": available_task_kinds},
        )


class CapabilityAdapterNotFoundError(WorkflowError):
    code = "capability_adapter_not_found"
    status_code = 422

    def __init__(self, capability: str, adapter_name: str, available_adapters: list[str]):
        super().__init__(
            f"adapter `{adapter_name}` is not available for capability `{capability}`",
            {
                "capability": capability,
                "adapter_name": adapter_name,
                "available_adapters": available_adapters,
            },
        )


class WorkerAdapterUnavailableError(WorkflowError):
    code = "worker_adapter_unavailable"
    status_code = 503

    def __init__(self, adapter_name: str, reason: str, details: dict | None = None):
        super().__init__(
            f"worker adapter `{adapter_name}` is unavailable: {reason}",
            {"adapter_name": adapter_name, "reason": reason, **(details or {})},
        )


class TaskKindNotAllowedError(WorkflowError):
    code = "task_kind_not_allowed"
    status_code = 409

    def __init__(self, preset_id: str, task_kind: str, allowed_task_kinds: list[str]):
        super().__init__(
            f"task kind `{task_kind}` is not allowed for preset `{preset_id}`",
            {
                "preset_id": preset_id,
                "task_kind": task_kind,
                "allowed_task_kinds": allowed_task_kinds,
            },
        )


class ExecutionLaneNotAllowedError(WorkflowError):
    code = "execution_lane_not_allowed"
    status_code = 409

    def __init__(self, preset_id: str, lane_type: str, allowed_lane_types: list[str]):
        super().__init__(
            f"execution lane `{lane_type}` is not allowed for preset `{preset_id}`",
            {
                "preset_id": preset_id,
                "lane_type": lane_type,
                "allowed_lane_types": allowed_lane_types,
            },
        )


class UnsupportedRepairActionError(WorkflowError):
    code = "unsupported_repair_action"
    status_code = 422

    def __init__(self, action: str, available_actions: list[str]):
        super().__init__(
            f"unsupported repair action: {action}",
            {"action": action, "available_actions": available_actions},
        )


class RepairActionNotAvailableError(WorkflowError):
    code = "repair_action_not_available"
    status_code = 409

    def __init__(self, run_id: str, action: str | None, available_actions: list[str]):
        super().__init__(
            f"repair action is not available for run `{run_id}`",
            {"run_id": run_id, "action": action, "available_actions": available_actions},
        )


class RuntimeClaimConflictError(WorkflowError):
    code = "runtime_claim_conflict"
    status_code = 409

    def __init__(self, runtime_task_id: str, claim_id: str, lease_expires_at: str):
        super().__init__(
            f"runtime task `{runtime_task_id}` already has an active claim",
            {
                "runtime_task_id": runtime_task_id,
                "claim_id": claim_id,
                "lease_expires_at": lease_expires_at,
            },
        )


class ParallelBarrierBrokenError(WorkflowError):
    code = "parallel_barrier_broken"
    status_code = 409

    def __init__(self, barrier_id: str, run_id: str):
        super().__init__(
            f"parallel barrier `{barrier_id}` broke before run `{run_id}` could start execution",
            {"barrier_id": barrier_id, "run_id": run_id},
        )


class BudgetExhaustedError(WorkflowError):
    code = "budget_exhausted"
    status_code = 409

    def __init__(self, run_id: str, remaining_retries: int, max_retries: int):
        super().__init__(
            f"budget exhausted for run `{run_id}`",
            {
                "run_id": run_id,
                "remaining_retries": remaining_retries,
                "max_retries": max_retries,
            },
        )


class RuntimeGatewayConfigurationError(WorkflowError):
    code = "runtime_gateway_configuration_error"
    status_code = 422


class RuntimeGatewayExecutionError(WorkflowError):
    code = "runtime_gateway_execution_error"
    status_code = 502


class DatabaseBusyError(WorkflowError):
    code = "database_busy"
    status_code = 423

    def __init__(self, db_path: str, operation: str, details: dict | None = None):
        super().__init__(
            f"database is busy during `{operation}`: {db_path}",
            {"db_path": db_path, "operation": operation, **(details or {})},
        )
