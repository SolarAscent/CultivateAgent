"""Quantity parsing that PRESERVES the original reporting.

The project record's critique correctly identifies outcome comparability as the
weakest link: a "2x proliferation" in one paper is not commensurable with a
"39 h doubling time" in another. We do not pretend to solve that. What we do:

* parse ``number [range] unit`` without ever discarding the original string,
* add an *optional* normalized view (e.g. time -> hours) as a separate field,
* explicitly flag when a value is NOT safely normalizable/comparable.

Downstream code should compare on ``normalized_*`` only within a single
``unit_dimension`` and should surface ``comparable=False`` to the user.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

_NUM = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"
_RANGE_RE = re.compile(rf"(?P<lo>{_NUM})\s*(?:-|–|—|to)\s*(?P<hi>{_NUM})\s*(?P<unit>[^\s,;]*)")
_SINGLE_RE = re.compile(rf"(?P<val>{_NUM})\s*(?P<unit>%|[^\s,;]*)")

# unit token -> (canonical unit, dimension, factor to canonical)
_TIME_TO_H = {"h": 1.0, "hr": 1.0, "hrs": 1.0, "hour": 1.0, "hours": 1.0,
              "min": 1 / 60, "mins": 1 / 60, "minute": 1 / 60, "minutes": 1 / 60,
              "d": 24.0, "day": 24.0, "days": 24.0, "week": 168.0, "weeks": 168.0}


@dataclass
class Quantity:
    original: str
    value: Optional[float] = None            # single value, or midpoint of a range
    value_range: Optional[Tuple[float, float]] = None
    unit: Optional[str] = None
    dimension: Optional[str] = None          # "time" | "percent" | "concentration" | None
    normalized_value: Optional[float] = None
    normalized_unit: Optional[str] = None
    comparable: bool = False                 # safe to compare across papers?
    note: str = ""

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        if self.value_range is not None:
            d["value_range"] = list(self.value_range)
        return d


def parse_quantity(text: str) -> Quantity:
    """Parse a single ``number[-range] unit`` string, preserving the original."""
    original = (text or "").strip()
    q = Quantity(original=original)
    if not original:
        return q

    m = _RANGE_RE.search(original)
    if m:
        lo, hi = float(m.group("lo")), float(m.group("hi"))
        q.value_range = (lo, hi)
        q.value = (lo + hi) / 2.0
        q.unit = (m.group("unit") or "").strip() or None
    else:
        m = _SINGLE_RE.search(original)
        if m:
            try:
                q.value = float(m.group("val"))
            except ValueError:
                q.value = None
            q.unit = (m.group("unit") or "").strip() or None

    _apply_dimension(q)
    return q


def _apply_dimension(q: Quantity) -> None:
    if q.unit is None or q.value is None:
        return
    u = q.unit.lower()
    if u in _TIME_TO_H:
        q.dimension = "time"
        q.normalized_unit = "h"
        q.normalized_value = q.value * _TIME_TO_H[u]
        q.comparable = True
        return
    if q.unit == "%" or u in ("percent", "pct"):
        q.dimension = "percent"
        q.normalized_unit = "%"
        q.normalized_value = q.value
        q.comparable = True
        return
    # Concentrations etc.: recognized but NOT auto-normalized (mg/mL vs uM need
    # molar mass). Keep the parsed value; mark not-comparable to avoid false
    # cross-paper comparisons.
    if "/" in q.unit or q.unit.lower() in ("m", "mm", "um", "nm", "µm", "ng", "ug", "mg", "g"):
        q.dimension = "concentration"
        q.comparable = False
        q.note = "concentration parsed but not normalized (needs molar-mass/context)"


def normalize_time_to_hours(text: str) -> Optional[float]:
    """Convenience: return hours for a time string, or ``None`` if not a time."""
    q = parse_quantity(text)
    return q.normalized_value if q.dimension == "time" else None


def extract_quantities(items: Optional[List[str]]) -> List[Quantity]:
    """Parse each entry of a list field (e.g. ``key_numeric_results``)."""
    return [parse_quantity(s) for s in (items or []) if str(s).strip()]
