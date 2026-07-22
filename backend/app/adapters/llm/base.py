"""LangChain-backed implementation of the ``LLMProvider`` port (shared base).

Both concrete providers — Gemini (primary) and Groq (fallback) — are thin
wrappers over a LangChain ``BaseChatModel``, so the prompt→messages→invoke logic
and the structured-output path are written **once** here. Concrete adapters
(:mod:`app.adapters.llm.gemini` / :mod:`app.adapters.llm.groq`) supply a
*factory* that builds the chat model for a given temperature.

Design notes:

* **Lazy + import-free hot path.** Messages are passed to LangChain as
  ``(role, content)`` tuples — a valid ``LanguageModelInput`` — so this module
  never imports LangChain at runtime. The heavy provider SDK is imported lazily
  inside each concrete factory (mirrors the bge adapter, AD-4).
* **Per-call temperature (honoring the port).** LangChain bakes ``temperature``
  in at model construction, so we build and memoize one model per distinct
  temperature value. Most agent calls use ``0.0`` (deterministic), so this is a
  single cached model in practice.
* **Structured output stays out of the domain.** ``complete_structured`` is
  generic over the schema type and delegates to ``with_structured_output``;
  concrete Pydantic schemas live in the application/agent layer.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar, cast

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

T = TypeVar("T")

#: Builds a chat model configured for a given sampling temperature.
ModelFactory = Callable[[float], "BaseChatModel"]


class LangChainLLMProvider:
    """Adapts any LangChain chat model to the synchronous ``LLMProvider`` port."""

    def __init__(self, model_factory: ModelFactory) -> None:
        self._model_factory = model_factory
        self._models: dict[float, BaseChatModel] = {}

    def _model(self, temperature: float) -> BaseChatModel:
        """Return the chat model for ``temperature`` (built + cached on first use)."""
        model = self._models.get(temperature)
        if model is None:
            model = self._model_factory(temperature)
            self._models[temperature] = model
        return model

    def complete(
        self, prompt: str, *, system: str | None = None, temperature: float = 0.0
    ) -> str:
        response = self._model(temperature).invoke(_build_messages(prompt, system))
        return _content_to_text(response.content)

    def complete_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        system: str | None = None,
        temperature: float = 0.0,
    ) -> T:
        structured = self._model(temperature).with_structured_output(schema)
        return cast(T, structured.invoke(_build_messages(prompt, system)))


def _build_messages(prompt: str, system: str | None) -> list[tuple[str, str]]:
    """Render the prompt as LangChain ``(role, content)`` message tuples."""
    messages: list[tuple[str, str]] = []
    if system:
        messages.append(("system", system))
    messages.append(("human", prompt))
    return messages


def _content_to_text(content: object) -> str:
    """Normalize a chat-message ``content`` (str, or multimodal parts) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return str(content)
