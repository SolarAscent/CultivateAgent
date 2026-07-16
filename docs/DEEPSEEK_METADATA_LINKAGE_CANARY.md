# DeepSeek Metadata-Linkage Capability Canary

Decision: **FAIL**

## Fixed Protocol

- Model: `deepseek-v4-flash` (thinking disabled, temperature 0)
- Frozen source-authentic items: 12 (6 cross-linked)
- Repeats: 3; schema permits item/field pointers only
- Hard request cap: 6
- Hard total-token cap: 15000
- Gate: minimum repeat recall >= 0.95, minimum repeat precision >= 0.75, selection Jaccard >= 0.95, and every response schema-valid

## Result

- Valid requests: 6/6
- Repeat recall: 0.5000, 0.5000, 0.5000
- Repeat precision: 1.0000, 1.0000, 1.0000
- Candidate counts: [3, 3, 3] (population SD 0.0000)
- Pairwise selection Jaccard: 1.0000
- Reported tokens: 11934
- Schema/runtime issues: 0
- False-negative pointers: M002, M006, M008
- False-positive pointers: none
- Prior invalid implementation attempts: 1; token usage unknown and excluded from the valid-run metrics

## Routing Decision

Do not delegate metadata-linkage screening to this model/prompt.
DeepSeek is not authorized to return replacement titles, abstracts, DOI/year values, scientific inclusion decisions, or evidence judgments.
