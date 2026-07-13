# Literature Decision Record: Wet-Lab Entry Target

Date: 2026-07-07

Purpose: decide the first biologically useful target and scope boundary for turning
CultivateAgent from a literature-mining prototype into a system that can support
pre-registered cultivated-meat medium experiments.

## Executive Decision

The first wet-lab-facing system should target **bovine satellite cells / bovine
myoblasts in the expansion phase**, with the objective:

> Design and prioritize serum-free, preferably animal-component-free, cost-aware
> medium formulations that preserve myogenic identity while improving expansion
> performance.

This target is narrower than "cultivated meat media" but broad enough to be
publishable and experimentally useful. It aligns with the strongest public
evidence base: Beefy-9-like bovine satellite-cell serum-free media, Mosa-style
serum-free bovine differentiation work, microalga/conditioned-medium bovine
myoblast work, and cost-reduction reviews focused on serum-free media.

## Why This Target

### Literature Signal

Recent reviews converge on the same bottleneck: culture medium is a major
cost-driver and conventional biomedical media are not fit for food-scale
cultivated meat. A 2026 Future Foods review frames medium as a critical input
and major cost driver, estimates medium at 31-99% of scaled CM production cost,
and argues for first-principles design rather than blindly adapting biomedical
formulations. A 2024 npj Science of Food review similarly identifies serum-free
medium cost, especially growth factors and recombinant proteins, as a central
industrial obstacle.

The bovine satellite-cell track is the best first target because it has direct
primary evidence rather than only generic tissue-culture analogy:

- Stout et al. adapted B8 into Beefy-9 for bovine satellite-cell expansion and
  showed sustained serum-free expansion while maintaining myogenic markers.
- Messmer et al. demonstrated serum-free bovine satellite-cell differentiation,
  making the expansion/differentiation boundary experimentally meaningful.
- O'Neill et al. showed that medium needs are species- and cell-type-dependent,
  arguing against one universal medium.
- Kolkmann et al. showed serum-free, grain-derived-nutrient-free bovine
  myoblast media with microalga-derived nutrients and cell-secreted factors.

### Why Not Start With Chicken

Chicken has impressive recent scale/cost demonstrations, including animal-free
continuous manufacturing and high-density serum-free chicken cell systems.
However, those examples depend more strongly on stable or specialized cell
lines, suspension/perfusion process choices, and process economics. They are
excellent second-phase targets, but they are less suited to this repository's
current evidence-grounded medium-optimization workflow.

### Why Not Start With Porcine, Fish, Fat, Scaffold, Or Whole Tissue

These are valid cultivated-meat directions, but they add avoidable uncertainty:

- Porcine and fish have thinner public medium-optimization corpora.
- Adipogenic/fat systems require different endpoints and media logic.
- Scaffold, microcarrier, perfusion, and texture couple media effects to
  process variables, making the first closed-loop experiment harder to
  interpret.

The first experiment should prove that the system can make reliable
medium-variable decisions before adding process and tissue-structure variables.

## Scope Boundary

### In Scope For The First Wet-Lab-Ready System

- Species: bovine.
- Cell type: bovine satellite cells or bovine myoblasts.
- Stage: expansion/proliferation, not terminal differentiation.
- Intervention class: medium variables only.
- Objective set:
  - proliferation / viable cell expansion,
  - cost reduction,
  - serum-free and animal-component-free preference,
  - preservation of myogenic identity.
- Candidate variable classes:
  - basal medium choice or basal-medium simplification,
  - FGF2 concentration and growth-factor minimization,
  - insulin/transferrin/selenium axis,
  - albumin and albumin substitutes,
  - lipids/fatty-acid carriers,
  - amino-acid or energy-metabolism supplements,
  - plant, yeast, or algae hydrolysates/extracts as a secondary, evidence-gated
    cost-reduction axis.

### Out Of Scope For The First Round

- Genetic engineering or immortalization as an intervention.
- Bioreactor, perfusion, suspension adaptation, or microcarrier optimization.
- Scaffold, structuring, whole-cut tissue formation, texture, or sensory targets.
- Differentiation medium optimization, except as a safety check that expansion
  conditions do not destroy myogenic potential.
- Cross-species transfer claims unless explicitly labeled as weak prior evidence.
- Proprietary or undisclosed media as direct optimization targets.

