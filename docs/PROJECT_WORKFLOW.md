# CultivateAgent Project Workflow

Status: active
Last updated: 2026-07-09
Chinese version: [`PROJECT_WORKFLOW_ZH.md`](PROJECT_WORKFLOW_ZH.md)

This is the controlling workflow manual for CultivateAgent. It is for software
developers, literature reviewers, wet-lab collaborators, project owners, and AI
agents that need to continue the same thesis project without conflicting
changes.

## 0. Documentation Contract

This manual is organized so that stable process and changing status do not
overwrite each other.

| Section | Purpose | Update frequency |
|---|---|---|
| 0-4 | Orientation, project boundaries, repository map, ownership rules | Rarely; only when the project structure or decision rights change |
| 5-6 | End-to-end workflow and stage gates | When a gate, required artifact, or review rule changes |
| 7 | Parallel human/AI/lab work plan | When team responsibilities change |
| 8 | Current project ledger | After material work sessions |
| 9 | Handoff protocol | When another AI or teammate needs a different entry path |

Detailed daily history belongs in [`SESSION_LOG.md`](SESSION_LOG.md). New
scientific or methodological decisions belong in a separate decision record under
`docs/`. Human review notes must not be overwritten by AI-generated text.

Documentation standards used for this revision:

- [Google developer documentation style guide](https://developers.google.com/style):
  clear and consistent technical documentation, with project-specific style
  taking priority.
- [Microsoft Writing Style Guide](https://learn.microsoft.com/en-us/style-guide/welcome/):
  concise technical writing for mixed technical audiences.
- [Microsoft reference documentation guidance](https://learn.microsoft.com/en-us/style-guide/developer-content/reference-documentation):
  predictable headings and consistent structure so developers can find facts
  quickly.
- [Diataxis](https://diataxis.fr/start-here/): separation of explanation,
  how-to guidance, reference, and learning material.
- [GOV.UK user-needs guidance](https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/plan-manage-content/identify-user-needs/):
  write around real user tasks and acceptance criteria.

## 1. Project At A Glance

CultivateAgent is a CLI-first literature-mining and optimization system for
cultivated-meat culture-medium design. It adapts a ReactionSeek-like scientific
mining pattern to a medium-centered wet-lab workflow:

```text
ingest -> triage -> extract -> normalize -> knowledge base -> retrieve -> design -> optimize
```

The system does not treat cross-paper outcome numbers as directly comparable
training labels. Literature evidence defines search regions, priors, caveats,
and candidate rationales. Objective values for optimization must come from the
project's own wet-lab measurements through the closed-loop `tell()` path.

Locked first wet-lab-facing target:

> Bovine satellite cells / bovine myoblasts in the expansion phase, optimizing
> serum-free, preferably animal-component-free, cost-aware medium variables while
> preserving myogenic identity.

Round-1 scope:

| In scope | Out of scope unless a new decision record approves it |
|---|---|
| Culture-medium variables for bovine muscle-cell expansion | Scaffold, microcarrier, perfusion, and bioreactor optimization |
| Serum-free and animal-component-free medium evidence | Genetic engineering and stable cell-line engineering |
| Dose/range, endpoint, cost, and supply plausibility | Whole-cut texture, sensory testing, and product formulation |
| Myogenic identity retention endpoints | Primary optimization of differentiation medium |

Scope changes require a new decision record before downstream files are edited.

## 2. Delivery Surface

Current expected delivery is local, file-based, and CLI-first.

| Surface | Current status |
|---|---|
| CLI | `cultivate ingest`, `triage`, `extract`, `evidence`, `evidence-audit`, `review-packet`, `export`, `design`, `optimize` |
| Artifacts | Markdown reports, TSV/CSV tables, JSON/JSONL records, SQLite knowledge base |
| Web UI | Not implemented and not required for the current thesis workflow |
| Wet-lab entry | Blocked until evidence, human-review, search-space, robustness, and pre-registration gates pass |

The README is the quickstart. This document is the operating manual. The session
log is the chronological record.

## 3. Repository Map

```text
CultivateAgent/
  README.md                         overview and CLI quickstart
  pyproject.toml                    package metadata and optional dependencies
  requirements.txt                  default runtime dependencies
  config/
    config.example.yaml             runtime configuration template
    ontology/                       component ontology seeds and normalization hooks
  cultivate_agent/
    cli.py                          command-line entrypoint
    ingest/                         BibTeX, PDF, text, GROBID TEI/JATS XML ingestion
    triage/                         paper screening and A/B/C tiering
    extract/                        prompts, operator extraction, grounding checks
    schema/                         A-M schema, evidence models, paper objects
    normalize/                      component names and units
    kb/                             SQLite store and export helpers
    evidence/                       effect extraction, synthesis, audit, review packet
    retrieve/                       BM25 and optional embedding retrieval
    design/                         evidence-grounded medium recommender
    optimize/                       search space, surrogate model, MOBO loop
    evaluate/                       extraction scoring and model agreement
    llm/                            provider-agnostic LLM clients and mock client
  scripts/
    ingest_pdfs.py                  ingest loose PDF folders/lists
    run_evidence_parallel.py        parallel evidence extraction helper
    evaluate_medium_corpus.py       extraction and provider-agreement benchmark
    compare_mobo_backends.py        optimizer backend comparison
  data/literature/
    bovine_corpus_manifest.tsv      curated bovine literature metadata
    bovine_human_review_queue.tsv   human adjudication queue
    ai_for_science_method_sources.tsv method-source registry
  docs/
    PROJECT_WORKFLOW.md             this manual
    PROJECT_WORKFLOW_ZH.md          Chinese manual
    AI_COLLABORATION_PROTOCOL.md    Codex/Claude concurrent-work protocol
    SESSION_LOG.md                  chronological work log
    ARCHITECTURE.md                 technical architecture
    OPTIMIZATION.md                 optimization design
    EVIDENCE_SYNTHESIS.md           random-effects evidence synthesis design
    BOVINE_CORPUS_MANIFEST.md       corpus status and gates
    EVIDENCE_AUDIT_PROLIFERATION.md current conservative wet-lab-entry audit
    HUMAN_REVIEW_PACKET_H001_H016.md first human review locator packet
    LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md first target decision
    AI_FOR_SCIENCE_METHOD_REVIEW.md method review and algorithm roadmap
```

## 4. Roles, Rights, And Artifacts

Use these labels in issues, notes, tables, commits, and handoffs.

| Label | Actor | Decision rights |
|---|---|---|
| `[HUMAN]` | Project owner or domain reviewer | Biological scope, evidence adjudication, wet-lab go/no-go |
| `[AI]` | Codex, Claude, or another AI agent | Search, extraction, coding, draft reports, structured tables |
| `[LAB]` | Wet-lab collaborator | Cell source, reagent feasibility, protocol execution |
| `[REVIEW]` | Assigned reviewer | Gate checks, conflict resolution, claim audit |
| `[DOC]` | Any contributor | Traceable documentation update |

Non-negotiable rules:

- AI may prepare evidence; humans approve scientific use.
- AI must record uncertainty instead of inventing missing data.
- AI must not overwrite human notes or another contributor's untracked work.
- Wet-lab design packets must be committed before results are known.
- Results must not be used to retroactively edit pre-registration.
- Large PDFs, raw images, SQLite databases, and instrument files stay out of git
  unless a separate storage policy approves them.

Artifact registry:

| Artifact | Path | Primary owner | Update trigger |
|---|---|---|---|
| Operating manual | `docs/PROJECT_WORKFLOW.md`, `docs/PROJECT_WORKFLOW_ZH.md` | `[DOC]` | Process or major status change |
| Collaboration protocol | `docs/AI_COLLABORATION_PROTOCOL.md` | `[AI]` + `[DOC]` | Concurrent-agent rule change |
| Chronological log | `docs/SESSION_LOG.md` | `[AI]` | Each substantial work session |
| Target decision | `docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md` | `[HUMAN]` + `[AI]` | Target or scope change |
| Corpus manifest | `data/literature/bovine_corpus_manifest.tsv` | `[AI]` + `[REVIEW]` | Source status change |
| Gate 1 corpus audit | `docs/BOVINE_CORPUS_GATE1_AUDIT.md`, `data/literature/bovine_corpus_gate1_issues.tsv` | `[AI]` + `[REVIEW]` | Manifest or review-status change |
| Human review queue | `data/literature/bovine_human_review_queue.tsv` | `[HUMAN]` + `[AI]` | Evidence adjudication update |
| Corpus summary | `docs/BOVINE_CORPUS_MANIFEST.md` | `[AI]` | Manifest or gate change |
| Method-source registry | `data/literature/ai_for_science_method_sources.tsv` | `[AI]` + `[REVIEW]` | Algorithm or pipeline decision |
| Method review | `docs/AI_FOR_SCIENCE_METHOD_REVIEW.md` | `[AI]` + `[REVIEW]` | Method decision |
| Extraction reports | `docs/EVAL_RESULTS.md`, `docs/MODEL_AGREEMENT.md` | `[AI]` | Evaluation run |
| Extraction readiness report | `docs/EXTRACTION_READINESS_H001_H016.md`, `docs/EXTRACTION_READINESS_H031_H033.md`, matching TSV files | `[AI]` + `[REVIEW]` | Before live operator extraction |
| Evidence audit | `docs/EVIDENCE_AUDIT_PROLIFERATION.md` | `[AI]` + `[REVIEW]` | Evidence export or gate update |
| Review packet | `docs/HUMAN_REVIEW_PACKET_H001_H016.md`, `docs/HUMAN_REVIEW_PACKET_H031_H033.md` | `[AI]` + `[HUMAN]` | Source availability or review queue update |
| Human adjudication worksheet | `data/literature/bovine_adjudication_H001_H014.tsv` | `[HUMAN]` + `[AI]` | Before and after human evidence review |
| Worksheet validation report | `docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md` | `[AI]` + `[REVIEW]` | After worksheet creation or edits |
| Worksheet status report | `docs/HUMAN_ADJUDICATION_STATUS_H001_H014.md` | `[AI]` + `[REVIEW]` | After worksheet creation or edits |
| Adjudicated evidence table | `data/literature/bovine_evidence_table.tsv` | `[HUMAN]` + `[AI]` + `[REVIEW]` | After valid human adjudication export |
| Candidate variables | `docs/CANDIDATE_VARIABLES.md` | `[AI]` + `[HUMAN]` | Human evidence review completion |
| Wet-lab design packet | `docs/wetlab/ROUND_<n>_DESIGN_PACKET.md` | `[AI]` + `[LAB]` + `[REVIEW]` | Before each wet-lab round |
| Wet-lab results | `docs/wetlab/ROUND_<n>_RESULTS.md` | `[AI]` + `[LAB]` | After each wet-lab round |

## 5. Thesis Lifecycle

The lifecycle is sequential at the gate level. Work inside a stage can be
parallelized, but wet-lab execution cannot start until S7 passes.

| Stage | Name | Primary output | Current status | Gate owner |
|---|---|---|---|---|
| S0 | Environment setup | Runnable repository | Pass | `[AI]` |
| S1 | Scope lock | Wet-lab target decision | Pass | `[HUMAN]` + `[REVIEW]` |
| S2 | Corpus construction | Bovine manifest and review queue | Partial | `[AI]` + `[REVIEW]` |
| S3 | Full-text extraction | Grounded evidence tables | Fail / incomplete | `[AI]` + `[REVIEW]` |
| S4 | Human evidence review | Adjudicated evidence table | Fail / open | `[HUMAN]` |
| S5 | Search-space design | Bounded candidate variables | Not started | `[HUMAN]` + `[REVIEW]` |
| S6 | In-silico robustness | Sensitivity and optimizer checks | Not started | `[AI]` + `[REVIEW]` |
| S7 | Wet-lab pre-registration | Frozen design packet | Not started | `[HUMAN]` + `[LAB]` + `[REVIEW]` |
| S8 | Wet-lab execution | Raw results and deviations | Not started | `[LAB]` |
| S9 | Result comparison | Processed results and Pareto analysis | Not started | `[AI]` + `[HUMAN]` |
| S10 | Closed-loop update | Next-round or stop decision | Not started | `[HUMAN]` + `[REVIEW]` |
| S11 | Manuscript audit | Paper-ready claims and artifacts | Not started | `[REVIEW]` |

Status terms:

- `Pass`: gate criteria are satisfied or the artifact exists.
- `Partial`: useful work exists, but required gate evidence is incomplete.
- `Fail / incomplete`: current evidence explicitly blocks advancement.
- `Not started`: downstream stage must wait for earlier gates.

## 6. Stage Checklists

### S0. Environment Setup

Goal: make the repository reproducible.

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

Goal: keep the first wet-lab round interpretable.

Checklist:

- [x] `[AI]` Review recent cultivated-meat medium and cell-biology literature.
- [x] `[AI]` Propose the first wet-lab-facing biological target.
- [x] `[REVIEW]` Separate in-scope and out-of-scope work.
- [x] `[DOC]` Record target, boundaries, and scope-change rules.

Gate: `docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md` documents the target and
boundaries.

### S2. Corpus Construction

Goal: create a traceable literature set before extraction and experiment design.

Checklist:

- [x] `[AI]` Create the bovine-focused corpus manifest.
- [x] `[AI]` Make Gate 1 counts, required metadata, and P1 human-curation status executable with `python scripts/audit_bovine_corpus.py --require-pass`.
- [x] `[AI]` Classify records as `core`, `core_context`, `context`, `defer`, or
  `background`.
- [x] `[AI]` Create a human review queue.
- [ ] `[HUMAN]` Confirm P1 core inclusion and exclusion.
- [ ] `[AI]` Pull full text or PDFs for P1 records where access is available.
- [ ] `[REVIEW]` Verify DOI, URL, species, cell type, stage, medium focus, dose
  availability, and endpoints.

Wet-lab-entry corpus gate:

- 35-50 peer-reviewed sources curated.
- At least 8 recent review or scoping papers.
- At least 12 primary medium or cell-culture papers.
- At least 10 bovine satellite-cell or myoblast relevant papers.
- At least 5 papers with extractable dose or range information.
- At least 3 papers reporting serum-free or animal-component-free bovine
  muscle-cell culture.
- Background-only sources excluded from wet-lab evidence counts.

### S3. Full-Text Extraction

Goal: convert papers into structured, grounded data.

Checklist:

- [ ] `[AI]` Ingest BibTeX, PDFs, full text, or externally generated structured
  paper files.
- [ ] `[AI]` Prefer structured parsing when available: GROBID TEI, structured
  text sections, or future PDF backends.
- [ ] `[AI]` Run triage and extraction on P1/P2 sources.
- [ ] `[AI]` Export screening, component, evidence, and extraction tables.
- [ ] `[AI]` Run `cultivate evidence-audit` before proposing wet-lab variables.
- [ ] `[AI]` Record extraction coverage, non-missing fields, and grounding rate.
- [x] `[AI]` Evaluate corpora with strict paper-ID alignment: score every gold
  record, count missing predictions as false negatives, report unexpected IDs,
  and reject duplicate IDs.
- [x] `[AI]` Report gold-field presence and evidence attachment separately from
  paper-ID coverage and quote grounding; a bibliographic shell is not a
  substantive extraction.
- [x] `[AI]` Evaluate all eight Gate 2 concepts separately at the 0.75
  non-missing threshold. Do not let pooled coverage offset a failed concept;
  keep A-M `dose_range` results provisional until dedicated dose extraction is
  reviewed.
- [x] `[AI]` In operator mode, emit component-dose records only when one
  verified quote contains both the component and dose/range. Preserve unit,
  comparison group, and endpoint; unverified relations cannot count as direct
  Gate 2 dose coverage.
- [x] `[AI]` Extract explicit culture stage and medium role/type into dedicated
  `D.culture_stage` and `E.medium_type` fields. Do not infer either from an
  endpoint or ingredient list.
- [ ] `[HUMAN]` Version and re-adjudicate stage/type gold before changing the
  frozen four-paper benchmark; preserve the raw predictions used by each report.
- [x] `[AI]` Support replayable T1/T2 bundles containing exact gold, all provider
  predictions, source hashes, file checksums, paper order, failures, and report
  configuration. Reject drift or tampering before scoring.
- [ ] `[REVIEW]` Before committing a bundle, verify its gold version, quotation
  rights, secret scan, provider/model labels, and byte-stable replay.
- [x] `[AI]` Keep `data/evaluation/runs/mock-baseline-v1` as an offline
  format/replay exemplar. Never cite its deterministic mock scores as model
  accuracy or wet-lab evidence.
- [x] `[AI]` Generate `medium-fulltext-v1` over R015, R016, R017, and R023 with
  all 380 paper x A-M field cells, source/schema hashes, and two independent
  reviewer slots plus final adjudication.
- [ ] `[HUMAN]` Complete reviewer 1 without seeing reviewer 2; complete reviewer
  2 independently using separate copies of `reviewer_blank.tsv`; merge both into
  the controlled master, then adjudicate every disagreement and unresolved field.
- [ ] `[REVIEW]` Run `prepare_medium_gold_review.py validate --require-ready`.
  Do not run production T1 scoring until it reports 380/380 adjudicated and zero
  issues.
- [x] `[AI]` Prepare `medium-pilot-v1` over R015/R016 and 28 high-risk fields
  (56 cells), with manifest-controlled field scope and the same blind merge and
  validation rules.
- [ ] `[HUMAN]` Complete and adjudicate the 56-cell pilot first. Scale only when
  both reviewers are 56/56, issues are zero, decision kappa >= 0.70, and pilot
  status is READY. If kappa is undefined because only one decision class occurs,
  require exact agreement 1.0 and document the prevalence limitation; otherwise
  revise instructions and version a new pilot.
- [x] `[AI]` Provide `prepare_medium_gold_review.py passages` as a read-only
  field-aware locator. It verifies source hashes and never changes a worksheet;
  lexical no-hit cannot be coded as `not_reported` without reading the source.
- [x] `[AI]` Run `cultivate extraction-readiness` before live operator
  extraction to separate missing sources from weak section routing.
- [x] `[AI]` Ingest lawful R045-R047 full text and generate the H031-H033
  hash-anchored review packet plus readiness report. All 3 tasks are directly
  operator-ready; this is source navigation, not evidence approval.
- [x] `[AI]` Use `cultivate extract --ids ...` for live pilots so H review IDs,
  source record IDs, or paper IDs select an explicit paper set.
- [x] `[AI]` Treat total provider-call failure as extraction failure; do not
  write empty extraction records when all operators return `call_error`.
- [x] `[AI]` Fail fast on non-retryable provider errors such as authentication,
  balance, permission, invalid-request, invalid-parameter, or missing-model
  errors; keep retry/backoff for transient rate-limit/server errors.
- [ ] `[REVIEW]` Flag sparse or unreliable extraction runs.
- [ ] `[AI]` Repair parser or prompt issues only when evidence shows a
  technical failure rather than missing source content.

Commands:

```bash
cultivate ingest
cultivate ingest --grobid-tei --grobid-url http://localhost:8070  # optional
cultivate triage
cultivate extraction-readiness --ids H001-H016 \
  --out docs/EXTRACTION_READINESS_H001_H016.md \
  --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv
cultivate extraction-readiness --ids H031-H033 \
  --out docs/EXTRACTION_READINESS_H031_H033.md \
  --tsv data/literature/bovine_extraction_readiness_H031_H033.tsv
cultivate review-packet --ids H031-H033 --out docs/HUMAN_REVIEW_PACKET_H031_H033.md
cultivate extract --ids H014 --mode operators --provider openai --model deepseek-v4-flash
cultivate extract --ids H001-H014 --mode operators --provider openai --model deepseek-v4-flash
cultivate export
cultivate evidence-audit --outcome proliferation --out docs/EVIDENCE_AUDIT_PROLIFERATION.md
python scripts/evaluate_medium_corpus.py --provider mock_gpt --agreement-scope mock \
  --artifacts-out data/evaluation/runs/mock-baseline-v1 --out-dir /tmp/mock-baseline-v1
python scripts/evaluate_medium_corpus.py \
  --artifacts-in data/evaluation/runs/mock-baseline-v1 --out-dir /tmp/mock-baseline-v1-replay
python scripts/prepare_medium_gold_review.py validate \
  --manifest data/evaluation/gold/medium-fulltext-v1/manifest.json \
  --worksheet data/evaluation/gold/medium-fulltext-v1/review.tsv \
  --out docs/FULLTEXT_GOLD_VALIDATION_MEDIUM_V1.md
# After two independent reviewer files are complete:
python scripts/prepare_medium_gold_review.py merge \
  --master data/evaluation/gold/medium-fulltext-v1/review.tsv \
  --reviewer-1 /path/to/reviewer_1.tsv --reviewer-2 /path/to/reviewer_2.tsv \
  --out data/evaluation/gold/medium-fulltext-v1/review.tsv
python scripts/prepare_medium_gold_review.py passages \
  --manifest data/evaluation/gold/medium-pilot-v1/manifest.json \
  --record R015 --field E.growth_factors --out /tmp/r015-growth-factor-locators.md
```

Gate:

- Evidence quote grounding rate is at least 0.95 for top-ranked records.
- Non-missing fraction is at least 0.75 for species, cell type, stage, medium
  type, serum-free status, component identity, dose/range, and endpoint.
- Evidence audit is not `NO-GO` for the target outcome.
- Every component entering the design space links to a source quote and a
  normalized component record.

### S4. Human Evidence Review

Goal: turn extracted evidence into scientifically usable evidence.

Method rule: S4 follows a human-in-the-loop systematic-review pattern. AI may
rank records, generate locators, preview snippets, and validate worksheet
structure. It may not decide evidence support, exclude a source, or promote a
variable into the wet-lab search space. This follows Cochrane duplicate-checking
and transparent-decision principles, PRISMA/PRISMA-trAIce reporting expectations
for AI-assisted reviews, and the ASReview/RobotReviewer automation boundary.

Checklist:

- [ ] `[AI]` Generate passage locators with `cultivate review-packet`.
- [ ] `[AI]` Generate a human-fillable adjudication worksheet with
  `cultivate adjudication-template`.
- [ ] `[AI]` Record provider, model, extraction mode, locator source, and
  validator status for any AI-assisted review artifact.
- [ ] `[REVIEW]` Pilot the worksheet on 2-3 records before scaling; check that
  decisions, ranges, notes, and conflict labels are usable.
- [ ] `[HUMAN]` Review `H001-H016` first.
- [ ] `[HUMAN]` Mark each item as `supported`, `partial`, `unsupported`,
  `uncertain`, or `defer`.
- [ ] `[HUMAN]` Add concise notes with formulation, dose, endpoint, caveat, or
  exclusion reason.
- [ ] `[HUMAN]` Independently check outcome-direction and dose/range rows when a
  row could affect wet-lab variables.
- [ ] `[HUMAN]` For quantitative effect claims, fill `numeric_effect_status`,
  `numeric_effect_metric`, `numeric_effect_value`, optional
  `numeric_effect_variance`, and `numeric_effect_notes`; use
  `not_applicable` for direction-only rows.
- [ ] `[AI]` Validate the filled worksheet with
  `cultivate adjudication-validate`.
- [ ] `[AI]` Export only `supported` and `partial` human decisions to
  `data/literature/bovine_evidence_table.tsv` with
  `cultivate adjudication-export`.
- [ ] `[REVIEW]` Resolve conflicts between AI extraction and human reading.
- [ ] `[DOC]` Update `docs/BOVINE_CORPUS_MANIFEST.md`.

Command:

```bash
cultivate review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md
cultivate adjudication-template --ids H001-H014 --out data/literature/bovine_adjudication_H001_H014.tsv
cultivate adjudication-status --out docs/HUMAN_ADJUDICATION_STATUS_H001_H014.md
cultivate adjudication-passages --ids H014 --max-ranges 1
cultivate adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv \
  --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md
cultivate adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv \
  --out data/literature/bovine_evidence_table.tsv
```

Recommended review order:

1. Beefy-9 benchmark, FGF2 reduction, albumin dose/cost.
2. Chemically defined bovine medium and differentiation capacity.
3. Commercial serum-free medium benchmarks.
4. Spent-media species and cell-type dependence.
5. DOE/RSM bovine serum-free media.
6. Albumin substitutes, protein isolates, and hydrolysates.
7. Safety and cost annotations.

Gate: every non-exploratory variable entering the first design batch has
human-reviewed support, outcome-direction and dose/range rows that affect the
first design are independently checked or explicitly waived by `[REVIEW]`, and
`docs/EVIDENCE_AUDIT_PROLIFERATION.md` has no open wet-lab-entry blockers.

### S5. Search-Space Design

Goal: define what the optimizer may change.

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

Goal: test whether the proposed design is robust to retrieval and optimizer
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

Goal: freeze the experiment before results exist.

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

Goal: execute the frozen design without changing the question mid-run.

Checklist:

- [ ] `[LAB]` Prepare cells and reagents according to the frozen protocol.
- [ ] `[LAB]` Record plate map, reagent lots, operator, passage number, seeding
  density, and timing.
- [ ] `[LAB]` Store raw measurements and raw images where applicable.
- [ ] `[HUMAN]` Record deviations immediately.
- [ ] `[REVIEW]` Decide whether deviations invalidate, qualify, or annotate the
  run.
- [ ] `[DOC]` Commit metadata and result manifests; store large raw files
  outside git unless storage policy changes.

Gate: the run is completed or stopped with deviations and raw data recorded.

### S9. Result Comparison

Goal: compare measured results against controls and objectives.

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

Goal: decide whether and how to run another round.

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

Goal: turn the system and experiments into a defensible paper workflow.

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

## 7. Parallel Work Plan

Work that can happen now:

| Stream | Can start now | Must not do yet |
|---|---|---|
| `[HUMAN]` evidence review | Adjudicate H001-H014 using the locator packet and worksheet | Approve wet-lab variables without completed S3-S4 gates |
| `[AI]` corpus/extraction | Maintain the H001-H014 adjudication worksheet; acquire R024 main full text when human/institutional access is available; convert human notes into evidence records | Generate a wet-lab design packet as if the evidence gate passed |
| `[LAB]` feasibility | Confirm cell source, passage limits, baseline medium, plate format, assay duration, maximum conditions, and reagent constraints | Start experiments or change formulation candidates |
| `[REVIEW]` gatekeeping | Check whether extracted claims match source text and whether variables are supported | Treat direction-only evidence as quantitative proof |

Conflict rules:

- Pull latest changes before editing.
- Treat untracked files as another contributor's work unless ownership is clear.
- Prefer small, reviewable commits.
- Record important coordination decisions in `SESSION_LOG.md`, decision records,
  or commit messages.
- If a human-only blocker appears, record it and continue with non-blocked work.

## 8. Current Project Ledger

This section is the concise status snapshot. It should be updated after material
work sessions; detailed history stays in `SESSION_LOG.md`.

### 8.1 Completed Technical Work

- CLI-first Python package exists.
- Latest main-line validation after merging the Codex JATS/readiness and
  provider fail-fast branches, S4 review helpers, and Claude DeepSeek comparison
  handoff, plus numeric quote verification and quote-based log fold-change
  inference, numeric adjudication fields, and explicit treatment/control mean
  log-ratio/variance inference for effect items: focused numeric tests pass; in
  the current managed sandbox, the suite excluding the local-loopback GROBID mock
  test reports 66 tests passed, 2 optional tests skipped, and 1 deselected.
- Codex now works from `/Users/tianyangsong/Desktop/Research/CultivateAgent-codex`;
  Claude works from `/Users/tianyangsong/Desktop/Research/CultivateAgent-claude`.
  Short-lived feature branches should be merged into `main` and deleted instead
  of accumulating as stale side branches.
- Smoke pipeline passes.
- Demo optimization loop passes.
- Extraction evaluator and offline four-paper fixture exist.
- Provider-agnostic LLM layer exists, including mock mode for offline runs and
  `llm.extra_body` passthrough for OpenAI-compatible provider options.
- Operator extraction exists for smaller section-routed prompts.
- Structured-paper schema, plain-text fallback, GROBID TEI parsing, and
  JATS/Open Access XML parsing exist.
- Europe PMC JATS and P1 PDF audit manifests are checked against the canonical
  corpus record and title-derived paper directory before use. This prevents a
  valid DOI/XML source from being attached to a different local paper.
- `cultivate ingest --grobid-tei` can call a running GROBID service and save
  `fulltext.xml`.
- Embedding retriever exists.
- BoTorch qNEHVI and qLogNEHVI backends exist.
- Optional citation verifier exists.
- Ontology-to-search-space handling includes hydrolysates, extracts, defined
  supplements, albumin substitutes, amino acids, carbon sources, trace elements,
  B8/Beefy-9/Beefy-R/SFB/SFGM, rapeseed-protein isolate, Grifola frondosa
  extract, Auxenochlorella pyrenoidosa protein extract, and copper ions. These
  are normalization hooks, not wet-lab approvals.
- `scripts/ingest_pdfs.py` can ingest loose PDF folders/lists.
- `scripts/run_evidence_parallel.py` can generate effect-item exports and
  controlled provider/model comparison files with `--model`, `--max-tokens`,
  and `--items-out`; it reports tier counts to distinguish direction-only
  evidence from quantitative effect-size evidence.
- `evidence.extract_effects` now verifies numeric `effect` and `variance`
  fields against the evidence quote. Unsupported numbers are cleared so they
  cannot enter the random-effects pool as quantitative evidence.
- Explicit quoted fold/percent changes can be converted into log response
  ratios `ln(ratio)`. This remains tier 2 because no variance is inferred.
- Very explicit quoted treatment/control means can also be converted into
  `ln(treatment_mean/control_mean)` with endpoint/timepoint context when
  available. Dose, concentration, timepoint, and factor-name numbers are skipped
  as response values. A ROM sampling variance is computed only when the same
  quote explicitly reports mean, SD/SE/SEM, and sample size for both groups.
- Percentage effect inference requires explicit increase/decrease/change
  language and rejects percentages followed by reagent or medium terms as
  concentrations. For `N +/- M-fold`, only N is the point estimate; M is an
  error term. These exclusions are regression-tested and remain subject to S4.
- `cultivate evidence` writes raw `effect_items_<outcome>.json`.
- `cultivate evidence-audit` produces a conservative wet-lab-entry report.
- `cultivate extraction-readiness` checks local full-text and section-routing
  readiness for the operator extractor without calling an LLM or adjudicating
  evidence. Current H001-H016 result: 14 direct-ready, 0 full-text fallback-ready,
  2 missing R024 tasks. The generated report now records repo-relative
  `data/papers/...` paths so it stays stable across Codex/Claude worktrees.
- `cultivate review-packet` generates repo-relative local full-text
  character-range locators for human review without making adjudication
  decisions.
- `cultivate adjudication-template` and `cultivate adjudication-validate`
  create and check the human-fillable H001-H014 worksheet with portable
  `data/papers/...` paths, without deciding evidence support. The template
  command refuses to overwrite a worksheet that already contains human decisions
  unless `--force` is passed; forced overwrites create a timestamped `.bak` copy
  next to the worksheet first. These local backup files are ignored by git. The
  worksheet now includes `numeric_effect_status`, metric, value, variance, and
  notes fields so quote-inferred tier 2 values and future tier 1 values require
  explicit human numeric review before thesis claims.
- `cultivate adjudication-status` summarizes blank, resolved, evidence-bearing,
  and invalid worksheet decisions. Current H001-H014 status: 0/14 resolved,
  0 evidence-bearing decisions, 0 validation issues.
- `cultivate adjudication-passages` previews short local snippets for worksheet
  ranges to speed human inspection. It does not adjudicate support, and generated
  snippet files should stay local unless source quotation rights are reviewed.
- `cultivate adjudication-export` exports valid human-supported or partial rows
  into `data/literature/bovine_evidence_table.tsv`; the committed table is
  currently header-only because no human decisions have been entered.

### 8.2 Completed Literature And Planning Work

- First wet-lab-facing target is documented.
- Bovine manifest contains 47 records.
- The executable Gate 1 audit counts only design-included records: 35
  peer-reviewed records, 18 reviews, 17 primary papers, 13 bovine primary
  papers, 17 dose-bearing primary papers, and 8 serum-free bovine primary
  papers. All six numerical thresholds and required metadata pass. Gate 1
  remains `FAIL` because 0/14 P1 core/core-context records have an explicit
  human-verified status.
- R045-R047 add directly bounded evidence on microbial lysate serum replacement,
  Pichia-derived recombinant albumin, and donor variance under serum-free
  culture. Titles and DOI metadata were checked against Crossref plus PubMed or
  publisher records; none is treated as adjudicated evidence.
- Human review queue contains 33 open tasks.
- AI-for-science method review exists.
- DeepSeek compatibility-route vs explicit v4-flash effect-extraction
  comparison exists in `docs/MODEL_COMPARISON_DEEPSEEK.md`; it found the
  explicit v4-flash run cleaner and more critical but still direction-only, so
  it does not remove the need for human review or numeric effect-size extraction
  work.
- A quote-level numeric gate now prevents unquoted LLM-provided effect or
  variance numbers from upgrading an item into tier 1 or tier 2 evidence.
- The S4 human worksheet now carries a separate numeric-effect review gate; a
  row can be supported directionally while a quantitative value remains
  `partial`, `unsupported`, `uncertain`, or `defer`.
- Method-source registry now includes Cochrane ratio-measure guidance and
  Hedges/Gurevitch/Curtis response ratios plus Friedrich/Adhikari/Beyene ratio
  of means and the metafor ROM implementation notes for deterministic
  quote-level log-ratio and variance extraction.
- Method-source registry covers autonomous labs, scientific RAG, information
  extraction, document parsing, ETL, systematic-review tooling, human-in-the-loop
  evidence review, AI review reporting, and Bayesian optimization.
- Current method decision: prioritize S3 full-text extraction reliability and S4
  evidence audit / human review before wet-lab design generation.

### 8.3 Current Gate Status

| Gate | Current result | Meaning |
|---|---|---|
| Corpus Gate 1 | `FAIL`; 6/6 numerical checks and metadata pass | 35/35 included peer-reviewed sources; 0/14 P1 core/core-context rows are human verified |
| Proliferation evidence audit | `NO-GO` | Current extracted evidence cannot justify wet-lab entry |
| Extraction readiness | 14 direct-ready, 0 fallback-ready, 2 missing | H001-H014 are ready for section-routed operators; H015-H016 need R024 |
| Gate 2 critical-field coverage | `FAIL`: 0/17 applicable concept-paper cells in the committed live benchmark | Paper IDs were returned, but no B-M critical content was extracted; stage and medium type fixture gold are not evaluable |
| Critical human review | 16/16 open | H001-H014 worksheet and evidence-table export path exist, but no human decisions have been entered |
| H001-H014 adjudication status | 0/14 resolved, 0 evidence-bearing | Status report confirms the worksheet is structurally valid but still awaiting human decisions |
| Adjudicated evidence table | 0 rows | Header-only export from the blank worksheet; not evidence approval |
| Review-packet coverage | 14/16 with local locators | H001-H014 are ready for efficient human review |
| New-source review packet | 3/3 with SHA-256-bound local locators | H031-H033 cover R045-R047; all decisions remain open |
| New-source extraction readiness | 3/3 direct-ready | R046 uses Europe PMC JATS; R045/R047 route from lawful local/open PDFs |
| P1 PDF structured-table off-ramp | `FAIL`; 10 identity-matched PDFs, 0 statistical line-table cells | 116 layout-text hits are locators only; use a bounded caption/prose and figure pilot |
| Missing review-packet sources | 2/16 | H015-H016 map to R024 and need institutional or human-provided main full text |
| Wet-lab design packet | Missing | Must wait for evidence review, search-space, robustness, and pre-registration gates |

### 8.4 Known Blockers And Risks

- Fresh worktrees do not automatically contain ignored local paper assets
  (`data/papers/`). Extraction-readiness verification needs those assets copied
  or regenerated locally.
- Current managed Codex sandbox cannot complete local `urllib` POST calls to a
  temporary `HTTPServer`, even with command escalation. This blocks
  `tests/test_pipeline.py::test_grobid_client_writes_and_parses_tei` in this
  environment but does not affect the non-loopback suite or CLI smoke checks.
- Once a reviewer starts filling `data/literature/bovine_adjudication_H001_H014.tsv`,
  do not regenerate it with `adjudication-template` unless a reviewed copy has
  been saved and `--force` is intentionally used. Forced overwrites create a
  timestamped `.bak` copy, but the backup is a last-resort guard, not the normal
  review workflow, and these backup files should stay local.
- Live OpenAI/Anthropic extraction was too sparse to count as successful model
  agreement.
- Gemini live comparison is incomplete because no Gemini/Google key was
  available.
- OpenAI raw-response debugging hit insufficient quota.
- The latest DeepSeek-compatible H014 live pilot reached the provider but failed
  authentication with the currently available environment key; no extraction was
  written.
- The DeepSeek compatibility-route vs explicit v4-flash comparison is a useful
  quality check, not wet-lab evidence: both outputs were direction-only and need
  human adjudication before any variable is promoted.
- Current corpus manifest is not yet fully extracted.
- GROBID service availability is external; legally obtained JATS/Open Access XML
  can also be parsed when available.
- Cost, supplier, and food-grade annotations are incomplete.
- Current audit candidates are direction-only; they are not quantitative wet-lab
  proof.
- In-silico robustness has not been run on reviewed bovine evidence.
- No wet-lab design packet or wet-lab result exists.

### 8.5 Immediate Next Actions

1. `[HUMAN]` Confirm or correct the 14 P1 core/core-context manifest decisions,
   including the cell-line limit for R045 and formulation availability for R047.
2. `[HUMAN]` Adjudicate H001-H014 using the current
   locator packet and `data/literature/bovine_adjudication_H001_H014.tsv`.
3. `[HUMAN]` Provide R024 main full text, or confirm it should remain deferred.
4. `[AI]` Regenerate `docs/HUMAN_REVIEW_PACKET_H001_H016.md` after R024 is
   available.
5. `[AI]` Validate the filled worksheet and run `cultivate adjudication-export`
   to refresh `data/literature/bovine_evidence_table.tsv`.
6. `[AI]` Run a small live operator-extraction pilot with
   `cultivate extract --ids H014 --mode operators`, inspect grounding and raw
   extraction metadata, then scale to `--ids H001-H014` only if the pilot is
   acceptable.
7. `[AI]` Extend deterministic number-aware extraction to confidence intervals,
   table-formatted group statistics, and more notation variants only when all
   required values are explicitly quoted and human numeric review remains in the
   loop.
8. `[REVIEW]` Decide which variables can enter S5 search-space design.
9. `[LAB]` In parallel, confirm assay constraints and reagent feasibility.

## 9. AI Handoff Protocol

Any AI agent taking over must:

1. Read `README.md`.
2. Read `docs/AI_COLLABORATION_PROTOCOL.md`.
3. Read this manual or `docs/PROJECT_WORKFLOW_ZH.md`.
4. Read `docs/SESSION_LOG.md`.
5. Read `docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md`.
6. Read `docs/BOVINE_CORPUS_MANIFEST.md`.
7. Run `git fetch --all --prune`.
8. Run `git status --short --branch`.
9. Identify untracked files and avoid overwriting them.
10. Work only in that agent's own worktree.
11. Continue from the next failed gate in Section 8.3.
12. Before choosing work, estimate current completion under three explicit
    denominators: software infrastructure, wet-lab-entry readiness, and the full
    paper workflow. Record the evidence and avoid increasing the estimate when
    a change improves auditability but does not pass a scientific gate.

Recommended handoff prompt:

```text
Continue CultivateAgent using docs/PROJECT_WORKFLOW.md as the controlling
workflow manual and docs/AI_COLLABORATION_PROTOCOL.md as the concurrent-agent
protocol. Keep the current bovine satellite-cell/myoblast expansion-medium
target unless a new scope-change decision record exists. Fetch first, inspect
git status and untracked files, then advance the next failed gate. Do not
overwrite human review notes, another agent's files, or missing evidence.
```
