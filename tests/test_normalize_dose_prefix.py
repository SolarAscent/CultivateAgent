"""Leading-dose stripping so dose-labelled component variants pool (raise k).

"5% FBS-PSFC" and "2% FBS-PSFC" are the same component at different doses; they
must canonicalize to one key so evidence pools instead of splitting k. The strip
must NOT fire on names that merely start with a number ("2i", "M199", "5-HT").
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cultivate_agent.normalize import ComponentNormalizer

ONTOLOGY = Path(__file__).resolve().parents[1] / "config" / "ontology"


@pytest.fixture(scope="module")
def norm():
    return ComponentNormalizer(ONTOLOGY)


def test_percent_dose_variants_pool(norm):
    a = norm.canonicalize("5% FBS-PSFC").canonical
    b = norm.canonicalize("2% FBS-PSFC").canonical
    assert a == b                      # same component, dose stripped
    assert "%" not in a


def test_concentration_prefix_reaches_ontology_alias(norm):
    # "5 ng/mL bFGF" -> "bFGF" -> FGF2 (alias hit after the dose is stripped).
    assert norm.canonicalize("5 ng/mL bFGF").canonical == "FGF2"


def test_percent_prefix_matches_bare_component(norm):
    assert norm.canonicalize("20% FBS").canonical == norm.canonicalize("FBS").canonical


@pytest.mark.parametrize("name", ["2i", "M199", "5-HT", "18-crown-6", "3T3"])
def test_number_starting_names_are_not_stripped(norm, name):
    # No unit+space after the leading number, so identity is preserved.
    assert norm.canonicalize(name).canonical == name


def test_plain_canonical_unaffected(norm):
    assert norm.canonicalize("FGF2").canonical == "FGF2"
    assert norm.canonicalize("bFGF").canonical == "FGF2"
