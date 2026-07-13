# Human Review Packet: H001-H016

Status: candidate passage locators for human adjudication; not an AI decision.

## Summary

| Metric | Value |
|---|---:|
| Review tasks | 16 |
| Tasks with local full text | 14 |
| Tasks needing source/fulltext action | 2 |

## How To Use

For each task, open the listed local `fulltext.txt` and inspect the character ranges.
The packet avoids embedding long source excerpts; record the final human decision in
`data/literature/bovine_human_review_queue.tsv` and transfer adjudicated facts to
`data/literature/bovine_evidence_table.tsv`.

## H001: Beefy-9 expansion benchmark

- Status: `ready_for_human_review`
- Source record: `R015`
- Manifest title: Simple and effective serum-free medium for sustained expansion of bovine satellite cells for cell cultured meat
- Human question: Does the full paper support using Beefy-9/B8 plus recombinant albumin as the positive serum-free bovine expansion anchor, and what exact doubling-time/passaging claims should be recorded?
- Suggested action: Extract exact formulation, dose levels, passage counts, doubling times, and myogenic marker results.
- Local paper: `simple-and-effective-serum-free-medium-for-sustained-expansion-of-bovine-satelli`
- Full text: `data/papers/simple-and-effective-serum-free-medium-for-sustained-expansion-of-bovine-satelli/fulltext.txt`
- Source SHA-256: `2caba0ae328473d43a17c330c14d467aef763c2877a74b0f465d42c6cc8831ad`
- Query terms: beefy-9, expansion, benchmark, proliferation_endpoint, doubling_time, passages, full, support, beefy-9/b8, plus, recombinant, albumin, positive, serum-free, bovine, anchor, exact, doubling-time/passaging, claims, recorded, extract, formulation, dose, levels

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 17.0 | `4928-5973` | albumin, beefy-9, bovine, cells, cultured, effective, expansion, formulation, meat, recombinant, reduction, satellite |
| 2 | 16.5 | `7454-10419` | albumin, b8, beefy-9, bovine, cell, cost, effective, full, proliferation, recombinant, reduction, serum-free |
| 3 | 15.5 | `584-1730` | albumin, b8, beefy-9, bovine, cell, cells, cultured, expansion, meat, passages, recombinant, satellite |
| 4 | 15.0 | `25279-27361` | albumin, b8, beefy-9, cell, cells, cultured, doubling, passages, serum-free, time, times |
| 5 | 14.5 | `3965-4926` | b8, bovine, cell, cost, cultured, effective, expansion, meat, medium, satellite, serum-free, simple |

## H002: FGF2 reduction in Beefy-9

- Status: `ready_for_human_review`
- Source record: `R015`
- Manifest title: Simple and effective serum-free medium for sustained expansion of bovine satellite cells for cell cultured meat
- Human question: What FGF2 concentrations were tested, which concentrations preserved short-term and long-term growth, and where did morphology suffer?
- Suggested action: Record exact tested FGF2 range and classify safe/reduced/removal levels.
- Local paper: `simple-and-effective-serum-free-medium-for-sustained-expansion-of-bovine-satelli`
- Full text: `data/papers/simple-and-effective-serum-free-medium-for-sustained-expansion-of-bovine-satelli/fulltext.txt`
- Source SHA-256: `2caba0ae328473d43a17c330c14d467aef763c2877a74b0f465d42c6cc8831ad`
- Query terms: fgf2, reduction, beefy-9, fgf2_dose_range, growth_effect, morphology, concentrations, were, tested, preserved, short-term, long-term, growth, suffer, exact, range, classify, safe/reduced/removal, levels., simple, effective, serum-free, medium, sustained

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 22.5 | `7454-10419` | albumin, b8, beefy-9, bovine, cell, concentrations, cost, effective, growth, morphology, proliferation, range |
| 2 | 19.5 | `4928-5973` | albumin, beefy-9, bovine, cells, concentrations, cultured, effective, expansion, growth, long-term, meat, recombinant |
| 3 | 17.0 | `584-1730` | albumin, b8, beefy-9, bovine, cell, cells, cultured, expansion, growth, long-term, meat, recombinant |
| 4 | 17.0 | `19816-21904` | b8, beefy-9, cell, cells, concentrations, cultured, expansion, growth, long-term, morphology, proliferation, reduction |
| 5 | 15.5 | `3965-4926` | b8, bovine, cell, cost, cultured, effective, expansion, growth, meat, medium, satellite, serum-free |

