# Extraction Readiness: H034-H037

Status: offline section-routing preflight; not an extraction result and not evidence adjudication.

## Summary

| Metric | Value |
|---|---:|
| Review tasks checked | 4 |
| Ready for operator extraction | 4 |
| Ready with full-text fallback | 0 |
| Partial operator-ready | 0 |
| Not ready / missing | 0 |

## Status Counts

| Status | Count |
|---|---:|
| `ready_for_operator_extraction` | 4 |

## Task Detail

| Review ID | Source | Status | Critical operators ready | Source type | Text chars | Sections | Tables |
|---|---|---|---:|---|---:|---:|---:|
| `H034` | `R048` | `ready_for_operator_extraction` | 3/3 | plain_text | 41820 | 8 | 0 |
| `H035` | `R049` | `ready_for_operator_extraction` | 3/3 | plain_text | 38683 | 8 | 0 |
| `H036` | `R050` | `ready_for_operator_extraction` | 3/3 | plain_text | 51511 | 7 | 0 |
| `H037` | `R051` | `ready_for_operator_extraction` | 3/3 | plain_text | 57165 | 10 | 0 |

## Operator Detail

### H034: R048

- Title: Microbiota-Derived Postbiotics Enhance the Proliferative Effects of Growth Factors on Satellite Cells in Cultivated Meat Applications
- Full text: `data/papers/microbiota-derived-postbiotics-enhance-the-proliferative-effects-of-growth-facto/fulltext.txt`

| Operator | Status | Context chars | Routed sections | Signal terms | Numeric hits |
|---|---|---:|---|---|---:|
| `context` | `ready` | 15030 | S1, S3, S4 | bovine, cell, cells, muscle, satellite | 13 |
| `medium` | `ready` | 16777 | S2, S4, S5, S6 | dmem, fgf2, formulation, media, medium, serum, serum-free, supplement | 35 |
| `dose` | `ready` | 16777 | S2, S4, S5, S6 | concentration, dose, mg/ml, ng/ml, passage, proliferation, viability | 35 |
| `endpoints` | `ready` | 16777 | S2, S4, S5, S6 | differentiation, myod, myog, myogenic, pax7, proliferation, viability | 35 |
| `findings` | `ready` | 31070 | S1, S2, S3, S5, S6, S7 | alternative, conclusion, cost, increased, limitation, serum-free | 25 |

### H035: R049

- Title: Discovery of Novel Stimulators of Pax7 and/or MyoD: Enhancing the Efficacy of Cultured Meat Production through Culture Media Enrichment
- Full text: `data/papers/discovery-of-novel-stimulators-of-pax7-andor-myod-enhancing-the-efficacy-of-cult/fulltext.txt`

| Operator | Status | Context chars | Routed sections | Signal terms | Numeric hits |
|---|---|---:|---|---|---:|
| `context` | `ready` | 11150 | S1, S2, S4 | bovine, cell, cells, muscle, myoblast, satellite | 10 |
| `medium` | `ready` | 10967 | S4, S5 | medium, serum, supplement | 12 |
| `dose` | `ready` | 15637 | S5, S7 | concentration, dose, proliferation, viability | 2 |
| `endpoints` | `ready` | 5509 | S5 | differentiation, myod, myog, myogenic, pax7, proliferation, viability | 2 |
| `findings` | `ready` | 21480 | S1, S2, S5, S6 | alternative, conclusion, cost, decreased, increased, serum-free, significant | 3 |

### H036: R050

- Title: Effect of Serum and Oxygen on the In Vitro Culture of Hanwoo Korean Native Cattle-Derived Skeletal Myogenic Cells Used in Cellular Agriculture
- Full text: `data/papers/effect-of-serum-and-oxygen-on-the-in-vitro-culture-of-hanwoo-korean-native-cattl/fulltext.txt`

| Operator | Status | Context chars | Routed sections | Signal terms | Numeric hits |
|---|---|---:|---|---|---:|
| `context` | `ready` | 14562 | S1, S2, S3 | bovine, cell, cells, muscle, myoblast | 13 |
| `medium` | `ready` | 27586 | S3, S4 | basal, dmem, extract, media, medium, serum, serum-free, supplement | 32 |
| `dose` | `ready` | 37643 | S3, S4, S6 | cell number, concentration, ng/ml, passage, proliferation | 39 |
| `endpoints` | `ready` | 27586 | S3, S4 | cell counting, differentiation, fusion, myod, myog, myogenic, pax7, proliferation | 32 |
| `findings` | `ready` | 30876 | S1, S2, S4, S5 | alternative, conclusion, cost, decreased, improved, increased, serum-free | 19 |

### H037: R051

- Title: The Role of Insulin in the Proliferation and Differentiation of Bovine Muscle Satellite (Stem) Cells for Cultured Meat Production
- Full text: `data/papers/the-role-of-insulin-in-the-proliferation-and-differentiation-of-bovine-muscle-sa/fulltext.txt`

| Operator | Status | Context chars | Routed sections | Signal terms | Numeric hits |
|---|---|---:|---|---|---:|
| `context` | `ready` | 16729 | S1, S2, S6, S8 | bovine, cell, cells, muscle, satellite | 6 |
| `medium` | `ready` | 29713 | S3, S4, S6, S7, S8 | dmem, media, medium, serum, serum-free, supplement | 29 |
| `dose` | `ready` | 49185 | S3, S4, S6, S7, S8, S9 | cell number, concentration, ng/ml, passage, proliferation, viability | 30 |
| `endpoints` | `ready` | 29713 | S3, S4, S6, S7, S8 | differentiation, myod, myog, myogenic, pax7, proliferation, viability | 29 |
| `findings` | `ready` | 24774 | S1, S2, S3, S4, S5, S7 | alternative, cost, decreased, increased, serum-free, significant | 23 |
