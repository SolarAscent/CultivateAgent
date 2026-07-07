"""Export the knowledge base to human- and ML-friendly files.

The screening table implements the record's recommended fast-review workflow
(blocks A + B + C + J + M) so a human can triage the whole corpus in a
spreadsheet before committing to deep extraction of core papers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .store import KnowledgeBase

_SCREEN_COLUMNS = [
    "paper_id", "title", "year", "journal", "triage_category",
    "main_track", "target_product_type", "is_core_for_review", "is_core_for_modeling",
    "has_extractable_quant_data", "modeling_value_score",
    "review_usefulness", "research_usefulness", "data_extraction_usefulness",
    "recommended_action", "grounding_rate", "one_paragraph_reader_summary",
]


def export_screening_csv(kb: KnowledgeBase, out_path: str | Path) -> Path:
    """A+B+C+J+M rapid-screening table -> CSV."""
    import pandas as pd

    rows: List[dict] = []
    for ext in kb.iter_extractions():
        b, ft, qd, fj = ext.basic_info, ext.fast_triage, ext.quant_data, ext.final_judgment
        grounding = None
        for p in (ext.extraction_meta or {}).get("passes", []) or []:
            if p.get("grounding_rate") is not None:
                grounding = p["grounding_rate"]
                break
        rows.append({
            "paper_id": ext.paper_id,
            "title": b.title,
            "year": b.year,
            "journal": b.journal,
            "triage_category": ext.triage_category,
            "main_track": ft.main_track,
            "target_product_type": ft.target_product_type,
            "is_core_for_review": ft.is_core_for_review,
            "is_core_for_modeling": ft.is_core_for_modeling,
            "has_extractable_quant_data": qd.has_extractable_quant_data,
            "modeling_value_score": qd.modeling_value_score,
            "review_usefulness": fj.review_usefulness,
            "research_usefulness": fj.research_usefulness,
            "data_extraction_usefulness": fj.data_extraction_usefulness,
            "recommended_action": fj.recommended_action,
            "grounding_rate": grounding,
            "one_paragraph_reader_summary": fj.one_paragraph_reader_summary,
        })
    df = pd.DataFrame(rows, columns=_SCREEN_COLUMNS)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return out


def export_components_csv(kb: KnowledgeBase, out_path: str | Path) -> Path:
    """Flattened, normalized medium components -> CSV (one row per component use)."""
    import pandas as pd

    df = pd.read_sql_query(
        "SELECT paper_id, role, raw_name, canonical, category, matched_via FROM medium_components ORDER BY paper_id, role",
        kb.conn,
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return out


def export_evidence_csv(kb: KnowledgeBase, out_path: str | Path) -> Path:
    """All evidence quotes + verification status -> CSV (audit trail)."""
    import pandas as pd

    df = pd.read_sql_query(
        "SELECT paper_id, field_key, quote, location, source, confidence, is_inference, verified FROM evidence ORDER BY paper_id",
        kb.conn,
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return out


def export_extractions_jsonl(kb: KnowledgeBase, out_path: str | Path) -> Path:
    """Full structured records -> JSONL (one paper per line; ML-ready)."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for ext in kb.iter_extractions():
            f.write(json.dumps(json.loads(ext.model_dump_json()), ensure_ascii=False) + "\n")
    return out
