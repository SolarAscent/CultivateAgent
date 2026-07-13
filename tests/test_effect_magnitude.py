"""Guards against fabricated effect magnitudes in the numeric inference.

The magnitude inferrer parses proportional phrasing out of a *verified* quote.
The risk is that a number appearing in the quote is a concentration ("30% FBS")
or a dispersion ("2.2 ± 0.4-fold"), not an effect size. Those must NOT become a
log-response-ratio; the item stays direction-only instead.
"""

from __future__ import annotations

import math

from cultivate_agent.evidence.effect_operator import (
    _infer_log_response_ratio as infer,
    numeric_effect_from_group_stats,
)


def test_concentration_percent_is_not_an_effect():
    # "30% FBS" / "1% Glutamax" are composition, even though the model said dir=+1.
    q = "The proliferation medium was a mixture of 30% FBS, 1% Glutamax, and 5 ng/mL bFGF"
    assert infer(q, 1).effect is None


def test_concentration_with_effect_word_is_still_not_an_effect():
    # A real effect word ("enhanced") next to a concentration number must not pair
    # the two into a fabricated "+20%" magnitude.
    q = "20% FBS-PSFC significantly enhanced cell expansion compared to 20% FBS"
    assert infer(q, 1).effect is None


def test_dispersion_is_not_mistaken_for_the_point_estimate():
    # "2.2 ± 0.4-fold": the effect is 2.2x, never the error bar 0.4.
    r = infer("cells amplified 2.2 ± 0.4-fold over control", 1)
    assert r.effect is not None
    assert math.isclose(math.exp(r.effect), 2.2, rel_tol=1e-6)


def test_genuine_percent_change_survives():
    r = infer("FGF2 increased proliferation by 30% relative to control", 1)
    assert r.effect is not None
    assert math.isclose(math.exp(r.effect), 1.30, rel_tol=1e-6)


def test_genuine_fold_change_survives():
    r = infer("supplementation enhanced cell number 2.5-fold over the control", 1)
    assert r.effect is not None
    assert math.isclose(math.exp(r.effect), 2.5, rel_tol=1e-6)


def test_genuine_reduction_survives():
    r = infer("treatment reduced proliferation by 40%", -1)
    assert r.effect is not None
    assert math.isclose(math.exp(r.effect), 0.60, rel_tol=1e-6)


def test_no_variance_is_ever_fabricated_from_proportional_text():
    # Proportional phrasing yields tier-2 at most: an effect, never a variance.
    r = infer("supplementation enhanced cell number 2.5-fold over the control", 1)
    assert r.variance is None


# --- frozen seam for the table-extraction path (evidence/tables.py feeds this) ---

def test_group_stats_seam_yields_tier1_effect_and_variance():
    # treatment 2.0±0.4 (n=6) vs control 1.0±0.3 (n=6):
    #   effect = ln(2/1) = 0.6931; var = 0.4^2/(6*2^2) + 0.3^2/(6*1^2) = 0.021667
    r = numeric_effect_from_group_stats(
        {"mean": 2.0, "sd": 0.4, "n": 6},
        {"mean": 1.0, "sd": 0.3, "n": 6},
        outcome="proliferation",
    )
    assert r.effect is not None and r.variance is not None          # tier 1
    assert math.isclose(r.effect, math.log(2.0), rel_tol=1e-9)
    assert math.isclose(r.variance, 0.4**2 / (6 * 2.0**2) + 0.3**2 / (6 * 1.0**2), rel_tol=1e-9)


def test_group_stats_seam_rejects_degenerate_and_malformed_input():
    # n <= 1, non-positive mean/sd, and missing keys must not raise; return empty.
    assert numeric_effect_from_group_stats({"mean": 2.0, "sd": 0.4, "n": 1},
                                           {"mean": 1.0, "sd": 0.3, "n": 6}).effect is None
    assert numeric_effect_from_group_stats({"mean": 0.0, "sd": 0.4, "n": 6},
                                           {"mean": 1.0, "sd": 0.3, "n": 6}).effect is None
    assert numeric_effect_from_group_stats({"mean": 2.0, "n": 6},
                                           {"mean": 1.0, "sd": 0.3, "n": 6}).effect is None


def test_group_stats_seam_propagates_timepoint():
    r = numeric_effect_from_group_stats(
        {"mean": 2.0, "sd": 0.4, "n": 6},
        {"mean": 1.0, "sd": 0.3, "n": 6},
        outcome="proliferation",
        timepoint="day 7",
    )
    assert r.context.get("effect_timepoint") == "day 7"
