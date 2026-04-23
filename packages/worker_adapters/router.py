from __future__ import annotations

import os

from packages.contracts import TaskPacket
from packages.core_domain.errors import CapabilityAdapterNotFoundError, UnsupportedTaskKindError
from packages.worker_adapters.base import WorkerAdapter
from packages.worker_adapters.capability_registry import CapabilityRegistry
from packages.worker_adapters.codex_adapter import CodexAdapter
from packages.worker_adapters.noop_adapter import NoopAdapter
from packages.worker_adapters.opencode_adapter import OpenCodeAdapter
from packages.worker_adapters.shell_adapter import ShellAdapter


class WorkerRouter:
    def __init__(self, adapters: list[WorkerAdapter] | None = None):
        self._adapters = adapters or [ShellAdapter(), CodexAdapter(), OpenCodeAdapter(), NoopAdapter()]
        self._registry = CapabilityRegistry(self._adapters)
        self._default_preferences = {
            "noop": "noop",
            "shell_exec": "shell",
        }

    def _env_preference_key(self, capability: str) -> str:
        normalized = capability.upper().replace("-", "_")
        return f"WORKFLOW_{normalized}_ADAPTER"

    def _preferred_adapter_name(self, capability: str, explicit_adapter: str | None = None) -> str | None:
        if explicit_adapter:
            return explicit_adapter
        env_preference = os.getenv(self._env_preference_key(capability))
        if env_preference:
            return env_preference.strip().lower()
        return self._default_preferences.get(capability)

    def capabilities(self) -> list[str]:
        return self._registry.capabilities()

    def routes(self) -> list[dict[str, str]]:
        return [route.model_dump(mode="json") for route in self._registry.list_routes()]

    def describe(self, capability: str, adapter_name: str | None = None) -> dict[str, str] | None:
        route = self._registry.describe(
            capability,
            adapter_name=self._preferred_adapter_name(str(capability), explicit_adapter=adapter_name),
        )
        return route.model_dump(mode="json") if route is not None else None

    def route(self, packet: TaskPacket) -> WorkerAdapter:
        task_kind = str(packet.task_kind)
        preferred_adapter = packet.env.get("WORKFLOW_CAPABILITY_ADAPTER")
        adapter = self._registry.adapter_for(
            task_kind,
            adapter_name=self._preferred_adapter_name(task_kind, explicit_adapter=preferred_adapter),
        )
        if adapter is None:
            if preferred_adapter:
                raise CapabilityAdapterNotFoundError(
                    task_kind,
                    preferred_adapter,
                    [route.adapter_name for route in self._registry.routes_for(task_kind)],
                )
            raise UnsupportedTaskKindError(task_kind, self.capabilities())
        return adapter
