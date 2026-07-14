# Human Review Packet: H034-H037

Status: candidate passage locators for human adjudication; not an AI decision.

## Summary

| Metric | Value |
|---|---:|
| Review tasks | 4 |
| Tasks with local full text | 4 |
| Tasks needing source/fulltext action | 0 |

## How To Use

For each task, open the listed local `fulltext.txt` and inspect the character ranges.
The packet avoids embedding long source excerpts; record the final human decision in
`data/literature/bovine_human_review_queue.tsv` and transfer adjudicated facts to
`data/literature/bovine_evidence_table.tsv`.

## H034: Postbiotic-assisted growth-factor reduction

- Status: `ready_for_human_review`
- Source record: `R048`
- Manifest title: Microbiota-Derived Postbiotics Enhance the Proliferative Effects of Growth Factors on Satellite Cells in Cultivated Meat Applications
- Human question: Does Biftek-1 at a traceable composition and dose permit lower IGF1/FGF2 use in primary bovine satellite cells, and is the FBS comparison quantitatively supported?
- Suggested action: Verify postbiotic preparation and dose, growth-factor concentrations, controls, biological versus technical replicates, proliferation statistics, and myogenic markers; do not promote an undisclosed mixture.
- Local paper: `microbiota-derived-postbiotics-enhance-the-proliferative-effects-of-growth-facto`
- Full text: `data/papers/microbiota-derived-postbiotics-enhance-the-proliferative-effects-of-growth-facto/fulltext.txt`
- Source SHA-256: `20de4ed9febe19468e8561e8210c45b558f4818d33d6bdac598955c0627c8957`
- Query terms: postbiotic-assisted, growth-factor, reduction, postbiotic_identity, composition, dose, igf1, fgf2, fbs_comparator, proliferation, replicates, myogenicity, biftek-1, traceable, permit, lower, igf1/fgf2, primary, bovine, satellite, cells, fbs, comparison, quantitatively

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 28.5 | `0-4313` | applications, biftek-1, bovine, cell, cells, concentrations, cultivated, effects, enhance, factors, fbs, fgf2 |
| 2 | 23.5 | `25278-29948` | applications, bovine, cell, cells, concentrations, cultivated, effects, fbs, fgf2, growth, igf1, lower |
| 3 | 19.5 | `18390-20966` | bovine, cell, cells, concentrations, dose, effects, fbs, fgf2, igf1, lower, postbiotics, proliferation |
| 4 | 18.0 | `33870-39810` | bovine, cell, cells, cultivated, factors, growth, meat, microbiota-derived, myogenic, postbiotics, primary, proliferation |
| 5 | 15.5 | `4314-8777` | bovine, cell, cultivated, effects, factors, fbs, fgf2, growth, igf1, lower, meat, microbiota-derived |

## H035: Natural-product additives under reduced FBS

- Status: `ready_for_human_review`
- Source record: `R049`
- Manifest title: Discovery of Novel Stimulators of Pax7 and/or MyoD: Enhancing the Efficacy of Cultured Meat Production through Culture Media Enrichment
- Human question: Which compounds and doses reproduce 20% FBS-like Hanwoo satellite-cell proliferation in 10% FBS, without cytotoxicity or loss of differentiation?
- Suggested action: Separate SPR binding from cell assays; record compound doses, serum levels, controls, replicate structure, proliferation variance, cytotoxicity, and differentiation outcomes.
- Local paper: `discovery-of-novel-stimulators-of-pax7-andor-myod-enhancing-the-efficacy-of-cult`
- Full text: `data/papers/discovery-of-novel-stimulators-of-pax7-andor-myod-enhancing-the-efficacy-of-cult/fulltext.txt`
- Source SHA-256: `7e1f2073414370be16b3cbb2c80ac25f5c7ad3f7e3a5fe0b17f77fa9bd52bfc3`
- Query terms: natural-product, additives, under, reduced, fbs, compound_identity, dose, fbs_level, proliferation, differentiation, cytotoxicity, replicates, compounds, doses, reproduce, 20%, fbs-like, hanwoo, satellite-cell, 10%, loss, separate, spr, binding

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 33.0 | `0-4377` | 10%, 20%, additives, adenosine, and/or, assays, cell, culture, cultured, differentiation, discovery, efficacy |
| 2 | 26.0 | `18248-22750` | acid, adenosine, and/or, binding, cell, culture, cultured, differentiation, efficacy, fbs, levels, matrine |
| 3 | 23.0 | `22751-27339` | adenosine, assays, cell, culture, cultured, cytotoxicity, differentiation, discovery, efficacy, enhancing, meat, myod |
| 4 | 20.0 | `4378-8682` | 20%, and/or, binding, cell, compound, culture, cultured, differentiation, fbs, hanwoo, meat, myod |
| 5 | 19.5 | `31956-37782` | cell, culture, differentiation, discovery, hanwoo, meat, media, myod, parthenolide, pax7, production, proliferation |

