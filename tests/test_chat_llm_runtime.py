from __future__ import annotations

from types import SimpleNamespace

from packages.runtime_langgraph.chat_control_graph import CHAT_CONTROL_NODES, ChatControlGraph
from packages.runtime_langgraph.chat_runtime import (
    ChatActionDecision,
    DegradedChatLLMRuntime,
    DeepSeekChatLLMRuntime,
    FallbackChatLLMRuntime,
    MiniMaxChatLLMRuntime,
    OpenAIChatLLMRuntime,
    _iter_chat_completion_deltas,
    _minimax_base_url_from_env,
    _strip_reasoning_markup,
    build_chat_llm_runtime_from_env,
    infer_rule_based_chat_action,
)


def test_rule_based_chat_action_understands_chinese_control_words() -> None:
    assert infer_rule_based_chat_action("为当前项目做一个计划预览").action_type == "plan_preview"

    resume_decision = infer_rule_based_chat_action("继续执行下一步")

    assert resume_decision.action_type == "resume_run"
    assert resume_decision.requires_confirmation is True
    assert resume_decision.degraded is True


def test_degraded_chat_runtime_streams_clear_fallback_chunks() -> None:
    runtime = DegradedChatLLMRuntime()
    decision = ChatActionDecision(action_type="summarize_run", degraded=True)

    chunks = list(
        runtime.stream_reply(
            content="总结当前状态",
            context={},
            decision=decision,
            action_result={"summary": "当前没有 active run。"},
        )
    )

    assert "".join(chunks) == "当前没有 active run。"
    assert runtime.describe()["configured"] is False


def test_openai_chat_runtime_uses_streaming_response_deltas() -> None:
    class _FakeResponses:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if kwargs.get("stream"):
                return [
                    SimpleNamespace(type="response.output_text.delta", delta="流式"),
                    SimpleNamespace(type="response.output_text.delta", delta="回复"),
                ]
            return SimpleNamespace(
                output_text='{"action_type":"summarize_run","confidence":0.91,"rationale":"user asked for status"}'
            )

    fake_responses = _FakeResponses()
    fake_client = SimpleNamespace(responses=fake_responses)
    runtime = OpenAIChatLLMRuntime(client=fake_client, model="gpt-test")

    decision = runtime.infer_action("总结一下当前运行", {"active_run_id": "run_123"})
    chunks = list(
        runtime.stream_reply(
            content="总结一下当前运行",
            context={"active_run_id": "run_123"},
            decision=decision,
            action_result={"summary": "运行等待审查。"},
        )
    )

    assert decision.action_type == "summarize_run"
    assert chunks == ["流式", "回复"]
    assert any(call.get("stream") is True for call in fake_responses.calls)


def test_deepseek_chat_runtime_uses_chat_completion_deltas() -> None:
    class _FakeChatCompletions:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if kwargs.get("stream"):
                return [
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="深度"))]),
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="回复"))]),
                ]
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content='{"action_type":"plan_preview","confidence":0.88,"rationale":"user asked for a plan"}'
                        )
                    )
                ]
            )

    fake_completions = _FakeChatCompletions()
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=fake_completions))
    runtime = DeepSeekChatLLMRuntime(client=fake_client, model="deepseek-chat")

    decision = runtime.infer_action("为当前项目做一个计划预览", {"session_id": "intent_session_123"})
    chunks = list(
        runtime.stream_reply(
            content="为当前项目做一个计划预览",
            context={"session_id": "intent_session_123"},
            decision=decision,
            action_result={"summary": "计划已生成。"},
        )
    )

    assert decision.action_type == "plan_preview"
    assert decision.degraded is False
    assert "".join(chunks) == "深度回复"
    assert len(chunks) == 1
    assert any(call.get("stream") is True for call in fake_completions.calls)


def test_minimax_chat_runtime_uses_openai_compatible_chat_completion() -> None:
    class _FakeChatCompletions:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if kwargs.get("stream"):
                return [
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="MiniMax 已"))]),
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="接入。"))]),
                ]
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content='{"action_type":"summarize_run","confidence":0.86,"rationale":"user asked for status"}'
                        )
                    )
                ]
            )

    fake_completions = _FakeChatCompletions()
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=fake_completions))
    runtime = MiniMaxChatLLMRuntime(client=fake_client, model="MiniMax-M2.7")

    decision = runtime.infer_action("总结当前状态", {"active_run_id": "run_123"})
    chunks = list(
        runtime.stream_reply(
            content="总结当前状态",
            context={"active_run_id": "run_123"},
            decision=decision,
            action_result={"summary": "运行等待确认。"},
        )
    )

    assert runtime.describe()["provider"] == "minimax"
    assert decision.action_type == "summarize_run"
    assert "".join(chunks) == "MiniMax 已接入。"
    assert any(call.get("stream") is True for call in fake_completions.calls)


