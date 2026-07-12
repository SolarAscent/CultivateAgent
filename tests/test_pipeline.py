"""Offline unit + integration tests. No API key required (uses the mock client)."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import sys
import threading
import types

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
    assert norm.canonicalize("serum-free base medium").canonical == "SFB"
    assert norm.canonicalize("Beefy R").canonical == "Beefy-R"
    assert norm.canonicalize("Grifola frondosa extract").canonical == "Grifola-frondosa-extract"
    assert norm.canonicalize("APE").canonical == "Auxenochlorella-pyrenoidosa-protein-extract"
    assert norm.canonicalize("rapeseed protein isolates").canonical == "rapeseed-protein-isolate"
    assert norm.canonicalize("copper ions").canonical == "copper-ions"
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


def test_openai_compatible_client_passes_extra_body(monkeypatch):
    from cultivate_agent.llm import get_client

    class FakeOpenAI:
        last_instance = None

        def __init__(self, **kwargs):
            self.init_kwargs = kwargs
            self.calls = []
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=self.create))
            FakeOpenAI.last_instance = self

        def create(self, **kwargs):
            self.calls.append(kwargs)
            message = types.SimpleNamespace(content='{"ok": true}')
            choice = types.SimpleNamespace(message=message)
            usage = types.SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2)
            return types.SimpleNamespace(choices=[choice], usage=usage)

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = get_client(
        "openai",
        "deepseek-v4-flash",
        base_url="https://api.deepseek.com",
        extra_body={"thinking": {"type": "disabled"}},
    )
    assert client.chat("system", "user") == '{"ok": true}'
    call = FakeOpenAI.last_instance.calls[0]
    assert call["model"] == "deepseek-v4-flash"
    assert call["extra_body"] == {"thinking": {"type": "disabled"}}


def test_llm_client_does_not_retry_auth_errors(monkeypatch):
    from cultivate_agent.llm.base import LLMClient, LLMError, Message

    class AuthError(RuntimeError):
        status_code = 401

    class FailingClient(LLMClient):
        def __init__(self):
            super().__init__("m", max_retries=4)
            self.calls = 0

        def _raw_complete(self, messages, **kwargs):
            self.calls += 1
            raise AuthError("Authentication Fails, Your api key: test-token is invalid")

    monkeypatch.setattr("time.sleep", lambda _seconds: None)
    client = FailingClient()
    with pytest.raises(LLMError) as err:
        client.complete([Message("user", "hello")])
    assert client.calls == 1
    assert "Non-retryable" in str(err.value)
    assert "test-token" not in str(err.value)


def test_llm_client_retries_transient_errors(monkeypatch):
    from cultivate_agent.llm.base import LLMClient, LLMError, Message

    class TransientError(RuntimeError):
        status_code = 503

    class FailingClient(LLMClient):
        def __init__(self):
            super().__init__("m", max_retries=3)
            self.calls = 0

        def _raw_complete(self, messages, **kwargs):
            self.calls += 1
            raise TransientError("server overloaded")

    monkeypatch.setattr("time.sleep", lambda _seconds: None)
    client = FailingClient()
    with pytest.raises(LLMError) as err:
        client.complete([Message("user", "hello")])
    assert client.calls == 3
    assert "after 3 attempts" in str(err.value)


def test_extract_id_resolution_maps_review_and_source_ids(tmp_path):
    from cultivate_agent.cli import _expand_review_ids, _resolve_extract_paper_ids
    from cultivate_agent.config import Config
    from cultivate_agent.ingest import iter_ingested
    from cultivate_agent.schema.paper import PaperMetadata, PaperPaths, PaperRef

    papers = tmp_path / "papers"
    ref = PaperRef(
        paper_id="paper-alpha",
        title="Defined bovine satellite cell medium",
        doi="10.123/example",
    )
    paths = PaperPaths(papers, ref.paper_id, slug=ref.slug).ensure()
    paths.fulltext.write_text("Bovine cells in serum-free medium.", encoding="utf-8")
    paths.save_metadata(PaperMetadata(ref=ref, triage_category="A"))

    manifest = tmp_path / "manifest.tsv"
    manifest.write_text(
        "record_id\ttitle\tdoi\tyear\tspecies\tcell_type\tstage\tmedium_focus\tendpoints\n"
        "R001\tDefined bovine satellite cell medium\t10.123/example\t2026\tbovine"
        "\tsatellite cells\texpansion\tserum-free medium\tproliferation\n",
        encoding="utf-8",
    )
    queue = tmp_path / "queue.tsv"
    queue.write_text(
        "review_id\tpriority\tsource_record_id\tevidence_topic\tfield_to_verify\thuman_question"
        "\tdecision_impact\tsuggested_action\tstatus\n"
        "H001\tP1\tR001\tMedium dose\tmedium; dose\tDoes the paper report medium dose?"
        "\tSearch-space seed\tCheck methods/results\topen\n",
        encoding="utf-8",
    )

    cfg = Config()
    cfg.root = str(tmp_path)
    ingested = list(iter_ingested(papers))
    assert _expand_review_ids("H001-H003,my-paper-slug") == ["H001", "H002", "H003", "my-paper-slug"]
    assert _resolve_extract_paper_ids("H001", cfg, ingested, review_queue=str(queue), manifest=str(manifest)) == {
        "paper-alpha"
    }
    assert _resolve_extract_paper_ids("R001", cfg, ingested, review_queue=str(queue), manifest=str(manifest)) == {
        "paper-alpha"
    }
    assert _resolve_extract_paper_ids("paper-alpha", cfg, ingested, review_queue=str(queue), manifest=str(manifest)) == {
        "paper-alpha"
    }


def test_total_operator_call_failure_is_not_success():
    from cultivate_agent.cli import _is_total_operator_call_failure

    failed = types.SimpleNamespace(extraction_meta={
        "mode": "operators",
        "operators": [
            {"operator": "context", "status": "call_error"},
            {"operator": "medium", "status": "call_error"},
        ],
    })
    partial = types.SimpleNamespace(extraction_meta={
        "mode": "operators",
        "operators": [
            {"operator": "context", "status": "ok"},
            {"operator": "medium", "status": "call_error"},
        ],
    })
    blocks = types.SimpleNamespace(extraction_meta={"mode": "blocks"})

    assert _is_total_operator_call_failure(failed) is True
    assert _is_total_operator_call_failure(partial) is False
    assert _is_total_operator_call_failure(blocks) is False


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


def test_structured_paper_from_grobid_tei_xml():
    from cultivate_agent.schema import structured_paper_from_grobid_tei_xml

    tei = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt><title level="a">Bovine medium paper</title></titleStmt>
    </fileDesc>
    <profileDesc>
      <abstract><p>We report a serum-free bovine myoblast medium.</p></abstract>
    </profileDesc>
  </teiHeader>
  <text>
    <body>
      <div>
        <head>Materials and Methods</head>
        <p>Cells were cultured in DMEM/F12 with FGF2.</p>
        <p>The formulation used recombinant albumin.</p>
      </div>
      <div>
        <head>Results</head>
        <p>Proliferation increased over six days.</p>
      </div>
      <figure type="table">
        <head>Table 1</head>
        <figDesc>Medium component concentrations.</figDesc>
      </figure>
      <figure>
        <head>Figure 1</head>
        <figDesc>Growth curve.</figDesc>
      </figure>
    </body>
  </text>
</TEI>"""
    paper = structured_paper_from_grobid_tei_xml("tei-1", tei)
    assert paper.source == "grobid_tei"
    assert paper.title == "Bovine medium paper"
    assert paper.abstract and "serum-free" in paper.abstract
    assert [s.title for s in paper.sections] == ["Materials and Methods", "Results"]
    assert paper.sections[0].paragraphs[0].paragraph_id == "S1.p1"
    assert paper.tables and "Medium component" in (paper.tables[0].caption or "")
    assert paper.figures and "Growth curve" in (paper.figures[0].caption or "")


