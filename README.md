# CultivateAgent

**A goal-conditioned, medium-centered literature-mining agent for culture-medium
optimization in cultivated meat.**

CultivateAgent turns a pile of cultivated-meat / tissue-engineering papers into a
structured, **evidence-grounded** knowledge base, and then uses that knowledge
base to propose *medium-formulation* changes conditioned on user objectives
(proliferation, cost, differentiation retention, 3D tissue-readiness).
The extractor now has a structured-paper layer: plain text can be converted into
section/paragraph objects, and extraction can route medium fields toward
Methods/media/cell-culture sections before prompting. It can also parse GROBID
TEI XML and JATS/Open Access article XML into the same structured-paper object.
For JATS tables, the structured layer preserves stable cell pointers, header
flags, row/column spans, footnotes, and a source-content hash; numeric values
remain source cells and are not transcribed by an LLM. Treatment/control role
labeling uses a pointer-only schema in `evidence/tables.py`: unknown fields and
model-returned numeric values are rejected, then deterministic code resolves
the cited cells, converts SEM to SD, and calls the frozen ROM effect seam.
This mechanism is implemented, but its semantic pointer accuracy still requires
the planned repeated-run gold evaluation before production use.
When a GROBID service is running, `cultivate ingest --grobid-tei` can submit PDFs
to `processFulltextDocument`, save the returned TEI as `fulltext.xml`, and let
`cultivate extract` use that structured file automatically.

It is modeled on an LLM + domain-tool hybrid that mines reaction data from the organic-synthesis
literature — and adapts that recipe to cell-culture media. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design and the
mapping to ReactionSeek.

```
 ingest ─▶ triage ─▶ extract ─▶ normalize ─▶ knowledge base ─▶ evidence ─▶ retrieve ─▶ design ─▶ optimize
 (BibTeX   (A/B/C    (blocks OR   (ontology +   (SQLite:         (random-    (BM25/    (goal-    (evidence-prior
  +PDFs)    tiers)    operators;   unit-aware)    papers,          effects     embed)    cond.      guided MOBO;
                      evidence-                   components,      meta-                  medium     qNEHVI/qLogNEHVI)
                      grounded)                   evidence)        analysis)              cands)
```

**Two additions beyond a plain "LLM extracts, BO suggests" pipeline:**

* **Operator extraction** (`--mode operators`): the A–M schema is split into small,
  section-routed operators — far more reliable with real LLMs than one giant prompt.
* **Evidence synthesis** (`cultivate evidence`): heterogeneous cross-paper results are
  pooled by **random-effects meta-analysis** into honest "is component X beneficial?"
  posteriors *with uncertainty*, which bias the optimizer as **priors** (πBO), never as
  labels. High-heterogeneity components are flagged "test directly". See
  [`docs/EVIDENCE_SYNTHESIS.md`](docs/EVIDENCE_SYNTHESIS.md).
* **Literature-grown ontology**: live extractions now feed back into the seed
  ontology. Current normalization covers B8/Beefy-9/Beefy-R/SFB/SFGM,
  rapeseed-protein isolate, Grifola frondosa extract, Auxenochlorella
  pyrenoidosa protein extract, and copper ions; these are normalization hooks,
  not wet-lab approval.

The last stage — `optimize` — closes the loop: it proposes a **pre-registerable
batch of next experiments** on the cost/performance Pareto front using
multi-objective Bayesian optimization warm-started by the literature and an LLM
proposer. See [`docs/OPTIMIZATION.md`](docs/OPTIMIZATION.md).

For the first wet-lab-facing target and entry criteria, see
[`docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md`](docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md).
The current bovine-focused corpus manifest and human review queue are summarized
in [`docs/BOVINE_CORPUS_MANIFEST.md`](docs/BOVINE_CORPUS_MANIFEST.md).
Gate 1 is executable rather than inferred from row count:

```bash
python scripts/audit_bovine_corpus.py --require-pass
```