## H003: Albumin dose and cost tradeoff

- Status: `ready_for_human_review`
- Source record: `R015`
- Manifest title: Simple and effective serum-free medium for sustained expansion of bovine satellite cells for cell cultured meat
- Human question: Which recombinant albumin concentration and source were used in Beefy-9/Beefy-9+, and how did cost/performance change?
- Suggested action: Extract albumin source, g/L or mg/mL, and cost-performance notes.
- Local paper: `simple-and-effective-serum-free-medium-for-sustained-expansion-of-bovine-satelli`
- Full text: `data/papers/simple-and-effective-serum-free-medium-for-sustained-expansion-of-bovine-satelli/fulltext.txt`
- Source SHA-256: `2caba0ae328473d43a17c330c14d467aef763c2877a74b0f465d42c6cc8831ad`
- Query terms: albumin, dose, cost, tradeoff, albumin_concentration, albumin_type, recombinant, concentration, source, were, beefy-9/beefy-9+, cost/performance, change, extract, g/l, mg/ml, cost-performance, notes., simple, effective, serum-free, medium, sustained, expansion

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 16.5 | `7454-10419` | albumin, b8, beefy-9, bovine, cell, cost, effective, proliferation, recombinant, reduction, serum-free, were |
| 2 | 15.5 | `4928-5973` | albumin, beefy-9, bovine, cells, cultured, effective, expansion, meat, recombinant, reduction, satellite, serum-free |
| 3 | 14.5 | `3965-4926` | b8, bovine, cell, cost, cultured, effective, expansion, meat, medium, satellite, serum-free, simple |
| 4 | 14.0 | `584-1730` | albumin, b8, beefy-9, bovine, cell, cells, cultured, expansion, meat, recombinant, satellite, serum-free |
| 5 | 14.0 | `23195-25271` | b8, beefy-9, cell, cells, concentration, cultured, expansion, medium, satellite, serum-free, sustained, were |

## H004: Chemically defined bovine medium formulation

- Status: `ready_for_human_review`
- Source record: `R016`
- Manifest title: Development of a Chemically Defined Medium for in vitro Expansion of Primary Bovine Satellite Cells
- Human question: Which components and concentrations made the Kolkmann chemically defined medium animal-free and effective for primary bovine satellite cell expansion?
- Suggested action: Extract full component table, supplements, attachment conditions, and endpoint values.
- Local paper: `development-of-a-chemically-defined-medium-for-in-vitro-expansion-of-primary-bov`
- Full text: `data/papers/development-of-a-chemically-defined-medium-for-in-vitro-expansion-of-primary-bov/fulltext.txt`
- Source SHA-256: `25fabce9211fbb531fbcc7051ccc945bc92347b70c078c8934d7f71a6ef8a17a`
- Query terms: chemically, defined, bovine, medium, formulation, component_list, dose_range, animal_free_status, components, concentrations, made, kolkmann, animal-free, effective, primary, satellite, cell, expansion, extract, full, component, table, supplements, attachment

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 27.0 | `13185-18322` | animal-free, attachment, bovine, cell, cells, chemically, component, components, concentrations, conditions, development, differentiation |
| 2 | 25.0 | `18323-24893` | attachment, bovine, capacity, cell, cells, chemically, component, concentrations, conditions, development, differentiation, effective |
| 3 | 25.0 | `39977-45025` | attachment, bovine, capacity, cell, cells, chemically, components, concentrations, development, differentiation, effective, expansion |
| 4 | 24.0 | `3889-10062` | animal-free, attachment, bovine, cell, cells, chemically, components, development, differentiation, expansion, formulation, full |
| 5 | 24.0 | `26483-33136` | bovine, cell, cells, chemically, concentrations, conditions, development, differentiation, effective, expansion, formulation, full |

