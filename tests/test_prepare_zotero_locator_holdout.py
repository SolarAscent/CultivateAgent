from __future__ import annotations

import pytest

from scripts.prepare_zotero_locator_holdout import verify_pdf


class FakePage:
    def __init__(self, text):
        self.text = text

    def get_text(self):
        return self.text


class FakeDocument:
    page_count = 1

    def __init__(self, text, title=""):
        self.pages = [FakePage(text)]
        self.metadata = {"title": title}

    def __iter__(self):
        return iter(self.pages)

    def close(self):
        return None


class FakeFitz:
    text = ""
    title = ""

    @classmethod
    def open(cls, path):
        return FakeDocument(cls.text, cls.title)


def test_verify_pdf_requires_title_doi_and_explicit_cc_by(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"pdf")
    title = "Bovine Satellite Cell Medium Study"
    FakeFitz.title = title
    FakeFitz.text = (
        "doi: 10.1234/example. This article is distributed under the Creative Commons "
        "Attribution (CC BY) license (https://creativecommons.org/licenses/by/4.0/)."
    )

    pdf_hash, pages = verify_pdf(
        pdf, doi="10.1234/example", title=title, expected_license="CC-BY-4.0",
        fitz_module=FakeFitz,
    )

    assert len(pdf_hash) == 64
    assert pages == 1


def test_verify_pdf_rejects_identity_or_license_mismatch(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"pdf")
    FakeFitz.title = "Different paper"
    FakeFitz.text = "doi: 10.1234/wrong. All rights reserved."

    with pytest.raises(ValueError, match="title mismatch"):
        verify_pdf(
            pdf, doi="10.1234/example", title="Expected title",
            expected_license="CC-BY-4.0", fitz_module=FakeFitz,
        )