The committed audit is currently `FAIL`: all six numerical checks and required
metadata pass for 44 design-included peer-reviewed sources, but none of the 23
P1 core/core-context records has an explicit human-verified review status. See
[`docs/BOVINE_CORPUS_GATE1_AUDIT.md`](docs/BOVINE_CORPUS_GATE1_AUDIT.md); a
nonzero exit is expected until human curation passes.
For the end-to-end project operating manual, including developer orientation,
human/AI/lab checklists, gates, handoff rules, and current status, see
[`docs/PROJECT_WORKFLOW.md`](docs/PROJECT_WORKFLOW.md) or the Chinese version
[`docs/PROJECT_WORKFLOW_ZH.md`](docs/PROJECT_WORKFLOW_ZH.md).
Those workflow manuals are now structured as maintainable control documents:
stable process sections are separated from the current project ledger so future
updates should not be scattered through the whole file.
For concurrent Codex/Claude work, start with
[`docs/AI_COLLABORATION_PROTOCOL.md`](docs/AI_COLLABORATION_PROTOCOL.md) before
editing. Current convention: Claude works in `../CultivateAgent-claude`, Codex
works in `../CultivateAgent-codex`, and completed short-lived branches are merged
back into `main` promptly.
For the current AI-for-science method review and algorithm roadmap, see
[`docs/AI_FOR_SCIENCE_METHOD_REVIEW.md`](docs/AI_FOR_SCIENCE_METHOD_REVIEW.md).

---

## Why this design

Three decisions, taken straight from the project record and its critique, shape
the whole codebase:

1. **Multi-objective, single-factor.** The agent may *read* any context (cell
   type, species, scaffold) but may only *act on medium variables*. Objectives
   are a **fixed** set with user-chosen *weights*, not open-ended goals. This is
   enforced in code (`design/objectives.py`, whitelist checks in
   `design/recommender.py`) so scope cannot silently explode.
2. **Evidence grounding is a first-class citizen.** Every extracted value can
   carry a verbatim `quote`, and the extractor **verifies** each quote against
   the source text, producing a measurable *grounding rate* per paper. Quotes
   that aren't found are flagged, not trusted.
3. **A sequential pipeline, not a fake "multi-agent" system.** Stages are named
   by function. A generate→critique verifier loop is a natural extension point
   (see the roadmap), but is not pretended to exist.

The record's critique (scope = "roughly three PhDs", comparability of outcomes
is the weakest link, wet-lab validation must be pre-registered) is taken
seriously: this repo builds the **literature → structured DB → grounded
recommendation** core well, and is explicit about what it does *not* solve
(cross-paper outcome comparability; it parses numbers but never fakes
comparability — see `normalize/units.py`).

---

## Install

```bash
cd CultivateAgent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # or: pip install -e ".[all]"
```

Core deps are light (`pydantic`, `pyyaml`, `pandas`). PDF processing
(`pymupdf`), BibTeX (`bibtexparser`), retrieval (`rank-bm25`), and the LLM SDKs
are pulled in as needed. Everything degrades gracefully if an optional package
is missing.

```bash
cultivate init          # create config/config.yaml and .env from templates
# edit .env  -> put OPENAI_API_KEY (and/or ANTHROPIC_API_KEY, GEMINI_API_KEY)
# edit config/config.yaml -> choose llm.provider / llm.model
```

**No API key? Prove the wiring offline:**

```bash
cultivate smoke         # runs ingest→extract→normalize→KB→retrieve→design with a mock LLM
```

---

## Quickstart

