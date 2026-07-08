"""Tests for hierarchical evidence synthesis (offline, numpy + mock LLM)."""

from __future__ import annotations

import json

import pytest


def test_dersimonian_laird_identical_studies():
    from cultivate_agent.evidence import dersimonian_laird

    pooled, var, tau2, i2, Q = dersimonian_laird([0.5, 0.5, 0.5], [0.1, 0.1, 0.1])
    assert pooled == pytest.approx(0.5)
    assert tau2 == pytest.approx(0.0) and i2 == pytest.approx(0.0) and Q == pytest.approx(0.0)


def test_concordant_evidence_is_confident():
    from cultivate_agent.evidence import EvidenceItem, meta_analyze

    items = [EvidenceItem("FGF2", "proliferation", f"p{i}", effect=e, variance=0.05)
             for i, e in enumerate([0.8, 0.9, 0.75])]
    s = meta_analyze(items)
    assert s.method == "random_effects_DL"
    assert s.p_beneficial > 0.95
    assert s.i_squared is not None and s.i_squared < 0.5
    assert s.context_dependent is False
    assert s.ci_low > 0                      # CI excludes zero -> real signal


def test_conflicting_evidence_is_flagged_context_dependent():
    from cultivate_agent.evidence import EvidenceItem, meta_analyze

    items = [
        EvidenceItem("serum", "proliferation", "p1", effect=1.2, variance=0.05),
        EvidenceItem("serum", "proliferation", "p2", effect=-1.0, variance=0.05),
        EvidenceItem("serum", "proliferation", "p3", effect=1.1, variance=0.05),
        EvidenceItem("serum", "proliferation", "p4", effect=-0.9, variance=0.05),
    ]
    s = meta_analyze(items)
    assert s.i_squared > 0.5                 # substantial heterogeneity
    assert s.context_dependent is True
    assert 0.35 < s.p_beneficial < 0.65      # honest uncertainty, not a fake confident call
    assert s.ci_low < 0 < s.ci_high          # CI spans zero
    assert "context-dependent" in s.note


def test_beta_binomial_direction_only():
    from cultivate_agent.evidence import EvidenceItem, meta_analyze

    items = [EvidenceItem("soy-hydrolysate", "proliferation", f"p{i}", direction=d)
             for i, d in enumerate([1, 1, 1, -1])]
    s = meta_analyze(items)
    assert s.method == "beta_binomial"
    assert s.p_beneficial == pytest.approx(4 / 6, abs=1e-3)   # (1+3)/(2+4)


def test_synthesize_groups_and_ranks():
    from cultivate_agent.evidence import EvidenceItem, synthesize

    items = [
        EvidenceItem("FGF2", "proliferation", "p1", effect=0.9, variance=0.05),
        EvidenceItem("FGF2", "proliferation", "p2", effect=0.8, variance=0.05),
        EvidenceItem("IGF-1", "proliferation", "p1", direction=1),
    ]
    out = synthesize(items)
    comps = {s.component for s in out}
    assert comps == {"FGF2", "IGF-1"}
    # FGF2 (2 concordant quantitative studies) should rank above IGF-1 (1 direction vote)
    assert out[0].component == "FGF2"


def test_kb_evidence_roundtrip_and_prior(tmp_path):
    from cultivate_agent.evidence import EvidenceItem, synthesize
    from cultivate_agent.kb import KnowledgeBase
    from cultivate_agent.optimize import EvidencePrior, default_medium_space

    items = [EvidenceItem("FGF2", "proliferation", f"p{i}", effect=e, variance=0.05)
             for i, e in enumerate([0.8, 0.9])]
    items += [EvidenceItem("FBS", "proliferation", "p1", direction=-1),
              EvidenceItem("FBS", "proliferation", "p2", direction=-1)]
    kb = KnowledgeBase(tmp_path / "kb.sqlite")
    kb.upsert_evidence_summaries(synthesize(items))
    back = {s.component: s for s in kb.get_evidence_summaries(outcome="proliferation")}
    assert back["FGF2"].p_beneficial == pytest.approx(1.0, abs=0.05)
    assert back["FBS"].p_beneficial < 0.5

    prior = EvidencePrior.from_kb(kb, default_medium_space(), "proliferation")
    by = {b.parameter: b for b in prior.raw_beliefs}
    assert by["FGF2"].direction == 1 and by["FBS"].direction == -1
    kb.close()


