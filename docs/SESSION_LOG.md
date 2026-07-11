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

---

# Session 10 (Codex) — adjudicated evidence export path

Date: 2026-07-08
Branch: `main`

## Coordination Decision

The human worksheet exists, but no human decisions have been entered. The next
non-blocked engineering step was therefore not to approve evidence, but to add
the deterministic export path that will run immediately after human review.

## Changes Made

- Added `cultivate adjudication-export`.
- Added `data/literature/bovine_evidence_table.tsv` as the adjudicated evidence
  table target.
- Added export tests covering the current blank worksheet and a filled
  supported-row example.
- Updated README, both workflow manuals, `BOVINE_CORPUS_MANIFEST.md`, and
  `AI_FOR_SCIENCE_METHOD_REVIEW.md` to state that export follows human
  adjudication and does not create evidence by itself.

## Current Evidence Table Result

- Exported rows: 0.
- Reason: `data/literature/bovine_adjudication_H001_H014.tsv` is still blank.
- Meaning: the pipeline can now preserve human-supported or partial decisions in
  a structured TSV, but no wet-lab variable has been approved.

## What This Does Not Claim

- No human evidence decision was made.
- No literature outcome was converted into a BO training label.
- The proliferation audit remains `NO-GO`.
- R024 / H015-H016 remain blocked on main full text.

## Verification

- `git diff --check`: passed.
- `.venv/bin/python -m pytest -q`: 55 passed, 3 warnings.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed; ontology loaded 176
  surface terms.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.

## Next 3 Steps

1. Human reviewer fills `data/literature/bovine_adjudication_H001_H014.tsv`.
2. AI runs `cultivate adjudication-validate` and `cultivate adjudication-export`.
3. AI re-runs evidence audit and updates candidate-variable decisions only from
   reviewed evidence.

---

# Session 11 (Codex) — extraction-readiness preflight

Date: 2026-07-08
Branch: `main`

## Coordination Decision

The next non-blocked task was to reduce live extraction trial-and-error before
asking GPT/Claude/Gemini to parse the P1 bovine papers. Human adjudication is
still blank and R024 is still missing, so this session added a deterministic
preflight that checks local full text and section routing without making
evidence claims.

## Literature And Method Basis

- Added PaperMage (Lo et al., EMNLP 2023) to the method-source registry because
  it motivates explicit scientific-document objects with sections, paragraphs,
  tables, and figures.
- Added Nougat (Blecher et al., arXiv 2023) because it supports keeping
  PDF-to-markup/parser alternatives separate from downstream evidence claims.
- Reused the existing DocETL/GROBID method decisions: complex document tasks
  should be decomposed, evaluated, and routed before expensive LLM calls.

## Changes Made

- Added `cultivate extraction-readiness`.
- Added `cultivate_agent/extract/readiness.py`.
- Generated `docs/EXTRACTION_READINESS_H001_H016.md`.
- Generated `data/literature/bovine_extraction_readiness_H001_H016.tsv`.
- Added tests for direct section-routed readiness and full-text fallback
  readiness.
- Updated README, both workflow manuals, `BOVINE_CORPUS_MANIFEST.md`,
  `AI_FOR_SCIENCE_METHOD_REVIEW.md`, and
  `data/literature/ai_for_science_method_sources.tsv`.

## Current Readiness Result

- H001-H013: ready for section-routed operator extraction.
- H014: ready only through full-text fallback; TEI parsing produced too little
  useful section structure for routed context.
- H015-H016: missing ingested paper/full text because both map to R024.
- Summary: 13 direct-ready, 1 fallback-ready, 0 partial, 2 missing.

## What This Does Not Claim

- No evidence field was extracted or approved.
- No human adjudication decision was made.
- No wet-lab variable was approved.
- The proliferation audit remains `NO-GO`.

## Verification

- `git diff --check`: passed.
- `.venv/bin/python -m pytest -q`: 57 passed, 3 warnings.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 13 ready, 1 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed; ontology loaded 176
  surface terms.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.

## Next 3 Steps

1. Run operator extraction on the direct-ready H001-H013 sources.
2. Improve TEI/plain-text section recovery for R023/H014, or accept it as
   fallback-context for the next extraction run.
3. Obtain R024 main full text before H015-H016 can enter the same preflight.

---

# Session 12 (Codex) — JATS full-text parser hardening

Date: 2026-07-09
Branch: `codex/jats-fulltext-readiness`

## Coordination Decision

The next non-blocked task was to remove the H014 extraction-readiness fallback
without spending live LLM calls. Inspection showed that R023's `fulltext.xml` is
JATS/Open Access article XML, not GROBID TEI. The parser should therefore
auto-detect JATS and expose sections/tables before operator extraction.

The user provided test provider keys in chat. No key was written to the repo,
docs, commit message, or generated reports. DeepSeek was reviewed only as an
OpenAI-compatible provider option; this parser fix did not require live LLM
spend.

## Literature And Method Basis

- DeepSeek official API docs confirm OpenAI/Anthropic-compatible API formats and
  `https://api.deepseek.com` as the OpenAI-compatible base URL.
- Europe PMC RESTful API documentation confirms `fullTextXML` for Open Access
  full text XML retrieval.
- JATS tag-library documentation records article-level metadata and `table-wrap`
  table containers, supporting parser-level section/table handling.

