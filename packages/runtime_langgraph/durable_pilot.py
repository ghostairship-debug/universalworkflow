from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any
from uuid import uuid4

from packages.core_domain.m8_flags import is_durable_pilot_enabled


def _new_ref(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class DurableRuntimePilot(ABC):
    @abstractmethod
    def describe(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def start(self, run_id: str, runtime_task_id: str) -> dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    def checkpoint(self, refs: dict[str, str], *, reason: str) -> dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    def review_decision(self, refs: dict[str, str], *, decision: str) -> dict[str, str]:
        raise NotImplementedError


class NullDurableRuntimePilot(DurableRuntimePilot):
    def describe(self) -> dict[str, Any]:
        return {"provider": "null", "enabled": False}

    def start(self, run_id: str, runtime_task_id: str) -> dict[str, str]:
        return {}

    def checkpoint(self, refs: dict[str, str], *, reason: str) -> dict[str, str]:
        return dict(refs)

    def review_decision(self, refs: dict[str, str], *, decision: str) -> dict[str, str]:
        return dict(refs)


class LangGraphDurableRuntimePilot(DurableRuntimePilot):
    def __init__(self) -> None:
        try:
            import langgraph  # noqa: F401
        except ImportError as exc:
            raise RuntimeError("langgraph durable pilot requires the langgraph package") from exc

    def describe(self) -> dict[str, Any]:
        return {"provider": "langgraph", "enabled": True, "mode": "functional_pilot"}

    def start(self, run_id: str, runtime_task_id: str) -> dict[str, str]:
        return {
            "thread_id": _new_ref("thread"),
            "checkpoint_id": _new_ref("checkpoint"),
            "assistant_id": _new_ref("assistant"),
        }

    def checkpoint(self, refs: dict[str, str], *, reason: str) -> dict[str, str]:
        return {
            **refs,
            "checkpoint_id": _new_ref("checkpoint"),
            "checkpoint_reason": reason,
        }

    def review_decision(self, refs: dict[str, str], *, decision: str) -> dict[str, str]:
        return {
            **refs,
            "checkpoint_id": _new_ref("checkpoint"),
            "review_decision": decision,
        }


def build_durable_runtime_pilot_from_env() -> DurableRuntimePilot:
    if not is_durable_pilot_enabled():
        return NullDurableRuntimePilot()
    provider = os.getenv("UAWO_DURABLE_PILOT_PROVIDER", "langgraph").strip().lower()
    if provider in {"", "null", "none"}:
        return NullDurableRuntimePilot()
    if provider == "langgraph":
        return LangGraphDurableRuntimePilot()
    return NullDurableRuntimePilot()
