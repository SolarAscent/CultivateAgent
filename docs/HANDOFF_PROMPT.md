# Handoff prompt — continue CultivateAgent (paste this to ChatGPT / Codex)

> Copy everything below the line into your next assistant. It is written to be
> self-contained. Give the assistant access to the repo (clone it or upload the
> folder) before starting.

---

## ROLE

You are a senior research engineer + ML scientist taking over an in-progress
research codebase, **CultivateAgent**, for a ~5-hour session. The previous
engineer (Claude) built the foundation and is handing off. Your job: **advance
the project without breaking it, verify what exists, extend it carefully, and
push back critically — grounded in real literature and facts.** You are not a
yes-machine: if a design decision is wrong, say so with evidence.

## WHAT THE PROJECT IS (read this fully before touching anything)

CultivateAgent is a **goal-conditioned, medium-centered literature-mining agent
+ optimizer for cultivated-meat (cell-cultured meat) culture-medium design**. It
turns a corpus of papers into a structured, evidence-grounded knowledge base and
then proposes the next wet-lab experiments to run.

Pipeline (a sequential pipeline, **not** a "multi-agent" system — do not
re-brand it as one):

```
ingest → triage → extract → normalize → knowledge base → retrieve → design → optimize
```

Reference architecture: **ReactionSeek** (Li et al., *Nature Communications*
2026; github.com/DeepSynthesis/ReactionSeek) — an LLM + deterministic-domain-tool
hybrid with heavy prompt engineering and no fine-tuning. The full PDF is in the
owner's `~/Downloads`. Our optimizer additionally draws on multi-objective
Bayesian optimization and LLM-as-optimizer work (see `docs/OPTIMIZATION.md`).

**Current state:** 43 Python modules, 21 offline tests passing, a working CLI
(`cultivate ...`), and three docs (`README.md`, `docs/ARCHITECTURE.md`,
`docs/OPTIMIZATION.md`). Everything runs offline with a mock LLM (no API key).

## DESIGN PHILOSOPHY — these are LOCKED. Do not silently change them.

1. **Multi-objective, single-factor (medium-centered).** The agent may *read*
   any context (cell type, species, scaffold) but may only *act on medium
   variables*. Objectives are a FIXED set {proliferation, cost,
   differentiation_retention, tissue_readiness} with user-chosen *weights*, not
   open-ended goals. Enforced in `design/objectives.py` + a whitelist check.
2. **Evidence grounding is mandatory.** Every extracted value carries a verbatim
   quote that is *verified* against source text (grounding rate is measured).
   This is the anti-hallucination guardrail. Do not weaken it.
3. **Honesty about comparability.** Cross-paper outcome numbers are NOT treated
   as comparable training labels (a "2× proliferation" and a "39 h doubling
   time" are not commensurable). The KB seeds the *search space and candidate
   regions*; objective *values* come from the user's own experiments via the
   optimizer's `tell()`. Keep this honesty; do not fabricate comparability.
4. **Provider-agnostic LLM layer** (`llm/`): OpenAI/Anthropic/Gemini/mock behind
   one interface; switching models is a config flag (`llm.provider`, `llm.model`).
5. **Pre-registerable optimization.** `optimize` proposes a whole batch *before*
   any experiment runs, cost is always a Pareto objective (never a standalone
   "win"), and LLM-seeded candidates keep their citations.

If you believe one of these is wrong, do NOT just change it — write a short,
citation-backed argument in `docs/REVIEW_BY_NEXT_ENGINEER.md` and flag it for the
owner. (See "CRITICAL-THINKING MANDATE" below.)

## GROUND RULES (guardrails)

- **Orient before editing.** First 20 minutes: read `README.md`,
  `docs/ARCHITECTURE.md`, `docs/OPTIMIZATION.md`; set up the venv; run the tests.
- **Never break the 21 tests.** Run `pytest -q` after every change. If you add
  behavior, add tests. Target: tests count only goes up.
- **Match the existing conventions** (module layout, docstring style, typing,
  graceful degradation when optional deps are missing). Read a neighbor file
  before writing a new one. Do NOT reformat or restructure files you aren't
  functionally changing.
- **Small, reviewable commits** with clear messages. One concern per commit.
  Work on a branch (`git checkout -b <feature>`), not directly on `main`.
- **Do not add heavy dependencies to the core.** Keep optional deps optional
  (lazy imports, feature-flagged), exactly as `kb/export.py` and
  `optimize/surrogate.py` do.
- **No hallucinated citations, ever** (see literature rules below). A fabricated
  DOI/author is worse than "I couldn't verify this."
- If you get stuck or a task is ambiguous, leave a `# TODO(handoff):` note and
  move on; don't guess destructively.

## SETUP + VERIFY (run this first)

```bash
cd CultivateAgent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
pytest -q                                   # expect: 21 passed
python -m cultivate_agent.cli smoke         # offline end-to-end, no API key
python -m cultivate_agent.cli optimize --demo --rounds 6   # closed loop should converge (HV rises)
```

If any of these fail on arrival, FIX THAT FIRST and report what was wrong.

## ENVIRONMENT NOTES / KNOWN ISSUES

- **Claude's web search/fetch tools were broken** (a misconfigured summarizer
  backend). You (ChatGPT) have your own browsing — **use it** for literature.
  Fallback that always works: query the arXiv API directly, e.g.
  `http://export.arxiv.org/api/query?search_query=all:"multi-objective Bayesian optimization"&max_results=5`
  and parse the Atom XML. Cross-check every paper via a second source (Semantic
  Scholar / Crossref / the publisher page) before citing it.
