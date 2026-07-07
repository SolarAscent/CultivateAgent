# CultivateAgent Project Operating Manual

Status: active  
Last updated: 2026-07-07  
Chinese version: [`PROJECT_WORKFLOW_ZH.md`](PROJECT_WORKFLOW_ZH.md)

This document is the operating manual for CultivateAgent. It is written for
developers, literature reviewers, wet-lab collaborators, project owners, and AI
agents that need to continue the same work without conflict.

## 1. Document Standard

This manual follows a simple documentation model inspired by Diataxis, Google
developer documentation, Microsoft procedure guidance, and GitLab documentation
style:

- Keep explanation, procedure, reference, and current status visibly separated.
- Use stable stage IDs so updates do not require rewriting the whole document.
- Put checklists under the stage where the work happens.
- Record review gates separately from task lists.
- Make every required artifact explicit.
- Keep current status in one section so it can be updated without disturbing the
  process definition.

Update rule:

- Change Section 2-8 only when the project process changes.
- Change Section 9 after each substantial work session.
- Add new scientific decisions as separate decision records in `docs/`.
- Do not overwrite human review notes with AI-generated text.

## 2. Project Summary

CultivateAgent is a CLI-first literature-mining and optimization system for
cultivated-meat culture-medium design. It adapts the ReactionSeek pattern:

1. extract structured facts from papers with an LLM;
2. validate, normalize, and ground the facts with deterministic tools;
3. store evidence in a queryable knowledge base;
4. retrieve evidence for a specified biological goal;
5. propose medium-formulation changes with citations;
6. select pre-registerable wet-lab batches with multi-objective Bayesian
   optimization.

Current first wet-lab-facing target:

> Bovine satellite cells / bovine myoblasts in the expansion phase, optimizing
> serum-free, preferably animal-component-free, cost-aware medium variables while
> preserving myogenic identity.

Current scope boundary:

- In scope: medium variables for bovine muscle-cell expansion.
- Out of scope for the first round: scaffold, microcarrier, perfusion,
  bioreactor, genetic engineering, whole-cut texture, sensory testing, and
  primary differentiation-medium optimization.

## 3. Repository Map

```text
CultivateAgent/
  README.md                         project overview and CLI quickstart
  pyproject.toml                    package metadata and optional dependencies
  requirements.txt                  default runtime dependencies
  config/
    config.example.yaml             runtime configuration template
  cultivate_agent/
    cli.py                          CLI entrypoint
    ingest/                         BibTeX, PDF, and text ingestion
    triage/                         paper screening and A/B/C tiering
    extract/                        LLM prompts, JSON parsing, grounding checks
    schema/                         A-M extraction schema and evidence models
                                     plus structured paper objects
    normalize/                      component and unit normalization
    kb/                             SQLite knowledge base and exports
    retrieve/                       BM25 and optional embedding retrievers
    design/                         evidence-grounded medium recommender
    optimize/                       search space, surrogate model, MOBO loop
    evaluate/                       extraction scoring and model agreement
    llm/                            OpenAI, Anthropic, Gemini, and mock clients
  scripts/
    evaluate_medium_corpus.py       extraction and agreement benchmark
    compare_mobo_backends.py        optimizer backend comparison
  data/
    library.example.bib             example BibTeX file
    literature/
      bovine_corpus_manifest.tsv    curated literature metadata
      bovine_human_review_queue.tsv human adjudication queue
  docs/
    ARCHITECTURE.md                 technical architecture
    OPTIMIZATION.md                 optimization design
    AI_FOR_SCIENCE_METHOD_REVIEW.md algorithm roadmap from reviewed AI-for-science literature
    PROJECT_WORKFLOW.md             this manual
    PROJECT_WORKFLOW_ZH.md          Chinese manual
    LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md
    BOVINE_CORPUS_MANIFEST.md
    SESSION_LOG.md
    REVIEW_BY_NEXT_ENGINEER.md
```

Current interface:

- CLI commands: `cultivate ingest`, `cultivate extract`, `cultivate export`,
  `cultivate design`, `cultivate optimize`.
- Data artifacts: TSV, CSV, JSONL, SQLite, and Markdown.
- No production web UI exists yet. A dashboard is optional later work, not the
  current delivery format.

## 4. Roles And Responsibilities

Use these labels in tasks, review notes, commits, and handoffs.

