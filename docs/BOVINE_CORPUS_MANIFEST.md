# Bovine-Focused Corpus Manifest

Date: 2026-07-07

This document records the first bovine-focused literature manifest and human
review queue for moving CultivateAgent toward a wet-lab-ready design packet.

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
- Next step is full-text extraction plus human adjudication for the top 20-30
  review tasks.

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

1. Pull full text/PDFs for all P1 core records.
2. Extract exact component tables, dose ranges, endpoints, and evidence quotes.
3. Fill the 30 human review tasks.
4. Promote only reviewed and grounded variables into a bounded search space.
5. Generate a first wet-lab design packet only after Gates 1-6 pass.
