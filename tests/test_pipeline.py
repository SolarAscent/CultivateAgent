"""Offline unit + integration tests. No API key required (uses the mock client)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "config" / "ontology"


# --------------------------------------------------------------------------- #
# Schema                                                                      #
# --------------------------------------------------------------------------- #
def test_schema_controlled_vocab_normalization():
    from cultivate_agent.schema.extraction import MediumInfo, normalize_controlled

    assert normalize_controlled("serum_free_status", "Serum-Free") == "serum-free"
    assert normalize_controlled("serum_usage", "NR") == "NR"           # null code passes
    assert normalize_controlled("serum_usage", "INF: reduced").startswith("INF:")
    m = MediumInfo(serum_free_status="SERUM-FREE")
    assert m.serum_free_status == "serum-free"


def test_schema_prompt_lists_allowed_values():
    from cultivate_agent.schema.extraction import schema_for_prompt

    guide = schema_for_prompt(["E"])
    assert "serum_free_status" in guide and "choose one of" in guide


def test_evidence_verification():
    from cultivate_agent.schema.evidence import Evidence

    src = "Basal medium was DMEM/F12 and cells were expanded serum-free."
    assert Evidence(quote="Basal medium was DMEM/F12").verify_against(src)
    assert not Evidence(quote="RPMI-1640 with 10% serum").verify_against(src)


# --------------------------------------------------------------------------- #
# Normalization                                                               #
# --------------------------------------------------------------------------- #
def test_component_canonicalization():
    from cultivate_agent.normalize import ComponentNormalizer

    norm = ComponentNormalizer(ONTOLOGY)
    assert norm.canonicalize("bFGF").canonical == "FGF2"
    assert norm.canonicalize("basic FGF").canonical == "FGF2"
    assert norm.canonicalize("fetal bovine serum").canonical == "FBS"
    assert norm.canonicalize("totally unknown reagent").matched_via == "none"


def test_unit_parsing_preserves_original():
    from cultivate_agent.normalize import parse_quantity

    q = parse_quantity("66-75 g")
    assert q.original == "66-75 g" and q.value_range == (66.0, 75.0)
    t = parse_quantity("39 h")
    assert t.dimension == "time" and t.normalized_value == pytest.approx(39.0) and t.comparable
    m = parse_quantity("30 minutes")
    assert m.normalized_value == pytest.approx(0.5)
    c = parse_quantity("0.8 mg/mL")
    assert c.dimension == "concentration" and c.comparable is False  # not falsely comparable


# --------------------------------------------------------------------------- #
# LLM plumbing                                                                #
# --------------------------------------------------------------------------- #
def test_extract_json_robustness():
    from cultivate_agent.llm import extract_json

    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('prefix {"a": [1,2]} suffix') == {"a": [1, 2]}


def test_extraction_with_mock_and_grounding():
    from cultivate_agent.extract import extract_paper
    from cultivate_agent.llm import get_client
    from cultivate_agent.schema.paper import PaperRef

    payload = json.dumps({
        "blocks": {"E": {"basal_medium": ["DMEM/F12"], "serum_free_status": "serum-free"}},
        "evidence": {
            "E.basal_medium": {"quote": "Basal medium was DMEM/F12", "location": "Methods", "confidence": "high"},
            "E.serum_free_status": {"quote": "cells were expanded serum-free", "location": "Methods", "confidence": "high"},
        },
    })
    # full=True so the deep block E (medium) is extracted (2 passes -> 2 responses).
    client = get_client("mock", "m", responses=[payload, payload])
    ref = PaperRef(paper_id="p1", title="t")
    text = "Basal medium was DMEM/F12 and cells were expanded serum-free."
    ext = extract_paper(client, ref, text, full=True, verify_evidence=True)
    assert ext.medium_info.serum_free_status == "serum-free"
    assert ext.medium_info.basal_medium == ["DMEM/F12"]
    meta = ext.extraction_meta["passes"][0]
    assert meta["grounding_rate"] == 1.0  # both quotes verified


def test_extraction_flags_unverified_quote():
    from cultivate_agent.extract import extract_paper
    from cultivate_agent.llm import get_client
    from cultivate_agent.schema.paper import PaperRef

    payload = json.dumps({
        "blocks": {"E": {"serum_free_status": "serum-free"}},
        "evidence": {"E.serum_free_status": {"quote": "this text is not in the source at all", "confidence": "high"}},
    })
    client = get_client("mock", "m", responses=[payload])
    ext = extract_paper(client, PaperRef(paper_id="p2"), "real source text about DMEM", full=False)
    ev = ext.evidence["E.serum_free_status"]
    assert "UNVERIFIED" in (ev.location or "")


def test_extraction_accepts_schema_attribute_block_names():
    from cultivate_agent.extract import extract_paper
    from cultivate_agent.llm import get_client
    from cultivate_agent.schema.paper import PaperRef

    payload = json.dumps({
        "blocks": {
            "medium_info": {"serum_free_status": "serum-free"},
            "fast_triage": {"main_track": "medium"},
        },
        "evidence": {
            "medium_info.serum_free_status": {"quote": "serum-free expansion", "confidence": "high"},
            "fast_triage.main_track": {"quote": "culture medium optimization", "confidence": "high"},
        },
    })
    client = get_client("mock", "m", responses=[payload])
    text = "The paper reports culture medium optimization for serum-free expansion."
    ext = extract_paper(client, PaperRef(paper_id="p3"), text, triage_blocks=["B", "E"], full=False)
    assert ext.fast_triage.main_track == "medium"
    assert ext.medium_info.serum_free_status == "serum-free"
    assert "E.serum_free_status" in ext.evidence
    assert "B.main_track" in ext.evidence


def test_structured_paper_from_text_sections():
    from cultivate_agent.schema import structured_paper_from_text

    text = """Title line