## Changes Made

- Extended `structured_paper_from_grobid_tei_xml` to parse both GROBID TEI and
  JATS article XML.
- Added JATS title, nested `body/sec/title/p` section recovery, `table-wrap`
  table caption/text recovery, and XML-source labeling as `jats_xml`.
- Added a regression test that verifies nested JATS methods/results sections and
  table content are available for routing.
- Regenerated `docs/EXTRACTION_READINESS_H001_H016.md` and
  `data/literature/bovine_extraction_readiness_H001_H016.tsv`.
- Updated README, workflow manuals, corpus manifest, method review, method-source
  registry, and `.env.example` to document JATS parsing and DeepSeek local
  configuration without secrets.

## Current Readiness Result

- H001-H014: ready for section-routed operator extraction.
- H015-H016: missing ingested paper/full text because both map to R024.
- Summary: 14 direct-ready, 0 fallback-ready, 0 partial, 2 missing.

## What This Does Not Claim

- No evidence field was extracted or approved.
- No human adjudication decision was made.
- No wet-lab variable was approved.
- The proliferation audit remains `NO-GO`.

## Verification

- `git diff --check`: passed.
- `.venv/bin/python -m pytest -q`: 58 passed, 3 warnings.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 14 ready, 0 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed; ontology loaded 176
  surface terms.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.

## Next 3 Steps

1. Run operator extraction on the direct-ready H001-H014 sources.
2. Human reviewer fills `data/literature/bovine_adjudication_H001_H014.tsv`.
3. Obtain R024 main full text before H015-H016 can enter the same preflight.

---

# Session 13 (Codex) — DeepSeek/OpenAI-compatible config hardening

Date: 2026-07-09
Branch: `codex/llm-provider-fail-fast`

## Coordination Decision

The next non-blocked task was to prepare for H001-H014 live operator extraction
without creating a provider/configuration trap for Codex, Claude, or the project
owner. Local ignored config still pointed at the legacy `deepseek-chat` model,
and the versioned template also recommended that name. DeepSeek's current docs
now list `deepseek-v4-flash` and `deepseek-v4-pro` as current model names and
mark `deepseek-chat` / `deepseek-reasoner` as compatibility names deprecated
after 2026-07-24 15:59 UTC.

No API key was written to the repository, command history in committed files,
or generated reports. The local ignored `config/config.yaml` was inspected only
for non-secret provider/model settings and was not edited.

## Literature And Method Basis

- DeepSeek official quick-start/API docs confirm OpenAI-compatible access at
  `https://api.deepseek.com`.
- DeepSeek official Models & Pricing docs identify `deepseek-v4-flash` and
  `deepseek-v4-pro` as current models and document the deprecation date for
  `deepseek-chat` / `deepseek-reasoner`.
- DeepSeek Create Chat Completion docs document the `thinking` request object,
  so CultivateAgent now exposes an `llm.extra_body` passthrough for
  provider-specific OpenAI-compatible request options.

## Changes Made

- Added `llm.extra_body` to typed configuration.
- Passed `extra_body` through `Config.make_llm_client`, the LLM factory, and the
  OpenAI-compatible/Gemini clients.
- Added an offline test that proves an OpenAI-compatible client sends
  `extra_body={"thinking": {"type": "disabled"}}` to the SDK call.
- Updated `config/config.example.yaml`, `.env.example`, README, method review,
  DeepSeek live-run note, workflow manuals, and method-source registry.

## What This Does Not Claim

- No live DeepSeek extraction was run in this session.
- No evidence field was extracted or approved.
- No human adjudication decision was made.
- No wet-lab variable was approved.

## Verification

- `git diff --check`: passed.
- `.venv/bin/python -m pytest -q`: 59 passed, 3 warnings.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 14 ready, 0 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed; ontology loaded 176
  surface terms.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.

## Next 3 Steps

1. Update the ignored local `config/config.yaml` manually before any live run:
   use `model: deepseek-v4-flash` or `deepseek-v4-pro`, set
   `OPENAI_BASE_URL=https://api.deepseek.com`, and optionally set
   `extra_body: { thinking: { type: disabled } }` for low-cost extraction.
2. Run a small supervised H001-H014 operator-extraction pilot before scaling to
   all 14 ready tasks.
3. Keep the human adjudication worksheet as the wet-lab evidence gate.

---

# Session 14 (Codex) — target live extraction by review/source IDs

Date: 2026-07-09
Branch: `codex/jats-fulltext-readiness`

## Coordination Decision

The next non-blocked task was to make the planned H001-H014 live operator
extraction controllable. Before this session, `cultivate extract` could filter
by tier and limit, but not by H review IDs or R source record IDs. That made a
small DeepSeek/GPT/Claude pilot too easy to aim at the wrong papers or scale
accidentally.

The decision was to add target selection before spending live LLM calls:
`cultivate extract --ids H014 --mode operators` now resolves H review IDs
through the bovine review queue and manifest to the matching ingested paper.
Direct paper IDs and R source record IDs also work. Duplicate review tasks that
map to the same source paper are extracted once.

## Changes Made

- Added `--ids`, `--review-queue`, and `--manifest` to `cultivate extract`.
- Added review/source/paper ID resolution for extraction targets.
- Hardened ID range parsing so only patterns like `H001-H014` are expanded;
  hyphenated paper IDs/slugs are no longer misread as ranges.
