# Model comparison: deepseek-chat compatibility alias vs deepseek-v4-flash

Controlled effect-extraction run over the **same 15 medium papers**, same code
(`scripts/run_evidence_parallel.py`), outcome = proliferation, `temperature=0`.
Reproduce: `--model deepseek-chat` vs `--model deepseek-v4-flash --max-tokens 8000`.

Premise being tested: "if the cheaper/faster compatibility route works, an
explicit v4-flash run with a larger output budget does better." The honest
answer here is **more nuanced than a simple yes**.

## Headline numbers

| metric | deepseek-chat compatibility alias | deepseek-v4-flash explicit run |
|---|---:|---:|
| grounded effects | **42** | 28 |
| distinct components | 34 | 21 |
| direction split (help / hurt / neutral) | 26 / 8 / 8 | **11 / 9 / 8** |
| wall-clock (5 workers) | **13 s** | 72 s |
| tier (effect+variance) | 0 | 0 |

## What actually differs

- **The core biology is model-agnostic.** Both models independently extract the
  canonical proliferation factors — FGF2, FGF1, HGF, IGF-family, PDGF-BB, TGF-β,
  Insulin, BSA, ITS were in *both* outputs. The faster compatibility route
  already recovers the signal that matters.
- **The explicit v4-flash run buys precision, not recall.** The compatibility
  route extracts *more but noisier*: verbose duplicates ("DMEM with FBS" / "DMEM
  without FBS"), over-specific strings ("microalgal nutrient extracts added to
  waste medium"), and **non-medium items** ("curvature feature", "hybrid
  geometry" — scaffold geometry, out of scope). The explicit v4-flash run
  extracts *fewer but cleaner* — crisp reagents (CHIR99021, LY2090314, repsox,
  GA-017) and far less junk.
- **The explicit v4-flash run reads more critically.** The compatibility route's
  directions skew 26-help / 8-hurt (everything-is-beneficial optimism); the
  explicit v4-flash run is balanced 11-help / 9-hurt / 8-neutral, i.e. it calls
  "no effect" and "detrimental" more often — the more scientifically honest
  posture.
- **Neither gives effect sizes.** Both are 100% direction-only (tier 3). This is
  driven by the *prompt* (which asks for direction first), not model quality — so
  activating continuous random-effects meta-analysis needs a prompt that extracts
  control-normalized fold-changes **and** verification of the number against its
  quote.
- **Numeric verification now exists, but computation is still future work.**
  After this comparison, `evidence.extract_effects` was hardened so returned
  `effect` and `variance` numbers are kept only when the verified quote contains
  the supporting numeric token. A later update added deterministic `ln(ratio)`
  inference for explicit quoted fold/percent changes. This prevents unquoted
  numbers from entering tier 1/2 evidence, but it still does not compute
  variances from raw control/treatment values.

## Takeaways for the pipeline

1. For a **knowledge base**, precision > recall: the explicit v4-flash run's
   cleaner, more critical output is more trustworthy, and the grounding + audit
   layers filter the rest. Use the explicit current model name for the *final*
   corpus pass; use the cheap fast route for breadth/first-pass triage.
2. "Better model → better results" is true for **quality/precision**, false for
   **speed and raw count** — report both, don't assume.
3. The over-extraction produced by the compatibility route (geometry, verbose
   duplicates) is exactly what Codex's `evidence-audit` `not_medium_only` /
   dedup filters are for; a cleaner model route reduces the load on those
   filters but does not remove the need for them.

Cost note: `deepseek-chat`/`deepseek-reasoner` are deprecated compatibility names
(sunset 2026-07-24). DeepSeek currently documents them as compatibility names
for `deepseek-v4-flash` non-thinking/thinking modes, so this report should not
be read as a clean V3-vs-V4 model-family comparison. New runs should use
`deepseek-v4-flash` / `deepseek-v4-pro`. This naming note was re-checked against
DeepSeek's official
[quick start](https://api-docs.deepseek.com/) and
[models/pricing](https://api-docs.deepseek.com/quick_start/pricing) pages before
the report was merged into `main`.
