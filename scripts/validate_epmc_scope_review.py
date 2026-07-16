#!/usr/bin/env python3
"""Validate bovine JATS scope decisions against local source-hash locators."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

from cultivate_agent.evaluate.scope_review import validate_scope_review
from cultivate_agent.ingest.epmc_canary import _checkpoint_path
from cultivate_agent.ingest.oa_audit import normalize_doi
from cultivate_agent.schema import structured_paper_from_grobid_tei_path


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=Path("data/literature/zotero_epmc_bovine_scope_review.tsv"))
    parser.add_argument("--canary", type=Path, default=Path("data/literature/zotero_epmc_bovine_canary.tsv"))
    parser.add_argument("--verification", type=Path, default=Path("data/literature/zotero_epmc_bovine_canary_verification.tsv"))
    parser.add_argument("--corpus", type=Path, default=Path("data/literature/bovine_corpus_manifest.tsv"))
    parser.add_argument("--queue", type=Path, default=Path("data/literature/bovine_human_review_queue.tsv"))
    parser.add_argument("--source-manifest", type=Path, default=Path("data/literature/bovine_jats_source_manifest.tsv"))
    parser.add_argument(
        "--acquisition", type=Path,
        default=Path("data/literature/bovine_jats_acquisition_R052_R056.tsv"),
    )
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("data/checkpoints/zotero_epmc_canary"))
    parser.add_argument("--out", type=Path, default=Path("docs/ZOTERO_EPMC_BOVINE_SCOPE_REVIEW.md"))
    args = parser.parse_args()

    reviews = _read(args.review)
    canary = _read(args.canary)
    verification = _read(args.verification)
    canary_by_id = {row["canary_id"]: row for row in canary}
    papers = {}
    source_hashes = {}
    for row in reviews:
        source = canary_by_id[row["canary_id"]]
        path = _checkpoint_path(args.checkpoint_dir, source["doi"], source["pmcid"])
        data = path.read_bytes()
        source_hashes[row["canary_id"]] = hashlib.sha256(data).hexdigest()
        papers[row["canary_id"]] = structured_paper_from_grobid_tei_path(
            row["canary_id"], path, title=source["title"],
        )
    corpus = _read(args.corpus)
    queue = _read(args.queue)
    source_manifest = _read(args.source_manifest)
    acquisition = _read(args.acquisition)
    promoted_record_ids = {
        row["record_id"] for row in reviews if row["decision"].startswith("promote_")
    }
    promoted_review_ids = {
        row["review_id"] for row in reviews if row["decision"].startswith("promote_")
    }
    result = validate_scope_review(
        reviews, canary_rows=canary, verification_rows=verification,
        papers=papers, source_hashes=source_hashes,
        existing_record_ids={row["record_id"] for row in corpus} - promoted_record_ids,
        existing_review_ids={row["review_id"] for row in queue} - promoted_review_ids,
    )
    corpus_by_id = {row["record_id"]: row for row in corpus}
    queue_by_id = {row["review_id"]: row for row in queue}
    sources_by_id = {row["record_id"]: row for row in source_manifest}
    verification_by_id = {row["canary_id"]: row for row in verification}
    review_by_record = {row["record_id"]: row for row in reviews if row["record_id"] != "-"}
    acquisition_by_id = {row["record_id"]: row for row in acquisition}
    if set(acquisition_by_id) != set(result.promoted_record_ids):
        raise ValueError("scope acquisition report must contain exactly the promoted records")
    for record_id in result.promoted_record_ids:
        review_row = review_by_record[record_id]
        source = canary_by_id[review_row["canary_id"]]
        canonical = corpus_by_id.get(record_id)
        task = queue_by_id.get(review_row["review_id"])
        source_row = sources_by_id.get(record_id)
        acquisition_row = acquisition_by_id[record_id]
        if canonical is None or normalize_doi(canonical.get("doi", "")) != normalize_doi(source["doi"]):
            raise ValueError(f"{record_id} canonical DOI is missing or wrong")
        if task is None or task.get("source_record_id") != record_id or task.get("status") != "open":
            raise ValueError(f"{record_id} open review task is missing or wrong")
        if (
            source_row is None
            or normalize_doi(source_row.get("doi", "")) != normalize_doi(source["doi"])
            or source_row.get("pmcid", "").upper() != source["pmcid"].upper()
            or source_row.get("expected_license") != verification_by_id[review_row["canary_id"]]["license"]
        ):
            raise ValueError(f"{record_id} JATS source-manifest mapping is missing or wrong")
        if (
            acquisition_row.get("status") not in {"downloaded", "existing_verified"}
            or normalize_doi(acquisition_row.get("doi", "")) != normalize_doi(source["doi"])
            or acquisition_row.get("pmcid", "").upper() != source["pmcid"].upper()
            or acquisition_row.get("source_sha256")
            != verification_by_id[review_row["canary_id"]]["source_sha256"]
            or acquisition_row.get("error") != "-"
        ):
            raise ValueError(f"{record_id} acquisition result is missing or wrong")
    excluded_dois = {
        normalize_doi(canary_by_id[canary_id]["doi"])
        for canary_id in result.excluded_canary_ids
    }
    if excluded_dois & {normalize_doi(row.get("doi", "")) for row in corpus}:
        raise ValueError("scope-excluded DOI entered the canonical corpus")
    if excluded_dois & {normalize_doi(row.get("doi", "")) for row in source_manifest}:
        raise ValueError("scope-excluded DOI entered the JATS source manifest")
    counts = [f"| `{decision}` | {count} |" for decision, count in result.decision_counts]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join([
        "# Europe PMC Bovine Scope Review", "",
        "Status: **PASS; locator/hash validation complete**.", "",
        "This review applies the fixed first-round bovine satellite-cell/myoblast expansion",
        "scope. It promotes source candidates into open review, not approved evidence.", "",
        "## Decisions", "", "| Decision | Rows |", "|---|---:|", *counts, "",
        f"- Promoted record IDs: `{','.join(result.promoted_record_ids)}`",
        f"- Excluded canary IDs: `{','.join(result.excluded_canary_ids)}`", "",
        "## Integrity", "",
        f"- Scope-review SHA-256: `{_hash(args.review)}`",
        f"- Canary SHA-256: `{_hash(args.canary)}`",
        f"- Verification SHA-256: `{_hash(args.verification)}`",
        f"- Acquisition SHA-256: `{_hash(args.acquisition)}`",
        "- Every decision resolves three source paragraph groups: cell identity, medium",
        "  intervention, and outcome. Locator text is not copied into this report.",
        "- EBC02/EBC03 are held outside the first-round corpus because their experimental",
        "  cells are embryonic and/or mesenchymal stem cells, not satellite cells/myoblasts.",
        "- All promoted records retain explicit serum, composition, genotype, source-cell,",
        "  or surface-context transfer limits for human review.", "",
    ]) + "\n", encoding="utf-8")
    print(f"Validated {len(result.rows)} scope decisions; promoted={len(result.promoted_record_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
