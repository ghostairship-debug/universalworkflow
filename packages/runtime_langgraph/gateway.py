from __future__ import annotations

from packages.contracts.runtime import RuntimeGateway, RuntimeStateRef


class NullRuntimeGateway(RuntimeGateway):
    def start(self, run_id: str, runtime_task_id: str) -> RuntimeStateRef:
        return RuntimeStateRef(
            run_id=run_id,
            runtime_task_id=runtime_task_id,
            graph_step="compiled",
            state_payload={"entrypoint": "resume"},
        )

    def resume(self, state_ref: RuntimeStateRef) -> RuntimeStateRef:
        return RuntimeStateRef(
            state_ref_id=state_ref.state_ref_id,
            run_id=state_ref.run_id,
            runtime_task_id=state_ref.runtime_task_id,
            graph_step="resuming",
            state_payload={**state_ref.state_payload, "resumed_from": state_ref.graph_step},
            is_terminal=state_ref.is_terminal,
            created_at=state_ref.created_at,
        )
