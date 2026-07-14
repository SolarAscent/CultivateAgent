# Quantitative Pointer Pilot v1

**Status: HOLD — wait for two independent human reviewers.**

This benchmark extends the existing A-M gold workflow through the linked
`J.key_numeric_results`, `J.experimental_comparison_groups`, and
`J.sample_size_or_replicate_info` fields. It does not create a competing gold
standard and contains no transcribed source values.

## Scope

- 20 deterministic PDF block locators: R017 (4), R018 (8), R045 (4), R047 (4).
- Each locator is bound to the canonical corpus identity, PDF SHA-256, page,
  block index, bounding box, and normalized block-text SHA-256.
- `reviewer_blank.tsv` contains role/pointer fields only. There is deliberately
  no numeric-value output field for an LLM.
- Local review crops and working sheets remain ignored under
  `data/evaluation/reviews/quantitative-pilot-v1/`.

## Human Review (start only when reviewer A and reviewer B are available)

1. Give each reviewer only their own working TSV and the matching local crops.
2. Inspect the crop, then verify the original PDF page before deciding.
3. Record treatment/control labels and source pointers for effect, means,
   SD/SEM/SE, and exact per-group or shared `n`. Do not type source numbers into
   the worksheet.
4. Use `tier1_ready` only when both means, both dispersions, exact sample size,
   and biological or mixed replication belong to the same comparison.
5. Use `tier2_only` only when a point effect is recoverable but variance is not;
   state the missing requirement in `notes`.
6. Use `reject` for an irrelevant locator and `not_recoverable` when the required
   values cannot be resolved. Both require notes.
7. Do not inspect the other reviewer's sheet before both reviews are complete.

Working files already prepared on the owner machine:

```text
data/evaluation/reviews/quantitative-pilot-v1/reviewer_A.tsv
data/evaluation/reviews/quantitative-pilot-v1/reviewer_B.tsv
data/evaluation/reviews/quantitative-pilot-v1/crops/
```

## Commands

```bash
python scripts/prepare_quantitative_review.py validate \
  --reviewer data/evaluation/reviews/quantitative-pilot-v1/reviewer_A.tsv
python scripts/prepare_quantitative_review.py validate \
  --reviewer data/evaluation/reviews/quantitative-pilot-v1/reviewer_B.tsv
python scripts/prepare_quantitative_review.py compare \
  --reviewer-a data/evaluation/reviews/quantitative-pilot-v1/reviewer_A.tsv \
  --reviewer-b data/evaluation/reviews/quantitative-pilot-v1/reviewer_B.tsv \
  --out docs/QUANTITATIVE_REVIEW_PILOT_STATUS.md
```

The pilot gate requires zero validation issues, both reviewers complete,
decision kappa at least 0.80 (or exact agreement 1.0 when kappa is undefined),
and at least 10 independently agreed `tier1_ready` locators. Passing means
"ready for conflict adjudication and deterministic value resolution," not
wet-lab approval.
