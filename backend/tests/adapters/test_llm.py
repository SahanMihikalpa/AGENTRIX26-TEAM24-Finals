"""Unit tests for the LangChain LLM provider wrapper.

The wrapper is exercised with a *fake* chat model injected via the factory, so no
real provider, SDK, or API key is needed — only the prompt→messages→invoke and
structured-output logic is under test.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.adapters.llm.base import LangChainLLMProvider
from app.domain.ports.llm import LLMProvider


@dataclass
class _Intent:
    service: str
    confidence: float


class _FakeResponse:
    def __init__(self, content: Any) -> None:
        self.content = content


class _FakeStructuredRunnable:
    def __init__(self, value: Any) -> None:
        self._value = value

    def invoke(self, messages: Any) -> Any:
        return self._value


class _FakeChatModel:
    def __init__(self, *, content: Any = "", structured: Any = None) -> None:
        self._content = content
        self._structured = structured
        self.invocations: list[Any] = []
        self.structured_schema: Any = None

    def invoke(self, messages: Any) -> _FakeResponse:
        self.invocations.append(messages)
        return _FakeResponse(self._content)

    def with_structured_output(self, schema: Any) -> _FakeStructuredRunnable:
        self.structured_schema = schema
        return _FakeStructuredRunnable(self._structured)


def test_provider_satisfies_port() -> None:
    provider = LangChainLLMProvider(lambda _t: _FakeChatModel())
    assert isinstance(provider, LLMProvider)


def test_complete_returns_text_and_builds_system_and_human_messages() -> None:
    model = _FakeChatModel(content="Renew at the DS office.")
    provider = LangChainLLMProvider(lambda _t: model)

    answer = provider.complete("How do I renew my NIC?", system="Be concise.")

    assert answer == "Renew at the DS office."
    assert model.invocations[0] == [
        ("system", "Be concise."),
        ("human", "How do I renew my NIC?"),
    ]


def test_complete_without_system_omits_the_system_message() -> None:
    model = _FakeChatModel(content="ok")
    LangChainLLMProvider(lambda _t: model).complete("hello")
    assert model.invocations[0] == [("human", "hello")]


def test_complete_joins_multimodal_content_parts() -> None:
    model = _FakeChatModel(content=[{"type": "text", "text": "Hello "}, "world", {"x": 1}])
    answer = LangChainLLMProvider(lambda _t: model).complete("q")
    assert answer == "Hello world"


def test_complete_structured_returns_the_schema_instance() -> None:
    intent = _Intent(service="nic_renewal", confidence=0.9)
    model = _FakeChatModel(structured=intent)
    provider = LangChainLLMProvider(lambda _t: model)

    result = provider.complete_structured("classify this", _Intent)

    assert result is intent
    assert model.structured_schema is _Intent


def test_models_are_built_once_per_temperature() -> None:
    built: list[float] = []

    def factory(temperature: float) -> _FakeChatModel:
        built.append(temperature)
        return _FakeChatModel(content="x")

    provider = LangChainLLMProvider(factory)
    provider.complete("a")
    provider.complete("b")  # same temperature → cached, not rebuilt
    provider.complete("c", temperature=0.7)

    assert built == [0.0, 0.7]
