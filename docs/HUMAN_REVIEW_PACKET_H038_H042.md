# Human Review Packet: H038-H042

Status: candidate passage locators for human adjudication; not an AI decision.

## Summary

| Metric | Value |
|---|---:|
| Review tasks | 5 |
| Tasks with local full text | 5 |
| Tasks needing source/fulltext action | 0 |

## How To Use

For each task, open the listed local `fulltext.txt` and inspect the character ranges.
The packet avoids embedding long source excerpts; record the final human decision in
`data/literature/bovine_human_review_queue.tsv` and transfer adjudicated facts to
`data/literature/bovine_evidence_table.tsv`.

## H038: Drone-pupae extract in Hanwoo satellite-cell culture

- Status: `ready_for_human_review`
- Source record: `R052`
- Manifest title: Drone pupae extract enhances Hanwoo myosatellite cell function for cultivated meat production
- Human question: Does dose-defined drone-pupae extract improve primary Hanwoo satellite-cell expansion, and which effects remain dependent on 20% FBS, bFGF, collagen coating, or undefined composition?
- Suggested action: Verify extract preparation and composition, exact doses, controls, biological replication, proliferation variance, myogenic retention, animal-origin status, and high-serum limitations.
- Local paper: `drone-pupae-extract-enhances-hanwoo-myosatellite-cell-function-for-cultivated-me`
- Full text: `data/papers/drone-pupae-extract-enhances-hanwoo-myosatellite-cell-function-for-cultivated-me/fulltext.txt`
- Source SHA-256: `c9a09bea88f49946e9a0c30887fadff43a16c4ff1d693e03f267e2ec3e1eee2a`
- Query terms: drone-pupae, extract, hanwoo, satellite-cell, culture, extract_preparation, composition, animal_origin, dose, fbs_level, bfgf, proliferation, differentiation, replicates, dose-defined, improve, primary, expansion, effects, remain, dependent, 20%, fbs, collagen

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 15.0 | `95-1694` | cell, culture, differentiation, drone, effects, extract, hanwoo, improve, myosatellite, proliferation, pupae, viability |
| 2 | 13.0 | `16460-17639` | 20%, bfgf, cell, coating, collagen, culture, f-10, fbs, ham, proliferation |
| 3 | 13.0 | `32724-34115` | cell, culture, differentiation, drone, improve, oxidative, proliferation, pupae, stress, viability |
| 4 | 11.0 | `0-94` | cell, cultivated, drone, enhances, extract, function, hanwoo, meat, myosatellite, production, pupae |
| 5 | 11.0 | `5045-5455` | cell, cultivated, differentiation, drone, hanwoo, meat, myosatellite, production, proliferation, pupae |

## H039: L-ascorbic acid dose response in bovine satellite cells

- Status: `ready_for_human_review`
- Source record: `R053`
- Manifest title: The L-Ascorbic Acid Increases Proliferation and Differentiation of Yanbian Cattle Skeletal Muscle Satellite Cells by Activating the Akt/mTOR/P70S6K Signaling Pathway
- Human question: Which L-ascorbic acid doses and durations improve Yanbian-cattle satellite-cell proliferation without the high-dose viability loss, and are effects transferable beyond 10% FBS?
- Suggested action: Record all dose/time groups, serum and basal medium, controls, group n and variance, EdU and viability effects, differentiation retention, and the toxicity boundary.
- Local paper: `the-l-ascorbic-acid-increases-proliferation-and-differentiation-of-yanbian-cattl`
- Full text: `data/papers/the-l-ascorbic-acid-increases-proliferation-and-differentiation-of-yanbian-cattl/fulltext.txt`
- Source SHA-256: `3ccce65608f82ecb8e498b5aafd893596b99b194f1cee84fdf1c0420257420dd`
- Query terms: l-ascorbic, acid, dose, response, bovine, satellite, cells, duration, fbs_level, viability, edu, proliferation, myogenicity, toxicity, replicates, doses, durations, improve, yanbian-cattle, satellite-cell, high-dose, loss, effects, transferable

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 20.0 | `27731-33428` | cattle, cell, cells, controls, differentiation, edu, effects, group, increases, muscle, myogenic, pathway |
| 2 | 19.0 | `167-1762` | acid, activating, akt/mtor/p70s6k, bovine, cell, cells, differentiation, edu, effects, l-ascorbic, muscle, pathway |
| 3 | 18.5 | `1777-3805` | acid, bovine, cell, cells, differentiation, effects, l-ascorbic, medium, muscle, myogenic, proliferation, satellite |
| 4 | 16.5 | `0-166` | acid, activating, akt/mtor/p70s6k, cattle, cells, differentiation, increases, l-ascorbic, muscle, pathway, proliferation, satellite |
| 5 | 14.5 | `39745-41290` | acid, all, bovine, cell, cells, edu, groups, l-ascorbic, muscle, proliferation, satellite, skeletal |

## H040: Glucose and lysine under PLAG1 genotype context