## H005: Differentiation capacity after expansion

- Status: `ready_for_human_review`
- Source record: `R016`
- Manifest title: Development of a Chemically Defined Medium for in vitro Expansion of Primary Bovine Satellite Cells
- Human question: Did cells expanded in the chemically defined medium retain differentiation capacity, and what marker/assay proves it?
- Suggested action: Record markers, assay timing, and comparison condition.
- Local paper: `development-of-a-chemically-defined-medium-for-in-vitro-expansion-of-primary-bov`
- Full text: `data/papers/development-of-a-chemically-defined-medium-for-in-vitro-expansion-of-primary-bov/fulltext.txt`
- Source SHA-256: `25fabce9211fbb531fbcc7051ccc945bc92347b70c078c8934d7f71a6ef8a17a`
- Query terms: differentiation, capacity, expansion, myogenic_identity, differentiation_capacity, cells, expanded, chemically, defined, medium, retain, marker/assay, proves, markers, assay, timing, comparison, condition., development, vitro, primary, bovine, satellite, serum-free

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 18.5 | `13185-18322` | animal-free, attachment, bovine, cells, chemically, comparison, development, differentiation, expansion, medium, proliferation, satellite |
| 2 | 18.5 | `18323-24893` | attachment, bovine, capacity, cells, chemically, comparison, development, differentiation, medium, primary, proliferation, satellite |
| 3 | 18.5 | `39977-45025` | attachment, bovine, capacity, cells, chemically, development, differentiation, expanded, expansion, medium, primary, proliferation |
| 4 | 17.5 | `3889-10062` | animal-free, assay, attachment, bovine, cells, chemically, development, differentiation, expansion, medium, proliferation, satellite |
| 5 | 16.5 | `10063-13184` | animal-free, assay, bovine, capacity, cells, chemically, development, differentiation, medium, proliferation, satellite, serum-free |

## H006: Commercial SFM benchmark

- Status: `ready_for_human_review`
- Source record: `R017`
- Manifest title: Serum-free media for the growth of primary bovine myoblasts
- Human question: Which commercial chemically defined serum-free media supported primary bovine myoblast growth, and how did they compare with serum-containing medium?
- Suggested action: Record media names, 6-day proliferation data, morphology notes, and limitations.
- Local paper: `serum-free-media-for-the-growth-of-primary-bovine-myoblasts`
- Full text: `data/papers/serum-free-media-for-the-growth-of-primary-bovine-myoblasts/fulltext.txt`
- Source SHA-256: `fd804bcf8c812094397cd2b6acfcf6853c773da6db4c51283bcb452e82494fa0`
- Query terms: commercial, sfm, benchmark, negative_evidence, serum_free_status, chemically, defined, serum-free, media, supported, primary, bovine, myoblast, growth, they, compare, serum-containing, medium, names, 6-day, proliferation, data, morphology, notes

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 18.5 | `11523-14880` | bovine, chemically, data, growth, media, medium, morphology, mts, myoblast, myoblasts, proliferation, serum-containing |
| 2 | 16.0 | `7578-11522` | benchmark, commercial, data, growth, media, medium, mts, myoblast, myoblasts, proliferation, serum-free, sfm |
| 3 | 16.0 | `20219-23837` | benchmark, bovine, data, growth, media, medium, myoblast, myoblasts, primary, serum-containing, serum-free, supported |
| 4 | 14.0 | `15803-18055` | bovine, growth, media, medium, mts, myoblast, myoblasts, serum-free, supported, they |
| 5 | 13.5 | `0-3108` | bovine, growth, media, medium, mts, myoblast, myoblasts, primary, proliferation, serum-free |

## H007: Serum-free differentiation guardrail

