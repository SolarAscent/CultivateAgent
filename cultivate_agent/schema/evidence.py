"""Provenance primitives.

Every non-trivial extracted value should be *traceable* back to the source text.
This is the single most important guardrail against hallucination and the
`evidence_traceability` benchmark named in the project record.

Design choices (faithful to the record's schema conventions):

* Null / uncertainty codes are kept **inline** as sentinel strings, exactly as
  the record specifies: ``NR`` (not reported), ``NA`` (not applicable),
  ``UNC`` (mentioned but unclear). Inferences use an ``INF:`` prefix on the
  value itself (e.g. ``"INF: likely plant-derived polysaccharide scaffold"``).
* Quantitative values preserve the *original reporting* (number + unit as
  written); normalization is a separate, additive step (see
  ``cultivate_agent.normalize``) that never overwrites the raw value.
* A parallel :class:`Evidence` record can be attached to any field via the
  extraction's ``evidence`` map, keyed by ``"<block>.<field>"``.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class NullCode(str, Enum):
    """Sentinel codes for absent / inapplicable / uncertain values."""

    NR = "NR"    # not reported by the authors
    NA = "NA"    # not applicable to this paper
    UNC = "UNC"  # mentioned but genuinely unclear

    @classmethod
    def is_code(cls, value: object) -> bool:
        return isinstance(value, str) and value.strip() in {c.value for c in cls}


INFERENCE_PREFIX = "INF:"


def is_inference(value: object) -> bool:
    """True if ``value`` is a justified inference rather than an explicit claim."""
    return isinstance(value, str) and value.strip().startswith(INFERENCE_PREFIX)


class Confidence(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Evidence(BaseModel):
    """Where a value came from, so a human (or verifier agent) can check it."""

    quote: str = Field(
        ...,
        description="Verbatim span copied from the source text that supports the value. "
        "Must be an exact substring of the source; do not paraphrase.",
    )
    location: Optional[str] = Field(
        None,
        description="Human-readable locator, e.g. 'Results §2.1', 'Table 2', "
        "'Fig. 3 caption', 'p. 4', or 'SI Table S1'.",
    )
    source: str = Field(
        "fulltext",
        description="Which artifact the quote is from: fulltext | abstract | "
        "table | figure_caption | si | metadata.",
    )
    confidence: Confidence = Confidence.medium
    is_inference: bool = Field(
        False,
        description="True when the value is inferred (INF:) rather than explicitly stated.",
    )

    def verify_against(self, text: str, *, min_len: int = 8) -> bool:
        """Cheap grounding check: is the quote actually present in ``text``?

        Whitespace is collapsed on both sides so line-wrapped PDF text still
        matches. Very short quotes are treated as unverifiable (return False)
        to avoid trivially-matching fragments passing the check.
        """
        q = " ".join((self.quote or "").split())
        if len(q) < min_len:
            return False
        haystack = " ".join((text or "").split())
        return q.lower() in haystack.lower()
