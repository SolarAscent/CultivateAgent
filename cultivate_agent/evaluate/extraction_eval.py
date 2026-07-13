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

# Gate 2 concepts from docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md. Some
# concepts span several A-M fields. dose_range remains a proxy because the A-M
# schema has no dedicated component-dose structure; a proxy can diagnose a
# failure but cannot by itself approve wet-lab entry.
DECISION_CRITICAL_FIELD_GROUPS: Dict[str, Dict[str, object]] = {
    "species": {"paths": ("B.species",), "basis": "direct"},
    "cell_type": {"paths": ("D.cell_type",), "basis": "direct"},
    "stage": {
        "paths": ("D.expansion_conditions_summary", "D.differentiation_conditions_summary"),
        "basis": "direct",
    },
    "medium_type": {"paths": ("E.basal_medium",), "basis": "direct"},
    "serum_free_status": {"paths": ("E.serum_free_status",), "basis": "direct"},
    "component_identity": {
        "paths": (
            "E.growth_factors",
            "E.small_molecules",
            "E.hydrolysates_or_extracts",
            "E.conditioned_medium_or_recycling",
        ),
        "basis": "direct",
    },
    "dose_range": {
        "paths": ("J.extractable_variables", "J.key_numeric_results", "J.units_reported"),
        "basis": "proxy",
    },
    "endpoint": {
        "paths": ("I.main_readouts", "I.proliferation_metrics", "I.differentiation_metrics"),
        "basis": "direct",
    },
}


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
    expected_paper_ids: List[str] = field(default_factory=list)
    predicted_paper_ids: List[str] = field(default_factory=list)
    matched_paper_ids: List[str] = field(default_factory=list)
    missing_prediction_ids: List[str] = field(default_factory=list)
    unexpected_prediction_ids: List[str] = field(default_factory=list)
    gold_populated_field_cells: int = 0
    predicted_gold_field_cells: int = 0
    substantive_predicted_field_cells: int = 0
    evidence_attached_field_cells: int = 0
    unverified_evidence_field_cells: int = 0
    critical_expected_cells: Dict[str, int] = field(default_factory=dict)
    critical_predicted_cells: Dict[str, int] = field(default_factory=dict)
    critical_direct_predicted_cells: Dict[str, int] = field(default_factory=dict)

    def overall(self) -> Dict[str, float]:
        tp = sum(s.tp for s in self.per_field.values())
        fp = sum(s.fp for s in self.per_field.values())
        fn = sum(s.fn for s in self.per_field.values())
        p, r, f1 = _prf(tp, fp, fn)
        return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f1}

    def mean_grounding(self) -> Optional[float]:
        return round(sum(self.grounding_rates) / len(self.grounding_rates), 3) if self.grounding_rates else None

    def alignment(self) -> Dict[str, object]:
        expected = len(self.expected_paper_ids)
        matched = len(self.matched_paper_ids)
        return {
            "expected": expected,
            "predicted": len(self.predicted_paper_ids),
            "matched": matched,
            "coverage": round(matched / expected, 4) if expected else 1.0,
            "missing_prediction_ids": list(self.missing_prediction_ids),
            "unexpected_prediction_ids": list(self.unexpected_prediction_ids),
        }

    def coverage(self) -> Dict[str, object]:
        gold_total = self.gold_populated_field_cells
        substantive_total = self.substantive_predicted_field_cells
        return {
            "gold_populated_field_cells": gold_total,
            "predicted_gold_field_cells": self.predicted_gold_field_cells,
            "gold_field_presence_rate": (
                round(self.predicted_gold_field_cells / gold_total, 4)
                if gold_total else None
            ),
            "substantive_predicted_field_cells": substantive_total,
            "evidence_attached_field_cells": self.evidence_attached_field_cells,
            "evidence_attachment_rate": (
                round(self.evidence_attached_field_cells / substantive_total, 4)
                if substantive_total else None
            ),
            "unverified_evidence_field_cells": self.unverified_evidence_field_cells,
        }

    def critical_coverage(self, *, threshold: float = 0.75) -> Dict[str, object]:
        rows = []
        total_expected = 0
        total_predicted = 0
        proxy_evaluated = False
        for concept, spec in DECISION_CRITICAL_FIELD_GROUPS.items():
            expected = self.critical_expected_cells.get(concept, 0)
            predicted = self.critical_predicted_cells.get(concept, 0)
            direct_predicted = self.critical_direct_predicted_cells.get(concept, 0)
            rate = round(predicted / expected, 4) if expected else None
            basis = str(spec["basis"])
            if concept == "dose_range" and expected and direct_predicted == expected:
                basis = "direct_operator"
            if basis == "proxy" and expected:
                proxy_evaluated = True
            status = "NOT_EVALUABLE" if rate is None else ("PASS" if rate >= threshold else "FAIL")
            rows.append({
                "concept": concept,
                "basis": basis,
                "expected": expected,
                "predicted": predicted,
                "direct_predicted": direct_predicted,
                "nonmissing_fraction": rate,
                "status": status,
            })
            total_expected += expected
            total_predicted += predicted
        overall_rate = round(total_predicted / total_expected, 4) if total_expected else None
        if overall_rate is None:
            gate_status = "NOT_EVALUABLE"
        elif overall_rate < threshold or any(row["status"] == "FAIL" for row in rows):
            gate_status = "FAIL"
        elif any(row["status"] == "NOT_EVALUABLE" for row in rows):
            gate_status = "NOT_EVALUABLE"
        elif proxy_evaluated:
            gate_status = "PROVISIONAL_ONLY"
        else:
            gate_status = "PASS"
        return {
            "threshold": threshold,
            "expected": total_expected,
            "predicted": total_predicted,
            "nonmissing_fraction": overall_rate,
            "gate_status": gate_status,
            "rows": rows,
        }

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
    gold_fields = dict(_iter_fields(gold))
    for concept, spec in DECISION_CRITICAL_FIELD_GROUPS.items():
        paths = spec["paths"]
        gold_present = any(_to_set(gold_fields.get(path)) for path in paths)
        if not gold_present:
            continue
        report.critical_expected_cells[concept] = report.critical_expected_cells.get(concept, 0) + 1
        direct_present = concept != "dose_range" or _has_grounded_dose_record(pred)
        predicted_present = direct_present if concept == "dose_range" else any(
            _to_set(pred_fields.get(path)) for path in paths
        )
        if concept == "dose_range" and not predicted_present:
            predicted_present = any(_to_set(pred_fields.get(path)) for path in paths)
        if predicted_present:
            report.critical_predicted_cells[concept] = report.critical_predicted_cells.get(concept, 0) + 1
        if predicted_present and direct_present:
            report.critical_direct_predicted_cells[concept] = (
                report.critical_direct_predicted_cells.get(concept, 0) + 1
            )
    for key, gold_val in gold_fields.items():
        gset = _to_set(gold_val)
        pset = _to_set(pred_fields.get(key))
        if gset:
            report.gold_populated_field_cells += 1
            if pset:
                report.predicted_gold_field_cells += 1
        if not key.startswith("A.") and pset:
            report.substantive_predicted_field_cells += 1
            evidence = pred.evidence.get(key)
            if evidence is not None:
                report.evidence_attached_field_cells += 1
                if "UNVERIFIED" in (evidence.location or ""):
                    report.unverified_evidence_field_cells += 1
        if not gset and not pset:
            continue  # neither reported -> not scored (as in ReactionSeek)
        report.per_field.setdefault(key, FieldScore()).add(pset, gset)
    report.n_papers += 1

    for p in (pred.extraction_meta or {}).get("passes", []) or []:
        if p.get("grounding_rate") is not None:
            report.grounding_rates.append(p["grounding_rate"])
    return report