- Status: `ready_for_human_review`
- Source record: `R018`
- Manifest title: A serum-free media formulation for cultured meat production supports bovine satellite cell differentiation in the absence of serum starvation
- Human question: Which ligands/receptors enabled serum-free myogenic differentiation, and are any of these also plausible expansion-stage risks or constraints?
- Suggested action: Extract IGF1R/TFRC/LPAR1-related ligands, markers, and whether expansion formulation should avoid differentiation induction.
- Local paper: `a-serum-free-media-formulation-for-cultured-meat-production-supports-bovine-sate`
- Full text: `data/papers/a-serum-free-media-formulation-for-cultured-meat-production-supports-bovine-sate/fulltext.txt`
- Source SHA-256: `793d4561289421161a64e029e2b3503804b28fc8f1d7d9766860b268d5a77544`
- Query terms: serum-free, differentiation, guardrail, differentiation_endpoint, ligand_list, ligands/receptors, enabled, myogenic, plausible, expansion-stage, risks, constraints, extract, igf1r/tfrc/lpar1-related, ligands, markers, whether, expansion, formulation, avoid, induction., media, cultured, meat

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 28.5 | `2378-8256` | absence, bovine, cell, chemically, cultured, defined, differentiation, enabled, expression, formulation, gene, igf1r |
| 2 | 26.5 | `23235-31306` | absence, bovine, cell, chemically, cultured, defined, differentiation, expression, formulation, gene, ligands, markers |
| 3 | 23.0 | `12469-20778` | absence, bovine, cell, differentiation, expression, formulation, gene, igf1r, ligands, lpar1, markers, media |
| 4 | 19.0 | `48895-58888` | bovine, cell, chemically, cultured, defined, differentiation, expression, gene, media, medium, myogenic, satellite |
| 5 | 17.5 | `32536-38369` | absence, cell, cultured, differentiation, expression, formulation, ligands, meat, medium, myogenic, production, serum |

## H008: Species and cell-type dependence

- Status: `ready_for_human_review`
- Source record: `R019`
- Manifest title: Spent media analysis suggests cultivated meat media will require species and cell type optimization
- Human question: Which consumed nutrients/metabolites differed by species/cell type, and which findings justify avoiding cross-species transfer?
- Suggested action: Extract bovine-relevant spent-media findings and any reusable assay recommendations.
- Local paper: `spent-media-analysis-suggests-cultivated-meat-media-will-require-species-and-cel`
- Full text: `data/papers/spent-media-analysis-suggests-cultivated-meat-media-will-require-species-and-cel/fulltext.txt`
- Source SHA-256: `2a0b8024867784b0def0d71f1c92a44365fa21f5af0d1a159406b5cd72d18739`
- Query terms: species, cell-type, dependence, cell_type_specificity, spent_media_features, consumed, nutrients/metabolites, differed, species/cell, type, findings, justify, avoiding, cross-species, transfer, extract, bovine-relevant, spent-media, reusable, assay, recommendations., spent, media, analysis

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 16.5 | `0-6323` | analysis, cell, consumed, consumption, cultivated, growth, meat, media, nutrient, optimization, require, species |
| 2 | 16.5 | `31873-39708` | analysis, cell, consumption, cultivated, growth, meat, media, nutrient, optimization, species, spent, suggests |
| 3 | 14.5 | `14961-20489` | analysis, assay, cell, cultivated, growth, meat, media, nutrient, species, spent, type, will |
| 4 | 14.5 | `20490-25135` | analysis, cell, consumption, cultivated, growth, meat, media, nutrient, optimization, require, species, spent |
| 5 | 13.5 | `27415-31872` | analysis, cell, consumption, cultivated, growth, meat, media, nutrient, spent, suggests, will |

## H009: Microalga/conditioned medium variable