- Status: `ready_for_human_review`
- Source record: `R054`
- Manifest title: Effect of glucose and lysine supplementation on myogenic and adipogenic gene expression in muscle satellite cells isolated from Hanwoo with different genotypes of PLAG1: Implications for cell-based food production
- Human question: Which glucose/lysine effects are supported by cell number or viability rather than gene expression alone, and how strongly do they interact with PLAG1 genotype?
- Suggested action: Extract factorial levels, animal and replicate structure, serum conditions, cell-count variance, viability, marker outcomes, genotype interactions, and expansion-versus-differentiation timing.
- Local paper: `effect-of-glucose-and-lysine-supplementation-on-myogenic-and-adipogenic-gene-exp`
- Full text: `data/papers/effect-of-glucose-and-lysine-supplementation-on-myogenic-and-adipogenic-gene-exp/fulltext.txt`
- Source SHA-256: `85179948bc655bcdcc9c06926c64014f7e808cf5c2e79cd0693135dc63060583`
- Query terms: glucose, lysine, under, plag1, genotype, context, fbs_level, cell_count, viability, gene_expression, interaction, replicates, glucose/lysine, effects, supported, cell, number, rather, than, gene, expression, alone, strongly, they

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 23.5 | `215-2493` | adipogenic, cell, cell-based, cells, differentiation, effects, expression, food, gene, genotype, genotypes, glucose |
| 2 | 21.0 | `0-214` | adipogenic, cell-based, cells, different, effect, expression, food, gene, genotypes, glucose, hanwoo, implications |
| 3 | 20.0 | `24434-26611` | cell, cell-based, conditions, different, differentiation, expression, food, gene, genotype, genotypes, glucose, levels |
| 4 | 18.5 | `26612-28938` | cell, cell-based, cells, conditions, different, differentiation, effects, expression, food, gene, genotype, genotypes |
| 5 | 18.0 | `6697-7494` | cell, cell-based, cells, differentiation, effect, expression, food, gene, genotype, glucose, hanwoo, isolated |

## H041: Ecklonia crude-polysaccharide fractions in Hanwoo cells

- Status: `ready_for_human_review`
- Source record: `R055`
- Manifest title: Effect of Crude Polysaccharides from Ecklonia cava Hydrolysate on Cell Proliferation and Differentiation of Hanwoo Muscle Stem Cells for Cultured Meat Production
- Human question: Does a chemically traceable E. cava fraction improve primary Hanwoo satellite-cell proliferation at a non-cytotoxic dose, and can evidence transfer from 20% FBS plus bFGF?
- Suggested action: Verify hydrolysis and fraction preparation, composition, all doses and controls, biological replication, proliferation variance, cytotoxicity, migration, differentiation, and serum/growth-factor dependence.
- Local paper: `effect-of-crude-polysaccharides-from-ecklonia-cava-hydrolysate-on-cell-prolifera`
- Full text: `data/papers/effect-of-crude-polysaccharides-from-ecklonia-cava-hydrolysate-on-cell-prolifera/fulltext.txt`
- Source SHA-256: `6e53252e228db694bd814c30c20493d5d44e8025d2b586ba75af608781e1feae`
- Query terms: ecklonia, crude-polysaccharide, fractions, hanwoo, cells, fraction_identity, composition, dose, fbs_level, bfgf, proliferation, cytotoxicity, differentiation, replicates, chemically, traceable, cava, fraction, improve, primary, satellite-cell, non-cytotoxic, evidence, transfer

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 21.0 | `163-1628` | cava, cell, cells, composition, crude, cultured, differentiation, ecklonia, effect, hanwoo, hydrolysate, markers |
| 2 | 18.0 | `24271-25346` | cava, cell, cells, crude, cultured, differentiation, ecklonia, hanwoo, markers, meat, migration, muscle |
| 3 | 17.5 | `0-162` | cava, cell, cells, crude, cultured, differentiation, ecklonia, effect, hanwoo, hydrolysate, meat, muscle |
| 4 | 16.5 | `3578-4463` | cava, cell, composition, crude, cultured, differentiation, ecklonia, extract, hanwoo, meat, muscle, polysaccharide |
| 5 | 13.5 | `13729-14842` | all, cava, cell, crude, cytotoxicity, effect, enzyme, extract, polysaccharide, proliferation, viability |

## H042: Conditioned serum-free medium and nutrient deconvolution

- Status: `ready_for_human_review`
- Source record: `R056`
- Manifest title: Conditioned serum-free culture medium accomplishes adhesion and proliferation of bovine myogenic cells on uncoated dishes
- Human question: Which disclosed nutrients reproduce the conditioned-medium adhesion/proliferation effect in primary bovine myogenic cells, and what prevents use of the human/mouse cell-derived supernatant itself?
- Suggested action: Separate conditioned-medium effects from individual nutrient tests; record source cells, composition, doses, controls, surface context, biological replication, passage stability, adhesion/proliferation variance, myogenic markers, and food-safety constraints.
- Local paper: `conditioned-serum-free-culture-medium-accomplishes-adhesion-and-proliferation-of`
- Full text: `data/papers/conditioned-serum-free-culture-medium-accomplishes-adhesion-and-proliferation-of/fulltext.txt`
- Source SHA-256: `cb1b4349945e7e1040e36eff38e5df843d99fcb2c9860c71e5343cb877b0d3c4`
- Query terms: conditioned, serum-free, medium, nutrient, deconvolution, conditioner_cell_sources, medium_composition, nutrient_doses, surface_context, adhesion, proliferation, ki67, desmin, passages, replicates, safety, disclosed, nutrients, reproduce, conditioned-medium, adhesion/proliferation, effect, primary, bovine

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 23.0 | `22736-23979` | acid, adhesion, asparagine, biological, bovine, cell, cells, culture, dishes, effect, glutamic, medium |
| 2 | 22.5 | `123-1469` | acid, adhesion, asparagine, biological, bovine, cell, cells, composition, conditioned, culture, dishes, glutamic |
| 3 | 21.0 | `27671-29716` | acid, adhesion, asparagine, bovine, cell, cells, culture, dishes, effect, glutamic, medium, myogenic |
| 4 | 18.0 | `31612-32856` | acid, adhesion, asparagine, bovine, cell, cells, conditioned, culture, dishes, glutamic, medium, myogenic |
| 5 | 17.0 | `52600-53967` | bovine, cell, cells, culture, dishes, medium, myogenic, number, passage, serum-free, stability, supernatant |
