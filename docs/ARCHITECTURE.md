# CultivateAgent — Architecture

This document explains *why* the code is shaped the way it is: how it maps onto
ReactionSeek (the reference system), and how it responds to the critique
recorded in the project notes.

## 1. The reference: ReactionSeek

ReactionSeek (Li et al., *Nat. Commun.* 2026) mines reaction data from the
organic-synthesis literature. Its core recipe, read from the released code:

| ReactionSeek stage | What it does | CultivateAgent analog |
|---|---|---|
| `extract_gpt.py` | Domain persona + **heavy few-shot** + `temperature=0` → a fixed-column table; "N/A" for missing | `extract/prompts.py` + `extract/extractor.py` (schema-driven prompt, few-shot, null codes) |
| `structurelize.py` | Deterministic parse of the LLM's table into clean rows | Pydantic validation of the LLM's JSON into typed blocks |
| `standardize/` (PubChem, OPSIN, CIR, RDKit) | **Domain tools** turn free-text names → canonical SMILES; LLM only where tools fail | `normalize/components.py` (ontology → canonical component) + `normalize/units.py` |
| `evaluate.py` | Field-level **TP/FP/FN → P/R/F1** vs annotations, with synonym/containment normalization | `evaluate/extraction_eval.py` |
| SynChat | RAG chat over the reaction DB | `retrieve/` + `design/recommender.py` (grounded generation) |

**The transferable idea** is the *hybrid*: LLMs supply contextual understanding;
deterministic domain tools supply precision; heavy prompt engineering replaces
fine-tuning. CultivateAgent keeps this and adds one thing ReactionSeek did not
emphasize: **per-value evidence verification**.

## 2. Why a schema-first design

Cultivated-meat medium knowledge is far more heterogeneous than reaction tables
(no SMILES-like canonical form for an outcome). So the schema *is* the product.
`schema/extraction.py` encodes the record's A–M blocks as typed models with a
`CONTROLLED_VOCAB` registry that:

* validates enum fields leniently (case-insensitive, null-code- and
  `INF:`-aware, never dropping data), and
* **generates the field guide fed to the LLM** (`schema_for_prompt`), so the
  prompt and the validator can never drift apart.

This single-source-of-truth pattern is the main reason the extractor stays small.

## 3. Evidence grounding (the guardrail)

`schema/evidence.py` defines an `Evidence` record (quote + location + confidence
+ `is_inference`). The extractor asks the model for a quote per value, then calls
`Evidence.verify_against(source_text)` — a whitespace-insensitive substring check
— and:

* counts a **grounding rate** = verified / total quotes (stored in
  `extraction_meta`, surfaced in the screening table and `stats`), and
* **downgrades + flags** any quote not found verbatim (`[UNVERIFIED ...]`).

This directly targets the record's `evidence_traceability` benchmark and is the
concrete answer to "how do you keep the LLM from hallucinating fields?".

## 4. Normalization: honest about comparability

The critique's sharpest point: outcome standardization is the weakest link,
because a "2× proliferation" and a "39 h doubling time" are not commensurable at
the source. We do **not** paper over this.

* `normalize/components.py` canonicalizes *inputs* (component names) against an
  ontology — a tractable, high-value problem (the FGF2/bFGF/basic-FGF collapse).
* `normalize/units.py` parses *quantities* but **preserves the original string**
  and sets `comparable=False` for anything that needs context to compare (e.g.
  `mg/mL` without a molar mass). Time and percent are normalized because they are
  safe; concentrations are parsed but explicitly marked not-cross-comparable.

So the knowledge base never fabricates a comparison the literature can't support.

## 5. Goal-conditioned, medium-centered design

`design/objectives.py` fixes four objectives (proliferation, cost,
differentiation_retention, tissue_readiness) and a whitelist of actionable
*medium* variables. `design/recommender.py`:

