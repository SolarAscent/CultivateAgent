import hashlib
import json

import pytest

from cultivate_agent.evidence.visual_asset_readiness import extract_visual_asset_readiness


def _fixture(tmp_path):
    fitz = pytest.importorskip("fitz")
    paper_dir = tmp_path / "data/papers/paper"
    paper_dir.mkdir(parents=True)
    pdf_path = paper_dir / "paper.pdf"
    document = fitz.open()
    page = document.new_page(width=400, height=500)
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 30), False)
    pixmap.clear_with(180)
    pixmap.set_pixel(0, 0, (0, 0, 0))
    image_data = pixmap.tobytes("png")
    page.insert_image(fitz.Rect(40, 40, 360, 280), stream=image_data)
    caption = (
        "Fig. 1. Cell proliferation in treatment and control medium. Mean and standard "
        "deviation from n = 3 experiments."
    )
    page.insert_textbox(fitz.Rect(40, 300, 360, 380), caption, fontsize=9)
    page.insert_text((40, 450), "Creative Commons Attribution License (CC BY).", fontsize=8)
    document.save(pdf_path)
    document.close()
    pdf_sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()

    jats_path = paper_dir / "fulltext.xml"
    jats_path.write_text(
        "<article xmlns:xlink='http://www.w3.org/1999/xlink'>"
        "<fig id='F1'><label>Fig. 1</label><graphic xlink:href='figure1.png'/></fig>"
        "<supplementary-material id='S1'><media xlink:href='supp.pdf'/></supplementary-material>"
        "<supplementary-material id='S2'><media xlink:href='supp.pdf'/></supplementary-material>"
        "</article>",
        encoding="utf-8",
    )
    jats_sha = hashlib.sha256(jats_path.read_bytes()).hexdigest()
    corpus = [{"record_id": "R1", "doi": "10.1/example"}]
    audits = [{
        "record_id": "R1", "paper_id": "paper", "pdf_status": "audited",
        "pdf_path": str(pdf_path.relative_to(tmp_path)), "pdf_sha256": pdf_sha,
        "pages": "1",
    }]
    heldout = {
        "selector_version": "pdf-visual-stat-block-v1",
        "sources": [{
            "record_id": "R1", "pdf_path": audits[0]["pdf_path"],
            "pdf_sha256": pdf_sha,
        }],
        "candidates": [{"record_id": "R1", "pdf_page": 1}],
    }
    sources = [{
        "record_id": "R1", "paper_id": "paper", "doi": "10.1/example",
        "expected_license": "CC-BY-4.0",
    }]
    acquisitions = [{
        "record_id": "R1", "paper_id": "paper", "doi": "10.1/example",
        "status": "existing_verified", "license": "CC-BY-4.0",
        "source_sha256": jats_sha,
    }]
    return fitz, corpus, audits, heldout, sources, acquisitions


def test_extract_visual_assets_binds_pdf_jats_image_and_supplement_pointers(tmp_path):
    fitz, corpus, audits, heldout, sources, acquisitions = _fixture(tmp_path)
    source_rows, assets, supplements = extract_visual_asset_readiness(
        ["R1"], corpus_rows=corpus, pdf_audits=audits, heldout=heldout,
        jats_sources=sources, jats_acquisitions=acquisitions, repo_root=tmp_path,
        output_dir=tmp_path / "data/visual_assets/test", fitz_module=fitz,
    )
    assert source_rows[0]["status"] == "ready_for_visual_review"
    assert source_rows[0]["license_evidence"] == "verified_jats_registry"
    assert len(assets) == 1
    asset = assets[0]
    assert asset["candidate_class"] == "strict_group_stats_visual_candidate"
    assert asset["source_kind"] == "embedded_pdf_image"
    assert asset["image_color_count"] > 1
    assert asset["jats_figure_id"] == "F1"
    assert asset["jats_graphic_hrefs"] == "figure1.png"
    local_path = tmp_path / asset["local_asset_path"]
    assert local_path.is_file()
    assert hashlib.sha256(local_path.read_bytes()).hexdigest() == asset["image_sha256"]
    assert "cell proliferation" not in json.dumps(assets).casefold()
    assert supplements == [{
        "record_id": "R1", "doi": "10.1/example", "jats_source_sha256": acquisitions[0]["source_sha256"],
        "supplement_id": "S1", "href": "supp.pdf", "local_path": "",
        "local_sha256": "", "status": "referenced_not_local",
    }]


def test_extract_visual_assets_rejects_heldout_pdf_provenance_drift(tmp_path):
    fitz, corpus, audits, heldout, sources, acquisitions = _fixture(tmp_path)
    heldout["sources"][0]["pdf_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="provenance mismatch"):
        extract_visual_asset_readiness(
            ["R1"], corpus_rows=corpus, pdf_audits=audits, heldout=heldout,
            jats_sources=sources, jats_acquisitions=acquisitions, repo_root=tmp_path,
            output_dir=tmp_path / "data/visual_assets/test", fitz_module=fitz,
        )


def test_extract_visual_assets_rejects_jats_doi_drift(tmp_path):
    fitz, corpus, audits, heldout, sources, acquisitions = _fixture(tmp_path)
    acquisitions[0]["doi"] = "10.1/wrong"
    with pytest.raises(ValueError, match="JATS DOI mismatch"):
        extract_visual_asset_readiness(
            ["R1"], corpus_rows=corpus, pdf_audits=audits, heldout=heldout,
            jats_sources=sources, jats_acquisitions=acquisitions, repo_root=tmp_path,
            output_dir=tmp_path / "data/visual_assets/test", fitz_module=fitz,
        )
