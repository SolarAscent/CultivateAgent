# P1 Bovine PDF Table Off-Ramp Audit

**Status: FAIL**

The table-first off-ramp requires at least 10 gold-verified tier-1 effects. This audit only discovers candidate source cells; it never promotes a cell to tier-1.

## Result

- P1 primary records: 14
- PDFs audited: 11; unavailable/ambiguous: 3
- Pages: 202
- Default line-strategy tables/cells: 22 / 195
- Default line-strategy statistical cells: 0
- Text-layout regions/cells: 187 / 72326
- Text-layout statistical locator candidates: 140
- Gold-verified tier-1 effects produced by this audit: 0

## Interpretation

PyMuPDF's default strategy detects vector-line tables. Its zero statistical-cell yield means the current PDFs do not expose an immediately usable structured mean/SD-or-SEM/n table path. The text strategy is deliberately reported separately: it reconstructs page-wide layout grids and its hits include prose and figure captions, so they are locator candidates rather than table cells or effects.
PyMuPDF officially recommends `strategy="text"` when borderless tables are missed ([documentation](https://pymupdf.readthedocs.io/en/latest/faq/index.html#table-extraction)); the separation here is an empirical safeguard for this corpus, not a rejection of that strategy in general.

The result triggers the planned off-ramp from structured tables to a bounded caption/prose and figure-data pilot. It does not justify scaling text extraction, and it does not establish that all 140 locator candidates are relevant.
R023 and R046 have already been audited through JATS; R024 remains the only P1 primary record in this set without either audited JATS or a local PDF.

## Per-Record Counts

| record | PDF | line tables | line stat cells | text locator candidates | classification |
|---|---:|---:|---:|---:|---|
| R015 | audited | 0 | 0 | 5 | layout_text_candidates_only |
| R016 | audited | 0 | 0 | 2 | layout_text_candidates_only |
| R017 | audited | 1 | 0 | 18 | layout_text_candidates_only |
| R018 | audited | 10 | 0 | 20 | layout_text_candidates_only |
| R019 | audited | 1 | 0 | 0 | no_stat_candidates |
| R020 | audited | 2 | 0 | 21 | layout_text_candidates_only |
| R021 | audited | 0 | 0 | 28 | layout_text_candidates_only |
| R022 | audited | 1 | 0 | 3 | layout_text_candidates_only |
| R023 | missing | 0 | 0 | 0 | not_audited |
| R024 | missing | 0 | 0 | 0 | not_audited |
| R029 | audited | 2 | 0 | 24 | layout_text_candidates_only |
| R045 | audited | 5 | 0 | 11 | layout_text_candidates_only |
| R046 | missing | 0 | 0 | 0 | not_audited |
| R047 | audited | 0 | 0 | 8 | layout_text_candidates_only |

## Reproduce

```bash
python scripts/audit_bovine_pdf_tables.py --max-items 14
```

The TSV report binds each available PDF to SHA-256. Extracted page text and table content remain local and are not committed.
