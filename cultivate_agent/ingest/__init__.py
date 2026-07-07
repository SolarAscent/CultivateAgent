"""Ingestion: BibTeX parsing, PDF processing, and per-paper folder building."""

from .bibtex import parse_bibtex
from .grobid import (
    GrobidError,
    grobid_is_alive,
    process_fulltext_document,
    structured_paper_from_grobid_pdf,
    write_fulltext_tei,
)
from .organize import IngestResult, ingest_library, ingest_paper, iter_ingested
from ..schema.structured_paper import (
    structured_paper_from_grobid_tei_path,
    structured_paper_from_grobid_tei_xml,
    structured_paper_from_text,
)

__all__ = [
    "parse_bibtex", "ingest_paper", "ingest_library", "iter_ingested",
    "IngestResult", "structured_paper_from_text",
    "structured_paper_from_grobid_tei_xml", "structured_paper_from_grobid_tei_path",
    "GrobidError", "grobid_is_alive", "process_fulltext_document",
    "write_fulltext_tei", "structured_paper_from_grobid_pdf",
]
