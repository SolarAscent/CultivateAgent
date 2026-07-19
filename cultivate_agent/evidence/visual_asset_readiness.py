"""Deterministic, source-bound visual assets for figure-level evidence review."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ..evaluate.deepseek_visual_page_probe import PDF_HELDOUT_SELECTOR_VERSION
from ..evaluate.quantitative_review import _signals


_XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
_FIGURE_LABEL = re.compile(r"\bfig(?:ure)?\.?\s*([0-9]+[a-z]?)\b", re.I)
_CC_BY = re.compile(r"creative commons attribution(?: 4\.0)?|\bcc by\b", re.I)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as h:
        temporary = Path(h.name)
        h.write(data)
    os.replace(temporary, path)


def _local_tag(element: ET.Element) -> str:
    return element.tag.split("}")[-1]


def _text(element: ET.Element | None) -> str:
    return " ".join("".join(element.itertext()).split()) if element is not None else ""


def _figure_key(value: str) -> str:
    match = _FIGURE_LABEL.search(value)
    return match.group(1).casefold() if match else ""


@dataclass(frozen=True)
class _JatsFigure:
    figure_id: str
    label: str
    graphic_hrefs: tuple[str, ...]


@dataclass(frozen=True)
class _JatsSource:
    source_sha256: str
    license: str
    figures: dict[str, _JatsFigure]
    supplements: tuple[tuple[str, str], ...]


def _load_jats(
    record_id: str,
    *,
    paper_id: str,
    doi: str,
    source_rows: dict[str, dict[str, str]],
    acquisition_rows: dict[str, dict[str, str]],
    repo_root: Path,
) -> _JatsSource | None:
    source = source_rows.get(record_id)
    acquisition = acquisition_rows.get(record_id)
    if source is None and acquisition is None:
        return None
    if source is None or acquisition is None:
        raise ValueError(f"{record_id}: partial JATS registry entry")
    if source["paper_id"] != paper_id or acquisition["paper_id"] != paper_id:
        raise ValueError(f"{record_id}: JATS paper ID mismatch")
    expected_doi = doi.strip().casefold()
    if (
        source.get("doi", "").strip().casefold() != expected_doi
        or acquisition.get("doi", "").strip().casefold() != expected_doi
    ):
        raise ValueError(f"{record_id}: JATS DOI mismatch")
    if acquisition.get("status") != "existing_verified":
        raise ValueError(f"{record_id}: JATS acquisition is not verified")
    if source.get("expected_license") != acquisition.get("license"):
        raise ValueError(f"{record_id}: JATS license mismatch")
    path = repo_root / "data/papers" / paper_id / "fulltext.xml"
    data = path.read_bytes() if path.is_file() else b""
    if not data or _sha256(data) != acquisition["source_sha256"]:
        raise ValueError(f"{record_id}: JATS missing or hash mismatch")
    root = ET.fromstring(data)
    figures: dict[str, _JatsFigure] = {}
    for figure in (item for item in root.iter() if _local_tag(item) == "fig"):
        label_node = next((item for item in figure if _local_tag(item) == "label"), None)
        label = _text(label_node)
        key = _figure_key(label)
        hrefs = tuple(dict.fromkeys(
            item.get(_XLINK_HREF) or item.get("href") or ""
            for item in figure.iter() if _local_tag(item) == "graphic"
        ))
        hrefs = tuple(value for value in hrefs if value)
        if key:
            if key in figures:
                raise ValueError(f"{record_id}: duplicate JATS figure label {label}")
            figures[key] = _JatsFigure(figure.get("id") or "", label, hrefs)
    supplements: list[tuple[str, str]] = []
    seen_hrefs: set[str] = set()
    for supplement in (item for item in root.iter() if _local_tag(item) == "supplementary-material"):
        supplement_id = supplement.get("id") or ""
        for item in supplement.iter():
            href = item.get(_XLINK_HREF) or item.get("href") or ""
            if href and href not in seen_hrefs:
                seen_hrefs.add(href)
                supplements.append((supplement_id, href))
    return _JatsSource(
        source_sha256=acquisition["source_sha256"],
        license=source["expected_license"],
        figures=figures,
        supplements=tuple(supplements),
    )


def extract_visual_asset_readiness(
    record_ids: Sequence[str],
    *,
    corpus_rows: Sequence[dict[str, str]],
    pdf_audits: Sequence[dict[str, str]],
    heldout: dict[str, object],
    jats_sources: Sequence[dict[str, str]],
    jats_acquisitions: Sequence[dict[str, str]],
    repo_root: Path,
    output_dir: Path,
    fitz_module=None,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    """Extract candidate-page images and map them to verified source pointers."""
    if not record_ids or len(record_ids) != len(set(record_ids)):
        raise ValueError("visual asset record IDs are empty or duplicated")
    if heldout.get("selector_version") != PDF_HELDOUT_SELECTOR_VERSION:
        raise ValueError("visual assets require the frozen PDF held-out selector")
    if fitz_module is None:
        import fitz as fitz_module  # type: ignore[no-redef]
    corpus = {row["record_id"]: row for row in corpus_rows}
    audits = {row["record_id"]: row for row in pdf_audits}
    heldout_sources = {str(row["record_id"]): row for row in heldout["sources"]}
    strict_pages = {
        (str(row["record_id"]), int(row["pdf_page"])) for row in heldout["candidates"]
    }
    source_registry = {row["record_id"]: row for row in jats_sources}
    acquisition_registry = {row["record_id"]: row for row in jats_acquisitions}
    source_results: list[dict[str, object]] = []
    assets: list[dict[str, object]] = []
    supplements: list[dict[str, object]] = []
    for record_id in record_ids:
        canonical = corpus.get(record_id)
        audit = audits.get(record_id)
        heldout_source = heldout_sources.get(record_id)
        if canonical is None or audit is None or heldout_source is None:
            raise ValueError(f"{record_id}: canonical/PDF/held-out metadata is incomplete")
        if audit.get("pdf_status") != "audited":
            raise ValueError(f"{record_id}: PDF is not audited")
        if (
            audit["pdf_sha256"] != heldout_source["pdf_sha256"]
            or audit["pdf_path"] != heldout_source["pdf_path"]
        ):
            raise ValueError(f"{record_id}: held-out PDF provenance mismatch")
        pdf_path = repo_root / audit["pdf_path"]
        pdf_data = pdf_path.read_bytes() if pdf_path.is_file() else b""
        if not pdf_data or _sha256(pdf_data) != audit["pdf_sha256"]:
            raise ValueError(f"{record_id}: PDF missing or hash mismatch")
        jats = _load_jats(
            record_id,
            paper_id=audit["paper_id"],
            doi=canonical["doi"],
            source_rows=source_registry,
            acquisition_rows=acquisition_registry,
            repo_root=repo_root,
        )
        document = fitz_module.open(pdf_path)
        broad_pages = 0
        strict_count = 0
        source_asset_count = 0
        ready_asset_count = 0
        pdf_text = ""
        try:
            if len(document) != int(audit["pages"]):
                raise ValueError(f"{record_id}: audited PDF page count mismatch")
            pdf_text = "\n".join(page.get_text() for page in document)
            for page_number, page in enumerate(document, 1):
                caption_rows: list[tuple[int, tuple[float, float, float, float], str, str]] = []
                for block_index, block in enumerate(page.get_text("blocks", sort=True)):
                    text = " ".join(str(block[4]).split())
                    if {"figure_caption", "outcome", "medium"} <= set(_signals(text)):
                        caption_rows.append((
                            block_index,
                            tuple(float(value) for value in block[:4]),
                            _sha256(text.encode()),
                            _figure_key(text),
                        ))
                if not caption_rows:
                    continue
                broad_pages += 1
                candidate_class = (
                    "strict_group_stats_visual_candidate"
                    if (record_id, page_number) in strict_pages
                    else "broad_visual_candidate"
                )
                if candidate_class.startswith("strict_"):
                    strict_count += 1
                figure_keys = {row[3] for row in caption_rows if row[3]}
                if len(figure_keys) > 1:
                    raise ValueError(f"{record_id} page {page_number}: multiple figure labels")
                figure_key = next(iter(figure_keys), "")
                jats_figure = jats.figures.get(figure_key) if jats and figure_key else None
                images = page.get_images(full=True)
                if not images:
                    pixmap = page.get_pixmap(matrix=fitz_module.Matrix(2, 2), alpha=False)
                    image_records = [(0, "png", pixmap.width, pixmap.height, pixmap.tobytes("png"), ())]
                    source_kind = "rendered_page_fallback"
                else:
                    image_records = []
                    for image_index, image in enumerate(images):
                        xref = int(image[0])
                        extracted = document.extract_image(xref)
                        rects = tuple(
                            tuple(float(value) for value in rect)
                            for rect in page.get_image_rects(xref)
                        )
                        image_records.append((
                            image_index,
                            str(extracted["ext"]),
                            int(extracted["width"]),
                            int(extracted["height"]),
                            bytes(extracted["image"]),
                            rects,
                        ))
                    source_kind = "embedded_pdf_image"
                for image_index, extension, width, height, image_data, rects in image_records:
                    local_path = output_dir / record_id / f"p{page_number:03d}_i{image_index:02d}.{extension}"
                    _atomic_bytes(local_path, image_data)
                    source_asset_count += 1
                    color_count = int(fitz_module.Pixmap(image_data).color_count())
                    asset_status = "ready_for_visual_review" if color_count > 1 else "blank_asset"
                    if asset_status == "ready_for_visual_review":
                        ready_asset_count += 1
                    assets.append({
                        "record_id": record_id,
                        "doi": canonical["doi"],
                        "pdf_path": audit["pdf_path"],
                        "pdf_sha256": audit["pdf_sha256"],
                        "pdf_page": page_number,
                        "candidate_class": candidate_class,
                        "caption_block_indexes": ";".join(str(row[0]) for row in caption_rows),
                        "caption_block_sha256": ";".join(row[2] for row in caption_rows),
                        "caption_bboxes": ";".join(
                            ",".join(f"{value:.3f}" for value in row[1]) for row in caption_rows
                        ),
                        "source_kind": source_kind,
                        "image_index": image_index,
                        "image_ext": extension,
                        "image_width": width,
                        "image_height": height,
                        "image_bytes": len(image_data),
                        "image_color_count": color_count,
                        "image_sha256": _sha256(image_data),
                        "image_rects": ";".join(
                            ",".join(f"{value:.3f}" for value in rect) for rect in rects
                        ),
                        "local_asset_path": str(local_path.relative_to(repo_root)),
                        "jats_figure_id": jats_figure.figure_id if jats_figure else "",
                        "jats_figure_label": jats_figure.label if jats_figure else "",
                        "jats_graphic_hrefs": ";".join(jats_figure.graphic_hrefs) if jats_figure else "",
                        "status": asset_status,
                    })
        finally:
            document.close()
        if jats:
            license_value = jats.license
            license_evidence = "verified_jats_registry"
            paper_dir = repo_root / "data/papers" / audit["paper_id"]
            for supplement_id, href in jats.supplements:
                local_path = paper_dir / Path(href).name
                local_data = local_path.read_bytes() if local_path.is_file() else b""
                supplements.append({
                    "record_id": record_id,
                    "doi": canonical["doi"],
                    "jats_source_sha256": jats.source_sha256,
                    "supplement_id": supplement_id,
                    "href": href,
                    "local_path": str(local_path.relative_to(repo_root)) if local_data else "",
                    "local_sha256": _sha256(local_data) if local_data else "",
                    "status": "available_local" if local_data else "referenced_not_local",
                })
        elif _CC_BY.search(pdf_text):
            license_value = "CC-BY-4.0"
            license_evidence = "verified_pdf_text"
        else:
            license_value = "unverified"
            license_evidence = "none"
        source_results.append({
            "record_id": record_id,
            "paper_id": audit["paper_id"],
            "doi": canonical["doi"],
            "pdf_path": audit["pdf_path"],
            "pdf_sha256": audit["pdf_sha256"],
            "pdf_pages": int(audit["pages"]),
            "license": license_value,
            "license_evidence": license_evidence,
            "jats_status": "verified" if jats else "not_registered",
            "jats_source_sha256": jats.source_sha256 if jats else "",
            "broad_candidate_pages": broad_pages,
            "strict_candidate_pages": strict_count,
            "extracted_assets": source_asset_count,
            "status": "ready_for_visual_review" if ready_asset_count >= broad_pages else "partial",
        })
    return source_results, assets, supplements
