# Medium Gold Pilot v1

Status: blank two-paper calibration pilot; **not ready**.

This pilot uses R015 and R016 and 28 high-risk fields (56 paper x field cells)
covering bibliographic identity, species/cell/stage/passage, medium composition,
endpoints, quantitative data, findings, and limitations. It exists to calibrate
the coding guide before two reviewers independently annotate all 380 cells in
`medium-fulltext-v1`.

Use `reviewer_blank.tsv` as the immutable source for two isolated reviewer
files. Reviewers must not see each other's work. After both finish, merge them
into `review.tsv`, inspect agreement, adjudicate all rows, and validate.

Progression criteria:

- Reviewer 1 completed: 56/56.
- Reviewer 2 completed: 56/56.
- Structural/typing/quote-grounding issues: 0.
- Decision Cohen kappa: at least 0.70 when estimable. If both reviewers use only
  one decision class and kappa is undefined, exact agreement must be 1.0 and the
  methods lead must document the prevalence limitation.
- Every disagreement and uncertain/deferred row is explicitly adjudicated.
- Final adjudication: 56/56; validator status READY.

Reported-value exact agreement is diagnostic and must be reviewed field by
field; list order is canonicalized and does not create a false disagreement.
No unsupported universal threshold is imposed. If decision kappa is below
0.70 or coding instructions repeatedly disagree, revise the guide and create a
new pilot version instead of overwriting v1.

Merge and validate using the commands documented in
`medium-fulltext-v1/README.md`, substituting this pilot directory.

Generate local lexical passage locators for one paper/field without changing any
worksheet value:

```bash
python scripts/prepare_medium_gold_review.py passages \
  --manifest data/evaluation/gold/medium-pilot-v1/manifest.json \
  --record R015 \
  --field E.growth_factors \
  --field J.key_numeric_results \
  --out /tmp/medium-pilot-r015-locators.md
```

Locators are search aids, not evidence decisions. A missing lexical hit never
means `not_reported`; the reviewer must still inspect the source.
