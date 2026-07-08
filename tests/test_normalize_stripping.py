"""Qualifier-stripping canonicalization + cross-context pooling (from the corpus run)."""

from __future__ import annotations

from pathlib import Path

ONTOLOGY = Path(__file__).resolve().parents[1] / "config" / "ontology"


def test_canonicalize_strips_parenthetical_qualifier_to_ontology():
    from cultivate_agent.normalize import ComponentNormalizer

    norm = ComponentNormalizer(ONTOLOGY)
    m = norm.canonicalize("FGF2 (immobilized in affibody hydrogels)")
    assert m.canonical == "FGF2"                 # base matches the ontology
    assert m.matched_via in ("stripped", "alias", "exact")


def test_verbose_variants_pool_to_same_canonical():
    from cultivate_agent.normalize import ComponentNormalizer

    norm = ComponentNormalizer(ONTOLOGY)
    a = norm.canonicalize("Mystery reagent X (at 10 ng/mL)").canonical
    b = norm.canonicalize("Mystery reagent X (high dose)").canonical
    assert a == b == "Mystery reagent X"         # unknown component still pools by stripped base


def test_synthesize_pools_across_context_by_default():
    from cultivate_agent.evidence import EvidenceItem, synthesize

    # Same component + outcome, different contexts -> should pool (k=2), not split.
    items = [
        EvidenceItem("FGF2", "proliferation", "p1", direction=1, context={"species": "bovine"}),
        EvidenceItem("FGF2", "proliferation", "p2", direction=1, context={"species": "human"}),
    ]
    out = synthesize(items)
    assert len(out) == 1 and out[0].k == 2

    # Explicit subgroup analysis still splits when asked.
    assert len(synthesize(items, by_context=True)) == 2
