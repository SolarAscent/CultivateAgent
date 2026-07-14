# DeepSeek Alias-Mapping Capability Probe

**Status: FAIL**

- Model: `deepseek-v4-flash` (non-thinking, temperature 0)
- Prompt/schema version: `alias-map-pointer-v2-recall`
- Ontology-derived alias gold: 8
- Valid requests: 3/3
- Hard request cap: 3
- Recall by repeat: 0.875, 0.875, 0.875
- Canonical run-to-run consistency: 1.000
- Total API tokens reported: 1701
- Validation issues: 0

Passing authorizes only shadow alias-candidate mapping. Codex/Claude must still review every proposed ontology change; this report is not biological evidence.

Official configuration references: [DeepSeek V4 models](https://api-docs.deepseek.com/quick_start/pricing), [thinking-mode toggle](https://api-docs.deepseek.com/guides/thinking_mode), and [JSON output](https://api-docs.deepseek.com/api/create-chat-completion).

## Stable Or Intermittent Mismatches

- `A005 'Beefy-9 base': expected 'B8'; repeats=('UNKNOWN', 'UNKNOWN', 'UNKNOWN')`