```bash
# 1. Export your Zotero library to BibTeX (data/library.bib), then:
cultivate ingest                     # build data/papers/<slug>/ folders + full text
# Optional structured full text: start GROBID separately, then:
cultivate ingest --grobid-tei --grobid-url http://localhost:8070
# If legally obtained JATS/Open Access XML already exists as fulltext.xml,
# cultivate extract and extraction-readiness will auto-detect it.
# Acquire the explicit bovine OA subset from Europe PMC with DOI/license checks:
python scripts/ingest_europe_pmc_jats.py --max-items 9
# Acquisition also rejects record/DOI/title-derived directory mismatches against
# the canonical bovine corpus manifest before writing source files.
# Before any new Zotero acquisition, derive the corpus-deduplicated queue. Use
# only the actionable output; conflicts remain held for human/version review:
python scripts/deduplicate_zotero_acquisition.py
# Discover license-verifiable OA candidates without downloading full text.
# The audit is request-bounded and resumes from local DOI/source checkpoints:
python scripts/audit_zotero_oa.py --max-requests 410
# Verify the bounded bovine-focused Europe PMC canary without corpus entry:
python scripts/verify_zotero_epmc_canary.py --max-items 10 --max-downloads 10
# Reproduce source-hash/paragraph-locator scope decisions and canonical bindings:
python scripts/validate_epmc_scope_review.py
# Reproduce the bounded DeepSeek page-pointer capability/holdout probes from
# source-hash-bound PDFs (three repeats; output schema permits IDs only):
python scripts/run_deepseek_page_probe.py --manifest data/evaluation/gold/quantitative-pilot-v1/manifest.json --checkpoint-dir data/checkpoints/deepseek-page-capability-v1 --report docs/DEEPSEEK_PAGE_CAPABILITY.md
# Reproduce the P1 PDF table off-ramp audit (counts/hashes only):
python scripts/audit_bovine_pdf_tables.py --max-items 14

# 2. Tier papers A/B/C (evidence-backed, reproducible):
cultivate triage

# 3. Extract the A–M schema (grounded). Start with core papers:
cultivate extract --tier A
# Real LLMs are more reliable with the decomposed operator extractor:
cultivate extract --tier A --mode operators
# Before spending LLM calls, audit whether local full text supports operator routing:
cultivate extraction-readiness --ids H001-H016
# Current H001-H016 preflight: 14 direct-ready, 0 fallback-ready, 2 missing R024 tasks.
# Newly added H031-H033 sources are separately 3/3 direct-ready:
cultivate extraction-readiness --ids H031-H033 \
  --out docs/EXTRACTION_READINESS_H031_H033.md \
  --tsv data/literature/bovine_extraction_readiness_H031_H033.tsv
# Identity/license-verified Zotero additions H034-H037 are 4/4 direct-ready:
python scripts/ingest_verified_sources.py \
  --verified-sources data/evaluation/gold/zotero-locator-heldout-v1/verified_sources.tsv
cultivate extraction-readiness --ids H034-H037 \
  --out docs/EXTRACTION_READINESS_H034_H037.md \
  --tsv data/literature/bovine_extraction_readiness_H034_H037.tsv
# Rebuild R052-R056 metadata/plain text from source-verified local JATS, then
# reproduce their readiness report:
python scripts/materialize_verified_jats.py
cultivate extraction-readiness --ids H038-H042 \
  --out docs/EXTRACTION_READINESS_H038_H042.md \
  --tsv data/literature/bovine_extraction_readiness_H038_H042.tsv
# For a controlled live pilot, target review IDs/source IDs instead of the whole tier:
cultivate extract --ids H014 --mode operators --provider openai --model deepseek-v4-flash
# If every operator fails at the provider-call layer, the command exits nonzero
# and does not write an extraction record.
# Non-retryable provider errors such as auth/balance/request-format failures are
# fail-fast; transient server/rate-limit errors still use retry/backoff.

# 4. Look at what you have:
cultivate stats
cultivate export                     # screening_table.csv, medium_components.csv, evidence.csv, extractions.jsonl

# 4b. Extract/synthesize heterogeneous evidence for one outcome:
cultivate evidence --outcome proliferation   # -> effect_items JSON + P(component beneficial) + I²
# Audit extracted effect items before any wet-lab design packet:
cultivate evidence-audit --outcome proliferation --out docs/EVIDENCE_AUDIT_PROLIFERATION.md
# Build character-range locators for the first human review gate:
cultivate review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md
# Current committed packet covers 14/16 tasks; H015-H016 still need R024 main full text.
# R045-R047 are available in a separate hash-anchored packet with no AI decisions:
cultivate review-packet --ids H031-H033 --out docs/HUMAN_REVIEW_PACKET_H031_H033.md
# R048-R051 likewise remain open human-review candidates:
cultivate review-packet --ids H034-H037 --out docs/HUMAN_REVIEW_PACKET_H034_H037.md
# R052-R056 are source-hash-bound JATS candidates; all decisions remain open:
cultivate review-packet --ids H038-H042 --out docs/HUMAN_REVIEW_PACKET_H038_H042.md
# Create and check the human-fillable adjudication worksheet for ready tasks:
cultivate adjudication-template --ids H001-H014 --out data/literature/bovine_adjudication_H001_H014.tsv
cultivate adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv
cultivate adjudication-status --out docs/HUMAN_ADJUDICATION_STATUS_H001_H014.md
# Local helper for a human reviewer: preview short snippets for suggested ranges.
# Omit --out to avoid committing source excerpts.
cultivate adjudication-passages --ids H014 --max-ranges 1
# Export only human-supported/partial rows after the worksheet is filled:
cultivate adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv \
  --out data/literature/bovine_evidence_table.tsv

# 5. Ask for a medium design, conditioned on objectives + context:
cultivate design \
  --weights "proliferation=0.6,cost=0.3,differentiation_retention=0.1" \
  --cell "bovine satellite cells" --species bovine --stage expansion \
  --scaffold "gelatin-alginate hydrogel"

# Optional: ask a second LLM pass to verify that candidate citations support
# the proposed medium changes, downgrading unsupported claims in the output.
cultivate design --verify-citations \
  --weights "proliferation=0.6,cost=0.3,differentiation_retention=0.1" \
  --cell "bovine satellite cells" --species bovine

# 6. Optimize: propose the next PRE-REGISTERABLE batch of experiments:
cultivate optimize --weights "proliferation=0.6,cost=0.4" \
  --cell "bovine satellite cells" --species bovine --batch 4
# ...guided by the literature evidence priors from step 4b:
cultivate optimize --weights "proliferation=0.6,cost=0.4" --evidence-prior
# ...or watch the closed loop converge offline (no KB / API key):
cultivate optimize --demo --rounds 6
# optional BoTorch log-qNEHVI backend:
cultivate optimize --demo --rounds 6 --backend botorch-log
```

