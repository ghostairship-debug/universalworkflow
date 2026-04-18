from __future__ import annotations

from packages.contracts import CapabilityRoute
from packages.worker_adapters.base import WorkerAdapter


class CapabilityRegistry:
    def __init__(self, adapters: list[WorkerAdapter]):
        self._routes: dict[str, list[CapabilityRoute]] = {}
        self._adapters: dict[str, dict[str, WorkerAdapter]] = {}
        for adapter in adapters:
            adapter_name = adapter.normalized_name()
            for capability in adapter.get_capabilities():
                route = CapabilityRoute(
                    capability=str(capability),
                    adapter_name=adapter_name,
                    adapter_class=adapter.__class__.__name__,
                )
                self._routes.setdefault(route.capability, []).append(route)
                self._adapters.setdefault(route.capability, {})[adapter_name] = adapter
        for capability, routes in self._routes.items():
            routes.sort(
                key=lambda route: (
                    self._adapters[capability][route.adapter_name].route_priority,
                    route.adapter_name,
                )
            )

    def capabilities(self) -> list[str]:
        return sorted(self._routes)

    def routes_for(self, capability: str) -> list[CapabilityRoute]:
        return list(self._routes.get(str(capability), []))

    def list_routes(self) -> list[CapabilityRoute]:
        routes: list[CapabilityRoute] = []
        for key in sorted(self._routes):
            routes.extend(self._routes[key])
        return routes

    def describe(self, capability: str, adapter_name: str | None = None) -> CapabilityRoute | None:
        routes = self._routes.get(str(capability), [])
        if not routes:
            return None
        if adapter_name is None:
            return routes[0]
        for route in routes:
            if route.adapter_name == adapter_name:
                return route
        return None

    def adapter_for(self, capability: str, adapter_name: str | None = None) -> WorkerAdapter | None:
        routes = self._routes.get(str(capability), [])
        adapters = self._adapters.get(str(capability), {})
        if not routes:
            return None
        if adapter_name is None:
            return adapters.get(routes[0].adapter_name)
        return adapters.get(adapter_name)
