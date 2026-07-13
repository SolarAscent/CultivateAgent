"""Hierarchical evidence synthesis: pool heterogeneous literature into priors."""

from .effect_operator import extract_effects
from .audit import (
    EvidenceAudit,
    ComponentAudit,
    audit_effect_items,
    load_effect_items_json,
    write_evidence_audit_markdown,
)
from .review_packet import build_review_packet, write_review_packet_markdown
from .adjudication import (
    ALLOWED_DECISIONS,
    AdjudicationStatus,
    ValidationIssue,
    ValidationResult,
    summarize_adjudication_worksheet,
    format_adjudication_status_markdown,
    write_adjudication_status_markdown,
    validate_adjudication_worksheet,
    build_adjudication_passage_previews,
    format_adjudication_passages_markdown,
    write_adjudication_passages_markdown,
    export_adjudicated_evidence,
    count_evidence_rows,
    write_adjudication_template,
    write_validation_markdown,
)
from .meta_analysis import (
    EvidenceItem,
    EvidenceSummary,
    beta_binomial_direction,
    dersimonian_laird,
    meta_analyze,
    synthesize,
)
from .tables import (
    ResolvedGroupStatistics,
    TableCellPointer,
    TableCellRole,
    TableEffectPointers,
    TableNumericEffect,
    TablePointerError,
    numeric_effect_from_table_pointers,
    parse_cell_number,
    validate_table_pointers,
)

__all__ = [
    "EvidenceItem", "EvidenceSummary",
    "meta_analyze", "synthesize", "dersimonian_laird", "beta_binomial_direction",
    "extract_effects",
    "EvidenceAudit", "ComponentAudit", "audit_effect_items", "load_effect_items_json",
    "write_evidence_audit_markdown",
    "build_review_packet", "write_review_packet_markdown",
    "ALLOWED_DECISIONS", "AdjudicationStatus", "ValidationIssue", "ValidationResult",
    "summarize_adjudication_worksheet", "format_adjudication_status_markdown",
    "write_adjudication_status_markdown",
    "write_adjudication_template", "validate_adjudication_worksheet",
    "build_adjudication_passage_previews", "format_adjudication_passages_markdown",
    "write_adjudication_passages_markdown",
    "export_adjudicated_evidence", "count_evidence_rows",
    "write_validation_markdown",
    "TableCellRole", "TableCellPointer", "TableEffectPointers",
    "ResolvedGroupStatistics", "TableNumericEffect", "TablePointerError",
    "parse_cell_number", "validate_table_pointers", "numeric_effect_from_table_pointers",
]
