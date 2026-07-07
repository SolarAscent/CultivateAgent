"""Anthropic (Claude) client. Optional dependency: `pip install anthropic`."""

from __future__ import annotations

import os
from typing import List, Optional

from .base import LLMClient, LLMError, LLMResponse, Message


class AnthropicClient(LLMClient):
    def __init__(self, model: str, *, api_key: Optional[str] = None, **kwargs):
        super().__init__(model, **kwargs)
        try:
            import anthropic  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise LLMError("anthropic package not installed. `pip install anthropic`") from e
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMError("ANTHROPIC_API_KEY not set (put it in .env)")
        self._client = anthropic.Anthropic(api_key=api_key, timeout=self.timeout_s)

    def _raw_complete(self, messages: List[Message], **kwargs) -> LLMResponse:
        # Anthropic keeps the system prompt as a separate top-level arg.
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        turns = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]
        resp = self._client.messages.create(
            model=self.model,
            system=system or None,
            messages=turns,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        text = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
        usage = {}
        if getattr(resp, "usage", None):
            usage = {
                "prompt_tokens": getattr(resp.usage, "input_tokens", 0),
                "completion_tokens": getattr(resp.usage, "output_tokens", 0),
            }
        return LLMResponse(text=text, model=self.model, usage=usage, raw=resp)
