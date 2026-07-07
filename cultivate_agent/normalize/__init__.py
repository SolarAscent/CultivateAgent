"""Normalization: ontology-backed component canonicalization + unit parsing."""

from .components import ComponentMatch, ComponentNormalizer
from .units import Quantity, extract_quantities, normalize_time_to_hours, parse_quantity

__all__ = [
    "ComponentNormalizer", "ComponentMatch",
    "Quantity", "parse_quantity", "extract_quantities", "normalize_time_to_hours",
]
