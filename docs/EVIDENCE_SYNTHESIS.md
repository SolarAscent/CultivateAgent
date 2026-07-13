# Evidence synthesis — turning heterogeneous literature into honest priors

The project record's critique names **outcome comparability** as the deepest
problem: a "2× proliferation" and a "39 h doubling time" are not commensurable,
so cross-paper numbers cannot be pooled naively or used as training labels. This
layer answers that directly, and is CultivateAgent's core scientific contribution
beyond "LLM extracts, BO suggests".

## What it does

For each `(component, outcome, context)` it produces a **posterior belief that the
component is beneficial**, with an explicit uncertainty and a heterogeneity flag —
and it says "I don't know, test it" when the evidence conflicts, instead of
manufacturing a confident point estimate.

```
quoted directional/effect claims (per paper)
        │  evidence.effect_operator (LLM, grounded, verified quotes)
        ▼
   EvidenceItem[]  (component, outcome, effect±var | direction, context, quote, paper_id)
        │  group by (component, outcome, context)
        ▼
   meta_analyze()  ── DerSimonian–Laird random-effects  (continuous, ≥2 studies)
                   ── single-study normal                (1 quantitative study)
                   └─ Beta–Binomial direction vote       (direction-only evidence)
        ▼
   EvidenceSummary  (p_beneficial, CI, I², context_dependent, paper_ids, quotes)
        │
        ▼  feeds the optimizer as PRIORS over promising regions (never as labels)
   optimize/  (prior mean + per-component trust width; high-I² → "test directly")
```

## Method (closed-form, no MCMC — always runs)

* **Random-effects meta-analysis (DerSimonian & Laird 1986).** Pool standardized
  effects `y_i` with within-study variances `v_i`. Between-study variance
  `τ² = max(0, (Q−(k−1))/c)`; random-effects weights `w*_i = 1/(v_i+τ²)`; pooled
  `ȳ = Σw*_i y_i / Σw*_i`, `Var = 1/Σw*_i`.
* **Heterogeneity (Higgins & Thompson 2002).** `I² = max(0, (Q−(k−1))/Q)`. When
  `I² ≥ 0.5` the component is flagged **context-dependent — test directly** rather
  than trusting the pooled estimate.
* **Direction-only fallback.** When papers give only a direction (helps/hurts),
  a Beta–Binomial posterior `Beta(1+helps, 1+hurts)` gives `P(beneficial)` with a
  credible interval.
* `p_beneficial = Φ(ȳ / √Var)` (continuous) or the Beta posterior mean.

## Why this is honest (the constraint the whole project keeps)

* **No co-occurrence signal.** Evidence items are only created from *quoted
  directional claims* the model can point to in the text (verified against the
  source; ungrounded claims are dropped). A component appearing in a paper is
  **not** evidence that it helps.
* **Priors, not labels.** Summaries bias *where the optimizer looks*; the actual
  objective values still come from the user's own experiments via `tell()`.
* **Conflict is surfaced, not hidden.** High I² → wide CI, `p_beneficial ≈ 0.5`,
  and an explicit "test directly" note. (Demonstrated: 4 opposite strong effects →
  I²≈97%, p≈0.57, `context_dependent=True`.)
* **Traceability.** Every summary keeps its contributing `paper_ids` and verbatim
  `quotes`.

## Try it (offline)

```python
from cultivate_agent.evidence import EvidenceItem, meta_analyze
items = [EvidenceItem("FGF2", "proliferation", f"p{i}", effect=e, variance=0.05)
         for i, e in enumerate([0.8, 0.9, 0.75])]
s = meta_analyze(items)
print(s.p_beneficial, s.ci_low, s.ci_high, s.i_squared, s.context_dependent)
# ~1.0, CI excludes 0, I²=0, not context-dependent
```

Real evidence comes from `evidence.extract_effects(client, ref, text, "proliferation")`,
which is offline-testable with the mock client and drops any claim whose quote is
not found verbatim in the source.

Number handling is intentionally conservative. If an LLM returns `effect` or
`variance` but the corresponding numeric token is not present in the verified
quote, CultivateAgent clears that numeric field and keeps the item at the
appropriate lower tier. For explicit proportional phrases such as "2-fold
increase" or "50% reduction", and for very explicit treatment/control means, the
extractor can deterministically infer a log response ratio `ln(ratio)` from the
quote. This creates tier-2 evidence unless the same verified quote also reports
SD/SE/SEM and sample size for both treatment and control groups; only then is a
large-sample ROM variance computed. Dose or timepoint numbers are ignored as
response values, and any quantitative use still requires human numeric review.
Composition percentages are also excluded: a percentage followed by a reagent
or medium term is treated as concentration, and a percentage effect requires
explicit increase/decrease/change language. For `N +/- M-fold`, N is the point
estimate and M is the error term, not a second effect magnitude.
Structured JATS tables use a stricter boundary. The LLM-facing
`TableEffectPointers` schema contains semantic roles and cell IDs but no numeric
fields. `numeric_effect_from_table_pointers()` verifies the table ID and source
hash, reads each pointed-to source cell deterministically, converts SEM to SD
only after resolving sample size, and calls the shared ROM implementation.
Missing cells, incomplete statistics, stale hashes, ambiguous numeric prose, or
model-returned extra fields fail closed. This removes numeric transcription
hallucination but does not make treatment/control role labeling trustworthy;
that semantic step remains subject to repeated-run gold evaluation and human
numeric review.
The current S4 worksheet separates this review into `numeric_effect_status`,
`numeric_effect_metric`, `numeric_effect_value`, optional variance, and notes,
so a directionally supported row is not automatically a thesis-ready
quantitative effect.

Operator-mode extraction also keeps component-dose relations separate from
effect sizes. Its optional `dose_records` attach one reported component to one
dose/range, unit, comparison group, endpoint, and same-passage evidence quote.
The local verifier requires the quote to contain both the component string and
numeric dose/range (plus the separate unit when supplied). These records can
replace the A-M dose proxy for Gate 2 coverage, but they remain candidate
extractions until S4 human numeric review and are never treated as outcome
effects or BO labels.

## Relation to prior art

The closest prior work — **Cai et al. 2023**, "Multi-objective Bayesian algorithm
automatically discovers low-cost high-growth serum-free media" (*Eng. Life Sci.*,
DOI 10.1002/elsc.202300005) — runs BO directly in the lab from a cold start.
CultivateAgent differs by *warm-starting from the literature*: this evidence layer
converts heterogeneous published results into calibrated priors (with honesty about
heterogeneity), which the optimizer then refines with far fewer wet-lab runs.

## References

- R. DerSimonian, N. Laird. *Meta-analysis in clinical trials.* Control. Clin.
  Trials 7(3):177–188, 1986. DOI 10.1016/0197-2456(86)90046-2.
- J. Higgins, S. Thompson. *Quantifying heterogeneity in a meta-analysis.* Stat.
  Med. 21(11):1539–1558, 2002. DOI 10.1002/sim.1186.
- C. Röver et al. *Weakly informative priors for the heterogeneity parameter in
  Bayesian random-effects meta-analysis.* 2020. arXiv:2007.08352.
- L. V. Hedges, J. Gurevitch, P. S. Curtis. *The meta-analysis of response
  ratios in experimental ecology.* Ecology 80(4):1150-1156, 1999.
- Prior art to differentiate: Cai et al., *Eng. Life Sci.* 2023, DOI 10.1002/elsc.202300005.