- The ReactionSeek Nature paper is paywalled online; the owner has the PDF locally.
- Real extraction/design/optimize runs need an API key in `.env`
  (`cp .env.example .env`). Without a key, use `--provider mock` or the `smoke`
  and `optimize --demo` paths.

## YOUR TASKS THIS SESSION (prioritized; do them in order, stop when time runs out)

Each task lists an **acceptance criterion**. Don't mark a task done without it.

**T1 — Verify + harden the extraction quality (highest value).**
Build a tiny **gold-standard eval set**: hand-annotate the A–M schema for 3–5
real cultivated-meat medium papers (the owner can point you to PDFs; or use the
4 in `data/library.example.bib` + their abstracts). Run
`cultivate_agent.evaluate.evaluate_corpus` (predicted vs gold) and report
per-field P/R/F1 + grounding rate. *Acceptance:* a reproducible eval script under
`scripts/` + a short results table in `docs/EVAL_RESULTS.md`, with an honest
error analysis (which fields are weak and why).

**T2 — Model cross-validation (the owner explicitly wants this).**
Run the SAME extraction on the SAME papers with ≥2 providers (e.g. GPT-5.x vs
Claude vs Gemini — flags: `--provider`/`--model`). Measure inter-model agreement
per field (treat one as reference, or compute pairwise agreement / Cohen's κ on
categorical fields). *Acceptance:* an agreement report; identify fields where
models disagree most (those are the least reliable and most important to fix).

**T3 — Wire the production BoTorch/qNEHVI backend end-to-end.**
`optimize/mobo.py` already has a `backend="botorch"` path (qNEHVI). Install
`torch botorch gpytorch`, make `cultivate optimize --backend botorch --demo`
run, and add a test that skips cleanly if botorch is absent
(`pytest.importorskip`). Compare qNEHVI vs the default q-ParEGO on the synthetic
benchmark (normalized hypervolume, multiple seeds). *Acceptance:* a passing
(skippable) test + a comparison table; qNEHVI should be ≥ q-ParEGO.

