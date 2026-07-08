# Bovine-Focused Corpus Manifest

Date: 2026-07-07

This document records the first bovine-focused literature manifest and human
review queue for moving CultivateAgent toward a wet-lab-ready design packet.

2026-07-08 normalization follow-up: the first DeepSeek live run exposed
ontology gaps for real extracted components. The seed ontology now includes
SFB/SFGM, Beefy-R, rapeseed-protein isolate, Grifola frondosa extract,
Auxenochlorella pyrenoidosa protein extract, and copper ions so evidence can be
canonicalized for review and pooling. This does not approve any of those entries
for wet-lab use; it only prevents known aliases from remaining unnormalized.

2026-07-09 extraction-readiness follow-up: R023/H014 was previously marked
full-text-fallback-ready because its `fulltext.xml` was treated like GROBID TEI.
The file is JATS/Open Access article XML from Europe PMC, so CultivateAgent now
auto-detects JATS sections and `table-wrap` tables. H014 is now direct
section-routed-ready for operator extraction. This still does not approve the
evidence for wet-lab use.

Data files:

- `data/literature/bovine_corpus_manifest.tsv`
- `data/literature/bovine_human_review_queue.tsv`

## Target

First wet-lab-facing target:

> Bovine satellite cells / bovine myoblasts in the expansion phase, optimizing
> serum-free, preferably animal-component-free, cost-aware medium variables while
> preserving myogenic identity.

## Manifest Summary

The v0 manifest contains 44 records:

- 10 core records and 1 core-context record relevant to the first bovine
  expansion-medium scope.
- 21 context records covering reviews, safety, cost, systems biology, or
  optimization methods.
- 8 deferred records that are important for later phases but outside the first
  medium-only wet-lab round.
- 4 background-only gray-literature records retained for cost and industry
  orientation, not as wet-lab evidence.

The highest-priority direct wet-lab sources are:

- Stout et al. 2022, Beefy-9 bovine satellite-cell serum-free expansion.
- Kolkmann et al. 2022, chemically defined serum-free/animal-free bovine
  satellite-cell expansion medium.
- Kolkmann et al. 2020, serum-free commercial medium benchmark for primary
  bovine myoblasts.
- Messmer et al. 2022, serum-free bovine satellite-cell differentiation.
- O'Neill et al. 2022, spent-media species/cell-type dependence.
- Kolkmann et al. 2023, microalga-derived nutrients and conditioned medium.
- Skrivergaard et al. 2023, DOE/RSM serum-free bovine muscle-cell medium.
- Schenzle et al. 2025, food-grade albumin alternatives in bovine muscle stem
  cells.
- Zygmunt et al. 2023, bovine satellite-cell proliferation and media
  composition.
- Amirvaresi et al. 2025, plant/insect protein isolate alternatives for bovine
  satellite-cell serum-free media.

## Human Review Queue

The human review queue contains 30 open review tasks. It is intentionally
smaller than the manifest: it focuses on decision-critical evidence that could
change the first wet-lab batch.

Top review topics:

- exact Beefy-9/Beefy-9+ formulation and FGF2 reduction bounds;
- albumin source, dose, and replacement candidates;
- chemically defined animal-free bovine medium component tables;
- DOE/RSM factor levels and validated endpoints;
- protein isolate and hydrolysate evidence grading;
- live-run extract candidates such as Beefy-R, GFE, APE, copper ions, and
  SFB/SFGM as normalization targets;
- myogenic identity guardrails;
- cost and safety annotations for growth-factor-heavy formulations.

## Current Gate Status

Gate 1, corpus coverage: **partially met for manifest v0, not yet passed for
wet-lab entry**.

- The manifest has more than 35 candidate records.
- It includes more than 8 review/context papers.
- It includes more than 12 primary culture/media/process papers.
- It includes more than 10 bovine-relevant records.
- It includes at least 5 candidate records with likely extractable dose/range
  information.