def test_extract_effects_drops_ungrounded(monkeypatch):
    from cultivate_agent.evidence import extract_effects
    from cultivate_agent.llm import get_client
    from cultivate_agent.schema.paper import PaperRef

    text = "FGF2 at 20 ng/mL increased bovine satellite cell proliferation over 5 passages."
    payload = json.dumps({"evidence": [
        {"component": "FGF2", "direction": 1, "context": {"species": "bovine"},
         "quote": "FGF2 at 20 ng/mL increased bovine satellite cell proliferation"},   # grounded
        {"component": "IGF-1", "direction": 1, "context": {},
         "quote": "IGF-1 tripled the growth rate"},                                     # NOT in text -> dropped
    ]})
    client = get_client("mock", "m", responses=[payload])
    items = extract_effects(client, PaperRef(paper_id="p1", title="t"), text, "proliferation")
    comps = [it.component for it in items]
    assert comps == ["FGF2"]                 # ungrounded IGF-1 claim dropped
    assert items[0].context.get("species") == "bovine"


def test_evidence_audit_blocks_until_human_review_and_filters_process_items(tmp_path):
    from cultivate_agent.evidence import EvidenceItem, audit_effect_items, write_evidence_audit_markdown

    items = [
        EvidenceItem(
            "FGF2 20 ng/mL", "proliferation", "p1", direction=1,
            context={"species": "bovine", "cell_type": "satellite cells", "stage": "expansion"},
            quote="FGF2 at 20 ng/mL increased bovine satellite cell proliferation.",
        ),
        EvidenceItem(
            "Matrigel 0.5 mg/mL", "proliferation", "p2", direction=1,
            context={"species": "bovine", "cell_type": "myoblasts", "stage": "proliferation"},
            quote="0.5 mg/mL Matrigel improved engraftment.",
        ),
        EvidenceItem(
            "soy hydrolysate", "proliferation", "p3", direction=1,
            context={"species": "mouse", "cell_type": "C2C12", "stage": "growth"},
            quote="soy hydrolysate increased C2C12 growth.",
        ),
    ]
    review = tmp_path / "review.tsv"
    review.write_text(
        "review_id\tpriority\tstatus\n"
        "H001\tP1\topen\n"
        "H017\tP2\topen\n",
        encoding="utf-8",
    )
    audit = audit_effect_items(items, human_review_path=review, min_candidates=1)
    assert audit.decision == "NO-GO"
    assert audit.human_open_critical == 1
    assert [c.component for c in audit.ai_review_candidates] == ["FGF2 20 ng/mL"]
    by_component = {c.component: c for c in audit.components}
    assert "not_medium_only" in by_component["Matrigel 0.5 mg/mL"].flags
    assert "indirect_species_or_cell" in by_component["soy hydrolysate"].flags

    out = write_evidence_audit_markdown(audit, tmp_path / "audit.md")
    text = out.read_text(encoding="utf-8")
    assert "Wet-lab entry gate: NO-GO" in text
    assert "FGF2 20 ng/mL" in text


def test_review_packet_builds_locators_without_adjudicating(tmp_path):
    from cultivate_agent.evidence import build_review_packet, write_review_packet_markdown
    from cultivate_agent.schema.paper import IngestStatus, PaperMetadata, PaperPaths, PaperRef

    papers = tmp_path / "papers"
    paths = PaperPaths(papers, "p1", slug="beefy").ensure()
    text = (
        "Simple serum-free medium for bovine satellite cells.\n\n"
        "Beefy-9 contains recombinant albumin and supported proliferation over seven passages. "
        "FGF2 at 20 ng/mL was used in the expansion medium.\n\n"
        "Differentiation markers included PAX7 and MYOD after expansion."
    )
    paths.fulltext.write_text(text, encoding="utf-8")
    meta = PaperMetadata(
        ref=PaperRef(
            paper_id="p1",
            title="Simple and effective serum-free medium for sustained expansion of bovine satellite cells",
        ),
        status=IngestStatus(has_fulltext=True, fulltext_chars=len(text)),
    )
    paths.save_metadata(meta)

    manifest = tmp_path / "manifest.tsv"
    manifest.write_text(
        "record_id\ttitle\tmedium_focus\tendpoints\n"
        "R015\tSimple and effective serum-free medium for sustained expansion of bovine satellite cells\t"
        "Beefy-9; albumin; FGF2\tproliferation; passages\n",
        encoding="utf-8",
    )
    queue = tmp_path / "queue.tsv"
    queue.write_text(
        "review_id\tpriority\tsource_record_id\tevidence_topic\tfield_to_verify\t"
        "human_question\tdecision_impact\tsuggested_action\tstatus\n"
        "H001\tP1\tR015\tBeefy-9 expansion benchmark\tpassages\t"
        "What passages and proliferation claims are supported?\tcontrol\t"
        "Extract formulation and passage claims.\topen\n",
        encoding="utf-8",
    )

    packet = build_review_packet(
        review_queue_path=queue,
        manifest_path=manifest,
        papers_dir=papers,
        review_ids=["H001"],
        top_k=2,
        path_base=tmp_path,
    )
    assert packet[0].status == "ready_for_human_review"
    assert packet[0].fulltext_path.startswith("papers/")
    assert not packet[0].fulltext_path.startswith("/")
    assert packet[0].hits
    assert packet[0].hits[0].start < packet[0].hits[0].end
    assert packet[0].hits[0].fulltext_path == packet[0].fulltext_path

    out = write_review_packet_markdown(packet, tmp_path / "packet.md")
    rendered = out.read_text(encoding="utf-8")
    assert "candidate passage locators" in rendered
    assert "decision: supported" not in rendered.lower()  # no AI adjudication label


