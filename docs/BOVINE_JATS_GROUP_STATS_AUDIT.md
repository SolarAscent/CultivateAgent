# Bovine JATS Group-Statistics Readiness Audit

## Scope And Safety Boundary

- Verified JATS sources: 14.
- Parsed structured tables: 37; cells: 2103.
- This audit emits source/table/cell/footnote pointers and counts only. It does
  not transcribe source numbers, assign treatment/control roles, approve an
  evidence tier, or call an LLM.
- Every source passed canonical DOI/paper-ID, PMCID, license, XML SHA-256, and
  acquisition table/cell-count checks before classification.

## Result

- Structural group-statistics candidates: 0.
- Incomplete statistical tables: 9.
- Excluded non-effect statistical tables: 12.
- Decision: `OFF_RAMP_NO_COMPLETE_TABLE_STRUCTURE`.

| Deterministic status | Tables |
|---|---:|
| `excluded_non_effect_statistics` | 12 |
| `incomplete_missing_dispersion_type_and_sample_size` | 1 |
| `incomplete_missing_sample_size` | 8 |
| `no_group_stat_structure` | 16 |

The current verified JATS set does not justify a DeepSeek cell-role run unless
the candidate count is nonzero. Tables with dispersion but no table-bound sample
size remain incomplete; composition/resource statistics and model coefficients
cannot be promoted as treatment/control effects. Caption and footnote sample-size
locators are diagnostic only: the frozen pointer schema requires an addressable
table cell for n.

## Incomplete Tables

| Record | Table | Status | Dispersion locators | Sample-size context locators |
|---|---|---|---|---|
| R023 | T3 | `incomplete_missing_dispersion_type_and_sample_size` | - | - |
| R054 | T5 | `incomplete_missing_sample_size` | T5.R1.C10;T5.F4 | - |
| R054 | T6 | `incomplete_missing_sample_size` | T6.R1.C10;T6.F4 | - |
| R054 | T7 | `incomplete_missing_sample_size` | T7.R1.C10;T7.F4 | - |
| R054 | T8 | `incomplete_missing_sample_size` | T8.R2.C9;T8.F2 | - |
| R054 | T9 | `incomplete_missing_sample_size` | T9.R1.C10;T9.F4 | - |
| R054 | T10 | `incomplete_missing_sample_size` | T10.R1.C10;T10.F4 | - |
| R054 | T11 | `incomplete_missing_sample_size` | T11.R1.C10;T11.F4 | - |
| R054 | T12 | `incomplete_missing_sample_size` | T12.R2.C9;T12.F2 | - |

## Excluded Statistical Tables

| Record | Table | Reason |
|---|---|---|
| R023 | T6 | `model_or_significance_statistics` |
| R023 | T7 | `model_or_significance_statistics` |
| R023 | T8 | `model_or_significance_statistics` |
| R023 | T9 | `model_or_significance_statistics` |
| R023 | T10 | `model_or_significance_statistics` |
| R023 | T11 | `model_or_significance_statistics` |
| R023 | T12 | `model_or_significance_statistics` |
| R023 | T13 | `model_or_significance_statistics` |
| R052 | T4 | `composition_or_resource_statistics` |
| R052 | T5 | `composition_or_resource_statistics` |
| R052 | T6 | `composition_or_resource_statistics` |
| R054 | T4 | `non_medium_outcome_statistics` |

## Reproduction

```bash
python scripts/audit_bovine_jats_group_stats.py
```

- Source audit SHA-256: `50f1445a0fdf521d18a170ed336f75ed174fdcac1021be073714fa1597bb005c`.
- Table audit SHA-256: `828ae42cce234a48c75c5e3e14ad511882d040a3d77a37cd7e62c4fed039815c`.
- Source and table TSVs contain no source numeric values.
