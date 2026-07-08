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

- Latest `.venv/bin/python -m pytest -q`: 47 passed, 3 warnings.
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

---

# Session 3 (Codex) — live-run ontology normalization patch

Date: 2026-07-08
Branch: `main`

## Coordination Decision

Claude's Session 2 already implemented operator extraction, evidence synthesis,
πBO priors, and the DeepSeek live run on `main`. To avoid conflicts or rollback,
this session did not edit the operator/evidence core. The most valuable
non-conflicting next step was to close the live run's normalization gap so real
component names can be canonicalized before evidence pooling and human review.

## Literature Checked And Applied

- Messmer et al. 2022, Nature Food, DOI `10.1038/s43016-021-00419-1`: confirms
  serum-free bovine satellite-cell differentiation media terminology including
  SFB/SFGM-family abbreviations.
- Stout et al. 2023, Biomaterials, DOI `10.1016/j.biomaterials.2023.122092`:
  supports Beefy-R and rapeseed-protein isolate as the albumin-replacement axis.
- Yu et al. 2024, Food Research International, DOI
  `10.1016/j.foodres.2024.115173`: supports Grifola frondosa extract / GFE,
  including the 12.5 ug/mL low-serum bovine satellite-cell context.
- Dong et al. 2024, Journal of Agricultural and Food Chemistry, DOI
  `10.1021/acs.jafc.4c00624`: supports Auxenochlorella pyrenoidosa protein
  extract / APE as a weak cross-species algae-extract prior.
- Gu et al. 2025 review and the DeepSeek live report: surfaced copper ions around
  5 uM, motivating a trace-element search-bound correction.

## Changes Made

- Added ontology canonical entries and aliases for SFB, SFGM, Beefy-R,
  rapeseed-protein isolate, Grifola frondosa extract, Auxenochlorella
  pyrenoidosa protein extract, and copper ions.
- Updated `CLASS_RANGES["trace_element"]` from `0-100 nM` to `0-10 uM`, because
  the prior nM range would exclude the copper-ion evidence surfaced by the live
  run.
- Added tests for the new canonicalization targets and for copper ions entering
  `space_from_kb` with the uM trace-element range.
- Updated README, both project workflow manuals, `BOVINE_CORPUS_MANIFEST.md`,
  `LIVE_RUN_DEEPSEEK.md`, and `REVIEW_BY_NEXT_ENGINEER.md`.

## What This Does Not Claim

- These ontology entries are normalization hooks only; they do not make any
  component approved for wet-lab use.
- GFE, APE, Beefy-R, and copper-ion claims still require human adjudication and
  dose/risk review before becoming non-exploratory variables.

## Verification

- `.venv/bin/python -m pytest -q`: 47 passed, 3 warnings.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed; ontology loaded 176
  surface terms.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.

---

# Session 4 (Codex) — documentation structure and AI coordination protocol

Date: 2026-07-08
Branch: `main`

## Coordination Decision

The previous project workflow manuals were useful but too ledger-like for
long-term maintenance. The owner asked for the Chinese and English versions to
be rewritten with a clearer professional documentation logic, while preserving
the existing project record and avoiding conflicts with concurrent Claude work.

This session treated documentation architecture as the most valuable immediate
task. It did not edit extraction, evidence synthesis, optimization, ontology, or
the untracked local scripts.

## Documentation References Checked

- Diataxis: used to separate orientation, how-to checklists, reference tables,
  and current project ledger.
- Google developer documentation style guide: used for task-oriented, concise,
  stable wording.
- Microsoft Learn contributor guide: used for maintainable ownership and update
  flow.
- GitLab documentation style guide: used for topic-based, scannable structure.
- GitHub pull request documentation and Conventional Commits: used to define a
  lightweight concurrent-agent protocol and commit-message handoff style.

## Changes Made

- Reorganized `docs/PROJECT_WORKFLOW.md` and
  `docs/PROJECT_WORKFLOW_ZH.md` into a stable manual:
  - how to use the manual,
  - project definition,
  - deliverable model,
  - repository map,
  - roles and decision rights,
  - artifact registry,
  - lifecycle overview,
  - stage checklists,
  - parallel-work rules,
  - current project ledger,
  - AI handoff protocol.
