"""Versioned, dual-review gold-standard worksheets for full-text extraction."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from ..schema.extraction import _BLOCK_ATTR, block_model

FORMAT_VERSION = 1
DECISIONS = {"reported", "not_reported", "not_applicable", "uncertain", "defer"}
REVIEW_SLOTS = ("reviewer_1", "reviewer_2", "adjudicated")

BASE_COLUMNS = [
    "benchmark_version",
    "record_id",
    "paper_id",
    "title",
    "year",
    "doi",
    "url",
    "block",
    "field",
    "field_description",
    "value_type",
    "source_path",
    "source_sha256",
]
SLOT_COLUMNS = [
    f"{slot}_{suffix}"
    for slot in REVIEW_SLOTS
    for suffix in ("decision", "value_json", "quote", "location", "reviewer", "date")
]
COLUMNS = BASE_COLUMNS + SLOT_COLUMNS + ["notes"]
REVIEWER_COLUMNS = BASE_COLUMNS + [
    "decision", "value_json", "quote", "location", "reviewer", "date", "notes"
]


@dataclass(frozen=True)
class GoldSource:
    record_id: str
    paper_id: str
    title: str
    year: str
    doi: str
    url: str
    source_path: str
    source_sha256: str
    source_chars: int


@dataclass
class GoldValidation:
    rows: int
    expected_rows: int
    reviewer_1_completed: int
    reviewer_2_completed: int
    adjudicated_completed: int
    issues: List[str]
    double_reviewed: int = 0
    decision_exact_rate: Optional[float] = None
    decision_kappa: Optional[float] = None
    reported_pairs: int = 0
    value_exact_rate: Optional[float] = None

    @property
    def ready(self) -> bool:
        return (
            not self.issues
            and self.rows == self.expected_rows
            and self.reviewer_1_completed == self.expected_rows
            and self.reviewer_2_completed == self.expected_rows
            and self.adjudicated_completed == self.expected_rows
        )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _schema_fields() -> List[Tuple[str, str, str, str]]:
    rows: List[Tuple[str, str, str, str]] = []
    for letter, attr in _BLOCK_ATTR.items():
        model = block_model(letter)
        for name, info in model.model_fields.items():
            rows.append((letter, name, info.description or "", str(info.annotation)))
    return rows


def _selected_schema_fields(field_paths: Optional[Sequence[str]]) -> List[Tuple[str, str, str, str]]:
    fields = _schema_fields()
    if not field_paths:
        return fields
    requested = list(field_paths)
    if len(requested) != len(set(requested)):
        raise ValueError("field scope contains duplicate paths")
    by_path = {f"{row[0]}.{row[1]}": row for row in fields}
    unknown = [path for path in requested if path not in by_path]
    if unknown:
        raise ValueError(f"unknown field path(s): {', '.join(unknown)}")
    return [by_path[path] for path in requested]


def _schema_sha256() -> str:
    payload = json.dumps(_schema_fields(), ensure_ascii=False, separators=(",", ":"))
    return _sha256_bytes(payload.encode("utf-8"))


def create_gold_review(
    selections: Sequence[Tuple[str, Path]],
    *,
    repo_root: Path,
    benchmark_version: str,
    manifest_path: Path,
    worksheet_path: Path,
    bibliography: Optional[Dict[str, Dict[str, str]]] = None,
    field_paths: Optional[Sequence[str]] = None,
) -> Tuple[Path, Path]:
    """Create a manifest and blank A-M dual-review worksheet."""
    sources: List[GoldSource] = []
    seen_records = set()
    seen_papers = set()
    for record_id, paper_dir in selections:
        if record_id in seen_records:
            raise ValueError(f"duplicate record_id: {record_id}")
        metadata_path = paper_dir / "metadata.json"
        fulltext_path = paper_dir / "fulltext.txt"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        ref = metadata.get("ref") or {}
        citation = (bibliography or {}).get(record_id, {})
        paper_id = str(ref.get("paper_id") or paper_dir.name)
        if paper_id in seen_papers:
            raise ValueError(f"duplicate paper_id: {paper_id}")
        text_bytes = fulltext_path.read_bytes()
        relative = fulltext_path.resolve().relative_to(repo_root.resolve()).as_posix()
        sources.append(GoldSource(
            record_id=record_id,
            paper_id=paper_id,
            title=str(citation.get("title") or ref.get("title") or paper_id),
            year=str(citation.get("year") or ref.get("year") or ""),
            doi=str(citation.get("doi") or ref.get("doi") or ""),
            url=str(citation.get("url") or ref.get("url") or ""),
            source_path=relative,
            source_sha256=_sha256_bytes(text_bytes),
            source_chars=len(text_bytes.decode("utf-8")),
        ))
        seen_records.add(record_id)
        seen_papers.add(paper_id)

    selected_fields = _selected_schema_fields(field_paths)
    manifest = {
        "format_version": FORMAT_VERSION,
        "benchmark_version": benchmark_version,
        "schema_sha256": _schema_sha256(),
        "field_paths": [f"{letter}.{name}" for letter, name, _d, _t in selected_fields],
        "papers": [source.__dict__ for source in sources],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    worksheet_path.parent.mkdir(parents=True, exist_ok=True)
    with worksheet_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for source in sources:
            for letter, field_name, description, value_type in selected_fields:
                row = {column: "" for column in COLUMNS}
                row.update({
                    "benchmark_version": benchmark_version,
                    "record_id": source.record_id,
                    "paper_id": source.paper_id,
                    "title": source.title,
                    "year": source.year,
                    "doi": source.doi,
                    "url": source.url,
                    "block": letter,
                    "field": field_name,
                    "field_description": description,
                    "value_type": value_type,
                    "source_path": source.source_path,
                    "source_sha256": source.source_sha256,
                })
                writer.writerow(row)
    return manifest_path, worksheet_path


def create_reviewer_template(master_worksheet: Path, reviewer_template: Path) -> Path:
    """Create a single-reviewer blank sheet that does not expose another review."""
    with master_worksheet.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    reviewer_template.parent.mkdir(parents=True, exist_ok=True)
    with reviewer_template.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=REVIEWER_COLUMNS, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        for row in rows:
            output = {column: row.get(column, "") for column in BASE_COLUMNS}
            output.update({column: "" for column in REVIEWER_COLUMNS if column not in BASE_COLUMNS})
            writer.writerow(output)
    return reviewer_template


def merge_independent_reviews(
    master_worksheet: Path,
    reviewer_1_path: Path,
    reviewer_2_path: Path,
    output_path: Path,
) -> Path:
    """Merge two blind reviewer sheets into the controlled adjudication master."""
    with master_worksheet.open(encoding="utf-8", newline="") as handle:
        master_reader = csv.DictReader(handle, delimiter="\t")
        if master_reader.fieldnames != COLUMNS:
            raise ValueError("master worksheet columns do not match controlled template")
        master_rows = list(master_reader)

    def load_reviewer(path: Path) -> Dict[Tuple[str, str, str], Dict[str, str]]:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames != REVIEWER_COLUMNS:
                raise ValueError(f"reviewer worksheet columns do not match template: {path}")
            rows = list(reader)
        mapped: Dict[Tuple[str, str, str], Dict[str, str]] = {}
        for row in rows:
            key = (row["paper_id"], row["block"], row["field"])
            if key in mapped:
                raise ValueError(f"duplicate reviewer field cell {key}: {path}")
            mapped[key] = row
        return mapped

    reviews = (load_reviewer(reviewer_1_path), load_reviewer(reviewer_2_path))
    expected_keys = {(row["paper_id"], row["block"], row["field"]) for row in master_rows}
    for index, review in enumerate(reviews, start=1):
        if set(review) != expected_keys:
            raise ValueError(f"reviewer {index} field cells do not match master")
    for row in master_rows:
        key = (row["paper_id"], row["block"], row["field"])
        notes = []
        for index, review in enumerate(reviews, start=1):
            source_row = review[key]
            for column in BASE_COLUMNS:
                if source_row.get(column, "") != row.get(column, ""):
                    raise ValueError(f"reviewer {index} base metadata drift for {key}: {column}")
            for suffix in ("decision", "value_json", "quote", "location", "reviewer", "date"):
                row[f"reviewer_{index}_{suffix}"] = source_row.get(suffix, "")
            if source_row.get("notes"):
                notes.append(f"reviewer_{index}: {source_row['notes']}")
        if notes:
            row["notes"] = " | ".join(filter(None, [row.get("notes", ""), *notes]))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(master_rows)
    return output_path


def validate_gold_review(
    manifest_path: Path,
    worksheet_path: Path,
    *,
    repo_root: Path,
) -> GoldValidation:
    """Validate structure, source/schema hashes, JSON types, and exact quotes."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    issues: List[str] = []
    if manifest.get("format_version") != FORMAT_VERSION:
        issues.append(f"unsupported manifest format_version: {manifest.get('format_version')!r}")
    if manifest.get("schema_sha256") != _schema_sha256():
        issues.append("schema hash mismatch; version the benchmark before changing fields")
    papers = manifest.get("papers") or []
    try:
        selected_fields = _selected_schema_fields(manifest.get("field_paths"))
    except ValueError as exc:
        issues.append(str(exc))
        selected_fields = []
    sources: Dict[str, str] = {}
    for paper in papers:
        paper_id = str(paper.get("paper_id") or "")
        path = repo_root / str(paper.get("source_path") or "")
        if not path.is_file():
            issues.append(f"{paper_id}: source file missing: {path}")
            continue
        payload = path.read_bytes()
        if _sha256_bytes(payload) != paper.get("source_sha256"):
            issues.append(f"{paper_id}: source hash mismatch")
        sources[paper_id] = payload.decode("utf-8")

    with worksheet_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != COLUMNS:
            issues.append("worksheet columns do not match the controlled template")
        rows = list(reader)

    expected_keys = {
        (str(paper.get("paper_id") or ""), letter, field_name)
        for paper in papers
        for letter, field_name, _description, _value_type in selected_fields
    }
    seen: Dict[Tuple[str, str, str], int] = {}
    completed = {slot: 0 for slot in REVIEW_SLOTS}
    for line_number, row in enumerate(rows, start=2):
        key = (row.get("paper_id", ""), row.get("block", ""), row.get("field", ""))
        if key in seen:
            issues.append(f"line {line_number}: duplicate field cell {key}")
        seen[key] = line_number
        if key not in expected_keys:
            issues.append(f"line {line_number}: unexpected field cell {key}")
            continue
        source = sources.get(key[0], "")
        for slot in REVIEW_SLOTS:
            decision = (row.get(f"{slot}_decision") or "").strip()
            if not decision:
                continue
            completed[slot] += 1
            if decision not in DECISIONS:
                issues.append(f"line {line_number}: invalid {slot} decision {decision!r}")
                continue
            _validate_slot(row, slot, source, key[1], key[2], line_number, issues)
    missing = sorted(expected_keys - set(seen))
    if missing:
        issues.append(f"worksheet missing {len(missing)} field cell(s)")
    double_rows = [
        row for row in rows
        if (row.get("reviewer_1_decision") or "").strip() in DECISIONS
        and (row.get("reviewer_2_decision") or "").strip() in DECISIONS
    ]
    decisions_1 = [row["reviewer_1_decision"].strip() for row in double_rows]
    decisions_2 = [row["reviewer_2_decision"].strip() for row in double_rows]
    decision_exact = (
        sum(a == b for a, b in zip(decisions_1, decisions_2)) / len(double_rows)
        if double_rows else None
    )
    reported_pairs = [
        row for row in double_rows
        if row["reviewer_1_decision"].strip() == "reported"
        and row["reviewer_2_decision"].strip() == "reported"
    ]
    value_exact = None
    if reported_pairs:
        matches = 0
        for row in reported_pairs:
            try:
                left = _canonical_value_json(row["reviewer_1_value_json"])
                right = _canonical_value_json(row["reviewer_2_value_json"])
                matches += left == right
            except Exception:  # invalid JSON is already reported by slot validation
                pass
        value_exact = matches / len(reported_pairs)
    return GoldValidation(
        rows=len(rows),
        expected_rows=len(expected_keys),
        reviewer_1_completed=completed["reviewer_1"],
        reviewer_2_completed=completed["reviewer_2"],
        adjudicated_completed=completed["adjudicated"],
        issues=issues,
        double_reviewed=len(double_rows),
        decision_exact_rate=round(decision_exact, 4) if decision_exact is not None else None,
        decision_kappa=_cohen_kappa(decisions_1, decisions_2),
        reported_pairs=len(reported_pairs),
        value_exact_rate=round(value_exact, 4) if value_exact is not None else None,
    )


