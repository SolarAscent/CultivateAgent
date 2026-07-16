"""Source-hash-bound page-candidate probe using existing locator gold."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Sequence

from .deepseek_locator_probe import LocatorItem
from .quantitative_review import _sha256, _signals


PROMPT_VERSION = "page-candidate-pointer-v1"
SIGNALS = {
    "explicit_dispersion", "named_dispersion_value", "sample_size", "sd", "sem",
    "outcome", "medium", "figure_caption", "mean", "error_policy",
}


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _page_excerpt(page, *, max_chars: int) -> str:
    blocks = [_normalized(str(block[4])) for block in page.get_text("blocks", sort=True)]
    blocks = [block for block in blocks if block]
    selected = [block for block in blocks if set(_signals(block)) & SIGNALS]
    if blocks:
        selected.insert(0, blocks[0])
    excerpt = "\n".join(dict.fromkeys(selected))
    return excerpt[:max_chars]


def load_page_silver(
    manifest_path: Path,
    *,
    repo_root: Path,
    negatives_per_positive: float = 1.0,
    max_excerpt_chars: int = 2400,
    fitz_module=None,
) -> list[LocatorItem]:
    """Aggregate existing block gold to pages and add deterministic unlabeled decoys."""
    if negatives_per_positive < 0 or max_excerpt_chars < 400:
        raise ValueError("invalid page-probe sampling settings")
    if fitz_module is None:
        import fitz as fitz_module  # type: ignore[no-redef]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources = {str(row["record_id"]): row for row in manifest.get("sources", [])}
    positive_pages: dict[str, set[int]] = {record_id: set() for record_id in sources}
    for row in manifest.get("candidates", []):
        record_id = str(row["record_id"])
        if record_id not in sources:
            raise ValueError(f"candidate source is absent: {record_id}")
        positive_pages[record_id].add(int(row["pdf_page"]))
    if not sources or not all(positive_pages.values()):
        raise ValueError("page silver requires candidates for every source")

    raw: list[tuple[str, int, str, bool, str]] = []
    for record_id in sorted(sources):
        source = sources[record_id]
        path = repo_root / source["pdf_path"]
        if not path.is_file() or _sha256(path.read_bytes()) != source["pdf_sha256"]:
            raise ValueError(f"{record_id}: PDF missing or hash mismatch")
        document = fitz_module.open(path)
        try:
            pages = []
            for page_index, page in enumerate(document, start=1):
                excerpt = _page_excerpt(page, max_chars=max_excerpt_chars)
                if not excerpt:
                    continue
                digest = _sha256(excerpt.encode("utf-8"))
                pages.append((page_index, excerpt, digest))
            by_number = {page_number: (excerpt, digest) for page_number, excerpt, digest in pages}
            for page_number in sorted(positive_pages[record_id]):
                if page_number not in by_number:
                    raise ValueError(f"{record_id}: gold page {page_number} has no excerpt")
                excerpt, digest = by_number[page_number]
                raw.append((record_id, page_number, excerpt, True, digest))
            decoys = [row for row in pages if row[0] not in positive_pages[record_id]]
            decoys.sort(key=lambda row: hashlib.sha256(
                f"{record_id}:{row[0]}:{row[2]}".encode()
            ).hexdigest())
            needed = round(len(positive_pages[record_id]) * negatives_per_positive)
            if len(decoys) < needed:
                raise ValueError(f"{record_id}: insufficient decoy pages")
            for page_number, excerpt, digest in decoys[:needed]:
                raw.append((record_id, page_number, excerpt, False, digest))
        finally:
            document.close()
    raw.sort(key=lambda row: hashlib.sha256(f"{row[0]}:{row[1]}:{row[4]}".encode()).hexdigest())
    return [
        LocatorItem(
            item_id=f"P{index:03d}", snippet=excerpt, positive=positive,
            record_id=record_id, pdf_page=page_number, block_index=-1,
            block_text_sha256=digest,
        )
        for index, (record_id, page_number, excerpt, positive, digest)
        in enumerate(raw, start=1)
    ]


def build_page_prompt(batch: Sequence[LocatorItem]) -> str:
    payload = {"pages": [{"id": item.item_id, "excerpt": item.snippet} for item in batch]}
    return (
        "Select every page that could help a reviewer locate quantitative cell-culture medium "
        "comparison evidence, including methods, results, tables, or figure captions. Optimize "
        "for recall; deterministic code and expert review will remove false positives. Return "
        "JSON only with exactly {\"candidate_ids\":[str]}. IDs must come from the input and "
        "must not repeat. Return no excerpts, numbers, explanations, confidence, or other keys.\n"
        "INPUT_JSON:\n" + json.dumps(payload, ensure_ascii=False, sort_keys=True)
    )
