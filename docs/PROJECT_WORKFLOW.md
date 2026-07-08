# CultivateAgent Project Manual

Status: active  
Last updated: 2026-07-08
Chinese version: [`PROJECT_WORKFLOW_ZH.md`](PROJECT_WORKFLOW_ZH.md)

> **Session 2 additions (see `SESSION_LOG.md`).** Two new stages sit between
> extraction and optimization: (1) **operator extraction** — `cultivate extract
> --mode operators` splits the A–M schema into small section-routed operators
> (more reliable with real LLMs); (2) **evidence synthesis** — `cultivate evidence
> --outcome <o>` pools heterogeneous cross-paper effects via random-effects
> meta-analysis into `P(component beneficial)`+I² posteriors, stored in the KB and
> injected into `cultivate optimize --evidence-prior` as πBO priors (never labels;
> high-I² components are flagged "test directly"). Details:
> [`EVIDENCE_SYNTHESIS.md`](EVIDENCE_SYNTHESIS.md), [`OPTIMIZATION.md`](OPTIMIZATION.md).

This is the controlling project manual for CultivateAgent. It is written for
developers, literature reviewers, wet-lab collaborators, project owners, and AI
agents that need to continue the same project without creating conflicting
records.

## 0. How To Use This Manual

Use this document as a map, not as a daily notebook.

| Need | Go to |
|---|---|
| Understand the project | Sections 1-3 |
| Know who should do what | Section 4 |
| Find the right artifact to edit | Section 5 |
| See the whole thesis workflow | Section 6 |
| Execute a specific stage | Section 7 |
| Work in parallel with AI, human reviewers, and lab collaborators | Section 8 |
| Check current progress, blockers, and next actions | Section 9 |
| Hand the project to another AI or teammate | Section 10 |

Documentation rule:

- Sections 1-8 define the stable operating process.
- Section 9 is the current project ledger and should be updated after material
  work sessions.
- New scientific decisions belong in separate decision records under `docs/`.
- `docs/SESSION_LOG.md` remains the chronological log.
- Human review notes must not be overwritten by AI-generated text.

This structure follows these documentation references:

