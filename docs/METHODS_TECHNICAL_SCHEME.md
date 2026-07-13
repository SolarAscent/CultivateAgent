# Methods — CultivateAgent technical scheme

Manuscript-ready Methods draft for the CultivateAgent system. Prose is grounded in
the implemented pipeline; results placeholders are marked `[…]` for author numbers.

---

## 2. Methods

### 2.1 Overview

We address serum-free culture-medium optimization for cultivated meat, where the
design variables are medium components (basal medium, growth factors,
hydrolysates, small molecules) and their doses, and the objectives are
cell-expansion performance, cost, and retention of myogenic identity. The central
difficulty is that the informative prior knowledge — thousands of heterogeneous
primary papers — is written for human readers, is not directly comparable across
studies, and cannot be used as optimization labels without introducing confounds
from differing cell sources, basal media, and assays.

CultivateAgent is a goal-conditioned agent that separates two epistemic roles
that are usually conflated in "LLM-for-science" pipelines. Literature is mined
only to define **where to look** — the search region, component priors, dose
ranges, and constraints — whereas the **objective values that drive optimization
come exclusively from the project's own wet-lab measurements**, entered through a
closed-loop interface. This firewall (Section 2.2) is enforced structurally: no
cross-paper outcome number is ever passed to the optimizer as a training target.

The pipeline is a directed sequence,
`ingest → triage → extract → normalize → synthesize → prior → optimize`,
wrapped by staged human-in-the-loop gates (Section 2.9). Sections 2.3–2.5 recover
structured, quote-verified evidence from full text; Section 2.6 pools it with
random-effects meta-analysis; Sections 2.7–2.8 convert the pooled beliefs into
priors for a multi-objective Bayesian optimizer that closes the loop with
wet-lab experiments.

### 2.2 Problem formulation and the evidence–label firewall

A medium formulation is encoded as a point `x` in a mixed continuous/binary
design space `X` (component present/absent and its dose). We seek the Pareto
front over objectives `f(x) = (f_expansion, −f_cost, f_identity)` under
feasibility constraints (animal-component-free preference, supply, and dose
bounds). Optimization is a closed loop: the agent proposes a batch of
formulations, the wet lab returns measured objective values `y`, and the
surrogate is updated by `tell(x, y)`.

Literature evidence enters this loop only as a prior `π(x)` over the design space
(Section 2.7) and as the bounds of `X`; it never enters as `y`. This is the key
design decision. Treating reported effects as labels would pool measurements
taken under incomparable protocols into a single regression target, which is the
dominant failure mode we designed against. Instead, each literature-derived
belief influences *where the acquisition function searches* and decays as real
observations accumulate (Section 2.7).

### 2.3 Operator-decomposition extraction

**Motivation.** A single prompt asked to return the full A–M paper schema fails
on real full-text inputs: with production LLMs the second-pass response is
truncated at the output-token limit and the trailing schema blocks are lost,
yielding empty or invalid structured output. The failure is systematic, not
model-specific, because the requested output length scales with the schema.

**Design.** We decompose extraction into five operators with **disjoint** field
ownership — `context`, `medium`, `dose`, `endpoints`, and `findings`. Each
operator is a small, focused prompt that receives section-routed text and returns
only its own fields plus per-field evidence. Given a paper, the operators run
independently; their outputs are merged by field key into one structured record,
and a per-operator status (`ok`/`empty`/`parse_error`) is recorded so a single
failing operator degrades gracefully instead of failing the paper.

**Technical advantage.** Because each operator's output is bounded and small, it
completes within the token budget where the monolithic prompt truncates; in our
runs operator decomposition recovered the full schema on papers where block-mode
extraction returned invalid JSON. Disjoint field ownership also guarantees that no
field is written by two operators, removing merge ambiguity.

### 2.4 Evidence grounding and ontology normalization

**Motivation.** A weak or hallucination-prone extractor frequently returns a
correct value attached to a paraphrased, non-verbatim quote; if such claims enter
the knowledge base they become indistinguishable from fabrications.

