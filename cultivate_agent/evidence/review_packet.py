"""Build human-review packets from the review queue and local full text.

The packet is deliberately conservative: it finds candidate passage locations
for a human reviewer, but it does not adjudicate evidence and does not embed long
paper excerpts in committed docs.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

from ..ingest import iter_ingested
from ..schema.paper import PaperMetadata, PaperPaths

_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9+\-_/%.]*")
_STOP = {
    "about", "after", "against", "also", "and", "any", "are", "can", "could",
    "did", "does", "for", "from", "has", "have", "how", "into", "its", "not",
    "only", "or", "over", "paper", "record", "should", "that", "the", "their",
    "these", "this", "use", "used", "using", "what", "when", "where", "which",
    "with", "without", "would",
}
_DOMAIN_KEEP = {
    "b8", "b9", "beefy", "fgf2", "bfgf", "albumin", "serum", "free", "bovine",
    "satellite", "myoblast", "proliferation", "doubling", "passage", "passages",
    "myod", "pax7", "dose", "concentration", "medium", "media", "differentiation",
    "myogenic", "animal", "defined", "protein", "isolate", "insect", "plant",
    "hydrolysate", "cost", "endpoint", "composition", "formulation",
}


@dataclass
class ReviewTask:
    review_id: str
    priority: str
    source_record_id: str
    evidence_topic: str
    field_to_verify: str
    human_question: str
    decision_impact: str
    suggested_action: str
    status: str


@dataclass
class ManifestRecord:
    record_id: str
    title: str
    doi: str = ""
    year: str = ""
    species: str = ""
    cell_type: str = ""
    stage: str = ""
    medium_focus: str = ""
    endpoints: str = ""


@dataclass
class PassageHit:
    paper_id: str
    title: str
    fulltext_path: str
    start: int
    end: int
    score: float
    matched_terms: List[str] = field(default_factory=list)
    locator: str = ""


@dataclass
class ReviewPacketItem:
    task: ReviewTask
    manifest: Optional[ManifestRecord]
    paper_id: str = ""
    title: str = ""
    fulltext_path: str = ""
    status: str = "missing_source"
    query_terms: List[str] = field(default_factory=list)
    hits: List[PassageHit] = field(default_factory=list)


def load_review_tasks(path: str | Path, *, ids: Optional[set[str]] = None) -> List[ReviewTask]:
    out: List[ReviewTask] = []
    with Path(path).open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            rid = row.get("review_id", "")
            if ids and rid not in ids:
                continue
            out.append(ReviewTask(
                review_id=rid,
                priority=row.get("priority", ""),
                source_record_id=row.get("source_record_id", ""),
                evidence_topic=row.get("evidence_topic", ""),
                field_to_verify=row.get("field_to_verify", ""),
                human_question=row.get("human_question", ""),
                decision_impact=row.get("decision_impact", ""),
                suggested_action=row.get("suggested_action", ""),
                status=row.get("status", ""),
            ))
    return out


def load_manifest(path: str | Path) -> dict[str, ManifestRecord]:
    records: dict[str, ManifestRecord] = {}
    with Path(path).open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            rid = row.get("record_id", "")
            if not rid:
                continue
            records[rid] = ManifestRecord(
                record_id=rid,
                title=row.get("title", ""),
                doi=row.get("doi", ""),
                year=row.get("year", ""),
                species=row.get("species", ""),
                cell_type=row.get("cell_type", ""),
                stage=row.get("stage", ""),
                medium_focus=row.get("medium_focus", ""),
                endpoints=row.get("endpoints", ""),
            )
    return records


def build_review_packet(
    *,
    review_queue_path: str | Path,
    manifest_path: str | Path,
    papers_dir: str | Path,
    review_ids: Iterable[str],
    top_k: int = 5,
    path_base: str | Path | None = None,
) -> List[ReviewPacketItem]:
    ids = set(review_ids)
    tasks = load_review_tasks(review_queue_path, ids=ids)
    manifest = load_manifest(manifest_path)
    ingested = list(iter_ingested(papers_dir))
    display_base = Path(path_base).resolve() if path_base is not None else Path.cwd().resolve()
    out: List[ReviewPacketItem] = []
    for task in tasks:
        rec = manifest.get(task.source_record_id)
        terms = _query_terms(task, rec)
        match = _best_paper_match(rec, ingested)
        item = ReviewPacketItem(task=task, manifest=rec, query_terms=terms)
        if not match:
            item.status = "missing_ingested_paper"
            out.append(item)
            continue
        paths, meta = match
        item.paper_id = meta.ref.paper_id
        item.title = meta.ref.title
        item.fulltext_path = _display_path(paths.fulltext, display_base)
        text = paths.read_fulltext()
        if not text.strip():
            item.status = "missing_fulltext"
        else:
            item.status = "ready_for_human_review"
            item.hits = rank_passages(text, terms, meta, paths, top_k=top_k, path_base=display_base)
        out.append(item)
    return out


def rank_passages(
    text: str,
    terms: List[str],
    meta: PaperMetadata,
    paths: PaperPaths,
    *,
    top_k: int = 5,
    path_base: str | Path | None = None,
) -> List[PassageHit]:
    passages = _paragraph_spans(text)
    term_set = {t.lower() for t in terms}
    display_base = Path(path_base).resolve() if path_base is not None else Path.cwd().resolve()
    hits: List[PassageHit] = []
    for start, end, passage in passages:
        words = {w.lower() for w in _WORD_RE.findall(passage)}
        matched = sorted(term_set & words)
        if not matched:
            continue
        score = len(matched)
        score += sum(1 for t in matched if t in _DOMAIN_KEEP) * 0.5
        score += min(2.0, len(re.findall(r"\b\d+(?:\.\d+)?\s*(?:ng/ml|ug/ml|µg/ml|mg/ml|g/l|%|days?|passages?)\b", passage, re.I)))
        hits.append(PassageHit(
            paper_id=meta.ref.paper_id,
            title=meta.ref.title,
            fulltext_path=_display_path(paths.fulltext, display_base),
            start=start,
            end=end,
            score=round(score, 3),
            matched_terms=matched,
            locator=_short_locator(passage, matched),
        ))
    hits.sort(key=lambda h: (-h.score, h.start))
    return hits[:top_k]


def _display_path(path: Path, base: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(base).as_posix()
    except ValueError:
        return str(resolved)


def write_review_packet_markdown(items: List[ReviewPacketItem], path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    ready = sum(1 for i in items if i.status == "ready_for_human_review")
    lines = [
        "# Human Review Packet: H001-H016",
        "",
        "Status: candidate passage locators for human adjudication; not an AI decision.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Review tasks | {len(items)} |",
        f"| Tasks with local full text | {ready} |",
        f"| Tasks needing source/fulltext action | {len(items) - ready} |",
        "",
        "## How To Use",
        "",
        "For each task, open the listed local `fulltext.txt` and inspect the character ranges.",
        "The packet avoids embedding long source excerpts; record the final human decision in",
        "`data/literature/bovine_human_review_queue.tsv` and transfer adjudicated facts to",
        "`data/literature/bovine_evidence_table.tsv`.",
        "",
    ]
    for item in items:
        task = item.task
        rec = item.manifest
        lines += [
            f"## {task.review_id}: {task.evidence_topic}",
            "",
            f"- Status: `{item.status}`",
            f"- Source record: `{task.source_record_id}`",
            f"- Manifest title: {rec.title if rec else 'MISSING'}",
            f"- Human question: {task.human_question}",
            f"- Suggested action: {task.suggested_action}",
            f"- Local paper: `{item.paper_id or 'MISSING'}`",
            f"- Full text: `{item.fulltext_path or 'MISSING'}`",
            f"- Query terms: {', '.join(item.query_terms[:24])}",
            "",
            "| Rank | Score | Character Range | Matched Terms |",
            "|---:|---:|---|---|",
        ]
        if item.hits:
            for idx, hit in enumerate(item.hits, start=1):
                lines.append(
                    f"| {idx} | {hit.score:.1f} | `{hit.start}-{hit.end}` | "
                    f"{', '.join(hit.matched_terms[:12])} |"
                )
        else:
            lines.append("| - | - | - | - |")
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def _best_paper_match(
    rec: Optional[ManifestRecord],
    ingested: list[tuple[PaperPaths, PaperMetadata]],
) -> Optional[tuple[PaperPaths, PaperMetadata]]:
    if not rec:
        return None
    target = _tokens(rec.title)
    best = None
    best_score = 0.0
    for paths, meta in ingested:
        score = _jaccard(target, _tokens(meta.ref.title))
        if rec.doi and meta.ref.doi and rec.doi.lower() == meta.ref.doi.lower():
            score += 2.0
        if score > best_score:
            best_score = score
            best = (paths, meta)
    return best if best_score >= 0.40 else None


def _query_terms(task: ReviewTask, rec: Optional[ManifestRecord]) -> List[str]:
    text = " ".join([
        task.evidence_topic,
        task.field_to_verify,
        task.human_question,
        task.suggested_action,
        rec.title if rec else "",
        rec.medium_focus if rec else "",
        rec.endpoints if rec else "",
    ])
    terms = []
    seen = set()
    for tok in _tokens(text):
        if tok in seen:
            continue
        seen.add(tok)
        terms.append(tok)
    return terms


def _tokens(text: str) -> List[str]:
    out = []
    for m in _WORD_RE.finditer(text.lower()):
        tok = m.group(0).strip("-_/")
        if len(tok) < 3 and tok not in {"b8", "b9"}:
            continue
        if tok in _STOP and tok not in _DOMAIN_KEEP:
            continue
        out.append(tok)
    return out


def _jaccard(a: List[str], b: List[str]) -> float:
    aa, bb = set(a), set(b)
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / len(aa | bb)


def _paragraph_spans(text: str) -> List[tuple[int, int, str]]:
    spans: List[tuple[int, int, str]] = []
    start: Optional[int] = None
    chunks: List[str] = []
    pos = 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped:
            if start is None:
                start = pos
            chunks.append(line)
        elif start is not None:
            end = pos
            passage = "".join(chunks).strip()
            if len(passage) >= 80:
                spans.append((start, end, passage))
            start = None
            chunks = []
        pos += len(line)
    if start is not None:
        passage = "".join(chunks).strip()
        if len(passage) >= 80:
            spans.append((start, len(text), passage))
    return spans


def _short_locator(passage: str, matched: List[str], *, max_words: int = 12) -> str:
    words = _WORD_RE.findall(passage)
    if not words:
        return ""
    lower = [w.lower() for w in words]
    first = 0
    for term in matched:
        if term in lower:
            first = lower.index(term)
            break
    lo = max(0, first - 4)
    hi = min(len(words), lo + max_words)
    snippet = " ".join(words[lo:hi])
    return snippet.replace("|", "/")