def evaluate_corpus(preds: Sequence[PaperExtraction], golds: Sequence[PaperExtraction]) -> EvalReport:
    """Evaluate a corpus with strict paper-ID alignment.

    Every gold record is scored. A missing prediction is represented by an
    empty extraction so its populated gold fields become false negatives.
    Unexpected predictions are reported but cannot be scored without gold.
    Duplicate IDs are rejected because silently keeping one record would make
    the benchmark dependent on input order.
    """
    gold_by_id = _unique_by_paper_id(golds, label="gold")
    pred_by_id = _unique_by_paper_id(preds, label="prediction")
    expected_ids = list(gold_by_id)
    predicted_ids = list(pred_by_id)
    matched_ids = [paper_id for paper_id in expected_ids if paper_id in pred_by_id]
    missing_ids = [paper_id for paper_id in expected_ids if paper_id not in pred_by_id]
    unexpected_ids = [paper_id for paper_id in predicted_ids if paper_id not in gold_by_id]
    report = EvalReport(
        expected_paper_ids=expected_ids,
        predicted_paper_ids=predicted_ids,
        matched_paper_ids=matched_ids,
        missing_prediction_ids=missing_ids,
        unexpected_prediction_ids=unexpected_ids,
    )
    for paper_id, gold in gold_by_id.items():
        pred = pred_by_id.get(paper_id) or PaperExtraction(paper_id=paper_id)
        evaluate_extraction(pred, gold, report)
    return report


def _unique_by_paper_id(
    records: Sequence[PaperExtraction], *, label: str
) -> Dict[str, PaperExtraction]:
    by_id: Dict[str, PaperExtraction] = {}
    duplicates: Set[str] = set()
    for record in records:
        if record.paper_id in by_id:
            duplicates.add(record.paper_id)
        else:
            by_id[record.paper_id] = record
    if duplicates:
        duplicate_list = ", ".join(sorted(duplicates))
        raise ValueError(f"duplicate {label} paper_id(s): {duplicate_list}")
    return by_id


def _has_grounded_dose_record(extraction: PaperExtraction) -> bool:
    records = (extraction.extraction_meta or {}).get("dose_records") or []
    return any(isinstance(record, dict) and record.get("grounded") is True for record in records)