**Design.** Every extracted value carries an evidence quote, which is verified by
exact-substring match against the **original** source text (not text
round-tripped through section parsing, which silently alters spans). A claim whose
quote does not verify is flagged `UNVERIFIED`, and for effect evidence it is
dropped entirely rather than pooled. Component strings are then canonicalized
against a curated ontology of basal media, growth factors, hydrolysates, and small
molecules; unmatched strings fall back to a qualifier-stripping normalizer that
removes parenthetical dose/formulation qualifiers (e.g.
"FGF2 (immobilized in hydrogel)" → "FGF2") so the same component pools across
papers.

**Technical advantage.** Grounding converts extractor trust from a global
assumption into a per-field, auditable property: downstream synthesis consumes
only quote-verified evidence, and the grounding rate becomes a measurable quality
signal. Canonicalization is what makes cross-paper pooling (Section 2.6) possible
at all.

### 2.5 Quantitative effect-size recovery with numeric provenance

**Motivation.** Direction-only evidence ("component improves proliferation")
supports voting but not weighted meta-analysis. We therefore recover effect
magnitudes where the paper states them — without letting a language model's
arithmetic fabricate precision.

**Design.** For each grounded effect we assign a direction and, where the verified
quote contains explicit proportional language, a standardized effect. Fold and
percentage changes are mapped to a log response ratio
`θ = ln(x̄_t / x̄_c)`; when the quote reports treatment and control means with
dispersion and sample sizes, we additionally compute the ratio-of-means variance
(Hedges–Gurevitch–Curtis estimator)

```
v(θ) = s_t² / (n_t · x̄_t²) + s_c² / (n_c · x̄_c²).
```

Two provenance safeguards prevent fabricated magnitudes. First, any numeric value
the model returns is retained only if that number appears as a token in the
verified quote; otherwise the effect stays direction-only. Second, the parser
distinguishes an effect number from an incidental one: a percentage immediately
followed by a reagent term (e.g. "30% FBS") is treated as a composition
concentration and rejected, an explicit change word must sit next to the number
for a percentage to count, and in "N ± M-fold" the point estimate `N` is taken
rather than the dispersion `M`. Evidence is thereby stratified into three tiers —
**tier 1** (effect + variance), **tier 2** (effect only), **tier 3** (direction
only).

**Technical advantage.** The system extracts magnitude only when it is literally
present and unit-consistent in the source, and refuses variance otherwise, so it
never manufactures confidence. In a controlled audit, this rejected the majority
of naively parsed magnitudes that were in fact concentrations or error bars
[Results: Table X], while preserving genuine reported fold and percentage changes.

### 2.6 Hierarchical random-effects evidence synthesis

**Motivation.** Effects for one component come from studies with genuinely
different cell sources and assays, so a fixed-effect pool would understate
uncertainty and hide disagreement.

**Design.** For a component with `k ≥ 2` tier-1 effects we fit a DerSimonian–Laird
random-effects model: the pooled effect is `θ̂ = Σ wᵢθᵢ / Σ wᵢ` with inverse-total-
variance weights `wᵢ = 1 / (vᵢ + τ²)`, where the between-study variance `τ²` is the
DerSimonian–Laird moment estimator from Cochran's `Q`. Heterogeneity is reported
as the Higgins–Thompson statistic `I² = max(0, (Q − (k−1)) / Q)`. Components with
only direction-tiered evidence are summarized by a Beta-Binomial posterior on the
probability of benefit `p_beneficial`, updated from the counts of supporting and
opposing studies under a weak symmetric prior. Evidence that is directionally
split beyond a threshold is flagged `context_dependent`.

**Technical advantage.** Synthesis reports not just a pooled direction but a
calibrated dispersion: high `I²` and the context-dependence flag are carried
forward and change how the optimizer treats the component (Section 2.7), so
disagreement in the literature becomes exploration rather than false confidence.