Abstract
We optimize bovine myoblast expansion medium.

Materials and Methods
Cells were cultured in DMEM/F12 with FGF2.

Results
The serum-free condition supported proliferation."""
    paper = structured_paper_from_text("p-structured", text, title="Title line")
    assert paper.abstract and "bovine myoblast" in paper.abstract
    titles = [s.title.lower() for s in paper.sections]
    assert any("materials and methods" in t for t in titles)
    assert any("results" in t for t in titles)
    assert paper.all_text().count("DMEM/F12") == 1


def test_extraction_uses_structured_section_routing():
    from cultivate_agent.extract import extract_paper
    from cultivate_agent.llm import get_client
    from cultivate_agent.schema import structured_paper_from_text
    from cultivate_agent.schema.paper import PaperRef

    payload = json.dumps({
        "blocks": {"E": {"basal_medium": ["DMEM/F12"], "serum_free_status": "serum-free"}},
        "evidence": {
            "E.basal_medium": {"quote": "DMEM/F12 with FGF2", "confidence": "high"},
            "E.serum_free_status": {"quote": "serum-free medium", "confidence": "high"},
        },
    })
    text = """Abstract
This work studies bovine cells.

Methods
The cells were cultured in serum-free medium based on DMEM/F12 with FGF2.

Discussion
The method supports future medium optimization."""
    paper = structured_paper_from_text("p4", text)
    client = get_client("mock", "m", responses=[payload])
    ext = extract_paper(
        client,
        PaperRef(paper_id="p4"),
        text,
        triage_blocks=["E"],
        full=False,
        structured_paper=paper,
    )
    meta = ext.extraction_meta["passes"][0]
    assert ext.medium_info.basal_medium == ["DMEM/F12"]
    assert meta["used_section_routing"] is True
    assert meta["routed_section_ids"]
    assert meta["structured_source"] == "plain_text"


# --------------------------------------------------------------------------- #
# Knowledge base + retrieval                                                  #
# --------------------------------------------------------------------------- #
def test_kb_roundtrip_and_flatten(tmp_path):
    from cultivate_agent.kb import KnowledgeBase
    from cultivate_agent.normalize import ComponentNormalizer
    from cultivate_agent.schema.extraction import MediumInfo, PaperExtraction
    from cultivate_agent.schema.paper import PaperRef

    ext = PaperExtraction(paper_id="p1")
    ext.medium_info = MediumInfo(growth_factors=["bFGF"], basal_medium=["DMEM/F12"], serum_free_status="serum-free")
    kb = KnowledgeBase(tmp_path / "kb.sqlite", normalizer=ComponentNormalizer(ONTOLOGY))
    kb.upsert_paper(PaperRef(paper_id="p1", title="t"))
    kb.upsert_extraction(ext)
    assert kb.stats()["medium_components"] == 2
    assert "p1" in kb.papers_with_component("FGF2")   # canonicalized in the flatten step
    assert "p1" in kb.papers_with_component("FGF2", role="growth_factor")
    assert kb.get_extraction("p1").medium_info.serum_free_status == "serum-free"
    kb.close()


def test_retriever_returns_relevant_doc():
    from cultivate_agent.retrieve import BM25Retriever, Document

    r = BM25Retriever()
    r.index([
        Document("a", "serum-free medium FGF2 bovine satellite cells proliferation", "A"),
        Document("b", "scaffold gelatin alginate 3D printing texture", "B"),
    ])
    hits = r.search("serum-free FGF2 proliferation", top_k=2)
    assert hits and hits[0].doc_id == "a"


def test_embedding_retriever_handles_semantic_mismatch():
    from cultivate_agent.retrieve import BM25Retriever, Document, EmbeddingRetriever

    docs = [
        Document("a", "serum-free FGF2 bovine satellite cell proliferation medium", "A"),
        Document("b", "alginate scaffold texture printing mechanics", "B"),
    ]
    query = "animal-component-free cattle myoblast expansion with mitogens"

    bm25 = BM25Retriever()
    bm25.index(docs)
    emb = EmbeddingRetriever(backend="local")
    emb.index(docs)

    assert bm25.search(query, top_k=2) == []
    hits = emb.search(query, top_k=2)
    assert hits and hits[0].doc_id == "a"


# --------------------------------------------------------------------------- #
# Design                                                                      #
# --------------------------------------------------------------------------- #
def test_objective_weights_validation_and_normalization():
    from cultivate_agent.design import ObjectiveWeights

    w = ObjectiveWeights(weights={"proliferation": 3, "cost": 1})
    assert w.normalized["proliferation"] == 0.75
    with pytest.raises(ValueError):
        ObjectiveWeights(weights={"not_an_objective": 1})


def test_recommender_enforces_actionable_whitelist():
    from cultivate_agent.design import DesignContext, MediumRecommender, ObjectiveWeights
    from cultivate_agent.llm import get_client
    from cultivate_agent.retrieve import BM25Retriever, Document

    design = json.dumps({"candidates": [{
        "name": "c", "changes": [
            {"variable": "serum_level", "change": "reduce"},
            {"variable": "scaffold", "change": "swap"},   # not actionable
        ],
    }]})
    client = get_client("mock", "m", responses=[design])
    r = BM25Retriever()
    r.index([Document("a", "serum-free medium proliferation", "A")])
    rec = MediumRecommender(client, r).recommend(
        ObjectiveWeights(weights={"proliferation": 1.0}), DesignContext()
    )
    changes = {c.variable: c.is_actionable for c in rec.candidates[0].changes}
    assert changes["serum_level"] is True and changes["scaffold"] is False


def test_recommender_verifier_downgrades_unsupported_citation():
    from cultivate_agent.design import DesignContext, MediumRecommender, ObjectiveWeights
    from cultivate_agent.llm import get_client
    from cultivate_agent.retrieve import BM25Retriever, Document

    design = json.dumps({"candidates": [{
        "name": "c", "changes": [
            {"variable": "growth_factors", "change": "add FGF2 at 20 ng/mL",
             "rationale": "FGF2 supports expansion", "cited_paper_ids": ["p1"]},
            {"variable": "small_molecules", "change": "add CHIR99021",
             "rationale": "Wnt activation", "cited_paper_ids": ["p1"]},
        ],
    }]})
    verification = json.dumps({
        "checks": [
            {"candidate_index": 1, "change_index": 1, "support": "supported", "reason": "FGF2 appears in evidence"},
            {"candidate_index": 1, "change_index": 2, "support": "unsupported", "reason": "CHIR99021 is absent from evidence"},
        ],
        "caveats": ["one unsupported claim"],
    })
    client = get_client("mock", "m", responses=[design, verification])
    r = BM25Retriever()
    r.index([Document("p1", "serum-free medium with FGF2 supports bovine proliferation", "A")])
    rec = MediumRecommender(client, r, verify_citations=True).recommend(
        ObjectiveWeights(weights={"proliferation": 1.0}), DesignContext(), n_candidates=1
    )

    changes = rec.candidates[0].changes
    assert changes[0].evidence_support == "supported"
    assert changes[1].evidence_support == "unsupported"
    assert "VERIFIER: unsupported" in changes[1].rationale
    assert any("downgraded" in c for c in rec.caveats)


# --------------------------------------------------------------------------- #
# Evaluation                                                                  #
# --------------------------------------------------------------------------- #
def test_extraction_eval_prf():
    from cultivate_agent.evaluate import evaluate_extraction
    from cultivate_agent.schema.extraction import MediumInfo, PaperExtraction

    gold = PaperExtraction(paper_id="p")
    gold.medium_info = MediumInfo(growth_factors=["FGF2", "IGF-1"], serum_free_status="serum-free")
    pred = PaperExtraction(paper_id="p")
    pred.medium_info = MediumInfo(growth_factors=["FGF2", "EGF"], serum_free_status="serum-free")

    rep = evaluate_extraction(pred, gold)
    overall = rep.overall()
    # growth_factors: TP=1 (FGF2), FP=1 (EGF), FN=1 (IGF-1); serum: TP=1
    assert overall["tp"] == 2 and overall["fp"] == 1 and overall["fn"] == 1


def test_bibtex_parsing(tmp_path):
    from cultivate_agent.ingest import parse_bibtex

    bib = tmp_path / "lib.bib"
    bib.write_text(
        "@article{stout2022,\n"
        "  title = {Serum-free B8 medium for bovine satellite cells},\n"
        "  author = {Stout, Andrew and Kaplan, David},\n"
        "  year = {2022},\n  journal = {Communications Biology},\n"
        "  doi = {10.1038/s42003-022-03423-8}\n}\n",
        encoding="utf-8",
    )
    refs = parse_bibtex(bib)
    assert len(refs) == 1
    assert refs[0].year == 2022 and refs[0].authors[0] == "Andrew Stout"
