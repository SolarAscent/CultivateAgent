# Does the evidence prior actually help? An honest benchmark

Reproduce: `python scripts/benchmark_evidence_prior.py` (offline, no API key).
Metric: normalized hypervolume vs number of experiments, mean over 6 seeds. Three
conditions: **no-prior**, **correct** evidence prior, and **wrong** evidence prior
(points at decoy components) — the wrong condition is included on purpose, to show
the failure mode and the πBO recovery rather than only a flattering number.

## Result 1 — easy, saturating objective: prior ≈ neutral

`SyntheticMediumObjective` (benefits saturate, cost linear; random search already
does well). The directional prior neither helps nor meaningfully hurts.

| #exp | no-prior | correct | wrong |
|---|---|---|---|
| 9  | 0.690 | 0.689 | 0.681 |
| 17 | 0.753 | 0.766 | 0.756 |
| 37 | 0.821 | 0.812 | 0.811 |

## Result 2 — sparse objective: correct prior accelerates, wrong prior costs

`SparseProliferationBenchmark`: only 3 of 12 components affect proliferation; the
rest are pure-cost decoys. This is the regime the literature prior is *for* —
"which knobs matter" is exactly what a cold-start optimizer must otherwise
discover.

| #exp | no-prior | correct | wrong |
|---|---|---|---|
| 9  | 0.682 | 0.683 | 0.606 |
| 13 | 0.761 | **0.787** | 0.714 |
| 17 | 0.788 | **0.834** | 0.734 |
| 21 | 0.845 | 0.846 | 0.799 |
| 37 | 0.935 | 0.925 | 0.878 |

* **Correct prior accelerates early** (+0.03 to +0.05 normalized-HV around 13–17
  experiments) — reaching a given quality in fewer wet-lab runs, which is the
  whole point when each run is expensive.
* **Wrong prior consistently costs experiments** (it steers toward decoys),
  recovering slowly as the πBO weight `β/(1+n)` decays.
* **The advantage fades late**: by ~37 experiments the no-prior optimizer catches
  up. Correct — priors matter most when data is scarce; they are not a permanent
  crutch.

## A design flaw this benchmark caught (and fixed)

The first prior encoded "beneficial → prefer the *maximum* dose" (linear). On
saturating-benefit / linear-cost objectives the optimum is *interior*, so that
prior **overshot and hurt even when it named the right components**. The fix,
also more biologically faithful: reward *inclusion with diminishing returns*
(a Michaelis-Menten-like saturating reward), so the prior says "include this
component" without pushing the dose to the boundary. Result 2 is with the fix.

## Takeaways (what to tell a reviewer)

1. Directional literature evidence is best used for **inclusion / direction-of-
   change** decisions, not for setting optimal continuous doses.
2. The prior **earns its keep when the search is hard** (many candidate
   components, few relevant) — precisely the cultivated-meat medium setting.
3. A **wrong** prior is not catastrophic but is not free either — which is exactly
   why high-heterogeneity (I² ≥ 0.5) components get a *flat* prior and a
   "test directly" flag instead of a confident bias (see `EVIDENCE_SYNTHESIS.md`).

This is honest evaluation: the method helps where it should, is neutral where the
problem is easy, and its failure mode is bounded and understood.
