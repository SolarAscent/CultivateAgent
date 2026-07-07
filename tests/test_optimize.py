"""Offline tests for the multi-objective optimization layer (numpy only)."""

from __future__ import annotations

import json

import numpy as np
import pytest


# --------------------------------------------------------------------------- #
# Pareto / hypervolume                                                        #
# --------------------------------------------------------------------------- #
def test_pareto_and_hypervolume():
    from cultivate_agent.optimize import hypervolume, non_dominated_mask, pareto_front

    Y = np.array([[1.0, 4.0], [3.0, 2.0], [4.0, 4.5]])  # 3rd dominated by (3,2)
    assert non_dominated_mask(Y).tolist() == [True, True, False]
    assert set(pareto_front(Y).tolist()) == {0, 1}
    assert hypervolume(Y[:2], np.array([5.0, 5.0])) == pytest.approx(8.0)
    # 3D unit box, single point at origin
    assert hypervolume(np.array([[0.0, 0.0, 0.0]]), np.array([1.0, 1.0, 1.0])) == pytest.approx(1.0, abs=0.05)


# --------------------------------------------------------------------------- #
# Design space                                                                #
# --------------------------------------------------------------------------- #
def test_space_encode_decode_roundtrip():
    from cultivate_agent.optimize import default_medium_space

    space = default_medium_space()
    f = {"basal_medium": "DMEM/F12", "FBS": 5.0, "FGF2": 20.0, "IGF-1": 0.0,
         "recombinant-albumin": 0.8, "ITS": True, "Y-27632": 0.0, "soy-protein-hydrolysate": 0.0}
    dec = space.decode(space.encode(f))
    assert dec["basal_medium"] == "DMEM/F12"
    assert dec["FBS"] == pytest.approx(5.0, abs=0.01)
    assert dec["ITS"] is True
    # samples are valid one-hots / in range
    for s in space.sample(5, seed=1):
        assert s["basal_medium"] in ["DMEM", "DMEM/F12", "Ham's F-10", "B8"]
        assert 0 <= s["FGF2"] <= 100


def test_space_from_kb(tmp_path):
    from cultivate_agent.kb import KnowledgeBase
    from cultivate_agent.normalize import ComponentNormalizer
    from cultivate_agent.optimize import space_from_kb
    from cultivate_agent.schema.extraction import MediumInfo, PaperExtraction
    from cultivate_agent.schema.paper import PaperRef

    ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
    kb = KnowledgeBase(tmp_path / "kb.sqlite", normalizer=ComponentNormalizer(ROOT / "config" / "ontology"))
    ext = PaperExtraction(paper_id="p1")
    ext.medium_info = MediumInfo(growth_factors=["bFGF"], basal_medium=["DMEM/F12"])
    kb.upsert_paper(PaperRef(paper_id="p1", title="t"))
    kb.upsert_extraction(ext)
    space = space_from_kb(kb)
    names = [p.name for p in space.parameters]
    assert "FGF2" in names          # canonicalized from bFGF, promoted into the space
    assert "basal_medium" in names
    kb.close()


# --------------------------------------------------------------------------- #
# Surrogate                                                                   #
# --------------------------------------------------------------------------- #
def test_gp_fits_training_points():
    from cultivate_agent.optimize.surrogate import GaussianProcess

    rng = np.random.default_rng(0)
    X = rng.random((12, 3))
    y = np.sin(X.sum(axis=1) * 3)
    gp = GaussianProcess(noise=1e-6).fit(X, y)
    mu, std = gp.predict(X)
    assert np.mean(np.abs(mu - y)) < 0.05          # interpolates training data
    assert np.all(std >= 0)


# --------------------------------------------------------------------------- #
# MOBO loop                                                                   #
# --------------------------------------------------------------------------- #
def test_mobo_cold_start_and_convergence():
    from cultivate_agent.optimize import MultiObjectiveBO, SyntheticMediumObjective, default_medium_space

    space = default_medium_space()
    obj = SyntheticMediumObjective(noise=0.0)
    mobo = MultiObjectiveBO(space, obj.objectives, backend="gp", seed=0)

    # cold start -> space-filling
    first = mobo.ask(4)
    assert all(s.source == "space-filling" for s in first)

    init = space.sample(6, seed=0)
    mobo.tell(init, obj.evaluate_many(init))
    hv0 = mobo.hypervolume()
    for _ in range(4):
        sugg = mobo.ask(4, pool_size=400, preference_weights={"proliferation": 0.6, "cost": 0.4})
        assert all(s.source in ("bo", "llm") for s in sugg)
        mobo.tell([s.formulation for s in sugg], obj.evaluate_many([s.formulation for s in sugg]))
    # hypervolume is monotonically non-decreasing (we keep all observations)
    assert mobo.hypervolume() >= hv0
    assert len(mobo.pareto()) >= 3


