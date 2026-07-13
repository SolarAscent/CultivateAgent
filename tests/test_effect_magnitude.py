"""Guards against fabricated effect magnitudes in the numeric inference.

The magnitude inferrer parses proportional phrasing out of a *verified* quote.
The risk is that a number appearing in the quote is a concentration ("30% FBS")
or a dispersion ("2.2 ± 0.4-fold"), not an effect size. Those must NOT become a
log-response-ratio; the item stays direction-only instead.
"""

from __future__ import annotations

import math

from cultivate_agent.evidence.effect_operator import _infer_log_response_ratio as infer


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