- Added an offline unit test for H review ID, R source ID, and direct paper ID
  resolution.
- Ran a mock-provider smoke check:
  `cultivate extract --ids H014 --mode operators --provider mock --model mock --limit 1`.
  This verified target selection only; it is not a scientific extraction result.
- Updated README, both workflow manuals, bovine manifest, method review, and
  this session log.

## What This Does Not Claim

- No live DeepSeek/GPT/Claude extraction was run in this session.
- The mock smoke run does not approve any evidence field.
- No human adjudication decision was made.
- No wet-lab variable was approved.

## Verification

- `git diff --check`: passed.
- `.venv/bin/python -m pytest -q`: 60 passed, 3 warnings.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 14 ready, 0 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli extract --ids H014 --mode operators --provider mock --model mock --limit 1`:
  passed; extracted exactly 1 paper, R023/H014. This was a target-selection
  smoke test only.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed; ontology loaded 176
  surface terms.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.

## Next 3 Steps

1. Configure the live provider locally without committing secrets.
2. Run a small supervised live pilot, for example
   `cultivate extract --ids H014 --mode operators --provider openai --model deepseek-v4-flash`.
3. Inspect extraction metadata and grounding before scaling to
   `cultivate extract --ids H001-H014 --mode operators`.

---

# Session 15 (Codex) — provider-failure handling for live extraction

Date: 2026-07-09
Branch: `codex/jats-fulltext-readiness`

## Coordination Decision

The next non-blocked task was to run the planned H014 live operator-extraction
pilot through the new `--ids` targeting path. The command reached the
DeepSeek-compatible provider endpoint, but every operator failed at the provider
call layer because the currently available environment key did not authenticate.

This exposed a real pipeline bug: `cultivate extract` printed a successful
extraction message and wrote an empty extraction record even when all operators
had `call_error`. That is unsafe for a thesis workflow because downstream export
or review could mistake a provider failure for a sparse extraction.

## Changes Made

- Cleaned the local ignored SQLite failed extraction row created by the failed
  pilot.
- Added `_is_total_operator_call_failure` to detect operator-mode extractions
  where all operators failed at the provider-call layer.
- Updated `cultivate extract` so total provider-call failure is not written to
  the knowledge base and returns a nonzero exit code.
- Added an offline regression test for total operator-call failure detection.
- Re-ran the same H014 live pilot; it now exits nonzero, reports 0 extracted
  papers, and leaves the local extraction table empty.
- Updated README, workflow manuals, method review, and this session log.

## What This Does Not Claim

- No successful live DeepSeek extraction occurred.
- No evidence field was extracted or approved.
- No human adjudication decision was made.
- No wet-lab variable was approved.

## Verification

- `OPENAI_BASE_URL=https://api.deepseek.com .venv/bin/python -m cultivate_agent.cli extract --ids H014 --mode operators --provider openai --model deepseek-v4-flash --limit 1`:
  reached the provider but failed authentication; after the fix it exited
  nonzero, reported 0 extracted papers, and did not write an extraction record.
- Local cleanup check: removed the failed ignored SQLite row; after final mock
  smoke cleanup, `remaining_extractions=0`.
- `git diff --check`: passed.
- `.venv/bin/python -m pytest -q`: 61 passed, 3 warnings.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 14 ready, 0 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli extract --ids H014 --mode operators --provider mock --model mock --limit 1`:
  passed as a target-selection smoke test only; the local mock extraction row was
  removed afterward.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed; ontology loaded 176
  surface terms.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.

## Next 3 Steps

1. Provide or configure a valid provider key locally without committing secrets.
2. Re-run `cultivate extract --ids H014 --mode operators --provider openai --model deepseek-v4-flash`.
3. Proceed to H001-H014 only after H014 has nonzero filled fields and acceptable
   grounding metadata.

---

# Session 16 (Codex) — fail-fast non-retryable provider errors

Date: 2026-07-09
Branch: `codex/llm-provider-fail-fast`

## Coordination Decision

The next non-blocked task was to reduce live extraction trial-and-error after
the H014 DeepSeek-compatible pilot failed authentication. The previous fix
prevented empty extraction records, but the LLM layer still retried
non-retryable authentication failures. That wastes time and provider calls
before every operator reports `call_error`.

During this session, a separate local unpushed commit
`0c8d279 fix(optimize): dedupe evidence beliefs by component in EvidencePrior`
was present on `codex/jats-fulltext-readiness`. To avoid mixing another agent's
optimization work into this provider-layer change, this session's final commit
was moved to a new branch from `origin/codex/jats-fulltext-readiness`:
`codex/llm-provider-fail-fast`.

DeepSeek's official error-code documentation distinguishes configuration or
account problems (400 invalid format, 401 authentication, 402 balance, 422
invalid parameters) from rate-limit/server conditions (429, 500, 503). The
project should therefore fail fast for non-retryable provider errors and keep
backoff for transient errors.

## Changes Made

- Added provider-agnostic non-retryable error detection to `LLMClient.complete`.
- Fail-fast now covers common authentication, balance/quota, permission,
  invalid-request, invalid-parameter, and missing-model failures.
- Transient provider errors still use the existing retry/backoff path.
- Added light error-message scrubbing before provider errors enter logs or
  extraction metadata.
- Added offline tests proving auth-like errors call the provider once and
  transient 503-like errors retry up to `max_retries`.
- Verified the current H014 DeepSeek-compatible pilot now fails quickly, exits
  nonzero, and writes no extraction record.
- Updated README, workflow manuals, method review, method-source registry, and
  this session log.

## What This Does Not Claim

- No successful live DeepSeek extraction occurred.
- No evidence field was extracted or approved.
- No human adjudication decision was made.
- No wet-lab variable was approved.

## Verification

- `OPENAI_BASE_URL=https://api.deepseek.com .venv/bin/python -m cultivate_agent.cli extract --ids H014 --mode operators --provider openai --model deepseek-v4-flash --limit 1`:
  after fail-fast handling, failed quickly with provider authentication error,
  exited nonzero, and wrote no extraction record.
