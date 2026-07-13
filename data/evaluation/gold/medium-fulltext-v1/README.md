# Medium Full-Text Gold v1

Status: blank dual-review worksheet; **not ready for model evaluation**.

This benchmark preparation set contains four independent bovine medium papers:

- R015: Beefy-9/B8 serum-free expansion anchor.
- R016: chemically defined primary bovine satellite-cell expansion medium.
- R017: commercial serum-free primary bovine myoblast benchmark.
- R023: bovine satellite-cell media-composition/proliferation study.

The manifest stores official title/year/DOI/URL, repository-relative local
full-text path, full-text SHA-256, and A-M schema SHA-256. Full text remains
local and is not committed.

`review.tsv` is the controlled master with one row for every paper x A-M field
cell. Reviewers must not edit it directly. Give each reviewer a separate fresh
instance of `reviewer_blank.tsv`; it contains only one reviewer's columns and
cannot expose the other review. After both return, the coordinator merges them
into the master, then an adjudicator fills the final columns.
Allowed decisions are:

- `reported`: `value_json`, exact source quote, location, reviewer, and date are
  required. Scalars must be JSON strings/numbers; list fields must be JSON
  arrays.
- `not_reported`: the full text does not report the field.
- `not_applicable`: the field does not apply to the paper.
- `uncertain`: evidence is ambiguous; explain in `notes` and optionally retain a
  locator/quote.
- `defer`: external expertise or a better source artifact is required.

Do not let reviewer 2 see reviewer 1 values before independent extraction. Do
not use AI-generated values as either reviewer. AI may merge files, validate
structure, and check quote grounding only.

Merge the two independently completed reviewer files:

```bash
python scripts/prepare_medium_gold_review.py merge \
  --master data/evaluation/gold/medium-fulltext-v1/review.tsv \
  --reviewer-1 /path/to/reviewer_1.tsv \
  --reviewer-2 /path/to/reviewer_2.tsv \
  --out data/evaluation/gold/medium-fulltext-v1/review.tsv
```

Validate at any time:

```bash
python scripts/prepare_medium_gold_review.py validate \
  --manifest data/evaluation/gold/medium-fulltext-v1/manifest.json \
  --worksheet data/evaluation/gold/medium-fulltext-v1/review.tsv \
  --out docs/FULLTEXT_GOLD_VALIDATION_MEDIUM_V1.md
```

Add `--require-ready` only when checking the final adjudicated benchmark. The
command then exits non-zero until all 380 rows are adjudicated without issues.

The optional `passages` command creates local field-aware lexical locators and
does not edit the master or reviewer files. Generated snippets are not committed
without a separate quotation-rights review; no-hit fields still require manual
source inspection.