### Reproduce the model comparison

The record plans to compare GPT-5.4 vs Claude Opus vs Gemini. Because everything
talks to one provider-agnostic interface, that's a flag, not a rewrite:

```bash
cultivate extract --tier A --provider openai    --model gpt-5.4
cultivate extract --tier A --provider anthropic --model claude-opus-4-6
cultivate extract --tier A --provider gemini    --model gemini-3.1-pro
```

OpenAI-compatible providers can use the same `openai` provider path. For
DeepSeek, set `OPENAI_BASE_URL=https://api.deepseek.com` locally and use current
model names such as `deepseek-v4-flash` or `deepseek-v4-pro`; the config also
supports `llm.extra_body` for provider-specific request options such as
disabling DeepSeek thinking mode during extraction.

The offline evaluation fixture can also be re-run with live provider calls when
API keys are present:

```bash
python scripts/evaluate_medium_corpus.py \
  --live-provider openai:gpt-5.4 \
  --live-provider anthropic:claude-opus-4-6 \
  --live-provider gemini:gemini-3.1-pro \
  --provider openai:gpt-5.4 \
  --agreement-scope live \
  --artifacts-out data/evaluation/runs/live-pilot-v1

# Deterministic replay restores the original provider and agreement scope.
python scripts/evaluate_medium_corpus.py \
  --artifacts-in data/evaluation/runs/live-pilot-v1 \
  --out-dir /tmp/live-pilot-v1-replay
```

If a provider is unavailable, the agreement report records the failure instead
of fabricating a comparison. Corpus evaluation is ID-strict: every gold paper
is scored, missing predictions count as false negatives, unexpected IDs are
reported, and duplicate gold or prediction IDs fail the run. The report also
separates paper-ID coverage, gold-field presence, B-M substantive-field count,
evidence attachment, and grounding; none of these metrics substitutes for the
others. It also applies the pre-wet-lab Gate 2 threshold to each predefined
decision-critical concept. Pooled coverage cannot hide a failed concept, and
the A-M `dose_range` proxy cannot produce final approval. Operator-mode dose
extraction can additionally emit grounded component-dose records linking one
component, dose/range, unit, comparison group, endpoint, and same-quote
evidence; only locally verified records count as direct Gate 2 dose coverage.
The context and medium operators also own explicit `D.culture_stage` and
`E.medium_type` fields. These remove summary-field proxies for future runs, but
do not retroactively fill or alter the frozen four-paper benchmark gold.

An evaluation artifact bundle contains exact gold records, every provider's
predictions, paper order, source-excerpt SHA-256 values, artifact checksums,
requested live-provider labels/failures, and the original report configuration.
Replay fails on fixture drift, file tampering, unsafe filenames, or record-order
misalignment. Review credentials, quotation rights, and gold-version approval
before committing a bundle.

