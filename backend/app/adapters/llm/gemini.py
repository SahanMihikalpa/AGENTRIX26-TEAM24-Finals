"""Gemini Flash adapter — the **primary** ``LLMProvider`` (AD-6).

Wraps ``langchain_google_genai.ChatGoogleGenerativeAI``. The provider SDK is
imported lazily inside the model factory, so importing this module never requires
the package or a key — construction fails loudly only on first real use.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import SecretStr

from app.adapters.llm.base import LangChainLLMProvider

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

_DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiLLMProvider(LangChainLLMProvider):
    """Google Gemini Flash (free tier) behind the ``LLMProvider`` port."""

    def __init__(self, api_key: str, *, model: str = _DEFAULT_MODEL) -> None:
        def factory(temperature: float) -> BaseChatModel:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
            except ImportError as exc:  # pragma: no cover - requires the provider extra
                raise RuntimeError(
                    "langchain-google-genai is not installed; install the backend "
                    "dependencies (`pip install -e .[dev]`)."
                ) from exc
            return ChatGoogleGenerativeAI(
                model=model, google_api_key=SecretStr(api_key), temperature=temperature
            )

        super().__init__(factory)
