# DeepSeek Page Shadow: R053-R055

Status: **HOLD; stable pointers, insufficient incremental utility for production routing**.

## Boundary

- Sources: R053, R054, and R055; none participated in either DeepSeek page gold set.
- DeepSeek output schema permits page IDs only. The committed JSON contains source/page/hash
  pointers and aggregate counts, not excerpts, transcribed numbers, or evidence decisions.
- R052 and R056 are absent because no hash-bound local PDF page source was available.
- Pointer artifact: `data/evaluation/shadow/deepseek-page-R053-R055-v1/manifest.json`.

## Live Shadow Result

| Metric | Result |
|---|---:|
| Source PDFs | 3 |
| Input pages | 55 |
| Unanimously selected pages | 47 |
| Page reduction | 14.55% |
| Input excerpt characters | 63,292 |
| Selected excerpt characters | 55,042 |
| Excerpt reduction | 13.03% |
| Repeated requests | 18/18 valid |
| Selection consistency | 1.000 |
| DeepSeek API tokens | 52,986 |

All three repeats were identical. A checkpoint-only replay made no API calls and reproduced
the pointer artifact.

## Deterministic Comparator

A no-model signal filter selected pages containing the same predeclared medium, outcome,
dispersion, sample-size, or figure-caption signals used to construct page summaries.

| Dataset | Gold-page recall | Page reduction |
|---|---:|---:|
| quantitative-pilot-v1 | 1.000 (20/20) | 11.34% |
| zotero-locator-heldout-v1 | 1.000 (13/13) | 0.00% |
| R053-R055 unlabeled shadow | Not measurable | 5.45% |

DeepSeek therefore adds about 7.58 percentage points of excerpt reduction over the
deterministic shadow baseline. That is a real but small saving. Because R053-R055 have no
independent page-level gold, this run cannot establish the recall of the eight omitted pages.

## Decision

Do not route the 47 pages automatically into evidence extraction or claim production token
savings. Retain the JSON as an audit artifact and the exporter as a bounded evaluation tool.
The next deployment test must either demonstrate materially stronger reduction on a new,
independently reviewed page set or use a task where deterministic validation cannot already
capture most of the value.
