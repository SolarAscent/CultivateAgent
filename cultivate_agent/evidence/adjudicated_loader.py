"""Load the human-adjudicated evidence table (S4 product) into EvidenceItems.

This is the S4 -> S5 bridge. ``export_adjudicated_evidence`` (Codex's side) writes
``bovine_evidence_table.tsv`` from supported/partial human decisions; this module
turns those rows into :class:`EvidenceItem`s that ``synthesize`` /
``EvidencePrior.from_summaries`` already consume, so a finished human review flows
straight into search-space priors and the design recommender.

Direction handling (honest, since the worksheet has no explicit sign column):

* A recorded **ratio** effect (``fold_change`` etc.) gives both the signed direction
  and a log-response-ratio ``effect`` (tier 2, or tier 1 if a variance is recorded).
* Otherwise direction is inferred from the ``key_finding`` polarity words the human
  wrote. Absolute metrics (a bare doubling time) are NOT turned into an effect —
  a single absolute value has no control-relative magnitude.
* Rows whose direction cannot be determined are skipped and counted, never guessed.

Recommended follow-up (Codex's adjudication schema): add an explicit
``effect_direction`` column (increase/decrease/no-change) so direction is recorded
by the human rather than inferred here.
"""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path
from typing import List, Optional, Tuple

from .meta_analysis import EvidenceItem

_SUPPORTED = {"supported", "partial"}

_RATIO_METRICS = {"fold_change", "fold change", "fold", "response_ratio", "ratio",
                  "proliferation_ratio", "relative_proliferation"}

_POS_WORDS = ("increase", "increased", "enhance", "enhanced", "improve", "improved",
              "higher", "greater", "faster", "promote", "promoted", "support",
              "supported", "boost", "accelerat", "superior", "better")
_NEG_WORDS = ("decrease", "decreased", "reduce", "reduced", "reduction", "lower",
              "slower", "impair", "impaired", "inhibit", "inhibited", "suppress",
              "suppressed", "detrimental", "worse", "decline", "loss")


def _direction_from_text(text: str) -> Optional[int]:
    t = (text or "").lower()
    pos = any(w in t for w in _POS_WORDS)
    neg = any(w in t for w in _NEG_WORDS)
    if pos and not neg:
        return 1
    if neg and not pos:
        return -1
    return None


def _outcome_from_endpoint(endpoint: str) -> str:
    e = (endpoint or "").lower()
    if "differentiat" in e or "myotube" in e or "fusion" in e:
        return "differentiation"
    return "proliferation"


def _to_float(x) -> Optional[float]:
    try:
        return float(str(x).strip())
    except (TypeError, ValueError):
        return None


def load_adjudicated_items(
    path: str | Path,
    *,
    normalizer=None,
    default_outcome: str = "proliferation",
) -> Tuple[List[EvidenceItem], int]:
    """Return (items, n_skipped) from an adjudicated evidence TSV.

    Only ``supported``/``partial`` rows with a determinable direction become items.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"adjudicated evidence table not found: {path}")

    items: List[EvidenceItem] = []
    skipped = 0
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if (row.get("decision") or "").strip().lower() not in _SUPPORTED:
                continue
            component = (row.get("formulation_or_variable") or "").strip()
            if not component:
                skipped += 1
                continue
            if normalizer is not None:
                component = normalizer.canonicalize(component).canonical or component

            outcome = _outcome_from_endpoint(row.get("endpoint") or "") or default_outcome
            finding = (row.get("key_finding") or "").strip()

            effect = variance = None
            direction: Optional[int] = None
            metric = (row.get("numeric_effect_metric") or "").strip().lower()
            value = _to_float(row.get("numeric_effect_value"))
            var = _to_float(row.get("numeric_effect_variance"))
            if value is not None and value > 0 and metric in _RATIO_METRICS:
                effect = math.log(value)                 # control-normalized log ratio
                direction = 1 if value > 1 else (-1 if value < 1 else 0)
                if var is not None and var > 0:
                    variance = var                        # tier 1 (human-recorded)
            if direction is None:
                direction = _direction_from_text(finding)
            if direction is None:
                skipped += 1
                continue

            context = {k: v for k, v in (
                ("finding", finding),
                ("dose_or_range", (row.get("dose_or_range") or "").strip()),
                ("cell_context", (row.get("cell_context") or "").strip()),
                ("decision", (row.get("decision") or "").strip()),
                ("review_id", (row.get("review_id") or "").strip()),
            ) if v}
            items.append(EvidenceItem(
                component=component, outcome=outcome,
                paper_id=(row.get("source_record_id") or "").strip() or "unknown",
                effect=effect, variance=variance, direction=direction,
                context=context, quote=finding,
            ))
    return items, skipped


def summarize_adjudicated(path: str | Path, *, normalizer=None, by_context: bool = False):
    """Convenience: adjudicated table -> EvidenceSummaries (ready for EvidencePrior)."""
    from .meta_analysis import synthesize
    items, _ = load_adjudicated_items(path, normalizer=normalizer)
    return synthesize(items, by_context=by_context)
