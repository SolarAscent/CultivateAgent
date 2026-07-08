# Model comparison: deepseek-chat (v3) vs deepseek-v4-flash

Controlled effect-extraction run over the **same 15 medium papers**, same code
(`scripts/run_evidence_parallel.py`), outcome = proliferation, `temperature=0`.
Reproduce: `--model deepseek-chat` vs `--model deepseek-v4-flash --max-tokens 8000`.

Premise being tested: "if the weak model works, a better one does better." The
honest answer here is **more nuanced than a simple yes**.

## Headline numbers

| metric | deepseek-chat (V3) | deepseek-v4-flash (reasoning) |
|---|---:|---:|
| grounded effects | **42** | 28 |
| distinct components | 34 | 21 |
| direction split (help / hurt / neutral) | 26 / 8 / 8 | **11 / 9 / 8** |
| wall-clock (5 workers) | **13 s** | 72 s |
| tier (effect+variance) | 0 | 0 |

## What actually differs

- **The core biology is model-agnostic.** Both models independently extract the
  canonical proliferation factors — FGF2, FGF1, HGF, IGF-family, PDGF-BB, TGF-β,
  Insulin, BSA, ITS were in *both* outputs. A weak model already recovers the
  signal that matters.
- **v4 buys precision, not recall.** V3 extracts *more but noisier*: verbose
  duplicates ("DMEM with FBS" / "DMEM without FBS"), over-specific strings
  ("microalgal nutrient extracts added to waste medium"), and **non-medium
  items** ("curvature feature", "hybrid geometry" — scaffold geometry, out of
  scope). V4 extracts *fewer but cleaner* — crisp reagents (CHIR99021, LY2090314,
  repsox, GA-017) and far less junk.
- **v4 reads more critically.** V3's directions skew 26-help / 8-hurt
  (everything-is-beneficial optimism); v4 is balanced 11-help / 9-hurt / 8-neutral,
  i.e. it calls "no effect" and "detrimental" more often — the more scientifically
  honest posture.
- **Neither gives effect sizes.** Both are 100% direction-only (tier 3). This is
  driven by the *prompt* (which asks for direction first), not model quality — so
  activating continuous random-effects meta-analysis needs a prompt that extracts
  control-normalized fold-changes **and** verification of the number against its
  quote (a weak model will misread numbers even when the quote is real).

## Takeaways for the pipeline

1. For a **knowledge base**, precision > recall: v4's cleaner, more critical
   output is more trustworthy, and the grounding + audit layers filter the rest.
   Use a reasoning model for the *final* corpus pass; use the cheap fast model for
   breadth/first-pass triage.
2. "Better model → better results" is true for **quality/precision**, false for
   **speed and raw count** — report both, don't assume.
3. The over-extraction v3 produces (geometry, verbose duplicates) is exactly what
   Codex's `evidence-audit` `not_medium_only` / dedup filters are for; a stronger
   model reduces the load on those filters but does not remove the need for them.

Cost note: `deepseek-chat`/`deepseek-reasoner` are deprecated compatibility names
(sunset 2026-07-24); new runs should use `deepseek-v4-flash` / `deepseek-v4-pro`.
