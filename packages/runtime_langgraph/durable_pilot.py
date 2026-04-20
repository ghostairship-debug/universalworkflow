from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from packages.core_domain.config import build_effective_config
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
    _SAVERS: dict[str, Any] = {}

    def __init__(self, *, state_dir: str | Path | None = None) -> None:
        try:
            from langgraph.checkpoint.base import empty_checkpoint
            from langgraph.checkpoint.memory import InMemorySaver
        except ImportError as exc:
            raise RuntimeError("langgraph durable pilot requires the langgraph package") from exc
        self._empty_checkpoint = empty_checkpoint
        effective = build_effective_config()
        configured_state_dir = state_dir or effective["durable_pilot"]["state_dir"] or "state/durable"
        self.state_dir = Path(str(configured_state_dir)).resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        saver_key = self.state_dir.as_posix()
        if saver_key not in self._SAVERS:
            self._SAVERS[saver_key] = InMemorySaver()
        self._saver = self._SAVERS[saver_key]

    def describe(self) -> dict[str, Any]:
        return {
            "provider": "langgraph",
            "enabled": True,
            "mode": "functional_pilot",
            "state_dir": self.state_dir.as_posix(),
        }

    def start(self, run_id: str, runtime_task_id: str) -> dict[str, str]:
        thread_id = _new_ref("thread")
        assistant_id = _new_ref("assistant")
        config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        checkpoint = self._empty_checkpoint()
        returned_config = self._saver.put(
            config,
            checkpoint,
            {"source": "start", "run_id": run_id, "runtime_task_id": runtime_task_id, "step": 0},
            {},
        )
        checkpoint_id = returned_config["configurable"]["checkpoint_id"]
        self._write_checkpoint_snapshot(
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            metadata={"source": "start", "run_id": run_id, "runtime_task_id": runtime_task_id, "assistant_id": assistant_id},
        )
        return {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "assistant_id": assistant_id,
        }

    def checkpoint(self, refs: dict[str, str], *, reason: str) -> dict[str, str]:
        config = {"configurable": {"thread_id": refs["thread_id"], "checkpoint_ns": "", "checkpoint_id": refs["checkpoint_id"]}}
        checkpoint_tuple = self._saver.get_tuple(config)
        checkpoint = checkpoint_tuple.checkpoint if checkpoint_tuple is not None else self._empty_checkpoint()
        metadata = {"source": "checkpoint", "reason": reason, "step": 1}
        returned_config = self._saver.put(
            {"configurable": {"thread_id": refs["thread_id"], "checkpoint_ns": ""}},
            checkpoint,
            metadata,
            {},
        )
        checkpoint_id = returned_config["configurable"]["checkpoint_id"]
        self._write_checkpoint_snapshot(
            thread_id=refs["thread_id"],
            checkpoint_id=checkpoint_id,
            metadata={**metadata, "assistant_id": refs.get("assistant_id")},
        )
        return {
            **refs,
            "checkpoint_id": checkpoint_id,
            "checkpoint_reason": reason,
        }

    def review_decision(self, refs: dict[str, str], *, decision: str) -> dict[str, str]:
        updated = self.checkpoint(refs, reason=f"review_{decision}")
        updated["review_decision"] = decision
        return updated

    def _write_checkpoint_snapshot(self, *, thread_id: str, checkpoint_id: str, metadata: dict[str, Any]) -> None:
        path = self.state_dir / f"{thread_id}.json"
        payload: dict[str, Any]
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
        else:
            payload = {"thread_id": thread_id, "checkpoints": []}
        payload["latest_checkpoint_id"] = checkpoint_id
        payload["checkpoints"].append(
            {
                "checkpoint_id": checkpoint_id,
                "recorded_at": datetime.now(UTC).isoformat(),
                "metadata": metadata,
            }
        )
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_durable_runtime_pilot_from_env() -> DurableRuntimePilot:
    if not is_durable_pilot_enabled():
        return NullDurableRuntimePilot()
    effective = build_effective_config()
    provider = str(effective["durable_pilot"]["provider"]).strip().lower()
    if provider in {"", "null", "none"}:
        return NullDurableRuntimePilot()
    if provider == "langgraph":
        return LangGraphDurableRuntimePilot(state_dir=effective["durable_pilot"]["state_dir"])
    return NullDurableRuntimePilot()
