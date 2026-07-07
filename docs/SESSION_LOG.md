# Session Log

Date: 2026-07-07 / 2026-07-08

Branch: `session/eval-retrieval-mobo-hardening`

## Arrival Checks

- `python -m pip install -r requirements.txt pytest`: completed.
- Initial `pytest -q`: failed with 21 `ModuleNotFoundError` errors because the local package was not installed in the venv.
- Fix: ran `python -m pip install -e .`.
- Baseline after fix: `21 passed in 0.28s`.
- `python -m cultivate_agent.cli smoke`: passed.
- `python -m cultivate_agent.cli optimize --demo --rounds 6`: passed; hypervolume rose from 7.050 to 16.464.

## Changes Made

- Added `EmbeddingRetriever` behind the existing retriever interface with lazy optional backends:
  - `local` deterministic concept embedding for offline tests.
  - `sentence-transformers` lazy backend.
  - `openai` lazy embeddings backend.
- Added a semantic retrieval test where embedding retrieval finds an animal-component-free/cattle/myoblast query match that BM25 misses.
- Added `scripts/evaluate_medium_corpus.py`:
  - Four hand-annotated real medium-paper fixtures.
  - Offline provider profiles for repeatable T1/T2 protocol checks.
  - Optional `--live-provider provider:model` mode to run the same fixture texts through real provider clients when API keys are present.
  - Writes `docs/EVAL_RESULTS.md` and `docs/MODEL_AGREEMENT.md`.
- Installed `torch`, `botorch`, and `gpytorch` into `.venv`.
- Added a BoTorch qNEHVI test guarded by `pytest.importorskip`; it now runs in this venv because the optional deps are installed.
- Added `backend="botorch-log"` for BoTorch `qLogNoisyExpectedHypervolumeImprovement`, plus a guarded test.
- Added `scripts/compare_mobo_backends.py`.
- Generated `docs/OPTIMIZATION_BENCHMARK.md`.
- Added this session log and `docs/REVIEW_BY_NEXT_ENGINEER.md`.
- Added an optional verifier/critique loop in `design/recommender.py`:
  - `MediumRecommender(..., verify_citations=True)` runs a second LLM pass.
  - `cultivate design --verify-citations` and `cultivate optimize --verify-citations` expose it.
  - Unsupported/partial citation support is written to `VariableChange.evidence_support` and caveats.
- Fixed ontology-to-search-space coverage:
  - `hydrolysate`, `extract`, `defined_supplement`, `albumin_substitute`, amino acid, carbon source, and trace element categories can enter `space_from_kb`.
  - KB component role queries now match either `role` or `category`, preserving compatibility with older flattened rows.
- Hardened extractor parsing for live model JSON variants:
  - Accepts `blocks` keys such as `medium_info` / `fast_triage`, not only `E` / `B`.
  - Normalizes evidence keys such as `medium_info.serum_free_status` to `E.serum_free_status`.
- Added `docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md` after reviewing recent cultivated-meat medium/cell-biology reviews and key primary papers:
  - First wet-lab-facing target is bovine satellite cells / bovine myoblasts in the expansion phase.
  - First scope is serum-free, preferably animal-component-free, cost-aware medium optimization with myogenic-identity preservation.
  - Chicken continuous manufacturing, differentiation media, scaffolds, bioreactors, perfusion, and genetic engineering are recorded as later-stage or out-of-scope for the first wet-lab round.
  - Pre-wet-lab entry gates now cover corpus size, extraction reliability, biological plausibility, cost/supply sanity, in-silico robustness, and pre-registration readiness.
- Added the first bovine-focused corpus manifest and human review queue:
  - `data/literature/bovine_corpus_manifest.tsv`: 44 records, including 10 core sources, 1 core-context source, 21 context sources, 8 deferred sources, and 4 background-only records.
  - `data/literature/bovine_human_review_queue.tsv`: 30 open decision-critical review tasks for formulation, dose, endpoint, cost, safety, and transferability checks.
  - `docs/BOVINE_CORPUS_MANIFEST.md`: summary, current gate status, and immediate next steps.
- Added `docs/PROJECT_WORKFLOW.md` as the end-to-end operating manual:
  - Starts from developer-oriented repository structure and current interface.
  - Defines human, AI, lab, review, and gate responsibilities.
  - Covers the full path from setup through literature review, extraction, pre-registration, wet-lab execution, result comparison, closed-loop update, and manuscript audit.
  - Includes current completed work, known problems, next actions, and a handoff protocol for other AI agents.