## Pre-Wet-Lab Self-Validation Gates

Wet-lab intervention should start only when the system passes all gates below.
Failing any gate means the next step is more literature extraction, human review,
or software repair rather than experiments.

### Gate 1: Corpus Coverage

Minimum corpus before the first experimental design:

- 35-50 peer-reviewed sources.
- At least 8 recent reviews or consensus/scoping papers.
- At least 12 primary medium/cell-culture papers.
- At least 10 bovine satellite-cell/myoblast-relevant papers.
- At least 5 papers with extractable dose/range information.
- At least 3 papers that report serum-free or animal-component-free bovine
  muscle-cell culture.

Each included source must have DOI/URL, species, cell type, stage, medium type,
and reason for inclusion/exclusion recorded.

### Gate 2: Extraction Reliability

For decision-critical fields, the extraction layer must meet:

- Evidence quote grounding rate >= 0.95 for top-ranked records.
- Non-missing fraction >= 0.75 for species, cell type, stage, medium type,
  serum-free status, component identity, dose/range, and endpoint.
- Independent extractor agreement or human adjudication for all top candidates.
- Categorical agreement kappa >= 0.70 where two independent model/human passes
  are available.
- Every component entering the design space must link back to at least one
  traceable source quote and one normalized component record.

The current live OpenAI/Anthropic run does not meet this gate because coverage
was too sparse; it is useful as a failure diagnosis, not as design evidence.

Operationalization: each of the eight concepts is evaluated separately at the
0.75 non-missing threshold. A pooled average never compensates for a failed
concept. `species`, `cell_type`, `stage`, `medium_type`,
`serum_free_status`, `component_identity`, and `endpoint` map to direct A-M
fields or field groups. `dose_range` is only a proxy over J-block quantitative
fields because A-M has no dedicated component-dose structure; even complete
proxy coverage yields `PROVISIONAL_ONLY` until the dedicated dose operator and
human review confirm it. Missing gold coverage yields `NOT_EVALUABLE`, not a
pass. This follows Cochrane Handbook Chapter 5 guidance to predefine and pilot
distinct data items and expose missing decision-critical outcome information.

The operator path now emits an optional direct component-dose record. A record
counts as direct coverage only when one locally verified quote contains both the
reported component string and the reported numeric dose/range, with unit checks
when a separate unit is supplied. Comparison group and endpoint remain attached
to that relation. Flat J-block lists remain a proxy; unverified or cross-passage
pairings cannot upgrade Gate 2. Human numeric adjudication is still required for
thesis use.

### Gate 3: Biological Plausibility

Every proposed medium variable must be assigned one mechanism class:

- mitogen / signaling factor,
- carrier or stabilizer,
- nutrient or metabolic substrate,
- serum substitute / undefined bioactive mixture,
- stress-protection or survival factor,
- differentiation-risk factor.

Decision-critical interventions require one of:

- direct bovine satellite-cell/myoblast evidence, or
- one direct cultivated-meat cell-culture paper plus a mechanistic review, or
- two independent non-bovine sources explicitly marked as weak prior evidence.

No variable should be recommended if its mechanism is unknown, its composition is
undisclosed, and no food/safety rationale is available.

### Gate 4: Cost And Supply Sanity

Before wet-lab work, each candidate formulation should include:

- rough raw-material cost class: low, medium, high, or unknown;
- recombinant protein burden;
- animal-origin status;
- food-grade plausibility;
- supplier availability risk;
- whether the variable is expected to increase performance, reduce cost, or
  merely explore uncertainty.

No first-round formulation should be dominated by a more expensive formulation
with no plausible performance or uncertainty benefit.

### Gate 5: In-Silico Robustness

The first experiment design should be stable under perturbation:

- BM25 and embedding retrieval should agree on most of the top evidence clusters.
- q-ParEGO and qLogNEHVI should select overlapping high-level variable classes,
  even if exact doses differ.
- Removing any single paper should not remove more than one critical candidate
  class unless that class is explicitly labeled exploratory.
- The first batch should include controls and avoid testing many near-duplicate
  formulations.

Suggested pass threshold: at least 70% overlap in top variable classes across
retrieval/optimizer perturbations, with all disagreements documented.

### Gate 6: Pre-Registration Readiness

Before starting wet-lab work, the system must output a design packet containing:

