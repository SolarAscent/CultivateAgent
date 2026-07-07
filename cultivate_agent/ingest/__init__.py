"""Ingestion: BibTeX parsing, PDF processing, and per-paper folder building."""

from .bibtex import parse_bibtex
from .organize import IngestResult, ingest_library, ingest_paper, iter_ingested

__all__ = ["parse_bibtex", "ingest_paper", "ingest_library", "iter_ingested", "IngestResult"]
