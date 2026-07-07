"""LLM-driven schema extraction with evidence verification.

Pipeline per paper:

    text --(prompt for blocks)--> LLM --> JSON
         --> validate into Pydantic blocks
         --> attach + VERIFY evidence quotes against the source text
         --> PaperExtraction

The evidence-verification step is what separates this from a plain "ask the LLM
for JSON" script: any quote that is not actually present in the source is
flagged (confidence downgraded and counted), giving a measurable grounding rate
per paper.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from ..llm.base import LLMClient, LLMError
from ..schema.evidence import Confidence, Evidence
from ..schema.extraction import PaperExtraction, _BLOCK_ATTR, block_model
from ..schema.paper import PaperRef
from .prompts import SYSTEM_EXTRACTION, build_extraction_prompt


import re

# Section headers where medium / quantitative detail concentrates. ReactionSeek
# notes that co-reference and key facts are dispersed across a paper; we bias the
# context toward Methods/Results rather than blindly truncating.
_SECTION_RE = re.compile(
    r"(?im)^\s*(?:\d+\.?\s*)?(materials?\s+and\s+methods|methods|experimental(?:\s+section)?|"
    r"results(?:\s+and\s+discussion)?|results|media\s+formulation|cell\s+culture)\b.*$"
)


def _select_context(text: str, max_chars: int) -> str:
    """Fit text into the context budget, biased toward Methods/Results.

    Strategy when the paper exceeds the budget:
      1. always keep the head (title/abstract/intro),
      2. then pack in the Methods/Results sections (highest medium-signal),
      3. fall back to a head+tail window if no sections are detected.
    A marker makes any elision explicit to the model.
    """
    if len(text) <= max_chars:
        return text

    head_budget = int(max_chars * 0.35)
    head = text[:head_budget]

    # Locate section starts; take spans from each match to the next.
    matches = list(_SECTION_RE.finditer(text, head_budget))
    if matches:
        remaining = max_chars - head_budget - 100
        chunks: List[str] = []
        for i, m in enumerate(matches):
            if remaining <= 0:
                break
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            span = text[m.start():end][:remaining]
            chunks.append(span)
            remaining -= len(span)
        body = "\n\n[...]\n\n".join(chunks)
        return head + "\n\n[... jumping to key sections ...]\n\n" + body

    # No sections detected -> head + tail window.
    tail = max_chars - head_budget
    return text[:head_budget] + "\n\n[... middle omitted for length ...]\n\n" + text[-tail:]


_ATTR_TO_BLOCK = {attr: letter for letter, attr in _BLOCK_ATTR.items()}


def _block_key(key: object) -> Optional[str]:
    k = str(key).strip()
    if len(k) == 1 and k.upper() in _BLOCK_ATTR:
        return k.upper()
    return _ATTR_TO_BLOCK.get(k)


def _normalize_evidence_key(key: object) -> str:
    text = str(key).strip()
    if "." not in text:
        return text
    prefix, field = text.split(".", 1)
    letter = _block_key(prefix)
    return f"{letter}.{field}" if letter else text


def _coerce_blocks_payload(payload: dict) -> Tuple[dict, dict]:
    """Return ``(blocks, evidence)`` from a possibly-messy JSON payload."""
    if not isinstance(payload, dict):
        return {}, {}
    blocks = payload.get("blocks")
    evidence = payload.get("evidence", {})
    source = blocks if isinstance(blocks, dict) else payload
    coerced_blocks = {}
    for k, v in (source or {}).items():
        letter = _block_key(k)
        if letter and isinstance(v, dict):
            coerced_blocks[letter] = v
    coerced_evidence = {
        _normalize_evidence_key(k): v
        for k, v in (evidence or {}).items()
    } if isinstance(evidence, dict) else {}
    return coerced_blocks, coerced_evidence


def extract_blocks(
    client: LLMClient,
    ref: PaperRef,
    text: str,
    blocks: List[str],
    *,
    max_context_chars: int = 60000,
    verify_evidence: bool = True,
) -> Tuple[Dict[str, object], Dict[str, Evidence], Dict[str, object]]:
    """Extract the requested schema ``blocks`` from ``text``.

    Returns ``(block_letter -> block_model_instance, "L.field" -> Evidence,
    meta)``.
    """
    ctx = _select_context(text, max_context_chars)
    prompt = build_extraction_prompt(ref, ctx, blocks)
    payload = client.complete_json(SYSTEM_EXTRACTION, prompt)
    raw_blocks, raw_evidence = _coerce_blocks_payload(payload)

    parsed: Dict[str, object] = {}
    parse_errors: List[str] = []
    for letter in blocks:
        letter = letter.upper()
        data = raw_blocks.get(letter) or raw_blocks.get(letter.lower())
        if not isinstance(data, dict):
            continue
        try:
            parsed[letter] = block_model(letter).model_validate(data)
        except Exception as e:  # noqa: BLE001 - keep going on one bad block
            parsed[letter] = block_model(letter)()  # empty block, don't lose the paper
            parse_errors.append(f"{letter}: {e}")

    # Evidence + verification.
    evidence: Dict[str, Evidence] = {}
    verified = 0
    total = 0
    for key, ev in (raw_evidence or {}).items():
        if not isinstance(ev, dict) or "." not in str(key):
            continue
        try:
            evobj = Evidence.model_validate(ev)
        except Exception:  # noqa: BLE001
            continue
        total += 1
        if verify_evidence:
            if evobj.verify_against(text):
                verified += 1
            else:
                # Not found verbatim -> keep the claim but flag it as ungrounded.
                evobj.confidence = Confidence.low
                evobj.location = (evobj.location or "") + " [UNVERIFIED: quote not found in source]"
        evidence[key] = evobj

    meta = {
        "model": client.model,
        "blocks": blocks,
        "evidence_total": total,
        "evidence_verified": verified,
        "grounding_rate": round(verified / total, 3) if total else None,
        "context_chars": len(ctx),
        "truncated": len(text) > max_context_chars,
        "parse_errors": parse_errors,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
    }
    return parsed, evidence, meta


def extract_paper(
    client: LLMClient,
    ref: PaperRef,
    text: str,
    *,
    triage_blocks: Optional[List[str]] = None,
    full_blocks: Optional[List[str]] = None,
    full: bool = True,
    max_context_chars: int = 60000,
    verify_evidence: bool = True,
    triage_category: Optional[str] = None,
) -> PaperExtraction:
    """Extract a full :class:`PaperExtraction` for one paper.

    ``full=False`` runs only the fast-triage blocks (cheap first pass);
    ``full=True`` additionally runs the deep-extraction blocks (for core papers).
    """
    triage_blocks = triage_blocks or ["A", "B", "C", "J", "M"]
    full_blocks = full_blocks or ["D", "E", "F", "G", "H", "I", "K", "L"]

    extraction = PaperExtraction(paper_id=ref.paper_id, triage_category=triage_category)

    # Pre-fill block A from the bibliographic ref (cheap + reliable).
    extraction.basic_info.paper_id = ref.paper_id
    extraction.basic_info.title = ref.title or None
    extraction.basic_info.authors = ref.authors or None
    extraction.basic_info.year = ref.year
    extraction.basic_info.journal = ref.journal
    extraction.basic_info.doi = ref.doi or "NR"

    plan = list(triage_blocks)
    if full:
        plan += [b for b in full_blocks if b not in plan]

    if not text.strip():
        extraction.extraction_meta = {"warning": "no full text available; only bibliographic block A filled"}
        return extraction

    all_meta: List[dict] = []
    # Two passes keep each prompt focused (triage group, then deep group).
    groups = [triage_blocks] + ([full_blocks] if full else [])
    for group in groups:
        group = [b for b in group if b in plan]
        if not group:
            continue
        try:
            parsed, evidence, meta = extract_blocks(
                client, ref, text, group,
                max_context_chars=max_context_chars, verify_evidence=verify_evidence,
            )
        except LLMError as e:
            all_meta.append({"group": group, "error": str(e)})
            continue
        for letter, block in parsed.items():
            # Do not let an extracted (possibly weaker) A overwrite the reliable
            # bibliographic prefill for identity fields.
            if letter == "A":
                merged = block
                if getattr(merged, "title", None) is None:
                    merged.title = extraction.basic_info.title
                if not getattr(merged, "authors", None):
                    merged.authors = extraction.basic_info.authors
                extraction.set_block("A", merged)
                extraction.basic_info.paper_id = ref.paper_id
            else:
                extraction.set_block(letter, block)
        extraction.evidence.update(evidence)
        all_meta.append(meta)

    extraction.extraction_meta = {"passes": all_meta}
    return extraction