- Added `docs/AI_COLLABORATION_PROTOCOL.md` for Codex, Claude Code, humans, and
  any later AI agent working concurrently.
- Updated `README.md` so new contributors start with the operating manual and
  the collaboration protocol before editing.
- Added explicit rules that untracked files should be treated as another
  contributor's work unless ownership is proven.

## What This Does Not Claim

- The workflow manuals are process control documents, not evidence that wet-lab
  entry gates have passed.
- No human review task has been completed in this session.
- No full-text extraction, evidence adjudication, candidate variable approval,
  design packet, or wet-lab protocol was generated in this session.

## Known Concurrent Work Left Untouched

- `scripts/ingest_pdfs.py` is untracked and was not committed.
- `scripts/run_evidence_parallel.py` is untracked and was not committed.

## Verification

- `git diff --check`: passed.
- `.venv/bin/python -m pytest -q`: 47 passed, 3 warnings.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed; ontology loaded 176
  surface terms.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.

## Next 3 Steps

1. Resume S3/S4 technical work: batch full-text ingestion, extraction,
   normalization inspection, and human evidence review.
2. Human reviewer completes `H001-H016` in the bovine review queue.
3. Reviewer decides which adjudicated variables can enter the first bounded
   search space.

---

# Session 5 (Codex) — deterministic evidence audit before wet-lab entry

Date: 2026-07-08
Branch: `main`

## Coordination Decision

After the collaboration protocol was added, the next highest-value
non-conflicting task was to turn existing extracted effect items into a
deterministic wet-lab-entry audit. Local ignored data already contained a
proliferation effect-item export, but it mixed direct bovine medium evidence
with scaffold, microcarrier, process, cross-species, and direction-only claims.
Generating a wet-lab design packet from that state would be premature.

This session therefore added a no-LLM audit gate that can say `NO-GO` before
experimental design. During this session Claude's related commits landed on
`main`: `d33c3dd` pools evidence across context and strips verbose component
qualifiers; `f159f9f` adds the loose-PDF ingester and parallel evidence runner.
The audit layer is compatible with those outputs and does not overwrite them.

## Literature And Method Sources Checked

- GRADE / CDC ACIP GRADE criteria: used for the idea that indirectness,
  imprecision, and inconsistency should block action even when some evidence
  exists.
- PRISMA 2020: used for separating source identification, screening, synthesis,
  and reporting artifacts.
- NIST AI RMF 1.0: used for the requirement that AI-assisted scientific actions
  should have mapped context, measured validity, transparent records, and managed
  risk.
- DocETL remains the document-processing reference for modular extraction and
  validation, but the new audit itself is deterministic and does not call an LLM.

## Changes Made

- Added `cultivate_agent/evidence/audit.py`.
- Added CLI command:
  `cultivate evidence-audit --outcome proliferation --out docs/EVIDENCE_AUDIT_PROLIFERATION.md`.
- Updated `cultivate evidence` to write `effect_items_<outcome>.json` beside the
  synthesized evidence CSV, so the audit has an official no-rerun input path.
- Added an offline test for the audit gate: direct bovine medium evidence can
  become an AI-review candidate, while scaffold/process/cross-species items are
  filtered or flagged; open human review keeps the gate `NO-GO`.
- Generated `docs/EVIDENCE_AUDIT_PROLIFERATION.md` from the current local
  ignored effect-item export.
- Updated README, both workflow manuals, `BOVINE_CORPUS_MANIFEST.md`,
  `AI_FOR_SCIENCE_METHOD_REVIEW.md`, and the method-source registry.

## Current Audit Result

- Input: `data/exports/effect_items_proliferation.json` from local ignored data.
- Items audited: 145.
- Papers represented: 40.
- Components/interventions represented: 103.
- AI-review candidates: 4.
- Critical human-review status: 16/16 open.
- Decision: `NO-GO`.

Main blockers:

- All AI-review candidates are direction-only; none has quantitative effect
  evidence in the extracted record.
