# Visual-Result Page Held-out v1

**Status: FROZEN_UNEXPOSED.**

This source-disjoint PDF set was frozen before the first
`visual-result-page-pointer-v1` API run. It contains all 48 readable pages from
R016, R021, and R022. Six strict positive pages come from R021; R016 and R022
remain unlabeled shadow sources and are not precision negatives.

The deterministic selector requires an existing field-aware PDF block to carry
figure-caption, measured-outcome, medium-comparison, sample-size, and dispersion
signals. Every source is bound to the canonical DOI plus the audited PDF path,
page count, and SHA-256. Positive pages retain block/page hashes only; no source
text or numeric value is committed.

This silver can measure high-recall page localization and total page reduction.
It cannot approve a source number, effect, evidence tier, biological claim, or
wet-lab variable.

Rebuild with:

```bash
python scripts/prepare_visual_page_heldout.py \
  --out data/evaluation/gold/visual-page-heldout-v1/manifest.json
```
