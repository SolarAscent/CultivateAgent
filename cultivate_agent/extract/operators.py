"""Operator-decomposition extraction.

The monolithic "ask one LLM for all A-M fields + evidence" prompt is fragile with
real models (observed live F1 ~0.25; near-empty outputs). Following schema-reduction
and modular-document-processing work (SchemaRAG, arXiv:2607.00008; schema-aware IE,
arXiv:2505.14992; DocETL), we split extraction into a few **operators**, each of
which:

* owns a small, DISJOINT set of schema fields,
* is routed to the paper sections most likely to contain them,
* uses a tiny focused prompt (few fields, not the whole schema),
* returns a small JSON that is validated + evidence-verified independently.

Smaller asks are dramatically more reliable, and per-operator coverage/grounding
makes failures diagnosable (call error vs empty vs parse error vs ungrounded)
instead of a single opaque low score.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from ..llm.base import LLMClient, LLMError, extract_json
from ..schema.evidence import Confidence, Evidence
from ..schema.extraction import CONTROLLED_VOCAB, PaperExtraction, block_model
from ..schema.paper import PaperRef
from ..schema.structured_paper import StructuredPaper, structured_paper_from_text


@dataclass
class ExtractionOperator:
    name: str
    fields: List[str]                 # "<LETTER>.<field>", disjoint across operators
    section_hints: List[str]          # section-title substrings to route context
    guidance: str = ""                # short operator-specific heuristic


class ComponentDoseRecord(BaseModel):
    """A component-dose relation supported by one verbatim source quote."""

    component: str
    dose_or_range: str
    unit: Optional[str] = None
    comparison_group: Optional[str] = None
    endpoint: Optional[str] = None
    evidence: Evidence
    grounded: bool = Field(False, description="Set only by local quote verification.")


# Field ownership is DISJOINT so operators never conflict on merge.
OPERATORS: List[ExtractionOperator] = [
    ExtractionOperator(
        name="context",
        fields=["B.main_track", "B.species", "B.target_product_type",
                "D.cell_type", "D.primary_or_cell_line", "D.tissue_of_origin", "D.species_detail"],
        section_hints=["abstract", "introduction", "methods", "materials and methods", "cell culture"],
        guidance="Identify species, cell identity, and the dominant contribution lane. Sub-headings often name species/cell type.",
    ),
    ExtractionOperator(
        name="medium",
        fields=["E.basal_medium", "E.serum_usage", "E.serum_free_status", "E.growth_factors",
                "E.small_molecules", "E.hydrolysates_or_extracts", "E.conditioned_medium_or_recycling",
                "E.medium_optimization_strategy"],
        section_hints=["methods", "materials and methods", "media formulation", "cell culture", "experimental", "results"],
        guidance="Priority operator. Separate basal medium from supplements. Do not overclaim 'chemically defined'. Capture named growth factors and small molecules.",
    ),
    ExtractionOperator(
        name="dose",
        fields=["J.has_extractable_quant_data", "J.extractable_variables", "J.key_numeric_results",
                "J.units_reported", "J.experimental_comparison_groups"],
        section_hints=["results", "methods", "materials and methods", "supplementary", "table"],
        guidance="Preserve original numbers and units exactly. Keep the comparison group with each number.",
    ),
    ExtractionOperator(
        name="endpoints",
        fields=["I.main_readouts", "I.proliferation_metrics", "I.differentiation_metrics", "I.maturation_metrics"],
        section_hints=["results", "methods", "materials and methods", "figure"],
        guidance="List the measured readouts. Proliferation vs differentiation vs maturation are distinct.",
    ),
    ExtractionOperator(
        name="findings",
        fields=["C.problem_statement", "C.proposed_solution", "C.claimed_novelty",
                "K.core_findings", "K.authors_reported_limitations",
                "M.recommended_action", "M.one_paragraph_reader_summary"],
        section_hints=["abstract", "introduction", "discussion", "conclusion", "results"],
        guidance="Keep author novelty claims separate from evidence. Be dense and factual.",
    ),
]


def _field_line(key: str) -> str:
    """Render a single field descriptor for the prompt from the schema itself."""
    letter, name = key.split(".", 1)
    info = block_model(letter).model_fields.get(name)
    if info is None:
        return f"- {key}"
    ann = str(info.annotation)
    base = "list[str]" if "List" in ann else ("int" if "int" in ann else "str")
    allowed = CONTROLLED_VOCAB.get(name)
    allowed_str = f" | choose one of: {allowed}" if allowed else ""
    return f"- {key} ({base}){allowed_str}: {info.description or ''}"


_OP_SYSTEM = (
    "You extract a SMALL set of specific fields from a cultivated-meat paper excerpt "
    "for a medium-optimization knowledge base. Use ONLY the provided text; never use "
    "outside knowledge. Unsupported fields must be \"NR\". Every real value needs a "
    "verbatim quote copied exactly from the text. Prefer marking a field NR over guessing. "
    "Output STRICT JSON only."
)


def build_operator_prompt(op: ExtractionOperator, ref: PaperRef, text: str) -> str:
    field_lines = "\n".join(_field_line(k) for k in op.fields)
    dose_shape = ""
    dose_instruction = ""
    if op.name == "dose":
        dose_shape = """,
  "dose_records": [
    {
      "component": "<component exactly as reported>",
      "dose_or_range": "<number/range plus unit exactly as reported>",
      "unit": "<unit or null>",
      "comparison_group": "<group or null>",
      "endpoint": "<measured endpoint or null>",
      "evidence": {"quote": "<one verbatim quote containing component and dose>", "location": "<section>", "confidence": "low|medium|high"}
    }
  ]