- Status: `ready_for_human_review`
- Source record: `R020`
- Manifest title: Development of serum-free and grain-derived-nutrient-free medium using microalga-derived nutrients and mammalian cell-secreted growth factors for sustainable cultured meat production
- Human question: Can the microalga-derived nutrient and conditioned-medium system be decomposed into controllable, reproducible variables for first-round testing?
- Suggested action: Extract CVE dose, conditioned medium fraction, growth effect, and reproducibility caveats.
- Local paper: `development-of-serum-free-and-grain-derived-nutrient-free-medium-using-microalga`
- Full text: `data/papers/development-of-serum-free-and-grain-derived-nutrient-free-medium-using-microalga/fulltext.txt`
- Source SHA-256: `6568319895f8ad2a1aefd225a5fd433231e9a237d574be697f729a405ad64751`
- Query terms: microalga/conditioned, medium, variable, composition_disclosure, algae_extract_dose, conditioned_medium, microalga-derived, nutrient, conditioned-medium, system, decomposed, controllable, reproducible, variables, first-round, testing, extract, cve, dose, conditioned, fraction, growth, effect, reproducibility

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 20.0 | `3456-7441` | conditioned, cultured, cve, extract, factors, grain-derived-nutrient-free, growth, mammalian, meat, medium, nutrient, nutrients |
| 2 | 19.0 | `0-3455` | cell-secreted, conditioned, cultured, cve, development, extract, factors, grain-derived-nutrient-free, growth, mammalian, meat, medium |
| 3 | 18.0 | `43475-51604` | conditioned, cultured, development, effect, extract, factors, fraction, growth, mammalian, meat, medium, nutrients |
| 4 | 17.0 | `19384-23271` | cell-secreted, conditioned, cultured, cve, effect, extract, factors, growth, medium, microalga-derived, nutrient, nutrients |
| 5 | 17.0 | `30861-37684` | cell-secreted, cultured, cve, extract, factors, growth, meat, medium, nutrient, nutrients, production, proliferation |

## H010: DOE/RSM bovine SFM formulation

- Status: `ready_for_human_review`
- Source record: `R021`
- Manifest title: A simple and robust serum-free media for the proliferation of muscle cells
- Human question: What factors and levels were screened by DOE/RSM, and which optimized formulation should seed the search space?
- Suggested action: Extract factor list, low/high levels, optimal recipe, response metrics, and validation data.
- Local paper: `a-simple-and-robust-serum-free-media-for-the-proliferation-of-muscle-cells`
- Full text: `data/papers/a-simple-and-robust-serum-free-media-for-the-proliferation-of-muscle-cells/fulltext.txt`
- Source SHA-256: `1fc65fdb5dc5eb0cd18a1a51096a983400ca66d4ff06a8bd0dc01c733847bb16`
- Query terms: doe/rsm, bovine, sfm, formulation, doe_factors, optimized_levels, endpoint, factors, levels, were, screened, optimized, seed, search, space, extract, factor, list, low/high, optimal, recipe, response, metrics, validation

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 18.5 | `0-5055` | bovine, cells, factors, long-term, media, muscle, optimized, performance, proliferation, response, robust, serum-free |
| 2 | 17.0 | `65213-74491` | bovine, cells, factors, formulation, levels, long-term, media, muscle, optimized, proliferation, response, serum-free |
| 3 | 16.5 | `18625-26847` | bovine, cells, factors, levels, list, media, optimized, performance, proliferation, response, serum-free, transcriptomics |
| 4 | 16.5 | `74492-82848` | bovine, cells, factor, long-term, media, muscle, optimized, performance, proliferation, response, seed, serum-free |
| 5 | 14.0 | `5056-11010` | bovine, cells, extract, factor, factors, long-term, media, optimized, response, screened, serum-free, transcriptomics |

## H011: Long-term and transcriptomic validation