## H036: Serum and basal-medium effects under oxygen context

- Status: `ready_for_human_review`
- Source record: `R050`
- Manifest title: Effect of Serum and Oxygen on the In Vitro Culture of Hanwoo Korean Native Cattle-Derived Skeletal Myogenic Cells Used in Cellular Agriculture
- Human question: Which effects are attributable to FBS level or DMEM/F12 versus F10, and which depend on non-actionable oxygen conditions?
- Suggested action: Extract factorial conditions, cell counts and variance, replicate structure, apoptosis and differentiation outcomes; keep oxygen as a blocked contextual factor, not a proposed medium variable.
- Local paper: `effect-of-serum-and-oxygen-on-the-in-vitro-culture-of-hanwoo-korean-native-cattl`
- Full text: `data/papers/effect-of-serum-and-oxygen-on-the-in-vitro-culture-of-hanwoo-korean-native-cattl/fulltext.txt`
- Source SHA-256: `10d9bfda28ea55dc86077545d0500b7c1e7ea44d0b717bde6118e0057a74bb9e`
- Query terms: serum, basal-medium, effects, under, oxygen, context, fbs_level, basal_medium, oxygen_level, proliferation, apoptosis, differentiation, factorial_interaction, replicates, attributable, fbs, level, dmem/f12, versus, f10, depend, non-actionable, conditions, extract

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 30.5 | `0-4386` | agriculture, cattle-derived, cell, cells, cellular, conditions, culture, differentiation, dmem/f12, effect, f10, factor |
| 2 | 25.5 | `11465-15263` | cell, cells, concentration, conditions, culture, differentiation, dmem/f12, extract, f10, fbs, fusion, genes |
| 3 | 24.5 | `41425-46266` | agriculture, apoptosis, cell, cells, concentration, conditions, effect, effects, factor, fbs, genes, medium |
| 4 | 24.0 | `38537-41424` | agriculture, cell, cells, cellular, conditions, culture, differentiation, dmem/f12, effect, effects, factor, fbs |
| 5 | 23.0 | `4387-8660` | cell, cells, concentration, conditions, culture, differentiation, extract, fbs, hanwoo, korean, level, medium |

## H037: Insulin under reduced-serum bovine culture

- Status: `ready_for_human_review`
- Source record: `R051`
- Manifest title: The Role of Insulin in the Proliferation and Differentiation of Bovine Muscle Satellite (Stem) Cells for Cultured Meat Production
- Human question: At which insulin doses and FBS levels are bovine muscle satellite-cell proliferation and differentiation supported, with what variance and biological replication?
- Suggested action: Record insulin source and dose, serum conditions, controls, proliferation and identity endpoints, group n and variance; keep expansion and differentiation effects separate.
- Local paper: `the-role-of-insulin-in-the-proliferation-and-differentiation-of-bovine-muscle-sa`
- Full text: `data/papers/the-role-of-insulin-in-the-proliferation-and-differentiation-of-bovine-muscle-sa/fulltext.txt`
- Source SHA-256: `eea74f0f110abc6f8f50b03c1b336010a4383a841d92f8821aec6a36a666d53e`
- Query terms: insulin, under, reduced-serum, bovine, culture, insulin_source, dose, fbs_level, comparator, proliferation, ki67, pcna, differentiation, replicates, doses, fbs, levels, muscle, satellite-cell, supported, variance, biological, replication, source

| Rank | Score | Character Range | Matched Terms |
|---:|---:|---|---|
| 1 | 30.5 | `0-3923` | bovine, cells, conditions, creatine, culture, cultured, cytokine, differentiation, effects, factors, fbs, formation |
| 2 | 25.0 | `25364-29782` | bovine, cells, creatine, culture, cultured, differentiation, effects, factors, fbs, formation, growth, insulin |
| 3 | 24.0 | `3924-8048` | bovine, cells, culture, cultured, cytokine, differentiation, effects, factors, fbs, formation, growth, insulin |
| 4 | 24.0 | `40344-46138` | bovine, cells, culture, cultured, differentiation, effects, expansion, factors, fbs, growth, insulin, meat |
| 5 | 23.5 | `11544-15773` | bovine, cells, controls, creatine, culture, cultured, differentiation, effects, factors, formation, growth, insulin |
