"""Build an :class:`LLMClient` from a provider name + settings."""

from __future__ import annotations

from typing import Any, Optional

from .base import LLMClient, LLMError


def get_client(
    provider: str,
    model: str,
    *,
    temperature: float = 0.0,
    max_tokens: int = 4096,
    max_retries: int = 4,
    timeout_s: int = 120,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    **extra: Any,
) -> LLMClient:
    """Return a ready-to-use client for ``provider``.

    Supported: ``openai`` (and any OpenAI-compatible endpoint via ``base_url``),
    ``anthropic``, ``gemini``, ``mock``.
    """
    common = dict(
        temperature=temperature,
        max_tokens=max_tokens,
        max_retries=max_retries,
        timeout_s=timeout_s,
    )
    provider = (provider or "openai").lower()

    if provider in ("openai", "openai-compatible", "compatible"):
        from .openai_client import OpenAIClient
        return OpenAIClient(model, api_key=api_key, base_url=base_url, **common)
    if provider in ("anthropic", "claude"):
        from .anthropic_client import AnthropicClient
        return AnthropicClient(model, api_key=api_key, **common)
    if provider in ("gemini", "google"):
        from .openai_client import GeminiClient
        return GeminiClient(model, api_key=api_key, base_url=base_url, **common)
    if provider == "mock":
        from .mock_client import MockClient
        return MockClient(model, **common, **extra)

    raise LLMError(f"unknown LLM provider: {provider!r}")
