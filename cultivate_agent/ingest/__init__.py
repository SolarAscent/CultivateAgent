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
from .europe_pmc import (
    EUROPE_PMC_REST,
    EuropePMCError,
    JATSAcquisition,
    acquire_europe_pmc_jats,
    fetch_europe_pmc_jats,
    inspect_europe_pmc_jats,
)
from .jats_materialize import JATSMaterialization, materialize_verified_jats
from .pdf_table_audit import (
    PDFTableAudit,
    PDFTableAuditError,
    TableStrategyAudit,
    audit_pdf_tables,
    is_stat_candidate,
)
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
    "EUROPE_PMC_REST", "EuropePMCError", "JATSAcquisition",
    "JATSMaterialization", "materialize_verified_jats",
    "inspect_europe_pmc_jats", "fetch_europe_pmc_jats", "acquire_europe_pmc_jats",
    "TableStrategyAudit", "PDFTableAudit", "PDFTableAuditError",
    "is_stat_candidate", "audit_pdf_tables",
]
