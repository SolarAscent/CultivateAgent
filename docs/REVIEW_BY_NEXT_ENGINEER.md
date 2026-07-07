# Review By Next Engineer

This is a critical review of the current CultivateAgent design after the July 2026 continuation session.

## What I Would Keep

- The locked medium-only action boundary is right for a first working system. Medium variables are expensive, measurable, and directly optimizable; cell source, scaffold, and process context should be read as covariates until the project has enough data to model interactions.
- Evidence grounding should remain non-negotiable. The extraction evaluator and smoke fixtures now make grounding rate a reported quantity rather than an aspiration.
- Treating cross-paper outcomes as search-space priors rather than training labels is scientifically honest. Stout et al. report Beefy-9 expansion behavior in a specific bovine satellite-cell context; Messmer et al. address differentiation; O'Neill et al. explicitly points toward species and cell-type dependence. Those are not interchangeable response labels.

## Design Risks

- The A-M schema is probably too large for reliable full-paper annotation without a two-pass human rubric. The offline fixture in `docs/EVAL_RESULTS.md` shows that fields requiring methods/tables are easy to miss even with generous mock predictions. The next step should be a strict "screening subset" score and a separate deep-extraction score.
- The optimizer's default numpy GP + q-ParEGO path is useful as an offline baseline, but it is not enough to call the project production-ready. The BoTorch qNEHVI path now runs, and the small synthetic benchmark in `docs/OPTIMIZATION_BENCHMARK.md` favored qNEHVI over q-ParEGO on mean normalized final HV. However, BoTorch 0.18.1 warns that legacy qNEHVI has numerical issues; Ament et al. 2023 introduced LogEI-family acquisitions to address vanishing acquisition values and gradients. The next production path should test `qLogNoisyExpectedHypervolumeImprovement`.
- Medium-only scope is focused, but novelty will not come from "LLM extracts papers then BO suggests knobs" by itself. The high-value contribution is the honest treatment of heterogeneous literature evidence plus pre-registerable wet-lab optimization.

## Deepest Problem: Outcome Comparability

The current stance, "do not treat cross-paper outcomes as comparable labels," is correct but incomplete. A stronger path is a hierarchical Bayesian meta-analysis layer:

- Standardize within-paper effects when possible: log fold-change for proliferation endpoints, standardized mean difference when variance is reported, or direction-only Bernoulli evidence when the paper lacks usable variance.
- Model paper/context heterogeneity explicitly: effect ~ component + dose + basal medium + species + cell type + stage + random paper intercept + random lab/source intercept.
- Use the posterior as a prior over candidate regions, not as direct objective values. For example, high posterior probability that FGF2 helps bovine satellite-cell expansion should bias candidate generation, while uncertainty should widen the trust region.
- Keep original values and quotes attached to every transformed effect so the reviewer can audit what was pooled and what was only directionally encoded.

This is likely more publishable than another wrapper around qEHVI because it attacks the core scientific obstacle in medium literature mining.

## Alternative Algorithms To Consider

- TuRBO: Eriksson et al. introduced trust-region BO for high-dimensional black-box optimization; it fits medium design once ontology-derived spaces grow beyond a dozen knobs. It can slot into `optimize/` as a candidate-pool generator that maintains local regions around good formulations.
- SCBO: Eriksson and Poloczek's scalable constrained BO extends the trust-region idea to constraints. This fits food-grade, osmolality, pH, maximum cost, or "no animal-derived component" constraints better than encoding everything as objectives.
- Multi-fidelity BO: Kandasamy et al. frame cheap approximations as a way to reduce expensive evaluations. Medium design has natural fidelities: 72 h viability or metabolic proxy first, then longer proliferation, then differentiation retention.
- Information-theoretic MOBO: PESMO, MESMO, or JES are appropriate when the scientific objective is learning the Pareto set efficiently, not merely improving a scalar hypervolume proxy.
- Deep-kernel or BNN surrogates: only justified after enough wet-lab points accumulate or if transfer data across cell types becomes real. Do not add this early.
- DPP batch diversity: Nava, Mutny, and Krause use determinantal point processes for diverse batched BO. This is a good fit when a wet-lab batch should avoid testing four near-duplicates.
- Meta/transfer BO across cell types: useful only after the project has consistently annotated species/cell-type covariates and measured same-lab outcomes. Until then, it risks laundering incomparability into a model.

