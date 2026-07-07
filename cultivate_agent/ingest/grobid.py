"""Optional GROBID REST client for PDF-to-TEI conversion.

GROBID is deliberately optional: CultivateAgent's offline ingestion still uses
PyMuPDF/pdftotext, while this module can enrich an ingested PDF with
``fulltext.xml`` when a local or remote GROBID service is available.
"""

from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path
from typing import Mapping, Optional
from urllib import error, request

from ..schema.structured_paper import StructuredPaper, structured_paper_from_grobid_tei_xml


class GrobidError(RuntimeError):
    """Raised when the optional GROBID service cannot produce TEI."""


def _endpoint(base_url: str, service: str = "processFulltextDocument") -> str:
    return f"{base_url.rstrip('/')}/api/{service.lstrip('/')}"


def _encode_multipart(
    fields: Mapping[str, str],
    file_field: str,
    file_path: Path,
) -> tuple[bytes, str]:
    boundary = f"----CultivateAgentGrobid{uuid.uuid4().hex}"
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/pdf"
    body = bytearray()

    def add_line(value: bytes | str = b"") -> None:
        if isinstance(value, str):
            value = value.encode("utf-8")
        body.extend(value)
        body.extend(b"\r\n")

    for name, value in fields.items():
        add_line(f"--{boundary}")
        add_line(f'Content-Disposition: form-data; name="{name}"')
        add_line()
        add_line(str(value))

    add_line(f"--{boundary}")
    add_line(
        f'Content-Disposition: form-data; name="{file_field}"; '
        f'filename="{file_path.name}"'
    )
    add_line(f"Content-Type: {content_type}")
    add_line()
    body.extend(file_path.read_bytes())
    body.extend(b"\r\n")
    add_line(f"--{boundary}--")

    return bytes(body), f"multipart/form-data; boundary={boundary}"


def grobid_is_alive(base_url: str = "http://localhost:8070", *, timeout: float = 5.0) -> bool:
    """Return True when a GROBID service answers its liveness endpoint."""
    try:
        with request.urlopen(_endpoint(base_url, "isalive"), timeout=timeout) as resp:
            return resp.status == 200 and resp.read().decode("utf-8", errors="ignore").strip() == "true"
    except Exception:  # noqa: BLE001
        return False


def process_fulltext_document(
    pdf_path: str | Path,
    *,
    base_url: str = "http://localhost:8070",
    timeout: float = 60.0,
    consolidate_header: int = 0,
    consolidate_citations: int = 0,
    include_raw_citations: bool = True,
    generate_ids: bool = True,
    segment_sentences: bool = False,
    tei_coordinates: Optional[list[str]] = None,
) -> str:
    """Submit a PDF to GROBID's ``processFulltextDocument`` endpoint.

    Parameters mirror the stable GROBID REST options CultivateAgent currently
    needs. The function returns TEI XML as text and raises ``GrobidError`` for
    service, request, or empty-content failures.
    """
    pdf = Path(pdf_path)
    if not pdf.exists():
        raise GrobidError(f"PDF not found: {pdf}")

    fields: dict[str, str] = {
        "consolidateHeader": str(consolidate_header),
        "consolidateCitations": str(consolidate_citations),
        "includeRawCitations": "1" if include_raw_citations else "0",
        "generateIDs": "1" if generate_ids else "0",
    }
    if segment_sentences:
        fields["segmentSentences"] = "1"
    if tei_coordinates:
        fields["teiCoordinates"] = ",".join(tei_coordinates)

    data, content_type = _encode_multipart(fields, "input", pdf)
    req = request.Request(
        _endpoint(base_url),
        data=data,
        method="POST",
        headers={
            "Content-Type": content_type,
            "Accept": "application/xml",
            "User-Agent": "CultivateAgent/0.1",
        },
    )

    try:
        with request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read()
            if resp.status == 204:
                raise GrobidError(f"GROBID returned no extractable content for {pdf.name}")
            if resp.status != 200:
                raise GrobidError(f"GROBID returned HTTP {resp.status} for {pdf.name}")
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise GrobidError(f"GROBID HTTP {exc.code} for {pdf.name}: {details[:300]}") from exc
    except error.URLError as exc:
        raise GrobidError(f"GROBID service unavailable at {base_url}: {exc.reason}") from exc

    text = payload.decode("utf-8", errors="replace").strip()
    if not text:
        raise GrobidError(f"GROBID returned empty TEI for {pdf.name}")
    return text


def write_fulltext_tei(
    pdf_path: str | Path,
    out_path: str | Path,
    **kwargs,
) -> Path:
    """Run GROBID and write the TEI XML output to ``out_path``."""
    tei = process_fulltext_document(pdf_path, **kwargs)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(tei, encoding="utf-8")
    return out


def structured_paper_from_grobid_pdf(
    paper_id: str,
    pdf_path: str | Path,
    *,
    title: Optional[str] = None,
    **kwargs,
) -> StructuredPaper:
    """Convert one PDF through GROBID and parse the returned TEI."""
    tei = process_fulltext_document(pdf_path, **kwargs)
    return structured_paper_from_grobid_tei_xml(paper_id, tei, title=title)
