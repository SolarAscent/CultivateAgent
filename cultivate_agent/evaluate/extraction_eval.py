"""Extraction benchmarking: precision / recall / F1 against a gold standard.

Adapted from ReactionSeek's field-level evaluation, generalized to the A-M
schema. For each field we compute TP/FP/FN by comparing normalized value sets
(list fields compared as sets; scalar fields as singletons). Null codes count as
"no value". Aggregates to per-field and overall P/R/F1, matching the
`extraction_accuracy` benchmark named in the project record.

Also reports the mean **grounding rate** (fraction of evidence quotes verified
against source), which measures traceability rather than accuracy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

from ..schema.evidence import NullCode, is_inference
from ..schema.extraction import PaperExtraction
from ..schema.extraction import _BLOCK_ATTR  # block letter -> attr name

_WS = re.compile(r"\s+")


def normalize_value(text: str) -> str:
    s = _WS.sub(" ", str(text).strip().lower())
    s = re.sub(r"\b(\d+(?:\.\d+)?)\s*hours?\b", r"\1 h", s)
    s = re.sub(r"\b(\d+(?:\.\d+)?)\s*minutes?\b", r"\1 min", s)
    s = re.sub(r"\b(\d+(?:\.\d+)?)\s*%", r"\1%", s)
    return s


def _to_set(value) -> Set[str]:
    """Normalized comparison set for a field value; null codes -> empty."""
    if value is None:
        return set()
    if isinstance(value, list):
        items = value
    else:
        items = [value]
    out: Set[str] = set()
    for it in items:
        if it is None:
            continue
        s = str(it).strip()
        if not s or NullCode.is_code(s):
            continue
        s2 = s[len("INF:"):].strip() if is_inference(s) else s
        out.add(normalize_value(s2))
    return out


def _prf(tp: int, fp: int, fn: int) -> Tuple[float, float, float]:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return round(p, 4), round(r, 4), round(f1, 4)


@dataclass
class FieldScore:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def add(self, pred: Set[str], gold: Set[str]) -> None:
        self.tp += len(pred & gold)
        self.fp += len(pred - gold)
        self.fn += len(gold - pred)

    @property
    def prf(self) -> Tuple[float, float, float]:
        return _prf(self.tp, self.fp, self.fn)


@dataclass
class EvalReport:
    per_field: Dict[str, FieldScore] = field(default_factory=dict)
    n_papers: int = 0
    grounding_rates: List[float] = field(default_factory=list)

    def overall(self) -> Dict[str, float]:
        tp = sum(s.tp for s in self.per_field.values())
        fp = sum(s.fp for s in self.per_field.values())
        fn = sum(s.fn for s in self.per_field.values())
        p, r, f1 = _prf(tp, fp, fn)
        return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f1}

    def mean_grounding(self) -> Optional[float]:
        return round(sum(self.grounding_rates) / len(self.grounding_rates), 3) if self.grounding_rates else None

    def to_rows(self) -> List[dict]:
        rows = []
        for name, s in sorted(self.per_field.items()):
            p, r, f1 = s.prf
            rows.append({"field": name, "tp": s.tp, "fp": s.fp, "fn": s.fn,
                         "precision": p, "recall": r, "f1": f1})
        o = self.overall()
        rows.append({"field": "OVERALL", **{k: o[k] for k in ("tp", "fp", "fn", "precision", "recall", "f1")}})
        return rows


def _iter_fields(ext: PaperExtraction):
    """Yield ``("<block>.<field>", value)`` for every schema field."""
    for letter, attr in _BLOCK_ATTR.items():
        block = getattr(ext, attr)
        for name in type(block).model_fields:
            yield f"{letter}.{name}", getattr(block, name)


def evaluate_extraction(pred: PaperExtraction, gold: PaperExtraction, report: Optional[EvalReport] = None) -> EvalReport:
    """Accumulate TP/FP/FN for one predicted vs gold record."""
    report = report or EvalReport()
    pred_fields = dict(_iter_fields(pred))
    for key, gold_val in _iter_fields(gold):
        gset = _to_set(gold_val)
        pset = _to_set(pred_fields.get(key))
        if not gset and not pset:
            continue  # neither reported -> not scored (as in ReactionSeek)
        report.per_field.setdefault(key, FieldScore()).add(pset, gset)
    report.n_papers += 1

    for p in (pred.extraction_meta or {}).get("passes", []) or []:
        if p.get("grounding_rate") is not None:
            report.grounding_rates.append(p["grounding_rate"])
    return report


def evaluate_corpus(preds: Sequence[PaperExtraction], golds: Sequence[PaperExtraction]) -> EvalReport:
    """Evaluate matched lists of predictions and gold records (aligned by paper_id)."""
    gold_by_id = {g.paper_id: g for g in golds}
    report = EvalReport()
    for pred in preds:
        gold = gold_by_id.get(pred.paper_id)
        if gold is not None:
            evaluate_extraction(pred, gold, report)
    return report
