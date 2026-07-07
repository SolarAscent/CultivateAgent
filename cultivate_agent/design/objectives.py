"""Objectives, weights, context, and the actionable-variable whitelist.

Design decision from the project record: **multi-objective but single-factor
(medium-centered)**. Objectives are a FIXED set; users choose weights, not new
objectives. The agent may *read* any context (cell type, scaffold, species) but
may only *act* on medium variables. This module encodes and enforces that so the
scope cannot silently explode.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# The four fixed objectives (record's wording; "tissue_readiness" deliberately
# replaces the looser "big chunk of meat" goal).
OBJECTIVES: List[str] = ["proliferation", "cost", "differentiation_retention", "tissue_readiness"]

# Metrics associated with each objective (surfaced to the LLM and to the user).
OBJECTIVE_METRICS: Dict[str, List[str]] = {
    "proliferation": ["viable cell density", "proliferation rate", "doubling time", "cell viability"],
    "cost": ["cost per unit volume", "cost per cell", "growth-factor / recombinant-protein usage"],
    "differentiation_retention": ["MYOD", "MYOG", "MYH", "fusion index", "myotube formation"],
    "tissue_readiness": ["3D viability", "stress tolerance", "ECM/adhesion support", "hypoxia-related risk"],
}

# The ONLY variables the design agent may propose changing.
DEFAULT_ACTIONABLE_VARIABLES: List[str] = [
    "basal_medium", "serum_level", "growth_factors", "small_molecules",
    "amino_acids", "glucose", "lipids", "vitamins", "trace_elements",
    "albumin_substitute", "ITS", "hydrolysates_or_extracts",
    "medium_change_or_feed_strategy",
]


class ObjectiveWeights(BaseModel):
    """Normalized weights over the fixed objective set."""

    weights: Dict[str, float]

    @field_validator("weights")
    @classmethod
    def _check(cls, v: Dict[str, float]) -> Dict[str, float]:
        bad = set(v) - set(OBJECTIVES)
        if bad:
            raise ValueError(f"unknown objective(s): {sorted(bad)}; allowed: {OBJECTIVES}")
        if any(w < 0 for w in v.values()):
            raise ValueError("weights must be non-negative")
        if sum(v.values()) <= 0:
            raise ValueError("at least one objective weight must be > 0")
        return v

    @property
    def normalized(self) -> Dict[str, float]:
        total = sum(self.weights.values())
        return {k: round(w / total, 4) for k, w in self.weights.items()}

    def describe(self) -> str:
        return ", ".join(f"{k}={w}" for k, w in sorted(self.normalized.items(), key=lambda t: -t[1]))

    @classmethod
    def from_preset(cls, presets: Dict[str, Dict[str, float]], name: str) -> "ObjectiveWeights":
        if name not in presets:
            raise KeyError(f"unknown preset '{name}'; available: {list(presets)}")
        return cls(weights=dict(presets[name]))


class DesignContext(BaseModel):
    """Read-only constraints. The agent conditions on these but cannot change them."""

    cell_type: Optional[str] = None          # e.g. "bovine satellite cells"
    species: Optional[str] = None            # e.g. "bovine"
    stage: Optional[str] = Field(None, description="expansion | differentiation | both")
    scaffold: Optional[str] = None           # e.g. "gelatin-alginate hydrogel"
    target_product_type: Optional[str] = None
    starting_medium: Optional[str] = None    # current formulation to improve on
    notes: Optional[str] = None

    def describe(self) -> str:
        parts = []
        for k in ("cell_type", "species", "stage", "scaffold", "target_product_type", "starting_medium", "notes"):
            v = getattr(self, k)
            if v:
                parts.append(f"{k}: {v}")
        return "; ".join(parts) if parts else "(no specific context provided)"
