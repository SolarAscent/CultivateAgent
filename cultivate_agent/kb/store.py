"""SQLite knowledge base.

Stores three views of each paper:

1. the full :class:`PaperExtraction` as JSON (lossless),
2. an ``evidence`` table (every quote, with its verification status),
3. a **flattened, normalized** ``medium_components`` table -- the queryable
   core that turns unstructured papers into an "AI-ready knowledge base"
   (e.g. "which papers use FGF2 in a serum-free bovine context?").

Uses only the Python standard library (``sqlite3``) so it has no runtime deps.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

from ..normalize.components import ComponentNormalizer
from ..schema.extraction import PaperExtraction
from ..schema.paper import PaperRef

_SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    paper_id TEXT PRIMARY KEY,
    slug TEXT, title TEXT, authors_json TEXT, year INTEGER,
    journal TEXT, doi TEXT, triage_category TEXT, ingested_at TEXT
);
CREATE TABLE IF NOT EXISTS extractions (
    paper_id TEXT PRIMARY KEY,
    json TEXT NOT NULL, model TEXT, grounding_rate REAL, extracted_at TEXT,
    FOREIGN KEY(paper_id) REFERENCES papers(paper_id)
);
CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT, field_key TEXT, quote TEXT, location TEXT,
    source TEXT, confidence TEXT, is_inference INTEGER, verified INTEGER
);
CREATE TABLE IF NOT EXISTS medium_components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT, role TEXT, raw_name TEXT, canonical TEXT,
    category TEXT, matched_via TEXT
);
CREATE TABLE IF NOT EXISTS medium_summary (
    paper_id TEXT PRIMARY KEY,
    serum_usage TEXT, serum_free_status TEXT,
    basal_medium_json TEXT, optimization_strategy TEXT, cost_relevance TEXT
);
CREATE TABLE IF NOT EXISTS triage (
    paper_id TEXT PRIMARY KEY,
    category TEXT, rationale TEXT, evidence_quote TEXT,
    main_track TEXT, target_product_type TEXT, is_core_for_modeling TEXT
);
CREATE INDEX IF NOT EXISTS idx_comp_canonical ON medium_components(canonical);
CREATE INDEX IF NOT EXISTS idx_comp_role ON medium_components(role);
CREATE INDEX IF NOT EXISTS idx_papers_triage ON papers(triage_category);
"""

_LIST_ROLES = {
    "growth_factors": "growth_factor",
    "small_molecules": "small_molecule",
    "hydrolysates_or_extracts": "supplement",
    "basal_medium": "basal_medium",
}


