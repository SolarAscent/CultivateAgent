# Human Review Packet: H031-H033

Status: candidate passage locators for human adjudication; not an AI decision.

## Summary

| Metric | Value |
|---|---:|
| Review tasks | 3 |
| Tasks with local full text | 3 |
| Tasks needing source/fulltext action | 0 |

## How To Use

For each task, open the listed local `fulltext.txt` and inspect the character ranges.
The packet avoids embedding long source excerpts; record the final human decision in
`data/literature/bovine_human_review_queue.tsv` and transfer adjudicated facts to
`data/literature/bovine_evidence_table.tsv`.

## H031: Microbial-lysate serum replacement

- Status: `ready_for_human_review`
- Source record: `R045`
- Manifest title: Microbial lysates as low-cost serum replacements in cellular agriculture media formulation
- Human question: Does VN40 support sustained serum-free iBSC expansion at a traceable dose, and which findings cannot be transferred from immortalized to primary bovine cells?
- Suggested action: Verify formulation, dose, passage duration, comparator, phenotype and differentiation results; mark immortalized-cell evidence as indirect for primary-cell claims.
- Local paper: `microbial-lysates-as-low-cost-serum-replacements-in-cellular-agriculture-media-f`
- Full text: `data/papers/microbial-lysates-as-low-cost-serum-replacements-in-cellular-agriculture-media-f/fulltext.txt`
- Source SHA-256: `e2ba17d462c8feff7345abcbc7516860d3dc9ae9204c46791791d8bfa293c14d`
- Query terms: microbial-lysate, serum, replacement, lysate_identity, dose, passage_count, proliferation, myogenicity, cell_line_limit, vn40, support, sustained, serum-free, ibsc, expansion, traceable, findings, cannot, transferred, immortalized, primary, bovine, cells, verify

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 20.0 | `750-1899` | b8, bovine, cells, immortalized, low-cost, lysate, lysates, media, microbial, natriegens, phenotype, replacements |
| 2 | 15.5 | `46250-47903` | cells, differentiation, formulation, lysate, media, myogenicity, passage, phenotype, proliferation, serum-free, vn40 |
| 3 | 14.5 | `8457-9648` | bovine, cells, lysate, lysates, media, microbial, natriegens, phenotype, replacements, serum, support, vibrio |
| 4 | 14.0 | `37509-40657` | b8, cells, ibsc, lysate, media, natriegens, passage, proliferation, serum-free, vn40 |
| 5 | 12.5 | `16740-19255` | b8, cells, ibsc, lysate, lysates, media, microbial, proliferation, serum-free |

## H032: Pichia-derived recombinant albumin

- Status: `ready_for_human_review`
- Source record: `R046`
- Manifest title: Serum-free cultured meat production by using Pichia pastoris-derived recombinant albumin
- Human question: Which bovine-versus-porcine recombinant albumin doses support primary bMuSC proliferation and preserve differentiation, and are cost claims reproducible?
- Suggested action: Extract exact formulations, albumin doses, controls, proliferation and identity endpoints, and the assumptions behind reported cost comparisons.
- Local paper: `R046`
- Full text: `data/papers/serum-free-cultured-meat-production-by-using-pichia-pastoris-derived-recombinant/fulltext.txt`
- Source SHA-256: `b394cdf7fd51b78cebb22c2ddaecf899d1ff0f3052799a45e9b6acb7c9f66461`
- Query terms: pichia-derived, recombinant, albumin, albumin_species, dose_range, proliferation, pax7, differentiation, cost, bovine-versus-porcine, doses, support, primary, bmusc, preserve, claims, reproducible, extract, exact, formulations, controls, identity, endpoints, assumptions

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 17.0 | `15252-17814` | bmusc, bovine, cost, cultured, differentiation, formation, meat, medium, myotube, pichia, production, recombinant |
| 2 | 16.5 | `90-1295` | albumin, bovine, cultured, differentiation, formation, meat, myotube, pax7, pichia, porcine, production, proliferation |
| 3 | 12.5 | `1310-2434` | bovine, cost, cultured, differentiation, meat, medium, production, proliferation, serum-free, support |
| 4 | 12.0 | `7444-9898` | albumin, bmusc, bovine, cultured, differentiation, medium, myotube, recombinant |
| 5 | 12.0 | `12416-15071` | albumin, cultured, identity, medium, pax7, proliferation, recombinant, support |

## H033: Donor variance under serum-free culture

- Status: `ready_for_human_review`
- Source record: `R047`
- Manifest title: Satellite cells sourced from bull calves and dairy cows differs in proliferative and myogenic capacity - Implications for cultivated meat
- Human question: How strongly do bull-calf and dairy-cow cells differ, is the in-house serum-free formulation disclosed, and what blocking or donor replication follows from the data?
- Suggested action: Record donor counts, biological replicate structure, serum-free formulation availability, effect directions and variance; do not treat an undisclosed formulation as an actionable medium.
- Local paper: `R047`
- Full text: `data/papers/satellite-cells-sourced-from-bull-calves-and-dairy-cows-differs-in-proliferative/fulltext.txt`
- Source SHA-256: `948d543f8b4fb2e9b10dd1b933206559637397a785eff73129d70309336d83b5`
- Query terms: donor, variance, under, serum-free, culture, donor_age, donor_type, serum_free_formula, proliferation, differentiation, strongly, bull-calf, dairy-cow, cells, differ, in-house, formulation, disclosed, blocking, replication, follows, data, counts, biological

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 32.0 | `0-5185` | 10%, availability, biological, bull, calves, capacity, cells, cows, cultivated, culture, dairy, data |
| 2 | 25.0 | `5186-13474` | 10%, bull, calves, capacity, cells, cows, cultivated, culture, dairy, density, differentiation, donor |
| 3 | 23.0 | `13475-21847` | 10%, biological, blocking, bull, capacity, cells, dairy, data, density, differentiation, donor, fbs |
| 4 | 23.0 | `40007-49315` | biological, bull, capacity, cells, cultivated, culture, dairy, data, differentiation, donor, effect, in-house |
| 5 | 20.5 | `21848-26848` | 10%, biological, bull, cells, dairy, data, differ, differentiation, donor, effect, fbs, myogenic |
