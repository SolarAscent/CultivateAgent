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

EVIDENCE_TABLE_COLUMNS = [
    "review_id",
    "source_record_id",
    "decision",
    "evidence_status",
    "fulltext_path",
    "selected_range",
    "key_finding",
    "formulation_or_variable",
    "dose_or_range",
    "endpoint",
    "cell_context",
    "limitations",
    "wetlab_use",
    "reviewer",
    "review_date",
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


@dataclass
class PassagePreview:
    review_id: str
    source_record_id: str
    fulltext_path: str
    range_text: str
    start: int
    end: int
    excerpt: str
    status: str = "ok"


def write_adjudication_template(
    *,
    review_queue_path: str | Path,
    manifest_path: str | Path,
    papers_dir: str | Path,
    review_ids: Iterable[str],
    out_path: str | Path,
    top_k: int = 3,
    include_missing: bool = False,
    path_base: str | Path | None = None,
) -> Path:
    """Write a TSV worksheet prefilled with review task metadata and locators."""
    items = build_review_packet(
        review_queue_path=review_queue_path,
        manifest_path=manifest_path,
        papers_dir=papers_dir,
        review_ids=review_ids,
        top_k=top_k,
        path_base=path_base,
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
        writer = csv.DictWriter(
            f,
            fieldnames=WORKSHEET_COLUMNS,
            delimiter="\t",
            lineterminator="\n",
        )
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


def build_adjudication_passage_previews(
    worksheet_path: str | Path,
    *,
    review_ids: Iterable[str] | None = None,
    path_base: str | Path | None = None,
    max_ranges: int = 3,
    context_chars: int = 260,
) -> List[PassagePreview]:
    """Load short local snippets for worksheet ranges without adjudicating them."""
    wanted = set(review_ids or [])
    base = Path(path_base).resolve() if path_base is not None else Path.cwd().resolve()
    previews: List[PassagePreview] = []
    with Path(worksheet_path).open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            review_id = row.get("review_id", "")
            if wanted and review_id not in wanted:
                continue
            source_record_id = row.get("source_record_id", "")
            fulltext_path = row.get("fulltext_path", "")
            ranges = _ranges_for_preview(row, max_ranges=max_ranges)
            if not ranges:
                previews.append(PassagePreview(
                    review_id=review_id,
                    source_record_id=source_record_id,
                    fulltext_path=fulltext_path,
                    range_text="",
                    start=0,
                    end=0,
                    excerpt="",
                    status="missing_range",
                ))
                continue
            if not fulltext_path:
                previews.append(PassagePreview(
                    review_id=review_id,
                    source_record_id=source_record_id,
                    fulltext_path="",
                    range_text="",
                    start=0,
                    end=0,
                    excerpt="",
                    status="missing_fulltext_path",
                ))
                continue
            resolved = _resolve_fulltext_path(fulltext_path, base)
            if not resolved.exists():
                previews.append(PassagePreview(
                    review_id=review_id,
                    source_record_id=source_record_id,
                    fulltext_path=fulltext_path,
                    range_text="",
                    start=0,
                    end=0,
                    excerpt="",
                    status="missing_fulltext_file",
                ))
                continue
            text = resolved.read_text(encoding="utf-8", errors="ignore")
            for range_text in ranges:
                parsed = _parse_range(range_text)
                if parsed is None:
                    previews.append(PassagePreview(
                        review_id=review_id,
                        source_record_id=source_record_id,
                        fulltext_path=fulltext_path,
                        range_text=range_text,
                        start=0,
                        end=0,
                        excerpt="",
                        status="invalid_range",
                    ))
                    continue
                start, end = parsed
                if start >= len(text):
                    excerpt = ""
                    status = "range_out_of_bounds"
                else:
                    bounded_end = min(end, len(text))
                    excerpt = _short_excerpt(text[start:bounded_end], context_chars)
                    status = "ok"
                previews.append(PassagePreview(
                    review_id=review_id,
                    source_record_id=source_record_id,
                    fulltext_path=fulltext_path,
                    range_text=range_text,
                    start=start,
                    end=end,
                    excerpt=excerpt,
                    status=status,
                ))
    return previews


def write_adjudication_passages_markdown(previews: List[PassagePreview], path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(format_adjudication_passages_markdown(previews), encoding="utf-8")
    return out


def format_adjudication_passages_markdown(previews: List[PassagePreview]) -> str:
    lines = [
        "# Human Adjudication Passage Preview",
        "",
        "Status: local review aid with short source snippets; not an AI adjudication decision.",
        "Do not commit expanded excerpts unless source rights and quotation limits are reviewed.",
        "",
        "| Review ID | Source | Range | Status | Full text | Excerpt |",
        "|---|---|---|---|---|---|",
    ]
    if not previews:
        lines.append("| - | - | - | no_rows | - | - |")
    for item in previews:
        excerpt = item.excerpt.replace("|", "\\|")
        lines.append(
            f"| `{item.review_id}` | `{item.source_record_id}` | `{item.range_text or '-'}` | "
            f"`{item.status}` | `{item.fulltext_path or 'MISSING'}` | {excerpt or '-'} |"
        )
    lines.append("")
    return "\n".join(lines)


def export_adjudicated_evidence(
    *,
    worksheet_path: str | Path,
    out_path: str | Path,
    include_partial: bool = True,
    require_valid: bool = True,
) -> Path:
    """Export human-supported worksheet rows to the adjudicated evidence table.

    This table records human-reviewed claims for downstream search-space design.
    It is not a cross-paper training-label table.
    """
    if require_valid:
        result = validate_adjudication_worksheet(worksheet_path)
        if not result.ok:
            first = result.issues[0]
            raise ValueError(
                f"worksheet validation failed at row {first.row_number} "
                f"{first.review_id} {first.field}: {first.message}"
            )
    allowed = {"supported", "partial"} if include_partial else {"supported"}
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with (
        Path(worksheet_path).open(newline="", encoding="utf-8") as f_in,
        out.open("w", newline="", encoding="utf-8") as f_out,
    ):
        reader = csv.DictReader(f_in, delimiter="\t")
        writer = csv.DictWriter(
            f_out,
            fieldnames=EVIDENCE_TABLE_COLUMNS,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in reader:
            decision = (row.get("decision") or "").strip().lower()
            if decision not in allowed:
                continue
            writer.writerow({
                "review_id": row.get("review_id", ""),
                "source_record_id": row.get("source_record_id", ""),
                "decision": decision,
                "evidence_status": "human_reviewed",
                "fulltext_path": row.get("fulltext_path", ""),
                "selected_range": row.get("selected_range", ""),
                "key_finding": row.get("key_finding", ""),
                "formulation_or_variable": row.get("formulation_or_variable", ""),
                "dose_or_range": row.get("dose_or_range", ""),
                "endpoint": row.get("endpoint", ""),
                "cell_context": row.get("cell_context", ""),
                "limitations": row.get("limitations", ""),
                "wetlab_use": row.get("wetlab_use", ""),
                "reviewer": row.get("reviewer", ""),
                "review_date": row.get("review_date", ""),
            })
    return out


def count_evidence_rows(path: str | Path) -> int:
    with Path(path).open(newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f, delimiter="\t"))


def _is_range(value: str) -> bool:
    if "-" not in value:
        return False
    start, end = value.split("-", 1)
    if not (start.isdigit() and end.isdigit()):
        return False
    return int(start) < int(end)


def _ranges_for_preview(row: dict[str, str], *, max_ranges: int) -> List[str]:
    selected = (row.get("selected_range") or "").strip()
    if selected:
        return [selected]
    ranges = [
        r.strip()
        for r in (row.get("suggested_ranges") or "").split(";")
        if r.strip()
    ]
    return ranges[:max_ranges]


def _resolve_fulltext_path(path: str, base: Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return base / p


def _parse_range(value: str) -> tuple[int, int] | None:
    if not _is_range(value):
        return None
    start, end = value.split("-", 1)
    return int(start), int(end)


def _short_excerpt(text: str, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 3)].rstrip() + "..."
