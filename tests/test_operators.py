"""Tests for operator-decomposition extraction (offline, mock LLM)."""

from __future__ import annotations

import json

import pytest

TEXT = (
    "Abstract\nWe developed a serum-free medium for bovine satellite cells.\n\n"
    "Methods\nBasal medium was DMEM/F12 with FGF2 at 20 ng/mL and recombinant albumin. "
    "Cells were bovine satellite cells expanded serum-free.\n\n"
    "Results\nProliferation was measured by cell counting; doubling time was 39 h. "
    "MYOD and MYOG expression confirmed myogenicity."
)


def _handler(msgs):
    u = msgs[-1].content
    if "Operator: context" in u:
        return json.dumps({"fields": {"B.main_track": "medium", "B.species": ["bovine"],
                                      "D.cell_type": ["satellite cells"],
                                      "D.culture_stage": ["expansion"]},
                           "evidence": {
                               "B.species": {"quote": "bovine satellite cells",
                                             "location": "Methods", "confidence": "high"},
                               "D.culture_stage": {"quote": "satellite cells expanded serum-free",
                                                   "location": "Methods", "confidence": "high"},
                           }})
    if "Operator: medium" in u:
        return json.dumps({"fields": {"E.basal_medium": ["DMEM/F12"], "E.serum_free_status": "serum-free",
                                      "E.medium_type": ["serum-free medium"],
                                      "E.growth_factors": ["FGF2", "recombinant albumin"]},
                           "evidence": {
                               "E.basal_medium": {"quote": "Basal medium was DMEM/F12",
                                                  "location": "Methods", "confidence": "high"},
                               "E.medium_type": {"quote": "serum-free medium",
                                                 "location": "Abstract", "confidence": "high"},
                           }})
    if "Operator: dose" in u:
        return json.dumps({
            "fields": {
                "J.has_extractable_quant_data": "yes",
                "J.extractable_variables": ["FGF2 concentration"],
                "J.key_numeric_results": ["FGF2 at 20 ng/mL"],
                "J.units_reported": ["ng/mL"],
            },
            "evidence": {},
            "dose_records": [{
                "component": "FGF2",
                "dose_or_range": "20 ng/mL",
                "unit": "ng/mL",
                "comparison_group": None,
                "endpoint": "proliferation",
                "evidence": {
                    "quote": "FGF2 at 20 ng/mL",
                    "location": "Methods",
                    "confidence": "high",
                },
            }],
        })
    if "Operator: endpoints" in u:
        return json.dumps({"fields": {"I.proliferation_metrics": ["cell counting", "doubling time"]},
                           "evidence": {}})
    if "Operator: findings" in u:
        return json.dumps({"fields": {"M.recommended_action": "must_extract_now"}, "evidence": {}})
    return "{}"


def test_operator_fields_are_disjoint():
    from cultivate_agent.extract import OPERATORS

    seen = set()
    for op in OPERATORS:
        for f in op.fields:
            assert f not in seen, f"field {f} owned by >1 operator"
            seen.add(f)


def test_operator_extractor_merges_and_grounds():
    from cultivate_agent.extract import OperatorExtractor
    from cultivate_agent.llm import get_client
    from cultivate_agent.schema.paper import PaperRef

    client = get_client("mock", "m", handler=_handler)
    ext = OperatorExtractor(client).extract(
        PaperRef(paper_id="p1", title="Serum-free bovine medium", year=2022), TEXT)

    assert ext.medium_info.serum_free_status == "serum-free"
    assert ext.medium_info.basal_medium == ["DMEM/F12"]
    assert ext.medium_info.medium_type == ["serum-free medium"]
    assert ext.fast_triage.species == ["bovine"]
    assert ext.cell_info.culture_stage == ["expansion"]
    assert ext.quant_data.has_extractable_quant_data == "yes"
    assert ext.final_judgment.recommended_action == "must_extract_now"

    meta = ext.extraction_meta
    assert meta["mode"] == "operators"
    assert len(meta["operators"]) == 5
    assert all(o["status"] == "ok" for o in meta["operators"])
    assert len(meta["dose_records"]) == 1
    assert meta["dose_records"][0]["grounded"] is True
    dose_meta = next(o for o in meta["operators"] if o["operator"] == "dose")
    assert dose_meta["grounded_dose_records"] == 1
    # grounded evidence (verified quotes) present
    assert "E.basal_medium" in ext.evidence
    assert "B.species" in ext.evidence


def test_operator_failure_is_diagnosable():
    """A single failing operator must not crash extraction; its status is recorded."""
    from cultivate_agent.extract import OperatorExtractor
    from cultivate_agent.llm import get_client
    from cultivate_agent.schema.paper import PaperRef

    def handler(msgs):
        u = msgs[-1].content
        if "Operator: medium" in u:
            return "not json at all"          # parse_error
        if "Operator: dose" in u:
            return json.dumps({"fields": {}})  # empty
        return _handler(msgs)

    client = get_client("mock", "m", handler=handler)
    ext = OperatorExtractor(client).extract(PaperRef(paper_id="p2", title="t"), TEXT)
    statuses = {o["operator"]: o["status"] for o in ext.extraction_meta["operators"]}
    assert statuses["medium"] == "parse_error"
    assert statuses["dose"] == "empty"
    assert statuses["context"] == "ok"        # other operators still succeed
    assert ext.fast_triage.species == ["bovine"]