- `.venv/bin/python -m pytest tests/test_pipeline.py::test_llm_client_does_not_retry_auth_errors tests/test_pipeline.py::test_llm_client_retries_transient_errors -q`:
  passed; auth-like errors call once, transient 503-like errors retry.
- `git diff --check`: passed.
- `.venv/bin/python -m pytest -q`: 63 passed, 3 warnings on
  `codex/llm-provider-fail-fast`.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 14 ready, 0 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed; ontology loaded 176
  surface terms.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.

## Next 3 Steps

1. Configure a valid provider key locally without committing secrets.
2. Re-run H014 live pilot and inspect filled fields, per-operator status, and
   quote grounding.
3. Scale to H001-H014 only after H014 is technically successful.

---

# Session 17 (Codex) — worktree migration and main-line merge

Date: 2026-07-09
Branch: `main` in `/Users/tianyangsong/Desktop/Research/CultivateAgent-codex`

## Coordination Decision

Claude identified that Codex's recent work was stranded on two side branches
while `main` had already advanced with the isolated-worktree protocol. The
highest-value task was therefore not new extraction work, but coordination:
move Codex into its own worktree, merge the Codex branches into `main`, validate
the integrated state, and delete stale feature branches after pushing.

## Changes Made

- Confirmed active worktrees:
  `/Users/tianyangsong/Desktop/Research/CultivateAgent-claude` for Claude and
  `/Users/tianyangsong/Desktop/Research/CultivateAgent-codex` for Codex.
- Merged `origin/codex/jats-fulltext-readiness` into `main`.
- Merged `origin/codex/llm-provider-fail-fast` into `main`.
- Created an isolated `.venv` in the Codex worktree instead of reusing another
  worktree's interpreter.
- Copied ignored local `data/papers/` assets into the Codex worktree for
  readiness verification only; these assets remain untracked.
- Pushed the merged `main` and deleted the merged Codex feature branches both
  remotely and locally.
- Updated the collaboration protocol, README, English workflow, Chinese
  workflow, and this session log.

## What This Does Not Claim

- No new live DeepSeek/GPT/Claude/Gemini extraction was run.
- No evidence field was approved.
- No human adjudication decision was entered.
- No wet-lab variable was approved.

## Verification

- `git diff --check`: passed.
- `.venv/bin/python -m pytest -q`: 62 passed, 2 skipped in the isolated Codex
  worktree venv.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed after local paper assets were copied into the Codex worktree; 14 ready,
  0 fallback-ready, 0 partial, 2 not ready. The generated files were restored to
  avoid committing path-only changes from the new worktree location.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.

## Next 3 Steps

1. Ask Claude to rebase/rebaseline on the updated `main` before the v4 quality
   re-run.
2. Continue with H014 live pilot only after valid provider credentials are
   configured locally without committing secrets.
3. Keep future Codex changes in `/Users/tianyangsong/Desktop/Research/CultivateAgent-codex`
   and merge/delete short-lived branches promptly.

---

# Session 18 (Codex) — portable extraction-readiness paths

Date: 2026-07-09
Branch: `codex/readiness-portable-paths`

## Coordination Decision

After Codex moved into its own worktree, rerunning
`cultivate extraction-readiness` produced the same scientific readiness counts
but changed every `fulltext_path` from the old checkout path to the Codex
worktree path. That is noisy for a multi-agent project because path-only churn
looks like a data change.

The decision was to make readiness reports repo-portable before continuing live
LLM extraction work. This keeps H001-H016 audit artifacts stable when Codex,
Claude, or a human reruns the command from different worktrees.

## Changes Made

- Added a `path_base` option to `build_extraction_readiness`.
- `cultivate extraction-readiness` now passes the configured project root, so
  generated Markdown and TSV reports use `data/papers/.../fulltext.txt` instead
  of machine-specific absolute paths.
- Added a regression assertion that readiness paths are relative when a base is
  provided.
- Regenerated `docs/EXTRACTION_READINESS_H001_H016.md` and
  `data/literature/bovine_extraction_readiness_H001_H016.tsv`; readiness counts
  are unchanged.
- Updated README and both workflow manuals.

## What This Does Not Claim

- No live extraction was run.
- No evidence field was approved.
- No human adjudication decision was entered.
- No wet-lab variable was approved.

## Verification

- `.venv/bin/python -m pytest tests/test_operators.py::test_extraction_readiness_reports_operator_context -q`:
  passed.
- `.venv/bin/python -m pytest -q`: 62 passed, 2 skipped.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 14 ready, 0 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.

