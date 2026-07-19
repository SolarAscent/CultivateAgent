# Visual-Result Page Silver v1

**Status: FROZEN_EXPOSED_PASS_FOR_BOUNDED_SHADOW.**

This source-disjoint silver set covers R015, R019, and R020. The deterministic
builder verifies local JATS and PDF hashes, selects JATS figure captions that
contain outcome, comparison, dispersion, and sample-size context, and maps them
to PDF pages by token overlap. It stores figure/page pointers and hashes only.

The set contains six positive pages among 40 readable page excerpts. One
otherwise qualifying R015 figure was excluded because its PDF text match was
ambiguous. Silver positives are not human-adjudicated effects and cannot approve
a number, evidence tier, biological claim, or wet-lab variable.

Rebuild with:

```bash
python scripts/prepare_visual_page_silver.py \
  --out data/evaluation/gold/visual-page-silver-v1/manifest.json
```