- Critical human review `H001-H016` is still open.

## What This Does Not Claim

- The audit does not approve any wet-lab variable.
- The audit report is not a substitute for the adjudicated bovine evidence table.
- The local ignored effect-item JSON is not committed; the committed report is a
  transparent snapshot of the current local audit state.

## Coordination With Claude Work

- `d33c3dd` and `f159f9f` were already on `main` before this session's commit.
- This session did not modify those files further.
- `cultivate evidence-audit` can consume `effect_items_<outcome>.json` generated
  by the parallel evidence runner or by any future official evidence export.

## Verification

- `git diff --check`: passed.
- `.venv/bin/python -m pytest -q`: 51 passed, 3 warnings.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed; ontology loaded 176
  surface terms.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.

## Next 3 Steps

1. Complete human review `H001-H016`.
2. Extract exact formulations, doses, endpoints, passages, and grounded quotes
   for the 4 audit candidates and any newly recovered direct bovine candidates.
3. Re-run `cultivate evidence-audit` after the next extraction/evidence export;
   only then decide whether S5 search-space design can start.

---

# Session 6 (Codex) — human-review packet for H001-H016

Date: 2026-07-08
Branch: `main`

## Coordination Decision

Session 5 established that wet-lab entry is still `NO-GO` because critical human
review tasks remain open. The highest-value next step was not another design
generator; it was to reduce the human review burden without replacing human
judgment. This session added a deterministic review-packet builder that links
review tasks to local full-text character ranges.

During this session Claude's `968d38f` landed on `main`, adding a
context-dependent flag for conflicting direction-only evidence. This work does
not modify that evidence-synthesis logic and was verified on top of it.

## Method Sources Checked

- ASReview: supports transparent human-in-the-loop prioritization for systematic
  review screening.
- SWIFT-Review: supports keeping the review expert in control while software
  organizes and prioritizes literature.
- RobotReviewer: supports surfacing source text for review tasks while avoiding
  final automated evidence judgments.

## Changes Made

- Added `cultivate_agent/evidence/review_packet.py`.
- Added CLI command:
  `cultivate review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md`.
- Generated `docs/HUMAN_REVIEW_PACKET_H001_H016.md`.
- Added tests covering packet generation from local full text.
- Updated README, both workflow manuals, `BOVINE_CORPUS_MANIFEST.md`,
  `AI_FOR_SCIENCE_METHOD_REVIEW.md`, and the method-source registry.

## Current Review Packet Result

- Review tasks covered: 16 (`H001-H016`).
- Local full-text locators found: 9/16.
- Ready for human review with locators: H001-H005, H008, H009, H012, H013.
- Missing local source/full-text or strict title match: H006-H007, H010-H011,
  H014-H016.

The committed packet gives full-text paths, character ranges, matched terms, and
task metadata. It intentionally does not embed long source excerpts and does not
mark any item `supported`, `partial`, `unsupported`, `uncertain`, or `defer`.

## What This Does Not Claim

- No human review decision was made.
- No wet-lab variable was approved.
- Missing review tasks still require source/full-text acquisition or stricter
  matching before efficient adjudication.

## Verification

- `.venv/bin/python -m pytest -q`: 54 passed, 3 warnings after Claude commit
  `968d38f`.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed; ontology loaded 176
  surface terms.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.
- `.venv/bin/python -m cultivate_agent.cli review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md`:
  passed; 9/16 tasks have local full-text locators.

## Next 3 Steps

1. Human reviewer adjudicates H001-H005, H008, H009, H012, and H013 using the
   locator packet.
2. AI acquires or ingests missing full text for H006-H007, H010-H011, and
   H014-H016.
3. Re-run `cultivate review-packet` and `cultivate evidence-audit` after the
   missing sources are available.

---

# Session 7 (Codex) — workflow manual rewrite for maintainability

Date: 2026-07-08
Branch: `main`

## Coordination Decision

The project owner reported that the English and Chinese workflow manuals were
logically cluttered, hard to update, and incomplete as professional project
guides. The highest-value task for this session was therefore documentation
repair, not new wet-lab design or additional evidence claims.