- Status: `ready_for_human_review`
- Source record: `R021`
- Manifest title: A simple and robust serum-free media for the proliferation of muscle cells
- Human question: Did the DOE/RSM formulation preserve proliferative attributes and myogenic identity over longer culture?
- Suggested action: Record long-term assay length, live assays, transcriptomics summary, and warnings.
- Local paper: `a-simple-and-robust-serum-free-media-for-the-proliferation-of-muscle-cells`
- Full text: `data/papers/a-simple-and-robust-serum-free-media-for-the-proliferation-of-muscle-cells/fulltext.txt`
- Source SHA-256: `1fc65fdb5dc5eb0cd18a1a51096a983400ca66d4ff06a8bd0dc01c733847bb16`
- Query terms: long-term, transcriptomic, validation, long_term_performance, identity_markers, doe/rsm, formulation, preserve, proliferative, attributes, myogenic, identity, longer, culture, assay, length, live, assays, transcriptomics, summary, warnings., simple, robust, serum-free

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 17.0 | `0-5055` | attributes, cells, culture, live, long-term, media, muscle, performance, proliferation, proliferative, robust, serum-free |
| 2 | 16.5 | `18625-26847` | assay, assays, cells, culture, live, longer, media, myogenic, performance, proliferation, proliferative, serum-free |
| 3 | 16.5 | `46453-52400` | assay, assays, cells, live, long-term, media, muscle, myogenic, performance, proliferation, proliferative, serum-free |
| 4 | 15.5 | `65213-74491` | assay, assays, cells, culture, formulation, live, long-term, longer, media, muscle, proliferation, serum-free |
| 5 | 14.5 | `60011-65212` | assays, cells, culture, long-term, media, myogenic, proliferation, proliferative, robust, serum-free, simple |

## H012: Albumin replacement candidates

- Status: `ready_for_human_review`
- Source record: `R022`
- Manifest title: Low-cost food-grade alternatives for serum albumins in FBS-free cell culture media
- Human question: Which low-cost food-grade alternatives to serum albumin worked in B8/B9 for bovine muscle stem cells, and at what concentration?
- Suggested action: Extract substitute identity, dose, performance relative to albumin, and food-grade status.
- Local paper: `low-cost-food-grade-alternatives-for-serum-albumins-in-fbs-free-cell-culture-med`
- Full text: `data/papers/low-cost-food-grade-alternatives-for-serum-albumins-in-fbs-free-cell-culture-med/fulltext.txt`
- Source SHA-256: `ae70adf2819b5b58cd0b0ee3cb8232751e20f1a553e010db40e07dd0e97f1bb9`
- Query terms: albumin, replacement, candidates, albumin_substitute, food_grade, dose_range, low-cost, food-grade, alternatives, serum, worked, b8/b9, bovine, muscle, stem, cells, concentration, extract, substitute, identity, dose, performance, relative, status.

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 23.5 | `4685-11667` | albumin, albumins, alternatives, b8/b9, bovine, cell, cells, concentration, cost, culture, food-grade, media |
| 2 | 23.0 | `0-4684` | albumin, albumins, alternatives, b8/b9, bovine, cell, cells, concentration, cost, culture, fbs-free, food-grade |
| 3 | 17.0 | `37701-42494` | albumin, b8/b9, bovine, cell, cells, concentration, cost, media, muscle, optimization, proliferation, replacement |
| 4 | 15.5 | `27122-33782` | albumin, bovine, cell, cells, culture, media, muscle, proliferation, serum, stabilizers, substitute |
| 5 | 13.5 | `54639-61145` | albumin, bovine, cell, cells, culture, media, muscle, proliferation, serum, stabilizers, stem |

## H013: Stabilizer mechanism

- Status: `ready_for_human_review`
- Source record: `R022`
- Manifest title: Low-cost food-grade alternatives for serum albumins in FBS-free cell culture media
- Human question: Is the albumin substitute acting as carrier/stabilizer, nutrient, or undefined bioactive mixture?
- Suggested action: Assign mechanism class and note unknown composition risk.
- Local paper: `low-cost-food-grade-alternatives-for-serum-albumins-in-fbs-free-cell-culture-med`
- Full text: `data/papers/low-cost-food-grade-alternatives-for-serum-albumins-in-fbs-free-cell-culture-med/fulltext.txt`
- Source SHA-256: `ae70adf2819b5b58cd0b0ee3cb8232751e20f1a553e010db40e07dd0e97f1bb9`
- Query terms: stabilizer, mechanism, mechanism_class, safety, reproducibility, albumin, substitute, acting, carrier/stabilizer, nutrient, undefined, bioactive, mixture, assign, class, note, unknown, composition, risk., low-cost, food-grade, alternatives, serum, albumins

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 20.0 | `4685-11667` | albumin, albumins, alternatives, b8/b9, cell, composition, cost, culture, food-grade, media, optimization, proliferation |
| 2 | 18.0 | `0-4684` | albumin, albumins, alternatives, b8/b9, cell, cost, culture, fbs-free, food-grade, low-cost, media, mixture |
| 3 | 13.0 | `27122-33782` | albumin, cell, culture, media, proliferation, serum, stabilizer, stabilizers, substitute |
| 4 | 12.0 | `37701-42494` | albumin, b8/b9, cell, cost, media, optimization, proliferation, stabilizer, stabilizers, substitute |
| 5 | 11.5 | `33783-37571` | albumin, albumins, b8/b9, cell, culture, media, serum, stabilizer, stabilizers, substitute |

