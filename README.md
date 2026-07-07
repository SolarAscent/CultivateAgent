# CultivateAgent

**A goal-conditioned, medium-centered literature-mining agent for culture-medium
optimization in cultivated meat.**

CultivateAgent turns a pile of cultivated-meat / tissue-engineering papers into a
structured, **evidence-grounded** knowledge base, and then uses that knowledge
base to propose *medium-formulation* changes conditioned on user objectives
(proliferation, cost, differentiation retention, 3D tissue-readiness).

It is modeled on **ReactionSeek** (Li et al., *Nature Communications*, 2026) —
an LLM + domain-tool hybrid that mines reaction data from the organic-synthesis
literature — and adapts that recipe to cell-culture media. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design and the
mapping to ReactionSeek.

```
 ingest ─▶ triage ─▶ extract ─▶ normalize ─▶ knowledge base ─▶ retrieve ─▶ design ─▶ optimize
 (BibTeX   (A/B/C    (schema A–M  (ontology +   (SQLite:         (BM25 /    (goal-     (evidence-
  +PDFs)    tiers)    evidence-    unit-aware)    papers,          embed-     cond.      grounded
                      grounded)                   components,      ding)      medium     LLM-warm-
                                                  evidence)                   cands)     started MOBO)
```

The last stage — `optimize` — closes the loop: it proposes a **pre-registerable
batch of next experiments** on the cost/performance Pareto front using
multi-objective Bayesian optimization warm-started by the literature and an LLM
proposer. See [`docs/OPTIMIZATION.md`](docs/OPTIMIZATION.md).

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

# 2. Tier papers A/B/C (evidence-backed, reproducible):
cultivate triage

# 3. Extract the A–M schema (grounded). Start with core papers:
cultivate extract --tier A

# 4. Look at what you have:
cultivate stats
cultivate export                     # screening_table.csv, medium_components.csv, evidence.csv, extractions.jsonl

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
  ingest/       BibTeX parsing, PDF→text/figures/tables, per-paper folder builder
  triage/       A/B/C relevance classifier (evidence-backed)
  extract/      domain prompts + evidence-grounded schema extractor
  normalize/    ontology component canonicalization + provenance-preserving units
  kb/           SQLite knowledge base + CSV/JSONL exports
  retrieve/     BM25 (+ fallback) retriever over the KB
  design/       fixed objectives/weights + goal-conditioned medium recommender
  optimize/     evidence-grounded, LLM-warm-started multi-objective Bayesian optimization
  evaluate/     extraction P/R/F1 + grounding-rate benchmarking
  cli.py        `cultivate` command-line entrypoint
config/
  config.example.yaml
  ontology/     basal_media, growth_factors, small_molecules, supplements (seed vocab)
tests/          offline pytest suite (no API key needed)
```

Run the tests: `pip install pytest && pytest -q` (14 tests, all offline).

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
