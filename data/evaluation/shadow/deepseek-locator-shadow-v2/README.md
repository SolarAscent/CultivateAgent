# DeepSeek Locator Shadow v2

**Status: FAIL_HELD_OUT_RECALL; no delegated candidate output.**

This run corrected the v1 prefilter by requiring both a statistical signal and
a medium/outcome/figure/error-policy context signal. The deterministic pool fell
from 24 to 17 blocks while retaining all 12 frozen R018/R045 quantitative-pilot
locators.

`deepseek-v4-flash` processed the 17 blocks in two batches for three repeats at
temperature 0 with thinking disabled. All six responses were schema-valid and
selection consistency was 1.0. The model selected 12 blocks in every repeat,
but only 10 of the 12 held-out silver locators, for recall 0.8333. It missed
Q005 and Q009, below the predeclared 0.95 delegation threshold.

The committed manifest therefore contains no candidate pointers and has
`deployment_gate_pass=false`. Raw ID-only responses remain in ignored atomic
checkpoints. Do not tune against Q005/Q009 and then report the same set as an
independent test; a new held-out set is required before reconsidering bulk
delegation.
