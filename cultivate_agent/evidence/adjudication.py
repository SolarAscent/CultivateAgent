"""Human evidence-adjudication worksheet helpers.

These helpers create and validate a TSV worksheet for human reviewers. They do
not decide whether evidence is supported; they only make the handoff from
locator packet to structured adjudication less lossy.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List

from .review_packet import build_review_packet

ALLOWED_DECISIONS = {"", "supported", "partial", "unsupported", "uncertain", "defer"}
REQUIRES_RANGE = {"supported", "partial"}

WORKSHEET_COLUMNS = [
    "review_id",
    "source_record_id",
    "status",
    "decision",
    "reviewer",
    "review_date",
    "fulltext_path",
    "suggested_ranges",
    "selected_range",
    "key_finding",
    "formulation_or_variable",
    "dose_or_range",
    "endpoint",
    "cell_context",
    "limitations",
    "wetlab_use",
    "notes",
]


@dataclass
class ValidationIssue:
    row_number: int
    review_id: str
    field: str
    message: str


@dataclass
class ValidationResult:
    rows: int
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


def write_adjudication_template(
    *,
    review_queue_path: str | Path,
    manifest_path: str | Path,
    papers_dir: str | Path,
    review_ids: Iterable[str],
    out_path: str | Path,
    top_k: int = 3,
    include_missing: bool = False,
) -> Path:
    """Write a TSV worksheet prefilled with review task metadata and locators."""
    items = build_review_packet(
        review_queue_path=review_queue_path,
        manifest_path=manifest_path,
        papers_dir=papers_dir,
        review_ids=review_ids,
        top_k=top_k,
    )
    rows = []
    for item in items:
        if item.status != "ready_for_human_review" and not include_missing:
            continue
        ranges = ";".join(f"{h.start}-{h.end}" for h in item.hits[:top_k])
        rows.append({
            "review_id": item.task.review_id,
            "source_record_id": item.task.source_record_id,
            "status": item.status,
            "decision": "",
            "reviewer": "",
            "review_date": "",
            "fulltext_path": item.fulltext_path,
            "suggested_ranges": ranges,
            "selected_range": "",
            "key_finding": "",
            "formulation_or_variable": "",
            "dose_or_range": "",
            "endpoint": "",
            "cell_context": "",
            "limitations": "",
            "wetlab_use": "",
            "notes": (
                "Human reviewer: set decision to supported, partial, unsupported, "
                "uncertain, or defer. For supported/partial, fill selected_range "
                "and key_finding."
            ),
        })
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=WORKSHEET_COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    return out


def validate_adjudication_worksheet(path: str | Path) -> ValidationResult:
    """Validate allowed decisions and range references in a filled worksheet."""
    issues: List[ValidationIssue] = []
    rows = 0
    with Path(path).open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        missing = [c for c in WORKSHEET_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            for col in missing:
                issues.append(ValidationIssue(0, "", col, "missing required column"))
            return ValidationResult(rows=0, issues=issues)
        for row_number, row in enumerate(reader, start=2):
            rows += 1
            rid = row.get("review_id", "")
            decision = (row.get("decision") or "").strip().lower()
            if decision not in ALLOWED_DECISIONS:
                issues.append(ValidationIssue(
                    row_number, rid, "decision",
                    f"must be one of {', '.join(sorted(d or '<blank>' for d in ALLOWED_DECISIONS))}",
                ))
                continue
            if not decision:
                continue
            if decision in REQUIRES_RANGE:
                selected = (row.get("selected_range") or "").strip()
                if not _is_range(selected):
                    issues.append(ValidationIssue(row_number, rid, "selected_range", "required as start-end"))
                suggested = {
                    r.strip()
                    for r in (row.get("suggested_ranges") or "").split(";")
                    if r.strip()
                }
                if selected and suggested and selected not in suggested:
                    issues.append(ValidationIssue(
                        row_number, rid, "selected_range",
                        "must match one of suggested_ranges unless the reviewer updates suggested_ranges",
                    ))
                if not (row.get("key_finding") or "").strip():
                    issues.append(ValidationIssue(row_number, rid, "key_finding", "required for supported/partial"))
            if decision in {"supported", "partial", "unsupported"} and not (row.get("wetlab_use") or "").strip():
                issues.append(ValidationIssue(row_number, rid, "wetlab_use", "required for evidence-bearing decisions"))
    return ValidationResult(rows=rows, issues=issues)


def write_validation_markdown(result: ValidationResult, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Human Adjudication Worksheet Validation",
        "",
        f"- Rows checked: {result.rows}",
        f"- Result: {'PASS' if result.ok else 'FAIL'}",
        f"- Issues: {len(result.issues)}",
        "",
    ]
    if result.issues:
        lines += [
            "| Row | Review ID | Field | Issue |",
            "|---:|---|---|---|",
        ]
        for issue in result.issues:
            lines.append(f"| {issue.row_number} | {issue.review_id} | {issue.field} | {issue.message} |")
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def _is_range(value: str) -> bool:
    if "-" not in value:
        return False
    start, end = value.split("-", 1)
    if not (start.isdigit() and end.isdigit()):
        return False
    return int(start) < int(end)