## H014: bFGF/media composition interactions

- Status: `ready_for_human_review`
- Source record: `R023`
- Manifest title: Influence of Media Composition on the Level of Bovine Satellite Cell Proliferation
- Human question: What media components interacted with bFGF in bovine satellite proliferation, and what were the tested levels?
- Suggested action: Extract DOE design, factor levels, interaction terms, and effect direction.
- Local paper: `influence-of-media-composition-on-the-level-of-bovine-satellite-cell-proliferati`
- Full text: `data/papers/influence-of-media-composition-on-the-level-of-bovine-satellite-cell-proliferati/fulltext.txt`
- Source SHA-256: `8e27c3ff5e9114a90d78fccf3de731c97942e7377ad0d4e20fc8e006b41dca7e`
- Query terms: bfgf/media, composition, interactions, bfgf_dose, interaction_effects, doe_model, media, components, interacted, bfgf, bovine, satellite, proliferation, were, tested, levels, extract, doe, design, factor, interaction, terms, effect, direction.

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 19.0 | `6376-8434` | bfgf, bovine, cell, components, composition, design, doe, factor, influence, interactions, level, media |
| 2 | 16.5 | `35731-38478` | bfgf, bovine, cell, components, composition, design, effect, factor, interaction, level, proliferation, satellite |
| 3 | 16.5 | `38479-40034` | bfgf, bovine, cell, effect, factor, influence, interaction, interactions, level, levels, proliferation, tested |
| 4 | 15.5 | `1312-2991` | bfgf, bovine, cell, components, composition, effect, factor, level, proliferation, satellite, tested |
| 5 | 14.5 | `21192-22098` | bfgf, cell, components, effect, factor, interaction, level, levels, proliferation, satellite, terms, tested |

## H015: Plant/insect protein isolate status

- Status: `missing_ingested_paper`
- Source record: `R024`
- Manifest title: Sustainable alternatives to fetal bovine serum: evaluating the role of plant and insect protein isolates in serum-free media for bovine satellite cell proliferation in cultivated meat production
- Human question: Which plant or insect protein isolates improved bovine satellite-cell proliferation, and which violate animal-component-free preference?
- Suggested action: Extract isolate source, dose, performance, and animal-origin classification.
- Local paper: `MISSING`
- Full text: `MISSING`
- Source SHA-256: `MISSING`
- Query terms: plant/insect, protein, isolate, status, animal_origin_status, protein_isolate_dose, performance, plant, insect, isolates, improved, bovine, satellite-cell, proliferation, violate, animal-component-free, preference, extract, source, dose, animal-origin, classification., sustainable, alternatives

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| - | - | - | - |

## H016: Undefined supplement risk

- Status: `missing_ingested_paper`
- Source record: `R024`
- Manifest title: Sustainable alternatives to fetal bovine serum: evaluating the role of plant and insect protein isolates in serum-free media for bovine satellite cell proliferation in cultivated meat production
- Human question: Are the protein isolates sufficiently characterized for reproducible medium optimization?
- Suggested action: Record composition data, certificate/spec needs, and batch-risk notes.
- Local paper: `MISSING`
- Full text: `MISSING`
- Source SHA-256: `MISSING`
- Query terms: undefined, supplement, risk, composition_disclosure, batch_variability, protein, isolates, sufficiently, characterized, reproducible, medium, optimization, composition, data, certificate/spec, needs, batch-risk, notes., sustainable, alternatives, fetal, bovine, serum, evaluating

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| - | - | - | - |