def test_structured_paper_from_jats_xml_routes_nested_sections():
    from cultivate_agent.schema import structured_paper_from_grobid_tei_xml

    xml = """<?xml version="1.0" encoding="UTF-8"?>
<article>
  <front>
    <article-meta>
      <title-group><article-title>JATS bovine medium paper</article-title></title-group>
      <abstract><p>We optimized bovine satellite cell proliferation media.</p></abstract>
    </article-meta>
  </front>
  <body>
    <sec id="intro"><title>1. Introduction</title><p>Medium composition matters.</p></sec>
    <sec id="methods"><title>2. Materials and Methods</title>
      <sec id="media"><title>2.2. Selection of the Components of the Tested Media</title>
        <p>Cells were cultured in DMEM with bFGF at 10 ng/mL and bovine serum.</p>
      </sec>
    </sec>
    <sec id="results"><title>3. Results</title>
      <p>Proliferation increased under bFGF conditions.</p>
    </sec>
    <table-wrap id="t1"><label>Table 1</label>
      <caption><p>Media compositions for bovine satellite cells.</p></caption>
      <table><tbody><tr><td>DMEM and 10 ng/mL bFGF</td></tr></tbody></table>
    </table-wrap>
    <fig id="f1"><label>Figure 1</label><caption><p>Growth curve.</p></caption></fig>
  </body>
</article>"""
    paper = structured_paper_from_grobid_tei_xml("jats-1", xml)
    assert paper.source == "jats_xml"
    assert paper.title == "JATS bovine medium paper"
    assert paper.abstract and "proliferation media" in paper.abstract
    assert any("Materials and Methods" in s.title for s in paper.sections)
    assert any("Selection of the Components" in s.title for s in paper.sections)
    assert paper.section_passages(["materials and methods", "results"])
    assert paper.tables and "10 ng/mL bFGF" in (paper.tables[0].caption or "")
    assert paper.figures and "Growth curve" in (paper.figures[0].caption or "")