def test_operator_flags_unverified_quote():
    from cultivate_agent.extract import OperatorExtractor
    from cultivate_agent.llm import get_client
    from cultivate_agent.schema.paper import PaperRef

    def handler(msgs):
        if "Operator: medium" in msgs[-1].content:
            return json.dumps({"fields": {"E.serum_free_status": "serum-free"},
                               "evidence": {"E.serum_free_status": {
                                   "quote": "this exact phrase is absent from the source text",
                                   "location": "Methods", "confidence": "high"}}})
        return "{}"

    client = get_client("mock", "m", handler=handler)
    ext = OperatorExtractor(client).extract(PaperRef(paper_id="p3", title="t"), TEXT)
    ev = ext.evidence["E.serum_free_status"]
    assert "UNVERIFIED" in (ev.location or "")


def test_operator_rejects_unsupported_component_dose_relation():
    from cultivate_agent.extract import OperatorExtractor
    from cultivate_agent.llm import get_client
    from cultivate_agent.schema.paper import PaperRef

    def handler(msgs):
        if "Operator: dose" in msgs[-1].content:
            return json.dumps({
                "fields": {"J.key_numeric_results": ["IGF-1 at 20 ng/mL"]},
                "evidence": {},
                "dose_records": [{
                    "component": "IGF-1",
                    "dose_or_range": "20 ng/mL",
                    "unit": "ng/mL",
                    "evidence": {
                        "quote": "FGF2 at 20 ng/mL",
                        "location": "Methods",
                        "confidence": "high",
                    },
                }],
            })
        return _handler(msgs)

    ext = OperatorExtractor(get_client("mock", "m", handler=handler)).extract(
        PaperRef(paper_id="p-dose", title="t"), TEXT
    )

    record = ext.extraction_meta["dose_records"][0]
    assert record["grounded"] is False
    assert "UNVERIFIED" in (record["evidence"]["location"] or "")


def test_operator_dose_relation_is_not_direct_when_verification_disabled():
    from cultivate_agent.extract import OperatorExtractor
    from cultivate_agent.llm import get_client
    from cultivate_agent.schema.paper import PaperRef

    ext = OperatorExtractor(
        get_client("mock", "m", handler=_handler), verify_evidence=False
    ).extract(PaperRef(paper_id="p-no-verify", title="t"), TEXT)

    record = ext.extraction_meta["dose_records"][0]
    assert record["grounded"] is False
    assert "verification disabled" in record["evidence"]["location"]


def test_extraction_readiness_reports_operator_context(tmp_path):
    from cultivate_agent.extract import (
        build_extraction_readiness,
        write_extraction_readiness_markdown,
        write_extraction_readiness_tsv,
    )
    from cultivate_agent.schema.paper import PaperMetadata, PaperPaths, PaperRef

    papers = tmp_path / "papers"
    ref = PaperRef(
        paper_id="p-ready",
        title="Defined bovine satellite cell medium",
        doi="10.123/example",
    )
    paths = PaperPaths(papers, ref.paper_id, slug=ref.slug).ensure()
    paths.fulltext.write_text(
        "Abstract\nSerum-free bovine satellite cell medium.\n\n"
        "Materials and methods\nCells were cultured in DMEM/F12 medium with FGF2 at 20 ng/ml "
        "and recombinant albumin supplement.\n\n"
        "Results\nProliferation was measured by cell counting. Doubling time was 39 h and "
        "MYOD differentiation was monitored.\n",
        encoding="utf-8",
    )
    paths.save_metadata(PaperMetadata(ref=ref))

    manifest = tmp_path / "manifest.tsv"
    manifest.write_text(
        "record_id\ttitle\tdoi\tyear\tspecies\tcell_type\tstage\tmedium_focus\tendpoints\n"
        "R001\tDefined bovine satellite cell medium\t10.123/example\t2026\tbovine\tsatellite cells"
        "\texpansion\tserum-free medium; FGF2\tproliferation\n",
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

    rows = build_extraction_readiness(
        review_queue_path=queue,
        manifest_path=manifest,
        papers_dir=papers,
        review_ids=["H001"],
        path_base=tmp_path,
    )
    assert len(rows) == 1
    assert rows[0].status == "ready_for_operator_extraction"
    assert rows[0].critical_ready == 3
    assert rows[0].fulltext_path.startswith("papers/")
    assert not rows[0].fulltext_path.startswith("/")
    assert {op.operator for op in rows[0].operators if op.ready} >= {"medium", "dose", "endpoints"}

    md = write_extraction_readiness_markdown(rows, tmp_path / "readiness.md")
    tsv = write_extraction_readiness_tsv(rows, tmp_path / "readiness.tsv")
    rendered = md.read_text(encoding="utf-8")
    assert "# Extraction Readiness: H001" in rendered
    assert "Ready for operator extraction" in rendered
    assert "ready_for_operator_extraction" in tsv.read_text(encoding="utf-8")


def test_extraction_readiness_distinguishes_fulltext_fallback():
    from cultivate_agent.extract.readiness import assess_operator_readiness
    from cultivate_agent.extract import OPERATORS
    from cultivate_agent.schema.structured_paper import structured_paper_from_text

    paper = structured_paper_from_text(
        "p-fallback",
        "No obvious headings here. Bovine satellite cells used DMEM medium with serum-free "
        "albumin supplement. FGF2 was tested at 20 ng/ml. Proliferation and doubling were "
        "reported by cell counting.",
        title="Fallback paper",
    )
    medium = next(op for op in OPERATORS if op.name == "medium")
    result = assess_operator_readiness(paper, medium)
    assert result.ready
    assert result.status == "fallback_ready"
