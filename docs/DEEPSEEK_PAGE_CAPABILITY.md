# DeepSeek Page-Candidate Localization Probe

**Status: PASS_FOR_BOUNDED_SHADOW_LOCALIZATION**

- Model: `deepseek-v4-flash` (non-thinking, temperature 0)
- Prompt/schema version: `page-candidate-pointer-v1`
- Hash-verified silver items: 40 (20 positives)
- Valid requests: 12/12
- Hard request cap: 12
- Recall by repeat: 1.000, 1.000, 1.000
- Silver precision by repeat (decoys unadjudicated; not gated): 0.588, 0.625, 0.588
- Run-to-run selection consistency: 0.950
- Total API tokens reported: 58366
- Validation issues: 0

Passing authorizes only bounded shadow candidate localization. Silver positives are frozen deterministic locators, not adjudicated biological evidence; DeepSeek outputs cannot create evidence tiers or transcribe numeric values.

## False-Positive IDs

- `P001`, `P009`, `P011`, `P014`, `P015`, `P017`, `P018`, `P019`, `P021`, `P026`, `P028`, `P030`, `P035`, `P037`
