# Extraction Evaluation Results

Status: offline hand-annotated fixture over four real medium papers. This is a smoke benchmark for `evaluate.evaluate_corpus`, not a claim of full-paper production accuracy. When `--live-provider provider:model` is supplied, the same fixture texts are extracted through the real provider client and scored here.

Evaluated provider profile: `openai:gpt-5.4`

- Papers: 4
- Prediction coverage: 4/4 (1.0)
- Missing prediction IDs: none
- Unexpected prediction IDs: none
- Gold-field presence: 8/45 (0.1778)
- Substantive B-M fields: 0
- Evidence attachment: 0/0 (None)
- Attached evidence flagged unverified: 0
- Decision-critical coverage: 0/17 (0.0)
- Decision-critical Gate 2 status: FAIL
- Mean grounding rate: None
- Overall: {'tp': 8, 'fp': 8, 'fn': 39, 'precision': 0.5, 'recall': 0.1702, 'f1': 0.254}

## Per-Field Scores

| field | tp | fp | fn | precision | recall | f1 |
| --- | --- | --- | --- | --- | --- | --- |
| A.journal | 0 | 4 | 0 | 0.0 | 0.0 | 0.0 |
| A.paper_id | 4 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| A.title | 4 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| A.year | 0 | 4 | 0 | 0.0 | 0.0 | 0.0 |
| B.main_track | 0 | 0 | 4 | 0.0 | 0.0 | 0.0 |
| B.species | 0 | 0 | 6 | 0.0 | 0.0 | 0.0 |
| B.target_product_type | 0 | 0 | 2 | 0.0 | 0.0 | 0.0 |
| D.cell_type | 0 | 0 | 3 | 0.0 | 0.0 | 0.0 |
| E.conditioned_medium_or_recycling | 0 | 0 | 1 | 0.0 | 0.0 | 0.0 |
| E.growth_factors | 0 | 0 | 1 | 0.0 | 0.0 | 0.0 |
| E.hydrolysates_or_extracts | 0 | 0 | 1 | 0.0 | 0.0 | 0.0 |
| E.medium_optimization_strategy | 0 | 0 | 3 | 0.0 | 0.0 | 0.0 |
| E.serum_free_status | 0 | 0 | 4 | 0.0 | 0.0 | 0.0 |
| H.structured_product_goal | 0 | 0 | 1 | 0.0 | 0.0 | 0.0 |
| I.differentiation_metrics | 0 | 0 | 1 | 0.0 | 0.0 | 0.0 |
| I.proliferation_metrics | 0 | 0 | 1 | 0.0 | 0.0 | 0.0 |
| J.extractable_variables | 0 | 0 | 1 | 0.0 | 0.0 | 0.0 |
| J.has_extractable_quant_data | 0 | 0 | 4 | 0.0 | 0.0 | 0.0 |
| J.key_numeric_results | 0 | 0 | 1 | 0.0 | 0.0 | 0.0 |
| K.core_findings | 0 | 0 | 1 | 0.0 | 0.0 | 0.0 |
| M.recommended_action | 0 | 0 | 4 | 0.0 | 0.0 | 0.0 |
| OVERALL | 8 | 8 | 39 | 0.5 | 0.1702 | 0.254 |

## Decision-Critical Coverage

| concept | basis | expected | predicted | direct_predicted | nonmissing_fraction | status |
| --- | --- | --- | --- | --- | --- | --- |
| species | direct | 4 | 0 | 0 | 0.0 | FAIL |
| cell_type | direct | 3 | 0 | 0 | 0.0 | FAIL |
| stage | direct | 0 | 0 | 0 | None | NOT_EVALUABLE |
| medium_type | direct | 0 | 0 | 0 | None | NOT_EVALUABLE |
| serum_free_status | direct | 4 | 0 | 0 | 0.0 | FAIL |
| component_identity | direct | 2 | 0 | 0 | 0.0 | FAIL |
| dose_range | proxy | 2 | 0 | 0 | 0.0 | FAIL |
| endpoint | direct | 2 | 0 | 0 | 0.0 | FAIL |

`dose_range` is an A-M proxy over quantitative fields. Even when all rows pass,
a `PROVISIONAL_ONLY` result still requires dedicated dose extraction and review.
When every applicable paper instead has at least one locally grounded operator
`dose_record`, the row basis becomes `direct_operator`; unverified records never
contribute to `direct_predicted`.

The schema and operators now have dedicated `D.culture_stage` and
`E.medium_type` fields for future runs. This report remains tied to the prior
frozen fixture and historical live run. Its raw predictions were not versioned,
so those gold cells are not backfilled here; their `NOT_EVALUABLE` status is
preserved rather than retroactively changing the
published denominator.

## Corpus

- Stout et al., Communications Biology 5, 466 (2022). Sources: https://www.nature.com/articles/s42003-022-03423-8, https://pubmed.ncbi.nlm.nih.gov/35654948/
- Messmer et al., Nature Food 3, 74-85 (2022). Sources: https://www.nature.com/articles/s43016-021-00419-1, https://pubmed.ncbi.nlm.nih.gov/37118488/
- O'Neill et al., npj Science of Food 6, 46 (2022). Sources: https://www.nature.com/articles/s41538-022-00157-z, https://pmc.ncbi.nlm.nih.gov/articles/PMC11663224/
- Kolkmann et al., Scientific Reports 13, 498 (2023). Sources: https://www.nature.com/articles/s41598-023-27629-w, https://pubmed.ncbi.nlm.nih.gov/36627406/

## Error Analysis

- Live provider run note: `openai:gpt-5.4` and `anthropic:claude-opus-4-6` completed on the four fixture texts, but the scored A-M fields were almost entirely missing beyond bibliographic prefill. The resulting F1 is low and grounding rate is `None`, so this run diagnoses prompt/provider non-compliance or insufficient fixture context rather than successful production extraction.
- Parser hardening note: the extractor now accepts provider JSON that uses schema attribute names such as `medium_info` instead of A-M block letters such as `E`. Re-running live OpenAI/Anthropic after that change did not improve coverage, so the current live failure is likely sparse/null provider output or prompt non-compliance rather than only a parser-key mismatch.
- The A-M schema is broad enough that sparse abstracts under-score fields that require methods/tables; this fixture should be treated as a lower-bound protocol check.
- Medium fields are the most stable when the source explicitly names serum-free status or a component. Growth-factor and extract names still need synonym canonicalization before scoring.
- Quantitative fields are brittle: `partial` versus `yes` often depends on whether the paper has machine-readable tables, not only whether the abstract mentions numbers.
- Grounding failures are correctly counted when a provider supplies a plausible but absent quote.
- Corpus alignment is now strict: a missing paper-level prediction is scored as
  false negatives, unexpected IDs are reported, and duplicate IDs fail the
  evaluation instead of being silently overwritten. This run had complete 4/4
  paper-ID coverage; its poor field coverage and absent grounding remain the
  substantive failure.
- Field-cell diagnostics confirm that the four returned records were
  bibliographic shells: only 8/45 populated gold field cells were present and
  no B-M substantive field was extracted. Evidence attachment is `None`, not
  100%, because there were zero substantive predicted fields.