# --------------------------------------------------------------------------- #
# LLM-guided MOBO integration                                                 #
# --------------------------------------------------------------------------- #
def test_candidate_to_formulation_mapping():
    from cultivate_agent.design.recommender import MediumCandidate, VariableChange
    from cultivate_agent.optimize import MultiObjectiveBO, default_medium_space
    from cultivate_agent.optimize.llm_mobo import EvidenceGuidedMOBO

    space = default_medium_space()
    mobo = MultiObjectiveBO(space, __import__("cultivate_agent.optimize", fromlist=["SyntheticMediumObjective"]).SyntheticMediumObjective().objectives)
    egm = EvidenceGuidedMOBO(mobo, recommender=None)

    cand = MediumCandidate(name="c", changes=[
        VariableChange(variable="serum_level", change="reduce FBS to 2%", cited_paper_ids=["p1"]),
        VariableChange(variable="growth_factors", change="add FGF2 at 20 ng/mL", cited_paper_ids=["p2"]),
    ])
    form = egm._candidate_to_formulation(cand)
    assert form.get("FBS") == pytest.approx(2.0)
    assert form.get("FGF2") == pytest.approx(20.0)


def test_evidence_guided_mobo_end_to_end():
    from cultivate_agent.design import DesignContext, MediumRecommender, ObjectiveWeights
    from cultivate_agent.llm import get_client
    from cultivate_agent.optimize import (
        EvidenceGuidedMOBO,
        MultiObjectiveBO,
        SyntheticMediumObjective,
        default_medium_space,
    )
    from cultivate_agent.retrieve import BM25Retriever, Document

    design = json.dumps({"candidates": [{
        "name": "serum-reduced + FGF2",
        "summary": "reduce serum, add FGF2",
        "changes": [
            {"variable": "serum_level", "change": "reduce FBS to 2%", "cited_paper_ids": ["p1"]},
            {"variable": "growth_factors", "change": "add FGF2 at 20 ng/mL", "cited_paper_ids": ["p1"]},
        ],
        "cited_paper_ids": ["p1"],
    }]})
    client = get_client("mock", "m", responses=[design])
    retr = BM25Retriever()
    retr.index([Document("p1", "serum-free FGF2 bovine proliferation medium", "Serum-free medium")])
    recommender = MediumRecommender(client, retr)

    space = default_medium_space()
    obj = SyntheticMediumObjective()
    mobo = MultiObjectiveBO(space, obj.objectives, seed=0)
    init = space.sample(6, seed=0)
    mobo.tell(init, obj.evaluate_many(init))

    egm = EvidenceGuidedMOBO(mobo, recommender)
    proposal = egm.propose(
        ObjectiveWeights(weights={"proliferation": 0.6, "cost": 0.4}),
        DesignContext(cell_type="bovine satellite cells"),
        batch_size=4,
    )
    assert len(proposal.batch) == 4
    assert proposal.n_observed == 6
    assert len(proposal.evidence) >= 1          # retrieval surfaced the paper
    assert any(c for c in proposal.llm_caveats)  # guardrail caveat present


def test_botorch_backend_demo_path_if_available():
    pytest.importorskip("torch")
    pytest.importorskip("botorch")
    pytest.importorskip("gpytorch")

    from cultivate_agent.optimize import MultiObjectiveBO, SyntheticMediumObjective, default_medium_space

    space = default_medium_space()
    obj = SyntheticMediumObjective(noise=0.0)
    mobo = MultiObjectiveBO(space, obj.objectives, backend="botorch", seed=0)
    init = space.sample(6, seed=0)
    mobo.tell(init, obj.evaluate_many(init))
    sugg = mobo.ask(2, pool_size=32, preference_weights={"proliferation": 0.6, "cost": 0.4})
    assert len(sugg) == 2
    assert all(s.note == "qNEHVI" for s in sugg)
