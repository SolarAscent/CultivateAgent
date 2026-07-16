# Zotero Acquisition Queue Deduplication

Status: **PASS**; deterministic partition against the canonical corpus.

The original DeepSeek-generated acquisition list is retained unchanged. DOI matches are
automatic exclusions. Title-only exclusion is allowed only when the candidate DOI is
missing; equal titles with different non-empty DOIs are isolated for human review.

## Counts

| Output | Rows |
|---|---:|
| Source queue | 236 |
| Actionable acquisition | 212 |
| Deterministic exclusions | 23 |
| Human-review conflicts | 1 |

## Partition Reasons

| Reason | Rows |
|---|---:|
| `actionable` | 212 |
| `corpus_doi_duplicate` | 22 |
| `queue_title_duplicate_missing_doi` | 1 |
| `title_match_different_doi` | 1 |

## Integrity

- Source SHA-256: `64930cd0cad2a79fb0ea4e943e5a1f77d106e4269b3b64dbaff681ed0a3de93c`
- Corpus SHA-256: `24663e28596fcb49796d3d0c3a738610da961c17c582badbf851114af7092e1a`
- Actionable output: `data/literature/zotero_acquire_actionable.tsv`; SHA-256 `d78eb3253755ebd4b9c0b0e2bab209236e8f376bcafb1044c2664e56972257ac`
- Exclusion audit: `data/literature/zotero_acquire_exclusions.tsv`; SHA-256 `d6edb26f7c8418ef3b2975000406147fa5af022133b20743f41b3de64d018fdc`
- Conflict audit: `data/literature/zotero_acquire_conflicts.tsv`; SHA-256 `379117fc9902a9f96b3ac387ed6bbf6182702f04696345cf8d811ca6a8bfeb8b`
- Every source row appears in exactly one derived category.
- Actionable DOI overlap with the canonical corpus is zero.
- Actionable DOI/title identities are unique.
- Conflict rows are not authorized for acquisition until reviewed.