def _cohen_kappa(left: Sequence[str], right: Sequence[str]) -> Optional[float]:
    if not left:
        return None
    observed = sum(a == b for a, b in zip(left, right)) / len(left)
    labels = set(left) | set(right)
    expected = sum(
        (left.count(label) / len(left)) * (right.count(label) / len(right))
        for label in labels
    )
    return round((observed - expected) / (1 - expected), 4) if expected < 1 else None


def _canonical_value_json(payload: str) -> str:
    value = json.loads(payload)
    if isinstance(value, list):
        value = sorted(value, key=lambda item: json.dumps(item, sort_keys=True))
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _validate_slot(
    row: Dict[str, str],
    slot: str,
    source: str,
    letter: str,
    field_name: str,
    line_number: int,
    issues: List[str],
) -> None:
    decision = row[f"{slot}_decision"].strip()
    value_json = (row.get(f"{slot}_value_json") or "").strip()
    quote = (row.get(f"{slot}_quote") or "").strip()
    location = (row.get(f"{slot}_location") or "").strip()
    reviewer = (row.get(f"{slot}_reviewer") or "").strip()
    date = (row.get(f"{slot}_date") or "").strip()
    if not reviewer or not date:
        issues.append(f"line {line_number}: {slot} requires reviewer and date")
    if decision == "reported":
        if not value_json or not quote or not location:
            issues.append(f"line {line_number}: reported {slot} requires value_json, quote, and location")
            return
        try:
            value = json.loads(value_json)
            block_model(letter).model_validate({field_name: value})
        except Exception as exc:  # noqa: BLE001
            issues.append(f"line {line_number}: invalid {slot} value_json: {exc}")
        normalized_quote = " ".join(quote.split())
        normalized_source = " ".join(source.split())
        if len(normalized_quote) < 8 or normalized_quote.lower() not in normalized_source.lower():
            issues.append(f"line {line_number}: {slot} quote is not grounded in source")
    elif value_json:
        issues.append(f"line {line_number}: non-reported {slot} must not contain value_json")
    if decision in {"not_reported", "not_applicable", "defer"} and (quote or location):
        issues.append(f"line {line_number}: {decision} {slot} must not contain quote/location")


def validation_markdown(result: GoldValidation) -> str:
    status = "READY" if result.ready else "NOT READY"
    lines = [
        "# Full-Text Gold Review Validation",
        "",
        f"Status: **{status}**",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Rows | {result.rows} |",
        f"| Expected rows | {result.expected_rows} |",
        f"| Reviewer 1 completed | {result.reviewer_1_completed} |",
        f"| Reviewer 2 completed | {result.reviewer_2_completed} |",
        f"| Adjudicated completed | {result.adjudicated_completed} |",
        f"| Double-reviewed rows | {result.double_reviewed} |",
        f"| Decision exact agreement | {result.decision_exact_rate} |",
        f"| Decision Cohen kappa | {result.decision_kappa} |",
        f"| Both-reported rows | {result.reported_pairs} |",
        f"| Reported-value exact agreement | {result.value_exact_rate} |",
        f"| Validation issues | {len(result.issues)} |",
        "",
        "## Issues",
        "",
    ]
    lines.extend(f"- {issue}" for issue in result.issues)
    if not result.issues:
        lines.append("- None.")
    return "\n".join(lines) + "\n"