- biological target and scope statement;
- inclusion/exclusion criteria for papers;
- candidate formulation table;
- control categories;
- endpoint definitions;
- replicate plan at the level approved by the wet-lab lead;
- stopping/failure criteria;
- planned analysis;
- caveats and unsupported claims;
- exact citations supporting each variable.

The first wet-lab round should be framed as **validation of the literature-driven
design workflow**, not as an attempt to discover a final commercial medium.

## Result Standard For Wet-Lab Entry

Wet-lab work is justified when the system can produce the following evidence:

1. A curated bovine expansion-medium corpus meeting Gate 1.
2. A structured evidence table whose decision-critical fields pass Gate 2.
3. A bounded search space of 4-6 controllable medium-variable classes.
4. A ranked first-round design of 12-24 candidate conditions plus controls.
5. A cost/animal-origin/supply annotation for every candidate component.
6. A human-review sign-off that top evidence quotes support the recommendation.
7. A pre-registration packet that a wet-lab collaborator can execute without
   changing the scientific question midstream.

If these conditions are not met, the correct next action is more curation and
verification, not wet-lab trial-and-error.

## Source Set Used For This Decision

Reviews and scoping papers:

- Goodwin et al. 2026, "Cell culture media for cultivated meat: Review and
  perspectives on first principles design to drive cost-effective scale-up",
  Future Foods. https://www.sciencedirect.com/science/article/pii/S2666833526000109
- Xie et al. 2026, "Technological Advances and the Challenges for Large-Scale
  Cultured Meat Production", Annual Review of Food Science and Technology.
  https://www.annualreviews.org/content/journals/10.1146/annurev-food-053124-085815
- Martins et al. 2024, "Advances and Challenges in Cell Biology for Cultured
  Meat", Annual Review of Animal Biosciences.
  https://www.annualreviews.org/content/journals/10.1146/annurev-animal-021022-055132
- Nikkhah et al. 2024, "Exploring cost reduction strategies for serum free media
  development", npj Science of Food.
  https://www.nature.com/articles/s41538-024-00352-0
- O'Neill et al. 2021, "Considerations for the development of cost-effective
  cell culture media for cultivated meat production", Comprehensive Reviews in
  Food Science and Food Safety.
  https://pubmed.ncbi.nlm.nih.gov/33325139/
- Todhunter et al. 2024, "Artificial intelligence and machine learning
  applications for cultured meat", Frontiers in Artificial Intelligence.
  https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2024.1424012/full
- Jiang et al. 2025, "Serum-free media for cultured meat: insights into protein
  hydrolysates as proliferation enhancers", Food Research International.
  https://www.sciencedirect.com/science/article/abs/pii/S0963996925013547
- "Fetal bovine serum: how to leave it behind in the pursuit of more reliable
  science", Frontiers in Toxicology, 2025.
  https://www.frontiersin.org/journals/toxicology/articles/10.3389/ftox.2025.1612903/full
- "Standardising Culture Medium Safety Testing for Cultivated Meat", Foods,
  2026. https://www.mdpi.com/2304-8158/15/4/783

Primary anchors:

- Stout et al. 2022, Beefy-9 bovine satellite-cell serum-free medium.
  https://www.nature.com/articles/s42003-022-03423-8
- Messmer et al. 2022, serum-free bovine satellite-cell differentiation.
  https://www.nature.com/articles/s43016-021-00419-1
- O'Neill et al. 2022, spent-media analysis and species/cell-type dependence.
  https://www.nature.com/articles/s41538-022-00157-z
- Kolkmann et al. 2023, microalga-derived nutrients and cell-secreted growth
  factors for bovine myoblasts.
  https://www.nature.com/articles/s41598-023-27629-w
- Pasitka et al. 2023, high-yield serum-free chicken fibroblast production.
  https://www.nature.com/articles/s43016-022-00658-w
- Pasitka et al. 2024, animal-free cultivated chicken continuous manufacturing.
  https://www.nature.com/articles/s43016-024-01022-w

## Immediate Next Work

1. Build a bovine-focused corpus manifest with inclusion/exclusion reasons.
2. Re-run extraction on full text, not abstracts only.
3. Add a human-adjudication table for the top 20 decision-critical records.
4. Generate a first bounded search space with 4-6 variable classes.
5. Produce the first wet-lab design packet only after the gates above pass.
