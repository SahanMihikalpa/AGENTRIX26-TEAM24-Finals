"""``LLMProvider`` port — the reasoning socket (Strategy / Adapter).

Implemented by ``adapters/llm/gemini.py`` (primary) and ``adapters/llm/groq.py``
(fallback). Synchronous by design (see docs/10, Stage 1). Structured output is
generic over the schema type, so the domain never imports Pydantic — concrete
schemas are supplied by the application/agent layer.
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class LLMProvider(Protocol):
    """A swappable large-language-model backend."""

    def complete(
        self, prompt: str, *, system: str | None = None, temperature: float = 0.0
    ) -> str:
        """Return a free-text completion for ``prompt``."""
        ...

    def complete_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        system: str | None = None,
        temperature: float = 0.0,
    ) -> T:
        """Return an instance of ``schema`` populated by the model.

        Implementations use schema-constrained / function-calling generation so
        the result is validated against ``schema`` rather than parsed from prose.
        """
        ...
