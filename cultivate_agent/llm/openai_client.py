"""OpenAI / OpenAI-compatible client (GPT-5.x, proxies, local gateways).

Uses the openai>=1.x SDK. Newer models differ in accepted params (e.g.
``max_completion_tokens`` instead of ``max_tokens``, or a fixed temperature);
this wrapper retries with adapted params instead of failing.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .base import LLMClient, LLMError, LLMResponse, Message


class OpenAIClient(LLMClient):
    def __init__(
        self,
        model: str,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(model, **kwargs)
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise LLMError("openai package not installed. `pip install openai`") from e

        api_key = api_key or os.getenv("OPENAI_API_KEY")
        base_url = base_url or os.getenv("OPENAI_BASE_URL")
        if not api_key:
            raise LLMError("OPENAI_API_KEY not set (put it in .env)")
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=self.timeout_s)
        self.extra_body = extra_body or {}

    def _raw_complete(self, messages: List[Message], **kwargs) -> LLMResponse:
        payload = [{"role": m.role, "content": m.content} for m in messages]
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)

        def _call(params: dict):
            return self._client.chat.completions.create(model=self.model, messages=payload, **params)

        params = {"temperature": temperature, "max_tokens": max_tokens}
        if self.extra_body:
            params["extra_body"] = self.extra_body
        try:
            resp = _call(params)
        except Exception as e:  # adapt to newer-model param constraints
            msg = str(e).lower()
            if "max_tokens" in msg and "max_completion_tokens" in msg:
                params.pop("max_tokens", None)
                params["max_completion_tokens"] = max_tokens
                resp = _call(params)
            elif "temperature" in msg and ("unsupported" in msg or "does not support" in msg or "only the default" in msg):
                params.pop("temperature", None)
                resp = _call(params)
            else:
                raise

        choice = resp.choices[0].message.content or ""
        usage = {}
        if getattr(resp, "usage", None):
            usage = {
                "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(resp.usage, "completion_tokens", 0),
                "total_tokens": getattr(resp.usage, "total_tokens", 0),
            }
        return LLMResponse(text=choice, model=self.model, usage=usage, raw=resp)


class GeminiClient(LLMClient):
    """Gemini via its OpenAI-compatibility endpoint (keeps one code path).

    Google exposes an OpenAI-compatible surface at
    ``https://generativelanguage.googleapis.com/v1beta/openai/``; we reuse the
    OpenAI SDK against it so provider switching stays a config change.
    """

    _DEFAULT_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"

    def __init__(
        self,
        model: str,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(model, **kwargs)
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise LLMError("openai package not installed. `pip install openai`") from e
        api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise LLMError("GEMINI_API_KEY not set (put it in .env)")
        self._client = OpenAI(api_key=api_key, base_url=base_url or self._DEFAULT_BASE, timeout=self.timeout_s)
        self.extra_body = extra_body or {}

    def _raw_complete(self, messages: List[Message], **kwargs) -> LLMResponse:
        payload = [{"role": m.role, "content": m.content} for m in messages]
        params = {
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }
        if self.extra_body:
            params["extra_body"] = self.extra_body
        resp = self._client.chat.completions.create(model=self.model, messages=payload, **params)
        text = resp.choices[0].message.content or ""
        return LLMResponse(text=text, model=self.model, raw=resp)