def test_adjudication_template_and_validation(tmp_path):
    from cultivate_agent.evidence import (
        count_evidence_rows,
        export_adjudicated_evidence,
        summarize_adjudication_worksheet,
        validate_adjudication_worksheet,
        write_adjudication_template,
    )
    from cultivate_agent.schema.paper import IngestStatus, PaperMetadata, PaperPaths, PaperRef

    papers = tmp_path / "papers"
    paths = PaperPaths(papers, "p1", slug="paper-one").ensure()
    text = (
        "Defined bovine medium benchmark.\n\n"
        "The tested medium used FGF2 at 10 ng/mL and supported bovine satellite "
        "cell proliferation over six days."
    )
    paths.fulltext.write_text(text, encoding="utf-8")
    paths.save_metadata(PaperMetadata(
        ref=PaperRef(paper_id="p1", title="Defined bovine medium benchmark"),
        status=IngestStatus(has_fulltext=True, fulltext_chars=len(text)),
    ))

    manifest = tmp_path / "manifest.tsv"
    manifest.write_text(
        "record_id\ttitle\tmedium_focus\tendpoints\n"
        "R001\tDefined bovine medium benchmark\tFGF2; serum-free\tproliferation\n",
        encoding="utf-8",
    )
    queue = tmp_path / "queue.tsv"
    queue.write_text(
        "review_id\tpriority\tsource_record_id\tevidence_topic\tfield_to_verify\t"
        "human_question\tdecision_impact\tsuggested_action\tstatus\n"
        "H001\tP1\tR001\tFGF2 dose check\tbFGF_dose\t"
        "What dose was tested?\tsearch-space\tExtract dose and endpoint.\topen\n",
        encoding="utf-8",
    )

    worksheet = write_adjudication_template(
        review_queue_path=queue,
        manifest_path=manifest,
        papers_dir=papers,
        review_ids=["H001"],
        out_path=tmp_path / "worksheet.tsv",
        path_base=tmp_path,
    )
    text = worksheet.read_text(encoding="utf-8")
    assert "\tdecision\t" in text
    assert "\tsupported\t" not in text
    assert "\tpapers/paper-one/fulltext.txt\t" in text

    # Blank decisions are allowed while the worksheet is still awaiting human review.
    assert validate_adjudication_worksheet(worksheet).ok
    blank_status = summarize_adjudication_worksheet(worksheet)
    assert blank_status.rows == 1
    assert blank_status.blank == 1
    assert blank_status.evidence_bearing == 0
    assert not blank_status.ready_for_export
    empty_export = export_adjudicated_evidence(
        worksheet_path=worksheet,
        out_path=tmp_path / "empty_evidence.tsv",
    )
    assert count_evidence_rows(empty_export) == 0

    lines = text.splitlines()
    header = lines[0].split("\t")
    row = lines[1].split("\t")
    row[header.index("decision")] = "supported"
    row[header.index("selected_range")] = row[header.index("suggested_ranges")].split(";")[0]
    row[header.index("key_finding")] = "FGF2 dose supported proliferation"
    row[header.index("dose_or_range")] = "10 ng/mL"
    row[header.index("endpoint")] = "proliferation"
    row[header.index("wetlab_use")] = "range_seed"
    worksheet.write_text("\n".join([lines[0], "\t".join(row)]) + "\n", encoding="utf-8")
    result = validate_adjudication_worksheet(worksheet)
    assert result.ok
    supported_status = summarize_adjudication_worksheet(worksheet)
    assert supported_status.blank == 0
    assert supported_status.evidence_bearing == 1
    assert supported_status.ready_for_export
    try:
        write_adjudication_template(
            review_queue_path=queue,
            manifest_path=manifest,
            papers_dir=papers,
            review_ids=["H001"],
            out_path=worksheet,
            path_base=tmp_path,
        )
    except FileExistsError as exc:
        assert "already contains human decisions" in str(exc)
    else:
        raise AssertionError("expected template overwrite guard")
    write_adjudication_template(
        review_queue_path=queue,
        manifest_path=manifest,
        papers_dir=papers,
        review_ids=["H001"],
        out_path=worksheet,
        path_base=tmp_path,
        force_overwrite=True,
    )
    backups = sorted(tmp_path.glob("worksheet.tsv.bak.*"))
    assert len(backups) == 1
    assert "FGF2 dose supported proliferation" in backups[0].read_text(encoding="utf-8")
    assert summarize_adjudication_worksheet(worksheet).blank == 1

    # Recreate the supported row for export/validation checks below.
    lines = worksheet.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    row = lines[1].split("\t")
    row[header.index("decision")] = "supported"
    row[header.index("selected_range")] = row[header.index("suggested_ranges")].split(";")[0]
    row[header.index("key_finding")] = "FGF2 dose supported proliferation"
    row[header.index("dose_or_range")] = "10 ng/mL"
    row[header.index("endpoint")] = "proliferation"
    row[header.index("wetlab_use")] = "range_seed"
    worksheet.write_text("\n".join([lines[0], "\t".join(row)]) + "\n", encoding="utf-8")
    evidence = export_adjudicated_evidence(
        worksheet_path=worksheet,
        out_path=tmp_path / "evidence.tsv",
    )
    assert count_evidence_rows(evidence) == 1
    rendered = evidence.read_text(encoding="utf-8")
    assert "FGF2 dose supported proliferation" in rendered
    assert "human_reviewed" in rendered

    row[header.index("decision")] = "maybe"
    worksheet.write_text("\n".join([lines[0], "\t".join(row)]) + "\n", encoding="utf-8")
    result = validate_adjudication_worksheet(worksheet)
    assert not result.ok
    assert any(i.field == "decision" for i in result.issues)