## Science / Ontology Sanity Check

- `CLASS_RANGES["growth_factor"] = 0-100 ng/mL` covers common FGF2-style ranges used around B8/Beefy-9 and is reasonable as a broad search bound.
- `CLASS_RANGES["albumin_substitute"] = 0-5 mg/mL` is broad enough for recombinant albumin search around Beefy-9-like formulations.
- `CLASS_RANGES["serum"] = 0-20%` excludes some legacy high-serum expansion protocols; that is acceptable for a serum-reduction optimizer but should be documented as an intervention range, not a literature-universal range.
- Potential bug: ontology categories `hydrolysate` and `extract` are not selected by `space_from_kb`, which loops only over `growth_factor`, `small_molecule`, and `supplement`. This can drop cost-reduction components such as algae extract or plant hydrolysates from the warm-started search space.
- Potential modeling issue: `supplement` range is reused as `g/L` for soy-protein-hydrolysate in the default space, while the class label says `x/%`. Add class-specific ranges for `hydrolysate` and `extract`.

## Verified Sources Used

- Stout et al., "Simple and effective serum-free medium for sustained expansion of bovine satellite cells for cell cultured meat", Communications Biology 5, 466 (2022): [Nature](https://www.nature.com/articles/s42003-022-03423-8), [PubMed](https://pubmed.ncbi.nlm.nih.gov/35654948/).
- Messmer et al., "A serum-free media formulation for cultured meat production supports bovine satellite cell differentiation in the absence of serum starvation", Nature Food 3, 74-85 (2022): [Nature](https://www.nature.com/articles/s43016-021-00419-1), [PubMed](https://pubmed.ncbi.nlm.nih.gov/37118488/).
- O'Neill et al., "Spent media analysis suggests cultivated meat media will require species and cell type optimization", npj Science of Food 6, 46 (2022): [Nature](https://www.nature.com/articles/s41538-022-00157-z), [PMC reference context](https://pmc.ncbi.nlm.nih.gov/articles/PMC11663224/).
- Kolkmann et al., "Development of serum-free and grain-derived-nutrient-free medium using microalga-derived nutrients and mammalian cell-secreted growth factors for sustainable cultured meat production", Scientific Reports 13, 498 (2023): [Nature](https://www.nature.com/articles/s41598-023-27629-w), [PubMed](https://pubmed.ncbi.nlm.nih.gov/36627406/).
- Daulton, Balandat, and Bakshy, qEHVI/qNEHVI family: [BoTorch multi-objective docs](https://botorch.org/docs/multi_objective), [qNEHVI/qParEGO tutorial](https://botorch.org/docs/tutorials/constrained_multi_objective_bo). LogEI guidance: [Ament et al. 2023](https://arxiv.org/abs/2310.20708).
- Eriksson et al., TuRBO, NeurIPS 2019: [NeurIPS](https://proceedings.neurips.cc/paper/2019/hash/6c990b7aca7bc7058f5e98ea909e924b-Abstract.html). Eriksson and Poloczek, SCBO, AISTATS 2021: [PMLR PDF](https://proceedings.mlr.press/v130/eriksson21a/eriksson21a.pdf). Kandasamy et al., multi-fidelity BO, ICML 2017: [PMLR](https://proceedings.mlr.press/v70/kandasamy17a.html). Hernandez-Lobato et al., PESMO, ICML 2016: [PMLR](https://proceedings.mlr.press/v48/hernandez-lobatoa16.html). Nava, Mutny, and Krause, DPP-BBO, AISTATS 2022: [PMLR](https://proceedings.mlr.press/v151/nava22a.html).
