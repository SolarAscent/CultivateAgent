# DeepSeek Visual-Result Page Held-out Shadow v1

**Status: FAIL_NO_PRODUCTION_ROUTING.**

The PDF held-out manifest was committed before this first API run with SHA-256
`aacb1ab9f73e1dc7bbb9fbf6a7cb3ad858153f94166d636c44964a3af8bb8b05`.
`deepseek-v4-flash` processed all 48 readable pages from R016, R021, and
R022 in five batches for three repeats at temperature 0 with thinking disabled.
All 15 responses passed the ID-only schema and reported 80,940 total tokens.

The strict frozen result looked successful: every repeat selected the same
26/48 pages and recovered all 6/6 strict R021 positives. This corresponds to
recall 1.00, consistency 1.00, and 45.8% reduction relative to reading every
page.

Production routing nevertheless fails. A deterministic post-hoc sensitivity
audit found 12 pages containing field-aware figure-caption, outcome, and medium
signals. DeepSeek recovered 11/12 (recall 0.9167), missing R016 page 12. The
model also selected 26 pages versus 12 for the no-model baseline, so it did not
reduce review work relative to the existing deterministic system. Because this
broader rule was applied after the API run, it can block deployment but cannot
be used to claim an independent pass.

The result and utility audit contain source-bound page pointers and hashes only.
They contain no source text or numeric values and cannot approve evidence or a
wet-lab variable.
