"""Hierarchical evidence synthesis: pool heterogeneous literature into priors."""

from .effect_operator import extract_effects
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
]