### 2.7 Evidence-conditioned priors for Bayesian optimization

**Motivation.** Literature beliefs should bias early search toward plausible
formulations, but must never override the wet lab as data accumulates, and must
not push a beneficial component to an unrealistic maximum dose.

**Design.** Each component summary is mapped to a belief (direction, strength,
context flag) and combined into a prior `π(x)` over the encoded design space. The
prior is injected into the acquisition function following the πBO scheme,

```
α_πBO(x) = α(x) · π(x)^{β / (1 + n)},
```

so the prior's weight decays with the number of wet-lab observations `n`. A
beneficial component contributes a **saturating** inclusion reward,
`r(x) = 2·x/(x + K) − 1`, which rewards presence with diminishing returns rather
than rewarding the maximum dose; a detrimental component is pushed symmetrically
toward exclusion. Components flagged high-`I²` or context-dependent receive a
**flat** prior, so the optimizer explores them instead of trusting a
non-transferable pooled belief. Duplicate component summaries are de-duplicated,
keeping the best-supported (highest `k`) row.

**Technical advantage.** The prior is strong exactly when data is scarce and
vanishes as the loop runs, giving sample-efficient early search without biasing
the converged solution; the saturating reward encodes the biological fact that
benefits plateau, avoiding the dose-overshoot that a linear preference would
cause.

### 2.8 Multi-objective closed-loop optimization

**Motivation.** Expansion, cost, and identity trade off against one another, so
the target is a Pareto front rather than a single optimum, under a small
experimental budget.

**Design.** We model the objectives with Gaussian-process surrogates and select
batches by multi-objective acquisition — noisy expected hypervolume improvement
(qNEHVI) and, as an alternative backend, randomized-scalarization q-ParEGO — with
the evidence prior of Section 2.7 folded into the acquisition. Each proposed batch
is executed in the wet lab; measured objectives are returned through `tell(x, y)`,
which conditions the surrogate and advances the loop. Pre-registered design
packets are committed before results exist, so proposals cannot be retrofitted to
outcomes.

**Technical advantage.** Hypervolume-based batch acquisition targets the whole
trade-off surface under a fixed experiment budget, and the closed-loop `tell`
path keeps the optimizer grounded in the project's own measurements — the only
labels the system treats as objective truth.

### 2.9 Human-in-the-loop gating and auditability

**Motivation.** Scientific decisions — which evidence is admissible, which
variables enter a wet-lab round, whether to proceed — must remain human, and must
be traceable.

**Design.** The workflow is organized as sequential gates from environment setup
and scope locking, through corpus curation, extraction, and **human adjudication
of the evidence table**, to search-space design, robustness/pre-registration, and
wet-lab entry. Wet-lab execution is blocked until the upstream evidence,
adjudication, and pre-registration gates pass. Machine outputs (grounded evidence,
audit packets, adjudication worksheets) are prepared for review but never
overwrite human notes, and each gate names its owner.

**Technical advantage.** Gating makes the system's epistemic status explicit at
all times: a failing gate is reported as a failure rather than silently bypassed,
so no optimization or wet-lab claim can outrun the evidence and human approval
behind it.

### 2.10 Implementation details

The extractor and effect operators are provider-agnostic (OpenAI-compatible
clients) and were validated with a deliberately low-quality, text-only model to
stress the grounding and provenance safeguards; a stronger model raises coverage
and precision but is not required for the design to hold. Extraction runs at
temperature 0, routes effect-bearing sections (results/methods/media/discussion)
into a bounded context window, and drops ungrounded claims before synthesis. The
optimizer uses a Gaussian-process/BoTorch backend for qNEHVI and q-ParEGO. The
knowledge base, evidence tables, audit packets, and pre-registered design packets
are stored as file-based, version-controlled artifacts to preserve provenance.

---

*Assumptions/placeholders:* result magnitudes (`[Results: Table X]`), the exact
objective and constraint list, final journal target, and any citations are left
for the author to supply; the Methods above describe only the implemented method.