| Label | Responsible actor | Typical responsibility |
|---|---|---|
| `[HUMAN]` | Project owner or domain reviewer | Scientific judgment, scope approval, evidence adjudication |
| `[AI]` | Codex, Claude, or another AI agent | Search, extraction, coding, table preparation, draft reports |
| `[LAB]` | Wet-lab collaborator | Cells, reagents, protocol feasibility, experiment execution |
| `[REVIEW]` | Human or assigned reviewer | Gate checks, conflict resolution, claim audit |
| `[DOC]` | Any contributor | Traceable documentation update |

Conflict rules:

- AI may prepare evidence; humans approve scientific use.
- AI must not overwrite human notes.
- Wet-lab designs must be committed before results are known.
- Results must not be used to retroactively edit pre-registration.
- Scope changes require a new decision record.

## 5. Artifact Registry

| Artifact | Path or expected path | Owner | Update trigger |
|---|---|---|---|
| Operating manual | `docs/PROJECT_WORKFLOW.md`, `docs/PROJECT_WORKFLOW_ZH.md` | `[DOC]` | Process changes or major status update |
| Session log | `docs/SESSION_LOG.md` | `[AI]` | Each substantial work session |
| Wet-lab target decision | `docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md` | `[HUMAN]` + `[AI]` | Scope decision or scope change |
| Corpus manifest | `data/literature/bovine_corpus_manifest.tsv` | `[AI]` + `[REVIEW]` | New source or source status change |
| Human review queue | `data/literature/bovine_human_review_queue.tsv` | `[HUMAN]` + `[AI]` | Evidence adjudication |
| Corpus summary | `docs/BOVINE_CORPUS_MANIFEST.md` | `[AI]` | Manifest or review gate change |
| Extraction reports | `docs/EVAL_RESULTS.md`, `docs/MODEL_AGREEMENT.md` | `[AI]` | Evaluation run |
| Optimization report | `docs/OPTIMIZATION_BENCHMARK.md` | `[AI]` | Optimizer benchmark |
| AI-for-science method review | `docs/AI_FOR_SCIENCE_METHOD_REVIEW.md` and `data/literature/ai_for_science_method_sources.tsv` | `[AI]` + `[REVIEW]` | Literature-backed algorithm or pipeline decision |
| Evidence table | `data/literature/bovine_evidence_table.tsv` | `[AI]` + `[REVIEW]` | After full-text extraction |
| Candidate variables | `docs/CANDIDATE_VARIABLES.md` | `[AI]` + `[HUMAN]` | After evidence review |
| Design packet | `docs/wetlab/ROUND_<n>_DESIGN_PACKET.md` | `[AI]` + `[LAB]` + `[REVIEW]` | Before each wet-lab round |
| Results manifest | `docs/wetlab/ROUND_<n>_RESULTS.md` | `[AI]` + `[LAB]` | After each wet-lab round |

Do not commit large PDFs, raw images, SQLite databases, or raw instrument files
unless a separate storage policy approves it.

## 6. Lifecycle Overview

| Stage | Name | Main output | Gate status now |
|---|---|---|---|
| S0 | Environment setup | runnable repository | pass |
| S1 | Scope lock | wet-lab target decision | pass |
| S2 | Corpus construction | bovine manifest and review queue | partial |
| S3 | Full-text extraction | grounded evidence tables | fail |
| S4 | Human evidence review | adjudicated evidence | fail |
| S5 | Search-space design | bounded candidate variables | fail |
| S6 | In-silico robustness | stable design rationale | fail |
| S7 | Wet-lab pre-registration | committed design packet | fail |
| S8 | Wet-lab execution | raw results and deviations | not started |
| S9 | Result comparison | processed results and Pareto analysis | not started |
| S10 | Closed-loop update | next-round design or stop decision | not started |
| S11 | Manuscript audit | paper-ready claims and artifacts | not started |

## 7. Stage Checklists

### S0. Environment Setup

Purpose: make the repository reproducible.

Checklist:

- [ ] `[AI]` Create or activate the Python environment.
- [ ] `[AI]` Install dependencies and the package in editable mode.
- [ ] `[AI]` Run unit tests.
- [ ] `[AI]` Run the smoke pipeline.
- [ ] `[HUMAN]` Confirm API-key policy and whether live provider calls are
  allowed.
- [ ] `[DOC]` Record failures and fixes in `docs/SESSION_LOG.md`.

