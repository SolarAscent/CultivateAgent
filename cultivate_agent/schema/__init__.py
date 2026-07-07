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

__all__ = [
    # evidence
    "Evidence", "Confidence", "NullCode", "INFERENCE_PREFIX", "is_inference",
    # extraction
    "PaperExtraction", "SchemaBlock", "BLOCKS", "CONTROLLED_VOCAB",
    "block_model", "normalize_controlled", "schema_for_prompt",
    # paper
    "PaperRef", "PaperMetadata", "PaperPaths", "IngestStatus", "slugify",
]