- Added `docs/PROJECT_WORKFLOW_ZH.md`, a Chinese version of the operating manual for the project owner, human reviewers, wet-lab collaborators, and Chinese-speaking AI handoffs.
- Reworked both operating manuals into a more maintainable standard-doc structure after reviewing established documentation guidance from Diataxis, Google Developer Documentation Style Guide, Microsoft Learn contributor guidance, and GitLab documentation style guidance:
  - Reorganized the manuals around a stable project definition, deliverable model, repository map, role/decision rights, artifact registry, lifecycle overview, stage SOPs, parallel-work protocol, current project ledger, and AI handoff protocol.
  - Adds stable stage IDs S0-S11 and a central artifact registry so future updates have obvious locations.
  - Keeps current status, completed work, blockers, and next actions in one ledger section instead of mixing progress records through procedural text.
  - Synchronized the English and Chinese manuals so both versions use the same structure and status model.
- Reviewed AI-for-science, scientific RAG, scientific information extraction, document parsing/ETL, and Bayesian optimization sources to decide the next highest-value technical work:
  - Added `data/literature/ai_for_science_method_sources.tsv`, now at 18 reviewed sources after the GROBID service documentation update, with project lessons.
  - Added `docs/AI_FOR_SCIENCE_METHOD_REVIEW.md`.
  - Decision: prioritize S3 full-text extraction reliability through structured paper objects, section-routed extraction, operator-level coverage/grounding metrics, and human-review integration before generating new wet-lab design packets.
  - Human/external blockers recorded rather than guessed: paywalled PDFs/supplements, Gemini credentials, OpenAI quota, lab constraints, and final human evidence approval.
- Implemented the first S3 structured-paper foundation:
  - Added `schema/structured_paper.py` with `StructuredPaper`, section, paragraph, table, and figure models.
  - Added `structured_paper_from_text` as a no-dependency plain-text fallback with stable section/paragraph IDs.
  - `extract_paper` / `extract_blocks` now accept an optional `structured_paper` and route context using block-specific section hints.
  - Extraction metadata now records structured source, routed section IDs, section hints, and whether section routing was used.
  - Added tests for structured fallback parsing and structured section-routed extraction.
- Added no-dependency parsing for GROBID-flavored TEI XML that has already been produced externally:
  - `structured_paper_from_grobid_tei_xml` and `structured_paper_from_grobid_tei_path` parse title, abstract, body `div/head/p` sections, table captions, and figure captions.
  - Added GROBID TEI documentation to the method source registry.
  - This does not run a GROBID service/client yet; PDF-to-TEI generation remains a next step.
- Added optional GROBID service/client ingestion after reviewing the GROBID Service API and official Python client documentation:
  - Added `ingest/grobid.py`, a standard-library REST client for `/api/processFulltextDocument`.
  - `cultivate ingest --grobid-tei --grobid-url http://localhost:8070` now saves GROBID TEI as `fulltext.xml` when a service is running.
  - `cultivate extract` now parses existing `fulltext.xml` and passes the resulting `StructuredPaper` into section-routed extraction, falling back to plain text if TEI parsing fails.
  - `metadata.json` records `has_structured_fulltext` and `structured_extractor`.
  - Added a local HTTP-server test that simulates GROBID, checks multipart PDF submission, writes TEI, and parses it back into `StructuredPaper`.
  - Added GROBID service documentation to the method source registry.
  - This still does not prove P1 corpus coverage because a running GROBID service and accessible PDFs are external/currently unverified.

## Results

- Extraction fixture score for `mock_gpt`: precision 1.0, recall 0.8298, F1 0.907, mean grounding rate 1.0.
- Provider agreement fixture:
  - Least reliable fields: `J.has_extractable_quant_data`, `B.main_track`.
  - `E.serum_free_status` is also risky because providers can overclaim "chemically defined".
- Live OpenAI/Anthropic agreement run:
  - Ran `scripts/evaluate_medium_corpus.py --live-provider openai:gpt-5.4 --live-provider anthropic:claude-opus-4-6 --agreement-scope live --provider openai:gpt-5.4`.
  - Both providers completed, but scored A-M fields were nearly all missing beyond bibliographic prefill.
  - Agreement kappa is therefore not meaningful despite being 1.0 on selected categorical fields; `MODEL_AGREEMENT.md` now reports `nonmissing_fraction=0.0` to expose this.
  - `openai:gpt-5.4` fixture F1 was 0.254 with no verified evidence quotes.
  - Re-running after parser hardening did not improve live coverage; an attempted raw OpenAI response inspection then failed with insufficient quota.
- MOBO synthetic comparison, 3 seeds:
  - q-ParEGO mean normalized final HV: 0.924.
  - qNEHVI mean normalized final HV: 0.963.
  - qLogNEHVI mean normalized final HV: 0.963.
- BoTorch demo with `--backend botorch --demo --rounds 6`: passed; hypervolume rose from 7.050 to 19.005.

## Final Verification