## Next 3 Steps

1. Merge this short-lived branch into `main`, push, and delete it.
2. Continue toward the H014 live pilot only after provider credentials are
   configured locally without committing secrets.
3. Ask Claude to rebase/rebaseline on updated `main` before continuing the v4
   quality run.

---

# Session 19 (Codex) — portable human-review packet paths

Date: 2026-07-09
Branch: `codex/review-packet-portable-paths`

## Coordination Decision

After making extraction-readiness paths portable, the same problem remained in
the S4 human-review packet and blank adjudication worksheet. Both artifacts are
meant to be shared among Codex, Claude, and human reviewers, but they recorded
machine-specific absolute `fulltext.txt` paths.

The decision was to make review-packet and adjudication-template outputs use
repo-relative `data/papers/...` paths too. This keeps the human review handoff
stable across isolated worktrees and avoids noisy path-only diffs.

## Changes Made

- Added a `path_base` option to `build_review_packet`.
- Added the same option to `write_adjudication_template`.
- `cultivate review-packet` and `cultivate adjudication-template` now pass the
  configured project root, producing portable `data/papers/.../fulltext.txt`
  paths.
- `write_adjudication_template` now writes LF line endings explicitly so TSV
  regeneration does not introduce diff-check whitespace noise.
- Regenerated `docs/HUMAN_REVIEW_PACKET_H001_H016.md` and
  `data/literature/bovine_adjudication_H001_H014.tsv`.
- Added regression assertions that review packet hits and worksheet rows use
  relative paths when a path base is provided.
- Updated README and both workflow manuals.

## What This Does Not Claim

- No human review decision was entered.
- No evidence field was approved.
- No live extraction was run.
- No wet-lab variable was approved.

## Verification

- `.venv/bin/python -m pytest tests/test_evidence.py::test_review_packet_builds_locators_without_adjudicating tests/test_evidence.py::test_adjudication_template_and_validation -q`:
  passed.
- `.venv/bin/python -m pytest -q`: 62 passed, 2 skipped.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 14 ready, 0 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md`:
  passed; 14/16 tasks have local full-text locators.
- `.venv/bin/python -m cultivate_agent.cli adjudication-template --ids H001-H014 --out data/literature/bovine_adjudication_H001_H014.tsv`:
  passed; regenerated the blank 14-row human worksheet with relative paths.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed after LF-regenerating the worksheet; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.

## Next 3 Steps

1. Merge this short-lived branch into `main`, push, and delete it.
2. Keep the next scientific step focused on H014 live pilot or human
   adjudication after Claude rebases on current `main`.
3. Do not regenerate or overwrite the human worksheet after a reviewer starts
   filling decisions; validate/export it instead.

---

# Session 20 (Codex) — local adjudication passage preview

Date: 2026-07-09
Branch: `codex/adjudication-passages`

## Coordination Decision

The next non-conflicting S4 task was to reduce the manual cost of using the
blank H001-H014 adjudication worksheet. The worksheet already had portable
`fulltext_path` values and suggested character ranges, but a human still had to
open files manually and jump to ranges without a helper.

The decision was to add a local preview command that reads the worksheet and
prints short snippets for suggested or selected ranges. It is deliberately a
review aid only: it does not set decisions, does not approve evidence, and
defaults to stdout so source excerpts are not committed.

## Changes Made

- Added `build_adjudication_passage_previews`,
  `format_adjudication_passages_markdown`, and
  `write_adjudication_passages_markdown`.
- Added CLI command:
  `cultivate adjudication-passages --ids H014 --max-ranges 1`.
- The command resolves repo-relative `data/papers/...` paths against the project
  root, prefers `selected_range` when present, otherwise previews
  `suggested_ranges`, and reports missing files or invalid ranges explicitly.
- Added regression coverage for relative path resolution and selected-range
  preview behavior.
- Updated README and both workflow manuals.

## What This Does Not Claim

- No human decision was entered.
- No evidence field was approved.
- No live extraction was run.
- No wet-lab variable was approved.
- No source excerpts were committed as generated output; the preview command is
  for local human use.

## Verification

- `.venv/bin/python -m pytest tests/test_evidence.py::test_adjudication_passage_preview_resolves_relative_paths -q`:
  passed.
- `.venv/bin/python -m pytest -q`: 63 passed, 2 skipped.
- `.venv/bin/python -m cultivate_agent.cli adjudication-passages --ids H014 --max-ranges 1 --context-chars 80`:
  passed locally; 1/1 ranges readable. Output was redirected to `/tmp` and not
  committed.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 14 ready, 0 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md`:
  passed; 14/16 tasks have local full-text locators.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.

## Next 3 Steps

1. Merge this short-lived branch into `main`, push, and delete it.
2. Next scientific progress still requires either human adjudication of
   H001-H014 or valid-provider H014 live extraction.
3. Keep Claude's model-comparison commits separate until that worktree is
   rebased on current `main`.

---

# Session 21 (Codex) — adjudication worksheet status gate

Date: 2026-07-09
Branch: `codex/adjudication-status`

## Coordination Decision

The next non-conflicting S4 task was to make worksheet progress machine-readable
without reading source passages or changing any human fields. `adjudication-validate`
already proved the blank worksheet was structurally valid, but it did not tell
humans or other agents whether the review gate had actually advanced.

