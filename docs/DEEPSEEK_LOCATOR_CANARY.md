# DeepSeek Quantitative-Block Localization Probe

**Status: PASS_FOR_BOUNDED_SHADOW_LOCALIZATION**

- Model: `deepseek-v4-flash` (non-thinking, temperature 0)
- Prompt/schema version: `quant-block-candidate-pointer-v1`
- Hash-verified silver items: 24 (8 positives)
- Valid requests: 6/6
- Hard request cap: 6
- Recall by repeat: 1.000, 1.000, 1.000
- Precision by repeat (reported, not gated): 0.889, 0.889, 0.889
- Run-to-run selection consistency: 1.000
- Total API tokens reported: 8820
- Validation issues: 0

Passing authorizes only bounded shadow candidate localization. Silver positives are frozen deterministic locators, not adjudicated biological evidence; DeepSeek outputs cannot create evidence tiers or transcribe numeric values.

## False-Positive IDs

- `L012`