The manuals were rewritten as control documents with stable process sections
separated from the current project ledger. This keeps future updates focused:
change process sections only when rules change, and update the ledger after
material work sessions.

## Documentation Sources Checked

- Google developer documentation style guide: used for clear, consistent,
  project-specific technical documentation.
- Microsoft Writing Style Guide: used for concise writing for mixed technical
  audiences.
- Microsoft reference documentation guidance: used for predictable headings and
  repeatable reference structure.
- Diataxis: used to separate explanation, how-to guidance, reference material,
  and learning/onboarding content.
- GOV.UK user-needs guidance: used to frame sections around real user tasks and
  acceptance criteria.

## Changes Made

- Rewrote `docs/PROJECT_WORKFLOW.md` into a stable structure:
  documentation contract, project overview, delivery surface, repository map,
  roles and artifacts, thesis lifecycle, stage checklists, parallel work plan,
  current ledger, and handoff protocol.
- Rewrote `docs/PROJECT_WORKFLOW_ZH.md` with the same structure and current
  project status in Chinese.
- Kept the locked bovine satellite-cell/myoblast expansion-medium target and
  did not introduce new scientific conclusions.
- Preserved current committed status: S2 partial, S3/S4 blocked, evidence audit
  `NO-GO`, human review `H001-H016` still open, and review-packet coverage 9/16.
- Updated `README.md` to explain that the workflow manuals now separate stable
  process from the current project ledger.

## What This Does Not Claim

- No new literature evidence was adjudicated.
- No missing full text was acquired in this session.
- No wet-lab variable, formulation, or design packet was approved.
- The rewrite improves handoff structure; it does not advance any wet-lab gate.

## Verification

- `git diff --check`: passed.
- `.venv/bin/python -m pytest -q`: 54 passed, 3 warnings.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed; ontology loaded 176
  surface terms.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.

## Next 3 Steps

1. Run verification commands and update this session entry if anything fails.
2. Resume the S3/S4 blocker: acquire or ingest missing full text for H006-H007,
   H010-H011, and H014-H016.
3. Regenerate `docs/HUMAN_REVIEW_PACKET_H001_H016.md` after missing sources are
   available, then continue human adjudication.

---

# Session 8 (Codex) — acquire missing review-packet full text

Date: 2026-07-08
Branch: `main`

## Coordination Decision

After the workflow manuals were reorganized, the next highest-value non-wet-lab
task was to reduce the S4 human-review blocker. The committed review packet only
had local full-text locators for 9/16 critical tasks. This session focused on
legally accessible source acquisition for H006-H007, H010-H011, and H014-H016,
then regenerated the locator packet without making any human adjudication
decision.

## Sources Checked Or Acquired

- R017 / H006: Kolkmann et al. 2020, `Serum-free media for the growth of primary
  bovine myoblasts`, DOI `10.1007/s10616-019-00361-y`; PDF acquired from the
  publisher/PMC-accessible route and ingested.
- R018 / H007: Messmer et al. 2022, `A serum-free media formulation for cultured
  meat production supports bovine satellite cell differentiation in the absence
  of serum starvation`, DOI `10.1038/s43016-021-00419-1`; Maastricht University
  Pure portal-file PDF was accessible and ingested.
- R021 / H010-H011: Skrivergaard et al. 2023, `A simple and robust serum-free
  media for the proliferation of muscle cells`, DOI
  `10.1016/j.foodres.2023.113194`; Aarhus Pure PDF was accessible and ingested.
- R023 / H014: Zygmunt et al. 2023, `Influence of Media Composition on the Level
  of Bovine Satellite Cell Proliferation`, DOI `10.3390/ani13111855`; MDPI/PMC
  PDF downloads were access-challenged, so Europe PMC `fullTextXML` for PMCID
  `PMC10251972` was used to create local `fulltext.txt` and `fulltext.xml`.
- R024 / H015-H016: Amirvaresi et al. 2025, `Sustainable alternatives to fetal
  bovine serum...`, DOI `10.1021/acsfoodscitech.5c00023`; ACS main PDF and ACS
  Figshare supporting-information downloads were access-challenged. This remains
  a human/institutional-access blocker.

