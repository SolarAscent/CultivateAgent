"""Effect-extraction operator: turn paper text into quoted directional evidence.

This is the honest data source for :mod:`cultivate_agent.evidence.meta_analysis`.
It asks the LLM, for one outcome (e.g. proliferation), which medium components the
paper provides *directional* evidence about, each with a verbatim quote and the
experimental context. It never infers an effect from mere co-occurrence.

Each returned :class:`EvidenceItem` carries:
* direction (+1 beneficial / -1 detrimental / 0 neutral),
* an optional standardized effect + variance when the paper reports them,
* context covariates (species, cell type, stage) for heterogeneity modeling,
* a verbatim quote, verified against the source.
"""

from __future__ import annotations

import math
import re
from typing import List, Optional

from ..llm.base import LLMClient, LLMError, extract_json
from ..schema.evidence import Evidence
from ..schema.paper import PaperRef
from ..schema.structured_paper import structured_paper_from_text
from .meta_analysis import EvidenceItem

# Sections where component->outcome effects are reported. A naive text[:N] prefix
# misses these in long reviews (found during the live DeepSeek run), so we route.
_EFFECT_SECTION_HINTS = [
    "results", "discussion", "methods", "materials and methods",
    "media", "medium", "cell culture", "growth", "proliferation", "expansion",
]

_SYSTEM = (
    "You extract DIRECTIONAL EVIDENCE about how culture-medium components affect a "
    "specific outcome, from a cultivated-meat paper. Report only relationships the "
    "text actually supports, each with a verbatim quote. Do NOT infer an effect from "
    "the mere presence of a component. If the paper does not state a direction, use 0 "
    "(neutral/unclear). Output STRICT JSON only."
)


def _route_effect_context(text: str, paper_id: str, title: Optional[str], max_chars: int) -> str:
    """Concatenate effect-bearing sections (results/methods/media...) up to a budget.

    Falls back to the leading text if no sections match, so short inputs still work.
    """
    if len(text) <= max_chars:
        return text
    paper = structured_paper_from_text(paper_id, text, title=title)
    passages = paper.section_passages(_EFFECT_SECTION_HINTS)
    if not passages:
        return text[:max_chars]
    out, used = [], 0
    if paper.abstract:
        chunk = "Abstract\n" + paper.abstract
        out.append(chunk[: max_chars // 4]); used += len(out[-1])
    for _sid, passage in passages:
        if used >= max_chars:
            break
        chunk = passage[: max_chars - used]
        out.append(chunk); used += len(chunk)
    return "\n\n".join(out)


def _prompt(ref: PaperRef, outcome: str, text: str) -> str:
    return f"""PAPER: {ref.title or ref.paper_id}
OUTCOME OF INTEREST: {outcome}

For each medium component the paper gives evidence about, report its effect on
{outcome}: +1 = increases/beneficial, -1 = decreases/detrimental, 0 = no or
unclear effect. Include an `effect` number and `variance` ONLY if the quoted
span contains the exact reported number needed to support that field; otherwise
omit it. Do not compute transformed effect sizes yourself. Include experimental
context. Every item needs a verbatim `quote` from the text.

Return STRICT JSON:
{{
  "evidence": [
    {{"component": "<name>", "direction": 1, "effect": null, "variance": null,
      "context": {{"species": "<or omit>", "cell_type": "<or omit>", "stage": "<or omit>"}},
      "quote": "<verbatim span>"}}
  ]
}}

TEXT:
'''{text}'''

REMINDER: only text-supported directional claims; verbatim quotes; strict JSON.
"""


def extract_effects(
    client: LLMClient,
    ref: PaperRef,
    text: str,
    outcome: str,
    *,
    normalizer=None,
    verify_evidence: bool = True,
    max_context_chars: int = 28000,
) -> List[EvidenceItem]:
    """Extract directional :class:`EvidenceItem`s for ``outcome`` from one paper."""
    if not text or not text.strip():
        return []
    routed = _route_effect_context(text, ref.paper_id, ref.title, max_context_chars)
    try:
        raw = client.chat(_SYSTEM, _prompt(ref, outcome, routed))
        payload = extract_json(raw)
    except LLMError:
        return []
    if not isinstance(payload, dict):
        return []

    items: List[EvidenceItem] = []
    for e in payload.get("evidence", []) or []:
        if not isinstance(e, dict):
            continue
        component = str(e.get("component", "")).strip()
        quote = str(e.get("quote", "")).strip()
        if not component:
            continue
        if verify_evidence and quote and not Evidence(quote=quote).verify_against(text):
            # Ungrounded claim -> drop (stricter than the schema extractor: an
            # unverifiable effect must not enter the meta-analysis).
            continue
        if normalizer is not None:
            component = normalizer.canonicalize(component).canonical

        direction = e.get("direction")
        try:
            direction = int(direction) if direction is not None else None
        except (TypeError, ValueError):
            direction = None
        effect = _to_float(e.get("effect"))
        variance = _to_float(e.get("variance"))
        if quote:
            inferred_effect = _infer_log_response_ratio(quote, direction)
            if effect is not None and not _number_supported_by_quote(effect, quote):
                effect = None
            if variance is not None and not _number_supported_by_quote(variance, quote):
                variance = None
            if inferred_effect is not None:
                effect = inferred_effect
                variance = None
        else:
            effect = None
            variance = None
        context = {k: str(v) for k, v in (e.get("context") or {}).items() if v}

        items.append(EvidenceItem(
            component=component, outcome=outcome, paper_id=ref.paper_id,
            effect=effect, variance=variance, direction=direction,
            context=context, quote=quote,
        ))
    return items


def _to_float(x) -> Optional[float]:
    try:
        return float(x) if x is not None else None
    except (TypeError, ValueError):
        return None


_NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


def _number_supported_by_quote(value: float, quote: str) -> bool:
    """Return True only when ``quote`` contains a numerically matching token.

    This is deliberately conservative. If an LLM computes a transformed effect
    (for example log fold-change) without the resulting number appearing in the
    quote, the item stays direction-only until a deterministic numeric extractor
    or human reviewer verifies the calculation.
    """
    for match in _NUMBER_RE.finditer(quote):
        token = match.group(0)
        try:
            observed = float(token)
        except ValueError:
            continue
        tol = max(1e-9, abs(value) * 1e-6)
        if abs(observed - value) <= tol:
            return True
    return False


_POSITIVE_WORDS = (
    "increase", "increased", "increases", "increasing", "improve", "improved",
    "improves", "enhance", "enhanced", "enhances", "higher", "greater", "more",
)
_NEGATIVE_WORDS = (
    "decrease", "decreased", "decreases", "decreasing", "reduce", "reduced",
    "reduces", "reduction", "lower", "less", "suppress", "suppressed",
    "inhibit", "inhibited", "decline", "declined",
)
_FOLD_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?:-| )?(?:fold|x|\u00d7)\b",
    flags=re.IGNORECASE,
)
_PERCENT_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*%\s*(?:change|increase|decrease|reduction|improvement|higher|lower|more|less)?",
    flags=re.IGNORECASE,
)


