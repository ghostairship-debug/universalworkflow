from __future__ import annotations

from typing import Any


CHAT_CONTROL_NODES = [
    "user_input",
    "llm_intent",
    "plan_or_answer",
    "action_proposal",
    "confirmation_gate",
    "workflow_action",
    "monitor",
    "final_summary",
]


class ChatControlGraph:
    def __init__(self) -> None:
        self.provider = "linear"
        self._compiled_graph = None
        try:
            from langgraph.graph import END, START, StateGraph

            def _node(name: str):
                def _inner(state: dict[str, Any]) -> dict[str, Any]:
                    path = list(state.get("path", []))
                    path.append(name)
                    return {**state, "graph_node": name, "path": path}

                return _inner

            builder = StateGraph(dict)
            for node_name in CHAT_CONTROL_NODES:
                builder.add_node(node_name, _node(node_name))
            builder.add_edge(START, CHAT_CONTROL_NODES[0])
            for current, next_node in zip(CHAT_CONTROL_NODES, CHAT_CONTROL_NODES[1:]):
                builder.add_edge(current, next_node)
            builder.add_edge(CHAT_CONTROL_NODES[-1], END)
            self._compiled_graph = builder.compile()
            self.provider = "langgraph"
        except Exception:
            self._compiled_graph = None

    def describe(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "nodes": CHAT_CONTROL_NODES,
        }

    def run(self, *, session_id: str, action_type: str, requires_confirmation: bool, degraded: bool) -> dict[str, Any]:
        state = {
            "session_id": session_id,
            "action_type": action_type,
            "requires_confirmation": requires_confirmation,
            "degraded": degraded,
            "path": [],
        }
        if self._compiled_graph is not None:
            return self._compiled_graph.invoke(state)
        return {**state, "graph_node": CHAT_CONTROL_NODES[-1], "path": list(CHAT_CONTROL_NODES)}