## Changes Made

- Ingested accessible PDFs into ignored `data/papers/` using
  `scripts/ingest_pdfs.py`.
- Added ignored local full-text data for R023 from Europe PMC XML.
- Regenerated `docs/HUMAN_REVIEW_PACKET_H001_H016.md`.
- Updated `data/literature/bovine_corpus_manifest.tsv`: R017, R018, R021, and
  R023 are now `fulltext_ingested_for_review_packet`; R024 is
  `needs_institutional_or_human_full_text`.
- Updated README, both workflow manuals, `BOVINE_CORPUS_MANIFEST.md`, and
  `AI_FOR_SCIENCE_METHOD_REVIEW.md` to reflect 14/16 review-packet coverage.

## Current Review Packet Result

- Review tasks covered: 16 (`H001-H016`).
- Local full-text locators found: 14/16.
- Ready for human review with locators: H001-H014.
- Still missing: H015-H016 because R024 main full text is not locally available.

## What This Does Not Claim

- No human review decision was made.
- No R024 evidence was adjudicated from partial or access-challenged sources.
- No wet-lab variable was approved.
- The proliferation audit remains `NO-GO` until human adjudication and updated
  evidence audit pass.

## Verification

- `git diff --check`: passed.
- `.venv/bin/python -m pytest -q`: 54 passed, 3 warnings.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed; ontology loaded 176
  surface terms.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.
- `.venv/bin/python -m cultivate_agent.cli review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md`:
  passed; 14/16 tasks have local full-text locators.

## Next 3 Steps

1. Human reviewer adjudicates H001-H014 using
   `docs/HUMAN_REVIEW_PACKET_H001_H016.md`.
2. Human owner provides R024 main full text through institutional access, or
   explicitly defers H015-H016.
3. After human notes exist, AI converts them into structured adjudication and
   re-runs `cultivate evidence-audit`.

---

# Session 9 (Codex) — human adjudication worksheet and validator

Date: 2026-07-08
Branch: `main`

## Coordination Decision

R024 remains a human/institutional-access blocker, but S4 can still advance for
the 14 review tasks that already have local passage locators. The next
non-blocked step was to turn the locator packet into a human-fillable,
machine-checkable worksheet so reviewers do not write decisions in scattered
Markdown notes.

This session added a worksheet generator and validator. The validator checks
format, allowed decisions, and selected character ranges. It does not determine
whether evidence is supported.

## Changes Made

- Added `cultivate_agent/evidence/adjudication.py`.
- Added CLI commands:
  `cultivate adjudication-template` and `cultivate adjudication-validate`.
- Generated `data/literature/bovine_adjudication_H001_H014.tsv` with one blank
  row per ready review task.
- Generated `docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md`.
- Added tests for template generation and validation failure cases.
- Updated README, both workflow manuals, `BOVINE_CORPUS_MANIFEST.md`, and
  `AI_FOR_SCIENCE_METHOD_REVIEW.md`.

## Current Worksheet Result

- Rows: 14 (`H001-H014`).
- Decisions entered: 0.
- Validation result for the blank template: `PASS`.
- Meaning of blank-template `PASS`: required columns and locator ranges are
  structurally valid. It is not evidence approval.

## What This Does Not Claim

- No human evidence decision was made.
- No reviewed evidence table exists yet.
- No wet-lab variable was approved.
- R024 / H015-H016 remain blocked on main full text.

## Verification

- `git diff --check`: passed.
- `.venv/bin/python -m pytest -q`: 55 passed, 3 warnings.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed; ontology loaded 176
  surface terms.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.
- `.venv/bin/python -m cultivate_agent.cli adjudication-template --ids H001-H014 --out data/literature/bovine_adjudication_H001_H014.tsv`:
  passed.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.

## Next 3 Steps

1. Human reviewer fills `data/literature/bovine_adjudication_H001_H014.tsv`.
2. AI runs `cultivate adjudication-validate` after human edits.
3. AI converts valid human decisions into the adjudicated bovine evidence table
   and then re-runs `cultivate evidence-audit`.
