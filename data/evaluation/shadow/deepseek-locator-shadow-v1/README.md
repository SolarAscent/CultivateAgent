# DeepSeek Locator Shadow v1

This artifact is a bounded candidate-generation result over R018 and R045.

- A deterministic prefilter supplied 24 PDF text-block candidates containing an
  SD/SEM, sample-size, or explicit dispersion signal.
- `deepseek-v4-flash` ran with thinking disabled and temperature 0 for three
  repeats. All six requests were schema-valid and selection consistency was 1.0.
- Only the 18 unanimously selected block pointers are retained in `manifest.json`.
- The manifest contains page/block/hash pointers only. It contains no source
  excerpts or transcribed numeric values.

These pointers require deterministic source revalidation and expert review.
They are not biological evidence and cannot establish an evidence tier.

Post-run source inspection found that this `stat-only-block-v1` prefilter also
admitted RNA/protein quality-control statistics, a reporting checklist, and a
metabolite AUC table. This artifact is retained as an audit trail and must not
be used as the current candidate set; `deepseek-locator-shadow-v2` supersedes it.