**T4 — Add an embedding retriever (match ReactionSeek's SynChat).**
`retrieve/` currently has BM25 only; config already has a `backend: embedding`
hook. Add a `sentence-transformers` (all-MiniLM-L6-v2) or OpenAI-embeddings
backend with cosine search, behind the same `Retriever` interface, optional-dep
and falling back to BM25. *Acceptance:* a test showing the embedding retriever
ranks a semantically-related-but-lexically-different doc above BM25 would.

**T5 (stretch) — Verifier/critique loop for the recommender.**
The record's critique noted the ONE defensible reason to go multi-agent is a
proposer→verifier loop. Add an optional verifier pass in `design/recommender.py`:
a second LLM call that checks each candidate's citations actually support the
claim and flags unsupported changes, iterating once. *Acceptance:* a test with a
mock verifier that downgrades an unsupported candidate.

Do NOT start new tasks beyond these without leaving the codebase green and
committed.

## LITERATURE-RETRIEVAL REQUIREMENTS (strict)

- Ground every technical claim/citation in a source you actually retrieved.
  Prefer: arXiv, Nature/Science/Cell family, npj, Communications Biology, GFI
  technical reports, JACS/Angew for method analogies.
- **Verify each citation** (title + authors + venue + year) against ≥2 sources.
  If you cannot verify, write "unverified" — never invent a DOI or author list.
- Domain anchors already used (verify, then build on): O'Neill et al. 2022 npj
  Sci Food (spent-media, no universal medium); Stout et al. 2022 Commun Biol
  (Beefy-9/B8 + recombinant albumin); Messmer et al. 2022 Nat Food (serum-free
  differentiation); Kolkmann et al. 2023 Sci Rep (grain-free defined medium);
  Todhunter et al. 2024 arXiv:2407.09982 (AI/ML for cultured meat).
- Optimization anchors (verify, then critique): Daulton et al. NeurIPS 2020
  qEHVI (arXiv:2006.05078); OPRO Yang et al. 2023 (arXiv:2309.03409); LLMs-as-
  evolutionary-optimizers Liu et al. 2023 (arXiv:2310.19046); LLAMBO ICLR 2024.

## CRITICAL-THINKING MANDATE (the owner wants this, not flattery)

Write your analysis to `docs/REVIEW_BY_NEXT_ENGINEER.md`. Be specific and cite.

1. **Critique the current design** on evidence. Candidate weak points to pressure-
   test (agree or rebut with citations): (a) is the A–M schema too large to
   annotate reliably? (b) is single-factor medium-only scope too narrow to be
   novel, or correctly focused? (c) is the numpy-GP + q-ParEGO adequate, or a toy?
2. **Attack the deepest problem: outcome comparability.** The literature reports
   media→outcome relationships in non-comparable forms. Propose a *principled*
   handling beyond "keep originals" — e.g. a **hierarchical/random-effects
   Bayesian meta-analysis** that pools effects across papers while modeling
   per-paper/per-context heterogeneity, or a standardized-effect-size normalization
   with explicit context covariates. This is likely the highest-value innovation;
   sketch it concretely and, if time allows, prototype it.
3. **Propose algorithms DIFFERENT from the reference papers** (verify each is real
   and appropriate; don't cargo-cult). Non-exhaustive starting points to evaluate:
   - **TuRBO** (trust-region BO, Eriksson et al. NeurIPS 2019) for higher-dim
     medium spaces where global GPs struggle.
   - **SCBO / constrained BO** for hard food-grade + cost-budget constraints.
   - **Multi-fidelity BO** (cheap proxy assays, e.g. metabolic/viability at 72 h,
     as low-fidelity for expensive differentiation/3D endpoints).
   - **Information-theoretic acquisition** (MES/JES/PES) as an alternative to EHVI.
   - **Deep-kernel or Bayesian-NN surrogates** for mixed/combinatorial spaces.
   - **Batch diversity via DPPs** to avoid redundant experiments in a batch.
   - **Meta/transfer BO across cell types/species** (multi-task GP; ties to the
     comparability problem).
   For each you recommend: say *why it fits cultivated-meat medium specifically*,
   the cost/complexity, and how it would slot into `optimize/` without breaking
   the interfaces. Pick at most ONE to prototype if time remains.
4. **Cross-validate the science, not just the code.** Sanity-check the ontology
   (`config/ontology/*.yaml`) and default concentration ranges
   (`optimize/space.py` `CLASS_RANGES`) against real serum-free formulations
   (e.g. B8/Beefy-9 component levels). Flag anything unphysical with a citation.

## REPORTING / HANDOFF FORMAT (so the owner + next Claude can resume)

At the end of your session, ensure:
- All work is committed on a branch and pushed; open a PR with a summary, OR
  leave clear commit messages + a `docs/SESSION_LOG.md` entry.
- `docs/SESSION_LOG.md` (create if absent) lists: what you did, test count
  before/after, decisions made, what you deliberately did NOT do, and the exact
  next 3 steps you'd take.
- `docs/REVIEW_BY_NEXT_ENGINEER.md` holds your critique + algorithm proposals.
- `docs/EVAL_RESULTS.md` holds T1/T2 numbers.
- Tests are green (`pytest -q`) and `cultivate smoke` + `optimize --demo` still work.

Prime directive: **leave the project better, greener, and better-documented than
you found it — and tell the truth about what works and what doesn't.**
```
