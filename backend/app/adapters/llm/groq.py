"""Groq adapter — the **fallback** ``LLMProvider`` (AD-6).

Same interface as the Gemini adapter; the LLM gateway (AD-10) flips to this
provider when the primary fails. Wraps ``langchain_groq.ChatGroq``; the SDK is
imported lazily inside the model factory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import SecretStr

from app.adapters.llm.base import LangChainLLMProvider

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

_DEFAULT_MODEL = "llama-3.1-8b-instant"


class GroqLLMProvider(LangChainLLMProvider):
    """Groq-hosted Llama (free tier) behind the ``LLMProvider`` port."""

    def __init__(self, api_key: str, *, model: str = _DEFAULT_MODEL) -> None:
        def factory(temperature: float) -> BaseChatModel:
            try:
                from langchain_groq import ChatGroq
            except ImportError as exc:  # pragma: no cover - requires the provider extra
                raise RuntimeError(
                    "langchain-groq is not installed; install the backend "
                    "dependencies (`pip install -e .[dev]`)."
                ) from exc
            return ChatGroq(model=model, api_key=SecretStr(api_key), temperature=temperature)

        super().__init__(factory)
