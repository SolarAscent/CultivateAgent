# DeepSeek Visual-Result Page Probe v1

**Status: PASS_FOR_BOUNDED_SHADOW; NOT APPROVED FOR PRODUCTION BATCHING.**

`deepseek-v4-flash` ran `visual-result-page-pointer-v1` three times at
temperature 0 with thinking disabled. Fifteen requests were allowed, all
responses passed the ID-only schema, and 68,562 tokens were reported.

All three runs selected the same 20/40 pages and recovered all 6/6 silver
positives: recall 1.00, exact selection consistency 1.00, and page reduction
50%. The fixed utility gate required at least 40% reduction. The committed
manifest preserves every repeat's source-bound page pointers and hashes, but no
page text or source numeric value.

This pass permits only a small source-disjoint shadow run. Production routing
still requires shadow utility plus recall safeguards; DeepSeek cannot approve
evidence, transcribe figure values, or assign treatment/control statistics.
