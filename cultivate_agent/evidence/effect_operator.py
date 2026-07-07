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

from typing import List, Optional

from ..llm.base import LLMClient, LLMError, extract_json
from ..schema.evidence import Evidence
from ..schema.paper import PaperRef
from .meta_analysis import EvidenceItem

_SYSTEM = (
    "You extract DIRECTIONAL EVIDENCE about how culture-medium components affect a "
    "specific outcome, from a cultivated-meat paper. Report only relationships the "
    "text actually supports, each with a verbatim quote. Do NOT infer an effect from "
    "the mere presence of a component. If the paper does not state a direction, use 0 "
    "(neutral/unclear). Output STRICT JSON only."
)


def _prompt(ref: PaperRef, outcome: str, text: str) -> str:
    return f"""PAPER: {ref.title or ref.paper_id}
OUTCOME OF INTEREST: {outcome}

For each medium component the paper gives evidence about, report its effect on
{outcome}: +1 = increases/beneficial, -1 = decreases/detrimental, 0 = no or
unclear effect. Include a standardized `effect` number and `variance` ONLY if the
paper reports enough to compute them (otherwise omit). Include experimental
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
'''{text[:16000]}'''

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
) -> List[EvidenceItem]:
    """Extract directional :class:`EvidenceItem`s for ``outcome`` from one paper."""
    if not text or not text.strip():
        return []
    try:
        raw = client.chat(_SYSTEM, _prompt(ref, outcome, text))
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