- Latest `.venv/bin/python -m pytest -q`: 30 passed, 3 warnings.
- Warnings:
  - BoTorch recommends replacing legacy `qNoisyExpectedHypervolumeImprovement` with `qLogNoisyExpectedHypervolumeImprovement`.
  - PyTorch sparse invariant warning from `linear_operator`.
  - qLogNEHVI fell back to pure Python because `ninja` is not installed.
- `smoke`: still passed after changes.
- `optimize --demo --rounds 6`: still passed after changes.
- `scripts/evaluate_medium_corpus.py`: default offline mode passed.
- `scripts/evaluate_medium_corpus.py --out-dir /tmp/cultivate_eval_live_check --live-provider openai:gpt-test --live-limit 1`: live-mode plumbing completed and wrote reports in the temp directory.

## What I Did Not Do

- I did not complete the requested real GPT/Claude/Gemini extraction comparison across three providers. OpenAI and Anthropic were run live, but Gemini was unavailable because no Gemini/Google key was present; the live OpenAI/Anthropic outputs were too sparse to count as a successful model-comparison result.
- I did not claim the fixture metrics are production extraction accuracy; they are protocol checks over short source excerpts.
- I did not change the locked medium-only action scope.
- I pushed the branch to `origin/session/eval-retrieval-mobo-hardening`; I did not open a PR.

## Next 3 Steps

1. Run `cultivate ingest --grobid-tei` against accessible P1 PDFs with a running GROBID service, then inspect how many `fulltext.xml` files were produced.
2. Build `data/literature/bovine_evidence_table.tsv` from P1 full text and TEI-routed extraction.
3. Extend the one-shot verifier into an optional repair loop that asks the proposer to revise unsupported changes before final output.

---

# Session 2 (Claude) — operator extraction + evidence synthesis

Date: 2026-07-08
Branch: `session/operator-extraction-evidence-synthesis` (from `main` after merging Session 1)

## Review of Session 1 (Codex)

- Verified 8 sampled corpus DOIs against Crossref: all real; no fabricated citations.
- Confirmed the honest reporting (live extraction F1~0.25, `nonmissing_fraction=0.0`).
- Merged `session/eval-retrieval-mobo-hardening` into `main` (30 tests green).
- Recorded the key prior art Codex found — Cai et al. 2023, "Multi-objective Bayesian
  algorithm automatically discovers low-cost high-growth serum-free media" (Eng. Life
  Sci., DOI 10.1002/elsc.202300005) — as `M024` in the method registry; must be cited
  and differentiated.

## Changes Made

- **Phase B — operator-decomposition extraction** (`extract/operators.py`):
  - 5 operators (`context`, `medium`, `dose`, `endpoints`, `findings`) owning DISJOINT
    field sets, each with a tiny focused prompt and section routing.
  - `OperatorExtractor.extract(ref, text|StructuredPaper)` merges operator outputs into a
    `PaperExtraction`, verifies each evidence quote, and records per-operator status
    (`ok|empty|call_error|parse_error`), coverage, and grounding — so live failures are
    diagnosable instead of one opaque score.
  - CLI: `cultivate extract --mode operators` (default remains `blocks`).
  - Grounded in schema-reduction / modular-document IE work (SchemaRAG arXiv:2607.00008,
    schema-aware IE arXiv:2505.14992, DocETL) recorded as `M019`/`M020`.
  - Tests: 4 added (disjoint fields, merge+grounding, failure-diagnosability, unverified
    quote flagging).

## Results

- `pytest -q`: 34 passed (was 30).
- Offline operator extraction over a synthetic bovine serum-free excerpt populated
  blocks B/D/E/I/J/K/M and recorded per-operator coverage/grounding.

## Rationale

Session 1 correctly diagnosed that the monolithic all-A-M prompt is the cause of the
live-extraction failure but did not yet implement the fix. Phase B implements it.
The next live run should compare `--mode operators` vs `--mode blocks` on real papers.

- **Phase C — hierarchical Bayesian evidence synthesis** (`evidence/`): the answer to
  the record's outcome-comparability critique. `meta_analysis.py` pools heterogeneous
  cross-paper effects via DerSimonian-Laird random-effects (M021) + Higgins-Thompson
  I² (M022), with a Beta-Binomial fallback (direction-only evidence). High I² →
  "context-dependent, test directly" instead of a fake confident estimate.
  `effect_operator.py` produces quoted directional `EvidenceItem`s and drops any
  ungrounded claim (never co-occurrence). Closed-form, numpy-only. 6 tests;
  `docs/EVIDENCE_SYNTHESIS.md`.
