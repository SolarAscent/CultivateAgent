"""A/B/C relevance triage.

The project record flagged that the first-pass A/B/C classification (done ad hoc
with a general assistant) was unreliable -- some Category-A papers did not meet
the criteria on manual review. This module makes triage:

* **defined** -- the exact tier definitions live in the prompt,
* **evidence-backed** -- each decision carries a supporting quote,
* **reproducible** -- ``temperature=0`` and a fixed prompt,
* **auditable** -- results are dataclasses you can dump to CSV for spot checks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from ..llm.base import LLMClient, LLMError
from ..schema.extraction import normalize_controlled
from ..schema.paper import PaperRef
from ..extract.prompts import SYSTEM_TRIAGE, build_triage_prompt


@dataclass
class TriageResult:
    paper_id: str
    triage_category: Optional[str]        # "A" | "B" | "C"
    rationale: str = ""
    evidence_quote: str = ""
    main_track: Optional[str] = None
    target_product_type: Optional[str] = None
    is_core_for_modeling: Optional[str] = None
    error: Optional[str] = None

    def as_row(self) -> dict:
        return asdict(self)


def classify_paper(client: LLMClient, ref: PaperRef, text: str) -> TriageResult:
    """Assign an A/B/C tier to one paper with an evidence quote."""
    prompt = build_triage_prompt(ref, text or "")
    try:
        data = client.complete_json(SYSTEM_TRIAGE, prompt)
    except LLMError as e:
        return TriageResult(paper_id=ref.paper_id, triage_category=None, error=str(e))

    if not isinstance(data, dict):
        return TriageResult(paper_id=ref.paper_id, triage_category=None, error="non-dict response")

    cat = normalize_controlled("triage_category", str(data.get("triage_category", "")).strip().upper() or None)
    if cat not in ("A", "B", "C"):
        cat = None
    return TriageResult(
        paper_id=ref.paper_id,
        triage_category=cat,
        rationale=str(data.get("rationale", "")),
        evidence_quote=str(data.get("evidence_quote", "")),
        main_track=normalize_controlled("main_track", data.get("main_track")),
        target_product_type=normalize_controlled("target_product_type", data.get("target_product_type")),
        is_core_for_modeling=normalize_controlled("is_core_for_modeling", data.get("is_core_for_modeling")),
    )