1. builds a retrieval query from the top-weighted objectives + context,
2. pulls a **numbered evidence pack** from the KB (each item → a `paper_id`),
3. prompts the LLM to produce candidate formulations that cite evidence and
   touch only actionable variables, and
4. **enforces** the whitelist in code — any change to `scaffold`, `cell_type`,
   etc. is flagged `is_actionable=False` rather than executed.

The system prompt hard-codes the critique's rules: cite everything; multi-source
combinations are novel/untested; **cost is reported jointly with performance**
(a Pareto statement), never as a standalone win.

## 6. Provider-agnostic LLM layer

`llm/` exposes one `LLMClient` interface with OpenAI-compatible, Anthropic,
Gemini (via its OpenAI-compat endpoint), and mock backends. Switching providers
is a config/flag change, which is what makes the record's GPT-5.4 vs Claude vs
Gemini comparison a one-liner. `temperature=0` and JSON-extraction robustness
(fences/prose) are handled centrally.

## 7. What this is *not* (roadmap)

Taking the critique seriously about scope, the following are **intentionally not
built here**, with notes on where they'd attach:

* **Verifier / critique loop — optional first pass built.** `MediumRecommender`
  can now run a second LLM pass with `verify_citations=True` (CLI:
  `cultivate design --verify-citations`). It checks whether each candidate's
  cited paper IDs and evidence snippets support the proposed medium change, then
  labels the change as `supported`, `partial`, or `unsupported` and adds caveats
  for downgraded claims. It is a one-shot verifier, not an iterative debate loop.
* **Predictive modeling — now partially built.** The `optimize/` layer adds a GP
  surrogate + multi-objective Bayesian optimization that consumes the KB
  (`space_from_kb`) and proposes pre-registerable experiment batches. See
  [`OPTIMIZATION.md`](OPTIMIZATION.md). A deeper predictive model (e.g. a neural
  surrogate trained on your own experimental results, or a knowledge graph over
  `medium_components` + evidence edges) remains future work; the KB's JSONL
  export is the intended input.
* **Wet-lab validation.** Out of scope for code. If pursued, the critique's
  minimal defensible design is the spec: **one** cell source, **one** primary
  endpoint, **one** pre-committed strong serum-free baseline, candidate
  formulations registered *before* running, powered with biological replicates.
  `design/recommender.py` already emits candidates + a DoE suggestion in a form
  suitable for such pre-registration.

## 8. Data flow summary

```
library.bib ─┐
             ├─▶ ingest.parse_bibtex ─▶ PaperRef[]
PDFs (Zotero)┘                            │
                                          ▼
                 ingest.ingest_library ─▶ data/papers/<slug>/{fulltext.txt, figures/, tables/, metadata.json}
                                          │
                 triage.classify_paper ──┤─▶ KB.triage  (A/B/C + evidence)
                                          │
                 extract.extract_paper ──┴─▶ PaperExtraction (A–M + evidence, verified)
                                          │
                 kb.KnowledgeBase ────────┤─▶ extractions / evidence / medium_components (normalized)
                                          │
                 evidence.extract_effects ┤─▶ EvidenceItem[] ─▶ meta_analysis.synthesize
                                          │        └─▶ EvidenceSummary[] (P(beneficial), I²) ─▶ KB
                                          │                                        │
                 retrieve.build_corpus ───┤─▶ BM25 / embedding index               │ EvidencePrior (πBO)
                                          │                                        ▼
                 design.MediumRecommender ┴─▶ EvidenceGuidedMOBO.propose ─▶ pre-registerable batch
```

**Extraction has two modes** (`extract --mode`): `blocks` (2 large passes) and
`operators` (small, section-routed, disjoint-field operators — reliable with real
LLMs; see `extract/operators.py`). **Evidence synthesis** (`evidence/`) is the
honest answer to outcome comparability — see
[`EVIDENCE_SYNTHESIS.md`](EVIDENCE_SYNTHESIS.md) — feeding the optimizer priors, not
labels.
