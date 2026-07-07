#!/usr/bin/env python3
"""End-to-end pipeline demo (programmatic API, not the CLI).

Usage:
    python scripts/run_pipeline.py            # offline, mock LLM (no key needed)
    python scripts/run_pipeline.py --live     # real LLM from config/config.yaml

The offline path proves the wiring; the live path shows the exact calls you'd
make in your own scripts / notebooks.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # allow running as a standalone script (no install)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="use the configured real LLM instead of the mock")
    ap.add_argument("--bibtex", default=str(ROOT / "data" / "library.example.bib"))
    args = ap.parse_args()

    from cultivate_agent import load_config
    from cultivate_agent.ingest import ingest_library, iter_ingested, parse_bibtex
    from cultivate_agent.kb import KnowledgeBase, export_screening_csv
    from cultivate_agent.normalize import ComponentNormalizer
    from cultivate_agent.triage import classify_paper
    from cultivate_agent.extract import extract_paper
    from cultivate_agent.retrieve import BM25Retriever, build_corpus_from_kb
    from cultivate_agent.design import DesignContext, MediumRecommender, ObjectiveWeights

    cfg = load_config(root=ROOT)

    # --- LLM: real or mock ------------------------------------------------
    if args.live:
        client = cfg.make_llm_client()
        print(f"Using live LLM: {cfg.llm.provider}/{cfg.llm.model}")
    else:
        from cultivate_agent.llm import get_client

        # A generic mock that returns an empty object for every call. Real runs
        # obviously produce real extractions; this just exercises the plumbing.
        client = get_client("mock", "mock", default="{}")
        print("Using mock LLM (offline). Pass --live to use a real model.")

    # --- 1. Ingest --------------------------------------------------------
    bib = Path(args.bibtex)
    if not bib.exists():
        print(f"No BibTeX at {bib}; export your Zotero library there first.")
        return 1
    refs = parse_bibtex(bib)
    print(f"\n[1] Parsed {len(refs)} references")
    ingest_library(refs, cfg.papers_dir, extract_page_images=False, extract_figures=False, extract_tables=False)

    normalizer = ComponentNormalizer(cfg.ontology_dir)
    kb = KnowledgeBase(cfg.kb_file, normalizer=normalizer)

    # --- 2/3. Triage + extract each paper --------------------------------
    for paths, meta in iter_ingested(cfg.papers_dir):
        text = paths.read_fulltext() or (meta.ref.abstract or "")
        kb.upsert_paper(meta.ref)
        tri = classify_paper(client, meta.ref, text)
        kb.upsert_triage(tri)
        ext = extract_paper(client, meta.ref, text, triage_category=tri.triage_category,
                            triage_blocks=cfg.extract.triage_blocks, full_blocks=cfg.extract.full_blocks)
        kb.upsert_extraction(ext)
    print(f"[2/3] Triaged + extracted. KB stats: {kb.stats()}")

    # --- 4. Export --------------------------------------------------------
    out = export_screening_csv(kb, cfg.data_path / "exports" / "screening_table.csv")
    print(f"[4] Wrote screening table -> {out}")

    # --- 5. Design --------------------------------------------------------
    retriever = BM25Retriever()
    retriever.index(build_corpus_from_kb(kb))
    rec = MediumRecommender(client, retriever, kb, top_k=cfg.retrieve.top_k).recommend(
        ObjectiveWeights(weights={"proliferation": 0.6, "cost": 0.3, "differentiation_retention": 0.1}),
        DesignContext(cell_type="bovine satellite cells", species="bovine", stage="expansion"),
    )
    print(f"[5] Recommendation: {len(rec.candidates)} candidate(s), {len(rec.evidence)} evidence item(s)")
    print(json.dumps(rec.objectives, indent=2))
    kb.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
