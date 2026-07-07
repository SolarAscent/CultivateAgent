# Provider Agreement Report

Status: offline cross-provider simulation (`mock_gpt`, `mock_claude`, `mock_gemini`).

Compared providers: `mock_claude`, `mock_gemini`, `mock_gpt`

## Agreement By Categorical Field

| field | mean_kappa | mean_exact |
| --- | --- | --- |
| B.main_track | 0.3333 | 0.5 |
| E.serum_free_status | 0.3846 | 0.5 |
| J.has_extractable_quant_data | 0.203 | 0.5 |
| M.recommended_action | 0.3762 | 0.6667 |

## Least Reliable Fields

- `J.has_extractable_quant_data`: mean kappa 0.203, exact agreement 0.5
- `B.main_track`: mean kappa 0.3333, exact agreement 0.5

## Interpretation

- `E.serum_free_status` is vulnerable to overclaiming chemically defined status from a serum-free claim.
- `J.has_extractable_quant_data` mixes article-level data availability with abstract-level visibility; it needs a stricter rubric.
- `B.main_track` splits when papers are both medium and structured-tissue demonstrations; medium-centered downstream code should keep acting only on medium variables.