- [Diataxis](https://diataxis.fr/) for separating explanation, how-to,
  tutorial-like onboarding, and reference material.
- [Google developer documentation style guide](https://developers.google.com/style)
  for clear, task-oriented writing.
- [Microsoft Learn contributor guide](https://learn.microsoft.com/en-us/contribute/)
  for maintainable documentation ownership and update flow.
- [GitLab documentation style guide](https://docs.gitlab.com/development/documentation/styleguide/)
  for topic-based, scannable documentation.

## 1. Project Definition

CultivateAgent is a CLI-first literature-mining and optimization system for
cultivated-meat culture-medium design. It adapts the ReactionSeek pattern to a
wet-lab-ready cultivated-meat workflow:

1. collect and triage literature;
2. extract structured facts with LLMs and deterministic grounding checks;
3. normalize components, doses, units, species, cell type, and endpoints;
4. store evidence in a queryable knowledge base;
5. retrieve evidence for a locked biological target;
6. generate cited medium-formulation hypotheses;
7. select bounded wet-lab batches with multi-objective Bayesian optimization;
8. compare wet-lab results and close the loop.

Locked first wet-lab-facing target:

> Bovine satellite cells / bovine myoblasts in the expansion phase, optimizing
> serum-free, preferably animal-component-free, cost-aware medium variables while
> preserving myogenic identity.

First-round scope:

| In scope | Out of scope for round 1 |
|---|---|
| Medium variables for bovine muscle-cell expansion | Scaffold, microcarrier, perfusion, bioreactor |
| Serum-free and animal-component-free evidence | Genetic engineering and stable cell-line engineering |
| Cost and supply plausibility | Whole-cut texture and sensory testing |
| Myogenic identity retention endpoints | Primary differentiation-medium optimization |

Scope changes require a new decision record before downstream files are edited.

## 2. Deliverable Model

Current delivery surface:

- CLI commands: `cultivate ingest`, `cultivate extract`, `cultivate export`,
  `cultivate design`, `cultivate optimize`.
- Primary artifacts: Markdown, TSV, CSV, JSONL, SQLite, and evaluation reports.
- No production web UI exists. A dashboard can be added later, but it is not the
  current expected output.

Wet-lab entry is not allowed until the evidence and design gates in Sections 7
and 9 pass.

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
    ingest/                         BibTeX, PDF, text, and structured-paper ingestion
    triage/                         paper screening and A/B/C tiering
    extract/                        LLM prompts, JSON parsing, grounding checks
    schema/                         A-M schema, evidence models, structured paper objects
    normalize/                      component and unit normalization
    kb/                             SQLite knowledge base and exports
    retrieve/                       BM25 and optional embedding retrieval
    design/                         evidence-grounded medium recommender
    optimize/                       search space, surrogate model, MOBO loop
    evaluate/                       extraction scoring and model agreement
    llm/                            OpenAI, Anthropic, Gemini, and mock clients
  scripts/
    ingest_pdfs.py                   ingest loose PDF folders/lists without BibTeX
    run_evidence_parallel.py         parallel effect extraction over ingested papers
    evaluate_medium_corpus.py       extraction and agreement benchmark
    compare_mobo_backends.py        optimizer backend comparison
  data/
    library.example.bib             example BibTeX file
    literature/
      bovine_corpus_manifest.tsv    curated bovine literature metadata
      bovine_human_review_queue.tsv human adjudication queue
      ai_for_science_method_sources.tsv method-source registry
  docs/
    PROJECT_WORKFLOW.md             this manual
    PROJECT_WORKFLOW_ZH.md          Chinese version
    AI_COLLABORATION_PROTOCOL.md    Codex/Claude concurrent-work protocol
    SESSION_LOG.md                  chronological work log
    ARCHITECTURE.md                 technical architecture
    OPTIMIZATION.md                 optimization design
    AI_FOR_SCIENCE_METHOD_REVIEW.md AI-for-science method review
    LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md
    BOVINE_CORPUS_MANIFEST.md
    REVIEW_BY_NEXT_ENGINEER.md
```

## 4. Roles And Decision Rights

Use these labels in tasks, review notes, commits, and handoffs.

| Label | Actor | Decision rights |
|---|---|---|
| `[HUMAN]` | Project owner or domain reviewer | Biological scope, evidence adjudication, wet-lab go/no-go |
| `[AI]` | Codex, Claude, or another AI agent | Search, extraction, coding, draft reports, structured tables |
| `[LAB]` | Wet-lab collaborator | Cell source, reagent feasibility, protocol execution |
| `[REVIEW]` | Assigned reviewer | Gate checks, conflict resolution, claim audit |
| `[DOC]` | Any contributor | Traceable documentation update |

Rules:

- AI may prepare evidence; humans approve scientific use.
- AI must record uncertainty instead of inventing missing data.
- AI must not overwrite human notes.
- Wet-lab design packets must be committed before results are known.
- Results must not be used to retroactively edit pre-registration.
- Large PDFs, raw images, SQLite databases, and raw instrument files stay out of
  git unless a separate storage policy approves them.

## 5. Artifact Registry

| Artifact | Path | Owner | Update trigger |
|---|---|---|---|
| Operating manual | `docs/PROJECT_WORKFLOW.md`, `docs/PROJECT_WORKFLOW_ZH.md` | `[DOC]` | Process changes or major status update |
| AI collaboration protocol | `docs/AI_COLLABORATION_PROTOCOL.md` | `[AI]` + `[DOC]` | Concurrent-agent coordination rules or conflict-prone workflow changes |
| Chronological log | `docs/SESSION_LOG.md` | `[AI]` | Each substantial work session |
| Wet-lab target decision | `docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md` | `[HUMAN]` + `[AI]` | Target or scope change |
| Corpus manifest | `data/literature/bovine_corpus_manifest.tsv` | `[AI]` + `[REVIEW]` | Source status change |
| Human review queue | `data/literature/bovine_human_review_queue.tsv` | `[HUMAN]` + `[AI]` | Evidence adjudication |
| Corpus summary | `docs/BOVINE_CORPUS_MANIFEST.md` | `[AI]` | Manifest or gate change |
| Method-source registry | `data/literature/ai_for_science_method_sources.tsv` | `[AI]` + `[REVIEW]` | Algorithm or pipeline decision |
| Method review | `docs/AI_FOR_SCIENCE_METHOD_REVIEW.md` | `[AI]` + `[REVIEW]` | Method decision |
| Extraction reports | `docs/EVAL_RESULTS.md`, `docs/MODEL_AGREEMENT.md` | `[AI]` | Evaluation run |
| Optimization report | `docs/OPTIMIZATION_BENCHMARK.md` | `[AI]` | Optimizer benchmark |
| Evidence table | `data/literature/bovine_evidence_table.tsv` | `[AI]` + `[REVIEW]` | Full-text extraction and review |
| Candidate variables | `docs/CANDIDATE_VARIABLES.md` | `[AI]` + `[HUMAN]` | Evidence review completion |
| Wet-lab design packet | `docs/wetlab/ROUND_<n>_DESIGN_PACKET.md` | `[AI]` + `[LAB]` + `[REVIEW]` | Before each wet-lab round |
| Wet-lab results | `docs/wetlab/ROUND_<n>_RESULTS.md` | `[AI]` + `[LAB]` | After each wet-lab round |

## 6. Lifecycle Overview

| Stage | Name | Main output | Current status |
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

Only advance a stage when its gate is satisfied or the blocker is explicitly
recorded.

## 7. Stage Checklists

### S0. Environment Setup

Purpose: make the repository reproducible.

Checklist:

- [ ] `[AI]` Create or activate the Python environment.
- [ ] `[AI]` Install dependencies and the package in editable mode.
- [ ] `[AI]` Run unit tests.
- [ ] `[AI]` Run the smoke pipeline.
- [ ] `[AI]` Run demo optimization.
- [ ] `[HUMAN]` Confirm API-key policy for live providers.
- [ ] `[DOC]` Record failures and fixes in `docs/SESSION_LOG.md`.

Commands:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
.venv/bin/python -m pytest -q
.venv/bin/python -m cultivate_agent.cli smoke
.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6
```

Gate: tests, smoke, and demo optimization pass, or blockers are recorded with a
repair plan.

### S1. Scope Lock

Purpose: prevent the first wet-lab round from becoming too broad to interpret.

Checklist:

- [x] `[AI]` Review recent cultivated-meat medium and cell-biology literature.
- [x] `[AI]` Propose the first wet-lab-facing target.
- [x] `[REVIEW]` Separate in-scope and out-of-scope work.
- [x] `[DOC]` Record the target in a decision record.

Gate: target, boundaries, and scope-change rules are documented.

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

Wet-lab entry gate:

- 35-50 peer-reviewed sources are curated.
- At least 8 are recent reviews or scoping papers.
- At least 12 are primary medium or cell-culture papers.
- At least 10 are bovine satellite-cell or myoblast relevant.
- At least 5 include extractable dose or range information.
- At least 3 report serum-free or animal-component-free bovine muscle-cell
  culture.
- Background-only sources are excluded from wet-lab evidence counts.

### S3. Full-Text Extraction

Purpose: convert papers into structured, grounded data.

Checklist:

- [ ] `[AI]` Ingest BibTeX, PDFs, full text, or externally generated structured
  paper files.
- [ ] `[AI]` Prefer structured parsing when available: GROBID TEI, structured
  text sections, or future PDF backends.
- [ ] `[AI]` When a GROBID service is available, run `cultivate ingest
  --grobid-tei` so PDFs produce `fulltext.xml` before extraction.
- [ ] `[AI]` Run triage and extraction on P1/P2 sources.
- [ ] `[AI]` Export screening, component, evidence, and extraction tables.
- [ ] `[AI]` Run `cultivate evidence-audit` on extracted effect items before
  proposing wet-lab variables.
- [ ] `[AI]` Record extraction coverage, non-missing fields, and grounding rate.
- [ ] `[REVIEW]` Flag sparse or unreliable extraction runs.
- [ ] `[AI]` Repair parser or prompt issues only when evidence shows a technical
  failure rather than missing source content.

Commands:

```bash
cultivate ingest
# optional, when a GROBID service is running:
cultivate ingest --grobid-tei --grobid-url http://localhost:8070
cultivate triage
cultivate extract --tier A
cultivate export
cultivate evidence-audit --outcome proliferation --out docs/EVIDENCE_AUDIT_PROLIFERATION.md
```

Gate:

- Evidence quote grounding rate is at least 0.95 for top-ranked records.
- Non-missing fraction is at least 0.75 for species, cell type, stage, medium
  type, serum-free status, component identity, dose/range, and endpoint.
- Evidence audit is not `NO-GO` for the target outcome.
- Every component entering the design space links to a source quote and a
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

1. Beefy-9 benchmark, FGF2 reduction, albumin dose/cost.
2. Chemically defined bovine medium and differentiation capacity.
3. Commercial serum-free medium benchmarks.
4. Spent-media species and cell-type dependence.
5. DOE/RSM bovine serum-free media.
6. Albumin substitutes, protein isolates, and hydrolysates.
7. Safety and cost annotations.

Gate: every non-exploratory variable entering the first design batch has
human-reviewed support, and `docs/EVIDENCE_AUDIT_PROLIFERATION.md` has no
open wet-lab entry blockers.

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

Gate: the search space is bounded, controllable, purchasable, and
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

Gate:

- Top variable classes overlap by at least 70% across retrieval and optimizer
  perturbations.
- No non-exploratory critical variable depends on only one paper.
- Disagreements are documented.
- The first batch includes controls and avoids near-duplicates.

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

- Biological target and scope statement.
- Literature inclusion and exclusion criteria.
- Candidate formulation table.
- Positive, negative, and baseline controls.
- Endpoint definitions.
- Replicate plan.
- Stopping and failure criteria.
- Analysis plan.
- Caveats and unsupported claims.
- Exact citations supporting each variable.

Gate: the design packet is committed before wet-lab work starts.

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
- [ ] `[DOC]` Commit metadata and result manifests. Store large raw files
  outside git unless storage policy changes.

Gate: the run is completed or stopped with deviations and raw data recorded.

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

Gate: results are processed, compared, and reviewed.

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

Gate: the next action is documented.

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
- [ ] `[DOC]` Archive code commit, data manifests, analysis scripts, and
  protocol versions.

Gate: paper claims are traceable to evidence and results.

## 8. Parallel Work Protocol

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
- Draft design packets and analysis reports after gates pass.

Lab stream:

- Confirm cell source, passage limits, and culture constraints.
- Confirm control media and assay protocol.
- Confirm throughput: number of conditions and replicates per round.
- Execute only frozen, committed designs.
- Return raw results in an agreed structured format.

Parallel rule: human review, AI extraction hardening, and lab feasibility checks
can run at the same time. Wet-lab execution cannot start until S7 passes.

## 9. Current Project Ledger

Update this section after major sessions. Do not scatter status updates through
the procedural sections above.

### 9.1 Stage Ledger

| Stage | Done | Open problems | Next action |
|---|---|---|---|
| S0 | Package installs, tests pass, smoke passes, demo optimization passes | Optional provider credentials and quotas are external | Keep gates green after each change |
| S1 | Wet-lab target and boundaries recorded | Scope must remain locked unless decision record changes | Preserve bovine expansion-medium focus |
| S2 | 44-record bovine manifest and 30-task review queue created | P1 human review and full-text acquisition incomplete | Human reviews H001-H016; AI pulls P1 full text |
| S3 | Structured paper schema, plain-text fallback, section routing, GROBID TEI parser, and optional GROBID service client exist | P1 corpus has not been batch-converted/extracted; GROBID service availability is external | Run `cultivate ingest --grobid-tei` on accessible P1 PDFs, then extract |
| S4 | Review queue exists | No adjudicated evidence table yet | Convert human notes into structured adjudication |
| S5 | Ontology can expose more component classes to search space | Candidate variables not approved | Build only after S3-S4 gates |
| S6 | MOBO backends and benchmark script exist | Robustness not run on bovine evidence | Run retrieval and optimizer sensitivity after S5 |
| S7 | Pre-registration format defined | No design packet frozen | Draft after evidence and robustness gates |
| S8 | Execution record requirements defined | No wet-lab run | Wait for S7 |
| S9 | Analysis requirements defined | No wet-lab results | Wait for S8 |
| S10 | Closed-loop update requirements defined | No measured objectives | Wait for S9 |
| S11 | Manuscript audit requirements defined | No final claims or figures | Wait for validated results |

### 9.2 Completed Technical Work

- CLI-first Python package exists.
- Latest validation: `.venv/bin/python -m pytest -q` reports 51 passed with 3
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
- Live-run ontology gaps have been partially closed for SFB, SFGM, Beefy-R,
  rapeseed-protein isolate, Grifola frondosa extract, Auxenochlorella
  pyrenoidosa protein extract, and copper ions. These are normalization hooks,
  not wet-lab approval.
- Trace-element search bounds were widened from nM to 0-10 uM so the optimizer
  can represent copper-ion evidence reported around 5 uM; this is a broad search
  bound, not a recommended dose.
- Live provider mode exists for extraction evaluation.
- Parser accepts both A-M block letters and schema attribute block names.
- Structured-paper schema and plain-text fallback exist.
- Extractor can route block-specific context through structured sections and
  records routing metadata.
- GROBID-flavored TEI XML can be parsed into `StructuredPaper` when TEI has
  already been generated externally.
- `cultivate ingest --grobid-tei` can call a running GROBID service, save
  `fulltext.xml`, and `cultivate extract` will use that TEI for structured
  section routing.
- `scripts/ingest_pdfs.py` can ingest loose PDF folders/lists when BibTeX is not
  available.
- `scripts/run_evidence_parallel.py` can generate effect-item exports across the
  ingested corpus for later synthesis and audit.
- `cultivate evidence` now writes raw `effect_items_<outcome>.json` next to the
  synthesized evidence CSV so audits can be rerun without another LLM call.
- `cultivate evidence-audit` can inspect extracted `EvidenceItem` JSON and
  produce a conservative wet-lab entry gate report.

### 9.3 Completed Literature And Planning Work

- First wet-lab-facing target is documented.
- Bovine manifest v0 contains 44 records.
- Human review queue v0 contains 30 open tasks.
- AI-for-science method review exists.
- Method-source registry contains reviewed sources across autonomous labs,
  scientific RAG, information extraction, document parsing, ETL, and Bayesian
  optimization.
- Current method decision: prioritize S3 full-text extraction reliability and
  S4 evidence audit/human review before new wet-lab design generation.

### 9.4 Known Blockers And Risks

- Live OpenAI/Anthropic extraction was too sparse to count as successful model
  agreement.
- Gemini live comparison is incomplete because no Gemini/Google key was
  available.
- OpenAI raw-response debugging hit insufficient quota.
- The current corpus manifest is not yet full-text extracted.
- GROBID service availability is external; if no service is running, ingestion
  keeps the plain-text fallback and records the failure as a warning.
- Human review queue remains open.
- Current proliferation evidence audit is `NO-GO`: local extracted evidence has
  AI-review candidates, but all are direction-only and 16/16 critical human
  review tasks remain open.
- Cost, supplier, and food-grade annotations are incomplete.
- Newly added ontology entries from the live run still need human evidence
  adjudication before they can become non-exploratory wet-lab variables.
- In-silico robustness has not been run on the bovine manifest.
- No wet-lab design packet has been generated or frozen.
- No wet-lab results exist.

### 9.5 Immediate Next Actions

1. `[AI]` Run optional GROBID TEI generation on accessible P1 PDFs with
   `cultivate ingest --grobid-tei`, then inspect coverage.
2. `[AI]` Pull full text for all P1 core records.
3. `[AI]` Re-run evidence extraction/normalization on live/P1 sources after the
   ontology update and inspect which components now pool correctly.
4. `[AI]` Re-run `cultivate evidence-audit` after updated extraction outputs.
5. `[AI]` Extract exact formulations, dose ranges, endpoints, and quotes for
   the audit candidates.
6. `[HUMAN]` Review `H001-H016`.
7. `[AI]` Build the adjudicated bovine evidence table.
8. `[REVIEW]` Decide which variables can enter the first search space.
9. `[AI]` Draft the first design packet only after earlier gates pass.

## 10. AI Handoff Protocol

When another AI agent resumes the project:

1. Read `README.md`.
2. Read `docs/AI_COLLABORATION_PROTOCOL.md`.
3. Read this manual or `docs/PROJECT_WORKFLOW_ZH.md`.
4. Read `docs/SESSION_LOG.md`.
5. Read `docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md`.
6. Read `docs/BOVINE_CORPUS_MANIFEST.md`.
7. Run `git fetch --all --prune` and `git status --short --branch`.
8. Continue from the next failed gate in Section 9.1 without touching
   untracked files owned by another agent.

Suggested handoff prompt:

```text
Continue CultivateAgent using docs/PROJECT_WORKFLOW.md as the controlling
manual and docs/AI_COLLABORATION_PROTOCOL.md as the concurrent-agent protocol.
Preserve the bovine satellite-cell/myoblast expansion-medium scope unless you
create a documented scope-change decision record. Start by fetching, checking
git status, and identifying untracked files, then advance the next failed gate.
Do not overwrite human review notes, another agent's files, or invent missing
evidence.
```