The committed
[`mock-baseline-v1`](data/evaluation/runs/mock-baseline-v1/README.md) bundle is a
format/replay exemplar only. Its deterministic mock scores are not production
model accuracy and are not wet-lab evidence.

The production T1 gold path is
[`medium-fulltext-v1`](data/evaluation/gold/medium-fulltext-v1/README.md): four
independent bovine medium papers and 380 A-M field cells, with separate reviewer
1, reviewer 2, and adjudication columns in the controlled master. Reviewers use
separate single-reviewer files generated from `reviewer_blank.tsv`, then merge
before adjudication. It is currently blank and `NOT READY`.
`reported` values must be typed JSON with an exact full-text quote; schema and
source hashes are validated before scoring.

Human review starts with
[`medium-pilot-v1`](data/evaluation/gold/medium-pilot-v1/README.md): R015/R016 and
28 high-risk fields (56 cells). Both reviewers must finish independently,
decision kappa must be at least 0.70, all rows must be adjudicated, and the
validator must report READY before scaling to the 380-cell full benchmark.
`prepare_medium_gold_review.py passages` can generate read-only, field-aware
local locators to reduce review time; it never assigns a decision, and no hit is
not evidence of absence.

---

## The extraction schema (A–M)

The record's schema is codified as typed Pydantic models in
[`cultivate_agent/schema/extraction.py`](cultivate_agent/schema/extraction.py):

| Block | Contents | Block | Contents |
|---|---|---|---|
| **A** Basic info | id, title, authors, year, DOI… | **H** Tissue | structuring, alignment, texture strategy |
| **B** Fast triage | main_track, product type, core-ness | **I** Measurements | proliferation/diff/scaffold/quality metrics |
| **C** Objective | problem, bottlenecks, novelty | **J** Quant data | extractable variables, key numbers, units |
| **D** Cell info | source, type, isolation, culture | **K** Findings/limits | core findings, hidden limitations |
| **E** Medium ⭐ | basal, serum, GFs, small molecules… | **L** Review synthesis | category, direction-setting, representativeness |
| **F** Scaffold | material, origin, edibility, fabrication | **M** Final judgment | usefulness, action, one-paragraph summary |
| **G** Process | format, bioreactor, scale-up | | |

Fast-review workflow (from the record): screen on **A + B + C + J + M**, then do
deep extraction of **D + E + F + G + H + I + K + L** only on core papers.
`cultivate extract --triage-only` runs just the first pass.

```bash
cultivate schema --blocks E      # human-readable field guide (also fed to the LLM)
cultivate schema --json          # full JSON Schema
```

---

## Project layout

```
cultivate_agent/
  schema/       evidence primitives, the A–M schema, paper records + folder layout
  llm/          provider-agnostic client (openai / anthropic / gemini / mock)
  ingest/       BibTeX parsing, PDF→text/figures/tables, optional GROBID TEI/JATS XML, per-paper folder builder
  triage/       A/B/C relevance classifier (evidence-backed)
  extract/      domain prompts + evidence-grounded schema extractor
  normalize/    ontology component canonicalization + provenance-preserving units
  kb/           SQLite knowledge base + CSV/JSONL exports
  evidence/     random-effects meta-analysis + deterministic wet-lab-entry audit over quoted effects
  retrieve/     BM25 + embedding (+ fallback) retriever over the KB
  design/       fixed objectives/weights + goal-conditioned medium recommender (+ verifier)
  optimize/     LLM-warm-started multi-objective BO (q-ParEGO / qNEHVI) + evidence πBO priors
  evaluate/     extraction P/R/F1 + grounding-rate benchmarking
  cli.py        `cultivate` command-line entrypoint
config/
  config.example.yaml
  ontology/     basal_media, growth_factors, small_molecules, supplements (seed vocab)
tests/          offline pytest suite (no API key needed)
```

Useful scripts:

- `scripts/ingest_pdfs.py`: ingest loose PDF folders/lists when BibTeX is not
  available.
