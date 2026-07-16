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

---

# Session 28 (Codex) — quote-based log fold-change inference

Date: 2026-07-12
Branch: `codex/infer-log-fold-change`

## Decision

The previous numeric gate prevented unsupported LLM numbers from entering
quantitative evidence tiers. The next useful step was a tiny deterministic
effect-size parser for explicit proportional phrases in verified quotes.

Adopted rule:

- If a verified quote explicitly reports a fold change, such as "2-fold
  increase", infer `effect = ln(2)`.
- If a verified quote explicitly reports a percent change, such as "50%
  reduction", infer `effect = ln(0.5)`.
- Do not infer any variance.
- Do not parse medium concentrations, doses, or raw treatment/control means as
  effect sizes.

This follows Cochrane ratio-measure guidance and the Hedges/Gurevitch/Curtis
log response-ratio method, recorded as `M041-M042`.

## Changes Made

- Added `M041-M042` to
  `data/literature/ai_for_science_method_sources.tsv`.
- Added conservative `ln(ratio)` inference to `evidence.extract_effects` for
  explicit fold/percent-change phrases.
- Added offline tests for 2-fold increase, 50% reduction, and a non-effect
  medium percentage that must remain tier 3.
- Updated README, `docs/EVIDENCE_SYNTHESIS.md`,
  `docs/AI_FOR_SCIENCE_METHOD_REVIEW.md`,
  `docs/MODEL_COMPARISON_DEEPSEEK.md`, and both workflow manuals.
- Updated this session log.

## What This Does Not Claim

- No variance is inferred.
- Raw treatment/control means are not parsed yet.
- Literature effect sizes still do not become BO training labels.
- No wet-lab variable or human evidence decision was approved.

## Verification

- Focused tests:
  `.venv/bin/python -m pytest tests/test_evidence.py::test_extract_effects_infers_log_fold_change_from_quote tests/test_evidence.py::test_extract_effects_demotes_unquoted_numbers -q`:
  passed.
- TSV registry structure check: 42 rows, 9 columns, no malformed rows.
- Secret scan for pasted-style Gemini/DeepSeek/OpenAI key patterns: no hits.
- `.venv/bin/python -m pytest -q`: 65 passed, 2 skipped.
- `.venv/bin/python -m cultivate_agent.cli smoke`: passed.
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
2. Add deterministic treatment/control mean extraction with units and endpoint
   labels.
3. Add human numeric-review fields before any tier 1 evidence is used in thesis
   claims.

---

# Session 29 (Codex) — numeric effect adjudication fields

Date: 2026-07-12
Branch: `codex/numeric-adjudication-fields`

## Decision

Quote-level numeric verification and quote-based log fold-change inference were
necessary but not sufficient for thesis-use evidence. A value inferred from a
verified quote can still be misinterpreted, incomplete, variance-free, or
context-dependent. The S4 worksheet therefore needs a separate human numeric
review gate.

Adopted rule:

- Directional evidence review remains in `decision`.
- Quantitative effect review is recorded separately in
  `numeric_effect_status`, `numeric_effect_metric`, `numeric_effect_value`,
  optional `numeric_effect_variance`, and `numeric_effect_notes`.
- `supported` and `partial` numeric statuses require a metric and numeric value.
- Legacy worksheets without these fields still validate, so old human notes are
  not broken.

## Changes Made

- Added numeric-effect review columns to the H001-H014 adjudication worksheet
  and adjudicated evidence export table.
- Hardened worksheet validation for numeric-effect status, required metric/value
  on supported or partial numeric effects, and numeric parsing of value and
  variance fields.
- Kept legacy worksheet validation compatible when numeric-effect columns are
  absent.
- Regenerated the committed blank H001-H014 worksheet and header-only evidence
  table with the new columns.
- Updated README, both workflow manuals, corpus manifest, evidence synthesis
  notes, and AI-for-science method review.

## What This Does Not Claim

- No human adjudication decision was entered.
- No numeric value was approved for thesis claims.
- No wet-lab variable, search-space bound, or design packet was approved.

## Verification

- Focused adjudication test:
  `.venv/bin/python -m pytest tests/test_evidence.py::test_adjudication_template_and_validation -q`:
  passed.
- Full pytest:
  `.venv/bin/python -m pytest -q`: 65 passed, 2 skipped.
- Secret scan for pasted-style Gemini/DeepSeek/OpenAI key patterns:
  no hits.
- S4 CLI checks:
  `.venv/bin/python -m cultivate_agent.cli adjudication-status --out docs/HUMAN_ADJUDICATION_STATUS_H001_H014.md`:
  passed; 0/14 resolved, 0 evidence-bearing decisions, 0 validation issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 14 ready, 0 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md`:
  passed; 14/16 tasks have local full-text locators.
- Smoke and demo optimization:
  smoke passed; `optimize --demo --rounds 6` passed with hypervolume rising
  from 7.050 to 16.464.

## Next 3 Steps

1. Human reviewer fills H001-H014, including numeric-effect fields where a row
   carries a quantitative claim.
2. AI validates and exports only after human decisions exist.
3. Extend deterministic number-aware extraction to treatment/control means only
   after the S4 numeric review gate remains stable.

---

# Session 30 (Codex) — treatment/control mean log-ratio inference

Date: 2026-07-12
Branch: `codex/raw-mean-log-ratio`

## Decision

The next useful S3/S4 improvement was to reduce manual arithmetic for quoted
quantitative evidence while keeping the human numeric gate intact. Cochrane
ratio-measure guidance, Hedges/Gurevitch/Curtis response ratios, and
Friedrich/Adhikari/Beyene ratio-of-means work support log-ratio effects when
the experimental and control means are explicitly reported.

Adopted rule:

- Infer `ln(treatment_mean/control_mean)` only when a verified quote contains
  exactly one treatment mean and one control/comparator mean.
- Do not infer variance.
- Skip numbers that are doses, concentrations, timepoints, passages, percentages,
  fold changes handled by the existing parser, or embedded in factor names such
  as `FGF2`.
- Store `effect_metric`, `effect_inference_source`, treatment/control means,
  endpoint, and timepoint in `EvidenceItem.context` for human review.

## Changes Made

- Added a conservative treatment/control mean parser to
  `evidence.effect_operator`.
- Hardened numeric matching so embedded factor-name numbers do not support or
  create effect values.
- Added an offline test covering quoted treatment/control means and a dose
  number that must remain non-effect evidence.
- Added method-source record `M043` for ratio of means.
- Updated README, both workflow manuals, corpus manifest, evidence synthesis,
  AI-for-science method review, and this session log.

## What This Does Not Claim

- No human numeric effect was approved.
- No variance is inferred from means alone.
- No cross-paper numeric value is used as a BO training label.
- No wet-lab design packet or variable promotion was created.

## Verification

- Focused numeric tests:
  `.venv/bin/python -m pytest tests/test_evidence.py::test_extract_effects_infers_log_ratio_from_treatment_control_means tests/test_evidence.py::test_extract_effects_infers_log_fold_change_from_quote tests/test_evidence.py::test_extract_effects_demotes_unquoted_numbers -q`:
  passed.
- TSV registry structure check:
  passed; 43 rows, 9 columns, no malformed rows.
- Secret scan for pasted-style Gemini/DeepSeek/OpenAI key patterns:
  no hits.
- Full pytest:
  `.venv/bin/python -m pytest -q`: 66 passed, 2 skipped.
- S4 CLI checks:
  `.venv/bin/python -m cultivate_agent.cli adjudication-status --out docs/HUMAN_ADJUDICATION_STATUS_H001_H014.md`:
  passed; 0/14 resolved, 0 evidence-bearing decisions, 0 validation issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 14 ready, 0 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md`:
  passed; 14/16 tasks have local full-text locators.
- Smoke and demo optimization:
  smoke passed; `optimize --demo --rounds 6` passed with hypervolume rising
  from 7.050 to 16.464.

## Next 3 Steps

1. Human reviewer still needs to adjudicate H001-H014, including numeric-effect
   status where an extracted row carries a quantitative claim.
2. Extend deterministic variance extraction only when SD/SE, sample size, and
   group mapping are explicitly quoted.
3. Run a small live operator extraction pilot after the provider environment is
   known to be valid.

---

# Session 31 (Codex) — ROM variance from quoted group statistics

Date: 2026-07-12
Branch: `codex/rom-variance-from-quote`

## Decision

The treatment/control mean parser created tier-2 log response ratios. The next
safe improvement was to compute a within-study variance only when the same
verified quote includes the additional group statistics required by the
large-sample ROM formula.

Adopted rule:

- Infer `effect = ln(treatment_mean/control_mean)` from explicit group means.
- Infer ROM sampling variance only when both treatment and control groups also
  have SD/SE/SEM and `n` in the quote.
- Convert SE/SEM to SD using `SD = SE * sqrt(n)`.
- Do not infer variance from means alone, missing group sizes, CI-only text, or
  table layouts not represented in the quote.
- Keep S4 numeric-effect review as the thesis-use gate.

The method basis is Cochrane ratio-measure guidance, Hedges/Gurevitch/Curtis
response ratios, Friedrich/Adhikari/Beyene ratio of means, and the metafor ROM
implementation notes.

## Changes Made

- Extended `evidence.effect_operator` so deterministic numeric inference can
  carry a variance as well as an effect.
- Added quote-only parsing for group `mean`, SD/SE/SEM, and `n`.
- Added context fields for treatment/control SD, group sizes, and the variance
  formula identifier `ROM_LS_Hedges1999`.
- Added an offline test that promotes a complete quoted group-statistics item to
  tier 1 with expected variance.
- Added method-source record `M044`.
- Updated README, both workflow manuals, corpus manifest, evidence synthesis,
  AI-for-science method review, and this session log.

## What This Does Not Claim

- No human numeric effect was approved.
- CI-only, p-value-only, table-only, or ambiguous multi-group evidence is not
  parsed as variance.
- Literature effect sizes still do not become BO training labels.
- No wet-lab design packet or variable promotion was created.

## Verification

- Focused numeric tests:
  `.venv/bin/python -m pytest tests/test_evidence.py::test_extract_effects_infers_rom_variance_from_quoted_group_stats tests/test_evidence.py::test_extract_effects_infers_log_ratio_from_treatment_control_means tests/test_evidence.py::test_extract_effects_demotes_unquoted_numbers -q`:
  passed.
- TSV registry structure check:
  passed; 44 rows, 9 columns, no malformed rows.
- Secret scan for pasted-style Gemini/DeepSeek/OpenAI key patterns:
  no hits.
- Full pytest:
  `.venv/bin/python -m pytest -q` in the current managed sandbox reached 66
  passed and 2 skipped, then failed only
  `tests/test_pipeline.py::test_grobid_client_writes_and_parses_tei`.
  The failure is environmental: even a minimal `urllib` POST to a local
  `HTTPServer` fails with `RemoteDisconnected` in this sandbox.
- Non-loopback pytest:
  `.venv/bin/python -m pytest -q -k 'not test_grobid_client_writes_and_parses_tei'`:
  passed; 66 passed, 2 skipped, 1 deselected.
