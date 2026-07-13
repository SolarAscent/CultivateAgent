# Extraction Readiness: H031-H033

Status: offline section-routing preflight; not an extraction result and not evidence adjudication.

## Summary

| Metric | Value |
|---|---:|
| Review tasks checked | 3 |
| Ready for operator extraction | 3 |
| Ready with full-text fallback | 0 |
| Partial operator-ready | 0 |
| Not ready / missing | 0 |

## Status Counts

| Status | Count |
|---|---:|
| `ready_for_operator_extraction` | 3 |

## Task Detail

| Review ID | Source | Status | Critical operators ready | Source type | Text chars | Sections | Tables |
|---|---|---|---:|---|---:|---:|---:|
| `H031` | `R045` | `ready_for_operator_extraction` | 3/3 | plain_text | 106911 | 7 | 0 |
| `H032` | `R046` | `ready_for_operator_extraction` | 3/3 | jats_xml | 54032 | 29 | 1 |
| `H033` | `R047` | `ready_for_operator_extraction` | 3/3 | plain_text | 71675 | 8 | 0 |

## Operator Detail

### H031: R045

- Title: Microbial lysates as low-cost serum replacements in cellular agriculture media formulation
- Full text: `data/papers/microbial-lysates-as-low-cost-serum-replacements-in-cellular-agriculture-media-f/fulltext.txt`

| Operator | Status | Context chars | Routed sections | Signal terms | Numeric hits |
|---|---|---:|---|---|---:|
| `context` | `ready` | 66628 | S1, S2, S5, S6 | bovine, cell, cells, muscle, myoblast, satellite | 24 |
| `medium` | `ready` | 66923 | S3, S5, S6 | albumin, basal, dmem, extract, fgf2, formulation, hydrolysate, media, medium, serum | 23 |
| `dose` | `ready` | 28460 | S3 | concentration, doubling, passage, proliferation, viability | 20 |
| `endpoints` | `ready` | 28460 | S3 | differentiation, doubling, myog, myogenic, pax7, proliferation, viability | 20 |
| `findings` | `ready` | 67189 | S1, S2, S3, S4 | alternative, cost, decreased, improved, increased, limitation, serum-free, significant | 42 |

### H032: R046

- Title: Serum-free cultured meat production by using Pichia pastoris-derived recombinant albumin
- Full text: `data/papers/serum-free-cultured-meat-production-by-using-pichia-pastoris-derived-recombinant/fulltext.txt`

| Operator | Status | Context chars | Routed sections | Signal terms | Numeric hits |
|---|---|---:|---|---|---:|
| `context` | `ready` | 25744 | S1, S8.1, S8.2.1, S8.2.2, S8.2.3, S8.3.1, S8.3.2, S8.3.3, S8.3.4, S8.3.5, S8.3.6, S8.3.7, S8.3.8, S8.3.9, S8.3.10, S8.3.11, S8.3.12, S8.4 | bovine, cell, cells, muscle, satellite | 31 |
| `medium` | `ready` | 33027 | S2.1, S2.2, S2.3, S8.1, S8.2.1, S8.2.2, S8.2.3, S8.3.1, S8.3.2, S8.3.3, S8.3.4, S8.3.5, S8.3.6, S8.3.7, S8.3.8, S8.3.9, S8.3.10, S8.3.11, S8.3.12, S8.4 | albumin, basal, dmem, extract, formulation, media, medium, serum, serum-free, supplement | 45 |
| `dose` | `ready` | 33027 | S2.1, S2.2, S2.3, S8.1, S8.2.1, S8.2.2, S8.2.3, S8.3.1, S8.3.2, S8.3.3, S8.3.4, S8.3.5, S8.3.6, S8.3.7, S8.3.8, S8.3.9, S8.3.10, S8.3.11, S8.3.12, S8.4 | cell number, concentration, doubling, mg/ml, ng/ml, passage, proliferation, viability | 45 |
| `endpoints` | `ready` | 33027 | S2.1, S2.2, S2.3, S8.1, S8.2.1, S8.2.2, S8.2.3, S8.3.1, S8.3.2, S8.3.3, S8.3.4, S8.3.5, S8.3.6, S8.3.7, S8.3.8, S8.3.9, S8.3.10, S8.3.11, S8.3.12, S8.4 | cell counting, differentiation, doubling, myod, myog, myogenic, pax7, proliferation, viability | 45 |
| `findings` | `ready` | 22339 | S1, S2.1, S2.2, S2.3, S3, S3.1 | alternative, conclusion, cost, decreased, increased, limitation, serum-free, significant | 19 |

### H033: R047

- Title: Satellite cells sourced from bull calves and dairy cows differs in proliferative and myogenic capacity - Implications for cultivated meat
- Full text: `data/papers/satellite-cells-sourced-from-bull-calves-and-dairy-cows-differs-in-proliferative/fulltext.txt`

| Operator | Status | Context chars | Routed sections | Signal terms | Numeric hits |
|---|---|---:|---|---|---:|
| `context` | `ready` | 15822 | S1, S2, S3 | bovine, cell, cells, muscle, myoblast, satellite | 28 |
| `medium` | `ready` | 51749 | S2, S3, S4, S6, S7 | basal, dmem, fgf2, formulation, media, medium, serum, serum-free, supplement | 40 |
| `dose` | `ready` | 42583 | S2, S4, S6 | cell number, mg/ml, ng/ml, proliferation | 24 |
| `endpoints` | `ready` | 42583 | S2, S4, S6 | cell counting, differentiation, fusion, myog, myogenic, proliferation | 24 |
| `findings` | `ready` | 54822 | S1, S4, S5, S6 | alternative, conclusion, decreased, improved, increased, limitation, serum-free, significant | 12 |