def test_grobid_client_writes_and_parses_tei(tmp_path):
    from cultivate_agent.ingest import (
        process_fulltext_document,
        structured_paper_from_grobid_pdf,
        write_fulltext_tei,
    )

    tei = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <text><body><div><head>Methods</head><p>Cells used DMEM/F12.</p></div></body></text>
</TEI>"""
    seen = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            seen["path"] = self.path
            length = int(self.headers["Content-Length"])
            body = self.rfile.read(length)
            seen["body"] = body
            self.send_response(200)
            self.send_header("Content-Type", "application/xml")
            self.end_headers()
            self.wfile.write(tei.encode("utf-8"))

        def log_message(self, *args):  # noqa: D102
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\nfake test pdf")

    try:
        text = process_fulltext_document(pdf, base_url=base_url, timeout=5)
        out = write_fulltext_tei(pdf, tmp_path / "fulltext.xml", base_url=base_url, timeout=5)
        paper = structured_paper_from_grobid_pdf("p-grobid", pdf, base_url=base_url, timeout=5)
    finally:
        server.shutdown()
        server.server_close()

    assert seen["path"] == "/api/processFulltextDocument"
    assert b'name="input"; filename="paper.pdf"' in seen["body"]
    assert b'name="consolidateHeader"' in seen["body"]
    assert "DMEM/F12" in text
    assert out.read_text(encoding="utf-8") == tei
    assert paper.source == "grobid_tei"
    assert paper.sections[0].title == "Methods"


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


def test_extraction_eval_corpus_counts_missing_and_unexpected_records():
    from cultivate_agent.evaluate import evaluate_corpus
    from cultivate_agent.schema.extraction import MediumInfo, PaperExtraction

    gold_a = PaperExtraction(paper_id="a")
    gold_a.medium_info = MediumInfo(serum_free_status="serum-free")
    gold_b = PaperExtraction(paper_id="b")
    gold_b.medium_info = MediumInfo(growth_factors=["FGF2"])
    pred_a = PaperExtraction(paper_id="a")
    pred_a.medium_info = MediumInfo(serum_free_status="serum-free")
    pred_extra = PaperExtraction(paper_id="extra")

    report = evaluate_corpus([pred_a, pred_extra], [gold_a, gold_b])

    assert report.n_papers == 2
    assert report.overall() == {
        "tp": 1, "fp": 0, "fn": 1, "precision": 1.0, "recall": 0.5, "f1": 0.6667
    }
    assert report.alignment() == {
        "expected": 2,
        "predicted": 2,
        "matched": 1,
        "coverage": 0.5,
        "missing_prediction_ids": ["b"],
        "unexpected_prediction_ids": ["extra"],
    }
    assert report.coverage() == {
        "gold_populated_field_cells": 2,
        "predicted_gold_field_cells": 1,
        "gold_field_presence_rate": 0.5,
        "substantive_predicted_field_cells": 1,
        "evidence_attached_field_cells": 0,
        "evidence_attachment_rate": 0.0,
        "unverified_evidence_field_cells": 0,
    }


def test_extraction_eval_corpus_rejects_duplicate_ids():
    import pytest

    from cultivate_agent.evaluate import evaluate_corpus
    from cultivate_agent.schema.extraction import PaperExtraction

    duplicate_predictions = [PaperExtraction(paper_id="p"), PaperExtraction(paper_id="p")]
    with pytest.raises(ValueError, match="duplicate prediction paper_id.*p"):
        evaluate_corpus(duplicate_predictions, [PaperExtraction(paper_id="p")])

    duplicate_gold = [PaperExtraction(paper_id="g"), PaperExtraction(paper_id="g")]
    with pytest.raises(ValueError, match="duplicate gold paper_id.*g"):
        evaluate_corpus([], duplicate_gold)


def test_extraction_eval_reports_substantive_evidence_attachment():
    from cultivate_agent.evaluate import evaluate_corpus
    from cultivate_agent.schema.evidence import Evidence
    from cultivate_agent.schema.extraction import FastTriage, MediumInfo, PaperExtraction

    gold = PaperExtraction(paper_id="p")
    gold.fast_triage = FastTriage(main_track="medium")
    gold.medium_info = MediumInfo(serum_free_status="serum-free")
    pred = PaperExtraction(paper_id="p")
    pred.fast_triage = FastTriage(main_track="medium")
    pred.medium_info = MediumInfo(serum_free_status="serum-free")
    pred.evidence = {
        "B.main_track": Evidence(quote="This study optimizes the culture medium."),
        "E.serum_free_status": Evidence(
            quote="Cells were maintained in serum-free medium.",
            location="Results [UNVERIFIED: quote not found in source]",
        ),
    }

    coverage = evaluate_corpus([pred], [gold]).coverage()

    assert coverage["gold_field_presence_rate"] == 1.0
    assert coverage["substantive_predicted_field_cells"] == 2
    assert coverage["evidence_attachment_rate"] == 1.0
    assert coverage["unverified_evidence_field_cells"] == 1


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
