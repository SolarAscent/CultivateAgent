# Provider Agreement Report

Status: offline cross-provider simulation (`mock_gpt`, `mock_claude`, `mock_gemini`). Requested live providers: openai:gpt-5.4, anthropic:claude-opus-4-6.

Agreement scope: `live`

Compared providers: `anthropic:claude-opus-4-6`, `openai:gpt-5.4`

## Agreement By Categorical Field

| field | mean_kappa | mean_exact | nonmissing_fraction |
| --- | --- | --- | --- |
| B.main_track | 1.0 | 1.0 | 0.0 |
| E.serum_free_status | 1.0 | 1.0 | 0.0 |
| J.has_extractable_quant_data | 1.0 | 1.0 | 0.0 |
| M.recommended_action | 1.0 | 1.0 | 0.0 |

## Least Reliable Fields

- `B.main_track`: mean kappa 1.0, exact agreement 1.0, non-missing fraction 0.0
- `E.serum_free_status`: mean kappa 1.0, exact agreement 1.0, non-missing fraction 0.0

## Interpretation

- `E.serum_free_status` is vulnerable to overclaiming chemically defined status from a serum-free claim.
- `J.has_extractable_quant_data` mixes article-level data availability with abstract-level visibility; it needs a stricter rubric.
- `B.main_track` splits when papers are both medium and structured-tissue demonstrations; medium-centered downstream code should keep acting only on medium variables.
- High agreement with low non-missing fraction is not meaningful agreement; it means providers failed to extract the field.