- `scripts/run_evidence_parallel.py`: generate corpus-wide effect-item exports
  for synthesis and `cultivate evidence-audit`. It now supports controlled live
  model comparisons with `--model`, `--max-tokens`, and `--items-out`, and
  prints tier counts so direction-only evidence is not mistaken for extractable
  quantitative effects. The current DeepSeek compatibility-alias vs explicit
  v4-flash comparison is recorded in
  [`docs/MODEL_COMPARISON_DEEPSEEK.md`](docs/MODEL_COMPARISON_DEEPSEEK.md).
  Numeric `effect` and `variance` fields from `extract_effects` are accepted
  only when the verified quote contains the supporting number; otherwise the
  item is automatically downgraded to a lower evidence tier. Explicit
  quote-backed fold/percent changes and very explicit treatment/control means
  are converted to log response ratios. A ROM sampling variance is computed
  only when the same verified quote also reports SD/SE/SEM and sample size for
  both treatment and control groups.
  Reagent/medium concentration percentages are excluded from effect inference;
  percentage effects require explicit change language, and `N +/- M-fold` uses
  N as the point estimate rather than reading the error term M as an effect.
- `cultivate extraction-readiness`: checks whether local full text can support
  section-routed `context`, `medium`, `dose`, `endpoints`, and `findings`
  operators before spending LLM calls; it does not extract or approve evidence.
  Its report paths are repo-relative so the committed audit is portable across
  Codex/Claude worktrees.
- `cultivate review-packet`: creates human-review passage locators without AI
  adjudication; local full-text paths are repo-relative for portable handoff.
  S4 uses a human-in-the-loop systematic-review rule: AI may prioritize and
  surface source locations, but humans decide evidence support, dose/range
  interpretation, exclusions, and wet-lab readiness.
- `cultivate adjudication-template` / `cultivate adjudication-validate`: creates
  and checks a human-fillable evidence-adjudication worksheet with the same
  portable paths; a blank PASS only means the worksheet format is valid, not
  that evidence has been approved. The template command refuses to overwrite a
  worksheet that already contains decisions unless `--force` is passed; forced
  overwrites create a timestamped `.bak` copy next to the worksheet first, and
  those local backups are ignored by git. The worksheet also has numeric-effect
  review fields (`numeric_effect_status`, metric, value, variance, notes) so
  quote-inferred tier 2 effects and future tier 1 effects require human numeric
  review before thesis claims.
- `cultivate adjudication-status`: summarizes worksheet progress and whether any
  evidence-bearing human decisions are ready to export.
- `cultivate adjudication-passages`: prints short local snippets for worksheet
  ranges so a human can inspect the source faster; it is a review aid, not an
  AI adjudication step, and generated snippet files should not be committed by
  default.
- `cultivate adjudication-export`: converts valid human-supported or partial
  decisions into `data/literature/bovine_evidence_table.tsv` without inventing
  evidence; the current blank worksheet exports zero rows.

Run the tests: `pip install pytest && pytest -q` (offline suite).

Current main-line verification after merging the Codex JATS/readiness and
provider fail-fast branches, S4 review helpers, Claude's DeepSeek comparison
handoff, numeric quote verification, quote-based log ratio inference, ROM
variance inference from quoted group statistics, and numeric adjudication fields
for effect items: focused numeric tests pass, and the managed-sandbox suite
excluding the local-loopback GROBID mock test reports `66 passed, 2 skipped,
1 deselected`. The excluded test currently fails because this environment cannot
complete even a minimal `urllib` POST to a local `HTTPServer`; `smoke`,
`optimize --demo --rounds 6`, `extraction-readiness --ids H001-H016`,
`adjudication-status`, `adjudication-validate`, and `adjudication-export` pass.

---

## Status & scope

Runnable and tested offline: ingestion, the schema, grounded
extraction, normalization, the knowledge base, retrieval, the goal-conditioned
recommender, **and the evidence-grounded multi-objective Bayesian optimizer**
(GP surrogate + q-ParEGO, with optional BoTorch qNEHVI/qLogNEHVI backends). The
optimizer is the "closed-loop, experimentally-testable" route the record's
abstract promised, made pre-registerable.

Still deliberately **out of scope** (and discussed with an honest reading of the
critique in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#roadmap)): a full
knowledge graph, deep predictive models beyond the BO surrogate, and the wet-lab
validation itself (the optimizer *produces* the pre-registerable experiment
batches such a validation would run).

## License

MIT.
