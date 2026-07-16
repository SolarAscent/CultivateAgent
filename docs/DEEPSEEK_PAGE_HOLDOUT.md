# DeepSeek Page-Candidate Localization Probe

**Status: PASS_FOR_BOUNDED_SHADOW_LOCALIZATION**

- Model: `deepseek-v4-flash` (non-thinking, temperature 0)
- Prompt/schema version: `page-candidate-pointer-v1`
- Hash-verified silver items: 26 (13 positives)
- Valid requests: 9/9
- Hard request cap: 9
- Recall by repeat: 1.000, 1.000, 1.000
- Silver precision by repeat (decoys unadjudicated; not gated): 0.650, 0.650, 0.650
- Run-to-run selection consistency: 1.000
- Total API tokens reported: 44820
- Validation issues: 0

Passing authorizes only bounded shadow candidate localization. Silver positives are frozen deterministic locators, not adjudicated biological evidence; DeepSeek outputs cannot create evidence tiers or transcribe numeric values.

## False-Positive IDs

- `P002`, `P003`, `P007`, `P011`, `P012`, `P015`, `P018`
