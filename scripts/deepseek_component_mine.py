#!/usr/bin/env python3
"""DeepSeek component-name mining to grow the ontology (funnel for canonicalization).

Bounded DeepSeek labour: per paper, list the culture-MEDIUM components/reagents named
in it (names + coarse category only -- NO effects, NO numbers). Aggregate, canonicalize
against the current ontology, and surface the names that DON'T yet canonicalize and recur
across papers -- those are alias/synonym candidates for Claude to curate into the ontology.
Higher-quality canonicalization raises k (pooling), which multiplies the value of every
downstream evidence item (tier-1 or tier-3).

Delegation stays honest: DeepSeek proposes NAMES that appear in the text; it never decides
the ontology. Claude reviews the candidate list and adds only confident, additive aliases.

Norms: narrow per-paper task; temperature=0; key from .env; per-row provenance; output to
an auditable TSV; pilot-before-scale; run on the triage's A/core papers only (high signal).

    python scripts/deepseek_component_mine.py --limit 8      # pilot
    python scripts/deepseek_component_mine.py                # full (A/core papers)
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cultivate_agent import load_config                    # noqa: E402
from cultivate_agent.ingest import iter_ingested           # noqa: E402
from cultivate_agent.normalize import ComponentNormalizer  # noqa: E402

TRIAGE = ROOT / "data" / "literature" / "corpus_relevance_triage.tsv"
HEAD_CHARS = 16000

SYSTEM = (
    "You extract the culture-MEDIUM components named in a cultivated-meat paper: basal media, "
    "growth factors, recombinant proteins, serum/albumin and their replacements, hydrolysates, "
    "small molecules, vitamins, lipids, and defined supplements. List NAMES ONLY as written in "
    "the text -- no doses, no effects, no numbers. Answer ONLY JSON."
)


def build_user(text: str) -> str:
    return (
        "From the text below, list every distinct culture-medium component/reagent NAME that is "
        "mentioned. Use the exact surface form in the text (keep abbreviations). Do not invent "
        "components not present. Do not include cell types, assays, equipment, scaffolds, or "
        "outcomes.\n\n"
        f"{text}\n\n"
        'Return JSON: {"components": [{"name":"<as written>","category":"basal|growth_factor|'
        'protein|albumin|hydrolysate|small_molecule|vitamin|lipid|supplement|other"}]}'
    )


def _core_paper_ids() -> set[str]:
    ids: set[str] = set()
    if TRIAGE.exists():
        for r in csv.DictReader(open(TRIAGE, encoding="utf-8"), delimiter="\t"):
            if r.get("triage_category") == "A":
                ids.add(r["paper_id"])
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--model", default="deepseek-chat")
    ap.add_argument("--out", default="/tmp/component_candidates.tsv")
    ap.add_argument("--all", action="store_true", help="mine all ingested papers, not just A/core")
    args = ap.parse_args()

    cfg = load_config(root=ROOT)
    cfg.llm.model = args.model
    normalizer = ComponentNormalizer(cfg.ontology_dir)
    run_id = time.strftime("%Y%m%dT%H%M%S")

    core = _core_paper_ids()
    papers = [(p, m) for p, m in iter_ingested(cfg.papers_dir)
              if args.all or not core or m.ref.paper_id in core]
    if args.limit:
        papers = papers[: args.limit]
    print(f"Mining components from {len(papers)} papers (model={cfg.llm.model}, "
          f"workers={args.workers})", flush=True)

    freq: Counter = Counter()          # raw name -> paper count
    cat: dict[str, str] = {}
    lock_papers = 0

    def work(item):
        paths, meta = item
        text = (paths.read_fulltext() or "")[:HEAD_CHARS]
        if not text.strip():
            return []
        client = cfg.make_llm_client()
        try:
            data = client.complete_json(SYSTEM, build_user(text))
        except Exception:              # noqa: BLE001
            return []
        out = []
        if isinstance(data, dict):
            for c in data.get("components", []) or []:
                if isinstance(c, dict) and str(c.get("name", "")).strip():
                    out.append((str(c["name"]).strip()[:80], str(c.get("category", "other"))[:20]))
        return out

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(work, it) for it in papers]
        for i, fut in enumerate(as_completed(futs), 1):
            names = fut.result()
            for name, category in set(names):        # dedup within a paper
                freq[name] += 1
                cat.setdefault(name, category)
            if i % 10 == 0:
                print(f"  {i}/{len(papers)} papers", flush=True)

    # Canonicalize each raw name; surface the ones that DON'T resolve and recur.
    rows = []
    for name, n in freq.items():
        m = normalizer.canonicalize(name)
        rows.append((name, n, cat.get(name, "other"), m.canonical, m.matched_via))
    rows.sort(key=lambda r: (r[4] != "none", -r[1]))   # unresolved first, then by frequency

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["raw_name", "paper_count", "category", "canonical", "matched_via", "model", "run_id"])
        for name, n, category, canon, via in rows:
            w.writerow([name, n, category, canon, via, args.model, run_id])

    unresolved = [r for r in rows if r[4] == "none" and r[1] >= 2]
    print(f"\nDONE -> {args.out}")
    print(f"distinct names: {len(rows)}  |  resolved to ontology: {sum(1 for r in rows if r[4] != 'none')}")
    print(f"UNRESOLVED and recurring (k>=2) -> alias candidates: {len(unresolved)}")
    for name, n, category, _c, _v in unresolved[:20]:
        print(f"  k={n:<2} [{category}] {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