"""
        dose_instruction = (
            "Only emit a dose_record when the SAME quote explicitly contains both the "
            "component and its dose/range. Do not pair values across separate passages."
        )
    return f"""PAPER: {ref.title or ref.paper_id}

Operator: {op.name}. {op.guidance}

Extract ONLY these fields (nothing else):
{field_lines}

Return STRICT JSON in exactly this shape:
{{
  "fields": {{ "<LETTER>.<field>": <value or "NR">, ... }},
  "evidence": {{ "<LETTER>.<field>": {{"quote": "<verbatim>", "location": "<section>", "confidence": "low|medium|high"}}, ... }}{dose_shape}
}}

{dose_instruction}

TEXT:
'''{text}'''

REMINDER: only the listed fields; verbatim quotes; NR when unsupported; strict JSON.
"""


def _route_context(paper: StructuredPaper, hints: List[str], max_chars: int) -> str:
    """Concatenate the sections whose titles match the operator's hints."""
    passages = paper.section_passages(hints)
    if not passages:
        # fall back to abstract + whole text (bounded)
        base = (("Abstract\n" + paper.abstract) if paper.abstract else "") + "\n\n" + paper.all_text()
        return base.strip()[:max_chars]
    out, used = [], 0
    if paper.abstract:
        chunk = "Abstract\n" + paper.abstract
        out.append(chunk[: max_chars // 3])
        used += len(out[-1])
    for _sid, passage in passages:
        if used >= max_chars:
            break
        chunk = passage[: max_chars - used]
        out.append(chunk)
        used += len(chunk)
    return "\n\n".join(out)


@dataclass
class OperatorResult:
    name: str
    status: str                       # ok | empty | call_error | parse_error
    fields: Dict[str, object] = field(default_factory=dict)
    evidence: Dict[str, Evidence] = field(default_factory=dict)
    n_requested: int = 0
    n_filled: int = 0
    n_grounded: int = 0
    dose_records: List[ComponentDoseRecord] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def coverage(self) -> float:
        return round(self.n_filled / self.n_requested, 3) if self.n_requested else 0.0

    @property
    def grounding(self) -> Optional[float]:
        return round(self.n_grounded / self.n_filled, 3) if self.n_filled else None


def _is_null(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() in {"", "NR", "NA", "UNC"})


def _normalized_span(value: str) -> str:
    return " ".join((value or "").lower().split())


def _dose_record_supported(record: ComponentDoseRecord, source: str) -> bool:
    quote = _normalized_span(record.evidence.quote)
    component = _normalized_span(record.component)
    dose = _normalized_span(record.dose_or_range)
    if not component or not dose or not re.search(r"\d", dose):
        return False
    if component not in quote or dose not in quote:
        return False
    if record.unit:
        unit = _normalized_span(record.unit)
        if unit and unit not in quote and unit not in dose:
            return False
    return record.evidence.verify_against(source)


def run_operator(client: LLMClient, op: ExtractionOperator, ref: PaperRef,
                 paper: StructuredPaper, *, max_chars: int = 16000,
                 verify_evidence: bool = True, full_text: str = "") -> OperatorResult:
    """Run one operator: route -> prompt -> JSON -> validate fields + verify quotes."""
    res = OperatorResult(name=op.name, status="ok", n_requested=len(op.fields))
    ctx = _route_context(paper, op.section_hints, max_chars)
    try:
        raw = client.chat(_OP_SYSTEM, build_operator_prompt(op, ref, ctx))
    except LLMError as e:
        res.status, res.error = "call_error", str(e)
        return res
    try:
        payload = extract_json(raw)
    except LLMError as e:
        res.status, res.error = "parse_error", str(e)
        return res

    fields = payload.get("fields", payload) if isinstance(payload, dict) else {}
    ev_raw = payload.get("evidence", {}) if isinstance(payload, dict) else {}

    source_for_verify = full_text or paper.all_text()
    for key in op.fields:
        val = fields.get(key)
        if _is_null(val):
            continue
        res.fields[key] = val
        res.n_filled += 1
        ev = ev_raw.get(key) if isinstance(ev_raw, dict) else None
        if isinstance(ev, dict) and ev.get("quote"):
            try:
                evobj = Evidence.model_validate(ev)
            except Exception:  # noqa: BLE001
                continue
            if verify_evidence:
                if evobj.verify_against(source_for_verify):
                    res.n_grounded += 1
                else:
                    evobj.confidence = Confidence.low
                    evobj.location = (evobj.location or "") + " [UNVERIFIED: quote not found in source]"
            else:
                res.n_grounded += 1
            res.evidence[key] = evobj

    if op.name == "dose" and isinstance(payload, dict):
        raw_records = payload.get("dose_records") or []
        if isinstance(raw_records, list):
            for raw_record in raw_records:
                if not isinstance(raw_record, dict):
                    continue
                try:
                    record = ComponentDoseRecord.model_validate(raw_record)
                except Exception:  # noqa: BLE001
                    continue
                record.grounded = (
                    _dose_record_supported(record, source_for_verify)
                    if verify_evidence else False
                )
                if not record.grounded:
                    record.evidence.confidence = Confidence.low
                    reason = (
                        "component-dose relation not supported by quote"
                        if verify_evidence else "component-dose verification disabled"
                    )
                    record.evidence.location = (
                        (record.evidence.location or "")
                        + f" [UNVERIFIED: {reason}]"
                    )
                res.dose_records.append(record)

    if res.n_filled == 0:
        res.status = "empty"
    return res


class OperatorExtractor:
    """Run all operators and merge into a :class:`PaperExtraction`."""

    def __init__(self, client: LLMClient, operators: Optional[List[ExtractionOperator]] = None,
                 *, max_chars: int = 16000, verify_evidence: bool = True):
        self.client = client
        self.operators = operators or OPERATORS
        self.max_chars = max_chars
        self.verify_evidence = verify_evidence

    def extract(self, ref: PaperRef, source: Union[str, StructuredPaper]) -> PaperExtraction:
        if isinstance(source, StructuredPaper):
            paper = source
            # No separate original available; all_text() is the best source we have.
            full_text = source.all_text()
        else:
            original = source or ""
            paper = structured_paper_from_text(ref.paper_id, original, title=ref.title)
            # Verify quotes against the ORIGINAL text, not the round-tripped
            # section reconstruction (which can drop/alter spans and falsely flag
            # real quotes as ungrounded).
            full_text = original

        ext = PaperExtraction(paper_id=ref.paper_id)
        # Reliable bibliographic prefill (block A).
        ext.basic_info.paper_id = ref.paper_id
        ext.basic_info.title = ref.title or None
        ext.basic_info.authors = ref.authors or None
        ext.basic_info.year = ref.year
        ext.basic_info.journal = ref.journal
        ext.basic_info.doi = ref.doi or "NR"

        per_block: Dict[str, dict] = defaultdict(dict)
        op_meta: List[dict] = []
        total_filled = total_grounded = 0
        dose_records: List[dict] = []

        for op in self.operators:
            r = run_operator(self.client, op, ref, paper, max_chars=self.max_chars,
                             verify_evidence=self.verify_evidence, full_text=full_text)
            for key, val in r.fields.items():
                letter, name = key.split(".", 1)
                per_block[letter][name] = val
            ext.evidence.update(r.evidence)
            total_filled += r.n_filled
            total_grounded += r.n_grounded
            dose_records.extend(record.model_dump(mode="json") for record in r.dose_records)
            op_meta.append({"operator": r.name, "status": r.status, "coverage": r.coverage,
                            "grounding": r.grounding, "n_filled": r.n_filled,
                            "n_requested": r.n_requested,
                            "dose_records": len(r.dose_records),
                            "grounded_dose_records": sum(x.grounded for x in r.dose_records),
                            "error": r.error})

        # Merge operator field values into their blocks (validators normalize vocab).
        for letter, vals in per_block.items():
            existing = ext.get_block(letter).model_dump()
            existing.update({k: _coerce(letter, k, v) for k, v in vals.items()})
            ext.set_block(letter, block_model(letter).model_validate(existing))

        ext.extraction_meta = {
            "mode": "operators",
            "source": paper.source,
            "operators": op_meta,
            "dose_records": dose_records,
            "n_filled": total_filled,
            "grounding_rate": round(total_grounded / total_filled, 3) if total_filled else None,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }
        return ext


def _coerce(letter: str, name: str, value):
    """Coerce a raw operator value to the field's list/scalar shape."""
    info = block_model(letter).model_fields.get(name)
    if info is None:
        return value
    is_list = "List" in str(info.annotation)
    if is_list and not isinstance(value, list):
        return [str(value)] if not _is_null(value) else None
    if not is_list and isinstance(value, list):
        return "; ".join(str(v) for v in value) if value else None
    return value