- S4 CLI checks:
  `.venv/bin/python -m cultivate_agent.cli adjudication-status --out docs/HUMAN_ADJUDICATION_STATUS_H001_H014.md`:
  passed; 0/14 resolved, 0 evidence-bearing decisions, 0 validation issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md --fail-on-issues`:
  passed; 14 rows, 0 issues.
- `.venv/bin/python -m cultivate_agent.cli adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv --out data/literature/bovine_evidence_table.tsv`:
  passed; 0 adjudicated evidence rows exported.
- `.venv/bin/python -m cultivate_agent.cli extraction-readiness --ids H001-H016 --out docs/EXTRACTION_READINESS_H001_H016.md --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv`:
  passed; 14 ready, 0 fallback-ready, 0 partial, 2 not ready.
- `.venv/bin/python -m cultivate_agent.cli review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md`:
  passed; 14/16 tasks have local full-text locators.
- Smoke and demo optimization:
  smoke passed; `optimize --demo --rounds 6` passed with hypervolume rising
  from 7.050 to 16.464.

## Next 3 Steps

1. Human reviewer still needs to adjudicate H001-H014 and verify any numeric
   effect fields before thesis use.
2. Extend deterministic extraction to CI-formatted and table-formatted group
   statistics only when source text exposes all required values.
3. Run a small live operator extraction pilot after provider credentials are
   confirmed valid.

---

# Session 32 (Codex) — strict corpus alignment for extraction evaluation

Date: 2026-07-13
Branch: `codex/eval-corpus-alignment`

## Decision

T1/T2 evaluation previously iterated only over returned predictions. A gold
paper with no prediction was therefore omitted from both the paper count and
field recall, and duplicate IDs were silently collapsed by dictionary
construction. This could make an incomplete provider run look better than it
was. Corpus alignment must be auditable before further live model comparisons.

Adopted rule:

- Score every gold paper exactly once.
- Treat a missing paper-level prediction as an empty extraction so populated
  gold fields become false negatives.
- Report expected, predicted, matched, missing, and unexpected paper IDs.
- Reject duplicate IDs on either side instead of choosing one by input order.
- Do not score an unexpected prediction without a gold record.

## Changes Made

- Added alignment metadata and coverage reporting to `EvalReport`.
- Hardened `evaluate_corpus` with strict ID alignment and duplicate detection.
- Added regression tests for missing, unexpected, and duplicate records.
- Updated the evaluation report generator and recorded 4/4 ID coverage for the
  existing live benchmark. Its F1 of 0.254 and missing grounding remain
  unchanged and still fail the extraction-reliability gate.
- Updated README and both workflow manuals.

## What This Does Not Claim

- The four-paper fixture is not a complete full-text production benchmark.
- Complete paper-ID coverage does not imply adequate field coverage.
- The live OpenAI/Anthropic run remains too sparse for valid model agreement.
- No human adjudication, wet-lab variable, or design packet was approved.

## Verification

- Focused evaluation tests:
  `.venv/bin/python -m pytest tests/test_pipeline.py::test_extraction_eval_prf tests/test_pipeline.py::test_extraction_eval_corpus_counts_missing_and_unexpected_records tests/test_pipeline.py::test_extraction_eval_corpus_rejects_duplicate_ids -q`:
  passed; 3 passed.
- Offline report-generation check in `/tmp`:
  passed; mock benchmark reported 4/4 matched, no missing IDs, and no unexpected
  IDs without changing the committed live-provider result.
- Non-loopback pytest:
  `.venv/bin/python -m pytest -q -k 'not test_grobid_client_writes_and_parses_tei'`:
  passed; 68 passed, 2 skipped, 1 deselected. The deselected local-HTTP test is
  the previously documented managed-sandbox limitation.
- CLI smoke and optimization demo:
  passed; smoke completed and hypervolume rose from 7.050 to 16.464.
- `git diff --check` passed; secret scan found no pasted-style API keys.

## Next 3 Steps

1. Add explicit field-support and evidence-coverage diagnostics so a paper-level
   record containing only bibliographic prefill cannot look extraction-complete.
2. Human reviewer completes H001-H014 adjudication.
3. Re-run a one-paper live operator pilot only after provider credentials are
   valid, then scale if grounding and non-missing gates pass.

---

# Session 33 (Codex) — separate field and evidence coverage diagnostics

Date: 2026-07-13
Branch: `codex/eval-field-coverage`

## Start-State Assessment

Before choosing work, the evidence-based baseline was unchanged from the prior
audit: software infrastructure about 72%, literature/evidence work about 43%,
wet-lab-entry readiness about 24%, and the full workflow through paper results
about 29% (reasonable range 25-33%). The strict corpus-ID fix improved metric
integrity but did not pass a scientific gate, so it did not justify increasing
the full-workflow percentage.

The highest-value non-human task was to prevent 4/4 paper-ID coverage from being
misread as extraction completeness. H001-H014 adjudication remains human-only
and was recorded rather than simulated.

## Decision

Extraction evaluation must report four distinct layers:

- paper-ID alignment;
- presence of predictions for populated gold field cells;
- evidence attachment for non-bibliographic B-M predicted fields;
- grounding of attached evidence.

A zero denominator is reported as `None`; an empty substantive extraction must
never appear to have perfect evidence coverage.

## Changes Made

- Added gold-field presence and substantive evidence-attachment counters to
  `EvalReport`.
- Excluded Block A bibliographic prefill from substantive-field counts.
- Counted attached evidence flagged `UNVERIFIED` separately from attachment.
- Updated the report generator and tests.
- Updated README, both workflow manuals, collaboration protocol, evaluation
  report, and this session log.
- The committed live benchmark is now explicit: 4/4 paper IDs, but only 8/45
  populated gold field cells, zero B-M substantive fields, and therefore no
  evidence-attachment denominator or grounding result.

## What This Does Not Claim

- Evidence attachment is not evidence grounding or scientific correctness.
- Gold-field presence is not exact-value accuracy; P/R/F1 remains separate.
- The live benchmark still fails Gate 2.
- No human evidence or wet-lab condition was approved.

## Completion Impact

This change increases auditability and reduces future rework risk, but it does
not pass extraction reliability, human adjudication, or wet-lab gates. The
rounded full-workflow estimate therefore remains 29%; software infrastructure
may be described as about 73% only after regression verification succeeds.

## Verification

- Focused coverage tests: 4 passed.
- Non-loopback suite:
  `.venv/bin/python -m pytest -q -k 'not test_grobid_client_writes_and_parses_tei'`:
  69 passed, 2 skipped, 1 deselected. The deselection is the previously recorded
  managed-sandbox local-HTTP limitation.
- Offline report generation: passed; mock fixture reported 38/45 gold-field
  presence, 30 substantive fields, and 5/30 evidence attachment, demonstrating
  that attachment and grounding expose different failure modes.
- CLI smoke passed.
- Optimization demo passed; hypervolume rose from 7.050 to 16.464.
- `git diff --check` passed; secret scan found no pasted-style API keys.

## Next 3 Steps

1. Add a gate-oriented report that evaluates the predefined decision-critical
   fields rather than treating every A-M field as equally important.
2. Human reviewer completes H001-H014 adjudication; AI validates and exports it.
3. Re-run H014 live extraction only after provider credentials are valid.

---

# Session 34 (Codex) — decision-critical Gate 2 coverage

Date: 2026-07-13
Branch: `codex/eval-critical-field-gate`

## Start-State Assessment

The evidence-based baseline at session start was: software infrastructure about
73%, literature/evidence work about 43%, wet-lab-entry readiness about 24%, and
the complete workflow through paper results about 29% (reasonable range
25-33%). Gate 2, H001-H014 human adjudication, cost/supply review, robustness,
pre-registration, wet-lab execution, and result analysis were still unpassed.

The highest-value non-human task was to convert the documented Gate 2 critical
field threshold into an executable, conservative acceptance result. This makes
future H014 live pilots decisional rather than merely descriptive.

## Literature Check And Decision

Cochrane Handbook Chapter 5 was verified against both the official Cochrane
chapter and the Wiley chapter record. It supports predefined and pilot-tested
structured forms, explicit outcome/intervention data items, transparent missing
information, and independent checking of decision-critical outcome data. Added
method record `M045` documents the source and project use.

Adopted rules:

- Evaluate species, cell type, stage, medium type, serum-free status, component
  identity, dose/range, and endpoint separately at non-missing >= 0.75.
- Any concept below threshold makes Gate 2 `FAIL`; pooled coverage cannot offset
  it.
- A concept absent from gold is `NOT_EVALUABLE`, never an automatic pass.
- A-M `dose_range` is a J-block proxy. Complete proxy coverage can produce at
  most `PROVISIONAL_ONLY` until the dedicated dose operator and human review
  confirm component-dose pairs.
- Final Gate 2 approval still also requires grounding >= 0.95 and agreement or
  human adjudication; this coverage status is necessary but not sufficient.

## Changes Made

- Added eight decision-critical concept groups and threshold evaluation to
  `EvalReport`.
- Added `FAIL`, `NOT_EVALUABLE`, `PROVISIONAL_ONLY`, and conservative `PASS`
  states.
- Added per-concept tables to `scripts/evaluate_medium_corpus.py`.
- Added tests for sparse failure, complete proxy coverage, and incomplete gold.
- Updated the committed live report: 0/17 applicable critical cells, Gate 2
  `FAIL`; stage and medium type are not evaluable in the current fixture.
- Updated README, both workflow manuals, wet-lab decision record, method review,
  bovine manifest, method registry, and this session log.

## What This Does Not Claim

- The current fixture is not sufficient to validate all eight concepts.
- A coverage pass would not prove value correctness, grounding, agreement, or
  human approval.
- No current live provider passes Gate 2.
- No wet-lab variable or experiment was approved.

## Verification

- Focused Gate tests: 4 passed.
- Non-loopback suite:
  `.venv/bin/python -m pytest -q -k 'not test_grobid_client_writes_and_parses_tei'`:
  71 passed, 2 skipped, 1 deselected. The deselection is the known managed
  environment local-HTTP limitation.
- Offline mock report generation passed. It demonstrated why per-concept gating
  is required: pooled critical coverage was 16/17 (0.9412), but endpoint was
  1/2 (0.5), stage and medium type were not evaluable, and the result correctly
  remained `FAIL`.
- Method registry validation passed: 45 data rows, 9 columns, no malformed row.
- CLI smoke passed.
- Optimization demo passed; hypervolume rose from 7.050 to 16.464.
- `git diff --check` passed; secret scan found no pasted-style API keys.

## Completion Impact

Software infrastructure rises conservatively from about 73% to about 74%
because Gate 2 is now executable and tested. Literature/evidence work remains
about 43%, wet-lab-entry readiness remains about 24%, and the complete paper
workflow remains about 29%: the current real benchmark failed, no human row was
adjudicated, and no scientific gate passed.

## Next 3 Steps

1. Make the dedicated operator extraction emit a direct component-dose coverage
   report so `dose_range` no longer depends on the A-M proxy.
2. Human reviewer completes H001-H014; AI validates and exports without changing
   scientific decisions.
3. Run H014 live operator extraction only after provider credentials are valid,
   and require all Gate 2 metrics before scaling.

---

# Session 35 (Codex) — grounded component-dose operator records

Date: 2026-07-13
Branch: `codex/operator-dose-records`

## Start-State Assessment

The session began at approximately 74% software infrastructure, 43%
literature/evidence work, 24% wet-lab-entry readiness, and 29% for the complete
workflow through paper results (reasonable range 25-33%). The previous Gate 2
implementation exposed `dose_range` as the sole A-M proxy. No real benchmark,
human adjudication, wet-lab gate, or result-analysis gate had passed.

The highest-value non-human task was therefore to make the existing dedicated
dose operator emit auditable component-dose relations. This removes a technical
precondition for a future direct Gate 2 decision without fabricating evidence or
cross-pairing independent lists.

## Decision And Method Basis

The implementation follows the already registered DocETL-style method decision:
keep document extraction modular, schema-bound, and independently verifiable.
It also follows Cochrane Chapter 5's requirement to keep intervention, outcome,
group, and numerical result data explicit rather than relying on ambiguous
summaries.

Adopted rules:

- A dose record links component, dose/range, optional unit, comparison group,
  endpoint, and one evidence object.
- One quote must contain both the reported component string and reported numeric
  dose/range. A separately supplied unit must occur in the quote or dose string.
- The quote must verify against the local source text.
- If evidence verification is disabled, a dose record remains ungrounded and
  cannot count as direct coverage.
- Invalid records remain visible as `grounded=false` with an `UNVERIFIED`
  locator, but cannot count as direct Gate 2 coverage.
- Flat J-block fields remain backward compatible and remain proxy evidence.
- Direct operator coverage does not replace S4 human numeric adjudication.

## Changes Made

- Added typed `ComponentDoseRecord` support to the dose operator.
- Extended the dose prompt with an optional relation-level output schema and an
  explicit same-quote rule.
- Added local component, numeric-dose, unit, and full-text verification.
- Stored all records and grounded counts in extraction metadata.
- Extended Gate 2 reporting with `direct_predicted`; complete grounded records
  can change dose basis from `proxy` to `direct_operator`.
- Added positive, mismatched-component, verification-disabled, and Gate-upgrade
  tests.
- Updated README, both workflow manuals, wet-lab decision record, evidence and
  method reviews, bovine manifest, evaluation report, and this session log.

## What This Does Not Claim

- No current live extraction has produced a reviewed direct dose record.
- String verification does not prove biological interpretation or group mapping.
- A direct technical Gate result still requires grounding, agreement or human
  adjudication, and all other wet-lab gates.
- Literature doses remain priors/search-space evidence, never BO labels.

## Verification

- Focused operator/Gate tests: 4 passed.
- Non-loopback suite:
  `.venv/bin/python -m pytest -q -k 'not test_grobid_client_writes_and_parses_tei'`:
  73 passed, 2 skipped, 1 deselected. The deselection is the known local-HTTP
  managed-environment limitation.
- Offline evaluation report generation passed.
- CLI smoke passed.
- Optimization demo passed; hypervolume rose from 7.050 to 16.464.

## Completion Impact

Software infrastructure rises conservatively from about 74% to about 75% after
verification. Literature/evidence remains about 43%, wet-lab-entry readiness
remains about 24%, and the full workflow remains about 29%, because no real
extraction or scientific gate passed.

## Next 3 Steps

1. Add direct stage and medium-type operator coverage so the current fixture and
   future pilots can evaluate all eight Gate 2 concepts without missing gold.
2. Human reviewer completes H001-H014; AI validates and exports the worksheet.
3. Run H014 live operator extraction after provider credentials are valid and
   inspect direct dose records before any scale-up.

---

# Session 36 (Codex) — direct stage and medium-type fields

Date: 2026-07-13
Branch: `codex/operator-stage-medium-type`

## Start-State Assessment

The evidence-based baseline was about 75% software infrastructure, 43%
literature/evidence work, 24% wet-lab-entry readiness, and 29% for the complete
workflow through paper results (reasonable range 25-33%). Direct dose records
were implemented, but the frozen evaluation fixture still had no evaluable
stage or medium-type gold cells. No scientific or wet-lab gate had newly passed.

The initial idea was to add source-supported stage/type labels to the four-paper
fixture. Audit showed that this would retroactively change a report whose raw
live predictions were not versioned. The safer high-value task was to add narrow
direct schema/operator fields while keeping the historical benchmark frozen.

## Decision And Method Basis

Following the registered SchemaRAG/DocETL schema-reduction decision and
Cochrane's predefined-data-item guidance:

- Add `D.culture_stage` for explicitly reported isolation, expansion or
  proliferation, differentiation, and maturation stages.
- Add `E.medium_type` for explicitly reported formulation roles such as
  expansion, differentiation, conditioned, or spent medium.
- Give the context and medium operators disjoint ownership of the fields.
- Do not infer stage from an endpoint alone or medium type from ingredients.
- Map Gate 2 directly to these fields rather than broad condition summaries or
  basal-medium names.
- Do not backfill the frozen gold fixture without versioned raw predictions and
  human or independent re-adjudication.

## Changes Made

- Added optional typed fields to Blocks D and E; old extraction JSON remains
  compatible.
- Extended the focused context and medium operator prompts and field ownership.
- Replaced Gate 2 stage/medium-type mappings with the dedicated fields.
- Added grounded mock extraction and synthetic Gate tests for both concepts.
- Updated README, both workflow manuals, wet-lab decision record, method review,
  bovine manifest, evaluation report, and this session log.

## What This Does Not Claim

- The existing four-paper fixture now covers stage or medium type; it does not.
- H001-H014 have been re-extracted or adjudicated; they have not.
- A field value is valid without a supporting quote and later human review.
- The historical live benchmark can be recomputed without its raw predictions.

## Completion Impact

This closes another technical schema gap but does not pass a scientific gate.
Software infrastructure may rise from about 75% to about 76% after verification;
literature/evidence remains about 43%, wet-lab entry about 24%, and the full
workflow about 29%.

## Verification

- Focused schema/operator/Gate tests: 3 passed.
- Non-loopback suite:
  `.venv/bin/python -m pytest -q -k 'not test_grobid_client_writes_and_parses_tei'`:
  73 passed, 2 skipped, 1 deselected. The deselection is the known local-HTTP
  environment limitation.
- Offline evaluation report generation passed and preserved stage/medium-type
  `NOT_EVALUABLE` for the unchanged fixture.
- CLI smoke passed.
- Optimization demo passed; hypervolume rose from 7.050 to 16.464.
- `git diff --check` passed; secret scan found no pasted-style API keys.

## Next 3 Steps

1. Persist versioned gold, source excerpts, provider predictions, and run
   metadata so T1/T2 reports become exactly reproducible before gold revision.
2. Human reviewer completes H001-H014; AI validates and exports without changing
   scientific decisions.
3. Run H014 live operator extraction after provider credentials are valid and
   require direct stage/type/dose plus the other Gate 2 concepts.

---

# Session 37 (Codex) — replayable T1/T2 evaluation artifacts

Date: 2026-07-13
Branch: `codex/eval-artifact-replay`

## Start-State Assessment

The session began at approximately 76% software infrastructure, 43%
literature/evidence work, 24% wet-lab-entry readiness, and 29% for the complete
workflow through paper results (reasonable range 25-33%). Direct stage, medium
type, and dose extraction paths existed, but the historical T1/T2 report could
not be reproduced because exact live predictions were not retained.

Claude was concurrently editing `evidence/effect_operator.py`; this session used
only the independent evaluation-script lane and did not touch Claude's file or
worktree.

During push, Claude landed `a60cf42` on `main`. It rejects reagent/medium
concentration percentages as effects, requires explicit change language for
percentage effects, and parses `N +/- M-fold` using N rather than the error term.
This evaluation commit was rebased cleanly onto it, and the shared behavior was
added to README, both workflow manuals, evidence synthesis, and this log.

## Decision And Method Basis

Cochrane Chapter 5 and PRISMA-trAIce require transparent data collection,
automation reporting, verification, and updateability. A prose report is not
sufficient evidence of a model benchmark. The exact gold, predictions, source
version, provider set, failures, and report configuration must travel together.

Adopted rules:

- `--artifacts-out` writes exact gold and every available provider prediction.
- The manifest records ordered paper IDs, source-excerpt SHA-256 values,
  per-file checksums, live-provider labels and failures, and original scored
  provider/agreement scope.
- `--artifacts-in` performs no provider call and restores the original report
  configuration unless the caller explicitly requests another analysis.
- Replay rejects source drift, artifact tampering, unsafe filenames, duplicate
  or unavailable papers, and prediction/gold order misalignment.
- Bundle reports must be byte-stable on replay.
- Before committing a real bundle, a reviewer must check credentials, quote
  rights, provider/model labels, and gold-version approval.

## Changes Made

- Added deterministic artifact serialization and SHA-256 manifests to
  `scripts/evaluate_medium_corpus.py`.
- Added artifact loading, validation, provider-free replay, and CLI flags.
- Added round-trip, fixture-drift, artifact-tamper, and conflicting-option tests.
- Updated README, both workflow manuals, collaboration protocol, method review,
  bovine manifest, legacy evaluation/agreement reports, and this session log.
- Did not fabricate a bundle for the historical live report; its raw predictions
  are unavailable and the report remains explicitly legacy/non-replayable.

## What This Does Not Claim

- The four-paper gold is now human-revalidated or production-grade.
- The historical OpenAI/Anthropic run can be reconstructed.
- Checksums authenticate an author; they detect drift/tampering but are not a
  cryptographic signature.
- Any extraction or wet-lab gate passed.

## Verification

- Artifact tests: 5 passed, covering byte-stable replay, fixture source drift,
  artifact-file tampering, semantic prediction-order drift with a valid updated
  checksum, and replay/live-option conflicts.
- CLI round-trip produced byte-identical `EVAL_RESULTS.md` and
  `MODEL_AGREEMENT.md` while the replay command omitted provider/scope and
  restored them from the manifest.
- Combined Claude/Codex focused tests: 12 passed
  (`test_effect_magnitude.py` plus `test_eval_artifacts.py`).
- Non-loopback suite after rebase:
  `.venv/bin/python -m pytest -q -k 'not test_grobid_client_writes_and_parses_tei'`:
  85 passed, 2 skipped, 1 deselected. The deselection is the known local-HTTP
  environment limitation.
- CLI help exposed both artifact options with the expected semantics.
- CLI smoke passed.
- Optimization demo passed; hypervolume rose from 7.050 to 16.464.
- `git diff --check` passed; secret scan found no pasted-style API keys.

## Completion Impact

Software infrastructure rises conservatively from about 76% to about 79%
because T1/T2 runs can now be preserved and reproduced without provider calls.
Literature/evidence remains about 43%, wet-lab entry about 24%, and the complete
workflow about 29%: the historical benchmark remains legacy, gold remains
unrevalidated, and no scientific gate passed.

## Next 3 Steps

1. Generate and review a committed offline mock-baseline bundle as a format
   exemplar, without presenting mock scores as scientific accuracy.
2. Human reviewer versions and re-adjudicates the four-paper gold before any
   production T1 claim; future live runs must write bundles.
3. Let Claude finish the independent effect-operator work, then rebase and
   inspect its commit before touching overlapping evidence code.

---

# Session 38 (Codex) — committed offline evaluation exemplar

Date: 2026-07-13
Branch: `codex/mock-eval-bundle`

## Start-State Assessment

The session began at approximately 79% software infrastructure, 43%
literature/evidence work, 24% wet-lab-entry readiness, and 29% for the complete
workflow through paper results. Artifact serialization and replay existed, but
the repository had no reviewed bundle demonstrating clean-checkout replay.

The highest-value non-human task was to commit a deterministic offline exemplar
without confusing mock profiles with real model quality. Claude had no
uncommitted changes and was one commit behind; this work stayed in the evaluation
data/test lane.

## Decision

- Commit one small `mock-baseline-v1` bundle generated entirely offline.
- Keep generated reports in `/tmp`; do not overwrite the historical live failure
  report with favorable mock scores.
- Include exact gold and all three mock prediction profiles plus manifest hashes.
- Add a bundle README that prohibits scientific-accuracy and wet-lab use.
- Add a repository-level test so future fixture/schema edits must either preserve
  replay or intentionally version the bundle.
- Do not claim the gold is human-revalidated for the new stage/type fields.

## Changes Made

- Added `data/evaluation/runs/mock-baseline-v1` with gold, three deterministic
  prediction files, manifest, and usage/limitations README.
- Added a narrow `.gitignore` exception for this reviewed exemplar only; all
  other run-specific data remain ignored.
- Added a clean-checkout replay test.
- Updated README, both workflow manuals, and this session log.

## Content Review

- Bundle size is approximately 78 KB excluding its README.
- It contains four structured fixture records and short evidence quotes, not
  paper full text; 22 quote fields were found and the longest is 52 characters.
- Provider labels are explicitly `mock_gpt`, `mock_claude`, and `mock_gemini`.
- No live-provider output, credentials, or user API keys are present.
- Manifest contains source and artifact SHA-256 values and the original
  `mock_gpt`/`mock` report configuration.
- Byte-stable replay was confirmed before commit.

## What This Does Not Claim

- Mock scores estimate GPT, Claude, Gemini, or production extraction accuracy.
- The fixture gold is production-grade or newly human-adjudicated.
- The bundle contributes approved bovine evidence or passes Gate 2.
- Any wet-lab readiness or paper-result milestone advanced.

## Verification

- Artifact tests: 6 passed, including clean-checkout replay of the committed
  bundle.
- Non-loopback suite:
  `.venv/bin/python -m pytest -q -k 'not test_grobid_client_writes_and_parses_tei'`:
  86 passed, 2 skipped, 1 deselected. The deselection is the known local-HTTP
  environment limitation.
- Byte comparison passed for fresh generation versus provider-free replay.
- Bundle scan: no pasted-style API key; 22 quote fields, maximum 52 characters.
- CLI smoke passed.
- Optimization demo passed; hypervolume rose from 7.050 to 16.464.
- `git diff --check` passed.

## Completion Impact

Software infrastructure rises conservatively from about 79% to about 80%
because a clean checkout now contains a tested replay exemplar. Literature and
evidence remains about 43%, wet-lab entry about 24%, and the complete workflow
about 29% because the exemplar is synthetic and no scientific gate passed.

## Next 3 Steps

1. Human or independent reviewers version and re-adjudicate the four-paper gold,
   especially `culture_stage` and `medium_type`, without overwriting v1.
2. Run the next real H014 provider pilot with `--artifacts-out`; inspect all Gate
   2 fields before expanding to H001-H014.
3. Convert accepted H001-H014 decisions into the evidence table, then run
   robustness and cost/supply gates before any wet-lab packet.

---

# Session 39 (Codex) — full-text dual-review T1 gold workflow

Date: 2026-07-13
Branch: `codex/fulltext-gold-review`

## Start-State Assessment

The session began at approximately 80% software infrastructure, 43%
literature/evidence work, 24% wet-lab-entry readiness, and 29% for the complete
workflow. The committed mock bundle proved replayability, but production T1 was
still blocked because the four-paper excerpt fixture was neither full-text nor
versioned dual-human gold.

The highest-value AI task was to prepare a real full-text gold workflow while
leaving all scientific annotation blank for humans. Human annotation itself was
recorded as the gate rather than simulated.

## Corpus Decision

Selected four independent, locally available bovine papers:

- R015: Beefy-9/B8 sustained serum-free expansion anchor.
- R016: chemically defined primary bovine satellite-cell expansion medium.
- R017: commercial serum-free primary bovine myoblast benchmark.
- R023: media-composition effects on bovine satellite-cell proliferation.

This avoids treating multiple H tasks from one paper as independent papers and
keeps the production gold aligned with the bovine expansion-medium target.
Official title/year/DOI/URL come from `bovine_corpus_manifest.tsv`; local
metadata is not trusted when truncated.

## Method Decision

Following Cochrane Chapter 5 duplicate-extraction guidance:

- Every paper x A-M field cell has reviewer 1, reviewer 2, and final adjudication
  decision/value/evidence/location/reviewer/date columns.
- Reviewers work independently; AI cannot fill either review slot.
- Allowed decisions are `reported`, `not_reported`, `not_applicable`,
  `uncertain`, and `defer`.
- `reported` values use typed JSON and require reviewer/date, exact source quote,
  and location. Pydantic validates the field type.
- Source full-text and schema SHA-256 values prevent silent drift.
- The benchmark is READY only when all 380 rows are adjudicated with zero
  validation issues.

## Changes Made

- Added `cultivate_agent.evaluate.gold_review` generator, validator, result
  model, and Markdown status output.
- Added `scripts/prepare_medium_gold_review.py create|merge|validate`.
- Added an isolated single-reviewer template and `merge` command so reviewer 2
  cannot see reviewer 1 values before both are returned.
- Added six tests for blank-template status, valid typed/grounded extraction,
  invalid type/quote/non-reported values, source drift, blind-sheet merge, and
  prevention of adjudication-only READY bypass.
- Generated `data/evaluation/gold/medium-fulltext-v1/manifest.json` and blank
  `review.tsv`, plus human instructions and a narrow `.gitignore` exception.
- Generated `docs/FULLTEXT_GOLD_VALIDATION_MEDIUM_V1.md`.
- Updated README, both workflow manuals, method review, bovine manifest,
  evaluation report, and this session log.

## Current Human Gate

- Rows/expected: 380/380.
- Reviewer 1 completed: 0/380.
- Reviewer 2 completed: 0/380.
- Final adjudication completed: 0/380.
- Structural/hash validation issues: 0.
- Status: `NOT READY`.

No gold value was AI-generated or inferred.

## What This Does Not Claim

- Production T1 evaluation is complete.
- The old excerpt fixture is production gold.
- A structurally valid blank worksheet is evidence.
- H001-H014 evidence adjudication or wet-lab readiness advanced.

## Verification

- Gold-review tests: 6 passed.
- Non-loopback suite:
  `.venv/bin/python -m pytest -q -k 'not test_grobid_client_writes_and_parses_tei'`:
  92 passed, 2 skipped, 1 deselected. The deselection is the known local-HTTP
  environment limitation.
- Current `validate --require-ready` exited 1 as designed: 380/380 structural
  rows, 0/380 in every review/adjudication stage, 0 validation issues,
  `NOT READY`.
- Gold package size: approximately 432 KB; full text is not committed.
- CLI smoke passed.
- Optimization demo passed; hypervolume rose from 7.050 to 16.464.
- `git diff --check` passed; no pasted-style API key was found.

## Completion Impact

Software infrastructure rises conservatively from about 80% to about 82%.
Literature/evidence preparation rises from about 43% to about 45% because four
real full-text sources and a controlled gold protocol are fixed, but no field is
yet human-labelled. Wet-lab entry remains about 24%, and the complete workflow
remains about 29% because production T1, S4, and every wet-lab/result gate remain
unpassed.

## Next 3 Steps

1. `[HUMAN]` Assign two independent reviewers the isolated reviewer template;
   AI validates each returned file and merges only after both finish.
2. `[HUMAN]` Adjudicate all 380 rows; AI runs `--require-ready` and exports a new
   versioned gold artifact without overwriting v1.
3. `[AI]` Only after READY, run operator extraction on the same four full texts,
   save an artifact bundle, and report production T1 per-field P/R/F1,
   grounding, and Gate 2 coverage.

---

# Session 40 (Codex) — blind two-paper gold calibration pilot

Date: 2026-07-13
Branch: `codex/gold-review-pilot`

## Start-State Assessment

The session began at approximately 82% software infrastructure, 45%
literature/evidence preparation, 24% wet-lab-entry readiness, and 29% for the
complete workflow. The 380-cell production gold gate existed, but asking two
reviewers to complete all fields before testing the coding form created a high
risk of systematic disagreement and rework.

The highest-value task was to implement the Cochrane requirement to pilot the
collection form: a smaller, manifest-controlled field scope using the same
source hashes, blind-review files, merge, typing, grounding, and adjudication
rules.

## Pilot Decision

- Papers: R015 and R016, two distinct core bovine expansion-medium studies.
- Scope: 28 high-risk fields, 56 paper x field cells.
- Fields cover identity/DOI, species/cell/stage/passage, eight medium fields,
  three endpoint fields, six quantitative fields, and three findings/limitations
  fields.
- Reviewer files remain isolated and are merged only after both return.
- Validator reports double-review coverage, decision exact agreement, Cohen's
  kappa, both-reported coverage, and reported-value exact agreement.
- Progression requires both reviewers 56/56, zero validation issues, decision
  kappa >= 0.70, all disagreements adjudicated, 56/56 final adjudication, and
  READY status.
- Reported-value agreement is diagnostic; no unsupported universal threshold is
  imposed. List order is canonicalized before comparison; every substantive
  mismatch is adjudicated directly.
- If kappa is below 0.70, revise coding instructions and create a new pilot
  version rather than overwriting v1.
- If kappa is undefined because only one decision class occurs, do not coerce it
  to 1.0; require exact agreement 1.0 and document the prevalence limitation.

## Changes Made

- Added optional manifest-backed `field_paths` to gold generator/validator.
- Added CLI `--field` support with duplicate/unknown-field rejection.
- Added reviewer agreement metrics to validation output.
- Added a subset-scope test and expanded merge assertions for agreement metrics.
- Generated `data/evaluation/gold/medium-pilot-v1` with manifest, controlled
  master, isolated reviewer template, and limitations/progression README.
- Generated `docs/FULLTEXT_GOLD_VALIDATION_MEDIUM_PILOT_V1.md` and refreshed the
  full benchmark validation report with agreement metrics.
- Updated README, both workflow manuals, method review, bovine manifest, and
  this session log.

## Current Human Gate

- Pilot rows/expected: 56/56.
- Reviewer 1 completed: 0/56.
- Reviewer 2 completed: 0/56.
- Double-reviewed: 0/56.
- Decision kappa: not estimable.
- Final adjudication: 0/56.
- Validation issues: 0.
- Status: `NOT READY`.

No reviewer or adjudication value was AI-filled.

## What This Does Not Claim

- The pilot form has been calibrated; humans have not started it.
- Kappa can be interpreted before all 56 rows are independently reviewed.
- Pilot READY substitutes for completing the 380-cell production gold.
- T1, S4, or any wet-lab gate passed.

## Verification

- Gold-review tests: 7 passed.
- Non-loopback suite:
  `.venv/bin/python -m pytest -q -k 'not test_grobid_client_writes_and_parses_tei'`:
  93 passed, 2 skipped, 1 deselected. The deselection is the known local-HTTP
  environment limitation.
- Pilot `validate --require-ready` exited 1 as designed: 56/56 structural rows,
  zero completed reviews, kappa not estimable, zero issues, `NOT READY`.
- Full benchmark validation remains 380/380 structural rows and `NOT READY`.
- CLI smoke passed.
- Optimization demo passed; hypervolume rose from 7.050 to 16.464.
- `git diff --check` passed; no pasted-style API key was found.

## Completion Impact

Software infrastructure rises conservatively from about 82% to about 84%.
Literature/evidence preparation rises from about 45% to about 46% because the
human calibration sequence and agreement metrics are now fixed, but no review
decision exists. Wet-lab entry remains about 24%, and the complete workflow
remains about 29% because production T1 and all downstream scientific gates are
still unpassed.

## Next 3 Steps

1. `[HUMAN]` Two reviewers independently complete the 56-cell pilot using
   isolated files; AI validates each and merges only after both are returned.
2. `[REVIEW]` Adjudicate pilot disagreements and require kappa >= 0.70 plus READY
   before opening the 380-cell benchmark.
3. `[AI]` After production gold is READY, run versioned extraction artifacts and
   replace the legacy T1 report with reproducible full-text metrics.

---

# Session 41 (Codex) — field-aware gold-review passage locators

Date: 2026-07-13
Branch: `codex/gold-review-locators`

## Start-State Assessment

The session began at approximately 84% software infrastructure, 46%
literature/evidence preparation, 24% wet-lab-entry readiness, and 29% for the
complete workflow. The next scientific step was human completion of the 56-cell
pilot, but no DeepSeek environment was configured and the available OpenAI key
had a documented quota failure. No live call was made.

Following the rule to record and skip human/external blockers, the highest-value
AI task was to reduce reviewer navigation cost without assigning any gold value.

## Decision

- Add a read-only `passages` subcommand over a versioned gold manifest.
- Verify source SHA-256 before producing locators.
- Allow record and field filters, bounded context, and bounded hit count.
- Use field-specific lexical terms for the 28-field pilot and safe fallback terms
  elsewhere.
- Return raw character ranges and short whitespace-normalized snippets.
- Never edit master/reviewer worksheets.
- Treat no lexical hit as inconclusive, never as `not_reported`.
- Keep generated snippets local unless quotation rights are reviewed.

## Quality Correction

The first real R015 smoke returned introductory lifecycle percentages for
`J.key_numeric_results` because results were sorted by earliest character.
Locator ranking was corrected to preserve curated term specificity:
`doubling time`, `fold`, `passage`, and `cell count` precede generic `mean` and
`%`. The repeated smoke then returned the Beefy-9 doubling-time passages around
chars 22102-22463 rather than introduction statistics.

## Changes Made

- Added field-aware term registry, source-hash validation, filtered passage
  rendering, raw ranges, and bounded snippets to `gold_review.py`.
- Added `prepare_medium_gold_review.py passages` CLI.
- Added a test proving expected hits and byte-identical worksheet preservation.
- Updated pilot/full gold instructions, README, both workflow manuals, method
  review, and this session log.

## What This Does Not Claim

- Lexical locators find every relevant table, figure, or synonym.
- A hit supports a field value.
- A no-hit field is not reported.
- Human pilot work, T1, S4, or wet-lab readiness advanced.

## Verification

- Gold-review tests: 8 passed.
- Real R015 smoke located the expected Beefy-9 doubling-time passages after the
  term-priority correction; output stayed in `/tmp`.
- Non-loopback suite:
  `.venv/bin/python -m pytest -q -k 'not test_grobid_client_writes_and_parses_tei'`:
  94 passed, 2 skipped, 1 deselected. The deselection is the known local-HTTP
  environment limitation.
- CLI `passages --help` exposed record/field/context/hit/output controls.
- CLI smoke passed.
- Optimization demo passed; hypervolume rose from 7.050 to 16.464.
- `git diff --check` passed; no pasted-style API key was found.

## Completion Impact

Software infrastructure rises conservatively from about 84% to about 85%.
Literature/evidence preparation remains about 46%, wet-lab entry remains about
24%, and the complete workflow remains about 29% because no human decision or
scientific gate passed.

## Next 3 Steps

1. `[HUMAN]` Begin the two isolated 56-cell pilot reviews, using local locators
   as navigation aids only.
2. `[AI]` Validate each returned reviewer file, merge after both are complete,
   and compute agreement without reading one review into the other.
3. `[REVIEW]` Revise coding instructions if kappa is below 0.70; otherwise
   adjudicate and open the 380-cell production set only after pilot READY.

---

# Session 42 (Codex) — executable bovine corpus Gate 1 audit

Date: 2026-07-13
Branch: `codex/corpus-gate-audit`

## Start-State Assessment

The session began at approximately 85% software infrastructure, 46%
literature/evidence preparation, 24% wet-lab-entry readiness, and 29% for the
complete workflow. Human gold review remained 0/56 for both reviewers and final
adjudication; H001-H014 evidence adjudication remained 0/14. Claude's isolated
worktree had no new commit and was five commits behind `main`.

The human review blocker was recorded and skipped. The highest-value independent
task was to make Gate 1 reproducible and prevent the 44-row manifest from being
misreported as a curated corpus.

## Decision And Implementation

- Count peer-reviewed records only when their decision is design-included;
  deferred records cannot satisfy coverage.
- Check required metadata for the same design-included set.
- Require explicit human verification for every P1 core record.
- Generate both a Markdown decision report and a row-level TSV issue list.
- Make `--require-pass` return nonzero while any Gate 1 condition fails.
- Add synthetic PASS and multi-cause FAIL tests without inventing corpus data.

## Current Result

The first implementation counted deferred sources and produced an optimistic 40
peer-reviewed sources. Review caught this before merge: only design-included
records now count. The corrected result is 32 peer-reviewed sources, 18 reviews,
14 primary papers, 10 bovine primary papers, 14 dose-bearing primary papers, and
5 serum-free bovine primary papers. Overall Gate 1 is `FAIL`: total coverage is
3 below minimum and 0/11 P1 core rows are human verified.

Four missing DOI values were independently title-matched against Crossref and a
publisher or bibliographic source, then added to the manifest: R008
`10.1016/j.foodres.2025.117016`, R013 `10.1016/j.animal.2024.101242`, R037
`10.1016/j.crfs.2024.100943`, and R038 `10.1111/1541-4337.13193`. Required
metadata now passes; the row-level report contains 11 human-curation issues.

## What This Does Not Claim

- Numerical coverage proves relevance, full-text availability, or evidence
  quality.
- Missing DOI always means a DOI exists; a reviewer must verify it.
- The audit replaces dual review, evidence adjudication, Gate 2, or wet-lab
  approval.

## Verification

- Corpus audit tests: 2 passed, including explicit proof that 34 deferred rows
  cannot make one included source pass the 35-source threshold.
- `audit_bovine_corpus.py --require-pass` wrote both reports and returned 1 for
  the documented Gate 1 failure.
- Non-loopback suite: 96 passed, 2 skipped, 1 deselected. The deselection is the
  known local HTTP/GROBID environment limitation.
- CLI smoke passed.
- Optimization demo passed; hypervolume rose from 7.050 to 16.464.
- `git diff --check` and the repository secret-pattern scan passed.

## Completion Impact

Software infrastructure rises conservatively from about 85% to about 86% after
merge because Gate 1 becomes executable and tested. Literature/evidence remains
about 46%, wet-lab entry remains about 24%, and the complete workflow remains
about 29% because no scientific gate or human review item passed.

## Next 3 Steps

1. `[HUMAN]` Review the 11 P1 manifest decisions.
2. `[AI]` Screen at least three additional non-duplicate peer-reviewed sources,
   then rerun the audit without counting deferred records.
3. `[HUMAN]` Complete the isolated 56-cell dual-review pilot; AI then validates
   agreement before production extraction evaluation.

---

# Session 43 (Codex) — close numerical corpus coverage without counting deferrals

Date: 2026-07-13
Branch: `codex/corpus-gate-coverage`

## Start-State Assessment

The session began at approximately 86% software infrastructure, 46%
literature/evidence preparation, 24% wet-lab-entry readiness, and 29% for the
complete workflow. Gate 1 had 32/35 design-included peer-reviewed sources and
0/11 human-verified P1 records. Human review remained blocked at 0/56 pilot
cells and 0/14 H001-H014 decisions. Claude's worktree had no new commit and was
six commits behind `main`.

The human blockers were recorded and skipped. The highest-value independent
task was to close the three-source numerical gap with relevant, non-duplicate
evidence while preserving the human-curation failure.

## Literature Search And Decisions

Three primary studies were added after title, DOI, publication type, species,
stage, and scope were checked against Crossref plus PubMed and publisher or
institutional records:

- R045, Dolgin et al., Food Research International 2025,
  `10.1016/j.foodres.2024.115633`: VN40 microbial lysate at 40 ug/mL for
  serum-free iBSC expansion. It is `core_context`, not unrestricted direct
  evidence, because immortalized-to-primary transfer is unresolved.
- R046, Kim et al., iScience 2025, `10.1016/j.isci.2025.113242`:
  Pichia-derived bovine and porcine recombinant albumin in primary bMuSCs.
  Europe PMC full text confirmed 800-11,200 ug/mL short-term dose comparisons,
  longer passage experiments, Pax7, proliferation, and differentiation checks.
- R047, Skrivergaard et al., Food Research International 2023,
  `10.1016/j.foodres.2023.113217`: bull-calf versus dairy-cow primary satellite
  cells under in-house serum-free medium versus 10% FBS. It informs donor
  blocking and biological variance; an undisclosed formulation cannot become an
  actionable ingredient recommendation.

The Glycyrrhiza/licochalcone study (`10.1038/s41598-025-98386-1`) was explicitly
excluded from this expansion because bovine and porcine effects were negligible
and the positive result was chicken-specific. This prevents a cross-species
positive finding from being used to pad bovine coverage.

## Changes Made

- Added R045-R047 to the corpus manifest with bounded inclusion rationales and
  unresolved review statuses.
- Added H031-H033 to the human review queue for cell-line transferability,
  albumin dose/source, donor variance, and formulation-disclosure checks.
- Regenerated the Markdown Gate 1 report and row-level issue TSV.
- Extended the audit with duplicate record-ID and normalized included-DOI
  checks, plus a regression test, so repeated citations cannot pad coverage.
- Updated README, both workflow manuals, the wet-lab-entry decision record,
  corpus summary, and this session log.

## Current Result

All numerical and metadata checks now pass: 35 peer-reviewed sources, 18
reviews, 17 primary papers, 13 bovine primary papers, 17 dose-bearing primary
papers, and 8 serum-free bovine primary papers. Gate 1 remains `FAIL` because
0/14 P1 core/core-context records are human verified. The review queue now has
33 open tasks.

## What This Does Not Claim

- The three new papers have passed full-text human adjudication.
- Immortalized iBSC results transfer directly to primary bovine cells.
- R047 discloses an actionable serum-free formulation.
- Numerical corpus coverage permits wet-lab entry or compensates for Gate 2.

## Verification

- Corpus audit tests: 3 passed, including deferred-row exclusion and duplicate
  record-ID/DOI rejection.
- `audit_bovine_corpus.py --require-pass` regenerated both reports and returned
  1 because human curation remains incomplete.
- Non-loopback suite: 97 passed, 2 skipped, 1 deselected. The deselection is the
  known local HTTP/GROBID environment limitation.
- CLI smoke passed.
- Optimization demo passed; hypervolume rose from 7.050 to 16.464.
- TSV width/identifier checks, `git diff --check`, and the repository
  secret-pattern scan passed.

## Completion Impact

Software infrastructure remains about 86%. Literature/evidence preparation
rises conservatively from about 46% to 47% because the numerical and metadata
portion of Gate 1 is now satisfied with verified records, but the gate remains
failed. Wet-lab entry remains about 24%, and the complete workflow remains about
29% because no human decision or scientific gate passed.

## Next 3 Steps

1. `[HUMAN]` Confirm the 14 P1 manifest decisions, using H031-H033 to preserve
   the new evidence boundaries.
2. `[AI]` Obtain lawful full text for R045 where available and prepare locators
   for R045-R047 without assigning evidence decisions.
3. `[HUMAN]` Complete the isolated 56-cell dual-review pilot; AI validates and
   computes agreement only after both reviewer files are returned.

---

# Session 44 (Codex) — lawful full text and review locators for R045-R047

Date: 2026-07-13
Branch: `codex/new-source-review-packet`

## Start-State Assessment

The session began at approximately 86% software infrastructure, 47%
literature/evidence preparation, 24% wet-lab-entry readiness, and 29% for the
complete workflow. Gate 1 numerical, metadata, and identifier checks passed,
but P1 human curation remained 0/14. The dual-review pilot remained 0/56 and
Claude's worktree had no new commit and was seven commits behind `main`.

The human blockers were recorded and skipped. The highest-value independent
task was to move R045-R047 from manifest-only records to lawful, hash-anchored
full-text review inputs without assigning evidence decisions.

## Source And Rights Decisions

- R045 already existed in the owner's ignored local Zotero assets. Its metadata
  was completed locally with the verified DOI and journal; the PDF and extracted
  text remain ignored and are not redistributed.
- R046 was ingested from Europe PMC `PMC12362010` JATS. The article declares CC
  BY-NC-ND 4.0. JATS parsing produced 54,032 characters, 29 sections, one table,
  and five figure captions.
- R047 was ingested from the Aarhus University institutional manuscript. The
  PDF identifies itself as CC BY 4.0; local extraction produced 71,675
  characters.
- Raw PDFs/XML/full text remain under ignored `data/papers/`. Committed reports
  contain paths, source status, short metadata, hashes, and character ranges but
  no long copyrighted excerpts.

## Engineering Corrections

- Review-packet and extraction-readiness headings were hard-coded to H001-H016.
  Both now derive labels from the actual requested task IDs, so H031-H033 reports
  cannot carry a contradictory title.
- Review packets now record the SHA-256 of each local `fulltext.txt`; a reviewer
  can detect source replacement before trusting character ranges.
- Tests cover the dynamic single-task title and source-hash rendering.

## Generated Artifacts

- `docs/HUMAN_REVIEW_PACKET_H031_H033.md`: 3/3 tasks have local, SHA-256-bound
  passage locators. It does not contain AI decisions.
- Regenerated `docs/HUMAN_REVIEW_PACKET_H001_H016.md` under the same integrity
  rule: 14 available sources now carry hashes and the 2 missing R024 tasks remain
  explicitly `MISSING`.
- `docs/EXTRACTION_READINESS_H031_H033.md` and matching TSV: 3/3 tasks are
  directly operator-ready, with no fallback or missing source.
- Manifest statuses for R045-R047 are now
  `fulltext_ingested_for_review_packet`; Gate 1 still fails human curation.

## What This Does Not Claim

- Locator hits support the requested scientific claims.
- Operator readiness is extraction accuracy or Gate 2 success.
- CC/Open Access status permits copying entire articles into committed reports.
- Any R045-R047 evidence has been human approved.

## Verification

- Review-packet/readiness focused tests: 2 passed.
- Non-loopback suite: 97 passed, 2 skipped, 1 deselected. The deselection is the
  known local HTTP/GROBID environment limitation.
- Repeated H031-H033 generation remained 3/3 locator-ready and 3/3 directly
  operator-ready; the TSV has 18 columns on all 16 rows.
- All 3 new and 14 existing available-source locator entries contain a
  64-character source SHA-256; the 2 missing-source entries say `MISSING`.
- `audit_bovine_corpus.py --require-pass` returned 1 for the documented 0/14
  human-curation failure.
- CLI smoke passed.
- Optimization demo passed; hypervolume rose from 7.050 to 16.464.
- `git diff --check` and the repository secret-pattern scan passed.

## Completion Impact

Software infrastructure rises conservatively from about 86% to 87% because
review packets are source-hash anchored and correctly labeled for arbitrary ID
ranges. Literature/evidence preparation rises from about 47% to 48% because all
three new P1 sources now have reviewable local full text and routing reports.
Wet-lab entry remains about 24%, and the complete workflow remains about 29%
because no human decision or scientific gate passed.

## Next 3 Steps

1. `[HUMAN]` Review H031-H033 using the hash-bound locator packet, preserving
   the immortalized-cell and undisclosed-formulation limits.
2. `[HUMAN]` Complete the isolated 56-cell dual-review pilot.
3. `[AI]` After reviewer files return, validate them without cross-exposure and
   compute agreement; do not scale production evaluation before pilot READY.

---

# Session 45 (Codex) — structured-source identity repair

Date: 2026-07-15
Branch: `codex/source-identity-guard`

## Trigger

Preparation of the quantitative human-review pilot exposed a source identity
conflict. Canonical `R029` is the 2018 p38-pathway paper, while the JATS and PDF
source manifests pointed its DOI/XML at the local directory for a different 2025
insulin paper. That directory therefore contained an insulin PDF/plain text and
p38 JATS XML under one metadata record. No R029 candidate can be trusted from
that mixed directory.

## Changes

- Added canonical corpus checks to both Europe PMC JATS acquisition and the P1
  PDF audit. Each source `record_id`, DOI where applicable, and title-derived
  directory must agree before any source is used.
- Added pre-write checks for JATS article title, directory, existing local paper
  ID, metadata title, and metadata DOI. Validation occurs before XML, assets, or
  metadata are changed.
- Corrected R029 to
  `maintaining-bovine-satellite-cells-stemness-through-p38-pathway` in both
  source manifests and reacquired its DOI-verified JATS into that directory.
- Preserved the misattached XML under its SHA-bound quarantine filename in the
  insulin directory, removed it from the active `fulltext.xml` path, and restored
  the insulin metadata DOI (`10.3390/ijms26094109`). These ignored local repairs
  must be repeated or regenerated in other worktrees that copied the old assets.
- Regenerated both source audits. The PDF result is now 10 identity-matched PDFs,
  186 pages, zero statistical line-table cells, and 116 layout-text locators.

## Verification

- Focused identity and PDF-audit tests: 14 passed.
- Non-loopback suite: 137 passed, 2 optional tests skipped, and the known local
  HTTP/GROBID test deselected.
- CLI smoke passed; the synthetic optimization demo increased hypervolume from
  7.050 to 16.464.
- Europe PMC acquisition: 9/9 sources passed canonical identity, DOI, license,
  hash, and parseability checks; 17 tables and 1,258 cells remain unchanged.
- The active insulin directory has no `fulltext.xml`; the quarantined XML and
  the correctly placed p38 XML share the expected SHA-256
  `814e96b8ec5554cadf5157f844f22b7bc82cc32aa5c792c27acb7cbf1c03e4bc`.

## Next Step

Build the bounded dual-blind quantitative locator packet from identity-verified
R018, R045, R047, and a separately verified calibration source. Do not use R029
as the planned PDF negative example because its valid local source is JATS-only.

---

# Session 46 (Codex) — quantitative pointer pilot prepared and held

Date: 2026-07-15
Branch: `codex/quantitative-review-pilot`

## Result

- Added a deterministic 20-locator quantitative review extension linked to the
  existing A-M `J.*` gold fields: R017 (4), R018 (8), R045 (4), and R047 (4).
- Locators contain PDF/page/block/bounding-box hashes and signal categories, but
  no source text or transcribed value fields. DeepSeek cannot structurally emit
  numeric values through this schema.
- Added blind-review validation, agreement/kappa reporting, a strict
  `tier1_ready` role-pointer gate, and local crop rendering. Twenty local crops
  and two separate blank working sheets were generated under ignored data.
- Representative crops from all four sources were visually checked. Full-width
  crop context was used so two-column captions are not truncated.

## Hold Decision

The owner will first adjudicate H001-H014 with Claude and will start this pilot
only after a second independent reviewer is available. DeepSeek must not be used
as reviewer B. The committed benchmark and local working files remain blank.

## Verification

- Quantitative/gold focused tests: 11 passed.
- Both local working sheets validate as 20/20 structurally present, 0 completed,
  and 0 issues. This is expected `HOLD`, not a passed pilot.

## Next Step

Use DeepSeek only for a separate bounded candidate-generation capability probe,
with temperature zero repeated runs, pointer/candidate outputs, hard budgets,
atomic checkpoints, and deterministic Codex acceptance.

---

# Session 47 (Codex) — DeepSeek alias-mapping capability gate

Date: 2026-07-15
Branch: `codex/deepseek-alias-probe`

## Task Boundary

The quantitative human pilot remains on hold and DeepSeek was not used as a
reviewer. The delegated task was limited to mapping ontology alias candidates
to an allowed canonical vocabulary. Outputs could not modify ontology files and
contained no numeric-value fields.

## Implementation

- Built category-balanced alias gold directly from unique aliases already in
  `config/ontology/*.yaml`; no new manual answer set was created.
- Added strict JSON validation, exact ID coverage, allowed-canonical checks,
  `temperature=0`, non-thinking `deepseek-v4-flash`, hard request/token caps,
  no SDK retries, and atomic hash-keyed checkpoints.
- Required three repeats and gated delegation on minimum recall >=0.95 plus
  canonical consistency >=0.95. DeepSeek self-review was not used.
- Verified the current model name, non-thinking toggle, JSON mode, and endpoint
  against official DeepSeek API documentation before the live calls.

## Live Result And Decision

- Canary v1: 3/3 schema-valid calls, recall 0.875 on every repeat, consistency
  1.0, 1,530 reported tokens.
- Recall-oriented prompt v2 kept the gold unchanged and clarified that plausible
  formulation-family mappings should be proposed rather than suppressed.
- Canary v2: 3/3 schema-valid calls, recall still 0.875 on every repeat,
  consistency 1.0, 1,701 reported tokens.
- Both versions stably returned `UNKNOWN` for the ontology mapping
  `Beefy-9 base -> B8`. Total live use was 6 requests and 3,231 reported tokens.
- The 48-alias expansion was not run because the canary failed the predeclared
  recall gate. No ontology alias was added, removed, or changed.

## Verification

- Probe unit tests cover category balancing, strict schema rejection, checkpoint
  resume without duplicate billing, recall, consistency, and gate behavior.
- Raw checkpoints remain under ignored `data/evaluation/runs/`; the committed
  report is `docs/DEEPSEEK_ALIAS_CANARY.md` and contains no key or source text.

## Routing Decision

Do not delegate context-free novel-alias-to-opaque-canonical mapping to DeepSeek
yet. A later probe should target a task better matched to a weak model, such as
metadata-format checking or high-recall page/candidate location, with the same
budget and deterministic-validation controls.

---

# Session 48 (Codex) — DeepSeek high-recall locator gate and bounded shadow

Date: 2026-07-15
Branch: `codex/deepseek-locator-probe`

## Capability Gate

- Reused eight frozen, hash-verified quantitative locators from open R017 and
  R047 as silver positives; no parallel human gold set was created.
- Added 16 deterministic same-paper decoys with no statistical, medium,
  outcome, mean, figure-caption, or error-policy signal. DeepSeek received only
  opaque IDs and short text blocks and could return only candidate IDs.
- Three repeated `deepseek-v4-flash` runs at temperature 0 and with thinking
  disabled produced recall 1.0, precision 0.889, and selection consistency 1.0.
  Precision was reported but was not a delegation gate. Six requests used 8,820
  reported tokens, within the fixed request/token caps.

## Bounded Shadow Delegation

- Because the capability gate passed, expanded only to R018 and R045. A broad
  deterministic statistical-signal prefilter produced 24 hash-bound blocks.
- The shadow run used three repeats, six requests, no retries, atomic
  checkpoints, and 13,731 reported tokens. Selection consistency was 1.0; 18
  unanimously selected pointers were retained.
- The committed shadow manifest contains only record/page/block/text-hash
  pointers. It contains no excerpts or numeric values and was independently
  schema/count/pointer validated after generation.

## Decision Boundary

DeepSeek is now eligible for bounded high-recall block localization behind the
same deterministic prefilter, repeated-run gate, hard budgets, and checkpoint
controls. It is not authorized to transcribe numbers, assign evidence tiers,
adjudicate biology, or replace the held dual-blind quantitative pilot.

## Verification

- Locator-focused tests: 10 passed.
- Non-loopback suite: 147 passed, 2 optional tests skipped, and the known local
  HTTP/GROBID test deselected.
- Both locator CLIs and the main CLI passed help smoke tests; the offline
  end-to-end pipeline completed normally.
- The committed shadow artifact passed schema, count, source-pointer, and hash
  validation and contains no source-text field. The repository secret scan had
  no DeepSeek or Gemini key match.

---

# Session 49 (Codex) — locator shadow audit revokes bulk delegation

Date: 2026-07-15
Branch: `codex/locator-context-prefilter`

## Trigger And Source Audit

Source-level inspection of all 18 v1 selected pointers found systematic
off-target blocks: RNA alignment and protein-count quality control, a reporting
checklist, and a metabolite AUC table. The v1 deterministic prefilter required
only SD/SEM/sample-size syntax, so repeated model agreement did not establish
task validity. The v1 artifact is retained as `superseded_audit_only`.

## Correction

- Added selector `stat-context-block-v2`, which requires both a statistical
  signal and a medium/outcome/figure/error-policy context signal.
- The pool decreased from 24 to 17 blocks and still covered all 12 frozen
  R018/R045 quantitative-pilot locators. A unit test prevents re-admitting
  context-free RNA alignment statistics.
- Added a held-out evaluation gate to the shadow CLI. Stable output is now
  suppressed unless the deterministic prefilter covers every held-out locator
  and model recall is at least 0.95.

## Live Result And Decision

- The v2 run used six schema-valid requests, three repeats, temperature 0,
  thinking disabled, no retries, atomic checkpoints, and 10,212 reported
  tokens. Run-to-run selection consistency was 1.0.
- DeepSeek selected 10/12 held-out silver locators (recall 0.8333), missing
  Q005 and Q009. The committed v2 manifest is
  `failed_held_out_recall_no_output`, contains zero candidate pointers, and
  records `deployment_gate_pass=false`.
- Bulk quantitative-block localization is not delegated to DeepSeek. Q005 and
  Q009 must not be used for prompt tuning and then reused as an independent
  test; promotion requires a new held-out set.

## Verification

- Locator and quantitative focused tests: 9 passed.
- Non-loopback suite: 149 passed, 2 optional tests skipped, and the known local
  HTTP/GROBID test deselected.
- Rebuilt v2 input produced zero manifest-validation issues; deployment remained
  false and the committed candidate list remained empty.
- CLI smoke passed. The six-round optimization demo increased synthetic
  hypervolume from 7.050 to 16.464.
- `git diff --check` and the repository API-key pattern scan passed.

---

# Session 56 (Codex) — source-verified bovine Europe PMC canary

Date: 2026-07-16
Branch: `codex/epmc-bovine-canary`

## Selection And Boundary

- Selected 10 corpus-new Europe PMC candidates from the committed OA audit: 7
  title-level direct bovine medium-intervention primary studies and 3 bovine
  expansion-context studies. The explicit canary manifest is bound to source
  row, DOI, PMCID, title, scope hint, and selection reason.
- This is acquisition-path verification only. No XML entered the canonical
  corpus, no biological scope decision was approved, no numeric value was
  extracted, and no human evidence or wet-lab decision was changed.
- Claude's worktree remained clean at `e27f0e3`; this work stayed in Codex-owned
  ingest files and did not touch normalization, synthesis, or tier-1 audit.

## Implementation And Live Result

- Added a bounded verifier with manifest-to-OA-audit identity checks, hard item
  and download limits, zero retries, atomic local XML checkpoints, exact JATS
  DOI validation, markup-aware title validation, `research-article` type
  validation, in-document CC validation, source hashes, and deterministic
  table/statistical-notation counts.
- The first live run verified 9/10. EBC04 correctly failed because the existing
  parser recognized CC 4.0 and CC0 but not its explicit CC BY-NC 3.0 URL. Direct
  inspection of the Europe PMC JATS license element confirmed the official
  Creative Commons URL; the parser was narrowly extended to BY-family versions
  2.0, 2.5, 3.0, and 4.0. It still rejects vague open-access prose.
- The one-request resume verified EBC04 and reused the other 9 checkpoints.
  Final result: 10/10 source-verified, comprising all 7 direct-medium and all 3
  context candidates. Eight JATS contain tables and three contain cells with
  statistical notation: 25 tables, 996 cells, and 58 notation hits total.
  These are locators, not tier-1 evidence.
- A zero-network replay reused 10/10 checkpoints and reproduced the verification
  TSV byte-for-byte. The committed verification SHA-256 is
  `ac0877a5500c006bd96196ff322eb0ce20e9cad0735da8dc999f0e863b5647eb`.

## Verification

- Non-loopback suite: 174 passed, 2 optional tests skipped, and the known local
  HTTP/GROBID test deselected. New tests cover audit binding, corpus DOI
  non-overlap, hard-budget behavior, checkpoint replay, source DOI/title
  rejection before checkpointing, non-research article rejection, source
  hashes, and explicit CC BY-NC 3.0 parsing.
- CLI smoke passed. The six-round optimization demo increased synthetic
  hypervolume from 7.050 to 16.464.
- Local checkpoint hashes match every committed source hash; table/cell totals,
  status counts, artifact hashes, `git diff --check`, and API-key scanning pass.

## Next

Review the 7 source-verified direct-medium papers against the fixed bovine
satellite-cell/myoblast expansion scope using their JATS metadata and methods.
Promote only valid papers as open, unadjudicated corpus/review candidates; keep
the held double-blind quantitative pilot untouched until the second reviewer is
available.

---

# Session 55 (Codex) — resumable OA discovery for actionable Zotero records

Date: 2026-07-16
Branch: `codex/zotero-oa-audit`

## Decision And Boundary

- Audited all 212 corpus-deduplicated Zotero candidates with Europe PMC and
  Crossref metadata. OpenAlex was excluded because its current API requires a
  key; no LLM or paid provider was needed.
- Metadata produces acquisition leads only. Crossref CC fields do not prove the
  linked file's license, and Europe PMC hits still require the existing JATS
  DOI, in-document license, and structure checks before corpus entry.
- This work did not touch Claude-owned normalization, synthesis, or tier-1
  audit files and did not download or adjudicate scientific evidence.

## Implementation And Result

- Added a zero-retry audit with a global request cap, timeout, rate delay,
  atomic DOI/source checkpoints, bounded workers, exact DOI checks, and
  markup-aware title checks. A 4-worker attempt hit Crossref HTTP 429 and
  stopped cleanly; the resumed 2-worker run reused 225 checkpoints and made
  185 successful requests. The final replay reused all 410 checkpoints with
  zero network requests.
- Results: 75 `epmc_jats_candidate`, 34 `crossref_cc_vor_candidate`, 96
  `metadata_only_license_unverified`, and 7 `missing_doi`. Eighteen initial
  title warnings were all deterministic HTML/encoding/truncation variants;
  markup decoding plus a 0.90 similarity guard resolved them, leaving zero
  identity conflicts.
- The original actionable TSV remained unchanged. The committed audit has 212
  rows and SHA-256
  `4a2eb46365f3fb75721456a3012aff1ee003901090f0ff0a4d9ddef67b5d6255`.

## Verification

- OA-audit focused tests: 6 passed, including hard-budget stop, atomic resume,
  zero-call replay, DOI mismatch rejection, true title mismatch quarantine, and
  harmless HTML/encoding title variants.
- Zero-network replay reproduced the 212-row TSV byte-for-byte and reused
  410/410 source checkpoints.
- Non-loopback suite: 166 passed, 2 optional tests skipped, and the known local
  HTTP/GROBID test deselected. CLI smoke passed; the six-round optimization demo
  increased synthetic hypervolume from 7.050 to 16.464.
- Artifact count/hash validation, `git diff --check`, and the repository
  API-key pattern scan passed.

## Next

Run a bounded canary of the existing Europe PMC fullTextXML verifier on the 75
JATS candidates, then promote only source-verified bovine primary papers into
the canonical manifest/review flow.

---

# Session 54 (Codex) — canonical-corpus deduplication of Zotero acquisitions

Date: 2026-07-16
Branch: `codex/zotero-acquisition-dedup`

## Decision And Implementation

- Preserved `data/literature/zotero_acquire_list.tsv` as the immutable 236-row
  DeepSeek funnel output and added a deterministic derivation step instead of
  rewriting model provenance.
- DOI normalization handles DOI URLs, prefixes, case, Unicode normalization,
  and terminal citation punctuation. Title normalization converts Unicode
  punctuation to separators while preserving Unicode letters during casefold,
  preventing both em-dash word concatenation and Greek-letter collapse.
- Automatic exclusion is conservative: canonical DOI matches are removed;
  title-only matches are removed only when the candidate DOI is missing.
  Equal titles with different non-empty DOI values are never auto-excluded and
  are isolated in a conflict table.
- Added `scripts/deduplicate_zotero_acquisition.py` and three derived artifacts:
  the actionable queue, exclusion audit, and conflict audit. All outputs retain
  original fields or source-row/match pointers and are hash-anchored in the
  generated report.

## Result And Boundary

- Partitioned 236 source rows into 212 actionable acquisitions, 23 deterministic
  exclusions, and one conflict. The exclusions comprise 22 DOI matches already
  present in the 51-record canonical corpus and one DOI-less duplicate of a
  DOI-bearing queue row.
- The conflict is bioRxiv DOI `10.1101/2023.04.17.537163`, whose exact title
  matches the final-publication queue row linked to corpus record R035. It is
  held, not acquired or deleted, until a human checks for unique supplemental
  material.
- Only `data/literature/zotero_acquire_actionable.tsv` is authorized as the next
  acquisition input. Neither the raw list nor the conflict table is an approved
  download queue.

## Verification

- Deduplication tests: 3 passed, covering DOI URL normalization, Unicode title
  punctuation, corpus DOI/title matches, DOI-less queue duplicates, and
  different-DOI conflict preservation.
- Non-loopback suite: 160 passed, 2 optional tests skipped, and the known local
  HTTP/GROBID test deselected. CLI smoke passed; the six-round optimization demo
  increased synthetic hypervolume from 7.050 to 16.464.
- Every source row belongs to exactly one output category; actionable DOI
  overlap with the corpus is zero and actionable DOI/title identities are
  unique.
- Repeated generation produced byte-identical TSV and Markdown artifacts with
  source, corpus, and output SHA-256 values.
- The raw 236-row source hash remained
  `64930cd0cad2a79fb0ea4e943e5a1f77d106e4269b3b64dbaff681ed0a3de93c`;
  repository API-key scanning and `git diff --check` passed.

---

# Session 53 (Codex) — DeepSeek metadata-linkage canary rejects delegation

Date: 2026-07-16
Branch: `codex/deepseek-metadata-linkage-probe`

## Task And Frozen Gate

- Selected semantic title/abstract linkage anomaly localization because
  deterministic syntax checks are cheaper without an LLM and the repository
  previously experienced cross-paper source-identity mixing.
- Froze 12 source-authentic, DOI/title-verified Zotero pairs before the first
  live call: six correct pairs and six same-domain cross-links. The spec stores
  record pointers only; exact prompt inputs are represented by SHA-256 hashes.
- DeepSeek could return only item IDs and the literal `abstract` field pointer.
  Replacement metadata, explanations, DOI/year values, and arbitrary fields
  fail schema validation.
- The fixed gate required each of three temperature-zero repeats to reach
  recall >= 0.95 and precision >= 0.75, with pairwise Jaccard >= 0.95 and all
  requests schema-valid. Flagging every record cannot pass the precision gate.

## Live Result And Routing

- The valid run used `deepseek-v4-flash`, thinking disabled, no retries, two
  batches per repeat, six requests, atomic checkpoints, and 11,934 reported
  tokens under a 15,000-token cap.
- All three repeats selected exactly M004, M010, and M012: recall 0.50,
  precision 1.00, Jaccard 1.00, and candidate-count SD 0. The stable misses were
  M002, M006, and M008, all deliberate same-domain cross-paper linkages.
- The capability gate failed. Do not delegate semantic metadata-linkage
  screening or metadata correction to this model/prompt. Deterministic
  DOI/title/hash checks remain authoritative; ambiguous semantic consistency
  routes to Codex, Claude, or human review.
- One earlier implementation attempt made one API request and then crashed
  before checkpointing because the runner treated the shared usage dictionary
  as an integer. The response was not inspected or used for tuning. Commit
  `d446714` fixed usage accounting only; that call's unknown token usage is
  explicitly excluded from valid-run metrics.

## Verification

- Metadata-probe tests: 4 passed, covering DOI/title resolution, pointer-only
  schema rejection, three-repeat stability/resume, and the all-flag precision
  failure.
- Non-loopback suite: 157 passed, 2 optional tests skipped, and the known local
  HTTP/GROBID test deselected. CLI smoke passed; the six-round optimization demo
  increased synthetic hypervolume from 7.050 to 16.464.
- Six checkpoint records independently show the frozen prompt version,
  temperature 0, thinking disabled, schema-valid ID pointers, and token counts.
- Checkpoint replay made no API mutation, reproduced the same metrics, and
  returned the expected nonzero gate-failure exit.
- Committed report and manifest contain hashes and pointers, not source
  abstracts, replacement metadata, or API credentials.
- Deterministic manifest validation recomputed all metrics, source-input hashes,
  false-negative/false-positive IDs, and the failed gate with zero issues.

---

# Session 52 (Codex) — verified Zotero sources enter canonical review flow

Date: 2026-07-15
Branch: `codex/promote-zotero-bovine-sources`

## Scope And Boundary

The four bovine primary sources previously frozen as Z001-Z004 were promoted
from evaluation-only assets into canonical candidate records R048-R051 and open
human-review tasks H034-H037. This is corpus preparation only: no evidence was
approved, no numeric value was transcribed by a model, and no wet-lab variable
was promoted.

## Implementation

- Added `scripts/ingest_verified_sources.py`. It accepts only rows already
  marked `identity_license_verified`, verifies the committed PDF SHA-256 before
  extraction, and rebuilds exact title/year/DOI metadata plus plain full text.
- Added R048-R051 with explicit transfer limits for postbiotic composition,
  serum-containing natural-product assays, oxygen confounding, and separation
  of insulin expansion versus differentiation outcomes.
- Added H034-H037 with decision-focused fields and questions. All remain
  `open`.
- Generated hash-bound review locators and extraction-readiness artifacts. All
  4 tasks have local full text and all 4 are directly operator-ready.
- Refreshed Gate 1 and the English/Chinese control documents. The manifest now
  has 51 records and the queue 37 open tasks. Gate 1 remains `FAIL` solely on
  human curation: 0/18 P1 core/core-context rows are human verified.

## Verification

- Verified-source ingestion tests: 2 passed, including hash rejection and exact
  metadata/full-text output.
- Non-loopback suite: 153 passed, 2 optional tests skipped, and the known local
  HTTP/GROBID test deselected.
- Local source ingestion: 4/4 succeeded; parsed page counts are 12, 11, 16,
  and 16, matching the frozen source registry.
- Review packet: 4/4 hash-bound locator-ready.
- Extraction readiness: 4 direct-ready, 0 fallback, 0 partial, 0 missing.
- Corpus audit: all six numerical checks, metadata completeness, record-ID
  uniqueness, and included-DOI uniqueness pass; human curation remains the
  expected failing gate.
- CLI smoke passed. The six-round optimization demo increased synthetic
  hypervolume from 7.050 to 16.464.
- Regenerating the review/readiness artifacts was byte-identical.

---

# Session 51 (Codex) — independent locator held-out closes DeepSeek task

Date: 2026-07-15
Branch: `codex/zotero-heldout-run`

## Frozen Test

- Verified the gold manifest still came from commit `111b7c3` with SHA-256
  `46ca3a166d54fac3aca5328c5e8d601db530c14cd1e09502556d1cd04ccf2b6c`.
- Made no change to `quant-block-candidate-pointer-v1`,
  `stat-context-block-v2`, the four sources, or the 13 silver locators.
- The deterministic input pool contained 19 blocks and covered all 13 silver
  locators before any API request.

## Live Result

- Ran `deepseek-v4-flash` with thinking disabled, temperature 0, no retries,
  two batches, three repeats, six requests, atomic checkpoints, and 11,904
  reported tokens. All responses passed the candidate-ID-only schema.
- The same 16 blocks were selected in all three repeats, so consistency was 1.0.
  Only 10/13 held-out locators were recovered (recall 0.7692), below the fixed
  0.95 gate. Q009, Q011, and Q013 were missed.
- Source inspection confirmed all three misses are explicit bovine MSC
  growth-medium/insulin/FBS quantitative figure captions, not ambiguous
  statistics-only blocks.
- The deployment gate suppressed all output: the committed manifest has
  `deployment_gate_pass=false`, status `failed_held_out_recall_no_output`, and
  an empty candidate list.

## Final Routing Decision

DeepSeek quantitative-block localization is closed for this prompt/model after
two held-out failures (10/12 and 10/13). Do not spend further calls tuning on
the exposed misses. The deterministic context prefilter remains useful, but
candidate review routes to Codex/Claude or a separately validated stronger
model. This decision does not affect the held human quantitative pilot.

## Verification

- Non-loopback suite: 151 passed, 2 optional tests skipped, and the known local
  HTTP/GROBID test deselected.
- Rebuilt the 19-block pool and validated the committed manifest with zero
  issues; deployment remained false and candidate count remained zero.
- Checkpoint resume reproduced the same metrics and expected nonzero CLI exit
  without another API call.
- CLI smoke passed. The six-round optimization demo increased synthetic
  hypervolume from 7.050 to 16.464.
- `git diff --check` and the repository API-key pattern scan passed.

---

# Session 50 (Codex) — source-disjoint Zotero locator holdout frozen

Date: 2026-07-15
Branch: `codex/zotero-locator-heldout`

## Source Funnel Audit

- Claude's committed screen contains 6,072 data rows: 275 yes, 741 maybe, and
  5,056 no. Thirty-nine yes rows report a local PDF; 236 yes rows do not.
- The 236-row acquire list includes 22 DOIs already present in the bovine corpus,
  so it must be corpus-deduplicated before any acquisition batch. This session
  did not rewrite Claude's result file or download those duplicates.
- Four direct bovine primary sources were selected only from yes/has-PDF rows
  whose DOI is absent from the corpus. Local PDF title, DOI, CC BY statement,
  duplicate-attachment hash agreement, and page parseability were verified.
- Claude had independently copied the same four ignored PDFs into its own
  worktree as part of a 10-paper local ingest, but did not build or run this
  locator benchmark. The shared addition here is the verification/gold artifact,
  not a second canonical corpus entry.

## Frozen Held-out Set

- Added a reproducible Zotero-to-local-PDF verification and quantitative-review
  generator. It refuses corpus DOI overlap, missing or conflicting PDFs,
  title/DOI mismatch, unsupported licenses, and missing prior screen support.
- Reused the existing `pdf-stat-block-v1` selector rather than defining a new
  answer generator. It froze 13 locators across Z001-Z004 with PDF/page/block,
  bounding-box, and normalized-text hashes and no source text or numeric value.
- Manual source inspection found all 13 blocks to be medium/additive/serum
  condition results or figure captions. The `stat-context-block-v2` prefilter
  covers 13/13 in a 19-block pool.

## Decision Boundary

The set is `FROZEN_UNEXPOSED_SILVER`. It is source-disjoint from R017, R018,
R045, and R047 and has not been used to tune the prompt. It may be used once for
the next repeated locator capability test. It is not human tier-1 gold and
cannot support evidence or wet-lab decisions.

## Verification

- Holdout/quantitative focused tests: 5 passed.
- Non-loopback suite: 151 passed, 2 optional tests skipped, and the known local
  HTTP/GROBID test deselected.
- Repeated generation produced byte-identical committed artifacts. Its temporary
  blank worksheet validated as 13/13 rows, zero completed, and zero issues, then
  was removed because this benchmark is not a human-review packet.
- All 13 frozen locators are covered by the 19-block context-aware input pool;
  no source-text or numeric-value field appears in the manifest.
- CLI smoke passed. The six-round optimization demo increased synthetic
  hypervolume from 7.050 to 16.464.
- `git diff --check` and the repository API-key pattern scan passed.