class KnowledgeBase:
    def __init__(self, path: str | Path, *, normalizer: Optional[ComponentNormalizer] = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.normalizer = normalizer
        self.init_schema()

    def init_schema(self) -> None:
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "KnowledgeBase":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ------------------------------------------------------------------ #
    # Writers                                                            #
    # ------------------------------------------------------------------ #
    def upsert_paper(self, ref: PaperRef, *, triage_category: Optional[str] = None, ingested_at: Optional[str] = None) -> None:
        self.conn.execute(
            """INSERT INTO papers(paper_id, slug, title, authors_json, year, journal, doi, triage_category, ingested_at)
               VALUES(?,?,?,?,?,?,?,?,?)
               ON CONFLICT(paper_id) DO UPDATE SET
                 slug=excluded.slug, title=excluded.title, authors_json=excluded.authors_json,
                 year=excluded.year, journal=excluded.journal, doi=excluded.doi,
                 triage_category=COALESCE(excluded.triage_category, papers.triage_category),
                 ingested_at=excluded.ingested_at""",
            (ref.paper_id, ref.slug, ref.title, json.dumps(ref.authors), ref.year,
             ref.journal, ref.doi, triage_category, ingested_at),
        )
        self.conn.commit()

    def upsert_triage(self, result) -> None:
        self.conn.execute(
            """INSERT INTO triage(paper_id, category, rationale, evidence_quote, main_track, target_product_type, is_core_for_modeling)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(paper_id) DO UPDATE SET
                 category=excluded.category, rationale=excluded.rationale, evidence_quote=excluded.evidence_quote,
                 main_track=excluded.main_track, target_product_type=excluded.target_product_type,
                 is_core_for_modeling=excluded.is_core_for_modeling""",
            (result.paper_id, result.triage_category, result.rationale, result.evidence_quote,
             result.main_track, result.target_product_type, result.is_core_for_modeling),
        )
        if result.triage_category:
            self.conn.execute("UPDATE papers SET triage_category=? WHERE paper_id=?",
                              (result.triage_category, result.paper_id))
        self.conn.commit()

    def upsert_extraction(self, extraction: PaperExtraction) -> None:
        pid = extraction.paper_id
        meta = extraction.extraction_meta or {}
        grounding = _overall_grounding(meta)
        model = _first_model(meta)

        self.conn.execute(
            """INSERT INTO extractions(paper_id, json, model, grounding_rate, extracted_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(paper_id) DO UPDATE SET
                 json=excluded.json, model=excluded.model,
                 grounding_rate=excluded.grounding_rate, extracted_at=excluded.extracted_at""",
            (pid, extraction.model_dump_json(), model, grounding, _first_time(meta)),
        )

        # Refresh derived rows for this paper.
        self.conn.execute("DELETE FROM evidence WHERE paper_id=?", (pid,))
        for key, ev in extraction.evidence.items():
            verified = 0 if "UNVERIFIED" in (ev.location or "") else 1
            self.conn.execute(
                """INSERT INTO evidence(paper_id, field_key, quote, location, source, confidence, is_inference, verified)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (pid, key, ev.quote, ev.location, ev.source, ev.confidence.value if hasattr(ev.confidence, "value") else str(ev.confidence),
                 int(ev.is_inference), verified),
            )

        self.conn.execute("DELETE FROM medium_components WHERE paper_id=?", (pid,))
        self._flatten_components(extraction)

        m = extraction.medium_info
        self.conn.execute(
            """INSERT INTO medium_summary(paper_id, serum_usage, serum_free_status, basal_medium_json, optimization_strategy, cost_relevance)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(paper_id) DO UPDATE SET
                 serum_usage=excluded.serum_usage, serum_free_status=excluded.serum_free_status,
                 basal_medium_json=excluded.basal_medium_json, optimization_strategy=excluded.optimization_strategy,
                 cost_relevance=excluded.cost_relevance""",
            (pid, m.serum_usage, m.serum_free_status, json.dumps(m.basal_medium or []),
             m.medium_optimization_strategy, m.cost_reduction_relevance),
        )
        self.conn.commit()

    def _flatten_components(self, extraction: PaperExtraction) -> None:
        pid = extraction.paper_id
        m = extraction.medium_info
        for field, role in _LIST_ROLES.items():
            values = getattr(m, field) or []
            for raw in values:
                if self.normalizer:
                    match = self.normalizer.canonicalize(raw)
                    canonical, category, via = match.canonical, match.category, match.matched_via
                else:
                    canonical, category, via = raw, None, "none"
                component_role = category or role
                self.conn.execute(
                    """INSERT INTO medium_components(paper_id, role, raw_name, canonical, category, matched_via)
                       VALUES(?,?,?,?,?,?)""",
                    (pid, component_role, raw, canonical, category, via),
                )

    # ------------------------------------------------------------------ #
    # Readers                                                            #
    # ------------------------------------------------------------------ #
    def get_extraction(self, paper_id: str) -> Optional[PaperExtraction]:
        row = self.conn.execute("SELECT json FROM extractions WHERE paper_id=?", (paper_id,)).fetchone()
        return PaperExtraction.model_validate_json(row["json"]) if row else None

    def iter_extractions(self) -> Iterator[PaperExtraction]:
        for row in self.conn.execute("SELECT json FROM extractions"):
            try:
                yield PaperExtraction.model_validate_json(row["json"])
            except Exception:  # noqa: BLE001
                continue

    def papers_with_component(self, canonical: str, *, role: Optional[str] = None) -> List[str]:
        sql = "SELECT DISTINCT paper_id FROM medium_components WHERE canonical=?"
        args: Tuple = (canonical,)
        if role:
            sql += " AND (role=? OR category=?)"
            args = (canonical, role, role)
        return [r["paper_id"] for r in self.conn.execute(sql, args)]

    def component_counts(self, *, role: Optional[str] = None) -> List[Tuple[str, int]]:
        sql = "SELECT canonical, COUNT(DISTINCT paper_id) n FROM medium_components"
        args: Tuple = ()
        if role:
            sql += " WHERE role=? OR category=?"
            args = (role, role)
        sql += " GROUP BY canonical ORDER BY n DESC"
        return [(r["canonical"], r["n"]) for r in self.conn.execute(sql, args)]

    def stats(self) -> Dict[str, int]:
        def _count(t: str) -> int:
            return self.conn.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"]

        by_tier = {r["triage_category"] or "unclassified": r["n"] for r in
                   self.conn.execute("SELECT triage_category, COUNT(*) n FROM papers GROUP BY triage_category")}
        return {
            "papers": _count("papers"),
            "extractions": _count("extractions"),
            "evidence": _count("evidence"),
            "medium_components": _count("medium_components"),
            **{f"tier_{k}": v for k, v in by_tier.items()},
        }


def _overall_grounding(meta: dict) -> Optional[float]:
    rates = []
    for p in meta.get("passes", []) or []:
        r = p.get("grounding_rate")
        if r is not None:
            rates.append(r)
    return round(sum(rates) / len(rates), 3) if rates else None


def _first_model(meta: dict) -> Optional[str]:
    for p in meta.get("passes", []) or []:
        if p.get("model"):
            return p["model"]
    return None


def _first_time(meta: dict) -> Optional[str]:
    for p in meta.get("passes", []) or []:
        if p.get("extracted_at"):
            return p["extracted_at"]
    return None
