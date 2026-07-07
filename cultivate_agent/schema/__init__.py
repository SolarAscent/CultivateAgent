"""Typed schema layer: paper records, folder layout, and the A-M extraction schema."""

from .evidence import Confidence, Evidence, NullCode, INFERENCE_PREFIX, is_inference
from .extraction import (
    BLOCKS,
    CONTROLLED_VOCAB,
    PaperExtraction,
    SchemaBlock,
    block_model,
    normalize_controlled,
    schema_for_prompt,
)
from .paper import (
    IngestStatus,
    PaperMetadata,
    PaperPaths,
    PaperRef,
    slugify,
)
from .structured_paper import (
    PaperFigure,
    PaperParagraph,
    PaperSection,
    PaperTable,
    StructuredPaper,
    structured_paper_from_grobid_tei_path,
    structured_paper_from_grobid_tei_xml,
    structured_paper_from_text,
)

__all__ = [
    # evidence
    "Evidence", "Confidence", "NullCode", "INFERENCE_PREFIX", "is_inference",
    # extraction
    "PaperExtraction", "SchemaBlock", "BLOCKS", "CONTROLLED_VOCAB",
    "block_model", "normalize_controlled", "schema_for_prompt",
    # paper
    "PaperRef", "PaperMetadata", "PaperPaths", "IngestStatus", "slugify",
    # structured paper
    "PaperParagraph", "PaperSection", "PaperTable", "PaperFigure",
    "StructuredPaper", "structured_paper_from_text",
    "structured_paper_from_grobid_tei_xml", "structured_paper_from_grobid_tei_path",
]