def _infer_log_response_ratio(quote: str, direction: Optional[int]) -> Optional[float]:
    """Infer ln(response ratio) from explicit fold/percent-change phrasing.

    The parser only handles directly reported proportional changes in the quote.
    It does not compute from raw treatment/control means and never infers a
    variance. This creates tier-2 evidence at most.
    """
    fold = _infer_fold_ratio(quote, direction)
    if fold is not None and fold > 0:
        return math.log(fold)
    percent = _infer_percent_ratio(quote, direction)
    if percent is not None and percent > 0:
        return math.log(percent)
    return None


def _infer_fold_ratio(quote: str, direction: Optional[int]) -> Optional[float]:
    for match in _FOLD_RE.finditer(quote):
        fold = _safe_positive_float(match.group("value"))
        if fold is None or fold <= 0:
            continue
        polarity = _local_polarity(quote, match.start(), match.end(), direction)
        if polarity > 0:
            return fold
        if polarity < 0:
            return 1.0 / fold
    return None


def _infer_percent_ratio(quote: str, direction: Optional[int]) -> Optional[float]:
    for match in _PERCENT_RE.finditer(quote):
        pct = _safe_positive_float(match.group("value"))
        if pct is None:
            continue
        polarity = _local_polarity(quote, match.start(), match.end(), direction)
        if polarity > 0:
            return 1.0 + pct / 100.0
        if polarity < 0 and pct < 100.0:
            return 1.0 - pct / 100.0
    return None


def _local_polarity(quote: str, start: int, end: int, direction: Optional[int]) -> int:
    window = quote[max(0, start - 48): min(len(quote), end + 48)].lower()
    has_pos = any(word in window for word in _POSITIVE_WORDS)
    has_neg = any(word in window for word in _NEGATIVE_WORDS)
    if has_pos and not has_neg:
        return 1
    if has_neg and not has_pos:
        return -1
    if direction is not None:
        return int(math.copysign(1, direction)) if direction != 0 else 0
    return 0


def _safe_positive_float(value: str) -> Optional[float]:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out > 0 else None
