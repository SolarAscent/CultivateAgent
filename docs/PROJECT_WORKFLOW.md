# CultivateAgent Project Workflow

Date: 2026-07-07

Audience: developers, wet-lab collaborators, literature reviewers, and AI agents
that need to continue the same project without stepping on each other.

This is the operational guide for taking CultivateAgent from an empty project
state to a completed paper workflow: literature collection, extraction,
human review, candidate medium design, wet-lab validation, result comparison,
analysis, and paper-ready reporting.

## Role Legend

Use these labels in issues, commits, review notes, and handoff messages.

- `[HUMAN]`: requires human scientific judgment or wet-lab ownership.
- `[AI]`: can be executed by Codex, Claude, or another AI agent.
- `[LAB]`: requires wet-lab execution or lab-manager confirmation.
- `[REVIEW]`: explicit check, audit, or sign-off step.
- `[GATE]`: a stage boundary. Do not proceed until the checklist is satisfied.
- `[DOC]`: update documentation or a traceable project record.

## What This Project Is

CultivateAgent is a medium-centered literature-mining and optimization system
for cultivated meat. It adapts the ReactionSeek pattern:

1. use LLMs to extract structured facts from papers,
2. validate and normalize those facts with deterministic tools,
3. store them in a knowledge base,
4. retrieve evidence,
5. propose medium-formulation changes, and
6. produce pre-registerable experimental batches through multi-objective
   Bayesian optimization.

The current first wet-lab-facing target is:

> Bovine satellite cells / bovine myoblasts in the expansion phase, optimizing
> serum-free, preferably animal-component-free, cost-aware medium variables while
> preserving myogenic identity.

The first round is intentionally medium-only. Scaffold, microcarrier, perfusion,
bioreactor, genetic engineering, differentiation-media optimization, whole-cut
texture, and sensory work are later phases unless a documented review changes
the scope.

## Repository Structure For Developers

Read this section before editing.

```text
CultivateAgent/
  README.md                         project overview and CLI quickstart
  pyproject.toml                    package metadata and optional deps
  requirements.txt                  default environment dependencies
  config/
    config.example.yaml             runtime config template
  cultivate_agent/
    cli.py                          command-line entrypoint
    ingest/                         BibTeX/PDF/text ingestion
    triage/                         paper screening and tiering
    extract/                        LLM extraction prompts and parser
    schema/                         typed A-M extraction schema and evidence
    normalize/                      component and unit normalization
    kb/                             SQLite knowledge base and exports
    retrieve/                       BM25 and optional embedding retrievers
    design/                         evidence-grounded medium recommender
    optimize/                       MOBO search space, surrogate, acquisition
    evaluate/                       extraction evaluation metrics
    llm/                            provider-agnostic OpenAI/Anthropic/Gemini/mock clients
  scripts/
    evaluate_medium_corpus.py       extraction/agreement evaluation fixture
    compare_mobo_backends.py        q-ParEGO/qNEHVI/qLogNEHVI benchmark
  data/
    library.example.bib             example BibTeX
    literature/
      bovine_corpus_manifest.tsv    curated literature manifest metadata
      bovine_human_review_queue.tsv decision-critical human review tasks
  docs/
    ARCHITECTURE.md                 architecture and ReactionSeek mapping
    OPTIMIZATION.md                 optimizer design
    LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md
    BOVINE_CORPUS_MANIFEST.md
    SESSION_LOG.md
    REVIEW_BY_NEXT_ENGINEER.md
```

Important implementation rules:

- Keep medium-only action boundaries unless a documented review changes scope.
- Do not treat cross-paper outcomes as comparable training labels.
- Use evidence quotes and grounding checks for extraction claims.
- Use `data/literature/*.tsv` for curated metadata; keep PDFs, SQLite files, and
  raw paper artifacts out of git unless explicitly approved.
- Run tests after code changes.
- Record scientific decisions in `docs/`, not only in chat.

## Current Interface And Final Presentation

The current system is not a web application. The working interface is:

- CLI commands such as `cultivate ingest`, `cultivate extract`,
  `cultivate export`, `cultivate design`, and `cultivate optimize`.
- Markdown decision records in `docs/`.
- TSV/CSV/JSONL tables for literature, evidence, extracted fields, components,
  candidate designs, and experiment results.