Commands:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
.venv/bin/python -m pytest -q
.venv/bin/python -m cultivate_agent.cli smoke
```

Gate S0 passes when tests and smoke pass, or blockers are documented with a
repair plan.

### S1. Scope Lock

Purpose: prevent the first wet-lab round from becoming an untestable broad
project.

Checklist:

- [x] `[AI]` Review recent cultivated-meat medium and cell-biology literature.
- [x] `[AI]` Propose the first wet-lab-facing target.
- [x] `[REVIEW]` Separate in-scope from out-of-scope work.
- [x] `[DOC]` Record the decision.

Gate S1 passes when the target and boundaries are documented.

Scope-change procedure:

- [ ] `[HUMAN]` State the proposed change.
- [ ] `[AI]` Gather evidence for and against the change.
- [ ] `[REVIEW]` Identify affected artifacts and gates.
- [ ] `[DOC]` Add a new decision record before changing downstream files.

### S2. Corpus Construction

Purpose: create a traceable literature set before extraction and experiment
design.

Checklist:

- [x] `[AI]` Create the bovine-focused corpus manifest.
- [x] `[AI]` Classify records as `core`, `core_context`, `context`, `defer`, or
  `background`.
- [x] `[AI]` Create a human review queue.
- [ ] `[HUMAN]` Confirm P1 core inclusion and exclusion.
- [ ] `[AI]` Pull full text or PDFs for P1 records where access is available.
- [ ] `[REVIEW]` Verify DOI, URL, species, cell type, stage, medium focus, dose
  availability, and endpoints.

Gate S2 passes for wet-lab entry only when:

- 35-50 peer-reviewed sources are curated;
- at least 8 are recent reviews or scoping papers;
- at least 12 are primary medium or cell-culture papers;
- at least 10 are bovine satellite-cell or myoblast relevant;
- at least 5 include extractable dose or range information;
- at least 3 report serum-free or animal-component-free bovine muscle-cell
  culture;
- background-only sources are excluded from wet-lab evidence counts.

### S3. Full-Text Extraction

Purpose: convert papers into structured, grounded data.

Checklist:

- [ ] `[AI]` Ingest BibTeX, PDFs, or full text.
- [ ] `[AI]` Run triage and extraction on P1/P2 sources.
- [ ] `[AI]` Export screening, component, evidence, and extraction tables.
- [ ] `[AI]` Record extraction coverage and grounding rate.
- [ ] `[REVIEW]` Flag sparse or unreliable extraction runs.
- [ ] `[AI]` Repair parser or prompt issues only when evidence shows the
  failure is technical rather than missing source content.

Commands:

```bash
cultivate ingest
cultivate triage
cultivate extract --tier A
cultivate export
```

Gate S3 passes when decision-critical fields meet:

- evidence quote grounding rate >= 0.95 for top-ranked records;
- non-missing fraction >= 0.75 for species, cell type, stage, medium type,
  serum-free status, component identity, dose/range, and endpoint;
- every component entering the design space links to a source quote and a
  normalized component record.

### S4. Human Evidence Review

Purpose: turn extracted evidence into scientifically usable evidence.

Checklist:

- [ ] `[HUMAN]` Review `H001-H016` first in
  `data/literature/bovine_human_review_queue.tsv`.
- [ ] `[HUMAN]` Mark each item as `supported`, `partial`, `unsupported`,
  `uncertain`, or `defer`.
- [ ] `[HUMAN]` Add concise notes with formulation, dose, endpoint, caveat, or
  exclusion reason.
- [ ] `[AI]` Convert notes into a structured adjudication table.
- [ ] `[REVIEW]` Resolve conflicts between AI extraction and human reading.
- [ ] `[DOC]` Update `docs/BOVINE_CORPUS_MANIFEST.md`.

Recommended review order:

1. Beefy-9 benchmark, FGF2 reduction, and albumin dose/cost.
2. Chemically defined bovine medium and differentiation capacity.
3. Commercial serum-free medium benchmarks.
4. Spent-media species and cell-type dependence.
5. DOE/RSM bovine serum-free media.
6. Albumin substitutes, protein isolates, and hydrolysates.
7. Safety and cost annotations.

Gate S4 passes when every non-exploratory variable entering the first design
batch has human-reviewed support.

### S5. Search-Space Design

Purpose: define what the optimizer may change.

Checklist:

- [ ] `[AI]` Build candidate variable classes from reviewed evidence.
- [ ] `[AI]` Assign a mechanism class to every variable.
- [ ] `[AI]` Add cost class, animal-origin status, food-grade plausibility, and
  supplier risk.
- [ ] `[HUMAN]` Confirm which reagents are available and acceptable.
- [ ] `[LAB]` Confirm cell source, baseline medium, plate format, assay
  duration, and throughput.
- [ ] `[REVIEW]` Remove variables with unsupported mechanism, undisclosed
  composition, or unacceptable risk.

Candidate variable classes should normally be limited to 4-6 classes, such as:

- basal medium choice or simplification;
- FGF2 concentration;
- insulin, transferrin, and selenium axis;
- albumin or albumin substitute;
- lipid or fatty-acid carrier;
- amino-acid or metabolic supplement;
- evidence-gated hydrolysate or extract.

Gate S5 passes when the search space is bounded, controllable, purchasable, and
evidence-supported.

### S6. In-Silico Robustness

Purpose: test whether the proposed design is robust to retrieval and optimizer
choices.

Checklist:

- [ ] `[AI]` Compare BM25 and embedding retrieval evidence clusters.
- [ ] `[AI]` Compare q-ParEGO and qLogNEHVI design suggestions.
- [ ] `[AI]` Run leave-one-source-out sensitivity for critical variable classes.
- [ ] `[AI]` Generate the first candidate formulation table.
- [ ] `[REVIEW]` Check duplicates, unsafe extrapolation, unsupported claims, and
  dominated candidates.
- [ ] `[HUMAN]` Approve or revise variables and controls.

Gate S6 passes when:

- top variable classes overlap by at least 70% across retrieval and optimizer
  perturbations;
- no non-exploratory critical variable depends on only one paper;
- disagreements are documented;
- the first batch includes controls and avoids near-duplicates.

### S7. Wet-Lab Pre-Registration

Purpose: freeze the experiment before results exist.

Checklist:

- [ ] `[AI]` Draft the design packet.
- [ ] `[LAB]` Confirm reagent list and preparation constraints.
- [ ] `[LAB]` Confirm cell source, passage window, seeding density, culture
  duration, media-change schedule, plate format, and replicate count.
- [ ] `[HUMAN]` Confirm primary and secondary endpoints.
- [ ] `[REVIEW]` Freeze candidate formulations before any result is known.
- [ ] `[DOC]` Commit the design packet.

Minimum design packet:

- biological target and scope statement;
- literature inclusion and exclusion criteria;
- candidate formulation table;
- positive, negative, and baseline controls;
- endpoint definitions;
- replicate plan;
- stopping and failure criteria;
- analysis plan;
- caveats and unsupported claims;
- exact citations supporting each variable.

Gate S7 passes when the design packet is committed before wet-lab work starts.

### S8. Wet-Lab Execution

Purpose: execute the frozen design without changing the question mid-run.

Checklist:

- [ ] `[LAB]` Prepare cells and reagents according to the frozen protocol.
- [ ] `[LAB]` Record plate map, reagent lots, operator, passage number, seeding
  density, and timing.
- [ ] `[LAB]` Store raw measurements and raw images where applicable.
- [ ] `[HUMAN]` Record deviations immediately.
- [ ] `[REVIEW]` Decide whether deviations invalidate, qualify, or simply
  annotate the run.
- [ ] `[DOC]` Commit metadata and result manifests. Store large raw files outside
  git unless storage policy changes.

Gate S8 passes when the run is completed or stopped with deviations and raw data
recorded.

### S9. Result Comparison

Purpose: compare measured results against controls and objectives.

Checklist:

- [ ] `[AI]` Load raw results into a structured table.
- [ ] `[AI]` Normalize within the experiment only.
- [ ] `[AI]` Compute primary endpoint, secondary endpoints, and cost estimates.
- [ ] `[AI]` Compare candidates against baseline and positive controls.
- [ ] `[AI]` Update the Pareto front for proliferation, cost, and identity
  retention.
- [ ] `[HUMAN]` Review whether statistical results match biological
  interpretation.
- [ ] `[REVIEW]` Label each claim as `supported`, `partial`, `unsupported`, or
  `exploratory`.

Gate S9 passes when results are processed, compared, and claim labels are
reviewed.

### S10. Closed-Loop Update

Purpose: decide whether and how to run another round.

Checklist:

- [ ] `[AI]` Feed measured objective values into `optimize.tell()`.
- [ ] `[AI]` Generate the next candidate batch or stop recommendation.
- [ ] `[REVIEW]` Check whether the model is exploiting, exploring, or repeating
  failed regions.
- [ ] `[HUMAN]` Decide whether to continue, narrow the search space, add an
  assay, or stop.
- [ ] `[DOC]` Commit the round summary and next-round design packet if
  continuing.

Gate S10 passes when the next action is documented.

### S11. Manuscript Audit

Purpose: turn the system and experiments into a defensible paper workflow.

Checklist:

- [ ] `[AI]` Generate final tables: corpus, evidence, variables, formulations,
  results, Pareto comparison, and sensitivity checks.
- [ ] `[AI]` Generate figures: workflow, evidence map, variable support,
  experimental outcomes, Pareto front, and closed-loop trajectory.
- [ ] `[HUMAN]` Write biological interpretation and limitations.
- [ ] `[REVIEW]` Audit every claim against evidence and wet-lab data.
- [ ] `[REVIEW]` Report negative or inconclusive results honestly.
- [ ] `[DOC]` Archive code commit, data manifests, analysis scripts, and protocol
  versions.

Gate S11 passes when paper claims are traceable to evidence and results.

## 8. Parallel Work Plan

Human stream:

- Review `H001-H016`.
- Confirm cell source and assay constraints.
- Confirm reagent availability and budget limits.
- Approve candidate variable classes.
- Sign off on pre-registration before wet-lab work.

AI stream:

- Pull and organize P1 full texts.
- Extract component tables, dose ranges, endpoints, and quotes.
- Build `data/literature/bovine_evidence_table.tsv`.
- Convert human notes into adjudicated evidence records.
- Generate candidate variable classes.
- Run retrieval and optimizer robustness checks.
- Draft design packets and analysis reports.

Lab stream:

- Confirm cell source, passage limits, and culture constraints.
- Confirm control media and assay protocol.
- Confirm throughput: number of conditions and replicates per round.
- Execute only frozen, committed designs.
- Return raw results in an agreed structured format.

## 9. Current Project Record

Update this section after major sessions.

### 9.1 Completed

- Repository is a CLI-first Python package.
- Latest validation: `.venv/bin/python -m pytest -q` reports 26 passed with 3
  known warnings.
- Smoke pipeline passes.
- Demo optimization loop passes.
- Extraction evaluator exists.
- Offline four-paper evaluation fixture exists.
- Embedding retriever exists.
- BoTorch qNEHVI and qLogNEHVI backends exist.
- Optional citation verifier exists.
- Ontology-to-search-space handling includes hydrolysates, extracts, defined
  supplements, albumin substitutes, amino acids, carbon sources, and trace
  elements.
- Live provider mode exists for extraction evaluation.
- Parser accepts both A-M block letters and schema attribute block names.
- Structured-paper schema and plain-text fallback exist; extractor can route
  block-specific context through structured sections and records routing
  metadata.
- First wet-lab-facing target is documented.
- Bovine manifest v0 contains 44 records.
- Human review queue v0 contains 30 open tasks.
- English and Chinese operating manuals exist.
- AI-for-science method review exists and identifies S3 full-text extraction
  reliability as the current highest-value technical bottleneck.

### 9.2 Known Problems

- Live OpenAI/Anthropic extraction was too sparse to count as successful model
  agreement.
- Gemini live comparison is incomplete because no Gemini/Google key was
  available.
- OpenAI raw-response debugging hit insufficient quota.
- The current corpus manifest is not yet full-text extracted.
- Optional GROBID/TEI import is not implemented; current structured-paper support
  is the plain-text fallback plus schema placeholders for tables and figures.
- The human review queue is still open.
- Cost, supplier, and food-grade annotations are incomplete.
- In-silico robustness has not been run on the bovine manifest.
- No wet-lab design packet has been generated or frozen.
- No wet-lab results exist.

### 9.3 Immediate Next Actions

1. `[AI]` Add optional GROBID/TEI import or another structured PDF backend.
2. `[AI]` Pull full text for all P1 core records.
3. `[AI]` Extract exact formulations, dose ranges, endpoints, and quotes.
4. `[HUMAN]` Review H001-H016.
5. `[AI]` Build the adjudicated bovine evidence table.
6. `[REVIEW]` Decide which variables can enter the first search space.
7. `[AI]` Draft the first design packet only after earlier gates pass.

Current algorithm roadmap:

- Follow `docs/AI_FOR_SCIENCE_METHOD_REVIEW.md`.
- Prioritize structured-paper objects, section-routed extraction, operator-level
  coverage/grounding metrics, and human-review integration before new wet-lab
  proposal generation.

## 10. AI Handoff Protocol

When another AI agent resumes the project:

1. Read `README.md`.
2. Read this manual or `docs/PROJECT_WORKFLOW_ZH.md`.
3. Read `docs/SESSION_LOG.md`.
4. Read `docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md`.
5. Read `docs/BOVINE_CORPUS_MANIFEST.md`.
6. Run `git status --short --branch`.
7. Continue from the next failed gate.

Suggested handoff prompt:

```text
Continue CultivateAgent using docs/PROJECT_WORKFLOW.md as the controlling
workflow. Preserve the current bovine satellite-cell/myoblast expansion-medium
scope unless you create a documented scope-change decision record. Start by
checking git status, then advance the next failed gate. Do not overwrite human
review notes.
```
