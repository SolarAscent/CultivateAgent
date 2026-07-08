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
    ValidationIssue,
    ValidationResult,
    validate_adjudication_worksheet,
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

__all__ = [
    "EvidenceItem", "EvidenceSummary",
    "meta_analyze", "synthesize", "dersimonian_laird", "beta_binomial_direction",
    "extract_effects",
    "EvidenceAudit", "ComponentAudit", "audit_effect_items", "load_effect_items_json",
    "write_evidence_audit_markdown",
    "build_review_packet", "write_review_packet_markdown",
    "ALLOWED_DECISIONS", "ValidationIssue", "ValidationResult",
    "write_adjudication_template", "validate_adjudication_worksheet",
    "write_validation_markdown",
]
