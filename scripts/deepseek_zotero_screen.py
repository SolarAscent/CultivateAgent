#!/usr/bin/env python3
"""DeepSeek title/abstract relevance screen over a Zotero CSV export (funnel step 2).

Turns a large, mostly-irrelevant reference dump into a focused candidate list. DeepSeek
does bounded labour: given title + abstract, classify relevance to the narrow project
scope (expansion-phase culture MEDIUM for muscle/satellite/stem cells; serum-free /
serum-reduced, growth factors, medium components). It never decides science downstream;
this is a first-pass funnel, spot-checked by Claude.

Norms: dedup first; batched narrow task; temperature=0; key only from .env (via cfg);
per-row provenance (model + run_id); keeps the has_pdf flag so survivors split into
"extract now" (has PDF) vs "acquire" (no PDF). Output is an auditable TSV.

    python scripts/deepseek_zotero_screen.py --limit 60          # pilot
    python scripts/deepseek_zotero_screen.py --workers 20        # full
"""

from __future__ import annotations

import argparse
import csv
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cultivate_agent import load_config          # noqa: E402

DEFAULT_CSV = "/Users/tianyangsong/Desktop/CulturedMeat_fullpapers.csv"

SYSTEM = (
    "You screen paper title+abstracts for ONE narrow topic: culture MEDIUM for the "
    "EXPANSION / proliferation of muscle, satellite, myoblast, or stem cells for "
    "cultivated (cultured) meat -- serum-free or serum-reduced media, growth factors, "
    "albumin/serum replacements, hydrolysates, and other medium components. "
    "Answer ONLY with compact JSON, no prose."
)


def build_user(batch: list[dict]) -> str:
    blocks = []
    for i, it in enumerate(batch, 1):
        blocks.append(f"[{i}] TITLE: {it['title']}\nABSTRACT: {it['abs'][:600]}")
    body = "\n\n".join(blocks)
    return (
        "Classify each paper's relevance to the topic:\n"
        "- yes = clearly about expansion/proliferation culture medium, serum-free/reduced "
        "media, growth factors, albumin/serum replacement, or medium components for "
        "muscle/satellite/myoblast/stem cells\n"
        "- maybe = related but off-target (differentiation-only medium, other cell types, "
        "scaffold/microcarrier papers that also tune medium)\n"
        "- no = unrelated (pure scaffold/tissue engineering, sensory/texture, life-cycle "
        "or techno-economics, policy, unrelated biology/medicine)\n\n"
        f"{body}\n\n"
        f'Return JSON mapping each number to a verdict, for all {len(batch)} items:\n'
        '{"1":{"r":"yes|maybe|no","why":"<=8 words"}, "2":{...}, ...}'
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--batch", type=int, default=10)
    ap.add_argument("--model", default="deepseek-chat")
    ap.add_argument("--out", default="/tmp/zotero_screen.tsv")
    args = ap.parse_args()

    cfg = load_config(root=ROOT)
    cfg.llm.model = args.model
    run_id = time.strftime("%Y%m%dT%H%M%S")

    # Load + dedup by DOI (fallback title).
    seen: set[str] = set()
    uniq: list[dict] = []
    for r in csv.DictReader(open(args.csv, encoding="utf-8-sig")):
        doi = (r.get("DOI") or "").strip().lower()
        title = (r.get("Title") or "").strip()
        key = doi or title.lower()
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append({
            "doi": doi, "title": title,
            "abs": (r.get("Abstract Note") or "").strip(),
            "has_pdf": "yes" if (r.get("File Attachments") or "").strip() else "no",
            "year": (r.get("Publication Year") or "").strip(),
        })
    if args.limit:
        uniq = uniq[: args.limit]
    batches = [uniq[i:i + args.batch] for i in range(0, len(uniq), args.batch)]
    print(f"Screening {len(uniq)} unique papers in {len(batches)} batches "
          f"(model={cfg.llm.model}, workers={args.workers})", flush=True)

    verdict: dict[int, tuple[str, str]] = {}
    lock = threading.Lock()
    progress = [0]

    def work(bi: int, batch: list[dict]):
        client = cfg.make_llm_client()          # key from .env
        try:
            data = client.complete_json(SYSTEM, build_user(batch))
        except Exception:                        # noqa: BLE001
            data = None
        base = bi * args.batch
        for j in range(len(batch)):
            r, why = "?", ""
            if isinstance(data, dict):
                e = data.get(str(j + 1))
                if isinstance(e, dict):
                    r = str(e.get("r", "?")).strip().lower()
                    why = str(e.get("why", ""))[:60]
                    if r not in ("yes", "maybe", "no"):
                        r = "?"
            verdict[base + j] = (r, why)
        with lock:
            progress[0] += 1
            if progress[0] % 25 == 0:
                print(f"  {progress[0]}/{len(batches)} batches", flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(work, bi, b) for bi, b in enumerate(batches)]
        for fut in as_completed(futs):
            fut.result()

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["relevance", "has_pdf", "year", "doi", "title", "why", "model", "run_id"])
        order = {"yes": 0, "maybe": 1, "no": 2, "?": 3}
        idx = sorted(range(len(uniq)), key=lambda k: (order.get(verdict.get(k, ("?", ""))[0], 3),))
        for k in idx:
            it = uniq[k]
            r, why = verdict.get(k, ("?", ""))
            w.writerow([r, it["has_pdf"], it["year"], it["doi"],
                        it["title"][:200].replace("\t", " "), why, args.model, run_id])

    cnt = Counter(v[0] for v in verdict.values())
    yes_nopdf = sum(1 for k in range(len(uniq))
                    if verdict.get(k, ("?",))[0] == "yes" and uniq[k]["has_pdf"] == "no")
    yes_pdf = sum(1 for k in range(len(uniq))
                  if verdict.get(k, ("?",))[0] == "yes" and uniq[k]["has_pdf"] == "yes")
    print(f"\nDONE -> {args.out}")
    print(f"verdicts: {dict(cnt)}")
    print(f"relevant(yes) with PDF (extract now): {yes_pdf}  |  yes without PDF (acquire): {yes_nopdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