def test_chat_completion_delta_iterator_does_not_duplicate_sdk_events() -> None:
    class _SdkLikeEvent:
        choices = [SimpleNamespace(delta=SimpleNamespace(content="一次"))]

        def model_dump(self, mode="json"):
            return {"choices": [{"delta": {"content": "一次"}}]}

    assert list(_iter_chat_completion_deltas([_SdkLikeEvent()])) == ["一次"]


def test_minimax_chat_runtime_filters_reasoning_markup_from_stream() -> None:
    class _FakeChatCompletions:
        def create(self, **kwargs):
            if kwargs.get("stream"):
                return [
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="<thi"))]),
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="nk>hidden"))]),
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=" reasoning</thi"))]),
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="nk>MiniMax "))]),
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="已接入。"))]),
                ]
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content='{"action_type":"answer_only","confidence":0.8,"rationale":"fallback"}'
                        )
                    )
                ]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeChatCompletions()))
    runtime = MiniMaxChatLLMRuntime(client=fake_client, model="MiniMax-M2.7")
    chunks = list(
        runtime.stream_reply(
            content="你是谁？",
            context={},
            decision=ChatActionDecision(action_type="answer_only"),
        )
    )

    assert "".join(chunks) == "MiniMax 已接入。"


def test_minimax_chat_runtime_filters_dangling_reasoning_close_from_stream() -> None:
    class _FakeChatCompletions:
        def create(self, **kwargs):
            if kwargs.get("stream"):
                return [
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="hidden reasoning"))]),
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="</thi"))]),
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="nk>可见"))]),
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="回答。"))]),
                ]
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=""))])

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeChatCompletions()))
    runtime = MiniMaxChatLLMRuntime(client=fake_client, model="MiniMax-M2.7")

    chunks = list(
        runtime.stream_reply(
            content="你是谁？",
            context={},
            decision=ChatActionDecision(action_type="answer_only"),
        )
    )

    assert "".join(chunks) == "可见回答。"


def test_strip_reasoning_markup_handles_non_streaming_minimax_text() -> None:
    assert _strip_reasoning_markup("<think>hidden</think>可见回答") == "可见回答"
    assert _strip_reasoning_markup("开头<think>hidden</think>结尾") == "开头结尾"
    assert _strip_reasoning_markup("hidden</think>可见回答") == "可见回答"
    assert _strip_reasoning_markup("<think>unfinished") == ""


def test_minimax_base_url_defaults_to_token_plan_endpoint(monkeypatch) -> None:
    monkeypatch.delenv("MINIMAX_BASE_URL", raising=False)
    monkeypatch.delenv("MINIMAX_API_HOST", raising=False)

    assert _minimax_base_url_from_env() == "https://api.minimaxi.com/v1"


def test_chat_runtime_factory_prefers_deepseek_when_key_is_configured(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("WORKFLOW_CHAT_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("WORKFLOW_CHAT_LLM_MODEL", "deepseek-chat")

    runtime = build_chat_llm_runtime_from_env()

    assert runtime.describe()["provider"] == "deepseek"
    assert runtime.describe()["model"] == "deepseek-chat"


def test_chat_runtime_factory_prefers_minimax_in_auto_mode(monkeypatch) -> None:
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-test")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.delenv("WORKFLOW_CHAT_LLM_PROVIDER", raising=False)

    runtime = build_chat_llm_runtime_from_env()

    assert runtime.describe()["provider"] == "minimax"
    assert runtime.describe()["model"] == "MiniMax-M2.7"
    assert runtime.describe()["fallback_provider"] == "deepseek"


def test_fallback_chat_runtime_uses_deepseek_when_minimax_reply_fails() -> None:
    class _FailingRuntime:
        def describe(self):
            return {"provider": "minimax", "model": "MiniMax-M2.7"}

        def infer_action(self, content, context):
            return ChatActionDecision(action_type="answer_only", confidence=0.8)

        def stream_reply(self, **kwargs):
            raise RuntimeError("minimax unavailable")

    fallback = DegradedChatLLMRuntime()
    runtime = FallbackChatLLMRuntime(primary=_FailingRuntime(), fallback=fallback)  # type: ignore[arg-type]
    decision = ChatActionDecision(action_type="answer_only")

    chunks = list(runtime.stream_reply(content="你是谁？", context={}, decision=decision))

    assert chunks
    assert "MiniMax" not in "".join(chunks)


def test_chat_control_graph_projects_expected_nodes() -> None:
    graph = ChatControlGraph()

    state = graph.run(
        session_id="intent_session_graph",
        action_type="plan_preview",
        requires_confirmation=False,
        degraded=False,
    )

    assert state["path"][0] == CHAT_CONTROL_NODES[0]
    assert state["path"][-1] == CHAT_CONTROL_NODES[-1]
    assert state["graph_node"] == CHAT_CONTROL_NODES[-1]