def test_adjudication_passage_preview_resolves_relative_paths(tmp_path):
    from cultivate_agent.evidence import (
        build_adjudication_passage_previews,
        format_adjudication_passages_markdown,
    )

    papers = tmp_path / "papers" / "paper-one"
    papers.mkdir(parents=True)
    fulltext = papers / "fulltext.txt"
    text = (
        "Defined bovine medium benchmark.\n\n"
        "The tested medium used FGF2 at 10 ng/mL and supported bovine satellite "
        "cell proliferation over six days."
    )
    fulltext.write_text(text, encoding="utf-8")
    start = text.index("FGF2")
    end = len(text)
    worksheet = tmp_path / "worksheet.tsv"
    worksheet.write_text(
        "review_id\tsource_record_id\tstatus\tdecision\treviewer\treview_date\t"
        "fulltext_path\tsuggested_ranges\tselected_range\tkey_finding\t"
        "formulation_or_variable\tdose_or_range\tendpoint\tcell_context\t"
        "limitations\twetlab_use\tnotes\n"
        f"H001\tR001\tready_for_human_review\t\t\t\tpapers/paper-one/fulltext.txt\t"
        f"0-10;{start}-{end}\t{start}-{end}\t\t\t\t\t\t\t\t\n",
        encoding="utf-8",
    )

    previews = build_adjudication_passage_previews(
        worksheet,
        review_ids=["H001"],
        path_base=tmp_path,
        context_chars=90,
    )
    assert len(previews) == 1
    assert previews[0].status == "ok"
    assert previews[0].range_text == f"{start}-{end}"
    assert "FGF2 at 10 ng/mL" in previews[0].excerpt

    rendered = format_adjudication_passages_markdown(previews)
    assert "not an AI adjudication decision" in rendered
    assert "FGF2 at 10 ng/mL" in rendered
