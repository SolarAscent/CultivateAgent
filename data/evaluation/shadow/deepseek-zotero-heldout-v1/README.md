# DeepSeek Zotero Locator Held-out v1

**Status: FAIL_INDEPENDENT_RECALL; task closed for bulk delegation.**

The gold manifest was frozen in commit `111b7c3` with SHA-256
`46ca3a166d54fac3aca5328c5e8d601db530c14cd1e09502556d1cd04ccf2b6c`.
No prompt, selector, source, or silver locator was changed before this run.

## Configuration

- Model: `deepseek-v4-flash`, thinking disabled, temperature 0.
- Prompt: `quant-block-candidate-pointer-v1`.
- Selector: `stat-context-block-v2`.
- Input: 19 blocks; held-out silver: 13; prefilter coverage: 13/13.
- Runtime: two batches for three repeats, six requests, no retries, atomic
  checkpoints, 11,904 reported tokens.

## Result

- All six responses passed the ID-only JSON schema.
- Run-to-run selection consistency was 1.0.
- The model selected the same 16 blocks each time but recovered only 10/13
  silver locators: recall 0.7692.
- Missed locators: Q009, Q011, and Q013. All three are explicit Z004 bovine MSC
  growth-medium/insulin/FBS quantitative figure captions.
- The deployment gate failed and the committed manifest contains zero candidate
  pointers.

This is the second held-out recall failure after R018/R045 (10/12, 0.8333).
Stable repetition does not compensate for stable false negatives. Do not tune
on these misses and reuse this benchmark as independent evidence. Keep the
deterministic context prefilter, but route quantitative-block review to
Codex/Claude or a future separately validated model.
