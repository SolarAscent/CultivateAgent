"""Provider-agnostic LLM interface.

Everything downstream (triage, extraction, normalization, design) talks to this
interface, never to a vendor SDK directly. Swapping ``provider`` in the config
is enough to re-run the whole pipeline on GPT-5.x, Claude, or Gemini -- the
model-comparison experiment described in the project record.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    text: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    raw: Any = None
    latency_s: float = 0.0


class LLMError(RuntimeError):
    pass


_NON_RETRYABLE_STATUS_CODES = {400, 401, 402, 403, 404, 422}
_NON_RETRYABLE_PATTERNS = (
    "authentication",
    "invalid api key",
    "invalid_api_key",
    "insufficient balance",
    "insufficient_quota",
    "permission denied",
    "invalid parameter",
    "invalid request",
    "model not found",
)
_SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_-]+|AQ\.[A-Za-z0-9_-]+)")
_API_KEY_MSG_RE = re.compile(r"(api key\s*:?)\s*[^\s,'}]+", re.IGNORECASE)


def _status_code(exc: Exception) -> Optional[int]:
    code = getattr(exc, "status_code", None)
    if isinstance(code, int):
        return code
    response = getattr(exc, "response", None)
    code = getattr(response, "status_code", None)
    return code if isinstance(code, int) else None


def is_non_retryable_error(exc: Exception) -> bool:
    """Return true for provider errors that should fail fast, not back off."""
    code = _status_code(exc)
    if code in _NON_RETRYABLE_STATUS_CODES:
        return True
    msg = str(exc).lower()
    return any(pattern in msg for pattern in _NON_RETRYABLE_PATTERNS)


def safe_error_message(exc: Exception) -> str:
    """Scrub likely API-key material before errors enter metadata or logs."""
    msg = str(exc)
    msg = _SECRET_RE.sub("[REDACTED_KEY]", msg)
    msg = _API_KEY_MSG_RE.sub(r"\1 [REDACTED_KEY]", msg)
    return msg


# --------------------------------------------------------------------------- #
# JSON extraction helpers (LLMs love wrapping JSON in prose / code fences).    #
# --------------------------------------------------------------------------- #
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> Any:
    """Best-effort parse of the first JSON object/array embedded in ``text``.

    Handles: raw JSON, ```json fenced blocks, and JSON preceded/followed by
    prose. Raises :class:`LLMError` if nothing parseable is found.
    """
    if text is None:
        raise LLMError("empty LLM response")
    candidates: List[str] = []
    for m in _FENCE_RE.finditer(text):
        candidates.append(m.group(1).strip())
    candidates.append(text.strip())
    # Also try the substring from the first bracket to its matching last bracket.
    for opener, closer in (("{", "}"), ("[", "]")):
        i, j = text.find(opener), text.rfind(closer)
        if 0 <= i < j:
            candidates.append(text[i : j + 1])

    for cand in candidates:
        try:
            return json.loads(cand)
        except (json.JSONDecodeError, TypeError):
            continue
    raise LLMError(f"no valid JSON found in response: {text[:200]!r}...")


class LLMClient:
    """Base class with retry/backoff and JSON convenience methods.

    Subclasses implement :meth:`_raw_complete`.
    """

    def __init__(
        self,
        model: str,
        *,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        max_retries: int = 4,
        timeout_s: int = 120,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.timeout_s = timeout_s

    # -- to implement in subclasses --
    def _raw_complete(self, messages: List[Message], **kwargs) -> LLMResponse:  # pragma: no cover
        raise NotImplementedError

    # -- public API --
    def complete(self, messages: List[Message], **kwargs) -> LLMResponse:
        """Call the model with exponential backoff on transient errors."""
        delay = 2.0
        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries):
            t0 = time.perf_counter()
            try:
                resp = self._raw_complete(messages, **kwargs)
                resp.latency_s = time.perf_counter() - t0
                return resp
            except Exception as e:  # noqa: BLE001 - provider SDKs raise varied types
                last_err = e
                if is_non_retryable_error(e):
                    raise LLMError(f"Non-retryable LLM call failed: {safe_error_message(e)}") from e
                if attempt == self.max_retries - 1:
                    break
                time.sleep(delay)
                delay *= 2
        safe = safe_error_message(last_err) if last_err else "unknown error"
        raise LLMError(f"LLM call failed after {self.max_retries} attempts: {safe}") from last_err

    def chat(self, system: str, user: str, **kwargs) -> str:
        """Convenience: system+user -> assistant text."""
        msgs = [Message("system", system), Message("user", user)]
        return self.complete(msgs, **kwargs).text

    def complete_json(self, system: str, user: str, **kwargs) -> Any:
        """system+user -> parsed JSON (robust to fences/prose)."""
        text = self.chat(system, user, **kwargs)
        return extract_json(text)