- **Phase D — evidence-derived πBO priors** (`optimize/priors.py`): `EvidencePrior`
  maps evidence posteriors to a prior over the design space and injects it into the
  acquisition (πBO, Hvarfner et al. ICLR 2022 / M025), decaying as observations accrue;
  high-I² components get a flat prior and are surfaced in the proposal's
  `context_dependent_components`. Verified: prior raises beneficial-FGF2 / lowers
  detrimental-FBS in early batches. 4 tests.

## Session 2 Results

- `pytest -q`: 44 passed (was 30 at session start).
- New end-to-end capability: literature → operator extraction → evidence synthesis →
  πBO prior → evidence-guided MOBO batch, all offline-validated with the mock LLM.

## Session 2 — What I Did NOT Do (needs a live LLM / human)

- Did not run live real-LLM extraction (owner's OpenAI quota was exhausted last session;
  no Gemini key). `--mode operators` is ready for that comparison.
- Did not yet wire `extract_effects` into a CLI command over the real corpus (needs
  live LLM); the math + operator are offline-tested and ready.

## Session 2 — Next 3 Steps

1. Live: run `cultivate extract --mode operators` on 1-2 P1 full-text papers; inspect raw
   responses; compare coverage/grounding vs `--mode blocks`.
2. Add a `cultivate evidence` CLI: run `extract_effects` over the corpus for a chosen
   outcome, synthesize summaries, and export an evidence table with quotes + I².
3. Wire `EvidencePrior.from_summaries(kb-derived)` into `cultivate optimize` so the
   proposed batch is literature-prior-guided end to end.

## Session 2 (cont.) — Phases F & G

- **Phase F — evidence pipeline integration**: `kb` `evidence_summaries` table +
  upsert/read; `cultivate evidence --outcome <o>` (extract_effects → synthesize →
  store + export); `EvidencePrior.from_kb`; `cultivate optimize --evidence-prior`.
  Pipeline is now ingest→triage→extract→normalize→KB→**evidence**→retrieve→design→optimize.
- **Phase G — honest benchmark of the evidence prior** (`scripts/benchmark_evidence_prior.py`,
  `docs/EVIDENCE_PRIOR_BENCHMARK.md`):
  - Found and FIXED a real design flaw: the linear "beneficial → prefer maximum dose"
    prior **overshot** interior optima (saturating benefit + linear cost) and hurt even
    when it named the right components. Replaced with a saturating inclusion reward
    (Michaelis-Menten-like), which is also more biologically faithful.
  - Honest result: on easy/saturating objectives the prior is ~neutral; on **sparse**
    problems (few of many components matter) a **correct prior accelerates early search
    (+0.03–0.05 normalized-HV at 13–17 experiments)**, a **wrong prior costs experiments**
    (recovering via the πBO decay), and the advantage fades late (BO catches up). This
    validates using directional evidence for inclusion/direction decisions, not dose
    tuning — and justifies the flat prior + "test directly" flag on high-I² components.
  - Tests: 46 pass (was 30 at session start).

## Session 2 — Verified literature (Crossref/arXiv), recorded in method registry M019–M025

SchemaRAG (2607.00008), schema-aware IE (2505.14992), DerSimonian-Laird 1986, Higgins-
Thompson I² 2002, Röver 2020 heterogeneity priors, Cai et al. 2023 (elsc.202300005, prior
art), πBO Hvarfner et al. ICLR 2022 (2204.11051). All DOIs/arXiv IDs verified.

## Session 2 (cont.) — first LIVE run on real papers (DeepSeek)

Owner provided a DeepSeek key + two real PDFs (Lee et al. 2024 Nat Commun research;
Gu et al. 2025 Compr Rev Food Sci review). Wired DeepSeek with **zero code change**
(OpenAI-compatible; `.env` `OPENAI_BASE_URL`). Full report: `docs/LIVE_RUN_DEEPSEEK.md`.

- **Validated Phase B on real data**: `extract --mode blocks` FAILS (pass-2 JSON truncated
  at max_tokens → whole D–L block lost — the exact GPT-5.4 failure); `--mode operators`
  completes all 5 operators. Triage: both → A (correct).
- **Grounding verification proved essential**: DeepSeek's *values* are often right but its
  *quotes* are paraphrased → grounding flags them. Also over-extracts loose causal
  associations (needs human gate).
- **Two bugs found by scrutinizing live output + fixed**: (748bf5d) verify quotes against
  original text not round-tripped sections; (f986e2a) section-route the effect operator
  instead of truncating to the intro → **0 → 16 grounded proliferation effects** (Beefy-9,
  SFB +76% nuclei, Grifola frondosa extract, copper 5µM, ...).
- **Honest limits**: 2 papers → all components k=1 → Beta-Binomial p=0.67 (no fake
  confidence); ontology lacks the real components (Beefy-9/SFB/etc.) so no cross-paper
  pooling yet. 47 tests still pass.
