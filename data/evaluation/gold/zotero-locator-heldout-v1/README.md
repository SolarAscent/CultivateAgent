# Zotero Locator Held-out v1

**Status: FROZEN_EXPOSED_FAIL — retained for audit, not future independent tuning.**

This benchmark provides a new source-disjoint silver set for the DeepSeek
quantitative-block localization gate. It was frozen after the earlier R017,
R018, R045, and R047 runs and does not contain Q005/Q009 or any source used in
those runs.

## Sources

- Z001: bovine satellite-cell postbiotics and growth-factor supplementation.
- Z002: Hanwoo satellite-cell medium additives targeting Pax7/MyoD.
- Z003: Hanwoo skeletal myogenic cells under FBS, oxygen, and basal-medium
  conditions.
- Z004: bovine muscle satellite cells under insulin, growth-factor, FBS, and
  serum-free conditions.

All four local Zotero PDFs are absent from the canonical bovine corpus by DOI.
The generator verifies exact DOI text, normalized title, a CC BY statement, PDF
hash agreement across duplicate Zotero attachments, and the prior
`relevance=yes; has_pdf=yes` screen result before copying an ignored local PDF.
The committed `verified_sources.tsv` contains only repository-relative source
pointers and hashes.

## Silver Locators

The existing `pdf-stat-block-v1` selector produced 13 source-hash-bound
locators: Z001 (2), Z002 (2), Z003 (3), and Z004 (6). Source inspection confirms
that each block contains a medium/additive/serum-condition quantitative result
or figure caption. The context-aware shadow prefilter covers all 13 locators in
a 19-block candidate pool.

These are deterministic silver candidates, not human-adjudicated tier-1
effects. They may measure high-recall localization, but cannot approve a number,
effect size, evidence tier, biological claim, or wet-lab variable.

## Reproduce

```bash
python scripts/prepare_zotero_locator_holdout.py \
  --zotero-csv /path/to/CulturedMeat_fullpapers.csv
```

The generator creates a temporary blank worksheet, validates every source hash
and locator through the existing quantitative-review validator, then removes
the worksheet because this benchmark is not a human-review packet.

The first unchanged-prompt run is recorded under
`data/evaluation/shadow/deepseek-zotero-heldout-v1/` and failed recall at 10/13.
Any later prompt change requires a different held-out source set; do not tune on
the misses and reuse this benchmark as independent evidence.
