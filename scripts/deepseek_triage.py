#!/usr/bin/env python3
"""DeepSeek-delegated relevance triage over the corpus (bounded, verifiable labor).

Per the AI-collaboration delegation protocol, DeepSeek does bounded, auto-verifiable
labour and never decides science. This reuses the tested, temperature=0,
evidence-quote-backed triage classifier: DeepSeek assigns A/B/C + is_core_for_modeling
with a grounded quote; a deterministic check confirms the quote is verbatim in the
source; Claude/Codex only design + spot-check.

Norm compliance: narrow per-paper task; temperature=0 (classifier); key read only
from .env (via cfg); provenance (model + run_id) on every row; output is an auditable
TSV, never the shared KB (so no conflict with Codex's worktree).

    python scripts/deepseek_triage.py --limit 10 --model deepseek-chat   # pilot
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
from cultivate_agent.triage.classifier import classify_paper  # noqa: E402

TRIAGE_HEAD_CHARS = 12000  # title + abstract + intro is enough for relevance triage


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--model", default="deepseek-chat")
    ap.add_argument("--out", default="/tmp/triage_deepseek.tsv")
    args = ap.parse_args()

    cfg = load_config(root=ROOT)
    cfg.llm.model = args.model
    run_id = time.strftime("%Y%m%dT%H%M%S")

    papers = [(paths, meta) for paths, meta in iter_ingested(cfg.papers_dir)]
    if args.limit:
        papers = papers[: args.limit]
    print(f"Triage {len(papers)} papers (model={cfg.llm.model}, workers={args.workers})", flush=True)

    def work(item):
        paths, meta = item
        text = (paths.read_fulltext() or "")[:TRIAGE_HEAD_CHARS]
        if not text.strip():
            return meta.ref.paper_id, None, False
        client = cfg.make_llm_client()          # one client per task; key from .env
        res = classify_paper(client, meta.ref, text)
        # Deterministic grounding: the model's quote must be verbatim in what it saw.
        q = (res.evidence_quote or "").strip()
        grounded = len(q) >= 12 and q[:80] in text
        return meta.ref.paper_id, res, grounded

    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(work, it) for it in papers]
        for i, fut in enumerate(as_completed(futs), 1):
            pid, res, grounded = fut.result()
            cat = res.triage_category if res else None
            core = res.is_core_for_modeling if res else None
            err = (res.error if res and res.error else ("" if res else "no_fulltext"))
            print(f"  [{i}/{len(papers)}] {cat or '-'} core={core or '-'} "
                  f"grounded={int(grounded)} {pid[:56]}", flush=True)
            clip = lambda s: (s or "")[:300].replace("\t", " ").replace("\n", " ")
            rows.append([
                pid, cat, core,
                res.main_track if res else None,
                res.target_product_type if res else None,
                "yes" if grounded else "no",
                clip(res.rationale if res else ""),
                clip(res.evidence_quote if res else ""),
                err, args.model, run_id,
            ])

    order = {"A": 0, "B": 1, "C": 2, None: 3}
    rows.sort(key=lambda r: (order.get(r[1], 3), r[0]))
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["paper_id", "triage_category", "is_core_for_modeling", "main_track",
                    "target_product_type", "quote_grounded", "rationale", "evidence_quote",
                    "error", "model", "run_id"])
        w.writerows(rows)

    cats = Counter(r[1] for r in rows)
    grounded_n = sum(1 for r in rows if r[5] == "yes")
    core_n = sum(1 for r in rows if r[1] == "A" and r[2] == "yes")
    errs = sum(1 for r in rows if r[8])
    print(f"\nDONE -> {args.out}")
    print(f"categories: {dict(cats)}  |  grounded quotes: {grounded_n}/{len(rows)}  "
          f"|  A+core: {core_n}  |  errors/no-text: {errs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
