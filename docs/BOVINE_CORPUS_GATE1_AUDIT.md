# Bovine Corpus Gate 1 Audit

Status: **FAIL**

Numerical coverage and metadata checks apply only to design-included
manifest decisions; deferred records cannot satisfy corpus thresholds.
P1 core/core-context records additionally require
explicit human curation status.

## Metrics

| Metric | Value |
|---|---:|
| peer_reviewed_sources | 39 |
| reviews | 18 |
| primary_papers | 21 |
| bovine_primary | 17 |
| dose_primary | 21 |
| serum_free_bovine_primary | 8 |
| included_rows | 43 |
| p1_core_rows | 18 |
| p1_core_human_verified | 0 |

## Checks

| Check | Result |
|---|---|
| peer_reviewed_range | PASS |
| reviews_min | PASS |
| primary_min | PASS |
| bovine_primary_min | PASS |
| dose_primary_min | PASS |
| serum_free_bovine_primary_min | PASS |
| included_metadata_complete | PASS |
| unique_record_ids | PASS |
| unique_included_dois | PASS |
| p1_core_human_curated | FAIL |

## Issues

- `R015` [human_curation_pending]: needs_full_text_check
- `R016` [human_curation_pending]: needs_full_text_check
- `R017` [human_curation_pending]: fulltext_ingested_for_review_packet
- `R018` [human_curation_pending]: fulltext_ingested_for_review_packet
- `R019` [human_curation_pending]: needs_full_text_check
- `R020` [human_curation_pending]: needs_full_text_check
- `R021` [human_curation_pending]: fulltext_ingested_for_review_packet
- `R022` [human_curation_pending]: needs_full_text_check
- `R023` [human_curation_pending]: fulltext_ingested_for_review_packet
- `R024` [human_curation_pending]: needs_institutional_or_human_full_text
- `R029` [human_curation_pending]: needs_full_text_check
- `R045` [human_curation_pending]: fulltext_ingested_for_review_packet
- `R046` [human_curation_pending]: fulltext_ingested_for_review_packet
- `R047` [human_curation_pending]: fulltext_ingested_for_review_packet
- `R048` [human_curation_pending]: fulltext_ingested_for_review_packet
- `R049` [human_curation_pending]: fulltext_ingested_for_review_packet
- `R050` [human_curation_pending]: fulltext_ingested_for_review_packet
- `R051` [human_curation_pending]: fulltext_ingested_for_review_packet
