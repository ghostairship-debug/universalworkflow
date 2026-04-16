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
