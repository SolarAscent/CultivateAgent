# Extraction Evaluation Results

Status: offline hand-annotated fixture over four real medium papers. This is a smoke benchmark for `evaluate.evaluate_corpus`, not a claim of full-paper production accuracy. When `--live-provider provider:model` is supplied, the same fixture texts are extracted through the real provider client and scored here.

Evaluated provider profile: `mock_gpt`

- Papers: 4
- Mean grounding rate: 1.0
- Overall: {'tp': 39, 'fp': 0, 'fn': 8, 'precision': 1.0, 'recall': 0.8298, 'f1': 0.907}

## Per-Field Scores

| field | tp | fp | fn | precision | recall | f1 |
| --- | --- | --- | --- | --- | --- | --- |
| A.paper_id | 4 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| A.title | 4 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| B.main_track | 4 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| B.species | 5 | 0 | 1 | 1.0 | 0.8333 | 0.9091 |
| B.target_product_type | 0 | 0 | 2 | 0.0 | 0.0 | 0.0 |
| D.cell_type | 3 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| E.conditioned_medium_or_recycling | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| E.growth_factors | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| E.hydrolysates_or_extracts | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| E.medium_optimization_strategy | 1 | 0 | 2 | 1.0 | 0.3333 | 0.5 |
| E.serum_free_status | 4 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| H.structured_product_goal | 0 | 0 | 1 | 0.0 | 0.0 | 0.0 |
| I.differentiation_metrics | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| I.proliferation_metrics | 0 | 0 | 1 | 0.0 | 0.0 | 0.0 |
| J.extractable_variables | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| J.has_extractable_quant_data | 4 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| J.key_numeric_results | 1 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| K.core_findings | 0 | 0 | 1 | 0.0 | 0.0 | 0.0 |
| M.recommended_action | 4 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| OVERALL | 39 | 0 | 8 | 1.0 | 0.8298 | 0.907 |

## Corpus

- Stout et al., Communications Biology 5, 466 (2022). Sources: https://www.nature.com/articles/s42003-022-03423-8, https://pubmed.ncbi.nlm.nih.gov/35654948/
- Messmer et al., Nature Food 3, 74-85 (2022). Sources: https://www.nature.com/articles/s43016-021-00419-1, https://pubmed.ncbi.nlm.nih.gov/37118488/
- O'Neill et al., npj Science of Food 6, 46 (2022). Sources: https://www.nature.com/articles/s41538-022-00157-z, https://pmc.ncbi.nlm.nih.gov/articles/PMC11663224/
- Kolkmann et al., Scientific Reports 13, 498 (2023). Sources: https://www.nature.com/articles/s41598-023-27629-w, https://pubmed.ncbi.nlm.nih.gov/36627406/

## Error Analysis

- The A-M schema is broad enough that sparse abstracts under-score fields that require methods/tables; this fixture should be treated as a lower-bound protocol check.
- Medium fields are the most stable when the source explicitly names serum-free status or a component. Growth-factor and extract names still need synonym canonicalization before scoring.
- Quantitative fields are brittle: `partial` versus `yes` often depends on whether the paper has machine-readable tables, not only whether the abstract mentions numbers.
- Grounding failures are correctly counted when a provider supplies a plausible but absent quote.
