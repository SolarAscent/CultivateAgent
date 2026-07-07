"""Deterministic mock client.

Lets the entire pipeline run offline (no API key, no cost) for smoke tests,
CI, and development. Configure ``responses`` with a queue of canned strings, or
pass a ``handler`` callable ``(messages) -> str`` for smarter fakes.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from .base import LLMClient, LLMResponse, Message


class MockClient(LLMClient):
    def __init__(
        self,
        model: str = "mock",
        *,
        responses: Optional[List[str]] = None,
        handler: Optional[Callable[[List[Message]], str]] = None,
        default: str = "{}",
        **kwargs,
    ):
        super().__init__(model, **kwargs)
        self._responses = list(responses or [])
        self._handler = handler
        self._default = default
        self.calls: List[List[Message]] = []

    def _raw_complete(self, messages: List[Message], **kwargs) -> LLMResponse:
        self.calls.append(messages)
        if self._handler is not None:
            text = self._handler(messages)
        elif self._responses:
            text = self._responses.pop(0)
        else:
            text = self._default
        return LLMResponse(text=text, model=self.model, usage={"total_tokens": 0})