The decision was to add `cultivate adjudication-status`: a lightweight summary
of blank, resolved, evidence-bearing, invalid, and validation-issue counts. This
helps prevent a blank PASS from being mistaken for evidence approval.

## Changes Made

- Added `AdjudicationStatus`, `summarize_adjudication_worksheet`,
  `format_adjudication_status_markdown`, and
  `write_adjudication_status_markdown`.
- Added CLI command:
  `cultivate adjudication-status --out docs/HUMAN_ADJUDICATION_STATUS_H001_H014.md`.
- Generated `docs/HUMAN_ADJUDICATION_STATUS_H001_H014.md`.
- Extended adjudication tests to cover blank and supported worksheet status.
- Updated README, both workflow manuals, and the bovine corpus manifest.

## Current Result

- H001-H014 status: 14 rows, 14 blank decisions, 0 resolved decisions,
  0 evidence-bearing decisions, 0 validation issues.
- Ready for evidence export: no.

## What This Does Not Claim

- No human decision was entered.
- No evidence field was approved.
- No live extraction was run.
- No wet-lab variable was approved.

## Verification

- `.venv/bin/python -m pytest tests/test_evidence.py::test_adjudication_template_and_validation -q`:
  passed.
- `.venv/bin/python -m pytest -q`: 63 passed, 2 skipped.
- `.venv/bin/python -m cultivate_agent.cli adjudication-status --out docs/HUMAN_ADJUDICATION_STATUS_H001_H014.md`:
  passed; 0/14 resolved, 0 evidence-bearing decisions, 0 validation issues.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 14 ready, 0 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md`:
  passed; 14/16 tasks have local full-text locators.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.

## Next 3 Steps

1. Merge this short-lived branch into `main`, push, and delete it.
2. Human reviewers can now use `adjudication-status`, `adjudication-passages`,
   and `adjudication-validate` together while filling H001-H014.
3. After human decisions exist, run `adjudication-status` and
   `adjudication-export` before any S5 search-space decision.

---

# Session 22 (Codex) — protect filled adjudication worksheets

Date: 2026-07-09
Branch: `codex/protect-adjudication-template`

## Coordination Decision

The S4 worksheet is now the human-review source of truth. A real risk remained:
rerunning `cultivate adjudication-template` after a reviewer has filled
decisions would overwrite human work with a blank template.

The decision was to protect human decisions by default. The template command now
refuses to overwrite an existing worksheet with any nonblank `decision` value.
It still allows regeneration of a blank worksheet, and it allows intentional
overwrite only with `--force` after a reviewed copy has been saved.

## Changes Made

- Added overwrite protection to `write_adjudication_template`.
- Added `cultivate adjudication-template --force` for deliberate overwrite.
- Added regression coverage proving nonblank worksheets are protected and
  `force_overwrite=True` is explicit.
- Updated README and both workflow manuals.

## What This Does Not Claim

- No human decision was entered.
- No evidence field was approved.
- No live extraction was run.
- No wet-lab variable was approved.

## Verification

- `.venv/bin/python -m pytest tests/test_evidence.py::test_adjudication_template_and_validation -q`:
  passed.
- `.venv/bin/python -m pytest -q`: 63 passed, 2 skipped.
- `.venv/bin/python -m cultivate_agent.cli adjudication-template --ids H001-H014 --out data/literature/bovine_adjudication_H001_H014.tsv`:
  passed because the committed worksheet is still blank.
- `.venv/bin/python -m cultivate_agent.cli adjudication-status --out docs/HUMAN_ADJUDICATION_STATUS_H001_H014.md`:
  passed; 0/14 resolved, 0 evidence-bearing decisions, 0 validation issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 14 ready, 0 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md`:
  passed; 14/16 tasks have local full-text locators.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.

## Next 3 Steps

1. Merge this short-lived branch into `main`, push, and delete it.
2. When human decisions are entered, use `adjudication-status`,
   `adjudication-validate`, and `adjudication-export`; do not regenerate the
   template unless `--force` is intentional.
3. Claude still needs to rebase its three local commits onto current `main`.

---

# Session 23 (Codex) — backup before forced worksheet overwrite

Date: 2026-07-09
Branch: `codex/adjudication-force-backup`

## Coordination Decision

Session 22 protected filled adjudication worksheets by default. The remaining
risk was the explicit `--force` path: a reviewer or AI could intentionally
overwrite a filled worksheet but forget to preserve the reviewed copy first.

The decision was to make `force_overwrite=True` safer by automatically creating
a timestamped `.bak` copy of the existing worksheet when it contains nonblank
decisions. This backup is a last-resort guard; the normal workflow is still to
avoid regenerating a filled worksheet.

## Changes Made

- Added automatic backup creation before forced overwrite of a worksheet with
  nonblank decisions.
- Added regression coverage proving the backup preserves the prior supported
  decision before the template is regenerated.
- Updated README and both workflow manuals.

## What This Does Not Claim

- No human decision was entered.
- No evidence field was approved.
- No live extraction was run.
- No wet-lab variable was approved.

## Verification

- `.venv/bin/python -m pytest tests/test_evidence.py::test_adjudication_template_and_validation -q`:
  passed.
- `.venv/bin/python -m pytest -q`: 63 passed, 2 skipped.
- `.venv/bin/python -m cultivate_agent.cli adjudication-template --ids H001-H014 --out data/literature/bovine_adjudication_H001_H014.tsv`:
  passed because the committed worksheet is still blank.