The expected paper-facing final output is a **design and validation package**,
not just a terminal printout:

- curated literature manifest,
- human-reviewed evidence table,
- normalized component and dose table,
- bounded search space,
- pre-registered candidate formulation table,
- wet-lab protocol summary,
- raw and processed experiment results,
- comparison against baselines,
- statistical analysis and interpretation,
- final figures/tables for manuscript.

A dashboard can be built later, but it should not precede the evidence and
wet-lab validation workflow.

## End-To-End Workflow

### Phase 0: Project Setup

Goal: make the repository runnable and reproducible.

- [ ] `[AI]` Create or update Python environment.
- [ ] `[AI]` Install package in editable mode.
- [ ] `[AI]` Run smoke test and unit tests.
- [ ] `[HUMAN]` Confirm local paths, API-key policy, and whether cloud provider
  calls are allowed.
- [ ] `[DOC]` Record environment, branch, and known blockers in
  `docs/SESSION_LOG.md`.

Commands:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
.venv/bin/python -m pytest -q
.venv/bin/python -m cultivate_agent.cli smoke
```

`[GATE]` Phase 0 passes when tests and smoke pass, or any failure is documented
with a repair plan.

### Phase 1: Scientific Scope Lock

Goal: choose one first experimentable biological target.

- [x] `[AI]` Review recent cultivated-meat medium and cell-biology literature.
- [x] `[AI]` Propose a first wet-lab-facing target.
- [x] `[REVIEW]` Decide what is in scope and out of scope.
- [x] `[DOC]` Record the decision in
  `docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md`.

Current locked first target:

- bovine satellite cells / bovine myoblasts,
- expansion/proliferation phase,
- serum-free and preferably animal-component-free medium optimization,
- cost-aware objective,
- myogenic identity preservation.

`[GATE]` Any scope change requires a short decision record explaining:

- why the current bovine expansion target is insufficient,
- what evidence supports the new target,
- which downstream tables and gates must change.

### Phase 2: Literature Corpus Construction

Goal: build a traceable paper set before extraction and experiment design.

- [x] `[AI]` Create a bovine-focused corpus manifest.
- [x] `[AI]` Mark each record as `core`, `core_context`, `context`, `defer`, or
  `background`.
- [x] `[AI]` Create a human review queue for decision-critical evidence.
- [ ] `[HUMAN]` Confirm inclusion/exclusion of P1 core records.
- [ ] `[AI]` Pull full text/PDFs for P1 records where access is available.
- [ ] `[REVIEW]` Verify DOI, URL, species, cell type, stage, medium focus, dose
  availability, and endpoint fields.

Files:

- `data/literature/bovine_corpus_manifest.tsv`
- `data/literature/bovine_human_review_queue.tsv`
- `docs/BOVINE_CORPUS_MANIFEST.md`

`[GATE]` Corpus coverage is considered wet-lab-entry ready only when:

- 35-50 peer-reviewed sources are curated,
- at least 8 are recent reviews or consensus/scoping papers,
- at least 12 are primary medium/cell-culture papers,
- at least 10 are bovine satellite-cell/myoblast relevant,
- at least 5 include extractable dose/range information,
- at least 3 report serum-free or animal-component-free bovine muscle-cell
  culture,
- background-only sources are not counted as wet-lab evidence.

### Phase 3: Full-Text Extraction

Goal: turn papers into structured, grounded data.

- [ ] `[AI]` Ingest BibTeX/PDFs or full-text files.
- [ ] `[AI]` Run triage and extraction on P1/P2 sources.
- [ ] `[AI]` Export screening, component, evidence, and extraction tables.
- [ ] `[AI]` Record extraction coverage and grounding rate.
- [ ] `[REVIEW]` Flag sparse or unreliable extraction runs.
- [ ] `[AI]` Repair parser/prompt issues only when the error is demonstrably
  technical rather than missing source content.

Commands:

```bash
cultivate ingest
cultivate triage
cultivate extract --tier A
cultivate export
```

Expected exports:

- `screening_table.csv`
- `medium_components.csv`
- `evidence.csv`
- `extractions.jsonl`

`[GATE]` Extraction reliability passes only when decision-critical fields meet:

- evidence quote grounding rate >= 0.95 for top-ranked records,
- non-missing fraction >= 0.75 for species, cell type, stage, medium type,
  serum-free status, component identity, dose/range, and endpoint,
- every component entering the design space links to a source quote and a
  normalized component record.

### Phase 4: Human Evidence Review

Goal: make AI-extracted evidence scientifically trustworthy.

- [ ] `[HUMAN]` Review `H001-H016` first in
  `data/literature/bovine_human_review_queue.tsv`.
- [ ] `[HUMAN]` Mark each item as `supported`, `partial`, `unsupported`,
  `uncertain`, or `defer`.
- [ ] `[HUMAN]` Add short notes: exact formulation, dose, endpoint, caveat, or
  reason for exclusion.
- [ ] `[AI]` Convert human notes into a structured adjudication table.
- [ ] `[REVIEW]` Resolve disagreements between AI extraction and human reading.
- [ ] `[DOC]` Update gate status in `docs/BOVINE_CORPUS_MANIFEST.md`.

Recommended human review order:

1. Beefy-9 expansion benchmark, FGF2 reduction, albumin dose/cost.
2. Chemically defined bovine medium and differentiation capacity.
3. Commercial SFM benchmarks.
4. Spent-media species/cell-type dependence.
5. DOE/RSM bovine serum-free media.
6. Albumin substitutes and protein isolate/hydrolysate candidates.
7. Safety and cost annotations.

`[GATE]` Evidence review passes when all variables entering the first design
batch have human-reviewed support or are explicitly labeled exploratory.

### Phase 5: Candidate Variable And Search-Space Design

Goal: define what the optimizer is allowed to change.

- [ ] `[AI]` Build candidate variable classes from reviewed evidence.
- [ ] `[AI]` Assign mechanism class to every variable.
- [ ] `[AI]` Assign cost class, animal-origin status, food-grade plausibility,
  and supplier risk.
- [ ] `[HUMAN]` Confirm which reagents are available in the lab.
- [ ] `[LAB]` Confirm cell source, baseline medium, plate format, assay
  duration, and measurement capacity.
- [ ] `[REVIEW]` Remove variables with unsupported mechanism, undisclosed
  composition, or unacceptable safety/supply risk.

Candidate variable classes should normally be 4-6 classes, for example:

- basal medium choice or simplification,
- FGF2 concentration,
- insulin/transferrin/selenium axis,
- albumin or albumin substitute,
- lipid/fatty-acid carrier,
- amino-acid/metabolic supplement,
- evidence-gated hydrolysate or extract.

`[GATE]` Search space passes when it is bounded, controllable, purchasable, and
reviewed.

### Phase 6: In-Silico Robustness And Design Packet

Goal: make sure the first wet-lab batch is not a fragile artifact of one paper,
one retriever, or one optimizer.

- [ ] `[AI]` Compare BM25 and embedding retrieval evidence clusters.
- [ ] `[AI]` Run optimizer perturbations using q-ParEGO and qLogNEHVI.
- [ ] `[AI]` Run leave-one-source-out sensitivity for critical candidate
  classes.
- [ ] `[AI]` Generate a first candidate formulation table.
- [ ] `[REVIEW]` Check duplicates, unsafe extrapolation, unsupported claims, and
  dominance by cheaper/equally plausible alternatives.
- [ ] `[HUMAN]` Approve or revise candidate classes and controls.

`[GATE]` In-silico robustness passes when:

- top variable classes overlap by at least 70% across retrieval/optimizer
  perturbations,
- no single paper is the only support for a non-exploratory critical class,
- disagreements are documented,
- the first batch includes controls and avoids near-duplicates.

### Phase 7: Wet-Lab Pre-Registration

Goal: freeze the experiment before running it.

- [ ] `[AI]` Draft the pre-registration packet.
- [ ] `[LAB]` Confirm exact reagent list and preparation constraints.
- [ ] `[LAB]` Confirm cell source, passage window, seeding density, culture
  duration, media-change schedule, plate format, and replicate count.
- [ ] `[HUMAN]` Confirm primary endpoint and secondary endpoints.
- [ ] `[REVIEW]` Freeze candidate formulations before any wet-lab results are
  known.
- [ ] `[DOC]` Commit the design packet to git.

Minimum packet:

- biological target and scope statement,
- literature inclusion/exclusion criteria,
- candidate formulation table,
- positive, negative, and baseline controls,
- endpoint definitions,
- replicate plan,
- stopping/failure criteria,
- analysis plan,
- caveats and unsupported claims,
- exact citations supporting each variable.

`[GATE]` Wet lab may start only after this packet is committed.

### Phase 8: Wet-Lab Execution

Goal: run the pre-registered experiment without changing the question midstream.

- [ ] `[LAB]` Prepare cells and reagents according to the frozen protocol.
- [ ] `[LAB]` Run the experiment with logged plate map, reagent lots, operator,
  passage number, seeding density, and timing.
- [ ] `[LAB]` Record raw measurements and raw images where applicable.
- [ ] `[HUMAN]` Record deviations immediately.
- [ ] `[REVIEW]` Decide whether deviations invalidate, qualify, or merely
  annotate the run.
- [ ] `[DOC]` Store raw result files outside git if large, and commit metadata
  and result manifests.

Do not tune formulations during the run. If changes are needed, create a new
round with a new pre-registration packet.

### Phase 9: Result Processing And Comparison

Goal: compare measured results against controls and objectives.

- [ ] `[AI]` Load raw results into a structured result table.
- [ ] `[AI]` Normalize within-experiment outcomes only.
- [ ] `[AI]` Compute primary endpoint, secondary endpoints, and cost estimates.
- [ ] `[AI]` Compare candidates against baseline and positive controls.
- [ ] `[AI]` Update Pareto front: proliferation vs cost vs identity retention.
- [ ] `[HUMAN]` Review whether statistical results match biological
  interpretation.
- [ ] `[REVIEW]` Label every claim as supported, partial, unsupported, or
  exploratory.

Do not compare wet-lab outcomes directly to heterogeneous literature outcomes as
if they are the same training label. Literature defines the space; your wet-lab
data supplies the objective values.

### Phase 10: Closed-Loop Update

Goal: use measured results to choose the next round.

- [ ] `[AI]` Feed measured objective values into `optimize.tell()`.
- [ ] `[AI]` Generate next candidate batch with the same bounded search space or
  a documented revised search space.
- [ ] `[REVIEW]` Check whether the model is exploiting, exploring, or repeating
  failed regions.
- [ ] `[HUMAN]` Decide whether to run another round, narrow the search space,
  add an assay, or stop.
- [ ] `[DOC]` Commit round summary and next-round design packet.

`[GATE]` A new wet-lab round requires the same pre-registration discipline as
the first round.

### Phase 11: Manuscript-Ready Analysis

Goal: turn the system and experiments into a defensible paper.

- [ ] `[AI]` Generate final tables: corpus, evidence, variables, formulations,
  results, Pareto comparison, and ablation/sensitivity checks.
- [ ] `[AI]` Generate figures: workflow, literature evidence map, variable
  support, experimental outcomes, Pareto front, closed-loop trajectory.
- [ ] `[HUMAN]` Write biological interpretation and limitations.
- [ ] `[REVIEW]` Audit every claim against evidence and wet-lab data.
- [ ] `[REVIEW]` Confirm negative or inconclusive results are reported honestly.
- [ ] `[DOC]` Archive exact code commit, data manifests, analysis scripts, and
  protocol versions.

Paper claims should be limited to what the gates prove:

- the literature-mining workflow is traceable,
- the chosen search space is evidence-grounded,
- the wet-lab batch was pre-registered,
- measured outcomes improve, fail, or trade off against controls as shown,
- the system reduced unstructured trial-and-error only to the extent supported
  by the experiment design.

## Parallel Work Plan

The project can move faster if human and AI work in parallel, but each stream
must write to different artifacts.

### Human Stream

- [ ] Review `H001-H016` in `bovine_human_review_queue.tsv`.
- [ ] Confirm cell source and assay constraints.
- [ ] Confirm reagent availability and budget limits.
- [ ] Approve first candidate variable classes.
- [ ] Sign off on pre-registration before wet-lab work.

### AI Stream

- [ ] Pull and organize P1 full texts.
- [ ] Extract component tables, dose ranges, endpoints, and quotes.
- [ ] Build `bovine_evidence_table.tsv`.
- [ ] Convert human notes into adjudicated evidence records.
- [ ] Generate candidate variable classes.
- [ ] Run retrieval and optimizer robustness checks.
- [ ] Draft design packets and analysis reports.

### Lab Stream

- [ ] Confirm cell source, passage limits, and culture constraints.
- [ ] Confirm control media and assay protocol.
- [ ] Confirm throughput: number of conditions and replicates per round.
- [ ] Run only frozen, committed designs.
- [ ] Return raw results in agreed structured format.

### Conflict Avoidance

- Only one actor edits a TSV row group at a time.
- AI agents should not overwrite human notes.
- Human decisions override AI suggestions when documented.
- Scope changes require a decision record.
- Wet-lab designs must be committed before results are known.
- Results must not be used to retroactively edit the pre-registration packet.

## Current Status Snapshot

This section should be updated after major sessions.

### Completed

- [x] Project runs as a CLI-first Python package.
- [x] Core tests pass: latest `.venv/bin/python -m pytest -q` reported
  26 passed with 3 known warnings.
- [x] Smoke pipeline passes.
- [x] Demo optimization loop passes.
- [x] Extraction evaluator exists.
- [x] Offline four-paper evaluation fixture exists.
- [x] Optional embedding retriever exists.
- [x] BoTorch qNEHVI and qLogNEHVI backends exist.
- [x] Optional citation verifier exists.
- [x] Ontology-to-search-space handling was hardened for hydrolysates, extracts,
  defined supplements, albumin substitutes, amino acids, carbon sources, and
  trace elements.
- [x] Live provider mode exists for extraction evaluation.
- [x] Parser accepts both A-M block letters and schema attribute block names.
- [x] First wet-lab-facing target is decided and documented.
- [x] Bovine-focused manifest v0 exists with 44 records.
- [x] Human review queue v0 exists with 30 open tasks.

### Known Problems

- [ ] Live OpenAI/Anthropic extraction was too sparse to count as successful
  model agreement.
- [ ] Gemini live comparison has not been completed because no Gemini/Google key
  was available.
- [ ] OpenAI raw-response debugging hit insufficient quota.
- [ ] Current corpus manifest is not yet full-text extracted.
- [ ] Human review queue is entirely open.
- [ ] Cost, supplier, and food-grade annotations are not yet complete.
- [ ] In-silico robustness has not been run on the bovine manifest.
- [ ] No wet-lab design packet has been generated or frozen.
- [ ] No wet-lab results exist yet.

### Current Best Next Actions

1. `[AI]` Pull full text for all P1 core records.
2. `[AI]` Extract exact formulations, dose ranges, endpoints, and quotes.
3. `[HUMAN]` Review H001-H016.
4. `[AI]` Build the adjudicated bovine evidence table.
5. `[REVIEW]` Decide which variables can enter the first search space.
6. `[AI]` Generate the first design packet draft.

## How To Hand Off To Another AI Agent

When another AI resumes:

1. Read `README.md`.
2. Read this file.
3. Read `docs/SESSION_LOG.md`.
4. Read `docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md`.
5. Read `docs/BOVINE_CORPUS_MANIFEST.md`.
6. Check `git status --short --branch`.
7. Do not mark the project complete unless every gate in this document is
   satisfied with current evidence.

Suggested handoff prompt:

```text
Continue CultivateAgent using docs/PROJECT_WORKFLOW.md as the controlling
workflow. Preserve the current bovine satellite-cell/myoblast expansion-medium
scope unless you create a documented scope-change decision record. Start by
checking git status, then advance the next unchecked gate. Do not overwrite
human review notes.
```

## Appendix: Gate Summary

| Gate | Pass Condition | Current State |
|---|---|---|
| Phase 0 setup | tests/smoke pass or blockers documented | pass |
| Scope lock | target and boundaries documented | pass |
| Corpus coverage | curated corpus meets size/source requirements | partial |
| Extraction reliability | grounded, non-sparse decision fields | fail |
| Human review | top variables adjudicated | fail |
| Search space | bounded, purchasable, evidence-supported variables | fail |
| In-silico robustness | retrieval/optimizer perturbations stable | fail |
| Pre-registration | committed design packet before wet-lab | fail |
| Wet-lab execution | frozen protocol executed and deviations logged | not started |
| Result comparison | raw results analyzed against controls/objectives | not started |
| Manuscript audit | claims matched to evidence and data | not started |
