# Live run on real papers with DeepSeek (deepseek-chat)

First end-to-end run of the pipeline against **real PDFs with a real (deliberately
low-quality) LLM**. The premise: if the design survives a weak, text-only,
hallucination-prone model, a stronger model can only do better. Everything below
is measured, not asserted; DeepSeek's failures are reported alongside its wins.

## Setup

- Model: `deepseek-chat` (DeepSeek-V3), OpenAI-compatible endpoint, `temperature=0`.
  Wired with zero code change — just `.env` (`OPENAI_BASE_URL=https://api.deepseek.com`).
- 2026-07-09 provider-config update: DeepSeek's current API docs list
  `deepseek-v4-flash` and `deepseek-v4-pro` as the current model names and mark
  `deepseek-chat`/`deepseek-reasoner` as compatibility names deprecated after
  2026-07-24 15:59 UTC. This report remains a historical live run; new runs
  should use a current v4 model name.
- Papers (ingested via PyMuPDF; metadata from Crossref):
  - **research** — Lee et al., *Nat. Commun.* 2024, "Cultured meat with enriched
    organoleptic properties by regulating cell differentiation" (13 pp, 76 K chars).
  - **review** — Gu et al., *Compr. Rev. Food Sci.* 2025, "Scaling Cultured Meat:
    Challenges and Solutions for Affordable Mass Production" (40 pp, 210 K chars).

## Headline: the pipeline works live — and operator decomposition is what makes it work

| stage | result |
|---|---|
| triage | both papers → **A** (correct), with sensible rationales |
| extract `--mode blocks` (old monolithic) | **FAILS**: pass-2 response truncated at max_tokens → invalid JSON → **all of blocks D–L lost** |
| extract `--mode operators` (new) | **all 5 operators complete**; research 21 fields, review 28 fields |
| evidence synthesis | **16 grounded proliferation effects** (2 research + 14 review) |

The monolithic-prompt failure is the exact failure Codex saw with GPT-5.4 (near-empty
output). Here we can see *why*: DeepSeek's block-mode pass-2 came back as
`'{ "blocks": { "D": { ... "prima'` — cut off mid-JSON. Small, focused operator prompts
finish; one giant prompt does not. **Phase B is validated on real data.**

## Per-operator coverage + grounding (operators mode)

Grounding = fraction of the operator's evidence quotes found verbatim in the source.

| operator | research: cov / ground | review: cov / ground |
|---|---|---|
| context   | 1.00 / 0.57 | 0.71 / 1.00 |
| medium    | 0.00 / — (¹) | 1.00 / 0.25 |
| dose      | 1.00 / 0.80 | 1.00 / 0.60 |
| endpoints | 0.75 / 0.00 | 1.00 / 1.00 |
| findings  | 0.86 / 0.33 | 0.86 / 0.33 |

(¹) The research paper is a scaffold/differentiation study; it carries little
medium-specific content, so an *empty* medium operator is largely correct here.

## What DeepSeek got right — and its characteristic failure mode

- **Values are often correct even when the quote is not.** Example (context operator,
  research paper): it correctly returned species=bovine, cell types = myoblasts +
  adMSCs, `species_detail = "Hanwoo cattle"`, main_track = scaffold — all true — but
  attached **paraphrased quotes that did not verify verbatim**, so the grounding check
  flagged them. This is the core lesson: **trust the grounding rate, not the value.**
  The evidence-verification layer is not optional decoration; with a weak model it is
  the only thing standing between the KB and confident nonsense.
- **Real, specific, verified evidence is recoverable.** From the review, the effect
  operator produced grounded, quote-checked proliferation effects including:
  Beefy-9 (+, "sustained cell growth over seven passages"), SFB (+, "increased nuclei
  count by 76% over DMEM/F-12"), Beefy-R rapeseed-protein isolate (+, "14-fold cost
  reduction"), *Auxenochlorella pyrenoidosa* protein extract (+, "1 mg/mL APE"),
  *Grifola frondosa* extract (+, "12.5 µg/mL … $0.51/g"), copper ions 5 µM (+), and
  FGF2 immobilized in affibody hydrogels (+). These are exactly the medium→outcome
  relations the system exists to capture.
- **Over-extraction / loose association (needs human review).** DeepSeek also tagged
  cost/byproduct-management items — zeolite adsorption, Mg-Al layered double oxides,
  lactate/aldehyde dehydrogenase flow reactors — as proliferation-positive. The quotes
  are real, but the *causal attribution to proliferation is a stretch*. The grounding
  check verifies the quote, not the reasoning; a human gate is still required. This is
  the monitoring the model's owner explicitly asked for.

## Two bugs found by scrutinizing the live output (both fixed this session)

1. **Grounding verified against the wrong text.** `OperatorExtractor` checked quotes
   against `paper.all_text()` (text round-tripped through section parsing), which
   dropped/altered spans and falsely flagged real quotes as ungrounded (review `dose`
   reported 0.0 when 4/5 quotes were actually present). Fixed to verify against the
   original source text (commit `748bf5d`).
2. **Effect operator truncated to the intro.** `extract_effects` sent only
   `text[:16000]` — the first 16 K of a 210 K review — and returned **0 effects**. Now
   it routes to effect-bearing sections (results/methods/media/discussion):
   **0 → 16 grounded effects** (commit `f986e2a`).

## Honest limitations

- **Two papers → every component has k=1**, so evidence synthesis falls back to the
  direction-only Beta-Binomial (p_beneficial = 0.67) for all of them. The
  random-effects meta-analysis and heterogeneity (I²) machinery is correct but only
  *bites* with many papers per component. The system does **not** fake confidence from a
  single study — which is the honest behavior.
- **Ontology canonicalization gaps.** Real components (Beefy-9, SFB, SFGM, *Grifola
  frondosa* extract, rapeseed/microalgae isolates) are not in the seed ontology, so
  they pass through un-normalized and cannot yet be pooled across papers. Growing the
  ontology from real extractions is the obvious next step.
- **Non-determinism.** Even at `temperature=0`, DeepSeek varies slightly run-to-run, so
  grounding rates move by a few points between runs.

2026-07-08 follow-up: the ontology gap is now partially closed for SFB, SFGM,
Beefy-R, rapeseed-protein isolate, Grifola frondosa extract, Auxenochlorella
pyrenoidosa protein extract, and copper ions. These entries only support
normalization and evidence pooling; each still requires human review before
being promoted into a non-exploratory wet-lab variable.

## Conclusion

The pipeline ran end-to-end on real papers with a weak model and produced *verifiable*
structured knowledge, precisely because the design leans on **decomposition** (small
operators finish where monolithic prompts truncate) and **grounding verification**
(quote-checking separates DeepSeek's correct values from its paraphrases and its loose
associations). The recommended production posture: **only trust high-grounding fields,
keep the human gate for causal claims, and expect a stronger model to raise coverage
and grounding across the board.**
