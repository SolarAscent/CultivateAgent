"""Evidence-grounded schema extraction."""

from .extractor import extract_blocks, extract_paper
from .operators import (
    OPERATORS,
    ComponentDoseRecord,
    ExtractionOperator,
    OperatorExtractor,
    run_operator,
)
from .readiness import (
    PaperReadiness,
    build_extraction_readiness,
    write_extraction_readiness_markdown,
    write_extraction_readiness_tsv,
)

__all__ = [
    "extract_paper", "extract_blocks",
    "OperatorExtractor", "ExtractionOperator", "ComponentDoseRecord", "OPERATORS", "run_operator",
    "PaperReadiness", "build_extraction_readiness",
    "write_extraction_readiness_markdown", "write_extraction_readiness_tsv",
]
