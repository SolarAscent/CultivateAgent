# Evidence Audit: proliferation

Status: generated from extracted evidence items; requires human review before wet-lab use.

## Decision

**Wet-lab entry gate: NO-GO.**

| Metric | Value |
|---|---:|
| Evidence items audited | 145 |
| Source papers represented | 40 |
| Components/interventions represented | 103 |
| AI-review candidates | 4 |
| Critical human-review tasks open | 16/16 |

## Blocking Reasons

- 16/16 critical human-review tasks remain open.
- All AI-review candidates are direction-only; no candidate has quantitative effect evidence.

## Criteria

A component is only an **AI-review candidate** when all of these are true:

- at least one item matches the locked bovine satellite-cell/myoblast expansion target;
- at least one item is medium-actionable rather than scaffold, microcarrier, process, or genetic-engineering coupled;
- at least one item contains a dose or concentration cue in the component text or quote;
- all items have grounded quotes in the extracted record.

This audit is intentionally stricter than evidence synthesis. It is a go/no-go guardrail, not a ranking of biological promise.

## AI-Review Candidates

| Component | Papers | Ready items | Direct target items | Dose-supported items | Quantitative items | Flags |
|---|---:|---:|---:|---:|---:|---|
| FGF2 | 5 | 1 | 3 | 2 | 0 | direction_only |
| ECC_CPS3 | 1 | 1 | 6 | 1 | 0 | direction_only |
| ECC_CPS1 | 1 | 1 | 1 | 1 | 0 | direction_only |
| ECC_CPS2 | 1 | 1 | 1 | 1 | 0 | direction_only |

## Top Rejected Or Weak Items

| Component | Papers | Direct target items | Medium-actionable items | Dose-supported items | Flags |
|---|---:|---:|---:|---:|---|
| FBS | 5 | 0 | 5 | 1 | indirect_species_or_cell, direction_only |
| hypoxia | 2 | 2 | 0 | 0 | not_medium_only, no_dose_cue, direction_only |
| differentiation medium | 2 | 0 | 2 | 0 | indirect_species_or_cell, no_dose_cue, direction_only |
| Matrigel | 2 | 0 | 0 | 2 | indirect_species_or_cell, not_medium_only, direction_only |
| heparan sulphate | 1 | 2 | 2 | 0 | no_dose_cue, direction_only |
| addition of new microcarriers | 1 | 1 | 0 | 0 | not_medium_only, no_dose_cue, direction_only |
| B8 media alone | 1 | 1 | 1 | 0 | no_dose_cue, direction_only |
| B8 media mixed with BSC-GM | 1 | 1 | 1 | 0 | no_dose_cue, direction_only |
| bovine collagen type I | 1 | 1 | 0 | 0 | not_medium_only, no_dose_cue, direction_only |
| hIL-6 | 1 | 1 | 1 | 0 | no_dose_cue, direction_only |
| Mesenchymal Stem Cell Growth Medium DXF | 1 | 1 | 1 | 0 | no_dose_cue, direction_only |
| mouse bladder organoid supernatant | 1 | 1 | 2 | 0 | no_dose_cue, direction_only |
| PD173074 | 1 | 1 | 1 | 0 | no_dose_cue, direction_only |
| recombinant-albumin | 1 | 1 | 1 | 0 | no_dose_cue, direction_only |
| StemFlex™ Medium | 1 | 1 | 1 | 0 | no_dose_cue, direction_only |
| 10% FBS | 1 | 0 | 1 | 0 | indirect_species_or_cell, no_dose_cue, direction_only |
| 2D monolayer culture | 1 | 0 | 1 | 0 | indirect_species_or_cell, no_dose_cue, direction_only |
| 2xM17 + 2% glucose medium | 1 | 0 | 1 | 0 | indirect_species_or_cell, no_dose_cue, direction_only |
| 3D spheroid culture | 1 | 0 | 1 | 0 | indirect_species_or_cell, no_dose_cue, direction_only |
| A. awamori | 1 | 0 | 1 | 0 | indirect_species_or_cell, no_dose_cue, direction_only |

## Next Actions

1. Complete the open critical human-review tasks before any wet-lab design packet.
2. For each AI-review candidate, extract exact formulation, dose, endpoint, passage, and quote into the adjudicated evidence table.
3. Keep rejected process/scaffold/genetic-engineering items out of the first medium-only search space unless a scope-change decision record is created.