- `.venv/bin/python -m cultivate_agent.cli adjudication-status --out docs/HUMAN_ADJUDICATION_STATUS_H001_H014.md`:
  passed; 0/14 resolved, 0 evidence-bearing decisions, 0 validation issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 14 ready, 0 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md`:
  passed; 14/16 tasks have local full-text locators.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.

## Next 3 Steps

1. Merge this short-lived branch into `main`, push, and delete it.
2. Continue to treat H001-H014 human adjudication as the blocking S4 gate.
3. Claude still needs to rebase its three local commits onto current `main`.

---

# Session 24 (Codex) — ignore local adjudication backups

Date: 2026-07-09
Branch: `codex/ignore-adjudication-backups`

## Coordination Decision

Session 23 added timestamped `.bak` files before forced overwrite of a filled
adjudication worksheet. Those backups are useful as local safety copies, but
they should not become versioned project artifacts or confuse the S4 evidence
ledger.

The decision was to add an explicit ignore rule for adjudication worksheet
backup files and document that they are local-only safeguards.

## Changes Made

- Added `.gitignore` rule for `data/literature/*.tsv.bak.*`.
- Updated README and both workflow manuals to state that forced-overwrite
  backups are ignored by git and should stay local.
- Updated this session log.

## What This Does Not Claim

- No human decision was entered.
- No evidence field was approved.
- No live extraction was run.
- No wet-lab variable was approved.

## Verification

- Temporary ignored-file check:
  `data/literature/bovine_adjudication_H001_H014.tsv.bak.codex-check` appeared
  as ignored (`!!`) and was removed before commit.
- `.venv/bin/python -m pytest -q`: 63 passed, 2 skipped.
- `.venv/bin/python -m cultivate_agent.cli adjudication-status --out docs/HUMAN_ADJUDICATION_STATUS_H001_H014.md`:
  passed; 0/14 resolved, 0 evidence-bearing decisions, 0 validation issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 14 ready, 0 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md`:
  passed; 14/16 tasks have local full-text locators.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.

## Next 3 Steps

1. Merge this short-lived branch into `main`, push, and delete it.
2. Continue to treat H001-H014 human adjudication as the blocking S4 gate.
3. Claude still needs to rebase its three local commits onto current `main`.

---

# Session 25 (Codex) — S4 human-in-the-loop method record

Date: 2026-07-09
Branch: `codex/s4-hitl-method-record`

## Coordination Decision

The project already had review-packet and adjudication tooling, but the method
rule behind S4 needed to be explicit enough for humans, Claude, and future AI
agents to apply consistently.

After checking systematic-review and review-automation sources, the adopted rule
is:

- AI may rank records, generate source locators, preview snippets, and validate
  worksheet structure.
- Humans decide evidence support, selected ranges, dose and endpoint
  interpretation, exclusion reasons, and wet-lab readiness.
- Outcome-direction and dose/range rows that can affect wet-lab variables need
  independent checking or an explicit `[REVIEW]` waiver.
- A blank worksheet that validates is only a valid form, not evidence approval.

## Sources Added

- `M038`: Cochrane MECIR selection/data-collection standards.
- `M039`: PRISMA-trAIce AI-assisted systematic-review reporting checklist.
- `M040`: Marshall and Wallace 2019 practical guide to systematic-review
  automation.

These complement the existing PRISMA, ASReview, SWIFT-Review, and
RobotReviewer entries.

## Changes Made

- Added `M038-M040` to
  `data/literature/ai_for_science_method_sources.tsv`.
- Added a new S4 method subsection to
  `docs/AI_FOR_SCIENCE_METHOD_REVIEW.md`.
- Updated the S4 checklists and gate language in both workflow manuals.
- Updated README and `docs/BOVINE_CORPUS_MANIFEST.md` to state that S4 tools are
  review aids, not adjudicators.
- Updated this session log.

## What This Does Not Claim

- No human decision was entered.
- No evidence row was approved.
- No live extraction was run.
- No wet-lab design packet was generated.

## Verification

- TSV registry structure check: 40 rows, 9 columns, no malformed rows.
- Secret scan for pasted-style Gemini/DeepSeek/OpenAI key patterns: no hits.
- `.venv/bin/python -m pytest -q`: 63 passed, 2 skipped.
- `.venv/bin/python -m cultivate_agent.cli adjudication-status --out docs/HUMAN_ADJUDICATION_STATUS_H001_H014.md`:
  passed; 0/14 resolved, 0 evidence-bearing decisions, 0 validation issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 14 ready, 0 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md`:
  passed; 14/16 tasks have local full-text locators.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.

## Next 3 Steps

1. Merge this short-lived branch into `main`, push, and delete it.
2. Have a human reviewer pilot 2-3 H001-H014 worksheet rows before filling the
   whole worksheet.
3. After human edits, validate and export only supported or partial rows.

---

# Session 26 (Codex) — integrate Claude DeepSeek comparison handoff

Date: 2026-07-12
Branch: `codex/integrate-claude-v4-comparison`

## Coordination Decision

Claude had three useful commits stranded on its isolated worktree:

- `scripts/run_evidence_parallel.py` gained `--model`, `--max-tokens`, and
  `--items-out` for controlled provider/model comparisons plus tier reporting.
- `config/ontology/growth_factors.yaml` mapped "basic fibroblast growth factor"
  to FGF2 so live-model aliases pool correctly.
- `docs/MODEL_COMPARISON_DEEPSEEK.md` recorded a controlled 15-paper DeepSeek
  comparison.

Codex integrated those commits into a short-lived Codex branch rather than
editing Claude's worktree. During review, Codex corrected the model-comparison
language: DeepSeek's official docs currently describe `deepseek-chat` as a
compatibility name for `deepseek-v4-flash` non-thinking mode, so the report is a
compatibility-route vs explicit `deepseek-v4-flash` comparison, not a clean
V3-vs-V4 model-family comparison.

## Changes Made

- Cherry-picked Claude's three local commits into this Codex branch.
- Added official DeepSeek model-name links to
  `docs/MODEL_COMPARISON_DEEPSEEK.md`.
- Updated README, `docs/AI_FOR_SCIENCE_METHOD_REVIEW.md`,
  `docs/BOVINE_CORPUS_MANIFEST.md`, and both workflow manuals.
- Recorded that the comparison remains direction-only evidence and does not
  approve wet-lab variables.
- Updated this session log.

## What This Does Not Claim

- The DeepSeek comparison is not wet-lab evidence.
- The compatibility-route output is not a validated V3 baseline.
- Direction-only effect items are not quantitative effect sizes.
- No human adjudication decision was entered.

## Verification

- `.venv/bin/python scripts/run_evidence_parallel.py --help`: passed; help
  includes `--model`, `--max-tokens`, and `--items-out`.
- Ontology check: "basic fibroblast growth factor", "bFGF", and "FGF-2" all
  canonicalize to FGF2.
- Secret scan for pasted-style Gemini/DeepSeek/OpenAI key patterns: no hits.
- `.venv/bin/python -m pytest -q`: 63 passed, 2 skipped.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed; ontology surface
  terms increased from 176 to 177 after the new FGF2 alias.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.
- `.venv/bin/python -m cultivate_agent.cli adjudication-status --out docs/HUMAN_ADJUDICATION_STATUS_H001_H014.md`:
  passed; 0/14 resolved, 0 evidence-bearing decisions, 0 validation issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 14 ready, 0 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md`:
  passed; 14/16 tasks have local full-text locators.

## Next 3 Steps

1. Merge this branch into `main`, push, and delete it.
2. Use `scripts/run_evidence_parallel.py --model ... --items-out ...` for future
   controlled live comparisons.
3. Prototype a number-aware effect extractor before claiming random-effects
   quantitative synthesis from literature.

---

# Session 27 (Codex) — quote-level numeric verification for effect items

Date: 2026-07-12
Branch: `codex/verify-effect-numbers`

## Decision

The DeepSeek comparison showed that both routes produced direction-only evidence.
The next safe step was not to claim quantitative synthesis, but to prevent LLM
numbers from entering `EvidenceItem.effect` or `EvidenceItem.variance` unless
the verified quote actually contains the supporting number.

This is a conservative gate:

- If the quote supports both `effect` and `variance`, the item can remain tier 1.
- If the quote supports `effect` but not `variance`, the item becomes tier 2.
- If the quote supports neither numeric field, the item stays tier 3
  direction-only.

It does not compute fold-changes, standardized mean differences, or variances
from raw treatment/control data. That remains future work.

## Changes Made

- Hardened `evidence.extract_effects` so unquoted `effect` and `variance`
  numbers are cleared before creating `EvidenceItem` records.
- Updated the effect-extraction prompt to require quoted numeric support for
  numeric fields.
- Added an offline mock-LLM test for numeric demotion behavior.
- Updated README, `docs/EVIDENCE_SYNTHESIS.md`,
  `docs/AI_FOR_SCIENCE_METHOD_REVIEW.md`,
  `docs/MODEL_COMPARISON_DEEPSEEK.md`, and both workflow manuals.
- Updated this session log.

## What This Does Not Claim

- No new wet-lab evidence was approved.
- No human adjudication decision was entered.
- No deterministic fold-change or variance calculator was implemented.
- Literature numbers still do not become BO training labels.

## Verification

- Focused numeric-demotion tests:
  `.venv/bin/python -m pytest tests/test_evidence.py::test_extract_effects_demotes_unquoted_numbers tests/test_evidence.py::test_extract_effects_drops_ungrounded -q`:
  passed.
- `.venv/bin/python -m pytest -q`: 64 passed, 2 skipped.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed.
- `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`: passed;
  hypervolume rose from 7.050 to 16.464.
- Secret scan for pasted-style Gemini/DeepSeek/OpenAI key patterns: no hits.
- `.venv/bin/python -m cultivate_agent.cli adjudication-status --out docs/HUMAN_ADJUDICATION_STATUS_H001_H014.md`:
  passed; 0/14 resolved, 0 evidence-bearing decisions, 0 validation issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 14 ready, 0 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md`:
  passed; 14/16 tasks have local full-text locators.

## Next 3 Steps

1. Merge this branch into `main`, push, and delete it.
2. Prototype deterministic extraction of treatment/control numeric values with
   units and endpoints.
3. Add human review fields for numeric effect-size validation before any tier 1
   evidence is used in reports.
