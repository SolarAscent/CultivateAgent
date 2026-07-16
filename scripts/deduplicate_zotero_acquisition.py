#!/usr/bin/env python3
"""Deduplicate the Zotero acquisition queue against the canonical corpus."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import tempfile
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ACQUIRE_FIELDS = ["year", "doi", "title", "why"]
AUDIT_FIELDS = [
    "source_row", "reason", "year", "doi", "title", "why",
    "matched_record_id", "matched_doi", "matched_title", "matched_source_row",
]


@dataclass(frozen=True)
class DedupResult:
    source_rows: int
    actionable: tuple[dict[str, str], ...]
    exclusions: tuple[dict[str, str], ...]
    conflicts: tuple[dict[str, str], ...]
    reason_counts: tuple[tuple[str, int], ...]
    source_sha256: str
    corpus_sha256: str


def normalize_doi(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").strip().lower()
    normalized = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", normalized)
    return normalized.rstrip(" .;,")


def normalize_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").casefold()
    return " ".join(re.sub(r"[\W_]+", " ", normalized).split())


def _read_tsv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or required - set(reader.fieldnames):
            raise ValueError(f"{path} is missing required columns")
        return list(reader)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _join_matches(matches: list[dict[str, str]], key: str) -> str:
    return ";".join(dict.fromkeys(row.get(key, "") for row in matches if row.get(key, "")))


def _audit_row(
    row: dict[str, str],
    *,
    source_row: int,
    reason: str,
    corpus_matches: list[dict[str, str]] | None = None,
    queue_matches: list[tuple[int, dict[str, str]]] | None = None,
) -> dict[str, str]:
    corpus_matches = corpus_matches or []
    queue_matches = queue_matches or []
    queue_rows = [match for _, match in queue_matches]
    return {
        "source_row": str(source_row),
        "reason": reason,
        **{field: row.get(field, "") for field in ACQUIRE_FIELDS},
        "matched_record_id": _join_matches(corpus_matches, "record_id"),
        "matched_doi": _join_matches(corpus_matches + queue_rows, "doi"),
        "matched_title": _join_matches(corpus_matches + queue_rows, "title"),
        "matched_source_row": ";".join(str(number) for number, _ in queue_matches),
    }


def deduplicate_acquisition(acquire_path: Path, corpus_path: Path) -> DedupResult:
    acquire_rows = _read_tsv(acquire_path, set(ACQUIRE_FIELDS))
    corpus_rows = _read_tsv(corpus_path, {"record_id", "title", "doi"})

    corpus_by_doi: dict[str, list[dict[str, str]]] = defaultdict(list)
    corpus_by_title: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in corpus_rows:
        doi = normalize_doi(row["doi"] if row["doi"].upper() != "NONE" else "")
        title = normalize_title(row["title"])
        if doi:
            corpus_by_doi[doi].append(row)
        if title:
            corpus_by_title[title].append(row)

    queue_by_title: dict[str, list[tuple[int, dict[str, str]]]] = defaultdict(list)
    for source_row, row in enumerate(acquire_rows, start=2):
        queue_by_title[normalize_title(row["title"])].append((source_row, row))

    actionable: list[dict[str, str]] = []
    exclusions: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []
    reasons: Counter[str] = Counter()
    assigned_rows: set[int] = set()
    for source_row, row in enumerate(acquire_rows, start=2):
        doi = normalize_doi(row["doi"])
        title = normalize_title(row["title"])
        corpus_doi_matches = corpus_by_doi.get(doi, []) if doi else []
        corpus_title_matches = corpus_by_title.get(title, []) if title else []
        queue_peers = [
            (number, peer) for number, peer in queue_by_title.get(title, [])
            if number != source_row
        ]
        queue_doi_peers = [
            (number, peer) for number, peer in queue_peers if normalize_doi(peer["doi"])
        ]

        if corpus_doi_matches:
            reason = "corpus_doi_duplicate"
            exclusions.append(_audit_row(
                row, source_row=source_row, reason=reason,
                corpus_matches=corpus_doi_matches,
            ))
        elif not doi and corpus_title_matches:
            reason = "corpus_title_duplicate_missing_doi"
            exclusions.append(_audit_row(
                row, source_row=source_row, reason=reason,
                corpus_matches=corpus_title_matches,
            ))
        elif not doi and queue_doi_peers:
            reason = "queue_title_duplicate_missing_doi"
            exclusions.append(_audit_row(
                row, source_row=source_row, reason=reason,
                queue_matches=queue_doi_peers,
            ))
        else:
            different_corpus_doi = [
                match for match in corpus_title_matches
                if normalize_doi(match["doi"] if match["doi"].upper() != "NONE" else "") != doi
            ]
            different_queue_doi = [
                (number, peer) for number, peer in queue_doi_peers
                if normalize_doi(peer["doi"]) != doi
            ]
            if doi and (different_corpus_doi or different_queue_doi):
                reason = "title_match_different_doi"
                linked_corpus = list(different_corpus_doi)
                for _, peer in different_queue_doi:
                    linked_corpus.extend(corpus_by_doi.get(normalize_doi(peer["doi"]), []))
                linked_corpus = list({row["record_id"]: row for row in linked_corpus}.values())
                conflicts.append(_audit_row(
                    row, source_row=source_row, reason=reason,
                    corpus_matches=linked_corpus,
                    queue_matches=different_queue_doi,
                ))
            else:
                reason = "actionable"
                actionable.append({field: row.get(field, "") for field in ACQUIRE_FIELDS})
        reasons[reason] += 1
        assigned_rows.add(source_row)

    if len(assigned_rows) != len(acquire_rows):
        raise ValueError("acquisition rows were not partitioned exactly once")
    if len(actionable) + len(exclusions) + len(conflicts) != len(acquire_rows):
        raise ValueError("derived acquisition outputs do not partition the source")
    corpus_dois = set(corpus_by_doi)
    actionable_overlap = {
        normalize_doi(row["doi"]) for row in actionable if normalize_doi(row["doi"])
    } & corpus_dois
    if actionable_overlap:
        raise ValueError("actionable queue still overlaps canonical corpus DOI values")
    actionable_keys = [
        normalize_doi(row["doi"]) or f"title:{normalize_title(row['title'])}"
        for row in actionable
    ]
    if len(actionable_keys) != len(set(actionable_keys)):
        raise ValueError("actionable queue still contains duplicate DOI/title identities")

    return DedupResult(
        source_rows=len(acquire_rows), actionable=tuple(actionable),
        exclusions=tuple(exclusions), conflicts=tuple(conflicts),
        reason_counts=tuple(sorted(reasons.items())),
        source_sha256=_hash(acquire_path), corpus_sha256=_hash(corpus_path),
    )


def _atomic_tsv(path: Path, fields: list[str], rows: tuple[dict[str, str], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", dir=path.parent,
        prefix=f".{path.name}.", delete=False,
    ) as handle:
        temporary = Path(handle.name)
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def report_markdown(
    result: DedupResult,
    *,
    actionable_path: Path,
    exclusions_path: Path,
    conflicts_path: Path,
) -> str:
    reason_lines = [f"| `{reason}` | {count} |" for reason, count in result.reason_counts]
    return "\n".join([
        "# Zotero Acquisition Queue Deduplication",
        "",
        "Status: **PASS**; deterministic partition against the canonical corpus.",
        "",
        "The original DeepSeek-generated acquisition list is retained unchanged. DOI matches are",
        "automatic exclusions. Title-only exclusion is allowed only when the candidate DOI is",
        "missing; equal titles with different non-empty DOIs are isolated for human review.",
        "",
        "## Counts",
        "",
        "| Output | Rows |",
        "|---|---:|",
        f"| Source queue | {result.source_rows} |",
        f"| Actionable acquisition | {len(result.actionable)} |",
        f"| Deterministic exclusions | {len(result.exclusions)} |",
        f"| Human-review conflicts | {len(result.conflicts)} |",
        "",
        "## Partition Reasons",
        "",
        "| Reason | Rows |",
        "|---|---:|",
        *reason_lines,
        "",
        "## Integrity",
        "",
        f"- Source SHA-256: `{result.source_sha256}`",
        f"- Corpus SHA-256: `{result.corpus_sha256}`",
        f"- Actionable output: `{actionable_path.as_posix()}`; SHA-256 `{_hash(actionable_path)}`",
        f"- Exclusion audit: `{exclusions_path.as_posix()}`; SHA-256 `{_hash(exclusions_path)}`",
        f"- Conflict audit: `{conflicts_path.as_posix()}`; SHA-256 `{_hash(conflicts_path)}`",
        "- Every source row appears in exactly one derived category.",
        "- Actionable DOI overlap with the canonical corpus is zero.",
        "- Actionable DOI/title identities are unique.",
        "- Conflict rows are not authorized for acquisition until reviewed.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--acquire", type=Path, default=Path("data/literature/zotero_acquire_list.tsv")
    )
    parser.add_argument(
        "--corpus", type=Path, default=Path("data/literature/bovine_corpus_manifest.tsv")
    )
    parser.add_argument(
        "--out", type=Path, default=Path("data/literature/zotero_acquire_actionable.tsv")
    )
    parser.add_argument(
        "--exclusions", type=Path,
        default=Path("data/literature/zotero_acquire_exclusions.tsv"),
    )
    parser.add_argument(
        "--conflicts", type=Path,
        default=Path("data/literature/zotero_acquire_conflicts.tsv"),
    )
    parser.add_argument(
        "--report", type=Path, default=Path("docs/ZOTERO_ACQUISITION_DEDUP.md")
    )
    args = parser.parse_args()

    result = deduplicate_acquisition(args.acquire, args.corpus)
    _atomic_tsv(args.out, ACQUIRE_FIELDS, result.actionable)
    _atomic_tsv(args.exclusions, AUDIT_FIELDS, result.exclusions)
    _atomic_tsv(args.conflicts, AUDIT_FIELDS, result.conflicts)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report_markdown(
        result, actionable_path=args.out, exclusions_path=args.exclusions,
        conflicts_path=args.conflicts,
    ), encoding="utf-8")
    print(
        f"source={result.source_rows} actionable={len(result.actionable)} "
        f"excluded={len(result.exclusions)} conflicts={len(result.conflicts)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
