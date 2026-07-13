"""Conservative Gate 1 audit for the bovine literature corpus manifest."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

PEER_REVIEWED_TYPES = {"primary", "review", "scoping_review"}
INCLUDED_DECISIONS = {"core", "core_context", "context", "background"}
HUMAN_VERIFIED_STATUSES = {"human_verified_included", "human_verified_context"}
REQUIRED_INCLUDED_FIELDS = (
    "title", "doi", "url", "species", "cell_type", "stage", "medium_focus", "why_included"
)

THRESHOLDS = {
    "peer_reviewed_sources_min": 35,
    "peer_reviewed_sources_max": 50,
    "reviews_min": 8,
    "primary_papers_min": 12,
    "bovine_primary_min": 10,
    "dose_primary_min": 5,
    "serum_free_bovine_primary_min": 3,
}


@dataclass(frozen=True)
class CorpusIssue:
    record_id: str
    category: str
    detail: str


@dataclass
class CorpusGateResult:
    rows: int
    metrics: Dict[str, int]
    checks: Dict[str, bool]
    issues: List[CorpusIssue]

    @property
    def gate_status(self) -> str:
        return "PASS" if all(self.checks.values()) and not self.issues else "FAIL"


def audit_corpus_manifest(path: Path) -> CorpusGateResult:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    included = [row for row in rows if row.get("decision") in INCLUDED_DECISIONS]
    peer = [row for row in included if row.get("source_type") in PEER_REVIEWED_TYPES]
    reviews = [row for row in peer if row.get("source_type") in {"review", "scoping_review"}]
    primary = [row for row in peer if row.get("source_type") == "primary"]
    bovine_primary = [row for row in primary if _contains(row.get("species"), "bovine")]
    dose_primary = [row for row in primary if (row.get("dose_or_quant") or "").lower().startswith("yes")]
    sf_bovine_primary = [
        row for row in bovine_primary
        if _contains(row.get("medium_focus"), "serum-free")
        or _contains(row.get("medium_focus"), "serum free")
    ]
    p1_core = [
        row for row in rows
        if row.get("priority") == "P1" and row.get("decision") in {"core", "core_context"}
    ]
    issues: List[CorpusIssue] = []
    for record_id in _duplicate_values(rows, "record_id"):
        issues.append(CorpusIssue(record_id, "duplicate_record_id", record_id))
    for doi in _duplicate_values(included, "doi", ignored={"none", "unknown", "na", "nr"}):
        duplicate_ids = ", ".join(
            row.get("record_id", "") for row in included
            if (row.get("doi") or "").strip().lower() == doi
        )
        issues.append(CorpusIssue(duplicate_ids, "duplicate_doi", doi))
    for row in included:
        missing = [field for field in REQUIRED_INCLUDED_FIELDS if _missing(row.get(field))]
        if missing:
            issues.append(CorpusIssue(row.get("record_id", ""), "missing_metadata", ", ".join(missing)))
    for row in p1_core:
        if row.get("review_status") not in HUMAN_VERIFIED_STATUSES:
            issues.append(CorpusIssue(
                row.get("record_id", ""),
                "human_curation_pending",
                row.get("review_status") or "blank",
            ))

    metrics = {
        "peer_reviewed_sources": len(peer),
        "reviews": len(reviews),
        "primary_papers": len(primary),
        "bovine_primary": len(bovine_primary),
        "dose_primary": len(dose_primary),
        "serum_free_bovine_primary": len(sf_bovine_primary),
        "included_rows": len(included),
        "p1_core_rows": len(p1_core),
        "p1_core_human_verified": sum(
            row.get("review_status") in HUMAN_VERIFIED_STATUSES for row in p1_core
        ),
    }
    checks = {
        "peer_reviewed_range": (
            THRESHOLDS["peer_reviewed_sources_min"]
            <= metrics["peer_reviewed_sources"]
            <= THRESHOLDS["peer_reviewed_sources_max"]
        ),
        "reviews_min": metrics["reviews"] >= THRESHOLDS["reviews_min"],
        "primary_min": metrics["primary_papers"] >= THRESHOLDS["primary_papers_min"],
        "bovine_primary_min": metrics["bovine_primary"] >= THRESHOLDS["bovine_primary_min"],
        "dose_primary_min": metrics["dose_primary"] >= THRESHOLDS["dose_primary_min"],
        "serum_free_bovine_primary_min": (
            metrics["serum_free_bovine_primary"]
            >= THRESHOLDS["serum_free_bovine_primary_min"]
        ),
        "included_metadata_complete": not any(i.category == "missing_metadata" for i in issues),
        "unique_record_ids": not any(i.category == "duplicate_record_id" for i in issues),
        "unique_included_dois": not any(i.category == "duplicate_doi" for i in issues),
        "p1_core_human_curated": metrics["p1_core_human_verified"] == metrics["p1_core_rows"],
    }
    return CorpusGateResult(rows=len(rows), metrics=metrics, checks=checks, issues=issues)


def _contains(value: object, needle: str) -> bool:
    return needle.lower() in str(value or "").lower()


def _missing(value: object) -> bool:
    return str(value or "").strip().lower() in {"", "unknown", "nr", "na", "unc"}


def _duplicate_values(
    rows: Sequence[Dict[str, str]], field: str, *, ignored: set[str] | None = None
) -> List[str]:
    ignored = ignored or set()
    counts: Dict[str, int] = {}
    for row in rows:
        value = (row.get(field) or "").strip().lower()
        if value and value not in ignored:
            counts[value] = counts.get(value, 0) + 1
    return sorted(value for value, count in counts.items() if count > 1)


def corpus_gate_markdown(result: CorpusGateResult) -> str:
    lines = [
        "# Bovine Corpus Gate 1 Audit",
        "",
        f"Status: **{result.gate_status}**",
        "",
        "Numerical coverage and metadata checks apply only to design-included",
        "manifest decisions; deferred records cannot satisfy corpus thresholds.",
        "P1 core/core-context records additionally require",
        "explicit human curation status.",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    lines.extend(f"| {name} | {value} |" for name, value in result.metrics.items())
    lines.extend(["", "## Checks", "", "| Check | Result |", "|---|---|"])
    lines.extend(f"| {name} | {'PASS' if passed else 'FAIL'} |" for name, passed in result.checks.items())
    lines.extend(["", "## Issues", ""])
    if result.issues:
        lines.extend(
            f"- `{issue.record_id}` [{issue.category}]: {issue.detail}"
            for issue in result.issues
        )
    else:
        lines.append("- None.")
    return "\n".join(lines) + "\n"


def write_corpus_issues_tsv(issues: Sequence[CorpusIssue], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["record_id", "category", "detail"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for issue in issues:
            writer.writerow(issue.__dict__)
    return path