- It includes at least 3 records that report serum-free or animal-free bovine
  muscle-cell culture.

Why this is still not a pass:

- Several records are not yet full-text extracted.
- Some DOI and quantitative fields need confirmation from full text.
- Background gray literature must not count as peer-reviewed wet-lab evidence.
- Human review is still open for all top evidence tasks.

Gate 2, extraction reliability: **not passed**.

- The current live model extraction run remained too sparse.
- `docs/EVIDENCE_AUDIT_PROLIFERATION.md` audits the current local
  proliferation effect-item export: 145 items across 40 papers and 103
  components/interventions, but only 4 AI-review candidates pass the direct
  bovine/medium-actionable/dose/grounding filter.
- The audit is still **NO-GO** because 16/16 critical human-review tasks remain
  open and all AI-review candidates are direction-only rather than quantitative.
- `docs/HUMAN_REVIEW_PACKET_H001_H016.md` now gives local full-text
  character-range locators for 14/16 critical review tasks: H001-H014. R017,
  R018, and R021 were added from accessible PDFs; R023 was added from Europe PMC
  fullTextXML. The remaining H015-H016 map to R024 and still need institutional
  or human-provided main full text before efficient review.
- Next step is full-text extraction plus human adjudication for the top 20-30
  review tasks.
- `data/literature/bovine_adjudication_H001_H014.tsv` now provides the
  human-fillable worksheet for H001-H014, and
  `docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md` confirms the blank template
  is structurally valid. This is not evidence approval.
- `data/literature/bovine_evidence_table.tsv` now exists as the export target
  for human-supported or partial adjudication rows. The committed file is
  header-only because no human decisions have been entered yet.
- `docs/EXTRACTION_READINESS_H001_H016.md` and
  `data/literature/bovine_extraction_readiness_H001_H016.tsv` now report
  offline operator-readiness before live extraction: H001-H014 are direct-ready,
  and H015-H016 remain missing because R024 is not ingested locally.

Gate 3, biological plausibility: **not passed**.

- Mechanism classes have been defined, but each candidate variable still needs
  review-level and direct-evidence support.

Gate 4, cost and supply sanity: **not passed**.

- Cost classes and supplier/food-grade annotations are not yet filled for each
  candidate component.

Gate 5, in-silico robustness: **not passed**.

- Search-space perturbation, retrieval agreement, and optimizer agreement have
  not yet been run on this bovine manifest.

Gate 6, pre-registration readiness: **not passed**.

- Candidate formulations, controls, endpoints, replicate plans, stopping
  criteria, and analysis plan still need to be produced after human review.

## Immediate Next Steps

1. Use `docs/HUMAN_REVIEW_PACKET_H001_H016.md` and
   `data/literature/bovine_adjudication_H001_H014.tsv` to review H001-H014.
2. Obtain R024 main full text through institutional access or a human-provided
   PDF; ACS and ACS Figshare automated downloads were access-challenged in this
   session.
3. After human edits, run `cultivate adjudication-validate`, then
   `cultivate adjudication-export` to refresh
   `data/literature/bovine_evidence_table.tsv`.
4. Run a small targeted operator-extraction pilot first, for example
   `cultivate extract --ids H014 --mode operators`, then scale to
   `--ids H001-H014` only after checking grounding and extraction metadata. The
   latest DeepSeek-compatible H014 pilot failed provider authentication and
   produced no extraction evidence, so a valid local provider key is required
   before repeating this step.
5. Re-run `cultivate review-packet` and `cultivate evidence-audit` after updated
   extraction outputs.
6. Extract exact component tables, dose ranges, endpoints, and evidence quotes
   for audit candidates.
7. Fill the 30 human review tasks, starting with `H001-H016`.
8. Promote only reviewed and grounded variables into a bounded search space.
9. Generate a first wet-lab design packet only after Gates 1-6 pass.
