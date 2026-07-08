#!/usr/bin/env python3
"""Extract directional effects over the whole ingested corpus, in parallel.

extract_effects is one independent LLM call per paper, so we fan out across a
thread pool (providers like DeepSeek handle concurrent requests). Collects all
grounded EvidenceItems, synthesizes (random-effects meta-analysis), stores to the
KB, and prints components ranked by number of contributing studies (k) so the
k>1 pooled evidence is visible.

    python scripts/run_evidence_parallel.py --outcome proliferation --workers 6
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cultivate_agent import load_config                          # noqa: E402
from cultivate_agent.evidence import extract_effects, synthesize # noqa: E402
from cultivate_agent.ingest import iter_ingested                 # noqa: E402
from cultivate_agent.kb import KnowledgeBase                     # noqa: E402
from cultivate_agent.normalize import ComponentNormalizer        # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outcome", default="proliferation")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--by-context", action="store_true",
                    help="group by (component,outcome,context); default pools across context so I² captures heterogeneity")
    args = ap.parse_args()

    cfg = load_config(root=ROOT)
    normalizer = ComponentNormalizer(cfg.ontology_dir)

    def clean_component(name: str) -> str:
        """Strip parenthetical qualifiers/doses so verbose LLM names pool, then canonicalize."""
        base = re.sub(r"\s*\([^)]*\)", "", name).strip()          # drop "(immobilized ...)" / "(5 µM)"
        base = re.sub(r"\s+at\s+[\d.].*$", "", base, flags=re.I)   # drop "... at 20 ng/mL"
        return normalizer.canonicalize(base).canonical or base

    papers = [(paths, meta) for paths, meta in iter_ingested(cfg.papers_dir)]
    if args.limit:
        papers = papers[: args.limit]
    print(f"Extracting '{args.outcome}' effects from {len(papers)} papers "
          f"(workers={args.workers}, model={cfg.llm.model})")

    def work(item):
        paths, meta = item
        client = cfg.make_llm_client()   # one client per task (thread-safe usage)
        text = paths.read_fulltext()
        if not text.strip():
            return meta.ref.paper_id, []
        try:
            items = extract_effects(client, meta.ref, text, args.outcome,
                                    normalizer=normalizer, verify_evidence=cfg.extract.require_evidence)
        except Exception as e:  # noqa: BLE001
            return meta.ref.paper_id, f"ERROR: {e}"
        return meta.ref.paper_id, items

    all_items = []
    done = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(work, it): it for it in papers}
        for fut in as_completed(futs):
            pid, res = fut.result()
            done += 1
            if isinstance(res, str):
                print(f"  [{done}/{len(papers)}] {pid}: {res}")
            else:
                all_items.extend(res)
                print(f"  [{done}/{len(papers)}] {pid}: {len(res)} grounded effect(s)")

    # Re-canonicalize verbose component names so the same component pools across papers.
    for it in all_items:
        it.component = clean_component(it.component)
    # Persist raw items so we can re-synthesize without re-calling the API.
    items_path = cfg.data_path / "exports" / f"effect_items_{args.outcome}.json"
    items_path.parent.mkdir(parents=True, exist_ok=True)
    items_path.write_text(json.dumps([it.__dict__ for it in all_items], ensure_ascii=False, indent=1))

    summaries = synthesize(all_items, by_context=args.by_context)
    kb = KnowledgeBase(cfg.kb_file, normalizer=normalizer)
    kb.upsert_evidence_summaries(summaries)
    kb.close()

    dt = time.time() - t0
    print(f"\n{len(all_items)} grounded effects -> {len(summaries)} summaries in {dt:.0f}s")
    multi = [s for s in summaries if s.k > 1]
    print(f"\nComponents with k>1 (real pooled evidence): {len(multi)}")
    for s in sorted(multi, key=lambda x: -x.k)[:25]:
        het = f" I²={s.i_squared:.0%}" if s.i_squared is not None else ""
        flag = "  [context-dependent: TEST]" if s.context_dependent else ""
        print(f"  k={s.k:2d}  p_benef={s.p_beneficial:.2f}  {s.component[:44]:44s} ({s.method}{het}){flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
